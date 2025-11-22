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

# Health check script for AWS Carbon Footprint MCP Server Docker container

set -e

# Check if the MCP server module can be imported
python -c "import awslabs.carbon_footprint_mcp_server.server; print('MCP server module imported successfully')" || exit 1

# Check if AWS CLI is available
aws --version > /dev/null 2>&1 || exit 1

# Check if required Python packages are available
python -c "import boto3, pydantic, loguru; print('Required packages available')" || exit 1

echo "Health check passed"
exit 0
