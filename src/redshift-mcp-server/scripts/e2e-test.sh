#!/usr/bin/env bash
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

# End-to-end test for the Redshift MCP Server tools, driven via kiro-cli.
# Run from the package root before raising a PR:  ./scripts/e2e-test.sh
set -euo pipefail

MODEL="${MODEL:-claude-opus-4.8}"
REQUEST_FILE="$(mktemp)"
trap 'rm -f "$REQUEST_FILE"' EXIT

cat > "$REQUEST_FILE" <<'EOF'
Test if all the Redshift MCP Server tools available to you are working. Check both
provisioned and serverless clusters, including database schema exploration in both.
Check the SQL read-only protection, transaction breaker protection, and failed user
SQL behavior. Test the new tool describe_execution_plan and return the explain result.
Also, check BaseSchema regarding optimization of token usage.
Get test scenario ideas from the unit tests under the project directory. Provide a
short testing summary, one line per tool.
EOF

kiro-cli chat --model "$MODEL" \
  --no-interactive \
  --trust-tools "@{awslabsredshift-mcp-server}/*,execute_bash,fs_read" \
  "$(cat "$REQUEST_FILE")"
