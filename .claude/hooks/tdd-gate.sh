#!/bin/bash
# tdd-gate.sh — TDD/BDD gate for hexagonal + BDD-first architectures
# Adapted from pm-workspace / davila7 for Deacero schematics.
# Primary: BDD feature file covering the domain.
# Secondary: test file with broad name matching (test_project_service.py → service.py).
# Blocks editing production code when neither check passes.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=""

case "$TOOL" in
  Edit|MultiEdit|Write) FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty') ;;
  *) exit 0 ;;
esac

[ -z "$FILE_PATH" ] && exit 0

EXT="${FILE_PATH##*.}"
case "$EXT" in
  py|ts|tsx|js|jsx|go|rs|rb|php|java|kt|swift|dart|cs) ;;
  *) exit 0 ;;
esac

BASENAME=$(basename "$FILE_PATH")
NAME_NO_EXT="${BASENAME%.*}"

# Skip names that are too generic or infrastructure to gate
case "$BASENAME" in
  *[Tt]est*|*[Ss]pec*|conftest*) exit 0 ;;
  __init__*|server*|app*|main*|settings*|config*) exit 0 ;;
  types*|exceptions*|constants*|errors*|enums*) exit 0 ;;
  *[Mm]igration*|*.dto*|env*) exit 0 ;;
  *.d.ts|tsconfig*|*.config.ts|*.config.js) exit 0 ;;
esac

# Skip by path pattern
case "$FILE_PATH" in
  */test*|*/spec*|*/fixture*|*/mock*|*/stub*|*/fake*) exit 0 ;;
  */migration*|*/seed*|*/alembic*|*/versions/*) exit 0 ;;
  */config*|*/scripts*|*/infra*|*/ports*) exit 0 ;;
  */node_modules*|*/.venv*|*/dist*|*/build*) exit 0 ;;
esac

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
PARENT_DIR=$(basename "$(dirname "$FILE_PATH")")

# 1. BDD feature file covering this domain (match by parent dir name, then module name)
FEATURE_FOUND=$(find "$PROJECT_ROOT/tests/features" "$PROJECT_ROOT/features" \
  -maxdepth 2 -name "*.feature" 2>/dev/null | grep -iF "$PARENT_DIR" | head -1)

if [ -z "$FEATURE_FOUND" ] && [ "$NAME_NO_EXT" != "$PARENT_DIR" ]; then
  FEATURE_FOUND=$(find "$PROJECT_ROOT/tests/features" "$PROJECT_ROOT/features" \
    -maxdepth 2 -name "*.feature" 2>/dev/null | grep -iF "$NAME_NO_EXT" | head -1)
fi

[ -n "$FEATURE_FOUND" ] && exit 0

# 2. Test file: broad substring match (test_project_service.py covers service.py in projects/)
TESTS_FOUND=$(find "$PROJECT_ROOT/tests" "$PROJECT_ROOT/test" \
  -maxdepth 6 -type f \( -name "test_*" -o -name "*_test.*" \) 2>/dev/null | \
  grep -iF "$NAME_NO_EXT" | head -1)

[ -n "$TESTS_FOUND" ] && exit 0

# 3. Fallback: exact legacy patterns (Java / TypeScript conventions)
TESTS_FOUND=$(find "$PROJECT_ROOT" -maxdepth 7 -type f 2>/dev/null \( \
  -name "${NAME_NO_EXT}Test.${EXT}" \
  -o -name "${NAME_NO_EXT}Tests.${EXT}" \
  -o -name "${NAME_NO_EXT}.test.${EXT}" \
  -o -name "${NAME_NO_EXT}.spec.${EXT}" \
  \) | head -1)

[ -n "$TESTS_FOUND" ] && exit 0

# 4. All-words filename match: handles reversed naming (test_factory_mcp.py covers mcp_factory.py)
CANDIDATES=$(find "$PROJECT_ROOT/tests" "$PROJECT_ROOT/test" \
  -maxdepth 6 -type f \( -name "test_*" -o -name "*_test.*" \) 2>/dev/null)
for WORD in $(echo "$NAME_NO_EXT" | tr '_' ' '); do
  CANDIDATES=$(echo "$CANDIDATES" | grep -iF "$WORD")
  [ -z "$CANDIDATES" ] && break
done
[ -n "$CANDIDATES" ] && exit 0

# 5. Content-based fallback: test file that mentions this module by name
TESTS_FOUND=$(grep -rl "$NAME_NO_EXT" "$PROJECT_ROOT/tests" "$PROJECT_ROOT/test" \
  2>/dev/null | grep -iE "(test_|_test\.)" | head -1)
[ -n "$TESTS_FOUND" ] && exit 0

echo "TDD GATE: No test coverage found for '${BASENAME}'." >&2
echo "  Option A: BDD scenario  → tests/features/${PARENT_DIR}.feature" >&2
echo "  Option B: Unit test     → tests/unit/test_*${NAME_NO_EXT}*.${EXT}" >&2
exit 2
