"""
MCP server API for ECS tools.

This module provides API endpoints for the MCP server.
"""

from .ecs_troubleshooting import ecs_troubleshooting_tool

# Export the functions that will be available to the MCP server
__all__ = [
    "ecs_troubleshooting_tool",
]
