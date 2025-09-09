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

"""Tests for the Context class."""

import pytest
from awslabs.dms_mcp_server.context import Context


class TestContext:
    """Tests for the Context class."""

    def test_initialize_readonly_true(self):
        """Test initializing context with readonly=True."""
        Context.initialize(readonly=True)

        assert Context.readonly_mode() is True

    def test_initialize_readonly_false(self):
        """Test initializing context with readonly=False."""
        Context.initialize(readonly=False)

        assert Context.readonly_mode() is False

    def test_default_readonly_state(self):
        """Test that default state is readonly=True."""
        # Reset to default state
        Context._readonly_mode = True

        assert Context.readonly_mode() is True

    def test_require_write_access_when_readonly_false(self):
        """Test require_write_access when readonly=False."""
        Context.initialize(readonly=False)

        # Should not raise an exception
        Context.require_write_access()

    def test_require_write_access_when_readonly_true(self):
        """Test require_write_access when readonly=True."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError) as exc_info:
            Context.require_write_access()

        assert 'Your DMS MCP server does not allow writes' in str(exc_info.value)
        assert 'remove the --read-only-mode parameter' in str(exc_info.value)

    def test_multiple_initializations(self):
        """Test that multiple initializations work correctly."""
        # Initialize as readonly
        Context.initialize(readonly=True)
        assert Context.readonly_mode() is True

        # Change to write mode
        Context.initialize(readonly=False)
        assert Context.readonly_mode() is False

        # Change back to readonly
        Context.initialize(readonly=True)
        assert Context.readonly_mode() is True

    def test_context_state_persistence(self):
        """Test that context state persists across calls."""
        Context.initialize(readonly=False)

        # Multiple calls should return the same state
        assert Context.readonly_mode() is False
        assert Context.readonly_mode() is False

        # Write access should work multiple times
        Context.require_write_access()
        Context.require_write_access()
