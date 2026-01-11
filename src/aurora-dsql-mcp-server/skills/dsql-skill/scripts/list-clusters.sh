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

# list-clusters.sh - List all Aurora DSQL clusters
#
# Usage: ./list-clusters.sh [--region REGION]
#
# Examples:
#   ./list-clusters.sh
#   ./list-clusters.sh --region us-west-2

REGION="${AWS_REGION:-us-east-1}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      REGION="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--region REGION]"
      echo ""
      echo "List all Aurora DSQL clusters in the specified region."
      echo ""
      echo "Options:"
      echo "  --region REGION    AWS region (default: \$AWS_REGION or us-east-1)"
      echo "  -h, --help         Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Listing Aurora DSQL clusters in $REGION..."
echo ""

# List clusters
aws dsql list-clusters --region "$REGION" --output table

echo ""
echo "To get details about a cluster:"
echo "./scripts/cluster-info.sh CLUSTER_IDENTIFIER"
