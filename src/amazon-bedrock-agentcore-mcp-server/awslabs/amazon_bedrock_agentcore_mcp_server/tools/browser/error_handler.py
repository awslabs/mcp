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

"""Shared error handling for browser tools.

Most browser tools follow the same error recovery pattern: on failure,
capture a snapshot of the current page state so the caller can see
what went wrong and retry with correct refs. These helpers deduplicate
that pattern across tool modules.
"""

from .snapshot_manager import (
    SnapshotManager,
)
from loguru import logger
from playwright.async_api import Page


async def error_with_snapshot(
    error_msg: str,
    page: Page | None,
    session_id: str,
    snapshot_manager: SnapshotManager,
) -> str:
    """Log an error and return it with a snapshot of the current page.

    If page is None (e.g. get_page() itself failed) or the snapshot capture
    fails, returns just the error message.
    """
    logger.error(error_msg)
    if page is None:
        return error_msg
    try:
        snapshot = await snapshot_manager.capture(page, session_id)
        return f'{error_msg}\n\nCurrent page:\n{snapshot}'
    except Exception as snapshot_err:
        logger.warning(
            f'Failed to capture error snapshot for session {session_id}: {snapshot_err}'
        )
        return error_msg


async def safe_capture(
    page: Page | None,
    session_id: str,
    snapshot_manager: SnapshotManager,
) -> str:
    """Capture a snapshot, returning a fallback message if capture fails.

    Use this on the happy path after a successful interaction so that a
    snapshot failure does not mask the fact that the action succeeded.
    """
    if page is None:
        return '[Snapshot unavailable]'
    try:
        return await snapshot_manager.capture(page, session_id)
    except Exception as e:
        logger.warning(f'Snapshot unavailable for session {session_id}: {e}')
        return '[Snapshot unavailable — take a new snapshot to see current page state]'


def ref_not_found_msg(ref: str) -> str:
    """Format a user-friendly error for a missing element ref."""
    return (
        f'Error: ref "{ref}" not found in current page. '
        f'Take a new snapshot or use a ref from below.'
    )
