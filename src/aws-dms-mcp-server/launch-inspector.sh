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

# Launch MCP Inspector for AWS DMS MCP Server
# This script sets up the environment and launches the MCP Inspector v0.17.0
# to connect to the AWS DMS MCP Server

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AWS DMS MCP Server - Inspector Launcher${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Set AWS Configuration
# Default to us-east-1, but can be overridden by environment
export AWS_REGION="${AWS_REGION:-us-east-1}"

# Set DMS Server Configuration
export DMS_READ_ONLY_MODE="${DMS_READ_ONLY_MODE:-false}"
export DMS_LOG_LEVEL="${DMS_LOG_LEVEL:-INFO}"
export DMS_DEFAULT_TIMEOUT="${DMS_DEFAULT_TIMEOUT:-300}"
export DMS_ENABLE_STRUCTURED_LOGGING="${DMS_ENABLE_STRUCTURED_LOGGING:-true}"

# Display Configuration
echo -e "${YELLOW}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Read-Only Mode: $DMS_READ_ONLY_MODE"
echo "  Log Level: $DMS_LOG_LEVEL"
echo "  Timeout: $DMS_DEFAULT_TIMEOUT seconds"
echo ""

# Check for AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$AWS_PROFILE" ]; then
    echo -e "${YELLOW}Warning: AWS credentials not found in environment${NC}"
    echo "  Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or"
    echo "  Set AWS_PROFILE, or"
    echo "  Run 'aws configure' to set up default credentials"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at .venv/${NC}"
    echo "Please create it first:"
    echo "  cd SampleCode"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js first:"
    echo "  brew install node  # macOS"
    echo "  Or visit: https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}Launching MCP Inspector v0.17.0...${NC}"
echo ""
echo "The web interface will open automatically at:"
echo "  http://localhost:5173"
echo ""
echo "Available tools (13):"
echo "  - describe_replication_instances"
echo "  - create_replication_instance"
echo "  - describe_endpoints"
echo "  - create_endpoint"
echo "  - delete_endpoint"
echo "  - test_connection"
echo "  - describe_connections"
echo "  - describe_replication_tasks"
echo "  - create_replication_task"
echo "  - start_replication_task"
echo "  - stop_replication_task"
echo "  - describe_table_statistics"
echo "  - reload_replication_tables"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the inspector${NC}"
echo ""

# Launch MCP Inspector with the DMS MCP Server
# Set PYTHONPATH to include current directory for module resolution
PYTHONPATH=. npx @modelcontextprotocol/inspector@0.17.0 \
  .venv/bin/python \
  -m awslabs.aws_dms_mcp_server.server
