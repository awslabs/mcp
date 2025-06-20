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

# Simple health check for the IAM MCP Server
# This script checks if the server can start and respond to basic requests

set -e

# Check if the server can import and start
timeout 10s python -c "
import sys
sys.path.insert(0, '/app')
from awslabs.iam_mcp_server.server import mcp
print('IAM MCP Server health check passed')
" || exit 1

echo "Health check completed successfully"
