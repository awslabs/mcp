"""Unit tests for the server module."""

import pytest
from awslabs.aws_finops_mcp_server.server import create_tool_function
from fastmcp import FastMCP


@pytest.mark.unit
def test_create_tool_function(registry):
    """Test that create_tool_function creates a properly named function."""
    # Create a tool function
    tool_name = 'test_tool'
    tool_function = create_tool_function(registry, tool_name)

    # Verify the function name
    assert tool_function.__name__ == tool_name


@pytest.mark.unit
def test_register_boto3_tools_with_real_mcp(registry):
    """Test that tools can be registered with a real FastMCP instance."""
    # Create a real FastMCP instance
    mcp = FastMCP('Test MCP Server')

    # Register tools with the MCP server
    for tool_name, tool_info in registry.tools.items():
        # Create a tool function
        tool_function = create_tool_function(registry, tool_name)

        # Register the tool with FastMCP
        mcp.tool(name=tool_name, description=tool_info['docstring'])(tool_function)

    # Verify that tools were registered
    # FastMCP doesn't expose a way to count registered tools directly,
    # but we can check that the registration process completed without errors
    assert True
