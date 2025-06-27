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

# Check if the process is running
if ! pgrep -f "awslabs.valkey-mcp-server" > /dev/null; then
    echo "Process not running"
    exit 1
fi

# Check if the port is listening (default MCP server port is 8080)
if ! lsof -i :8080 -sTCP:LISTEN > /dev/null; then
    echo "Port 8080 not listening"
    exit 1
fi

# All checks passed
exit 0
