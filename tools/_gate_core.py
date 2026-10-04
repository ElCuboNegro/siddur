#!/usr/bin/env python3
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (schematics, per ADR-0159 Decision 1) and propagate with
# `cornerstone update`.
# ADR: 0159
"""tools/_gate_core.py — hardened shared foundation for all governance gates.

ADR-0159. Every gate consumes these primitives instead of re-implementing
classification, bypass parsing, range resolution and git plumbing — which is
how the pre-0159 harness ended up bypassable along six shared axes (S1..S6).

Closes:
  S1/S5  bypass parsed ONLY from the commit-message trailer; covered-by verified
         against the ADR cache; blanket skip only on hotfix/*.
  S2     classification by EXCLUSION (default governed; small exempt allowlist;
         case-folded; segment-anchored; governs tools/ and IaC).
  S3     range resolver computes its own merge-base (never trusts caller input).
  S4     BDD/red-phase verdict: presence -> EXECUTION; flags "unexpectedly green
         at red" as probable duplication (the reuse detector).
  S6     git plumbing is NUL-delimited (-z) and FAIL-CLOSED.
  AC-5   sequence verdict walks first-parent (merges cannot smuggle source).
"""

from __future__ import annotations

import re
import subprocess  # nosec B404
import sys
from pathlib import Path, PurePosixPath


class GateError(Exception):
    """Raised on any git/plumbing failure so callers FAIL CLOSED (S6)."""


# --- S2: classification by EXCLUSION ---------------------------------------
_EXEMPT_SUFFIXES = {".md", ".rst", ".txt", ".lock", ".png", ".jpg", ".svg", ".csv"}
_DOC_SEGMENTS = {"docs"}
_FEATURE_SUFFIX = ".feature"


def _parts(path: str) -> tuple[str, ...]:
    return PurePosixPath(path.replace("\\", "/")).parts


def _suffix(path: str) -> str:
    parts = _parts(path)
    name = parts[-1] if parts else ""
    return ("." + name.rsplit(".", 1)[-1]).lower() if "." in name else ""


def is_governed(path: str) -> bool:
    """EXCLUSION model: governed unless clearly exempt data/docs (closes S2)."""
    parts = _parts(path)
    if not parts:
        return False
    if _suffix(path) == _FEATURE_SUFFIX:
        return False
    if parts[0] in _DOC_SEGMENTS:
        return False
    if _suffix(path) in _EXEMPT_SUFFIXES:
        return False
    return True


def phase_of(path: str) -> str:
    """SPARC phase of a changed path (S / A / R_red / C / R_green / exempt)."""
    parts = _parts(path)
    low = path.lower()
    if low.endswith(_FEATURE_SUFFIX):
        return "S"
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "adr" and low.endswith(".md"):
        return "A"
    if parts and parts[0] in ("tests", "test"):
        return "R_red"
    if PurePosixPath(low).name in ("changelog.md", "changelog"):
        return "C"
    return "R_green" if is_governed(path) else "exempt"


# --- SDLC phase declaration (ADR-0079) -------------------------------------
# The gates already classify a change into a SPARC letter (phase_of). We surface
# it to telemetry: the gate writes the current lifecycle phase to a marker that
# the Stop-hook emitter reads and tags onto every spend event. Offline,
# best-effort, never blocks the gate.
_PHASE_MARKER = PurePosixPath(".telemetry") / ".phase"
_PHASE_LABELS = {
    "S": "specification",
    "A": "architecture",
    "R_red": "test",
    "R_green": "refinement",
    "C": "completion",
}


def phase_label(letter: str) -> str | None:
    """Map a SPARC letter (phase_of) to the canonical telemetry phase label."""
    return _PHASE_LABELS.get(letter)


def declare_phase(phase: str | None, *, root: str | None = None) -> None:
    """Write the current lifecycle phase to ``.telemetry/.phase`` (ADR-0079).

    Accepts a SPARC letter (``S``/``A``/``R_red``/``R_green``/``C``) or an
    explicit label (``pre-commit``/``ci``/``review``…). ``exempt``/unknown letters
    and ``None`` are ignored (no marker written). Best-effort and offline — a
    failure must never break the gate.
    """
    if not phase:
        return
    label = _PHASE_LABELS.get(phase, phase)
    if label in (None, "exempt"):
        return
    try:
        base = Path(root) if root else Path.cwd()
        marker = base / str(_PHASE_MARKER)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(label + "\n", encoding="utf-8")
    except Exception:  # nosec B110  # noqa: BLE001 — telemetry marker is never load-bearing
        pass


# --- S1/S5: bypass from the commit MESSAGE only ----------------------------
_BYPASS_RE = re.compile(
    r"\[skip-(?P<gate>[a-z]+)(?::\s*covered-by:\s*(?P<adr>\d{3,4}))?\]", re.IGNORECASE
)


def parse_bypass(commit_message: str, branch: str, adr_exists) -> dict:
    """Decide a bypass from the COMMIT MESSAGE ONLY (never file content/diff).

    Returns {allowed, reason}. Closes S1 (content self-authorization) and S5
    (branch restriction + covered-by verification).
    """
    m = _BYPASS_RE.search(commit_message or "")
    if not m:
        return {"allowed": False, "reason": "no bypass token"}
    gate, adr = m.group("gate"), m.group("adr")
    if adr is not None:
        num = f"{int(adr):04d}"
        ok = bool(adr_exists(num))
        return {
            "allowed": ok,
            "reason": f"covered-by ADR-{num}" + ("" if ok else " does NOT exist"),
        }
    if (branch or "").startswith("hotfix/"):
        return {"allowed": True, "reason": "blanket skip on hotfix/*"}
    return {"allowed": False, "reason": f"blanket skip-{gate} not allowed off hotfix/*"}


# --- S6: NUL-delimited, fail-closed git plumbing ---------------------------
def _git(args: list[str], cwd) -> str:
    try:
        r = subprocess.run(  # nosec B603 B607
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise GateError(f"git failed: {e}") from e
    if r.returncode != 0:
        raise GateError(f"git {args[:2]} rc={r.returncode}: {r.stderr.strip()[:120]}")
    return r.stdout


def git_changed(
    cwd, base: str | None = None, head: str = "HEAD", staged: bool = False
) -> list[str]:
    """Changed paths via `-z` (no quoting/mangling of unicode/space names). S6."""
    if staged:
        args = ["diff", "--cached", "-z", "--name-only", "--diff-filter=ACMRD"]
    else:
        if not base:
            raise GateError("base required")
        args = ["diff", "-z", "--name-only", "--diff-filter=ACMRD", f"{base}..{head}"]
    return [p for p in _git(args, cwd).split("\0") if p]


def resolve_range(cwd, protected: str = "origin/main") -> tuple[str, str]:
    """Compute our OWN merge-base — never trust a caller-supplied range (S3)."""
    base = _git(["merge-base", protected, "HEAD"], cwd).strip()
    if not base:
        raise GateError("no merge-base")
    return base, "HEAD"


def gitlink_paths(cwd, base: str, head: str = "HEAD") -> list[str]:
    """Submodule/gitlink (mode 160000) changes — smuggling vector (AC-5)."""
    out = _git(["diff", "--raw", "--no-renames", f"{base}..{head}"], cwd)
    paths = []
    for line in out.splitlines():
        if line.startswith(":") and "160000" in line.partition("\t")[0]:
            paths.append(line.partition("\t")[2])
    return paths


# --- S4: BDD execution / red-phase verdict (the reuse detector) ------------
def bdd_red_verdict(collected: int, failed: int) -> str:
    """At R_red a spec must exist AND fail. Presence != validity (S4).

    NO_SCENARIOS       -> empty/junk .feature; BLOCK.
    UNEXPECTEDLY_GREEN  -> already implemented elsewhere; probable DUPLICATION.
    RED_OK             -> falsifiable & unimplemented; proceed to green.
    """
    if collected <= 0:
        return "NO_SCENARIOS"
    if failed == 0:
        return "UNEXPECTEDLY_GREEN"
    return "RED_OK"


def run_pytest(cwd, target: str) -> tuple[int, int]:
    """Run pytest; return (collected, failed). Fail-closed on plumbing error."""
    try:
        r = subprocess.run(  # nosec B603 B607
            [
                sys.executable,
                "-m",
                "pytest",
                target,
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise GateError(f"pytest failed to run: {e}") from e
    out = r.stdout + r.stderr
    mp = re.search(r"(\d+) passed", out)
    mf = re.search(r"(\d+) failed", out)
    p = int(mp.group(1)) if mp else 0
    f = int(mf.group(1)) if mf else 0
    return p + f, f


# --- AC-5: sequence verdict over FIRST-PARENT ------------------------------
def sequence_verdict(timeline: list[set]) -> list[str]:
    """timeline = first-parent commits (oldest->newest), each a set of phases.

    Source (R_green) must be preceded by S, A, R_red. The caller passes a
    first-parent walk, so side-branch smuggling and cherry-pick reordering
    cannot fake the order.
    """
    first: dict[str, int] = {}
    for i, phases in enumerate(timeline):
        for ph in phases:
            first.setdefault(ph, i)
    v = []
    src = first.get("R_green")
    if src is not None:
        for ph in ("S", "A", "R_red"):
            if ph not in first or first[ph] >= src:
                v.append(f"{ph} not before source@{src}")
    return v


def adr_cache_lookup(project_root) -> set:
    """Return the set of known ADR numbers from docs/adr/.adr-cache.json."""
    import json  # noqa: PLC0415

    cache = Path(project_root) / "docs" / "adr" / ".adr-cache.json"
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        return set(data.get("adrs", {}).keys())
    except (OSError, ValueError):
        return set()
