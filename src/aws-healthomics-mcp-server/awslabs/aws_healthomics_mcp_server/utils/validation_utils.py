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

import posixpath
from awslabs.aws_healthomics_mcp_server.models import ContainerRegistryMap
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import decode_from_base64
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import ValidationError
from typing import Any, Dict, List, Optional, Tuple


async def validate_s3_uri(ctx: Context, uri: str, parameter_name: str) -> None:
    """Validate that a URI is a valid S3 URI.

    Args:
        ctx: MCP context for error reporting
        uri: The URI to validate
        parameter_name: Name of the parameter for error messages

    Raises:
        ValueError: If the URI is not a valid S3 URI
    """
    from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
        is_valid_bucket_name,
        parse_s3_path,
    )

    try:
        bucket_name, _ = parse_s3_path(uri)
        if not is_valid_bucket_name(bucket_name):
            raise ValueError(f'Invalid bucket name: {bucket_name}')
    except ValueError as e:
        error_message = f'{parameter_name} must be a valid S3 URI, got: {uri}. Error: {str(e)}'
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
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(container_registry_map, 'default') and not isinstance(
        container_registry_map, (dict, type(None))
    ):
        container_registry_map = getattr(container_registry_map, 'default', None)

    if hasattr(container_registry_map_uri, 'default') and not isinstance(
        container_registry_map_uri, (str, type(None))
    ):
        container_registry_map_uri = getattr(container_registry_map_uri, 'default', None)

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


async def validate_adhoc_s3_buckets(adhoc_buckets: Optional[List[str]]) -> List[str]:
    """Validate adhoc S3 bucket paths and check access permissions.

    This function validates bucket path formats and tests access permissions
    for adhoc buckets that are not part of the standard configuration.

    Args:
        adhoc_buckets: List of S3 bucket paths to validate

    Returns:
        List of validated and accessible bucket paths

    Raises:
        ValueError: If no valid buckets are provided or accessible
    """
    if not adhoc_buckets:
        return []

    from awslabs.aws_healthomics_mcp_server.utils.s3_utils import validate_bucket_access

    try:
        # Use existing utility to validate bucket access
        # This handles format validation, deduplication, and access testing
        validated_buckets = validate_bucket_access(adhoc_buckets)

        logger.info(
            f'Validated {len(validated_buckets)} adhoc S3 buckets out of {len(adhoc_buckets)} provided'
        )
        return validated_buckets

    except ValueError as e:
        # Log the error but don't fail completely - let the search continue with configured buckets
        logger.warning(f'Adhoc S3 bucket validation failed: {e}')
        return []


async def validate_path_to_main(ctx: Context, path_to_main: Optional[str]) -> Optional[str]:
    """Validate that path_to_main is a safe relative path within the ZIP file.

    Args:
        ctx: MCP context for error reporting
        path_to_main: Path to the main workflow file within the ZIP

    Returns:
        The validated path, or None if path_to_main is None/empty

    Raises:
        ValueError: If the path is invalid or unsafe
    """
    if path_to_main is None or path_to_main == '':
        return None

    # Check for empty path components (double slashes) first
    if '//' in path_to_main:
        error_message = (
            f'path_to_main cannot contain empty path components (//), got: {path_to_main}'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Check for absolute paths BEFORE normalization
    if posixpath.isabs(path_to_main):
        error_message = f'path_to_main must be a relative path, got absolute path: {path_to_main}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Check for directory traversal attempts BEFORE normalization
    if path_to_main.startswith('../') or '/../' in path_to_main or path_to_main == '..':
        error_message = (
            f'path_to_main cannot contain directory traversal sequences (../), got: {path_to_main}'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Normalize the path to handle different path separators
    normalized_path = posixpath.normpath(path_to_main)

    # Check for paths that resolve to current directory
    if normalized_path in ('.', './'):
        error_message = f'path_to_main cannot be the current directory, got: {path_to_main}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate file extension (should be a workflow file)
    valid_extensions = ('.wdl', '.cwl', '.nf')
    if not any(normalized_path.lower().endswith(ext) for ext in valid_extensions):
        error_message = f'path_to_main must point to a workflow file with extension {valid_extensions}, got: {path_to_main}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    return normalized_path
