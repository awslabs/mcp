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

"""Shared test fixtures for database_insights tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods for tests."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def register_tools_and_capture():
    """Return a helper that registers tools into a mock MCP and
    captures registered tool functions into a dict.

    Usage:
        registered = register_tools_and_capture(tools_instance)
        # then use registered['tool-name'] to call the tool
    """
    def _register(tools_instance):
        mock_mcp = MagicMock()
        registered_funcs = {}

        def capture_tool(name):
            def decorator(func):
                registered_funcs[name] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        tools_instance.register(mock_mcp)
        return registered_funcs

    return _register
