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

# Health check script for EMR Troubleshooting MCP Server Docker container

set -e

# Check if Python can import the main module
python -c "
import sys
try:
    import awslabs.emr_troubleshooting_mcp_server
    from awslabs.emr_troubleshooting_mcp_server.tools import EMRTroubleshootingTools

    # Test basic functionality
    tools = EMRTroubleshootingTools()

    # Check if knowledge base is loaded
    if len(tools.known_issues) == 0:
        print('ERROR: No known issues loaded', file=sys.stderr)
        sys.exit(1)

    print(f'OK: {len(tools.known_issues)} known issues loaded')
    sys.exit(0)

except ImportError as e:
    print(f'ERROR: Import failed - {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'ERROR: Health check failed - {e}', file=sys.stderr)
    sys.exit(1)
"

echo "Health check passed"
