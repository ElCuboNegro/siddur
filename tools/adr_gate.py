#!/usr/bin/env python3
# ADR: 0017, ADR: 0060, ADR: 0068, ADR: 0099, ADR: 0124, ADR: 0129, ADR: 0155, ADR: 0172, ADR: 0190
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (cornerstone/data/starters/ + tools/) and propagate with
# `cornerstone update`.
"""tools/adr_gate.py — ADR Gate for Claude Code / Gemini PreToolUse[Edit|Write] hooks.

ADRs live in GitHub Discussions (ADR-0128); this gate validates that an edit
references an ADR that EXISTS, using a versioned offline cache
(docs/adr/.adr-cache.json) so commit-time stays network-free (ADR-0129).

An edit to a guarded file is allowed when ANY of:
  (a) Post-edit content (or existing file) carries an ADR annotation `# ADR: NNNN`
      and NNNN is present in the offline cache.
  (b) An ADR is referenced but the cache is genuinely unknown (offline,
      pre-migration, corrupt) -> fail-open allow. A cache that exists but is
      EMPTY is a different, known state (ADR-0172), and splits in two by
      whether it carries `refreshed_at` (ADR-0190): never refreshed (the
      starter/`cornerstone init` seed) -> bootstrap, allowed but WARN +
      logged as `type=empty-cache`; refreshed and still reporting zero ADRs
      -> the reference is provably fabricated -> DENIED.
  (c) An ADR is referenced but NOT in the cache -> WARN, do not block (ADR-0129),
      unless CORNERSTONE_ADR_OFFLINE_STRICT is set.
  (d) The hook payload contains a typed bypass token.
  (e) The current branch is exempt (hotfix/*).
  (f) The edit is trivial (ADR-0124): cosmetic-only, or a small single-file diff.
  (g) The path matches a project-declared exemption in `.adr-exempt` (ADR-0172,
      #868) -- a versioned, reviewable alternative to embedding a typed bypass
      token inside the file itself, which PreToolUse mode otherwise forces.

An edit is DENIED regardless of ADR references when the target is a scaffolded
copy owned upstream (ADR-0155): the file carries a MANAGED BY CORNERSTONE
header and the project is cornerstone-generated. Such changes belong in
cornerstone/data/starters/ and propagate via `cornerstone update`.

If no ADR is referenced at all, the edit is BLOCKED (the ADR-First mandate).

Typed bypass vocabulary (strict format -- never matches session metadata accidentally):
  [skip-adr: trivial]          -- formatting / lint fix, no architectural decision
  [skip-adr: covered-by:NNNN] -- ADR-NNNN already covers this change
  [skip-adr: no-decision]      -- purely mechanical change

Every bypass is logged with the typed reason to .adr-gate-bypasses.log.

Configuration
-------------
CORNERSTONE_ADR_PATH            -- directory holding the ADR cache (default: docs/adr)
CORNERSTONE_ADR_OFFLINE_STRICT  -- if set, a cache-miss reference blocks instead of warns;
                                   same for a never-refreshed empty cache (ADR-0190)

Modes
-----
  PreToolUse hook (default): reads $ARGUMENTS env var or stdin, emits JSON decision.
  Pre-commit hook:           invoke with --pre-commit; reads staged file list from git.
"""

import difflib
import json
import logging
import os
import re
import subprocess  # nosec B404
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ADR_PATH = os.environ.get("CORNERSTONE_ADR_PATH", "docs/adr")
_CACHE_FILE = ".adr-cache.json"
_STRICT = bool(os.environ.get("CORNERSTONE_ADR_OFFLINE_STRICT"))
_LOG_FILE = Path(".adr-gate-bypasses.log")
_EXEMPT_FILE = ".adr-exempt"  # ADR-0172 (#868): project-local, versioned exemptions

_GUARDED_EXTENSIONS = {".py", ".sh", ".yml", ".yaml"}

_EXEMPT_FRAGMENTS = [
    "tests/",
    "/tests/",
    "migrations/",
    "/migrations/",
    "cookiecutter.",  # cookiecutter template variables -- never block
    "docs/",  # ADR-0124: documentation trees are non-structural
    "output/",  # ADR-0172 (#866): derived/regenerable artifacts, same reasoning as docs/
]

# ADR-0124: non-structural repo configuration files
_EXEMPT_BASENAMES = {
    ".pre-commit-config.yaml",
    "mkdocs.yml",
    "docker-compose.yml",
}

# ADR-0124: triviality thresholds
_SMALL_EDIT_MAX_CHANGED_LINES = 15
_MULTI_FILE_STRICT_THRESHOLD = 3  # >= this many dirty guarded files -> strict

_EXEMPT_BRANCH_PREFIXES = ("hotfix/",)

# Strict typed bypass -- the format makes accidental matches from session IDs impossible
_BYPASS_RE = re.compile(
    r"\[skip-adr:\s*(trivial|covered-by:\d{4}|no-decision)\]", re.IGNORECASE
)

# File-level ADR annotation: # ADR: NNNN  or  # ADR: ADR-0005
_ADR_ANNOTATION_RE = re.compile(r"#\s*adr\s*:?\s*(?:ADR-)?(\d{4})", re.IGNORECASE)

# Commit trailer: ADR: NNNN  or  ADR: <discussions url ending in /NNN>
_TRAILER_RE = re.compile(
    r"^\s*ADR:\s*(?:ADR-)?(\d{3,4})\s*$", re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return ""


def _parse_payload(raw: str) -> tuple[str, str, str]:
    """Return (file_path, post_edit_content, pre_edit_content) from the payload."""
    if not raw:
        return "", "", ""
    try:
        data = json.loads(raw)
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
        post_content = tool_input.get("new_string") or tool_input.get("content") or ""
        pre_content = tool_input.get("old_string") or ""
        return file_path, post_content, pre_content
    except (json.JSONDecodeError, AttributeError, TypeError):
        return "", "", ""


def _get_repo_root() -> "Path | None":
    """Return the absolute path of the current git repository root, or None."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        root = result.stdout.strip()
        return Path(root) if result.returncode == 0 and root else None
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return None


_MANAGED_MARK = "MANAGED BY CORNERSTONE"
_MANAGED_HEAD_LINES = 10


def _is_generated_project() -> bool:
    """True in a cornerstone-generated project (ADR-0155).

    Cornerstone itself is its own generated project (ADR-0153) but carries the
    canonical sources — detected by the bundled starters tree — so the
    managed-file rule never blocks upstream development.
    """
    root = _get_repo_root()
    if root is None or not (root / ".cornerstone").exists():
        return False
    return not (root / "cornerstone" / "data" / "starters").exists()


def _is_managed_copy(disk_content: str) -> bool:
    """True if the on-disk file declares itself a scaffolded managed copy."""
    head = disk_content.splitlines()[:_MANAGED_HEAD_LINES]
    return any(_MANAGED_MARK in line for line in head)


def _managed_message(file_path: str) -> str:
    return (
        f"MANAGED FILE BLOCKED (ADR-0155)\n\n"
        f"'{file_path}' is a scaffolded copy owned by Cornerstone.\n"
        f"Decisions about it belong upstream, not in this project:\n"
        f"  1. Change cornerstone/data/starters/ in the cornerstone repo\n"
        f'     (with its own ADR: `cornerstone adr new "<title>"`)\n'
        f"  2. Propagate here with `cornerstone update`\n\n"
        f"Emergency bypass (logged): [skip-adr: trivial]"
    )


@lru_cache(maxsize=1)
def _load_project_exemptions() -> tuple[str, ...]:
    """Read project-local exemption fragments from `.adr-exempt` (ADR-0172, #868).

    One fragment per line, same substring semantics as `_EXEMPT_FRAGMENTS` --
    a project declares these itself, versioned and reviewable in the diff of
    the PR that adds them, instead of an agent embedding a typed bypass token
    inside the file it is writing (the only channel PreToolUse mode otherwise
    offers). Blank lines and lines starting with '#' are ignored. Cached for
    the lifetime of the process -- this script runs fresh per hook/commit
    invocation, so there is no staleness risk within a single check.
    """
    root = _get_repo_root() or Path.cwd()
    path = root / _EXEMPT_FILE
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(
        stripped
        for raw_line in lines
        if (stripped := raw_line.strip()) and not stripped.startswith("#")
    )


def _is_exempt_path(file_path: str) -> bool:
    """True if file_path matches a built-in or project-declared exemption fragment."""
    fragments = (*_EXEMPT_FRAGMENTS, *_load_project_exemptions())
    return any(fragment in file_path for fragment in fragments)


def _needs_adr(file_path: str) -> bool:
    """True if this file path is subject to the ADR mandate."""
    if not file_path:
        return False

    if file_path.startswith(_ADR_PATH + "/") or ("/" + _ADR_PATH + "/") in file_path:
        return False

    if _is_exempt_path(file_path):
        return False

    p = Path(file_path)

    if p.suffix == ".md":
        return False

    if p.name in _EXEMPT_BASENAMES:  # ADR-0124: non-structural repo config
        return False

    # ADR-0017: only apply mandate to files within this repository
    repo_root = _get_repo_root()
    if repo_root is not None:
        try:
            Path(file_path).resolve().relative_to(repo_root)
        except ValueError:
            return False  # file is outside our repo -- no jurisdiction

    return p.suffix in _GUARDED_EXTENSIONS


def _current_branch() -> str:
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return ""


def _on_exempt_branch() -> bool:
    """True when the current branch is exempt from the ADR mandate (hotfix/*)."""
    branch = _current_branch()
    return any(branch.startswith(p) for p in _EXEMPT_BRANCH_PREFIXES)


# ---------------------------------------------------------------------------
# Offline ADR cache (ADR-0129) — the single source of "does this ADR exist?"
# ---------------------------------------------------------------------------


def _load_adr_cache() -> tuple[bool, bool, set[str]]:
    """Return (cache_known, cache_verified, ids) from docs/adr/.adr-cache.json.

    cache_known=False means genuinely unknown (no cache file / corrupt /
    offline pre-migration) -- callers treat that as fail-open, per ADR-0129.
    cache_known=True with an empty ids set means the cache file exists and
    parses, but reports zero ADRs -- a known state (project has no ADRs yet),
    not an unknown one. Conflating the two was ADR-0172's #867: any fabricated
    '# ADR: NNNN' satisfied the gate in the empty-cache state every freshly
    generated project starts in.

    cache_verified is the ADR-0190 refinement: `refreshed_at` is stamped only by
    adr_mgmt.write_cache(), which only runs after a successful Discussions
    listing. Its presence therefore proves we DID reach GitHub and the answer
    was "zero ADRs" -- so the project can create its first ADR and any
    reference is fabricated. Its absence is the untouched seed written by
    `cornerstone init` (and shipped in the starters), where the project may
    genuinely not be able to create an ADR yet (#869).
    """
    root = _get_repo_root() or Path.cwd()
    path = root / _ADR_PATH / _CACHE_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        verified = bool(str(data.get("refreshed_at") or "").strip())
        ids = {str(k).zfill(4) for k in (data.get("adrs") or {})}
    except (OSError, ValueError, AttributeError, TypeError):
        return False, False, set()
    return True, verified, ids


def _trailer_adrs(message: str) -> set[str]:
    """ADR ids referenced via a commit trailer `ADR: NNNN`."""
    return {m.group(1).zfill(4) for m in _TRAILER_RE.finditer(message or "")}


# ---------------------------------------------------------------------------
# ADR-0124 — triviality heuristics (small / cosmetic edits skip the mandate)
# ---------------------------------------------------------------------------


def _meaningful_lines(text: str) -> list[str]:
    """Lines that survive removing blanks, full-line comments and whitespace."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        out.append("".join(stripped.split()))
    return out


def _is_cosmetic_edit(pre: str, post: str) -> bool:
    """True when the edit only touches whitespace, blank lines or comments."""
    return bool(pre) and _meaningful_lines(pre) == _meaningful_lines(post)


def _changed_line_count(pre: str, post: str) -> int:
    """Number of lines added/removed/replaced between pre and post content."""
    matcher = difflib.SequenceMatcher(
        a=pre.splitlines(), b=post.splitlines(), autojunk=False
    )
    changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def _dirty_guarded_count() -> int:
    """Count modified guarded files in the working tree (multi-file signal)."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return 0
        count = 0
        for line in result.stdout.splitlines():
            path = line[3:].strip()
            if not path:
                continue
            if Path(path).suffix not in _GUARDED_EXTENSIONS:
                continue
            if _is_exempt_path(path):
                continue
            count += 1
        return count
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return 0


def _is_trivial_edit(pre: str, post: str) -> bool:
    """ADR-0124: cosmetic edits, or small single-file edits, skip the mandate."""
    if not pre:
        return False
    if _is_cosmetic_edit(pre, post):
        return True
    if _changed_line_count(pre, post) >= _SMALL_EDIT_MAX_CHANGED_LINES:
        return False
    return _dirty_guarded_count() < _MULTI_FILE_STRICT_THRESHOLD


def _annotated_adrs(content: str) -> set[str]:
    """Return zero-padded ADR IDs declared via # ADR: NNNN in content."""
    return {m.group(1).zfill(4) for m in _ADR_ANNOTATION_RE.finditer(content)}


def _log_bypass(bypass_type: str, file_path: str) -> None:
    try:
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        entry = f"{ts} | type={bypass_type} | file={file_path}\n"
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception as exc:  # nosec B110
        logger.debug("adr_gate: swallowed exception: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Reference validation against the cache (ADR-0129)
# ---------------------------------------------------------------------------


def _classify_reference(referenced: set[str]) -> str:
    """Classify an ADR reference set: 'none' | 'ok' | 'bootstrap' | 'empty' | 'stale'.

    'none'      -> no ADR referenced (block).
    'ok'        -> referenced ADR is known, or cache is genuinely unknown (allow).
    'bootstrap' -> cache reports zero ADRs and was never refreshed (no
                   `refreshed_at`): the untouched seed a generated project
                   starts with, where `cornerstone adr new` may still be
                   impossible (#869). Warn loudly and log (ADR-0172), block
                   only under strict mode.
    'empty'     -> cache reports zero ADRs but WAS refreshed: we reached
                   Discussions and the answer was "none", so the reference is
                   provably fabricated -> block (ADR-0190, closes #867).
    'stale'     -> referenced ADR(s) absent from a non-empty cache (warn or, under
                   strict mode, block).
    """
    if not referenced:
        return "none"
    cache_known, cache_verified, cache = _load_adr_cache()
    if not cache_known:
        return "ok"  # cannot validate offline / pre-migration -> fail-open
    if not cache:
        # ADR-0172: known state, not unknown -- never fail-open silently.
        # ADR-0190: `refreshed_at` says which of the two known states this is.
        return "empty" if cache_verified else "bootstrap"
    if referenced & cache:
        return "ok"
    return "stale"


def _bootstrap_cache_message(referenced: set[str]) -> str:
    ids = ", ".join(f"ADR-{r}" for r in sorted(referenced))
    return (
        f"references {ids}, but docs/adr/.adr-cache.json reports zero ADRs and "
        f"has never been refreshed. Run `cornerstone adr cache --refresh`, or "
        f'this may be the first ADR -- create it with `cornerstone adr new "<title>"` '
        f"(ADR-0172)."
    )


def _empty_cache_message(referenced: set[str]) -> str:
    ids = ", ".join(f"ADR-{r}" for r in sorted(referenced))
    return (
        f"ADR MANDATE BLOCKED: {ids} does not exist.\n\n"
        f"docs/adr/.adr-cache.json was refreshed from GitHub Discussions and "
        f"reports ZERO ADRs, so this reference cannot resolve to anything.\n"
        f'  1. Create the first ADR: `cornerstone adr new "<title>"`, then retry\n'
        f"  2. If ADRs do exist upstream, re-sync the index: "
        f"`cornerstone adr cache --refresh`\n\n"
        f"Typed bypasses (logged to {_LOG_FILE}):\n"
        f"  [skip-adr: trivial]      -- formatting / lint, no design decision\n"
        f"  [skip-adr: no-decision]  -- purely mechanical change (ADR-0190)"
    )


# ---------------------------------------------------------------------------
# Decision builders
# ---------------------------------------------------------------------------


def _allow() -> dict:
    return {
        "decision": "allow",  # Gemini CLI
        "hookSpecificOutput": {  # Claude Code
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
    }


def _deny(file_path: str, reason: str | None = None) -> dict:
    reason = reason or (
        f"ADR MANDATE BLOCKED\n\n"
        f"Modifying '{file_path}' requires an Architecture Decision Record.\n\n"
        f"ADRs live in GitHub Discussions (ADR-0128). Options:\n"
        f"  1. Include '# ADR: NNNN' in your edit (an existing ADR Discussion)\n"
        f'  2. Create one first: `cornerstone adr new "<title>"`, then retry\n\n'
        f"Typed bypasses (include verbatim in your message):\n"
        f"  [skip-adr: trivial]            -- formatting / lint, no design decision\n"
        f"  [skip-adr: covered-by:NNNN]    -- ADR-NNNN already covers this change\n"
        f"  [skip-adr: no-decision]         -- purely mechanical change\n"
    )
    return {
        "decision": "deny",  # Gemini CLI
        "reason": reason,  # Gemini CLI
        "hookSpecificOutput": {  # Claude Code
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def _stale_message(referenced: set[str]) -> str:
    ids = ", ".join(f"ADR-{n}" for n in sorted(referenced))
    return (
        f"ADR cache miss: {ids} not in {_ADR_PATH}/{_CACHE_FILE}. "
        f"Run `cornerstone adr cache --refresh` to pull the latest ADR index."
    )


# ---------------------------------------------------------------------------
# Pre-commit mode helpers
# ---------------------------------------------------------------------------


def _get_staged_guarded_files() -> "list[str] | None":
    """Return staged files subject to the ADR mandate, or None if git failed."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.splitlines()
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return None


def _has_bypass_in_diff(staged: list[str]) -> bool:
    """True if staged diff content contains a typed bypass token."""
    try:
        diff = subprocess.run(  # nosec B603, B607
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        bypass_match = _BYPASS_RE.search(diff.stdout)
        if bypass_match:
            _log_bypass(bypass_match.group(1).lower(), ",".join(staged))
            return True
        return False
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return False


def _staged_annotated_ids(files: list[str]) -> set[str]:
    """Collect ADR ids annotated in any guarded staged file."""
    ids: set[str] = set()
    for f in files:
        if not _needs_adr(f):
            continue
        try:
            content = Path(f).read_text(encoding="utf-8", errors="ignore")
            ids |= _annotated_adrs(content)
        except (OSError, ValueError):
            pass
    return ids


# ---------------------------------------------------------------------------
# Pre-commit mode
# ---------------------------------------------------------------------------


def _staged_change_is_trivial(staged: list[str]) -> bool:
    """ADR-0124 (pre-commit): single guarded file with a small/cosmetic diff."""
    guarded = [f for f in staged if _needs_adr(f)]
    if len(guarded) != 1:
        return False
    try:
        diff = subprocess.run(  # nosec B603, B607
            ["git", "diff", "--cached", "--unified=0", "--", guarded[0]],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if diff.returncode != 0:
            return False
        changed = [
            line
            for line in diff.stdout.splitlines()
            if (line.startswith("+") and not line.startswith("+++"))
            or (line.startswith("-") and not line.startswith("---"))
        ]
        if len(changed) < _SMALL_EDIT_MAX_CHANGED_LINES:
            return True
        return all(
            not line[1:].strip() or line[1:].strip().startswith(("#", "//"))
            for line in changed
        )
    except Exception:  # nosec B110  # noqa: BLE001 — failsafe: gate must not block the developer's commit/session
        return False


def _precommit_check() -> int:
    """Pre-commit mode: exit 0 if ADR mandate is satisfied, 1 if not."""
    if _on_exempt_branch():
        return 0

    staged = _get_staged_guarded_files()
    if staged is None or not any(_needs_adr(f) for f in staged):
        return 0

    if _staged_change_is_trivial(staged):  # ADR-0124
        return 0

    if _has_bypass_in_diff(staged):
        return 0

    referenced = _staged_annotated_ids(staged)
    verdict = _classify_reference(referenced)
    if verdict == "ok":
        return 0
    if verdict == "empty":  # ADR-0190: refreshed index, zero ADRs -> fabricated
        print(f"ADR MANDATE: {_empty_cache_message(referenced)}", file=sys.stderr)
        return 1
    if verdict == "bootstrap":
        if _STRICT:
            print(
                f"ADR MANDATE: {_bootstrap_cache_message(referenced)}", file=sys.stderr
            )
            return 1
        _log_bypass("empty-cache", ",".join(staged))
        print(
            f"[WARN] {_bootstrap_cache_message(referenced)} (allowed)", file=sys.stderr
        )
        return 0
    if verdict == "stale":
        if _STRICT:
            print(f"ADR MANDATE: {_stale_message(referenced)}", file=sys.stderr)
            return 1
        print(f"[WARN] {_stale_message(referenced)} (allowed)", file=sys.stderr)
        return 0

    branch = _current_branch()
    print(
        f"ADR MANDATE: staged files on '{branch}' require an ADR (ADR-0128/0129).\n"
        f"  Option 1: Add '# ADR: NNNN' to the files being changed.\n"
        f'  Option 2: Create one: `cornerstone adr new "<title>"`.\n'
        f"  Typed bypasses: [skip-adr: trivial] | [skip-adr: covered-by:NNNN] | [skip-adr: no-decision]",
        file=sys.stderr,
    )
    return 1


# ---------------------------------------------------------------------------
# Main hook logic
# ---------------------------------------------------------------------------


def _decision_for_verdict(verdict: str, file_path: str, referenced: set[str]) -> dict:
    """Map an offline-cache classification to a permissionDecision (ADR-0129/0190).

    Extracted verbatim from ``run``'s tail so the caller stays under the
    cognitive-complexity gate (ADR-0022, #913/#838). The branch order is preserved
    exactly: it is behavioral, not cosmetic (the first matching verdict wins), and
    the bootstrap/stale allowances stay fail-open unless ``_STRICT``.
    """
    # ADR: 0022
    if verdict == "ok":
        return _allow()
    if verdict == "empty":  # ADR-0190: refreshed index, zero ADRs -> fabricated
        return _deny(file_path, reason=_empty_cache_message(referenced))
    if verdict == "bootstrap":
        if _STRICT:
            return _deny(file_path, reason=_bootstrap_cache_message(referenced))
        _log_bypass("empty-cache", file_path)
        print(
            f"[WARN] {_bootstrap_cache_message(referenced)} (allowed)", file=sys.stderr
        )
        return _allow()
    if verdict == "stale":
        if _STRICT:
            return _deny(file_path, reason=_stale_message(referenced))
        print(f"[WARN] {_stale_message(referenced)} (allowed)", file=sys.stderr)
        return _allow()

    return _deny(file_path)


def run(raw: str = "") -> dict:
    """Evaluate the hook payload and return a permissionDecision."""
    if not raw:
        raw = _read_stdin()

    file_path, post_content, pre_content = _parse_payload(raw)

    # (d) Typed bypass -- strict format prevents accidental envelope matches
    bypass_match = _BYPASS_RE.search(raw)
    if bypass_match:
        _log_bypass(bypass_match.group(1).lower(), file_path)
        return _allow()

    # (e) Exempt branch (hotfix/*)
    if _on_exempt_branch():
        return _allow()

    if not _needs_adr(file_path):
        return _allow()

    # Read existing file content (managed-copy sniff + annotation check)
    disk_content = ""
    try:
        disk_content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        pass

    # ADR-0155: scaffolded copies are owned upstream — deny before the trivial
    # allowance, or local drift silently diverges from the template.
    if _is_managed_copy(disk_content) and _is_generated_project():
        return _deny(file_path, reason=_managed_message(file_path))

    # (f) ADR-0124: trivial edit (cosmetic, or small single-file diff)
    if _is_trivial_edit(pre_content, post_content):
        return _allow()

    # (a/b/c) Validate the referenced ADR against the offline cache (ADR-0129)
    referenced = _annotated_adrs(disk_content + "\n" + post_content)
    verdict = _classify_reference(referenced)
    return _decision_for_verdict(verdict, file_path, referenced)


def main() -> int:
    if "--pre-commit" in sys.argv:
        return _precommit_check()

    arguments_env = os.environ.get("ARGUMENTS", "")
    gemini_mode = bool(arguments_env)
    raw = arguments_env or _read_stdin()
    result = run(raw)

    # Each CLI only tolerates its own fields at the root level.
    if gemini_mode:
        output = {k: v for k, v in result.items() if k in ("decision", "reason")}
    else:
        output = {k: v for k, v in result.items() if k == "hookSpecificOutput"}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
