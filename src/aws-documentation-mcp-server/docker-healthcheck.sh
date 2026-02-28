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
  # Check HTTP endpoint - 406 is acceptable (means server is running but needs proper headers)
  PORT="${FASTMCP_PORT:-8000}"
  if python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://localhost:$PORT/mcp', timeout=5)
    exit(0)
except urllib.error.HTTPError as e:
    # 406 Not Acceptable means server is running
    exit(0 if e.code == 406 else 1)
except Exception:
    exit(1)
" 2>/dev/null; then
    echo "$SERVER HTTP is healthy"
    exit 0
  fi
  echo "$SERVER HTTP is unhealthy"
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
