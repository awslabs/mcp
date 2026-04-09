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

"""Tests for runtime_client.py — client caching, region handling, user-agent."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.runtime_client import (
    MCP_CONTROL_USER_AGENT,
    MCP_DATA_USER_AGENT,
    _control_clients,
    _data_clients,
    get_control_client,
    get_data_client,
)
from unittest.mock import MagicMock, patch


CLIENT_MODULE = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.runtime_client'


def _extract_config(mock_session):
    """Extract the Config object from a mock session.client() call."""
    call_kwargs = mock_session.client.call_args
    return call_kwargs.kwargs.get('config') or call_kwargs[1].get('config')


class TestGetControlClient:
    """Tests for get_control_client."""

    def setup_method(self):
        """Clear cached clients before each test."""
        _control_clients.clear()

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_creates_client_on_first_call(self, mock_session_cls):
        """First call creates a new client via boto3 Session."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        result = get_control_client('us-west-2')

        mock_session_cls.assert_called_once_with(region_name='us-west-2')
        mock_session.client.assert_called_once()
        assert mock_session.client.call_args[0][0] == 'bedrock-agentcore-control'
        assert result is mock_client

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_caches_client(self, mock_session_cls):
        """Second call for same region returns cached client."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        c1 = get_control_client('us-east-1')
        c2 = get_control_client('us-east-1')

        assert c1 is c2
        assert mock_session_cls.call_count == 1

    @patch.dict('os.environ', {}, clear=True)
    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_defaults_to_us_east_1(self, mock_session_cls):
        """No region argument and no AWS_REGION env var defaults to us-east-1."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_control_client()
        mock_session_cls.assert_called_once_with(region_name='us-east-1')

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_control_user_agent_tracking(self, mock_session_cls):
        """Control client includes runtime-control user-agent for usage tracking."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_control_client('us-east-1')

        config = _extract_config(mock_session)
        assert config is not None, 'boto3 client must be created with a Config'
        assert MCP_CONTROL_USER_AGENT in config.user_agent_extra
        assert 'runtime-control' in config.user_agent_extra


class TestGetDataClient:
    """Tests for get_data_client."""

    def setup_method(self):
        """Clear cached clients before each test."""
        _data_clients.clear()

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_creates_data_client(self, mock_session_cls):
        """First call creates a data-plane client."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        result = get_data_client('eu-west-1')

        mock_session.client.assert_called_once()
        assert mock_session.client.call_args[0][0] == 'bedrock-agentcore'
        assert result is mock_client

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_caches_data_client(self, mock_session_cls):
        """Second call for same region returns cached data client."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        c1 = get_data_client('us-west-2')
        c2 = get_data_client('us-west-2')

        assert c1 is c2
        assert mock_session_cls.call_count == 1

    @patch(f'{CLIENT_MODULE}.boto3.Session')
    def test_data_user_agent_tracking(self, mock_session_cls):
        """Data client includes runtime user-agent for usage tracking."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_data_client('us-east-1')

        config = _extract_config(mock_session)
        assert config is not None, 'boto3 client must be created with a Config'
        assert MCP_DATA_USER_AGENT in config.user_agent_extra
        assert 'runtime-control' not in config.user_agent_extra
