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

"""Unit tests for server.py — lifespan, tool registration, and main entry point."""

import asyncio
import importlib
import pytest
import signal
from unittest.mock import AsyncMock, MagicMock, patch


PATCH_BASE = 'awslabs.amazon_agentcore_browser_mcp_server.server'


class TestServerLifespan:
    """Tests for server_lifespan context manager."""

    async def test_lifespan_calls_cleanup_on_exit(self):
        """Lifespan cleans up connection manager in finally block."""
        with patch(f'{PATCH_BASE}.connection_manager') as mock_cm:
            mock_cm.cleanup = AsyncMock()
            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            async with server_lifespan(mock_server):
                pass

            mock_cm.cleanup.assert_awaited_once()

    async def test_lifespan_registers_signal_handlers(self):
        """Lifespan registers SIGTERM and SIGINT handlers."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_cm.cleanup = AsyncMock()
            mock_loop = MagicMock()
            mock_asyncio.get_running_loop.return_value = mock_loop

            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            async with server_lifespan(mock_server):
                # Verify signal handlers were registered for both SIGTERM and SIGINT
                assert mock_loop.add_signal_handler.call_count == 2
                registered_signals = [
                    call.args[0] for call in mock_loop.add_signal_handler.call_args_list
                ]
                assert signal.SIGTERM in registered_signals
                assert signal.SIGINT in registered_signals

    async def test_lifespan_cleans_up_on_exception(self):
        """Lifespan cleans up even when an exception occurs."""
        with patch(f'{PATCH_BASE}.connection_manager') as mock_cm:
            mock_cm.cleanup = AsyncMock()
            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            try:
                async with server_lifespan(mock_server):
                    raise RuntimeError('test error')
            except RuntimeError:
                pass

            mock_cm.cleanup.assert_awaited_once()


class TestToolRegistration:
    """Tests for tool group registration at module level."""

    def test_mcp_instance_created(self):
        """FastMCP instance is created with correct name."""
        from awslabs.amazon_agentcore_browser_mcp_server.server import mcp

        assert mcp.name == 'awslabs.amazon-agentcore-browser-mcp-server'

    def test_mcp_has_lifespan(self):
        """FastMCP instance has lifespan set."""
        from awslabs.amazon_agentcore_browser_mcp_server.server import mcp, server_lifespan

        assert mcp.settings.lifespan is server_lifespan


class TestMain:
    """Tests for the main entry point."""

    def test_main_calls_mcp_run(self):
        """main() invokes mcp.run()."""
        with patch(f'{PATCH_BASE}.mcp') as mock_mcp:
            from awslabs.amazon_agentcore_browser_mcp_server.server import main

            main()

            mock_mcp.run.assert_called_once()


class TestCleanupStaleSessions:
    """Tests for _cleanup_stale_sessions background task."""

    async def test_cleanup_prunes_stale_session(self):
        """Stale session (browser disconnected) triggers disconnect + cleanup."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.snapshot_manager') as mock_sm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            mock_cm.get_session_ids.return_value = ['sess-1']
            browser = MagicMock()
            browser.is_connected.return_value = False
            mock_cm.get_browser.return_value = browser
            mock_cm.disconnect = AsyncMock()

            from awslabs.amazon_agentcore_browser_mcp_server.server import _cleanup_stale_sessions

            with pytest.raises(asyncio.CancelledError):
                await _cleanup_stale_sessions()

            mock_cm.disconnect.assert_awaited_once_with('sess-1')
            mock_sm.cleanup_session.assert_called_once_with('sess-1')

    async def test_cleanup_skips_connected_session(self):
        """Connected session is not pruned."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.snapshot_manager') as mock_sm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            mock_cm.get_session_ids.return_value = ['sess-1']
            browser = MagicMock()
            browser.is_connected.return_value = True
            mock_cm.get_browser.return_value = browser
            mock_cm.disconnect = AsyncMock()

            from awslabs.amazon_agentcore_browser_mcp_server.server import _cleanup_stale_sessions

            with pytest.raises(asyncio.CancelledError):
                await _cleanup_stale_sessions()

            mock_cm.disconnect.assert_not_awaited()
            mock_sm.cleanup_session.assert_not_called()

    async def test_cleanup_handles_value_error(self):
        """ValueError from get_browser (session vanished) is silently handled."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            mock_cm.get_session_ids.return_value = ['sess-1']
            mock_cm.get_browser.side_effect = ValueError('No connection')
            mock_cm.disconnect = AsyncMock()

            from awslabs.amazon_agentcore_browser_mcp_server.server import _cleanup_stale_sessions

            with pytest.raises(asyncio.CancelledError):
                await _cleanup_stale_sessions()

            mock_cm.disconnect.assert_not_awaited()

    async def test_cleanup_handles_generic_exception(self):
        """Generic exception from get_browser is caught and loop continues."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            mock_cm.get_session_ids.return_value = ['sess-1']
            mock_cm.get_browser.side_effect = RuntimeError('Unexpected error')
            mock_cm.disconnect = AsyncMock()

            from awslabs.amazon_agentcore_browser_mcp_server.server import _cleanup_stale_sessions

            with pytest.raises(asyncio.CancelledError):
                await _cleanup_stale_sessions()

            mock_cm.disconnect.assert_not_awaited()

    async def test_cleanup_handles_get_session_ids_error(self):
        """Exception from get_session_ids is caught by outer handler."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            mock_cm.get_session_ids.side_effect = RuntimeError('Manager broken')

            from awslabs.amazon_agentcore_browser_mcp_server.server import _cleanup_stale_sessions

            with pytest.raises(asyncio.CancelledError):
                await _cleanup_stale_sessions()


class TestToolRegistrationError:
    """Tests for tool registration error handling."""

    def test_tool_registration_error_propagates(self):
        """Tool registration error is logged and re-raised."""
        with patch(
            'awslabs.amazon_agentcore_browser_mcp_server.tools.session.BrowserSessionTools.__init__',
            side_effect=RuntimeError('Init failed'),
        ):
            import awslabs.amazon_agentcore_browser_mcp_server.server as srv_mod

            with pytest.raises(RuntimeError, match='Init failed'):
                importlib.reload(srv_mod)
