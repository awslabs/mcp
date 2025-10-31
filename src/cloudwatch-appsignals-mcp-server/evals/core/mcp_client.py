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

import contextlib
import json
import os
import sys
import tempfile
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from typing import Any, Dict, List, Optional


@contextlib.asynccontextmanager
async def connect_to_mcp_server(
    server_file: str,
    server_root_dir: str,
    verbose: bool = False,
    mock_config: Optional[Dict[str, Any]] = None,
):
    """Connect to an MCP server via stdio.

    Connects to a local MCP server file, optionally applying mocks
    to external dependencies (boto3, etc.) in the server subprocess.

    Args:
        server_file: Path to MCP server.py file
        server_root_dir: Root directory where the server should run (where its imports work)
        verbose: Enable verbose logging from server
        mock_config: Optional mock configuration dictionary

    Yields:
        Context manager from stdio_client for MCP connection

    Example:
        async with connect_to_mcp_server(
            server_file='/path/to/cloudwatch-appsignals-mcp-server/awslabs/cloudwatch_appsignals_mcp_server/server.py',
            server_root_dir='/path/to/cloudwatch-appsignals-mcp-server',
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

        # With mocks
        async with connect_to_mcp_server(
            server_file='/path/to/server.py',
            server_root_dir='/path/to/server/root',
            mock_config={'boto3': {...}}
        ) as (read, write):
            ...
    """
    if not server_file:
        raise ValueError('server_file is required')
    if not server_root_dir:
        raise ValueError('server_root_dir is required')

    server_file_path = Path(server_file).resolve()
    if not server_file_path.exists():
        raise FileNotFoundError(f'MCP server not found: {server_file}')

    server_root_dir_path = Path(server_root_dir).resolve()
    if not server_root_dir_path.exists():
        raise FileNotFoundError(f'Server root directory not found: {server_root_dir}')

    env = os.environ.copy()
    if not verbose:
        env['LOGURU_LEVEL'] = 'ERROR'
        env['MCP_CLOUDWATCH_APPSIGNALS_LOG_LEVEL'] = 'WARNING'

    mock_file_path = None

    try:
        if mock_config:
            mock_fd, mock_file_path = tempfile.mkstemp(suffix='.json', prefix='mcp_mocks_')
            with os.fdopen(mock_fd, 'w') as f:
                json.dump(mock_config, f)

            env['MCP_EVAL_MOCK_FILE'] = mock_file_path

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[
                '-m',
                'evals.core.mock_server_wrapper',
                str(server_file_path),
                '--server-cwd',
                str(server_root_dir_path),
            ],
            env=env,
        )

        async with stdio_client(server_params) as client:
            yield client

    finally:
        if mock_file_path and os.path.exists(mock_file_path):
            try:
                os.unlink(mock_file_path)
            except OSError:
                pass


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
