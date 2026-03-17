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

"""Unit tests for error_handler.py — error_with_snapshot and ref_not_found_msg."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.error_handler import (
    error_with_snapshot,
    ref_not_found_msg,
    safe_capture,
)
from unittest.mock import AsyncMock, MagicMock


class TestErrorWithSnapshot:
    """Tests for error_with_snapshot helper."""

    async def test_error_with_snapshot_includes_snapshot(self):
        """Returns error message with snapshot appended."""
        page = MagicMock()
        sm = MagicMock()
        sm.capture = AsyncMock(return_value='- heading "Test" [level=1]')

        result = await error_with_snapshot('Something failed', page, 'sess-1', sm)

        assert 'Something failed' in result
        assert 'heading "Test"' in result
        sm.capture.assert_awaited_once_with(page, 'sess-1')

    async def test_error_with_snapshot_no_page(self):
        """Returns just the error message when page is None."""
        sm = MagicMock()
        sm.capture = AsyncMock()

        result = await error_with_snapshot('No page error', None, 'sess-1', sm)

        assert result == 'No page error'
        sm.capture.assert_not_awaited()

    async def test_error_with_snapshot_capture_fails(self):
        """Returns just the error message when snapshot capture raises."""
        page = MagicMock()
        sm = MagicMock()
        sm.capture = AsyncMock(side_effect=Exception('CDP disconnected'))

        result = await error_with_snapshot('Tool failed', page, 'sess-1', sm)

        assert result == 'Tool failed'


class TestSafeCapture:
    """Tests for safe_capture helper."""

    async def test_safe_capture_returns_snapshot(self):
        """Returns snapshot text when capture succeeds."""
        page = MagicMock()
        sm = MagicMock()
        sm.capture = AsyncMock(return_value='- button "OK" [ref=e1]')

        result = await safe_capture(page, 'sess-1', sm)

        assert result == '- button "OK" [ref=e1]'
        sm.capture.assert_awaited_once_with(page, 'sess-1')

    async def test_safe_capture_no_page(self):
        """Returns fallback when page is None."""
        sm = MagicMock()
        sm.capture = AsyncMock()

        result = await safe_capture(None, 'sess-1', sm)

        assert 'unavailable' in result.lower()
        sm.capture.assert_not_awaited()

    async def test_safe_capture_capture_fails(self):
        """Returns fallback message when snapshot capture raises."""
        page = MagicMock()
        sm = MagicMock()
        sm.capture = AsyncMock(side_effect=Exception('CDP timeout'))

        result = await safe_capture(page, 'sess-1', sm)

        assert 'unavailable' in result.lower()
        assert 'new snapshot' in result.lower()


class TestRefNotFoundMsg:
    """Tests for ref_not_found_msg helper."""

    def test_ref_not_found_msg(self):
        """Returns user-friendly message with ref value."""
        msg = ref_not_found_msg('btn42')
        assert 'btn42' in msg
        assert 'not found' in msg
