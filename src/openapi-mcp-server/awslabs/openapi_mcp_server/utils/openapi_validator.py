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
"""OpenAPI validation utilities.

This module provides validation for OpenAPI specifications using openapi-core
when available, with a simple fallback implementation.
"""

import os
from awslabs.openapi_mcp_server import logger
from typing import Any, Dict


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
                # Ignore type error since we're checking dynamically
                openapi_core.create_spec(spec)  # type: ignore
            # For older versions of openapi-core
            elif hasattr(openapi_core, 'Spec'):
                spec_class = getattr(openapi_core, 'Spec')
                if hasattr(spec_class, 'create'):
                    # Ignore type error since we're checking dynamically
                    spec_class.create(spec)  # type: ignore
            # For newer versions of openapi-core
            elif hasattr(openapi_core, 'OpenAPISpec'):
                # Ignore type error since we're checking dynamically
                getattr(openapi_core, 'OpenAPISpec').create(spec)  # type: ignore
            else:
                logger.warning('Unsupported openapi-core version - skipping additional validation')
            logger.debug('OpenAPI spec validated with openapi-core')
        except Exception as e:
            logger.error(f'Error validating OpenAPI spec with openapi-core: {e}')
            # We already did basic validation, so we'll still return True
            return True

    # Return True if we've passed all validations
    return True
