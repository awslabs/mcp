"""
Integration tests for ECS MCP Server using MCP Inspector CLI.

This module tests the ECS MCP server by calling it through the MCP inspector CLI tool,
which provides a more realistic testing environment similar to how MCP clients would interact.
"""

import logging
from pathlib import Path

import pytest

from .mcp_inspector_framework import (
    MCPInspectorError,
    MCPInspectorFramework,
    MCPTestAssertions,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestECSMCPInspector:
    """Integration tests for ECS MCP Server using MCP Inspector."""

    @classmethod
    def setup_class(cls):
        """Set up the test class with MCP Inspector framework."""
        # Path to the ECS MCP server main.py
        server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"

        # Initialize the framework
        cls.framework = MCPInspectorFramework(
            server_path=str(server_path),
            timeout=30,  # 30 second timeout for commands
        )

        # Create assertions helper
        cls.assertions = MCPTestAssertions()

    def setup_method(self):
        """Setup before each test method."""
        logger.info(f"Starting test: {self._get_test_name()}")

    def teardown_method(self):
        """Cleanup after each test method."""
        logger.info(f"Completed test: {self._get_test_name()}")

    def _get_test_name(self):
        """Get the current test method name."""
        import inspect

        return inspect.stack()[2].function

    def test_list_tools_basic(self):
        """Test basic tools/list functionality."""
        logger.info("Testing tools/list command")

        # Call the MCP inspector to list tools
        result = TestECSMCPInspector.framework.list_tools()

        # Basic assertions
        assert result.success, f"tools/list command failed: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"
        assert "tools" in result.parsed_json, "Response missing 'tools' key"

        # Check execution time is reasonable (under 10 seconds)
        TestECSMCPInspector.assertions.assert_execution_time_under(result, 10.0)

        # Log the tools found
        tools = result.parsed_json["tools"]
        tool_names = [tool.get("name", "unnamed") for tool in tools]
        logger.info(f"Found {len(tools)} tools: {tool_names}")

        # Verify we have some tools (ECS MCP server should have multiple tools)
        assert len(tools) > 0, "No tools found in ECS MCP server"

    def test_expected_ecs_tools_exist(self):
        """Test that expected ECS-related tools exist."""
        logger.info("Testing for expected ECS tools")

        result = TestECSMCPInspector.framework.list_tools()

        # If you don't know the exact tool names yet, let's discover them first
        tools = result.parsed_json["tools"]

        # For now, just verify we have tools and they have proper schemas
        for tool in tools:
            assert "name" in tool, "Tool missing name"
            assert "description" in tool, f"Tool '{tool.get('name')}' missing description"

            # Check that each tool has a proper input schema
            TestECSMCPInspector.assertions.assert_tool_has_schema(result, tool["name"])

        logger.info(f"All {len(tools)} tools have proper schemas")

    def test_tools_have_descriptions(self):
        """Test that all tools have meaningful descriptions."""
        logger.info("Testing tool descriptions")

        result = TestECSMCPInspector.framework.list_tools()
        tools = result.parsed_json["tools"]

        for tool in tools:
            name = tool.get("name", "unnamed")
            description = tool.get("description", "")

            # Verify description exists and is meaningful
            assert description, f"Tool '{name}' has empty description"
            assert len(description) > 10, (
                f"Tool '{name}' has too short description: '{description}'"
            )

            # Check for common description quality indicators
            assert not description.lower().startswith("todo"), (
                f"Tool '{name}' has placeholder description: '{description}'"
            )

        logger.info(f"All {len(tools)} tools have meaningful descriptions")

    def test_server_startup_time(self):
        """Test that the MCP server starts up in reasonable time."""
        logger.info("Testing server startup time")

        result = TestECSMCPInspector.framework.list_tools()

        # Server should start and respond within 5 seconds
        TestECSMCPInspector.assertions.assert_execution_time_under(result, 5.0)

        logger.info(f"Server startup and response time: {result.execution_time:.2f}s")

    @pytest.mark.skip(reason="Tool call test requires specific tool and parameters")
    def test_tool_call_example(self):
        """
        Example test for calling a specific tool.

        This test is skipped by default because it requires:
        1. Knowledge of specific tool names
        2. Valid parameters for the tool
        3. Potentially AWS credentials/resources

        Uncomment and modify when you want to test specific tool calls.
        """
        logger.info("Testing tool call functionality")

        # Example tool call (update with actual tool name and parameters)
        tool_name = "example_tool"
        arguments = {"parameter1": "value1", "parameter2": "value2"}

        result = TestECSMCPInspector.framework.call_tool(tool_name, arguments)
        TestECSMCPInspector.assertions.assert_tool_call_success(result, tool_name)

        logger.info(f"Tool '{tool_name}' executed successfully")

    def test_invalid_method_handling(self):
        """Test that invalid MCP methods are handled gracefully."""
        logger.info("Testing invalid method handling")

        # Try to call a non-existent method
        result = TestECSMCPInspector.framework.run_inspector_command(
            "invalid/method", expect_success=False
        )

        # Should fail gracefully
        assert not result.success, "Expected invalid method to fail"

        # Should have meaningful error message
        assert result.stderr, "Expected error message for invalid method"

        logger.info("Invalid method handled correctly")

    def test_resources_list(self):
        """Test resources/list functionality if supported."""
        logger.info("Testing resources/list command")

        try:
            result = TestECSMCPInspector.framework.list_resources()

            if result.success:
                assert result.parsed_json is not None, "No JSON response received"
                logger.info("Resources list command succeeded")

                if "resources" in result.parsed_json:
                    resources = result.parsed_json["resources"]
                    logger.info(f"Found {len(resources)} resources")
            else:
                # Some MCP servers don't support resources
                logger.info("Resources not supported by this server (expected)")

        except MCPInspectorError as e:
            # Resources might not be implemented
            logger.info(f"Resources command failed (might not be implemented): {e}")


# Standalone test function for pytest discovery
def test_ecs_mcp_tools_list():
    """Standalone test function that can be run independently."""
    # This allows running just this test without the class setup
    server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"
    framework = MCPInspectorFramework(server_path=str(server_path))

    result = framework.list_tools()

    assert result.success, f"tools/list failed: {result.stderr}"
    assert result.parsed_json is not None, "No JSON response"
    assert "tools" in result.parsed_json, "No tools in response"

    tools = result.parsed_json["tools"]
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')}")


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    test_ecs_mcp_tools_list()
