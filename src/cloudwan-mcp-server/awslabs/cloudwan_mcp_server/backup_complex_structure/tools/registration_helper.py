"""
Helper functions for MCP tool registration.

This module provides utilities to simplify the registration of MCP tools
using the correct v1.12.0 decorator-based API.
"""

from typing import Any, Dict, List, Callable, Optional
from mcp.server import Server
from mcp.types import TextContent
from .base import BaseMCPTool


def register_tool_with_server(
    server: Server, tool: BaseMCPTool, custom_name: Optional[str] = None
) -> None:
    """
    Register a single tool with the MCP server using the decorator pattern.

    Args:
        server: MCP server instance
        tool: Tool instance to register
        custom_name: Optional custom name for the tool
    """
    tool_name = custom_name or tool.tool_name

    @server.tool(name=tool_name, description=tool.description, inputSchema=tool.input_schema)
    async def handle_tool(arguments: Dict[str, Any]) -> List[TextContent]:
        return await tool.execute(**arguments)


def register_legacy_tool(
    server: Server,
    tool_name: str,
    tool_description: str,
    tool_schema: Dict[str, Any],
    handler: Callable,
) -> None:
    """
    Register a tool that doesn't inherit from BaseMCPTool.

    Args:
        server: MCP server instance
        tool_name: Name of the tool
        tool_description: Description of the tool
        tool_schema: Input schema for the tool
        handler: Async function to handle tool execution
    """

    @server.tool(name=tool_name, description=tool_description, inputSchema=tool_schema)
    async def handle_tool(arguments: Dict[str, Any]) -> List[TextContent]:
        return await handler(**arguments)
