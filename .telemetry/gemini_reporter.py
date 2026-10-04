#!/usr/bin/env python3
"""Gemini Telemetry Bridge — reports Gemini/Antigravity session token cost to Lodge.

Scans ~/.gemini/antigravity-cli/brain/ for new transcript steps, estimates tokens,
and dispatches events via .telemetry/client.py. Runs out-of-band at SessionStart.
"""

from __future__ import annotations

import os
import sys
import json
import re
from pathlib import Path
from typing import Any

# Setup path so we can import local modules
telemetry_dir = Path(__file__).parent
sys.path.insert(0, str(telemetry_dir))

try:
    from client import get_github_username, read_project_slug, send_event_sync
    from cost_rates import estimate_cost, get_provider
    from schema import SkillInvokedPayload, make_event
except ImportError:
    # Fail-safe if imports cannot be resolved
    sys.exit(0)

# Paths
ANTIGRAVITY_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"
STATE_FILE = telemetry_dir / "gemini_reported_state.json"


def load_state() -> dict[str, int]:
    """Load reported steps state from file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:  # nosec B110
            return {}
    return {}


def save_state(state: dict[str, int]) -> None:
    """Save reported steps state to file."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:  # nosec B110
        pass


def map_model_string(text: str) -> str:
    """Map human or description model name to a cost-rates supported model ID."""
    text_lower = text.lower()
    mappings = [
        ("gemini 3.5 flash", "gemini-2.0-flash"),
        ("gemini-3.5-flash", "gemini-2.0-flash"),
        ("2.0-flash", "gemini-2.0-flash"),
        ("2.0 flash", "gemini-2.0-flash"),
        ("2.0-pro", "gemini-2.0-pro"),
        ("2.0 pro", "gemini-2.0-pro"),
        ("1.5-flash", "gemini-1.5-flash"),
        ("1.5 flash", "gemini-1.5-flash"),
        ("1.5-pro", "gemini-1.5-pro"),
        ("1.5 pro", "gemini-1.5-pro"),
        ("flash", "gemini-2.0-flash"),
        ("pro", "gemini-1.5-pro"),
    ]
    for pattern, model_id in mappings:
        if pattern in text_lower:
            return model_id
    return "gemini-1.5-pro"  # standard fallback


def detect_model(transcript_path: Path) -> str:
    """Detect the model used in this session from env or transcript content."""
    env_model = os.environ.get("ANTIGRAVITY_MODEL")
    if env_model:
        return map_model_string(env_model)

    if not transcript_path.exists():
        return "gemini-1.5-pro"

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                if "Model Selection" in line or "model" in line.lower():
                    return map_model_string(line)
    except Exception:  # nosec B110
        pass

    return "gemini-1.5-pro"


def estimate_tokens(text: str) -> tuple[int, int]:
    """Estimate input and output tokens using a 90% input / 10% output split."""
    words = len(text.split())
    if words == 0:
        return 0, 0
    total_tokens = max(1, int(words * 1.33))
    tokens_in = max(1, int(total_tokens * 0.90))
    tokens_out = max(1, int(total_tokens * 0.10))
    return tokens_in, tokens_out


def _parse_content_blocks(content: str) -> list[str]:
    """Extract JSON-like blocks via brace matching."""
    blocks = []
    brace_count = 0
    current_block = []
    for char in content:
        if char == "{":
            brace_count += 1
            current_block.append(char)
        elif char == "}":
            if brace_count > 0:
                brace_count -= 1
                current_block.append(char)
                if brace_count == 0:
                    blocks.append("".join(current_block))
                    current_block = []
            else:
                current_block = []
        elif brace_count > 0:
            current_block.append(char)
    return blocks


def _parse_block_relation(block_str: str) -> tuple[str, str] | None:
    """Parse a single JSON block to extract (conversationId, typeName) if valid."""
    try:
        data = json.loads(block_str)
        if isinstance(data, dict):
            spec = data.get("spec")
            result = data.get("result")
            if isinstance(spec, dict) and isinstance(result, dict):
                t_name = spec.get("typeName") or spec.get("TypeName")
                c_id = result.get("conversationId")
                if t_name and c_id:
                    return c_id, t_name
    except Exception:  # nosec B110
        pass
    return None


def _extract_relations_from_blocks(
    blocks: list[str], parent_id: str, relations: dict[str, tuple[str, str]]
) -> None:
    """Extract parent-child subagent relations from JSON blocks."""
    for b in blocks:
        parsed = _parse_block_relation(b)
        if parsed:
            c_id, t_name = parsed
            relations[c_id] = (parent_id, t_name)


def _map_zipped_relations(
    c_ids: list[str],
    t_names: list[str],
    parent_id: str,
    relations: dict[str, tuple[str, str]],
) -> None:
    """Map zipped lists of conversation IDs and type names."""
    if len(t_names) == 1 and len(c_ids) == 1:
        relations[c_ids[0]] = (parent_id, t_names[0])
    elif len(t_names) == len(c_ids) and len(t_names) > 0:
        for c_id, t_name in zip(c_ids, t_names):
            relations[c_id] = (parent_id, t_name)


def _extract_relations_from_line(
    line: str,
    parent_id: str,
    relations: dict[str, tuple[str, str]],
    type_name_re: re.Pattern,
    conv_id_re: re.Pattern,
) -> None:
    """Extract parent-child subagent relations from a raw transcript line."""
    try:
        entry = json.loads(line)
    except Exception:  # nosec B112
        return

    content = entry.get("content", "") or ""
    blocks = _parse_content_blocks(content)
    _extract_relations_from_blocks(blocks, parent_id, relations)

    t_names = type_name_re.findall(line)
    c_ids = conv_id_re.findall(line)
    _map_zipped_relations(c_ids, t_names, parent_id, relations)


def _scan_single_session_relations(
    session_dir: Path,
    relations: dict[str, tuple[str, str]],
    type_name_re: re.Pattern,
    conv_id_re: re.Pattern,
) -> None:
    """Scan a single session directory for subagent relations."""
    if not session_dir.is_dir() or session_dir.name.startswith("."):
        return

    parent_id = session_dir.name
    t_file = session_dir / ".system_generated" / "logs" / "transcript_full.jsonl"
    if not t_file.exists():
        t_file = session_dir / ".system_generated" / "logs" / "transcript.jsonl"

    if not t_file.exists():
        return

    try:
        with open(t_file, "r", encoding="utf-8") as f:
            for line in f:
                if "conversationId" in line:
                    _extract_relations_from_line(
                        line, parent_id, relations, type_name_re, conv_id_re
                    )
    except Exception:  # nosec B110
        pass


def build_subagent_relationship_map() -> dict[str, tuple[str, str]]:
    """Scan all transcript files to map child_session_id -> (parent_session_id, type_name)."""
    relations: dict[str, tuple[str, str]] = {}
    if not ANTIGRAVITY_BRAIN_DIR.exists():
        return relations

    try:
        type_name_re = re.compile(r'"[tT]ypeName"\s*:\s*"([^"]+)"')
        conv_id_re = re.compile(r'"conversationId"\s*:\s*"([a-f0-9\-]{36})"')

        for session_dir in ANTIGRAVITY_BRAIN_DIR.iterdir():
            _scan_single_session_relations(
                session_dir, relations, type_name_re, conv_id_re
            )
    except Exception:  # nosec B110
        pass

    return relations


def get_session_skill_names(
    session_id: str, relations: dict[str, tuple[str, str]]
) -> tuple[str, str | None]:
    """Recursively resolve the skill_name and parent_skill_name for a given session."""
    if session_id in relations:
        parent_id, type_name = relations[session_id]
        parent_skill, _ = get_session_skill_names(parent_id, relations)
        return type_name, parent_skill
    return "antigravity-gemini-session", None


def _process_transcript_line(
    entry: dict[str, Any],
    resolved_skill_name: str,
    parent_skill_name: str | None,
    model: str,
    provider: str,
    project_slug: str,
    username: str,
) -> None:
    """Analyze a single transcript entry and dispatch its event if eligible."""
    content = entry.get("content", "") or ""
    thinking = entry.get("thinking", "") or ""
    full_text = (str(content) + " " + str(thinking)).strip()

    if not full_text:
        return

    tokens_in, tokens_out = estimate_tokens(full_text)
    cost = estimate_cost(model, tokens_in, tokens_out)

    skill_name = resolved_skill_name
    if skill_name == "antigravity-gemini-session":
        if "tool_calls" in entry or "skill" in full_text.lower():
            skill_name = "custom-agent-skill"

    payload = SkillInvokedPayload(
        skill_name=skill_name,
        skill_path="",
        model=model,
        provider=provider,
        parent_skill_name=parent_skill_name,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        tokens_cache_write=None,
        tokens_cache_read=None,
        estimated_cost_usd=cost,
        client="gemini-antigravity",
    )

    send_event_sync(make_event("skill.invoked", project_slug, username, payload))


def _process_session(
    session_dir: Path,
    state: dict[str, int],
    project_slug: str,
    username: str,
    relations: dict[str, tuple[str, str]],
) -> None:
    """Process a single session and send its telemetry events."""
    transcript_path = session_dir / ".system_generated" / "logs" / "transcript.jsonl"
    if not transcript_path.exists():
        return

    session_id = session_dir.name
    last_reported_step = state.get(session_id, -1)
    max_step_in_file = last_reported_step

    model = detect_model(transcript_path)
    provider = get_provider(model)
    resolved_skill_name, parent_skill_name = get_session_skill_names(
        session_id, relations
    )

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                step_index = entry.get("step_index", 0)
                if step_index <= last_reported_step:
                    continue

                if step_index > max_step_in_file:
                    max_step_in_file = step_index

                _process_transcript_line(
                    entry,
                    resolved_skill_name,
                    parent_skill_name,
                    model,
                    provider,
                    project_slug,
                    username,
                )

        state[session_id] = max_step_in_file
    except Exception:  # nosec B110
        pass


def main() -> int:
    # Silent fail-safe checks
    try:
        if not ANTIGRAVITY_BRAIN_DIR.exists():
            return 0

        state = load_state()
        project_slug = read_project_slug()
        username = get_github_username()

        # Build subagent relationship map
        relations = build_subagent_relationship_map()

        # Scan sessions and sort by modification time to keep only top 15 (recent ones)
        session_dirs = []
        for p in ANTIGRAVITY_BRAIN_DIR.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                t_file = p / ".system_generated" / "logs" / "transcript.jsonl"
                mtime = t_file.stat().st_mtime if t_file.exists() else p.stat().st_mtime
                session_dirs.append((mtime, p))

        session_dirs.sort(key=lambda x: x[0], reverse=True)
        recent_sessions = [p for _, p in session_dirs[:15]]

        for session_dir in recent_sessions:
            _process_session(session_dir, state, project_slug, username, relations)

        save_state(state)

    except Exception:  # nosec B110
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
