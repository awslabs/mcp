#!/bin/bash

# Check if the process is running
if ! pgrep -f "awslabs.valkey-mcp-server" > /dev/null; then
    echo "Process not running"
    exit 1
fi

# Check if the port is listening (default MCP server port is 8080)
if ! lsof -i :8080 -sTCP:LISTEN > /dev/null; then
    echo "Port 8080 not listening"
    exit 1
fi

# All checks passed
exit 0
