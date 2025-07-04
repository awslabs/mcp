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
"""Tests for the credential awareness in the cfn MCP Server."""

import pytest
from awslabs.ccapi_mcp_server.server import get_aws_profile_info, get_aws_session_info
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
class TestCredentialAwareness:
    """Test credential awareness functionality."""

    @patch('awslabs.ccapi_mcp_server.server.get_aws_client')
    @patch('awslabs.ccapi_mcp_server.server.environ')
    async def test_get_aws_session_info(self, mock_environ, mock_get_aws_client):
        """Test getting AWS session info."""
        # Setup mocks
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }
        mock_get_aws_client.return_value = mock_sts_client

        mock_environ.get.side_effect = lambda key, default=None: {
            'AWS_CREDENTIAL_SOURCE': 'profile',
            'AWS_PROFILE': 'test-profile',
            'AWS_REGION': 'us-east-1',
        }.get(key, default)

        # Call the function
        result = await get_aws_session_info({'properly_configured': True})

        # Verify results
        assert result['profile'] == 'test-profile'
        assert result['account_id'] == '123456789012'
        assert result['region'] == 'us-east-1'
        assert result['arn'] == 'arn:aws:iam::123456789012:user/test-user'
        assert result['credential_source'] == 'profile'

    @patch('awslabs.ccapi_mcp_server.server.get_aws_client')
    @patch('awslabs.ccapi_mcp_server.server.environ')
    def test_get_aws_profile_info_success(self, mock_environ, mock_get_aws_client):
        """Test getting AWS profile info successfully."""
        # Setup mocks
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user',
        }
        mock_get_aws_client.return_value = mock_sts_client

        mock_environ.get.side_effect = lambda key, default=None: {
            'AWS_CREDENTIAL_SOURCE': 'env',
            'AWS_PROFILE': 'default',
            'AWS_REGION': 'us-west-2',
        }.get(key, default)

        # Call the function
        result = get_aws_profile_info()

        # Verify results
        assert result['profile'] == 'default'
        assert result['account_id'] == '123456789012'
        assert result['region'] == 'us-west-2'
        assert result['arn'] == 'arn:aws:iam::123456789012:user/test-user'
        assert result['credential_source'] == 'env'

    @patch('awslabs.ccapi_mcp_server.server.get_aws_client')
    @patch('awslabs.ccapi_mcp_server.server.environ')
    def test_get_aws_profile_info_error(self, mock_environ, mock_get_aws_client):
        """Test getting AWS profile info with an error."""
        # Setup mocks
        mock_get_aws_client.side_effect = Exception('Failed to get client')

        mock_environ.get.side_effect = lambda key, default=None: {
            'AWS_CREDENTIAL_SOURCE': 'auto',
            'AWS_PROFILE': 'default',
            'AWS_REGION': 'us-east-1',
        }.get(key, default)

        # Call the function
        result = get_aws_profile_info()

        # Verify results
        assert result['profile'] == 'default'
        assert 'error' in result
        assert result['region'] == 'us-east-1'
        assert result['credential_source'] == 'auto'
