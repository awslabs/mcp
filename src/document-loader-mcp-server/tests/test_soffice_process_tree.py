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
"""Tests that the soffice process tree is stopped on timeout or cancel (#5104).

These tests run a fake ``soffice`` that starts a child process and then sleeps,
the way a launcher starts ``soffice.bin``, and check that no process from the
call is left once the call has timed out or been cancelled.
"""

import asyncio
import os
import pytest
import subprocess
import sys
import tempfile
import threading
import time
from awslabs.document_loader_mcp_server import server
from awslabs.document_loader_mcp_server.server import (
    WorkCancelledError,
    _CancelToken,
    _convert_to_pdf_with_soffice,
    _extract_slides_sync,
    _run_with_timeout,
)
from pathlib import Path
from unittest.mock import MagicMock


WAIT_SECONDS = 10

# Runs in place of soffice. In "hang" mode it starts a child, records both pids,
# and sleeps. In "convert" mode it writes the PDF soffice would write. In "fail"
# mode it exits with an error.
FAKE_SOFFICE = """
import os
import subprocess
import sys
import time

mode = os.environ['FAKE_SOFFICE_MODE']
if mode == 'hang':
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
    with open(os.environ['FAKE_SOFFICE_PIDS'] + '.tmp', 'w') as f:
        f.write(f'{os.getpid()} {child.pid}')
    os.replace(os.environ['FAKE_SOFFICE_PIDS'] + '.tmp', os.environ['FAKE_SOFFICE_PIDS'])
    time.sleep(120)
elif mode == 'convert':
    args = sys.argv[1:]
    outdir = args[args.index('--outdir') + 1]
    source = args[args.index('--convert-to') + 2]
    stem = os.path.splitext(os.path.basename(source))[0]
    with open(os.path.join(outdir, stem + '.pdf'), 'w') as f:
        f.write('fake pdf')
else:
    sys.stderr.write('conversion failed')
    sys.exit(3)
"""


def _pid_alive(pid: int) -> bool:
    if sys.platform == 'win32':
        out = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/NH', '/FO', 'CSV'],
            capture_output=True,
            text=True,
        ).stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        # A process that has exited but is not yet reaped still answers kill(0).
        with open(f'/proc/{pid}/stat') as f:
            return f.read().rsplit(')', 1)[1].split()[0] != 'Z'
    except OSError:
        return True


def _force_kill(pid: int) -> None:
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _wait_until(condition, timeout=WAIT_SECONDS) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


@pytest.fixture
def fake_soffice(tmp_path, monkeypatch):
    """Install a fake soffice and return the file its pids are written to."""
    script = tmp_path / 'fake_soffice.py'
    script.write_text(FAKE_SOFFICE)
    if sys.platform == 'win32':
        launcher = tmp_path / 'soffice.cmd'
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\r\n')
    else:
        launcher = tmp_path / 'soffice'
        launcher.write_text(f'#!/bin/sh\n"{sys.executable}" "{script}" "$@"\n')
        launcher.chmod(0o755)
    pids_file = tmp_path / 'pids'
    monkeypatch.setattr(server, '_find_soffice', lambda: str(launcher))
    monkeypatch.setenv('FAKE_SOFFICE_PIDS', str(pids_file))
    monkeypatch.setenv('FAKE_SOFFICE_MODE', 'hang')
    yield pids_file
    # Never leave a fake process behind, even if the test failed.
    if pids_file.exists():
        for pid in pids_file.read_text().split():
            _force_kill(int(pid))


def _read_pids(pids_file: Path) -> list:
    assert _wait_until(pids_file.exists), 'fake soffice did not start'
    return [int(p) for p in pids_file.read_text().split()]


def test_timeout_stops_soffice_process_tree(fake_soffice, tmp_path):
    """After the soffice timeout, neither soffice nor the process it started is left."""
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _convert_to_pdf_with_soffice(str(tmp_path / 'in.pptx'), str(tmp_path), timeout_seconds=3)
    assert time.monotonic() - started < 30
    for pid in _read_pids(fake_soffice):
        assert _wait_until(lambda pid=pid: not _pid_alive(pid)), f'process {pid} is still running'


def test_cancel_stops_soffice_process_tree(fake_soffice, tmp_path):
    """A cancelled call stops soffice and its child at once, not at the soffice timeout."""
    cancel = _CancelToken()
    errors = []

    def convert():
        try:
            _convert_to_pdf_with_soffice(
                str(tmp_path / 'in.pptx'), str(tmp_path), timeout_seconds=60, cancel=cancel
            )
        except BaseException as e:
            errors.append(e)

    worker = threading.Thread(target=convert)
    worker.start()
    pids = _read_pids(fake_soffice)
    assert all(_pid_alive(pid) for pid in pids)
    cancel.cancel()
    worker.join(WAIT_SECONDS)
    assert not worker.is_alive(), 'the conversion did not stop after cancel'
    assert len(errors) == 1 and isinstance(errors[0], WorkCancelledError)
    for pid in pids:
        assert _wait_until(lambda pid=pid: not _pid_alive(pid)), f'process {pid} is still running'


@pytest.mark.asyncio
async def test_tool_cancel_stops_soffice_and_removes_temp_dir(fake_soffice, tmp_path, monkeypatch):
    """When the tool call is cancelled, no process from it is left and its temp folder is gone."""
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))
    monkeypatch.setenv('DOCUMENT_BASE_DIR', str(tmp_path))
    out_dir = tmp_path / 'out'
    out_dir.mkdir()

    task = asyncio.ensure_future(
        _run_with_timeout(
            _extract_slides_sync,
            str(tmp_path / 'in.pptx'),
            str(out_dir),
            200,
            'png',
            60,
            timeout_seconds=60,
        )
    )
    pids = await asyncio.get_running_loop().run_in_executor(None, _read_pids, fake_soffice)
    assert list(scratch.glob('docloader_soffice_*'))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    def stopped():
        return not any(_pid_alive(pid) for pid in pids) and not list(
            scratch.glob('docloader_soffice_*')
        )

    assert await asyncio.get_running_loop().run_in_executor(None, _wait_until, stopped), (
        'soffice processes or the temp folder are still present after the call was cancelled'
    )


def test_normal_conversion_is_unchanged(fake_soffice, tmp_path, monkeypatch):
    """A conversion that finishes returns the PDF path, with or without a cancel token."""
    monkeypatch.setenv('FAKE_SOFFICE_MODE', 'convert')
    source = tmp_path / 'deck.pptx'
    for cancel in (None, _CancelToken()):
        result = _convert_to_pdf_with_soffice(
            str(source), str(tmp_path), timeout_seconds=30, cancel=cancel
        )
        assert result == str(tmp_path / 'deck.pdf')
        assert (tmp_path / 'deck.pdf').read_text() == 'fake pdf'


def test_failed_conversion_still_raises_called_process_error(fake_soffice, tmp_path, monkeypatch):
    """A non-zero soffice exit still raises CalledProcessError with its stderr."""
    monkeypatch.setenv('FAKE_SOFFICE_MODE', 'fail')
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        _convert_to_pdf_with_soffice(str(tmp_path / 'in.pptx'), str(tmp_path), timeout_seconds=30)
    assert excinfo.value.returncode == 3
    assert b'conversion failed' in excinfo.value.stderr


def test_windows_stops_process_tree_with_taskkill(monkeypatch, tmp_path):
    """On Windows the whole tree is stopped with taskkill /T, and soffice gets its own group."""
    monkeypatch.setattr(server, '_find_soffice', lambda: 'C:/soffice.exe')
    monkeypatch.setattr(sys, 'platform', 'win32')
    # subprocess.CREATE_NEW_PROCESS_GROUP only exists on Windows; raising=False keeps this test portable.
    monkeypatch.setattr(server.subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200, raising=False)
    monkeypatch.setenv('SystemRoot', 'C:\\Windows')
    cancel = _CancelToken()
    proc = MagicMock(pid=4321, returncode=None)

    def communicate(timeout=None):
        if not communicate.called:
            communicate.called = True
            cancel.cancel()  # the call is cancelled while soffice is still running
            raise subprocess.TimeoutExpired('soffice', timeout)
        return (b'', b'')

    communicate.called = False
    proc.communicate.side_effect = communicate
    popen = MagicMock(return_value=proc)
    run = MagicMock()
    monkeypatch.setattr(server.subprocess, 'Popen', popen)
    monkeypatch.setattr(server.subprocess, 'run', run)

    with pytest.raises(WorkCancelledError):
        _convert_to_pdf_with_soffice('in.pptx', str(tmp_path), timeout_seconds=30, cancel=cancel)

    assert popen.call_args.kwargs['creationflags'] == 0x00000200  # CREATE_NEW_PROCESS_GROUP
    assert run.call_args.args[0] == [
        'C:\\Windows\\System32\\taskkill.exe',
        '/F',
        '/T',
        '/PID',
        '4321',
    ]


def test_kill_process_tree_falls_back_to_killing_soffice(monkeypatch):
    """If the tree cannot be killed, soffice itself is still killed and reaped."""
    monkeypatch.setattr(sys, 'platform', 'win32')
    proc = MagicMock(pid=4321, returncode=None)
    proc.communicate.side_effect = subprocess.TimeoutExpired('soffice', 1)
    proc.wait.side_effect = subprocess.TimeoutExpired('soffice', 1)
    monkeypatch.setattr(server.subprocess, 'run', MagicMock(side_effect=OSError('no taskkill')))

    server._kill_process_tree(proc)

    proc.kill.assert_called_once_with()
    proc.wait.assert_called_once()


def test_posix_stops_process_group_with_killpg(monkeypatch, tmp_path):
    """On POSIX soffice gets its own session and the whole group is killed."""
    monkeypatch.setattr(server, '_find_soffice', lambda: '/usr/bin/soffice')
    monkeypatch.setattr(sys, 'platform', 'linux')
    # raising=False so the test also runs on platforms without these names.
    killpg = MagicMock()
    monkeypatch.setattr(os, 'killpg', killpg, raising=False)
    monkeypatch.setattr(server.signal, 'SIGKILL', 9, raising=False)
    cancel = _CancelToken()
    proc = MagicMock(pid=4321, returncode=None)

    def communicate(timeout=None):
        if not communicate.called:
            communicate.called = True
            cancel.cancel()  # the call is cancelled while soffice is still running
            raise subprocess.TimeoutExpired('soffice', timeout)
        return (b'', b'')

    communicate.called = False
    proc.communicate.side_effect = communicate
    popen = MagicMock(return_value=proc)
    monkeypatch.setattr(server.subprocess, 'Popen', popen)

    with pytest.raises(WorkCancelledError):
        _convert_to_pdf_with_soffice('in.pptx', str(tmp_path), timeout_seconds=30, cancel=cancel)

    assert popen.call_args.kwargs['start_new_session'] is True
    assert popen.call_args.kwargs['creationflags'] == 0
    killpg.assert_called_once_with(4321, 9)


def test_taskkill_is_run_from_the_system_directory(monkeypatch):
    """taskkill.exe is resolved under SystemRoot, never from the working directory or PATH."""
    monkeypatch.setenv('SystemRoot', 'D:\\Win')
    assert server._taskkill_path() == 'D:\\Win\\System32\\taskkill.exe'
    monkeypatch.delenv('SystemRoot')
    monkeypatch.delenv('windir', raising=False)
    assert server._taskkill_path() == 'C:\\Windows\\System32\\taskkill.exe'


@pytest.mark.parametrize('platform', ['win32', 'linux'])
def test_kill_process_tree_does_not_signal_a_reaped_process(monkeypatch, platform):
    """Once the process is reaped its pid may belong to someone else, so nothing is signalled."""
    monkeypatch.setattr(sys, 'platform', platform)
    killpg = MagicMock()
    monkeypatch.setattr(os, 'killpg', killpg, raising=False)
    run = MagicMock()
    monkeypatch.setattr(server.subprocess, 'run', run)
    proc = MagicMock(pid=4321, returncode=0)
    proc.communicate.return_value = (b'', b'')

    server._kill_process_tree(proc)

    killpg.assert_not_called()
    run.assert_not_called()
