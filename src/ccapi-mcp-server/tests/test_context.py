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
"""Tests for context."""

import pytest


class TestContext:
    """Test context functionality."""

    def test_context_readonly_true(self):
        """Test context readonly mode enabled."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(True)
        assert Context.readonly_mode()

    def test_context_readonly_false(self):
        """Test context readonly mode disabled."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)
        assert not Context.readonly_mode()

    def test_context_not_initialized(self):
        """Test context not initialized error."""
        from awslabs.ccapi_mcp_server.context import Context
        from awslabs.ccapi_mcp_server.errors import ServerError

        # Reset context
        Context._instance = None

        with pytest.raises(ServerError):
            Context.readonly_mode()

    def test_context_multiple_initializations(self):
        """Test multiple context initializations."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(True)
        assert Context.readonly_mode()

        Context.initialize(False)
        assert not Context.readonly_mode()

        Context.initialize(True)
        assert Context.readonly_mode()
