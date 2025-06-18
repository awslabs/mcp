# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Operation prompt generation for OpenAPI specifications."""

import inspect
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.models import (
    PromptArgument,
)
from fastmcp.prompts.prompt import Prompt
from fastmcp.prompts.prompt import PromptArgument as FastMCPPromptArgument
from fastmcp.server.openapi import RouteType
from typing import Any, Dict, List, Optional


def format_enum_values(enum_values: List[Any], max_inline: int = 4) -> str:
    """Format enum values in a token-efficient way.

    Args:
        enum_values: List of enum values
        max_inline: Maximum number of values to include inline

    Returns:
        Formatted enum string

    """
    if not enum_values:
        return ''

    # Handle short lists
    if len(enum_values) <= max_inline:
        # Format each value based on its type
        formatted_values = []
        for v in enum_values:
            if isinstance(v, str):
                formatted_values.append(f'"{v}"')
            else:
                formatted_values.append(str(v))
        return f'({", ".join(formatted_values)})'
    else:
        # For long lists, just show count
        return f'({len(enum_values)} possible values)'


def extract_prompt_arguments(
    parameters: List[Dict[str, Any]], request_body: Optional[Dict[str, Any]] = None
) -> List[PromptArgument]:
    """Extract prompt arguments from operation parameters and request body."""
    arguments = []
    used_names = set()

    # Process path and query parameters
    for param in parameters:
        if param.get('in') in ['path', 'query']:
            name = param.get('name', '')

            # Skip if we've already processed a parameter with this name
            if name in used_names:
                continue

            used_names.add(name)

            # Create concise description
            description = param.get('description', '')

            # Add enum values if available (token-efficient format)
            schema = param.get('schema', {})

            # Add default value if available
            if schema and 'default' in schema:
                default_value = schema['default']
                default_str = (
                    f'"{default_value}"' if isinstance(default_value, str) else str(default_value)
                )
                if description:
                    description += f'\nDefault: {default_str}'
                else:
                    description = f'Default: {default_str}'

            # Add enum values
            if schema and 'enum' in schema:
                enum_values = schema['enum']
                enum_str = format_enum_values(enum_values)

                # Add enum values to description
                if description:
                    description += f'\nAllowed values: {enum_str}'
                else:
                    description = f'Allowed values: {enum_str}'

            arguments.append(
                PromptArgument(
                    name=name,
                    description=description
                    or None,  # Use None instead of empty string for description
                    required=param.get('required', False),
                )
            )

    # Process request body if present
    if request_body and 'content' in request_body:
        for content_type, content_schema in request_body['content'].items():
            schema = content_schema.get('schema', {})
            if schema and schema.get('type') == 'object' and 'properties' in schema:
                required_fields = schema.get('required', [])

                # Process each property
                for prop_name, prop_schema in schema['properties'].items():
                    # Skip if we've already processed a parameter with this name
                    if prop_name in used_names:
                        continue

                    used_names.add(prop_name)

                    # Create description
                    description = prop_schema.get('description', '')

                    # Add default value if available
                    if 'default' in prop_schema:
                        default_value = prop_schema['default']
                        default_str = (
                            f'"{default_value}"'
                            if isinstance(default_value, str)
                            else str(default_value)
                        )
                        if description:
                            description += f'\nDefault: {default_str}'
                        else:
                            description = f'Default: {default_str}'

                    # Add enum values if available
                    if 'enum' in prop_schema:
                        enum_values = prop_schema['enum']
                        enum_str = format_enum_values(enum_values)

                        # Add enum values to description
                        if description:
                            description += f'\nAllowed values: {enum_str}'
                        else:
                            description = f'Allowed values: {enum_str}'

                    # Check if this property is required
                    is_required = prop_name in required_fields

                    arguments.append(
                        PromptArgument(
                            name=prop_name,
                            description=description
                            or None,  # Use None instead of empty string for description
                            required=is_required,
                        )
                    )

    return arguments


def determine_operation_type(server: Any, path: str, method: str) -> str:
    """Determine if an operation is mapped as a resource or tool."""
    # Default to tool if we can't determine
    operation_type = 'tool'

    # Check if server has route mappings
    if hasattr(server, '_openapi_router') and hasattr(server._openapi_router, '_routes'):
        routes = server._openapi_router._routes

        # Look for a matching route
        for route in routes:
            route_path = getattr(route, 'path', '')
            route_method = getattr(route, 'method', '')
            route_type = getattr(route, 'route_type', None)

            # Check if this route matches our operation
            if route_path == path and route_method.upper() == method.upper() and route_type:
                # Convert RouteType enum to string
                if route_type == RouteType.RESOURCE:
                    operation_type = 'resource'
                elif route_type == RouteType.RESOURCE_TEMPLATE:
                    operation_type = 'resource_template'
                elif route_type == RouteType.TOOL:
                    operation_type = 'tool'
                break

    return operation_type


def determine_mime_type(responses: Optional[Dict[str, Any]]) -> str:
    """Determine the MIME type for an operation response."""
    # Default to application/json
    mime_type = 'application/json'

    # Check responses section
    if responses:
        for status_code, response in responses.items():
            if status_code.startswith('2') and 'content' in response:
                mime_type = next(iter(response['content'].keys()), mime_type)
                break

    return mime_type


def generate_operation_documentation(
    operation_id: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
) -> str:
    """Generate documentation for an operation."""
    doc_lines = []

    # Add title (operation ID only)
    doc_lines.append(f'# {operation_id}')

    # Add summary or description (not both, to save tokens)
    if summary:
        doc_lines.append(f'\n{summary}')
    elif description:
        doc_lines.append(f'\n{description}')

    # Add method and path (token-efficient format)
    doc_lines.append(f'\n**{method.upper()}** `{path}`')

    # Add authentication requirements if present
    if security:
        auth_schemes = []
        for sec_req in security:
            for scheme, scopes in sec_req.items():
                scope_text = f' ({", ".join(scopes)})' if scopes else ''
                auth_schemes.append(f'{scheme}{scope_text}')

        if auth_schemes:
            doc_lines.append(f'\n**Auth**: {", ".join(auth_schemes)}')

    # Add parameters section (only if parameters exist)
    if parameters:
        # Group parameters by location
        path_params = [p for p in parameters if p.get('in') == 'path']
        query_params = [p for p in parameters if p.get('in') == 'query']

        # Add path parameters (concise format)
        if path_params:
            doc_lines.append('\n**Path parameters:**')
            for param in path_params:
                name = param.get('name', '')
                required = '*' if param.get('required', False) else ''

                # Add enum values inline if available
                schema = param.get('schema', {})
                enum_str = ''
                if schema and 'enum' in schema:
                    enum_values = schema['enum']
                    enum_str = ' ' + format_enum_values(enum_values)

                doc_lines.append(f'- {name}{required}{enum_str}')

        # Add query parameters (concise format)
        if query_params:
            doc_lines.append('\n**Query parameters:**')
            for param in query_params:
                name = param.get('name', '')
                required = '*' if param.get('required', False) else ''

                # Add enum values inline if available
                schema = param.get('schema', {})
                enum_str = ''
                if schema and 'enum' in schema:
                    enum_values = schema['enum']
                    enum_str = ' ' + format_enum_values(enum_values)

                doc_lines.append(f'- {name}{required}{enum_str}')

    # Add request body section with enum handling
    if request_body and 'content' in request_body:
        doc_lines.append(
            '\n**Request body:** Required'
            if request_body.get('required')
            else '\n**Request body:** Optional'
        )

        # Add schema information if available
        content = next(iter(request_body.get('content', {}).items()), None)
        if content:
            content_type, content_schema = content
            schema = content_schema.get('schema', {})

            if schema and schema.get('type') == 'object' and 'properties' in schema:
                required_fields = schema.get('required', [])

                # Add required fields with enum values
                if required_fields:
                    doc_lines.append('\n**Required fields:**')
                    for field in required_fields:
                        if field in schema['properties']:
                            prop_schema = schema['properties'][field]

                            # Add enum values if available
                            enum_str = ''
                            if 'enum' in prop_schema:
                                enum_values = prop_schema['enum']
                                enum_str = ' ' + format_enum_values(enum_values)

                            doc_lines.append(f'- {field}{enum_str}')

    # Add response codes (only success and common errors)
    if responses:
        success_codes = [code for code in responses.keys() if code.startswith('2')]
        error_codes = [code for code in responses.keys() if code.startswith(('4', '5'))]

        if success_codes or error_codes:
            doc_lines.append('\n**Responses:**')

            # Add success codes
            for code in success_codes[:1]:  # Only first success code for token efficiency
                doc_lines.append(f'- {code}: {responses[code].get("description", "Success")}')

            # Add error codes (limited to common ones)
            for code in error_codes[:2]:  # Only first two error codes for token efficiency
                doc_lines.append(f'- {code}: {responses[code].get("description", "Error")}')

    # Add example usage
    doc_lines.append('\n**Example usage:**')
    doc_lines.append('```python')

    # Create example based on operation type
    if method.lower() == 'get':
        # For GET operations
        param_str = ''
        if parameters:
            required_params = [p for p in parameters if p.get('required')]
            if required_params:
                param_examples = []
                for param in required_params:
                    name = param.get('name', '')
                    schema = param.get('schema', {})

                    # Use enum value as example if available
                    if schema and 'enum' in schema and schema['enum']:
                        example_value = (
                            f'"{schema["enum"][0]}"'
                            if isinstance(schema['enum'][0], str)
                            else schema['enum'][0]
                        )
                        param_examples.append(f'{name}={example_value}')
                    else:
                        param_examples.append(f'{name}="value"')

                param_str = ', '.join(param_examples)

        doc_lines.append(f'response = await {operation_id}({param_str})')

    elif method.lower() == 'post':
        # For POST operations
        if request_body:
            doc_lines.append('data = {')

            # Add required fields with example values
            content = next(iter(request_body.get('content', {}).items()), None)
            if content:
                content_type, content_schema = content
                schema = content_schema.get('schema', {})

                if schema and schema.get('type') == 'object' and 'properties' in schema:
                    required_fields = schema.get('required', [])

                    for field in required_fields:
                        if field in schema['properties']:
                            prop_schema = schema['properties'][field]
                            prop_type = prop_schema.get('type', 'string')

                            # Use enum value as example if available
                            if 'enum' in prop_schema and prop_schema['enum']:
                                if prop_type == 'string':
                                    doc_lines.append(f'    "{field}": "{prop_schema["enum"][0]}",')
                                else:
                                    doc_lines.append(f'    "{field}": {prop_schema["enum"][0]},')
                            else:
                                # Use type-appropriate example
                                if prop_type == 'string':
                                    doc_lines.append(f'    "{field}": "example",')
                                elif prop_type == 'integer' or prop_type == 'number':
                                    doc_lines.append(f'    "{field}": 0,')
                                elif prop_type == 'boolean':
                                    doc_lines.append(f'    "{field}": False,')
                                elif prop_type == 'array':
                                    doc_lines.append(f'    "{field}": [],')
                                elif prop_type == 'object':
                                    doc_lines.append(f'    "{field}": {{}},')

            doc_lines.append('}')
            doc_lines.append(f'response = await {operation_id}(data)')
        else:
            doc_lines.append(f'response = await {operation_id}()')

    else:
        # For other operations
        param_str = ''
        if parameters:
            required_params = [p for p in parameters if p.get('required')]
            if required_params:
                param_examples = []
                for param in required_params:
                    name = param.get('name', '')
                    schema = param.get('schema', {})

                    # Use enum value as example if available
                    if schema and 'enum' in schema and schema['enum']:
                        example_value = (
                            f'"{schema["enum"][0]}"'
                            if isinstance(schema['enum'][0], str)
                            else schema['enum'][0]
                        )
                        param_examples.append(f'{name}={example_value}')
                    else:
                        param_examples.append(f'{name}="value"')

                param_str = ', '.join(param_examples)

        doc_lines.append(f'response = await {operation_id}({param_str})')

    doc_lines.append('```')

    return '\n'.join(doc_lines)


def create_operation_prompt(
    server: Any,
    api_name: str,
    operation_id: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    parameters: List[Dict[str, Any]],
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
    paths: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create and register an operation prompt with the server.

    Args:
        server: MCP server instance
        api_name: Name of the API
        operation_id: Operation ID
        method: HTTP method
        path: API path
        summary: Operation summary
        description: Operation description
        parameters: Operation parameters
        request_body: Request body schema
        responses: Response schemas
        security: Security requirements
        paths: OpenAPI paths object

    Returns:
        bool: True if prompt was registered successfully, False otherwise

    """
    try:
        # Determine operation type
        operation_type = determine_operation_type(server, path, method)

        # Generate documentation
        documentation = generate_operation_documentation(
            operation_id=operation_id,
            method=method,
            path=path,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=security,
        )

        # Extract arguments from parameters and request body
        prompt_arguments = extract_prompt_arguments(parameters, request_body)

        # Create a function that returns messages for this operation
        # We need to create a function with the exact parameters we want to expose
        # Instead of using exec(), we'll use a function factory approach

        # Create a generic handler that will be wrapped with the correct signature
        def generic_handler(doc, op_type, api_name_val, path_val, resp, args, *args_values):
            """Handle operation prompts generically."""
            # Create a dictionary of parameter values
            param_values = {}
            for i, arg in enumerate(args):
                if i < len(args_values):
                    param_values[arg.name] = args_values[i]

            # Create messages
            messages = [{'role': 'user', 'content': {'type': 'text', 'text': doc}}]

            # For resources, add resource reference
            if op_type in ['resource', 'resource_template']:
                # Determine MIME type
                mime_type = determine_mime_type(resp)

                # Create resource URI
                resource_uri = f'api://{api_name_val}{path_val}'

                # Add resource reference message
                messages.append(
                    {
                        'role': 'user',
                        'content': {
                            'type': 'resource',
                            'resource': {'uri': resource_uri, 'mimeType': mime_type},
                        },
                    }
                )

            logger.debug(f'Operation {operation_id} returning {len(messages)} messages')
            return messages

        # Create a function with the correct signature using functools.partial
        from functools import partial

        # Create a partial function with the fixed arguments
        handler_with_fixed_args = partial(
            generic_handler,
            documentation,
            operation_type,
            api_name,
            path,
            responses,
            prompt_arguments,
        )

        # Define a function to create the appropriate operation function using inspect.Signature
        def create_operation_function():
            # Create a base function that will be wrapped with the correct signature
            def base_fn(*args, **kwargs):
                # Map positional args to their parameter names
                param_names = [p.name for p in inspect.signature(base_fn).parameters.values()]
                named_args = dict(zip(param_names, args))
                named_args.update(kwargs)

                # Extract the values in the correct order for handler_with_fixed_args
                arg_values = []
                for arg in prompt_arguments:
                    arg_values.append(named_args.get(arg.name))

                return handler_with_fixed_args(*arg_values)

            # Create parameters for the signature
            # Sort arguments so required parameters come first, followed by optional parameters
            required_args = [arg for arg in prompt_arguments if arg.required]
            optional_args = [arg for arg in prompt_arguments if not arg.required]

            # Create parameters list with required parameters first
            parameters = []

            # Add required parameters (no default value)
            for arg in required_args:
                param = inspect.Parameter(arg.name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                parameters.append(param)

            # Add optional parameters (with default=None)
            for arg in optional_args:
                param = inspect.Parameter(
                    arg.name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None
                )
                parameters.append(param)

            # Create a new signature
            sig = inspect.Signature(parameters, return_annotation=List[Dict[str, Any]])

            # Apply the signature to the function
            base_fn.__signature__ = sig
            base_fn.__name__ = 'operation_fn'
            base_fn.__doc__ = documentation

            return base_fn

        # Create the operation function
        operation_fn = create_operation_function()

        # Register the function as a prompt
        if hasattr(server, '_prompt_manager'):
            # Create tags based on operation metadata
            tags = set()
            # Get tags from the OpenAPI operation object if available
            if isinstance(method, str) and paths is not None and path in paths:
                path_item = paths.get(path, {})
                if method.lower() in path_item:
                    op = path_item[method.lower()]
                    if 'tags' in op and isinstance(op.get('tags'), list):
                        for tag in op.get('tags', []):
                            if isinstance(tag, str):
                                tags.add(tag)

            # Create a list of FastMCPPromptArgument objects for the Prompt
            prompt_args = []
            for arg in prompt_arguments:
                # Use the actual parameter name from the OpenAPI schema
                prompt_args.append(
                    FastMCPPromptArgument(
                        name=arg.name, description=arg.description, required=arg.required
                    )
                )

            # Create a prompt from the function
            prompt = Prompt.from_function(
                fn=operation_fn,
                name=operation_id,
                description=summary or description or f'{method.upper()} {path}',
                tags=tags,
            )

            # Update the arguments with descriptions
            prompt.arguments = prompt_args

            # Add the prompt to the server
            server._prompt_manager.add_prompt(prompt)
            logger.debug(
                f'Added operation prompt: {operation_id} with arguments: {[arg.name for arg in prompt.arguments]}'
            )
            return True
        else:
            logger.warning('Server does not have _prompt_manager')
            return False

    except Exception as e:
        logger.warning(f'Failed to create operation prompt: {e}')
        return False
