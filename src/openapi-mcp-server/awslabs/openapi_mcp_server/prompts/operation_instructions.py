"""Operation-specific instructions generation for OpenAPI specifications."""

import re
from awslabs.openapi_mcp_server import get_caller_info, logger
from awslabs.openapi_mcp_server.utils.config import ENABLE_OPERATION_PROMPTS
from mcp.server.fastmcp import FastMCP
from typing import Any, Callable, Dict, List, Protocol, Union, cast


# Define a protocol for server objects that can add prompts
class PromptServer(Protocol):
    """Protocol for server objects that can add prompts."""

    def add_prompt(self, *args: Any, **kwargs: Any) -> Any:
        """Add a prompt to the server."""
        ...


# Import Prompt directly
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
            def from_function(fn: Callable, name: str, description: str):
                """Create a simple prompt from a function."""
                return {'fn': fn, 'name': name, 'description': description}


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


async def generate_operation_prompts(
    server: Union[FastMCP, PromptServer], api_name: str, openapi_spec: Dict[str, Any]
) -> None:
    """Generate simple natural language prompts for each API operation.

    Args:
        server: The MCP server
        api_name: The name of the API
        openapi_spec: The OpenAPI specification
    """
    # Check if operation prompts are enabled
    if not ENABLE_OPERATION_PROMPTS:
        logger.info('Operation prompts generation is disabled by ENABLE_OPERATION_PROMPTS')
        return

    logger.info(f'Generating operation-specific prompts for {api_name} API')

    # Get caller information for debugging
    caller_info = get_caller_info()
    logger.debug(f'Called from {caller_info}')

    # Extract paths and operations from the spec
    paths = openapi_spec.get('paths', {})
    if not paths:
        logger.warning(f'No paths found in OpenAPI spec for {api_name}')
        return

    components = openapi_spec.get('components', {})

    # Track created prompts
    created_prompts = []

    # Process each path and operation
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'delete', 'patch']:
                continue

            # Extract operation details
            operation_id = operation.get('operationId')
            if not operation_id:
                logger.warning(
                    f'Operation at {method.upper()} {path} has no operationId, skipping'
                )
                continue

            try:
                logger.debug(f'Generating prompt for operation: {operation_id}')

                # Generate a simple prompt for this operation
                prompt_content = generate_simple_prompt(
                    operation_id=operation_id,
                    method=method,
                    path=path,
                    operation=operation,
                    components=components,
                )

                logger.debug(f'Generated prompt content for {operation_id}: {prompt_content}')

                # Create a prompt function with proper closure
                def prompt_fn(content=prompt_content):
                    return [{'role': 'user', 'content': content}]

                prompt_name = f'{api_name}_{operation_id}_prompt'

                # Create and add the prompt
                prompt = Prompt.from_function(
                    fn=prompt_fn,
                    name=prompt_name,
                    description=f'Simple prompt for {operation_id} operation',
                )

                # Create and add the prompt based on server capabilities
                server_obj = cast(Any, server)

                if hasattr(server_obj, 'add_prompt_from_fn'):
                    # Use add_prompt_from_fn if available
                    server_obj.add_prompt_from_fn(
                        fn=prompt_fn,
                        name=prompt_name,
                        description=f'Simple prompt for {operation_id} operation',
                    )
                elif hasattr(server_obj, 'add_prompt'):
                    # Try to use add_prompt directly
                    try:
                        server_obj.add_prompt(prompt)
                    except (AttributeError, TypeError):
                        # If that fails, try to add to prompt manager directly
                        if hasattr(server_obj, '_prompt_manager'):
                            server_obj._prompt_manager.add_prompt(prompt)  # type: ignore
                        else:
                            # For test mocks that only have add_prompt but don't accept Prompt objects
                            server_obj.add_prompt(
                                prompt_name,
                                prompt_fn,
                                f'Simple prompt for {operation_id} operation',
                            )  # type: ignore
                else:
                    # Last resort, try to add to prompt manager directly
                    try:
                        server_obj._prompt_manager.add_prompt(prompt)  # type: ignore
                    except (AttributeError, TypeError):
                        # For test mocks
                        server_obj.add_prompt(
                            prompt_name, prompt_fn, f'Simple prompt for {operation_id} operation'
                        )  # type: ignore
                created_prompts.append(prompt_name)
                logger.debug(
                    f'Added operation prompt: {prompt_name} with content: {prompt_content}'
                )
            except Exception as e:
                logger.warning(f'Failed to generate prompt for {operation_id}: {e}')
                import traceback

                logger.debug(f'Traceback: {traceback.format_exc()}')

    logger.debug(f'Created {len(created_prompts)} operation-specific prompts')
