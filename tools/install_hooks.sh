#!/usr/bin/env bash
# MANAGED BY CORNERSTONE (ADR-0155). In generated projects this file is a
# scaffolded copy: do not edit it there — change the canonical source in the
# cornerstone repo (schematics, per ADR-0159 Decision 1) and propagate with
# `cornerstone update`.
# ADR: 0020
# install_hooks.sh — Install Cornerstone git hooks into .git/hooks/
#
# Run once after cloning or generating the project:
#   bash tools/install_hooks.sh
#
# Hooks installed:
#   commit-msg   — ADR gate: blocks commits that modify library source
#                  code without a new ADR file staged alongside.
#   post-commit  — Auto SemVer bump (ADR-0020): parses the Conventional Commit
#                  type of the commit just made, bumps pyproject.toml +
#                  CHANGELOG.md, and folds the bump INTO that same commit via an
#                  amend (recursion-guarded). Runs post-commit so the amend is
#                  safe (the index lock is already released). This is why a lone
#                  `feat:` commit no longer fails the CI Semver Gate.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "[cornerstone:hooks] ERROR: .git/hooks not found. Is this a git repository?" >&2
  exit 1
fi

# ── pre-commit framework ──────────────────────────────────────────────────────
if command -v pre-commit &> /dev/null; then
    pre-commit install || true
    echo "[cornerstone:hooks] Installed pre-commit framework hooks."
fi

# ── commit-msg (ADR gate) ─────────────────────────────────────────────────────
COMMIT_MSG_HOOK="$HOOKS_DIR/commit-msg"

CORNERSTONE_BANNER="# cornerstone:adr-gate"

HOOK_BODY='#!/usr/bin/env bash
# cornerstone:adr-gate — ADR gate commit-msg hook (DO NOT REMOVE THIS LINE)
# Blocks commits that modify guarded library source without a new ADR staged.
# Installed by tools/install_hooks.sh — re-run to update.
set -euo pipefail

COMMIT_MSG_FILE=$1
STAGED=$(git diff --cached --name-only 2>/dev/null || true)
NEW_FILES=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)
COMMIT_MSG=""
if [[ -n "${COMMIT_MSG_FILE:-}" ]] && [[ -f "$COMMIT_MSG_FILE" ]]; then
  COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")
fi

cornerstone adr-gate \
  --changed-files "$STAGED" \
  --new-files     "$NEW_FILES" \
  --commit-message "$COMMIT_MSG"'

if [[ -f "$COMMIT_MSG_HOOK" ]]; then
  if grep -q "cornerstone:adr-gate" "$COMMIT_MSG_HOOK" 2>/dev/null; then
    # Already installed by Cornerstone — overwrite safely (update in place)
    echo "$HOOK_BODY" > "$COMMIT_MSG_HOOK"
    chmod +x "$COMMIT_MSG_HOOK"
    echo "[cornerstone:hooks] Updated existing Cornerstone hook: $COMMIT_MSG_HOOK"
  else
    # A non-Cornerstone hook exists — append a call rather than overwriting
    echo "" >> "$COMMIT_MSG_HOOK"
    echo "# --- BEGIN cornerstone:adr-gate (appended by install_hooks.sh) ---" >> "$COMMIT_MSG_HOOK"
    echo 'COMMIT_MSG_FILE=$1' >> "$COMMIT_MSG_HOOK"
    echo 'STAGED=$(git diff --cached --name-only 2>/dev/null || true)' >> "$COMMIT_MSG_HOOK"
    echo 'NEW_FILES=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)' >> "$COMMIT_MSG_HOOK"
    echo 'COMMIT_MSG=""' >> "$COMMIT_MSG_HOOK"
    echo 'if [[ -n "${COMMIT_MSG_FILE:-}" ]] && [[ -f "$COMMIT_MSG_FILE" ]]; then COMMIT_MSG=$(cat "$COMMIT_MSG_FILE"); fi' >> "$COMMIT_MSG_HOOK"
    echo 'cornerstone adr-gate --changed-files "$STAGED" --new-files "$NEW_FILES" --commit-message "$COMMIT_MSG"' >> "$COMMIT_MSG_HOOK"
    echo "# --- END cornerstone:adr-gate ---" >> "$COMMIT_MSG_HOOK"
    echo "[cornerstone:hooks] Appended ADR gate to existing hook: $COMMIT_MSG_HOOK"
    echo "[cornerstone:hooks] WARNING: existing hook was preserved — verify merged behavior."
  fi
else
  echo "$HOOK_BODY" > "$COMMIT_MSG_HOOK"
  chmod +x "$COMMIT_MSG_HOOK"
  echo "[cornerstone:hooks] Installed: $COMMIT_MSG_HOOK"
fi

# ── post-commit (auto SemVer bump, ADR-0020) ──────────────────────────────────
# A commit-msg hook cannot land its own `git add` in the current commit (the tree
# is already snapshotted), so the bump would leak into the NEXT commit and a lone
# feat: would fail the Semver Gate. Running as post-commit (lock released) and
# amending folds the bump into the just-made commit. Recursion-guarded via
# CORNERSTONE_SEMVER_AMENDING; the amend uses --no-verify so gates don't re-run.
POST_COMMIT_HOOK="$HOOKS_DIR/post-commit"
POST_COMMIT_BODY='#!/usr/bin/env bash
# cornerstone:semver-bump — auto SemVer bump post-commit hook (DO NOT REMOVE THIS LINE)
# Installed by tools/install_hooks.sh — re-run to update. ADR-0020.
set -euo pipefail
[ -n "${CORNERSTONE_SEMVER_AMENDING:-}" ] && exit 0
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
[ -f "$ROOT/tools/bump_version.py" ] || exit 0
MSGF="$(mktemp)"; git log -1 --format=%B > "$MSGF"
python3 "$ROOT/tools/bump_version.py" "$MSGF" || true
rm -f "$MSGF"
if ! git diff --cached --quiet; then
  CORNERSTONE_SEMVER_AMENDING=1 git commit --amend --no-edit --no-verify >/dev/null
fi'

if [[ -f "$POST_COMMIT_HOOK" ]] && ! grep -q "cornerstone:semver-bump" "$POST_COMMIT_HOOK" 2>/dev/null; then
  echo "" >> "$POST_COMMIT_HOOK"
  echo "$POST_COMMIT_BODY" | tail -n +2 >> "$POST_COMMIT_HOOK"
  echo "[cornerstone:hooks] Appended semver-bump to existing hook: $POST_COMMIT_HOOK"
else
  echo "$POST_COMMIT_BODY" > "$POST_COMMIT_HOOK"
  chmod +x "$POST_COMMIT_HOOK"
  echo "[cornerstone:hooks] Installed: $POST_COMMIT_HOOK"
fi

echo "[cornerstone:hooks] ADR gate + auto SemVer bump will run on every commit."
