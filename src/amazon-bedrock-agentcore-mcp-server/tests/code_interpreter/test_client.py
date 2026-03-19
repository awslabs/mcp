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

"""Tests for the AWS client factory module."""

import os
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import client as aws_client
from unittest.mock import MagicMock, patch


class TestGetDefaultRegion:
    """Test cases for get_default_region."""

    def test_returns_aws_region_env_var(self):
        """Test returns AWS_REGION when set."""
        with patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}):
            assert aws_client.get_default_region() == 'eu-west-1'

    def test_falls_back_to_us_east_1(self):
        """Test falls back to us-east-1 when no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            assert aws_client.get_default_region() == 'us-east-1'


class TestGetDefaultIdentifier:
    """Test cases for get_default_identifier."""

    def test_returns_env_var_when_set(self):
        """Test returns CODE_INTERPRETER_IDENTIFIER when set."""
        with patch.dict(os.environ, {'CODE_INTERPRETER_IDENTIFIER': 'custom.v2'}):
            assert aws_client.get_default_identifier() == 'custom.v2'

    def test_falls_back_to_default(self):
        """Test falls back to default identifier."""
        with patch.dict(os.environ, {}, clear=True):
            assert aws_client.get_default_identifier() == 'aws.codeinterpreter.v1'


class TestGetClient:
    """Test cases for get_client (region-level operations)."""

    def setup_method(self):
        """Reset client caches before each test."""
        aws_client._region_clients.clear()

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_creates_client_for_new_region(self, mock_ci_class):
        """Test creates a new client for an unseen region."""
        mock_instance = MagicMock()
        mock_ci_class.return_value = mock_instance

        client = aws_client.get_client('us-west-2')

        assert client is mock_instance
        mock_ci_class.assert_called_once_with(
            region='us-west-2',
            integration_source='awslabs-mcp-code-interpreter-server',
        )

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_caches_client_per_region(self, mock_ci_class):
        """Test returns the same cached client for the same region."""
        mock_instance = MagicMock()
        mock_ci_class.return_value = mock_instance

        client1 = aws_client.get_client('us-east-1')
        client2 = aws_client.get_client('us-east-1')

        assert client1 is client2
        mock_ci_class.assert_called_once()

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_different_regions_get_different_clients(self, mock_ci_class):
        """Test different regions get separate client instances."""
        mock_ci_class.side_effect = [MagicMock(), MagicMock()]

        client1 = aws_client.get_client('us-east-1')
        client2 = aws_client.get_client('eu-west-1')

        assert client1 is not client2
        assert mock_ci_class.call_count == 2

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_defaults_region_from_env(self, mock_ci_class):
        """Test uses default region when None is passed."""
        mock_ci_class.return_value = MagicMock()

        with patch.dict(os.environ, {'AWS_REGION': 'ap-northeast-1'}):
            aws_client.get_client(None)

        mock_ci_class.assert_called_once_with(
            region='ap-northeast-1',
            integration_source='awslabs-mcp-code-interpreter-server',
        )


class TestCreateSessionClient:
    """Test cases for create_session_client."""

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_creates_new_client_each_time(self, mock_ci_class):
        """Test creates a new client instance for each call."""
        client1_mock = MagicMock()
        client2_mock = MagicMock()
        mock_ci_class.side_effect = [client1_mock, client2_mock]

        client1 = aws_client.create_session_client('us-east-1')
        client2 = aws_client.create_session_client('us-east-1')

        assert client1 is not client2
        assert mock_ci_class.call_count == 2

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_defaults_region_from_env(self, mock_ci_class):
        """Test uses default region when None is passed."""
        mock_ci_class.return_value = MagicMock()

        with patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}):
            aws_client.create_session_client(None)

        mock_ci_class.assert_called_once_with(
            region='eu-west-1',
            integration_source='awslabs-mcp-code-interpreter-server',
        )


class TestSessionClientRegistry:
    """Test cases for register, get, and remove session client."""

    def setup_method(self):
        """Reset session clients before each test."""
        aws_client._session_clients.clear()

    def test_register_and_get_session_client(self):
        """Test registering and retrieving a session client."""
        mock_client = MagicMock()
        aws_client.register_session_client('session-1', mock_client)

        result = aws_client.get_session_client('session-1')
        assert result is mock_client

    def test_get_unregistered_session_raises_key_error(self):
        """Test getting an unregistered session raises KeyError."""
        with pytest.raises(KeyError, match='No active session client'):
            aws_client.get_session_client('nonexistent')

    def test_register_multiple_sessions(self):
        """Test multiple sessions can be registered independently."""
        client_a = MagicMock()
        client_b = MagicMock()
        aws_client.register_session_client('session-a', client_a)
        aws_client.register_session_client('session-b', client_b)

        assert aws_client.get_session_client('session-a') is client_a
        assert aws_client.get_session_client('session-b') is client_b

    def test_remove_session_client(self):
        """Test removing a session client."""
        mock_client = MagicMock()
        aws_client.register_session_client('session-1', mock_client)
        aws_client.remove_session_client('session-1')

        with pytest.raises(KeyError):
            aws_client.get_session_client('session-1')

    def test_remove_nonexistent_session_is_safe(self):
        """Test removing a session that doesn't exist is a no-op."""
        aws_client.remove_session_client('nonexistent')
        # No error raised


class TestClearClients:
    """Test cases for clear_clients."""

    def setup_method(self):
        """Reset all caches before each test."""
        aws_client._region_clients.clear()
        aws_client._session_clients.clear()

    def test_clears_all_cached_clients(self):
        """Test clears both region and session client caches."""
        aws_client._region_clients['us-east-1'] = MagicMock()
        aws_client._region_clients['eu-west-1'] = MagicMock()
        aws_client._session_clients['session-1'] = MagicMock()

        aws_client.clear_clients()

        assert len(aws_client._region_clients) == 0
        assert len(aws_client._session_clients) == 0


class TestStopAllSessions:
    """Test cases for stop_all_sessions."""

    def setup_method(self):
        """Reset all caches before each test."""
        aws_client._region_clients.clear()
        aws_client._session_clients.clear()

    @patch.object(aws_client, 'clear_clients')
    async def test_stops_all_session_clients(self, mock_clear):
        """Test stops all per-session clients."""
        client_a = MagicMock()
        client_b = MagicMock()
        aws_client._session_clients['session-a'] = client_a
        aws_client._session_clients['session-b'] = client_b

        await aws_client.stop_all_sessions()

        client_a.stop.assert_called_once()
        client_b.stop.assert_called_once()
        mock_clear.assert_called_once()

    @patch.object(aws_client, 'clear_clients')
    async def test_handles_stop_failure_gracefully(self, mock_clear):
        """Test continues even if stopping a session fails."""
        client_a = MagicMock()
        client_a.stop.side_effect = Exception('Connection refused')
        client_b = MagicMock()
        aws_client._session_clients['session-a'] = client_a
        aws_client._session_clients['session-b'] = client_b

        await aws_client.stop_all_sessions()

        client_a.stop.assert_called_once()
        client_b.stop.assert_called_once()
        mock_clear.assert_called_once()

    @patch.object(aws_client, 'clear_clients')
    async def test_empty_sessions_just_clears(self, mock_clear):
        """Test with no sessions just calls clear."""
        await aws_client.stop_all_sessions()

        mock_clear.assert_called_once()
