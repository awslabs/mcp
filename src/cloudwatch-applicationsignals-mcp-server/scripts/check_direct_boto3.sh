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

# Checks that tool modules don't call boto3.client() or boto3.Session() directly.
# All AWS client creation must go through aws_clients.get_client().
set -euo pipefail

# Support running from repo root (pre-commit) or package directory (manual)
if [ -d "src/cloudwatch-applicationsignals-mcp-server/awslabs" ]; then
  PKG_DIR="src/cloudwatch-applicationsignals-mcp-server/awslabs/cloudwatch_applicationsignals_mcp_server"
elif [ -d "awslabs/cloudwatch_applicationsignals_mcp_server" ]; then
  PKG_DIR="awslabs/cloudwatch_applicationsignals_mcp_server"
else
  echo "ERROR: Cannot find package directory. Run from repo root or package directory."
  exit 1
fi

EXCLUDE="aws_clients.py"

violations=$(grep -rn 'boto3\.client\|boto3\.Session' "$PKG_DIR" --include='*.py' \
  | grep -v "$EXCLUDE" \
  | grep -v '__pycache__' || true)

if [ -n "$violations" ]; then
  echo "ERROR: Direct boto3.client()/boto3.Session() calls found outside $EXCLUDE:"
  echo "$violations"
  echo ""
  echo "Use get_client() from aws_clients.py instead."
  exit 1
fi

echo "OK: No direct boto3 calls found in tool modules."
