"""
Unit tests for security analysis module registration.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP


def test_module_registration():
    """Test that security_analysis module registers correctly."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Create a mock FastMCP instance
    mock_mcp = MagicMock(spec=FastMCP)

    # Register the module
    security_analysis.register_module(mock_mcp)

    # Verify tool was registered
    assert mock_mcp.tool.called
    # Verify prompts were registered
    assert mock_mcp.prompt.called


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_clusters_with_metadata")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.format_clusters_for_display")
@patch.dict("os.environ", {"AWS_REGION": "us-east-1"})
async def test_tool_execution_list_clusters(mock_format, mock_list_clusters):
    """Test tool execution for listing clusters."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mocks
    mock_list_clusters.return_value = [
        {
            "cluster_name": "test-cluster",
            "status": "ACTIVE",
            "running_tasks_count": 5,
            "active_services_count": 3,
        }
    ]
    mock_format.return_value = "Formatted cluster list"

    # Create a mock FastMCP instance
    mock_mcp = MagicMock(spec=FastMCP)

    # Track the registered tool function
    registered_tool = None

    def capture_tool(name, annotations):
        def decorator(func):
            nonlocal registered_tool
            registered_tool = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    # Register the module
    security_analysis.register_module(mock_mcp)

    # Execute the tool
    result = await registered_tool()

    # Verify the result
    assert result == "Formatted cluster list"
    mock_list_clusters.assert_called_once()
    mock_format.assert_called_once()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_clusters_with_metadata")
@patch.dict("os.environ", {"AWS_REGION": "us-east-1"})
async def test_tool_execution_error_handling(mock_list_clusters):
    """Test tool execution error handling."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mock to raise an exception
    mock_list_clusters.side_effect = Exception("Test error")

    # Create a mock FastMCP instance
    mock_mcp = MagicMock(spec=FastMCP)

    # Track the registered tool function
    registered_tool = None

    def capture_tool(name, annotations):
        def decorator(func):
            nonlocal registered_tool
            registered_tool = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    # Register the module
    security_analysis.register_module(mock_mcp)

    # Execute the tool
    result = await registered_tool()

    # Verify error message is returned
    assert "❌" in result
    assert "Test error" in result


def test_prompt_patterns_registered():
    """Test that all prompt patterns are registered."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Create a mock FastMCP instance
    mock_mcp = MagicMock(spec=FastMCP)

    # Track registered prompts
    registered_prompts = []

    def capture_prompt(pattern):
        def decorator(func):
            registered_prompts.append(pattern)
            return func

        return decorator

    mock_mcp.prompt = capture_prompt

    # Register the module
    security_analysis.register_module(mock_mcp)

    # Verify expected prompts are registered
    expected_prompts = [
        "analyze ecs security",
        "check ecs security",
        "ecs security audit",
        "security best practices",
        "security recommendations",
        "scan ecs clusters",
        "ecs security scan",
        "list ecs clusters",
    ]

    for expected in expected_prompts:
        assert expected in registered_prompts
