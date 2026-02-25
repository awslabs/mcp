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

"""Browser management tools for tabs, viewport, and page lifecycle."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.navigation import (
    NAVIGATION_TIMEOUT_MS,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated


class ManagementTools:
    """Tools for managing browser tabs, viewport, and page lifecycle."""

    def __init__(
        self,
        connection_manager: BrowserConnectionManager,
        snapshot_manager: SnapshotManager,
    ):
        """Initialize with shared connection and snapshot managers."""
        self._connection_manager = connection_manager
        self._snapshot_manager = snapshot_manager

    def register(self, mcp):
        """Register management tools with the MCP server."""
        mcp.tool(name='browser_tabs')(self.browser_tabs)
        mcp.tool(name='browser_close')(self.browser_close)
        mcp.tool(name='browser_resize')(self.browser_resize)

    async def browser_tabs(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        action: Annotated[
            str,
            Field(
                description=(
                    'Tab action to perform: "list" to show all tabs, '
                    '"new" to open a new tab, "select" to switch to a tab by index, '
                    '"close" to close a tab by index.'
                )
            ),
        ] = 'list',
        tab_index: Annotated[
            int | None,
            Field(description='Zero-based tab index for "select" and "close" actions'),
        ] = None,
        url: Annotated[
            str | None,
            Field(description='URL to open in a new tab (for "new" action)'),
        ] = None,
    ) -> str:
        """Manage browser tabs: list, create, select, or close tabs.

        Actions:
        - "list": Show all open tabs with their titles and URLs.
        - "new": Open a new tab, optionally navigating to a URL.
        - "select": Switch the active tab (subsequent tools use this tab).
        - "close": Close a tab by its index.
        """
        logger.info(f'Tab action={action} in session {session_id}')

        try:
            browser = self._connection_manager._connections.get(session_id)
            if not browser:
                return f'Error: No connection for session {session_id}.'

            contexts = browser.contexts
            if not contexts:
                return 'Error: No browser context available.'

            context = contexts[0]
            pages = context.pages

            if action == 'list':
                if not pages:
                    return 'No tabs open.'
                lines = [f'Open tabs ({len(pages)}):']
                for i, page in enumerate(pages):
                    title = await page.title()
                    lines.append(f'  [{i}] {title} - {page.url}')
                return '\n'.join(lines)

            elif action == 'new':
                new_page = await context.new_page()
                try:
                    if url:
                        await new_page.goto(
                            url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT_MS
                        )
                    self._connection_manager.set_active_page(session_id, new_page)
                    title = await new_page.title()
                    return f'Opened new tab [{len(pages)}]: {title} - {new_page.url}'
                except Exception:
                    await new_page.close()
                    raise

            elif action == 'select':
                if tab_index is None:
                    return 'Error: Provide tab_index for "select" action.'
                if tab_index < 0 or tab_index >= len(pages):
                    return f'Error: tab_index {tab_index} out of range (0-{len(pages) - 1}).'
                await pages[tab_index].bring_to_front()
                self._connection_manager.set_active_page(session_id, pages[tab_index])
                title = await pages[tab_index].title()
                snapshot = await self._snapshot_manager.capture(pages[tab_index], session_id)
                return f'Switched to tab [{tab_index}]: {title}\n\n{snapshot}'

            elif action == 'close':
                if tab_index is None:
                    return 'Error: Provide tab_index for "close" action.'
                if tab_index < 0 or tab_index >= len(pages):
                    return f'Error: tab_index {tab_index} out of range (0-{len(pages) - 1}).'
                if len(pages) <= 1:
                    return 'Error: Cannot close the last tab.'
                title = await pages[tab_index].title()
                await pages[tab_index].close()
                remaining = context.pages
                if remaining:
                    self._connection_manager.set_active_page(session_id, remaining[-1])
                return f'Closed tab [{tab_index}]: {title}. {len(remaining)} tab(s) remaining.'

            else:
                return f'Error: Unknown action "{action}". Use list, new, select, or close.'

        except Exception as e:
            error_msg = f'Error managing tabs in session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_close(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """Close the current page.

        Closes the active page in the browser session. If multiple tabs
        are open, subsequent tools will use the remaining tab. Use
        stop_browser_session to fully terminate the session.
        """
        logger.info(f'Closing current page in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            title = await page.title()
            url = page.url
            await page.close()

            browser = self._connection_manager._connections.get(session_id)
            if browser and browser.contexts and browser.contexts[0].pages:
                self._connection_manager.set_active_page(session_id, browser.contexts[0].pages[-1])

            return f'Closed page: {title} ({url})'

        except Exception as e:
            error_msg = f'Error closing page in session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_resize(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        width: Annotated[
            int,
            Field(description='New viewport width in pixels'),
        ],
        height: Annotated[
            int,
            Field(description='New viewport height in pixels'),
        ],
    ) -> str:
        """Resize the browser viewport.

        Changes the viewport dimensions of the active page. Useful for
        testing responsive layouts or viewing content at different sizes.
        Returns the page snapshot at the new size.
        """
        logger.info(f'Resizing viewport to {width}x{height} in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            await page.set_viewport_size({'width': width, 'height': height})

        except Exception as e:
            error_msg = f'Error resizing viewport in session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

        snapshot = await self._snapshot_manager.capture(page, session_id)
        return f'Viewport resized to {width}x{height}\n\n{snapshot}'
