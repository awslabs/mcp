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

"""Unit tests for Policy tools registration."""

import pytest
from unittest.mock import MagicMock


class TestRegisterPolicyTools:
    """Tests for register_policy_tools."""

    def test_registers_all_groups(self):
        """Registers all tool groups without error."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy import (
            register_policy_tools,
        )

        mock_mcp = MagicMock()
        # tool() returns a decorator, which is called with the method
        mock_mcp.tool.return_value = lambda fn: fn

        register_policy_tools(mock_mcp)

        # Verify tool() was called for each of the 15 tools:
        #   5 engine tools + 5 policy tools + 4 generation tools + 1 guide tool
        assert mock_mcp.tool.call_count == 15

    def test_raises_runtime_error_on_failure(self):
        """Raises RuntimeError if a tool group fails to register."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy import (
            register_policy_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.side_effect = Exception('registration boom')

        with pytest.raises(RuntimeError, match='Failed to register policy'):
            register_policy_tools(mock_mcp)
