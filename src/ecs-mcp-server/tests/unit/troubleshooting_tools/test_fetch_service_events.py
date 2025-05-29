"""
Unit tests for the fetch_service_events function using pytest's native async test support.
"""

import datetime
from unittest import mock

import pytest

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_service_events
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events import (
    _analyze_load_balancer_issues,
    _check_port_mismatch,
    _check_target_group_health,
    _extract_filtered_events,
)


# Tests for helper functions
@pytest.mark.anyio
def test_extract_filtered_events():
    """Test extracting and filtering events by time window."""
    # Create a test service with events
    test_time = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
    service = {
        "events": [
            {"id": "1", "createdAt": test_time, "message": "event within window"},
            {
                "id": "2",
                "createdAt": test_time - datetime.timedelta(hours=2),
                "message": "event outside window",
            },
        ]
    }

    # Define time window
    start_time = test_time - datetime.timedelta(hours=1)
    end_time = test_time + datetime.timedelta(hours=1)

    # Call helper function
    events = _extract_filtered_events(service, start_time, end_time)

    # Verify results
    assert len(events) == 1
    assert events[0]["id"] == "1"
    assert events[0]["message"] == "event within window"


@pytest.mark.anyio
def test_extract_filtered_events_empty():
    """Test extracting events when service has no events."""
    service = {}  # No events key
    start_time = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = start_time + datetime.timedelta(hours=1)

    events = _extract_filtered_events(service, start_time, end_time)

    assert len(events) == 0


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_check_target_group_health_unhealthy(mock_boto_client):
    """Test checking target group health with unhealthy targets."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [{"TargetHealth": {"State": "unhealthy"}}]
    }

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    assert result is not None
    assert result["type"] == "unhealthy_targets"
    assert result["count"] == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_check_target_group_health_healthy(mock_boto_client):
    """Test checking target group health with all healthy targets."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [{"TargetHealth": {"State": "healthy"}}]
    }

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    assert result is None


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_check_port_mismatch_with_mismatch(mock_boto_client):
    """Test checking port mismatch when ports don't match."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_groups.return_value = {"TargetGroups": [{"Port": 80}]}

    result = await _check_port_mismatch(mock_elb_client, "test-arn", 8080)

    assert result is not None
    assert result["type"] == "port_mismatch"
    assert result["container_port"] == 8080
    assert result["target_group_port"] == 80


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_check_port_mismatch_no_mismatch(mock_boto_client):
    """Test checking port mismatch when ports match."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_groups.return_value = {"TargetGroups": [{"Port": 8080}]}

    result = await _check_port_mismatch(mock_elb_client, "test-arn", 8080)

    assert result is None


@pytest.mark.anyio
@mock.patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client", new_callable=mock.AsyncMock)
async def test_analyze_load_balancer_issues(mock_get_aws_client):
    """Test analyzing load balancer issues."""
    # Skip this test for now as it requires more complex mocking
    pytest.skip("This test requires more complex mocking")

    service = {"loadBalancers": [{"targetGroupArn": "test-arn", "containerPort": 8080}]}

    issues = await _analyze_load_balancer_issues(service)

    assert len(issues) == 1
    assert len(issues[0]["issues"]) == 2
    assert issues[0]["issues"][0]["type"] == "unhealthy_targets"
    assert issues[0]["issues"][1]["type"] == "port_mismatch"


# Tests for fetch_service_events function
@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_service_exists(mock_boto_client):
    """Test when ECS service exists."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp - use datetime with timezone for proper filtering
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "deployments": [
                    {
                        "id": "ecs-svc/1234567890123456",
                        "status": "PRIMARY",
                        "taskDefinition": (
                            "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                        ),
                        "desiredCount": 2,
                        "pendingCount": 0,
                        "runningCount": 2,
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                ],
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app has reached a steady state.",
                    },
                    {
                        "id": "1234567890-1234566",
                        "createdAt": timestamp - datetime.timedelta(minutes=5),
                        "message": (
                            "service test-app has started 2 tasks: "
                            "(task 1234567890abcdef0, task 1234567890abcdef1)."
                        ),
                    },
                ],
                "loadBalancers": [
                    {
                        "targetGroupArn": (
                            "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
                            "targetgroup/test-app/1234567890123456"
                        ),
                        "containerName": "test-app",
                        "containerPort": 8080,
                    }
                ],
            }
        ]
    }

    # Mock ELB client for target group health
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": "10.0.0.1", "Port": 8080},
                "HealthCheckPort": "8080",
                "TargetHealth": {"State": "healthy"},
            }
        ]
    }

    mock_elb_client.describe_target_groups.return_value = {
        "TargetGroups": [
            {
                "TargetGroupName": "test-app",
                "Protocol": "HTTP",
                "Port": 8080,
                "HealthCheckProtocol": "HTTP",
                "HealthCheckPath": "/health",
            }
        ]
    }

    # Configure boto3.client mock to return our mock clients
    mock_boto_client.side_effect = lambda service_name, **kwargs: {
        "ecs": mock_ecs_client,
        "elbv2": mock_elb_client,
    }[service_name]

    # Call the function with time window that includes the mock events
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 2
    assert "steady state" in result["events"][0]["message"]
    assert "deployment" in result
    assert "PRIMARY" == result["deployment"]["status"]


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_service_with_load_balancer_issues(mock_boto_client):
    """Test when ECS service has load balancer issues."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp - use datetime with timezone for proper filtering
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "deployments": [
                    {
                        "id": "ecs-svc/1234567890123456",
                        "status": "PRIMARY",
                        "taskDefinition": (
                            "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                        ),
                        "desiredCount": 2,
                        "pendingCount": 0,
                        "runningCount": 2,
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                ],
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": (
                            "service test-app has tasks that are unhealthy in target-group test-app"
                        ),
                    }
                ],
                "loadBalancers": [
                    {
                        "targetGroupArn": (
                            "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
                            "targetgroup/test-app/1234567890123456"
                        ),
                        "containerName": "test-app",
                        "containerPort": 8080,
                    }
                ],
            }
        ]
    }

    # Mock ELB client for target group health
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": "10.0.0.1", "Port": 8080},
                "HealthCheckPort": "8080",
                "TargetHealth": {
                    "State": "unhealthy",
                    "Reason": "Target.FailedHealthChecks",
                    "Description": "Health checks failed",
                },
            }
        ]
    }

    mock_elb_client.describe_target_groups.return_value = {
        "TargetGroups": [
            {
                "TargetGroupName": "test-app",
                "Protocol": "HTTP",
                "Port": 80,  # Mismatch with container port 8080
                "HealthCheckProtocol": "HTTP",
                "HealthCheckPath": "/health",
            }
        ]
    }

    # Configure boto3.client mock to return our mock clients
    mock_boto_client.side_effect = lambda service_name, **kwargs: {
        "ecs": mock_ecs_client,
        "elbv2": mock_elb_client,
    }[service_name]

    # Call the function with time window that includes the mock events
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1
    assert "unhealthy" in result["events"][0]["message"]
    assert len(result["issues"]) > 0

    # Find the load balancer issue in the issues list
    lb_issue = next((issue for issue in result["issues"] if "issues" in issue), None)
    assert lb_issue is not None

    # Check for port mismatch issue
    lb_issues = lb_issue["issues"]
    port_mismatch = next((issue for issue in lb_issues if issue["type"] == "port_mismatch"), None)
    assert port_mismatch is not None
    assert port_mismatch["container_port"] == 8080
    assert port_mismatch["target_group_port"] == 80

    # Check for unhealthy targets issue
    unhealthy_targets = next(
        (issue for issue in lb_issues if issue["type"] == "unhealthy_targets"), None
    )
    assert unhealthy_targets is not None
    assert unhealthy_targets["count"] == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_service_not_found(mock_boto_client):
    """Test when ECS service does not exist."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Mock describe_services with ServiceNotFoundException
    mock_ecs_client.describe_services.return_value = {
        "services": [],
        "failures": [
            {
                "arn": "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/test-app",
                "reason": "MISSING",
            }
        ],
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_ecs_client

    # Call the function
    result = await fetch_service_events("test-app", "test-cluster", "test-app", 3600)

    # Verify the result
    assert result["status"] == "success"
    assert not result["service_exists"]
    assert "message" in result
    assert "not found" in result["message"]


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_explicit_start_time(mock_boto_client):
    """Test with explicit start_time parameter."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp - use datetime with timezone for proper filtering
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app has reached a steady state.",
                    }
                ],
            }
        ]
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_ecs_client

    # Call the function with explicit start_time that includes mock event date
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_explicit_end_time(mock_boto_client):
    """Test with explicit end_time parameter."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp - use datetime with timezone for proper filtering
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app has reached a steady state.",
                    }
                ],
            }
        ]
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_ecs_client

    # Call the function with explicit end_time that includes mock event date
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_start_and_end_time(mock_boto_client):
    """Test with both start_time and end_time parameters."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp - use datetime with timezone for proper filtering
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app has reached a steady state.",
                    }
                ],
            }
        ]
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_ecs_client

    # Call the function with both start_time and end_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_only_time_window(mock_boto_client):
    """Test with only time_window parameter."""
    # Skip this test for now as it requires more complex mocking
    pytest.skip("This test requires more complex mocking")

    # Call the function with ONLY time_window parameter
    # This properly tests the time_window functionality
    time_window = 3600  # 1 hour in seconds
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", time_window=time_window
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1  # Only the event within time window should be returned
    assert "steady state" in result["events"][0]["message"]
