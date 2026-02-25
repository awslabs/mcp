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

"""Accessibility tree snapshot capture and ref system.

Captures the page's accessibility tree via CDP's Accessibility.getFullAXTree,
assigns sequential refs (e1, e2, ...) to interactable elements, and formats
as YAML-like text for LLM consumption.
"""

import asyncio
from loguru import logger
from playwright.async_api import Locator, Page


class RefNotFoundError(Exception):
    """Raised when a ref cannot be resolved to an element."""


# Roles that receive refs for interaction
INTERACTABLE_ROLES = frozenset(
    {
        'button',
        'checkbox',
        'combobox',
        'link',
        'menuitem',
        'menuitemcheckbox',
        'menuitemradio',
        'option',
        'radio',
        'searchbox',
        'slider',
        'spinbutton',
        'switch',
        'tab',
        'textbox',
        'treeitem',
    }
)

# Roles to skip entirely (noise in output)
SKIP_ROLES = frozenset(
    {
        'InlineTextBox',
        'StaticText',
        'none',
        'generic',
    }
)


class SnapshotManager:
    """Captures accessibility tree snapshots with element refs.

    Uses CDP's Accessibility.getFullAXTree to get the accessibility tree,
    which works reliably over CDP connections (including remote AgentCore
    sessions). The ref system maps short identifiers (e1, e2, ...) to
    element metadata for interaction via get_by_role locators.
    """

    def __init__(self):
        """Initialize the snapshot manager."""
        self._ref_counters: dict[str, int] = {}
        self._ref_maps: dict[str, dict[str, dict]] = {}
        self._nth_counters: dict[str, dict[tuple[str, str], int]] = {}
        self._previous_snapshots: dict[str, str] = {}

    async def capture(self, page: Page, session_id: str) -> str:
        """Capture the accessibility tree and return formatted text.

        Uses CDP Accessibility.getFullAXTree for reliable access over
        remote CDP connections (page.accessibility was removed in
        Playwright 1.42+).

        Args:
            page: Playwright Page to snapshot.
            session_id: Browser session identifier for scoping refs.

        Returns:
            YAML-like text representation of the accessibility tree.
        """
        try:
            cdp = await page.context.new_cdp_session(page)
            try:
                result = await asyncio.wait_for(
                    cdp.send('Accessibility.getFullAXTree'),
                    timeout=30.0,
                )
            finally:
                await cdp.detach()
        except Exception as e:
            logger.error(f'Failed to capture accessibility snapshot: {e}')
            return f'[Error capturing accessibility tree: {e}]'

        nodes = result.get('nodes', [])
        if not nodes:
            return '[Empty page - no accessibility tree available]'

        self._ref_counters[session_id] = 0
        self._ref_maps[session_id] = {}
        self._nth_counters[session_id] = {}

        # Build parent→children map from flat node list
        node_map = {}
        children_map: dict[str, list[str]] = {}
        root_id = None

        for node in nodes:
            nid = node.get('nodeId', '')
            node_map[nid] = node
            parent_id = node.get('parentId')
            if parent_id:
                children_map.setdefault(parent_id, []).append(nid)
            else:
                root_id = nid

        if not root_id:
            return '[No root node in accessibility tree]'

        lines: list[str] = []
        self._format_cdp_node(
            root_id, node_map, children_map, lines, indent=0, session_id=session_id
        )
        formatted = '\n'.join(lines)
        self._previous_snapshots[session_id] = formatted

        logger.debug(f'Captured snapshot with {self._ref_counters[session_id]} refs')
        return formatted

    def _format_cdp_node(
        self,
        node_id: str,
        node_map: dict,
        children_map: dict[str, list[str]],
        lines: list[str],
        indent: int,
        session_id: str = '',
    ) -> None:
        """Recursively format a CDP accessibility tree node.

        Args:
            node_id: CDP node ID.
            node_map: Map of node ID to node dict.
            children_map: Map of parent ID to child IDs.
            lines: Accumulator for output lines.
            indent: Current indentation level.
            session_id: Browser session identifier for scoping refs.
        """
        node = node_map.get(node_id)
        if not node:
            return

        # Skip ignored nodes but process their children
        if node.get('ignored'):
            for child_id in children_map.get(node_id, []):
                self._format_cdp_node(child_id, node_map, children_map, lines, indent, session_id)
            return

        role = node.get('role', {}).get('value', '')
        name = node.get('name', {}).get('value', '')
        child_ids = children_map.get(node_id, [])

        # Skip noise roles but process their children
        if role in SKIP_ROLES:
            for child_id in child_ids:
                self._format_cdp_node(child_id, node_map, children_map, lines, indent, session_id)
            return

        # Skip root WebArea, just process children
        if role == 'RootWebArea':
            for child_id in child_ids:
                self._format_cdp_node(child_id, node_map, children_map, lines, indent, session_id)
            return

        # Build the line
        prefix = '  ' * indent + '- '
        parts = [role]

        if name:
            display_name = name[:80] + '...' if len(name) > 80 else name
            parts.append(f'"{display_name}"')

        # Assign ref to interactable elements
        ref = None
        if role in INTERACTABLE_ROLES:
            self._ref_counters[session_id] = self._ref_counters.get(session_id, 0) + 1
            ref = f'e{self._ref_counters[session_id]}'

            # Track nth occurrence of this role+name combo for disambiguation
            role_name_key = (role, name)
            nth_map = self._nth_counters.setdefault(session_id, {})
            nth = nth_map.get(role_name_key, 0)
            nth_map[role_name_key] = nth + 1

            self._ref_maps.setdefault(session_id, {})[ref] = {
                'role': role,
                'name': name,
                'nth': nth,
            }

        line = prefix + ' '.join(parts)

        # Extract properties
        props_list = []
        if ref:
            props_list.append(f'ref={ref}')

        for prop in node.get('properties', []):
            prop_name = prop.get('name', '')
            prop_val = prop.get('value', {}).get('value')
            if prop_name == 'checked' and prop_val is not None:
                props_list.append(f'checked={prop_val}')
            elif prop_name == 'disabled' and prop_val:
                props_list.append('disabled')
            elif prop_name == 'expanded' and prop_val is not None:
                props_list.append(f'expanded={prop_val}')
            elif prop_name == 'pressed' and prop_val is not None:
                props_list.append(f'pressed={prop_val}')
            elif prop_name == 'selected' and prop_val:
                props_list.append('selected')
            elif prop_name == 'required' and prop_val:
                props_list.append('required')
            elif prop_name == 'level' and prop_val is not None:
                props_list.append(f'level={prop_val}')

        # Check for value
        value_info = node.get('value', {})
        if isinstance(value_info, dict):
            val = value_info.get('value')
            if val is not None and val != '':
                display_val = str(val)[:50] + '...' if len(str(val)) > 50 else str(val)
                props_list.append(f'value="{display_val}"')

        if props_list:
            line += ' [' + ', '.join(props_list) + ']'

        lines.append(line)

        # Recurse into children
        for child_id in child_ids:
            self._format_cdp_node(child_id, node_map, children_map, lines, indent + 1, session_id)

    async def resolve_ref(self, page: Page, ref: str, session_id: str) -> Locator:
        """Resolve a ref to a Playwright Locator.

        Args:
            page: Playwright Page to locate elements on.
            ref: Element ref from snapshot (e.g., 'e4').
            session_id: Browser session identifier for scoping refs.

        Returns:
            Playwright Locator for the referenced element.

        Raises:
            RefNotFoundError: If the ref is not in the current ref map.
        """
        ref_map = self._ref_maps.get(session_id, {})
        info = ref_map.get(ref)
        if not info:
            raise RefNotFoundError(
                f'Ref "{ref}" not found. Take a new snapshot to get current refs.'
            )

        role = info['role']
        name = info['name']
        nth = info.get('nth', 0)

        if name:
            locator = page.get_by_role(role, name=name)
        else:
            locator = page.get_by_role(role)

        # Use nth to disambiguate when multiple elements share the same role+name.
        # We check the nth_counters to see if this role+name had more than one
        # occurrence during snapshot capture. If so, apply .nth() even for the
        # first occurrence (nth=0) to avoid Playwright strict mode errors.
        role_name_key = (role, name)
        nth_map = self._nth_counters.get(session_id, {})
        total_occurrences = nth_map.get(role_name_key, 1)
        if total_occurrences > 1:
            locator = locator.nth(nth)

        return locator

    def ref_count(self, session_id: str) -> int:
        """Number of refs in the current snapshot for a session."""
        return self._ref_counters.get(session_id, 0)

    def previous_snapshot(self, session_id: str) -> str | None:
        """The most recently captured snapshot text for a session."""
        return self._previous_snapshots.get(session_id)

    def cleanup_session(self, session_id: str) -> None:
        """Remove all state for a session.

        Call this when a session is stopped to free memory.

        Args:
            session_id: Browser session identifier to clean up.
        """
        self._ref_counters.pop(session_id, None)
        self._ref_maps.pop(session_id, None)
        self._nth_counters.pop(session_id, None)
        self._previous_snapshots.pop(session_id, None)
