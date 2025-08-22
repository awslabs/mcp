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

SERVER="billing_cost_management_mcp_server"

# Check if the server process is running
if pgrep -P 0 -a -l -x -f "/app/.venv/bin/python3 /app/.venv/bin/awslabs.$SERVER" > /dev/null; then
  echo -n "$SERVER is running";
  exit 0;
fi;

# Unhealthy
exit 1;
