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

"""Validation utilities for workflow management."""

from awslabs.aws_healthomics_mcp_server.models import ContainerRegistryMap
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import decode_from_base64
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import ValidationError
from typing import Any, Dict, Optional, Tuple


async def validate_s3_uri(ctx: Context, uri: str, parameter_name: str) -> None:
    """Validate that a URI is a valid S3 URI.

    Args:
        ctx: MCP context for error reporting
        uri: The URI to validate
        parameter_name: Name of the parameter for error messages

    Raises:
        ValueError: If the URI is not a valid S3 URI
    """
    if not uri.startswith('s3://'):
        error_message = f'{parameter_name} must be a valid S3 URI starting with s3://, got: {uri}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)


async def validate_definition_sources(
    ctx: Context,
    definition_zip_base64: Optional[str],
    definition_uri: Optional[str],
) -> Tuple[Optional[bytes], Optional[str]]:
    """Validate that exactly one definition source is provided and process it.

    Args:
        ctx: MCP context for error reporting
        definition_zip_base64: Base64-encoded workflow definition ZIP file
        definition_uri: S3 URI of the workflow definition ZIP file

    Returns:
        Tuple of (decoded_zip_bytes, validated_uri)

    Raises:
        ValueError: If validation fails
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(definition_uri, 'default') and not isinstance(definition_uri, (str, type(None))):
        definition_uri = getattr(definition_uri, 'default', None)

    # Validate that exactly one definition source is provided
    if definition_zip_base64 is not None and definition_uri is not None:
        error_message = 'Cannot specify both definition_zip_base64 and definition_uri parameters'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    if definition_zip_base64 is None and definition_uri is None:
        error_message = 'Must specify either definition_zip_base64 or definition_uri parameter'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate and decode base64 input if provided
    definition_zip = None
    if definition_zip_base64 is not None:
        try:
            definition_zip = decode_from_base64(definition_zip_base64)
        except Exception as e:
            error_message = f'Failed to decode base64 workflow definition: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise

    # Validate S3 URI format if provided
    if definition_uri is not None:
        await validate_s3_uri(ctx, definition_uri, 'definition_uri')

    return definition_zip, definition_uri


async def validate_container_registry_params(
    ctx: Context,
    container_registry_map: Optional[Dict[str, Any]],
    container_registry_map_uri: Optional[str],
) -> None:
    """Validate container registry parameters.

    Args:
        ctx: MCP context for error reporting
        container_registry_map: Container registry map dictionary
        container_registry_map_uri: S3 URI pointing to container registry mappings

    Raises:
        ValueError: If validation fails
    """
    # Validate that both container registry parameters are not provided together
    if container_registry_map is not None and container_registry_map_uri is not None:
        error_message = (
            'Cannot specify both container_registry_map and container_registry_map_uri parameters'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate container registry map structure if provided
    if container_registry_map is not None:
        try:
            ContainerRegistryMap(**container_registry_map)
        except ValidationError as e:
            error_message = f'Invalid container registry map structure: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)
