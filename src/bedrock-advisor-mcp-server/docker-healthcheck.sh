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

# Simple health check for the Bedrock Advisor MCP Server
# This script verifies that the server can be imported and initialized

set -e

# Test if the server can be imported
python -c "from awslabs.bedrock_advisor_mcp_server.server import main; print('Health check passed')" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Health check passed"
    exit 0
else
    echo "Health check failed"
    exit 1
fi
