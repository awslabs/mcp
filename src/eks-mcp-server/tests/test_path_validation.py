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

import os
import pytest
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
