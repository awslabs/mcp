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

# Health check script for CloudWAN MCP Server Docker container

set -e

# Check if the Python module can be imported
echo "Checking CloudWAN MCP Server import..."
uv run python -c "import awslabs.cloudwan_mcp_server; print('✅ Import successful')" || {
    echo "❌ Failed to import CloudWAN MCP Server"
    exit 1
}

# Test basic server functionality
echo "Testing server basic functionality..."
timeout 10s uv run python -c "
import asyncio
import sys
try:
    from awslabs.cloudwan_mcp_server.server import main
    print('✅ Server module loaded successfully')
    sys.exit(0)
except Exception as e:
    print(f'❌ Server health check failed: {e}')
    sys.exit(1)
" || {
    echo "❌ Server health check timed out or failed"
    exit 1
}

echo "✅ CloudWAN MCP Server health check passed"
exit 0
