# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# ruff: noqa: D101, D102, D103
"""Tests for the K8sClientCache class."""

import pytest
import time
from awslabs.eks_mcp_server.k8s_client_cache import K8S_AWS_ID_HEADER, K8sClientCache
from unittest.mock import MagicMock, patch


class TestK8sClientCache:
    """Tests for the K8sClientCache class."""

    def test_singleton_pattern(self):
        """Test that K8sClientCache follows the singleton pattern."""
        # Create two instances of K8sClientCache
        cache1 = K8sClientCache()
        cache2 = K8sClientCache()

        # Verify that they are the same instance
        assert cache1 is cache2

    def test_initialization(self):
        """Test that K8sClientCache initializes correctly."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Verify that the client cache is initialized
        assert hasattr(cache, '_client_cache')
        assert cache._client_cache.maxsize == 100

        # Verify that the clients are not initialized yet
        assert cache._eks_client is None
        assert cache._sts_client is None

        # Verify that the initialization flag is set
        assert cache._initialized is True

    def test_get_eks_client(self):
        """Test _get_eks_client method."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Reset the eks_client
        cache._eks_client = None

        # Mock the AwsHelper.create_boto3_client method
        with patch(
            'awslabs.eks_mcp_server.k8s_client_cache.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_eks_client = MagicMock()
            mock_create_client.return_value = mock_eks_client

            # Get the EKS client
            client = cache._get_eks_client()

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('eks')

            # Verify that the client was cached
            assert cache._eks_client == mock_eks_client

            # Verify that the client was returned
            assert client == mock_eks_client

            # Call _get_eks_client again
            client2 = cache._get_eks_client()

            # Verify that AwsHelper.create_boto3_client was not called again
            assert mock_create_client.call_count == 1

            # Verify that the same client was returned
            assert client2 == mock_eks_client

    def test_get_sts_client(self):
        """Test _get_sts_client method."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Reset the sts_client
        cache._sts_client = None

        # Mock the AwsHelper.create_boto3_client method
        with patch(
            'awslabs.eks_mcp_server.k8s_client_cache.AwsHelper.create_boto3_client'
        ) as mock_create_client:
            mock_sts_client = MagicMock()
            mock_create_client.return_value = mock_sts_client

            # Mock the meta.events.register method
            mock_sts_client.meta.events.register = MagicMock()

            # Get the STS client
            client = cache._get_sts_client()

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('sts')

            # Verify that the event handlers were registered
            assert mock_sts_client.meta.events.register.call_count == 2

            # Verify that the client was cached
            assert cache._sts_client == mock_sts_client

            # Verify that the client was returned
            assert client == mock_sts_client

            # Call _get_sts_client again
            client2 = cache._get_sts_client()

            # Verify that AwsHelper.create_boto3_client was not called again
            assert mock_create_client.call_count == 1

            # Verify that the same client was returned
            assert client2 == mock_sts_client

    def test_retrieve_k8s_aws_id(self):
        """Test _retrieve_k8s_aws_id method."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Create test parameters and context
        params = {K8S_AWS_ID_HEADER: 'test-cluster'}
        context = {}

        # Call the _retrieve_k8s_aws_id method
        cache._retrieve_k8s_aws_id(params, context)

        # Verify that the header was moved from params to context
        assert K8S_AWS_ID_HEADER not in params
        assert context[K8S_AWS_ID_HEADER] == 'test-cluster'

        # Test with missing header
        params = {}
        context = {}

        # Call the _retrieve_k8s_aws_id method
        cache._retrieve_k8s_aws_id(params, context)

        # Verify that context is unchanged
        assert K8S_AWS_ID_HEADER not in context

    def test_inject_k8s_aws_id_header(self):
        """Test _inject_k8s_aws_id_header method."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Create a mock request with context
        mock_request = MagicMock()
        mock_request.context = {K8S_AWS_ID_HEADER: 'test-cluster'}
        mock_request.headers = {}

        # Call the _inject_k8s_aws_id_header method
        cache._inject_k8s_aws_id_header(mock_request)

        # Verify that the header was added to the request headers
        assert mock_request.headers[K8S_AWS_ID_HEADER] == 'test-cluster'

        # Test with missing header in context
        mock_request = MagicMock()
        mock_request.context = {}
        mock_request.headers = {}

        # Call the _inject_k8s_aws_id_header method
        cache._inject_k8s_aws_id_header(mock_request)

        # Verify that the headers are unchanged
        assert K8S_AWS_ID_HEADER not in mock_request.headers

    def test_get_client_success(self):
        """Test get_client method with successful client creation."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Clear the client cache
        cache._client_cache.clear()

        # Mock the _get_cluster_credentials method
        with patch.object(
            cache,
            '_get_cluster_credentials',
            return_value=('https://test-endpoint', 'test-token', 'test-ca-data'),
        ) as mock_cache:
            # Mock the K8sApis constructor
            with patch('awslabs.eks_mcp_server.k8s_client_cache.K8sApis') as mock_k8s_apis_class:
                mock_k8s_apis = MagicMock()
                mock_k8s_apis_class.return_value = mock_k8s_apis

                # Get a client
                client = cache.get_client('test-cluster')

                # Verify that _get_cluster_credentials was called
                mock_cache.assert_called_once_with('test-cluster')

                # Verify that K8sApis was initialized with the correct parameters
                mock_k8s_apis_class.assert_called_once_with(
                    'https://test-endpoint', 'test-token', 'test-ca-data'
                )

                # Verify that the client was cached
                assert 'test-cluster' in cache._client_cache
                assert cache._client_cache['test-cluster'] == mock_k8s_apis

                # Verify that the client was returned
                assert client == mock_k8s_apis

    def test_get_client_cached(self):
        """Test get_client method with cached client."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Create a mock client and add it to the cache
        mock_k8s_apis = MagicMock()
        cache._client_cache.clear()
        cache._client_cache['test-cluster'] = mock_k8s_apis

        # Mock the _get_cluster_credentials method
        with patch.object(cache, '_get_cluster_credentials') as mock_get_credentials:
            # Get a client
            client = cache.get_client('test-cluster')

            # Verify that _get_cluster_credentials was not called
            mock_get_credentials.assert_not_called()

            # Verify that the cached client was returned
            assert client == mock_k8s_apis

    def test_get_client_invalid_credentials(self):
        """Test get_client method with invalid credentials."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Clear the client cache
        cache._client_cache.clear()

        # Mock _get_cluster_credentials to return invalid credentials
        with patch.object(
            cache, '_get_cluster_credentials', return_value=(None, None, None)
        ) as mock_cache:
            # Get a client - should raise ValueError
            with pytest.raises(ValueError, match='Invalid cluster credentials'):
                cache.get_client('test-cluster')

            # Verify that _get_cluster_credentials was called
            mock_cache.assert_called_once_with('test-cluster')

            # Verify that the client was not cached
            assert 'test-cluster' not in cache._client_cache

    def test_get_client_error(self):
        """Test get_client method with error from _get_cluster_credentials."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Clear the client cache
        cache._client_cache.clear()

        # Mock _get_cluster_credentials to raise an exception
        with patch.object(
            cache, '_get_cluster_credentials', side_effect=Exception('Test error')
        ) as mock_cache:
            # Get a client - should raise Exception
            with pytest.raises(Exception, match='Failed to get cluster credentials: Test error'):
                cache.get_client('test-cluster')

            # Verify that _get_cluster_credentials was called
            mock_cache.assert_called_once_with('test-cluster')

            # Verify that the client was not cached
            assert 'test-cluster' not in cache._client_cache

    def test_ttl_cache_expiration(self):
        """Test that the TTLCache expires entries after the TTL."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Clear the client cache and create a new one with a very short TTL for testing
        cache._client_cache.clear()

        # Use a very short TTL for testing (0.1 seconds)
        test_ttl = 0.1

        # Create a new cache with the test TTL
        with patch('awslabs.eks_mcp_server.k8s_client_cache.TOKEN_TTL', test_ttl):
            from cachetools import TTLCache

            cache._client_cache = TTLCache(maxsize=100, ttl=test_ttl)

            # Mock _get_cluster_credentials to return valid credentials
            with patch.object(
                cache,
                '_get_cluster_credentials',
                return_value=('https://test-endpoint', 'test-token', 'test-ca-data'),
            ):
                # Mock the K8sApis constructor to return different instances each time
                with patch(
                    'awslabs.eks_mcp_server.k8s_client_cache.K8sApis'
                ) as mock_k8s_apis_class:
                    # Create two different mock instances
                    mock_k8s_apis1 = MagicMock()
                    mock_k8s_apis2 = MagicMock()

                    # Set up the mock to return different instances on consecutive calls
                    mock_k8s_apis_class.side_effect = [mock_k8s_apis1, mock_k8s_apis2]

                    # Get a client - should create a new one
                    client1 = cache.get_client('test-cluster')

                    # Verify that K8sApis was initialized
                    assert mock_k8s_apis_class.call_count == 1

                    # Wait for the cache entry to expire
                    time.sleep(test_ttl + 0.1)

                    # Get a client again - should create a new one because the cache entry expired
                    client2 = cache.get_client('test-cluster')

                    # Verify that K8sApis was initialized again
                    assert mock_k8s_apis_class.call_count == 2

                    # Verify that we got different client instances
                    assert client1 != client2

    def test_get_cluster_credentials(self):
        """Test _get_cluster_credentials method."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'endpoint': 'https://test-endpoint',
                'certificateAuthority': {'data': 'test-ca-data'},
            }
        }

        # Mock the STS client
        mock_sts_client = MagicMock()
        mock_sts_client.generate_presigned_url.return_value = 'https://test-presigned-url'

        # Mock the _get_eks_client and _get_sts_client methods
        with patch.object(
            cache, '_get_eks_client', return_value=mock_eks_client
        ) as mocked_eks_client:
            with patch.object(
                cache, '_get_sts_client', return_value=mock_sts_client
            ) as mocked_sts_client:
                # Get cluster credentials
                endpoint, token, ca_data = cache._get_cluster_credentials('test-cluster')

                # Verify that _get_eks_client and _get_sts_client were called
                mocked_eks_client.assert_called_once()
                mocked_sts_client.assert_called_once()

                # Verify that describe_cluster was called with the correct parameters
                mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

                # Verify that generate_presigned_url was called with the correct parameters
                mock_sts_client.generate_presigned_url.assert_called_once()
                args, kwargs = mock_sts_client.generate_presigned_url.call_args
                assert args[0] == 'get_caller_identity'
                assert kwargs['Params'] == {'x-k8s-aws-id': 'test-cluster'}
                assert kwargs['ExpiresIn'] == 60
                assert kwargs['HttpMethod'] == 'GET'

                # Verify the returned values
                assert endpoint == 'https://test-endpoint'
                assert (
                    'k8s-aws-v1.' in token
                )  # Token is base64 encoded, so we just check the prefix
                assert ca_data == 'test-ca-data'

    def test_get_cluster_credentials_error(self):
        """Test _get_cluster_credentials method with error."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Mock the EKS client to raise an exception
        mock_eks_client = MagicMock()
        mock_eks_client.describe_cluster.side_effect = Exception('Test error')

        # Mock the _get_eks_client method
        with patch.object(cache, '_get_eks_client', return_value=mock_eks_client) as mock_client:
            # Get cluster credentials - should raise Exception
            with pytest.raises(Exception, match='Test error'):
                cache._get_cluster_credentials('test-cluster')

            # Verify that _get_eks_client was called
            mock_client.assert_called_once()

            # Verify that describe_cluster was called with the correct parameters
            mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

    def test_get_cluster_credentials_missing_data(self):
        """Test _get_cluster_credentials method with missing data."""
        # Create a K8sClientCache instance
        cache = K8sClientCache()

        # Mock the EKS client with missing certificate authority data
        mock_eks_client = MagicMock()
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'endpoint': 'https://test-endpoint',
                # Missing certificateAuthority
            }
        }

        # Mock the _get_eks_client method
        with patch.object(cache, '_get_eks_client', return_value=mock_eks_client) as mock_client:
            # Get cluster credentials - should raise KeyError
            with pytest.raises(KeyError):
                cache._get_cluster_credentials('test-cluster')

            # Verify that _get_eks_client was called
            mock_client.assert_called_once()

            # Verify that describe_cluster was called with the correct parameters
            mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
