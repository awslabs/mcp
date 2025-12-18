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

import os
import sys
from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
from fastmcp.tools import Tool
from loguru import logger
from typing import Any, Callable, Dict, Optional


logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def get_remote_proxy_server_tool(
    remote_proxy_client: ProxyClient,
    remote_tool_name: str,
) -> Tool:
    """Get a tool from a remote MCP server via proxy.

    Args:
        remote_proxy_client: The ProxyClient connected to the remote server.
        remote_tool_name: Name of the tool to retrieve from the remote server.

    Returns:
        The Tool object from the remote server.

    Raises:
        ValueError: If the tool is not found on the remote server.
    """
    # https://gofastmcp.com/servers/proxy#transport-bridging
    remote_proxy = FastMCP.as_proxy(remote_proxy_client, name='Remote to local bridge')

    # Get the tool from the proxy server
    remote_tool = await remote_proxy.get_tool(remote_tool_name)
    if not remote_tool:
        raise ValueError(f'Tool {remote_tool_name} not found on remote server')

    return remote_tool


async def create_local_proxied_tool(
    remote_tool: Tool,
    local_tool_name: str,
    local_tool_description: Optional[str] = None,
    response_transformer: Optional[Callable[[Any], Any]] = None,
) -> Tool:
    """Create a proxied tool using Tool.from_tool() with optional transformations.

    Args:
        remote_tool: The remote Tool object to proxy.
        local_tool_name: Custom name for the local tool.
        local_tool_description: Optional custom description for the local tool.
        response_transformer: Optional function to transform the response.

    Returns:
        A Tool object that proxies to the remote tool.
    """
    # Build kwargs dict with only provided optional parameters (filter out None values)
    kwargs: Dict[str, Any] = {'name': local_tool_name}
    if local_tool_description is not None:
        kwargs['description'] = local_tool_description
    if response_transformer is not None:
        kwargs['transform_fn'] = response_transformer

    # Use Tool.from_tool to create the proxied tool
    proxied_tool = Tool.from_tool(remote_tool, **kwargs)

    return proxied_tool
