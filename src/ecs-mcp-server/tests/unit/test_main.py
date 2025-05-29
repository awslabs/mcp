"""
Unit tests for main server module.

This file contains granular tests that check specific aspects of the ECS MCP Server
configuration separately. Each test method focuses on a specific aspect of the server:
- Basic properties (name, version, description, instructions)
- Tools registration
- Prompt patterns registration

"""

import unittest
from unittest.mock import patch


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

    def tool(self, name=None, description=None, annotations=None):
        def decorator(func):
            self.tools.append(
                {
                    "name": name or func.__name__,
                    "function": func,
                    "annotations": annotations,
                    "description": description,
                }
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
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    from awslabs.ecs_mcp_server.main import mcp


class TestMain(unittest.TestCase):
    """
    Granular tests for main server module.

    This test class contains separate test methods for each aspect of the server
    configuration, providing better isolation and easier debugging when tests fail.
    """

    def test_server_basic_properties(self):
        """
        Test basic server properties.

        This test focuses only on the basic properties of the server:
        - Name
        - Version
        - Description
        - Instructions

        If this test fails, it indicates an issue with the basic server configuration.
        """
        # Verify the server has the correct name and version
        self.assertEqual(mcp.name, "AWS ECS MCP Server")
        self.assertEqual(mcp.version, "0.1.0")

        # Verify the description contains expected keywords
        self.assertIn("containerization", mcp.description.lower())
        self.assertIn("deployment", mcp.description.lower())
        self.assertIn("aws ecs", mcp.description.lower())

        # Verify instructions are provided
        self.assertIsNotNone(mcp.instructions)
        self.assertIn("WORKFLOW", mcp.instructions)
        self.assertIn("IMPORTANT", mcp.instructions)

    def test_server_tools(self):
        """
        Test that server has the expected tools.

        This test focuses only on the tools registered with the server.
        It verifies that all required tools are present.

        If this test fails, it indicates an issue with tool registration.
        """
        # Verify the server has registered tools
        self.assertGreaterEqual(len(mcp.tools), 4)

        # Verify tool names
        tool_names = [tool["name"] for tool in mcp.tools]
        self.assertIn("containerize_app", tool_names)
        self.assertIn("create_ecs_infrastructure", tool_names)
        self.assertIn("get_deployment_status", tool_names)
        self.assertIn("delete_ecs_infrastructure", tool_names)

    def test_server_prompts(self):
        """
        Test that server has the expected prompt patterns.

        This test focuses only on the prompt patterns registered with the server.
        It verifies that all required prompt patterns are present.

        If this test fails, it indicates an issue with prompt pattern registration.
        """
        # Verify the server has registered prompt patterns
        self.assertGreaterEqual(len(mcp.prompt_patterns), 14)

        # Verify prompt patterns
        patterns = [pattern["pattern"] for pattern in mcp.prompt_patterns]
        self.assertIn("dockerize", patterns)
        self.assertIn("containerize", patterns)
        self.assertIn("deploy to aws", patterns)
        self.assertIn("deploy to ecs", patterns)
        self.assertIn("ship it", patterns)
        self.assertIn("deploy flask", patterns)
        self.assertIn("deploy django", patterns)
        self.assertIn("delete infrastructure", patterns)
        self.assertIn("tear down", patterns)
        self.assertIn("remove deployment", patterns)
        self.assertIn("clean up resources", patterns)


if __name__ == "__main__":
    unittest.main()
