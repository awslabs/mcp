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

"""Tests for file_validation: validate_read_path, blocked dirs, blocked filenames."""
# ruff: noqa: D101, D102, D103

import os
import pytest
import tempfile
from unittest.mock import patch


class TestInBlockedDir:
    """Tests for _in_blocked_dir — exact match and child path checks."""

    def test_exact_blocked_dir_match(self):
        from awslabs.aws_transform_mcp_server.file_validation import (
            BLOCKED_READ_DIRS,
            _in_blocked_dir,
        )

        for d in BLOCKED_READ_DIRS:
            assert _in_blocked_dir(d) is True

    def test_file_inside_blocked_dir(self):
        from awslabs.aws_transform_mcp_server.file_validation import _in_blocked_dir

        home = os.path.realpath(os.path.expanduser('~'))
        assert _in_blocked_dir(os.path.join(home, '.aws', 'credentials')) is True

    def test_safe_path_not_blocked(self):
        from awslabs.aws_transform_mcp_server.file_validation import _in_blocked_dir

        assert _in_blocked_dir('/tmp/safe_file.txt') is False


class TestValidateReadPath:
    """Tests for validate_read_path — blocked dir and blocked filename branches."""

    def test_blocked_dir_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_read_path

        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_read_path(os.path.join(home, '.aws', 'credentials'))

    def test_blocked_filename_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_read_path

        with tempfile.TemporaryDirectory() as tmpdir:
            blocked_file = os.path.join(tmpdir, '.env')
            with open(blocked_file, 'w') as f:
                f.write('SECRET=abc')
            with pytest.raises(ValueError, match='Blocked filename'):
                validate_read_path(blocked_file)

    def test_valid_path_returns_resolved(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_read_path

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            f.write(b'{}')
            temp_path = f.name

        try:
            result = validate_read_path(temp_path)
            assert result == os.path.realpath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_blocked_dir_logs_warning(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_read_path

        home = os.path.expanduser('~')
        with (
            patch('awslabs.aws_transform_mcp_server.file_validation.logger') as mock_logger,
            pytest.raises(ValueError),
        ):
            validate_read_path(os.path.join(home, '.ssh', 'id_rsa'))
        mock_logger.warning.assert_called_once()

    def test_blocked_filename_logs_warning(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_read_path

        with tempfile.TemporaryDirectory() as tmpdir:
            blocked_file = os.path.join(tmpdir, '.netrc')
            with open(blocked_file, 'w') as f:
                f.write('machine example.com')
            with (
                patch('awslabs.aws_transform_mcp_server.file_validation.logger') as mock_logger,
                pytest.raises(ValueError),
            ):
                validate_read_path(blocked_file)
            mock_logger.warning.assert_called_once()


class TestValidateWritePath:
    """Tests for validate_write_path — path traversal, blocked dirs, base confinement, blocked filenames."""

    def test_traversal_in_filename_stripped(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            downloads = os.path.join(tmpdir, 'downloads')
            os.makedirs(downloads)
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                result = validate_write_path(downloads, '../../etc/passwd')
                assert result == os.path.join(os.path.realpath(downloads), 'passwd')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_deep_traversal_stripped(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            downloads = os.path.join(tmpdir, 'downloads')
            os.makedirs(downloads)
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                # 'authorized_keys' is in BLOCKED_FILENAMES, so this should now raise
                with pytest.raises(ValueError, match='Blocked filename'):
                    validate_write_path(downloads, '../../../../root/.ssh/authorized_keys')
                # Non-blocked filename with deep traversal should still work (basename stripped)
                result = validate_write_path(downloads, '../../../../tmp/safe_file.txt')
                assert result == os.path.join(os.path.realpath(downloads), 'safe_file.txt')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_legitimate_filename_unchanged(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            downloads = os.path.join(tmpdir, 'downloads')
            os.makedirs(downloads)
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                result = validate_write_path(downloads, 'artifact.json')
                assert result == os.path.join(os.path.realpath(downloads), 'artifact.json')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_no_filename_returns_resolved_dir(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                result = validate_write_path(tmpdir)
                assert result == os.path.realpath(tmpdir)
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_blocked_dir_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        home = os.path.expanduser('~')
        with pytest.raises(ValueError):
            validate_write_path(os.path.join(home, '.ssh'), 'authorized_keys')

    def test_blocked_dir_aws_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        home = os.path.expanduser('~')
        with pytest.raises(ValueError):
            validate_write_path(os.path.join(home, '.aws'), 'credentials')

    def test_dotdot_filename_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                with pytest.raises(ValueError, match='Invalid file name'):
                    validate_write_path(tmpdir, '..')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_slash_filename_raises_valueerror(self):
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                with pytest.raises(ValueError, match='Invalid file name'):
                    validate_write_path(tmpdir, '/')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_tilde_expansion_in_save_path(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with pytest.raises(ValueError, match='working directory'):
            validate_write_path('~/.ssh', 'key')

    def test_blocked_dir_logs_warning(self):
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        home = os.path.expanduser('~')
        with (
            patch('awslabs.aws_transform_mcp_server.file_validation.logger') as mock_logger,
            pytest.raises(ValueError),
        ):
            validate_write_path(os.path.join(home, '.ssh'), 'authorized_keys')
        mock_logger.warning.assert_called_once()

    def test_write_outside_allowed_base_raises_valueerror(self):
        """SavePath outside CWD must be rejected — prevents arbitrary file write."""
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with pytest.raises(ValueError, match='working directory'):
            validate_write_path('/etc/cron.d', 'backdoor')

    def test_write_to_home_dir_raises_valueerror(self):
        """Writing to ~ (home directory) must be blocked — not within CWD."""
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with pytest.raises(ValueError, match='working directory'):
            validate_write_path('~', '.bashrc')

    def test_write_to_autostart_raises_valueerror(self):
        """Writing to autostart folder must be blocked."""
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with pytest.raises(ValueError, match='working directory'):
            validate_write_path(os.path.expanduser('~/.config/autostart'), 'evil.desktop')

    def test_blocked_filename_on_write_raises_valueerror(self):
        """Sensitive filenames must be blocked on writes, not just reads."""
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                with pytest.raises(ValueError, match='Blocked filename'):
                    validate_write_path(tmpdir, '.bashrc')
                with pytest.raises(ValueError, match='Blocked filename'):
                    validate_write_path(tmpdir, '.env')
                with pytest.raises(ValueError, match='Blocked filename'):
                    validate_write_path(tmpdir, 'credentials')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_write_within_cwd_allowed(self):
        """Writes within CWD should succeed."""
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                result = validate_write_path(tmpdir, 'artifact.json')
                assert result == os.path.join(os.path.realpath(tmpdir), 'artifact.json')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_write_within_cwd_subdir_allowed(self):
        """Writes to subdirectories of CWD should succeed."""
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'downloads')
            os.makedirs(subdir)
            original_base = file_validation._ALLOWED_WRITE_BASE
            try:
                file_validation._ALLOWED_WRITE_BASE = os.path.realpath(tmpdir)
                result = validate_write_path(subdir, 'output.zip')
                assert result == os.path.join(os.path.realpath(subdir), 'output.zip')
            finally:
                file_validation._ALLOWED_WRITE_BASE = original_base

    def test_write_rejected_when_base_is_filesystem_root(self):
        """When the base is '/', every write is refused with a clear error.

        Regression test for D464432980: if the server is spawned with the
        filesystem root as its working directory, confining to '/' would place
        no bound on writes. Rather than fall back to allowing writes, the
        request is refused and the caller is told to set the write-dir env var.
        """
        from awslabs.aws_transform_mcp_server import file_validation
        from awslabs.aws_transform_mcp_server.file_validation import validate_write_path

        original_base = file_validation._ALLOWED_WRITE_BASE
        try:
            file_validation._ALLOWED_WRITE_BASE = os.sep
            for save_path, name in [
                (os.path.join(os.sep, 'tmp', 'x'), 'artifact.json'),
                ('/etc/cron.d', 'evil.sh'),
                (file_validation._HOME, '.bashrc'),
            ]:
                with pytest.raises(ValueError, match=file_validation.WRITE_BASE_ENV_VAR):
                    validate_write_path(save_path, name)
        finally:
            file_validation._ALLOWED_WRITE_BASE = original_base

    def test_write_base_defaults_to_cwd(self, monkeypatch):
        """Without the env var set, the base is the current working directory."""
        from awslabs.aws_transform_mcp_server import file_validation

        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.delenv(file_validation.WRITE_BASE_ENV_VAR, raising=False)
            monkeypatch.setattr(os, 'getcwd', lambda: tmpdir)
            assert file_validation._resolve_write_base() == os.path.realpath(tmpdir)

    def test_write_base_honors_env_override(self, monkeypatch):
        """An operator-set write dir env var pins the base explicitly."""
        from awslabs.aws_transform_mcp_server import file_validation

        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv(file_validation.WRITE_BASE_ENV_VAR, tmpdir)
            assert file_validation._resolve_write_base() == os.path.realpath(tmpdir)
