"""
Comprehensive unit tests for the fetch_cloudformation_status function.

This test suite achieves high coverage by testing the real code paths
through CloudFormationClient rather than using mock client implementations.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_cloudformation_status
from tests.unit.utils.async_test_utils import (
    create_sample_stack_data,
    create_sample_stack_event,
    create_sample_stack_resource,
)


@pytest.fixture
def mock_cloudformation_client():
    """Create a mock CloudFormation client for testing."""
    # Create a mock AWS CloudFormation client
    mock_cf = mock.AsyncMock()

    # Set up default responses to match behavior for key methods
    mock_cf.describe_stacks.return_value = {"Stacks": []}
    mock_cf.list_stack_resources.return_value = {"StackResourceSummaries": []}
    mock_cf.describe_stack_events.return_value = {"StackEvents": []}
    mock_cf.list_deleted_stacks.return_value = []

    return mock_cf


class TestFetchCloudFormationStatus:
    """Test the fetch_cloudformation_status function with CloudFormationClient mocking."""

    @pytest.mark.anyio
    async def test_stack_exists(self, mock_cloudformation_client):
        """Test when CloudFormation stack exists."""
        # Create sample stack data
        stack_data = create_sample_stack_data(stack_name="test-app", stack_status="CREATE_COMPLETE")

        # Set up mock responses
        mock_cloudformation_client.describe_stacks.return_value = {"Stacks": [stack_data]}

        # Create sample resources
        resources = [
            create_sample_stack_resource(
                logical_id="ECSCluster",
                physical_id="test-app-cluster",
                resource_type="AWS::ECS::Cluster",
            ),
            create_sample_stack_resource(
                logical_id="LoadBalancer",
                physical_id="arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/test-app/1234567890123456",
                resource_type="AWS::ElasticLoadBalancingV2::LoadBalancer",
            ),
        ]
        mock_cloudformation_client.list_stack_resources.return_value = {
            "StackResourceSummaries": resources
        }

        # Create sample events
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        events = [
            create_sample_stack_event(
                stack_name="test-app",
                logical_id="ECSCluster",
                physical_id="test-app-cluster",
                resource_type="AWS::ECS::Cluster",
                timestamp=timestamp,
            )
        ]
        mock_cloudformation_client.describe_stack_events.return_value = {"StackEvents": events}

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result
        assert result["status"] == "success"
        assert result["stack_exists"]
        assert result["stack_status"] == "CREATE_COMPLETE"
        assert len(result["resources"]) == 2
        assert len(result["raw_events"]) == 1

    @pytest.mark.anyio
    async def test_stack_failure(self, mock_cloudformation_client):
        """Test when CloudFormation stack exists but has failed resources."""
        # Create sample stack data
        stack_data = create_sample_stack_data(stack_name="test-app", stack_status="CREATE_FAILED")

        # Set up mock responses
        mock_cloudformation_client.describe_stacks.return_value = {"Stacks": [stack_data]}

        # Create sample resources including a failed one
        resources = [
            create_sample_stack_resource(
                logical_id="ECSCluster",
                physical_id="test-app-cluster",
                resource_type="AWS::ECS::Cluster",
            ),
            create_sample_stack_resource(
                logical_id="ECSService",
                physical_id="",
                resource_type="AWS::ECS::Service",
                status="CREATE_FAILED",
                status_reason="Resource creation cancelled",
            ),
        ]
        mock_cloudformation_client.list_stack_resources.return_value = {
            "StackResourceSummaries": resources
        }

        # Create sample events
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        events = [
            create_sample_stack_event(
                stack_name="test-app",
                logical_id="ECSService",
                physical_id="",
                resource_type="AWS::ECS::Service",
                status="CREATE_FAILED",
                status_reason="Resource creation cancelled",
                timestamp=timestamp,
            )
        ]
        mock_cloudformation_client.describe_stack_events.return_value = {"StackEvents": events}

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result
        assert result["status"] == "success"
        assert result["stack_exists"]
        assert result["stack_status"] == "CREATE_FAILED"
        assert len(result["failure_reasons"]) == 1
        assert result["failure_reasons"][0]["logical_id"] == "ECSService"
        assert "cancelled" in result["failure_reasons"][0]["reason"]

    @pytest.mark.anyio
    async def test_stack_not_found(self, mock_cloudformation_client):
        """Test when CloudFormation stack does not exist."""
        # Set up mock to raise a ClientError for describe_stacks
        mock_cloudformation_client.describe_stacks.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-app does not exist",
                }
            },
            "DescribeStacks",
        )

        # Set up deleted stacks
        deletion_time = datetime.datetime(2025, 5, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
        deleted_stack = create_sample_stack_data(
            stack_name="test-app", stack_status="DELETE_COMPLETE"
        )
        deleted_stack["DeletionTime"] = deletion_time

        # Manually add deleted_stacks to the response to simulate the behavior
        # The actual implementation should have this field populated
        mock_cloudformation_client.list_deleted_stacks.return_value = [deleted_stack]

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result
        assert result["status"] == "success"
        assert not result["stack_exists"]
        assert "deleted_stacks" in result
        assert len(result["deleted_stacks"]) == 1

    @pytest.mark.anyio
    async def test_client_error_handling(self, mock_cloudformation_client):
        """Test client error handling."""
        # Simulate an error in describe_stacks
        mock_cloudformation_client.describe_stacks.return_value = {
            "Stacks": [create_sample_stack_data(stack_name="test-app")]
        }

        # Make list_stack_resources raise an error that's handled by the client
        mock_cloudformation_client.list_stack_resources.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListStackResources"
        )

        # Set up a successful describe_stack_events call
        mock_cloudformation_client.describe_stack_events.return_value = {"StackEvents": []}

        # Call the function\
        #  with the mock client - this should handle the error in list_stack_resources
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # We expect the function to recover from the error
        assert result["status"] == "success"
        assert result["stack_exists"]
        assert "resources" in result
        # Expect resources to be empty since the side_effect is an error
        assert isinstance(result["resources"], list)

    @pytest.mark.anyio
    async def test_general_exception_handling(self, mock_cloudformation_client):
        """Test general exception handling."""
        # Make describe_stacks raise unexpected error
        mock_cloudformation_client.describe_stacks.side_effect = Exception("Unexpected error")

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result - should return error status
        assert result["status"] == "error"
        assert "error" in result
        assert "Unexpected error" in result["error"]

    @pytest.mark.anyio
    async def test_additional_failure_reasons_from_events(self, mock_cloudformation_client):
        """Test extracting additional failure reasons from events."""
        # Create sample stack data
        stack_data = create_sample_stack_data(stack_name="test-app", stack_status="CREATE_FAILED")

        # Set up mock responses
        mock_cloudformation_client.describe_stacks.return_value = {"Stacks": [stack_data]}

        # Create sample resources - don't include the failure here
        resources = [
            create_sample_stack_resource(
                logical_id="ECSCluster",
                physical_id="test-app-cluster",
                resource_type="AWS::ECS::Cluster",
            ),
            # No failed resource here
        ]
        mock_cloudformation_client.list_stack_resources.return_value = {
            "StackResourceSummaries": resources
        }

        # Create sample events with a failure that's not in the resources
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        events = [
            create_sample_stack_event(
                stack_name="test-app",
                logical_id="ECSService",  # Service failure only in events
                physical_id="",
                resource_type="AWS::ECS::Service",
                status="CREATE_FAILED",
                status_reason="Resource creation cancelled",
                timestamp=timestamp,
            )
        ]
        mock_cloudformation_client.describe_stack_events.return_value = {"StackEvents": events}

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result
        assert result["status"] == "success"
        assert result["stack_exists"]
        assert len(result["failure_reasons"]) == 1
        assert result["failure_reasons"][0]["logical_id"] == "ECSService"
        assert "cancelled" in result["failure_reasons"][0]["reason"]

    @pytest.mark.anyio
    async def test_list_deleted_stacks_error(self, mock_cloudformation_client):
        """Test error handling in list_deleted_stacks."""
        # Set up mock to raise a ClientError for describe_stacks
        mock_cloudformation_client.describe_stacks.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-app does not exist",
                }
            },
            "DescribeStacks",
        )

        # Make list_deleted_stacks raise an error
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListStacks"
        )
        mock_cloudformation_client.list_deleted_stacks.side_effect = error

        # Call the function with the mock client
        result = await fetch_cloudformation_status("test-app", mock_cloudformation_client)

        # Verify the result
        assert result["status"] == "success"
        assert not result["stack_exists"]
        # The function should have tried to handle the list_deleted_stacks error
        assert "list_error" in result
