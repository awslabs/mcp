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
"""Test cases for the aws_common utils module."""

import pytest
from awslabs.aws_network_mcp_server.utils.aws_common import get_account_id, get_aws_client
from unittest.mock import MagicMock, patch


class TestAwsCommon:
    """Test cases for aws_common utility functions."""

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.Session')
    def test_get_aws_client_with_profile(self, mock_session_class, mock_client):
        """Test get_aws_client with profile name."""
        mock_session = MagicMock()
        mock_session_client = MagicMock()
        mock_session.client.return_value = mock_session_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ec2', 'us-east-1', 'test-profile')

        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once_with('ec2', region_name='us-east-1')
        assert result == mock_session_client
        mock_client.assert_not_called()

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.getenv')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    def test_get_aws_client_without_profile(self, mock_client, mock_getenv):
        """Test get_aws_client without profile name."""
        mock_getenv.return_value = None
        mock_boto_client = MagicMock()
        mock_client.return_value = mock_boto_client

        result = get_aws_client('ec2', 'us-west-2', None)

        mock_client.assert_called_once_with('ec2', region_name='us-west-2')
        assert result == mock_boto_client

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.getenv')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    def test_get_aws_client_default_region_from_env(self, mock_client, mock_getenv):
        """Test get_aws_client with default region from environment."""
        mock_getenv.side_effect = (
            lambda key, default: 'eu-central-1' if key == 'AWS_REGION' else default
        )
        mock_boto_client = MagicMock()
        mock_client.return_value = mock_boto_client

        result = get_aws_client('s3', None, None)

        mock_client.assert_called_once_with('s3', region_name='eu-central-1')
        assert result == mock_boto_client

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.getenv')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    def test_get_aws_client_default_region_fallback(self, mock_client, mock_getenv):
        """Test get_aws_client with default region fallback."""
        mock_getenv.side_effect = lambda key, default: default
        mock_boto_client = MagicMock()
        mock_client.return_value = mock_boto_client

        result = get_aws_client('lambda', None, None)

        mock_client.assert_called_once_with('lambda', region_name='us-east-1')
        assert result == mock_boto_client

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.getenv')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.Session')
    def test_get_aws_client_profile_from_env(self, mock_session_class, mock_getenv):
        """Test get_aws_client with profile from environment."""
        mock_getenv.side_effect = (
            lambda key, default: 'env-profile' if key == 'AWS_PROFILE' else default
        )
        mock_session = MagicMock()
        mock_session_client = MagicMock()
        mock_session.client.return_value = mock_session_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('rds', 'ap-southeast-2', None)

        mock_session_class.assert_called_once_with(profile_name='env-profile')
        mock_session.client.assert_called_once_with('rds', region_name='ap-southeast-2')
        assert result == mock_session_client

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.getenv')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.Session')
    def test_get_aws_client_both_env_vars_set(self, mock_session_class, mock_getenv):
        """Test get_aws_client with both AWS_REGION and AWS_PROFILE from environment."""
        mock_getenv.side_effect = lambda key, default: {
            'AWS_REGION': 'ca-central-1',
            'AWS_PROFILE': 'env-profile',
        }.get(key, default)

        mock_session = MagicMock()
        mock_session_client = MagicMock()
        mock_session.client.return_value = mock_session_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('dynamodb', None, None)

        mock_session_class.assert_called_once_with(profile_name='env-profile')
        mock_session.client.assert_called_once_with('dynamodb', region_name='ca-central-1')
        assert result == mock_session_client

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    @patch('awslabs.aws_network_mcp_server.utils.aws_common.Session')
    def test_get_account_id_with_profile(self, mock_session_class, mock_client):
        """Test get_account_id with profile name."""
        mock_session = MagicMock()
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        result = get_account_id('test-profile')

        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once_with('sts')
        mock_sts_client.get_caller_identity.assert_called_once()
        assert result == '123456789012'
        mock_client.assert_not_called()

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    def test_get_account_id_without_profile(self, mock_client):
        """Test get_account_id without profile name."""
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {'Account': '987654321098'}
        mock_client.return_value = mock_sts_client

        result = get_account_id(None)

        mock_client.assert_called_once_with('sts')
        mock_sts_client.get_caller_identity.assert_called_once()
        assert result == '987654321098'

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.client')
    def test_get_account_id_error_handling(self, mock_client):
        """Test get_account_id error handling."""
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.side_effect = Exception('NoCredentialsError')
        mock_client.return_value = mock_sts_client

        with pytest.raises(Exception) as exc_info:
            get_account_id(None)

        assert 'NoCredentialsError' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.utils.aws_common.Session')
    def test_get_account_id_with_profile_error(self, mock_session_class):
        """Test get_account_id with profile error handling."""
        mock_session = MagicMock()
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.side_effect = Exception('ProfileNotFound')
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        with pytest.raises(Exception) as exc_info:
            get_account_id('invalid-profile')

        assert 'ProfileNotFound' in str(exc_info.value)
