#!/usr/bin/env python3
"""Stop hook — reports Claude Code session token cost to Lodge telemetry.

Tokens are attributed to each /skill invoked during the session by scanning
the transcript for Skill tool_use entries. Tokens accumulated before the first
Skill call (or between non-skill tool calls) are reported as "claude-code-session".
This is a heuristic: each skill gets the tokens of messages from its invocation
until the next Skill invocation. Nesting is not tracked.

ADR-0061 — attribution correctness:
- The Stop hook fires at the end of EVERY turn, so each run reports only the
  DELTA since the last accounted report, tracked per transcript in a watermark
  inside ~/.cornerstone/processed_transcripts.json. Hook runs never mark a
  transcript done (the session may continue); the catchup cron finalizes stale
  transcripts after sending any remaining delta.
- Session context is resolved by walking UP from the session cwd to the nearest
  Lodge-configured ancestor (.telemetry/.env.lodge or .cornerstone with a
  telemetry URL). Only if that fails does transcript inference run, and it is
  restricted to Lodge-configured git roots — an ungoverned cwd can no longer
  shadow a governed project.
- Events carry session_id (transcript stem) and report_kind="delta".
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ADR: 0058 — flush_pending_events for Stop-hook durability
# ADR: 0061 — delta reporting, context walk-up, cache pricing
from client import (  # noqa: E402
    flush_pending_events,
    get_github_username,
    send_event_sync,
)
from cost_rates import estimate_cost, get_provider  # noqa: E402
from schema import SkillInvokedPayload, ToolExecutedPayload, make_event  # noqa: E402


def _find_git_root(file_path: str) -> str | None:
    """Walk ancestor dirs until we find .git; return that path or None."""
    try:
        p = Path(file_path)
        if p.is_file():
            p = p.parent
        while True:
            if (p / ".git").exists():
                return str(p)
            parent = p.parent
            if parent == p:
                return None
            p = parent
    except OSError:
        return None


_branch_cache: str | None = None


def _current_branch() -> str | None:
    """Return the current git branch (cached per run) for cost-per-feature.

    Lodge groups spend by this so a ``feature/*`` branch's total = the cost of
    implementing that feature. None when detached/unavailable (event omits it).
    """
    global _branch_cache
    if _branch_cache is not None:
        return _branch_cache or None
    branch = ""
    try:
        import subprocess  # nosec B404

        result = subprocess.run(  # nosec B603, B607
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch == "HEAD":  # detached
                branch = ""
    except Exception:  # nosec B110  # noqa: BLE001 — git unavailable → no feature tag
        branch = ""
    _branch_cache = branch
    return branch or None


def _git_out(*args: str) -> str:
    """Run a git command, return stripped stdout ('' on any failure)."""
    try:
        import subprocess  # nosec B404

        r = subprocess.run(  # nosec B603, B607
            ["git", *args], capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # nosec B110  # noqa: BLE001 — git unavailable → no tag
        return ""


_commit_cache: str | None = None
_commit_read = False


def _current_commit() -> str | None:
    """Return the current HEAD commit sha (cached) so Lodge can attribute spend
    to a commit. None when unavailable."""
    global _commit_cache, _commit_read
    if _commit_read:
        return _commit_cache
    _commit_read = True
    _commit_cache = _git_out("rev-parse", "HEAD") or None
    return _commit_cache


_issue_cache: str | None = None
_issue_read = False
# Branch conventions that carry an issue number: feature/123-x, fix/123-x,
# 123-x, issue-123, issue/123, gh-123, #123.
_BRANCH_ISSUE_RE = re.compile(
    r"(?:^|/)(?:issue[-/]?|gh-|#)?(\d{1,6})(?:[-_/]|$)", re.IGNORECASE
)
# Commit trailers: "Fixes #123", "Closes #123", "Refs #123", or a bare "#123".
_MSG_ISSUE_RE = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|ref[s]?)?\s*#(\d{1,6})", re.IGNORECASE
)


def _current_issue() -> str | None:
    """Return the GitHub issue number the work traces to (cached).

    Resolution order: explicit env (ISSUE_NUMBER / GITHUB_ISSUE) → the branch name
    (feature/123-x, issue-123, …) → the latest commit message trailer (#123 /
    Fixes #123). None when nothing matches — Lodge then omits the dimension.
    """
    global _issue_cache, _issue_read
    if _issue_read:
        return _issue_cache
    _issue_read = True
    num = ""
    for var in ("ISSUE_NUMBER", "GITHUB_ISSUE"):
        val = os.environ.get(var, "").strip().lstrip("#")
        if val.isdigit():
            num = val
            break
    if not num:
        branch = _current_branch() or ""
        m = _BRANCH_ISSUE_RE.search(branch)
        if m:
            num = m.group(1)
    if not num:
        msg = _git_out("log", "-1", "--pretty=%B")
        m = _MSG_ISSUE_RE.search(msg)
        if m:
            num = m.group(1)
    _issue_cache = num or None
    return _issue_cache


_phase_cache: str | None = None
_phase_read = False


def _current_phase() -> str | None:
    """Return the SDLC lifecycle phase for this run (ADR-0079), cached.

    Resolved in priority order:
    1. ``LODGE_SDLC_PHASE`` env var — lets a CI step or ad-hoc run declare the
       phase without writing a file (e.g. ``LODGE_SDLC_PHASE=ci`` in a workflow).
    2. ``.telemetry/.phase`` marker file — written by the gates (specification/
       architecture/test/refinement/completion/pre-commit/ci) via
       ``tools/_gate_core.py::declare_phase``.
    3. None — no phase declared; the event omits the field.

    We tag every spend event with it so Lodge can report cost/time per lifecycle
    phase. Best-effort: any failure degrades to None (the marker is never
    load-bearing).
    """
    import os

    global _phase_cache, _phase_read
    if _phase_read:
        return _phase_cache
    _phase_read = True
    env_phase = os.environ.get("LODGE_SDLC_PHASE", "").strip()
    if env_phase:
        _phase_cache = env_phase
        return _phase_cache
    try:
        marker = Path(".telemetry") / ".phase"
        _phase_cache = (
            (marker.read_text(encoding="utf-8").strip() or None)
            if marker.is_file()
            else None
        )
    except Exception:  # nosec B110  # noqa: BLE001 — marker is never load-bearing
        _phase_cache = None
    return _phase_cache


_root_context_cache: dict[str, tuple[str, str]] = {}


def _context_for_root(root: str) -> tuple[str, str]:  # noqa: CCR001
    """Return (slug, telemetry_url) for a git root, reading .env.lodge or .cornerstone."""
    if root in _root_context_cache:
        return _root_context_cache[root]
    rp = Path(root)
    slug = ""
    url = ""
    try:
        env_lodge = rp / ".telemetry" / ".env.lodge"
        if env_lodge.is_file():
            for line in env_lodge.read_text(encoding="utf-8").splitlines():
                if line.startswith("PROJECT_SLUG=") and not slug:
                    slug = line.split("=", 1)[1].strip()
                elif line.startswith("AGENTIC_TELEMETRY_URL=") and not url:
                    url = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    if not slug or not url:
        try:
            data = json.loads((rp / ".cornerstone").read_text(encoding="utf-8"))
            cc = data.get("cookiecutter_vars", {})
            if not slug:
                slug = cc.get("project_slug", "")
            if not url:
                url = cc.get("agentic_telemetry_url", "").rstrip("/")
        except Exception:  # nosec B110  # noqa: BLE001
            pass
    if not slug:
        slug = rp.name
    result = (slug, url)
    _root_context_cache[root] = result
    return result


def _resolve_governed_ancestor(path: str) -> tuple[str, str] | None:
    """Walk up from *path* to the nearest Lodge-configured directory.

    Returns (slug, url) or None. Checks every ancestor (not just git roots) so
    a session started in a subdirectory of a governed repo is attributed to it
    (ADR-0061 — this was the 47%-of-sessions silent-drop bug).
    """
    try:
        p = Path(path)
        if p.is_file():
            p = p.parent
        while True:
            slug, url = _context_for_root(str(p))
            if url:
                return (slug, url)
            parent = p.parent
            if parent == p:
                return None
            p = parent
    except OSError:
        return None


def _infer_context_from_transcript(transcript_path: str) -> tuple[str, str] | None:  # noqa: CCR001
    """Return (slug, url) for the governed project with the most file activity.

    Only Lodge-configured git roots (those that resolve a telemetry URL) are
    counted — activity in ungoverned repos can no longer shadow a governed
    project (ADR-0061). Returns None if no governed project was touched.
    """
    from collections import Counter

    counts: Counter[str] = Counter()
    root_map: dict[str, tuple[str, str]] = {}
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                content = entry.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_use":
                        continue
                    if item.get("name") not in ("Read", "Edit", "Write"):
                        continue
                    fp = item.get("input", {}).get("file_path", "")
                    if not fp:
                        continue
                    root = _find_git_root(fp)
                    if not root:
                        continue
                    slug, url = _context_for_root(root)
                    if not url:
                        continue  # ungoverned root — never a candidate
                    counts[slug] += 1
                    root_map[slug] = (slug, url)
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    if not counts:
        return None
    top_slug = counts.most_common(1)[0][0]
    return root_map[top_slug]


def _resolve_session_context(
    transcript_path: str, cwd: str | None
) -> tuple[str, str] | None:
    """Resolve (slug, url): env override → cwd walk-up → governed inference."""

    env_slug = os.environ.get("PROJECT_SLUG", "").strip()
    env_url = os.environ.get("AGENTIC_TELEMETRY_URL", "").strip().rstrip("/")
    if env_slug and env_url:
        return (env_slug, env_url)
    if cwd:
        resolved = _resolve_governed_ancestor(cwd)
        if resolved:
            return resolved
    return _infer_context_from_transcript(transcript_path)


# ---------------------------------------------------------------------------
# Skill-name normalization — resolve abbreviated/aliased names to canonical.
# Carried over from the schematics starter so a skill invoked by a short alias
# (sparc -> sparc-methodology, gitops -> gitops-expert) folds into one bucket.
# ---------------------------------------------------------------------------
_SKILL_NAME_COMPOUND_SUFFIXES = (
    "-expert", "-methodology", "-writer", "-manager",
    "-builder", "-creator", "-tester", "-validator",
)

_skill_alias_map_cache: dict[str, str] | None = None


def _build_skill_alias_map() -> dict[str, str]:
    """Scan .agents/skills/**/ and return alias → canonical name mappings.

    Two heuristics applied per SKILL.md:
    1. dir_leaf ≠ canonical → dir_leaf is an alias (sparc → sparc-methodology).
    2. canonical ends with a compound suffix → stripped form is an alias
       (gitops-expert → gitops).
    """
    name_map: dict[str, str] = {}
    skills_dir = Path.cwd() / ".agents" / "skills"
    if not skills_dir.exists():
        return name_map
    for skill_md in skills_dir.rglob("SKILL.md"):
        try:
            content = skill_md.read_text(encoding="utf-8")
            canonical = ""
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    for line in content[3:end].splitlines():
                        if line.startswith("name:"):
                            canonical = line.split(":", 1)[1].strip().strip("\"'")
                            break
            if not canonical:
                continue
            dir_name = skill_md.parent.name
            if dir_name != canonical:
                name_map.setdefault(dir_name, canonical)
            for suffix in _SKILL_NAME_COMPOUND_SUFFIXES:
                if canonical.endswith(suffix):
                    name_map.setdefault(canonical[: -len(suffix)], canonical)
        except Exception:  # nosec B110  # noqa: BLE001
            pass
    return name_map


def _normalize_skill_name(raw: str) -> str:
    """Resolve abbreviated or aliased skill names to their canonical form."""
    global _skill_alias_map_cache
    if _skill_alias_map_cache is None:
        _skill_alias_map_cache = _build_skill_alias_map()
    return _skill_alias_map_cache.get(raw, raw)


def _skill_from_content(content: object) -> str | None:
    """Return the canonical skill name if the content has a Skill tool_use."""
    if not isinstance(content, list):
        return None
    for item in content:
        if (
            isinstance(item, dict)
            and item.get("type") == "tool_use"
            and item.get("name") == "Skill"
        ):
            raw = item.get("input", {}).get("skill", "unknown-skill")
            return _normalize_skill_name(raw)
    return None


def _accum_msg(
    msg: dict,
    current_skill: str,
    buckets: dict[str, dict[str, int]],
    parents: dict[str, str | None],
) -> str:
    """Accumulate token usage from one transcript message; return active skill."""
    skill = _skill_from_content(msg.get("content", []))
    if skill:
        if skill not in parents:
            # first time we see this skill — record who spawned it
            parent = current_skill if current_skill != "claude-code-session" else None
            parents[skill] = parent
        current_skill = skill
    if current_skill not in buckets:
        buckets[current_skill] = {"in": 0, "out": 0, "cache_create": 0, "cache_read": 0}
    usage = msg.get("usage", {})
    b = buckets[current_skill]
    b["in"] += usage.get("input_tokens", 0)
    b["out"] += usage.get("output_tokens", 0)
    b["cache_create"] += usage.get("cache_creation_input_tokens", 0)
    b["cache_read"] += usage.get("cache_read_input_tokens", 0)
    return current_skill


def _parse_transcript_by_skill(
    path: str,
) -> tuple[str, dict[str, dict[str, int]], dict[str, str | None]]:
    """Return (model, {skill_name: tokens}, {skill_name: parent_skill_name})."""
    model = "unknown"
    current_skill = "claude-code-session"
    buckets: dict[str, dict[str, int]] = {}
    parents: dict[str, str | None] = {}

    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message", {})
                if not msg:
                    continue
                if model == "unknown" and msg.get("model"):
                    model = msg["model"]
                current_skill = _accum_msg(msg, current_skill, buckets, parents)
    except Exception:  # nosec B110  # noqa: BLE001
        pass

    return model, buckets, parents


# ---------------------------------------------------------------------------
# Subagent (Task) attribution — ADR-0074
#
# A subagent spawned via the Task/Agent tool runs as its OWN transcript at
#   <project>/<parent_session_id>/subagents/agent-<agentId>.jsonl
# Its token usage is not in the parent transcript (the Task tool_result is an
# async launch ack). _find_pending_transcripts already discovers these files;
# without this remap they land under the "claude-code-session" wrapper, which
# ADR-0045 excludes from rankings — so cornerstone-agents are invisible. Here
# we relabel a subagent transcript to the agent name resolved from the parent's
# Task tool_use, with a call-graph edge to its caller.
# ---------------------------------------------------------------------------

_SUBAGENT_DIR = "subagents"
_SUBAGENT_FILE_PREFIX = "agent-"
_WRAPPER_SKILL = "claude-code-session"


def _is_subagent_transcript(transcript_path: str) -> bool:
    """True for a …/<sid>/subagents/agent-<id>.jsonl subagent transcript."""
    p = Path(transcript_path)
    return p.parent.name == _SUBAGENT_DIR and p.name.startswith(_SUBAGENT_FILE_PREFIX)


def _parent_transcript_of(transcript_path: str) -> Path:
    """Map a subagent transcript to its parent session transcript.

    <project>/<sid>/subagents/agent-<id>.jsonl  ->  <project>/<sid>.jsonl
    """
    p = Path(transcript_path)
    sid_dir = p.parent.parent
    return sid_dir.parent / f"{sid_dir.name}.jsonl"


def _agent_id_of(transcript_path: str) -> str:
    return Path(transcript_path).stem[len(_SUBAGENT_FILE_PREFIX) :]


def _tool_result_id(content: object) -> str | None:
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                return item.get("tool_use_id")
    return None


def _scan_parent_entry(
    entry: dict,
    task_type: dict[str, str],
    task_caller: dict[str, str],
    current_skill: str,
) -> str:
    """Record any Task/Agent tool_use in *entry* (id -> subagent_type / caller)
    and return the skill active after this entry."""
    content = (entry.get("message") or {}).get("content")
    sk = _skill_from_content(content)
    if sk:
        current_skill = sk
    if isinstance(content, list):
        for item in content:
            if (
                isinstance(item, dict)
                and item.get("type") == "tool_use"
                and item.get("name") in ("Task", "Agent")
                and item.get("id")
            ):
                raw_type = (item.get("input") or {}).get(
                    "subagent_type"
                ) or "unknown-agent"
                task_type[item["id"]] = _normalize_skill_name(raw_type)
                task_caller[item["id"]] = current_skill
    return current_skill


def _iter_transcript_entries(path: str):
    """Yield parsed JSON entries from a transcript, skipping blank/invalid lines."""
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _resolve_subagent_identity(
    parent_path: str, agent_id: str
) -> tuple[str, str | None, str | None] | None:
    """Return (skill_name, resolved_model, parent_skill) for *agent_id* by
    scanning the parent transcript for the Task/Agent tool_use whose async
    result carries this agentId. None when it cannot be resolved."""
    task_type: dict[str, str] = {}  # tool_use_id -> subagent_type
    task_caller: dict[str, str] = {}  # tool_use_id -> enclosing skill at spawn
    current_skill = _WRAPPER_SKILL
    for entry in _iter_transcript_entries(parent_path):
        current_skill = _scan_parent_entry(entry, task_type, task_caller, current_skill)
        tur = entry.get("toolUseResult")
        if isinstance(tur, dict) and tur.get("agentId") == agent_id:
            tuid = _tool_result_id((entry.get("message") or {}).get("content"))
            if tuid in task_type:
                return (
                    task_type[tuid],
                    tur.get("resolvedModel"),
                    task_caller.get(tuid),
                )
    return None


def _apply_subagent_attribution(
    model: str,
    buckets: dict[str, dict[str, int]],
    parents: dict[str, str | None],
    advisor_counts: dict[str, int],
    identity: tuple[str, str | None, str | None],
) -> tuple[str, dict[str, dict[str, int]], dict[str, str | None], dict[str, int]]:
    """Relabel the wrapper bucket/advisor counts of a subagent transcript to the
    resolved agent name, set its caller edge, and prefer the resolved model."""
    skill_name, resolved_model, parent_skill = identity
    if skill_name != _WRAPPER_SKILL and _WRAPPER_SKILL in buckets:
        dst = buckets.setdefault(skill_name, {f: 0 for f in _TOKEN_FIELDS})
        for field in _TOKEN_FIELDS:
            dst[field] += buckets[_WRAPPER_SKILL].get(field, 0)
        del buckets[_WRAPPER_SKILL]
        parents.pop(_WRAPPER_SKILL, None)
    if skill_name != _WRAPPER_SKILL and _WRAPPER_SKILL in advisor_counts:
        advisor_counts[skill_name] = advisor_counts.get(
            skill_name, 0
        ) + advisor_counts.pop(_WRAPPER_SKILL)
    # A top-level spawn records the session wrapper as caller so the call graph
    # still has an edge; a spawn from within a skill records that skill.
    parents[skill_name] = parent_skill or _WRAPPER_SKILL
    return (resolved_model or model), buckets, parents, advisor_counts


def _subagent_remap(
    transcript_path: str,
    model: str,
    buckets: dict[str, dict[str, int]],
    parents: dict[str, str | None],
    advisor_counts: dict[str, int],
) -> tuple[str, dict, dict, dict, str]:
    """For a subagent transcript, relabel its buckets to the resolved agent and
    return the parent transcript path for context resolution. A non-subagent
    transcript passes through unchanged. Returns (model, buckets, parents,
    advisor_counts, context_path)."""
    if not _is_subagent_transcript(transcript_path):
        return model, buckets, parents, advisor_counts, transcript_path
    parent_path = _parent_transcript_of(transcript_path)
    identity = _resolve_subagent_identity(
        str(parent_path), _agent_id_of(transcript_path)
    )
    if identity is not None:
        model, buckets, parents, advisor_counts = _apply_subagent_attribution(
            model, buckets, parents, advisor_counts, identity
        )
    context_path = str(parent_path) if parent_path.exists() else transcript_path
    return model, buckets, parents, advisor_counts, context_path


def _count_advisor_calls_by_skill(path: str) -> dict[str, int]:  # noqa: CCR001
    """Return {skill_name: call_count} for advisor tool_use entries in the transcript."""
    current_skill = "claude-code-session"
    counts: dict[str, int] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message", {})
                if not msg:
                    continue
                content = msg.get("content", [])
                skill = _skill_from_content(content)
                if skill:
                    current_skill = skill
                if isinstance(content, list):
                    for item in content:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "tool_use"
                            and item.get("name") == "advisor"
                        ):
                            counts[current_skill] = counts.get(current_skill, 0) + 1
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    return counts


# ---------------------------------------------------------------------------
# Registry: per-transcript done flag + delta watermark (ADR-0061)
# ---------------------------------------------------------------------------

_SKIP_RECENT_SECS_DEFAULT = 5 * 60  # 5 min

_TOKEN_FIELDS = ("in", "out", "cache_create", "cache_read")


def _config_path() -> Path:
    return Path.home() / ".cornerstone" / "config.json"


def _registry_path() -> Path:
    """Resolved at call time so tests that repoint HOME never touch the real file."""
    return Path.home() / ".cornerstone" / "processed_transcripts.json"


def _get_skip_recent_secs() -> int:
    """Return inactivity threshold in seconds; configurable from Lodge via config.json.

    Priority: ~/.cornerstone/config.json → CORNERSTONE_CATCHUP_SKIP_SECS env var → 300 s.
    Lodge writes {"catchup_skip_recent_secs": N} to update this centrally.
    """

    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        val = data.get("catchup_skip_recent_secs")
        if isinstance(val, int) and val > 0:
            return val
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    try:
        val = int(os.environ.get("CORNERSTONE_CATCHUP_SKIP_SECS", "0"))
        if val > 0:
            return val
    except (ValueError, TypeError):
        pass
    return _SKIP_RECENT_SECS_DEFAULT


def _normalize_entry(value: object) -> dict:
    """Upgrade a registry value to the ADR-0061 dict form.

    Legacy `true` means "fully processed under pre-delta semantics"; its
    watermark is unknown, so it is kept done and never re-sent (re-sending
    would re-inflate sessions that were already over-counted).
    """
    if isinstance(value, dict):
        return value
    if value is True:
        return {"done": True, "legacy": True}
    return {"done": False}


def _load_registry() -> dict[str, dict]:
    path = _registry_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return {k: _normalize_entry(v) for k, v in raw.items()}
        except Exception:  # nosec B110  # noqa: BLE001
            # A corrupt registry silently read as {} would reset every
            # watermark (mass re-send). Quarantine the evidence instead.
            try:
                path.replace(path.parent / (path.name + ".corrupt"))
            except OSError:
                pass
    return {}


class _registry_lock:  # noqa: N801
    """Best-effort cross-process flock guarding the read-modify-write."""

    def __enter__(self):
        self._fh = None
        try:
            import fcntl

            lock_path = _registry_path().parent / ".processed_transcripts.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(lock_path, "w")  # noqa: SIM115
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except Exception:  # nosec B110  # noqa: BLE001
            pass  # no fcntl / lock failure — fall back to lock-free best effort
        return self

    def __exit__(self, *exc: object) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass


def _save_registry_entry(transcript_path: str, entry: dict) -> None:
    """Merge one entry into the registry with an atomic replace.

    Holds a cross-process flock around the read-modify-write and writes to a
    per-process temp file: concurrent Stop hooks can neither publish a
    half-written registry nor clobber each other's entries (ADR-0061 review
    findings #2/#8).
    """
    import uuid

    try:
        with _registry_lock():
            registry = _load_registry()
            registry[transcript_path] = entry
            path = _registry_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.parent / f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            try:
                tmp.write_text(
                    json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
                )
                tmp.replace(path)
            except Exception:  # noqa: BLE001
                tmp.unlink(missing_ok=True)  # don't orphan tmp files (review R2)
                raise
    except Exception:  # nosec B110  # noqa: BLE001
        pass


def _find_pending_transcripts(registry: dict[str, dict]) -> list[Path]:
    """Return .jsonl files not marked done and older than _get_skip_recent_secs()."""
    import time

    transcripts_dir = Path.home() / ".claude" / "projects"
    if not transcripts_dir.exists():
        return []
    now = time.time()
    skip_secs = _get_skip_recent_secs()
    pending = []
    for p in sorted(transcripts_dir.rglob("*.jsonl")):
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_size == 0:
            continue
        if now - st.st_mtime < skip_secs:
            continue  # session may still be active
        if registry.get(str(p), {}).get("done"):
            continue
        pending.append(p)
    return pending


def _delta_buckets(
    buckets: dict[str, dict[str, int]], watermark: dict
) -> dict[str, dict[str, int]]:
    """Cumulative buckets minus the watermark, clamped at zero, zero-rows dropped."""
    deltas: dict[str, dict[str, int]] = {}
    for skill, tok in buckets.items():
        wm = watermark.get(skill, {})
        delta = {f: max(0, tok.get(f, 0) - wm.get(f, 0)) for f in _TOKEN_FIELDS}
        if any(delta.values()):
            deltas[skill] = delta
    return deltas


def _send_skill_deltas(
    deltas: dict[str, dict[str, int]],
    parents: dict[str, str | None],
    watermark: dict,
    buckets: dict[str, dict[str, int]],
    *,
    model: str,
    project_slug: str,
    username: str,
    session_id: str,
) -> bool:
    """Send one skill.invoked event per delta bucket; advance the watermark for
    each event that reached a final state. Returns True if all did."""
    provider = get_provider(model)
    all_final = True
    for skill_name, tok in deltas.items():
        cost = estimate_cost(
            model, tok["in"], tok["out"], tok["cache_read"], tok["cache_create"]
        )
        payload = SkillInvokedPayload(
            skill_name=skill_name,
            skill_path="",
            model=model,
            provider=provider,
            parent_skill_name=parents.get(skill_name),
            tokens_input=tok["in"],
            tokens_output=tok["out"],
            tokens_cache_write=tok["cache_create"] or None,
            tokens_cache_read=tok["cache_read"] or None,
            estimated_cost_usd=cost,
            client="claude-code",
            session_id=session_id,
            report_kind="delta",
        )
        final = send_event_sync(
            make_event(
                "skill.invoked", project_slug, username, payload,
                branch=_current_branch(),
                phase=_current_phase(),
                commit_sha=_current_commit(),
                issue_number=_current_issue(),
            )
        )
        if final:
            watermark[skill_name] = dict(buckets[skill_name])
        else:
            all_final = False
    return all_final


def _send_advisor_deltas(
    advisor_counts: dict[str, int],
    advisor_watermark: dict,
    *,
    project_slug: str,
    username: str,
    session_id: str,
) -> bool:
    """Send tool.executed deltas for advisor calls; advance per-skill counts."""
    all_final = True
    for skill_name, total in advisor_counts.items():
        delta = total - advisor_watermark.get(skill_name, 0)
        if delta <= 0:
            continue
        tool_payload = ToolExecutedPayload(
            tool_name="advisor",
            tool_path="",
            duration_ms=0,
            exit_code=0,
            invocation_count=delta,
            skill_name=skill_name,
            session_id=session_id,
        )
        final = send_event_sync(
            make_event(
                "tool.executed", project_slug, username, tool_payload,
                branch=_current_branch(),
                phase=_current_phase(),
                commit_sha=_current_commit(),
                issue_number=_current_issue(),
            )
        )
        if final:
            advisor_watermark[skill_name] = total
        else:
            all_final = False
    return all_final


def _send_all_deltas(
    deltas: dict[str, dict[str, int]],
    parents: dict[str, str | None],
    watermark: dict,
    buckets: dict[str, dict[str, int]],
    advisor_counts: dict[str, int],
    advisor_watermark: dict,
    *,
    model: str,
    project_slug: str,
    session_id: str,
) -> bool:
    """Send skill + advisor deltas; True when every event reached a final state."""
    username = get_github_username()
    try:
        skills_final = _send_skill_deltas(
            deltas,
            parents,
            watermark,
            buckets,
            model=model,
            project_slug=project_slug,
            username=username,
            session_id=session_id,
        )
        advisor_final = _send_advisor_deltas(
            advisor_counts,
            advisor_watermark,
            project_slug=project_slug,
            username=username,
            session_id=session_id,
        )
    except Exception:  # nosec B110  # noqa: BLE001
        return False
    return skills_final and advisor_final


_env_url_owned = False


def _skip_done_entry(entry: dict, finalize: bool) -> bool:
    """True when a done entry must stay closed.

    Legacy entries have no watermark — re-sending would re-inflate
    already-over-counted history, so they stay done forever. A watermarked
    entry seen again in HOOK mode means the session resumed after catchup
    finalized it (idle > skip window): reopen it — the watermark makes
    reprocessing safe (review finding #1).
    """
    if not entry.get("done"):
        return False
    return finalize or "watermark" not in entry


def _export_telemetry_url(url: str) -> None:
    """Point the client at *url*, overwriting only values this process set
    itself: two governed repos pointing at different Lodge instances must not
    cross-post within one catchup run (review finding #3), while a
    user-provided env override is never clobbered."""

    global _env_url_owned  # noqa: PLW0603
    if url and (not os.environ.get("AGENTIC_TELEMETRY_URL") or _env_url_owned):
        os.environ["AGENTIC_TELEMETRY_URL"] = url
        _env_url_owned = True


def process_transcript(
    transcript_path: str, cwd: str | None = None, finalize: bool = True
) -> int:
    """Report the unreported delta of one transcript to Lodge.

    finalize=False (hook mode): sends the delta and advances the watermark but
    never marks the transcript done — the session may continue.
    finalize=True (catchup/CLI): additionally marks it done when everything
    reached a final state.

    Returns 0 on success/skip, 2 on transient failure (retry later).
    """
    registry = _load_registry()
    entry = registry.get(transcript_path, {"done": False})
    if _skip_done_entry(entry, finalize):
        return 0

    model, buckets, parents = _parse_transcript_by_skill(transcript_path)
    if not buckets:
        if finalize:
            # Empty watermark (vs legacy no-watermark): nothing was ever
            # accounted, so a resumed session reopens safely (review R1).
            _save_registry_entry(transcript_path, {"done": True, "watermark": {}})
        return 0  # nothing to report

    advisor_counts = _count_advisor_calls_by_skill(transcript_path)

    # ADR-0074: a subagent transcript is relabeled to its agent name (resolved
    # from the parent's Task tool_use) and attributed to the parent's project.
    model, buckets, parents, advisor_counts, context_path = _subagent_remap(
        transcript_path, model, buckets, parents, advisor_counts
    )

    context = _resolve_session_context(context_path, cwd)
    if context is None:
        # Not attributable to any governed project. Catchup finalizes it so it
        # is not re-scanned forever; hook mode leaves it untouched (later turns
        # may touch a governed project).
        if finalize:
            _save_registry_entry(transcript_path, {"done": True, "watermark": {}})
        return 0
    project_slug, url = context
    _export_telemetry_url(url)

    watermark = dict(entry.get("watermark", {}))
    advisor_watermark = dict(entry.get("advisor", {}))
    session_id = Path(transcript_path).stem

    deltas = _delta_buckets(buckets, watermark)

    all_final = _send_all_deltas(
        deltas,
        parents,
        watermark,
        buckets,
        advisor_counts,
        advisor_watermark,
        model=model,
        project_slug=project_slug,
        session_id=session_id,
    )
    _save_registry_entry(
        transcript_path,
        {
            "done": bool(finalize and all_final),
            "watermark": watermark,
            "advisor": advisor_watermark,
        },
    )
    return 0 if all_final else 2


def _run_catchup(verbose: bool = True) -> int:  # noqa: CCR001
    """Find and process all pending transcripts; finalize the successful ones."""
    registry = _load_registry()
    pending = _find_pending_transcripts(registry)
    if not pending:
        if verbose:
            print("[catchup] no pending transcripts")
        return 0

    processed = 0
    failed = 0
    for p in pending:
        ret = process_transcript(str(p), finalize=True)
        if ret == 0:
            processed += 1
            if verbose:
                print(f"[catchup] reported: {p.name}")
        else:
            failed += 1
            if verbose:
                print(f"[catchup] transient failure: {p.name}", file=sys.stderr)

    if verbose:
        print(f"[catchup] done — {processed} reported, {failed} failed")
    return 2 if failed else 0


def main() -> int:
    # Durability catchup (ADR-0058, #56): flush any Stop-hook events a prior run
    # persisted while Lodge was unavailable. Shares the catchup invocation point;
    # storage is separate (~/.lodge/pending_events vs the ~/.cornerstone transcript
    # registry). Never raises.
    flush_pending_events()

    import argparse

    parser = argparse.ArgumentParser(
        description="Stop hook / catchup reporter", add_help=False
    )
    parser.add_argument("--transcript", metavar="PATH")
    parser.add_argument("--cwd", metavar="DIR")
    parser.add_argument("--catchup", action="store_true")
    args, _ = parser.parse_known_args()

    if args.transcript:
        return process_transcript(args.transcript, cwd=args.cwd, finalize=True)
    if args.catchup:
        return _run_catchup()

    # Hook mode: read transcript path (and session cwd) from stdin JSON.
    try:
        hook_data = json.loads(sys.stdin.read())
    except Exception:  # nosec B110  # noqa: BLE001
        return 0

    transcript_path = hook_data.get("transcript_path", "")
    if not transcript_path:
        return 0


    cwd = hook_data.get("cwd") or os.getcwd()
    process_transcript(transcript_path, cwd=cwd, finalize=False)
    # A Stop hook exiting non-zero blocks Claude Code from stopping; telemetry
    # must never do that. Unsent deltas stay in the watermark for the catchup.
    return 0


if __name__ == "__main__":
    sys.exit(main())
