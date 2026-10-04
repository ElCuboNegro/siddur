#!/usr/bin/env python3
"""tools/base_branch_gate.py -- G13: verify where a branch was actually cut from.

`enforce_gitflow.py` already checks branch *names* and PR targets. This gate
checks *history*: a branch named `feature/*` can still be cut from `main`,
dragging main-only commits (hotfixes) into `staging` when it merges. That is the
drift reported as R14 in RFC-0008 and observed in this ecosystem -- fix branches
born from `main` because `staging` was stale.

Rule
----
`feature/*`, `release/*`, `chore/*`, `docs/*`  must be cut from `staging`
`hotfix/*`                                     must be cut from `main`
integration branches and `dependabot/*`        are not checked

Predicate: the branch must not carry commits that belong exclusively to the
*other* integration branch. Comparing against a branch tip is wrong -- the tip
moves after you branch -- so the gate compares commit *sets*: any commit that is
in HEAD but not in the expected base, and also in the other integration branch
but not in the expected base, can only have arrived by branching from the wrong
place.

Invocation
----------
Both surfaces call this same script (cornerstone ADR-0225): the local hook via
`cornerstone hook` (ADR-0215) and the CI required check via the reusable
workflow. The contract is the exit code -- 0 pass, 1 fail -- plus a message on
stderr. CI must provide full history (`fetch-depth: 0`) or both refs will not
resolve.

Rendering note: this file is a cookiecutter template (`tools/` is not in
`_copy_without_render`), so it must contain no Jinja delimiters. The eleven
sibling gates take the same avoidance route; `migration_sequence_gate.py` fences
its literal braces with raw blocks instead. A test pins this.
"""

import os
import subprocess  # nosec B404
import sys

_SKIP_EXACT = ("main", "master", "staging", "HEAD")
_SKIP_PREFIXES = ("dependabot/",)
_FROM_MAIN = ("hotfix/",)
_FROM_STAGING = ("feature/", "release/", "chore/", "docs/")

_STAGING = "staging"
_MAIN_CANDIDATES = ("main", "master")


def _git(args):
    """Run git, returning (ok, stdout). Never raises on a non-zero exit."""
    proc = subprocess.run(  # nosec B603
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, proc.stdout.strip()


def _resolve(name):
    """Resolve a branch to a rev, preferring the remote-tracking copy."""
    for candidate in (f"origin/{name}", name):
        ok, _ = _git(["rev-parse", "--verify", "--quiet", candidate])
        if ok:
            return candidate
    return None


def _resolve_main():
    for name in _MAIN_CANDIDATES:
        found = _resolve(name)
        if found:
            return found
    return None


def _exclusive(include, exclude):
    """Commits reachable from `include` but not from `exclude`."""
    ok, out = _git(["rev-list", include, "--not", exclude])
    if not ok:
        return None
    return set(out.split()) if out else set()


def _head_branch():
    """The branch under test: the PR head in CI, else the checked-out branch."""
    for var in ("GITHUB_HEAD_REF", "CORNERSTONE_HEAD_REF"):
        value = os.environ.get(var)
        if value:
            return value.strip()
    ok, out = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out if ok else ""


def _expected_base(branch):
    if branch in _SKIP_EXACT or branch.startswith(_SKIP_PREFIXES):
        return None
    if branch.startswith(_FROM_MAIN):
        return "main"
    if branch.startswith(_FROM_STAGING):
        return _STAGING
    # An unrecognised prefix is enforce_gitflow.py's business (G07), not ours.
    return None


def main():
    branch = _head_branch()
    if not branch:
        print("base-branch-gate: cannot determine the current branch", file=sys.stderr)
        return 1

    expected = _expected_base(branch)
    if expected is None:
        print(f"base-branch-gate: {branch} is not subject to the base check.")
        return 0

    base_ref = _resolve_main() if expected == "main" else _resolve(_STAGING)
    other_ref = _resolve(_STAGING) if expected == "main" else _resolve_main()

    if base_ref is None:
        print(
            f"base-branch-gate: cannot resolve '{expected}'. CI needs the full "
            "history -- set fetch-depth: 0 or fetch the branch explicitly.",
            file=sys.stderr,
        )
        return 1
    if other_ref is None:
        # Nothing to compare against; the name check (G07) still applies.
        print(
            f"base-branch-gate: only '{expected}' is available, so the base of "
            f"{branch} cannot be distinguished. Fetch the full history to enable "
            "this check.",
            file=sys.stderr,
        )
        return 1

    ours = _exclusive("HEAD", base_ref)
    theirs = _exclusive(other_ref, base_ref)
    if ours is None or theirs is None:
        print("base-branch-gate: git rev-list failed; is this a git repo?", file=sys.stderr)
        return 1

    borrowed = ours & theirs
    if borrowed:
        sample = sorted(borrowed)[:3]
        print(
            f"base-branch-gate: {branch} carries {len(borrowed)} commit(s) that exist "
            f"only on '{other_ref}', so it was cut from there. Expected base: "
            f"'{expected}'. Offending commits: {', '.join(c[:8] for c in sample)}. "
            f"Rebase onto '{base_ref}' before opening the PR.",
            file=sys.stderr,
        )
        return 1

    print(f"base-branch-gate: {branch} is correctly based on '{expected}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
