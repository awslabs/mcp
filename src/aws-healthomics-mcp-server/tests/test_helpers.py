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

"""Test helper utilities for MCP tool testing."""

import inspect
from mcp.server.fastmcp import Context
from typing import Any, Dict


async def call_mcp_tool_directly(tool_func, ctx: Context, **kwargs) -> Any:
    """Call an MCP tool function directly in tests, bypassing Field annotation processing.

    This helper extracts the actual parameter values from Field annotations and calls
    the function with the correct parameter types.

    Args:
        tool_func: The MCP tool function to call
        ctx: MCP context
        **kwargs: Parameter values to pass to the function

    Returns:
        The result of calling the tool function
    """
    # Get the function signature
    sig = inspect.signature(tool_func)

    # Build the actual parameters, using defaults from Field annotations where needed
    actual_params: Dict[str, Any] = {'ctx': ctx}

    for param_name, param in sig.parameters.items():
        if param_name == 'ctx':
            continue

        if param_name in kwargs:
            # Use provided value
            actual_params[param_name] = kwargs[param_name]
        elif param.default != inspect.Parameter.empty:
            # Use default value from Field or regular default
            if hasattr(param.default, 'default'):
                # This is a Field object, extract the default
                if callable(param.default.default_factory):
                    actual_params[param_name] = param.default.default_factory()
                else:
                    actual_params[param_name] = param.default.default
            else:
                # Regular default value
                actual_params[param_name] = param.default
        # If no default and not provided, let the function handle it

    return await tool_func(**actual_params)


def extract_field_defaults(tool_func) -> Dict[str, Any]:
    """Extract default values from Field annotations in an MCP tool function.

    Args:
        tool_func: The MCP tool function to analyze

    Returns:
        Dictionary mapping parameter names to their default values
    """
    sig = inspect.signature(tool_func)
    defaults = {}

    for param_name, param in sig.parameters.items():
        if param_name == 'ctx':
            continue

        if param.default != inspect.Parameter.empty and hasattr(param.default, 'default'):
            # This is a Field object
            if callable(param.default.default_factory):
                defaults[param_name] = param.default.default_factory()
            else:
                defaults[param_name] = param.default.default

    return defaults


class MCPToolTestWrapper:
    """Wrapper class for testing MCP tools with Field annotations.

    This class provides a clean interface for calling MCP tools in tests
    without dealing with Field annotation complexities.
    """

    def __init__(self, tool_func):
        """Initialize the wrapper with an MCP tool function."""
        self.tool_func = tool_func
        self.defaults = extract_field_defaults(tool_func)

    async def call(self, ctx: Context, **kwargs) -> Any:
        """Call the wrapped MCP tool function with proper parameter handling.

        Args:
            ctx: MCP context
            **kwargs: Parameter values to pass to the function

        Returns:
            The result of calling the tool function
        """
        return await call_mcp_tool_directly(self.tool_func, ctx, **kwargs)

    def get_defaults(self) -> Dict[str, Any]:
        """Get the default parameter values for this tool."""
        return self.defaults.copy()
