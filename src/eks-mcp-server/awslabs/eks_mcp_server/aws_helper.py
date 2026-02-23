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

"""AWS helper for the EKS MCP Server.

This module provides utility methods for interacting with AWS services,
including support for multi-region and multi-account access via
role assumption and named profiles.
"""

import boto3
import os
from awslabs.eks_mcp_server import __version__
from botocore.config import Config
from loguru import logger
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from awslabs.eks_mcp_server.config import ClusterConfig


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and profile management and client creation.

    This class implements a singleton pattern with a client cache to avoid
    creating multiple clients for the same service. The cache key includes
    service name, region, and credential context to support multi-region
    and multi-account access.
    """

    # Singleton instance
    _instance = None

    # Client cache with composite key: service:region:credential_context
    _client_cache: Dict[str, Any] = {}

    # Cache for assumed role credentials
    _assumed_role_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def get_aws_region() -> Optional[str]:
        """Get the AWS region from the environment if set."""
        return os.environ.get('AWS_REGION')

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get the AWS profile from the environment if set."""
        return os.environ.get('AWS_PROFILE')

    @classmethod
    def assume_role(
        cls,
        role_arn: str,
        external_id: Optional[str] = None,
        session_name: str = 'eks-mcp-server',
        region_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assume an IAM role and return temporary credentials.

        Credentials are cached to avoid making repeated AssumeRole calls.
        The cache key includes role_arn and external_id.

        Args:
            role_arn: The ARN of the IAM role to assume
            external_id: Optional external ID for the role assumption
            session_name: Name for the assumed role session
            region_name: Optional region for the STS client

        Returns:
            Dictionary containing AccessKeyId, SecretAccessKey, and SessionToken

        Raises:
            Exception: If role assumption fails
        """
        # Build cache key for assumed role credentials
        cache_key = f'{role_arn}:{external_id or "none"}'

        # Check if we have cached credentials
        if cache_key in cls._assumed_role_cache:
            cached = cls._assumed_role_cache[cache_key]
            # Check if credentials are still valid (with 5 minute buffer)
            from datetime import datetime, timezone

            expiration = cached.get('Expiration')
            if expiration and expiration.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                logger.debug(f'Using cached assumed role credentials for {role_arn}')
                return cached

        try:
            # Get STS client (use default credentials to assume the role)
            sts_client = cls.create_boto3_client('sts', region_name=region_name)

            # Build assume role parameters
            params = {
                'RoleArn': role_arn,
                'RoleSessionName': session_name,
            }
            if external_id:
                params['ExternalId'] = external_id

            logger.info(f'Assuming role {role_arn}')
            response = sts_client.assume_role(**params)
            credentials = response['Credentials']

            # Cache the credentials
            cls._assumed_role_cache[cache_key] = credentials

            return credentials

        except Exception as e:
            raise Exception(f'Failed to assume role {role_arn}: {str(e)}')

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

            # Build cache key including region and profile for proper isolation
            cache_key = f'{service_name}:{region or "default"}:{profile or "default"}'

            # Check if client is already in cache
            if cache_key in cls._client_cache:
                logger.debug(f'Using cached boto3 client for {service_name}')
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

    @classmethod
    def create_boto3_client_for_account_region(
        cls, account_id: str, region_name: str, service_name: str = 'eks'
    ) -> Any:
        """Create a boto3 client with credentials appropriate for the specified account and region.

        This method looks up the account configuration and handles three credential scenarios:
        1. Role assumption: Uses STS AssumeRole with the configured or default role_arn
        2. Named profile: Uses the configured AWS CLI profile
        3. Default: Uses environment credentials or instance profile

        Args:
            account_id: AWS account ID
            region_name: AWS region name
            service_name: The AWS service name (default: 'eks')

        Returns:
            A boto3 client configured for the specified account and region

        Raises:
            Exception: If there's an error creating the client
        """
        from awslabs.eks_mcp_server.config import ConfigManager

        try:
            # Get account configuration
            account = ConfigManager.get_account(account_id)
            if not account:
                raise ValueError(f'Account {account_id} not found in configuration')

            # Check if the region is configured for this account
            if region_name not in account.regions:
                raise ValueError(
                    f'Region {region_name} not configured for account {account_id}. '
                    f'Configured regions: {account.regions}'
                )

            # Build cache key including credentials context
            credential_context = account.role_arn or account.profile or 'default'
            cache_key = f'{service_name}:{region_name}:{account_id}:{credential_context}'

            # Check if client is already in cache
            if cache_key in cls._client_cache:
                logger.debug(
                    f'Using cached boto3 client for {service_name} '
                    f'(account: {account_id}, region: {region_name})'
                )
                return cls._client_cache[cache_key]

            # Create config with user agent suffix
            config = Config(user_agent_extra=f'awslabs/mcp/eks-mcp-server/{__version__}')

            if account.profile:
                # Use named profile
                logger.info(
                    f"Creating {service_name} client with profile '{account.profile}' "
                    f'for account {account_id}, region {region_name}'
                )
                session = boto3.Session(profile_name=account.profile)
                client = session.client(service_name, region_name=region_name, config=config)
            else:
                # Use role assumption (with configured or default role)
                effective_role_arn = account.get_effective_role_arn()
                logger.info(
                    f'Creating {service_name} client with role assumption ({effective_role_arn}) '
                    f'for account {account_id}, region {region_name}'
                )
                credentials = cls.assume_role(
                    role_arn=effective_role_arn,
                    external_id=account.external_id,
                    region_name=region_name,
                )
                client = boto3.client(
                    service_name,
                    region_name=region_name,
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    config=config,
                )

            # Cache the client
            cls._client_cache[cache_key] = client

            return client

        except Exception as e:
            raise Exception(
                f'Failed to create boto3 client for {service_name} '
                f'(account: {account_id}, region: {region_name}): {str(e)}'
            )

    @classmethod
    def create_boto3_client_for_cluster(
        cls, cluster: 'ClusterConfig', service_name: str = 'eks'
    ) -> Any:
        """Create a boto3 client with credentials appropriate for the specified cluster.

        This method uses the account configuration associated with the cluster to determine
        the appropriate credentials.

        Args:
            cluster: ClusterConfig object containing region and account information
            service_name: The AWS service name (default: 'eks')

        Returns:
            A boto3 client configured for the specified cluster

        Raises:
            Exception: If there's an error creating the client
        """
        try:
            return cls.create_boto3_client_for_account_region(
                account_id=cluster.account_id,
                region_name=cluster.region,
                service_name=service_name,
            )
        except Exception as e:
            raise Exception(
                f'Failed to create boto3 client for {service_name} '
                f'(cluster: {cluster.name}): {str(e)}'
            )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached clients and credentials.

        This is useful for testing or when credentials need to be refreshed.
        """
        cls._client_cache.clear()
        cls._assumed_role_cache.clear()
        logger.debug('Cleared AWS client and credential caches')
