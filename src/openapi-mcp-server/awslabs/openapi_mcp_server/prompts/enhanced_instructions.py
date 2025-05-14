"""Enhanced instructions generation for OpenAPI specifications.

This module provides improved prompt generation for OpenAPI specifications,
with more detailed and structured information about each tool.
"""

import re
from awslabs.openapi_mcp_server import get_caller_info, logger
from awslabs.openapi_mcp_server.utils.openapi_validator import extract_api_structure
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Set


# Try to import Prompt from different locations
try:
    from mcp.prompts import Prompt  # type: ignore
except ImportError:
    try:
        from fastmcp.prompts.prompt import Prompt  # type: ignore
    except ImportError:
        # Define a simple Prompt class if neither is available
        class Prompt:
            """Simple fallback implementation of Prompt class."""

            @staticmethod
            def from_function(fn: Any, name: str, description: str):
                """Create a simple prompt from a function."""
                return {'fn': fn, 'name': name, 'description': description}


def format_parameter_info(param: Dict[str, Any]) -> str:
    """Format parameter information in a readable way.

    Args:
        param: Parameter information

    Returns:
        str: Formatted parameter information
    """
    name = param.get('name', 'unknown')
    param_in = param.get('in', 'query')
    required = param.get('required', False)
    description = param.get('description', '')

    # Extract schema information if available
    schema_type = 'string'
    example = None
    enum_values = None

    if 'schema' in param:
        schema = param['schema']
        schema_type = schema.get('type', 'string')
        example = schema.get('example')
        enum_values = schema.get('enum')

    # Build the parameter description
    result = f'`{name}`'

    if required:
        result += ' (required)'
    else:
        result += ' (optional)'

    result += f' - {param_in} parameter'

    if schema_type:
        result += f', type: {schema_type}'

    if enum_values:
        enum_str = ', '.join([f'`{val}`' for val in enum_values[:5]])
        if len(enum_values) > 5:
            enum_str += ', ...'
        result += f', allowed values: [{enum_str}]'

    if example is not None:
        result += f', example: `{example}`'

    if description:
        result += f' - {description}'

    return result


def format_request_body_info(request_body: Dict[str, Any], components: Dict[str, Any]) -> str:
    """Format request body information in a readable way.

    Args:
        request_body: Request body information
        components: Components from OpenAPI spec

    Returns:
        str: Formatted request body information
    """
    if not request_body:
        return ''

    result = []
    required = request_body.get('required', False)

    if required:
        result.append('Request body is required.')
    else:
        result.append('Request body is optional.')

    content = request_body.get('content', {})
    for content_type, content_info in content.items():
        result.append(f'Content type: `{content_type}`')

        schema = content_info.get('schema', {})
        if '$ref' in schema:
            # Extract schema name from reference
            ref_parts = schema['$ref'].split('/')
            schema_name = ref_parts[-1]
            result.append(f'Schema: `{schema_name}`')

            # Try to get the actual schema from components
            if components and 'schemas' in components and schema_name in components['schemas']:
                actual_schema = components['schemas'][schema_name]

                # Add required fields
                if 'required' in actual_schema and actual_schema['required']:
                    required_fields = ', '.join(
                        [f'`{field}`' for field in actual_schema['required']]
                    )
                    result.append(f'Required fields: {required_fields}')

                # Add properties (limited to first 5)
                if 'properties' in actual_schema:
                    props = actual_schema['properties']
                    prop_count = 0
                    prop_lines = []

                    for prop_name, prop_info in props.items():
                        if prop_count >= 5:
                            prop_lines.append('...')
                            break

                        prop_type = prop_info.get('type', 'string')
                        prop_desc = prop_info.get('description', '')
                        prop_line = f'- `{prop_name}` ({prop_type})'

                        if prop_desc:
                            prop_line += f': {prop_desc}'

                        prop_lines.append(prop_line)
                        prop_count += 1

                    if prop_lines:
                        result.append('Properties:')
                        result.extend(prop_lines)
        else:
            # Direct schema definition
            schema_type = schema.get('type', 'object')
            result.append(f'Schema type: `{schema_type}`')

    return '\n'.join(result)


def format_response_info(responses: Dict[str, Any]) -> str:
    """Format response information in a readable way.

    Args:
        responses: Response information

    Returns:
        str: Formatted response information
    """
    if not responses:
        return ''

    result = []

    # Sort status codes to show success responses first
    status_codes = sorted(responses.keys(), key=lambda x: 0 if x.startswith('2') else 1)

    for status_code in status_codes[:3]:  # Limit to first 3 status codes
        response = responses[status_code]
        description = response.get('description', '')

        result.append(f'- Status {status_code}: {description}')

        # Add content types if available
        content_types = response.get('content_types', [])
        if content_types:
            content_str = ', '.join([f'`{ct}`' for ct in content_types])
            result.append(f'  Content types: {content_str}')

    if len(responses) > 3:
        result.append(f'- Plus {len(responses) - 3} more response types')

    return '\n'.join(result)


def generate_tool_description(
    operation_id: str,
    method: str,
    path: str,
    operation: Dict[str, Any],
    components: Dict[str, Any],
) -> str:
    """Generate a detailed description for a tool.

    Args:
        operation_id: Operation ID
        method: HTTP method
        path: API path
        operation: Operation information
        components: Components from OpenAPI spec

    Returns:
        str: Detailed tool description
    """
    # Start with summary and description
    summary = operation.get('summary', '')
    description = operation.get('description', '')

    result = []

    if summary:
        result.append(summary)

    if description and description != summary:
        result.append(description)

    # Add endpoint information
    result.append(f'\nEndpoint: `{method.upper()} {path}`')

    # Add parameters
    parameters = operation.get('parameters', [])
    if parameters:
        result.append('\nParameters:')
        for param in parameters:
            result.append(f'- {format_parameter_info(param)}')

    # Add request body if present
    request_body = operation.get('requestBody')
    if request_body:
        result.append('\nRequest Body:')
        result.append(format_request_body_info(request_body, components))

    # Add responses
    responses = operation.get('responses', {})
    if responses:
        result.append('\nResponses:')
        result.append(format_response_info(responses))

    # Add usage example
    result.append('\nUsage Example:')

    # Create a simplified example based on the parameters and request body
    example_params = []

    # Add path parameters
    path_params = [p for p in parameters if p.get('in') == 'path']
    for param in path_params:
        name = param.get('name', 'param')
        example = 'value'
        if 'schema' in param:
            if 'example' in param['schema']:
                example = param['schema']['example']
            elif 'enum' in param['schema'] and param['schema']['enum']:
                example = param['schema']['enum'][0]
            elif param['schema'].get('type') == 'integer':
                example = 1

        example_params.append(f'{name}={example}')

    # Add a few query parameters if present
    query_params = [p for p in parameters if p.get('in') == 'query']
    for param in query_params[:2]:  # Limit to 2 query parameters
        name = param.get('name', 'param')
        example = 'value'
        if 'schema' in param:
            if 'example' in param['schema']:
                example = param['schema']['example']
            elif 'enum' in param['schema'] and param['schema']['enum']:
                example = param['schema']['enum'][0]

        example_params.append(f"{name}='{example}'")

    # Add request body example if needed
    if request_body:
        example_params.append('data={...}')  # Simplified placeholder

    # Format the example
    if example_params:
        params_str = ', '.join(example_params)
        result.append(f'`{operation_id}({params_str})`')
    else:
        result.append(f'`{operation_id}()`')

    return '\n'.join(result)


def categorize_operations(operations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize operations into logical groups.

    Args:
        operations: List of operations

    Returns:
        Dict[str, List[Dict[str, Any]]]: Operations grouped by category
    """
    categories = {}

    # First pass: try to extract categories from operation IDs
    for operation in operations:
        operation_id = operation.get('operationId', '')

        # Try to extract a category from the operation ID
        category = None

        # Pattern: get|list|create|update|delete + Category
        match = re.match(
            r'^(get|list|create|update|delete|put|post)([A-Z][a-zA-Z]+)', operation_id
        )
        if match:
            category = match.group(2)

        # Pattern: Category + get|list|create|update|delete
        if not category:
            match = re.match(r'^([a-zA-Z]+)(Get|List|Create|Update|Delete)', operation_id)
            if match:
                category = match.group(1)

        # Pattern: get|list|create|update|delete + Category + Something
        if not category:
            match = re.match(r'^(get|list|create|update|delete)([A-Z][a-zA-Z]+)', operation_id)
            if match:
                category = match.group(2)

        # If we found a category, add the operation to it
        if category:
            if category not in categories:
                categories[category] = []
            categories[category].append(operation)
        else:
            # Default category
            if 'Other' not in categories:
                categories['Other'] = []
            categories['Other'].append(operation)

    # Second pass: try to group by path patterns
    if len(categories) <= 1:
        categories = {}
        path_categories = {}

        for operation in operations:
            path = operation.get('path', '')

            # Extract the first meaningful path segment
            path_parts = [p for p in path.split('/') if p and not p.startswith('{')]
            if path_parts:
                category = path_parts[0].capitalize()

                if category not in path_categories:
                    path_categories[category] = []
                path_categories[category].append(operation)
            else:
                if 'Other' not in path_categories:
                    path_categories['Other'] = []
                path_categories['Other'].append(operation)

        categories = path_categories

    return categories


async def generate_enhanced_api_instructions(
    server: FastMCP, api_name: str, openapi_spec: Dict[str, Any]
) -> None:
    """Generate enhanced dynamic instructions based on the OpenAPI spec.

    Args:
        server: The MCP server
        api_name: The name of the API
        openapi_spec: The OpenAPI specification
    """
    logger.info(f'Generating enhanced dynamic instructions for {api_name} API')

    # Get caller information for debugging
    caller_info = get_caller_info()
    logger.debug(f'Called from {caller_info}')

    # Extract API title and description
    api_title = openapi_spec.get('info', {}).get('title', api_name)
    api_description = openapi_spec.get('info', {}).get('description', '')
    api_version = openapi_spec.get('info', {}).get('version', '')

    logger.debug(f'API title: {api_title}')
    if api_description:
        logger.debug(f'API description length: {len(api_description)} characters')

    # Extract API structure
    api_structure = extract_api_structure(openapi_spec)

    # Build dynamic instructions
    instructions = f'# {api_title} API\n\n'

    if api_version:
        instructions += f'Version: {api_version}\n\n'

    if api_description:
        instructions += f'{api_description}\n\n'

    # Get all tools for this API
    try:
        # Ignore type error since FastMCP in newer versions has get_tools
        all_tools = await server.get_tools()  # type: ignore
        api_tools = [tool for tool in all_tools.values() if tool.name.startswith(f'{api_name}_')]
        logger.debug(f'Found {len(api_tools)} tools for API {api_name}')
    except Exception as e:
        logger.warning(f'Error getting tools: {e}')
        api_tools = []

    # Get all resources for this API
    try:
        # Ignore type error since FastMCP in newer versions has get_resources
        all_resources = await server.get_resources()  # type: ignore
        api_resources = [
            res for res in all_resources.values() if str(res.uri).startswith(f'{api_name}+')
        ]
        logger.debug(f'Found {len(api_resources)} resources for API {api_name}')
    except Exception as e:
        logger.warning(f'Error getting resources: {e}')
        api_resources = []

    # Add API overview
    instructions += '## API Overview\n\n'

    # Add statistics
    instructions += f'- **Endpoints**: {len(api_structure["paths"])}\n'
    instructions += f'- **Operations**: {len(api_structure["operations"])}\n'
    instructions += f'- **Data Models**: {len(api_structure["schemas"])}\n\n'

    # Categorize operations
    categories = categorize_operations(api_structure['operations'])

    # Add categorized operations
    instructions += '## Available Operations\n\n'

    for category, operations in categories.items():
        instructions += f'### {category}\n\n'

        for operation in operations:
            operation_id = operation.get('operationId', '')
            method = operation.get('method', 'GET')
            path = operation.get('path', '')
            summary = operation.get('summary', '')

            if not summary:
                summary = f'{method} {path}'

            instructions += f'- `{operation_id}` - {summary}\n'

        instructions += '\n'

    # Add detailed tool documentation
    instructions += '## Detailed API Reference\n\n'

    # Track which operations we've documented
    documented_operations: Set[str] = set()

    for category, operations in categories.items():
        instructions += f'### {category}\n\n'

        for operation in operations:
            operation_id = operation.get('operationId', '')
            method = operation.get('method', 'GET')
            path = operation.get('path', '')

            # Find the full operation details from the paths
            full_operation = None
            if path in api_structure['paths']:
                path_info = api_structure['paths'][path]
                method_lower = method.lower()

                if method_lower in path_info.get('methods', {}):
                    full_operation = path_info['methods'][method_lower]

            if full_operation:
                # Generate detailed description
                tool_description = generate_tool_description(
                    operation_id, method, path, full_operation, openapi_spec.get('components', {})
                )

                instructions += f'#### {operation_id}\n\n{tool_description}\n\n'
                documented_operations.add(operation_id)
            else:
                # Fallback if we can't find the full operation
                summary = operation.get('summary', '')
                instructions += f'#### {operation_id}\n\n{summary}\n\n'
                instructions += f'Endpoint: `{method} {path}`\n\n'
                documented_operations.add(operation_id)

    # Add resource information
    if api_resources:
        instructions += '## Available Resources\n\n'
        for resource in api_resources:
            # Extract short description (first line or sentence)
            short_desc = (
                resource.description.split('\n')[0].split('.')[0] if resource.description else ''
            )
            instructions += f'- **{resource.name}**: {short_desc}\n'
        instructions += '\n'

    # Add common usage patterns
    instructions += '## Common Usage Patterns\n\n'

    # Find common patterns based on the API structure
    has_pagination = False
    has_filtering = False
    has_sorting = False
    has_crud = False

    # Check for pagination parameters
    for path_info in api_structure['paths'].values():
        for method_info in path_info.get('methods', {}).values():
            for param in method_info.get('parameters', []):
                param_name = param.get('name', '').lower()
                if param_name in ['limit', 'page', 'pagesize', 'offset', 'size']:
                    has_pagination = True
                if param_name in ['filter', 'query', 'search', 'where']:
                    has_filtering = True
                if param_name in ['sort', 'sortby', 'orderby']:
                    has_sorting = True

    # Check for CRUD operations
    operation_methods = [op.get('method', '') for op in api_structure['operations']]
    if 'GET' in operation_methods and 'POST' in operation_methods:
        if 'PUT' in operation_methods or 'PATCH' in operation_methods:
            if 'DELETE' in operation_methods:
                has_crud = True

    # Add usage patterns based on what we found
    if has_crud:
        instructions += '### CRUD Operations\n\n'
        instructions += 'This API supports standard Create, Read, Update, Delete operations:\n\n'
        instructions += '- **Create**: Use POST operations to create new resources\n'
        instructions += '- **Read**: Use GET operations to retrieve resources\n'
        instructions += '- **Update**: Use PUT or PATCH operations to modify existing resources\n'
        instructions += '- **Delete**: Use DELETE operations to remove resources\n\n'

    if has_pagination:
        instructions += '### Pagination\n\n'
        instructions += 'Many list operations support pagination parameters:\n\n'
        instructions += '- Use `limit` or `pageSize` to control the number of results\n'
        instructions += '- Use `page` or `offset` to navigate through result pages\n\n'

    if has_filtering:
        instructions += '### Filtering\n\n'
        instructions += 'Some operations support filtering results:\n\n'
        instructions += (
            '- Use `filter`, `query`, or `search` parameters to narrow down results\n\n'
        )

    if has_sorting:
        instructions += '### Sorting\n\n'
        instructions += 'Some operations support sorting results:\n\n'
        instructions += '- Use `sort` or `orderBy` parameters to control result ordering\n\n'

    # Add best practices
    instructions += '## Best Practices\n\n'
    instructions += '- Always check response status codes for errors\n'
    instructions += '- Include all required parameters in your requests\n'
    instructions += '- Use pagination for large result sets\n'

    logger.info(f'Generated enhanced instructions for {api_name}: {instructions[:100]}...')

    # Create a prompt function that returns the dynamic instructions
    def api_instructions():
        """Return the API instructions as a list of messages."""
        return [{'role': 'user', 'content': instructions}]

    # Create a prompt from the function and add it to the server
    prompt = Prompt.from_function(
        fn=api_instructions,
        name=f'{api_name}_enhanced_instructions',
        description=f'Enhanced instructions for using the {api_name} API',
    )

    # Check if we're using the simple Prompt class or the real one
    if isinstance(prompt, dict):
        logger.warning(
            'Using simple Prompt implementation. Dynamic prompts may not work correctly.'
        )
        # In this case, we can't add the prompt to the server
        return

    # Add the prompt to the server
    try:
        server._prompt_manager.add_prompt(prompt)
        logger.info(f'Added enhanced {api_name}_enhanced_instructions prompt')
    except Exception as e:
        logger.error(f'Failed to add prompt: {e}')
        # Continue without the prompt if there's an error
