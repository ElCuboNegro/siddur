#!/usr/bin/env python3
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (schematics, per ADR-0159 Decision 1) and propagate with
# `cornerstone update`.
# ADR: 0159
"""tools/governance_gate.py — consolidated co-presence gate on _gate_core.

ADR-0159 Decision 3 + 9: a change touching governed source must, in the SAME
change-set, carry a feature (S), an ADR (A) and tests (R_red) — unless a
verified bypass applies. All classification, bypass parsing, range resolution
and git plumbing are delegated to the hardened `_gate_core`, so this gate
inherits the S1..S6 closures instead of re-opening them.

Usage:
    python tools/governance_gate.py --check           # CI: self-resolved range
    python tools/governance_gate.py --pre-commit       # staged change-set
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gate_core as core  # noqa: E402


def decide(
    changed_files: list[str], commit_message: str, branch: str, adr_exists
) -> tuple[bool, list[str]]:
    """Pure decision (no git) — testable and red-team-attackable.

    Returns (allowed, reasons). A governed-source change requires co-presence
    of S + A + R_red in the same change-set, unless a verified bypass applies.
    """
    phases = {core.phase_of(f) for f in changed_files}
    touches_impl = "R_green" in phases
    if not touches_impl:
        return True, ["no governed source in change-set"]

    bypass = core.parse_bypass(commit_message, branch, adr_exists)
    if bypass["allowed"]:
        return True, [f"bypass: {bypass['reason']}"]

    missing = [p for p in ("S", "A", "R_red") if p not in phases]
    if missing:
        names = {"S": "feature(.feature)", "A": "ADR", "R_red": "tests"}
        return False, [f"governed source without {names[p]} in the change-set" for p in missing]
    return True, ["co-presence satisfied: feature + ADR + tests present"]


def _run(staged: bool) -> int:
    cwd = Path.cwd()
    try:
        if staged:
            changed = core.git_changed(cwd, staged=True)
        else:
            base, head = core.resolve_range(cwd, os.environ.get("PROTECTED_BRANCH", "origin/main"))
            changed = core.git_changed(cwd, base=base, head=head)
    except core.GateError as e:
        # FAIL CLOSED (S6): a plumbing failure must not silently allow.
        print(f"[governance-gate] FAILED CLOSED — {e}", file=sys.stderr)
        return 1

    commit_message = os.environ.get("COMMIT_MESSAGE", "")
    branch = core._git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).strip()
    adr_exists = core.adr_cache_lookup(cwd).__contains__

    ok, reasons = decide(changed, commit_message, branch, adr_exists)
    tag = "PASS" if ok else "BLOCKED"
    print(
        f"[governance-gate] {tag}: " + "; ".join(reasons),
        file=sys.stderr if not ok else sys.stdout,
    )
    return 0 if ok else 1


def main() -> int:
    args = sys.argv[1:]
    if "--pre-commit" in args:
        return _run(staged=True)
    if "--check" in args:
        return _run(staged=False)
    print("Usage: governance_gate.py [--check | --pre-commit]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
