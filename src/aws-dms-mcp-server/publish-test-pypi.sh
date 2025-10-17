#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Publish AWS DMS MCP Server to Test PyPI
# This script builds and publishes the package to Test PyPI for testing before production release

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AWS DMS MCP Server - Test PyPI Publish${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for Test PyPI token
if [ -z "$TEST_PYPI_TOKEN" ]; then
    echo -e "${YELLOW}Warning: TEST_PYPI_TOKEN environment variable not set${NC}"
    echo "You can set it with:"
    echo "  export TEST_PYPI_TOKEN='your-token-here'"
    echo ""
    echo -e "${BLUE}Or you'll be prompted for credentials during publish${NC}"
    echo ""
fi

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info
echo "✓ Cleaned"
echo ""

# Run tests first
echo -e "${YELLOW}Running tests before publish...${NC}"
if .venv/bin/pytest tests/ -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR)"; then
    echo "✓ Tests completed"
else
    echo -e "${RED}Warning: Some tests may have failed${NC}"
    read -p "Continue with publish? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Publish cancelled"
        exit 1
    fi
fi
echo ""

# Build the package
echo -e "${YELLOW}Building package with uv...${NC}"
uv build
echo "✓ Package built"
echo ""

# List built packages
echo -e "${BLUE}Built packages:${NC}"
ls -lh dist/
echo ""

# Get version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${GREEN}Package version: ${VERSION}${NC}"
echo ""

# Publish to Test PyPI
echo -e "${YELLOW}Publishing to Test PyPI...${NC}"
echo ""

if [ -n "$TEST_PYPI_TOKEN" ]; then
    # Use token authentication
    uv publish \
        --index-url https://test.pypi.org/legacy/ \
        --token "$TEST_PYPI_TOKEN"
else
    # Interactive authentication
    uv publish \
        --index-url https://test.pypi.org/legacy/
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Publish Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Test your package with:"
echo -e "${YELLOW}  uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ awslabs.aws-dms-mcp-server@${VERSION}${NC}"
echo ""
echo "Or install it:"
echo -e "${YELLOW}  uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ awslabs.aws-dms-mcp-server==${VERSION}${NC}"
echo ""
echo -e "${BLUE}View on Test PyPI:${NC}"
echo "  https://test.pypi.org/project/awslabs.aws-dms-mcp-server/${VERSION}/"
