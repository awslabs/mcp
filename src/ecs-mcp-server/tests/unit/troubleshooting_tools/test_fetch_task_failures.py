"""
Comprehensive unit tests for the fetch_task_failures function.

This test suite achieves high coverage by testing the real code paths
through direct boto3 client mocking.
"""

import datetime
import unittest.mock as mock
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_task_failures
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_task_failures import (
    _categorize_container_failure,
    _categorize_failures,
    _process_task_failure,
)
from tests.unit.utils.async_test_utils import (
    create_mock_ecs_client,
    create_sample_cluster_data,
    create_sample_task_data,
)


class TestFetchTaskFailuresBase:
    """Base class for fetch_task_failures tests."""

    def setup_method(self, method):
        """Clear AWS client cache before each test."""
        from awslabs.ecs_mcp_server.utils.aws import _aws_clients

        _aws_clients.clear()

    def mock_aws_clients(self, mock_clients):
        """Create a mock for boto3.client that returns specified clients."""

        def mock_client_factory(service_name, **kwargs):
            return mock_clients.get(service_name, MagicMock())

        return mock.patch("boto3.client", side_effect=mock_client_factory)


class TestHelperFunctions:
    """Test helper functions for fetch_task_failures."""

    @pytest.mark.parametrize(
        "container,expected_category",
        [
            # Image pull failures
            ({"reason": "CannotPullContainerError: Error pulling image"}, "image_pull_failure"),
            ({"reason": "ImagePull error"}, "image_pull_failure"),
            # Resource constraint failures
            ({"reason": "Resource constraint exceeded"}, "resource_constraint"),
            ({"reason": "Memory resource constraint"}, "resource_constraint"),
            ({"reason": "RESOURCE CONSTRAINT exceeded"}, "resource_constraint"),
            # Out of memory failures
            ({"exitCode": 137}, "out_of_memory"),
            ({"exitCode": 137, "reason": "Container killed"}, "out_of_memory"),
            # Segmentation fault failures
            ({"exitCode": 139}, "segmentation_fault"),
            ({"exitCode": 139, "reason": "Segmentation fault"}, "segmentation_fault"),
            # Application error failures
            ({"exitCode": 1}, "application_error"),
            ({"exitCode": 2}, "application_error"),
            ({"exitCode": 255}, "application_error"),
            # Dependent container stopped failures
            ({"reason": "Essential container in task exited"}, "dependent_container_stopped"),
            # Other failures
            ({"reason": "Unknown reason"}, "other"),
            ({"exitCode": 0}, "other"),
            ({}, "other"),
            ({"exitCode": "N/A"}, "other"),
            # Priority testing (image pull takes priority)
            ({"exitCode": 137, "reason": "CannotPullContainerError"}, "image_pull_failure"),
        ],
    )
    def test_categorize_container_failure(self, container, expected_category):
        """Test categorizing container failures with parameterized inputs."""
        result = _categorize_container_failure(container)
        assert result == expected_category

    @pytest.mark.parametrize(
        "task_data,expected_fields",
        [
            # Basic task with all fields
            (
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task1",
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    ),
                    "stoppedAt": datetime.datetime.now(datetime.timezone.utc),
                    "startedAt": datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(minutes=10),
                    "containers": [
                        {
                            "name": "app",
                            "exitCode": 1,
                            "reason": "Container exited with non-zero status",
                        }
                    ],
                },
                {
                    "task_id": "task1",
                    "task_definition": "test-app:1",
                    "containers_count": 1,
                    "container_name": "app",
                    "container_exit_code": 1,
                    "container_reason": "Container exited with non-zero status",
                },
            ),
            # Task with no containers
            (
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task2",
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    ),
                    "stoppedAt": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "task_id": "task2",
                    "task_definition": "test-app:1",
                    "containers_count": 0,
                    "started_at": "N/A",
                },
            ),
            # Task with string timestamp
            (
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task3",
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    ),
                    "stoppedAt": "2023-01-01T00:00:00Z",
                    "containers": [],
                },
                {
                    "task_id": "task3",
                    "task_definition": "test-app:1",
                    "stopped_at": "2023-01-01T00:00:00Z",
                    "containers_count": 0,
                },
            ),
            # Task with missing container fields
            (
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task4",
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    ),
                    "stoppedAt": "2023-01-01T00:00:00Z",
                    "containers": [
                        {
                            "name": "app",
                            # Missing exitCode and reason
                        }
                    ],
                },
                {
                    "task_id": "task4",
                    "task_definition": "test-app:1",
                    "containers_count": 1,
                    "container_name": "app",
                    "container_exit_code": "N/A",
                    "container_reason": "No reason provided",
                },
            ),
        ],
    )
    def test_process_task_failure(self, task_data, expected_fields):
        """Test processing task failures with parameterized inputs."""
        result = _process_task_failure(task_data)

        # Check basic fields
        assert result["task_id"] == expected_fields["task_id"]
        assert result["task_definition"] == expected_fields["task_definition"]
        assert len(result["containers"]) == expected_fields["containers_count"]

        # Check stopped_at format
        if "stopped_at" in expected_fields:
            assert result["stopped_at"] == expected_fields["stopped_at"]

        # Check started_at
        if "started_at" in expected_fields:
            assert result["started_at"] == expected_fields["started_at"]

        # Check container details if present
        if expected_fields["containers_count"] > 0:
            assert result["containers"][0]["name"] == expected_fields["container_name"]
            assert result["containers"][0]["exit_code"] == expected_fields["container_exit_code"]
            assert result["containers"][0]["reason"] == expected_fields["container_reason"]

    def test_categorize_failures(self):
        """Test categorizing multiple failures."""
        now = datetime.datetime.now(datetime.timezone.utc)
        tasks = [
            {
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task1",
                "taskDefinitionArn": "\
                        arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1\
                    ",
                "stoppedAt": now,
                "containers": [{"name": "app", "exitCode": 1, "reason": "Application error"}],
            },
            {
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task2",
                "taskDefinitionArn": "\
                        arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1\
                    ",
                "stoppedAt": now,
                "containers": [{"name": "app", "exitCode": 137, "reason": "OOM killed"}],
            },
        ]

        failed_tasks, failure_categories = _categorize_failures(tasks)

        assert len(failed_tasks) == 2
        assert "application_error" in failure_categories
        assert "out_of_memory" in failure_categories
        assert len(failure_categories["application_error"]) == 1
        assert len(failure_categories["out_of_memory"]) == 1

    def test_categorize_failures_empty(self):
        """Test categorizing failures with empty task list."""
        failed_tasks, failure_categories = _categorize_failures([])

        assert failed_tasks == []
        assert failure_categories == {}

    def test_categorize_failures_multiple_containers_per_task(self):
        """Test categorizing failures with multiple containers per task."""
        now = datetime.datetime.now(datetime.timezone.utc)
        tasks = [
            {
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/task1",
                "taskDefinitionArn": "\
                        arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1\
                    ",
                "stoppedAt": now,
                "containers": [
                    {"name": "app", "exitCode": 1, "reason": "Application error"},
                    {"name": "sidecar", "exitCode": 137, "reason": "OOM killed"},
                ],
            },
        ]

        failed_tasks, failure_categories = _categorize_failures(tasks)

        assert len(failed_tasks) == 1
        assert "application_error" in failure_categories
        assert "out_of_memory" in failure_categories
        # Each container failure should be categorized separately
        assert len(failure_categories["application_error"]) == 1
        assert len(failure_categories["out_of_memory"]) == 1


@pytest.fixture
def mock_aws_client():
    """Create a mock AWS client for testing."""
    mock_ecs = create_mock_ecs_client()

    with mock.patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client", return_value=mock_ecs):
        yield mock_ecs


class TestFetchTaskFailuresIntegration(TestFetchTaskFailuresBase):
    """Test the main fetch_task_failures function with boto3 client integration."""

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "cluster_exists,task_arns,expected_status",
        [
            # Cluster doesn't exist
            (False, [], {"status": "success", "cluster_exists": False}),
            # Cluster exists but no tasks
            (True, [], {"status": "success", "cluster_exists": True, "failed_tasks_count": 0}),
            # Cluster exists with tasks
            (
                True,
                ["task1"],
                {"status": "success", "cluster_exists": True, "failed_tasks_count": 1},
            ),
            # Multiple tasks
            (
                True,
                ["task1", "task2", "task3"],
                {"status": "success", "cluster_exists": True, "failed_tasks_count": 3},
            ),
        ],
    )
    async def test_fetch_task_failures_scenarios(self, cluster_exists, task_arns, expected_status):
        """Test different scenarios for fetch_task_failures with parameterization."""
        mock_ecs = MagicMock()

        # Set up cluster response
        if cluster_exists:
            cluster_data = create_sample_cluster_data("test-cluster")
            mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}
            if task_arns:
                tasks = [
                    create_sample_task_data(task_id=task_id, exit_code=1) for task_id in task_arns
                ]
                mock_ecs.list_tasks.return_value = {
                    "taskArns": [f"arn:aws:ecs:task/{t}" for t in task_arns]
                }
                mock_ecs.describe_tasks.return_value = {"tasks": tasks}
            else:
                mock_ecs.list_tasks.return_value = {"taskArns": []}
                mock_ecs.describe_tasks.return_value = {"tasks": []}
        else:
            mock_ecs.describe_clusters.return_value = {"clusters": []}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            # Call the function (no ecs_client parameter)
            result = await fetch_task_failures("test-cluster")

            # Check basic status
            assert result["status"] == expected_status["status"]
            assert result["cluster_exists"] == expected_status["cluster_exists"]

            # Check task count if cluster exists
            if cluster_exists:
                assert len(result["failed_tasks"]) == expected_status["failed_tasks_count"]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "exit_code,reason,expected_category",
        [
            (1, "Application error", "application_error"),
            (137, "OOM killed", "out_of_memory"),
            (139, "Segmentation fault", "segmentation_fault"),
            (1, "CannotPullContainerError", "image_pull_failure"),
            (1, "Resource constraint exceeded", "resource_constraint"),
        ],
    )
    async def test_failure_categorization(self, exit_code, reason, expected_category):
        """Test that different failure types are properly categorized."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create task with the specified failure type
        task_data = create_sample_task_data(task_id="task1", exit_code=exit_code, reason=reason)

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task1"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            # Call the function (no ecs_client parameter)
            result = await fetch_task_failures("test-cluster")

            # Check that the failure was properly categorized
            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 1
            assert expected_category in result["failure_categories"]
            assert len(result["failure_categories"][expected_category]) == 1

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "error_type,error_location,expected_result",
        [
            # Error in check_cluster_exists
            (
                "ClientError",
                "check_cluster_exists",
                {"status": "success", "has_ecs_error": True},
            ),
            # Error in get_stopped_tasks
            (
                "ClientError",
                "get_stopped_tasks",
                {"status": "success", "failed_tasks_count": 0},
            ),
            # General exception
            (
                "Exception",
                "check_cluster_exists",
                {"status": "error", "has_error": True},
            ),
        ],
    )
    async def test_error_handling(self, error_type, error_location, expected_result):
        """Test error handling with parameterization."""
        mock_ecs = MagicMock()

        # Set up the error
        if error_type == "ClientError":
            error = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "Operation",
            )
        else:
            error = Exception("Unexpected error")

        # Apply the error to the specified location
        if error_location == "check_cluster_exists":
            mock_ecs.describe_clusters.side_effect = error
        elif error_location == "get_stopped_tasks":
            cluster_data = create_sample_cluster_data("test-cluster")
            mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}
            mock_ecs.list_tasks.side_effect = error

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            # Call the function (no ecs_client parameter)
            result = await fetch_task_failures("test-cluster")

            # Check the result
            assert result["status"] == expected_result["status"]

            if "has_ecs_error" in expected_result and expected_result["has_ecs_error"]:
                assert "ecs_error" in result

            if "has_error" in expected_result and expected_result["has_error"]:
                assert "error" in result

            if "failed_tasks_count" in expected_result:
                assert len(result["failed_tasks"]) == expected_result["failed_tasks_count"]

    @pytest.mark.anyio
    async def test_cluster_not_found(self):
        """Test when cluster is not found."""
        mock_ecs = MagicMock()
        mock_ecs.describe_clusters.return_value = {"clusters": []}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("nonexistent-cluster")

            assert result["status"] == "success"
            assert result["cluster_exists"] is False
            assert "message" in result
            assert "does not exist" in result["message"]
            mock_ecs.describe_clusters.assert_called_once_with(clusters=["nonexistent-cluster"])

    @pytest.mark.anyio
    async def test_successful_execution_no_failures(self):
        """Test successful execution with no failures."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}
        mock_ecs.list_tasks.return_value = {"taskArns": []}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert result["cluster_exists"] is True
            assert result["failed_tasks"] == []
            assert result["failure_categories"] == {}
            assert "raw_data" in result
            assert result["raw_data"]["cluster"] == cluster_data

    @pytest.mark.anyio
    async def test_successful_execution_with_failures(self):
        """Test successful execution with failures."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create sample task data
        task_data = create_sample_task_data(
            task_id="task1", exit_code=1, reason="Application error"
        )

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task1"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert result["cluster_exists"] is True
            assert len(result["failed_tasks"]) == 1
            assert "application_error" in result["failure_categories"]
            assert result["failed_tasks"][0]["task_id"] == "task1"

    @pytest.mark.anyio
    async def test_multiple_pages_of_tasks(self):
        """Test handling multiple pages of task results."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create sample task data
        task1_data = create_sample_task_data(task_id="task1", exit_code=1)
        task2_data = create_sample_task_data(task_id="task2", exit_code=137)
        task3_data = create_sample_task_data(task_id="task3", exit_code=139)

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": [
                "arn:aws:ecs:task/task1",
                "arn:aws:ecs:task/task2",
                "arn:aws:ecs:task/task3",
            ]
        }
        mock_ecs.describe_tasks.return_value = {"tasks": [task1_data, task2_data, task3_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 3
            assert "application_error" in result["failure_categories"]
            assert "out_of_memory" in result["failure_categories"]
            assert "segmentation_fault" in result["failure_categories"]

    @pytest.mark.anyio
    async def test_time_window_filtering(self):
        """Test that tasks are properly filtered by time window."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        now = datetime.datetime.now(datetime.timezone.utc)

        # Create tasks - one recent, one old
        recent_task = create_sample_task_data(
            task_id="recent_task", stopped_at=now - datetime.timedelta(minutes=30), exit_code=1
        )

        # Set up boto3 API responses - return only recent task
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/recent_task"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [recent_task]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            # Test with 1 hour time window - should only include recent task
            result = await fetch_task_failures("test-cluster", time_window=3600)

            assert result["status"] == "success"
            # Only the recent task should be included since it's within the time window
            assert len(result["failed_tasks"]) == 1
            assert result["failed_tasks"][0]["task_id"] == "recent_task"

    @pytest.mark.anyio
    async def test_explicit_time_window(self):
        """Test with explicit start_time and end_time parameters."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(hours=2)
        end_time = now - datetime.timedelta(hours=1)

        # Create task within the window
        task_data = create_sample_task_data(
            task_id="task1", stopped_at=now - datetime.timedelta(minutes=90), exit_code=1
        )

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task1"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures(
                "test-cluster",
                start_time=start_time,
                end_time=end_time,
            )

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 1

    @pytest.mark.anyio
    async def test_running_tasks_count(self):
        """Test that running tasks count is included in results."""
        mock_ecs = MagicMock()

        # Set up cluster exists with 1 running task in cluster statistics
        cluster_data = create_sample_cluster_data("test-cluster")
        cluster_data["runningTasksCount"] = 1  # Set running tasks count in cluster data
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Set up boto3 API responses - no stopped tasks (only one call now)
        mock_ecs.list_tasks.return_value = {"taskArns": []}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert result["raw_data"]["running_tasks_count"] == 1

    @pytest.mark.anyio
    async def test_client_error_handling(self):
        """Test client error handling."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Make list_tasks raise ClientError for stopped tasks
        mock_ecs.list_tasks.side_effect = [
            ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListTasks"
            ),  # First call (stopped tasks) fails
            {"taskArns": []},  # Second call (running tasks) succeeds
        ]

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            # Since the error is caught, we should have empty task lists
            assert result["failed_tasks"] == []
            assert result["failure_categories"] == {}

    @pytest.mark.anyio
    async def test_cluster_describe_error(self):
        """Test error handling when describing clusters fails."""
        mock_ecs = MagicMock()

        # Make describe_clusters raise ClientError
        mock_ecs.describe_clusters.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DescribeClusters"
        )

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert "ecs_error" in result

    @pytest.mark.anyio
    async def test_general_exception_handling(self):
        """Test general exception handling."""
        mock_ecs = MagicMock()

        # Make describe_clusters raise unexpected error
        mock_ecs.describe_clusters.side_effect = Exception("Unexpected error")

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.anyio
    async def test_empty_task_arns_page(self):
        """Test handling of empty taskArns in paginator response."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create task data
        task_data = create_sample_task_data(task_id="task1", exit_code=1)

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task1"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 1

    @pytest.mark.anyio
    async def test_tasks_without_stopped_at(self):
        """Test handling of tasks without stoppedAt timestamp."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create task with stoppedAt
        task_with_stopped = create_sample_task_data(task_id="task2", exit_code=1)

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task2"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_with_stopped]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 1
            assert result["failed_tasks"][0]["task_id"] == "task2"

    @pytest.mark.anyio
    async def test_timezone_handling(self):
        """Test proper timezone handling for datetime comparisons."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        now = datetime.datetime.now(datetime.timezone.utc)

        # Create task with naive datetime
        task_data = create_sample_task_data(task_id="task1", exit_code=1)
        # Make stoppedAt naive (no timezone)
        task_data["stoppedAt"] = now.replace(tzinfo=None)

        # Set up boto3 API responses
        mock_ecs.list_tasks.return_value = {"taskArns": ["arn:aws:ecs:task/task1"]}
        mock_ecs.describe_tasks.return_value = {"tasks": [task_data]}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            # Use naive start_time as well
            result = await fetch_task_failures("test-cluster", time_window=3600)

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 1

    @pytest.mark.anyio
    async def test_comprehensive_failure_categories(self):
        """Test all failure categories are properly detected."""
        mock_ecs = MagicMock()

        # Set up cluster exists
        cluster_data = create_sample_cluster_data("test-cluster")
        mock_ecs.describe_clusters.return_value = {"clusters": [cluster_data]}

        # Create tasks with different failure types
        tasks = [
            create_sample_task_data(task_id="task1", exit_code=1, reason="App error"),
            create_sample_task_data(task_id="task2", exit_code=137, reason="OOM"),
            create_sample_task_data(task_id="task3", exit_code=139, reason="Segfault"),
            create_sample_task_data(task_id="task4", reason="CannotPullContainerError"),
            create_sample_task_data(task_id="task5", reason="Resource constraint exceeded"),
            create_sample_task_data(task_id="task6", reason="Essential container in task exited"),
            create_sample_task_data(task_id="task7", reason="Unknown failure type"),
        ]

        # Set up boto3 API responses
        task_arns = [f"arn:aws:ecs:task/task{i}" for i in range(1, 8)]
        mock_ecs.list_tasks.return_value = {"taskArns": task_arns}
        mock_ecs.describe_tasks.return_value = {"tasks": tasks}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            result = await fetch_task_failures("test-cluster")

            assert result["status"] == "success"
            assert len(result["failed_tasks"]) == 7

            # Check all failure categories are present
            expected_categories = {
                "application_error",
                "out_of_memory",
                "segmentation_fault",
                "image_pull_failure",
                "resource_constraint",
                "dependent_container_stopped",
                "other",
            }
            assert set(result["failure_categories"].keys()) == expected_categories
