"""
Unit tests for delete infrastructure functionality.

This file contains tests for the delete_infrastructure function in the ECS MCP Server.
It tests various scenarios for deleting ECS and ECR infrastructure, including:
- Basic deletion functionality
- Error handling
- Template validation and comparison
- Stack state handling
- API error handling
"""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.delete import delete_infrastructure
from awslabs.ecs_mcp_server.utils.security import ValidationError

# ----------------------------------------------------------------------------
# Basic Functionality Tests
# ----------------------------------------------------------------------------


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
async def test_delete_infrastructure_only_ecr_stack(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when only ECR stack exists."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            # No ECS stack
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
    assert result["ecs_stack"]["status"] == "not_found"

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_only_ecs_stack(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when only ECS stack exists."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            # No ECR stack
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"}
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
    assert result["ecr_stack"]["status"] == "not_found"
    assert result["ecs_stack"]["status"] == "deleting"

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecs-infrastructure")


# ----------------------------------------------------------------------------
# Template Validation and Comparison Tests
# ----------------------------------------------------------------------------


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
async def test_delete_infrastructure_mixed_template_match(mock_file, mock_get_aws_client):
    """Test deleting infrastructure when one template matches and one doesn't."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
        ]
    }

    # Mock get_template to return different responses for different stacks
    def mock_get_template_side_effect(StackName, **kwargs):
        if StackName == "test-app-ecr-infrastructure":
            return {"TemplateBody": '{"test": "template"}'}  # Match
        else:
            return {"TemplateBody": '{"test": "different"}'}  # No match

    mock_cf_client.get_template.side_effect = mock_get_template_side_effect
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
    assert result["ecs_stack"]["status"] == "not_found"
    assert "does not match" in result["ecs_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    assert mock_cf_client.get_template.call_count == 2
    mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_dict_template_body(mock_file, mock_get_aws_client):
    """Test template comparison when template body is a dict."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
        ]
    }
    mock_cf_client.get_template.return_value = {
        "TemplateBody": {"test": "template"}  # Dict instead of string
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
    assert result["ecr_stack"]["status"] == "deleting"

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
async def test_delete_infrastructure_invalid_json_template(mock_file, mock_get_aws_client):
    """Test template comparison when provided template is not valid JSON."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": {"test": "template"}}  # Dict
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
    assert "does not match" in result["ecr_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("builtins.open", new_callable=MagicMock)
@patch("awslabs.ecs_mcp_server.api.delete.os.path.exists")
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_ecr_template_mismatch(
    mock_get_aws_client, mock_exists, mock_open
):
    """Test delete_infrastructure when ECR template doesn't match deployed stack."""
    # Prepare mocks
    mock_exists.return_value = True

    # Create a mock CF client with the right behavior
    mock_cf_client = MagicMock()

    # Use functions that return the mock responses directly (no need for awaiting)
    def mock_list_stacks(*args, **kwargs):
        return {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "other-stack", "StackStatus": "CREATE_COMPLETE"},
            ]
        }

    def mock_get_template(*args, **kwargs):
        return {"TemplateBody": {"Resources": {"TestResource": {"Type": "AWS::ECR::Repository"}}}}

    # Assign the mock functions
    mock_cf_client.list_stacks = mock_list_stacks
    mock_cf_client.get_template = mock_get_template
    mock_get_aws_client.return_value = mock_cf_client

    # Mock open to return a different template
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = json.dumps(
        {"Resources": {"DifferentResource": {"Type": "AWS::ECR::Repository"}}}
    )
    mock_open.return_value = mock_file

    # Mock the validation function
    with patch("awslabs.ecs_mcp_server.api.delete.validate_cloudformation_template"):
        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr.json",
            ecs_template_path="/path/to/ecs.json",
        )

        # Verify the result
        assert result["operation"] == "delete"
        assert result["ecr_stack"]["status"] == "not_found"
        assert "Provided template does not match" in result["ecr_stack"]["message"]


# ----------------------------------------------------------------------------
# Stack State Tests
# ----------------------------------------------------------------------------


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
@patch("builtins.open", new_callable=MagicMock)
@patch("awslabs.ecs_mcp_server.api.delete.os.path.exists")
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_non_deletable_stack_state(
    mock_get_aws_client, mock_exists, mock_open
):
    """Test delete_infrastructure when stack is in a non-deletable state."""
    # Prepare mocks
    mock_exists.return_value = True

    # Create a mock CF client with the right behavior
    mock_cf_client = MagicMock()

    # Define mock functions
    def mock_list_stacks(*args, **kwargs):
        return {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "UPDATE_IN_PROGRESS"},
            ]
        }

    def mock_get_template(*args, **kwargs):
        return {"TemplateBody": "template-content"}

    # For delete_stack, use a regular MagicMock since it doesn't return anything
    mock_cf_client.list_stacks = mock_list_stacks
    mock_cf_client.get_template = mock_get_template
    mock_cf_client.delete_stack = MagicMock()
    mock_get_aws_client.return_value = mock_cf_client

    # Mock open to return matching templates
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = "template-content"
    mock_open.return_value = mock_file

    # Mock the validation function
    with patch("awslabs.ecs_mcp_server.api.delete.validate_cloudformation_template"):
        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr.json",
            ecs_template_path="/path/to/ecs.json",
        )

        # Verify the ECS stack was skipped due to being in UPDATE_IN_PROGRESS state
        assert result["operation"] == "delete"
        assert result["ecs_stack"]["status"] == "skipped"
        assert "UPDATE_IN_PROGRESS" in result["ecs_stack"]["message"]

        # Verify the ECR stack was deleted since it's in a deletable state
        mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")


# ----------------------------------------------------------------------------
# Error Handling Tests
# ----------------------------------------------------------------------------


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
async def test_delete_infrastructure_delete_stack_client_error(mock_file, mock_get_aws_client):
    """Test error handling when delete_stack API call fails with ClientError."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
    mock_cf_client.delete_stack.side_effect = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
                "Message": "User not authorized to perform cloudformation:DeleteStack",
            }
        },
        "DeleteStack",
    )
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
    assert "AccessDenied" in result["ecr_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_called_once()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open")
async def test_delete_infrastructure_file_read_error(mock_file, mock_get_aws_client):
    """Test error handling when template file cannot be read."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
        ]
    }
    mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
    mock_get_aws_client.return_value = mock_cf_client

    # Mock file open to raise an exception
    mock_file.side_effect = IOError("File not found")

    # Call the function
    result = await delete_infrastructure(
        app_name="test-app",
        ecr_template_path="/path/to/ecr-template.json",
        ecs_template_path="/path/to/ecs-template.json",
    )

    # Verify the result
    assert result["operation"] == "delete"
    assert result["ecr_stack"]["status"] == "not_found"
    assert "Error comparing templates" in result["ecr_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
@patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
async def test_delete_infrastructure_get_template_error(mock_file, mock_get_aws_client):
    """Test error handling when get_template API call fails."""
    # Mock CloudFormation client
    mock_cf_client = MagicMock()
    mock_cf_client.list_stacks.return_value = {
        "StackSummaries": [
            {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
        ]
    }
    mock_cf_client.get_template.side_effect = ClientError(
        {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}}, "GetTemplate"
    )
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
    assert "Error comparing templates" in result["ecr_stack"]["message"]

    # Verify CloudFormation client was called correctly
    mock_get_aws_client.assert_called_once_with("cloudformation")
    mock_cf_client.list_stacks.assert_called_once()
    mock_cf_client.get_template.assert_called_once()
    mock_cf_client.delete_stack.assert_not_called()


@pytest.mark.anyio
@patch("builtins.open", new_callable=MagicMock)
@patch("awslabs.ecs_mcp_server.api.delete.os.path.exists")
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_template_comparison_error(
    mock_get_aws_client, mock_exists, mock_open
):
    """Test delete_infrastructure when template comparison fails."""
    # Prepare mocks
    mock_exists.return_value = True

    # Create a mock CF client with the right behavior
    mock_cf_client = MagicMock()

    # Define mock list_stacks function
    def mock_list_stacks(*args, **kwargs):
        return {
            "StackSummaries": [
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }

    # Define mock get_template function that raises an exception
    def mock_get_template(*args, **kwargs):
        raise Exception("Cannot retrieve template")

    # Assign the mock functions
    mock_cf_client.list_stacks = mock_list_stacks
    mock_cf_client.get_template = mock_get_template
    mock_get_aws_client.return_value = mock_cf_client

    # Mock open to return a template
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = json.dumps(
        {"Resources": {"TestResource": {"Type": "AWS::ECS::Cluster"}}}
    )
    mock_open.return_value = mock_file

    # Mock the validation function
    with patch("awslabs.ecs_mcp_server.api.delete.validate_cloudformation_template"):
        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr.json",
            ecs_template_path="/path/to/ecs.json",
        )

        # Verify the result
        assert result["operation"] == "delete"
        assert result["ecs_stack"]["status"] == "not_found"
        assert "Error comparing templates" in result["ecs_stack"]["message"]


@pytest.mark.anyio
@patch("builtins.open", new_callable=MagicMock)
@patch("awslabs.ecs_mcp_server.api.delete.os.path.exists")
@patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
async def test_delete_infrastructure_error_deleting_stack(
    mock_get_aws_client, mock_exists, mock_open
):
    """Test delete_infrastructure when deleting a stack fails."""
    # Prepare mocks
    mock_exists.return_value = True

    # Create a mock CF client with the right behavior
    mock_cf_client = MagicMock()

    # Define mock functions
    def mock_list_stacks(*args, **kwargs):
        return {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }

    def mock_get_template(*args, **kwargs):
        return {"TemplateBody": "template-content"}

    def mock_delete_stack(*args, **kwargs):
        raise Exception("Permission denied")

    # Assign the mock functions
    mock_cf_client.list_stacks = mock_list_stacks
    mock_cf_client.get_template = mock_get_template
    mock_cf_client.delete_stack = mock_delete_stack
    mock_get_aws_client.return_value = mock_cf_client

    # Mock open to return matching templates
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = "template-content"
    mock_open.return_value = mock_file

    # Mock the validation function
    with patch("awslabs.ecs_mcp_server.api.delete.validate_cloudformation_template"):
        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr.json",
            ecs_template_path="/path/to/ecs.json",
        )

        # Verify the result
        assert result["operation"] == "delete"
        assert result["ecr_stack"]["status"] == "error"
        assert "Error deleting stack" in result["ecr_stack"]["message"]


# ----------------------------------------------------------------------------
# Validation Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.delete.os.path.exists")
async def test_delete_infrastructure_template_validation_fails(mock_exists):
    """Test delete_infrastructure when template validation fails."""
    # Set up mocks
    mock_exists.return_value = True

    # Mock the validation function to raise an error before we even need a CF client
    with patch(
        "awslabs.ecs_mcp_server.api.delete.validate_cloudformation_template"
    ) as mock_validate:
        # Have the first call raise an exception
        mock_validate.side_effect = ValidationError("Invalid CloudFormation template")

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr.json",
            ecs_template_path="/path/to/ecs.json",
        )

        # Verify the result
        assert result["operation"] == "delete"
        assert result["status"] == "error"
        assert "Template validation failed" in result["message"]
