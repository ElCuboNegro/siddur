#!/usr/bin/env python3
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (schematics, per ADR-0159 Decision 1) and propagate with
# `cornerstone update`.
# ADR: 0167
"""tools/migration_sequence_gate.py — guard against deploying code that is
BEHIND the Alembic migration state already applied to a shared database.

ADR-0167. A shared DB's ``alembic_version`` advances the moment ANY branch's
image boots and runs ``alembic upgrade head``. Application code is promoted
branch-by-branch and can lag behind the DB. When the deployed image's migration
set is a strict subset of what the shared DB already applied, ``alembic upgrade``
cannot resolve the stamped revision and the container dies at startup
(the 2026-07-29 ``Can't locate revision '0025_...'`` incident).

Two offline layers (a third, online, DB↔image guard is deferred — ADR-0167 L3):

  L1  graph integrity (pre-commit + CI): exactly one head; every ``down_revision``
      resolves; no duplicate ``revision`` ids; single connected chain.
  L2  promotion monotonicity (CI, on PR): the revision-set reachable from the
      HEAD branch must be a SUPERSET of the BASE branch's — ``main`` may never be
      released behind ``staging``'s already-deployed migrations.

Invariants (ADR-0167):
  INV-1  the DAG is read from the ``revision`` / ``down_revision`` SYMBOLS via
         ``ast`` — NEVER from filenames. The tree legitimately carries three
         ``0022_*`` files with distinct revision ids; filename logic false-fires.
         (``ScriptDirectory`` raises on the very defects L1 must *report*, so we
         parse the symbols directly to produce teaching errors.)
  INV-2  L2 keys off the Alembic revision-SETS, not git commit ancestry — the
         ecosystem reconciles promotions with ``merge -s ours`` / squash.
  INV-3  fail-closed: if the base tree cannot be materialized, the gate FAILS.
  INV-4  no-migration change-sets pass trivially and cheaply.
  INV-5  divergent heads FAIL with a message that teaches the fix (merge migration).

Usage:
    python tools/migration_sequence_gate.py --check-graph       # L1 (working tree)
    python tools/migration_sequence_gate.py --pre-commit         # L1 (alias)
    python tools/migration_sequence_gate.py --check-promotion \\
        --base origin/main --head HEAD                           # L2
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gate_core as core  # noqa: E402

# Where Alembic revision scripts live, relative to the repo root. Overridable
# via the MIGRATION_VERSIONS_PATH env var for projects that relocate migrations.
VERSIONS_PATH = os.environ.get("MIGRATION_VERSIONS_PATH", "alembic/versions")

# L2 governed base↔head promotion pairs. Config, not hardcoded (ADR-0167).
# A PR is checked only when its (base, head) matches one of these; head patterns
# ending in "/*" match by prefix. Everything else is a no-op (INV-4).
GOVERNED_PAIRS: tuple[tuple[str, str], ...] = (
    ("main", "staging"),
    ("main", "hotfix/*"),
    ("main", "release/*"),
)


# ---------------------------------------------------------------------------
# Symbol-level revision loading (INV-1: symbols, never filenames)
# ---------------------------------------------------------------------------
def _extract_revision(source: str) -> tuple[str | None, tuple[str, ...]]:
    """Return ``(revision, down_revisions)`` from a migration's module SYMBOLS.

    Reads the module-level ``revision`` / ``down_revision`` assignments via
    ``ast`` — no import, no execution, no filename inspection (INV-1).
    ``down_revision`` is normalised to a tuple (``()`` for a base, one entry for
    a linear child, many for a merge).
    """
    revision: str | None = None
    down: tuple[str, ...] = ()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None, ()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "revision" in names:
            revision = _as_str(node.value)
        elif "down_revision" in names:
            down = _as_str_tuple(node.value)
    return revision, down


def _as_str(value: ast.expr) -> str | None:
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _as_str_tuple(value: ast.expr) -> tuple[str, ...]:
    """Normalise a ``down_revision`` literal (str / None / tuple / list) to a tuple."""
    if isinstance(value, ast.Constant):
        return (value.value,) if isinstance(value.value, str) else ()
    if isinstance(value, (ast.Tuple, ast.List)):
        return tuple(s for el in value.elts if (s := _as_str(el)) is not None)
    return ()


def load_revmap(versions_dir: Path) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    """Parse ``versions_dir/*.py`` into ``{revision: down_revisions}``.

    Returns ``(revmap, duplicates)`` where ``duplicates`` names any revision id
    declared by more than one file (a collision the dict cannot represent).
    """
    revmap: dict[str, tuple[str, ...]] = {}
    duplicates: list[str] = []
    for path in sorted(versions_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        revision, down = _extract_revision(path.read_text(encoding="utf-8"))
        if revision is None:
            continue
        if revision in revmap:
            duplicates.append(revision)
            continue
        revmap[revision] = down
    return revmap, duplicates


# ---------------------------------------------------------------------------
# L1 — pure graph integrity (no git, no I/O — testable & red-team-attackable)
# ---------------------------------------------------------------------------
def _heads(revmap: dict[str, tuple[str, ...]]) -> set[str]:
    """Revisions that are not a parent of any other revision."""
    referenced = {p for downs in revmap.values() for p in downs}
    return set(revmap) - referenced


def check_graph(revmap: dict[str, tuple[str, ...]], duplicates: list[str]) -> list[str]:
    """Pure L1 verdict. Empty list == integral graph. Each string teaches a fix."""
    if not revmap:
        return []  # INV-4: nothing to check
    errors: list[str] = []

    for rev in sorted(duplicates):
        errors.append(
            f"duplicate revision id '{rev}' declared by two migrations — "
            f"each revision id must be unique (the filename prefix is irrelevant)."
        )

    missing = {parent for downs in revmap.values() for parent in downs if parent not in revmap}
    for parent in sorted(missing):
        errors.append(
            f"down_revision '{parent}' has no migration file — the parent revision "
            f"is missing from {VERSIONS_PATH}/ (a script was deleted or never added)."
        )

    heads = _heads(revmap)
    if not heads:
        errors.append(
            "no Alembic head found — every revision is referenced as a parent, so the "
            "down_revision chain contains a cycle. Break the cycle so exactly one head remains."
        )
    elif len(heads) > 1:
        listed = ", ".join(sorted(heads))
        errors.append(
            f"multiple Alembic heads: {listed}. Reconcile with a merge migration: "
            f'`alembic merge -m "merge heads" {" ".join(sorted(heads))}`.'
        )

    # Connectivity: everything must be reachable walking parents from the head(s).
    # Skip when parents are already missing (that error dominates and the walk
    # would just re-report it).
    if not missing and heads:
        reachable: set[str] = set()
        stack = list(heads)
        while stack:
            rev = stack.pop()
            if rev in reachable:
                continue
            reachable.add(rev)
            stack.extend(revmap.get(rev, ()))
        orphaned = set(revmap) - reachable
        if orphaned:
            listed = ", ".join(sorted(orphaned))
            errors.append(
                f"detached revision(s) not reachable from any head: {listed}. "
                f"Re-point their down_revision into the main chain."
            )
    return errors


# ---------------------------------------------------------------------------
# L2 — pure promotion monotonicity
# ---------------------------------------------------------------------------
def check_superset(
    base_revs: set[str], head_revs: set[str], base_ref: str, head_ref: str
) -> list[str]:
    """Pure L2 verdict: HEAD's revision-set must be a SUPERSET of BASE's."""
    missing = base_revs - head_revs
    if not missing:
        return []
    listed = ", ".join(sorted(missing))
    return [
        f"'{head_ref}' is BEHIND '{base_ref}': it is missing migration(s) {listed} "
        f"that '{base_ref}' already contains. A shared DB may already be stamped at "
        f"one of these — deploying '{head_ref}' would crash at `alembic upgrade`. "
        f"Merge '{base_ref}' into '{head_ref}' before promoting."
    ]


def pair_is_governed(base: str, head: str, pairs=GOVERNED_PAIRS) -> bool:
    """True when (base, head) is a governed promotion pair (INV-4 skip otherwise)."""
    for gbase, ghead in pairs:
        if base != gbase:
            continue
        if ghead.endswith("/*"):
            if head.startswith(ghead[:-1]):
                return True
        elif head == ghead:
            return True
    return False


# ---------------------------------------------------------------------------
# Plumbing (git + filesystem) — fail-closed (INV-3)
# ---------------------------------------------------------------------------
def _repo_root() -> Path:
    return Path(core._git(["rev-parse", "--show-toplevel"], Path.cwd()).strip())


def _touches_migrations(cwd: Path, base: str, head: str) -> bool:
    try:
        changed = core.git_changed(cwd, base=base, head=head)
    except core.GateError:
        return True  # can't tell -> don't skip; let the real check fail-closed
    return any(f.startswith(VERSIONS_PATH + "/") for f in changed)


def _materialize_versions(cwd: Path, ref: str, dest: Path) -> Path | None:
    """Extract ``VERSIONS_PATH`` at ``ref`` into ``dest`` via ``git archive`` (INV-3).

    Returns ``None`` when ``ref`` is valid but has no migrations dir yet (empty
    revision-set); raises GateError when the ref itself cannot be resolved so the
    caller fails closed instead of silently passing (INV-3).
    """
    # Validate the ref FIRST, locale- and git-version-independently: a bad/unfetched
    # ref is a hard failure (INV-3); a valid ref whose tree simply lacks the
    # migrations path is an empty revision-set, not a failure. This avoids matching
    # git's (localized) "did not match" stderr text.
    try:
        # : `^{commit}` is git peel syntax inside a Python f-string, so the
        # literal braces double to `^{{commit}}`. Cookiecutter renders this file with
        # Jinja, which would otherwise read `{{commit}}` as an undefined variable and
        # abort generation of every starter that includes the common overlay.
        core._git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd)  # 
    except core.GateError as exc:
        raise core.GateError(
            f"cannot resolve ref '{ref}'. In CI ensure it is fetched "
            f"(fetch-depth: 0 or an explicit `git fetch origin {ref}`)."
        ) from exc
    try:
        archive = subprocess.run(  # nosec B603 B607
            ["git", "archive", ref, "--", VERSIONS_PATH],
            cwd=cwd,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - defensive plumbing
        raise core.GateError(f"git archive {ref} failed: {exc}") from exc
    if archive.returncode != 0:
        # ref is valid (verified above) but the migrations path is absent at it
        # (e.g. the base of the first-ever migration PR) -> empty revision-set.
        return None
    try:
        tar = subprocess.run(  # nosec B603 B607
            ["tar", "-x", "-C", str(dest)],
            input=archive.stdout,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - defensive plumbing
        raise core.GateError(f"tar extract for '{ref}' failed: {exc}") from exc
    if tar.returncode != 0:  # pragma: no cover - defensive plumbing
        raise core.GateError(f"tar extract for '{ref}' rc={tar.returncode}")
    return dest / VERSIONS_PATH


def _revs_at_ref(cwd: Path, ref: str) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        versions = _materialize_versions(cwd, ref, Path(tmp))
        if versions is None:
            return set()  # ref has no migrations dir yet -> empty revision-set
        revmap, _ = load_revmap(versions)
        return set(revmap)


# ---------------------------------------------------------------------------
# Layer runners
# ---------------------------------------------------------------------------
def run_graph() -> int:
    """L1 on the working tree."""
    try:
        root = _repo_root()
    except core.GateError as exc:  # pragma: no cover - only reachable outside a git repo
        print(f"[migration-sequence-gate] FAILED CLOSED — {exc}", file=sys.stderr)
        return 1
    versions = root / VERSIONS_PATH
    if not versions.is_dir():
        print("[migration-sequence-gate] SKIP: no migrations directory", file=sys.stdout)
        return 0
    revmap, duplicates = load_revmap(versions)
    errors = check_graph(revmap, duplicates)
    if errors:
        print("[migration-sequence-gate] L1 BLOCKED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        f"[migration-sequence-gate] L1 PASS: {len(revmap)} revisions, single head", file=sys.stdout
    )
    return 0


def run_promotion(
    base: str, head: str, base_ref: str | None = None, head_ref: str | None = None
) -> int:
    """L2 for a governed base↔head promotion PR.

    ``base`` / ``head`` are the logical BRANCH NAMES used for governance matching
    (``main``, ``staging``, ``hotfix/*``). ``base_ref`` / ``head_ref`` are the git
    refs actually materialized — they default to the names but let CI pass the
    remote-tracking / checkout refs (e.g. ``origin/main`` and ``HEAD``).
    """
    if not pair_is_governed(base, head):
        print(
            f"[migration-sequence-gate] SKIP: ({base} <- {head}) is not a governed pair",
            file=sys.stdout,
        )
        return 0
    base_ref = base_ref or base
    head_ref = head_ref or head
    try:
        cwd = _repo_root()
    except core.GateError as exc:  # pragma: no cover - only reachable outside a git repo
        print(f"[migration-sequence-gate] L2 FAILED CLOSED — {exc}", file=sys.stderr)
        return 1
    if not _touches_migrations(cwd, base_ref, head_ref):
        print("[migration-sequence-gate] L2 PASS: no migration changes in this PR", file=sys.stdout)
        return 0
    try:
        base_revs = _revs_at_ref(cwd, base_ref)
        head_revs = _revs_at_ref(cwd, head_ref)
    except core.GateError as exc:
        print(f"[migration-sequence-gate] L2 FAILED CLOSED — {exc}", file=sys.stderr)
        return 1
    errors = check_superset(base_revs, head_revs, base, head)
    if errors:
        print("[migration-sequence-gate] L2 BLOCKED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"[migration-sequence-gate] L2 PASS: '{head}' ⊇ '{base}'", file=sys.stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-0167 migration sequence gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check-graph", action="store_true", help="L1: graph integrity (working tree)"
    )
    group.add_argument("--pre-commit", action="store_true", help="L1 alias for the pre-commit hook")
    group.add_argument("--check-promotion", action="store_true", help="L2: promotion monotonicity")
    parser.add_argument("--base", help="L2 base branch NAME for governance (e.g. main)")
    parser.add_argument(
        "--head", default="HEAD", help="L2 head branch NAME for governance (e.g. staging)"
    )
    parser.add_argument("--base-ref", help="git ref to materialize for base (default: --base)")
    parser.add_argument("--head-ref", help="git ref to materialize for head (default: --head)")
    args = parser.parse_args(argv)

    if args.check_graph or args.pre_commit:
        return run_graph()
    if not args.base:
        parser.error("--check-promotion requires --base")
    return run_promotion(args.base, args.head, args.base_ref, args.head_ref)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
