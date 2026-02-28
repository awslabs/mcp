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
# ruff: noqa: D101, D102, D103
"""Tests for the AWS Helper."""

import os
from awslabs.eks_mcp_server import __version__
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from unittest.mock import ANY, MagicMock, patch


class TestAwsHelper:
    """Tests for the AwsHelper class."""

    def setup_method(self):
        """Set up the test environment."""
        # Clear the client cache before each test
        AwsHelper._client_cache = {}

    @patch.dict(os.environ, {'AWS_REGION': 'us-west-2'})
    def test_get_aws_region_from_env(self):
        """Test that get_aws_region returns the region from the environment."""
        region = AwsHelper.get_aws_region()
        assert region == 'us-west-2'

    @patch.dict(os.environ, {}, clear=True)
    def test_get_aws_region_default(self):
        """Test that get_aws_region returns None when not set in the environment."""
        region = AwsHelper.get_aws_region()
        assert region is None

    @patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'})
    def test_get_aws_profile_from_env(self):
        """Test that get_aws_profile returns the profile from the environment."""
        profile = AwsHelper.get_aws_profile()
        assert profile == 'test-profile'

    @patch.dict(os.environ, {}, clear=True)
    def test_get_aws_profile_none(self):
        """Test that get_aws_profile returns None when not set in the environment."""
        profile = AwsHelper.get_aws_profile()
        assert profile is None

    @patch('boto3.client')
    def test_create_boto3_client_no_profile_with_region(self, mock_boto3_client):
        """Test that create_boto3_client creates a client with the correct parameters when no profile is set but region is in env."""
        # Mock the get_aws_profile method to return None
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Mock the get_aws_region method to return a specific region
            with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
                with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                    # Call the create_boto3_client method
                    AwsHelper.create_boto3_client('cloudformation')

                    # Verify that boto3.client was called with the correct parameters
                    mock_boto3_client.assert_called_once_with(
                        'cloudformation', region_name='us-west-2', config=ANY
                    )

    @patch('boto3.client')
    def test_create_boto3_client_no_profile_no_region(self, mock_boto3_client):
        """Test that create_boto3_client creates a client without region when no profile or region is set."""
        # Mock the get_aws_profile method to return None
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Mock the get_aws_region method to return None
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                    # Call the create_boto3_client method
                    AwsHelper.create_boto3_client('cloudformation')

                    # Verify that boto3.client was called without region_name
                    mock_boto3_client.assert_called_once_with('cloudformation', config=ANY)

    @patch('boto3.Session')
    def test_create_boto3_client_with_profile_with_region(self, mock_boto3_session):
        """Test that create_boto3_client creates a client with the correct parameters when a profile is set and region is in env."""
        # Create a mock session
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session

        # Mock the get_aws_profile method to return a profile
        with patch.object(AwsHelper, 'get_aws_profile', return_value='test-profile'):
            # Mock the get_aws_region method to return a specific region
            with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
                with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                    # Call the create_boto3_client method
                    AwsHelper.create_boto3_client('cloudformation')

                    # Verify that boto3.Session was called with the correct parameters
                    mock_boto3_session.assert_called_once_with(profile_name='test-profile')

                    # Verify that session.client was called with the correct parameters
                    mock_session.client.assert_called_once_with(
                        'cloudformation', region_name='us-west-2', config=ANY
                    )

    @patch('boto3.Session')
    def test_create_boto3_client_with_profile_no_region(self, mock_boto3_session):
        """Test that create_boto3_client creates a client without region when a profile is set but no region."""
        # Create a mock session
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session

        # Mock the get_aws_profile method to return a profile
        with patch.object(AwsHelper, 'get_aws_profile', return_value='test-profile'):
            # Mock the get_aws_region method to return None
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                    # Call the create_boto3_client method
                    AwsHelper.create_boto3_client('cloudformation')

                    # Verify that boto3.Session was called with the correct parameters
                    mock_boto3_session.assert_called_once_with(profile_name='test-profile')

                    # Verify that session.client was called without region_name
                    mock_session.client.assert_called_once_with('cloudformation', config=ANY)

    @patch('boto3.client')
    def test_create_boto3_client_with_region_override(self, mock_boto3_client):
        """Test that create_boto3_client uses the region override when provided."""
        # Mock the get_aws_profile method to return None
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Call the create_boto3_client method with a region override
            AwsHelper.create_boto3_client('cloudformation', region_name='eu-west-1')

            # Verify that boto3.client was called with the correct parameters
            mock_boto3_client.assert_called_once_with(
                'cloudformation', region_name='eu-west-1', config=ANY
            )

    def test_create_boto3_client_user_agent(self):
        """Test that create_boto3_client sets the user agent suffix correctly using the package version."""
        # Create a real Config object to inspect
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                with patch('boto3.client') as mock_client:
                    # Call the create_boto3_client method
                    AwsHelper.create_boto3_client('cloudformation')

                    # Get the config argument passed to boto3.client
                    _, kwargs = mock_client.call_args
                    config = kwargs.get('config')

                    # Verify the user agent suffix uses the version from __init__.py
                    assert config is not None
                    expected_user_agent = f'awslabs/mcp/eks-mcp-server/{__version__}'
                    assert config.user_agent_extra == expected_user_agent

    @patch('boto3.client')
    def test_client_caching(self, mock_boto3_client):
        """Test that clients are cached and reused."""
        # Create a mock client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the get_aws_profile and get_aws_region methods
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                # Call create_boto3_client twice with the same parameters
                client1 = AwsHelper.create_boto3_client('cloudformation')
                client2 = AwsHelper.create_boto3_client('cloudformation')

                # Verify that boto3.client was called only once
                mock_boto3_client.assert_called_once()

                # Verify that the same client instance was returned both times
                assert client1 is client2

    @patch('boto3.client')
    def test_different_services_not_cached_together(self, mock_boto3_client):
        """Test that different services get different cached clients."""
        # Create mock clients
        mock_cf_client = MagicMock()
        mock_s3_client = MagicMock()
        mock_boto3_client.side_effect = [mock_cf_client, mock_s3_client]

        # Mock the get_aws_profile and get_aws_region methods
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                # Call create_boto3_client for different services
                cf_client = AwsHelper.create_boto3_client('cloudformation')
                s3_client = AwsHelper.create_boto3_client('s3')

                # Verify that boto3.client was called twice
                assert mock_boto3_client.call_count == 2

                # Verify that different client instances were returned
                assert cf_client is not s3_client

    @patch('boto3.client')
    def test_same_service_different_regions_cached_separately(self, mock_boto3_client):
        """Test that clients for the same service in different regions are cached separately."""
        # Create mock clients
        mock_client_us = MagicMock()
        mock_client_eu = MagicMock()
        mock_boto3_client.side_effect = [mock_client_us, mock_client_eu]

        # Mock the get_aws_profile method
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Call create_boto3_client for different regions
            us_west_client = AwsHelper.create_boto3_client(
                'cloudformation', region_name='us-west-2'
            )
            eu_west_client = AwsHelper.create_boto3_client(
                'cloudformation', region_name='eu-west-1'
            )

            # Verify that boto3.client was called twice (once for each region)
            assert mock_boto3_client.call_count == 2

            # Verify that different client instances were returned
            assert us_west_client is not eu_west_client
            assert us_west_client is mock_client_us
            assert eu_west_client is mock_client_eu

    @patch('boto3.client')
    def test_error_handling(self, mock_boto3_client):
        """Test that errors during client creation are handled properly."""
        # Make boto3.client raise an exception
        mock_boto3_client.side_effect = Exception('Test error')

        # Mock the get_aws_profile and get_aws_region methods
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                # Verify that the exception is re-raised with more context
                try:
                    AwsHelper.create_boto3_client('cloudformation')
                    assert False, 'Exception was not raised'
                except Exception as e:
                    assert 'Failed to create boto3 client for cloudformation: Test error' in str(e)

    @patch('boto3.Session')
    def test_same_service_different_profiles_cached_separately(self, mock_boto3_session):
        """Test that clients for the same service with different profiles are cached separately."""
        # Create mock sessions and clients
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_session1.client.return_value = mock_client1
        mock_session2.client.return_value = mock_client2
        mock_boto3_session.side_effect = [mock_session1, mock_session2]

        # Call create_boto3_client with different profiles
        with patch.object(AwsHelper, 'get_aws_profile', return_value='profile1'):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                client1 = AwsHelper.create_boto3_client('cloudformation')

        with patch.object(AwsHelper, 'get_aws_profile', return_value='profile2'):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                client2 = AwsHelper.create_boto3_client('cloudformation')

        # Verify that boto3.Session was called twice (once for each profile)
        assert mock_boto3_session.call_count == 2

        # Verify that different client instances were returned
        assert client1 is not client2
        assert client1 is mock_client1
        assert client2 is mock_client2

    def test_clear_cache(self):
        """Test that clear_cache clears both client and assumed role caches."""
        # Add some items to the caches
        AwsHelper._client_cache['test_key'] = 'test_client'
        AwsHelper._assumed_role_cache['test_role'] = 'test_credentials'

        # Clear the cache
        AwsHelper.clear_cache()

        # Verify that both caches are empty
        assert len(AwsHelper._client_cache) == 0
        assert len(AwsHelper._assumed_role_cache) == 0

    @patch('boto3.client')
    def test_assume_role_success(self, mock_boto3_client):
        """Test successful role assumption."""
        from datetime import datetime, timezone, timedelta

        # Mock STS client
        mock_sts_client = MagicMock()
        mock_boto3_client.return_value = mock_sts_client

        # Mock assume_role response
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'SessionToken': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c',
                'Expiration': expiration_time,
            }
        }

        # Call assume_role
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_sts_client):
            credentials = AwsHelper.assume_role(
                role_arn='arn:aws:iam::123456789012:role/TestRole',
                external_id='test-external-id',
            )

        # Verify the result
        assert credentials['AccessKeyId'] == 'AKIAIOSFODNN7EXAMPLE'
        assert credentials['SecretAccessKey'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        assert credentials['SessionToken'] == 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c'

        # Verify assume_role was called with correct parameters
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn='arn:aws:iam::123456789012:role/TestRole',
            RoleSessionName='eks-mcp-server',
            ExternalId='test-external-id',
        )

    @patch('boto3.client')
    def test_assume_role_without_external_id(self, mock_boto3_client):
        """Test role assumption without external ID."""
        from datetime import datetime, timezone, timedelta

        # Mock STS client
        mock_sts_client = MagicMock()
        mock_boto3_client.return_value = mock_sts_client

        # Mock assume_role response
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'SessionToken': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c',
                'Expiration': expiration_time,
            }
        }

        # Call assume_role without external_id
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_sts_client):
            credentials = AwsHelper.assume_role(
                role_arn='arn:aws:iam::123456789012:role/TestRole'
            )

        # Verify assume_role was called without ExternalId
        mock_sts_client.assume_role.assert_called_once_with(
            RoleArn='arn:aws:iam::123456789012:role/TestRole',
            RoleSessionName='eks-mcp-server',
        )

    @patch('boto3.client')
    def test_assume_role_caching(self, mock_boto3_client):
        """Test that assumed role credentials are cached."""
        from datetime import datetime, timezone, timedelta

        # Clear cache first
        AwsHelper.clear_cache()

        # Mock STS client
        mock_sts_client = MagicMock()
        mock_boto3_client.return_value = mock_sts_client

        # Mock assume_role response
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'SessionToken': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c',
                'Expiration': expiration_time,
            }
        }

        # Call assume_role twice with the same parameters
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_sts_client):
            credentials1 = AwsHelper.assume_role(
                role_arn='arn:aws:iam::123456789012:role/TestRole'
            )
            credentials2 = AwsHelper.assume_role(
                role_arn='arn:aws:iam::123456789012:role/TestRole'
            )

        # Verify assume_role was called only once (second call used cache)
        mock_sts_client.assume_role.assert_called_once()

        # Verify both calls returned the same credentials
        assert credentials1 == credentials2

    @patch('boto3.client')
    def test_assume_role_error(self, mock_boto3_client):
        """Test error handling in assume_role."""
        # Clear cache to ensure clean test
        AwsHelper.clear_cache()

        # Mock STS client to raise an exception
        mock_sts_client = MagicMock()
        mock_sts_client.assume_role.side_effect = Exception('AccessDenied')
        mock_boto3_client.return_value = mock_sts_client

        # Verify that the exception is re-raised with more context
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_sts_client):
            try:
                AwsHelper.assume_role(role_arn='arn:aws:iam::123456789012:role/TestRoleError')
                assert False, 'Exception was not raised'
            except Exception as e:
                assert 'Failed to assume role' in str(e)
                assert 'arn:aws:iam::123456789012:role/TestRoleError' in str(e)

    @patch('boto3.client')
    def test_create_boto3_client_for_account_region_with_profile(self, mock_boto3_client):
        """Test creating a client for a specific account and region using profile."""
        from awslabs.eks_mcp_server.config import AccountConfig, ClustersConfig, ConfigManager

        # Create test account config with profile
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Mock boto3.Session
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Call create_boto3_client_for_account_region
        with patch('boto3.Session', return_value=mock_session):
            result = AwsHelper.create_boto3_client_for_account_region(
                account_id='123456789012', region_name='us-west-2', service_name='eks'
            )

        # Verify that Session was created with the profile
        assert result == mock_client

    @patch('boto3.client')
    def test_create_boto3_client_for_account_region_with_role(self, mock_boto3_client):
        """Test creating a client for a specific account and region using role assumption."""
        from awslabs.eks_mcp_server.config import AccountConfig, ClustersConfig, ConfigManager
        from datetime import datetime, timezone, timedelta

        # Clear cache first
        AwsHelper.clear_cache()

        # Create test account config with role_arn
        account_config = AccountConfig(
            account_id='123456789012',
            regions=['us-west-2'],
            role_arn='arn:aws:iam::123456789012:role/TestRole',
        )
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Mock credentials
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_credentials = {
            'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
            'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'SessionToken': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c',
            'Expiration': expiration_time,
        }

        # Mock client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Call create_boto3_client_for_account_region
        with patch.object(AwsHelper, 'assume_role', return_value=mock_credentials):
            result = AwsHelper.create_boto3_client_for_account_region(
                account_id='123456789012', region_name='us-west-2', service_name='eks'
            )

        # Verify boto3.client was called with credentials
        assert result == mock_client
        mock_boto3_client.assert_called_once()
        call_kwargs = mock_boto3_client.call_args[1]
        assert call_kwargs['aws_access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert call_kwargs['aws_secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        assert (
            call_kwargs['aws_session_token']
            == 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c'
        )

    def test_create_boto3_client_for_account_region_account_not_found(self):
        """Test error when account is not found in configuration."""
        from awslabs.eks_mcp_server.config import AccountConfig, ClustersConfig, ConfigManager

        # Set config with one account, but request a different one
        account_config = AccountConfig(account_id='123456789012', regions=['us-west-2'])
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Verify that an exception is raised for non-existent account
        try:
            AwsHelper.create_boto3_client_for_account_region(
                account_id='999999999999', region_name='us-west-2', service_name='eks'
            )
            assert False, 'Exception was not raised'
        except Exception as e:
            assert 'Account 999999999999 not found' in str(e)

    def test_create_boto3_client_for_account_region_region_not_configured(self):
        """Test error when region is not configured for account."""
        from awslabs.eks_mcp_server.config import AccountConfig, ClustersConfig, ConfigManager

        # Create test account config with only us-east-1
        account_config = AccountConfig(account_id='123456789012', regions=['us-east-1'])
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Verify that an exception is raised for unconfigured region
        try:
            AwsHelper.create_boto3_client_for_account_region(
                account_id='123456789012', region_name='us-west-2', service_name='eks'
            )
            assert False, 'Exception was not raised'
        except Exception as e:
            assert 'Region us-west-2 not configured' in str(e)

    @patch('boto3.client')
    def test_create_boto3_client_for_cluster(self, mock_boto3_client):
        """Test creating a client for a specific cluster."""
        from awslabs.eks_mcp_server.config import (
            AccountConfig,
            ClusterConfig,
            ClustersConfig,
            ConfigManager,
        )

        # Create test config
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Create test cluster
        cluster = ClusterConfig(
            name='test-cluster', region='us-west-2', account_id='123456789012'
        )

        # Mock the client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Call create_boto3_client_for_cluster
        with patch.object(
            AwsHelper, 'create_boto3_client_for_account_region', return_value=mock_client
        ) as mock_create:
            result = AwsHelper.create_boto3_client_for_cluster(cluster, 'eks')

        # Verify the result
        assert result == mock_client
        mock_create.assert_called_once_with(
            account_id='123456789012', region_name='us-west-2', service_name='eks'
        )

    def test_create_boto3_client_for_cluster_error(self):
        """Test error handling in create_boto3_client_for_cluster."""
        from awslabs.eks_mcp_server.config import (
            AccountConfig,
            ClusterConfig,
            ClustersConfig,
            ConfigManager,
        )

        # Set config with one account, but cluster references a different account
        account_config = AccountConfig(account_id='123456789012', regions=['us-west-2'])
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Create test cluster with non-existent account
        cluster = ClusterConfig(
            name='test-cluster', region='us-west-2', account_id='999999999999'
        )

        # Verify that an exception is raised with cluster context
        try:
            AwsHelper.create_boto3_client_for_cluster(cluster, 'eks')
            assert False, 'Exception was not raised'
        except Exception as e:
            assert 'Failed to create boto3 client for eks' in str(e)
            assert 'cluster: test-cluster' in str(e)
