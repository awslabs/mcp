#!/bin/bash
# Script to run the Prometheus MCP server with stdio transport

# Run the server with debug logging
python -m awslabs.prometheus_mcp_server.server --debug