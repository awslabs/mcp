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
from awslabs.aws_healthomics_mcp_server.models import ContainerRegistryMap, DefinitionRepository
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import decode_from_base64
from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import ValidationError
from typing import Any, Dict, List, Optional, Tuple


class ReadmeInputType(Enum):
    """Enumeration of README input types for workflow documentation."""

    S3_URI = 's3_uri'  # Input is an S3 URI (s3://bucket/path)
    LOCAL_FILE = 'local_file'  # Input is a path to a local .md file
    MARKDOWN_CONTENT = 'markdown_content'  # Input is direct markdown text


class ProviderType(str, Enum):
    """Supported Git provider types for CodeConnections."""

    BITBUCKET = 'Bitbucket'
    GITHUB = 'GitHub'
    GITHUB_ENTERPRISE_SERVER = 'GitHubEnterpriseServer'
    GITLAB = 'GitLab'
    GITLAB_SELF_MANAGED = 'GitLabSelfManaged'


def detect_readme_input_type(readme: str) -> ReadmeInputType:
    """Detect the type of README input.

    Detection rules (in order):
    1. If starts with 's3://' -> S3_URI
    2. If path exists and ends with '.md' -> LOCAL_FILE
    3. Otherwise -> MARKDOWN_CONTENT

    Args:
        readme: The README input string

    Returns:
        The detected input type
    """
    import os

    # Rule 1: Check for S3 URI prefix first
    if readme.startswith('s3://'):
        return ReadmeInputType.S3_URI

    # Rule 2: Check for existing local file with .md extension
    if readme.lower().endswith('.md') and os.path.isfile(readme):
        return ReadmeInputType.LOCAL_FILE

    # Rule 3: Default to markdown content
    return ReadmeInputType.MARKDOWN_CONTENT


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
    definition_repository: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[bytes], Optional[str], Optional[Dict[str, Any]]]:
    """Validate that exactly one definition source is provided and process it.

    Args:
        ctx: MCP context for error reporting
        definition_zip_base64: Base64-encoded workflow definition ZIP file
        definition_uri: S3 URI of the workflow definition ZIP file
        definition_repository: Git repository configuration

    Returns:
        Tuple of (decoded_zip_bytes, validated_uri, validated_repository)

    Raises:
        ValueError: If validation fails
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(definition_uri, 'default') and not isinstance(definition_uri, (str, type(None))):
        definition_uri = getattr(definition_uri, 'default', None)

    if hasattr(definition_repository, 'default') and not isinstance(
        definition_repository, (dict, type(None))
    ):
        definition_repository = getattr(definition_repository, 'default', None)

    # Count how many definition sources are provided
    sources_provided = sum(
        [
            definition_zip_base64 is not None,
            definition_uri is not None,
            definition_repository is not None,
        ]
    )

    # Validate that exactly one definition source is provided
    if sources_provided > 1:
        error_message = (
            'Cannot specify multiple definition sources. Use only one of: '
            'definition_zip_base64, definition_uri, or definition_repository'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    if sources_provided == 0:
        error_message = (
            'Must specify one definition source: '
            'definition_zip_base64, definition_uri, or definition_repository'
        )
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

    # Validate repository definition if provided
    validated_repository = None
    if definition_repository is not None:
        validated_repository = await validate_repository_definition(ctx, definition_repository)

    return definition_zip, definition_uri, validated_repository


async def validate_repository_definition(
    ctx: Context,
    definition_repository: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Validate and transform repository definition for API call.

    Args:
        ctx: MCP context for error reporting
        definition_repository: User-provided repository configuration

    Returns:
        Transformed repository definition for AWS API, or None if not provided

    Raises:
        ValueError: If validation fails
    """
    # Handle None input
    if definition_repository is None:
        return None

    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(definition_repository, 'default') and not isinstance(
        definition_repository, (dict, type(None))
    ):
        definition_repository = getattr(definition_repository, 'default', None)
        if definition_repository is None:
            return None

    try:
        # Validate using Pydantic model
        repo = DefinitionRepository(**definition_repository)

        # Transform to API format (snake_case to camelCase)
        result: Dict[str, Any] = {
            'connectionArn': repo.connection_arn,
            'fullRepositoryId': repo.full_repository_id,
            'sourceReference': {
                'type': repo.source_reference.type.value,
                'value': repo.source_reference.value,
            },
        }

        # Add optional excludeFilePatterns if provided
        if repo.exclude_file_patterns:
            result['excludeFilePatterns'] = repo.exclude_file_patterns

        return result

    except ValidationError as e:
        error_message = f'Invalid repository definition: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)


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


async def validate_readme_input(
    ctx: Context,
    readme: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate and process README input.

    Args:
        ctx: MCP context for error reporting
        readme: User-provided README input (markdown, file path, or S3 URI)

    Returns:
        Tuple of (readme_markdown, readme_uri) where exactly one is set,
        or (None, None) if readme is None

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If local file doesn't exist
        IOError: If local file cannot be read
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(readme, 'default') and not isinstance(readme, (str, type(None))):
        readme = getattr(readme, 'default', None)

    # Handle None input
    if readme is None:
        return (None, None)

    # Detect input type
    input_type = detect_readme_input_type(readme)

    if input_type == ReadmeInputType.S3_URI:
        # Validate S3 URI format using existing validate_s3_uri
        await validate_s3_uri(ctx, readme, 'readme')
        return (None, readme)

    elif input_type == ReadmeInputType.LOCAL_FILE:
        # Read file contents with proper error handling
        try:
            with open(readme, 'r', encoding='utf-8') as f:
                content = f.read()
            return (content, None)
        except FileNotFoundError:
            error_message = f'README file not found: {readme}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise FileNotFoundError(error_message)
        except IOError as e:
            error_message = f'Failed to read README file {readme}: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise IOError(error_message)

    else:  # MARKDOWN_CONTENT
        return (readme, None)


async def validate_repository_path_params(
    ctx: Context,
    definition_repository: Optional[Dict[str, Any]],
    parameter_template_path: Optional[str],
    readme_path: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate repository-specific path parameters.

    These parameters are only valid when definition_repository is provided.

    Args:
        ctx: MCP context for error reporting
        definition_repository: Repository configuration (to check if repository is used)
        parameter_template_path: Path to parameter template in repository
        readme_path: Path to README in repository

    Returns:
        Tuple of (validated_parameter_template_path, validated_readme_path)

    Raises:
        ValueError: If path params provided without repository definition
    """
    # Handle Field objects for optional parameters (FastMCP compatibility)
    if hasattr(definition_repository, 'default') and not isinstance(
        definition_repository, (dict, type(None))
    ):
        definition_repository = getattr(definition_repository, 'default', None)

    if hasattr(parameter_template_path, 'default') and not isinstance(
        parameter_template_path, (str, type(None))
    ):
        parameter_template_path = getattr(parameter_template_path, 'default', None)

    if hasattr(readme_path, 'default') and not isinstance(readme_path, (str, type(None))):
        readme_path = getattr(readme_path, 'default', None)

    # Check if path parameters are provided without definition_repository
    if definition_repository is None:
        if parameter_template_path is not None:
            error_message = 'parameter_template_path can only be used with definition_repository'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)

        if readme_path is not None:
            error_message = 'readme_path can only be used with definition_repository'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)

    return (parameter_template_path, readme_path)


async def validate_provider_type(
    ctx: Context,
    provider_type: Optional[str],
) -> Optional[str]:
    """Validate that provider_type is a supported value.

    Args:
        ctx: MCP context for error reporting
        provider_type: The provider type to validate

    Returns:
        The validated provider type, or None if not provided

    Raises:
        ValueError: If provider_type is invalid
    """
    if provider_type is None:
        return None

    valid_types = [pt.value for pt in ProviderType]
    if provider_type not in valid_types:
        error_message = (
            f"Invalid provider_type '{provider_type}'. Must be one of: {', '.join(valid_types)}"
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    return provider_type


async def validate_connection_arn(
    ctx: Context,
    connection_arn: str,
) -> str:
    """Validate that connection_arn follows the expected format.

    Args:
        ctx: MCP context for error reporting
        connection_arn: The connection ARN to validate

    Returns:
        The validated connection ARN

    Raises:
        ValueError: If connection_arn format is invalid
    """
    valid_prefixes = (
        'arn:aws:codeconnections:',
        'arn:aws:codestar-connections:',
    )

    if not connection_arn.startswith(valid_prefixes):
        error_message = (
            f"Invalid connection ARN format: '{connection_arn}'. "
            f'Expected format: arn:aws:codeconnections:{{region}}:{{account}}:connection/{{id}} '
            f'or arn:aws:codestar-connections:{{region}}:{{account}}:connection/{{id}}'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    return connection_arn


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
