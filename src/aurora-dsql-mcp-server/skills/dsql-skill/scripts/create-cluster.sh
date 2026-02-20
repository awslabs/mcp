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
set -euo pipefail

# create-cluster.sh - Create an Aurora DSQL cluster
#
# Usage: ./create-cluster.sh [--region REGION] [--tags KEY=VALUE,...]
#
# Examples:
#   ./create-cluster.sh
#   ./create-cluster.sh --region us-east-1
#   ./create-cluster.sh --region us-west-2 --tags Environment=dev,Project=myapp

REGION="${AWS_REGION:-us-east-1}"
TAGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      REGION="$2"
      shift 2
      ;;
    --tags)
      TAGS="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--region REGION] [--tags KEY=VALUE,...]"
      echo ""
      echo "Creates an Aurora DSQL cluster in the specified region."
      echo ""
      echo "Options:"
      echo "  --region REGION    AWS region (default: \$AWS_REGION or us-east-1)"
      echo "  --tags TAGS        Comma-separated tags (e.g., Env=dev,Project=app)"
      echo "  -h, --help         Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Creating Aurora DSQL cluster in $REGION..."

# Build the AWS CLI command as an array to avoid eval and shell injection
CMD=(aws dsql create-cluster --region "$REGION")

# Add tags if provided
if [[ -n "$TAGS" ]]; then
  # Convert comma-separated tags to JSON format using jq for safe escaping
  TAG_JSON=$(printf '%s\n' "$TAGS" | tr ',' '\n' | jq -Rn '
    [inputs | split("=") | {(.[0]): .[1:] | join("=")}] | add // {}
  ')
  CMD+=(--tags "$TAG_JSON")
fi

# Execute the command directly (no eval)
"${CMD[@]}" > /tmp/dsql-cluster-create.json

# Extract cluster identifier and endpoint
CLUSTER_ID=$(jq -r '.identifier' /tmp/dsql-cluster-create.json)
CLUSTER_ENDPOINT="${CLUSTER_ID}.dsql.${REGION}.on.aws"
CLUSTER_ARN=$(jq -r '.arn' /tmp/dsql-cluster-create.json)

echo ""
echo "✓ Cluster created successfully!"
echo ""
echo "Cluster Identifier: $CLUSTER_ID"
echo "Cluster Endpoint:   $CLUSTER_ENDPOINT"
echo "Cluster ARN:        $CLUSTER_ARN"
echo "Region:             $REGION"
echo ""
echo "Export these environment variables to use with MCP:"
echo ""
echo "export CLUSTER=$CLUSTER_ID"
echo "export REGION=$REGION"
echo ""
echo "To connect with psql:"
echo "./scripts/psql-connect.sh"

# Clean up temp file
rm /tmp/dsql-cluster-create.json
