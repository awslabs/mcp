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
# ruff: noqa: D101, D102, D103
"""Tests for the path_validation module."""

import importlib
import os
import pytest
from awslabs.eks_mcp_server import path_validation
from awslabs.eks_mcp_server.path_validation import (
    BLOCKED_DIRS,
    validate_directory_path,
    validate_file_path,
)


class TestValidateFilePath:
    def test_rejects_relative_path(self):
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_file_path('relative/path/template.yaml')

    def test_rejects_path_in_aws_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, '.aws', 'template.yaml'))

    def test_rejects_path_in_ssh_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, '.ssh', 'config.yaml'))

    def test_rejects_path_in_kube_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, '.kube', 'config.yaml'))

    def test_rejects_path_in_gnupg_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, '.gnupg', 'keys.yaml'))

    def test_rejects_path_in_docker_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, '.docker', 'config.json'))

    def test_rejects_path_in_etc(self):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path('/etc/cron.d/manifest.yaml')

    def test_rejects_path_in_root(self):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path('/root/template.yaml')

    def test_rejects_symlink_to_sensitive_dir(self, tmp_path):
        home = os.path.expanduser('~')
        aws_dir = os.path.join(home, '.aws')
        link_path = tmp_path / 'link.yaml'
        # Create a symlink pointing into ~/.aws
        target = os.path.join(aws_dir, 'template.yaml')
        link_path.symlink_to(target)

        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(str(link_path))

    def test_accepts_valid_absolute_path(self):
        result = validate_file_path('/tmp/projects/manifest.yaml')
        assert result == os.path.realpath('/tmp/projects/manifest.yaml')

    def test_returns_resolved_path(self):
        result = validate_file_path('/tmp/../tmp/projects/manifest.yaml')
        assert result == os.path.realpath('/tmp/projects/manifest.yaml')

    def test_blocked_dirs_use_realpath(self):
        for d in BLOCKED_DIRS:
            assert os.path.realpath(d) == d


class TestValidateDirectoryPath:
    def test_rejects_relative_path(self):
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_directory_path('relative/path')

    def test_rejects_path_in_aws_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(os.path.join(home, '.aws'))

    def test_rejects_path_in_ssh_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(os.path.join(home, '.ssh'))

    def test_rejects_path_in_kube_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(os.path.join(home, '.kube'))

    def test_rejects_subdirectory_of_sensitive_dir(self):
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(os.path.join(home, '.aws', 'subdir'))

    def test_rejects_etc(self):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path('/etc')

    def test_rejects_etc_subdir(self):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path('/etc/cron.d')

    def test_rejects_root_home(self):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path('/root')

    def test_rejects_symlink_to_sensitive_dir(self, tmp_path):
        home = os.path.expanduser('~')
        aws_dir = os.path.join(home, '.aws')
        link_path = tmp_path / 'link-dir'
        # Create a symlink pointing to ~/.aws
        link_path.symlink_to(aws_dir)

        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(str(link_path))

    def test_accepts_tmp_directory(self):
        result = validate_directory_path('/tmp/manifests')
        assert result == os.path.realpath('/tmp/manifests')

    def test_accepts_home_project_directory(self):
        home = os.path.expanduser('~')
        result = validate_directory_path(os.path.join(home, 'projects', 'my-app'))
        assert result == os.path.realpath(os.path.join(home, 'projects', 'my-app'))

    def test_does_not_check_extensions(self):
        result = validate_directory_path('/tmp/my-output')
        assert result == os.path.realpath('/tmp/my-output')

    def test_returns_resolved_path(self):
        result = validate_directory_path('/tmp/../tmp/output')
        assert result == os.path.realpath('/tmp/output')


class TestCaseInsensitiveFileSystems:
    """On macOS and Windows, a recased spelling names the same directory."""

    @pytest.fixture
    def case_insensitive(self, monkeypatch):
        monkeypatch.setattr(path_validation, '_CASE_INSENSITIVE_FS', True)

    @pytest.fixture
    def case_sensitive(self, monkeypatch):
        monkeypatch.setattr(path_validation, '_CASE_INSENSITIVE_FS', False)

    @pytest.mark.parametrize(
        'sensitive_dir, recased', [('.aws', '.AWS'), ('.ssh', '.SSH'), ('.kube', '.Kube')]
    )
    def test_rejects_recased_file_path(self, case_insensitive, sensitive_dir, recased):
        home = path_validation._HOME
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path(os.path.join(home, recased, 'config'))

    def test_rejects_recased_directory_path(self, case_insensitive):
        home = path_validation._HOME
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_directory_path(os.path.join(home, '.GnuPG'))

    def test_rejects_recased_system_dir(self, case_insensitive):
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_path('/ETC/passwd')

    def test_accepts_unrelated_path(self, case_insensitive):
        home = path_validation._HOME
        path = os.path.join(home, 'Projects', 'manifest.yaml')
        assert validate_file_path(path) == os.path.realpath(path)

    def test_recased_path_allowed_on_case_sensitive_fs(self, case_sensitive):
        # On a case-sensitive file system ~/.AWS is a different directory.
        home = path_validation._HOME
        path = os.path.join(home, '.AWS', 'config')
        assert validate_file_path(path) == os.path.realpath(path)


class TestSymlinkedSystemDirs:
    """System entries are resolved, so a symlinked /etc (as on macOS) still matches."""

    def test_rejects_resolved_etc(self, monkeypatch):
        # Simulate macOS, where /etc is a symlink to /private/etc, by rebuilding
        # the blocklist with a realpath that follows that link.
        real_realpath = os.path.realpath

        def macos_realpath(p):
            resolved = real_realpath(p)
            if resolved == '/etc' or resolved.startswith('/etc/'):
                return '/private' + resolved
            return resolved

        monkeypatch.setattr(os.path, 'realpath', macos_realpath)
        try:
            importlib.reload(path_validation)
            assert '/private/etc' in path_validation.BLOCKED_DIRS
            with pytest.raises(ValueError, match='sensitive directory'):
                path_validation.validate_file_path('/etc/passwd')
        finally:
            monkeypatch.undo()
            importlib.reload(path_validation)

    def test_blocked_dirs_are_resolved(self):
        assert os.path.realpath('/etc') in BLOCKED_DIRS
        assert os.path.realpath('/root') in BLOCKED_DIRS
