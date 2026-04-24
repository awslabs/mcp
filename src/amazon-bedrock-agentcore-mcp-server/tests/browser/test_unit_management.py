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

"""Unit tests for browser management tools (tabs, close, resize)."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.management import ManagementTools
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.snapshot_manager import (
    SnapshotManager,
)
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_connection_manager():
    """Create a mock BrowserConnectionManager with public API."""
    cm = MagicMock(spec=BrowserConnectionManager)
    cm.get_page = AsyncMock()
    cm.get_browser = MagicMock()
    cm.get_context = MagicMock()
    return cm


@pytest.fixture
def mock_snapshot_manager():
    """Create a mock SnapshotManager."""
    sm = MagicMock(spec=SnapshotManager)
    sm.capture = AsyncMock(return_value='- heading "Test" [level=1]')
    return sm


@pytest.fixture
def mock_browser():
    """Create a mock browser with context and pages."""
    browser = MagicMock()
    page1 = MagicMock()
    page1.title = AsyncMock(return_value='Page One')
    page1.url = 'https://example.com'
    page1.close = AsyncMock()
    page1.bring_to_front = AsyncMock()
    page1.set_viewport_size = AsyncMock()

    page2 = MagicMock()
    page2.title = AsyncMock(return_value='Page Two')
    page2.url = 'https://other.com'
    page2.close = AsyncMock()
    page2.bring_to_front = AsyncMock()

    context = MagicMock()
    context.pages = [page1, page2]
    context.new_page = AsyncMock()

    browser.contexts = [context]
    return browser


@pytest.fixture
def management_tools(mock_connection_manager, mock_snapshot_manager):
    """Create ManagementTools with mocked dependencies."""
    return ManagementTools(mock_connection_manager, mock_snapshot_manager)


def _setup_browser(mock_connection_manager, mock_browser):
    """Configure mock connection manager to return the mock browser."""
    mock_connection_manager.get_browser.return_value = mock_browser
    mock_connection_manager.get_context.return_value = mock_browser.contexts[0]


class TestBrowserTabs:
    """Tests for browser_tabs tool."""

    async def test_list_tabs(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """List tabs shows all open tabs."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='list'
        )

        assert 'Open tabs (2)' in result
        assert 'Page One' in result
        assert 'Page Two' in result
        assert '[0]' in result
        assert '[1]' in result

    async def test_new_tab(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """New tab creates a page, sets it as active, and returns snapshot."""
        _setup_browser(mock_connection_manager, mock_browser)
        new_page = MagicMock()
        new_page.title = AsyncMock(return_value='New Tab')
        new_page.url = 'about:blank'
        new_page.goto = AsyncMock()
        mock_browser.contexts[0].new_page.return_value = new_page

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='new'
        )

        mock_browser.contexts[0].new_page.assert_awaited_once()
        mock_connection_manager.set_active_page.assert_called_once_with('sess-1', new_page)
        assert 'Opened new tab' in result
        mock_snapshot_manager.capture.assert_awaited_once_with(new_page, 'sess-1')

    async def test_new_tab_with_url(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """New tab navigates to URL when provided and returns snapshot."""
        _setup_browser(mock_connection_manager, mock_browser)
        new_page = MagicMock()
        new_page.title = AsyncMock(return_value='Example')
        new_page.url = 'https://example.com'
        new_page.goto = AsyncMock()
        mock_browser.contexts[0].new_page.return_value = new_page

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='new', url='https://example.com'
        )

        new_page.goto.assert_awaited_once()
        mock_connection_manager.set_active_page.assert_called_once_with('sess-1', new_page)
        assert 'Example' in result
        mock_snapshot_manager.capture.assert_awaited_once_with(new_page, 'sess-1')

    async def test_select_tab(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """Select tab brings it to front, sets active page, and returns snapshot."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='select', tab_index=1
        )

        mock_browser.contexts[0].pages[1].bring_to_front.assert_awaited_once()
        mock_connection_manager.set_active_page.assert_called_once_with(
            'sess-1', mock_browser.contexts[0].pages[1]
        )
        assert 'Switched to tab [1]' in result
        mock_snapshot_manager.capture.assert_awaited_once()

    async def test_select_tab_out_of_range(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """Select tab with invalid index returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='select', tab_index=5
        )

        assert 'Error' in result
        assert 'out of range' in result

    async def test_close_tab(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """Close tab removes it, updates active page, and returns snapshot."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='close', tab_index=1
        )

        mock_browser.contexts[0].pages[1].close.assert_awaited_once()
        mock_connection_manager.set_active_page.assert_called_once()
        assert 'Closed tab [1]' in result
        mock_snapshot_manager.capture.assert_awaited_once()

    async def test_close_last_tab_error(self, management_tools, mock_ctx, mock_connection_manager):
        """Cannot close the last remaining tab."""
        browser = MagicMock()
        page = MagicMock()
        page.title = AsyncMock(return_value='Only Tab')
        context = MagicMock()
        context.pages = [page]
        browser.contexts = [context]
        mock_connection_manager.get_browser.return_value = browser
        mock_connection_manager.get_context.return_value = context

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='close', tab_index=0
        )

        assert 'Error' in result
        assert 'last tab' in result

    async def test_no_connection(self, management_tools, mock_ctx, mock_connection_manager):
        """Tabs with no connection returns error."""
        mock_connection_manager.get_context.side_effect = ValueError(
            'No connection for session nonexistent. Call start_browser_session first.'
        )

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='nonexistent', action='list'
        )

        assert 'Error' in result
        assert 'No connection' in result

    async def test_unknown_action(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """Unknown tab action returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='invalid'
        )

        assert 'Error' in result
        assert 'Unknown action' in result

    async def test_select_tab_missing_index(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """Select tab without tab_index returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='select', tab_index=None
        )

        assert 'Error' in result
        assert 'Provide tab_index' in result

    async def test_close_tab_missing_index(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """Close tab without tab_index returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='close', tab_index=None
        )

        assert 'Error' in result
        assert 'Provide tab_index' in result

    async def test_close_tab_out_of_range(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """Close tab with out-of-range index returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='close', tab_index=5
        )

        assert 'Error' in result
        assert 'out of range' in result

    async def test_new_tab_error_cleans_up(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """New tab cleans up page when goto raises an exception."""
        _setup_browser(mock_connection_manager, mock_browser)
        new_page = MagicMock()
        new_page.goto = AsyncMock(side_effect=Exception('Navigation failed'))
        new_page.close = AsyncMock()
        mock_browser.contexts[0].new_page.return_value = new_page

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='new', url='https://bad.com'
        )

        assert 'Error' in result
        new_page.close.assert_awaited()

    async def test_tabs_generic_exception(
        self, management_tools, mock_ctx, mock_connection_manager
    ):
        """Generic exception in tabs returns error with snapshot fallback."""
        mock_connection_manager.get_context.side_effect = Exception('CDP error')
        page = MagicMock()
        mock_connection_manager.get_page.return_value = page

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='list'
        )

        assert 'CDP error' in result

    async def test_list_tabs_empty(self, management_tools, mock_ctx, mock_connection_manager):
        """List tabs with no pages returns empty message."""
        browser = MagicMock()
        context = MagicMock()
        context.pages = []
        browser.contexts = [context]
        mock_connection_manager.get_browser.return_value = browser
        mock_connection_manager.get_context.return_value = context

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='list'
        )

        assert 'No tabs open.' in result


class TestBrowserClose:
    """Tests for browser_close tool."""

    async def test_close_page(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """Close page closes the active page, updates tracking, and returns snapshot."""
        page = MagicMock()
        page.title = AsyncMock(return_value='Closing Page')
        page.url = 'https://example.com'
        page.close = AsyncMock()
        mock_connection_manager.get_page.return_value = page
        mock_connection_manager.get_context.return_value = mock_browser.contexts[0]

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        page.close.assert_awaited_once()
        assert 'Closed page: Closing Page' in result
        mock_snapshot_manager.capture.assert_awaited_once()

    async def test_close_page_error(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Close page error returns error_with_snapshot result."""
        mock_connection_manager.get_page.side_effect = Exception('Page gone')

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        assert 'Error closing page' in result
        assert 'Page gone' in result

    async def test_close_last_page_error(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Cannot close the last remaining page."""
        page = MagicMock()
        page.title = AsyncMock(return_value='Only Page')
        page.url = 'https://example.com'
        context = MagicMock()
        context.pages = [page]
        mock_connection_manager.get_page.return_value = page
        mock_connection_manager.get_context.return_value = context

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        assert 'Cannot close the last page' in result
        page.close.assert_not_called()

    async def test_close_page_no_remaining_context(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Close page when get_context raises returns error."""
        page = MagicMock()
        mock_connection_manager.get_page.return_value = page
        mock_connection_manager.get_context.side_effect = ValueError('No remaining context')

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        assert 'Error closing page' in result


class TestBrowserResize:
    """Tests for browser_resize tool."""

    async def test_resize_viewport(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Resize changes viewport dimensions."""
        page = MagicMock()
        page.set_viewport_size = AsyncMock()
        mock_connection_manager.get_page.return_value = page

        result = await management_tools.browser_resize(
            ctx=mock_ctx, session_id='sess-1', width=1920, height=1080
        )

        page.set_viewport_size.assert_awaited_once_with({'width': 1920, 'height': 1080})
        assert '1920x1080' in result
        mock_snapshot_manager.capture.assert_awaited_once()

    async def test_resize_error(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Resize error returns error result."""
        mock_connection_manager.get_page.side_effect = Exception('No page')

        result = await management_tools.browser_resize(
            ctx=mock_ctx, session_id='sess-1', width=1920, height=1080
        )

        assert 'Error resizing viewport' in result
        assert 'No page' in result


class TestBrowserTabsEdgeCases:
    """Additional edge-case tests for browser_tabs."""

    async def test_new_tab_invalid_scheme(
        self, management_tools, mock_ctx, mock_connection_manager, mock_browser
    ):
        """New tab with invalid URL scheme returns error."""
        _setup_browser(mock_connection_manager, mock_browser)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='new', url='ftp://evil.com'
        )

        assert 'Error' in result
        assert 'scheme' in result.lower()

    async def test_close_tab_no_remaining_pages(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Close tab when no pages remain returns plain message without snapshot."""
        page1 = MagicMock()
        page1.title = AsyncMock(return_value='Tab One')
        page1.close = AsyncMock()
        page2 = MagicMock()
        page2.title = AsyncMock(return_value='Tab Two')
        page2.close = AsyncMock()

        context = MagicMock()
        context.pages = [page1, page2]
        mock_connection_manager.get_context.return_value = context

        # After close, context.pages becomes empty
        async def close_page():
            context.pages = []

        page2.close = AsyncMock(side_effect=close_page)

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='close', tab_index=1
        )

        assert 'Closed tab [1]' in result
        assert '0 tab(s) remaining' in result
        mock_snapshot_manager.capture.assert_not_awaited()

    async def test_tabs_generic_exception_snapshot_also_fails(
        self, management_tools, mock_ctx, mock_connection_manager
    ):
        """Generic exception when both tab operation and snapshot fallback fail."""
        mock_connection_manager.get_context.side_effect = Exception('CDP error')
        mock_connection_manager.get_page.side_effect = Exception('Page also gone')

        result = await management_tools.browser_tabs(
            ctx=mock_ctx, session_id='sess-1', action='list'
        )

        assert 'CDP error' in result


class TestBrowserCloseEdgeCases:
    """Additional edge-case tests for browser_close."""

    async def test_close_page_post_close_context_raises(
        self,
        management_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_browser,
    ):
        """Close page returns plain message when post-close get_context raises ValueError."""
        page = MagicMock()
        page.title = AsyncMock(return_value='Closing Page')
        page.url = 'https://example.com'
        page.close = AsyncMock()
        mock_connection_manager.get_page.return_value = page

        # First call succeeds (line 186), second call raises ValueError (line 197)
        call_count = [0]

        def get_context_side_effect(sid):
            call_count[0] += 1
            if call_count[0] == 1:
                ctx = MagicMock()
                ctx.pages = [page, MagicMock()]  # 2 pages so close is allowed
                return ctx
            raise ValueError('No context after close')

        mock_connection_manager.get_context.side_effect = get_context_side_effect

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        assert 'Closed page: Closing Page' in result
        mock_snapshot_manager.capture.assert_not_awaited()

    async def test_close_page_post_close_empty_pages(
        self, management_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager
    ):
        """Close page when post-close context has empty pages returns plain message."""
        page = MagicMock()
        page.title = AsyncMock(return_value='Closing Page')
        page.url = 'https://example.com'
        page.close = AsyncMock()
        mock_connection_manager.get_page.return_value = page

        call_count = [0]

        def get_context_side_effect(sid):
            call_count[0] += 1
            if call_count[0] == 1:
                ctx = MagicMock()
                ctx.pages = [page, MagicMock()]
                return ctx
            # Second call: context exists but pages is empty
            ctx = MagicMock()
            ctx.pages = []
            return ctx

        mock_connection_manager.get_context.side_effect = get_context_side_effect

        result = await management_tools.browser_close(ctx=mock_ctx, session_id='sess-1')

        assert 'Closed page: Closing Page' in result
        mock_snapshot_manager.capture.assert_not_awaited()


class TestBrowserResizeEdgeCases:
    """Additional edge-case tests for browser_resize."""

    async def test_resize_out_of_bounds(self, management_tools, mock_ctx, mock_connection_manager):
        """Resize with too-small dimensions returns bounds error."""
        result = await management_tools.browser_resize(
            ctx=mock_ctx, session_id='sess-1', width=50, height=50
        )

        assert 'Error' in result
        assert 'out of bounds' in result


class TestToolRegistration:
    """Tests for management tool registration."""

    def test_register_tools(self, management_tools):
        """All three management tools are registered."""
        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn

        management_tools.register(mock_mcp)

        tool_names = [call.kwargs['name'] for call in mock_mcp.tool.call_args_list]
        assert 'browser_tabs' in tool_names
        assert 'browser_close' in tool_names
        assert 'browser_resize' in tool_names
        assert len(tool_names) == 3
