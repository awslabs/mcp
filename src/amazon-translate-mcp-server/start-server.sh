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

# Startup script for Amazon Translate MCP Server with configuration validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to log with color
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    log_error "Python ${REQUIRED_VERSION} or higher is required. Found: ${PYTHON_VERSION}"
    exit 1
fi

log_info "Python version check passed: ${PYTHON_VERSION}"


# Check if server module is available
if ! python3 -c "import awslabs.amazon_translate_mcp_server.server" 2>/dev/null; then
    log_error "Amazon Translate MCP Server module not found"
    log_error "Please install the package: pip install awslabs.amazon-translate-mcp-server"
    exit 1
fi

log_info "Server module check passed"

# Start the server
log_info "Starting Amazon Translate MCP Server..."

# Handle signals gracefully
trap 'log_info "Received shutdown signal, stopping server..."; exit 0' SIGTERM SIGINT

# Start the server with configuration validation
exec python3 -m awslabs.amazon_translate_mcp_server.server "$@"
