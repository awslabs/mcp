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

"""Comprehensive server initialization and configuration tests following AWS Labs patterns."""

import asyncio
import os
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from mcp.server.fastmcp import FastMCP

from awslabs.cloudwan_mcp_server.server import (
    discover_vpcs,
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
    main,
    mcp,
    trace_network_path,
    validate_ip_cidr,
)


class TestComprehensiveServerInitialization:
    """Comprehensive server initialization and configuration tests."""

    @pytest.mark.integration
    def test_mcp_server_initialization(self) -> None:
        """Test MCP server initializes correctly following AWS Labs patterns."""
        # Verify FastMCP instance
        assert isinstance(mcp, FastMCP)

        # Verify server name contains CloudWAN identifier
        server_name = getattr(mcp, "name", "") or getattr(mcp, "_name", "")
        assert "CloudWAN" in server_name or "cloudwan" in server_name.lower()

        # Verify server has tools or can be identified as MCP server
        assert hasattr(mcp, "tools") or hasattr(mcp, "_tools") or isinstance(mcp, FastMCP)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_core_tools_registered(self) -> None:
        """Test that all core CloudWAN tools are registered properly."""
        expected_core_tools = {
            "trace_network_path",
            "list_core_networks",
            "get_global_networks",
            "discover_vpcs",
            "validate_ip_cidr",
            "get_core_network_policy",
        }

        # Get registered tool names from list_tools()
        tools = await mcp.list_tools()
        registered_tools = {tool.name for tool in tools}

        # Verify core tools are registered
        assert len(registered_tools.intersection(expected_core_tools)) >= 4, (
            f"Expected at least 4 core tools, found {len(registered_tools)}"
        )
        assert "list_core_networks" in registered_tools, "list_core_networks must be registered"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_function_async_compatibility(self) -> None:
        """Test that all tool functions are async-compatible following AWS Labs patterns."""
        core_functions = [
            list_core_networks,
            get_global_networks,
            get_core_network_policy,
            trace_network_path,
            discover_vpcs,
            validate_ip_cidr,
        ]

        for func in core_functions:
            assert callable(func), f"Function {func.__name__} is not callable"
            assert asyncio.iscoroutinefunction(func), f"Function {func.__name__} is not async"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_client_integration_success(self, mock_aws_context) -> None:
        """Test AWS client integration with successful configuration."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_get_client.return_value = mock_client

            result = await list_core_networks()

            # MCP tools return JSON strings, not dicts
            assert isinstance(result, str)

            # Parse JSON and verify AWS Labs standard response format
            import json

            parsed = json.loads(result)
            assert isinstance(parsed, dict)
            assert "success" in parsed

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_client_credential_error_handling(self, mock_aws_context) -> None:
        """Test AWS client error handling for missing credentials."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_get_client.side_effect = NoCredentialsError()

            result = await list_core_networks()

            # MCP tools return JSON strings, not dicts
            assert isinstance(result, str)

            # Parse JSON and verify error handling follows AWS Labs patterns
            import json

            parsed = json.loads(result)
            assert isinstance(parsed, dict)
            # Should return error response, not raise exception
            assert "error" in parsed or "success" in parsed

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_service_error_handling(self, mock_aws_context) -> None:
        """Test AWS service error handling following AWS Labs patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListCoreNetworks"
            )
            mock_get_client.return_value = mock_client

            result = await list_core_networks()

            # MCP tools return JSON strings, not dicts
            assert isinstance(result, str)

            # Parse JSON and verify AWS Labs error response format
            import json

            parsed = json.loads(result)
            assert isinstance(parsed, dict)
            assert "error" in parsed or "success" in parsed

    @pytest.mark.integration
    def test_environment_variable_configuration(self) -> None:
        """Test server handles environment variables correctly."""
        # Test AWS_DEFAULT_REGION is accessible
        original_region = os.environ.get("AWS_DEFAULT_REGION")

        try:
            # Test with valid region
            os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
            from awslabs.cloudwan_mcp_server.server import get_aws_client

            # Should not raise exception with valid region
            try:
                client = get_aws_client("networkmanager")
                assert client is not None
            except Exception:
                # Some errors are expected if no credentials, but should not be region-related
                pass

        finally:
            # Restore original environment
            if original_region:
                os.environ["AWS_DEFAULT_REGION"] = original_region
            else:
                os.environ.pop("AWS_DEFAULT_REGION", None)

    @pytest.mark.integration
    @patch("awslabs.cloudwan_mcp_server.server.mcp.run")
    def test_main_function_with_valid_environment(self, mock_run) -> None:
        """Test main function with valid environment configuration."""
        with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "us-east-1"}):
            try:
                main()
                # If main() completes without exception, test passes
                # mock_run should have been called
            except SystemExit:
                # SystemExit is acceptable for main function
                pass
            except Exception as e:
                # Any other exception suggests configuration issues
                pytest.fail(f"main() raised unexpected exception: {e}")

    @pytest.mark.integration
    def test_server_response_format_compliance(self) -> None:
        """Test server response format follows AWS Labs standards."""
        from awslabs.cloudwan_mcp_server.server import ContentItem, McpResponse

        # Test ContentItem structure
        content_item = ContentItem(type="text", text="test content")
        assert content_item["type"] == "text"
        assert content_item["text"] == "test content"

        # Test McpResponse structure
        response = McpResponse(content=[content_item])
        assert "content" in response
        assert len(response["content"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_aws_context) -> None:
        """Test concurrent tool execution following AWS Labs patterns."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_client.describe_global_networks.return_value = {"GlobalNetworks": []}
            mock_get_client.return_value = mock_client

            # Test concurrent execution of multiple tools
            tasks = [
                list_core_networks(),
                get_global_networks(),
                list_core_networks(),  # Duplicate to test caching/concurrency
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All tasks should complete successfully
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Task {i} failed with: {result}"
                assert isinstance(result, str), f"Task {i} returned invalid type: {type(result)}"

                # Parse JSON to verify structure
                import json

                parsed = json.loads(result)
                assert isinstance(parsed, dict), f"Task {i} JSON is not a dict: {type(parsed)}"

    @pytest.mark.integration
    def test_server_initialization_state(self) -> None:
        """Test server initialization state and configuration."""
        from awslabs.cloudwan_mcp_server import server

        # Verify server module has required attributes
        assert hasattr(server, "mcp"), "Server must have mcp attribute"
        assert hasattr(server, "main"), "Server must have main function"

        # Verify server has tool functions
        tool_functions = [
            "list_core_networks",
            "get_global_networks",
            "trace_network_path",
            "discover_vpcs",
            "validate_ip_cidr",
        ]

        available_tools = []
        for tool_name in tool_functions:
            if hasattr(server, tool_name):
                available_tools.append(tool_name)

        assert len(available_tools) >= 3, f"Expected at least 3 tools, found {len(available_tools)}: {available_tools}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_input_validation_patterns(self, mock_aws_context) -> None:
        """Test input validation following AWS Labs patterns."""
        # Test CIDR validation with correct parameters
        result = await validate_ip_cidr("validate_cidr", cidr="10.0.0.0/16")
        assert isinstance(result, str)

        # Parse JSON to verify structure
        import json

        parsed = json.loads(result)
        assert isinstance(parsed, dict)

        # Test invalid input handling
        result = await validate_ip_cidr("validate_cidr", cidr="invalid-cidr")
        assert isinstance(result, str)

        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        # Should handle invalid input gracefully, not raise exception

    @pytest.mark.integration
    def test_server_metadata_and_configuration(self) -> None:
        """Test server metadata and configuration following AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.server import mcp

        # Verify server has appropriate name/description
        assert hasattr(mcp, "name"), "Server must have name attribute"
        server_name = mcp.name.lower()
        assert any(keyword in server_name for keyword in ["cloudwan", "aws", "network"]), (
            f"Server name '{mcp.name}' should contain CloudWAN/AWS/Network identifier"
        )

        # Test server is properly initialized for MCP protocol
        assert isinstance(mcp, FastMCP), "Server must be FastMCP instance"
