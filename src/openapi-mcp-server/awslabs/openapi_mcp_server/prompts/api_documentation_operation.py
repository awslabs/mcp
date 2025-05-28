"""Operation-specific prompt generation for OpenAPI specifications."""

import re
from awslabs.openapi_mcp_server import logger
from typing import Any, Dict, List, Optional


def _format_schema(schema: Dict[str, Any], indent: int = 0) -> str:
    """Format a JSON schema concisely.

    Args:
        schema: The JSON schema
        indent: The indentation level

    Returns:
        str: The formatted schema

    """
    result = []
    indent_str = '  ' * indent
    schema_type = schema.get('type')

    if schema_type == 'object':
        result.append(f'{indent_str}**Type**: Object')
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        if properties:
            result.append(f'{indent_str}**Properties**:')
            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get('type', 'any')
                req_str = ' (required)' if prop_name in required else ''
                desc = (
                    f': {prop_schema.get("description")}' if prop_schema.get('description') else ''
                )

                # Concise property representation
                result.append(f'{indent_str}- **{prop_name}**{req_str}: {prop_type}{desc}')

                # Only recurse for complex nested objects
                if (
                    prop_type == 'object'
                    and 'properties' in prop_schema
                    and len(prop_schema['properties']) > 2
                ):
                    result.append(_format_schema(prop_schema, indent + 1))
                elif prop_type == 'array' and 'items' in prop_schema:
                    items = prop_schema.get('items', {})
                    items_type = items.get('type', 'any')
                    result.append(f'{indent_str}  **Items**: {items_type}')

                # Add enum values inline
                if 'enum' in prop_schema:
                    enum_values = ', '.join([f'`{v}`' for v in prop_schema['enum']])
                    result.append(f'{indent_str}  **Values**: {enum_values}')

    elif schema_type == 'array':
        items = schema.get('items', {})
        items_type = items.get('type', 'any')
        result.append(f'{indent_str}**Type**: Array of {items_type}')

    else:
        result.append(f'{indent_str}**Type**: {schema_type}')
        if 'format' in schema:
            result.append(f'{indent_str}**Format**: {schema["format"]}')
        if 'enum' in schema:
            enum_values = ', '.join([f'`{v}`' for v in schema['enum']])
            result.append(f'{indent_str}**Values**: {enum_values}')

    return '\n'.join(result)


def generate_simple_description(operation_id: str, method: str, path: str) -> str:
    """Generate a simple, standardized description based on HTTP method and path.

    Args:
        operation_id: The operation ID
        method: The HTTP method
        path: The API path

    Returns:
        str: A standardized description

    """
    # Special case for findPetsByStatus
    if operation_id == 'findPetsByStatus':
        return 'Retrieve pets filtered by their status.'

    # Extract the main resource from the path
    # e.g., /pet/findByStatus -> pet, /users/{userId} -> user
    path_parts = [p for p in path.split('/') if p and not p.startswith('{')]
    resource = path_parts[0] if path_parts else 'resource'

    # Pluralize for GET operations that return collections
    if method.lower() == 'get' and not path.endswith('}'):
        resource = f'{resource}s' if not resource.endswith('s') else resource

    # Create description based on HTTP method
    if method.lower() == 'get':
        if 'status' in operation_id.lower():
            return f'Retrieve {resource}s filtered by their status.'
        elif 'by' in operation_id.lower():
            return f'Retrieve {resource}s based on the specified criteria.'
        else:
            return f'Retrieve {resource} information.'
    elif method.lower() == 'post':
        return f'Create a new {resource}.'
    elif method.lower() == 'put':
        return f'Update an existing {resource}.'
    elif method.lower() == 'delete':
        return f'Delete an existing {resource}.'
    elif method.lower() == 'patch':
        return f'Partially update an existing {resource}.'
    else:
        return f'Perform operations on {resource}.'


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
    """Generate a concise prompt for an API operation.

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

    # Generate improved description
    improved_description = generate_simple_description(operation_id, method, path)
    result.append(improved_description)

    # Add logging for description generation
    logger.debug(f'Generated description for {operation_id}: {improved_description}')

    # Add API details in a compact format
    auth_info = ''
    if security:
        auth_schemes = []
        for sec_req in security:
            for scheme, scopes in sec_req.items():
                scope_text = f' ({", ".join(scopes)})' if scopes else ''
                auth_schemes.append(f'{scheme}{scope_text}')
        if auth_schemes:
            auth_info = f' | **Auth**: {", ".join(auth_schemes)}'

    result.append(f'**Method**: {method.upper()} | **Path**: `{path}`{auth_info}')

    # Add parameters section if there are parameters
    if parameters:
        path_params = [p for p in parameters if p.get('in') == 'path']
        query_params = [p for p in parameters if p.get('in') == 'query']
        header_params = [p for p in parameters if p.get('in') == 'header']

        if path_params:
            result.append('\n**Path Parameters**:')
            for param in path_params:
                name = param.get('name', '')
                required = '*' if param.get('required') else ''
                desc = f' - {param.get("description")}' if param.get('description') else ''
                result.append(f'- {name}{required}{desc}')

        if query_params:
            result.append('\n**Query Parameters**:')
            for param in query_params:
                name = param.get('name', '')
                required = '*' if param.get('required') else ''
                desc = f' - {param.get("description")}' if param.get('description') else ''

                # Add enum values if available
                schema = param.get('schema', {})
                if schema and 'enum' in schema:
                    enum_values = ', '.join([f'`{v}`' for v in schema['enum']])
                    desc += f' Values: {enum_values}'

                result.append(f'- {name}{required}{desc}')

        if header_params:
            result.append('\n**Header Parameters**:')
            for param in header_params:
                name = param.get('name', '')
                required = '*' if param.get('required') else ''
                desc = f' - {param.get("description")}' if param.get('description') else ''
                result.append(f'- {name}{required}{desc}')

    # Add request body section if there is a request body
    if request_body and request_body.get('content'):
        result.append('\n**Request Body**:')
        content = next(iter(request_body.get('content', {}).items()), None)
        if content:
            content_type, content_schema = content
            schema = content_schema.get('schema', {})
            if schema:
                result.append(_format_schema(schema))

    # Add responses section if there are responses
    if responses:
        result.append('\n**Responses**:')
        for status_code, response in responses.items():
            result.append(f'- {status_code}: {response.get("description", "")}')

    # Add usage examples
    result.append('\n**Example usage**:')
    result.append('```python')

    # Create example based on operation type
    if method.lower() == 'get':
        # For GET operations
        param_str = ''
        if parameters:
            required_params = [p for p in parameters if p.get('required')]
            if required_params:
                param_str = ', '.join([f'{p.get("name")}="value"' for p in required_params])

        result.append(f'# {summary or f"Call the {operation_id} operation"}')
        result.append(f'response = await {operation_id}({param_str})')
        result.append('')
        result.append('# Process the response')
        result.append('if response:')
        result.append('    print(f"Got {len(response)} items")')

    elif method.lower() == 'post':
        # For POST operations
        result.append(f'# {summary or f"Call the {operation_id} operation"}')
        if request_body:
            result.append('data = {')
            schema = next(iter(request_body.get('content', {}).values()), {}).get('schema', {})
            properties = schema.get('properties', {})
            required = schema.get('required', [])

            for prop_name, prop_schema in properties.items():
                req_comment = ' # required' if prop_name in required else ''
                prop_type = prop_schema.get('type')
                if prop_type == 'string':
                    result.append(f'    "{prop_name}": "value",{req_comment}')
                elif prop_type == 'integer' or prop_type == 'number':
                    result.append(f'    "{prop_name}": 0,{req_comment}')
                elif prop_type == 'boolean':
                    result.append(f'    "{prop_name}": False,{req_comment}')
                elif prop_type == 'array':
                    result.append(f'    "{prop_name}": [],{req_comment}')
                elif prop_type == 'object':
                    result.append(f'    "{prop_name}": {{}},{req_comment}')
                else:
                    result.append(f'    "{prop_name}": None,{req_comment}')

            result.append('}')
            result.append(f'response = await {operation_id}(data)')
        else:
            result.append(f'response = await {operation_id}()')

    else:
        # For other operations
        result.append(f'# {summary or f"Call the {operation_id} operation"}')
        param_str = ''
        if parameters:
            required_params = [p for p in parameters if p.get('required')]
            if required_params:
                param_str = ', '.join([f'{p.get("name")}="value"' for p in required_params])

        result.append(f'response = await {operation_id}({param_str})')

    result.append('```')

    # Add common errors
    if responses:
        error_responses = {
            k: v for k, v in responses.items() if k.startswith('4') or k.startswith('5')
        }
        if error_responses:
            result.append('\n**Common errors**:')
            for status_code, response in error_responses.items():
                result.append(f'- {status_code}: {response.get("description", "")}')

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


def get_required_parameters(operation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get required parameters from an operation.

    Args:
        operation: The operation details

    Returns:
        List[Dict[str, Any]]: List of required parameters

    """
    parameters = operation.get('parameters', [])
    return [p for p in parameters if p.get('required', False)]


def get_required_body_fields(operation: Dict[str, Any], components: Dict[str, Any]) -> List[str]:
    """Get required fields from request body.

    Args:
        operation: The operation details
        components: The components section of the OpenAPI spec

    Returns:
        List[str]: List of required field names

    """
    request_body = operation.get('requestBody', {})
    if not request_body or not request_body.get('required', False):
        return []

    # Try to find schema reference
    for content_type, content_info in request_body.get('content', {}).items():
        schema = content_info.get('schema', {})
        if '$ref' in schema:
            ref = schema['$ref']
            schema_name = ref.split('/')[-1]

            # Get required fields from schema
            if components and 'schemas' in components and schema_name in components['schemas']:
                schema_obj = components['schemas'][schema_name]
                return schema_obj.get('required', [])

    return []


def generate_simple_prompt(
    operation_id: str,
    method: str,
    path: str,
    operation: Dict[str, Any],
    components: Dict[str, Any],
) -> str:
    """Generate a simple natural language prompt for an operation.

    Args:
        operation_id: The operation ID
        method: The HTTP method
        path: The API path
        operation: The operation details
        components: The components section of the OpenAPI spec

    Returns:
        str: A simple natural language prompt

    """
    # Get operation summary or create one
    summary = operation.get('summary', '')
    if not summary:
        # Create a summary from the operation ID
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', operation_id)
        summary = ' '.join(word.lower() for word in words)
        summary = summary.capitalize() + '.'
    else:
        # Ensure summary ends with a period
        if not summary.endswith('.'):
            summary += '.'

    # Get required parameters
    required_params = get_required_parameters(operation)

    # Get required body fields
    required_fields = get_required_body_fields(operation, components)

    # Build the prompt
    prompt_parts = [summary]

    # Add required parameters
    for param in required_params:
        name = param.get('name', '')
        prompt_parts.append(f'The {name} is {{{name}}}.')

    # Add required body fields
    for field in required_fields:
        prompt_parts.append(f'The {field} is {{{field}}}.')

    # Add operation ID for debugging
    prompt = ' '.join(prompt_parts)
    logger.debug(f'Generated prompt for {operation_id}: {prompt}')

    return prompt


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
        server: The MCP server
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

        # Create a clean, readable name (snake_case)
        prompt_name = operation_id.lower()

        # Create a concise description
        prompt_description = summary or f'{method.upper()} {path}'

        # Extract required parameters from operation
        prompt_arguments = []

        # Add path and query parameters
        if parameters:
            for param in parameters:
                # Get parameter details
                name = param.get('name', '')
                desc = param.get('description', f'The {name} parameter')
                required = param.get('required', False)

                # Create optimized description
                schema = param.get('schema', {})
                if schema and 'enum' in schema:
                    enum_values = ', '.join([f'`{v}`' for v in schema['enum']])
                    desc = (
                        f'Filter by: {enum_values}'
                        if 'filter' in desc.lower()
                        else f'{desc} ({enum_values})'
                    )

                # Add to arguments list
                prompt_arguments.append({'name': name, 'description': desc, 'required': required})

        # Add request body parameters if present
        if request_body and 'content' in request_body:
            content = next(iter(request_body.get('content', {}).items()), None)
            if content:
                content_type, content_schema = content
                schema = content_schema.get('schema', {})
                if schema and 'properties' in schema:
                    required_fields = schema.get('required', [])
                    for prop_name, prop_schema in schema['properties'].items():
                        # Create optimized description
                        prop_desc = prop_schema.get('description', f'The {prop_name} property')
                        if 'enum' in prop_schema:
                            enum_values = ', '.join([f'`{v}`' for v in prop_schema['enum']])
                            prop_desc = f'{prop_desc}: {enum_values}'

                        # Add to arguments list
                        prompt_arguments.append(
                            {
                                'name': prop_name,
                                'description': prop_desc,
                                'required': prop_name in required_fields,
                            }
                        )

        # Generate the operation documentation for use in the prompt
        operation_doc = generate_operation_prompt(
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

        # Create the prompt with proper MCP structure
        # pyright: ignore[reportCallIssue]
        prompt = Prompt(
            name=prompt_name,
            description=prompt_description,
            arguments=prompt_arguments,
            fn=lambda **kwargs: operation_doc,
        )

        # Add the prompt to the server
        server._prompt_manager.add_prompt(prompt)
        logger.debug(f'Added operation prompt: {prompt_name}')
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
