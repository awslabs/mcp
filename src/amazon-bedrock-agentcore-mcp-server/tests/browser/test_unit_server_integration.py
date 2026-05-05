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

"""Unit tests for server.py browser integration and tools/browser/__init__.py."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


SERVER_PATCH = 'awslabs.amazon_bedrock_agentcore_mcp_server.server'
BROWSER_PATCH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser'


# ===========================================================================
# _is_service_enabled() tests
# ===========================================================================


class TestIsServiceEnabled:
    """Tests for _is_service_enabled() env var parsing."""

    def test_default_no_env_vars(self, monkeypatch):
        """Default behavior with no env vars returns True."""
        monkeypatch.delenv('AGENTCORE_DISABLE_TOOLS', raising=False)
        monkeypatch.delenv('AGENTCORE_ENABLE_TOOLS', raising=False)
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is True
        assert _is_service_enabled('runtime') is True

    def test_disable_browser(self, monkeypatch):
        """AGENTCORE_DISABLE_TOOLS=browser disables browser, not runtime."""
        monkeypatch.setenv('AGENTCORE_DISABLE_TOOLS', 'browser')
        monkeypatch.delenv('AGENTCORE_ENABLE_TOOLS', raising=False)
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is False
        assert _is_service_enabled('runtime') is True

    def test_enable_browser_only(self, monkeypatch):
        """AGENTCORE_ENABLE_TOOLS=browser enables only browser."""
        monkeypatch.delenv('AGENTCORE_DISABLE_TOOLS', raising=False)
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', 'browser')
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is True
        assert _is_service_enabled('runtime') is False

    def test_both_set_enable_wins(self, monkeypatch):
        """When both ENABLE and DISABLE are set, ENABLE wins."""
        monkeypatch.setenv('AGENTCORE_DISABLE_TOOLS', 'browser')
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', 'runtime')
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('runtime') is True
        assert _is_service_enabled('browser') is False

    def test_empty_after_split(self, monkeypatch):
        """Empty ENABLE_TOOLS (e.g. ',,,') enables all."""
        monkeypatch.delenv('AGENTCORE_DISABLE_TOOLS', raising=False)
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', ',,,')
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is True
        assert _is_service_enabled('runtime') is True

    def test_case_insensitive(self, monkeypatch):
        """Tool names are case-insensitive."""
        monkeypatch.setenv('AGENTCORE_DISABLE_TOOLS', 'Browser')
        monkeypatch.delenv('AGENTCORE_ENABLE_TOOLS', raising=False)
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is False

    def test_whitespace_handling(self, monkeypatch):
        """Whitespace around tool names is stripped."""
        monkeypatch.setenv('AGENTCORE_DISABLE_TOOLS', ' browser , runtime ')
        monkeypatch.delenv('AGENTCORE_ENABLE_TOOLS', raising=False)
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import _is_service_enabled

        assert _is_service_enabled('browser') is False
        assert _is_service_enabled('runtime') is False


# ===========================================================================
# cleanup_stale_sessions() tests
# ===========================================================================


class TestCleanupStaleSessions:
    """Tests for cleanup_stale_sessions() from tools/browser/__init__.py."""

    async def test_prunes_stale_session(self):
        """Stale session (browser disconnected) triggers disconnect + cleanup."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            cleanup_stale_sessions,
        )

        cm = MagicMock()
        sm = MagicMock()
        cm.get_session_ids.return_value = ['sess-1']
        browser = MagicMock()
        browser.is_connected.return_value = False
        cm.get_browser.return_value = browser
        cm.disconnect = AsyncMock()

        with patch(f'{BROWSER_PATCH}.asyncio') as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            with pytest.raises(asyncio.CancelledError):
                await cleanup_stale_sessions(cm, sm)

        cm.disconnect.assert_awaited_once_with('sess-1')
        sm.cleanup_session.assert_called_once_with('sess-1')

    async def test_skips_connected_session(self):
        """Connected session is not pruned."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            cleanup_stale_sessions,
        )

        cm = MagicMock()
        sm = MagicMock()
        cm.get_session_ids.return_value = ['sess-1']
        browser = MagicMock()
        browser.is_connected.return_value = True
        cm.get_browser.return_value = browser
        cm.disconnect = AsyncMock()

        with patch(f'{BROWSER_PATCH}.asyncio') as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            with pytest.raises(asyncio.CancelledError):
                await cleanup_stale_sessions(cm, sm)

        cm.disconnect.assert_not_awaited()
        sm.cleanup_session.assert_not_called()

    async def test_handles_value_error(self):
        """ValueError from get_browser (session vanished) is silently handled."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            cleanup_stale_sessions,
        )

        cm = MagicMock()
        sm = MagicMock()
        cm.get_session_ids.return_value = ['sess-1']
        cm.get_browser.side_effect = ValueError('No connection')
        cm.disconnect = AsyncMock()

        with patch(f'{BROWSER_PATCH}.asyncio') as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            with pytest.raises(asyncio.CancelledError):
                await cleanup_stale_sessions(cm, sm)

        cm.disconnect.assert_not_awaited()

    async def test_handles_generic_exception(self):
        """Generic exception from get_browser is caught and loop continues."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            cleanup_stale_sessions,
        )

        cm = MagicMock()
        sm = MagicMock()
        cm.get_session_ids.return_value = ['sess-1']
        cm.get_browser.side_effect = RuntimeError('Unexpected error')
        cm.disconnect = AsyncMock()

        with patch(f'{BROWSER_PATCH}.asyncio') as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            with pytest.raises(asyncio.CancelledError):
                await cleanup_stale_sessions(cm, sm)

        cm.disconnect.assert_not_awaited()

    async def test_handles_get_session_ids_error(self):
        """Exception from get_session_ids is caught by outer handler."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            cleanup_stale_sessions,
        )

        cm = MagicMock()
        sm = MagicMock()
        cm.get_session_ids.side_effect = RuntimeError('Manager broken')

        with patch(f'{BROWSER_PATCH}.asyncio') as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])
            with pytest.raises(asyncio.CancelledError):
                await cleanup_stale_sessions(cm, sm)


# ===========================================================================
# register_browser_tools() tests
# ===========================================================================


class TestRegisterBrowserTools:
    """Tests for register_browser_tools() from tools/browser/__init__.py."""

    def test_register_succeeds(self):
        """Registration creates managers and returns them."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            register_browser_tools,
        )

        mock_mcp = MagicMock()
        cm, sm = register_browser_tools(mock_mcp)
        assert cm is not None
        assert sm is not None

    def test_registration_error_includes_group_name(self):
        """When a tool group fails to register, the error includes the group name."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
            register_browser_tools,
        )

        mock_mcp = MagicMock()
        with patch(
            f'{BROWSER_PATCH}.BrowserSessionTools',
            side_effect=RuntimeError('Init failed'),
        ):
            with pytest.raises(RuntimeError, match='session'):
                register_browser_tools(mock_mcp)


# ===========================================================================
# server_lifespan() tests
# ===========================================================================


class TestServerLifespan:
    """Tests for server_lifespan() context manager."""

    async def test_lifespan_with_browser_enabled(self):
        """With browser enabled: signal handlers registered, cleanup on exit."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import server_lifespan

        mock_cm = MagicMock()
        mock_cm.cleanup = AsyncMock()
        mock_server = MagicMock()

        with (
            patch(f'{SERVER_PATCH}._browser_cm', mock_cm),
            patch(f'{SERVER_PATCH}._browser_sm', MagicMock()),
        ):
            async with server_lifespan(mock_server):
                pass

            mock_cm.cleanup.assert_awaited_once()

    async def test_lifespan_with_browser_disabled(self):
        """With browser disabled (_browser_cm is None), yields cleanly."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import server_lifespan

        mock_server = MagicMock()

        with patch(f'{SERVER_PATCH}._browser_cm', None):
            async with server_lifespan(mock_server):
                pass

    async def test_lifespan_cleans_up_on_exception(self):
        """Lifespan cleans up even when body raises."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import server_lifespan

        mock_cm = MagicMock()
        mock_cm.cleanup = AsyncMock()
        mock_server = MagicMock()

        with (
            patch(f'{SERVER_PATCH}._browser_cm', mock_cm),
            patch(f'{SERVER_PATCH}._browser_sm', MagicMock()),
        ):
            try:
                async with server_lifespan(mock_server):
                    raise RuntimeError('test error')
            except RuntimeError:
                pass

            mock_cm.cleanup.assert_awaited_once()


# ===========================================================================
# Idempotent cleanup test
# ===========================================================================


class TestIdempotentCleanup:
    """Test that BrowserConnectionManager.cleanup() is idempotent."""

    async def test_cleanup_called_twice_is_noop_second_time(self):
        """Second cleanup() call is a no-op."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.connection_manager import (
            BrowserConnectionManager,
        )

        cm = BrowserConnectionManager()
        assert cm._cleaned_up is False

        with patch.object(cm, 'disconnect', new=AsyncMock()):
            await cm.cleanup()
            assert cm._cleaned_up is True

            # Second call should be a no-op
            cm.disconnect.reset_mock()  # type: ignore[union-attr]
            await cm.cleanup()
            cm.disconnect.assert_not_awaited()  # type: ignore[union-attr]
