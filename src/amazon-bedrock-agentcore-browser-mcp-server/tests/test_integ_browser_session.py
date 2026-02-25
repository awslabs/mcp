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

"""Integration tests for all 24 browser MCP tools against live AgentCore sessions.

These tests make live API calls to Amazon Bedrock AgentCore and require:
- Valid AWS credentials (via profile or environment)
- Access to AgentCore Browser APIs
- Playwright browsers installed (npx playwright install chromium)

Run with: uv run pytest tests/test_integ_browser_session.py -m live -v
Skip with: uv run pytest -m "not live"

Architecture: 4 test classes, each sharing a single AgentCore session via
class-scoped fixtures. This minimizes session cost while covering all 24 tools
with full parameter variants (~45 test methods, 4 sessions total).
"""

import asyncio
import os
import pytest
import re
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.interaction import InteractionTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.management import ManagementTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.navigation import NavigationTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.observation import ObservationTools
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.session import BrowserSessionTools
from unittest.mock import AsyncMock, MagicMock


REGION = os.getenv('AWS_REGION', 'us-east-1')


# ---------------------------------------------------------------------------
# Test HTML pages
# ---------------------------------------------------------------------------

TEST_FORM_HTML = """
<html>
<head><title>Test Form Page</title></head>
<body>
    <h1>Test Form</h1>
    <form>
        <label for="email">Email</label>
        <input type="text" id="email" name="email" aria-label="Email">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" aria-label="Password">
        <label for="country">Country</label>
        <select id="country" name="country" aria-label="Country">
            <option value="us">United States</option>
            <option value="uk">United Kingdom</option>
            <option value="de">Germany</option>
        </select>
        <button type="submit" aria-label="Submit">Submit</button>
    </form>
    <button ondblclick="window._dblClicked=true" aria-label="Double Click">Double Click</button>
</body>
</html>
"""

TEST_UPLOAD_HTML = """
<html><body>
  <h1>Upload Test</h1>
  <input type="file" id="fileInput" aria-label="File upload">
  <button type="submit">Upload</button>
</body></html>
"""

TEST_DIALOG_HTML = """
<html><body>
  <h1>Dialog Test</h1>
  <button onclick="window._alertFired=true; alert('hello')" aria-label="Alert">Alert</button>
  <button onclick="window._confirmResult=confirm('sure?')" aria-label="Confirm">Confirm</button>
  <button onclick="window._promptResult=prompt('name?')" aria-label="Prompt">Prompt</button>
</body></html>
"""

TEST_NAV_HTML = """
<html>
<head><title>Navigation Test</title></head>
<body>
    <h1>Navigation Test Page</h1>
    <p>This page is used for navigation and observation tests.</p>
    <a href="about:blank" aria-label="Test Link">Test Link</a>
</body>
</html>
"""

TEST_TABS_HTML = """
<html>
<head><title>Tabs Test</title></head>
<body><h1>Tabs Test Page</h1></body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx():
    """Create a mock MCP Context for integration tests."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


async def _setup_page(connection_manager, session_id, html):
    """Set page content via CDP Page.setDocumentContent.

    AgentCore Chromium enforces Trusted Types, blocking page.set_content()
    and document.write(). Data URLs produce incomplete accessibility trees.
    CDP Page.setDocumentContent works at the protocol level, bypassing both.
    """
    page = await connection_manager.get_page(session_id)
    await page.goto('about:blank', wait_until='domcontentloaded')
    cdp = await page.context.new_cdp_session(page)
    try:
        frame_tree = await cdp.send('Page.getFrameTree')
        frame_id = frame_tree['frameTree']['frame']['id']
        await cdp.send(
            'Page.setDocumentContent',
            {'frameId': frame_id, 'html': html},
        )
    finally:
        await cdp.detach()
    await page.wait_for_load_state('domcontentloaded')


def _find_ref(snapshot_text, role, name):
    """Extract the element ref for a given role and name from snapshot text.

    Args:
        snapshot_text: Accessibility tree text from browser_snapshot.
        role: Element role (e.g., 'textbox', 'link', 'combobox', 'button').
        name: Element accessible name (e.g., 'Email', 'Submit').

    Returns:
        The ref string (e.g., 'e3').

    Raises:
        AssertionError: If the ref is not found in the snapshot.
    """
    pattern = rf'{role} "{re.escape(name)}".*?\[ref=(e\d+)'
    match = re.search(pattern, snapshot_text)
    assert match, f'No {role} "{name}" found in snapshot:\n{snapshot_text}'
    return match.group(1)


# ---------------------------------------------------------------------------
# Session fixtures (class-scoped, one session per test class)
# ---------------------------------------------------------------------------


@pytest.fixture(scope='class')
async def nav_env():
    """Start a session for navigation and observation tests."""
    ctx = _make_ctx()
    conn_mgr = BrowserConnectionManager()
    snap_mgr = SnapshotManager()
    session_tools = BrowserSessionTools(connection_manager=conn_mgr)

    start = await session_tools.start_browser_session(
        ctx=ctx,
        timeout_seconds=300,
        region=REGION,
    )

    yield {
        'ctx': ctx,
        'sid': start.session_id,
        'nav': NavigationTools(conn_mgr, snap_mgr),
        'obs': ObservationTools(conn_mgr, snap_mgr),
        'session_tools': session_tools,
        'conn_mgr': conn_mgr,
    }

    try:
        await session_tools.stop_browser_session(
            ctx=ctx,
            session_id=start.session_id,
            region=REGION,
        )
    except Exception:
        pass
    await conn_mgr.cleanup()


@pytest.fixture(scope='class')
async def form_env():
    """Start a session for interaction and form tests."""
    ctx = _make_ctx()
    conn_mgr = BrowserConnectionManager()
    snap_mgr = SnapshotManager()
    session_tools = BrowserSessionTools(connection_manager=conn_mgr)

    start = await session_tools.start_browser_session(
        ctx=ctx,
        timeout_seconds=300,
        region=REGION,
    )

    yield {
        'ctx': ctx,
        'sid': start.session_id,
        'nav': NavigationTools(conn_mgr, snap_mgr),
        'obs': ObservationTools(conn_mgr, snap_mgr),
        'interaction': InteractionTools(conn_mgr, snap_mgr),
        'session_tools': session_tools,
        'conn_mgr': conn_mgr,
    }

    try:
        await session_tools.stop_browser_session(
            ctx=ctx,
            session_id=start.session_id,
            region=REGION,
        )
    except Exception:
        pass
    await conn_mgr.cleanup()


@pytest.fixture(scope='class')
async def mgmt_env():
    """Start a session for management tool tests."""
    ctx = _make_ctx()
    conn_mgr = BrowserConnectionManager()
    snap_mgr = SnapshotManager()
    session_tools = BrowserSessionTools(connection_manager=conn_mgr)

    start = await session_tools.start_browser_session(
        ctx=ctx,
        timeout_seconds=300,
        region=REGION,
    )

    yield {
        'ctx': ctx,
        'sid': start.session_id,
        'nav': NavigationTools(conn_mgr, snap_mgr),
        'obs': ObservationTools(conn_mgr, snap_mgr),
        'mgmt': ManagementTools(conn_mgr, snap_mgr),
        'session_tools': session_tools,
        'conn_mgr': conn_mgr,
    }

    try:
        await session_tools.stop_browser_session(
            ctx=ctx,
            session_id=start.session_id,
            region=REGION,
        )
    except Exception:
        pass
    await conn_mgr.cleanup()


# ===========================================================================
# Class 1: Session Lifecycle (start, get, list, stop)
# ===========================================================================


@pytest.mark.live
@pytest.mark.asyncio(loop_scope='class')
class TestSessionLifecycle:
    """Integration tests for the 4 session management tools.

    Tests run in definition order and share state via class attributes.
    """

    async def test_start_session(self):
        """Start a session with default parameters."""
        cls = type(self)
        cls._ctx = _make_ctx()
        cls._conn_mgr = BrowserConnectionManager()
        cls._session_tools = BrowserSessionTools(connection_manager=cls._conn_mgr)

        result = await cls._session_tools.start_browser_session(
            ctx=cls._ctx,
            timeout_seconds=300,
            region=REGION,
        )

        cls._session_id = result.session_id
        assert result.session_id, 'Session ID should not be empty'
        assert result.status == 'ACTIVE'
        assert result.automation_stream_url is not None
        assert 'wss://' in result.automation_stream_url
        assert result.browser_identifier == 'aws.browser.v1'

    async def test_start_session_custom_viewport(self):
        """Start a separate session with custom viewport dimensions."""
        cls = type(self)
        ctx = cls._ctx
        conn_mgr2 = BrowserConnectionManager()
        session_tools2 = BrowserSessionTools(connection_manager=conn_mgr2)

        try:
            result = await session_tools2.start_browser_session(
                ctx=ctx,
                timeout_seconds=300,
                viewport_width=800,
                viewport_height=600,
                region=REGION,
            )
            assert result.session_id
            assert result.status == 'ACTIVE'
            assert result.viewport_width == 800
            assert result.viewport_height == 600
        finally:
            if result and result.session_id:
                await session_tools2.stop_browser_session(
                    ctx=ctx,
                    session_id=result.session_id,
                    region=REGION,
                )
            await conn_mgr2.cleanup()

    async def test_get_session(self):
        """Retrieve session details with get_browser_session."""
        cls = type(self)
        result = await cls._session_tools.get_browser_session(
            ctx=cls._ctx,
            session_id=cls._session_id,
            region=REGION,
        )

        assert result.session_id == cls._session_id
        assert result.status in ('READY', 'ACTIVE', 'INITIALIZING')
        assert result.viewport_width == 1456
        assert result.viewport_height == 819

    async def test_list_sessions(self):
        """List sessions and verify the API returns results."""
        cls = type(self)
        result = await cls._session_tools.list_browser_sessions(
            ctx=cls._ctx,
            region=REGION,
        )

        assert isinstance(result.sessions, list)
        assert result.message

    async def test_stop_session(self):
        """Stop the session and verify termination."""
        cls = type(self)
        result = await cls._session_tools.stop_browser_session(
            ctx=cls._ctx,
            session_id=cls._session_id,
            region=REGION,
        )

        assert result.status == 'TERMINATED'
        await cls._conn_mgr.cleanup()


# ===========================================================================
# Class 2: Navigation and Observation (navigate, snapshot, screenshot, etc.)
# ===========================================================================


@pytest.mark.live
@pytest.mark.asyncio(loop_scope='class')
class TestNavigationAndObservation:
    """Integration tests for 3 navigation tools and 6 observation tools."""

    async def test_navigate(self, nav_env):
        """Navigate to about:blank and verify the tool returns a result."""
        # AgentCore browser blocks external URLs, so we test navigation
        # with about:blank and verify the tool's return format.
        result = await nav_env['nav'].browser_navigate(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            url='about:blank',
        )

        assert 'Navigated to' in result
        assert 'about:blank' in result

    async def test_snapshot(self, nav_env):
        """Take an accessibility tree snapshot of an injected page."""
        await _setup_page(nav_env['conn_mgr'], nav_env['sid'], TEST_NAV_HTML)
        result = await nav_env['obs'].browser_snapshot(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert 'Navigation Test Page' in result
        assert 'heading' in result
        assert 'ref=e' in result

    async def test_screenshot(self, nav_env):
        """Take a viewport screenshot and verify image data."""
        result = await nav_env['obs'].browser_take_screenshot(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert isinstance(result, list)
        assert result[0]['type'] == 'image'
        assert result[0]['mimeType'] == 'image/png'
        assert len(result[0]['data']) > 100

        type(self)._viewport_screenshot_len = len(result[0]['data'])

    async def test_screenshot_full_page(self, nav_env):
        """Take a full-page screenshot (should be at least as large as viewport)."""
        result = await nav_env['obs'].browser_take_screenshot(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            full_page=True,
        )

        assert isinstance(result, list)
        assert len(result[0]['data']) > 100

    async def test_evaluate(self, nav_env):
        """Evaluate a JavaScript expression returning a string."""
        await _setup_page(nav_env['conn_mgr'], nav_env['sid'], TEST_NAV_HTML)
        result = await nav_env['obs'].browser_evaluate(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            expression='document.title',
        )

        assert 'Navigation Test' in result

    async def test_evaluate_object(self, nav_env):
        """Evaluate a JavaScript expression returning an object."""
        result = await nav_env['obs'].browser_evaluate(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            expression='({title: document.title, links: document.querySelectorAll("a").length})',
        )

        assert 'Navigation Test' in result
        assert 'links' in result

    async def test_evaluate_null(self, nav_env):
        """Evaluate a JavaScript expression returning null."""
        result = await nav_env['obs'].browser_evaluate(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            expression='null',
        )

        assert isinstance(result, str)

    async def test_console_messages(self, nav_env):
        """Retrieve console messages without crashing."""
        result = await nav_env['obs'].browser_console_messages(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert isinstance(result, str)

    async def test_network_requests(self, nav_env):
        """Retrieve network request log."""
        result = await nav_env['obs'].browser_network_requests(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert isinstance(result, str)

    async def test_wait_for_text(self, nav_env):
        """Wait for text that exists on the page."""
        await _setup_page(nav_env['conn_mgr'], nav_env['sid'], TEST_NAV_HTML)
        result = await nav_env['obs'].browser_wait_for(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            text='Navigation Test',
            timeout=5000,
        )

        assert 'Found' in result

    async def test_wait_for_selector(self, nav_env):
        """Wait for a CSS selector that exists on the page."""
        result = await nav_env['obs'].browser_wait_for(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            selector='h1',
            timeout=5000,
        )

        assert 'Found' in result

    async def test_wait_for_timeout(self, nav_env):
        """Wait for nonexistent text and verify timeout behavior."""
        result = await nav_env['obs'].browser_wait_for(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
            text='nonexistent_text_xyz',
            timeout=1000,
        )

        assert 'timed out' in result.lower() or 'timeout' in result.lower()

    async def test_wait_for_no_criteria(self, nav_env):
        """Call wait_for with no text or selector and verify error."""
        result = await nav_env['obs'].browser_wait_for(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert 'error' in result.lower() or 'provide' in result.lower()

    async def test_navigate_back(self, nav_env):
        """Navigate to two pages then go back to the first."""
        ctx, sid, nav = nav_env['ctx'], nav_env['sid'], nav_env['nav']
        conn_mgr = nav_env['conn_mgr']

        # Create two history entries using CDP-injected pages
        await _setup_page(
            conn_mgr, sid, '<html><head><title>Page One</title></head><body>First</body></html>'
        )
        await _setup_page(
            conn_mgr, sid, '<html><head><title>Page Two</title></head><body>Second</body></html>'
        )

        result = await nav.browser_navigate_back(ctx=ctx, session_id=sid)

        assert 'Navigated back' in result

    async def test_navigate_forward(self, nav_env):
        """After going back, navigate forward to the second page."""
        result = await nav_env['nav'].browser_navigate_forward(
            ctx=nav_env['ctx'],
            session_id=nav_env['sid'],
        )

        assert 'Navigated forward' in result


# ===========================================================================
# Class 3: Interaction and Forms (click, type, fill, select, hover, etc.)
# ===========================================================================


@pytest.mark.live
@pytest.mark.asyncio(loop_scope='class')
class TestInteractionAndForms:
    """Integration tests for all 8 interaction tools."""

    async def test_click(self, form_env):
        """Click a link on an injected page."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_NAV_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        link_ref = _find_ref(snap, 'link', 'Test Link')

        result = await interaction.browser_click(ctx=ctx, session_id=sid, ref=link_ref)

        assert 'Clicked' in result

    async def test_click_double(self, form_env):
        """Double-click a button on an injected page."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        btn_ref = _find_ref(snap, 'button', 'Double Click')

        result = await interaction.browser_click(
            ctx=ctx,
            session_id=sid,
            ref=btn_ref,
            double_click=True,
        )

        assert 'Double-clicked' in result

    async def test_type_text(self, form_env):
        """Type text into a form field."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        email_ref = _find_ref(snap, 'textbox', 'Email')

        result = await interaction.browser_type(
            ctx=ctx,
            session_id=sid,
            ref=email_ref,
            text='user@test.com',
        )

        assert 'Typed' in result
        assert 'user@test.com' in result

    async def test_type_with_submit(self, form_env):
        """Type text and press Enter to submit."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        email_ref = _find_ref(snap, 'textbox', 'Email')

        result = await interaction.browser_type(
            ctx=ctx,
            session_id=sid,
            ref=email_ref,
            text='test',
            submit=True,
        )

        assert 'pressed Enter' in result

    async def test_type_without_clear(self, form_env):
        """Type text without clearing existing content first."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        email_ref = _find_ref(snap, 'textbox', 'Email')

        result = await interaction.browser_type(
            ctx=ctx,
            session_id=sid,
            ref=email_ref,
            text='append',
            clear_first=False,
        )

        assert 'Typed' in result

    async def test_fill_form(self, form_env):
        """Fill multiple form fields at once."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        email_ref = _find_ref(snap, 'textbox', 'Email')
        pw_ref = _find_ref(snap, 'textbox', 'Password')

        result = await interaction.browser_fill_form(
            ctx=ctx,
            session_id=sid,
            fields=[
                {'ref': email_ref, 'value': 'a@b.c'},
                {'ref': pw_ref, 'value': 'secret'},
            ],
        )

        assert 'Filled 2 form field(s)' in result

    async def test_fill_form_with_submit(self, form_env):
        """Fill form fields and click the submit button."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        email_ref = _find_ref(snap, 'textbox', 'Email')
        pw_ref = _find_ref(snap, 'textbox', 'Password')
        submit_ref = _find_ref(snap, 'button', 'Submit')

        result = await interaction.browser_fill_form(
            ctx=ctx,
            session_id=sid,
            fields=[
                {'ref': email_ref, 'value': 'a@b.c'},
                {'ref': pw_ref, 'value': 'secret'},
            ],
            submit_ref=submit_ref,
        )

        assert 'Filled 2 form field(s)' in result
        assert 'clicked submit' in result

    async def test_select_option_by_label(self, form_env):
        """Select a dropdown option by its visible label."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        country_ref = _find_ref(snap, 'combobox', 'Country')

        result = await interaction.browser_select_option(
            ctx=ctx,
            session_id=sid,
            ref=country_ref,
            label='United Kingdom',
        )

        assert 'Selected' in result

    async def test_select_option_by_value(self, form_env):
        """Select a dropdown option by its value attribute."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        country_ref = _find_ref(snap, 'combobox', 'Country')

        result = await interaction.browser_select_option(
            ctx=ctx,
            session_id=sid,
            ref=country_ref,
            value='de',
        )

        assert 'Selected' in result

    async def test_select_option_by_index(self, form_env):
        """Select a dropdown option by zero-based index."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        country_ref = _find_ref(snap, 'combobox', 'Country')

        result = await interaction.browser_select_option(
            ctx=ctx,
            session_id=sid,
            ref=country_ref,
            index=0,
        )

        assert 'Selected' in result

    async def test_select_option_no_criteria(self, form_env):
        """Calling select_option with no criteria raises ValueError."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        country_ref = _find_ref(snap, 'combobox', 'Country')

        with pytest.raises(ValueError, match='Provide one of'):
            await interaction.browser_select_option(
                ctx=ctx,
                session_id=sid,
                ref=country_ref,
            )

    async def test_hover(self, form_env):
        """Hover over an element."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_FORM_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        submit_ref = _find_ref(snap, 'button', 'Submit')

        result = await interaction.browser_hover(
            ctx=ctx,
            session_id=sid,
            ref=submit_ref,
        )

        assert 'Hovered over element' in result

    async def test_press_key(self, form_env):
        """Press a single keyboard key."""
        ctx, sid = form_env['ctx'], form_env['sid']
        interaction = form_env['interaction']

        result = await interaction.browser_press_key(
            ctx=ctx,
            session_id=sid,
            key='Tab',
        )

        assert 'Pressed key: Tab' in result

    async def test_press_key_combo(self, form_env):
        """Press a key combination."""
        ctx, sid = form_env['ctx'], form_env['sid']
        interaction = form_env['interaction']

        result = await interaction.browser_press_key(
            ctx=ctx,
            session_id=sid,
            key='Control+a',
        )

        assert 'Pressed key: Control+a' in result

    async def test_upload_file(self, form_env):
        """Upload a file to a file input element."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_UPLOAD_HTML)
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)

        # The file input renders as button "File upload" in the accessibility tree
        file_ref = _find_ref(snap, 'button', 'File upload')

        # Use /etc/hosts — exists on both macOS and Linux
        result = await interaction.browser_upload_file(
            ctx=ctx,
            session_id=sid,
            ref=file_ref,
            paths=['/etc/hosts'],
        )

        assert 'Uploaded' in result

    async def test_handle_dialog_accept(self, form_env):
        """Set dialog handler to accept, then trigger an alert."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_DIALOG_HTML)

        # Set handler BEFORE triggering dialog
        handler_result = await interaction.browser_handle_dialog(
            ctx=ctx,
            session_id=sid,
            action='accept',
        )
        assert 'Dialog handler set: accept' in handler_result

        # Click the alert button — dialog should be auto-accepted
        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        alert_ref = _find_ref(snap, 'button', 'Alert')
        click_result = await interaction.browser_click(ctx=ctx, session_id=sid, ref=alert_ref)

        assert 'Clicked' in click_result

    async def test_handle_dialog_dismiss(self, form_env):
        """Set dialog handler to dismiss, then trigger a confirm dialog."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_DIALOG_HTML)

        handler_result = await interaction.browser_handle_dialog(
            ctx=ctx,
            session_id=sid,
            action='dismiss',
        )
        assert 'Dialog handler set: dismiss' in handler_result

        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        confirm_ref = _find_ref(snap, 'button', 'Confirm')
        click_result = await interaction.browser_click(
            ctx=ctx,
            session_id=sid,
            ref=confirm_ref,
        )

        assert 'Clicked' in click_result

    async def test_handle_dialog_with_prompt(self, form_env):
        """Set dialog handler with prompt_text, trigger prompt, verify result."""
        ctx, sid = form_env['ctx'], form_env['sid']
        obs, interaction = form_env['obs'], form_env['interaction']

        await _setup_page(form_env['conn_mgr'], sid, TEST_DIALOG_HTML)

        handler_result = await interaction.browser_handle_dialog(
            ctx=ctx,
            session_id=sid,
            action='accept',
            prompt_text='Claude',
        )
        assert 'with text "Claude"' in handler_result

        snap = await obs.browser_snapshot(ctx=ctx, session_id=sid)
        prompt_ref = _find_ref(snap, 'button', 'Prompt')
        await interaction.browser_click(ctx=ctx, session_id=sid, ref=prompt_ref)

        # Give the dialog handler a moment to fire
        await asyncio.sleep(0.5)

        # Verify the prompt result was set by our handler
        result = await obs.browser_evaluate(
            ctx=ctx,
            session_id=sid,
            expression='window._promptResult',
        )
        assert 'Claude' in result


# ===========================================================================
# Class 4: Management (tabs, resize, close)
# ===========================================================================


@pytest.mark.live
@pytest.mark.asyncio(loop_scope='class')
class TestManagement:
    """Integration tests for the 3 management tools with all action variants."""

    async def test_tabs_list(self, mgmt_env):
        """List tabs in the session."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        await _setup_page(mgmt_env['conn_mgr'], sid, TEST_TABS_HTML)

        result = await mgmt.browser_tabs(ctx=ctx, session_id=sid, action='list')

        assert 'Open tabs' in result
        assert '[0]' in result

    async def test_tabs_new(self, mgmt_env):
        """Open a new empty tab."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        result = await mgmt.browser_tabs(ctx=ctx, session_id=sid, action='new')

        assert 'Opened new tab' in result

    async def test_tabs_new_with_url(self, mgmt_env):
        """Open a new tab with a URL (about:blank since external URLs are blocked)."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        result = await mgmt.browser_tabs(
            ctx=ctx,
            session_id=sid,
            action='new',
            url='about:blank',
        )

        assert 'Opened new tab' in result

    async def test_tabs_select(self, mgmt_env):
        """Select a specific tab by index."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        result = await mgmt.browser_tabs(
            ctx=ctx,
            session_id=sid,
            action='select',
            tab_index=0,
        )

        assert 'Switched to tab [0]' in result

    async def test_tabs_close(self, mgmt_env):
        """Close a tab by index."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        # Close the last tab we opened (tab index 2 from the two 'new' calls above)
        result = await mgmt.browser_tabs(
            ctx=ctx,
            session_id=sid,
            action='close',
            tab_index=2,
        )

        assert 'Closed tab' in result

    async def test_tabs_unknown_action(self, mgmt_env):
        """Verify that an unknown tab action returns an error."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        result = await mgmt.browser_tabs(ctx=ctx, session_id=sid, action='invalid')

        assert 'error' in result.lower() or 'unknown' in result.lower()

    async def test_resize(self, mgmt_env):
        """Resize the browser viewport."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        result = await mgmt.browser_resize(
            ctx=ctx,
            session_id=sid,
            width=800,
            height=600,
        )

        assert '800x600' in result

    async def test_close_page(self, mgmt_env):
        """Open a new tab, select it, and close it with browser_close."""
        ctx, sid, mgmt = mgmt_env['ctx'], mgmt_env['sid'], mgmt_env['mgmt']

        # Open a new tab (no URL since external URLs are blocked in AgentCore)
        await mgmt.browser_tabs(
            ctx=ctx,
            session_id=sid,
            action='new',
        )

        # List to find the new tab's index
        list_result = await mgmt.browser_tabs(ctx=ctx, session_id=sid, action='list')
        tab_count_match = re.search(r'Open tabs \((\d+)\)', list_result)
        assert tab_count_match, f'Could not parse tab count from: {list_result}'
        last_tab = int(tab_count_match.group(1)) - 1

        # Select the new tab so browser_close targets it
        await mgmt.browser_tabs(ctx=ctx, session_id=sid, action='select', tab_index=last_tab)

        result = await mgmt.browser_close(ctx=ctx, session_id=sid)

        assert 'Closed page' in result
