#!/usr/bin/env python3
# ADR: 0038
"""tools/review_gate.py — Code-Reviewer gate for Claude Code / Gemini PreToolUse[Edit|Write].

Blocks edits to source files in src/ when no code-reviewer receipt exists for
the current session. A receipt is written by running:

    python tools/review_gate.py --register

which the code-reviewer SKILL.md instructs the agent to run as its final step.

Allow conditions (any one is sufficient):
  (a) A valid receipt exists in .review-gate/ (written this session)
  (b) A typed bypass token is present in the hook payload: [skip-review: trivial]
  (c) The file being edited is not a source file (tests, docs, config, infra)

Typed bypass vocabulary:
  [skip-review: trivial]   -- single-line fix, no logic change
  [skip-review: docs-only] -- documentation or comment change only

Every bypass is logged to .review-gate-bypasses.log.

Configuration (env vars):
  REVIEW_GATE_SRC_DIR  -- source directory watched for changes (default: src)
  REVIEW_RECEIPT_TTL   -- receipt validity in minutes (default: 120)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SRC_DIR = os.environ.get("REVIEW_GATE_SRC_DIR", "src")
_TTL_MINUTES = int(os.environ.get("REVIEW_RECEIPT_TTL", "120"))
_RECEIPT_DIR = Path(".review-gate")
_LOG_FILE = Path(".review-gate-bypasses.log")

_BYPASS_RE = re.compile(
    r"\[skip-review:\s*(trivial|docs-only)\]", re.IGNORECASE
)

_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".sh"}

_EXEMPT_PREFIXES = (
    "tests/",
    "test_",
    "docs/",
    ".agents/",
    ".claude/",
    ".gemini/",
    ".telemetry/",
    "migrations/",
    "cookiecutter.",
    "tools/",
    ".github/",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception:  # nosec B110
        return ""


def _parse_file_path(raw: str) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        return data.get("tool_input", {}).get("file_path", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return ""


def _is_guarded(file_path: str) -> bool:
    """Return True if the file is a source file under _SRC_DIR that we guard."""
    if not file_path:
        return False
    p = Path(file_path)
    if p.suffix not in _SOURCE_EXTENSIONS:
        return False
    normalized = file_path.replace("\\", "/")
    if any(normalized.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
        return False
    return normalized.startswith(_SRC_DIR + "/") or ("/" + _SRC_DIR + "/") in normalized


def _valid_receipt_exists() -> bool:
    """Return True if a receipt written within _TTL_MINUTES exists."""
    if not _RECEIPT_DIR.exists():
        return False
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=_TTL_MINUTES)
    for receipt in _RECEIPT_DIR.glob("code-reviewer-*.receipt"):
        try:
            content = receipt.read_text(encoding="utf-8").strip()
            ts = datetime.fromisoformat(content)
            if ts > cutoff:
                return True
        except Exception:  # nosec B110
            continue
    return False


def _write_receipt() -> None:
    """Write a timestamped receipt (called with --register)."""
    _RECEIPT_DIR.mkdir(exist_ok=True)
    ts = datetime.now(tz=timezone.utc)
    name = f"code-reviewer-{ts.strftime('%Y%m%dT%H%M%S')}.receipt"
    (_RECEIPT_DIR / name).write_text(ts.isoformat(), encoding="utf-8")
    print(f"[review-gate] Receipt written: .review-gate/{name}")


def _log_bypass(file_path: str, token: str) -> None:
    try:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = f"{ts} | bypass={token!r} | file={file_path}\n"
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception:  # nosec B110
        pass


# ---------------------------------------------------------------------------
# Decision builders
# ---------------------------------------------------------------------------


def _allow() -> dict:
    return {
        "decision": "allow",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
    }


def _deny(file_path: str) -> dict:
    reason = (
        f"CODE-REVIEWER GATE BLOCKED\n\n"
        f"Modificar '{file_path}' requiere que el skill code-reviewer\n"
        f"haya revisado el diff de esta sesión.\n\n"
        f"Pasos:\n"
        f"  1. Invoca el skill code-reviewer:\n"
        f"     Lee .agents/skills/software/quality/code-reviewer/SKILL.md\n"
        f"  2. Ejecuta la revisión sobre los cambios actuales\n"
        f"  3. Al finalizar la revisión, registra el receipt:\n"
        f"     python tools/review_gate.py --register\n"
        f"  4. Retoma la implementación\n\n"
        f"Bypass (solo para cambios triviales de 1 línea sin lógica):\n"
        f"  Incluye [skip-review: trivial] en tu siguiente mensaje.\n"
        f"  El bypass queda registrado en .review-gate-bypasses.log\n"
    )
    return {
        "decision": "deny",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(raw: str = "") -> dict:
    if not raw:
        raw = _read_stdin()

    file_path = _parse_file_path(raw)

    # Typed bypass
    m = _BYPASS_RE.search(raw)
    if m:
        _log_bypass(file_path, m.group(0))
        return _allow()

    # Not a guarded source file
    if not _is_guarded(file_path):
        return _allow()

    # Valid receipt exists
    if _valid_receipt_exists():
        return _allow()

    return _deny(file_path)


def main() -> int:
    if "--register" in sys.argv:
        _write_receipt()
        return 0

    arguments_env = os.environ.get("ARGUMENTS", "")
    gemini_mode = bool(arguments_env)
    raw = arguments_env or _read_stdin()
    result = run(raw)

    if gemini_mode:
        output = {k: v for k, v in result.items() if k in ("decision", "reason")}
    else:
        output = {k: v for k, v in result.items() if k == "hookSpecificOutput"}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
