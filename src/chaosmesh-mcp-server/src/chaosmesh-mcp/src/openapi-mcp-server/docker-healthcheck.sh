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
#!/bin/sh

if [ "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l)" -ne "0" ]; then
  echo -n "$(lsof +c 0 -p 1 | grep -e grep -e "^awslabs\..*\s1\s.*\unix\s.*socket$" | wc -l) awslabs.* streams found";
  exit 0;
else
  echo -n "Zero awslabs.* streams found";
  # For OpenAPI MCP Server, we'll check if the process is running as a fallback
  if pgrep -f "python -m awslabs.openapi_mcp_server.server" > /dev/null; then
    echo -n " but server process is running";
    exit 0;
  fi;
  exit 1;
fi;

echo -n "Never should reach here";
exit 99;
