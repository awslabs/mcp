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

"""Shared configuration utilities for all AWS MCP servers."""

import os
from loguru import logger
from typing import Set


def disabled_tools() -> Set[str]:
    """Get set of disabled tools from environment variables.

    Reads DISABLED_TOOLS environment variable containing comma-separated
    tool names and returns a set of tools to disable.

    Returns:
        Set of tool names to disable. Empty set if no tools disabled.

    Example:
        "DISABLED_TOOLS": "ExecuteTerraformCommand,RunCheckovScan"
    """
    disabled_tools = os.environ.get('DISABLED_TOOLS', '')
    if not disabled_tools:
        return set()

    tools = {tool.strip() for tool in disabled_tools.split(',') if tool.strip()}
    if tools:
        logger.debug(f'Disabled tools: {", ".join(sorted(tools))}')
    return tools


def tool_enabled(tool_name: str) -> bool:
    """Check if a tool is enabled (not in disabled list).

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if tool should be enabled, False if disabled
    """
    return tool_name not in disabled_tools()
