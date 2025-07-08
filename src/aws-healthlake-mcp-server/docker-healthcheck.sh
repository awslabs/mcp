#!/bin/bash

# Simple health check for the HealthLake MCP server
# This script checks if the server process is running

# Check if the Python process is running
if pgrep -f "awslabs.healthlake-mcp-server" > /dev/null; then
    echo "HealthLake MCP Server is running"
    exit 0
else
    echo "HealthLake MCP Server is not running"
    exit 1
fi
