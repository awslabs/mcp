"""
Unit tests for resource management module.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation

# ----------------------------------------------------------------------------
# Main Resource Management Function Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_cluster(mock_get_client):
    """Test ecs_api_operation function with DescribeClusters operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.return_value = {
        "clusters": [{"clusterName": "test-cluster", "status": "ACTIVE"}]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeClusters operation
    result = await ecs_api_operation(
        api_operation="DescribeClusters",
        api_params={
            "clusters": ["test-cluster"],
            "include": ["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"],
        },
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct parameters
    mock_ecs.describe_clusters.assert_called_once_with(
        clusters=["test-cluster"], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
    )

    # Verify the result
    assert result["clusters"][0]["clusterName"] == "test-cluster"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_list_services(mock_get_client):
    """Test ecs_api_operation function with ListServices operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_services.return_value = {"serviceArns": ["service-1", "service-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListServices operation
    result = await ecs_api_operation(
        api_operation="ListServices", api_params={"cluster": "test-cluster"}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_services was called with correct parameters
    mock_ecs.list_services.assert_called_once_with(cluster="test-cluster")

    # Verify the result
    assert len(result["serviceArns"]) == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_services(mock_get_client):
    """Test ecs_api_operation function with DescribeServices operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [{"serviceName": "test-service", "status": "ACTIVE", "events": []}]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeServices operation
    result = await ecs_api_operation(
        api_operation="DescribeServices",
        api_params={"cluster": "test-cluster", "services": ["test-service"], "include": ["TAGS"]},
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_services was called with correct parameters
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-cluster", services=["test-service"], include=["TAGS"]
    )

    # Verify the result
    assert result["services"][0]["serviceName"] == "test-service"


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
async def test_ecs_api_operation_list_clusters(mock_get_client):
    """Test ecs_api_operation function with ListClusters operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListClusters operation
    result = await ecs_api_operation(api_operation="ListClusters", api_params={})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once_with()

    # Verify the result
    assert len(result["clusterArns"]) == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_list_tasks(mock_get_client):
    """Test ecs_api_operation function with ListTasks operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListTasks operation
    result = await ecs_api_operation(
        api_operation="ListTasks",
        api_params={
            "cluster": "test-cluster",
            "serviceName": "test-service",
            "desiredStatus": "RUNNING",
        },
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_tasks was called with correct parameters
    mock_ecs.list_tasks.assert_called_once_with(
        cluster="test-cluster", serviceName="test-service", desiredStatus="RUNNING"
    )

    # Verify the result
    assert len(result["taskArns"]) == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_tasks(mock_get_client):
    """Test ecs_api_operation function with DescribeTasks operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_tasks.return_value = {
        "tasks": [
            {
                "taskArn": "task-1",
                "lastStatus": "RUNNING",
                "taskDefinitionArn": "task-def-1",
                "containers": [{"name": "container-1", "lastStatus": "RUNNING"}],
            }
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeTasks operation
    result = await ecs_api_operation(
        api_operation="DescribeTasks",
        api_params={"cluster": "test-cluster", "tasks": ["task-1"], "include": ["TAGS"]},
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_tasks was called with correct parameters
    mock_ecs.describe_tasks.assert_called_once_with(
        cluster="test-cluster", tasks=["task-1"], include=["TAGS"]
    )

    # Verify the result
    assert result["tasks"][0]["taskArn"] == "task-1"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_list_task_definitions(mock_get_client):
    """Test ecs_api_operation function with ListTaskDefinitions operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_task_definitions.return_value = {"taskDefinitionArns": ["taskdef-1", "taskdef-2"]}
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListTaskDefinitions operation
    result = await ecs_api_operation(
        api_operation="ListTaskDefinitions",
        api_params={"familyPrefix": "test-family", "status": "ACTIVE"},
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_task_definitions was called with correct parameters
    mock_ecs.list_task_definitions.assert_called_once_with(
        familyPrefix="test-family", status="ACTIVE"
    )

    # Verify the result
    assert result["taskDefinitionArns"] == ["taskdef-1", "taskdef-2"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_task_definition(mock_get_client):
    """Test ecs_api_operation function with DescribeTaskDefinition operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_task_definition.return_value = {
        "taskDefinition": {
            "family": "test-family",
            "revision": 1,
            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-family:1",
        }
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeTaskDefinition operation
    result = await ecs_api_operation(
        api_operation="DescribeTaskDefinition", api_params={"taskDefinition": "test-family:1"}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_task_definition was called with correct parameters
    mock_ecs.describe_task_definition.assert_called_once_with(taskDefinition="test-family:1")

    # Verify the result
    assert result["taskDefinition"]["family"] == "test-family"
    assert result["taskDefinition"]["revision"] == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_list_container_instances(mock_get_client):
    """Test ecs_api_operation function with ListContainerInstances operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_container_instances.return_value = {
        "containerInstanceArns": ["instance-1", "instance-2"]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with ListContainerInstances operation
    result = await ecs_api_operation(
        api_operation="ListContainerInstances", api_params={"cluster": "test-cluster"}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_container_instances was called with correct parameters
    mock_ecs.list_container_instances.assert_called_once_with(cluster="test-cluster")

    # Verify the result
    assert len(result["containerInstanceArns"]) == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_container_instances(mock_get_client):
    """Test ecs_api_operation function with DescribeContainerInstances operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_container_instances.return_value = {
        "containerInstances": [
            {
                "containerInstanceArn": "instance-1",
                "ec2InstanceId": "i-12345678",
                "status": "ACTIVE",
            }
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeContainerInstances operation
    result = await ecs_api_operation(
        api_operation="DescribeContainerInstances",
        api_params={"cluster": "test-cluster", "containerInstances": ["instance-1"]},
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_container_instances was called with correct parameters
    mock_ecs.describe_container_instances.assert_called_once_with(
        cluster="test-cluster", containerInstances=["instance-1"]
    )

    # Verify the result
    assert len(result["containerInstances"]) == 1
    assert result["containerInstances"][0]["containerInstanceArn"] == "instance-1"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_api_operation_describe_capacity_providers(mock_get_client):
    """Test ecs_api_operation function with DescribeCapacityProviders operation."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_capacity_providers.return_value = {
        "capacityProviders": [
            {
                "capacityProviderArn": (
                    "arn:aws:ecs:us-east-1:123456789012:capacity-provider/FARGATE"
                ),
                "name": "FARGATE",
                "status": "ACTIVE",
            }
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_api_operation with DescribeCapacityProviders operation
    result = await ecs_api_operation(
        api_operation="DescribeCapacityProviders", api_params={"capacityProviders": ["FARGATE"]}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_capacity_providers was called with correct parameters
    mock_ecs.describe_capacity_providers.assert_called_once_with(capacityProviders=["FARGATE"])

    # Verify the result
    assert len(result["capacityProviders"]) == 1
    assert result["capacityProviders"][0]["name"] == "FARGATE"


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
