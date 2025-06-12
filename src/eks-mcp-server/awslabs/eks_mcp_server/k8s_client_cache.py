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

"""Kubernetes client cache for the EKS MCP Server."""

import base64
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.k8s_apis import K8sApis
from cachetools import TTLCache


# Presigned url timeout in seconds
URL_TIMEOUT = 60
TOKEN_PREFIX = 'k8s-aws-v1.'
K8S_AWS_ID_HEADER = 'x-k8s-aws-id'

# 14 minutes in seconds (buffer before the 15-minute token expiration)
TOKEN_TTL = 14 * 60


class K8sClientCache:
    """Singleton class for managing Kubernetes API client cache.

    This class provides a centralized cache for Kubernetes API clients
    to avoid creating multiple clients for the same cluster.
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
        self._client_cache = TTLCache(maxsize=100, ttl=TOKEN_TTL)

        # Flag to track if STS event handlers have been registered
        self._sts_event_handlers_registered = False

        self._initialized = True

    def _get_sts_client(self):
        """Get the STS client with event handlers registered."""
        sts_client = AwsHelper.create_boto3_client('sts')

        # Register STS event handlers only once
        if not self._sts_event_handlers_registered:
            sts_client.meta.events.register(
                'provide-client-params.sts.GetCallerIdentity',
                self._retrieve_k8s_aws_id,
            )
            sts_client.meta.events.register(
                'before-sign.sts.GetCallerIdentity',
                self._inject_k8s_aws_id_header,
            )
            self._sts_event_handlers_registered = True

        return sts_client

    def _retrieve_k8s_aws_id(self, params, context, **kwargs):
        """Retrieve the Kubernetes AWS ID from parameters."""
        if K8S_AWS_ID_HEADER in params:
            context[K8S_AWS_ID_HEADER] = params.pop(K8S_AWS_ID_HEADER)

    def _inject_k8s_aws_id_header(self, request, **kwargs):
        """Inject the Kubernetes AWS ID header into the request."""
        if K8S_AWS_ID_HEADER in request.context:
            request.headers[K8S_AWS_ID_HEADER] = request.context[K8S_AWS_ID_HEADER]

    def _get_cluster_credentials(self, cluster_name: str):
        """Get credentials for an EKS cluster (private method).

        Args:
            cluster_name: Name of the EKS cluster

        Returns:
            Tuple of (endpoint, token, ca_data)

        Raises:
            ValueError: If the cluster credentials are invalid
            Exception: If there's an error getting the cluster credentials
        """
        eks_client = AwsHelper.create_boto3_client('eks')
        sts_client = self._get_sts_client()

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

        This is the only public method to access K8s API clients.

        Args:
            cluster_name: Name of the EKS cluster

        Returns:
            K8sApis instance

        Raises:
            ValueError: If the cluster credentials are invalid
            Exception: If there's an error getting the cluster credentials
        """
        if cluster_name not in self._client_cache:
            try:
                # Create a new client
                endpoint, token, ca_data = self._get_cluster_credentials(cluster_name)

                # Validate credentials
                if not endpoint or not token or endpoint is None or token is None:
                    raise ValueError('Invalid cluster credentials')

                self._client_cache[cluster_name] = K8sApis(endpoint, token, ca_data)
            except ValueError:
                # Re-raise ValueError for invalid credentials
                raise
            except Exception as e:
                # Re-raise any other exceptions
                raise Exception(f'Failed to get cluster credentials: {str(e)}')

        return self._client_cache[cluster_name]
