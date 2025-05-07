#!/bin/bash
# Run tests for the OpenAPI MCP Server

set -e  # Exit immediately if a command exits with a non-zero status

# Check if uv is installed
if command -v uv &> /dev/null; then
  echo "Running tests with uv..."
  uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
else
  echo "Running tests with pytest..."
  python -m pytest --cov=awslabs.openapi_mcp_server --cov-report=term --cov-report=html
fi

echo "Tests completed successfully!"
