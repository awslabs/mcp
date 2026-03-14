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

"""Tests for session lifecycle tools."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import session
from unittest.mock import MagicMock, patch


MODULE_PATH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.session'


class TestStartCodeInterpreterSession:
    """Test cases for start_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_happy_path(self, mock_identifier, mock_get_client):
        """Test starting a session returns correct response."""
        # Arrange — SDK start() returns session_id as a string
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'new-session-id'
        mock_get_client.return_value = mock_client

        # Act
        result = await session.start_code_interpreter_session()

        # Assert — returned session_id takes priority over client.session_id
        assert result['session_id'] == 'new-session-id'
        assert result['status'] == 'READY'
        assert result['code_interpreter_identifier'] == 'aws.codeinterpreter.v1'
        mock_client.start.assert_called_once_with(identifier='aws.codeinterpreter.v1')

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_with_optional_params(self, mock_identifier, mock_get_client):
        """Test starting a session with name and timeout."""
        # Arrange — SDK start() returns session_id as a string
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'named-session'
        mock_get_client.return_value = mock_client

        # Act
        result = await session.start_code_interpreter_session(
            name='my-session',
            session_timeout_seconds=3600,
            region='eu-west-1',
        )

        # Assert
        assert result['session_id'] == 'named-session'
        mock_client.start.assert_called_once_with(
            identifier='aws.codeinterpreter.v1',
            name='my-session',
            session_timeout_seconds=3600,
        )
        mock_get_client.assert_called_once_with('eu-west-1')

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_with_custom_identifier(self, mock_identifier, mock_get_client):
        """Test starting a session with a custom identifier."""
        # Arrange — SDK start() returns session_id as a string
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'custom-session'
        mock_get_client.return_value = mock_client

        # Act
        result = await session.start_code_interpreter_session(
            code_interpreter_identifier='custom.v2',
        )

        # Assert
        assert result['session_id'] == 'custom-session'
        assert result['code_interpreter_identifier'] == 'custom.v2'
        mock_client.start.assert_called_once_with(identifier='custom.v2')

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_returns_error_on_sdk_failure(
        self, mock_identifier, mock_get_client
    ):
        """Test starting a session returns structured error on SDK error."""
        # Arrange
        mock_client = MagicMock()
        mock_client.start.side_effect = Exception('Access denied')
        mock_get_client.return_value = mock_client

        # Act
        result = await session.start_code_interpreter_session()

        # Assert — returns structured error, not exception
        assert result['session_id'] == ''
        assert result['status'] == 'ERROR'
        assert 'Access denied' in result['message']


class TestStopCodeInterpreterSession:
    """Test cases for stop_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_happy_path(self, mock_identifier, mock_get_client):
        """Test stopping a session calls stop then verifies via get_session."""
        # Arrange — SDK stop() returns bool, then we verify with get_session()
        mock_client = MagicMock()
        mock_client.stop.return_value = True
        mock_client.get_session.return_value = {'status': 'TERMINATED'}
        mock_get_client.return_value = mock_client

        # Act
        result = await session.stop_code_interpreter_session(session_id='session-to-stop')

        # Assert — status comes from get_session(), not hardcoded
        assert result['session_id'] == 'session-to-stop'
        assert result['status'] == 'TERMINATED'
        assert mock_client.session_id == 'session-to-stop'
        mock_client.stop.assert_called_once()
        mock_client.get_session.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            session_id='session-to-stop',
        )

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_stop_returns_false(self, mock_identifier, mock_get_client):
        """Test stop returning False still verifies status via get_session."""
        # Arrange — stop() returns False but session may still be terminating
        mock_client = MagicMock()
        mock_client.stop.return_value = False
        mock_client.get_session.return_value = {'status': 'READY'}
        mock_get_client.return_value = mock_client

        # Act
        result = await session.stop_code_interpreter_session(session_id='stuck-session')

        # Assert — reports actual status from get_session
        assert result['session_id'] == 'stuck-session'
        assert result['status'] == 'READY'
        mock_client.stop.assert_called_once()
        mock_client.get_session.assert_called_once()

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_returns_error_on_sdk_failure(
        self, mock_identifier, mock_get_client
    ):
        """Test stopping a session returns structured error on SDK error."""
        # Arrange
        mock_client = MagicMock()
        mock_client.stop.side_effect = Exception('Session not found')
        mock_get_client.return_value = mock_client

        # Act
        result = await session.stop_code_interpreter_session(session_id='bad-session')

        # Assert — returns structured error, not exception
        assert result['session_id'] == 'bad-session'
        assert result['status'] == 'ERROR'
        assert 'Session not found' in result['message']


class TestGetCodeInterpreterSession:
    """Test cases for get_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_happy_path(self, mock_identifier, mock_get_client):
        """Test getting session status returns correct response."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_session.return_value = {'status': 'READY'}
        mock_get_client.return_value = mock_client

        # Act
        result = await session.get_code_interpreter_session(session_id='session-123')

        # Assert
        assert result['session_id'] == 'session-123'
        assert result['status'] == 'READY'
        mock_client.get_session.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            session_id='session-123',
        )

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_handles_non_dict_response(self, mock_identifier, mock_get_client):
        """Test handles unexpected non-dict response gracefully."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_session.return_value = 'unexpected'
        mock_get_client.return_value = mock_client

        # Act
        result = await session.get_code_interpreter_session(session_id='session-123')

        # Assert
        assert result['status'] == 'UNKNOWN'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_returns_error_on_sdk_failure(
        self, mock_identifier, mock_get_client
    ):
        """Test getting a nonexistent session returns structured error."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_session.side_effect = Exception('Session not found: INVALID')
        mock_get_client.return_value = mock_client

        # Act
        result = await session.get_code_interpreter_session(session_id='INVALID')

        # Assert — returns structured error, not exception
        assert result['session_id'] == 'INVALID'
        assert result['status'] == 'ERROR'
        assert 'Session not found' in result['message']


class TestListCodeInterpreterSessions:
    """Test cases for list_code_interpreter_sessions."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_happy_path(
        self, mock_identifier, mock_get_client, sample_list_sessions_response
    ):
        """Test listing sessions returns formatted response."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = sample_list_sessions_response
        mock_get_client.return_value = mock_client

        # Act
        result = await session.list_code_interpreter_sessions()

        # Assert
        assert len(result['sessions']) == 2
        assert result['sessions'][0]['session_id'] == 'session-1'
        assert result['sessions'][0]['status'] == 'READY'
        assert result['sessions'][1]['session_id'] == 'session-2'
        assert result['sessions'][1]['status'] == 'TERMINATED'
        assert result['message'] == 'Found 2 session(s).'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_with_filters(self, mock_identifier, mock_get_client):
        """Test listing sessions passes filter parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {'items': [], 'nextToken': None}
        mock_get_client.return_value = mock_client

        # Act
        result = await session.list_code_interpreter_sessions(
            status='READY',
            max_results=10,
            next_token='page-2',
        )

        # Assert
        mock_client.list_sessions.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            status='READY',
            max_results=10,
            next_token='page-2',
        )
        assert result['message'] == 'Found 0 session(s).'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_empty(self, mock_identifier, mock_get_client):
        """Test listing sessions returns empty list gracefully."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {'items': []}
        mock_get_client.return_value = mock_client

        # Act
        result = await session.list_code_interpreter_sessions()

        # Assert
        assert result['sessions'] == []
        assert result['next_token'] is None

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_returns_error_on_sdk_failure(
        self, mock_identifier, mock_get_client
    ):
        """Test listing sessions returns structured error on SDK error."""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_sessions.side_effect = Exception('Invalid token')
        mock_get_client.return_value = mock_client

        # Act
        result = await session.list_code_interpreter_sessions(next_token='bad-token')

        # Assert — returns structured error, not exception
        assert result['sessions'] == []
        assert result['next_token'] is None
        assert 'Invalid token' in result['message']
