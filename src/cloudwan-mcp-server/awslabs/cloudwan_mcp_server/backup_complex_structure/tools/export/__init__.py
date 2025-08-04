"""
Network data export tools for CloudWAN MCP.

This module provides tools for exporting AWS CloudWAN network data in various
formats with detailed filtering capabilities.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ... import CloudWANMCPServer
    from ...aws.client_manager import AWSClientManager
    from ...config import CloudWANConfig


def register_export_tools(server_instance):
    """Register network data export tools with the server."""
    from .tool import NetworkDataExportTool

    # Create tool instance
    export_tool = NetworkDataExportTool(server_instance.aws_manager, server_instance.config)

    # Helper function to create handler wrapper
    def create_handler_wrapper(tool_instance):
        """Create a wrapper that handles the signature mismatch"""

        async def wrapper(**kwargs):
            # Check if the tool expects 'arguments' parameter
            import inspect

            sig = inspect.signature(tool_instance.execute)
            params = list(sig.parameters.keys())

            # If it expects 'arguments' as first positional param, wrap kwargs
            if params and params[0] == "arguments":
                return await tool_instance.execute(kwargs)
            else:
                # Otherwise pass kwargs directly
                return await tool_instance.execute(**kwargs)

        return wrapper

    # Register with server
    server_instance.register_tool(
        name="export_network_data",
        description=export_tool.description,
        input_schema=export_tool.input_schema,
        handler=create_handler_wrapper(export_tool),
    )
