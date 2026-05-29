#!/bin/bash
# Iterates all src/*-mcp-server/ directories and validates structure.
# Usage: check-all-servers.sh [repo-root]
# Prints a summary table of pass/fail per server.

set -uo pipefail

REPO_ROOT="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="$SCRIPT_DIR/../hooks/scripts/validate-server-structure.sh"

PASS=0
FAIL=0
FAILURES=""

for server_dir in "$REPO_ROOT"/src/*-mcp-server; do
    [ -d "$server_dir" ] || continue
    name="$(basename "$server_dir")"

    output=$("$VALIDATOR" "$server_dir" 2>&1) && {
        PASS=$((PASS + 1))
    } || {
        FAIL=$((FAIL + 1))
        FAILURES="${FAILURES}\n  ${name}: ${output}"
    }
done

echo "=== Server Structure Check ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
    echo -e "\nFailures:$FAILURES"
    exit 1
fi

exit 0
