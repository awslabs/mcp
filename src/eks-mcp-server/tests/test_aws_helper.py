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
"""Tests for the AWS Helper."""

import os
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from unittest.mock import MagicMock, patch


class TestAwsHelper:
    """Tests for the AwsHelper class."""

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
                        'cloudformation', region_name='us-west-2'
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
                    mock_boto3_client.assert_called_once_with('cloudformation')

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
                        'cloudformation', region_name='us-west-2'
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
                    mock_session.client.assert_called_once_with('cloudformation')

    @patch('boto3.client')
    def test_create_boto3_client_with_region_override(self, mock_boto3_client):
        """Test that create_boto3_client uses the region override when provided."""
        # Mock the get_aws_profile method to return None
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            # Call the create_boto3_client method with a region override
            AwsHelper.create_boto3_client('cloudformation', region_name='eu-west-1')

            # Verify that boto3.client was called with the correct parameters
            mock_boto3_client.assert_called_once_with('cloudformation', region_name='eu-west-1')
