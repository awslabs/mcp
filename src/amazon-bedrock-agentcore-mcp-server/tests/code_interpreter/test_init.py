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

"""Tests for code_interpreter __init__ (cleanup and registration)."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import (
    cleanup_code_interpreter,
    register_code_interpreter_tools,
)
from unittest.mock import AsyncMock, MagicMock, patch


MODULE_PATH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter'


class TestCleanupCodeInterpreter:
    """Test cases for cleanup_code_interpreter."""

    @patch(f'{MODULE_PATH}.clear_clients')
    @patch(f'{MODULE_PATH}.stop_all_sessions', new_callable=AsyncMock)
    async def test_cleanup_default_clears_clients(self, mock_stop_all, mock_clear):
        """Default (AUTO_STOP_SESSIONS unset) just clears client caches."""
        with patch.dict('os.environ', {}, clear=True):
            await cleanup_code_interpreter()

        mock_clear.assert_called_once()
        mock_stop_all.assert_not_awaited()

    @patch(f'{MODULE_PATH}.clear_clients')
    @patch(f'{MODULE_PATH}.stop_all_sessions', new_callable=AsyncMock)
    async def test_cleanup_auto_stop_true_stops_sessions(self, mock_stop_all, mock_clear):
        """AUTO_STOP_SESSIONS=true stops all sessions before clearing."""
        with patch.dict('os.environ', {'AUTO_STOP_SESSIONS': 'true'}):
            await cleanup_code_interpreter()

        mock_stop_all.assert_awaited_once()
        mock_clear.assert_not_called()

    @patch(f'{MODULE_PATH}.clear_clients')
    @patch(f'{MODULE_PATH}.stop_all_sessions', new_callable=AsyncMock)
    async def test_cleanup_auto_stop_false_clears_clients(self, mock_stop_all, mock_clear):
        """AUTO_STOP_SESSIONS=false just clears client caches."""
        with patch.dict('os.environ', {'AUTO_STOP_SESSIONS': 'false'}):
            await cleanup_code_interpreter()

        mock_clear.assert_called_once()
        mock_stop_all.assert_not_awaited()

    @patch(f'{MODULE_PATH}.clear_clients')
    @patch(f'{MODULE_PATH}.stop_all_sessions', new_callable=AsyncMock)
    async def test_cleanup_auto_stop_case_insensitive(self, mock_stop_all, mock_clear):
        """AUTO_STOP_SESSIONS=True (mixed case) triggers stop."""
        with patch.dict('os.environ', {'AUTO_STOP_SESSIONS': 'True'}):
            await cleanup_code_interpreter()

        mock_stop_all.assert_awaited_once()
        mock_clear.assert_not_called()


class TestRegisterCodeInterpreterTools:
    """Test cases for register_code_interpreter_tools."""

    def test_registers_all_nine_tools(self):
        """Verify all 9 code interpreter tools are registered."""
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock(side_effect=lambda fn: fn)
        mock_mcp.tool.return_value = mock_tool_decorator

        register_code_interpreter_tools(mock_mcp)

        assert mock_mcp.tool.call_count == 9
