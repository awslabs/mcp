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

"""MCP client utilities.

Provides connection and tool conversion utilities for MCP servers.
"""

import os
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Any, Dict, List


def connect_to_mcp_server(
    server_module: str = 'awslabs.cloudwatch_appsignals_mcp_server.server',
    verbose: bool = False,
):
    """Connect to an MCP server via stdio.

    Args:
        server_module: Python module path to MCP server (e.g., 'package.module.server')
        verbose: Enable verbose logging from server
    """
    env = os.environ.copy()
    if not verbose:
        env['LOGURU_LEVEL'] = 'ERROR'

    server_params = StdioServerParameters(command='python', args=['-m', server_module], env=env)

    return stdio_client(server_params)


def convert_mcp_tools_to_bedrock(mcp_tools) -> List[Dict[str, Any]]:
    """Convert MCP tool format to Bedrock tool format.

    Args:
        mcp_tools: List of MCP tool definitions

    Returns:
        List of Bedrock-formatted tool specifications
    """
    bedrock_tools = []

    for tool in mcp_tools:
        bedrock_tool = {
            'toolSpec': {
                'name': tool.name,
                'description': tool.description or '',
                'inputSchema': {'json': tool.inputSchema},
            }
        }
        bedrock_tools.append(bedrock_tool)

    return bedrock_tools
