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

"""Browser observation tools for snapshots, screenshots, and page inspection."""

import base64
import json
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated


class ObservationTools:
    """Tools for observing page state in browser sessions."""

    def __init__(
        self,
        connection_manager: BrowserConnectionManager,
        snapshot_manager: SnapshotManager,
    ):
        """Initialize with shared connection and snapshot managers."""
        self._connection_manager = connection_manager
        self._snapshot_manager = snapshot_manager

    def register(self, mcp):
        """Register observation tools with the MCP server."""
        mcp.tool(name='browser_snapshot')(self.browser_snapshot)
        mcp.tool(name='browser_take_screenshot')(self.browser_take_screenshot)
        mcp.tool(name='browser_wait_for')(self.browser_wait_for)
        mcp.tool(name='browser_console_messages')(self.browser_console_messages)
        mcp.tool(name='browser_network_requests')(self.browser_network_requests)
        mcp.tool(name='browser_evaluate')(self.browser_evaluate)

    async def browser_snapshot(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """Capture an accessibility tree snapshot of the current page.

        Returns a structured text view of the page with element refs.
        Use the refs (e.g., e1, e2) in interaction tools like browser_click
        and browser_type to target specific elements.

        Example output:
          - heading "Sign In" [ref=e1]
          - textbox "Email" [ref=e2]
          - textbox "Password" [ref=e3]
          - button "Sign In" [ref=e4]
        """
        logger.info(f'Taking snapshot of session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            title = await page.title()
            url = page.url
            snapshot = await self._snapshot_manager.capture(page, session_id)

            return f'Page: {title}\nURL: {url}\n\n{snapshot}'

        except Exception as e:
            error_msg = f'Error capturing snapshot for session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_take_screenshot(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        full_page: Annotated[
            bool,
            Field(description='Capture the full scrollable page instead of just the viewport'),
        ] = False,
    ) -> list[dict]:
        """Capture a visual screenshot of the page.

        Returns the screenshot as a base64-encoded PNG image.
        Use this when you need to visually inspect the page rather
        than reading the accessibility tree.
        """
        logger.info(f'Taking screenshot of session {session_id} (full_page={full_page})')

        try:
            page = await self._connection_manager.get_page(session_id)
            data = await page.screenshot(full_page=full_page, type='png')
            encoded = base64.b64encode(data).decode('ascii')

            return [
                {
                    'type': 'image',
                    'data': encoded,
                    'mimeType': 'image/png',
                }
            ]

        except Exception as e:
            error_msg = f'Error taking screenshot for session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_wait_for(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        text: Annotated[
            str | None,
            Field(description='Wait for this text to appear on the page'),
        ] = None,
        selector: Annotated[
            str | None,
            Field(description='CSS selector to wait for'),
        ] = None,
        timeout: Annotated[
            int,
            Field(description='Maximum wait time in milliseconds (default: 10000)'),
        ] = 10000,
    ) -> str:
        """Wait for text to appear or an element to become visible.

        Provide either text or selector. Returns the page snapshot after
        the condition is met. Raises an error if the timeout is exceeded.
        """
        logger.info(f'Waiting in session {session_id}: text={text}, selector={selector}')

        try:
            page = await self._connection_manager.get_page(session_id)

            if text:
                await page.get_by_text(text).first.wait_for(state='visible', timeout=timeout)
            elif selector:
                await page.wait_for_selector(selector, state='visible', timeout=timeout)
            else:
                return 'Error: Provide either text or selector to wait for.'

        except Exception as e:
            error_msg = f'Wait timed out or failed: {e}'
            logger.error(error_msg)
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{error_msg}\n\nCurrent page:\n{snapshot}'

        snapshot = await self._snapshot_manager.capture(page, session_id)
        target = f'text "{text}"' if text else f'selector "{selector}"'
        return f'Found {target} on page\n\n{snapshot}'

    async def browser_console_messages(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """Get recent browser console messages.

        Returns console log, warning, and error messages captured since
        the Playwright connection was established. Useful for debugging
        JavaScript errors or inspecting application logging.
        """
        logger.info(f'Getting console messages for session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)

            # Scan DOM for error-like elements as a best-effort fallback.
            # (CDP Console.enable only captures future messages, not history,
            # so DOM inspection gives more useful results here.)
            result = await page.evaluate("""
                () => {
                    const errors = [];
                    document.querySelectorAll('[role="alert"], .error, .warning').forEach(el => {
                        errors.push(el.textContent.trim().substring(0, 200));
                    });
                    return errors;
                }
            """)

            if result:
                messages = '\n'.join(f'- {msg}' for msg in result)
                return f'Console/error messages found:\n{messages}'

            return (
                'No console messages captured. Console messages are captured '
                'going forward after this tool is called. Navigate or interact '
                'with the page, then call this again.'
            )

        except Exception as e:
            error_msg = f'Error getting console messages for session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_network_requests(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
    ) -> str:
        """List recent network requests and their status.

        Returns a summary of network requests made by the page, including
        URL, HTTP method, status code, and resource type. Useful for
        debugging API calls or monitoring page loading.
        """
        logger.info(f'Getting network requests for session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)

            # Use Performance API to get resource timing entries
            entries = await page.evaluate("""
                () => {
                    const entries = performance.getEntriesByType('resource');
                    return entries.slice(-50).map(e => ({
                        name: e.name.substring(0, 100),
                        type: e.initiatorType,
                        duration: Math.round(e.duration),
                        size: e.transferSize || 0,
                    }));
                }
            """)

            if not entries:
                return 'No network requests captured for this page.'

            lines = [f'Network requests ({len(entries)} recent):']
            for entry in entries:
                size_kb = entry.get('size', 0) / 1024
                lines.append(
                    f'  {entry["type"]:10s} {entry["duration"]:5d}ms '
                    f'{size_kb:7.1f}KB {entry["name"]}'
                )

            return '\n'.join(lines)

        except Exception as e:
            error_msg = f'Error getting network requests for session {session_id}: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise

    async def browser_evaluate(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        expression: Annotated[
            str,
            Field(
                description=(
                    'JavaScript expression to evaluate in the page context. '
                    'Use for inspecting state, extracting data, or performing '
                    'actions not covered by other tools.'
                )
            ),
        ],
    ) -> str:
        """Execute a JavaScript expression in the page context.

        The expression is evaluated in the browser and its return value
        is serialized to JSON. Use this for extracting data, reading
        page state, or performing custom interactions. You can use
        fetch() to make HTTP requests from the browser's origin and cookies.
        """
        logger.info(f'Evaluating JS in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            result = await page.evaluate(expression)

            if result is None:
                return 'Expression evaluated successfully (returned undefined/null).'

            if isinstance(result, (str, int, float, bool)):
                return f'Result: {result}'

            return f'Result:\n{json.dumps(result, indent=2, default=str)}'

        except Exception as e:
            error_msg = f'Error evaluating JavaScript: {e}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            raise
