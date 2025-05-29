"""
Pytest-style unit tests for status module.
"""

import datetime
import re
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.status import (
    _find_cloudformation_stack,
    _generate_custom_domain_guidance,
    _get_alb_url,
    _get_cfn_stack_status,
    _get_stack_names_to_try,
    get_deployment_status,
)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
@patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_deployment_status_active(
    mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
):
    """Test get_deployment_status with active service."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app-service",
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
                "deployments": [
                    {
                        "status": "PRIMARY",
                        "desiredCount": 2,
                        "runningCount": 2,
                        "pendingCount": 0,
                        "rolloutState": "COMPLETED",
                    }
                ],
                "events": [{"message": "service test-app-service has reached a steady state."}],
            }
        ]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
    mock_ecs.describe_tasks.return_value = {
        "tasks": [
            {
                "taskArn": "task-1",
                "lastStatus": "RUNNING",
                "healthStatus": "HEALTHY",
                "containers": [
                    {"name": "test-app", "lastStatus": "RUNNING", "healthStatus": "HEALTHY"}
                ],
                "startedAt": datetime.datetime(2023, 1, 1, 0, 0, 0),
            },
            {
                "taskArn": "task-2",
                "lastStatus": "RUNNING",
                "healthStatus": "HEALTHY",
                "containers": [
                    {"name": "test-app", "lastStatus": "RUNNING", "healthStatus": "HEALTHY"}
                ],
                "startedAt": datetime.datetime(2023, 1, 1, 0, 0, 0),
            },
        ]
    }

    # Return different clients based on service name
    def get_client_side_effect(service_name):
        if service_name == "ecs":
            return mock_ecs
        return MagicMock()

    mock_get_aws_client.side_effect = get_client_side_effect

    # Mock _get_alb_url
    mock_get_alb_url.return_value = "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"

    # Mock _find_cloudformation_stack
    mock_find_cloudformation_stack.return_value = (
        "test-app-ecs-infrastructure",
        {
            "status": "CREATE_COMPLETE",
            "outputs": {"LoadBalancerDNS": "test-app-alb-123456789.us-west-2.elb.amazonaws.com"},
        },
    )

    # Call get_deployment_status
    result = await get_deployment_status(
        app_name="test-app",
        cluster_name="test-app",
        stack_name="test-app-ecs-infrastructure",
        service_name="test-app-service",
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_with("ecs")

    # Verify describe_services was called
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-app", services=["test-app-service"]
    )

    # Verify list_tasks was called
    mock_ecs.list_tasks.assert_called_once_with(cluster="test-app", serviceName="test-app-service")

    # Verify describe_tasks was called
    mock_ecs.describe_tasks.assert_called_once_with(cluster="test-app", tasks=["task-1", "task-2"])

    # Verify _get_alb_url was called
    mock_get_alb_url.assert_called_once_with("test-app", "test-app-ecs-infrastructure")

    # Verify _find_cloudformation_stack was called
    mock_find_cloudformation_stack.assert_called_once_with(
        "test-app", "test-app-ecs-infrastructure"
    )

    # Verify the result
    assert result["status"] == "COMPLETE"
    assert result["service_status"] == "ACTIVE"
    assert result["desired_count"] == 2
    assert result["running_count"] == 2
    assert result["alb_url"] == "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"
    assert len(result["tasks"]) == 2
    assert result["deployment_status"] == "COMPLETED"
    assert "custom_domain_guidance" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
@patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_deployment_status_deploying(
    mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
):
    """Test get_deployment_status with deploying service."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app-service",
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 1,
                "pendingCount": 1,
                "deployments": [
                    {
                        "status": "PRIMARY",
                        "desiredCount": 2,
                        "runningCount": 1,
                        "pendingCount": 1,
                        "rolloutState": "IN_PROGRESS",
                    }
                ],
                "events": [
                    {"message": "service test-app-service has started 1 tasks: task task-1."},
                    {
                        "message": (
                            "service test-app-service has begun draining connections on 1 tasks."
                        )
                    },
                ],
            }
        ]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
    mock_ecs.describe_tasks.return_value = {
        "tasks": [
            {
                "taskArn": "task-1",
                "lastStatus": "RUNNING",
                "healthStatus": "HEALTHY",
                "containers": [
                    {"name": "test-app", "lastStatus": "RUNNING", "healthStatus": "HEALTHY"}
                ],
                "startedAt": datetime.datetime(2023, 1, 1, 0, 0, 0),
            },
            {
                "taskArn": "task-2",
                "lastStatus": "PROVISIONING",
                "healthStatus": "UNKNOWN",
                "containers": [
                    {"name": "test-app", "lastStatus": "PENDING", "healthStatus": "UNKNOWN"}
                ],
            },
        ]
    }

    # Return different clients based on service name
    def get_client_side_effect(service_name):
        if service_name == "ecs":
            return mock_ecs
        return MagicMock()

    mock_get_aws_client.side_effect = get_client_side_effect

    # Mock _get_alb_url
    mock_get_alb_url.return_value = "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"

    # Mock _find_cloudformation_stack
    mock_find_cloudformation_stack.return_value = (
        "test-app-ecs-infrastructure",
        {
            "status": "CREATE_COMPLETE",
            "outputs": {"LoadBalancerDNS": "test-app-alb-123456789.us-west-2.elb.amazonaws.com"},
        },
    )

    # Call get_deployment_status
    result = await get_deployment_status(
        app_name="test-app",
        cluster_name="test-app",
        stack_name="test-app-ecs-infrastructure",
        service_name="test-app-service",
    )

    # Verify the result
    assert result["status"] == "IN_PROGRESS"
    assert result["service_status"] == "ACTIVE"
    assert result["desired_count"] == 2
    assert result["running_count"] == 1
    assert result["pending_count"] == 1
    assert result["alb_url"] == "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"
    assert len(result["tasks"]) == 2
    assert result["deployment_status"] == "IN_PROGRESS"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
@patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_deployment_status_unhealthy(
    mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
):
    """Test get_deployment_status with unhealthy service."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [
            {
                "serviceName": "test-app-service",
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
                "deployments": [
                    {
                        "status": "PRIMARY",
                        "desiredCount": 2,
                        "runningCount": 2,
                        "pendingCount": 0,
                        "rolloutState": "COMPLETED",
                    }
                ],
                "events": [
                    {"message": "service test-app-service has reached a steady state."},
                    {
                        "message": (
                            "service test-app-service has failed to place a task due to "
                            "No Container Instances were found in your cluster."
                        )
                    },
                ],
            }
        ]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
    mock_ecs.describe_tasks.return_value = {
        "tasks": [
            {
                "taskArn": "task-1",
                "lastStatus": "RUNNING",
                "healthStatus": "UNHEALTHY",
                "containers": [
                    {"name": "test-app", "lastStatus": "RUNNING", "healthStatus": "UNHEALTHY"}
                ],
                "startedAt": datetime.datetime(2023, 1, 1, 0, 0, 0),
            },
            {
                "taskArn": "task-2",
                "lastStatus": "RUNNING",
                "healthStatus": "UNHEALTHY",
                "containers": [
                    {"name": "test-app", "lastStatus": "RUNNING", "healthStatus": "UNHEALTHY"}
                ],
                "startedAt": datetime.datetime(2023, 1, 1, 0, 0, 0),
            },
        ]
    }

    # Return different clients based on service name
    def get_client_side_effect(service_name):
        if service_name == "ecs":
            return mock_ecs
        return MagicMock()

    mock_get_aws_client.side_effect = get_client_side_effect

    # Mock _get_alb_url
    mock_get_alb_url.return_value = "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"

    # Mock _find_cloudformation_stack
    mock_find_cloudformation_stack.return_value = (
        "test-app-ecs-infrastructure",
        {
            "status": "CREATE_COMPLETE",
            "outputs": {"LoadBalancerDNS": "test-app-alb-123456789.us-west-2.elb.amazonaws.com"},
        },
    )

    # Call get_deployment_status
    result = await get_deployment_status(
        app_name="test-app",
        cluster_name="test-app",
        stack_name="test-app-ecs-infrastructure",
        service_name="test-app-service",
    )

    # Verify the result
    assert result["status"] == "COMPLETE"
    assert result["service_status"] == "ACTIVE"
    assert result["desired_count"] == 2
    assert result["running_count"] == 2
    assert result["alb_url"] == "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"
    assert len(result["tasks"]) == 2
    assert all(task["health_status"] == "UNHEALTHY" for task in result["tasks"])
    assert result["deployment_status"] == "COMPLETED"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_deployment_status_service_not_found(
    mock_get_aws_client, mock_find_cloudformation_stack
):
    """Test get_deployment_status with service not found."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [],
        "failures": [{"arn": "test-app-service", "reason": "MISSING"}],
    }

    # Return different clients based on service name
    def get_client_side_effect(service_name):
        if service_name == "ecs":
            return mock_ecs
        return MagicMock()

    mock_get_aws_client.side_effect = get_client_side_effect

    # Mock _find_cloudformation_stack
    mock_find_cloudformation_stack.return_value = (
        "test-app-ecs-infrastructure",
        {
            "status": "CREATE_COMPLETE",
            "outputs": {"LoadBalancerDNS": "test-app-alb-123456789.us-west-2.elb.amazonaws.com"},
        },
    )

    # Call get_deployment_status
    result = await get_deployment_status(
        app_name="test-app",
        cluster_name="test-app",
        stack_name="test-app-ecs-infrastructure",
        service_name="test-app-service",
    )

    # Verify the result
    assert result["status"] == "NOT_FOUND"
    assert "Service test-app-service not found" in result["message"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_find_cloudformation_stack(mock_get_aws_client):
    """Test _find_cloudformation_stack."""
    # Mock get_aws_client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [{"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"}]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Call _find_cloudformation_stack
    result, status = await _find_cloudformation_stack(
        app_name="test-app", stack_name="test-app-ecs-infrastructure"
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("cloudformation")

    # Verify describe_stacks was called
    mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app-ecs-infrastructure")

    # Verify the result
    assert result == "test-app-ecs-infrastructure"
    assert status["status"] == "CREATE_COMPLETE"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_find_cloudformation_stack_not_found(mock_get_aws_client):
    """Test _find_cloudformation_stack with stack not found."""
    # Mock get_aws_client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.side_effect = Exception(
        "Stack test-app-ecs-infrastructure does not exist"
    )
    mock_get_aws_client.return_value = mock_cfn

    # Call _find_cloudformation_stack
    result, status = await _find_cloudformation_stack(
        app_name="test-app", stack_name="test-app-ecs-infrastructure"
    )

    # Verify the result
    assert result is None
    assert status["status"] == "NOT_FOUND"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_alb_url(mock_get_aws_client):
    """Test _get_alb_url."""
    # Mock get_aws_client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackName": "test-app-ecs-infrastructure",
                "Outputs": [
                    {
                        "OutputKey": "LoadBalancerDNS",
                        "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                    }
                ],
            }
        ]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Call _get_alb_url
    result = await _get_alb_url(app_name="test-app", known_stack_name="test-app-ecs-infrastructure")

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("cloudformation")

    # Verify describe_stacks was called
    mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app-ecs-infrastructure")

    # Verify the result
    assert result == "http://test-app-alb-123456789.us-west-2.elb.amazonaws.com"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
async def test_get_alb_url_not_found(mock_find_cloudformation_stack):
    """Test _get_alb_url with ALB URL not found."""
    # Mock _find_cloudformation_stack
    mock_find_cloudformation_stack.return_value = (
        "test-app-ecs-infrastructure",
        {"status": "CREATE_COMPLETE", "outputs": {"OtherOutput": "some-value"}},
    )

    # Call _get_alb_url
    result = await _get_alb_url(app_name="test-app", known_stack_name="test-app-ecs-infrastructure")

    # Verify the result
    assert result is None


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_cfn_stack_status(mock_get_aws_client):
    """Test _get_cfn_stack_status."""
    # Mock get_aws_client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackName": "test-app-ecs-infrastructure",
                "StackStatus": "CREATE_COMPLETE",
                "Outputs": [
                    {
                        "OutputKey": "LoadBalancerDNSName",
                        "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                    }
                ],
            }
        ]
    }
    mock_cfn.describe_stack_events.return_value = {
        "StackEvents": [
            {
                "Timestamp": datetime.datetime(2023, 1, 1, 0, 0, 0),
                "ResourceType": "AWS::ECS::Service",
                "ResourceStatus": "CREATE_COMPLETE",
                "ResourceStatusReason": "Resource creation completed",
            }
        ]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Call _get_cfn_stack_status
    result = await _get_cfn_stack_status(stack_name="test-app-ecs-infrastructure")

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("cloudformation")

    # Verify describe_stacks was called
    mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app-ecs-infrastructure")

    # Verify describe_stack_events was called
    mock_cfn.describe_stack_events.assert_called_once_with(StackName="test-app-ecs-infrastructure")

    # Verify the result
    assert result["status"] == "CREATE_COMPLETE"
    assert "LoadBalancerDNSName" in result["outputs"]
    assert (
        result["outputs"]["LoadBalancerDNSName"]
        == "test-app-alb-123456789.us-west-2.elb.amazonaws.com"
    )
    assert len(result["recent_events"]) == 1
    assert result["recent_events"][0]["status"] == "CREATE_COMPLETE"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
async def test_get_cfn_stack_status_not_found(mock_get_aws_client):
    """Test _get_cfn_stack_status with stack not found."""
    # Mock get_aws_client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.side_effect = Exception(
        "Stack test-app-ecs-infrastructure does not exist"
    )
    mock_get_aws_client.return_value = mock_cfn

    # Call _get_cfn_stack_status
    result = await _get_cfn_stack_status(stack_name="test-app-ecs-infrastructure")

    # Verify the result
    assert result["status"] == "NOT_FOUND"
    assert "Stack test-app-ecs-infrastructure not found" in result["details"]


def test_get_stack_names_to_try():
    """Test _get_stack_names_to_try."""
    # Call _get_stack_names_to_try
    result = _get_stack_names_to_try(app_name="test-app", stack_name=None)

    # Verify the result
    assert "test-app-ecs-infrastructure" in result
    assert "test-app-ecs" in result


def test_get_stack_names_to_try_with_stack_name():
    """Test _get_stack_names_to_try with explicit stack name."""
    # Call _get_stack_names_to_try
    result = _get_stack_names_to_try(app_name="test-app", stack_name="custom-stack-name")

    # Verify the result
    assert result[0] == "custom-stack-name"
    assert "test-app-ecs-infrastructure" in result
    assert "test-app-ecs" in result


def test_generate_custom_domain_guidance():
    """Test _generate_custom_domain_guidance."""
    # Call _generate_custom_domain_guidance
    result = _generate_custom_domain_guidance(
        app_name="test-app", alb_url="test-app-alb-123456789.us-west-2.elb.amazonaws.com"
    )

    # Verify the result
    assert "custom_domain" in result
    assert "https_setup" in result
    assert "cloudformation_update" in result
    assert "next_steps" in result

    result_str = str(result)
    alb_pattern = r"test-app-alb-\d+\.us-west-2\.elb\.amazonaws\.com"
    assert re.search(alb_pattern, result_str) is not None

    assert "Route 53" in str(result)
    assert "HTTPS" in str(result)
