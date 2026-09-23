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


"""Tests for the environment settings."""

import pytest
from awslabs.redshift_mcp_server.consts import (
    ACCESS_MODE_READ_ONLY,
    ACCESS_MODE_READ_WRITE,
    ACCESS_MODES,
)
from awslabs.redshift_mcp_server.settings import (
    _resolve_int_env,
    resolve_access_mode,
    resolve_skip_write_confirmation,
)


class TestResolveIntEnv:
    """`_resolve_int_env` reads a setting without letting a typo stop the server."""

    def test_unset_uses_the_default(self, monkeypatch):
        """Nothing configured is the normal case."""
        monkeypatch.delenv('PROBE_SETTING', raising=False)
        assert _resolve_int_env('PROBE_SETTING', 600) == 600

    def test_a_valid_value_is_taken_with_surrounding_space_ignored(self, monkeypatch):
        """Values arrive from shells and JSON config, where stray space is common."""
        monkeypatch.setenv('PROBE_SETTING', '  120  ')
        assert _resolve_int_env('PROBE_SETTING', 600) == 120

    @pytest.mark.parametrize(
        'value',
        ['abc', '', '12.5', '0', '-1'],
        ids=['letters', 'empty', 'fractional', 'zero', 'negative'],
    )
    def test_an_unusable_value_falls_back(self, monkeypatch, value):
        """A mistyped timeout should not take the server down at import."""
        monkeypatch.setenv('PROBE_SETTING', value)
        assert _resolve_int_env('PROBE_SETTING', 600) == 600

    def test_a_value_past_the_ceiling_falls_back(self, monkeypatch):
        """The Data API refuses a keepalive above 86400, so sending one would fail every call."""
        monkeypatch.setenv('PROBE_SETTING', '86401')
        assert _resolve_int_env('PROBE_SETTING', 600, maximum=86400) == 600

    def test_a_value_below_the_floor_falls_back(self, monkeypatch):
        """A floor above 1 is rejected on its own terms, not just against zero."""
        monkeypatch.setenv('PROBE_SETTING', '5')
        assert _resolve_int_env('PROBE_SETTING', 600, minimum=10) == 600


class TestResolveAccessMode:
    """Read-write is opt-in and any unsupported mode falls back to read-only."""

    def test_unset_is_read_only(self, monkeypatch):
        """An unset variable leaves the server in the default read-only mode."""
        monkeypatch.delenv('ACCESS_MODE', raising=False)
        assert resolve_access_mode() == ACCESS_MODE_READ_ONLY

    @pytest.mark.parametrize('value', ['read-write', 'READ-WRITE', 'Read-Write', ' read-write '])
    def test_read_write_is_recognized(self, monkeypatch, value):
        """`read-write` selects read-write mode, case- and whitespace-insensitively."""
        monkeypatch.setenv('ACCESS_MODE', value)
        assert resolve_access_mode() == ACCESS_MODE_READ_WRITE

    @pytest.mark.parametrize('value', ['read-only', 'READ-ONLY', ' read-only '])
    def test_read_only_is_recognized(self, monkeypatch, value):
        """`read-only` selects read-only mode explicitly."""
        monkeypatch.setenv('ACCESS_MODE', value)
        assert resolve_access_mode() == ACCESS_MODE_READ_ONLY

    @pytest.mark.parametrize(
        'value',
        [
            '',
            '   ',
            'read_write',  # underscore instead of hyphen
            'readwrite',
            'read-wirte',  # typo: must not grant writes
            'write',
            'true',
            'rw',
            'admin',
        ],
    )
    def test_unsupported_mode_falls_back_to_read_only(self, monkeypatch, value):
        """Empty and unsupported values all fail closed to read-only."""
        monkeypatch.setenv('ACCESS_MODE', value)
        assert resolve_access_mode() == ACCESS_MODE_READ_ONLY

    def test_resolved_mode_is_always_supported(self, monkeypatch):
        """Whatever is configured, the resolved mode is one the server knows."""
        monkeypatch.setenv('ACCESS_MODE', 'nonsense')
        assert resolve_access_mode() in ACCESS_MODES


class TestResolveSkipWriteConfirmation:
    """The confirmation opt-out is off by default and inert outside read-write mode."""

    def test_unset_keeps_confirmation(self, monkeypatch):
        """An unset variable keeps the prompt."""
        monkeypatch.delenv('UNSAFE_SKIP_WRITE_CONFIRMATION', raising=False)
        assert resolve_skip_write_confirmation(ACCESS_MODE_READ_WRITE) is False

    def test_true_skips_confirmation_in_read_write(self, monkeypatch):
        """`true` skips the prompt in read-write mode."""
        monkeypatch.setenv('UNSAFE_SKIP_WRITE_CONFIRMATION', 'true')
        assert resolve_skip_write_confirmation(ACCESS_MODE_READ_WRITE) is True

    def test_true_is_inert_in_read_only(self, monkeypatch):
        """`true` has no effect when writes are not allowed at all."""
        monkeypatch.setenv('UNSAFE_SKIP_WRITE_CONFIRMATION', 'true')
        assert resolve_skip_write_confirmation(ACCESS_MODE_READ_ONLY) is False

    @pytest.mark.parametrize('value', ['false', '', '   ', 'ture', '1', 'yes'])
    def test_everything_else_keeps_confirmation(self, monkeypatch, value):
        """`false`, empty, and unrecognized values all keep the prompt."""
        monkeypatch.setenv('UNSAFE_SKIP_WRITE_CONFIRMATION', value)
        assert resolve_skip_write_confirmation(ACCESS_MODE_READ_WRITE) is False
