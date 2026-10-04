#!/usr/bin/env python3
"""tools/session_start.py — SessionStart hook for Gemini CLI and Claude Code.

Reads AGENTS.md and the domain-specific context file (.agents/AGENTS.*.md)
and injects them as `additionalContext` so the agent performs mandatory
initialization without relying on unsupported `type: "agent"` hooks.

Output
------
JSON with `hookSpecificOutput.additionalContext` containing both files.
Gemini CLI injects this as the first turn in history.
Claude Code prepends it to the next user prompt.
"""

import json
import subprocess  # nosec B404
import sys
from pathlib import Path


def _context_file(cwd: Path) -> str:
    """Pick the right AGENTS context file based on modified file paths."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        paths = [
            line.split()[-1] for line in result.stdout.splitlines() if line.strip()
        ]
    except Exception:
        paths = []

    if any(p.startswith("cornerstone/") for p in paths):
        return ".agents/AGENTS.cli.md"
    if any(p.startswith("services/") for p in paths):
        return ".agents/AGENTS.server.md"
    return ".agents/AGENTS.archaeology.md"


def main() -> int:
    cwd = Path.cwd()
    agents_path = cwd / "AGENTS.md"
    if not agents_path.exists():
        print(json.dumps({}))
        return 0

    agents_content = agents_path.read_text(encoding="utf-8", errors="replace")

    ctx_name = _context_file(cwd)
    ctx_path = cwd / ctx_name
    ctx_content = (
        ctx_path.read_text(encoding="utf-8", errors="replace")
        if ctx_path.exists()
        else f"(context file {ctx_name} not found)"
    )

    additional = (
        "[MANDATORY INITIALIZATION — agent MUST read this before acting]\n\n"
        f"=== AGENTS.md (Supreme Mandate) ===\n{agents_content}\n\n"
        f"=== {ctx_name} ===\n{ctx_content}"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
