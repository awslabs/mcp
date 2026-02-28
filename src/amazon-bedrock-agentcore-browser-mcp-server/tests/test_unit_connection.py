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

"""Unit tests for BrowserConnectionManager."""

import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_WS_URL = 'wss://bedrock-agentcore.us-east-1.amazonaws.com/browser-streams/aws.browser.v1/sessions/sess-1/automation'
MOCK_HEADERS = {'Authorization': 'AWS4-HMAC-SHA256 ...', 'X-Amz-Date': '20250101T000000Z'}

# Patch paths
PATCH_PW = 'awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager.async_playwright'
PATCH_CLIENT = 'awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager.get_browser_client'


@pytest.fixture
def connection_manager():
    """Create a fresh BrowserConnectionManager."""
    return BrowserConnectionManager()


@pytest.fixture
def mock_browser():
    """Create a mock Playwright Browser."""
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    page = MagicMock()
    context.pages = [page]
    browser.contexts = [context]
    return browser


@pytest.fixture
def mock_playwright():
    """Create a mock Playwright instance."""
    pw = MagicMock()
    pw.chromium = MagicMock()
    pw.chromium.connect_over_cdp = AsyncMock()
    pw.stop = AsyncMock()
    return pw


@pytest.fixture
def mock_sdk_client():
    """Create a mock BrowserClient from the SDK."""
    client = MagicMock()
    client.generate_ws_headers.return_value = (MOCK_WS_URL, MOCK_HEADERS)
    return client


class TestConnect:
    """Tests for connecting to browser sessions."""

    @patch(PATCH_CLIENT)
    @patch(PATCH_PW)
    async def test_connect_starts_playwright(
        self,
        mock_async_pw,
        mock_get_client,
        connection_manager,
        mock_playwright,
        mock_browser,
        mock_sdk_client,
    ):
        """First connect starts Playwright, signs request via SDK, and connects via CDP."""
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_get_client.return_value = mock_sdk_client

        browser = await connection_manager.connect('sess-1', 'aws.browser.v1')

        mock_get_client.assert_called_once_with('us-east-1')
        assert mock_sdk_client.identifier == 'aws.browser.v1'
        assert mock_sdk_client.session_id == 'sess-1'
        mock_sdk_client.generate_ws_headers.assert_called_once()
        mock_playwright.chromium.connect_over_cdp.assert_awaited_once_with(
            MOCK_WS_URL, headers=MOCK_HEADERS
        )
        assert browser is mock_browser
        assert connection_manager.is_connected('sess-1')

    @patch(PATCH_CLIENT)
    @patch(PATCH_PW)
    async def test_connect_passes_region(
        self,
        mock_async_pw,
        mock_get_client,
        connection_manager,
        mock_playwright,
        mock_browser,
        mock_sdk_client,
    ):
        """Connect passes region to get_browser_client."""
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_get_client.return_value = mock_sdk_client

        await connection_manager.connect('sess-1', 'aws.browser.v1', region='eu-west-1')

        mock_get_client.assert_called_once_with('eu-west-1')

    @patch(PATCH_CLIENT)
    @patch(PATCH_PW)
    async def test_connect_reuses_playwright(
        self,
        mock_async_pw,
        mock_get_client,
        connection_manager,
        mock_playwright,
        mock_browser,
        mock_sdk_client,
    ):
        """Subsequent connects reuse the same Playwright instance."""
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_get_client.return_value = mock_sdk_client

        await connection_manager.connect('sess-1', 'aws.browser.v1')
        await connection_manager.connect('sess-2', 'aws.browser.v1')

        # Playwright should only start once
        mock_async_pw.return_value.start.assert_awaited_once()
        assert mock_playwright.chromium.connect_over_cdp.await_count == 2


class TestGetPage:
    """Tests for getting the active page."""

    async def test_get_page_returns_last_page(self, connection_manager, mock_browser):
        """Returns the last page of the first context when no active page is set."""
        connection_manager._connections['sess-1'] = mock_browser

        page = await connection_manager.get_page('sess-1')

        assert page is mock_browser.contexts[0].pages[-1]

    async def test_get_page_returns_active_page(self, connection_manager, mock_browser):
        """Returns the explicitly set active page when one exists."""
        connection_manager._connections['sess-1'] = mock_browser
        target_page = mock_browser.contexts[0].pages[0]
        connection_manager.set_active_page('sess-1', target_page)

        page = await connection_manager.get_page('sess-1')

        assert page is target_page

    async def test_get_page_falls_back_when_active_page_closed(self, connection_manager):
        """Falls back to last page when the active page has been removed from context."""
        browser = MagicMock()
        page1 = MagicMock()
        page2 = MagicMock()
        closed_page = MagicMock()
        context = MagicMock()
        context.pages = [page1, page2]
        browser.contexts = [context]
        connection_manager._connections['sess-1'] = browser
        connection_manager.set_active_page('sess-1', closed_page)

        page = await connection_manager.get_page('sess-1')

        assert page is page2

    async def test_get_page_no_connection(self, connection_manager):
        """Raises ValueError for unknown session."""
        with pytest.raises(ValueError, match='No connection'):
            await connection_manager.get_page('nonexistent')

    async def test_get_page_no_contexts(self, connection_manager):
        """Raises ValueError when browser has no contexts."""
        browser = MagicMock()
        browser.contexts = []
        connection_manager._connections['sess-1'] = browser

        with pytest.raises(ValueError, match='No page available'):
            await connection_manager.get_page('sess-1')


class TestDisconnect:
    """Tests for disconnecting sessions."""

    async def test_disconnect_closes_browser(self, connection_manager, mock_browser):
        """Disconnect closes the browser and removes from map."""
        connection_manager._connections['sess-1'] = mock_browser

        await connection_manager.disconnect('sess-1')

        mock_browser.close.assert_awaited_once()
        assert not connection_manager.is_connected('sess-1')

    async def test_disconnect_nonexistent_session(self, connection_manager):
        """Disconnect on unknown session is a no-op."""
        await connection_manager.disconnect('nonexistent')  # Should not raise

    async def test_disconnect_handles_close_error(self, connection_manager, mock_browser):
        """Disconnect handles browser.close() errors gracefully."""
        mock_browser.close.side_effect = Exception('Already closed')
        connection_manager._connections['sess-1'] = mock_browser

        await connection_manager.disconnect('sess-1')  # Should not raise
        assert not connection_manager.is_connected('sess-1')

    async def test_disconnect_clears_active_page(self, connection_manager, mock_browser):
        """Disconnect removes the active page tracking for the session."""
        connection_manager._connections['sess-1'] = mock_browser
        connection_manager.set_active_page('sess-1', mock_browser.contexts[0].pages[0])

        await connection_manager.disconnect('sess-1')

        assert 'sess-1' not in connection_manager._active_pages


class TestCleanup:
    """Tests for full cleanup."""

    @patch(PATCH_CLIENT)
    @patch(PATCH_PW)
    async def test_cleanup_disconnects_all(
        self, mock_async_pw, mock_get_client, connection_manager, mock_playwright, mock_sdk_client
    ):
        """Cleanup disconnects all sessions and stops Playwright."""
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_get_client.return_value = mock_sdk_client
        browser1 = MagicMock()
        browser1.close = AsyncMock()
        browser2 = MagicMock()
        browser2.close = AsyncMock()
        mock_playwright.chromium.connect_over_cdp = AsyncMock(side_effect=[browser1, browser2])

        await connection_manager.connect('sess-1', 'aws.browser.v1')
        await connection_manager.connect('sess-2', 'aws.browser.v1')

        await connection_manager.cleanup()

        browser1.close.assert_awaited_once()
        browser2.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()
        assert connection_manager._playwright is None


class TestGenerateWsHeadersError:
    """Tests for credential validation via SDK."""

    @patch(PATCH_CLIENT)
    @patch(PATCH_PW)
    async def test_connect_no_credentials(
        self, mock_async_pw, mock_get_client, connection_manager, mock_playwright
    ):
        """Raises RuntimeError when SDK cannot generate WebSocket headers."""
        mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)
        mock_client = MagicMock()
        mock_client.generate_ws_headers.side_effect = RuntimeError('No AWS credentials found')
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match='No AWS credentials found'):
            await connection_manager.connect('sess-1', 'aws.browser.v1')


class TestDialogHandler:
    """Tests for dialog handler management."""

    async def test_set_dialog_handler(self, connection_manager, mock_browser):
        """Set dialog handler registers a page listener."""
        connection_manager._connections['sess-1'] = mock_browser
        page = mock_browser.contexts[0].pages[0]
        page.on = MagicMock()
        page.remove_listener = MagicMock()

        await connection_manager.set_dialog_handler('sess-1', action='accept')

        page.on.assert_called_once()
        assert page.on.call_args[0][0] == 'dialog'
        assert 'sess-1' in connection_manager._dialog_handlers

    async def test_remove_dialog_handler(self, connection_manager, mock_browser):
        """Remove dialog handler detaches the page listener."""
        connection_manager._connections['sess-1'] = mock_browser
        page = mock_browser.contexts[0].pages[0]
        page.on = MagicMock()
        page.remove_listener = MagicMock()

        await connection_manager.set_dialog_handler('sess-1', action='accept')
        await connection_manager.remove_dialog_handler('sess-1')

        page.remove_listener.assert_called_once()
        assert 'sess-1' not in connection_manager._dialog_handlers

    async def test_disconnect_removes_dialog_handler(self, connection_manager, mock_browser):
        """Disconnect properly removes dialog handler via remove_dialog_handler."""
        connection_manager._connections['sess-1'] = mock_browser
        page = mock_browser.contexts[0].pages[0]
        page.on = MagicMock()
        page.remove_listener = MagicMock()

        await connection_manager.set_dialog_handler('sess-1', action='accept')
        await connection_manager.disconnect('sess-1')

        page.remove_listener.assert_called_once()
        assert 'sess-1' not in connection_manager._dialog_handlers
