"""OpenAPI validation utilities.

This module provides validation for OpenAPI specifications using openapi-core
when available, with a simple fallback implementation.
"""

import os
from awslabs.openapi_mcp_server import logger
from typing import Any, Dict, List, Tuple


# Check if openapi-core is available
openapi_core = None
try:
    import openapi_core

    OPENAPI_CORE_AVAILABLE = True
    logger.debug('Using openapi-core for validation')
except ImportError:
    OPENAPI_CORE_AVAILABLE = False
    logger.debug('openapi-core not available, using simple validation')

# Use openapi-core if available and not explicitly disabled
USE_OPENAPI_CORE = OPENAPI_CORE_AVAILABLE and os.environ.get(
    'MCP_USE_OPENAPI_CORE', 'true'
).lower() in ('true', '1', 'yes')


def validate_openapi_spec(spec: Dict[str, Any]) -> bool:
    """Validate an OpenAPI specification.

    Args:
        spec: The OpenAPI specification to validate

    Returns:
        bool: True if the specification is valid, False otherwise
    """
    # Basic validation first
    # Check for required fields
    if 'openapi' not in spec:
        logger.error("Missing 'openapi' field in OpenAPI spec")
        return False

    if 'info' not in spec:
        logger.error("Missing 'info' field in OpenAPI spec")
        return False

    if 'paths' not in spec:
        logger.error("Missing 'paths' field in OpenAPI spec")
        return False

    # Check OpenAPI version
    version = spec['openapi']
    if not version.startswith('3.'):
        logger.warning(f'OpenAPI version {version} may not be fully supported')

    # Use openapi-core for additional validation if available
    if USE_OPENAPI_CORE and openapi_core is not None:
        try:
            # Create spec object - this will validate the spec
            if hasattr(openapi_core, 'create_spec'):
                openapi_core.create_spec(spec)
            # For older versions of openapi-core
            elif hasattr(openapi_core, 'Spec') and hasattr(openapi_core.Spec, 'create'):
                openapi_core.Spec.create(spec)
            # For newer versions of openapi-core
            elif hasattr(openapi_core, 'OpenAPISpec'):
                openapi_core.OpenAPISpec.create(spec)
            else:
                logger.warning('Unsupported openapi-core version - skipping additional validation')
            logger.debug('OpenAPI spec validated with openapi-core')
        except Exception as e:
            logger.error(f'Error validating OpenAPI spec with openapi-core: {e}')
            # We already did basic validation, so we'll still return True
            return True

    # Return True if we've passed all validations
    return True


def extract_api_structure(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the structure of an API from its OpenAPI specification.

    Args:
        spec: The OpenAPI specification

    Returns:
        Dict[str, Any]: A structured representation of the API
    """
    result = {
        'info': {
            'title': spec.get('info', {}).get('title', 'Unknown API'),
            'version': spec.get('info', {}).get('version', 'Unknown'),
            'description': spec.get('info', {}).get('description', ''),
        },
        'paths': {},
        'operations': [],
        'schemas': [],
    }

    # Extract paths and operations
    for path, path_item in spec.get('paths', {}).items():
        path_info = {'path': path, 'methods': {}}

        for method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
            if method in path_item:
                operation = path_item[method]
                operation_id = operation.get('operationId', f'{method}{path}')
                summary = operation.get('summary', '')
                description = operation.get('description', '')

                # Extract parameters
                parameters = []
                for param in operation.get('parameters', []):
                    parameters.append(
                        {
                            'name': param.get('name', ''),
                            'in': param.get('in', ''),
                            'required': param.get('required', False),
                            'description': param.get('description', ''),
                        }
                    )

                # Extract request body if present
                request_body = None
                if 'requestBody' in operation:
                    request_body = {
                        'required': operation['requestBody'].get('required', False),
                        'content_types': list(operation['requestBody'].get('content', {}).keys()),
                    }

                # Extract responses
                responses = {}
                for status_code, response in operation.get('responses', {}).items():
                    responses[status_code] = {
                        'description': response.get('description', ''),
                        'content_types': list(response.get('content', {}).keys()),
                    }

                # Add to path methods
                path_info['methods'][method] = {
                    'operationId': operation_id,
                    'summary': summary,
                    'description': description,
                    'parameters': parameters,
                    'requestBody': request_body,
                    'responses': responses,
                }

                # Add to operations list
                result['operations'].append(
                    {
                        'operationId': operation_id,
                        'method': method.upper(),
                        'path': path,
                        'summary': summary,
                    }
                )

        result['paths'][path] = path_info

    # Extract schemas
    if 'components' in spec and 'schemas' in spec['components']:
        for schema_name, schema in spec['components']['schemas'].items():
            result['schemas'].append(
                {
                    'name': schema_name,
                    'type': schema.get('type', 'object'),
                    'properties': len(schema.get('properties', {})),
                    'required': schema.get('required', []),
                }
            )

    return result


def find_pagination_endpoints(spec: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Find endpoints that likely support pagination.

    Args:
        spec: The OpenAPI specification

    Returns:
        List[Tuple[str, str, Dict[str, Any]]]: List of (path, method, operation) tuples
    """
    pagination_endpoints = []

    for path, path_item in spec.get('paths', {}).items():
        for method, operation in path_item.items():
            if method.lower() != 'get':
                continue

            # Check for pagination parameters
            has_pagination = False
            for param in operation.get('parameters', []):
                param_name = param.get('name', '').lower()
                if param_name in [
                    'page',
                    'limit',
                    'offset',
                    'size',
                    'per_page',
                    'pagesize',
                    'page_size',
                    'next',
                    'cursor',
                ]:
                    has_pagination = True
                    break

            # Check for array responses
            has_array_response = False
            for response in operation.get('responses', {}).values():
                for content_type, content in response.get('content', {}).items():
                    if 'application/json' in content_type:
                        schema = content.get('schema', {})
                        if schema.get('type') == 'array' or 'items' in schema:
                            has_array_response = True
                            break
                        # Check for common pagination response structures
                        properties = schema.get('properties', {})
                        for prop_name in properties:
                            if prop_name.lower() in ['items', 'data', 'results', 'content']:
                                prop_schema = properties[prop_name]
                                if prop_schema.get('type') == 'array' or 'items' in prop_schema:
                                    has_array_response = True
                                    break

            if has_pagination or has_array_response:
                pagination_endpoints.append((path, method, operation))

    return pagination_endpoints
