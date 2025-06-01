#!/bin/sh
set -e

# Simple health check to verify the server is running
if pgrep -f "python -m awslabs.cost_explorer_mcp_server" > /dev/null; then
    exit 0
else
    exit 1
fi
