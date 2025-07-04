"""Tests for the AWS Bedrock Data Automation MCP Server."""

import pytest
from awslabs.aws_bedrock_data_automation_mcp_server.server import (
    analyze_asset_tool,
    get_project_details_tool,
    get_projects_tool,
)
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_projects_tool():
    """Test the get_projects_tool function."""
    mock_projects = [{'projectArn': 'test-arn', 'name': 'test-project'}]

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.list_projects',
        new=AsyncMock(return_value=mock_projects),
    ):
        result = await get_projects_tool()
        assert result == {'projects': mock_projects}


@pytest.mark.asyncio
async def test_get_project_details_tool():
    """Test the get_project_details_tool function."""
    mock_project = {
        'projectArn': 'test-arn',
        'name': 'test-project',
        'description': 'Test project description',
    }

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.get_project',
        new=AsyncMock(return_value=mock_project),
    ):
        result = await get_project_details_tool(projectArn='test-arn')
        assert result == mock_project


@pytest.mark.asyncio
async def test_analyze_asset_tool():
    """Test the analyze_asset_tool function."""
    mock_results = {'standardOutput': {'key': 'value'}, 'customOutput': {'key2': 'value2'}}

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.invoke_data_automation_and_get_results',
        new=AsyncMock(return_value=mock_results),
    ):
        result = await analyze_asset_tool(assetPath='/path/to/asset.pdf')
        assert result == mock_results


@pytest.mark.asyncio
async def test_analyze_asset_tool_with_project_arn():
    """Test the analyze_asset_tool function with a project ARN."""
    mock_results = {'standardOutput': {'key': 'value'}, 'customOutput': {'key2': 'value2'}}

    mock_invoke = AsyncMock(return_value=mock_results)

    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.invoke_data_automation_and_get_results',
        new=mock_invoke,
    ):
        result = await analyze_asset_tool(
            assetPath='/path/to/asset.pdf', projectArn='test-project-arn'
        )

        mock_invoke.assert_called_once_with('/path/to/asset.pdf', 'test-project-arn')
        assert result == mock_results


@pytest.mark.asyncio
async def test_get_projects_tool_error():
    """Test the get_projects_tool function when an error occurs."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.list_projects',
        new=AsyncMock(side_effect=Exception('Test error')),
    ):
        with pytest.raises(ValueError, match='Error listing projects: Test error'):
            await get_projects_tool()


@pytest.mark.asyncio
async def test_get_project_details_tool_error():
    """Test the get_project_details_tool function when an error occurs."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.get_project',
        new=AsyncMock(side_effect=Exception('Test error')),
    ):
        with pytest.raises(ValueError, match='Error getting project details: Test error'):
            await get_project_details_tool(projectArn='test-arn')


@pytest.mark.asyncio
async def test_analyze_asset_tool_error():
    """Test the analyze_asset_tool function when an error occurs."""
    with patch(
        'awslabs.aws_bedrock_data_automation_mcp_server.server.invoke_data_automation_and_get_results',
        new=AsyncMock(side_effect=Exception('Test error')),
    ):
        with pytest.raises(ValueError, match='Error analyzing asset: Test error'):
            await analyze_asset_tool(assetPath='/path/to/asset.pdf')
