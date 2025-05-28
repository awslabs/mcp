"""Mapping reference prompt generation."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.base import format_display_name, format_markdown_table
from typing import Any, Dict


def generate_mapping_reference(
    api_name: str,
    paths: Dict[str, Any],
    operation_mappings: Dict[str, Dict[str, Any]],
) -> str:
    """Generate a mapping reference prompt.

    Args:
        api_name: The name of the API
        paths: The API paths
        operation_mappings: The operation mappings

    Returns:
        str: The generated mapping reference prompt

    """
    result = []

    # Add title and description
    result.append(f'# {api_name} API Mapping Reference')
    result.append(
        f'\nThis document provides a comprehensive reference for how the {api_name} API operations are mapped to MCP tools and resources.'
    )

    # Add function mappings section
    result.append('\n## Function Mappings')
    result.append('\nThe following API operations are mapped to MCP functions:')

    # Create a table of function mappings
    headers = ['Operation ID', 'HTTP Method', 'Path', 'Function Name']
    rows = []

    for operation_id, mapping in operation_mappings.items():
        if mapping.get('mapping_type') == 'function':
            method = mapping.get('method', '').upper()
            path = mapping.get('path', '')
            function_name = f'{api_name}_{operation_id}'

            rows.append(
                [
                    operation_id,
                    method,
                    f'`{path}`',
                    function_name,
                ]
            )

    if rows:
        result.append(format_markdown_table(headers, rows))
    else:
        result.append('\nNo function mappings found.')

    # Add resource mappings section
    result.append('\n## Resource Mappings')
    result.append('\nThe following API operations are mapped to MCP resources:')

    # Create a table of resource mappings
    headers = ['Operation ID', 'HTTP Method', 'Path', 'Resource URI']
    rows = []

    for operation_id, mapping in operation_mappings.items():
        if mapping.get('mapping_type') == 'resource':
            method = mapping.get('method', '').upper()
            path = mapping.get('path', '')
            resource_uri = mapping.get('resource_uri', '')

            rows.append(
                [
                    operation_id,
                    method,
                    f'`{path}`',
                    f'`{resource_uri}`',
                ]
            )

    if rows:
        result.append(format_markdown_table(headers, rows))
    else:
        result.append('\nNo resource mappings found.')

    # Add parameter mappings section
    result.append('\n## Parameter Mappings')
    result.append(
        '\nThe following table shows how API parameters are mapped to function parameters:'
    )

    # Create a table of parameter mappings
    headers = ['Operation ID', 'API Parameter', 'Parameter Type', 'Function Parameter']
    rows = []

    for operation_id, mapping in operation_mappings.items():
        if mapping.get('mapping_type') == 'function':
            parameters = mapping.get('parameters', [])

            for param in parameters:
                param_name = param.get('name', '')
                param_in = param.get('in', '')
                function_param = param_name  # Usually the same

                rows.append(
                    [
                        operation_id,
                        param_name,
                        param_in,
                        function_param,
                    ]
                )

    if rows:
        result.append(format_markdown_table(headers, rows))
    else:
        result.append('\nNo parameter mappings found.')

    # Add usage examples section
    result.append('\n## Usage Examples')

    # Function example
    result.append('\n### Function Example')
    result.append('```python')
    result.append('# Example of calling a function')
    result.append(f'result = await {api_name}_getItem(itemId=123)')
    result.append('print(result)')
    result.append('```')

    # Resource example
    result.append('\n### Resource Example')
    result.append('```python')
    result.append('# Example of accessing a resource')
    result.append(f'resource = await get_resource("{api_name}+item+123")')
    result.append('print(resource.name)')
    result.append('print(resource.description)')
    result.append('```')

    return '\n'.join(result)


def mapping_reference_fn(
    api_name: str,
    paths: Dict[str, Any],
    operation_mappings: Dict[str, Dict[str, Any]],
) -> str:
    """Generate a mapping reference.

    Args:
        api_name: The name of the API
        paths: The API paths
        operation_mappings: The operation mappings

    Returns:
        str: The generated mapping reference

    """
    return generate_mapping_reference(
        api_name=api_name,
        paths=paths,
        operation_mappings=operation_mappings,
    )


def create_mapping_reference_prompt(
    server: Any,
    api_name: str,
    paths: Dict[str, Any],
    operation_mappings: Dict[str, Dict[str, Any]],
) -> None:
    """Create and add a mapping reference prompt to the server.

    Args:
        server: The MCP server
        api_name: The name of the API
        paths: The API paths
        operation_mappings: The operation mappings

    """
    try:
        # Try to import the Prompt class from fastmcp
        from fastmcp.prompts.prompt import Prompt

        # Format the API name for display
        display_api_name = format_display_name(api_name)

        # Create a readable prompt name
        if display_api_name.upper().endswith('API'):
            prompt_name = f'{display_api_name} Mapping Reference'
        else:
            prompt_name = f'{display_api_name} API Mapping Reference'

        # Create the prompt using from_function
        prompt = Prompt.from_function(
            fn=mapping_reference_fn,
            name=prompt_name,
            description=f'Mapping reference for the {api_name}',
        )

        # Add the prompt to the server
        server._prompt_manager.add_prompt(prompt)
        logger.info(f'Added mapping reference prompt: {prompt_name}')
    except Exception as e:
        logger.warning(f'Failed to create mapping reference prompt: {e}')
