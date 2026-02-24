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
"""Tests for the AWS client factory."""

from awslabs.mwaa_mcp_server.aws_client import get_mwaa_client
from unittest.mock import MagicMock, patch


class TestGetMwaaClient:
    """Tests for the get_mwaa_client function."""

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_default_region_fallback(self, mock_session_cls):
        """Test that us-east-1 is used when no region is specified."""
        mock_session = MagicMock()
        mock_session.region_name = None
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        assert call_kwargs[1]['region_name'] == 'us-east-1'

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_explicit_region(self, mock_session_cls):
        """Test that explicit region_name parameter is used."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client(region_name='eu-west-1')

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        assert call_kwargs[1]['region_name'] == 'eu-west-1'

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_session_region_fallback(self, mock_session_cls):
        """Test that session region is used when no explicit region."""
        mock_session = MagicMock()
        mock_session.region_name = 'ap-southeast-1'
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        assert call_kwargs[1]['region_name'] == 'ap-southeast-1'

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_explicit_profile(self, mock_session_cls):
        """Test that explicit profile_name is passed to session."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client(profile_name='my-profile')

        mock_session_cls.assert_called_once_with(profile_name='my-profile')

    @patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'})
    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_profile_from_env(self, mock_session_cls):
        """Test that AWS_PROFILE env var is used when no explicit profile."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session_cls.assert_called_once_with(profile_name='env-profile')

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_no_profile(self, mock_session_cls):
        """Test that session is created without profile when none specified."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session_cls.assert_called_once_with()

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_user_agent_set(self, mock_session_cls):
        """Test that custom user-agent is set on the client config."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        config = call_kwargs[1]['config']
        assert 'awslabs/mcp/mwaa-mcp-server/' in config.user_agent_extra

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_service_name_is_mwaa(self, mock_session_cls):
        """Test that the client is created for the 'mwaa' service."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == 'mwaa'

    @patch('awslabs.mwaa_mcp_server.aws_client.Session')
    def test_timeouts_configured(self, mock_session_cls):
        """Test that read and connect timeouts are configured."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        get_mwaa_client()

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        config = call_kwargs[1]['config']
        assert config.read_timeout == 30
        assert config.connect_timeout == 10
