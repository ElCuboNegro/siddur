#!/usr/bin/env python3
# ADR: 0002
"""tools/sparc_gate.py — SPARC complexity gate for Claude Code / Gemini PreToolUse[Edit|Write].

Blocks edits when EITHER condition is true and no spec exists in docs/specs/:
  - The current branch touches ≥ SPARC_THRESHOLD source files (default: 3)
  - The change being written is ≥ SPARC_CHANGE_LINES lines (default: 50)

Allow conditions (any one is sufficient):
  (a) docs/specs/ contains at least one .md file
  (b) A typed bypass token is present in the hook payload: [skip-sparc]
  (c) The file being edited is not a source file (docs, config, tests, infra)

Typed bypass vocabulary:
  [skip-sparc]  -- skip SPARC for this operation (trivial change / hotfix)

Every bypass is logged to .sparc-gate-bypasses.log.

Configuration (env vars):
  SPARC_THRESHOLD     -- minimum file count that triggers the gate (default: 3)
  SPARC_CHANGE_LINES  -- minimum lines in a single change that triggers the gate (default: 50)
  SPARC_SPECS_PATH    -- directory scanned for specs (default: docs/specs)
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404
import sys
from datetime import datetime, timezone
from pathlib import Path

# SDLC phase telemetry (ADR-0079): declare the phase of the edited path so the
# Stop-hook emitter can tag spend with it. Import is best-effort — telemetry is
# never load-bearing for the gate.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from _gate_core import declare_phase, phase_of
except Exception:  # pragma: no cover — telemetry must never break the gate  # noqa: BLE001

    def declare_phase(*_a, **_k) -> None:  # type: ignore[misc]
        return None

    def phase_of(_p: str) -> str:  # type: ignore[misc]
        return "exempt"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_THRESHOLD = int(os.environ.get("SPARC_THRESHOLD", "3"))
_CHANGE_LINES = int(os.environ.get("SPARC_CHANGE_LINES", "50"))
_SPECS_PATH = os.environ.get("SPARC_SPECS_PATH", "docs/specs")
_LOG_FILE = Path(".sparc-gate-bypasses.log")

_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".sh"}

_EXEMPT_PREFIXES = (
    "docs/",
    "tests/",
    ".telemetry/",
    ".agents/",
    ".claude/",
    ".gemini/",
    "migrations/",
    "cookiecutter.",
    "tools/",
)

_BYPASS_RE = re.compile(r"\[skip-sparc\]", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception:  # nosec B110
        return ""


def _parse_payload(raw: str) -> tuple[str, int]:
    """Return (file_path, change_line_count) from the hook JSON payload."""
    if not raw:
        return "", 0
    try:
        data = json.loads(raw)
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        change_text = tool_input.get("new_string") or tool_input.get("content") or ""
        return file_path, len(change_text.splitlines())
    except (json.JSONDecodeError, AttributeError, TypeError):
        return "", 0


def _is_source_file(file_path: str) -> bool:
    if not file_path:
        return False
    p = Path(file_path)
    if p.suffix not in _SOURCE_EXTENSIONS:
        return False
    normalized = file_path.replace("\\", "/")
    return not any(normalized.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


def _spec_exists() -> bool:
    specs_dir = Path(_SPECS_PATH)
    if not specs_dir.exists():
        return False
    return any(
        f.is_file() and f.suffix == ".md" and not f.name.startswith(".")
        for f in specs_dir.iterdir()
    )


def _branch_source_file_count(current_file: str) -> int:
    """Count unique source files in branch diff (vs remote main/master) + current file."""
    touched: set[str] = set()
    try:
        for base in ("origin/main", "origin/master", "HEAD~1"):
            result = subprocess.run(  # nosec B603, B607
                ["git", "diff", "--name-only", f"{base}...HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for f in result.stdout.splitlines():
                    if _is_source_file(f):
                        touched.add(f)
                break
    except Exception:  # nosec B110
        pass
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for f in result.stdout.splitlines():
            if _is_source_file(f):
                touched.add(f)
    except Exception:  # nosec B110
        pass
    if _is_source_file(current_file):
        touched.add(current_file)
    return len(touched)


def _log_bypass(file_path: str) -> None:
    try:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = f"{ts} | type=skip-sparc | file={file_path}\n"
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception:  # nosec B110
        pass


# ---------------------------------------------------------------------------
# Decision builders (compatible with Claude Code and Gemini CLI)
# ---------------------------------------------------------------------------


def _allow() -> dict:
    return {
        "decision": "allow",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
    }


def _deny(*, file_count: int | None = None, change_lines: int | None = None) -> dict:
    if file_count is not None:
        trigger = f"toca {file_count} archivo(s) fuente (≥{_THRESHOLD} umbral de complejidad)"
    else:
        trigger = f"el cambio tiene {change_lines} líneas (≥{_CHANGE_LINES} umbral de tamaño)"
    reason = (
        f"SPARC GATE BLOCKED\n\n"
        f"Esta operación {trigger}, "
        f"pero no existe ningún spec en {_SPECS_PATH}/.\n\n"
        f"Completa las fases S y P de SPARC primero:\n"
        f"  1. Escribe {_SPECS_PATH}/<feature>.md con:\n"
        f"     ## Specification  — qué hace el sistema, ACs, edge cases\n"
        f"     ## Pseudocode     — flujo de control en lenguaje natural\n"
        f"  2. Retoma la implementación\n\n"
        f"Bypass (para cambios que el tech-lead considera triviales):\n"
        f"  Incluye [skip-sparc] en tu siguiente mensaje.\n"
        f"  El bypass queda registrado en .sparc-gate-bypasses.log\n"
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

    file_path, change_lines = _parse_payload(raw)

    # SDLC phase telemetry (ADR-0079): declare the phase of the path being edited
    # (specification/architecture/test/refinement/completion) for the emitter.
    if file_path:
        declare_phase(phase_of(file_path))

    # (b) Typed bypass
    if _BYPASS_RE.search(raw):
        _log_bypass(file_path)
        return _allow()

    # (c) Not a source file we govern
    if not _is_source_file(file_path):
        return _allow()

    # (a) Spec already exists
    if _spec_exists():
        return _allow()

    # Condition 1: branch touches ≥ THRESHOLD source files
    count = _branch_source_file_count(file_path)
    if count >= _THRESHOLD:
        return _deny(file_count=count)

    # Condition 2: single change is ≥ CHANGE_LINES lines
    if change_lines >= _CHANGE_LINES:
        return _deny(change_lines=change_lines)

    return _allow()


def main() -> int:
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
