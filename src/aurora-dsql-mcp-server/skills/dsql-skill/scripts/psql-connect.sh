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

# psql-connect.sh - Connect to Aurora DSQL using psql with IAM auth
#
# Usage: ./psql-connect.sh [CLUSTER_ID] [--region REGION] [--user USER] [--admin] [--command "SQL"]
#
# Examples:
#   ./psql-connect.sh
#   ./psql-connect.sh abc123def456 --region us-west-2
#   ./psql-connect.sh --user myuser
#   ./psql-connect.sh --admin
#   ./psql-connect.sh --command "SELECT * FROM entities LIMIT 5"

CLUSTER_ID="${CLUSTER:-}"
REGION="${REGION:-${AWS_REGION:-us-east-1}}"
USER="${DB_USER:-admin}"
ADMIN=false
COMMAND=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      REGION="$2"
      shift 2
      ;;
    --user)
      USER="$2"
      shift 2
      ;;
    --admin)
      ADMIN=true
      shift
      ;;
    --command|-c)
      COMMAND="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [CLUSTER_ID] [--region REGION] [--user USER] [--admin] [--command SQL]"
      echo ""
      echo "Connect to Aurora DSQL using psql with IAM authentication."
      echo ""
      echo "Arguments:"
      echo "  CLUSTER_ID         Cluster identifier (default: \$CLUSTER env var)"
      echo ""
      echo "Options:"
      echo "  --region REGION    AWS region (default: \$REGION or \$AWS_REGION or us-east-1)"
      echo "  --user USER        Database user (default: \$DB_USER or 'admin')"
      echo "  --admin            Generate admin token (uses generate-db-connect-admin-auth-token)"
      echo "  --command SQL      Execute SQL command and exit"
      echo "  -h, --help         Show this help message"
      echo ""
      echo "Environment Variables:"
      echo "  CLUSTER            Default cluster identifier"
      echo "  REGION             Default AWS region"
      echo "  DB_USER            Default database user"
      exit 0
      ;;
    -*)
      echo "Unknown option: $1"
      exit 1
      ;;
    *)
      CLUSTER_ID="$1"
      shift
      ;;
  esac
done

# Validate cluster ID
if [[ -z "$CLUSTER_ID" ]]; then
  echo "Error: CLUSTER_ID is required. Set \$CLUSTER env var or pass as argument."
  echo ""
  echo "Usage: $0 CLUSTER_ID [options]"
  echo "   or: export CLUSTER=abc123 && $0 [options]"
  exit 1
fi

# Build endpoint
ENDPOINT="${CLUSTER_ID}.dsql.${REGION}.on.aws"

# Generate auth token
echo "Generating IAM auth token for $ENDPOINT..." >&2

if [[ "$ADMIN" == "true" ]]; then
  TOKEN=$(aws dsql generate-db-connect-admin-auth-token \
    --hostname "$ENDPOINT" \
    --region "$REGION")
else
  TOKEN=$(aws dsql generate-db-connect-auth-token \
    --hostname "$ENDPOINT" \
    --region "$REGION")
fi

# Check if token generation was successful
if [[ -z "$TOKEN" ]]; then
  echo "Error: Failed to generate auth token. Check your AWS credentials." >&2
  exit 1
fi

echo "Connecting to $ENDPOINT as $USER..." >&2
echo "" >&2

# Connect with psql
if [[ -n "$COMMAND" ]]; then
  # Execute command and exit
  PGPASSWORD="$TOKEN" psql \
    -h "$ENDPOINT" \
    -U "$USER" \
    -d postgres \
    -c "$COMMAND"
else
  # Interactive session
  PGPASSWORD="$TOKEN" psql \
    -h "$ENDPOINT" \
    -U "$USER" \
    -d postgres
fi
