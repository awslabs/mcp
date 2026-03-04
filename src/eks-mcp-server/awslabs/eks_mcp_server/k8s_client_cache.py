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

"""Kubernetes client cache for the EKS MCP Server.

This module provides a cache for Kubernetes API clients that supports
multi-region and multi-account access through the cluster configuration.
"""

import base64
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.config import ClusterConfig, ConfigManager
from awslabs.eks_mcp_server.k8s_apis import K8sApis
from cachetools import TTLCache
from loguru import logger
from typing import Optional, Tuple


# Presigned url timeout in seconds
URL_TIMEOUT = 60
TOKEN_PREFIX = 'k8s-aws-v1.'
K8S_AWS_ID_HEADER = 'x-k8s-aws-id'

# 14 minutes in seconds (buffer before the 15-minute token expiration)
TOKEN_TTL = 14 * 60


class K8sClientCache:
    """Singleton class for managing Kubernetes API client cache.

    This class provides a centralized cache for Kubernetes API clients
    to avoid creating multiple clients for the same cluster. It supports
    multi-region and multi-account access through the cluster configuration.

    The cache key includes the cluster name and credential context to ensure
    proper isolation between different credential scenarios.
    """

    # Singleton instance
    _instance = None

    def __new__(cls):
        """Ensure only one instance of K8sClientCache exists."""
        if cls._instance is None:
            cls._instance = super(K8sClientCache, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the K8s client cache."""
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Client cache with TTL to handle token expiration
        # Key format: cluster_name:region:credential_context
        self._client_cache = TTLCache(maxsize=100, ttl=TOKEN_TTL)

        # Flag to track if STS event handlers have been registered
        self._sts_event_handlers_registered = {}

        self._initialized = True

    def _get_sts_client_for_cluster(self, cluster_config: Optional[ClusterConfig] = None):
        """Get the STS client with event handlers registered.

        Args:
            cluster_config: Optional cluster configuration for credentials

        Returns:
            STS client with K8s AWS ID event handlers registered
        """
        if cluster_config:
            sts_client = AwsHelper.create_boto3_client_for_cluster(cluster_config, 'sts')
            # Get account config to determine credential context
            account = ConfigManager.get_account(cluster_config.account_id)
            if account:
                credential_context = account.role_arn or account.profile or 'default'
            else:
                credential_context = 'default'
            client_id = f'{cluster_config.region}:{cluster_config.account_id}:{credential_context}'
        else:
            sts_client = AwsHelper.create_boto3_client('sts')
            client_id = 'default'

        # Register STS event handlers only once per client
        if client_id not in self._sts_event_handlers_registered:
            sts_client.meta.events.register(
                'provide-client-params.sts.GetCallerIdentity',
                self._retrieve_k8s_aws_id,
            )
            sts_client.meta.events.register(
                'before-sign.sts.GetCallerIdentity',
                self._inject_k8s_aws_id_header,
            )
            self._sts_event_handlers_registered[client_id] = True

        return sts_client

    def _retrieve_k8s_aws_id(self, params, context, **kwargs):
        """Retrieve the Kubernetes AWS ID from parameters."""
        if K8S_AWS_ID_HEADER in params:
            context[K8S_AWS_ID_HEADER] = params.pop(K8S_AWS_ID_HEADER)

    def _inject_k8s_aws_id_header(self, request, **kwargs):
        """Inject the Kubernetes AWS ID header into the request."""
        if K8S_AWS_ID_HEADER in request.context:
            request.headers[K8S_AWS_ID_HEADER] = request.context[K8S_AWS_ID_HEADER]

    def _get_cluster_credentials_with_config(
        self, cluster_config: ClusterConfig
    ) -> Tuple[str, str, str]:
        """Get credentials for an EKS cluster using cluster configuration.

        Args:
            cluster_config: ClusterConfig object with region and credential info

        Returns:
            Tuple of (endpoint, token, ca_data)

        Raises:
            ValueError: If the cluster credentials are invalid
            Exception: If there's an error getting the cluster credentials
        """
        # Get EKS client with appropriate credentials
        eks_client = AwsHelper.create_boto3_client_for_cluster(cluster_config, 'eks')
        sts_client = self._get_sts_client_for_cluster(cluster_config)

        # Get cluster details
        response = eks_client.describe_cluster(name=cluster_config.name)
        endpoint = response['cluster']['endpoint']
        ca_data = response['cluster']['certificateAuthority']['data']

        # Generate a presigned URL for authentication
        url = sts_client.generate_presigned_url(
            'get_caller_identity',
            Params={K8S_AWS_ID_HEADER: cluster_config.name},
            ExpiresIn=URL_TIMEOUT,
            HttpMethod='GET',
        )

        # Create the token from the presigned URL
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode('utf-8')).decode(
            'utf-8'
        ).rstrip('=')

        return endpoint, token, ca_data

    def _get_cluster_credentials_default(self, cluster_name: str) -> Tuple[str, str, str]:
        """Get credentials for an EKS cluster using default credentials.

        This is the legacy method used when no cluster config is available.

        Args:
            cluster_name: Name of the EKS cluster

        Returns:
            Tuple of (endpoint, token, ca_data)

        Raises:
            ValueError: If the cluster credentials are invalid
            Exception: If there's an error getting the cluster credentials
        """
        eks_client = AwsHelper.create_boto3_client('eks')
        sts_client = self._get_sts_client_for_cluster(None)

        # Get cluster details
        response = eks_client.describe_cluster(name=cluster_name)
        endpoint = response['cluster']['endpoint']
        ca_data = response['cluster']['certificateAuthority']['data']

        # Generate a presigned URL for authentication
        url = sts_client.generate_presigned_url(
            'get_caller_identity',
            Params={K8S_AWS_ID_HEADER: cluster_name},
            ExpiresIn=URL_TIMEOUT,
            HttpMethod='GET',
        )

        # Create the token from the presigned URL
        token = TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode('utf-8')).decode(
            'utf-8'
        ).rstrip('=')

        return endpoint, token, ca_data

    def get_client(self, cluster_name: str) -> K8sApis:
        """Get a Kubernetes client for the specified cluster.

        This method first checks if the cluster is configured in the cluster
        configuration file. If so, it uses the configured credentials (role
        assumption or profile). If configuration is in discovery mode (no explicit
        clusters), it uses default credentials. Otherwise, it falls back to default credentials.

        Args:
            cluster_name: Name of the EKS cluster

        Returns:
            K8sApis instance

        Raises:
            ValueError: If the cluster credentials are invalid or cluster not found in config
            Exception: If there's an error getting the cluster credentials
        """
        # Check if cluster configuration is available
        cluster_config = ConfigManager.get_cluster(cluster_name)
        logger.debug(cluster_config)
        if cluster_config:
            # Cluster configuration found (explicit or discovered)
            account = ConfigManager.get_account(cluster_config.account_id)
            if account:
                credential_context = account.role_arn or account.profile or 'default'
            else:
                credential_context = 'default'

            cache_key = f'{cluster_name}:{cluster_config.region}:{cluster_config.account_id}:{credential_context}'
            logger.debug(
                f'Using cluster config for {cluster_name} '
                f'(region: {cluster_config.region}, account: {cluster_config.account_id}, '
                f'access: {account.get_access_method() if account else "default"})'
            )
        elif ConfigManager.is_configured() and (
            ConfigManager.has_explicit_clusters() or ConfigManager.has_discovered_clusters()
        ):
            # Config is loaded with clusters (explicit or discovered), but this cluster not found - error
            available_clusters = ConfigManager.get_cluster_names()
            raise ValueError(
                f"Cluster '{cluster_name}' not found in configuration. "
                f'Available clusters: {", ".join(available_clusters)}'
            )
        else:
            # No config loaded - use default behavior
            cache_key = cluster_name
            logger.debug(f'No cluster config loaded, using default credentials for {cluster_name}')

        if cache_key not in self._client_cache:
            try:
                # Create a new client
                if cluster_config:
                    endpoint, token, ca_data = self._get_cluster_credentials_with_config(
                        cluster_config
                    )
                else:
                    endpoint, token, ca_data = self._get_cluster_credentials_default(cluster_name)

                # Validate credentials
                if not endpoint or not token or endpoint is None or token is None:
                    raise ValueError('Invalid cluster credentials')

                self._client_cache[cache_key] = K8sApis(endpoint, token, ca_data)
                logger.info(f'Created K8s client for cluster {cluster_name}')
            except ValueError:
                # Re-raise ValueError for invalid credentials
                raise
            except Exception as e:
                # Re-raise any other exceptions
                raise Exception(f'Failed to get cluster credentials: {str(e)}')

        return self._client_cache[cache_key]

    def clear_cache(self) -> None:
        """Clear the client cache.

        This is useful for testing or when credentials need to be refreshed.
        """
        self._client_cache.clear()
        self._sts_event_handlers_registered.clear()
        logger.debug('Cleared K8s client cache')
