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

"""Unit tests following AWS Labs MCP server patterns."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

# Import only modules that actually exist
from awslabs.cloudwan_mcp_server import server
from awslabs.cloudwan_mcp_server.server import list_core_networks


class TestAWSLabsPatterns:
    """Unit tests following AWS Labs standard patterns."""

    @pytest.mark.unit
    def test_server_module_available(self) -> None:
        """Test server module is available and has expected functions."""
        # Test that server module exists and has expected tools
        assert hasattr(server, "list_core_networks")
        assert hasattr(server, "get_global_networks")
        assert hasattr(server, "trace_network_path")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")
    async def test_aws_service_error_handling(self, mock_boto3) -> None:
        """Test AWS error handling patterns."""
        # Mock AWS client that raises service error
        mock_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_client
        mock_boto3.Session.return_value = mock_session
        mock_boto3.client.return_value = mock_client

        mock_client.list_core_networks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "ListCoreNetworks"
        )

        # Test error handling - should return error response, not raise
        result = await list_core_networks()
        result_json = server.json.loads(result) if isinstance(result, str) else result
        assert result_json["success"] is False
        assert "error" in result_json

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "tool_name,expected_result",
        [
            ("list_core_networks", True),
            ("get_global_networks", True),
            ("trace_network_path", True),
            ("nonexistent_tool", False),
        ],
    )
    def test_tool_availability_parametrized(self, tool_name, expected_result) -> None:
        """Test tool availability using parametrized testing (AWS Labs pattern)."""
        has_tool = hasattr(server, tool_name)
        assert has_tool == expected_result
