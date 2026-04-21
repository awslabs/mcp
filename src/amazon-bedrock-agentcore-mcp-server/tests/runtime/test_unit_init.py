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

"""Tests for runtime __init__.py — registration entry point."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime import (
    register_runtime_tools,
)
from unittest.mock import MagicMock


class TestRegisterRuntimeTools:
    """Tests for register_runtime_tools."""

    def test_registers_all_groups(self):
        """All tool groups register without error on a mock MCP server."""
        mock_mcp = MagicMock()
        # tool() returns a decorator that accepts the method
        mock_mcp.tool.return_value = lambda fn: fn

        register_runtime_tools(mock_mcp)

        # Verify tool() was called at least once for each group
        assert mock_mcp.tool.call_count >= 14  # 6 lifecycle + 5 endpoint + 2 invocation + 1 guide

    def test_raises_runtime_error_on_group_failure(self):
        """Registration failure in a tool group raises RuntimeError."""
        mock_mcp = MagicMock()
        # Make tool() raise to simulate a registration failure
        mock_mcp.tool.side_effect = TypeError('bad registration')

        with pytest.raises(RuntimeError, match='Failed to register runtime'):
            register_runtime_tools(mock_mcp)
