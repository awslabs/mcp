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

"""Browser navigation tools."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)
from loguru import logger
from mcp.server.fastmcp import Context
from os import getenv
from pydantic import Field
from typing import Annotated


NAVIGATION_TIMEOUT_MS = int(getenv('BROWSER_NAVIGATION_TIMEOUT_MS', '30000'))


class NavigationTools:
    """Tools for navigating in browser sessions."""

    def __init__(
        self,
        connection_manager: BrowserConnectionManager,
        snapshot_manager: SnapshotManager,
    ):
        """Initialize with shared connection and snapshot managers."""
        self._connection_manager = connection_manager
        self._snapshot_manager = snapshot_manager

    def register(self, mcp):
        """Register navigation tools with the MCP server."""
        mcp.tool(name='browser_navigate')(self.browser_navigate)
        mcp.tool(name='browser_navigate_back')(self.browser_navigate_back)
        mcp.tool(name='browser_navigate_forward')(self.browser_navigate_forward)

    async def browser_navigate(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        url: Annotated[
            str,
            Field(description='URL to navigate to'),
        ],
    ) -> str:
        """Navigate to a URL in the browser.

        Loads the specified URL and returns an accessibility tree snapshot
        of the loaded page. Use the element refs in the snapshot for
        subsequent interaction tools.
        """
        logger.info(f'Navigating session {session_id} to {url}')

        try:
            page = await self._connection_manager.get_page(session_id)
            response = await page.goto(
                url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT_MS
            )

            status = response.status if response else 'unknown'
            title = await page.title()
            final_url = page.url
            snapshot = await self._snapshot_manager.capture(page, session_id)

            return f'Navigated to {final_url}\nTitle: {title}\nStatus: {status}\n\n{snapshot}'

        except Exception as e:
            error_msg = f'Error navigating to {url}: {e}'
            logger.error(error_msg)
            try:
                snapshot = await self._snapshot_manager.capture(page, session_id)
                return f'{error_msg}\n\nCurrent page:\n{snapshot}'
            except Exception:
                return error_msg

    async def browser_navigate_back(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """Navigate back in browser history.

        Returns an accessibility tree snapshot of the previous page.
        """
        logger.info(f'Navigating back in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            await page.go_back(wait_until='commit', timeout=NAVIGATION_TIMEOUT_MS)

            title = await page.title()
            final_url = page.url
            snapshot = await self._snapshot_manager.capture(page, session_id)

            return f'Navigated back to {final_url}\nTitle: {title}\n\n{snapshot}'

        except Exception as e:
            error_msg = f'Error navigating back in session {session_id}: {e}'
            logger.error(error_msg)
            try:
                snapshot = await self._snapshot_manager.capture(page, session_id)
                return f'{error_msg}\n\nCurrent page:\n{snapshot}'
            except Exception:
                return error_msg

    async def browser_navigate_forward(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """Navigate forward in browser history.

        Returns an accessibility tree snapshot of the next page.
        """
        logger.info(f'Navigating forward in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            await page.go_forward(wait_until='commit', timeout=NAVIGATION_TIMEOUT_MS)

            title = await page.title()
            final_url = page.url
            snapshot = await self._snapshot_manager.capture(page, session_id)

            return f'Navigated forward to {final_url}\nTitle: {title}\n\n{snapshot}'

        except Exception as e:
            error_msg = f'Error navigating forward in session {session_id}: {e}'
            logger.error(error_msg)
            try:
                snapshot = await self._snapshot_manager.capture(page, session_id)
                return f'{error_msg}\n\nCurrent page:\n{snapshot}'
            except Exception:
                return error_msg
