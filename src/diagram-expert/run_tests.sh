#!/bin/bash
# Script to run the diagram-expert MCP server tests

# Set the Python path to include the current directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing pytest and dependencies..."
    # Check if uv is available
    if command -v uv &> /dev/null; then
        uv pip install pytest pytest-asyncio pytest-cov
    # Check if pip is available
    elif command -v pip &> /dev/null; then
        pip install pytest pytest-asyncio pytest-cov
    else
        echo "Error: Neither uv nor pip is available. Please install pytest manually."
        exit 1
    fi
fi

# Run the tests
echo "Running tests..."
pytest -xvs tests/

# If you want to run with coverage, uncomment the following line
# pytest --cov=ai3_diagrams_expert --cov-report=term-missing tests/

# If you want to run with coverage and generate an HTML report, uncomment the following line
# pytest --cov=ai3_diagrams_expert --cov-report=html tests/
