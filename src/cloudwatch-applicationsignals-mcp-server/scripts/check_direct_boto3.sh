#!/usr/bin/env bash
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
