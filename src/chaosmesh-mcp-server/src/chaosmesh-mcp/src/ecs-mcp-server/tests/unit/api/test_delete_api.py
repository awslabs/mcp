"""
Unit tests for delete infrastructure API functionality.

This file contains tests for the delete_infrastructure function in the ECS MCP Server API.
It tests various scenarios for deleting ECS and ECR infrastructure.
"""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from awslabs.ecs_mcp_server.api.delete import delete_infrastructure


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_no_stacks(mock_get_aws_client):
    """Test deleting infrastructure when no stacks exist."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {"StackSummaries": []}
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "not_found"
    assert result["ecs_stack"]["status"] == "not_found"

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_with_stacks(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when stacks exist and templates match."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "deleting"
    assert result["ecs_stack"]["status"] == "deleting"

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    assert mock_cf_client.delete_stack.call_count == 2
    mock_cf_client.delete_stack.assert_any_call(StackName="test-app-ecs-infrastructure")
    mock_cf_client.delete_stack.assert_any_call(StackName="test-app-ecr-infrastructure")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_template_mismatch(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when templates don't match."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "different-template"}'}
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "not_found"
    assert result["ecs_stack"]["status"] == "not_found"
    assert "does not match" in result["ecr_stack"]["message"]
    assert "does not match" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_stack_in_progress(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when stacks are in progress."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_IN_PROGRESS"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "UPDATE_IN_PROGRESS"},
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "skipped"
    assert result["ecs_stack"]["status"] == "skipped"
    assert "CREATE_IN_PROGRESS" in result["ecr_stack"]["message"]
    assert "UPDATE_IN_PROGRESS" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_list_stacks_error(mock_get_aws_client):
    """Test error handling when listing stacks fails."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.side_effect = Exception("API Error")
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["status"] == "error"
    assert "Error listing CloudFormation stacks" in result["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_delete_error(mock_file, mock_get_aws_client):
    """Test error handling when deleting stacks fails."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
    mock_cf_client.delete_stack.side_effect = Exception("Delete failed")
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "error"
    assert result["ecs_stack"]["status"] == "error"
    assert "Error deleting stack" in result["ecr_stack"]["message"]
    assert "Error deleting stack" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    assert mock_cf_client.delete_stack.call_count == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_file_not_found(mock_file, mock_get_aws_client):
    """Test error handling when template file is not found."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }
    mock_get_aws_client.return_value = mock_cf_client

    # Mock file open to raise FileNotFoundError
    mock_file.side_effect = FileNotFoundError("File not found")

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert "Error comparing templates" in result["ecr_stack"]["message"]
    assert "Error comparing templates" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
async def test_delete_infrastructure_invalid_json(mock_file, mock_get_aws_client):
    """Test error handling when template file contains invalid JSON."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }
    mock_get_aws_client.return_value = mock_cf_client

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert "Provided template does not match deployed stack" in result["ecr_stack"]["message"]
    assert "Provided template does not match deployed stack" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()
