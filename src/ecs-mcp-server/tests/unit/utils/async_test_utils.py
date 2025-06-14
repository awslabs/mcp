"""
Shared utilities for async testing.

This module provides common utilities for testing asynchronous code,
particularly for mocking AWS SDK interactions.
"""

import datetime
from typing import Any, Dict, List, Optional
from unittest import mock


class AsyncIterator:
    """
    Mock async iterator for testing paginated AWS API responses.

    This iterator properly implements the async iterator protocol
    and can be used to mock AWS SDK paginator responses.
    """

    def __init__(self, items: List[Any]):
        """
        Initialize with a list of items to iterate over.

        Parameters
        ----------
        items : List[Any]
            List of items to yield during iteration
        """
        self.items = items

    def __aiter__(self):
        """Return the iterator object."""
        return self

    async def __anext__(self):
        """Return the next item in the iteration."""
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


def create_mock_ecs_client():
    """
    Create a properly configured mock ECS client.

    Returns
    -------
    mock.AsyncMock
        Configured mock ECS client with common methods
    """
    mock_ecs = mock.AsyncMock()

    # Set up default responses for common methods
    mock_ecs.describe_clusters.return_value = {"clusters": []}
    mock_ecs.describe_tasks.return_value = {"tasks": []}
    mock_ecs.list_tasks.return_value = {"taskArns": []}

    # Set up paginator mock - paginate() is NOT async, it returns an async iterator
    mock_paginator = mock.Mock()  # Not AsyncMock!
    mock_paginator.paginate.return_value = AsyncIterator([])
    mock_ecs.get_paginator.return_value = mock_paginator

    return mock_ecs


def create_sample_task_data(
    task_id: str = "task1",
    cluster_name: str = "test-cluster",
    task_definition: str = "test-app:1",
    stopped_at: datetime.datetime = None,
    started_at: datetime.datetime = None,
    exit_code: int = None,
    reason: str = None,
    container_name: str = "app",
) -> Dict[str, Any]:
    """
    Create sample task data for testing.

    Parameters
    ----------
    task_id : str
        Task identifier
    cluster_name : str
        Cluster name
    task_definition : str
        Task definition ARN suffix
    stopped_at : datetime.datetime, optional
        When the task stopped
    started_at : datetime.datetime, optional
        When the task started
    exit_code : int, optional
        Container exit code
    reason : str, optional
        Failure reason
    container_name : str
        Container name

    Returns
    -------
    Dict[str, Any]
        Sample task data structure
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if stopped_at is None:
        stopped_at = now - datetime.timedelta(minutes=5)
    if started_at is None:
        started_at = stopped_at - datetime.timedelta(minutes=10)

    task_data = {
        "taskArn": f"arn:aws:ecs:us-west-2:123456789012:task/{cluster_name}/{task_id}",
        "taskDefinitionArn": f"\
            arn:aws:ecs:us-west-2:123456789012:task-definition/{task_definition}",
        "stoppedAt": stopped_at,
        "startedAt": started_at,
        "containers": [],
    }

    # Add container data if exit_code or reason provided
    if exit_code is not None or reason is not None:
        container_data = {"name": container_name}
        if exit_code is not None:
            container_data["exitCode"] = exit_code
        if reason is not None:
            container_data["reason"] = reason
        task_data["containers"].append(container_data)

    return task_data


def create_sample_cluster_data(
    cluster_name: str = "test-cluster", status: str = "ACTIVE"
) -> Dict[str, Any]:
    """
    Create sample cluster data for testing.

    Parameters
    ----------
    cluster_name : str
        Cluster name
    status : str
        Cluster status

    Returns
    -------
    Dict[str, Any]
        Sample cluster data structure
    """
    return {
        "clusterName": cluster_name,
        "status": status,
        "runningTasksCount": 0,
        "pendingTasksCount": 0,
        "activeServicesCount": 0,
    }


def create_mock_cloudformation_client():
    """
    Create a properly configured mock CloudFormation client.

    Returns
    -------
    mock.AsyncMock
        Configured mock CloudFormation client with common methods
    """
    mock_cf = mock.AsyncMock()

    # Set up default responses for common methods
    mock_cf.describe_stacks.return_value = {"Stacks": []}

    # For methods that handle errors internally, we need to match that behavior
    async def mock_list_stack_resources(StackName=None, **kwargs):
        # This method returns empty list on error in the real client
        return {"StackResourceSummaries": []}

    async def mock_describe_stack_events(StackName=None, **kwargs):
        # This method returns empty list on error in the real client
        return {"StackEvents": []}

    # Override the return_value with our functions that match the real client behavior
    mock_cf.list_stack_resources.side_effect = mock_list_stack_resources
    mock_cf.describe_stack_events.side_effect = mock_describe_stack_events

    # Set up paginator mock - paginate() is NOT async, it returns an async iterator
    mock_paginator = mock.Mock()  # Not AsyncMock!
    mock_paginator.paginate.return_value = AsyncIterator([])
    mock_cf.get_paginator.return_value = mock_paginator

    return mock_cf


def create_sample_stack_data(
    stack_name: str = "test-stack",
    stack_status: str = "CREATE_COMPLETE",
    creation_time: datetime.datetime = None,
    last_updated_time: Optional[datetime.datetime] = None,
    outputs: List[Dict[str, Any]] = None,
    parameters: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create sample CloudFormation stack data for testing.

    Parameters
    ----------
    stack_name : str
        Stack name
    stack_status : str
        Stack status (e.g., CREATE_COMPLETE, UPDATE_IN_PROGRESS)
    creation_time : datetime.datetime
        When the stack was created
    last_updated_time : datetime.datetime
        When the stack was last updated
    outputs : List[Dict[str, Any]]
        Stack outputs
    parameters : List[Dict[str, Any]]
        Stack parameters

    Returns
    -------
    Dict[str, Any]
        Sample stack data structure
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if creation_time is None:
        creation_time = now - datetime.timedelta(days=1)

    stack_data = {
        "StackName": stack_name,
        "StackId": (
            f"arn:aws:cloudformation:us-west-2:123456789012:stack/{stack_name}/1234567890123456"
        ),
        "CreationTime": creation_time,
        "StackStatus": stack_status,
        "Outputs": outputs or [],
        "Parameters": parameters or [],
    }

    if last_updated_time:
        stack_data["LastUpdatedTime"] = last_updated_time

    return stack_data


def create_sample_stack_resource(
    logical_id: str = "Resource1",
    physical_id: str = "ecs-cluster-12345",
    resource_type: str = "AWS::ECS::Cluster",
    status: str = "CREATE_COMPLETE",
    status_reason: Optional[str] = None,
    last_updated_timestamp: datetime.datetime = None,
) -> Dict[str, Any]:
    """
    Create sample CloudFormation stack resource data for testing.

    Parameters
    ----------
    logical_id : str
        Logical ID of the resource
    physical_id : str
        Physical ID of the resource
    resource_type : str
        Resource type
    status : str
        Resource status
    status_reason : str
        Reason for the current status
    last_updated_timestamp : datetime.datetime
        When the resource was last updated

    Returns
    -------
    Dict[str, Any]
        Sample stack resource data structure
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if last_updated_timestamp is None:
        last_updated_timestamp = now

    resource_data = {
        "LogicalResourceId": logical_id,
        "PhysicalResourceId": physical_id,
        "ResourceType": resource_type,
        "ResourceStatus": status,
        "LastUpdatedTimestamp": last_updated_timestamp,
    }

    if status_reason:
        resource_data["ResourceStatusReason"] = status_reason

    return resource_data


def create_sample_stack_event(
    stack_name: str = "test-stack",
    logical_id: str = "Resource1",
    physical_id: str = "ecs-cluster-12345",
    resource_type: str = "AWS::ECS::Cluster",
    status: str = "CREATE_COMPLETE",
    status_reason: Optional[str] = None,
    timestamp: datetime.datetime = None,
) -> Dict[str, Any]:
    """
    Create sample CloudFormation stack event data for testing.

    Parameters
    ----------
    stack_name : str
        Stack name
    logical_id : str
        Logical ID of the resource
    physical_id : str
        Physical ID of the resource
    resource_type : str
        Resource type
    status : str
        Resource status
    status_reason : str
        Reason for the event
    timestamp : datetime.datetime
        When the event occurred

    Returns
    -------
    Dict[str, Any]
        Sample stack event data structure
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if timestamp is None:
        timestamp = now

    event_data = {
        "StackName": stack_name,
        "StackId": (
            f"arn:aws:cloudformation:us-west-2:123456789012:stack/{stack_name}/1234567890123456"
        ),
        "LogicalResourceId": logical_id,
        "PhysicalResourceId": physical_id,
        "ResourceType": resource_type,
        "ResourceStatus": status,
        "Timestamp": timestamp,
        "EventId": f"1234567890-{timestamp.timestamp():.0f}",
    }

    if status_reason:
        event_data["ResourceStatusReason"] = status_reason

    return event_data
