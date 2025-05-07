#!/bin/bash
# Docker healthcheck script for the OpenAPI MCP Server

# Attempt to connect to the server's health endpoint
if curl -f http://localhost:${SERVER_PORT:-8888}/health > /dev/null 2>&1; then
    # Success - the server is responding
    exit 0
else
    # Failure - the server is not responding
    exit 1
fi
