"""Comprehensive API documentation generation for OpenAPI specifications.

This module serves as the main entry point for API documentation generation,
importing and orchestrating the functionality from specialized modules:
- api_documentation_operation.py - For operation-specific prompt generation
- api_documentation_workflow.py - For workflow prompt generation
"""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.api_documentation_operation import (
    create_operation_prompt,
    is_complex_operation,
)
from awslabs.openapi_mcp_server.prompts.api_documentation_workflow import (
    generate_generic_workflow_prompts,
)
from awslabs.openapi_mcp_server.prompts.base import GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY
from awslabs.openapi_mcp_server.utils.config import ENABLE_OPERATION_PROMPTS
from awslabs.openapi_mcp_server.utils.openapi_validator import extract_api_structure
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


async def generate_api_documentation(
    server: FastMCP, api_name: str, openapi_spec: Dict[str, Any]
) -> Dict[str, bool]:
    """Generate efficient API documentation for an OpenAPI specification.

    Args:
        server: The MCP server
        api_name: The name of the API
        openapi_spec: The OpenAPI specification

    Returns:
        Dict[str, bool]: Status of each documentation type generation

    """
    logger.info(f'Generating documentation for {api_name}')

    # Extract API information
    paths = openapi_spec.get('paths', {})
    components = (
        openapi_spec.get('components', {})
        if isinstance(openapi_spec.get('components'), dict)
        else {}
    )

    # Extract API structure for workflow generation
    try:
        api_structure = extract_api_structure(openapi_spec)
    except Exception as e:
        logger.warning(f'Error extracting API structure: {e}')
        api_structure = paths

    # Generate workflow section
    workflow_section = None
    try:
        workflow_section = await generate_generic_workflow_prompts(
            server, api_name, api_structure, components
        )
    except Exception as e:
        logger.warning(f'Error generating workflow prompts: {e}')

    # Create operation-specific prompts if enabled
    operation_prompts_generated = False
    if ENABLE_OPERATION_PROMPTS:
        logger.info(f'Generating operation prompts for {api_name}')
        operation_mappings = {}

        # Process each path and operation
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ['get', 'post', 'put', 'patch', 'delete']:
                    continue

                operation_id = operation.get('operationId')
                if not operation_id:
                    continue

                # Skip simple operations if configured to do so
                if GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY:
                    parameters = operation.get('parameters', [])
                    request_body = operation.get('requestBody')
                    responses = operation.get('responses', {})

                    if not is_complex_operation(parameters, request_body, responses):
                        logger.debug(f'Skipping simple operation: {operation_id}')
                        continue

                # Store operation mapping
                operation_mappings[operation_id] = {
                    'mapping_type': 'function',
                    'method': method,
                    'path': path,
                    'parameters': operation.get('parameters', []),
                }

                try:
                    # Generate prompt for this operation
                    create_operation_prompt(
                        server=server,
                        api_name=api_name,
                        operation_id=operation_id,
                        mapping_type='function',
                        method=method,
                        path=path,
                        summary=operation.get('summary', ''),
                        description=operation.get('description', ''),
                        parameters=operation.get('parameters', []),
                        request_body=operation.get('requestBody'),
                        responses=operation.get('responses', {}),
                        security=operation.get('security', []),
                    )
                    operation_prompts_generated = True
                except Exception as e:
                    logger.error(f'Error generating prompt for {operation_id}: {e}')

        # Mapping reference prompt generation removed as it's not needed

    # Return status
    return {
        'operation_prompts_generated': operation_prompts_generated,
        'workflow_prompts_generated': workflow_section is not None,
    }


# Alias for backward compatibility
generate_api_instructions = generate_api_documentation
generate_unified_prompts = generate_api_documentation
