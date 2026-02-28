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

"""Unit tests for browser interaction, navigation, and observation tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    RefNotFoundError,
    SnapshotManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.interaction import InteractionTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.navigation import NavigationTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.observation import ObservationTools
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_connection_manager():
    """Create a mock BrowserConnectionManager."""
    cm = MagicMock(spec=BrowserConnectionManager)
    cm.get_page = AsyncMock()
    cm.set_dialog_handler = AsyncMock()
    return cm


@pytest.fixture
def mock_snapshot_manager():
    """Create a mock SnapshotManager."""
    sm = MagicMock(spec=SnapshotManager)
    sm.capture = AsyncMock(return_value='- button "OK" [ref=e1]')
    sm.resolve_ref = AsyncMock()
    return sm


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page."""
    page = MagicMock()
    page.title = AsyncMock(return_value='Test Page')
    page.url = 'https://example.com'
    page.goto = AsyncMock()
    page.go_back = AsyncMock()
    page.go_forward = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock(return_value=b'\x89PNG\r\n')
    page.evaluate = AsyncMock(return_value=None)
    page.wait_for_selector = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.get_by_text = MagicMock()
    text_locator = MagicMock()
    text_locator.first = MagicMock()
    text_locator.first.wait_for = AsyncMock()
    page.get_by_text.return_value = text_locator
    return page


@pytest.fixture
def mock_locator():
    """Create a mock Playwright Locator."""
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.dblclick = AsyncMock()
    locator.clear = AsyncMock()
    locator.type = AsyncMock()
    locator.press = AsyncMock()
    locator.hover = AsyncMock()
    locator.select_option = AsyncMock()
    locator.set_input_files = AsyncMock()
    return locator


class TestNavigationTools:
    """Tests for browser_navigate and browser_navigate_back."""

    @pytest.fixture
    def nav_tools(self, mock_connection_manager, mock_snapshot_manager):
        """Create NavigationTools with mocked dependencies."""
        return NavigationTools(mock_connection_manager, mock_snapshot_manager)

    async def test_navigate_to_url(
        self, nav_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Navigate returns title, URL, status, and snapshot."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response

        result = await nav_tools.browser_navigate(
            ctx=mock_ctx,
            session_id='sess-1',
            url='https://example.com',
        )

        mock_page.goto.assert_awaited_once_with(
            'https://example.com', wait_until='domcontentloaded', timeout=30000
        )
        assert 'https://example.com' in result
        assert 'Test Page' in result
        assert '200' in result

    async def test_navigate_back(
        self, nav_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Navigate back returns snapshot of previous page."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await nav_tools.browser_navigate_back(ctx=mock_ctx, session_id='sess-1')

        mock_page.go_back.assert_awaited_once()
        assert 'Navigated back' in result
        assert 'Test Page' in result

    async def test_navigate_forward(
        self, nav_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Navigate forward returns snapshot of next page."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await nav_tools.browser_navigate_forward(ctx=mock_ctx, session_id='sess-1')

        mock_page.go_forward.assert_awaited_once()
        assert 'Navigated forward' in result
        assert 'Test Page' in result


class TestInteractionTools:
    """Tests for browser_click, browser_type, and other interaction tools."""

    @pytest.fixture
    def interaction_tools(self, mock_connection_manager, mock_snapshot_manager):
        """Create InteractionTools with mocked dependencies."""
        return InteractionTools(mock_connection_manager, mock_snapshot_manager)

    async def test_click_element(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Click resolves ref and clicks the element."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_click(ctx=mock_ctx, session_id='sess-1', ref='e1')

        mock_snapshot_manager.resolve_ref.assert_awaited_once_with(mock_page, 'e1', 'sess-1')
        mock_locator.click.assert_awaited_once_with(button='left', timeout=5000)
        assert 'Clicked element e1' in result

    async def test_double_click(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Double-click uses dblclick instead of click."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_click(
            ctx=mock_ctx, session_id='sess-1', ref='e1', double_click=True
        )

        mock_locator.dblclick.assert_awaited_once()
        assert 'Double-clicked' in result

    async def test_click_ref_not_found(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Click with invalid ref returns error and current snapshot."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.side_effect = RefNotFoundError('Ref "e99" not found')

        result = await interaction_tools.browser_click(
            ctx=mock_ctx, session_id='sess-1', ref='e99'
        )

        assert 'Error' in result
        assert 'e99' in result
        mock_snapshot_manager.capture.assert_awaited()

    async def test_type_text(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Type clears, types text, and returns snapshot."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_type(
            ctx=mock_ctx, session_id='sess-1', ref='e2', text='hello@example.com'
        )

        mock_locator.clear.assert_awaited_once()
        mock_locator.type.assert_awaited_once_with('hello@example.com', timeout=5000)
        assert 'Typed' in result

    async def test_type_without_clear(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Type with clear_first=False skips clearing."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        await interaction_tools.browser_type(
            ctx=mock_ctx, session_id='sess-1', ref='e2', text='appended', clear_first=False
        )

        mock_locator.clear.assert_not_awaited()
        mock_locator.type.assert_awaited_once()

    async def test_type_with_submit(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Type with submit=True presses Enter after typing."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_type(
            ctx=mock_ctx, session_id='sess-1', ref='e2', text='query', submit=True
        )

        mock_locator.press.assert_awaited_once_with('Enter', timeout=5000)
        assert 'pressed Enter' in result

    async def test_fill_form(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Fill form fills multiple fields and optionally submits."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        fields = [
            {'ref': 'e1', 'value': 'user@test.com'},
            {'ref': 'e2', 'value': 'password123'},
        ]
        result = await interaction_tools.browser_fill_form(
            ctx=mock_ctx, session_id='sess-1', fields=fields
        )

        assert mock_locator.clear.await_count == 2
        assert mock_locator.type.await_count == 2
        assert 'Filled 2 form field(s)' in result

    async def test_fill_form_with_submit(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Fill form clicks submit button when submit_ref is provided."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        fields = [{'ref': 'e1', 'value': 'test'}]
        result = await interaction_tools.browser_fill_form(
            ctx=mock_ctx, session_id='sess-1', fields=fields, submit_ref='e3'
        )

        assert 'clicked submit' in result
        mock_locator.click.assert_awaited_once()

    async def test_select_option_by_label(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Select option by visible label."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_select_option(
            ctx=mock_ctx, session_id='sess-1', ref='e1', label='United States'
        )

        mock_locator.select_option.assert_awaited_once_with(label='United States', timeout=5000)
        assert 'Selected "United States"' in result

    async def test_select_option_by_value(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Select option by value attribute."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_select_option(
            ctx=mock_ctx, session_id='sess-1', ref='e1', value='us'
        )

        mock_locator.select_option.assert_awaited_once_with(value='us', timeout=5000)
        assert 'Selected "us"' in result

    async def test_select_option_no_criteria(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Select option with no criteria raises ValueError."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = MagicMock()

        with pytest.raises(ValueError, match='Provide one of'):
            await interaction_tools.browser_select_option(
                ctx=mock_ctx, session_id='sess-1', ref='e1'
            )

    async def test_hover(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Hover over an element."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_hover(ctx=mock_ctx, session_id='sess-1', ref='e1')

        mock_locator.hover.assert_awaited_once_with(timeout=5000)
        assert 'Hovered over element e1' in result

    async def test_hover_ref_not_found(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Hover with invalid ref returns error."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.side_effect = RefNotFoundError('not found')

        result = await interaction_tools.browser_hover(
            ctx=mock_ctx, session_id='sess-1', ref='e99'
        )

        assert 'Error' in result
        assert 'e99' in result

    async def test_press_key(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Press keyboard key."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await interaction_tools.browser_press_key(
            ctx=mock_ctx, session_id='sess-1', key='Enter'
        )

        mock_page.keyboard.press.assert_awaited_once_with('Enter')
        assert 'Pressed key: Enter' in result

    async def test_press_key_combo(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Press key combination."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await interaction_tools.browser_press_key(
            ctx=mock_ctx, session_id='sess-1', key='Control+a'
        )

        mock_page.keyboard.press.assert_awaited_once_with('Control+a')
        assert 'Pressed key: Control+a' in result

    async def test_upload_file(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
        mock_locator,
    ):
        """Upload file resolves ref and sets input files."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.return_value = mock_locator

        result = await interaction_tools.browser_upload_file(
            ctx=mock_ctx, session_id='sess-1', ref='e5', paths=['/tmp/a.txt']
        )

        mock_locator.set_input_files.assert_awaited_once()
        assert 'Uploaded' in result

    async def test_upload_file_ref_not_found(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
        mock_page,
    ):
        """Upload file with invalid ref returns error and snapshot."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_snapshot_manager.resolve_ref.side_effect = RefNotFoundError('Ref "e5" not found')

        result = await interaction_tools.browser_upload_file(
            ctx=mock_ctx, session_id='sess-1', ref='e5', paths=['/tmp/a.txt']
        )

        assert 'Error' in result
        mock_snapshot_manager.capture.assert_awaited()

    async def test_handle_dialog_accept(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
    ):
        """Handle dialog with accept action sets handler."""
        result = await interaction_tools.browser_handle_dialog(
            ctx=mock_ctx, session_id='sess-1', action='accept'
        )

        mock_connection_manager.set_dialog_handler.assert_awaited_once_with(
            'sess-1', action='accept', prompt_text=None
        )
        assert 'accept' in result

    async def test_handle_dialog_dismiss(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
    ):
        """Handle dialog with dismiss action sets handler."""
        result = await interaction_tools.browser_handle_dialog(
            ctx=mock_ctx, session_id='sess-1', action='dismiss'
        )

        mock_connection_manager.set_dialog_handler.assert_awaited_once_with(
            'sess-1', action='dismiss', prompt_text=None
        )
        assert 'dismiss' in result

    async def test_handle_dialog_with_prompt(
        self,
        interaction_tools,
        mock_ctx,
        mock_connection_manager,
        mock_snapshot_manager,
    ):
        """Handle dialog with prompt text includes text in response."""
        result = await interaction_tools.browser_handle_dialog(
            ctx=mock_ctx, session_id='sess-1', action='accept', prompt_text='yes'
        )

        mock_connection_manager.set_dialog_handler.assert_awaited_once_with(
            'sess-1', action='accept', prompt_text='yes'
        )
        assert 'with text "yes"' in result


class TestObservationTools:
    """Tests for browser_snapshot, screenshot, wait_for, console, network, evaluate."""

    @pytest.fixture
    def obs_tools(self, mock_connection_manager, mock_snapshot_manager):
        """Create ObservationTools with mocked dependencies."""
        return ObservationTools(mock_connection_manager, mock_snapshot_manager)

    async def test_snapshot(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Snapshot returns page info and accessibility tree."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await obs_tools.browser_snapshot(ctx=mock_ctx, session_id='sess-1')

        mock_snapshot_manager.capture.assert_awaited_once_with(mock_page, 'sess-1', selector=None)
        assert 'Test Page' in result
        assert 'https://example.com' in result

    async def test_screenshot(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Screenshot returns base64 PNG image data."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await obs_tools.browser_take_screenshot(ctx=mock_ctx, session_id='sess-1')

        mock_page.screenshot.assert_awaited_once_with(full_page=False, type='png')
        assert isinstance(result, list)
        assert result[0]['type'] == 'image'
        assert result[0]['mimeType'] == 'image/png'
        assert isinstance(result[0]['data'], str)

    async def test_screenshot_full_page(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Full-page screenshot passes full_page=True."""
        mock_connection_manager.get_page.return_value = mock_page

        await obs_tools.browser_take_screenshot(ctx=mock_ctx, session_id='sess-1', full_page=True)

        mock_page.screenshot.assert_awaited_once_with(full_page=True, type='png')

    async def test_wait_for_text(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Wait for text to appear on page."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await obs_tools.browser_wait_for(
            ctx=mock_ctx, session_id='sess-1', text='Loading complete'
        )

        mock_page.get_by_text.assert_called_once_with('Loading complete')
        assert 'Found text "Loading complete"' in result

    async def test_wait_for_selector(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Wait for CSS selector to become visible."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await obs_tools.browser_wait_for(
            ctx=mock_ctx, session_id='sess-1', selector='#results'
        )

        mock_page.wait_for_selector.assert_awaited_once_with(
            '#results', state='visible', timeout=10000
        )
        assert 'Found selector "#results"' in result

    async def test_wait_for_no_criteria(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Wait with no text or selector returns error."""
        mock_connection_manager.get_page.return_value = mock_page

        result = await obs_tools.browser_wait_for(ctx=mock_ctx, session_id='sess-1')

        assert 'Error' in result

    async def test_wait_for_timeout(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Wait timeout returns error with current snapshot."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.get_by_text.return_value.first.wait_for.side_effect = Exception(
            'Timeout 10000ms'
        )

        result = await obs_tools.browser_wait_for(
            ctx=mock_ctx, session_id='sess-1', text='Missing'
        )

        assert 'timed out' in result or 'Timeout' in result
        mock_snapshot_manager.capture.assert_awaited()

    async def test_console_messages(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Console messages returns error elements from page."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock()
        mock_cdp.detach = AsyncMock()
        mock_page.context = MagicMock()
        mock_page.context.new_cdp_session = AsyncMock(return_value=mock_cdp)
        mock_page.evaluate.return_value = ['Error: 404 not found']

        result = await obs_tools.browser_console_messages(ctx=mock_ctx, session_id='sess-1')

        assert 'Error: 404 not found' in result

    async def test_console_messages_empty(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Console messages with no errors returns guidance."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock()
        mock_cdp.detach = AsyncMock()
        mock_page.context = MagicMock()
        mock_page.context.new_cdp_session = AsyncMock(return_value=mock_cdp)
        mock_page.evaluate.return_value = []

        result = await obs_tools.browser_console_messages(ctx=mock_ctx, session_id='sess-1')

        assert 'No console messages' in result

    async def test_network_requests(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Network requests returns performance entries."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.return_value = [
            {
                'name': 'https://api.example.com/data',
                'type': 'fetch',
                'duration': 150,
                'size': 2048,
            },
        ]

        result = await obs_tools.browser_network_requests(ctx=mock_ctx, session_id='sess-1')

        assert 'Network requests' in result
        assert 'fetch' in result
        assert 'api.example.com' in result

    async def test_network_requests_empty(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Network requests with no entries returns message."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.return_value = []

        result = await obs_tools.browser_network_requests(ctx=mock_ctx, session_id='sess-1')

        assert 'No network requests' in result

    async def test_evaluate_returns_string(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Evaluate returns string result."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.return_value = 'hello world'

        result = await obs_tools.browser_evaluate(
            ctx=mock_ctx, session_id='sess-1', expression='document.title'
        )

        assert 'Result: hello world' in result

    async def test_evaluate_returns_object(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Evaluate returns JSON-serialized object."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.return_value = {'key': 'value', 'count': 42}

        result = await obs_tools.browser_evaluate(
            ctx=mock_ctx, session_id='sess-1', expression='({key: "value", count: 42})'
        )

        assert 'Result:' in result
        assert '"key": "value"' in result

    async def test_evaluate_returns_null(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Evaluate with null return gives success message."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.return_value = None

        result = await obs_tools.browser_evaluate(
            ctx=mock_ctx, session_id='sess-1', expression='void 0'
        )

        assert 'evaluated successfully' in result

    async def test_evaluate_error(
        self, obs_tools, mock_ctx, mock_connection_manager, mock_snapshot_manager, mock_page
    ):
        """Evaluate JS error returns error string."""
        mock_connection_manager.get_page.return_value = mock_page
        mock_page.evaluate.side_effect = Exception('SyntaxError: Unexpected token')

        result = await obs_tools.browser_evaluate(
            ctx=mock_ctx, session_id='sess-1', expression='invalid{{'
        )

        assert 'Error evaluating JavaScript' in result
        assert 'SyntaxError' in result
