#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# Script to run tests for the Terraform MCP Server

set -e

# Set the Python path to include the current directory and the parent directory
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/..

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: You are not running in a virtual environment."
    echo "It's recommended to create and activate a virtual environment before running tests."
    echo "You can create one with: python -m venv .venv"
    echo "And activate it with: source .venv/bin/activate (Linux/Mac) or .venv\\Scripts\\activate (Windows)"
    echo "Continuing without a virtual environment..."
    echo ""
fi

# Check if pytest and other dependencies are installed
echo "Checking for required packages..."
MISSING_PACKAGES=()

# Check for pytest and related packages
python -c "import pytest" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("pytest pytest-asyncio pytest-cov")
fi

# Check for pydantic package
python -c "import pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("pydantic")
fi

# Check for requests package
python -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("requests")
fi

# Check for loguru package
python -c "import loguru" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("loguru")
fi

# Check for beautifulsoup4 package
python -c "import bs4" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("beautifulsoup4")
fi

# Check for checkov package
python -c "import checkov" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_PACKAGES+=("checkov")
fi

# Install missing packages
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "Installing missing packages: ${MISSING_PACKAGES[*]}"

    # Try pip first (more reliable)
    if command -v pip &> /dev/null; then
        echo "Using pip to install packages..."
        pip install ${MISSING_PACKAGES[*]} -v
    # Try pip3 if pip is not available
    elif command -v pip3 &> /dev/null; then
        echo "Using pip3 to install packages..."
        pip3 install ${MISSING_PACKAGES[*]} -v
    # Try uv as a last resort
    elif command -v uv &> /dev/null; then
        echo "Using uv to install packages..."
        uv pip install ${MISSING_PACKAGES[*]} -v
    else
        echo "Error: No package manager (pip, pip3, or uv) is available. Please install the missing packages manually."
        exit 1
    fi

    # Verify installation with more verbose output
    echo "Verifying package installations..."
    for pkg in "pytest" "pydantic" "requests" "loguru" "bs4" "checkov"; do
        echo "Checking for $pkg..."
        python -c "import $pkg; print(f'$pkg installed successfully')" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "Failed to install $pkg. Trying to install it individually..."
            pip install $pkg -v || pip3 install $pkg -v || echo "Failed to install $pkg. Please install it manually."

            # Check again
            python -c "import $pkg" 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "Still failed to install $pkg. Please install it manually."
                echo "You can try: pip install $pkg"
                exit 1
            fi
        fi
    done
fi

# Print debug information
echo "Debug information:"
echo "Python version: $(python --version)"
echo "Python path: $PYTHONPATH"
echo "Current directory: $(pwd)"
echo "Python executable: $(which python)"
echo "Pytest module location: $(python -c "import pytest; print(pytest.__file__)" 2>/dev/null || echo "Not found")"

# Check if terraform_mcp_server module can be imported
echo "Checking if terraform_mcp_server module can be imported..."
python -c "import awslabs.terraform_mcp_server; print('terraform_mcp_server module found')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Warning: terraform_mcp_server module cannot be imported. This may cause test failures."
    echo "Installing the package in development mode..."

    # Check if uv is available
    if command -v uv &> /dev/null; then
        uv pip install -e .
    # Check if pip is available
    elif command -v pip &> /dev/null; then
        pip install -e .
    else
        echo "Neither uv nor pip is available. Creating a symbolic link instead..."
        # Create a symbolic link to the module in the current directory
        ln -sf $(pwd)/awslabs/terraform_mcp_server $(pwd)/terraform_mcp_server 2>/dev/null
    fi

    echo "Trying again..."
    python -c "import awslabs.terraform_mcp_server; print('terraform_mcp_server module found')" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Still cannot import terraform_mcp_server module. Tests may fail."
        echo "Directory structure:"
        ls -la
        echo "awslabs directory:"
        ls -la awslabs 2>/dev/null || echo "awslabs directory not found"
    fi
fi

# Parse command line arguments
COVERAGE=0
REPORT=0
VERBOSE=0
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --coverage)
      COVERAGE=1
      shift
      ;;
    --report)
      REPORT=1
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    *)
      SPECIFIC_TEST="$1"
      shift
      ;;
  esac
done

# Set up the command
CMD="python -m pytest"

if [ $VERBOSE -eq 1 ]; then
  CMD="$CMD -v"
fi

if [ $COVERAGE -eq 1 ]; then
  CMD="$CMD --cov=awslabs.terraform_mcp_server"

  if [ $REPORT -eq 1 ]; then
    CMD="$CMD --cov-report=html"
  fi
fi

if [ -n "$SPECIFIC_TEST" ]; then
  CMD="$CMD $SPECIFIC_TEST"
else
  CMD="$CMD tests/"
fi

# Run the tests
echo "Running: $CMD"
$CMD

# If coverage report was generated, print the path
if [ $COVERAGE -eq 1 ] && [ $REPORT -eq 1 ]; then
  echo "Coverage report generated in htmlcov/ directory"
  echo "Open htmlcov/index.html in your browser to view the report"
fi
