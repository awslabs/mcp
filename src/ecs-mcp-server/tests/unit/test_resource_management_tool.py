"""
Unit tests for the ECS resource management tool in main.py.
"""

import unittest
from unittest.mock import AsyncMock, patch

import pytest

from awslabs.ecs_mcp_server.modules import resource_management


# We need to patch the imports before importing the module under test
class MockFastMCP:
    """Mock implementation of FastMCP for testing."""

    def __init__(self, name, instructions=None):
        self.name = name
        self.instructions = instructions
        self.tools = []
        self.prompt_patterns = []

    def tool(self, name=None, annotations=None):
        def decorator(func):
            self.tools.append(
                {"name": name or func.__name__, "function": func, "annotations": annotations}
            )
            return func

        return decorator

    def prompt(self, pattern):
        def decorator(func):
            self.prompt_patterns.append({"pattern": pattern, "function": func})
            return func

        return decorator

    def run(self):
        pass


# Apply the patches
# This is a standalone test that doesn't work well with pytest's isolation
# So we've moved the functionality into the TestResourceManagementTool class below


class TestResourceManagementTool(unittest.TestCase):
    """Test the ecs_resource_management tool in main.py."""

    def test_ecs_resource_management_tool_registration(self):
        """Test that the ecs_resource_management tool is properly registered."""
        mcp = MockFastMCP("AWS ECS MCP Server")
        resource_management.register_module(mcp)

        # Verify the tool is registered
        tool_names = [tool["name"] for tool in mcp.tools]
        self.assertIn("ecs_resource_management", tool_names)

    @pytest.mark.anyio
    @patch.object(resource_management, "ecs_api_operation", new_callable=AsyncMock)
    async def test_ecs_resource_management_tool_function(self, mock_ecs_api_operation):
        """Test that the ecs_resource_management tool function works correctly."""
        mcp = MockFastMCP("AWS ECS MCP Server")
        resource_management.register_module(mcp)
        mcp_ecs_resource_management = next(
            tool["function"] for tool in mcp.tools if tool["name"] == "ecs_resource_management"
        )

        # Setup mock
        mock_ecs_api_operation.return_value = {"test": "result"}

        # Test with different parameter combinations
        await mcp_ecs_resource_management("ListClusters", {})
        mock_ecs_api_operation.assert_awaited_with("ListClusters", {})

        await mcp_ecs_resource_management(
            "DescribeServices",
            {"cluster": "my-cluster", "services": ["my-service"], "include": ["TAGS"]},
        )
        mock_ecs_api_operation.assert_awaited_with(
            "DescribeServices",
            {"cluster": "my-cluster", "services": ["my-service"], "include": ["TAGS"]},
        )

        # Verify result is passed through
        result = await mcp_ecs_resource_management("ListClusters", {})
        self.assertEqual(result, {"test": "result"})


if __name__ == "__main__":
    unittest.main()
