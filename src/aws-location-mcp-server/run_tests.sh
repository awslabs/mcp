#!/bin/bash
# Run tests for AWS Location Service MCP Server

set -e

# Change to the script directory
cd "$(dirname "$0")"

# Run pytest with coverage
python -m pytest tests/ -v --cov=awslabs --cov-report=term-missing
