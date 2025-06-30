"""
Unit tests for the ECS resource management tool in main.py.
"""

import unittest
from unittest.mock import patch

import pytest


# We need to patch the imports before importing the module under test
class MockFastMCP:
    """Mock implementation of FastMCP for testing."""

    def __init__(self, name, description=None, version=None, instructions=None):
        self.name = name
        self.description = description or ""
        self.version = version
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

    @pytest.mark.anyio
    @patch("mcp.server.fastmcp.FastMCP", MockFastMCP)
    @patch("awslabs.ecs_mcp_server.api.resource_management.ecs_api_operation")
    async def test_ecs_resource_management_tool_registration(self, mock_ecs_api_operation):
        """Test that the ecs_resource_management tool is properly registered."""
        # Import the patched module
        from awslabs.ecs_mcp_server.main import mcp

        # Verify the tool is registered
        tool_names = [tool["name"] for tool in mcp.tools]
        self.assertIn("ecs_resource_management", tool_names)

    @pytest.mark.anyio
    @patch("mcp.server.fastmcp.FastMCP", MockFastMCP)
    @patch("awslabs.ecs_mcp_server.api.resource_management.ecs_api_operation")
    async def test_ecs_resource_management_tool_function(self, mock_ecs_api_operation):
        """Test that the ecs_resource_management tool function works correctly."""
        # Import the patched module
        from awslabs.ecs_mcp_server.modules.resource_management import mcp_ecs_resource_management

        # Setup mock
        mock_ecs_api_operation.return_value = {"test": "result"}

        # Test with different parameter combinations
        await mcp_ecs_resource_management("ListClusters", {})
        mock_ecs_api_operation.assert_called_with("ListClusters", {})

        await mcp_ecs_resource_management(
            "DescribeServices",
            {"cluster": "my-cluster", "services": ["my-service"], "include": ["TAGS"]},
        )
        mock_ecs_api_operation.assert_called_with(
            "DescribeServices",
            {"cluster": "my-cluster", "services": ["my-service"], "include": ["TAGS"]},
        )

        # Verify result is passed through
        result = await mcp_ecs_resource_management("ListClusters", {})
        self.assertEqual(result, {"test": "result"})


if __name__ == "__main__":
    unittest.main()
