"""Unified prompt generation for OpenAPI specifications.

This module serves as the main entry point for prompt generation,
coordinating the generation of different types of prompts.
"""

from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation as _generate_api_documentation,
)
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


async def generate_api_documentation(
    server: FastMCP, api_name: str, openapi_spec: Dict[str, Any]
) -> Dict[str, bool]:
    """Generate efficient API documentation for an OpenAPI specification.

    Args:
        server: The MCP server
        api_name: The name of the API
        openapi_spec: The OpenAPI specification

    Returns:
        Dict[str, bool]: Status of each documentation type generation

    """
    return await _generate_api_documentation(server, api_name, openapi_spec)


# Alias for backward compatibility
generate_api_instructions = generate_api_documentation
generate_unified_prompts = generate_api_documentation
