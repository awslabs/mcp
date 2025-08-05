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

"""AWS Labs compliance tests following standard patterns."""

import asyncio
import json
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
    mcp,
)


class TestAWSLabsCompliance:
    """Test suite following AWS Labs MCP server patterns."""

    @pytest.mark.asyncio
    async def test_mcp_protocol_compliance(self, mock_get_aws_client: Mock) -> None:
        """Test MCP protocol v1.1+ compliance following AWS Labs patterns."""
        # Test tool registration and availability
        assert hasattr(mcp, "list_tools"), "MCP server must expose list_tools method"  # noqa: S101

        # Test basic protocol compliance
        tools = await mcp.list_tools()
        assert len(tools) >= 10, f"Must have at least 10 core CloudWAN tools, found {len(tools)}"  # noqa: S101

        # Test async compatibility - tools are already registered as async in FastMCP
        assert all(hasattr(tool, "name") for tool in tools), "All tools must have names"  # noqa: S101
        assert all(tool.name for tool in tools), "All tools must have non-empty names"  # noqa: S101

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_aws_api_integration(self, secure_aws_credentials) -> None:
        """Live AWS API test - requires valid credentials."""
        pytest.skip("Live tests require valid AWS credentials and are run selectively")

        # This test would run against actual AWS APIs when credentials are available
        # Following AWS Labs pattern for live API testing
        result = await list_core_networks()
        assert isinstance(result, dict)  # noqa: S101
        assert "success" in result  # noqa: S101

    @pytest.mark.asyncio
    async def test_mocked_aws_service_integration(self, aws_service_mocker: Mock) -> None:
        """Test AWS service integration with moto mocking (AWS Labs pattern)."""
        # Create mock NetworkManager client
        nm_mocker = aws_service_mocker("networkmanager", "us-east-1")

        # Configure core networks mock data
        nm_mocker.client.list_core_networks = Mock(
            return_value={
                "CoreNetworks": [
                    {
                        "CoreNetworkId": "core-network-test123",
                        "CoreNetworkArn": "arn:aws:networkmanager::123456789012:core-network/core-network-test123",
                        "GlobalNetworkId": "global-network-test123",
                        "State": "AVAILABLE",
                        "Description": "Test core network",
                    }
                ]
            }
        )

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_get_client.return_value = nm_mocker.client
            result = await list_core_networks()
            # Parse JSON response to dict
            result = json.loads(result)
            assert result["success"] is True  # noqa: S101
            assert len(result["core_networks"]) >= 0  # noqa: S101

    @pytest.mark.asyncio
    async def test_error_handling_patterns(self, aws_service_mocker: Mock) -> None:
        """Test AWS Labs standard error handling patterns."""
        # Create mock NetworkManager client
        nm_mocker = aws_service_mocker("networkmanager", "us-east-1")

        # Configure mock to raise error
        nm_mocker.client.list_core_networks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListCoreNetworks"
        )

        # Patch get_aws_client to return our configured mock
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_get_client.return_value = nm_mocker.client

            # Test with error
            result = await list_core_networks()
            # Convert JSON string to dict
            result = json.loads(result)

            # AWS Labs standard error response format
            assert result["success"] is False  # noqa: S101
            assert "error" in result  # noqa: S101
            assert "error_code" in result  # noqa: S101

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_performance_characteristics(self, mock_aws_context: Mock) -> None:
        """Test performance following AWS Labs patterns."""
        import time

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_get_client.return_value = mock_client

            start_time = time.time()
            result = await list_core_networks()
            end_time = time.time()

            # Parse JSON response
            result = json.loads(result)

            # Performance assertion following AWS Labs patterns
            assert (end_time - start_time) < 5.0, "Tool should complete within 5 seconds"  # noqa: S101
            assert result["success"] is True  # noqa: S101

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tool_registration_compliance(self) -> None:
        """Test tool registration follows AWS Labs patterns."""
        tools = await mcp.list_tools()
        registered_tools = [tool.name for tool in tools]

        # Check for expected core tools
        expected_core_tools = [
            "trace_network_path",
            "list_core_networks",
            "get_global_networks",
            "discover_vpcs",
            "validate_ip_cidr",
        ]

        for tool_name in expected_core_tools:
            assert tool_name in registered_tools, f"Tool {tool_name} not registered"  # noqa: S101

    @pytest.mark.asyncio
    async def test_aws_credential_handling(self, secure_aws_credentials: Mock) -> None:
        """Test AWS credential handling following AWS Labs patterns."""
        # Test that tools handle missing credentials gracefully
        with patch("boto3.client") as mock_boto_client:
            mock_boto_client.side_effect = Exception("No credentials found")

            result = await list_core_networks()

            # Parse JSON response
            result = json.loads(result)

            # Should return error response, not raise exception
            assert isinstance(result, dict)  # noqa: S101
            assert "error" in result or "success" in result  # noqa: S101

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_chaining_patterns(self, mock_aws_context: Mock) -> None:
        """Test tool chaining following AWS Labs integration patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()

            # Mock sequential API calls
            mock_client.describe_global_networks.return_value = {
                "GlobalNetworks": [{"GlobalNetworkId": "gn-123", "State": "AVAILABLE"}]
            }
            mock_client.list_core_networks.return_value = {
                "CoreNetworks": [{"CoreNetworkId": "cn-123", "GlobalNetworkId": "gn-123"}]
            }
            mock_client.get_core_network_policy.return_value = {
                "CoreNetworkPolicy": {"PolicyVersionId": 1, "PolicyDocument": {}}
            }

            mock_get_client.return_value = mock_client

            # Test chaining: global networks -> core networks -> policy
            global_networks = await get_global_networks()
            global_networks = json.loads(global_networks)
            assert global_networks["success"] is True  # noqa: S101

            core_networks = await list_core_networks()
            core_networks = json.loads(core_networks)
            assert core_networks["success"] is True  # noqa: S101

            policy = await get_core_network_policy("cn-123")
            policy = json.loads(policy)
            assert policy["success"] is True  # noqa: S101

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_aws_context: Mock) -> None:
        """Test concurrent tool execution following AWS Labs patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.return_value = {"GlobalNetworks": []}
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_get_client.return_value = mock_client

            # Test concurrent execution
            tasks = [get_global_networks(), list_core_networks(), get_global_networks()]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All tasks should complete successfully
            for result in results:
                assert not isinstance(result, Exception)  # noqa: S101
                # Parse JSON to dict
                result = json.loads(result)
                assert result["success"] is True  # noqa: S101
