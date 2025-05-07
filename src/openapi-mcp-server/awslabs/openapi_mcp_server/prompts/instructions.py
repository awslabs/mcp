"""Instructions generation for OpenAPI specifications."""

from awslabs.openapi_mcp_server import get_caller_info, logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


async def generate_api_instructions(
    server: FastMCP, api_name: str, openapi_spec: Dict[str, Any]
) -> None:
    """Generate dynamic instructions based on the OpenAPI spec and available tools/resources.

    Args:
        server: The MCP server
        api_name: The name of the API
        openapi_spec: The OpenAPI specification
    """
    logger.info(f'Generating dynamic instructions for {api_name} API')

    # Get caller information for debugging
    caller_info = get_caller_info()
    logger.debug(f'Called from {caller_info}')

    # Extract API title and description
    api_title = openapi_spec.get('info', {}).get('title', api_name)
    api_description = openapi_spec.get('info', {}).get('description', '')

    logger.debug(f'API title: {api_title}')
    if api_description:
        logger.debug(f'API description length: {len(api_description)} characters')

    # Build dynamic instructions
    instructions = f'# {api_title} API Instructions\n\n'

    if api_description:
        instructions += f'{api_description}\n\n'

    # Count endpoints and tools for logging
    path_count = len(openapi_spec.get('paths', {}))
    operation_count = 0

    # Count operations (tools)
    for path, methods in openapi_spec.get('paths', {}).items():
        for method in methods:
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                operation_count += 1

    logger.info(f'API contains {path_count} paths and {operation_count} operations')

    # Instead of trying to set the instructions directly, which might not be allowed,
    # we'll update the initial instructions at initialization time
    # For now, we'll just log the generated instructions
    logger.info(f'Generated instructions for {api_name}: {instructions[:100]}...')
