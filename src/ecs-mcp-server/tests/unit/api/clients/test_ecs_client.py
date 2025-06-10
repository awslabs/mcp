"""
Unit tests for the EcsClient class.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.clients.ecs_client import EcsClient


# Helper function to create a mock async iterator
class AsyncIterator:
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


@pytest.fixture
def mock_aws_client():
    """Create a mock for AWS client."""
    # Create a mock for the AWS client
    mock_ecs = mock.AsyncMock()

    # Patch the get_aws_client function to return our mock directly
    with mock.patch(
        "awslabs.ecs_mcp_server.api.clients.ecs_client.get_aws_client", return_value=mock_ecs
    ):
        yield mock_ecs


class TestCheckClusterExists:
    """Tests for check_cluster_exists method."""

    @pytest.mark.anyio
    async def test_cluster_exists(self, mock_aws_client):
        """Test when the cluster exists and returns valid information."""
        # Arrange
        cluster_name = "test-cluster"
        # Set up mock for test
        # With our updated fixture, mock_aws_client is already the mock_ecs object
        mock_aws_client.describe_clusters.return_value = {
            "clusters": [{"clusterName": cluster_name, "status": "ACTIVE"}]
        }

        # Act
        client = EcsClient()
        exists, info = await client.check_cluster_exists(cluster_name)

        # Assert
        assert exists is True
        assert info["clusterName"] == cluster_name
        mock_aws_client.describe_clusters.assert_called_once_with(clusters=[cluster_name])

    @pytest.mark.anyio
    async def test_cluster_not_found(self, mock_aws_client):
        """Test when the cluster name is valid but doesn't exist."""
        # Arrange
        cluster_name = "nonexistent-cluster"
        # mock_aws_client is already the mock_ecs object from the fixture
        mock_aws_client.describe_clusters.return_value = {"clusters": []}

        # Act
        client = EcsClient()
        exists, info = await client.check_cluster_exists(cluster_name)

        # Assert
        assert exists is False
        assert info == {}
        mock_aws_client.describe_clusters.assert_called_once_with(clusters=[cluster_name])

    @pytest.mark.anyio
    async def test_client_error(self, mock_aws_client):
        """Test when the AWS SDK raises a ClientError exception."""
        # Arrange
        cluster_name = "test-cluster"
        # Set up mock to raise ClientError
        mock_aws_client.describe_clusters.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DescribeClusters"
        )

        # Act/Assert
        client = EcsClient()
        with pytest.raises(ClientError):
            await client.check_cluster_exists(cluster_name)

        mock_aws_client.describe_clusters.assert_called_once_with(clusters=[cluster_name])

    @pytest.mark.anyio
    async def test_unexpected_response_format(self, mock_aws_client):
        """Test with unexpected response structure."""
        # Arrange
        cluster_name = "test-cluster"
        # Missing "clusters" key - set on the mock_aws_client directly
        mock_aws_client.describe_clusters.return_value = {}

        # Act/Assert
        client = EcsClient()
        with pytest.raises(KeyError):
            await client.check_cluster_exists(cluster_name)

        mock_aws_client.describe_clusters.assert_called_once_with(clusters=[cluster_name])


class TestGetStoppedTasks:
    """Tests for get_stopped_tasks method."""

    @pytest.mark.anyio
    async def test_tasks_found(self, mock_aws_client):
        """Test when stopped tasks are found within the specified time window."""
        # Arrange
        cluster_name = "test-cluster"
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(hours=1)

        # Set up paginator mock with async iterator
        mock_paginator = mock.Mock()  # Regular Mock, not AsyncMock!
        mock_paginator.paginate.return_value = AsyncIterator([{"taskArns": ["task1", "task2"]}])
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Set up task details with tasks after start_time
        mock_aws_client.describe_tasks.return_value = {
            "tasks": [
                {"taskArn": "task1", "stoppedAt": now - datetime.timedelta(minutes=30)},
                {"taskArn": "task2", "stoppedAt": now - datetime.timedelta(minutes=45)},
            ]
        }

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert
        assert len(stopped_tasks) == 2
        assert stopped_tasks[0]["taskArn"] == "task1"
        assert stopped_tasks[1]["taskArn"] == "task2"
        mock_aws_client.get_paginator.assert_called_once_with("list_tasks")
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="STOPPED"
        )
        mock_aws_client.describe_tasks.assert_called_once_with(
            cluster=cluster_name, tasks=["task1", "task2"]
        )

    @pytest.mark.anyio
    async def test_no_tasks_found(self, mock_aws_client):
        """Test when no stopped tasks are found."""
        # Arrange
        cluster_name = "test-cluster"
        start_time = datetime.datetime.now(datetime.timezone.utc)

        # Set up paginator mock with empty task list
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskArns": []}])
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert
        assert len(stopped_tasks) == 0
        mock_aws_client.get_paginator.assert_called_once_with("list_tasks")
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="STOPPED"
        )
        mock_aws_client.describe_tasks.assert_not_called()

    @pytest.mark.anyio
    async def test_multi_page_results(self, mock_aws_client):
        """Test pagination handling."""
        # Arrange
        cluster_name = "test-cluster"
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(hours=1)

        # Set up paginator mock with multiple pages
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskArns": ["task1", "task2"]}, {"taskArns": ["task3"]}]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Set up responses for each describe_tasks call
        mock_aws_client.describe_tasks.side_effect = [
            {
                "tasks": [
                    {"taskArn": "task1", "stoppedAt": now - datetime.timedelta(minutes=30)},
                    {"taskArn": "task2", "stoppedAt": now - datetime.timedelta(minutes=45)},
                ]
            },
            {"tasks": [{"taskArn": "task3", "stoppedAt": now - datetime.timedelta(minutes=50)}]},
        ]

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert
        assert len(stopped_tasks) == 3
        task_arns = [task["taskArn"] for task in stopped_tasks]
        assert "task1" in task_arns
        assert "task2" in task_arns
        assert "task3" in task_arns
        mock_aws_client.get_paginator.assert_called_once_with("list_tasks")
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="STOPPED"
        )
        assert mock_aws_client.describe_tasks.call_count == 2

    @pytest.mark.anyio
    async def test_time_filtering(self, mock_aws_client):
        """Test tasks filtered by start_time."""
        # Arrange
        cluster_name = "test-cluster"
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(hours=1)

        # Set up paginator mock
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskArns": ["task1", "task2", "task3"]}]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Set up task details with mix of tasks before and after start_time
        mock_aws_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "task1",
                    "stoppedAt": now - datetime.timedelta(minutes=30),  # After start_time
                },
                {
                    "taskArn": "task2",
                    "stoppedAt": now - datetime.timedelta(hours=2),  # Before start_time
                },
                {
                    "taskArn": "task3",
                    "stoppedAt": now - datetime.timedelta(minutes=50),  # After start_time
                },
            ]
        }

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert
        assert len(stopped_tasks) == 2
        task_arns = [task["taskArn"] for task in stopped_tasks]
        assert "task1" in task_arns
        assert "task3" in task_arns
        assert "task2" not in task_arns  # Should be excluded

    @pytest.mark.anyio
    async def test_naive_datetime_handling(self, mock_aws_client):
        """Test handling of naive datetime objects."""
        # Arrange
        cluster_name = "test-cluster"
        # Create a naive datetime for start_time
        start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

        # Set up paginator mock
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskArns": ["task1"]}])
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Task with naive datetime
        naive_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        mock_aws_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "task1",
                    "stoppedAt": naive_time,  # Naive datetime
                }
            ]
        }

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time=start_time)

        # Assert
        assert len(stopped_tasks) == 1
        assert stopped_tasks[0]["taskArn"] == "task1"

    @pytest.mark.anyio
    async def test_missing_stopped_at(self, mock_aws_client):
        """Test behavior when a task doesn't have a stoppedAt field."""
        # Arrange
        cluster_name = "test-cluster"
        start_time = datetime.datetime.now(datetime.timezone.utc)

        # Set up paginator mock
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskArns": ["task1", "task2"]}])
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Task with and without stoppedAt
        mock_aws_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "task1",
                    # No stoppedAt field
                },
                {
                    "taskArn": "task2",
                    "stoppedAt": start_time
                    + datetime.timedelta(minutes=5),  # After start_time, not before
                },
            ]
        }

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert
        assert len(stopped_tasks) == 1
        assert stopped_tasks[0]["taskArn"] == "task2"

    @pytest.mark.anyio
    async def test_stopped_tasks_client_error(self, mock_aws_client):
        """Test error handling for stopped tasks query."""
        # Arrange
        cluster_name = "test-cluster"
        start_time = datetime.datetime.now(datetime.timezone.utc)

        # Simulate a ClientError
        mock_aws_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListTasks"
        )

        # Act
        client = EcsClient()
        stopped_tasks = await client.get_stopped_tasks(cluster_name, start_time)

        # Assert - should return empty list on error, not raise exception
        assert len(stopped_tasks) == 0


class TestGetRunningTasksCount:
    """Tests for get_running_tasks_count method."""

    @pytest.mark.anyio
    async def test_tasks_running(self, mock_aws_client):
        """Test when running tasks are found."""
        # Arrange
        cluster_name = "test-cluster"

        # Set up paginator mock
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskArns": ["task1", "task2", "task3"]}]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        mock_aws_client.describe_tasks.return_value = {
            "tasks": [{"taskArn": "task1"}, {"taskArn": "task2"}, {"taskArn": "task3"}]
        }

        # Act
        client = EcsClient()
        count = await client.get_running_tasks_count(cluster_name)

        # Assert
        assert count == 3
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="RUNNING"
        )

    @pytest.mark.anyio
    async def test_no_tasks_running(self, mock_aws_client):
        """Test when no running tasks are found."""
        # Arrange
        cluster_name = "test-cluster"

        # Set up paginator mock
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskArns": []}])
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Act
        client = EcsClient()
        count = await client.get_running_tasks_count(cluster_name)

        # Assert
        assert count == 0
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="RUNNING"
        )
        mock_aws_client.describe_tasks.assert_not_called()

    @pytest.mark.anyio
    async def test_multi_page_running_tasks(self, mock_aws_client):
        """Test pagination handling for running tasks."""
        # Arrange
        cluster_name = "test-cluster"

        # Set up paginator mock with multiple pages
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [
                {"taskArns": ["task1", "task2"]},
                {"taskArns": ["task3", "task4"]},
                {"taskArns": ["task5"]},
            ]
        )
        mock_aws_client.get_paginator.return_value = mock_paginator

        # Set up responses for each describe_tasks call
        mock_aws_client.describe_tasks.side_effect = [
            {"tasks": [{"taskArn": "task1"}, {"taskArn": "task2"}]},
            {"tasks": [{"taskArn": "task3"}, {"taskArn": "task4"}]},
            {"tasks": [{"taskArn": "task5"}]},
        ]

        # Act
        client = EcsClient()
        count = await client.get_running_tasks_count(cluster_name)

        # Assert
        assert count == 5
        mock_aws_client.get_paginator.assert_called_once_with("list_tasks")
        mock_paginator.paginate.assert_called_once_with(
            cluster=cluster_name, desiredStatus="RUNNING"
        )
        assert mock_aws_client.describe_tasks.call_count == 3

    @pytest.mark.anyio
    async def test_running_tasks_client_error(self, mock_aws_client):
        """Test error handling for running tasks query."""
        # Arrange
        cluster_name = "test-cluster"

        # Simulate a ClientError
        mock_aws_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListTasks"
        )

        # Act
        client = EcsClient()
        count = await client.get_running_tasks_count(cluster_name)

        # Assert - should return 0 on error, not raise exception
        assert count == 0
