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
"""Tests that a tool's work stops once its timeout has fired (#5083)."""

import asyncio
import pytest
import threading
from awslabs.document_loader_mcp_server import server
from awslabs.document_loader_mcp_server.server import (
    WorkCancelledError,
    _CancelToken,
    _extract_pdf_text_sync,
    _extract_slides_sync,
    _run_with_timeout,
)
from PIL import Image as PILImage
from unittest.mock import MagicMock, patch


WAIT_SECONDS = 5


@pytest.fixture
def base_dir(tmp_path, monkeypatch):
    """Use a temporary directory as DOCUMENT_BASE_DIR."""
    monkeypatch.setenv('DOCUMENT_BASE_DIR', str(tmp_path))
    return tmp_path


@pytest.fixture(params=['fd', 'path'])
def write_mode(request, monkeypatch):
    """Run a test with directory-descriptor writes and with the path fallback."""
    if request.param == 'fd' and not server._supports_fd_relative_writes():
        pytest.skip('directory-descriptor writes are not supported on this platform')
    if request.param == 'path':
        monkeypatch.setattr(server, '_supports_fd_relative_writes', lambda: False)
    return request.param


def _pages(count):
    return [PILImage.new('RGB', (8, 8), 'white') for _ in range(count)]


class _BlockingWrites:
    """Wraps _write_slide so a chosen write blocks until the test releases it."""

    def __init__(self, block_on):
        self.block_on = block_on
        self.started = []
        self.blocked = threading.Event()
        self.release = threading.Event()
        self._real_write = server._write_slide

    def __call__(self, page, name, *args, **kwargs):
        self.started.append(name)
        if len(self.started) == self.block_on:
            self.blocked.set()
            assert self.release.wait(WAIT_SECONDS)
        return self._real_write(page, name, *args, **kwargs)


def test_cancel_token_check_raises_after_cancel():
    """check() passes until the token is cancelled."""
    token = _CancelToken()
    token.check()

    assert token.cancel() is True
    with pytest.raises(WorkCancelledError):
        token.check()


def test_cancel_token_finish_wins_over_later_cancel():
    """A worker that finished first keeps its result."""
    token = _CancelToken()
    token.finish()

    assert token.cancel() is False
    token.check()


def test_cancel_token_finish_raises_after_cancel():
    """A worker cannot report success after its call was cancelled."""
    token = _CancelToken()
    token.cancel()

    with pytest.raises(WorkCancelledError):
        token.finish()


@pytest.mark.asyncio
async def test_run_with_timeout_returns_result():
    """Work that finishes in time returns its result."""

    def work(value, cancel):
        cancel.check()
        return value * 2

    assert await _run_with_timeout(work, 21, timeout_seconds=WAIT_SECONDS) == 42


@pytest.mark.asyncio
async def test_run_with_timeout_propagates_worker_error():
    """An error raised by the work reaches the caller."""

    def work(cancel):
        raise ValueError('bad input')

    with pytest.raises(ValueError, match='bad input'):
        await _run_with_timeout(work, timeout_seconds=WAIT_SECONDS)


@pytest.mark.asyncio
async def test_run_with_timeout_stops_worker_at_next_checkpoint():
    """After the timeout fires, the worker stops at its next checkpoint."""
    release = threading.Event()
    stopped = threading.Event()
    steps = []

    def work(cancel):
        try:
            for step in range(3):
                cancel.check()
                steps.append(step)
                assert release.wait(WAIT_SECONDS)
        except WorkCancelledError:
            stopped.set()
            raise

    with pytest.raises(asyncio.TimeoutError):
        await _run_with_timeout(work, timeout_seconds=0.05)
    release.set()

    assert await asyncio.to_thread(stopped.wait, WAIT_SECONDS)
    assert steps == [0]


@pytest.mark.asyncio
async def test_run_with_timeout_keeps_result_finished_as_timeout_fires():
    """Work that finished before the cancel took effect is returned, not discarded."""
    release = threading.Event()

    def work(cancel):
        cancel.finish()
        assert release.wait(WAIT_SECONDS)
        return 'done'

    task = asyncio.ensure_future(_run_with_timeout(work, timeout_seconds=0.05))
    await asyncio.sleep(0.2)
    release.set()

    assert await task == 'done'


@pytest.mark.asyncio
async def test_run_with_timeout_cancels_worker_when_caller_is_cancelled():
    """Cancelling the tool call also stops the worker."""
    started = threading.Event()
    release = threading.Event()
    stopped = threading.Event()

    def work(cancel):
        started.set()
        assert release.wait(WAIT_SECONDS)
        try:
            cancel.check()
        except WorkCancelledError:
            stopped.set()
            raise

    task = asyncio.ensure_future(_run_with_timeout(work, timeout_seconds=WAIT_SECONDS))
    assert await asyncio.to_thread(started.wait, WAIT_SECONDS)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()

    assert await asyncio.to_thread(stopped.wait, WAIT_SECONDS)


@pytest.mark.asyncio
async def test_no_slide_is_written_after_timeout_fires(base_dir, write_mode):
    """Once the timeout has fired, no further slide is written and none are left behind."""
    out = base_dir / 'out'
    writes = _BlockingWrites(block_on=2)
    finished = threading.Event()

    def extract(*args, cancel):
        try:
            return _extract_slides_sync(*args, cancel=cancel)
        finally:
            finished.set()

    with (
        patch.object(server, 'convert_from_path', return_value=_pages(5)),
        patch.object(server, '_write_slide', writes),
    ):
        with pytest.raises(asyncio.TimeoutError):
            await _run_with_timeout(
                extract, '/docs/deck.pdf', str(out), 72, 'png', timeout_seconds=0.2
            )
        # The timeout has fired while slide 2 is being written.
        assert writes.blocked.is_set()
        writes.release.set()
        assert await asyncio.to_thread(finished.wait, WAIT_SECONDS)

    assert writes.started == ['slide_1.png', 'slide_2.png']
    assert list(out.iterdir()) == []


@pytest.mark.asyncio
async def test_tool_timeout_leaves_no_slides(base_dir, write_mode):
    """End to end: the tool reports a timeout and the output directory holds no slides."""
    deck = base_dir / 'deck.pdf'
    PILImage.new('RGB', (40, 20), 'white').save(deck)
    out = base_dir / 'out'
    writes = _BlockingWrites(block_on=2)
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}
    ctx = MagicMock()
    ctx.error = MagicMock(side_effect=lambda message: asyncio.sleep(0))

    with (
        patch.object(server, 'convert_from_path', return_value=_pages(5)),
        patch.object(server, '_write_slide', writes),
    ):
        result = await tools['extract_slides_as_images'].fn(ctx, str(deck), str(out), 72, 0.2)
        writes.release.set()
        for _ in range(100):
            if not list(out.iterdir()):
                break
            await asyncio.sleep(0.05)

    assert result.status == 'error'
    assert result.slide_count == 0
    assert 'timed out' in result.error_message
    assert writes.started == ['slide_1.png', 'slide_2.png']
    assert list(out.iterdir()) == []


def test_cancelled_before_start_writes_nothing(base_dir, write_mode):
    """A call cancelled before the worker starts does no conversion and writes nothing."""
    out = base_dir / 'out'
    token = _CancelToken()
    token.cancel()

    with patch.object(server, 'convert_from_path') as mock_convert:
        with pytest.raises(WorkCancelledError):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png', cancel=token)

    mock_convert.assert_not_called()
    assert not out.exists()


def test_poppler_step_gets_the_tool_timeout(base_dir):
    """The poppler step is bounded by the same timeout as the tool call."""
    out = base_dir / 'out'

    with patch.object(server, 'convert_from_path', return_value=_pages(1)) as mock_convert:
        _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png', 45)

    mock_convert.assert_called_once_with('/docs/deck.pdf', dpi=72, timeout=45)


def test_pdf_text_extraction_stops_between_pages():
    """PDF text extraction stops at the next page once cancelled."""
    token = _CancelToken()
    extracted = []

    def extract_text(number):
        extracted.append(number)
        if number == 2:
            token.cancel()
        return f'page {number}'

    pages = [
        MagicMock(extract_text=MagicMock(side_effect=lambda n=n: extract_text(n)))
        for n in (1, 2, 3)
    ]
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = pages

    with patch.object(server.pdfplumber, 'open', return_value=pdf):
        with pytest.raises(WorkCancelledError):
            _extract_pdf_text_sync('/docs/report.pdf', cancel=token)

    assert extracted == [1, 2]
