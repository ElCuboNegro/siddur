#!/usr/bin/env python3
"""KDB-first Gate — enforce corpus consultation before deep exploration (ADR-0126).

Two hook entry points:

  --mark   PostToolUse on ``mcp__keystone__.*``: records that this session
           consulted the KDB. From that point on the gate is silent.

  --check  PreToolUse on ``Grep|Glob|Task``: counts exploration calls; once
           the threshold is crossed without a prior KDB consultation, nudges
           (soft) or blocks (hard) the call.

Modes (env ``KDB_FIRST_MODE``):
  off   gate disabled.
  soft  (default) deny exactly ONCE per session with guidance; every
        subsequent call passes. A one-time speed bump, not a wall — the
        agent can satisfy it by calling kdb_search, or simply retry when
        the corpus genuinely does not apply.
  hard  deny every exploration call until the session consults the KDB.
        Intended for archaeology repos where skipping the corpus is the
        single most expensive mistake (re-exploration: 100-500k tokens).

Tunables:
  KDB_FIRST_THRESHOLD  exploration calls tolerated before firing (default 3)
  KDB_FIRST_STATE_DIR  session-state directory (default /tmp/kdb-first-<uid>)

Design constraint (ADR-0124 lesson): a gate that fires on trivial actions
trains reflexive bypassing. Hence the threshold, the once-only soft mode,
and the fail-safe: ANY internal error exits 0 (allow). The gate must never
break a session.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

EXPLORATION_TOOLS = {"Grep", "Glob", "Task"}
# Task subagent types that are NOT exploration (implementation/review work).
NON_EXPLORATION_SUBAGENTS = {
    "tdd-developer",
    "code-reviewer",
    "qa-validator",
    "adr-writer",
    "technical-writer",
    "statusline-setup",
}

DENY_REASON_SOFT = (
    "KDB-first (ADR-0126): antes de explorar el codebase, consulta el corpus — "
    "kdb_search / kdb_get_project_context (Keystone MCP) suelen responder en 2-5k tokens "
    "lo que la exploración paga en 100-500k. Si el corpus no aplica a esta tarea, "
    "reintenta la llamada: este aviso es una sola vez por sesión."
)
DENY_REASON_HARD = (
    "KDB-first (ADR-0126, modo hard): este repositorio exige consultar Keystone "
    "(kdb_search / kdb_get_project_context) antes de explorar el código. "
    "Haz al menos una consulta al KDB y la exploración quedará desbloqueada. "
    "Para relajar el modo: export KDB_FIRST_MODE=soft."
)


def state_dir() -> Path:
    configured = os.environ.get("KDB_FIRST_STATE_DIR")
    if configured:
        d = Path(configured)
    else:
        d = Path(tempfile.gettempdir()) / f"kdb-first-{os.getuid()}"
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


def _session_file(session_id: str, suffix: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:128] or "unknown"
    return state_dir() / f"{safe}.{suffix}"


def mark(payload: dict) -> int:
    """Record a KDB consultation for this session (PostToolUse)."""
    session_id = str(payload.get("session_id", "unknown"))
    _session_file(session_id, "consulted").touch()
    return 0


def _is_exploration(payload: dict) -> bool:
    tool = payload.get("tool_name", "")
    if tool not in EXPLORATION_TOOLS:
        return False
    if tool == "Task":
        subagent = str(payload.get("tool_input", {}).get("subagent_type", ""))
        if subagent in NON_EXPLORATION_SUBAGENTS:
            return False
    return True


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def check(payload: dict) -> int:
    """Gate an exploration call (PreToolUse). Returns process exit code."""
    mode = os.environ.get("KDB_FIRST_MODE", "soft").strip().lower()
    if mode not in ("soft", "hard"):
        return 0  # off / unknown value → disabled
    if not _is_exploration(payload):
        return 0

    session_id = str(payload.get("session_id", "unknown"))
    if _session_file(session_id, "consulted").exists():
        return 0

    count_file = _session_file(session_id, "count")
    try:
        count = int(count_file.read_text() or "0")
    except (OSError, ValueError):
        count = 0
    count += 1
    count_file.write_text(str(count))

    try:
        threshold = int(os.environ.get("KDB_FIRST_THRESHOLD", "3"))
    except ValueError:
        threshold = 3
    if count < threshold:
        return 0

    if mode == "hard":
        _deny(DENY_REASON_HARD)
        return 0

    warned_file = _session_file(session_id, "warned")
    if warned_file.exists():
        return 0
    warned_file.touch()
    _deny(DENY_REASON_SOFT)
    return 0


def main(argv: list[str]) -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    if "--mark" in argv:
        return mark(payload)
    if "--check" in argv:
        return check(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        # Fail-safe: the gate must never break a session.
        sys.exit(0)
