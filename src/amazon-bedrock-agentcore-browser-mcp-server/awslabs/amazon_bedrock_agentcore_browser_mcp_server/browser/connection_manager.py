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

"""Manages Playwright CDP connections to AgentCore browser sessions."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.utils.aws_client import (
    get_browser_client,
)
from collections.abc import Callable
from loguru import logger
from playwright.async_api import Browser, Dialog, Page, Playwright, async_playwright


class BrowserConnectionManager:
    """Manages Playwright CDP connections to remote browser sessions.

    Maintains a mapping of session_id to Playwright Browser instances.
    Each browser is connected via CDP to an AgentCore automation stream
    using SigV4-signed WebSocket connections via the bedrock-agentcore SDK.
    """

    def __init__(self):
        """Initialize the connection manager."""
        self._connections: dict[str, Browser] = {}
        self._playwright: Playwright | None = None
        self._dialog_handlers: dict[str, Callable] = {}
        self._active_pages: dict[str, Page] = {}

    async def _ensure_playwright(self) -> Playwright:
        """Start Playwright if not already running."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            logger.info('Playwright instance started')
        return self._playwright

    async def connect(
        self,
        session_id: str,
        browser_identifier: str,
        region: str = 'us-east-1',
    ) -> Browser:
        """Connect Playwright to a remote browser via CDP.

        Uses the bedrock-agentcore SDK to generate SigV4-signed WebSocket
        headers and the automation stream URL, then establishes a CDP
        connection.

        Args:
            session_id: AgentCore browser session identifier.
            browser_identifier: AgentCore browser resource identifier.
            region: AWS region for SigV4 signing.

        Returns:
            Connected Playwright Browser instance.
        """
        if session_id in self._connections:
            logger.warning(f'Session {session_id} already connected, disconnecting first')
            await self.disconnect(session_id)

        pw = await self._ensure_playwright()

        # Use the SDK to generate the signed WebSocket URL and headers
        client = get_browser_client(region)
        client.identifier = browser_identifier
        client.session_id = session_id
        ws_url, headers = client.generate_ws_headers()

        browser = await pw.chromium.connect_over_cdp(
            ws_url,
            headers=headers,
        )
        self._connections[session_id] = browser
        logger.info(f'Connected to browser session {session_id}')
        return browser

    async def get_page(self, session_id: str) -> Page:
        """Get the active page for a session.

        Returns the explicitly set active page if one exists and is still open,
        otherwise falls back to the last page in the browser context.

        Args:
            session_id: AgentCore browser session identifier.

        Returns:
            The active page for the session.

        Raises:
            ValueError: If no connection or page exists for the session.
        """
        browser = self._connections.get(session_id)
        if not browser:
            raise ValueError(
                f'No connection for session {session_id}. Call start_browser_session first.'
            )
        contexts = browser.contexts
        if not contexts or not contexts[0].pages:
            raise ValueError(f'No page available for session {session_id}')

        active = self._active_pages.get(session_id)
        if active and active in contexts[0].pages:
            return active
        return contexts[0].pages[-1]

    def set_active_page(self, session_id: str, page: Page) -> None:
        """Set the active page for a session.

        Called by tab management to track which page subsequent tools should use.

        Args:
            session_id: AgentCore browser session identifier.
            page: The Playwright Page to make active.
        """
        self._active_pages[session_id] = page

    def is_connected(self, session_id: str) -> bool:
        """Check if a session has an active Playwright connection."""
        return session_id in self._connections

    async def set_dialog_handler(
        self,
        session_id: str,
        action: str = 'accept',
        prompt_text: str | None = None,
    ) -> None:
        """Set a persistent dialog handler for a session.

        Registers a page event listener that automatically handles
        JavaScript dialogs (alert, confirm, prompt, beforeunload).

        Args:
            session_id: Browser session identifier.
            action: "accept" or "dismiss".
            prompt_text: Text to enter for prompt dialogs (only used with accept).
        """
        page = await self.get_page(session_id)

        # Remove any existing handler first
        await self.remove_dialog_handler(session_id)

        async def handler(dialog: Dialog) -> None:
            logger.info(
                f'Handling {dialog.type} dialog in session {session_id}: "{dialog.message}"'
            )
            if action == 'accept':
                await dialog.accept(prompt_text or '')
            else:
                await dialog.dismiss()

        page.on('dialog', handler)
        self._dialog_handlers[session_id] = handler
        logger.info(f'Dialog handler set for session {session_id}: action={action}')

    async def remove_dialog_handler(self, session_id: str) -> None:
        """Remove the dialog handler for a session if one exists."""
        handler = self._dialog_handlers.pop(session_id, None)
        if handler:
            try:
                page = await self.get_page(session_id)
                page.remove_listener('dialog', handler)
            except ValueError:
                pass  # Session may already be disconnected

    async def disconnect(self, session_id: str) -> None:
        """Disconnect Playwright from a browser session.

        Args:
            session_id: AgentCore browser session identifier.
        """
        await self.remove_dialog_handler(session_id)
        self._active_pages.pop(session_id, None)
        browser = self._connections.pop(session_id, None)
        if browser:
            try:
                await browser.close()
                logger.info(f'Disconnected from browser session {session_id}')
            except Exception as e:
                logger.warning(f'Error closing browser for session {session_id}: {e}')

    async def cleanup(self) -> None:
        """Disconnect all sessions and stop Playwright."""
        for session_id in list(self._connections):
            try:
                await self.disconnect(session_id)
            except Exception as e:
                logger.error(f'Error disconnecting session {session_id} during cleanup: {e}')
        if self._playwright:
            try:
                await self._playwright.stop()
                logger.info('Playwright instance stopped')
            except Exception as e:
                logger.error(f'Error stopping Playwright: {e}')
            finally:
                self._playwright = None
