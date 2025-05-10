#!/bin/bash

# Exit on error
set -e

echo "========================================================"
echo "Running tests for git-repo-research-mcp-server"
echo "========================================================"

# Install dependencies if not already installed
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    uv sync --frozen --all-extras --dev
else
    echo "Using existing virtual environment"
fi

# Activate the virtual environment
source .venv/bin/activate

# Run the tests with coverage
echo "Running tests with coverage..."
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing

echo "Tests completed successfully!"
