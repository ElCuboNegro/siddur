#!/usr/bin/env python3
"""tools/check_bdd_gate.py — BDD Gate for CI and pre-commit hooks.

Enforces the BDD-first pipeline (ADR-0095): any commit that adds or modifies
Python source files under src/ must have at least one pytest-bdd scenario
collected from the tests/features/ directory.

Usage
-----
CI:
    python tools/check_bdd_gate.py --ci

Pre-commit:
    python tools/check_bdd_gate.py --pre-commit

Bypass
------
Include ``[skip-bdd]`` in the commit message or staged diff to bypass.
Every bypass is logged to ``.bdd-gate-bypasses.log``.

Configuration
-------------
``BDD_FEATURES_DIR``  — directory scanned for .feature files (default: tests/features)
``BDD_SRC_DIR``       — source directory watched for changes (default: src)
"""

import subprocess  # nosec B404
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_FEATURES_DIR = os.environ.get("BDD_FEATURES_DIR", "tests/features")
_SRC_DIR = os.environ.get("BDD_SRC_DIR", "src")
_BYPASS_TOKEN = "[skip-bdd]"  # nosec B105
_LOG_FILE = Path(".bdd-gate-bypasses.log")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_bypass(token: str, context: str) -> None:
    branch = _current_branch()
    entry = (
        f"[{datetime.now(tz=timezone.utc).isoformat()}] "
        f"bypass={token!r} branch={branch!r} context={context!r}\n"
    )
    try:
        with _LOG_FILE.open("a") as fh:
            fh.write(entry)
    except OSError:
        pass


def _current_branch() -> str:
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _on_exempt_branch() -> bool:
    return _current_branch().startswith("hotfix/")


def _get_changed_src_files(base_sha: str = "", head_sha: str = "") -> list[str]:
    """Return Python source files changed under _SRC_DIR."""
    try:
        if base_sha and head_sha:
            cmd = ["git", "diff", "--name-only", "--diff-filter=ACM", base_sha, head_sha]
        else:
            cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
        result = subprocess.run(  # nosec B603, B607
            cmd, capture_output=True, text=True, timeout=10
        )
        files = result.stdout.splitlines()
    except Exception:
        return []
    return [
        f for f in files
        if f.startswith(_SRC_DIR + "/") and f.endswith(".py")
    ]


def _count_bdd_scenarios(features_dir: str) -> int:
    """Run pytest --collect-only and count collected scenarios."""
    features_path = Path(features_dir)
    if not features_path.exists():
        return 0
    try:
        result = subprocess.run(  # nosec B603, B607
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "--tb=no", features_dir],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # pytest --collect-only -q emits "N tests collected" or "no tests ran"
        for line in result.stdout.splitlines():
            if "test" in line and "collected" in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
        # Fallback: count non-empty, non-error lines (each is a collected item)
        lines = [
            l for l in result.stdout.splitlines()
            if l.strip() and not l.startswith("=") and not l.startswith("ERRORS")
            and "warning" not in l.lower() and "error" not in l.lower()
        ]
        return len(lines)
    except Exception:
        return 0


def _has_bypass_in_staged_diff() -> bool:
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return _BYPASS_TOKEN in result.stdout
    except Exception:
        return False


def _has_bypass_in_commit_message(message: str) -> bool:
    return _BYPASS_TOKEN in message


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------


def _ci_check(base_sha: str, head_sha: str, commit_message: str, features_dir: str) -> int:
    """CI mode: compare two SHAs. Exit 0 = pass, 1 = fail."""
    if _on_exempt_branch():
        print("BDD gate: exempt branch — skipping.")
        return 0

    if _has_bypass_in_commit_message(commit_message):
        _log_bypass(_BYPASS_TOKEN, f"CI commit={commit_message[:60]}")
        print(f"BDD gate: bypass token found — skipping (logged to {_LOG_FILE}).")
        return 0

    changed = _get_changed_src_files(base_sha, head_sha)
    if not changed:
        print("BDD gate: no source files changed — skipping.")
        return 0

    print(f"BDD gate: {len(changed)} source file(s) changed, checking {features_dir}...")
    scenario_count = _count_bdd_scenarios(features_dir)

    if scenario_count == 0:
        print(
            f"\n[BDD GATE FAILED]\n\n"
            f"Source files changed:\n"
            + "\n".join(f"  {f}" for f in changed)
            + f"\n\nBut pytest --collect-only {features_dir} found ZERO scenarios.\n\n"
            f"Steps:\n"
            f"  1. Invoke bdd-writer-greenfield to write Gherkin scenarios\n"
            f"  2. Place .feature files in {features_dir}/\n"
            f"  3. Add step definitions in {features_dir}/steps/\n"
            f"  4. Verify: pytest --collect-only {features_dir} -q\n\n"
            f"Non-behavioral change? Add [skip-bdd] to the commit message to bypass.\n"
            f"Every bypass is logged to {_LOG_FILE}.\n"
        )
        return 1

    print(f"BDD gate: {scenario_count} scenario(s) collected — passed.")
    return 0


def _precommit_check(features_dir: str) -> int:
    """Pre-commit mode: check staged files. Exit 0 = pass, 1 = fail."""
    if _on_exempt_branch():
        return 0

    if _has_bypass_in_staged_diff():
        _log_bypass(_BYPASS_TOKEN, "pre-commit staged diff")
        return 0

    changed = _get_changed_src_files()
    if not changed:
        return 0

    scenario_count = _count_bdd_scenarios(features_dir)
    if scenario_count == 0:
        print(
            f"BDD gate (pre-commit): source files staged but {features_dir} has no scenarios.\n"
            f"Write BDD scenarios first, or add [skip-bdd] to bypass."
        )
        return 1

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = sys.argv[1:]

    features_dir = _FEATURES_DIR
    for arg in args:
        if arg.startswith("--features-dir="):
            features_dir = arg.split("=", 1)[1]

    if "--pre-commit" in args:
        return _precommit_check(features_dir)

    if "--ci" in args:
        base_sha = os.environ.get("BASE_SHA", "")
        head_sha = os.environ.get("HEAD_SHA", "")
        commit_message = os.environ.get("COMMIT_MESSAGE", "")
        # Fallback: diff HEAD~1 if no SHAs provided
        if not base_sha:
            try:
                r = subprocess.run(  # nosec B603, B607
                    ["git", "rev-parse", "HEAD~1"],
                    capture_output=True, text=True, timeout=5
                )
                base_sha = r.stdout.strip()
                head_sha = "HEAD"
            except Exception:
                base_sha = head_sha = ""
        return _ci_check(base_sha, head_sha, commit_message, features_dir)

    print("Usage: python tools/check_bdd_gate.py [--ci | --pre-commit] [--features-dir=PATH]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
