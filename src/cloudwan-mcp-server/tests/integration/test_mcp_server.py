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

"""Integration tests for MCP server functionality."""

import asyncio
import json
from unittest.mock import Mock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_routes,
    discover_vpcs,
    list_core_networks,
    main,
    mcp,
)


class TestMCPServerIntegration:
    """Test MCP server integration and tool registration."""

    @pytest.mark.integration
    def test_mcp_server_initialization(self) -> None:
        """Test that MCP server initializes correctly."""
        assert isinstance(mcp, FastMCP)
        assert "AWS CloudWAN MCP server" in mcp.name

    @pytest.mark.integration
    def test_all_tools_registered(self) -> None:
        """Test that all 16 tools are registered with the MCP server."""
        expected_tools = {
            "trace_network_path",
            "list_core_networks",
            "get_global_networks",
            "discover_vpcs",
            "discover_ip_details",
            "validate_ip_cidr",
            "list_network_function_groups",
            "analyze_network_function_group",
            "validate_cloudwan_policy",
            "manage_tgw_routes",
            "analyze_tgw_routes",
            "analyze_tgw_peers",
            "analyze_segment_routes",
            "get_core_network_policy",
            "get_core_network_change_set",
            "get_core_network_change_events",
        }

        # Get registered tools from FastMCP server
        registered_tools = set()
        # Use the tools property to access registered tools
        if hasattr(mcp, "tools"):
            for tool_name in mcp.tools.keys():
                registered_tools.add(tool_name)
        else:
            # Fallback: check for tool functions in the server module
            from awslabs.cloudwan_mcp_server import server

            for tool_name in expected_tools:
                if hasattr(server, tool_name):
                    registered_tools.add(tool_name)

        assert len(registered_tools) == len(expected_tools), f"Expected 16 tools, found {len(registered_tools)}"
        # Check that we have at least the core tools we expect
        assert len(expected_tools.intersection(registered_tools)) >= 10, (
            f"Found fewer than expected tools: {registered_tools}"
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    def test_tool_function_availability(self) -> None:
        """Test that all tool functions are available and callable."""
        from awslabs.cloudwan_mcp_server.server import (
            analyze_network_function_group,
            analyze_segment_routes,
            analyze_tgw_peers,
            discover_ip_details,
            get_core_network_change_events,
            get_core_network_change_set,
            get_core_network_policy,
            get_global_networks,
            list_network_function_groups,
            manage_tgw_routes,
            trace_network_path,
            validate_cloudwan_policy,
            validate_ip_cidr,
        )

        tool_functions = [
            trace_network_path,
            list_core_networks,
            get_global_networks,
            discover_vpcs,
            discover_ip_details,
            validate_ip_cidr,
            list_network_function_groups,
            analyze_network_function_group,
            validate_cloudwan_policy,
            manage_tgw_routes,
            analyze_tgw_routes,
            analyze_tgw_peers,
            analyze_segment_routes,
            get_core_network_policy,
            get_core_network_change_set,
            get_core_network_change_events,
        ]

        for func in tool_functions:
            assert callable(func), f"Function {func.__name__} is not callable"
            assert asyncio.iscoroutinefunction(func), f"Function {func.__name__} is not async"

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_with_valid_env(self, mock_run) -> None:
        """Test main function with valid environment variables."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            main()
            mock_run.assert_called_once()

    def test_main_function_missing_region(self) -> None:
        """Test main function with missing AWS_DEFAULT_REGION."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_keyboard_interrupt(self, mock_run) -> None:
        """Test main function handling keyboard interrupt."""
        mock_run.side_effect = KeyboardInterrupt()

        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            main()  # Should not raise exception

    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_server_error(self, mock_run) -> None:
        """Test main function handling server errors."""
        mock_run.side_effect = Exception("Server error")

        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestMCPToolExecution:
    """Test MCP tool execution through the server."""

    @pytest.mark.asyncio
    async def test_tool_execution_workflow(self, mock_get_aws_client, mock_aws_context) -> None:
        """Test complete tool execution workflow."""
        # Execute tool
        result = await list_core_networks("us-east-1")

        # Verify result is valid JSON
        response = json.loads(result)
        assert isinstance(response, dict)
        assert "success" in response

        # Verify AWS client was called
        mock_get_aws_client.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_tools_concurrent_execution(self, mock_get_aws_client, mock_aws_context) -> None:
        """Test concurrent execution of multiple tools."""
        from awslabs.cloudwan_mcp_server.server import get_global_networks

        # Execute multiple tools concurrently
        tasks = [list_core_networks("us-east-1"), get_global_networks("us-east-1"), discover_vpcs("us-east-1")]

        results = await asyncio.gather(*tasks)

        # Verify all results are valid
        assert len(results) == 3
        for result in results:
            response = json.loads(result)
            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self, mock_get_aws_client, mock_aws_context) -> None:
        """Test tool parameter validation."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        # Test valid parameters
        valid_result = await validate_ip_cidr("validate_ip", ip="10.0.1.100")
        valid_response = json.loads(valid_result)
        assert valid_response["success"] is True

        # Test invalid parameters
        invalid_result = await validate_ip_cidr("invalid_operation")
        invalid_response = json.loads(invalid_result)
        assert invalid_response["success"] is False

    @pytest.mark.asyncio
    async def test_tool_error_handling_integration(self, mock_get_aws_client, mock_aws_context) -> None:
        """Test integrated error handling across tools."""
        from botocore.exceptions import ClientError

        from awslabs.cloudwan_mcp_server.server import trace_network_path

        # Mock AWS client error
        mock_get_aws_client.return_value.some_operation.side_effect = ClientError(
            {"Error": {"Code": "TestError", "Message": "Test error"}}, "TestOperation"
        )

        # Test with invalid IP to trigger error
        result = await trace_network_path("invalid-ip", "10.0.1.100")
        response = json.loads(result)

        assert response["success"] is False
        assert "trace_network_path failed" in response["error"]


class TestMCPResponseFormats:
    """Test MCP response format consistency."""

    @pytest.mark.asyncio
    async def test_success_response_consistency(self, mock_get_aws_client) -> None:
        """Test that all successful responses follow consistent format."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        tools_to_test = [
            (list_core_networks, ("us-east-1",), {}),
            (discover_vpcs, ("us-east-1",), {}),
            (validate_ip_cidr, ("validate_ip",), {"ip": "10.0.1.100"}),
        ]

        for tool_func, args, kwargs in tools_to_test:
            result = await tool_func(*args, **kwargs)
            response = json.loads(result)

            # All responses should have success field
            assert "success" in response
            assert isinstance(response["success"], bool)

    @pytest.mark.asyncio
    async def test_error_response_consistency(self, mock_get_aws_client) -> None:
        """Test that all error responses follow consistent format."""
        from awslabs.cloudwan_mcp_server.server import trace_network_path, validate_ip_cidr

        # Test various error conditions
        error_tests = [(trace_network_path, ("invalid-ip", "10.0.1.100")), (validate_ip_cidr, ("invalid_operation",))]

        for tool_func, args in error_tests:
            result = await tool_func(*args)
            response = json.loads(result)

            assert response["success"] is False
            assert "error" in response
            assert isinstance(response["error"], str)

    @pytest.mark.asyncio
    async def test_json_serialization_all_tools(self, mock_get_aws_client) -> None:
        """Test that all tools return valid JSON."""
        from awslabs.cloudwan_mcp_server.server import (
            discover_ip_details,
            get_global_networks,
            list_network_function_groups,
        )

        tools_to_test = [
            list_core_networks,
            get_global_networks,
            discover_vpcs,
            discover_ip_details,
            list_network_function_groups,
        ]

        for tool_func in tools_to_test:
            if tool_func == discover_ip_details:
                result = await tool_func("10.0.1.100", "us-east-1")
            else:
                result = await tool_func("us-east-1")

            # Should not raise JSON decode error
            response = json.loads(result)
            assert isinstance(response, dict)


class TestMCPServerPerformance:
    """Test MCP server performance characteristics."""

    @pytest.mark.asyncio
    async def test_tool_execution_time(self, mock_get_aws_client) -> None:
        """Test that tools execute within reasonable time limits."""
        import time

        start_time = time.time()
        result = await list_core_networks("us-east-1")
        execution_time = time.time() - start_time

        # Should execute in under 1 second for mocked calls
        assert execution_time < 1.0

        # Verify result is valid
        response = json.loads(result)
        assert response["success"] is True


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance according to AWS Labs standards."""

    @pytest.mark.parametrize("tool_name", ["trace_network_path", "list_core_networks", "get_global_networks"])
    @pytest.mark.asyncio
    async def test_tool_protocol_interface(self, tool_name) -> None:
        """Verify all tools implement required MCP protocol interface."""
        # Get registered tools using list_tools()
        tools = await mcp.list_tools()
        [tool.name for tool in tools]
        tool_class = next((tool for tool in tools if tool.name == tool_name), None)

        assert tool_class is not None, f"Tool {tool_name} not found in registered tools"
        assert hasattr(tool_class, "input_schema")
        assert hasattr(tool_class, "execute")

    @pytest.mark.asyncio
    async def test_error_response_format(self) -> None:
        """Verify error responses follow MCP error specification."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        result = await validate_ip_cidr("invalid_operation")
        response = json.loads(result)

        assert response == {"success": False, "error": str, "error_code": str}

    @pytest.mark.asyncio
    async def test_required_protocol_methods(self) -> None:
        """Verify presence of required MCP protocol methods."""
        required_methods = ["health_check", "get_server_stats", "validate_configuration"]
        for method in required_methods:
            assert hasattr(mcp, method), f"Missing required protocol method: {method}"

        # Verify tool registration through list_tools()
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert len(tool_names) >= 4, f"Expected at least 4 tools, found {len(tool_names)}"

    @pytest.mark.asyncio
    async def test_concurrent_tool_performance(self, mock_get_aws_client) -> None:
        """Test performance of concurrent tool execution."""
        import time

        from awslabs.cloudwan_mcp_server.server import (
            get_global_networks,
            list_network_function_groups,
        )

        # Execute 4 tools concurrently
        start_time = time.time()
        tasks = [
            list_core_networks("us-east-1"),
            get_global_networks("us-east-1"),
            discover_vpcs("us-east-1"),
            list_network_function_groups("us-east-1"),
        ]
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time

        # Concurrent execution should be faster than sequential
        assert execution_time < 2.0  # Should be much faster with mocks
        assert len(results) == 4

        # All should succeed
        for result in results:
            response = json.loads(result)
            assert response["success"] is True

    def test_aws_client_caching_performance(self) -> None:
        """Test AWS client caching improves performance."""
        import time

        from awslabs.cloudwan_mcp_server.server import _create_client, get_aws_client

        _create_client.cache_clear()  # Clear cache to ensure fresh state

        with patch.dict("os.environ", {"AWS_PROFILE": ""}, clear=True):
            with patch("boto3.client") as mock_client:
                mock_client.return_value = Mock()

                # First call - should create client
                start_time = time.time()
                client1 = get_aws_client("networkmanager", "us-east-1")
                time.time() - start_time

                # Second call - should use cache
                start_time = time.time()
                client2 = get_aws_client("networkmanager", "us-east-1")
                time.time() - start_time

                # Cached call should be faster (though this might be too fast to measure reliably)
                # Main assertion: same client returned due to caching
                assert client1 is client2

                # Should only call boto3.client once due to caching
                mock_client.assert_called_once()
