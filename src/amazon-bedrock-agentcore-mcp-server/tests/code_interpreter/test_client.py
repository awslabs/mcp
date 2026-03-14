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
    """Test cases for get_client."""

    def setup_method(self):
        """Reset client cache before each test."""
        aws_client._clients.clear()

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_creates_client_for_new_region(self, mock_ci_class):
        """Test creates a new client for an unseen region."""
        # Arrange
        mock_instance = MagicMock()
        mock_ci_class.return_value = mock_instance

        # Act
        client = aws_client.get_client('us-west-2')

        # Assert
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
        # Arrange
        mock_instance = MagicMock()
        mock_ci_class.return_value = mock_instance

        # Act
        client1 = aws_client.get_client('us-east-1')
        client2 = aws_client.get_client('us-east-1')

        # Assert
        assert client1 is client2
        mock_ci_class.assert_called_once()

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_different_regions_get_different_clients(self, mock_ci_class):
        """Test different regions get separate client instances."""
        # Arrange
        mock_ci_class.side_effect = [MagicMock(), MagicMock()]

        # Act
        client1 = aws_client.get_client('us-east-1')
        client2 = aws_client.get_client('eu-west-1')

        # Assert
        assert client1 is not client2
        assert mock_ci_class.call_count == 2

    @patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.client.CodeInterpreter'
    )
    def test_defaults_region_from_env(self, mock_ci_class):
        """Test uses default region when None is passed."""
        # Arrange
        mock_ci_class.return_value = MagicMock()

        # Act
        with patch.dict(os.environ, {'AWS_REGION': 'ap-northeast-1'}):
            aws_client.get_client(None)

        # Assert
        mock_ci_class.assert_called_once_with(
            region='ap-northeast-1',
            integration_source='awslabs-mcp-code-interpreter-server',
        )


class TestClearClients:
    """Test cases for clear_clients."""

    def setup_method(self):
        """Reset client cache before each test."""
        aws_client._clients.clear()

    def test_clears_all_cached_clients(self):
        """Test clears the entire client cache."""
        # Arrange
        aws_client._clients['us-east-1'] = MagicMock()
        aws_client._clients['eu-west-1'] = MagicMock()

        # Act
        aws_client.clear_clients()

        # Assert
        assert len(aws_client._clients) == 0


class TestStopAllSessions:
    """Test cases for stop_all_sessions."""

    def setup_method(self):
        """Reset client cache before each test."""
        aws_client._clients.clear()

    @patch.object(aws_client, 'clear_clients')
    async def test_stops_active_sessions_and_clears(self, mock_clear):
        """Test stops sessions on all clients that have active sessions."""
        # Arrange
        client1 = MagicMock()
        client1.session_id = 'session-1'
        client2 = MagicMock()
        client2.session_id = 'session-2'
        aws_client._clients['us-east-1'] = client1
        aws_client._clients['eu-west-1'] = client2

        # Act
        await aws_client.stop_all_sessions()

        # Assert
        client1.stop.assert_called_once()
        client2.stop.assert_called_once()
        mock_clear.assert_called_once()

    @patch.object(aws_client, 'clear_clients')
    async def test_skips_clients_without_sessions(self, mock_clear):
        """Test skips clients that don't have active sessions."""
        # Arrange
        client_active = MagicMock()
        client_active.session_id = 'session-1'
        client_idle = MagicMock()
        client_idle.session_id = None
        aws_client._clients['us-east-1'] = client_active
        aws_client._clients['eu-west-1'] = client_idle

        # Act
        await aws_client.stop_all_sessions()

        # Assert
        client_active.stop.assert_called_once()
        client_idle.stop.assert_not_called()
        mock_clear.assert_called_once()

    @patch.object(aws_client, 'clear_clients')
    async def test_handles_stop_failure_gracefully(self, mock_clear):
        """Test continues even if stopping a session fails."""
        # Arrange
        client1 = MagicMock()
        client1.session_id = 'session-1'
        client1.stop.side_effect = Exception('Connection refused')
        client2 = MagicMock()
        client2.session_id = 'session-2'
        aws_client._clients['us-east-1'] = client1
        aws_client._clients['eu-west-1'] = client2

        # Act
        await aws_client.stop_all_sessions()

        # Assert
        client1.stop.assert_called_once()
        client2.stop.assert_called_once()
        mock_clear.assert_called_once()
