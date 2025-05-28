"""Operation-specific prompt generation."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.base import (
    format_display_name,
    format_parameter_description,
)
from typing import Any, Dict, List, Optional


def generate_operation_prompt(
    api_name: str,
    operation_id: str,
    mapping_type: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
) -> str:
    """Generate a detailed prompt for an API operation.

    Args:
        api_name: The name of the API
        operation_id: The operation ID
        mapping_type: The mapping type (function or resource)
        method: The HTTP method
        path: The API path
        summary: The operation summary
        description: The operation description
        parameters: The operation parameters
        request_body: The request body schema
        responses: The response schemas
        security: The security requirements

    Returns:
        str: The generated prompt

    """
    result = []

    # Add title
    result.append(f'# {operation_id}')

    # Add summary and description
    if summary:
        result.append(f'\n{summary}')
    if description:
        result.append(f'\n{description}')

    # Add HTTP method and path
    result.append('\n## API Details')
    result.append(f'- **HTTP Method**: {method.upper()}')
    result.append(f'- **Path**: `{path}`')
    result.append(f'- **Mapping Type**: {mapping_type}')

    # Add parameters section if there are parameters
    if parameters:
        result.append('\n## Parameters')

        # Group parameters by location
        path_params = [p for p in parameters if p.get('in') == 'path']
        query_params = [p for p in parameters if p.get('in') == 'query']
        header_params = [p for p in parameters if p.get('in') == 'header']

        # Add path parameters
        if path_params:
            result.append('\n### Path Parameters')
            for param in path_params:
                result.append(f'- {format_parameter_description(param)}')

        # Add query parameters
        if query_params:
            result.append('\n### Query Parameters')
            for param in query_params:
                result.append(f'- {format_parameter_description(param)}')

        # Add header parameters
        if header_params:
            result.append('\n### Header Parameters')
            for param in header_params:
                result.append(f'- {format_parameter_description(param)}')

    # Add request body section if there is a request body
    if request_body:
        result.append('\n## Request Body')

        # Check if request body is required
        required = request_body.get('required', False)
        result.append(f'- **Required**: {"Yes" if required else "No"}')

        # Add content types
        content = request_body.get('content', {})
        for content_type, content_schema in content.items():
            result.append(f'- **Content Type**: `{content_type}`')

            # Add schema if available
            schema = content_schema.get('schema', {})
            if schema:
                result.append('\n### Schema')
                result.append(_format_schema(schema))

    # Add responses section if there are responses
    if responses:
        result.append('\n## Responses')

        for status_code, response in responses.items():
            result.append(f'\n### {status_code} - {response.get("description", "")}')

            # Add content types
            content = response.get('content', {})
            for content_type, content_schema in content.items():
                result.append(f'- **Content Type**: `{content_type}`')

                # Add schema if available
                schema = content_schema.get('schema', {})
                if schema:
                    result.append('\n#### Schema')
                    result.append(_format_schema(schema))

    # Add security section if there are security requirements
    if security:
        result.append('\n## Security')

        for sec_req in security:
            for scheme, scopes in sec_req.items():
                result.append(f'- **{scheme}**')
                if scopes:
                    result.append(f'  - Scopes: {", ".join(scopes)}')

    return '\n'.join(result)


def _format_schema(schema: Dict[str, Any], indent: int = 0) -> str:
    """Format a JSON schema as a string.

    Args:
        schema: The JSON schema
        indent: The indentation level

    Returns:
        str: The formatted schema

    """
    result = []
    indent_str = '  ' * indent

    # Handle different schema types
    schema_type = schema.get('type')

    if schema_type == 'object':
        result.append(f'{indent_str}**Type**: Object')

        # Add properties
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        if properties:
            result.append(f'{indent_str}**Properties**:')

            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get('type', 'any')
                prop_desc = prop_schema.get('description', '')
                req_str = ' (required)' if prop_name in required else ''

                result.append(f'{indent_str}- **{prop_name}**{req_str}: {prop_type}')
                if prop_desc:
                    result.append(f'{indent_str}  {prop_desc}')

                # Handle nested objects
                if prop_type == 'object' and 'properties' in prop_schema:
                    result.append(_format_schema(prop_schema, indent + 1))

                # Handle arrays
                elif prop_type == 'array' and 'items' in prop_schema:
                    items = prop_schema.get('items', {})
                    items_type = items.get('type', 'any')

                    result.append(f'{indent_str}  **Items Type**: {items_type}')

                    if items_type == 'object' and 'properties' in items:
                        result.append(_format_schema(items, indent + 2))

                # Handle enums
                if 'enum' in prop_schema:
                    enum_values = ', '.join([f'`{v}`' for v in prop_schema['enum']])
                    result.append(f'{indent_str}  **Allowed Values**: {enum_values}')

    elif schema_type == 'array':
        result.append(f'{indent_str}**Type**: Array')

        # Add items
        items = schema.get('items', {})
        items_type = items.get('type', 'any')

        result.append(f'{indent_str}**Items Type**: {items_type}')

        if items_type == 'object' and 'properties' in items:
            result.append(_format_schema(items, indent + 1))

        # Handle enum values in array items
        if 'enum' in items:
            enum_values = ', '.join([f'`{v}`' for v in items['enum']])
            result.append(f'{indent_str}**Allowed Values**: {enum_values}')

    else:
        result.append(f'{indent_str}**Type**: {schema_type}')

        # Add format if available
        if 'format' in schema:
            result.append(f'{indent_str}**Format**: {schema["format"]}')

        # Add enum if available
        if 'enum' in schema:
            enum_values = ', '.join([f'`{v}`' for v in schema['enum']])
            result.append(f'{indent_str}**Allowed Values**: {enum_values}')

    return '\n'.join(result)


def operation_prompt_fn(
    api_name: str,
    operation_id: str,
    mapping_type: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
) -> str:
    """Generate an operation prompt.

    Args:
        api_name: The name of the API
        operation_id: The operation ID
        mapping_type: The mapping type (function or resource)
        method: The HTTP method
        path: The API path
        summary: The operation summary
        description: The operation description
        parameters: The operation parameters
        request_body: The request body schema
        responses: The response schemas
        security: The security requirements

    Returns:
        str: The generated operation prompt

    """
    return generate_operation_prompt(
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        security=security,
    )


def create_operation_prompt(
    server: Any,
    api_name: str,
    operation_id: str,
    mapping_type: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
) -> None:
    """Create and add an operation prompt to the server.

    Args:
        server: The Model Context Protocol (MCP) server
        api_name: The name of the API
        operation_id: The operation ID
        mapping_type: The mapping type (function or resource)
        method: The HTTP method
        path: The API path
        summary: The operation summary
        description: The operation description
        parameters: The operation parameters
        request_body: The request body schema
        responses: The response schemas
        security: The security requirements

    """
    try:
        # Try to import the Prompt class from fastmcp
        from fastmcp.prompts.prompt import Prompt

        # Create a readable display name for the prompt
        display_name = f'{api_name} {format_display_name(operation_id)}'

        # Create the prompt using from_function
        prompt = Prompt.from_function(
            fn=operation_prompt_fn,
            name=display_name,
            description=f'Documentation for {operation_id} operation',
        )

        # Add the prompt to the server
        server._prompt_manager.add_prompt(prompt)
        logger.debug(f'Added operation prompt: {display_name}')
    except Exception as e:
        logger.warning(f'Failed to create operation prompt: {e}')


def is_complex_operation(
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
) -> bool:
    """Determine if an operation is complex.

    An operation is considered complex if it has:
    - More than 2 parameters
    - A request body with a complex schema
    - A response with a complex schema

    Args:
        parameters: The operation parameters
        request_body: The request body schema
        responses: The response schemas

    Returns:
        bool: True if the operation is complex, False otherwise

    """
    # Check parameters
    if len(parameters) > 2:
        return True

    # Check request body
    if request_body and 'content' in request_body:
        for content_type, content_schema in request_body['content'].items():
            schema = content_schema.get('schema', {})
            if _is_complex_schema(schema):
                return True

    # Check responses
    if responses:
        for status_code, response in responses.items():
            if 'content' in response:
                for content_type, content_schema in response['content'].items():
                    schema = content_schema.get('schema', {})
                    if _is_complex_schema(schema):
                        return True

    return False


def _is_complex_schema(schema: Dict[str, Any]) -> bool:
    """Determine if a schema is complex.

    A schema is considered complex if it:
    - Is an object with more than 3 properties
    - Is an array of objects
    - Has nested objects or arrays

    Args:
        schema: The JSON schema

    Returns:
        bool: True if the schema is complex, False otherwise

    """
    schema_type = schema.get('type')

    if schema_type == 'object':
        properties = schema.get('properties', {})

        # Check number of properties
        if len(properties) > 3:
            return True

        # Check for nested objects or arrays
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get('type')

            if prop_type == 'object' or prop_type == 'array':
                return True

    elif schema_type == 'array':
        items = schema.get('items', {})
        items_type = items.get('type')

        if items_type == 'object':
            return True

    return False
