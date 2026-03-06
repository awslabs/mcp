#!/bin/sh

# Simple health check for MCP server
# Checks if the Python process is running

if pgrep -f "awslabs.mwaa_mcp_server" > /dev/null; then
    exit 0
else
    exit 1
fi