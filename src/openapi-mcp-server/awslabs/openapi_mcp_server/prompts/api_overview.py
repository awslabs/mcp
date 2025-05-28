"""API overview prompt generation."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.base import (
    format_display_name,
    format_markdown_table,
)
from typing import Any, Dict, List, Optional


def generate_api_overview(
    api_name: str,
    api_title: str,
    api_description: str,
    api_version: str,
    paths: Dict[str, Any],
    components: Dict[str, Any],
    servers: Optional[List[Dict[str, Any]]] = None,
    security_schemes: Optional[Dict[str, Any]] = None,
    workflow_section: Optional[str] = None,
) -> str:
    """Generate an API overview prompt.

    Args:
        api_name: The name of the API
        api_title: The title of the API
        api_description: The description of the API
        api_version: The version of the API
        paths: The API paths
        components: The API components
        servers: The API servers
        security_schemes: The API security schemes
        workflow_section: Optional workflow section to include

    Returns:
        str: The generated API overview prompt

    """
    result = []

    # Add title and description
    result.append(f'# {api_title}')
    result.append(f'\n{api_description}')
    result.append(f'\nVersion: {api_version}')

    # Add servers section if available
    if servers:
        result.append('\n## API Servers')

        for server in servers:
            url = server.get('url', '')
            description = server.get('description', '')

            result.append(f'- **{url}**')
            if description:
                result.append(f'  {description}')

    # Add security schemes section if available
    if security_schemes:
        result.append('\n## Authentication')

        for scheme_name, scheme in security_schemes.items():
            scheme_type = scheme.get('type', '')
            description = scheme.get('description', '')

            result.append(f'- **{scheme_name}** ({scheme_type})')
            if description:
                result.append(f'  {description}')

            # Add scheme-specific details
            if scheme_type == 'apiKey':
                result.append(f'  - **Name**: {scheme.get("name", "")}')
                result.append(f'  - **In**: {scheme.get("in", "")}')
            elif scheme_type == 'http':
                result.append(f'  - **Scheme**: {scheme.get("scheme", "")}')
            elif scheme_type == 'oauth2':
                result.append(f'  - **Flows**: {", ".join(scheme.get("flows", {}).keys())}')

    # Add endpoints section
    result.append('\n## Available Endpoints')

    # Group endpoints by tag
    endpoints_by_tag = {}

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                tags = operation.get('tags', ['default'])
                operation_id = operation.get('operationId', f'{method} {path}')
                summary = operation.get('summary', operation_id)

                for tag in tags:
                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []

                    endpoints_by_tag[tag].append(
                        {
                            'method': method.upper(),
                            'path': path,
                            'operation_id': operation_id,
                            'summary': summary,
                        }
                    )

    # Add endpoints grouped by tag
    for tag, endpoints in endpoints_by_tag.items():
        result.append(f'\n### {tag}')

        # Create a table of endpoints
        headers = ['Method', 'Path', 'Operation ID', 'Summary']
        rows = []

        for endpoint in endpoints:
            rows.append(
                [
                    endpoint['method'],
                    f'`{endpoint["path"]}`',
                    endpoint['operation_id'],
                    endpoint['summary'],
                ]
            )

        result.append(format_markdown_table(headers, rows))

    # Add schemas section if available
    schemas = components.get('schemas', {})
    if schemas:
        result.append('\n## Available Schemas')

        for schema_name, schema in schemas.items():
            schema_type = schema.get('type', 'object')
            description = schema.get('description', '')

            result.append(f'\n### {schema_name}')
            if description:
                result.append(f'{description}')

            result.append(f'**Type**: {schema_type}')

            # Add properties for object schemas
            if schema_type == 'object' and 'properties' in schema:
                result.append('\n**Properties**:')

                # Create a table of properties
                headers = ['Name', 'Type', 'Required', 'Description']
                rows = []

                required_props = schema.get('required', [])

                for prop_name, prop in schema['properties'].items():
                    prop_type = prop.get('type', 'any')
                    prop_desc = prop.get('description', '')
                    required = 'Yes' if prop_name in required_props else 'No'

                    rows.append(
                        [
                            prop_name,
                            prop_type,
                            required,
                            prop_desc,
                        ]
                    )

                result.append(format_markdown_table(headers, rows))

    # Add workflow section if available
    if workflow_section:
        result.append(workflow_section)

    return '\n'.join(result)


def api_overview_fn(
    api_name: str,
    api_title: str,
    api_description: str,
    api_version: str,
    paths: Dict[str, Any],
    components: Dict[str, Any],
    servers: Optional[List[Dict[str, Any]]] = None,
    security_schemes: Optional[Dict[str, Any]] = None,
    workflow_section: Optional[str] = None,
) -> str:
    """Generate an API overview.

    Args:
        api_name: The name of the API
        api_title: The title of the API
        api_description: The description of the API
        api_version: The version of the API
        paths: The API paths
        components: The API components
        servers: The API servers
        security_schemes: The API security schemes
        workflow_section: Optional workflow section to include

    Returns:
        str: The generated API overview

    """
    return generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
        servers=servers,
        security_schemes=security_schemes,
        workflow_section=workflow_section,
    )


def create_api_overview_prompt(
    server: Any,
    api_name: str,
    api_title: str,
    api_description: str,
    api_version: str,
    paths: Dict[str, Any],
    components: Dict[str, Any],
    servers: Optional[List[Dict[str, Any]]] = None,
    security_schemes: Optional[Dict[str, Any]] = None,
    workflow_section: Optional[str] = None,
) -> None:
    """Create and add an API overview prompt to the server.

    Args:
        server: The MCP server
        api_name: The name of the API
        api_title: The title of the API
        api_description: The description of the API
        api_version: The version of the API
        paths: The API paths
        components: The API components
        servers: The API servers
        security_schemes: The API security schemes
        workflow_section: Optional workflow section to include

    """
    try:
        # Try to import the Prompt class from fastmcp
        from fastmcp.prompts.prompt import Prompt

        # Format the API name for display
        display_api_name = format_display_name(api_name)

        # Create a readable prompt name
        if display_api_name.upper().endswith('API'):
            prompt_name = f'{display_api_name} Overview'
        else:
            prompt_name = f'{display_api_name} API Overview'

        # Create the prompt using from_function
        prompt = Prompt.from_function(
            fn=api_overview_fn,
            name=prompt_name,
            description=f'Overview of the {api_title}',
        )

        # Add the prompt to the server
        server._prompt_manager.add_prompt(prompt)
        logger.info(f'Added API overview prompt: {prompt_name}')
    except Exception as e:
        logger.warning(f'Failed to create API overview prompt: {e}')
