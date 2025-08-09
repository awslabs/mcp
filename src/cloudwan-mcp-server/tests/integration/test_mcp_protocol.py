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


"""MCP protocol compliance tests."""

import json
from unittest.mock import Mock, patch

import pytest

from awslabs.cloudwan_mcp_server.server import (
    get_global_networks,
    list_core_networks,
)


class TestMCPProtocol:
    """Test MCP protocol compliance using direct server function calls."""

    @pytest.mark.asyncio
    async def test_protocol_tool_execution(self) -> None:
        """Test MCP tool execution compliance."""
        # Mock AWS client for protocol testing
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {
                "CoreNetworks": [{"CoreNetworkId": "core-network-protocol-test", "State": "AVAILABLE"}]
            }
            mock_get_client.return_value = mock_client

            # Test core networks listing
            result = await list_core_networks()
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert "core_networks" in parsed
            assert len(parsed["core_networks"]) == 1

    @pytest.mark.asyncio
    async def test_tool_error_handling_compliance(self) -> None:
        """Test MCP error handling compliance."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Protocol test error")

            result = await get_global_networks()
            parsed = json.loads(result)

            # Verify AWS Labs compliant error format
            assert parsed["success"] is False
            assert "error" in parsed
            assert "error_code" in parsed  # This should now work with our fix
