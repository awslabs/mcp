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

"""Configuration utilities for the HealthOmics MCP server."""

import os
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS,
    DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT,
    DEFAULT_GENOMICS_SEARCH_TIMEOUT,
    ERROR_INVALID_S3_BUCKET_PATH,
    ERROR_NO_S3_BUCKETS_CONFIGURED,
    GENOMICS_SEARCH_ENABLE_HEALTHOMICS_ENV,
    GENOMICS_SEARCH_MAX_CONCURRENT_ENV,
    GENOMICS_SEARCH_S3_BUCKETS_ENV,
    GENOMICS_SEARCH_TIMEOUT_ENV,
)
from awslabs.aws_healthomics_mcp_server.models import SearchConfig
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
    validate_and_normalize_s3_path,
    validate_bucket_access,
)
from loguru import logger
from typing import List


def get_genomics_search_config() -> SearchConfig:
    """Get the genomics search configuration from environment variables.

    Returns:
        SearchConfig: Configuration object with validated settings

    Raises:
        ValueError: If configuration is invalid or missing required settings
    """
    # Get S3 bucket paths
    s3_bucket_paths = get_s3_bucket_paths()

    # Get max concurrent searches
    max_concurrent = get_max_concurrent_searches()

    # Get search timeout
    timeout_seconds = get_search_timeout_seconds()

    # Get HealthOmics search enablement
    enable_healthomics = get_enable_healthomics_search()

    return SearchConfig(
        s3_bucket_paths=s3_bucket_paths,
        max_concurrent_searches=max_concurrent,
        search_timeout_seconds=timeout_seconds,
        enable_healthomics_search=enable_healthomics,
    )


def get_s3_bucket_paths() -> List[str]:
    """Get and validate S3 bucket paths from environment variables.

    Returns:
        List of validated S3 bucket paths

    Raises:
        ValueError: If no bucket paths are configured or paths are invalid
    """
    bucket_paths_env = os.environ.get(GENOMICS_SEARCH_S3_BUCKETS_ENV, '').strip()

    if not bucket_paths_env:
        raise ValueError(ERROR_NO_S3_BUCKETS_CONFIGURED)

    # Split by comma and clean up paths
    raw_paths = [path.strip() for path in bucket_paths_env.split(',') if path.strip()]

    if not raw_paths:
        raise ValueError(ERROR_NO_S3_BUCKETS_CONFIGURED)

    # Validate and normalize each path
    validated_paths = []
    for path in raw_paths:
        try:
            validated_path = validate_and_normalize_s3_path(path)
            validated_paths.append(validated_path)
            logger.info(f'Configured S3 bucket path: {validated_path}')
        except ValueError as e:
            logger.error(f"Invalid S3 bucket path '{path}': {e}")
            raise ValueError(ERROR_INVALID_S3_BUCKET_PATH.format(path)) from e

    return validated_paths


def get_max_concurrent_searches() -> int:
    """Get the maximum number of concurrent searches from environment variables.

    Returns:
        Maximum number of concurrent searches
    """
    try:
        max_concurrent = int(
            os.environ.get(
                GENOMICS_SEARCH_MAX_CONCURRENT_ENV, str(DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT)
            )
        )
        if max_concurrent <= 0:
            logger.warning(
                f'Invalid max concurrent searches value: {max_concurrent}. Using default: {DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT}'
            )
            return DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT
        return max_concurrent
    except ValueError:
        logger.warning(
            f'Invalid max concurrent searches value in environment. Using default: {DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT}'
        )
        return DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT


def get_search_timeout_seconds() -> int:
    """Get the search timeout in seconds from environment variables.

    Returns:
        Search timeout in seconds
    """
    try:
        timeout = int(
            os.environ.get(GENOMICS_SEARCH_TIMEOUT_ENV, str(DEFAULT_GENOMICS_SEARCH_TIMEOUT))
        )
        if timeout <= 0:
            logger.warning(
                f'Invalid search timeout value: {timeout}. Using default: {DEFAULT_GENOMICS_SEARCH_TIMEOUT}'
            )
            return DEFAULT_GENOMICS_SEARCH_TIMEOUT
        return timeout
    except ValueError:
        logger.warning(
            f'Invalid search timeout value in environment. Using default: {DEFAULT_GENOMICS_SEARCH_TIMEOUT}'
        )
        return DEFAULT_GENOMICS_SEARCH_TIMEOUT


def get_enable_healthomics_search() -> bool:
    """Get whether HealthOmics search is enabled from environment variables.

    Returns:
        True if HealthOmics search is enabled, False otherwise
    """
    env_value = os.environ.get(
        GENOMICS_SEARCH_ENABLE_HEALTHOMICS_ENV, str(DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS)
    ).lower()

    # Accept various true/false representations
    true_values = {'true', '1', 'yes', 'on', 'enabled'}
    false_values = {'false', '0', 'no', 'off', 'disabled'}

    if env_value in true_values:
        return True
    elif env_value in false_values:
        return False
    else:
        logger.warning(
            f'Invalid HealthOmics search enablement value: {env_value}. Using default: {DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS}'
        )
        return DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS


def validate_bucket_access_permissions() -> List[str]:
    """Validate that we have access to all configured S3 buckets.

    Returns:
        List of bucket paths that are accessible

    Raises:
        ValueError: If no buckets are accessible
    """
    try:
        config = get_genomics_search_config()
    except ValueError as e:
        logger.error(f'Configuration error: {e}')
        raise

    return validate_bucket_access(config.s3_bucket_paths)
