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

"""Browser interaction tools for clicking, typing, and other element actions."""

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.connection_manager import (
    BrowserConnectionManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    RefNotFoundError,
    SnapshotManager,
)
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.error_handler import (
    error_with_snapshot,
    ref_not_found_msg,
)
from loguru import logger
from mcp.server.fastmcp import Context
from os import getenv
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import Field
from typing import Annotated


INTERACTION_TIMEOUT_MS = int(getenv('BROWSER_INTERACTION_TIMEOUT_MS', '5000'))


async def _wait_for_settled(page: Page, timeout_ms: int = INTERACTION_TIMEOUT_MS) -> None:
    """Wait for the page to settle after an interaction that may trigger navigation.

    Pages restored from the back-forward cache (bfcache) may not re-fire the
    domcontentloaded event, causing wait_for_load_state to hang. This helper
    catches the timeout so interaction tools can proceed to snapshot capture.
    """
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=timeout_ms)
    except PlaywrightTimeoutError:
        logger.debug('wait_for_load_state timed out (likely bfcache page), continuing')


class InteractionTools:
    """Tools for interacting with elements in browser sessions."""

    def __init__(
        self,
        connection_manager: BrowserConnectionManager,
        snapshot_manager: SnapshotManager,
    ):
        """Initialize with shared connection and snapshot managers."""
        self._connection_manager = connection_manager
        self._snapshot_manager = snapshot_manager

    def register(self, mcp):
        """Register interaction tools with the MCP server."""
        mcp.tool(name='browser_click')(self.browser_click)
        mcp.tool(name='browser_type')(self.browser_type)
        mcp.tool(name='browser_fill_form')(self.browser_fill_form)
        mcp.tool(name='browser_select_option')(self.browser_select_option)
        mcp.tool(name='browser_hover')(self.browser_hover)
        mcp.tool(name='browser_press_key')(self.browser_press_key)
        mcp.tool(name='browser_upload_file')(self.browser_upload_file)
        mcp.tool(name='browser_handle_dialog')(self.browser_handle_dialog)

    async def browser_click(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        ref: Annotated[
            str,
            Field(description='Element ref from snapshot (e.g., "e4")'),
        ],
        double_click: Annotated[
            bool,
            Field(description='Double-click instead of single click'),
        ] = False,
        button: Annotated[
            str,
            Field(description='Mouse button: "left", "right", or "middle"'),
        ] = 'left',
    ) -> str:
        """Click an element identified by its accessibility ref.

        Use refs from the most recent browser_snapshot or navigation result.
        If the ref is not found, returns an error with the current page
        snapshot so you can retry with a correct ref.
        """
        logger.info(f'Clicking ref={ref} in session {session_id}')

        page = await self._connection_manager.get_page(session_id)

        try:
            locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)
            if double_click:
                await locator.dblclick(button=button, timeout=INTERACTION_TIMEOUT_MS)
            else:
                await locator.click(button=button, timeout=INTERACTION_TIMEOUT_MS)

            await _wait_for_settled(page)
        except RefNotFoundError:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{ref_not_found_msg(ref)}\n\n{snapshot}'
        except Exception as e:
            return await error_with_snapshot(
                f'Error clicking ref={ref}: {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        action = 'Double-clicked' if double_click else 'Clicked'
        return f'{action} element {ref}\n\n{snapshot}'

    async def browser_type(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        ref: Annotated[
            str,
            Field(description='Element ref from snapshot (e.g., "e2")'),
        ],
        text: Annotated[
            str,
            Field(description='Text to type into the element'),
        ],
        submit: Annotated[
            bool,
            Field(description='Press Enter after typing to submit'),
        ] = False,
        clear_first: Annotated[
            bool,
            Field(description='Clear existing content before typing'),
        ] = True,
    ) -> str:
        """Type text into an element identified by its accessibility ref.

        By default, clears the existing content before typing. Set
        clear_first=False to append to existing text. Set submit=True
        to press Enter after typing.
        """
        logger.info(f'Typing into ref={ref} in session {session_id}')

        page = await self._connection_manager.get_page(session_id)

        try:
            locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)

            if clear_first:
                await locator.clear(timeout=INTERACTION_TIMEOUT_MS)

            await locator.type(text, timeout=INTERACTION_TIMEOUT_MS)

            if submit:
                await locator.press('Enter', timeout=INTERACTION_TIMEOUT_MS)
                await _wait_for_settled(page)

        except RefNotFoundError:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{ref_not_found_msg(ref)}\n\n{snapshot}'
        except Exception as e:
            return await error_with_snapshot(
                f'Error typing into ref={ref}: {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        action = f'Typed "{text}" into element {ref}'
        if submit:
            action += ' and pressed Enter'
        return f'{action}\n\n{snapshot}'

    async def browser_fill_form(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        fields: Annotated[
            list[dict[str, str]],
            Field(
                description=(
                    'List of form fields to fill. Each entry has "ref" (element ref) '
                    'and "value" (text to enter). Example: [{"ref": "e2", "value": "user@example.com"}]'
                )
            ),
        ],
        submit_ref: Annotated[
            str | None,
            Field(description='Ref of the submit button to click after filling all fields'),
        ] = None,
    ) -> str:
        """Fill multiple form fields in one action.

        Clears each field before filling. Optionally clicks a submit button
        after all fields are filled. Returns the page snapshot after completion.
        """
        logger.info(f'Filling {len(fields)} form fields in session {session_id}')

        page = await self._connection_manager.get_page(session_id)
        filled = []

        try:
            for field in fields:
                ref = field.get('ref', '')
                value = field.get('value', '')
                locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)
                await locator.clear(timeout=INTERACTION_TIMEOUT_MS)
                await locator.type(value, timeout=INTERACTION_TIMEOUT_MS)
                filled.append(ref)

            if submit_ref:
                locator = await self._snapshot_manager.resolve_ref(page, submit_ref, session_id)
                await locator.click(timeout=INTERACTION_TIMEOUT_MS)
                await _wait_for_settled(page)

        except RefNotFoundError as e:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'Error: {e}\nFilled {len(filled)}/{len(fields)} fields.\n\n{snapshot}'
        except Exception as e:
            error_msg = f'Error filling form: {e}'
            logger.error(error_msg)
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{error_msg}\nFilled {len(filled)}/{len(fields)} fields.\n\n{snapshot}'

        snapshot = await self._snapshot_manager.capture(page, session_id)
        msg = f'Filled {len(filled)} form field(s)'
        if submit_ref:
            msg += f' and clicked submit ({submit_ref})'
        return f'{msg}\n\n{snapshot}'

    async def browser_select_option(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        ref: Annotated[
            str,
            Field(description='Element ref of the select/combobox element'),
        ],
        value: Annotated[
            str | None,
            Field(description='Option value attribute to select'),
        ] = None,
        label: Annotated[
            str | None,
            Field(description='Visible text label of the option to select'),
        ] = None,
        index: Annotated[
            int | None,
            Field(description='Zero-based index of the option to select'),
        ] = None,
    ) -> str:
        """Select an option from a dropdown or combobox.

        Provide one of: value (option value attribute), label (visible text),
        or index (zero-based position). Returns the page snapshot after selection.
        """
        logger.info(f'Selecting option in ref={ref}, session {session_id}')

        if value is None and label is None and index is None:
            raise ValueError('Provide one of value, label, or index to select an option.')

        page = await self._connection_manager.get_page(session_id)

        try:
            locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)

            if label is not None:
                await locator.select_option(label=label, timeout=INTERACTION_TIMEOUT_MS)
            elif value is not None:
                await locator.select_option(value=value, timeout=INTERACTION_TIMEOUT_MS)
            elif index is not None:
                await locator.select_option(index=index, timeout=INTERACTION_TIMEOUT_MS)

        except RefNotFoundError:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{ref_not_found_msg(ref)}\n\n{snapshot}'
        except Exception as e:
            return await error_with_snapshot(
                f'Error selecting option in ref={ref}: {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        selection = label or value or f'index {index}'
        return f'Selected "{selection}" in element {ref}\n\n{snapshot}'

    async def browser_hover(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        ref: Annotated[
            str,
            Field(description='Element ref to hover over'),
        ],
    ) -> str:
        """Hover over an element identified by its accessibility ref.

        Useful for triggering tooltips, dropdown menus, or hover states.
        Returns the page snapshot after hovering.
        """
        logger.info(f'Hovering over ref={ref} in session {session_id}')

        page = await self._connection_manager.get_page(session_id)

        try:
            locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)
            await locator.hover(timeout=INTERACTION_TIMEOUT_MS)
            await _wait_for_settled(page, timeout_ms=2000)
        except RefNotFoundError:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{ref_not_found_msg(ref)}\n\n{snapshot}'
        except Exception as e:
            return await error_with_snapshot(
                f'Error hovering over ref={ref}: {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        return f'Hovered over element {ref}\n\n{snapshot}'

    async def browser_press_key(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        key: Annotated[
            str,
            Field(
                description=(
                    'Key to press. Examples: "Enter", "Tab", "Escape", "ArrowDown", '
                    '"Control+a", "Meta+c". See Playwright keyboard API for key names.'
                )
            ),
        ],
    ) -> str:
        """Press a keyboard key or key combination.

        Simulates a key press on the page (not a specific element).
        Supports modifier combinations like "Control+a" or "Meta+c".
        Returns the page snapshot after the key press.
        """
        logger.info(f'Pressing key={key} in session {session_id}')

        try:
            page = await self._connection_manager.get_page(session_id)
            await page.keyboard.press(key)
            await _wait_for_settled(page)
        except Exception as e:
            return await error_with_snapshot(
                f'Error pressing key "{key}": {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        return f'Pressed key: {key}\n\n{snapshot}'

    async def browser_upload_file(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        ref: Annotated[
            str,
            Field(description='Element ref of the file input (e.g., "e5")'),
        ],
        paths: Annotated[
            list[str],
            Field(description='List of file paths to upload'),
        ],
    ) -> str:
        """Upload files to a file input element identified by its ref.

        Resolves the ref to a file input locator and sets the specified
        file paths. For cloud AgentCore sessions, paths refer to files
        on the remote VM. For local Playwright connections, paths refer
        to files on the local filesystem.
        """
        logger.info(f'Uploading {len(paths)} file(s) to ref={ref} in session {session_id}')

        page = await self._connection_manager.get_page(session_id)

        try:
            locator = await self._snapshot_manager.resolve_ref(page, ref, session_id)
            await locator.set_input_files(paths, timeout=INTERACTION_TIMEOUT_MS)
        except RefNotFoundError:
            snapshot = await self._snapshot_manager.capture(page, session_id)
            return f'{ref_not_found_msg(ref)}\n\n{snapshot}'
        except Exception as e:
            return await error_with_snapshot(
                f'Error uploading file(s) to ref={ref}: {e}',
                page, session_id, self._snapshot_manager,
            )

        snapshot = await self._snapshot_manager.capture(page, session_id)
        file_names = ', '.join(paths)
        return f'Uploaded file(s) [{file_names}] to element {ref}\n\n{snapshot}'

    async def browser_handle_dialog(
        self,
        ctx: Context,
        session_id: Annotated[
            str,
            Field(description='Browser session identifier'),
        ],
        action: Annotated[
            str,
            Field(description='How to handle dialogs: "accept" or "dismiss"'),
        ] = 'accept',
        prompt_text: Annotated[
            str | None,
            Field(description='Text to enter for prompt dialogs (only used with accept)'),
        ] = None,
    ) -> str:
        """Configure how JavaScript dialogs are handled for a session.

        Sets a persistent handler for JavaScript dialogs (alert, confirm,
        prompt, beforeunload). Once set, all subsequent dialogs in the
        session are automatically accepted or dismissed. Call again to
        change the behavior.
        """
        logger.info(f'Setting dialog handler for session {session_id}: action={action}')

        try:
            await self._connection_manager.set_dialog_handler(
                session_id,
                action=action,
                prompt_text=prompt_text,
            )
        except Exception as e:
            error_msg = f'Error setting dialog handler for session {session_id}: {e}'
            logger.error(error_msg)
            return error_msg

        msg = f'Dialog handler set: {action}'
        if prompt_text and action == 'accept':
            msg += f' with text "{prompt_text}"'
        msg += (
            f'\nAll subsequent dialogs in session {session_id} will be automatically {action}ed.'
        )
        return msg
