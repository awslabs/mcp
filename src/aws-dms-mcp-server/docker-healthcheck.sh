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

# Health check script for AWS DMS MCP Server
# Verifies that the server module can be imported and version can be retrieved

set -e

# Check if the server module can be imported and version can be retrieved
# Use importlib to avoid initializing the server
python -c "
import sys
try:
    from awslabs.aws_dms_mcp_server import __version__
    print(f'AWS DMS MCP Server v{__version__} is healthy')
    sys.exit(0)
except Exception as e:
    print(f'Health check failed: {e}', file=sys.stderr)
    sys.exit(1)
" || exit 1

exit 0
