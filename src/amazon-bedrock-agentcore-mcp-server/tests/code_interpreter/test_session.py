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

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import session
from unittest.mock import MagicMock, patch


MODULE_PATH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.session'


class TestStartCodeInterpreterSession:
    """Test cases for start_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_happy_path(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test starting a session creates a per-session client and registers it."""
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'new-session-id'
        mock_create.return_value = mock_client

        result = await session.start_code_interpreter_session(mock_ctx)

        assert result.session_id == 'new-session-id'
        assert result.status == 'READY'
        assert result.code_interpreter_identifier == 'aws.codeinterpreter.v1'
        mock_client.start.assert_called_once_with(identifier='aws.codeinterpreter.v1')
        mock_register.assert_called_once_with('new-session-id', mock_client)

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_with_optional_params(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test starting a session with name and timeout."""
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'named-session'
        mock_create.return_value = mock_client

        result = await session.start_code_interpreter_session(
            mock_ctx,
            name='my-session',
            session_timeout_seconds=3600,
            region='eu-west-1',
        )

        assert result.session_id == 'named-session'
        mock_client.start.assert_called_once_with(
            identifier='aws.codeinterpreter.v1',
            name='my-session',
            session_timeout_seconds=3600,
        )
        mock_create.assert_called_once_with('eu-west-1')
        mock_register.assert_called_once_with('named-session', mock_client)

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_with_custom_identifier(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test starting a session with a custom identifier."""
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'custom-session'
        mock_create.return_value = mock_client

        result = await session.start_code_interpreter_session(
            mock_ctx,
            code_interpreter_identifier='custom.v2',
        )

        assert result.session_id == 'custom-session'
        assert result.code_interpreter_identifier == 'custom.v2'
        mock_client.start.assert_called_once_with(identifier='custom.v2')
        mock_register.assert_called_once_with('custom-session', mock_client)

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_raises_on_sdk_failure(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test starting a session raises on SDK error."""
        mock_client = MagicMock()
        mock_client.start.side_effect = Exception('Access denied')
        mock_create.return_value = mock_client

        with pytest.raises(Exception, match='Access denied'):
            await session.start_code_interpreter_session(mock_ctx)

        mock_ctx.error.assert_called_once()
        mock_register.assert_not_called()

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_empty_session_id_raises(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test that empty session ID from SDK raises ValueError."""
        mock_client = MagicMock()
        mock_client.session_id = None
        mock_client.start.return_value = None
        mock_create.return_value = mock_client

        with pytest.raises(ValueError, match='Failed to obtain session ID'):
            await session.start_code_interpreter_session(mock_ctx)

        mock_register.assert_not_called()

    @patch(f'{MODULE_PATH}.register_session_client')
    @patch(f'{MODULE_PATH}.create_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_start_session_zero_timeout_is_passed(
        self, mock_identifier, mock_create, mock_register, mock_ctx
    ):
        """Test that session_timeout_seconds=0 is passed (not dropped by truthiness)."""
        mock_client = MagicMock()
        mock_client.session_id = 'fallback-id'
        mock_client.start.return_value = 'session-with-zero-timeout'
        mock_create.return_value = mock_client

        await session.start_code_interpreter_session(
            mock_ctx,
            session_timeout_seconds=0,
        )

        mock_client.start.assert_called_once_with(
            identifier='aws.codeinterpreter.v1',
            session_timeout_seconds=0,
        )


class TestStopCodeInterpreterSession:
    """Test cases for stop_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.remove_session_client')
    @patch(f'{MODULE_PATH}.get_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_happy_path(
        self, mock_identifier, mock_get_session, mock_remove, mock_ctx
    ):
        """Test stopping a session returns TERMINATED and removes client."""
        mock_client = MagicMock()
        mock_client.stop.return_value = True
        mock_get_session.return_value = mock_client

        result = await session.stop_code_interpreter_session(
            mock_ctx, session_id='session-to-stop'
        )

        assert result.session_id == 'session-to-stop'
        assert result.status == 'TERMINATED'
        mock_client.stop.assert_called_once()
        mock_remove.assert_called_once_with('session-to-stop')

    @patch(f'{MODULE_PATH}.remove_session_client')
    @patch(f'{MODULE_PATH}.get_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_stop_returns_false(
        self, mock_identifier, mock_get_session, mock_remove, mock_ctx
    ):
        """Test stop returning False still reports TERMINATED and removes client."""
        mock_client = MagicMock()
        mock_client.stop.return_value = False
        mock_get_session.return_value = mock_client

        result = await session.stop_code_interpreter_session(mock_ctx, session_id='stuck-session')

        assert result.session_id == 'stuck-session'
        assert result.status == 'TERMINATED'
        mock_client.stop.assert_called_once()
        mock_remove.assert_called_once_with('stuck-session')

    @patch(f'{MODULE_PATH}.remove_session_client')
    @patch(f'{MODULE_PATH}.get_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_session_raises_on_sdk_failure(
        self, mock_identifier, mock_get_session, mock_remove, mock_ctx
    ):
        """Test stopping a session raises on SDK error but still removes client."""
        mock_client = MagicMock()
        mock_client.stop.side_effect = Exception('Session not found')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Session not found'):
            await session.stop_code_interpreter_session(mock_ctx, session_id='bad-session')

        mock_ctx.error.assert_called_once()
        # Client is always removed from registry even if stop() fails
        mock_remove.assert_called_once_with('bad-session')

    @patch(f'{MODULE_PATH}.remove_session_client')
    @patch(f'{MODULE_PATH}.get_session_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_stop_unregistered_session_raises(
        self, mock_identifier, mock_get_session, mock_remove, mock_ctx
    ):
        """Test stopping a session that was never started raises KeyError."""
        mock_get_session.side_effect = KeyError('No active session client for session unknown')

        with pytest.raises(KeyError, match='No active session client'):
            await session.stop_code_interpreter_session(mock_ctx, session_id='unknown')

        mock_ctx.error.assert_called_once()
        mock_remove.assert_not_called()


class TestGetCodeInterpreterSession:
    """Test cases for get_code_interpreter_session."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_happy_path(self, mock_identifier, mock_get_client, mock_ctx):
        """Test getting session status returns correct response."""
        mock_client = MagicMock()
        mock_client.get_session.return_value = {'status': 'READY'}
        mock_get_client.return_value = mock_client

        result = await session.get_code_interpreter_session(mock_ctx, session_id='session-123')

        assert result.session_id == 'session-123'
        assert result.status == 'READY'
        mock_client.get_session.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            session_id='session-123',
        )

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_handles_non_dict_response(
        self, mock_identifier, mock_get_client, mock_ctx
    ):
        """Test handles unexpected non-dict response gracefully."""
        mock_client = MagicMock()
        mock_client.get_session.return_value = 'unexpected'
        mock_get_client.return_value = mock_client

        result = await session.get_code_interpreter_session(mock_ctx, session_id='session-123')

        assert result.status == 'UNKNOWN'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_get_session_raises_on_sdk_failure(
        self, mock_identifier, mock_get_client, mock_ctx
    ):
        """Test getting a nonexistent session raises."""
        mock_client = MagicMock()
        mock_client.get_session.side_effect = Exception('Session not found: INVALID')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match='Session not found'):
            await session.get_code_interpreter_session(mock_ctx, session_id='INVALID')

        mock_ctx.error.assert_called_once()


class TestListCodeInterpreterSessions:
    """Test cases for list_code_interpreter_sessions."""

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_happy_path(
        self, mock_identifier, mock_get_client, sample_list_sessions_response, mock_ctx
    ):
        """Test listing sessions returns formatted response."""
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = sample_list_sessions_response
        mock_get_client.return_value = mock_client

        result = await session.list_code_interpreter_sessions(mock_ctx)

        assert len(result.sessions) == 2
        assert result.sessions[0].session_id == 'session-1'
        assert result.sessions[0].status == 'READY'
        assert result.sessions[1].session_id == 'session-2'
        assert result.sessions[1].status == 'TERMINATED'
        assert result.message == 'Found 2 session(s).'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_with_filters(self, mock_identifier, mock_get_client, mock_ctx):
        """Test listing sessions passes filter parameters."""
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {'items': [], 'nextToken': None}
        mock_get_client.return_value = mock_client

        result = await session.list_code_interpreter_sessions(
            mock_ctx,
            status='READY',
            max_results=10,
            next_token='page-2',
        )

        mock_client.list_sessions.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            status='READY',
            max_results=10,
            next_token='page-2',
        )
        assert result.message == 'Found 0 session(s).'

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_empty(self, mock_identifier, mock_get_client, mock_ctx):
        """Test listing sessions returns empty list gracefully."""
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {'items': []}
        mock_get_client.return_value = mock_client

        result = await session.list_code_interpreter_sessions(mock_ctx)

        assert result.sessions == []
        assert result.next_token is None

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_raises_on_sdk_failure(
        self, mock_identifier, mock_get_client, mock_ctx
    ):
        """Test listing sessions raises on SDK error."""
        mock_client = MagicMock()
        mock_client.list_sessions.side_effect = Exception('Invalid token')
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match='Invalid token'):
            await session.list_code_interpreter_sessions(mock_ctx, next_token='bad-token')

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_client')
    @patch(f'{MODULE_PATH}.get_default_identifier', return_value='aws.codeinterpreter.v1')
    async def test_list_sessions_zero_max_results_is_passed(
        self, mock_identifier, mock_get_client, mock_ctx
    ):
        """Test that max_results=0 is passed (not dropped by truthiness)."""
        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {'items': []}
        mock_get_client.return_value = mock_client

        await session.list_code_interpreter_sessions(mock_ctx, max_results=0)

        mock_client.list_sessions.assert_called_once_with(
            interpreter_id='aws.codeinterpreter.v1',
            max_results=0,
        )
