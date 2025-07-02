"""
Unit tests for the ecs_api_operation function.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.resource_management import camel_to_snake, ecs_api_operation


def test_camel_to_snake():
    """Test the camel_to_snake function."""
    assert camel_to_snake("CreateService") == "create_service"
    assert camel_to_snake("DescribeTaskDefinition") == "describe_task_definition"
    assert camel_to_snake("ListContainerInstances") == "list_container_instances"
    assert camel_to_snake("GetTaskProtection") == "get_task_protection"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.config.get_config")
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_create_service(mock_get_client, mock_get_config):
    """Test ecs_api_operation function with CreateService operation."""
    # Mock get_config to return allow-write=True
    mock_get_config.return_value = {"allow-write": True}

    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.create_service.return_value = {
        "service": {"serviceName": "my-service", "status": "ACTIVE"}
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with CreateService operation
    api_params = {
        "cluster": "my-cluster",
        "serviceName": "my-service",
        "taskDefinition": "my-task-definition",
        "desiredCount": 2,
        "launchType": "FARGATE",
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": ["subnet-1", "subnet-2"],
                "securityGroups": ["sg-1"],
                "assignPublicIp": "ENABLED",
            }
        },
    }

    result = await ecs_api_operation(api_operation="CreateService", api_params=api_params)

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify create_service was called with correct parameters
    mock_ecs.create_service.assert_called_once_with(**api_params)

    # Verify the result
    assert result["service"]["serviceName"] == "my-service"
    assert result["service"]["status"] == "ACTIVE"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_clusters(mock_get_client):
    """Test ecs_api_operation function with DescribeClusters operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.return_value = {
        "clusters": [{"clusterName": "test-cluster", "status": "ACTIVE"}]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeClusters operation
    api_params = {
        "clusters": ["test-cluster"],
        "include": ["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"],
    }

    result = await ecs_api_operation(api_operation="DescribeClusters", api_params=api_params)

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct parameters
    mock_ecs.describe_clusters.assert_called_once_with(**api_params)

    # Verify the result
    assert result["clusters"][0]["clusterName"] == "test-cluster"
    assert result["clusters"][0]["status"] == "ACTIVE"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_list_tasks(mock_get_client):
    """Test ecs_api_operation function with ListTasks operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListTasks operation
    api_params = {
        "cluster": "test-cluster",
        "serviceName": "test-service",
        "desiredStatus": "RUNNING",
    }

    result = await ecs_api_operation(api_operation="ListTasks", api_params=api_params)

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_tasks was called with correct parameters
    mock_ecs.list_tasks.assert_called_once_with(**api_params)

    # Verify the result
    assert len(result["taskArns"]) == 2
    assert "task-1" in result["taskArns"]
    assert "task-2" in result["taskArns"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_unsupported_operation(mock_get_client):
    """Test ecs_api_operation function with an unsupported operation."""
    # Call ecs_api_operation with an unsupported operation
    with pytest.raises(ValueError) as excinfo:
        await ecs_api_operation(api_operation="UnsupportedOperation", api_params={})

    # Verify the error message
    assert "Unsupported API operation" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_error_handling(mock_get_client):
    """Test ecs_api_operation function with an error from the AWS API."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.side_effect = Exception("Test error")
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeClusters operation
    result = await ecs_api_operation(
        api_operation="DescribeClusters", api_params={"clusters": ["test-cluster"]}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct parameters
    mock_ecs.describe_clusters.assert_called_once_with(clusters=["test-cluster"])

    # Verify the result contains the error
    assert "error" in result
    assert "Test error" in result["error"]
    assert result["status"] == "failed"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.config.get_config")
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_write_permission_required(mock_get_client, mock_get_config):
    """Test that write operations require WRITE permission."""
    # Mock get_config to return allow-write=False
    mock_get_config.return_value = {"allow-write": False}

    # Mock get_aws_client (should not be called)
    mock_ecs = MagicMock()
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with CreateCluster operation (requires WRITE permission)
    result = await ecs_api_operation(
        api_operation="CreateCluster", api_params={"clusterName": "test-cluster"}
    )

    # Verify get_config was called
    mock_get_config.assert_called_once()

    # Verify get_aws_client was NOT called (permission check should fail first)
    mock_get_client.assert_not_called()

    # Verify the result contains the permission error
    assert "status" in result
    assert result["status"] == "error"
    assert "error" in result
    assert "requires WRITE permission" in result["error"]
    assert "ALLOW_WRITE=true" in result["error"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.config.get_config")
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_read_only_no_permission_required(mock_get_client, mock_get_config):
    """Test that read-only operations don't require WRITE permission."""
    # Mock get_config to return allow-write=False
    mock_get_config.return_value = {"allow-write": False}

    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListClusters operation (read-only)
    result = await ecs_api_operation(api_operation="ListClusters", api_params={})

    # Verify get_aws_client was called (permission check should pass)
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once_with()

    # Verify the result contains the expected data
    assert "clusterArns" in result
    assert len(result["clusterArns"]) == 2
