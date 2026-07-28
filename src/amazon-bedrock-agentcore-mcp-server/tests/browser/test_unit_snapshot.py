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
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.snapshot_manager import (
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

    async def test_no_root_node(self, snapshot_manager, mock_page):
        """Tree with no root node returns informative message."""
        nodes = [
            _node(2, 'button', 'Click', parent_id=1),
            _node(3, 'link', 'Link', parent_id=1),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'No root node' in result

    async def test_property_pressed(self, snapshot_manager, mock_page):
        """Button with pressed=True property is included in output."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            _node(2, 'button', 'Toggle', parent_id=1, properties=[_prop('pressed', True)]),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'pressed=True' in result

    async def test_property_selected(self, snapshot_manager, mock_page):
        """Option with selected=True property is included in output."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            _node(2, 'option', 'Item', parent_id=1, properties=[_prop('selected', True)]),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'selected' in result

    async def test_property_required(self, snapshot_manager, mock_page):
        """Textbox with required=True property is included in output."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            _node(2, 'textbox', 'Name', parent_id=1, properties=[_prop('required', True)]),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert 'required' in result

    async def test_long_value_truncated(self, snapshot_manager, mock_page):
        """Textbox with value longer than 50 chars is truncated."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            {
                **_node(2, 'textbox', 'Input', parent_id=1),
                'value': {'type': 'string', 'value': 'X' * 100},
            },
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        assert '...' in result
        assert 'X' * 100 not in result


class TestRefResolution:
    """Tests for resolving refs to Playwright locators."""

    async def test_resolve_valid_ref(self, snapshot_manager, mock_page):
        """Resolves a valid ref to a Playwright locator."""
        _get_cdp(mock_page).send.return_value = {'nodes': SIMPLE_LOGIN_NODES}
        await snapshot_manager.capture(mock_page, 'sess-1')

        mock_locator = MagicMock()
        mock_page.get_by_role.return_value = mock_locator

        locator = await snapshot_manager.resolve_ref(mock_page, 'e3', 'sess-1')

        mock_page.get_by_role.assert_called_once_with('button', name='Sign In', exact=True)
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
        mock_page.get_by_role.assert_called_with('button', name='New Button', exact=True)

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
        mock_locator.nth = MagicMock(
            side_effect=lambda n: {0: mock_nth_locator_0, 1: mock_nth_locator_1}[n]
        )
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

    async def test_resolve_ref_nameless_element(self, snapshot_manager, mock_page):
        """Nameless element resolves with role only, no name kwarg."""
        nodes = [
            _node(1, 'RootWebArea', ''),
            _node(2, 'button', '', parent_id=1),
        ]
        _get_cdp(mock_page).send.return_value = {'nodes': nodes}
        await snapshot_manager.capture(mock_page, 'sess-1')

        mock_locator = MagicMock()
        mock_page.get_by_role.return_value = mock_locator

        locator = await snapshot_manager.resolve_ref(mock_page, 'e1', 'sess-1')

        mock_page.get_by_role.assert_called_with('button')
        assert locator is mock_locator


class TestScopedSnapshot:
    """Tests for selector-scoped accessibility tree capture.

    The scoping works by:
    1. Resolving the CSS selector to a backendNodeId via DOM CDP calls
    2. Calling Accessibility.queryAXTree(backendNodeId=X) to get the
       scoped subtree directly from CDP
    3. Falling back to getFullAXTree if queryAXTree fails
    """

    # Full-page nodes (no backendDOMNodeId — mirrors real CDP behavior)
    FULL_PAGE_NODES = [
        _node(1, 'RootWebArea', 'Test Page'),
        _node(2, 'navigation', 'Nav', parent_id=1),
        _node(3, 'link', 'Home', parent_id=2),
        _node(4, 'group', 'Main Content', parent_id=1),
        _node(5, 'heading', 'Welcome', parent_id=4, properties=[_prop('level', 1)]),
        _node(6, 'button', 'Action', parent_id=4),
    ]

    # Scoped subtree that queryAXTree returns — only the target node
    # and its descendants (no ancestors or siblings).
    SCOPED_SUBTREE_NODES = [
        _node(4, 'group', 'Main Content', parent_id=1),
        _node(5, 'heading', 'Welcome', parent_id=4, properties=[_prop('level', 1)]),
        _node(6, 'button', 'Action', parent_id=4),
    ]

    # backendNodeId returned by DOM.describeNode
    MAIN_BACKEND_NODE_ID = 20

    def _make_cdp_dispatcher(
        self,
        *,
        match_node_id=42,
        backend_node_id=None,
        full_nodes=None,
        partial_nodes=None,
        partial_error=False,
    ):
        """Create a side_effect function that dispatches CDP calls by method name."""
        full = full_nodes or self.FULL_PAGE_NODES
        partial = partial_nodes if partial_nodes is not None else self.SCOPED_SUBTREE_NODES
        bid = backend_node_id if backend_node_id is not None else self.MAIN_BACKEND_NODE_ID

        async def dispatcher(method, params=None):
            if method == 'DOM.enable':
                return {}
            if method == 'DOM.disable':
                return {}
            if method == 'DOM.getDocument':
                return {'root': {'nodeId': 1}}
            if method == 'DOM.querySelector':
                return {'nodeId': match_node_id}
            if method == 'DOM.describeNode':
                return {'node': {'backendNodeId': bid}}
            if method == 'Accessibility.queryAXTree':
                if partial_error:
                    raise Exception('queryAXTree not supported')
                return {'nodes': partial}
            if method == 'Accessibility.getFullAXTree':
                return {'nodes': full}
            return {}

        return dispatcher

    async def test_selector_scoped_capture(self, snapshot_manager, mock_page):
        """When selector matches, queryAXTree is used and only subtree nodes are returned."""
        cdp = _get_cdp(mock_page)
        cdp.send = AsyncMock(side_effect=self._make_cdp_dispatcher())

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Action' in result
        assert 'Welcome' in result
        assert 'Warning' not in result
        # Nav content should be filtered out
        assert 'Home' not in result
        assert 'Nav' not in result
        # Verify DOM + partial AX tree calls were made
        calls = [call.args[0] for call in cdp.send.call_args_list]
        assert 'DOM.enable' in calls
        assert 'DOM.querySelector' in calls
        assert 'DOM.disable' in calls
        assert 'Accessibility.queryAXTree' in calls
        assert 'Accessibility.getFullAXTree' not in calls

    async def test_selector_not_found_falls_back(self, snapshot_manager, mock_page):
        """When selector doesn't match, falls back to full page with warning."""
        cdp = _get_cdp(mock_page)
        cdp.send = AsyncMock(side_effect=self._make_cdp_dispatcher(match_node_id=0))

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='#nonexistent')

        assert 'Warning' in result
        assert '#nonexistent' in result
        # Full page content should still be present
        assert 'Home' in result

    async def test_no_selector_skips_dom_calls(self, snapshot_manager, mock_page):
        """When selector is None, no DOM calls are made (existing behavior)."""
        cdp = _get_cdp(mock_page)
        cdp.send = AsyncMock(return_value={'nodes': self.FULL_PAGE_NODES})

        result = await snapshot_manager.capture(mock_page, 'sess-1')

        # Only Accessibility.getFullAXTree should be called, no DOM methods
        calls = [call.args[0] for call in cdp.send.call_args_list]
        assert 'DOM.enable' not in calls
        assert 'DOM.querySelector' not in calls
        assert 'Accessibility.queryAXTree' not in calls
        assert 'Home' in result

    async def test_dom_error_falls_back(self, snapshot_manager, mock_page):
        """When CDP DOM calls fail, falls back to full page capture."""
        cdp = _get_cdp(mock_page)

        async def failing_dispatcher(method, params=None):
            if method == 'DOM.enable':
                raise Exception('DOM not supported')
            if method == 'DOM.disable':
                return {}
            if method == 'Accessibility.getFullAXTree':
                return {'nodes': self.FULL_PAGE_NODES}
            return {}

        cdp.send = AsyncMock(side_effect=failing_dispatcher)

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        # Should fall back gracefully — warning prefix + full page content
        assert 'Warning' in result
        assert 'Home' in result

    async def test_partial_ax_tree_failure_falls_back(self, snapshot_manager, mock_page):
        """When queryAXTree fails, falls back to full page with warning."""
        cdp = _get_cdp(mock_page)
        cdp.send = AsyncMock(side_effect=self._make_cdp_dispatcher(partial_error=True))

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Warning' in result
        assert 'failed to scope' in result
        # Full page content should still be present
        assert 'Home' in result
        assert 'Action' in result
        # Verify fallback used getFullAXTree
        calls = [call.args[0] for call in cdp.send.call_args_list]
        assert 'Accessibility.queryAXTree' in calls
        assert 'Accessibility.getFullAXTree' in calls

    async def test_scoped_snapshot_empty_formatted_fallback(self, snapshot_manager, mock_page):
        """Empty formatted scoped snapshot falls back to full tree."""
        cdp = _get_cdp(mock_page)
        # queryAXTree returns nodes that are all generic (skipped roles)
        generic_nodes = [
            _node(10, 'generic', '', parent_id=None),
            _node(11, 'generic', '', parent_id=10),
        ]
        cdp.send = AsyncMock(
            side_effect=self._make_cdp_dispatcher(
                partial_nodes=generic_nodes,
            )
        )

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Warning' in result
        assert 'empty accessibility subtree' in result
        # Full page content should be present from fallback
        assert 'Home' in result

    async def test_scoped_snapshot_fallback_cdp_error(self, snapshot_manager, mock_page):
        """Fallback CDP error returns warning prefix only."""
        cdp = _get_cdp(mock_page)
        generic_nodes = [
            _node(10, 'generic', '', parent_id=None),
        ]
        call_count = [0]

        async def dispatcher(method, params=None):
            if method == 'DOM.enable':
                return {}
            if method == 'DOM.disable':
                return {}
            if method == 'DOM.getDocument':
                return {'root': {'nodeId': 1}}
            if method == 'DOM.querySelector':
                return {'nodeId': 42}
            if method == 'DOM.describeNode':
                return {'node': {'backendNodeId': 20}}
            if method == 'Accessibility.queryAXTree':
                return {'nodes': generic_nodes}
            if method == 'Accessibility.getFullAXTree':
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception('CDP session detached')
                return {'nodes': self.FULL_PAGE_NODES}
            return {}

        cdp.send = AsyncMock(side_effect=dispatcher)

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Warning' in result

    async def test_queryAXTree_empty_nodes_falls_back(self, snapshot_manager, mock_page):
        """QueryAXTree returning empty nodes falls back to full tree."""
        cdp = _get_cdp(mock_page)
        cdp.send = AsyncMock(side_effect=self._make_cdp_dispatcher(partial_nodes=[]))

        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Warning' in result
        assert 'empty accessibility subtree' in result
        assert 'Home' in result


class TestFormatCdpNode:
    """Tests for _format_cdp_node edge cases."""

    def test_format_cdp_node_missing_node(self, snapshot_manager):
        """_format_cdp_node returns early when node_id not in node_map."""
        lines = []
        snapshot_manager._format_cdp_node(
            'nonexistent', {}, {}, lines, indent=0, session_id='sess-1'
        )
        assert lines == []

    def test_format_node_non_dict_value(self, snapshot_manager):
        """Node with non-dict value is handled without error."""
        node = {
            'nodeId': '1',
            'role': {'value': 'textbox'},
            'name': {'value': 'Input'},
            'properties': [],
            'value': 'plain_string',
        }
        lines = []
        snapshot_manager._ref_counters = {'sess-1': 0}
        snapshot_manager._ref_maps = {'sess-1': {}}
        snapshot_manager._nth_counters = {'sess-1': {}}
        snapshot_manager._format_cdp_node(
            '1', {'1': node}, {}, lines, indent=0, session_id='sess-1'
        )
        assert len(lines) == 1
        assert 'textbox' in lines[0]
        assert 'value=' not in lines[0]

    def test_format_node_unrecognized_property(self, snapshot_manager):
        """Node with an unrecognized property name does not include it in output."""
        node = {
            'nodeId': '1',
            'role': {'value': 'button'},
            'name': {'value': 'OK'},
            'properties': [
                {'name': 'unknown_prop', 'value': {'type': 'string', 'value': 'foo'}},
            ],
        }
        lines = []
        snapshot_manager._ref_counters = {'sess-1': 0}
        snapshot_manager._ref_maps = {'sess-1': {}}
        snapshot_manager._nth_counters = {'sess-1': {}}
        snapshot_manager._format_cdp_node(
            '1', {'1': node}, {}, lines, indent=0, session_id='sess-1'
        )
        assert len(lines) == 1
        assert 'unknown_prop' not in lines[0]
        assert 'ref=e1' in lines[0]

    def test_format_node_no_children_no_properties(self, snapshot_manager):
        """Node with no children and no properties formats correctly."""
        node = {
            'nodeId': '1',
            'role': {'value': 'button'},
            'name': {'value': 'Submit'},
            'properties': [],
        }
        lines = []
        snapshot_manager._ref_counters = {'sess-1': 0}
        snapshot_manager._ref_maps = {'sess-1': {}}
        snapshot_manager._nth_counters = {'sess-1': {}}
        snapshot_manager._format_cdp_node(
            '1', {'1': node}, {}, lines, indent=0, session_id='sess-1'
        )
        assert len(lines) == 1
        assert 'button "Submit"' in lines[0]
        assert 'ref=e1' in lines[0]


class TestScopedSnapshotEdgeCases:
    """Additional edge-case tests for selector-scoped capture."""

    async def test_scoped_fallback_full_tree_no_root(self, snapshot_manager, mock_page):
        """When fallback full tree has no root node, formatted output stays empty."""
        cdp = _get_cdp(mock_page)
        generic_nodes = [_node(10, 'generic', '', parent_id=None)]
        no_root_full_nodes = [
            _node(2, 'button', 'Click', parent_id=1),
            _node(3, 'link', 'Link', parent_id=1),
        ]

        async def dispatcher(method, params=None):
            if method == 'DOM.enable':
                return {}
            if method == 'DOM.disable':
                return {}
            if method == 'DOM.getDocument':
                return {'root': {'nodeId': 1}}
            if method == 'DOM.querySelector':
                return {'nodeId': 42}
            if method == 'DOM.describeNode':
                return {'node': {'backendNodeId': 20}}
            if method == 'Accessibility.queryAXTree':
                return {'nodes': generic_nodes}
            if method == 'Accessibility.getFullAXTree':
                return {'nodes': no_root_full_nodes}
            return {}

        cdp.send = AsyncMock(side_effect=dispatcher)
        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='main')

        assert 'Warning' in result
        assert 'empty accessibility subtree' in result

    async def test_resolve_selector_dom_disable_failure(self, snapshot_manager, mock_page):
        """DOM.disable failure in _resolve_selector is caught silently."""
        cdp = _get_cdp(mock_page)

        async def dispatcher(method, params=None):
            if method == 'DOM.enable':
                return {}
            if method == 'DOM.disable':
                raise Exception('Already detached')
            if method == 'DOM.getDocument':
                return {'root': {'nodeId': 1}}
            if method == 'DOM.querySelector':
                return {'nodeId': 42}
            if method == 'DOM.describeNode':
                return {'node': {'backendNodeId': 20}}
            if method == 'Accessibility.queryAXTree':
                return {
                    'nodes': [_node(1, 'RootWebArea', ''), _node(2, 'button', 'OK', parent_id=1)]
                }
            return {}

        cdp.send = AsyncMock(side_effect=dispatcher)
        result = await snapshot_manager.capture(mock_page, 'sess-1', selector='#btn')

        # Should succeed despite DOM.disable failure
        assert 'button' in result


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
