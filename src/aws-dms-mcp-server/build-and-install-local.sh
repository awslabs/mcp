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

# Build and Install AWS DMS MCP Server to Local uvx
# This script builds the package and installs it locally using uvx

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AWS DMS MCP Server - Local Build${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info
echo "✓ Cleaned"
echo ""

# Clean UV cache
echo -e "${YELLOW}Cleaning UV cache...${NC}"
uv cache clean
echo "✓ UV cache cleaned"
echo ""

# Build the package
echo -e "${YELLOW}Building package with uv...${NC}"
uv build
echo "✓ Package built"
echo ""

# Get the wheel file
WHEEL_FILE=$(ls dist/*.whl | head -1)
if [ -z "$WHEEL_FILE" ]; then
    echo -e "${RED}Error: No wheel file found in dist/${NC}"
    exit 1
fi

echo -e "${GREEN}Wheel file created: ${WHEEL_FILE}${NC}"
echo ""

# Install with uvx
echo -e "${YELLOW}Installing to uvx...${NC}"
echo -e "${YELLOW}Installing to uv tools...${NC}"
uv tool install --force "$WHEEL_FILE"
echo "✓ Installed to uv tools"
uvx --from "$WHEEL_FILE" awslabs.aws-dms-mcp-server --help 2>&1 | head -20

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "You can now run the server with:"
echo -e "${YELLOW}  uvx --from $WHEEL_FILE awslabs.aws-dms-mcp-server${NC}"
echo ""
echo "Or test it:"
echo -e "${YELLOW}  uvx --from $WHEEL_FILE awslabs.aws-dms-mcp-server --version${NC}"
