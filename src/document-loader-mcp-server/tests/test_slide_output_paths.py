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
"""Regression tests for how extract_slides_as_images writes slide files.

Slides must be written only inside the resolved output directory under
DOCUMENT_BASE_DIR. Existing symlinks at slide paths are refused, and links
swapped in after validation are never followed.
"""

import io
import os
import pytest
import stat
from awslabs.document_loader_mcp_server import server
from awslabs.document_loader_mcp_server.server import (
    UnsafeOutputPathError,
    _extract_slides_sync,
    _is_link_or_reparse_point,
    _supports_fd_relative_writes,
    validate_output_dir,
)
from PIL import Image as PILImage
from tests.test_server import call_mcp_tool_slides
from types import SimpleNamespace
from unittest.mock import patch


ORIGINAL = b'ORIGINAL CONTENT\n'
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def _pages(count=2):
    """Return small in-memory page images, as convert_from_path would."""
    colors = ['white', 'black', 'red', 'blue']
    return [PILImage.new('RGB', (40, 20), colors[i % len(colors)]) for i in range(count)]


def _png_bytes(page):
    buf = io.BytesIO()
    page.save(buf, 'PNG')
    return buf.getvalue()


def _require_symlinks(tmp_path):
    """Skip the test if this OS or user cannot create symlinks."""
    probe = tmp_path / 'symlink_probe'
    try:
        os.symlink(tmp_path, probe, target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip('symlinks are not supported here')
    probe.unlink()


def _temp_leftovers(directory):
    return [p.name for p in directory.iterdir() if p.name.startswith('.docloader_slide_')]


WRITE_MODES = ['fd', 'path']


@pytest.fixture(params=WRITE_MODES)
def write_mode(request):
    """Run each test with directory-descriptor writes and with the path fallback."""
    if request.param == 'fd' and not _supports_fd_relative_writes():
        pytest.skip('directory-relative no-follow writes not supported here')
    if request.param == 'path':
        with patch.object(server, '_supports_fd_relative_writes', return_value=False):
            yield request.param
    else:
        yield request.param


@pytest.fixture
def sandbox(tmp_path):
    """A resolved base directory and a sibling directory outside it."""
    root = tmp_path.resolve()
    base = root / 'base'
    outside = root / 'outside'
    base.mkdir()
    outside.mkdir()
    with patch.dict(os.environ, {'DOCUMENT_BASE_DIR': str(base)}):
        yield SimpleNamespace(root=root, base=base, outside=outside)


def test_preexisting_slide_symlink_outside_is_refused(sandbox, write_mode):
    """A slide_1.png link to an outside file is refused and the file is unchanged."""
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    out.mkdir()
    outside_file = sandbox.outside / 'outside.txt'
    outside_file.write_bytes(ORIGINAL)
    (out / 'slide_1.png').symlink_to(outside_file)

    assert validate_output_dir(str(out)) is None
    with patch.object(server, 'convert_from_path', return_value=_pages(2)):
        with pytest.raises(UnsafeOutputPathError, match='slide_1.png'):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')

    assert outside_file.read_bytes() == ORIGINAL
    assert (out / 'slide_1.png').is_symlink()
    # Targets are checked before any write, so no partial set is left behind.
    assert not (out / 'slide_2.png').exists()
    assert _temp_leftovers(out) == []


def test_preexisting_slide_symlink_inside_base_is_refused(sandbox, write_mode):
    """Links are refused even when they point inside the base directory."""
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    out.mkdir()
    other = sandbox.base / 'notes.txt'
    other.write_bytes(ORIGINAL)
    (out / 'slide_2.png').symlink_to(other)

    with patch.object(server, 'convert_from_path', return_value=_pages(2)):
        with pytest.raises(UnsafeOutputPathError):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert other.read_bytes() == ORIGINAL
    assert not (out / 'slide_1.png').exists()


@pytest.mark.asyncio
async def test_tool_returns_error_for_slide_symlink(sandbox, write_mode):
    """End to end: the tool returns an error response and writes nothing outside."""
    _require_symlinks(sandbox.root)
    deck = sandbox.base / 'deck.pdf'
    PILImage.new('RGB', (40, 20), 'white').save(deck)
    out = sandbox.base / 'out'
    out.mkdir()
    outside_file = sandbox.outside / 'outside.txt'
    outside_file.write_bytes(ORIGINAL)
    (out / 'slide_1.png').symlink_to(outside_file)

    with patch.object(server, 'convert_from_path', return_value=_pages(1)):
        result = await call_mcp_tool_slides(str(deck), str(out))

    assert result.status == 'error'
    assert result.error_message is not None
    assert 'Access denied' in result.error_message
    assert result.slide_images == []
    assert result.slide_count == 0
    assert outside_file.read_bytes() == ORIGINAL


def test_output_dir_swapped_to_symlink_after_validation(sandbox, write_mode):
    """The output directory replaced by a link after validation is not written through."""
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    out.mkdir()
    assert validate_output_dir(str(out)) is None

    out.rmdir()
    out.symlink_to(sandbox.outside, target_is_directory=True)

    with patch.object(server, 'convert_from_path', return_value=_pages(2)):
        with pytest.raises(UnsafeOutputPathError):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(sandbox.outside.iterdir()) == []


def test_parent_dir_swapped_to_symlink_after_validation(sandbox, write_mode):
    """A parent of the output directory replaced by a link is not written through."""
    _require_symlinks(sandbox.root)
    parent = sandbox.base / 'project'
    out = parent / 'out'
    out.mkdir(parents=True)
    assert validate_output_dir(str(out)) is None

    out.rmdir()
    parent.rmdir()
    (sandbox.outside / 'out').mkdir()
    parent.symlink_to(sandbox.outside, target_is_directory=True)

    with patch.object(server, 'convert_from_path', return_value=_pages(2)):
        with pytest.raises(UnsafeOutputPathError):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list((sandbox.outside / 'out').iterdir()) == []


def test_dir_swapped_after_internal_resolution_is_not_followed(sandbox, write_mode):
    """A link swapped in after the internal resolve and re-check is still refused.

    Simulates the race by having the resolve step return the pre-swap path.
    """
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    out.symlink_to(sandbox.outside, target_is_directory=True)

    with patch.object(server, '_resolve_output_dir', return_value=(sandbox.base, out)):
        with patch.object(server, 'convert_from_path', return_value=_pages(2)):
            with pytest.raises(UnsafeOutputPathError):
                _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(sandbox.outside.iterdir()) == []


def test_slide_link_swapped_after_check_is_replaced_not_followed(sandbox, write_mode):
    """A slide link created after the target check is replaced, not followed."""
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    out.mkdir()
    outside_file = sandbox.outside / 'outside.txt'
    outside_file.write_bytes(ORIGINAL)
    (out / 'slide_1.png').symlink_to(outside_file)
    pages = _pages(1)

    with patch.object(server, '_check_slide_target', return_value=None):
        with patch.object(server, 'convert_from_path', return_value=pages):
            result = _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')

    assert result == [os.path.join(str(out), 'slide_1.png')]
    assert outside_file.read_bytes() == ORIGINAL
    assert not (out / 'slide_1.png').is_symlink()
    assert (out / 'slide_1.png').read_bytes() == _png_bytes(pages[0])


def test_output_dir_outside_base_is_refused_without_creating_it(sandbox, write_mode):
    """The internal re-check refuses an outside directory and does not create it."""
    target = sandbox.outside / 'new_out'
    with patch.object(server, 'convert_from_path', return_value=_pages(1)):
        with pytest.raises(UnsafeOutputPathError, match='outside allowed directory'):
            _extract_slides_sync('/docs/deck.pdf', str(target), 72, 'png')
    assert not target.exists()


def test_normal_extraction_output_unchanged(sandbox, write_mode):
    """Normal path: same names, PNG content, and return value as before."""
    out = sandbox.base / 'nested' / 'out'
    pages = _pages(3)

    with patch.object(server, 'convert_from_path', return_value=pages) as mock_convert:
        result = _extract_slides_sync('/docs/deck.pdf', str(out), 150, 'png')

    mock_convert.assert_called_once_with('/docs/deck.pdf', dpi=150)
    assert result == [os.path.join(str(out), f'slide_{i}.png') for i in (1, 2, 3)]
    assert sorted(p.name for p in out.iterdir()) == ['slide_1.png', 'slide_2.png', 'slide_3.png']
    for i, page in enumerate(pages, 1):
        data = (out / f'slide_{i}.png').read_bytes()
        assert data.startswith(PNG_MAGIC)
        assert data == _png_bytes(page)


def test_existing_regular_slides_are_overwritten(sandbox, write_mode):
    """Re-running into a folder with regular slide files overwrites them as before."""
    out = sandbox.base / 'out'
    out.mkdir()
    (out / 'slide_1.png').write_bytes(b'old')
    pages = _pages(1)

    with patch.object(server, 'convert_from_path', return_value=pages):
        _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert (out / 'slide_1.png').read_bytes() == _png_bytes(pages[0])
    assert _temp_leftovers(out) == []


def test_symlinked_output_dir_inside_base_still_works(sandbox, write_mode):
    """An output_dir link that resolves inside the base keeps working."""
    _require_symlinks(sandbox.root)
    real = sandbox.base / 'real'
    real.mkdir()
    alias = sandbox.base / 'alias'
    alias.symlink_to(real, target_is_directory=True)

    with patch.object(server, 'convert_from_path', return_value=_pages(1)):
        result = _extract_slides_sync('/docs/deck.pdf', str(alias), 72, 'png')
    assert result == [os.path.join(str(alias), 'slide_1.png')]
    assert (real / 'slide_1.png').read_bytes().startswith(PNG_MAGIC)


@pytest.mark.asyncio
async def test_tool_success_response_unchanged(sandbox, write_mode):
    """End to end: the success response format is unchanged."""
    deck = sandbox.base / 'deck.pdf'
    PILImage.new('RGB', (40, 20), 'white').save(deck)
    out = sandbox.base / 'out'

    with patch.object(server, 'convert_from_path', return_value=_pages(2)):
        result = await call_mcp_tool_slides(str(deck), str(out))

    assert result.status == 'success'
    assert result.error_message is None
    assert result.slide_count == 2
    assert result.output_dir == str(out)
    assert result.file_path == str(deck)
    assert result.slide_images == [os.path.join(str(out), f'slide_{i}.png') for i in (1, 2)]


class _FailingPage:
    """A page whose save writes partial data and then fails."""

    def save(self, fp, fmt):
        fp.write(b'partial')
        raise OSError('disk full')


def test_temp_files_removed_when_save_fails(sandbox, write_mode):
    """A failed save leaves no temp file and no partial slide behind."""
    out = sandbox.base / 'out'
    out.mkdir()

    with patch.object(server, 'convert_from_path', return_value=[_FailingPage()]):
        with pytest.raises(OSError, match='disk full'):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(out.iterdir()) == []


def test_temp_files_removed_when_replace_fails(sandbox, write_mode):
    """A failed move onto the final name leaves no temp file behind."""
    out = sandbox.base / 'out'
    out.mkdir()

    with patch.object(server.os, 'replace', side_effect=OSError('replace failed')):
        with patch.object(server, 'convert_from_path', return_value=_pages(1)):
            with pytest.raises(OSError, match='replace failed'):
                _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(out.iterdir()) == []


def test_temp_files_removed_when_later_slide_fails(sandbox, write_mode):
    """A failure on a later slide leaves no temp files."""
    out = sandbox.base / 'out'
    out.mkdir()

    with patch.object(server, 'convert_from_path', return_value=[_pages(1)[0], _FailingPage()]):
        with pytest.raises(OSError):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert _temp_leftovers(out) == []


def test_failed_extraction_removes_slides_already_written(sandbox, write_mode):
    """A failure on a later slide also removes the slides this call already wrote."""
    out = sandbox.base / 'out'
    out.mkdir()

    with patch.object(server, 'convert_from_path', return_value=[*_pages(2), _FailingPage()]):
        with pytest.raises(OSError, match='disk full'):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(out.iterdir()) == []


def test_is_link_or_reparse_point_classification():
    """Symlinks and Windows name-surrogate reparse points are links; others are not."""
    reparse = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
    regular = SimpleNamespace(st_mode=stat.S_IFREG | 0o644)
    symlink = SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)
    junction = SimpleNamespace(
        st_mode=stat.S_IFDIR | 0o777, st_file_attributes=reparse, st_reparse_tag=0xA0000003
    )
    win_symlink = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o644, st_file_attributes=reparse, st_reparse_tag=0xA000000C
    )
    cloud_placeholder = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o644, st_file_attributes=reparse, st_reparse_tag=0x9000001A
    )
    assert _is_link_or_reparse_point(regular) is False  # type: ignore[arg-type]
    assert _is_link_or_reparse_point(symlink) is True  # type: ignore[arg-type]
    assert _is_link_or_reparse_point(junction) is True  # type: ignore[arg-type]
    assert _is_link_or_reparse_point(win_symlink) is True  # type: ignore[arg-type]
    assert _is_link_or_reparse_point(cloud_placeholder) is False  # type: ignore[arg-type]


def test_output_dir_component_is_a_file_raises_os_error(sandbox, write_mode):
    """A regular file in the output path fails with the normal OS error, not a link error."""
    blocker = sandbox.base / 'blocker'
    blocker.write_bytes(ORIGINAL)

    with patch.object(server, 'convert_from_path', return_value=_pages(1)):
        with pytest.raises(OSError) as excinfo:
            _extract_slides_sync('/docs/deck.pdf', str(blocker / 'out'), 72, 'png')
    assert not isinstance(excinfo.value, UnsafeOutputPathError)
    assert blocker.read_bytes() == ORIGINAL


def test_fallback_rechecks_dir_before_each_write(sandbox):
    """In the path fallback, a folder swapped to a link after preparation is refused."""
    _require_symlinks(sandbox.root)
    out = sandbox.base / 'out'
    real_prepare = server._prepare_output_dir_path

    def prepare_then_swap(base_dir, resolved_dir):
        real_prepare(base_dir, resolved_dir)
        resolved_dir.rmdir()
        resolved_dir.symlink_to(sandbox.outside, target_is_directory=True)

    with patch.object(server, '_supports_fd_relative_writes', return_value=False):
        with patch.object(server, '_prepare_output_dir_path', side_effect=prepare_then_swap):
            with patch.object(server, 'convert_from_path', return_value=_pages(2)):
                with pytest.raises(UnsafeOutputPathError):
                    _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    assert list(sandbox.outside.iterdir()) == []


@pytest.mark.skipif(os.name == 'nt', reason='POSIX permission bits')
def test_created_output_dirs_are_not_group_or_world_writable(sandbox, write_mode):
    """New output directories get mode 0o755 even with a permissive umask."""
    out = sandbox.base / 'nested' / 'out'
    old = os.umask(0)
    try:
        with patch.object(server, 'convert_from_path', return_value=_pages(1)):
            _extract_slides_sync('/docs/deck.pdf', str(out), 72, 'png')
    finally:
        os.umask(old)
    for d in (sandbox.base / 'nested', out):
        assert d.stat().st_mode & 0o777 == 0o755
