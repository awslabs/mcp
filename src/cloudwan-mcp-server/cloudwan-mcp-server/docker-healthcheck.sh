#!/bin/bash

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