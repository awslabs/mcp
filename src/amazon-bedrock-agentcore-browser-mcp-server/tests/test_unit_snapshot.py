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

"""Unit tests for SnapshotManager."""

import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    RefNotFoundError,
    SnapshotManager,
)
from unittest.mock import AsyncMock, MagicMock


def _node(node_id, role, name='', parent_id=None, properties=None, ignored=False):
    """Helper to build CDP AX tree nodes."""
    n = {
        'nodeId': str(node_id),
        'ignored': ignored,
        'role': {'type': 'role', 'value': role},
        'name': {'type': 'computedString', 'value': name},
        'properties': properties or [],
    }
    if parent_id is not None:
        n['parentId'] = str(parent_id)
    return n


def _prop(name, value):
    """Helper to build a CDP property entry."""
    return {'name': name, 'value': {'type': 'booleanOrUndefined', 'value': value}}


@pytest.fixture
def snapshot_manager():
    """Create a fresh SnapshotManager."""
    return SnapshotManager()


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page with CDP session support."""
    page = MagicMock()
    page.get_by_role = MagicMock()

    cdp_session = MagicMock()
    cdp_session.send = AsyncMock()
    cdp_session.detach = AsyncMock()

    context = MagicMock()
    context.new_cdp_session = AsyncMock(return_value=cdp_session)
    page.context = context

    return page


def _get_cdp(mock_page):
    """Get the mock CDP session from a mock page."""
    return mock_page.context.new_cdp_session.return_value


# CDP-format accessibility trees
SIMPLE_LOGIN_NODES = [
    _node(1, 'RootWebArea', 'Login Page'),
    _node(2, 'heading', 'Sign In', parent_id=1, properties=[_prop('level', 1)]),
    _node(3, 'group', 'Login Form', parent_id=1),
    _node(4, 'textbox', 'Email', parent_id=3),
    _node(5, 'textbox', 'Password', parent_id=3),
    _node(6, 'button', 'Sign In', parent_id=3),
    _node(7, 'link', 'Forgot password?', parent_id=3),
]

TREE_WITH_PROPERTIES_NODES = [
    _node(1, 'RootWebArea', ''),
    _node(2, 'checkbox', 'Remember me', parent_id=1, properties=[_prop('checked', False)]),
    _node(3, 'button', 'Submit', parent_id=1, properties=[_prop('disabled', True)]),
    {
        **_node(4, 'textbox', 'Search', parent_id=1),
        'value': {'type': 'string', 'value': 'hello'},
    },
    _node(5, 'combobox', 'Country', parent_id=1, properties=[_prop('expanded', False)]),
]

NESTED_NAV_NODES = [
    _node(1, 'RootWebArea', ''),
    _node(2, 'navigation', 'Main', parent_id=1),
    _node(3, 'link', 'Home', parent_id=2),
    _node(4, 'link', 'About', parent_id=2),
    _node(5, 'group', 'Products', parent_id=2),
    _node(6, 'link', 'Widget A', parent_id=5),
    _node(7, 'link', 'Widget B', parent_id=5),
]

GENERIC_WRAPPER_NODES = [
    _node(1, 'RootWebArea', ''),
    _node(2, 'generic', '', parent_id=1, ignored=True),
    _node(3, 'button', 'Click Me', parent_id=2),
]

DUPLICATE_LINKS_NODES = [
    _node(1, 'RootWebArea', 'Hacker News'),
    _node(2, 'link', '126 comments', parent_id=1),
    _node(3, 'link', '126 comments', parent_id=1),
    _node(4, 'link', '42 comments', parent_id=1),
]


class TestSnapshotCapture:
    """Tests for accessibility tree capture and formatting."""

    async def test_simple_login_page(self, snapshot_manager, mock_page):
        """Formats a simple login page with correct refs."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'heading "Sign In"' in result
        assert 'textbox "Email" [ref=e1]' in result
        assert 'textbox "Password" [ref=e2]' in result
        assert 'button "Sign In" [ref=e3]' in result
        assert 'link "Forgot password?" [ref=e4]' in result
        assert snapshot_manager.ref_count('sess-1') == 4

    async def test_properties_included(self, snapshot_manager, mock_page):
        """Includes element properties like checked, disabled, value."""
        _get_cdp(mock_page).send.return_value = {'nodes': TREE_WITH_PROPERTIES_NODES}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'checked=False' in result
        assert 'disabled' in result
        assert 'value="hello"' in result
        assert 'expanded=False' in result

    async def test_nested_indentation(self, snapshot_manager, mock_page):
        """Nested elements are properly indented."""
        _get_cdp(mock_page).send.return_value = {'nodes': NESTED_NAV_NODES}

        result = await snapshot_manager.capture(mock_page, 'sess-1')
        lines = result.split('\n')

        # navigation is top-level, Home is indented under it
        nav_line = next(l for l in lines if 'navigation' in l)
        home_line = next(l for l in lines if 'Home' in l)
        assert home_line.startswith('  ')  # Indented under navigation
        assert not nav_line.startswith('  ')  # Top-level

    async def test_empty_tree(self, snapshot_manager, mock_page):
        """Empty node list returns informative message."""
        _get_cdp(mock_page).send.return_value = {'nodes': []}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'Empty page' in result or 'no accessibility tree' in result
        assert snapshot_manager.ref_count('sess-1') == 0

    async def test_ignored_nodes_skipped_children_promoted(self, snapshot_manager, mock_page):
        """Ignored nodes are skipped but their children are promoted."""
        _get_cdp(mock_page).send.return_value = {'nodes': GENERIC_WRAPPER_NODES}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'generic' not in result
        assert 'button "Click Me" [ref=e1]' in result

    async def test_only_interactable_get_refs(self, snapshot_manager, mock_page):
        """Non-interactable elements (heading, group, navigation) get no refs."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        for line in result.split('\n'):
            if 'heading' in line:
                assert 'ref=' not in line
            if 'group' in line:
                assert 'ref=' not in line

    async def test_long_name_truncated(self, snapshot_manager, mock_page):
        """Very long element names are truncated."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            _node(2, 'button', 'A' * 200, parent_id=1),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert '...' in result
        assert 'A' * 200 not in result

    async def test_snapshot_error_handling(self, snapshot_manager, mock_page):
        """Snapshot errors return informative error message."""
        mock_page.context.new_cdp_session.return_value.send.side_effect = Exception('CDP timeout')

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'Error' in result
        assert 'CDP timeout' in result


class TestRefResolution:
    """Tests for resolving refs to Playwright locators."""

    async def test_resolve_valid_ref(self, snapshot_manager, mock_page):
        """Resolves a valid ref to a Playwright locator."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        mock_locator = MagicMock()
        mock_page.get_by_role.return_value = mock_locator

        locator = await snapshot_manager.resolve_ref(mock_page, 'e3', 'sess-1')

        mock_page.get_by_role.assert_called_once_with('button', name='Sign In')
        assert locator is mock_locator

    async def test_resolve_invalid_ref(self, snapshot_manager, mock_page):
        """Raises RefNotFoundError for unknown ref."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        with pytest.raises(RefNotFoundError, match='e99'):
            await snapshot_manager.resolve_ref(mock_page, 'e99', 'sess-1')

    async def test_resolve_after_recapture(self, snapshot_manager, mock_page):
        """Refs from old snapshot are cleared on recapture."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        # Recapture with different tree
        _get_cdp(mock_page).send.return_value = {
            'nodes': [
                _node(1, 'RootWebArea', ''),
                _node(2, 'button', 'New Button', parent_id=1),
            ]
        }
        await snapshot_manager.capture(mock_page, 'sess-1')

        # Old refs should be gone
        with pytest.raises(RefNotFoundError):
            await snapshot_manager.resolve_ref(mock_page, 'e4', 'sess-1')

        # New ref should work
        mock_page.get_by_role.return_value = MagicMock()
        await snapshot_manager.resolve_ref(mock_page, 'e1', 'sess-1')
        mock_page.get_by_role.assert_called_with('button', name='New Button')

    async def test_resolve_ref_no_snapshot(self, snapshot_manager, mock_page):
        """Raises RefNotFoundError when no snapshot has been taken."""
        with pytest.raises(RefNotFoundError):
            await snapshot_manager.resolve_ref(mock_page, 'e1', 'sess-1')

    async def test_resolve_duplicate_names_uses_nth(self, snapshot_manager, mock_page):
        """Duplicate role+name elements resolve to distinct nth locators."""
        _get_cdp(mock_page).send.return_value = {'nodes': DUPLICATE_LINKS_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        mock_locator = MagicMock()
        mock_nth_locator_0 = MagicMock(name='nth(0)')
        mock_nth_locator_1 = MagicMock(name='nth(1)')
        mock_locator.nth = MagicMock(side_effect=lambda n: {0: mock_nth_locator_0, 1: mock_nth_locator_1}[n])
        mock_page.get_by_role.return_value = mock_locator

        # e1 is the first "126 comments" link -> nth(0)
        locator_1 = await snapshot_manager.resolve_ref(mock_page, 'e1', 'sess-1')
        assert locator_1 is mock_nth_locator_0

        # e2 is the second "126 comments" link -> nth(1)
        locator_2 = await snapshot_manager.resolve_ref(mock_page, 'e2', 'sess-1')
        assert locator_2 is mock_nth_locator_1

    async def test_resolve_unique_name_no_nth(self, snapshot_manager, mock_page):
        """Unique role+name elements do not use nth disambiguation."""
        _get_cdp(mock_page).send.return_value = {'nodes': DUPLICATE_LINKS_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        mock_locator = MagicMock()
        mock_page.get_by_role.return_value = mock_locator

        # e3 is "42 comments" which is unique -- no .nth() needed
        locator = await snapshot_manager.resolve_ref(mock_page, 'e3', 'sess-1')
        assert locator is mock_locator
        mock_locator.nth.assert_not_called()


class TestCleanupSession:
    """Tests for session cleanup."""

    async def test_cleanup_session(self, snapshot_manager, mock_page):
        """Cleanup removes all state for a session."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        assert snapshot_manager.ref_count('sess-1') > 0
        assert snapshot_manager.previous_snapshot('sess-1') is not None

        snapshot_manager.cleanup_session('sess-1')

        assert snapshot_manager.ref_count('sess-1') == 0
        assert snapshot_manager.previous_snapshot('sess-1') is None
        with pytest.raises(RefNotFoundError):
            await snapshot_manager.resolve_ref(mock_page, 'e1', 'sess-1')
