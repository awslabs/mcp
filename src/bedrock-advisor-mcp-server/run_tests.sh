#!/bin/bash
# Run tests with coverage

set -e

# Run pytest with coverage
python -m pytest tests/ --cov=awslabs.bedrock_advisor_mcp_server --cov-report=term-missing
