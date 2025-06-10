"""
Unit tests for the CloudFormationClient class.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.clients.cloudformation_client import CloudFormationClient
from tests.unit.utils.async_test_utils import AsyncIterator


@pytest.fixture
def mock_aws_client():
    """Create a mock for AWS client."""
    # Create a mock for the AWS client
    mock_cfn = mock.AsyncMock()

    # Patch the get_aws_client function to return our mock directly
    with mock.patch(
        "awslabs.ecs_mcp_server.api.clients.cloudformation_client.get_aws_client",
        return_value=mock_cfn,
    ):
        yield mock_cfn


class TestDescribeStacks:
    """Tests for describe_stacks method."""

    @pytest.mark.anyio
    async def test_stack_exists(self, mock_aws_client):
        """Test when the stack exists and returns valid information."""
        # Arrange
        stack_id = "test-stack"
        # Set up mock for test
        mock_aws_client.describe_stacks.return_value = {
            "Stacks": [{"StackName": stack_id, "StackStatus": "CREATE_COMPLETE"}]
        }

        # Act
        client = CloudFormationClient()
        response = await client.describe_stacks(stack_id)

        # Assert
        assert response["Stacks"][0]["StackName"] == stack_id
        assert response["Stacks"][0]["StackStatus"] == "CREATE_COMPLETE"
        mock_aws_client.describe_stacks.assert_called_once_with(StackName=stack_id)

    @pytest.mark.anyio
    async def test_client_error(self, mock_aws_client):
        """Test when the AWS SDK raises a ClientError exception."""
        # Arrange
        stack_id = "test-stack"
        # Set up mock to raise ClientError
        mock_aws_client.describe_stacks.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-stack does not exist",
                }
            },
            "DescribeStacks",
        )

        # Act/Assert
        client = CloudFormationClient()
        with pytest.raises(ClientError):
            await client.describe_stacks(stack_id)

        mock_aws_client.describe_stacks.assert_called_once_with(StackName=stack_id)


class TestListStackResources:
    """Tests for list_stack_resources method."""

    @pytest.mark.anyio
    async def test_resources_found(self, mock_aws_client):
        """Test when stack resources are found."""
        # Arrange
        stack_id = "test-stack"
        # Set up mock for test
        mock_aws_client.list_stack_resources.return_value = {
            "StackResourceSummaries": [
                {
                    "LogicalResourceId": "EcsCluster",
                    "PhysicalResourceId": "test-cluster",
                    "ResourceType": "AWS::ECS::Cluster",
                    "ResourceStatus": "CREATE_COMPLETE",
                }
            ]
        }

        # Act
        client = CloudFormationClient()
        response = await client.list_stack_resources(stack_id)

        # Assert
        assert len(response["StackResourceSummaries"]) == 1
        assert response["StackResourceSummaries"][0]["LogicalResourceId"] == "EcsCluster"
        mock_aws_client.list_stack_resources.assert_called_once_with(StackName=stack_id)

    @pytest.mark.anyio
    async def test_client_error(self, mock_aws_client):
        """Test when the AWS SDK raises a ClientError exception."""
        # Arrange
        stack_id = "test-stack"
        # Set up mock to raise ClientError
        mock_aws_client.list_stack_resources.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-stack does not exist",
                }
            },
            "ListStackResources",
        )

        # Act
        client = CloudFormationClient()
        response = await client.list_stack_resources(stack_id)

        # Assert
        assert response["StackResourceSummaries"] == []
        mock_aws_client.list_stack_resources.assert_called_once_with(StackName=stack_id)


class TestDescribeStackEvents:
    """Tests for describe_stack_events method."""

    @pytest.mark.anyio
    async def test_events_found(self, mock_aws_client):
        """Test when stack events are found."""
        # Arrange
        stack_id = "test-stack"
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        # Set up mock for test
        mock_aws_client.describe_stack_events.return_value = {
            "StackEvents": [
                {
                    "StackId": stack_id,
                    "EventId": "1",
                    "StackName": stack_id,
                    "LogicalResourceId": "EcsCluster",
                    "PhysicalResourceId": "test-cluster",
                    "ResourceType": "AWS::ECS::Cluster",
                    "Timestamp": timestamp,
                    "ResourceStatus": "CREATE_COMPLETE",
                }
            ]
        }

        # Act
        client = CloudFormationClient()
        response = await client.describe_stack_events(stack_id)

        # Assert
        assert len(response["StackEvents"]) == 1
        assert response["StackEvents"][0]["LogicalResourceId"] == "EcsCluster"
        mock_aws_client.describe_stack_events.assert_called_once_with(StackName=stack_id)

    @pytest.mark.anyio
    async def test_client_error(self, mock_aws_client):
        """Test when the AWS SDK raises a ClientError exception."""
        # Arrange
        stack_id = "test-stack"
        # Set up mock to raise ClientError
        mock_aws_client.describe_stack_events.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-stack does not exist",
                }
            },
            "DescribeStackEvents",
        )

        # Act
        client = CloudFormationClient()
        response = await client.describe_stack_events(stack_id)

        # Assert
        assert response["StackEvents"] == []
        mock_aws_client.describe_stack_events.assert_called_once_with(StackName=stack_id)


class TestListDeletedStacks:
    """Tests for list_deleted_stacks method."""

    @pytest.mark.anyio
    async def test_deleted_stacks_found(self, mock_aws_client):
        """Test when deleted stacks are found."""
        # Arrange
        stack_name = "test-stack"
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        # Set up paginator mock with async iterator
        mock_paginator = mock.Mock()  # Regular Mock, not AsyncMock!
        mock_paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "StackSummaries": [
                        {
                            "StackId": (
                                "arn:aws:cloudformation:us-west-2:"
                                "123456789012:stack/test-stack/1234"
                            ),
                            "StackName": stack_name,
                            "StackStatus": "DELETE_COMPLETE",
                            "DeletionTime": timestamp,
                        },
                        {
                            "StackId": (
                                "arn:aws:cloudformation:us-west-2:"
                                "123456789012:stack/other-stack/5678"
                            ),
                            "StackName": "other-stack",
                            "StackStatus": "DELETE_COMPLETE",
                            "DeletionTime": timestamp,
                        },
                    ]
                }
            ]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Act
        client = CloudFormationClient()
        deleted_stacks = await client.list_deleted_stacks(stack_name)

        # Assert
        assert len(deleted_stacks) == 1
        assert deleted_stacks[0]["StackName"] == stack_name
        assert deleted_stacks[0]["StackStatus"] == "DELETE_COMPLETE"
        mock_aws_client.get_paginator.assert_called_once_with("list_stacks")
        mock_paginator.paginate.assert_called_once_with(StackStatusFilter=["DELETE_COMPLETE"])

    @pytest.mark.anyio
    async def test_multi_page_results(self, mock_aws_client):
        """Test pagination handling."""
        # Arrange
        stack_name = "test-stack"
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        # Set up paginator mock with multiple pages
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "StackSummaries": [
                        {
                            "StackId": (
                                "arn:aws:cloudformation:us-west-2:"
                                "123456789012:stack/test-stack/1234"
                            ),
                            "StackName": stack_name,
                            "StackStatus": "DELETE_COMPLETE",
                            "DeletionTime": timestamp,
                        }
                    ]
                },
                {
                    "StackSummaries": [
                        {
                            "StackId": (
                                "arn:aws:cloudformation:us-west-2:"
                                "123456789012:stack/test-stack/5678"
                            ),
                            "StackName": stack_name,
                            "StackStatus": "DELETE_COMPLETE",
                            "DeletionTime": timestamp - datetime.timedelta(days=1),
                        }
                    ]
                },
            ]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Act
        client = CloudFormationClient()
        deleted_stacks = await client.list_deleted_stacks(stack_name)

        # Assert
        assert len(deleted_stacks) == 2
        assert all(stack["StackName"] == stack_name for stack in deleted_stacks)
        mock_aws_client.get_paginator.assert_called_once_with("list_stacks")
        mock_paginator.paginate.assert_called_once_with(StackStatusFilter=["DELETE_COMPLETE"])

    @pytest.mark.anyio
    async def test_no_deleted_stacks(self, mock_aws_client):
        """Test when no deleted stacks are found."""
        # Arrange
        stack_name = "test-stack"
        # Set up paginator mock with empty results
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "StackSummaries": [
                        {
                            "StackId": (
                                "arn:aws:cloudformation:us-west-2:"
                                "123456789012:stack/other-stack/5678"
                            ),
                            "StackName": "other-stack",
                            "StackStatus": "DELETE_COMPLETE",
                        }
                    ]
                }
            ]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Act
        client = CloudFormationClient()
        deleted_stacks = await client.list_deleted_stacks(stack_name)

        # Assert
        assert len(deleted_stacks) == 0
        mock_aws_client.get_paginator.assert_called_once_with("list_stacks")

    @pytest.mark.anyio
    async def test_client_error(self, mock_aws_client):
        """Test when the AWS SDK raises a ClientError exception."""
        # Arrange
        stack_name = "test-stack"
        # Set up mock to raise ClientError
        mock_aws_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListStacks"
        )

        # Act
        client = CloudFormationClient()
        deleted_stacks = await client.list_deleted_stacks(stack_name)

        # Assert - should return empty list on error, not raise exception
        assert len(deleted_stacks) == 0

    @pytest.mark.anyio
    async def test_general_exception(self, mock_aws_client):
        """Test when a general exception occurs."""
        # Arrange
        stack_name = "test-stack"
        # Set up mock to raise a general exception
        mock_aws_client.get_paginator.side_effect = Exception("Unexpected error")

        # Act
        client = CloudFormationClient()
        deleted_stacks = await client.list_deleted_stacks(stack_name)

        # Assert - should return empty list on error, not raise exception
        assert len(deleted_stacks) == 0
