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
