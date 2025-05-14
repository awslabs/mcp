"""Instructions generation for OpenAPI specifications."""

from awslabs.openapi_mcp_server import get_caller_info, logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Tuple


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

    # Add tool information
    if api_tools:
        instructions += '## Available Tools\n\n'
        # Group tools by their purpose/category based on name patterns
        tool_categories = {}

        for tool in api_tools:
            # Extract category from tool name (e.g., petstore_getPet -> getPet)
            name_parts = tool.name.split('_', 1)
            if len(name_parts) > 1:
                category = name_parts[1]
                if category not in tool_categories:
                    tool_categories[category] = []
                tool_categories[category].append(tool)
            else:
                # Fallback if no category can be determined
                if 'other' not in tool_categories:
                    tool_categories['other'] = []
                tool_categories['other'].append(tool)

        # List tools by category
        for category, tools in tool_categories.items():
            instructions += f'### {category.capitalize()} Operations\n\n'
            for tool in tools:
                # Extract short description (first line or sentence)
                short_desc = tool.description.split('\n')[0].split('.')[0]
                instructions += f'- **{tool.name}**: {short_desc}\n'
            instructions += '\n'

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

    # Generate dynamic usage examples based on the OpenAPI spec
    instructions += '\n## Common Usage Examples\n\n'

    # Find GET endpoints for listing/retrieving data
    get_endpoints: List[Tuple[str, Dict[str, Any]]] = []
    post_endpoints: List[Tuple[str, Dict[str, Any]]] = []
    put_endpoints: List[Tuple[str, Dict[str, Any]]] = []

    # Extract endpoints from paths
    if 'paths' in openapi_spec:
        for path, path_item in openapi_spec['paths'].items():
            if 'get' in path_item:
                get_endpoints.append((path, path_item['get']))
            if 'post' in path_item:
                post_endpoints.append((path, path_item['post']))
            if 'put' in path_item:
                put_endpoints.append((path, path_item['put']))

    # Add examples for GET endpoints (retrieving data)
    if get_endpoints:
        # Sort by path length to prioritize simpler endpoints
        get_endpoints.sort(key=lambda x: len(x[0]))
        # Take up to 2 GET examples
        for _, (path, operation) in enumerate(get_endpoints[:2]):
            operation_id = operation.get('operationId', f'get{path}')
            tool_name = f'{api_name}_{operation_id}'

            # Check if this is a path with parameters
            if '{' in path and '}' in path:
                param_name = path[path.find('{') + 1 : path.find('}')]
                path_part = path.split('/')[-1].replace('{' + param_name + '}', '')
                instructions += (
                    f'- Get {path_part} details: Use `{tool_name}` with {param_name}=<value>\n'
                )
            else:
                # Check for query parameters
                if 'parameters' in operation:
                    query_params = [p for p in operation['parameters'] if p.get('in') == 'query']
                    if query_params:
                        param = query_params[0]
                        param_name = param.get('name', 'parameter')
                        param_example = 'value'
                        if 'schema' in param:
                            if 'enum' in param['schema']:
                                param_example = f'"{param["schema"]["enum"][0]}"'
                            elif 'example' in param['schema']:
                                param_example = f'"{param["schema"]["example"]}"'
                        path_part = path.split('/')[-1]
                        instr = f'- List {path_part}: Use `{tool_name}` with {param_name}='
                        instructions += f'{instr}{param_example}\n'
                    else:
                        instructions += f'- Get {path.split("/")[-1]}: Use `{tool_name}`\n'
                else:
                    instructions += f'- Get {path.split("/")[-1]}: Use `{tool_name}`\n'

    # Add examples for POST endpoints (creating data)
    if post_endpoints:
        post_endpoints.sort(key=lambda x: len(x[0]))
        # Take 1 POST example
        for path, operation in post_endpoints[:1]:
            operation_id = operation.get('operationId', f'post{path}')
            tool_name = f'{api_name}_{operation_id}'
            instructions += f'- Create new {path.split("/")[-1]}: Use `{tool_name}` with required information\n'

    # Add examples for PUT endpoints (updating data)
    if put_endpoints:
        put_endpoints.sort(key=lambda x: len(x[0]))
        # Take 1 PUT example
        for path, operation in put_endpoints[:1]:
            operation_id = operation.get('operationId', f'put{path}')
            tool_name = f'{api_name}_{operation_id}'
            instructions += (
                f'- Update {path.split("/")[-1]}: Use `{tool_name}` with required information\n'
            )

    # Add important notes based on schema requirements
    instructions += '\n### Important Notes\n'

    # Extract common data types and constraints
    id_fields: List[str] = []
    enum_fields: List[Tuple[str, List[str]]] = []
    required_fields: List[str] = []

    if 'components' in openapi_spec and 'schemas' in openapi_spec['components']:
        schemas = openapi_spec['components']['schemas']

        # Find ID fields, enum fields, and required fields
        for _, schema in schemas.items():
            if 'properties' in schema:
                for prop_name, prop in schema['properties'].items():
                    # Check for ID fields
                    if prop_name.lower().endswith('id') and prop.get('type') == 'integer':
                        id_fields.append(prop_name)

                    # Check for enum fields
                    if 'enum' in prop:
                        enum_values = prop['enum']
                        if len(enum_values) <= 5:  # Only include small enums
                            enum_fields.append((prop_name, enum_values))

                # Check for required fields
                if 'required' in schema and len(schema['required']) > 0:
                    for req_field in schema['required']:
                        if req_field not in required_fields:
                            required_fields.append(req_field)

    # Add notes about ID fields
    if id_fields:
        unique_id_fields = list(set(id_fields))
        if len(unique_id_fields) <= 3:
            instructions += f'- {", ".join(unique_id_fields)} must be integers\n'
        else:
            instructions += '- ID fields must be integers\n'

    # Add notes about enum fields
    for field_name, enum_values in enum_fields[:2]:  # Limit to 2 enum fields
        enum_str = ', '.join([f"'{val}'" for val in enum_values])
        instructions += f'- {field_name} values must be one of: {enum_str}\n'

    # Add notes about required fields
    if required_fields:
        if len(required_fields) <= 5:
            instructions += (
                f'- When creating or updating, {", ".join(required_fields)} are required fields\n'
            )
        else:
            instructions += (
                '- Make sure to include all required fields when creating or updating resources\n'
            )

    logger.info(f'Generated instructions for {api_name}: {instructions[:100]}...')

    # Create a prompt function that returns the dynamic instructions
    def api_instructions():
        """Return the API instructions as a list of messages."""
        return [{'role': 'user', 'content': instructions}]

    # Create a prompt from the function and add it to the server
    prompt = Prompt.from_function(
        fn=api_instructions,
        name=f'{api_name}_instructions',
        description=f'Dynamic instructions for using the {api_name} API',
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
        logger.info(f'Added dynamic {api_name}_instructions prompt')
    except Exception as e:
        logger.error(f'Failed to add prompt: {e}')
        # Continue without the prompt if there's an error
