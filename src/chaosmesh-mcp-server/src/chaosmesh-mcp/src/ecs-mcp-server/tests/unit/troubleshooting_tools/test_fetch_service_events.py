"""
Unit tests for the fetch_service_events function.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_service_events
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events import (
    _analyze_load_balancer_issues,
    _check_port_mismatch,
    _check_target_group_health,
    _extract_filtered_events,
)
from tests.unit.utils.async_test_utils import AsyncIterator

# ----------------------------------------------------------------------------
# Tests for helper functions
# ----------------------------------------------------------------------------


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
def test_extract_filtered_events_missing_timestamp():
    """Test when events have missing timestamps."""
    test_time = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
    service = {
        "events": [
            {"id": "1", "createdAt": test_time, "message": "event with timestamp"},
            {"id": "2", "message": "event missing timestamp"},  # Missing createdAt
        ]
    }

    start_time = test_time - datetime.timedelta(hours=1)
    end_time = test_time + datetime.timedelta(hours=1)

    events = _extract_filtered_events(service, start_time, end_time)

    # Should only include the event with a timestamp
    assert len(events) == 1
    assert events[0]["id"] == "1"


@pytest.mark.anyio
def test_extract_filtered_events_no_timezone():
    """Test when event timestamps don't have timezone info."""
    # Create timestamp without timezone
    naive_time = datetime.datetime(2025, 5, 13, 12, 0, 0)  # No timezone info

    service = {
        "events": [{"id": "1", "createdAt": naive_time, "message": "event with naive timestamp"}]
    }

    # Time window with timezone
    start_time = datetime.datetime(2025, 5, 13, 11, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 13, 0, 0, tzinfo=datetime.timezone.utc)

    events = _extract_filtered_events(service, start_time, end_time)

    # Should add timezone and include the event
    assert len(events) == 1
    assert events[0]["id"] == "1"


@pytest.mark.anyio
async def test_check_target_group_health_unhealthy():
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
async def test_check_target_group_health_healthy():
    """Test checking target group health with all healthy targets."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [{"TargetHealth": {"State": "healthy"}}]
    }

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    assert result is None


@pytest.mark.anyio
async def test_check_target_group_health_empty_response():
    """Test checking target group health with empty response."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Mock an empty response with no TargetHealthDescriptions
    mock_elb_client.describe_target_health.return_value = {
        # Empty TargetHealthDescriptions array
    }

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    # Should return None when there are no targets
    assert result is None


@pytest.mark.anyio
async def test_check_target_group_health_no_targets():
    """Test checking target group health with empty targets list."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Mock a response with empty TargetHealthDescriptions array
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": []  # Empty array
    }

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    # Should return None when there are no targets
    assert result is None


@pytest.mark.anyio
async def test_check_target_group_health_client_error():
    """Test handling ClientError in target group health check."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Mock describe_target_health to raise ClientError
    mock_elb_client.describe_target_health.side_effect = ClientError(
        {"Error": {"Code": "InvalidTargetGroup", "Message": "Target group not found"}},
        "DescribeTargetHealth",
    )

    result = await _check_target_group_health(mock_elb_client, "test-arn")

    # Should return error info when ClientError occurs
    assert result is not None
    assert result["type"] == "health_check_error"
    assert "Target group not found" in result["error"]


@pytest.mark.anyio
async def test_check_port_mismatch_with_mismatch():
    """Test checking port mismatch when ports don't match."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_groups.return_value = {"TargetGroups": [{"Port": 80}]}

    result = await _check_port_mismatch(mock_elb_client, "test-arn", 8080)

    assert result is not None
    assert result["type"] == "port_mismatch"
    assert result["container_port"] == 8080
    assert result["target_group_port"] == 80


@pytest.mark.anyio
async def test_check_port_mismatch_no_mismatch():
    """Test checking port mismatch when ports match."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_groups.return_value = {"TargetGroups": [{"Port": 8080}]}

    result = await _check_port_mismatch(mock_elb_client, "test-arn", 8080)

    assert result is None


@pytest.mark.anyio
async def test_check_port_mismatch_client_error():
    """Test handling ClientError in port mismatch check."""
    mock_elb_client = mock.Mock()
    mock_elb_client.describe_target_groups.side_effect = ClientError(
        {"Error": {"Code": "InvalidTargetGroup", "Message": "Target group not found"}},
        "DescribeTargetGroups",
    )

    result = await _check_port_mismatch(mock_elb_client, "test-arn", 8080)

    assert result is not None
    assert result["type"] == "target_group_error"
    assert "Target group not found" in result["error"]


@pytest.mark.anyio
async def test_analyze_load_balancer_issues():
    """Test analyzing load balancer issues."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Mock describe_target_health response for unhealthy targets
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": "10.0.0.1", "Port": 8080},
                "HealthCheckPort": "8080",
                "TargetHealth": {"State": "unhealthy", "Reason": "Target.FailedHealthChecks"},
            }
        ]
    }

    # Mock describe_target_groups response for port mismatch
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

    # Define a service with a load balancer configuration
    service = {
        "loadBalancers": [
            {"targetGroupArn": "test-arn", "containerName": "test-container", "containerPort": 8080}
        ]
    }

    # Call the function with our mock
    issues = await _analyze_load_balancer_issues(service, elb_client=mock_elb_client)

    # Verify the results
    assert len(issues) == 1
    assert len(issues[0]["issues"]) == 2

    # Check types of issues found
    issue_types = [issue["type"] for issue in issues[0]["issues"]]
    assert "unhealthy_targets" in issue_types
    assert "port_mismatch" in issue_types

    # Check the details of the port mismatch issue
    port_issue = next(issue for issue in issues[0]["issues"] if issue["type"] == "port_mismatch")
    assert port_issue["container_port"] == 8080
    assert port_issue["target_group_port"] == 80


@pytest.mark.anyio
async def test_analyze_load_balancer_no_targetgroup():
    """Test analyzing load balancers without target group ARNs."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Define a service with load balancer but no targetGroupArn
    service = {
        "loadBalancers": [
            {
                "containerName": "test-container",
                "containerPort": 8080,
                # No targetGroupArn provided
            }
        ]
    }

    # Call the function
    issues = await _analyze_load_balancer_issues(service, mock_elb_client)

    # Should not find any issues since no target group to check
    assert len(issues) == 0

    # Verify targetGroupArn check
    assert not mock_elb_client.describe_target_health.called


@pytest.mark.anyio
async def test_analyze_load_balancer_no_containerport():
    """Test analyzing load balancers without container port."""
    # Mock ELB client
    mock_elb_client = mock.Mock()

    # Mock describe_target_health to return unhealthy targets
    mock_elb_client.describe_target_health.return_value = {
        "TargetHealthDescriptions": [
            {"Target": {"Id": "10.0.0.1", "Port": 8080}, "TargetHealth": {"State": "unhealthy"}}
        ]
    }

    # Define a service with load balancer but no containerPort
    service = {
        "loadBalancers": [
            {
                "targetGroupArn": "test-arn",
                "containerName": "test-container",
                # No containerPort provided
            }
        ]
    }

    # Call the function
    issues = await _analyze_load_balancer_issues(service, mock_elb_client)

    # Should find health issues but not port issues
    assert len(issues) == 1
    assert len(issues[0]["issues"]) == 1
    assert issues[0]["issues"][0]["type"] == "unhealthy_targets"

    # Verify targetGroupArn check but not port check
    assert mock_elb_client.describe_target_health.called
    assert not mock_elb_client.describe_target_groups.called


# ----------------------------------------------------------------------------
# Tests for fetch_service_events function
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_service_exists():
    """Test when ECS service exists."""
    # Mock ECS client with proper pagination
    mock_ecs_client = mock.Mock()

    # Set up proper pagination for any paginator functions
    mock_paginator = mock.Mock()  # Use regular Mock, not AsyncMock
    mock_paginator.paginate.return_value = AsyncIterator([])
    mock_ecs_client.get_paginator.return_value = mock_paginator

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

    # Call the function with time window that includes the mock events and inject our mocks
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app",
        "test-cluster",
        "test-app",
        3600,
        start_time=start_time,
        end_time=end_time,
        ecs_client=mock_ecs_client,
        elb_client=mock_elb_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 2
    assert "steady state" in result["events"][0]["message"]
    assert "deployment" in result
    assert "PRIMARY" == result["deployment"]["status"]


@pytest.mark.anyio
async def test_service_with_load_balancer_issues():
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

    # Call the function with time window that includes the mock events and inject our mocks
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app",
        "test-cluster",
        "test-app",
        3600,
        start_time=start_time,
        end_time=end_time,
        ecs_client=mock_ecs_client,
        elb_client=mock_elb_client,
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
async def test_service_with_failed_deployment():
    """Test when service has a failed deployment."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response with a FAILED rolloutState
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "deployments": [
                    {
                        "id": "ecs-svc/1234567890123456",
                        "status": "PRIMARY",
                        "rolloutState": "FAILED",
                        "rolloutStateReason": "Deployment failed due to health checks",
                        "taskDefinition": "\
                            arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                        "desiredCount": 2,
                        "pendingCount": 0,
                        "runningCount": 0,
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                ],
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app deployment failed.",
                    }
                ],
            }
        ]
    }

    # Call the function
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, ecs_client=mock_ecs_client
    )

    # Verify the result includes the failed deployment issue
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["issues"]) > 0

    # Check for failed_deployment issue
    deployment_issue = next(
        (issue for issue in result["issues"] if issue.get("type") == "failed_deployment"), None
    )
    assert deployment_issue is not None
    assert deployment_issue["reason"] == "Deployment failed due to health checks"


@pytest.mark.anyio
async def test_service_with_stalled_deployment():
    """Test when service has a stalled deployment."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Event timestamp
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Mock describe_services response with stalled deployment (pending > 0, running < desired)
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "deployments": [
                    {
                        "id": "ecs-svc/1234567890123456",
                        "status": "PRIMARY",
                        "rolloutState": "IN_PROGRESS",
                        "taskDefinition": "arn:aws:ecs:us-west-2:"
                        "123456789012:task-definition/test-app:1",
                        "desiredCount": 4,
                        "pendingCount": 2,
                        "runningCount": 1,
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                ],
                "events": [
                    {
                        "id": "1234567890-1234567",
                        "createdAt": timestamp,
                        "message": "service test-app has tasks that are pending.",
                    }
                ],
            }
        ]
    }

    # Call the function
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, ecs_client=mock_ecs_client
    )

    # Verify the result includes the stalled deployment issue
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["issues"]) > 0

    # Check for stalled_deployment issue
    deployment_issue = next(
        (issue for issue in result["issues"] if issue.get("type") == "stalled_deployment"), None
    )
    assert deployment_issue is not None
    assert deployment_issue["pending_count"] == 2
    assert deployment_issue["running_count"] == 1
    assert deployment_issue["desired_count"] == 4


@pytest.mark.anyio
async def test_service_not_found():
    """Test when ECS service does not exist."""
    # Mock ECS client with proper pagination
    mock_ecs_client = mock.Mock()

    # Set up proper pagination for any paginator functions
    mock_paginator = mock.Mock()  # Use regular Mock, not AsyncMock
    mock_paginator.paginate.return_value = AsyncIterator([])
    mock_ecs_client.get_paginator.return_value = mock_paginator

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

    # Call the function with our mock
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, ecs_client=mock_ecs_client
    )

    # Verify the result
    assert result["status"] == "success"
    assert not result["service_exists"]
    assert "message" in result
    assert "not found" in result["message"]


@pytest.mark.anyio
async def test_with_explicit_start_time():
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

    # Call the function with explicit start_time that includes mock event date
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app",
        "test-cluster",
        "test-app",
        3600,
        start_time=start_time,
        end_time=end_time,
        ecs_client=mock_ecs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
async def test_with_explicit_end_time():
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

    # Call the function with explicit end_time that includes mock event date
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app",
        "test-cluster",
        "test-app",
        3600,
        start_time=start_time,
        end_time=end_time,
        ecs_client=mock_ecs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
async def test_with_start_and_end_time():
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

    # Call the function with both start_time and end_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_service_events(
        "test-app",
        "test-cluster",
        "test-app",
        3600,
        start_time=start_time,
        end_time=end_time,
        ecs_client=mock_ecs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]
    assert len(result["events"]) == 1


@pytest.mark.anyio
async def test_with_only_time_window():
    """Test with only time_window parameter."""
    # Mock ECS client
    mock_ecs_client = mock.Mock()

    # Create two events with different timestamps
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_event_time = now - datetime.timedelta(
        minutes=30
    )  # 30 minutes ago, within the 1-hour window
    old_event_time = now - datetime.timedelta(hours=2)  # 2 hours ago, outside the 1-hour window

    # Mock describe_services response with events at different times
    mock_ecs_client.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app",
                "status": "ACTIVE",
                "events": [
                    {
                        "id": "recent-event",
                        "createdAt": recent_event_time,
                        "message": "service test-app has reached a steady state.",
                    },
                    {
                        "id": "old-event",
                        "createdAt": old_event_time,
                        "message": "service test-app was older event outside time window.",
                    },
                ],
            }
        ]
    }

    # Call the function with only time_window parameter (1 hour)
    time_window = 3600  # 1 hour in seconds
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", time_window=time_window, ecs_client=mock_ecs_client
    )

    # Verify the result
    assert result["status"] == "success"
    assert result["service_exists"]

    # Only the recent event (within time window) should be included
    assert len(result["events"]) == 1
    assert result["events"][0]["id"] == "recent-event"
    assert "steady state" in result["events"][0]["message"]


@pytest.mark.anyio
async def test_service_client_error():
    """Test handling ClientError in service call."""
    # Mock ECS client with an error
    mock_ecs_client = mock.Mock()
    mock_ecs_client.describe_services.side_effect = ClientError(
        {"Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}},
        "DescribeServices",
    )

    # Call the function
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, ecs_client=mock_ecs_client
    )

    # Verify error handling
    assert result["status"] == "error"
    assert "AWS API error" in result["error"]
    assert "ClusterNotFoundException" in result["error"] or "Cluster not found" in result["error"]


@pytest.mark.anyio
async def test_general_exception():
    """Test handling general exceptions."""
    # Mock ECS client with a general exception
    mock_ecs_client = mock.Mock()
    mock_ecs_client.describe_services.side_effect = Exception("Unexpected error")

    # Call the function
    result = await fetch_service_events(
        "test-app", "test-cluster", "test-app", 3600, ecs_client=mock_ecs_client
    )

    # Verify error handling
    assert result["status"] == "error"
    assert result["error"] == "Unexpected error"
