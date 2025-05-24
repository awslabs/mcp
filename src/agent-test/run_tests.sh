#!/bin/bash
# Simple script to test agent-test implementation

# Parse command-line arguments
RUN_INTEG=false
for arg in "$@"; do
  case $arg in
  --integ)
    RUN_INTEG=true
    shift
    ;;
  esac
done

# Install dependencies using uv
echo "Installing dependencies..."
cd "$(dirname "$0")"

# Create virtual env with uv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv
fi

# Install the package and its dependencies
echo "Installing package dependencies..."
uv sync --all-groups

# Run tests based on requested type
if [ "$RUN_INTEG" = true ]; then
  echo "Running integration tests..."
  uv run pytest integ_tests/test_agent_tools.py -v
else
  echo "Running unit tests..."
  uv run pytest tests/test_yaml_loading.py -v
  # Note: test_agent_tools.py moved to integ_tests/ directory
fi
