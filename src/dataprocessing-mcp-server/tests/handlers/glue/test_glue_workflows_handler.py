# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# ruff: noqa: D101, D102, D103
"""Tests for the Glue Workflows and Triggers handler."""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from awslabs.dataprocessing_mcp_server.handlers.glue.glue_worklows_handler import GlueWorkflowAndTriggerHandler


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_glue_workflow_handler_initialization(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client

    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)

    # Verify that create_boto3_client was called with 'glue'
    mock_create_client.assert_called_once_with("glue")

    # Verify that all tools were registered
    assert mock_mcp.tool.call_count == 2

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]["name"] for call_args in call_args_list]

    # Verify that all expected tools were registered
    assert "manage_aws_glue_workflows" in tool_names
    assert "manage_aws_glue_triggers" in tool_names


# Tests for manage_aws_glue_workflows method

@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
async def test_create_workflow_success(mock_get_account_id, mock_get_region, mock_prepare_tags, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the resource tags
    mock_prepare_tags.return_value = {"ManagedBy": "MCP"}
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the create_workflow response
    mock_glue_client.create_workflow.return_value = {"Name": "test-workflow"}

    # Call the manage_aws_glue_workflows method with create-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="create-workflow",
        workflow_name="test-workflow",
        workflow_definition={
            "Description": "Test workflow",
            "DefaultRunProperties": {"ENV": "test"},
            "MaxConcurrentRuns": 1
        }
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully created workflow test-workflow" in result.content[0].text
    assert result.workflow_name == "test-workflow"

    # Verify that create_workflow was called with the correct parameters
    mock_glue_client.create_workflow.assert_called_once()
    args, kwargs = mock_glue_client.create_workflow.call_args
    assert kwargs["Name"] == "test-workflow"
    assert kwargs["Description"] == "Test workflow"
    assert kwargs["DefaultRunProperties"] == {"ENV": "test"}
    assert kwargs["MaxConcurrentRuns"] == 1
    assert kwargs["Tags"] == {"ManagedBy": "MCP"}


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_create_workflow_no_write_access(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server without write access
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=False)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_workflows method with create-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="create-workflow",
        workflow_name="test-workflow",
        workflow_definition={
            "Description": "Test workflow"
        }
    )

    # Verify the result indicates an error due to no write access
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Operation create-workflow is not allowed without write access" in result.content[0].text
    assert result.workflow_name == ""

    # Verify that create_workflow was NOT called
    mock_glue_client.create_workflow.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_workflow_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow response
    mock_glue_client.get_workflow.return_value = {
        "Workflow": {
            "Name": "test-workflow",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_workflows method with delete-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="delete-workflow",
        workflow_name="test-workflow"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully deleted workflow test-workflow" in result.content[0].text
    assert result.workflow_name == "test-workflow"

    # Verify that delete_workflow was called with the correct parameters
    mock_glue_client.delete_workflow.assert_called_once_with(Name="test-workflow")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_workflow_not_mcp_managed(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return False
    mock_is_mcp_managed.return_value = False
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow response
    mock_glue_client.get_workflow.return_value = {
        "Workflow": {
            "Name": "test-workflow",
            "Tags": {}  # No MCP tags
        }
    }

    # Call the manage_aws_glue_workflows method with delete-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="delete-workflow",
        workflow_name="test-workflow"
    )

    # Verify the result indicates an error because the workflow is not MCP managed
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Cannot delete workflow test-workflow - it is not managed by the MCP server" in result.content[0].text
    assert result.workflow_name == "test-workflow"

    # Verify that delete_workflow was NOT called
    mock_glue_client.delete_workflow.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_workflow_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow response
    mock_workflow_details = {
        "Name": "test-workflow",
        "Description": "Test workflow",
        "CreatedOn": "2023-01-01T00:00:00Z"
    }
    mock_glue_client.get_workflow.return_value = {
        "Workflow": mock_workflow_details
    }

    # Call the manage_aws_glue_workflows method with get-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="get-workflow",
        workflow_name="test-workflow"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved workflow test-workflow" in result.content[0].text
    assert result.workflow_name == "test-workflow"
    assert result.workflow_details == mock_workflow_details

    # Verify that get_workflow was called with the correct parameters
    mock_glue_client.get_workflow.assert_called_once_with(Name="test-workflow")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_workflow_with_include_graph(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow response
    mock_workflow_details = {
        "Name": "test-workflow",
        "Description": "Test workflow",
        "CreatedOn": "2023-01-01T00:00:00Z",
        "Graph": {
            "Nodes": [{"Type": "JOB", "Name": "test-job"}],
            "Edges": []
        }
    }
    mock_glue_client.get_workflow.return_value = {
        "Workflow": mock_workflow_details
    }

    # Call the manage_aws_glue_workflows method with get-workflow operation and include_graph
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="get-workflow",
        workflow_name="test-workflow",
        workflow_definition={"include_graph": True}
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved workflow test-workflow" in result.content[0].text
    assert result.workflow_name == "test-workflow"
    assert result.workflow_details == mock_workflow_details

    # Verify that get_workflow was called with the correct parameters
    mock_glue_client.get_workflow.assert_called_once_with(Name="test-workflow", IncludeGraph=True)


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_list_workflows_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the list_workflows response - AWS API returns workflow names as strings
    mock_glue_client.list_workflows.return_value = {
        "Workflows": ["workflow1", "workflow2"],
        "NextToken": "next-token"
    }

    # Call the manage_aws_glue_workflows method with list-workflows operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="list-workflows",
        max_results=10,
        next_token="token"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved workflows" in result.content[0].text
    assert len(result.workflows) == 2
    assert result.workflows[0]["Name"] == "workflow1"
    assert result.workflows[1]["Name"] == "workflow2"
    assert result.next_token == "next-token"

    # Verify that list_workflows was called with the correct parameters
    mock_glue_client.list_workflows.assert_called_once_with(MaxResults=10, NextToken="token")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_start_workflow_run_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow response
    mock_glue_client.get_workflow.return_value = {
        "Workflow": {
            "Name": "test-workflow",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Mock the start_workflow_run response
    mock_glue_client.start_workflow_run.return_value = {
        "RunId": "run-123"
    }

    # Call the manage_aws_glue_workflows method with start-workflow-run operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="start-workflow-run",
        workflow_name="test-workflow",
        workflow_definition={"run_properties": {"ENV": "test"}}
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully started workflow run for test-workflow" in result.content[0].text
    assert result.workflow_name == "test-workflow"
    assert result.run_id == "run-123"

    # Verify that start_workflow_run was called with the correct parameters
    mock_glue_client.start_workflow_run.assert_called_once_with(
        Name="test-workflow",
        RunProperties={"ENV": "test"}
    )


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_invalid_operation(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_workflows method with an invalid operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="invalid-operation",
        workflow_name="test-workflow"
    )

    # Verify the result indicates an error due to invalid operation
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Invalid operation: invalid-operation" in result.content[0].text
    assert result.workflow_name == "test-workflow"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_workflow_not_found(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_workflow to raise EntityNotFoundException
    mock_glue_client.exceptions.EntityNotFoundException = ClientError(
        {"Error": {"Code": "EntityNotFoundException", "Message": "Workflow not found"}},
        "get_workflow"
    )
    mock_glue_client.get_workflow.side_effect = mock_glue_client.exceptions.EntityNotFoundException

    # Call the manage_aws_glue_workflows method with delete-workflow operation
    result = await handler.manage_aws_glue_workflows(
        mock_ctx,
        operation="delete-workflow",
        workflow_name="test-workflow"
    )

    # Verify the result indicates an error because the workflow was not found
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Workflow test-workflow not found" in result.content[0].text
    assert result.workflow_name == "test-workflow"

    # Verify that delete_workflow was NOT called
    mock_glue_client.delete_workflow.assert_not_called()


# Tests for manage_aws_glue_triggers method

@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags")
async def test_create_trigger_success(mock_prepare_tags, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the resource tags
    mock_prepare_tags.return_value = {"ManagedBy": "MCP"}
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the create_trigger response
    mock_glue_client.create_trigger.return_value = {"Name": "test-trigger"}

    # Call the manage_aws_glue_triggers method with create-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="create-trigger",
        trigger_name="test-trigger",
        trigger_definition={
            "Type": "SCHEDULED",
            "Schedule": "cron(0 12 * * ? *)",
            "Actions": [{"JobName": "test-job"}],
            "Description": "Test trigger",
            "StartOnCreation": True
        }
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully created trigger test-trigger" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that create_trigger was called with the correct parameters
    mock_glue_client.create_trigger.assert_called_once()
    args, kwargs = mock_glue_client.create_trigger.call_args
    assert kwargs["Name"] == "test-trigger"
    assert kwargs["Type"] == "SCHEDULED"
    assert kwargs["Schedule"] == "cron(0 12 * * ? *)"
    assert kwargs["Actions"] == [{"JobName": "test-job"}]
    assert kwargs["Description"] == "Test trigger"
    assert kwargs["StartOnCreation"] == True
    assert kwargs["Tags"] == {"ManagedBy": "MCP"}


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_create_trigger_no_write_access(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server without write access
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=False)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_triggers method with create-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="create-trigger",
        trigger_name="test-trigger",
        trigger_definition={
            "Type": "SCHEDULED",
            "Actions": [{"JobName": "test-job"}]
        }
    )

    # Verify the result indicates an error due to no write access
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Operation create-trigger is not allowed without write access" in result.content[0].text
    assert result.trigger_name == ""

    # Verify that create_trigger was NOT called
    mock_glue_client.create_trigger.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_trigger_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger response
    mock_glue_client.get_trigger.return_value = {
        "Trigger": {
            "Name": "test-trigger",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_triggers method with delete-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="delete-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully deleted trigger test-trigger" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that delete_trigger was called with the correct parameters
    mock_glue_client.delete_trigger.assert_called_once_with(Name="test-trigger")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_delete_trigger_not_mcp_managed(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return False
    mock_is_mcp_managed.return_value = False
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger response
    mock_glue_client.get_trigger.return_value = {
        "Trigger": {
            "Name": "test-trigger",
            "Tags": {}  # No MCP tags
        }
    }

    # Call the manage_aws_glue_triggers method with delete-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="delete-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result indicates an error because the trigger is not MCP managed
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Cannot delete trigger test-trigger - it is not managed by the MCP server" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that delete_trigger was NOT called
    mock_glue_client.delete_trigger.assert_not_called()


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_trigger_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger response
    mock_trigger_details = {
        "Name": "test-trigger",
        "Type": "SCHEDULED",
        "Schedule": "cron(0 12 * * ? *)",
        "Actions": [{"JobName": "test-job"}],
        "Description": "Test trigger"
    }
    mock_glue_client.get_trigger.return_value = {
        "Trigger": mock_trigger_details
    }

    # Call the manage_aws_glue_triggers method with get-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="get-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved trigger test-trigger" in result.content[0].text
    assert result.trigger_name == "test-trigger"
    assert result.trigger_details == mock_trigger_details

    # Verify that get_trigger was called with the correct parameters
    mock_glue_client.get_trigger.assert_called_once_with(Name="test-trigger")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_get_triggers_success(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_triggers response
    mock_glue_client.get_triggers.return_value = {
        "Triggers": [
            {
                "Name": "trigger1",
                "Type": "SCHEDULED"
            },
            {
                "Name": "trigger2",
                "Type": "CONDITIONAL"
            }
        ],
        "NextToken": "next-token"
    }

    # Call the manage_aws_glue_triggers method with get-triggers operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="get-triggers",
        max_results=10,
        next_token="token"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully retrieved triggers" in result.content[0].text
    assert len(result.triggers) == 2
    assert result.triggers[0]["Name"] == "trigger1"
    assert result.triggers[1]["Name"] == "trigger2"
    assert result.next_token == "next-token"

    # Verify that get_triggers was called with the correct parameters
    mock_glue_client.get_triggers.assert_called_once_with(MaxResults=10, NextToken="token")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_start_trigger_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger response
    mock_glue_client.get_trigger.return_value = {
        "Trigger": {
            "Name": "test-trigger",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_triggers method with start-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="start-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully started trigger test-trigger" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that start_trigger was called with the correct parameters
    mock_glue_client.start_trigger.assert_called_once_with(Name="test-trigger")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id")
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed")
async def test_stop_trigger_success(mock_is_mcp_managed, mock_get_account_id, mock_get_region, mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Mock the region and account ID
    mock_get_region.return_value = "us-east-1"
    mock_get_account_id.return_value = "123456789012"
    
    # Mock the is_resource_mcp_managed to return True
    mock_is_mcp_managed.return_value = True
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger response
    mock_glue_client.get_trigger.return_value = {
        "Trigger": {
            "Name": "test-trigger",
            "Tags": {"ManagedBy": "MCP"}
        }
    }

    # Call the manage_aws_glue_triggers method with stop-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="stop-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Successfully stopped trigger test-trigger" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that stop_trigger was called with the correct parameters
    mock_glue_client.stop_trigger.assert_called_once_with(Name="test-trigger")


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_trigger_invalid_operation(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server with write access
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_aws_glue_triggers method with an invalid operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="invalid-operation",
        trigger_name="test-trigger"
    )

    # Verify the result indicates an error due to invalid operation
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Invalid operation: invalid-operation" in result.content[0].text
    assert result.trigger_name == "test-trigger"


@pytest.mark.asyncio
@patch("awslabs.dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client")
async def test_trigger_not_found(mock_create_client):
    # Create a mock Glue client
    mock_glue_client = MagicMock()
    mock_create_client.return_value = mock_glue_client
    
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the Glue Workflow handler with the mock MCP server
    handler = GlueWorkflowAndTriggerHandler(mock_mcp, allow_write=True)
    handler.glue_client = mock_glue_client

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Mock the get_trigger to raise EntityNotFoundException
    mock_glue_client.exceptions.EntityNotFoundException = ClientError(
        {"Error": {"Code": "EntityNotFoundException", "Message": "Trigger not found"}},
        "get_trigger"
    )
    mock_glue_client.get_trigger.side_effect = mock_glue_client.exceptions.EntityNotFoundException

    # Call the manage_aws_glue_triggers method with delete-trigger operation
    result = await handler.manage_aws_glue_triggers(
        mock_ctx,
        operation="delete-trigger",
        trigger_name="test-trigger"
    )

    # Verify the result indicates an error because the trigger was not found
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Trigger test-trigger not found" in result.content[0].text
    assert result.trigger_name == "test-trigger"

    # Verify that delete_trigger was NOT called
    mock_glue_client.delete_trigger.assert_not_called()
