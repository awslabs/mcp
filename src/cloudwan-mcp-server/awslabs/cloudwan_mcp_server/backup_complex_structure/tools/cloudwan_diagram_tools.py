"""
CloudWAN Diagram Tools.

This module provides MCP tool integration for CloudWAN diagram generation
using the Command pattern for consistent execution and organization.
"""

import logging

from mcp.server import Server

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .visualization.diagram_command_registry import register_diagram_commands


def register_cloudwan_diagram_tools(
    server: Server, aws_manager: AWSClientManager, config: CloudWANConfig
) -> None:
    """
    Register CloudWAN diagram tools with the MCP server using the Command pattern.

    This function registers all diagram generation commands with the MCP server,
    making them available as CLI tools. It uses the Command pattern for clean
    implementation and consistent execution.

    Args:
        server: MCP server instance
        aws_manager: AWS client manager instance
        config: CloudWAN configuration
    """
    logger = logging.getLogger(__name__)
    logger.info("Registering CloudWAN diagram tools using Command pattern")

    # Register all diagram commands
    register_diagram_commands(server, aws_manager, config)

    logger.info("CloudWAN diagram tools registered successfully")
