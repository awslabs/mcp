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

"""Tests for AWS common utilities with multi-profile support."""

from unittest.mock import MagicMock, patch


class TestGetAwsClient:
    """Test get_aws_client function."""

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    def test_with_explicit_profile(self, mock_session_class):
        """Test get_aws_client with explicit profile_name parameter."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_session = MagicMock()
        mock_session.region_name = 'us-west-2'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ssm-sap', region_name='us-east-1', profile_name='my-profile')

        mock_session_class.assert_called_once_with(profile_name='my-profile')
        call_args = mock_session.client.call_args
        assert call_args[0][0] == 'ssm-sap'
        assert call_args[1]['region_name'] == 'us-east-1'
        assert result == mock_client

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.getenv')
    def test_with_aws_profile_env(self, mock_getenv, mock_session_class):
        """Test get_aws_client falls back to AWS_PROFILE env var."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_getenv.return_value = 'env-profile'
        mock_session = MagicMock()
        mock_session.region_name = 'us-west-2'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ssm-sap', region_name='eu-west-1')

        mock_getenv.assert_called_once_with('AWS_PROFILE', None)
        mock_session_class.assert_called_once_with(profile_name='env-profile')
        assert result == mock_client

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.getenv')
    def test_without_profile(self, mock_getenv, mock_session_class):
        """Test get_aws_client without profile uses default credential chain."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ssm-sap', region_name='ap-southeast-1')

        mock_session_class.assert_called_once_with()
        assert result == mock_client

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.getenv')
    def test_region_fallback_to_session(self, mock_getenv, mock_session_class):
        """Test get_aws_client uses session region when region_name is None."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'eu-central-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ssm-sap')

        call_args = mock_session.client.call_args
        assert call_args[1]['region_name'] == 'eu-central-1'
        assert result == mock_client

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.getenv')
    def test_region_fallback_to_us_east_1(self, mock_getenv, mock_session_class):
        """Test get_aws_client falls back to us-east-1 when no region is available."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = None
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('ssm-sap')

        call_args = mock_session.client.call_args
        assert call_args[1]['region_name'] == 'us-east-1'
        assert result == mock_client

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.getenv')
    def test_user_agent_config(self, mock_getenv, mock_session_class):
        """Test get_aws_client sets proper user agent configuration."""
        from awslabs.aws_for_sap_management_mcp_server import MCP_SERVER_VERSION
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        get_aws_client('ssm-sap', region_name='us-east-1')

        call_args = mock_session.client.call_args
        config = call_args[1]['config']
        assert (
            f'md/awslabs#mcp#aws-for-sap-management-mcp-server#{MCP_SERVER_VERSION}'
            in config.user_agent_extra
        )

    @patch('awslabs.aws_for_sap_management_mcp_server.client_factory.Session')
    def test_explicit_profile_takes_precedence(self, mock_session_class):
        """Test explicit profile_name takes precedence over AWS_PROFILE env var."""
        from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client

        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        with patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'}):
            get_aws_client('ssm-sap', profile_name='explicit-profile')

        mock_session_class.assert_called_once_with(profile_name='explicit-profile')
