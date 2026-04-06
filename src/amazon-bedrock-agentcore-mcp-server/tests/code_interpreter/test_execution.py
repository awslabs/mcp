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

"""Tests for code execution tools."""

import pytest
from .conftest import make_stream_response
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import execution
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.execution import (
    _parse_invoke_response,
)
from unittest.mock import MagicMock, patch


MODULE_PATH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.execution'


class TestExecuteCode:
    """Test cases for execute_code."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_happy_path(
        self, mock_get_session, sample_execution_result, mock_ctx
    ):
        """Test executing code returns correct response."""
        mock_client = MagicMock()
        mock_client.execute_code.return_value = sample_execution_result
        mock_get_session.return_value = mock_client

        result = await execution.execute_code(
            mock_ctx,
            session_id='session-123',
            code='print("Hello, World!")',
        )

        assert result.stdout == 'Hello, World!\n'
        assert result.stderr == ''
        assert result.exit_code == 0
        assert result.is_error is False
        mock_get_session.assert_called_once_with('session-123')
        mock_client.execute_code.assert_called_once_with(code='print("Hello, World!")')

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_with_language(self, mock_get_session, mock_ctx):
        """Test executing code with a specific language."""
        mock_client = MagicMock()
        mock_client.execute_code.return_value = make_stream_response()
        mock_get_session.return_value = mock_client

        await execution.execute_code(
            mock_ctx,
            session_id='session-123',
            code='console.log("hi")',
            language='javascript',
        )

        mock_client.execute_code.assert_called_once_with(
            code='console.log("hi")',
            language='javascript',
        )

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_with_clear_context(self, mock_get_session, mock_ctx):
        """Test executing code with clear_context flag."""
        mock_client = MagicMock()
        mock_client.execute_code.return_value = make_stream_response()
        mock_get_session.return_value = mock_client

        await execution.execute_code(
            mock_ctx,
            session_id='session-123',
            code='x = 1',
            clear_context=True,
        )

        mock_client.execute_code.assert_called_once_with(code='x = 1', clear_context=True)

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_failure(self, mock_get_session, sample_execution_error, mock_ctx):
        """Test executing code that fails returns is_error=True."""
        mock_client = MagicMock()
        mock_client.execute_code.return_value = sample_execution_error
        mock_get_session.return_value = mock_client

        result = await execution.execute_code(
            mock_ctx,
            session_id='session-123',
            code='print(x)',
        )

        assert result.is_error is True
        assert result.exit_code == 1
        assert 'NameError' in result.stderr

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_sdk_exception(self, mock_get_session, mock_ctx):
        """Test SDK exception raises as infrastructure error."""
        mock_client = MagicMock()
        mock_client.execute_code.side_effect = Exception('Session expired')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Session expired'):
            await execution.execute_code(
                mock_ctx,
                session_id='session-123',
                code='print("hi")',
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_string_result(self, mock_get_session, mock_ctx):
        """Test handles string result from SDK."""
        mock_client = MagicMock()
        mock_client.execute_code.return_value = '42'
        mock_get_session.return_value = mock_client

        result = await execution.execute_code(
            mock_ctx,
            session_id='session-123',
            code='1 + 41',
        )

        assert result.content == '42'
        assert result.is_error is False

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_code_unregistered_session_raises(self, mock_get_session, mock_ctx):
        """Test executing code on unregistered session raises KeyError."""
        mock_get_session.side_effect = KeyError('No active session client for session unknown')

        with pytest.raises(KeyError, match='No active session client'):
            await execution.execute_code(
                mock_ctx,
                session_id='unknown',
                code='print("hi")',
            )

        mock_ctx.error.assert_called_once()


class TestExecuteCommand:
    """Test cases for execute_command."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_command_happy_path(self, mock_get_session, mock_ctx):
        """Test executing a shell command returns correct response."""
        mock_client = MagicMock()
        mock_client.execute_command.return_value = make_stream_response(
            stdout='file1.txt\nfile2.txt\n',
        )
        mock_get_session.return_value = mock_client

        result = await execution.execute_command(
            mock_ctx,
            session_id='session-123',
            command='ls /tmp',
        )

        assert result.stdout == 'file1.txt\nfile2.txt\n'
        assert result.is_error is False
        assert result.exit_code == 0
        mock_get_session.assert_called_once_with('session-123')
        mock_client.execute_command.assert_called_once_with(command='ls /tmp')

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_command_failure(self, mock_get_session, mock_ctx):
        """Test command failure returns is_error=True."""
        mock_client = MagicMock()
        mock_client.execute_command.return_value = make_stream_response(
            stderr='command not found: foobar',
            exit_code=127,
            is_error=True,
        )
        mock_get_session.return_value = mock_client

        result = await execution.execute_command(
            mock_ctx,
            session_id='session-123',
            command='foobar',
        )

        assert result.is_error is True
        assert result.exit_code == 127

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_execute_command_sdk_exception(self, mock_get_session, mock_ctx):
        """Test SDK exception raises as infrastructure error."""
        mock_client = MagicMock()
        mock_client.execute_command.side_effect = Exception('Timeout')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Timeout'):
            await execution.execute_command(
                mock_ctx,
                session_id='session-123',
                command='sleep 999',
            )

        mock_ctx.error.assert_called_once()


class TestInstallPackages:
    """Test cases for install_packages."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_install_packages_happy_path(self, mock_get_session, mock_ctx):
        """Test installing packages returns correct response."""
        mock_client = MagicMock()
        mock_client.install_packages.return_value = make_stream_response(
            stdout='Successfully installed numpy-1.26.0',
        )
        mock_get_session.return_value = mock_client

        result = await execution.install_packages(
            mock_ctx,
            session_id='session-123',
            packages=['numpy'],
        )

        assert result.is_error is False
        assert 'numpy' in result.stdout
        assert result.message == 'Installed 1 package(s) successfully.'
        mock_get_session.assert_called_once_with('session-123')
        mock_client.install_packages.assert_called_once_with(packages=['numpy'])

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_install_packages_with_upgrade(self, mock_get_session, mock_ctx):
        """Test installing packages with upgrade flag."""
        mock_client = MagicMock()
        mock_client.install_packages.return_value = make_stream_response(
            stdout='Successfully installed pandas-2.1.0',
        )
        mock_get_session.return_value = mock_client

        await execution.install_packages(
            mock_ctx,
            session_id='session-123',
            packages=['pandas'],
            upgrade=True,
        )

        mock_client.install_packages.assert_called_once_with(
            packages=['pandas'],
            upgrade=True,
        )

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_install_packages_multiple(self, mock_get_session, mock_ctx):
        """Test installing multiple packages."""
        mock_client = MagicMock()
        mock_client.install_packages.return_value = make_stream_response(
            stdout='Installed 3 packages',
        )
        mock_get_session.return_value = mock_client

        result = await execution.install_packages(
            mock_ctx,
            session_id='session-123',
            packages=['numpy', 'pandas', 'matplotlib'],
        )

        assert result.message == 'Installed 3 package(s) successfully.'

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_install_packages_failure(self, mock_get_session, mock_ctx):
        """Test package installation failure (execution-level)."""
        mock_client = MagicMock()
        mock_client.install_packages.return_value = make_stream_response(
            stderr='No matching distribution found for nonexistent-pkg',
            exit_code=1,
            is_error=True,
        )
        mock_get_session.return_value = mock_client

        result = await execution.install_packages(
            mock_ctx,
            session_id='session-123',
            packages=['nonexistent-pkg'],
        )

        assert result.is_error is True
        assert result.exit_code == 1


class TestParseInvokeResponse:
    """Test cases for _parse_invoke_response stream parser."""

    def test_stream_response_extracts_structured_content(self):
        """Test parsing a standard EventStream response."""
        raw = make_stream_response(stdout='hello\n', stderr='', exit_code=0)
        parsed = _parse_invoke_response(raw)
        assert parsed['stdout'] == 'hello\n'
        assert parsed['stderr'] == ''
        assert parsed['exitCode'] == 0
        assert parsed['isError'] is False

    def test_stream_response_with_error(self):
        """Test parsing an error EventStream response."""
        raw = make_stream_response(
            stderr='NameError: x',
            exit_code=1,
            is_error=True,
        )
        parsed = _parse_invoke_response(raw)
        assert parsed['stderr'] == 'NameError: x'
        assert parsed['exitCode'] == 1
        assert parsed['isError'] is True

    def test_stream_response_with_text_content_blocks(self):
        """Test that text content blocks are extracted."""
        raw = make_stream_response(stdout='out\n', content_text='result: 42')
        parsed = _parse_invoke_response(raw)
        assert parsed['stdout'] == 'out\n'
        assert parsed['content'] == 'result: 42'

    def test_stream_response_nonzero_exit_sets_is_error(self):
        """Test that nonzero exit code forces isError=True even without explicit flag."""
        raw = {
            'stream': [
                {
                    'result': {
                        'content': [],
                        'structuredContent': {'stdout': '', 'stderr': 'err', 'exitCode': 2},
                        'isError': False,
                    },
                },
            ],
        }
        parsed = _parse_invoke_response(raw)
        assert parsed['isError'] is True
        assert parsed['exitCode'] == 2

    def test_stream_response_skips_non_result_events(self):
        """Test that non-result events in the stream are ignored."""
        raw = {
            'stream': [
                {'someOtherEvent': {}},
                {
                    'result': {
                        'content': [],
                        'structuredContent': {'stdout': 'ok\n', 'stderr': '', 'exitCode': 0},
                        'isError': False,
                    },
                },
            ],
        }
        parsed = _parse_invoke_response(raw)
        assert parsed['stdout'] == 'ok\n'

    def test_flat_dict_fallback(self):
        """Test backward-compat: flat dict without 'stream' key."""
        raw = {'stdout': 'hello\n', 'stderr': '', 'exitCode': 0}
        parsed = _parse_invoke_response(raw)
        assert parsed['stdout'] == 'hello\n'
        assert parsed['exitCode'] == 0
        assert parsed['isError'] is False

    def test_string_fallback(self):
        """Test backward-compat: plain string result."""
        parsed = _parse_invoke_response('42')
        assert parsed['content'] == '42'
        assert parsed['isError'] is False
