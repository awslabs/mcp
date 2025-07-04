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
    def test_same_service_different_regions_cached_together(self, mock_boto3_client):
        """Test that clients for the same service are cached together regardless of region."""
        # Create mock client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the get_aws_profile method
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Call create_boto3_client for different regions
            us_west_client = AwsHelper.create_boto3_client(
                'cloudformation', region_name='us-west-2'
            )
            eu_west_client = AwsHelper.create_boto3_client(
                'cloudformation', region_name='eu-west-1'
            )

            # Verify that boto3.client was called only once
            mock_boto3_client.assert_called_once()

            # Verify that the same client instance was returned both times
            assert us_west_client is eu_west_client

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
    def test_same_service_different_profiles_cached_together(self, mock_boto3_session):
        """Test that clients for the same service are cached together regardless of profile."""
        # Create mock session and client
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3_session.return_value = mock_session

        # Call create_boto3_client with different profiles
        with patch.object(AwsHelper, 'get_aws_profile', return_value='profile1'):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                client1 = AwsHelper.create_boto3_client('cloudformation')

        with patch.object(AwsHelper, 'get_aws_profile', return_value='profile2'):
            with patch.object(AwsHelper, 'get_aws_region', return_value=None):
                client2 = AwsHelper.create_boto3_client('cloudformation')

        # Verify that boto3.Session was called only once
        mock_boto3_session.assert_called_once()

        # Verify that the same client instance was returned both times
        assert client1 is client2
