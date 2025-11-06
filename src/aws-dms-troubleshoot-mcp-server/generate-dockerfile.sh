#!/bin/bash
# Script to regenerate Dockerfile using cookiecutter CLI
# This works with the proper cookiecutter template structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Generating Dockerfile using cookiecutter..."

# Use cookiecutter CLI to generate from the template
cookiecutter .cookiecutter-template \
    --no-input \
    --output-dir /tmp/cookiecutter-output \
    --overwrite-if-exists

# Copy the generated Dockerfile to current directory
PROJECT_NAME=$(python3 -c "import json; print(json.load(open('.cookiecutter-template/cookiecutter.json'))['project_name'])")
cp "/tmp/cookiecutter-output/${PROJECT_NAME}/Dockerfile" ./Dockerfile

# Cleanup
rm -rf "/tmp/cookiecutter-output/${PROJECT_NAME}"

echo "✓ Dockerfile successfully generated!"
echo ""
echo "Next steps:"
echo "  1. Review the generated Dockerfile"
echo "  2. Test with: docker build -t aws-dms-troubleshoot-mcp-server:test ."
echo "  3. Commit if successful"