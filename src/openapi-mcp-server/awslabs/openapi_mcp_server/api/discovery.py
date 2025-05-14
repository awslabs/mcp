"""API discovery and introspection utilities."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.metrics_provider import metrics
from awslabs.openapi_mcp_server.utils.openapi_validator import extract_api_structure
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, cast


class ApiInfo(BaseModel):
    """Information about an API."""

    name: str = Field(..., description='Name of the API')
    title: str = Field(..., description='Title of the API')
    version: str = Field(..., description='Version of the API')
    description: str = Field('', description='Description of the API')
    base_url: str = Field(..., description='Base URL of the API')
    paths: int = Field(..., description='Number of paths in the API')
    operations: int = Field(..., description='Number of operations in the API')
    schemas: int = Field(..., description='Number of schemas in the API')


class ToolInfo(BaseModel):
    """Information about a tool."""

    name: str = Field(..., description='Name of the tool')
    description: str = Field('', description='Description of the tool')
    method: str = Field(..., description='HTTP method of the tool')
    path: str = Field(..., description='Path of the tool')
    parameters: List[Dict[str, Any]] = Field([], description='Parameters of the tool')
    usage_count: int = Field(0, description='Number of times the tool has been used')
    error_rate: float = Field(0.0, description='Error rate of the tool')
    avg_duration_ms: float = Field(0.0, description='Average duration of the tool in milliseconds')


class ApiStats(BaseModel):
    """Statistics about API usage."""

    total_calls: int = Field(..., description='Total number of API calls')
    error_count: int = Field(..., description='Number of API call errors')
    error_rate: float = Field(..., description='Error rate of API calls')
    unique_paths: int = Field(..., description='Number of unique API paths called')
    recent_errors: List[Dict[str, Any]] = Field([], description='Recent API call errors')


async def get_api_info(api_name: str, openapi_spec: Dict[str, Any], base_url: str) -> ApiInfo:
    """Get information about an API.

    Args:
        api_name: Name of the API
        openapi_spec: The OpenAPI specification
        base_url: Base URL of the API

    Returns:
        ApiInfo: Information about the API
    """
    # Extract API structure
    structure = extract_api_structure(openapi_spec)

    return ApiInfo(
        name=api_name,
        title=structure['info']['title'],
        version=structure['info']['version'],
        description=structure['info']['description'],
        base_url=base_url,
        paths=len(structure['paths']),
        operations=len(structure['operations']),
        schemas=len(structure['schemas']),
    )


async def get_api_tools(server: FastMCP, api_name: str) -> List[ToolInfo]:
    """Get information about tools for an API.

    Args:
        server: The MCP server
        api_name: Name of the API

    Returns:
        List[ToolInfo]: Information about tools for the API
    """
    tools = []

    # Get all tools for this API
    try:
        # Ignore type error since FastMCP in newer versions has get_tools
        all_tools = await server.get_tools()  # type: ignore

        # Defensive programming: check if all_tools is None or not a dict
        if not all_tools or not isinstance(all_tools, dict):
            logger.warning(f'Invalid tools data returned: {type(all_tools)}')
            return tools

        # Filter tools that match our API name prefix
        api_tools = []
        for tool_key, tool in all_tools.items():
            # Check if the tool has a name attribute and it's a string
            if (
                hasattr(tool, 'name')
                and isinstance(tool.name, str)
                and tool.name.startswith(f'{api_name}_')
            ):
                api_tools.append(tool)
            # If tool itself is a string (shouldn't happen but just in case)
            elif isinstance(tool, str) and tool.startswith(f'{api_name}_'):
                logger.debug(f'Found tool as string: {tool}')
                # Skip this tool as we can't extract more info
                continue

        # Get tool stats
        tool_stats = metrics.get_tool_stats()

        for tool in api_tools:
            try:
                # Extract method and path from description
                method = 'GET'  # Default
                path = ''
                if hasattr(tool, 'description') and isinstance(tool.description, str):
                    description_lines = tool.description.split('\n')
                    for line in description_lines:
                        if line.startswith('HTTP'):
                            parts = line.split(' ', 2)
                            if len(parts) >= 2:
                                method = parts[1]
                            if len(parts) >= 3:
                                path = parts[2]
                            break

                # Get parameters
                parameters = []
                if hasattr(tool, 'parameters') and tool.parameters:
                    for param in tool.parameters:
                        if hasattr(param, 'name'):
                            param_info = {
                                'name': param.name,
                                'type': str(getattr(param, 'type', 'unknown')),
                                'required': getattr(param, 'required', False),
                                'description': getattr(param, 'description', ''),
                            }
                            parameters.append(param_info)

                # Get usage stats - ensure tool.name is a string
                tool_name = (
                    tool.name
                    if hasattr(tool, 'name') and isinstance(tool.name, str)
                    else str(tool)
                )
                stats = tool_stats.get(tool_name, {})
                usage_count = stats.get('count', 0)
                error_rate = stats.get('error_rate', 0.0)
                avg_duration_ms = stats.get('avg_duration_ms', 0.0)

                # Get first line of description or use empty string if description is not a string
                first_line = ''
                if hasattr(tool, 'description') and isinstance(tool.description, str):
                    description_parts = tool.description.split('\n')
                    if description_parts:
                        first_line = description_parts[0]

                tools.append(
                    ToolInfo(
                        name=tool_name,
                        description=first_line,
                        method=method,
                        path=path,
                        parameters=parameters,
                        usage_count=usage_count,
                        error_rate=error_rate,
                        avg_duration_ms=avg_duration_ms,
                    )
                )
            except Exception as e:
                logger.warning(f'Error processing tool {getattr(tool, "name", "unknown")}: {e}')
                continue

    except Exception as e:
        logger.warning(f'Error getting tools: {e}')

    return tools


async def get_api_stats(api_name: Optional[str] = None) -> ApiStats:
    """Get statistics about API usage.

    Args:
        api_name: Optional name of the API to filter stats for

    Returns:
        ApiStats: Statistics about API usage
    """
    try:
        summary = metrics.get_summary()
        api_calls = summary.get('api_calls', {})

        return ApiStats(
            total_calls=api_calls.get('total', 0),
            error_count=api_calls.get('errors', 0),
            error_rate=api_calls.get('error_rate', 0.0),
            unique_paths=api_calls.get('paths', 0),
            recent_errors=metrics.get_recent_errors(limit=5),
        )
    except Exception as e:
        logger.warning(f'Error getting API stats: {e}')
        # Return default values if there's an error
        return ApiStats(
            total_calls=0,
            error_count=0,
            error_rate=0.0,
            unique_paths=0,
            recent_errors=[],
        )


def register_discovery_tools(
    server: FastMCP, api_name: str, openapi_spec: Dict[str, Any], base_url: str
) -> None:
    """Register discovery tools with the MCP server.

    Args:
        server: The MCP server
        api_name: Name of the API
        openapi_spec: The OpenAPI specification
        base_url: Base URL of the API
    """
    logger.info(f'Registering discovery tools for {api_name} API')

    # Register the API info tool
    server.add_tool(
        name=f'{api_name}_getApiInfo',
        description=f'Get information about the {api_name} API',
        fn=lambda: get_api_info(api_name, openapi_spec, base_url),
    )

    # Register the API tools tool
    # Use a closure to capture the current server and api_name
    def get_tools_wrapper() -> List[ToolInfo]:
        return cast(List[ToolInfo], get_api_tools(server, api_name))

    server.add_tool(
        name=f'{api_name}_getApiTools',
        description=f'Get a list of available tools for the {api_name} API',
        fn=get_tools_wrapper,
    )

    # Register the API stats tool
    # Use a closure to ensure no positional arguments
    def get_stats_wrapper() -> ApiStats:
        return cast(ApiStats, get_api_stats(api_name))

    server.add_tool(
        name=f'{api_name}_getApiStats',
        description=f'Get usage statistics for the {api_name} API',
        fn=get_stats_wrapper,
    )

    logger.info(f'Registered discovery tools for {api_name} API')
