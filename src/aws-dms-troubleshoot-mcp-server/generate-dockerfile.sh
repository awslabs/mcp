#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
