#!/usr/bin/env python3
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (cornerstone/data/starters/ + tools/) and propagate with
# `cornerstone update`.
# [skip-adr] governed by ADR-0137 (governance enforcement spec)
"""PreToolUse Bash guard (ADR-0137, AC-4): defense-in-depth.

Detects Bash commands that write directly to Python source files (a way to evade
the Edit/Write PreToolUse gates). Advisory only — exits 0 and prints a reminder;
the real barriers are the diff-based pre-commit and CI gates, which catch the
change regardless of how the file was written.
"""
from __future__ import annotations

import json
import re
import sys

_REDIRECT = re.compile(r"""(?:>>?|\btee\b)\s+["']?[\w./\-]+\.py\b""")
_PY_OPEN = re.compile(r"""open\(\s*["'][\w./\-]+\.py["']\s*,\s*["'][wa]""")


def is_source_write(command: str) -> bool:
    """Return True if the command appears to write to a .py source file."""
    if not command:
        return False
    return bool(_REDIRECT.search(command) or _PY_OPEN.search(command))


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return 0
    command = str(data.get("tool_input", {}).get("command", ""))
    if "[skip-" in command:
        return 0
    if is_source_write(command):
        sys.stderr.write(
            "[bash-write-guard] Direct write to a Python source file via Bash "
            "detected. The ADR/SPARC/BDD gates run on Edit/Write — prefer those. "
            "Either way, the commit/CI gates will check this change (ADR-0137).\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
