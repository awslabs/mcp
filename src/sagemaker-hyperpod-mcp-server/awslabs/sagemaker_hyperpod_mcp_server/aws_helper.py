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

"""AWS helper for the HyperPod MCP Server."""

import boto3
import os
import time
from awslabs.sagemaker_hyperpod_mcp_server import __version__
from awslabs.sagemaker_hyperpod_mcp_server.consts import SUPPORTED_REGIONS
from botocore.config import Config
from loguru import logger
from pydantic import validate_call
from typing import Any, Dict, Optional, cast, get_args


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and profile management and client creation.

    This class implements a singleton pattern with a client cache to avoid
    creating multiple clients for the same service. The cache includes TTL-based
    expiration and size limits to prevent memory issues and handle credential rotation.
    """

    # Singleton instance
    _instance = None

    # Client cache with AWS service name as key
    _client_cache: Dict[str, Any] = {}

    # Cache metadata for TTL and size management
    _cache_metadata: Dict[str, float] = {}  # key -> timestamp
    _cache_ttl: int = 1800  # 30 minutes TTL
    _cache_max_size: int = 100  # Maximum 100 cache entries

    @staticmethod
    def get_aws_region() -> Optional[SUPPORTED_REGIONS]:
        """Get the AWS region from the environment if set."""
        region = os.environ.get('AWS_REGION')
        return cast(SUPPORTED_REGIONS, region) if region in get_args(SUPPORTED_REGIONS) else None

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get the AWS profile from the environment if set."""
        return os.environ.get('AWS_PROFILE')

    @classmethod
    @validate_call
    def create_boto3_client(
        cls, service_name: str, region_name: Optional[SUPPORTED_REGIONS] = None
    ) -> Any:
        """Create or retrieve a cached boto3 client with the appropriate profile and region.

        The client is configured with a custom user agent suffix 'awslabs/mcp/sagemaker-hyperpod-mcp-server/{version}'
        to identify API calls made by the HyperPod MCP Server. Clients are cached to improve performance
        and reduce resource usage.

        Args:
            service_name: The AWS service name (e.g., 'sagemaker')
            region_name: Optional region name override

        Returns:
            A boto3 client for the specified service

        Raises:
            Exception: If there's an error creating the client
        """
        try:
            # Get region from parameter or environment if set
            region: Optional[SUPPORTED_REGIONS] = (
                region_name if region_name is not None else cls.get_aws_region()
            )

            # Get profile from environment if set
            profile = cls.get_aws_profile()

            # Use service name as the cache key
            cache_key = f'{service_name}+{region_name}'

            # Check if client is already in cache and not expired
            current_time = time.time()
            if cache_key in cls._client_cache:
                # Check TTL expiration (lazy expiration)
                if cache_key in cls._cache_metadata:
                    cache_time = cls._cache_metadata[cache_key]
                    if current_time - cache_time < cls._cache_ttl:
                        logger.info(
                            f'Using cached boto3 client for {service_name} in {region_name}'
                        )
                        return cls._client_cache[cache_key]
                    else:
                        # Expired - remove from cache
                        logger.info(
                            f'Cache expired for {service_name} in {region_name}, creating new client'
                        )
                        del cls._client_cache[cache_key]
                        del cls._cache_metadata[cache_key]
                else:
                    # No metadata, treat as expired
                    del cls._client_cache[cache_key]

            # Create config with user agent suffix
            config = Config(
                user_agent_extra=f'awslabs/mcp/sagemaker-hyperpod-mcp-server/{__version__}'
            )

            # Create session with profile if specified
            if profile:
                session = boto3.Session(profile_name=profile)
                if region is not None:
                    client = session.client(service_name, region_name=region, config=config)
                else:
                    client = session.client(service_name, config=config)
            else:
                if region is not None:
                    client = boto3.client(service_name, region_name=region, config=config)
                else:
                    client = boto3.client(service_name, config=config)

            # Enforce cache size limit before adding new entry
            if len(cls._client_cache) >= cls._cache_max_size:
                # Remove oldest entry (simple FIFO eviction)
                oldest_key = min(cls._cache_metadata.keys(), key=lambda k: cls._cache_metadata[k])
                logger.info(f'Cache size limit reached, evicting oldest entry: {oldest_key}')
                del cls._client_cache[oldest_key]
                del cls._cache_metadata[oldest_key]

            # Cache the client with timestamp metadata
            cls._client_cache[cache_key] = client
            cls._cache_metadata[cache_key] = current_time

            logger.info(f'Created and cached new boto3 client for {service_name} in {region_name}')
            return client
        except Exception as e:
            # Re-raise with more context
            raise Exception(f'Failed to create boto3 client for {service_name}: {str(e)}')
