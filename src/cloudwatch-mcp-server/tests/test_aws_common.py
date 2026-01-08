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

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    def test_get_aws_client_with_profile_name(self, mock_session_class):
        """Test get_aws_client with explicit profile_name parameter."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_session = MagicMock()
        mock_session.region_name = 'us-west-2'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('logs', region_name='us-east-1', profile_name='my-profile')

        # Should create session with profile_name
        mock_session_class.assert_called_once_with(profile_name='my-profile')
        # Should create client with specified region
        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == 'logs'
        assert call_args[1]['region_name'] == 'us-east-1'
        assert result == mock_client

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_with_aws_profile_env(self, mock_getenv, mock_session_class):
        """Test get_aws_client falls back to AWS_PROFILE env var."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = 'env-profile'
        mock_session = MagicMock()
        mock_session.region_name = 'us-west-2'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('cloudwatch', region_name='eu-west-1')

        # Should get AWS_PROFILE from environment
        mock_getenv.assert_called_once_with('AWS_PROFILE', None)
        # Should create session with profile from env
        mock_session_class.assert_called_once_with(profile_name='env-profile')
        assert result == mock_client

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_without_profile(self, mock_getenv, mock_session_class):
        """Test get_aws_client without profile uses default credential chain."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('logs', region_name='ap-southeast-1')

        # Should create session without profile_name
        mock_session_class.assert_called_once_with()
        assert result == mock_client

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_region_fallback_to_session(self, mock_getenv, mock_session_class):
        """Test get_aws_client uses session region when region_name is None."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'eu-central-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('cloudwatch')

        # Should use session's region
        call_args = mock_session.client.call_args
        assert call_args[1]['region_name'] == 'eu-central-1'
        assert result == mock_client

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_region_fallback_to_us_east_1(self, mock_getenv, mock_session_class):
        """Test get_aws_client falls back to us-east-1 when no region is available."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = None  # No session region
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        result = get_aws_client('logs')

        # Should fall back to us-east-1
        call_args = mock_session.client.call_args
        assert call_args[1]['region_name'] == 'us-east-1'
        assert result == mock_client

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_user_agent_config(self, mock_getenv, mock_session_class):
        """Test get_aws_client sets proper user agent configuration."""
        from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        get_aws_client('logs', region_name='us-east-1')

        # Verify config was passed with user_agent_extra
        call_args = mock_session.client.call_args
        config = call_args[1]['config']
        assert f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}' in config.user_agent_extra

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    def test_get_aws_client_profile_takes_precedence_over_env(self, mock_session_class):
        """Test explicit profile_name takes precedence over AWS_PROFILE env var."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        # Even if AWS_PROFILE is set, explicit profile_name should be used
        with patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'}):
            get_aws_client('logs', profile_name='explicit-profile')

        # Should use explicit profile, not env profile
        mock_session_class.assert_called_once_with(profile_name='explicit-profile')

    @patch('awslabs.cloudwatch_mcp_server.aws_common.Session')
    @patch('awslabs.cloudwatch_mcp_server.aws_common.getenv')
    def test_get_aws_client_all_services(self, mock_getenv, mock_session_class):
        """Test get_aws_client works with different AWS service names."""
        from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client

        mock_getenv.return_value = None
        mock_session = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        services = ['logs', 'cloudwatch', 's3', 'ec2']
        for service in services:
            mock_session_class.reset_mock()
            mock_session.client.reset_mock()

            get_aws_client(service, region_name='us-east-1')

            call_args = mock_session.client.call_args
            assert call_args[0][0] == service
