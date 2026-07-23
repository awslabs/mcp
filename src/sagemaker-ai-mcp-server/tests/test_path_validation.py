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
"""Tests for path validation."""

import os
import pytest
from awslabs.sagemaker_ai_mcp_server.path_validation import validate_file_read_path


class TestValidateFileReadPath:
    """Tests for validate_file_read_path."""

    def test_valid_absolute_path(self):
        """Test that a valid absolute path is accepted and resolved."""
        result = validate_file_read_path('/tmp/test-params.json')
        assert os.path.isabs(result)

    def test_relative_path_rejected(self):
        """Test that relative paths are rejected."""
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_file_read_path('../test.json')

    def test_relative_path_with_traversal_rejected(self):
        """Test that relative paths with traversal are rejected."""
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_file_read_path('../../.aws/credentials')

    def test_dot_relative_path_rejected(self):
        """Test that dot-relative paths are rejected."""
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_file_read_path('./params.json')

    def test_aws_credentials_blocked(self):
        """Test that ~/.aws/credentials is blocked."""
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path(os.path.join(home, '.aws', 'credentials'))

    def test_aws_config_blocked(self):
        """Test that ~/.aws/config is blocked."""
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path(os.path.join(home, '.aws', 'config'))

    def test_ssh_directory_blocked(self):
        """Test that ~/.ssh/ files are blocked."""
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path(os.path.join(home, '.ssh', 'id_rsa'))

    def test_gnupg_directory_blocked(self):
        """Test that ~/.gnupg/ files are blocked."""
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path(os.path.join(home, '.gnupg', 'private-keys-v1.d'))

    def test_docker_directory_blocked(self):
        """Test that ~/.docker/ files are blocked."""
        home = os.path.expanduser('~')
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path(os.path.join(home, '.docker', 'config.json'))

    def test_etc_shadow_blocked(self):
        """Test that /etc/shadow is blocked."""
        with pytest.raises(ValueError, match='sensitive'):
            validate_file_read_path('/etc/shadow')

    def test_etc_passwd_blocked(self):
        """Test that /etc/passwd is blocked."""
        with pytest.raises(ValueError, match='sensitive'):
            validate_file_read_path('/etc/passwd')

    def test_proc_blocked(self):
        """Test that /proc/ files are blocked."""
        with pytest.raises(ValueError, match='sensitive directory'):
            validate_file_read_path('/proc/self/environ')

    def test_sensitive_filename_id_rsa_blocked(self):
        """Test that id_rsa filename is blocked regardless of directory."""
        with pytest.raises(ValueError, match='sensitive file'):
            validate_file_read_path('/tmp/id_rsa')

    def test_sensitive_filename_credentials_blocked(self):
        """Test that 'credentials' filename is blocked regardless of directory."""
        with pytest.raises(ValueError, match='sensitive file'):
            validate_file_read_path('/tmp/credentials')

    def test_sensitive_filename_env_blocked(self):
        """Test that .env filename is blocked regardless of directory."""
        with pytest.raises(ValueError, match='sensitive file'):
            validate_file_read_path('/tmp/.env')

    def test_sensitive_filename_netrc_blocked(self):
        """Test that .netrc filename is blocked regardless of directory."""
        with pytest.raises(ValueError, match='sensitive file'):
            validate_file_read_path('/tmp/.netrc')

    def test_valid_json_filename_allowed(self):
        """Test that a normal JSON file in a safe directory is allowed."""
        result = validate_file_read_path('/tmp/my-cluster-params.json')
        assert result.endswith('my-cluster-params.json')

    def test_valid_path_in_home_allowed(self):
        """Test that a normal file in home directory is allowed."""
        home = os.path.expanduser('~')
        result = validate_file_read_path(os.path.join(home, 'workspace', 'params.json'))
        assert 'workspace' in result

    def test_symlink_traversal_to_sensitive_dir_blocked(self, tmp_path):
        """Test that symlinks resolving to sensitive directories are blocked."""
        home = os.path.expanduser('~')
        aws_dir = os.path.join(home, '.aws')
        if os.path.exists(aws_dir):
            link = tmp_path / 'sneaky-link'
            link.symlink_to(aws_dir)
            with pytest.raises(ValueError, match='sensitive directory'):
                validate_file_read_path(str(link / 'credentials'))

    def test_path_with_dot_dot_in_absolute_resolves_and_validates(self):
        """Test that /tmp/../etc/passwd is resolved and blocked."""
        with pytest.raises(ValueError, match='sensitive'):
            validate_file_read_path('/tmp/../etc/passwd')

    def test_tilde_expansion(self):
        """Test that ~ paths are rejected as non-absolute."""
        with pytest.raises(ValueError, match='Path must be absolute'):
            validate_file_read_path('~/.aws/credentials')
