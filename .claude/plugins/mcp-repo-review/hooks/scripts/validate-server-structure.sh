#!/bin/bash
# Validates basic MCP server directory structure.
# Usage: validate-server-structure.sh <server-dir>
# Exit code = number of errors found.

set -euo pipefail

SERVER_DIR="${1:?Usage: validate-server-structure.sh <server-dir>}"
ERRORS=0

check_exists() {
    local path="$1"
    local label="$2"
    if [ ! -e "$path" ]; then
        echo "MISSING: $label ($path)"
        ERRORS=$((ERRORS + 1))
    fi
}

check_exists "$SERVER_DIR/pyproject.toml" "pyproject.toml"
check_exists "$SERVER_DIR/README.md" "README.md"
check_exists "$SERVER_DIR/LICENSE" "LICENSE"
check_exists "$SERVER_DIR/awslabs" "awslabs/ package directory"
check_exists "$SERVER_DIR/tests" "tests/ directory"

if [ "$ERRORS" -eq 0 ]; then
    echo "OK: $SERVER_DIR"
fi

exit "$ERRORS"
