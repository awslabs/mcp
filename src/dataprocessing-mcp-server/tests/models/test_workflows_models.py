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

"""Tests for the Glue Workflows models."""

import pytest
from awslabs.dataprocessing_mcp_server.models.glue_models import (
    # Workflow response models
    CreateWorkflowResponse,
    DeleteWorkflowResponse,
    GetWorkflowResponse,
    ListWorkflowsResponse,
    StartWorkflowRunResponse,
    # Trigger response models
    CreateTriggerResponse,
    DeleteTriggerResponse,
    GetTriggerResponse,
    GetTriggersResponse,
    StartTriggerResponse,
    StopTriggerResponse,
)
from mcp.types import TextContent
from pydantic import ValidationError


class TestWorkflowResponseModels:
    """Tests for the workflow response models."""

    def test_create_workflow_response(self):
        """Test creating a CreateWorkflowResponse."""
        response = CreateWorkflowResponse(
            isError=False,
            workflow_name="test-workflow",
            content=[TextContent(type="text", text="Successfully created workflow")],
        )
        
        assert response.isError is False
        assert response.workflow_name == "test-workflow"
        assert response.operation == "create-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully created workflow"

    def test_create_workflow_response_with_error(self):
        """Test creating a CreateWorkflowResponse with error."""
        response = CreateWorkflowResponse(
            isError=True,
            workflow_name="test-workflow",
            content=[TextContent(type="text", text="Failed to create workflow")],
        )
        
        assert response.isError is True
        assert response.workflow_name == "test-workflow"
        assert response.operation == "create-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to create workflow"

    def test_delete_workflow_response(self):
        """Test creating a DeleteWorkflowResponse."""
        response = DeleteWorkflowResponse(
            isError=False,
            workflow_name="test-workflow",
            content=[TextContent(type="text", text="Successfully deleted workflow")],
        )
        
        assert response.isError is False
        assert response.workflow_name == "test-workflow"
        assert response.operation == "delete-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully deleted workflow"

    def test_delete_workflow_response_with_error(self):
        """Test creating a DeleteWorkflowResponse with error."""
        response = DeleteWorkflowResponse(
            isError=True,
            workflow_name="test-workflow",
            content=[TextContent(type="text", text="Failed to delete workflow")],
        )
        
        assert response.isError is True
        assert response.workflow_name == "test-workflow"
        assert response.operation == "delete-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to delete workflow"

    def test_get_workflow_response(self):
        """Test creating a GetWorkflowResponse."""
        workflow_details = {
            "Name": "test-workflow",
            "Description": "Test workflow",
            "CreatedOn": "2023-01-01T00:00:00Z",
            "LastModifiedOn": "2023-01-02T00:00:00Z",
            "LastRun": {
                "Name": "test-run",
                "StartedOn": "2023-01-03T00:00:00Z",
                "CompletedOn": "2023-01-03T01:00:00Z",
                "Status": "COMPLETED",
            },
        }
        
        response = GetWorkflowResponse(
            isError=False,
            workflow_name="test-workflow",
            workflow_details=workflow_details,
            content=[TextContent(type="text", text="Successfully retrieved workflow")],
        )
        
        assert response.isError is False
        assert response.workflow_name == "test-workflow"
        assert response.workflow_details == workflow_details
        assert response.operation == "get-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved workflow"

    def test_get_workflow_response_with_error(self):
        """Test creating a GetWorkflowResponse with error."""
        response = GetWorkflowResponse(
            isError=True,
            workflow_name="test-workflow",
            workflow_details={},
            content=[TextContent(type="text", text="Failed to retrieve workflow")],
        )
        
        assert response.isError is True
        assert response.workflow_name == "test-workflow"
        assert response.workflow_details == {}
        assert response.operation == "get-workflow"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve workflow"

    def test_list_workflows_response(self):
        """Test creating a ListWorkflowsResponse."""
        workflows = [
            {
                "Name": "workflow1",
                "CreatedOn": "2023-01-01T00:00:00Z",
            },
            {
                "Name": "workflow2",
                "CreatedOn": "2023-01-02T00:00:00Z",
            },
        ]
        
        response = ListWorkflowsResponse(
            isError=False,
            workflows=workflows,
            next_token="next-token",
            content=[TextContent(type="text", text="Successfully retrieved workflows")],
        )
        
        assert response.isError is False
        assert len(response.workflows) == 2
        assert response.workflows[0]["Name"] == "workflow1"
        assert response.workflows[1]["Name"] == "workflow2"
        assert response.next_token == "next-token"
        assert response.operation == "list-workflows"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved workflows"

    def test_list_workflows_response_with_error(self):
        """Test creating a ListWorkflowsResponse with error."""
        response = ListWorkflowsResponse(
            isError=True,
            workflows=[],
            content=[TextContent(type="text", text="Failed to retrieve workflows")],
        )
        
        assert response.isError is True
        assert len(response.workflows) == 0
        assert response.next_token is None  # Default value
        assert response.operation == "list-workflows"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve workflows"

    def test_start_workflow_run_response(self):
        """Test creating a StartWorkflowRunResponse."""
        response = StartWorkflowRunResponse(
            isError=False,
            workflow_name="test-workflow",
            run_id="run-12345",
            content=[TextContent(type="text", text="Successfully started workflow run")],
        )
        
        assert response.isError is False
        assert response.workflow_name == "test-workflow"
        assert response.run_id == "run-12345"
        assert response.operation == "start-workflow-run"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully started workflow run"

    def test_start_workflow_run_response_with_error(self):
        """Test creating a StartWorkflowRunResponse with error."""
        response = StartWorkflowRunResponse(
            isError=True,
            workflow_name="test-workflow",
            run_id="",
            content=[TextContent(type="text", text="Failed to start workflow run")],
        )
        
        assert response.isError is True
        assert response.workflow_name == "test-workflow"
        assert response.run_id == ""
        assert response.operation == "start-workflow-run"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to start workflow run"


class TestTriggerResponseModels:
    """Tests for the trigger response models."""

    def test_create_trigger_response(self):
        """Test creating a CreateTriggerResponse."""
        response = CreateTriggerResponse(
            isError=False,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Successfully created trigger")],
        )
        
        assert response.isError is False
        assert response.trigger_name == "test-trigger"
        assert response.operation == "create-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully created trigger"

    def test_create_trigger_response_with_error(self):
        """Test creating a CreateTriggerResponse with error."""
        response = CreateTriggerResponse(
            isError=True,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Failed to create trigger")],
        )
        
        assert response.isError is True
        assert response.trigger_name == "test-trigger"
        assert response.operation == "create-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to create trigger"

    def test_delete_trigger_response(self):
        """Test creating a DeleteTriggerResponse."""
        response = DeleteTriggerResponse(
            isError=False,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Successfully deleted trigger")],
        )
        
        assert response.isError is False
        assert response.trigger_name == "test-trigger"
        assert response.operation == "delete-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully deleted trigger"

    def test_delete_trigger_response_with_error(self):
        """Test creating a DeleteTriggerResponse with error."""
        response = DeleteTriggerResponse(
            isError=True,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Failed to delete trigger")],
        )
        
        assert response.isError is True
        assert response.trigger_name == "test-trigger"
        assert response.operation == "delete-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to delete trigger"

    def test_get_trigger_response(self):
        """Test creating a GetTriggerResponse."""
        trigger_details = {
            "Name": "test-trigger",
            "Type": "SCHEDULED",
            "Schedule": "cron(0 0 * * ? *)",
            "State": "CREATED",
            "Actions": [
                {
                    "JobName": "test-job",
                    "Arguments": {"--key": "value"},
                }
            ],
            "CreatedOn": "2023-01-01T00:00:00Z",
        }
        
        response = GetTriggerResponse(
            isError=False,
            trigger_name="test-trigger",
            trigger_details=trigger_details,
            content=[TextContent(type="text", text="Successfully retrieved trigger")],
        )
        
        assert response.isError is False
        assert response.trigger_name == "test-trigger"
        assert response.trigger_details == trigger_details
        assert response.operation == "get-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved trigger"

    def test_get_trigger_response_with_error(self):
        """Test creating a GetTriggerResponse with error."""
        response = GetTriggerResponse(
            isError=True,
            trigger_name="test-trigger",
            trigger_details={},
            content=[TextContent(type="text", text="Failed to retrieve trigger")],
        )
        
        assert response.isError is True
        assert response.trigger_name == "test-trigger"
        assert response.trigger_details == {}
        assert response.operation == "get-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve trigger"

    def test_get_triggers_response(self):
        """Test creating a GetTriggersResponse."""
        triggers = [
            {
                "Name": "trigger1",
                "Type": "SCHEDULED",
                "State": "CREATED",
            },
            {
                "Name": "trigger2",
                "Type": "CONDITIONAL",
                "State": "ACTIVATED",
            },
        ]
        
        response = GetTriggersResponse(
            isError=False,
            triggers=triggers,
            next_token="next-token",
            content=[TextContent(type="text", text="Successfully retrieved triggers")],
        )
        
        assert response.isError is False
        assert len(response.triggers) == 2
        assert response.triggers[0]["Name"] == "trigger1"
        assert response.triggers[1]["Name"] == "trigger2"
        assert response.next_token == "next-token"
        assert response.operation == "get-triggers"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully retrieved triggers"

    def test_get_triggers_response_with_error(self):
        """Test creating a GetTriggersResponse with error."""
        response = GetTriggersResponse(
            isError=True,
            triggers=[],
            content=[TextContent(type="text", text="Failed to retrieve triggers")],
        )
        
        assert response.isError is True
        assert len(response.triggers) == 0
        assert response.next_token is None  # Default value
        assert response.operation == "get-triggers"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to retrieve triggers"

    def test_start_trigger_response(self):
        """Test creating a StartTriggerResponse."""
        response = StartTriggerResponse(
            isError=False,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Successfully started trigger")],
        )
        
        assert response.isError is False
        assert response.trigger_name == "test-trigger"
        assert response.operation == "start-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully started trigger"

    def test_start_trigger_response_with_error(self):
        """Test creating a StartTriggerResponse with error."""
        response = StartTriggerResponse(
            isError=True,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Failed to start trigger")],
        )
        
        assert response.isError is True
        assert response.trigger_name == "test-trigger"
        assert response.operation == "start-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to start trigger"

    def test_stop_trigger_response(self):
        """Test creating a StopTriggerResponse."""
        response = StopTriggerResponse(
            isError=False,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Successfully stopped trigger")],
        )
        
        assert response.isError is False
        assert response.trigger_name == "test-trigger"
        assert response.operation == "stop-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Successfully stopped trigger"

    def test_stop_trigger_response_with_error(self):
        """Test creating a StopTriggerResponse with error."""
        response = StopTriggerResponse(
            isError=True,
            trigger_name="test-trigger",
            content=[TextContent(type="text", text="Failed to stop trigger")],
        )
        
        assert response.isError is True
        assert response.trigger_name == "test-trigger"
        assert response.operation == "stop-trigger"  # Default value
        assert len(response.content) == 1
        assert response.content[0].text == "Failed to stop trigger"


class TestValidationErrors:
    """Tests for validation errors in the models."""

    def test_create_workflow_response_missing_required_fields(self):
        """Test that creating a CreateWorkflowResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            CreateWorkflowResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing workflow_name")]
            )

    def test_delete_workflow_response_missing_required_fields(self):
        """Test that creating a DeleteWorkflowResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            DeleteWorkflowResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing workflow_name")]
            )

    def test_get_workflow_response_missing_required_fields(self):
        """Test that creating a GetWorkflowResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            GetWorkflowResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing workflow_name and workflow_details")]
            )

        with pytest.raises(ValidationError):
            GetWorkflowResponse(
                isError=False,
                workflow_name="test-workflow",
                content=[TextContent(type="text", text="Missing workflow_details")]
            )

    def test_list_workflows_response_missing_required_fields(self):
        """Test that creating a ListWorkflowsResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            ListWorkflowsResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing workflows")]
            )

    def test_start_workflow_run_response_missing_required_fields(self):
        """Test that creating a StartWorkflowRunResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            StartWorkflowRunResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing workflow_name and run_id")]
            )

        with pytest.raises(ValidationError):
            StartWorkflowRunResponse(
                isError=False,
                workflow_name="test-workflow",
                content=[TextContent(type="text", text="Missing run_id")]
            )

    def test_create_trigger_response_missing_required_fields(self):
        """Test that creating a CreateTriggerResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            CreateTriggerResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing trigger_name")]
            )

    def test_delete_trigger_response_missing_required_fields(self):
        """Test that creating a DeleteTriggerResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            DeleteTriggerResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing trigger_name")]
            )

    def test_get_trigger_response_missing_required_fields(self):
        """Test that creating a GetTriggerResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            GetTriggerResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing trigger_name and trigger_details")]
            )

        with pytest.raises(ValidationError):
            GetTriggerResponse(
                isError=False,
                trigger_name="test-trigger",
                content=[TextContent(type="text", text="Missing trigger_details")]
            )

    def test_get_triggers_response_missing_required_fields(self):
        """Test that creating a GetTriggersResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            GetTriggersResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing triggers")]
            )

    def test_start_trigger_response_missing_required_fields(self):
        """Test that creating a StartTriggerResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            StartTriggerResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing trigger_name")]
            )

    def test_stop_trigger_response_missing_required_fields(self):
        """Test that creating a StopTriggerResponse without required fields raises an error."""
        with pytest.raises(ValidationError):
            StopTriggerResponse(
                isError=False,
                content=[TextContent(type="text", text="Missing trigger_name")]
            )
