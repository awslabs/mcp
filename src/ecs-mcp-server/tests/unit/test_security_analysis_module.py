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
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_target_region")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_clusters_with_metadata")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.format_clusters_for_display")
async def test_tool_execution_list_clusters(mock_format, mock_list_clusters, mock_get_region):
    """Test tool execution for listing clusters."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mocks
    mock_get_region.return_value = "us-east-1"
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

    # Execute the tool (explicitly pass cluster_names=None for list mode)
    result = await registered_tool(cluster_names=None)

    # Verify the result
    assert result == "Formatted cluster list"
    mock_get_region.assert_called_once()
    mock_list_clusters.assert_called_once_with("us-east-1")
    mock_format.assert_called_once()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_target_region")
async def test_tool_execution_error_handling(mock_get_region):
    """Test tool execution error handling."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mock to raise an exception
    mock_get_region.side_effect = Exception("Test error")

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


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_target_region")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.validate_clusters")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.collect_cluster_configuration")
async def test_tool_execution_collect_configuration(
    mock_collect_config, mock_validate, mock_get_region
):
    """Test tool execution for collecting cluster configuration."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mocks
    mock_get_region.return_value = "us-east-1"
    mock_validate.return_value = ["arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"]
    mock_collect_config.return_value = {
        "cluster_name": "test-cluster",
        "region": "us-east-1",
        "cluster_metadata": {"status": "ACTIVE"},
        "services": [],
        "task_definitions": [],
        "security_groups": [],
        "collection_errors": [],
    }

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

    # Execute the tool with cluster_names
    result = await registered_tool(cluster_names=["test-cluster"])

    # Verify the result is JSON
    import json

    result_data = json.loads(result)
    assert result_data["analysis_type"] == "ecs_security_configuration"
    assert result_data["region"] == "us-east-1"
    assert result_data["clusters_analyzed"] == 1
    assert len(result_data["cluster_configurations"]) == 1

    # Verify mocks were called
    mock_get_region.assert_called_once()
    mock_validate.assert_called_once_with(["test-cluster"], "us-east-1")
    mock_collect_config.assert_called_once_with("us-east-1", "test-cluster")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_target_region")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.validate_clusters")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.collect_cluster_configuration")
async def test_tool_execution_multiple_clusters(
    mock_collect_config, mock_validate, mock_get_region
):
    """Test tool execution with multiple clusters."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mocks
    mock_get_region.return_value = "us-east-1"
    mock_validate.return_value = [
        "arn:aws:ecs:us-east-1:123456789012:cluster/cluster-1",
        "arn:aws:ecs:us-east-1:123456789012:cluster/cluster-2",
    ]
    mock_collect_config.side_effect = [
        {
            "cluster_name": "cluster-1",
            "region": "us-east-1",
            "cluster_metadata": {},
            "services": [],
            "task_definitions": [],
            "security_groups": [],
            "collection_errors": [],
        },
        {
            "cluster_name": "cluster-2",
            "region": "us-east-1",
            "cluster_metadata": {},
            "services": [],
            "task_definitions": [],
            "security_groups": [],
            "collection_errors": [],
        },
    ]

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

    # Execute the tool with multiple clusters
    result = await registered_tool(cluster_names=["cluster-1", "cluster-2"])

    # Verify the result
    import json

    result_data = json.loads(result)
    assert result_data["clusters_analyzed"] == 2
    assert len(result_data["cluster_configurations"]) == 2

    # Verify collect_config was called twice
    assert mock_collect_config.call_count == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.modules.security_analysis.get_target_region")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.validate_clusters")
@patch("awslabs.ecs_mcp_server.modules.security_analysis.collect_cluster_configuration")
async def test_tool_execution_with_collection_error(
    mock_collect_config, mock_validate, mock_get_region
):
    """Test tool execution when configuration collection fails for a cluster."""
    from awslabs.ecs_mcp_server.modules import security_analysis

    # Setup mocks
    mock_get_region.return_value = "us-east-1"
    mock_validate.return_value = ["arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"]
    mock_collect_config.side_effect = Exception("Collection failed")

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

    # Execute the tool with cluster_names
    result = await registered_tool(cluster_names=["test-cluster"])

    # Verify the result includes error information
    import json

    result_data = json.loads(result)
    assert result_data["clusters_analyzed"] == 1
    assert len(result_data["cluster_configurations"]) == 1
    # Should have error config
    assert "collection_error" in result_data["cluster_configurations"][0]
    assert "Collection failed" in result_data["cluster_configurations"][0]["collection_error"]
