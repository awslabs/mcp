#!/bin/sh
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

SERVER="aws-documentation-mcp-server"

# Check if HTTP transport is enabled
if [ "$FASTMCP_TRANSPORT" = "streamable-http" ]; then
  # Check HTTP endpoint with GET request
  # 200 = healthy, 406 = server running but needs proper MCP headers (also healthy)
  PORT="${FASTMCP_PORT:-8000}"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/mcp" --max-time 5 2>/dev/null) || HTTP_CODE="000"
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "406" ]; then
    echo "$SERVER HTTP is healthy (HTTP $HTTP_CODE)"
    exit 0
  fi
  echo "$SERVER HTTP is unhealthy (HTTP $HTTP_CODE)"
  exit 1
else
  # Original stdio check
  if pgrep -P 0 -a -l -x -f "/app/.venv/bin/python3? /app/.venv/bin/awslabs.$SERVER" > /dev/null; then
    echo "$SERVER is running"
    exit 0
  fi
  echo "$SERVER is not running"
  exit 1
fi
