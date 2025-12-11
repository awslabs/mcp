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
from fastmcp.tools import Tool
from loguru import logger
from typing import Any, Callable, Dict, Optional


logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def create_proxied_tool(
    proxy_server: FastMCP,
    remote_tool_name: str,
    local_tool_name: Optional[str] = None,
    local_description: Optional[str] = None,
    default_params: Optional[Dict[str, Any]] = None,
    response_transformer: Optional[Callable[[Any], Any]] = None,
) -> Tool:
    """Create a proxied tool using Tool.from_tool() with optional transformations.

    Args:
        proxy_server: The FastMCP proxy server instance.
        remote_tool_name: Name of the remote tool to proxy.
        local_tool_name: Optional custom name for the local tool.
        local_description: Optional custom description for the local tool.
        default_params: Default parameters to inject into every call.
        response_transformer: Optional function to transform the response.

    Returns:
        A Tool object that proxies to the remote tool.
    """
    # Get the tool from the proxy server
    remote_tool = await proxy_server.get_tool(remote_tool_name)
    if not remote_tool:
        raise ValueError(f'Tool {remote_tool_name} not found on remote server')

    # Use Tool.from_tool to create the proxied tool
    proxied_tool = Tool.from_tool(
        remote_tool,
        name=local_tool_name,
        description=local_description,
        transform_fn=response_transformer,
    )

    return proxied_tool
