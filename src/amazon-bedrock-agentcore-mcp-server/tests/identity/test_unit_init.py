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

"""Unit tests for Identity tools registration."""

import pytest
from unittest.mock import MagicMock


class TestRegisterIdentityTools:
    """Tests for register_identity_tools."""

    def test_registers_all_groups(self):
        """Registers all 21 identity tools without error."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity import (
            register_identity_tools,
        )

        mock_mcp = MagicMock()
        # tool() returns a decorator that's called with the method
        mock_mcp.tool.return_value = lambda fn: fn

        register_identity_tools(mock_mcp)

        # 5 workload identity + 5 api key + 5 oauth2 + 2 token vault
        # + 3 resource policy + 1 guide = 21
        assert mock_mcp.tool.call_count == 21

    def test_raises_runtime_error_on_failure(self):
        """Raises RuntimeError if a tool group fails to register."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity import (
            register_identity_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.side_effect = Exception('registration boom')

        with pytest.raises(RuntimeError, match='Failed to register identity'):
            register_identity_tools(mock_mcp)
