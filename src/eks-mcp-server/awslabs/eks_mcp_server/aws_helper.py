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

"""AWS helper for the EKS MCP Server."""

import boto3
import os
from awslabs.eks_mcp_server import __version__
from botocore.config import Config
from loguru import logger
from typing import Any, Dict, Optional


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and profile management and client creation.

    This class implements a singleton pattern with a client cache to avoid
    creating multiple clients for the same service.
    """

    # Singleton instance
    _instance = None

    # Client cache with AWS service name as key
    _client_cache: Dict[str, Any] = {}

    @staticmethod
    def get_aws_region() -> Optional[str]:
        """Get the AWS region from the environment if set."""
        return os.environ.get('AWS_REGION')

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get the AWS profile from the environment if set."""
        return os.environ.get('AWS_PROFILE')

    @classmethod
    def create_boto3_client(cls, service_name: str, region_name: Optional[str] = None) -> Any:
        """Create or retrieve a cached boto3 client with the appropriate profile and region.

        The client is configured with a custom user agent suffix 'awslabs/mcp/eks-mcp-server/{version}'
        to identify API calls made by the EKS MCP Server. Clients are cached to improve performance
        and reduce resource usage.

        Args:
            service_name: The AWS service name (e.g., 'ec2', 's3', 'eks')
            region_name: Optional region name override

        Returns:
            A boto3 client for the specified service

        Raises:
            Exception: If there's an error creating the client
        """
        try:
            # Get region from parameter or environment if set
            region: Optional[str] = (
                region_name if region_name is not None else cls.get_aws_region()
            )

            # Get profile from environment if set
            profile = cls.get_aws_profile()

            # Use only service name as the cache key
            cache_key = service_name

            # Check if client is already in cache
            if cache_key in cls._client_cache:
                logger.info(f'Using cached boto3 client for {service_name}')
                return cls._client_cache[cache_key]

            # Create config with user agent suffix
            config = Config(user_agent_extra=f'awslabs/mcp/eks-mcp-server/{__version__}')

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

            # Cache the client
            cls._client_cache[cache_key] = client

            return client
        except Exception as e:
            # Re-raise with more context
            raise Exception(f'Failed to create boto3 client for {service_name}: {str(e)}')
