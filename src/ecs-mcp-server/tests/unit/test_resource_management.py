"""
Pytest-style unit tests for resource management module.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.resource_management import (
    describe_cluster,
    describe_container_instance,
    describe_service,
    describe_task,
    describe_task_definition,
    ecs_resource_management,
    list_clusters,
    list_container_instances,
    list_services,
    list_task_definitions,
    list_tasks,
)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_list_clusters(mock_get_client):
    """Test ecs_resource_management function with list_clusters action."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
    mock_ecs.describe_clusters.return_value = {
        "clusters": [
            {"clusterName": "cluster-1", "status": "ACTIVE"},
            {"clusterName": "cluster-2", "status": "ACTIVE"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_resource_management with list_clusters action
    result = await ecs_resource_management(action="list", resource_type="cluster")

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once()

    # Verify the result
    assert len(result["clusters"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_describe_cluster(mock_get_client):
    """Test ecs_resource_management function with describe_cluster action."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.return_value = {
        "clusters": [{"clusterName": "test-cluster", "status": "ACTIVE"}]
    }
    mock_ecs.list_services.return_value = {"serviceArns": ["service-1"]}
    mock_ecs.list_tasks.side_effect = [
        {"taskArns": ["task-1"]},  # Running tasks
        {"taskArns": []},  # Stopped tasks
    ]
    mock_get_client.return_value = mock_ecs

    # Call ecs_resource_management with describe_cluster action
    result = await ecs_resource_management(
        action="describe", resource_type="cluster", identifier="test-cluster"
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct parameters
    mock_ecs.describe_clusters.assert_called_once_with(
        clusters=["test-cluster"], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
    )

    # Verify the result
    assert result["cluster"]["clusterName"] == "test-cluster"
    assert result["service_count"] == 1
    assert result["task_count"] == 1
    assert result["running_task_count"] == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_list_services(mock_get_client):
    """Test ecs_resource_management function with list_services action."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"serviceArns": ["service-1", "service-2"]}]
    mock_ecs.get_paginator.return_value = mock_paginator

    mock_ecs.describe_services.return_value = {
        "services": [
            {"serviceName": "service-1", "status": "ACTIVE"},
            {"serviceName": "service-2", "status": "ACTIVE"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call ecs_resource_management with list_services action
    result = await ecs_resource_management(
        action="list", resource_type="service", filters={"cluster": "test-cluster"}
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify get_paginator was called
    mock_ecs.get_paginator.assert_called_once_with("list_services")

    # Verify paginator.paginate was called with correct cluster
    mock_paginator.paginate.assert_called_once_with(cluster="test-cluster")

    # Verify describe_services was called with correct parameters
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-cluster", services=["service-1", "service-2"], include=["TAGS"]
    )

    # Verify the result
    assert len(result["services"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_describe_service(mock_get_client):
    """Test ecs_resource_management function with describe_service action."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [{"serviceName": "test-service", "status": "ACTIVE", "events": []}]
    }
    mock_ecs.list_tasks.side_effect = [
        {"taskArns": ["task-1"]},  # Running tasks
        {"taskArns": []},  # Stopped tasks
    ]
    mock_get_client.return_value = mock_ecs

    # Call ecs_resource_management with describe_service action
    result = await ecs_resource_management(
        action="describe",
        resource_type="service",
        identifier="test-service",
        filters={"cluster": "test-cluster"},
    )

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_services was called with correct parameters
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-cluster", services=["test-service"], include=["TAGS"]
    )

    # Verify the result
    assert result["service"]["serviceName"] == "test-service"
    assert result["running_task_count"] == 1
    assert result["stopped_task_count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_describe_service_missing_cluster(mock_get_client):
    """Test ecs_resource_management function with describe_service action and missing cluster."""
    # Call ecs_resource_management with describe_service action and no cluster
    with pytest.raises(ValueError) as excinfo:
        await ecs_resource_management(
            action="describe", resource_type="service", identifier="test-service"
        )

    # Verify the error message
    assert "Cluster filter is required" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_invalid_action(mock_get_client):
    """Test ecs_resource_management function with invalid action."""
    # Call ecs_resource_management with invalid action
    with pytest.raises(ValueError) as excinfo:
        await ecs_resource_management(action="invalid", resource_type="cluster")

    # Verify the error message
    assert "Unsupported action" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_invalid_resource_type(mock_get_client):
    """Test ecs_resource_management function with invalid resource type."""
    # Call ecs_resource_management with invalid resource type
    with pytest.raises(ValueError) as excinfo:
        await ecs_resource_management(action="list", resource_type="invalid")

    # Verify the error message
    assert "Unsupported resource type" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_ecs_resource_management_describe_missing_identifier(mock_get_client):
    """Test ecs_resource_management function with describe action and missing identifier."""
    # Call ecs_resource_management with describe action and no identifier
    with pytest.raises(ValueError) as excinfo:
        await ecs_resource_management(action="describe", resource_type="cluster")

    # Verify the error message
    assert "Identifier is required" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_clusters(mock_get_client):
    """Test list_clusters function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
    mock_ecs.describe_clusters.return_value = {
        "clusters": [
            {"clusterName": "cluster-1", "status": "ACTIVE"},
            {"clusterName": "cluster-2", "status": "ACTIVE"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call list_clusters
    result = await list_clusters({})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once()

    # Verify the result
    assert len(result["clusters"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_clusters_empty(mock_get_client):
    """Test list_clusters function with empty response."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": []}
    mock_get_client.return_value = mock_ecs

    # Call list_clusters
    result = await list_clusters({})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once()

    # Verify the result
    assert result["clusters"] == []
    assert result["count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_clusters_error(mock_get_client):
    """Test list_clusters function with error."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.side_effect = Exception("Test error")
    mock_get_client.return_value = mock_ecs

    # Call list_clusters
    result = await list_clusters({})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once()

    # Verify the result
    assert "error" in result
    assert result["clusters"] == []
    assert result["count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_cluster(mock_get_client):
    """Test describe_cluster function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.return_value = {
        "clusters": [{"clusterName": "test-cluster", "status": "ACTIVE"}]
    }
    mock_ecs.list_services.return_value = {"serviceArns": ["service-1"]}
    mock_ecs.list_tasks.side_effect = [
        {"taskArns": ["task-1"]},  # Running tasks
        {"taskArns": []},  # Stopped tasks
    ]
    mock_get_client.return_value = mock_ecs

    # Call describe_cluster
    result = await describe_cluster("test-cluster", {})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct cluster
    mock_ecs.describe_clusters.assert_called_once_with(
        clusters=["test-cluster"], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
    )

    # Verify the result
    assert result["cluster"]["clusterName"] == "test-cluster"
    assert result["service_count"] == 1
    assert result["task_count"] == 1
    assert result["running_task_count"] == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_cluster_not_found(mock_get_client):
    """Test describe_cluster function with cluster not found."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.return_value = {
        "clusters": [],
        "failures": [{"arn": "test-cluster", "reason": "MISSING"}],
    }
    mock_get_client.return_value = mock_ecs

    # Call describe_cluster
    result = await describe_cluster("test-cluster", {})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct cluster
    mock_ecs.describe_clusters.assert_called_once_with(
        clusters=["test-cluster"], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
    )

    # Verify the result
    assert "error" in result
    assert result["cluster"] is None


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_cluster_error(mock_get_client):
    """Test describe_cluster function with error."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_clusters.side_effect = Exception("Test error")
    mock_get_client.return_value = mock_ecs

    # Call describe_cluster
    result = await describe_cluster("test-cluster", {})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_clusters was called with correct cluster
    mock_ecs.describe_clusters.assert_called_once_with(
        clusters=["test-cluster"], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
    )

    # Verify the result
    assert "error" in result
    assert result["cluster"] is None


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_services_specific_cluster(mock_get_client):
    """Test list_services function with specific cluster."""
    # Mock get_aws_client
    mock_ecs = MagicMock()

    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"serviceArns": ["service-1", "service-2"]}]
    mock_ecs.get_paginator.return_value = mock_paginator

    mock_ecs.describe_services.return_value = {
        "services": [
            {"serviceName": "service-1", "serviceArn": "service-1"},
            {"serviceName": "service-2", "serviceArn": "service-2"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call list_services with cluster filter
    result = await list_services({"cluster": "test-cluster"})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify get_paginator was called
    mock_ecs.get_paginator.assert_called_once_with("list_services")

    # Verify paginator.paginate was called with correct cluster
    mock_paginator.paginate.assert_called_once_with(cluster="test-cluster")

    # Verify describe_services was called with correct parameters
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-cluster", services=["service-1", "service-2"], include=["TAGS"]
    )

    # Verify the result
    assert len(result["services"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_services_all_clusters(mock_get_client):
    """Test list_services function for all clusters."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}

    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.side_effect = [
        [{"serviceArns": ["service-1"]}],
        [{"serviceArns": ["service-2"]}],
    ]
    mock_ecs.get_paginator.return_value = mock_paginator

    mock_ecs.describe_services.side_effect = [
        {"services": [{"serviceName": "service-1", "serviceArn": "service-1"}]},
        {"services": [{"serviceName": "service-2", "serviceArn": "service-2"}]},
    ]
    mock_get_client.return_value = mock_ecs

    # Call list_services without cluster filter
    result = await list_services({})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_clusters was called
    mock_ecs.list_clusters.assert_called_once()

    # Verify get_paginator was called for each cluster
    assert mock_ecs.get_paginator.call_count == 2

    # Verify paginator.paginate was called for each cluster
    assert mock_paginator.paginate.call_count == 2
    mock_paginator.paginate.assert_any_call(cluster="cluster-1")
    mock_paginator.paginate.assert_any_call(cluster="cluster-2")

    # Verify describe_services was called for each cluster
    assert mock_ecs.describe_services.call_count == 2
    mock_ecs.describe_services.assert_any_call(
        cluster="cluster-1", services=["service-1"], include=["TAGS"]
    )
    mock_ecs.describe_services.assert_any_call(
        cluster="cluster-2", services=["service-2"], include=["TAGS"]
    )

    # Verify the result
    assert len(result["services"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_services_error(mock_get_client):
    """Test list_services function with error."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.get_paginator.side_effect = Exception("Test error")
    mock_get_client.return_value = mock_ecs

    # Call list_services with cluster filter
    result = await list_services({"cluster": "test-cluster"})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify get_paginator was called
    mock_ecs.get_paginator.assert_called_once_with("list_services")

    # Verify the result
    assert "error" in result
    assert result["services"] == []
    assert result["count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_service(mock_get_client):
    """Test describe_service function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        "services": [{"serviceName": "test-service", "status": "ACTIVE", "events": []}]
    }
    mock_ecs.list_tasks.side_effect = [
        {"taskArns": ["task-1"]},  # Running tasks
        {"taskArns": []},  # Stopped tasks
    ]
    mock_get_client.return_value = mock_ecs

    # Call describe_service
    result = await describe_service("test-service", {"cluster": "test-cluster"})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_services was called with correct parameters
    mock_ecs.describe_services.assert_called_once_with(
        cluster="test-cluster", services=["test-service"], include=["TAGS"]
    )

    # Verify the result
    assert result["service"]["serviceName"] == "test-service"
    assert result["running_task_count"] == 1
    assert result["stopped_task_count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_tasks_with_filters(mock_get_client):
    """Test list_tasks function with filters."""
    # Mock get_aws_client
    mock_ecs = MagicMock()

    # Mock paginator
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"taskArns": ["task-1", "task-2"]}]
    mock_ecs.get_paginator.return_value = mock_paginator

    mock_ecs.describe_tasks.return_value = {
        "tasks": [
            {"taskArn": "task-1", "lastStatus": "RUNNING"},
            {"taskArn": "task-2", "lastStatus": "RUNNING"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call list_tasks with filters
    filters = {"cluster": "test-cluster", "service": "test-service", "status": "RUNNING"}
    result = await list_tasks(filters)

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify get_paginator was called
    mock_ecs.get_paginator.assert_called_once_with("list_tasks")

    # Verify paginator.paginate was called with correct parameters
    mock_paginator.paginate.assert_called_once_with(
        cluster="test-cluster", serviceName="test-service", desiredStatus="RUNNING"
    )

    # Verify describe_tasks was called with correct parameters
    mock_ecs.describe_tasks.assert_called_once_with(
        cluster="test-cluster", tasks=["task-1", "task-2"], include=["TAGS"]
    )

    # Verify the result
    assert len(result["tasks"]) == 2
    assert result["count"] == 2
    assert result["running_count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_task(mock_get_client):
    """Test describe_task function."""
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
    mock_ecs.describe_task_definition.return_value = {
        "taskDefinition": {"family": "task-family", "revision": 1}
    }
    mock_get_client.return_value = mock_ecs

    # Call describe_task
    result = await describe_task("task-1", {"cluster": "test-cluster"})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_tasks was called with correct parameters
    mock_ecs.describe_tasks.assert_called_once_with(
        cluster="test-cluster", tasks=["task-1"], include=["TAGS"]
    )

    # Verify the result
    assert result["task"]["taskArn"] == "task-1"
    assert result["task_definition"]["family"] == "task-family"
    assert len(result["container_statuses"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_task_definitions_with_filters(mock_get_client):
    """Test list_task_definitions function with filters."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_task_definitions.return_value = {"taskDefinitionArns": ["taskdef-1", "taskdef-2"]}
    mock_get_client.return_value = mock_ecs

    # Call list_task_definitions with filters
    filters = {"family": "test-family", "status": "ACTIVE"}
    result = await list_task_definitions(filters)

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_task_definitions was called with correct parameters
    mock_ecs.list_task_definitions.assert_called_once_with(
        familyPrefix="test-family", status="ACTIVE"
    )

    # Verify the result
    assert result["task_definition_arns"] == ["taskdef-1", "taskdef-2"]
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_task_definition(mock_get_client):
    """Test describe_task_definition function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_task_definition.return_value = {
        "taskDefinition": {
            "family": "test-family",
            "revision": 1,
            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-family:1",
        }
    }
    mock_ecs.list_task_definitions.return_value = {
        "taskDefinitionArns": ["arn:aws:ecs:us-west-2:123456789012:task-definition/test-family:1"]
    }
    mock_get_client.return_value = mock_ecs

    # Call describe_task_definition
    result = await describe_task_definition("test-family:1")

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify describe_task_definition was called with correct parameters
    mock_ecs.describe_task_definition.assert_called_once_with(taskDefinition="test-family:1")

    # Verify the result
    assert result["task_definition"]["family"] == "test-family"
    assert result["task_definition"]["revision"] == 1
    assert result["is_latest"] is True


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_container_instances(mock_get_client):
    """Test list_container_instances function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.list_container_instances.return_value = {
        "containerInstanceArns": ["instance-1", "instance-2"]
    }
    mock_ecs.describe_container_instances.return_value = {
        "containerInstances": [
            {"containerInstanceArn": "instance-1", "status": "ACTIVE"},
            {"containerInstanceArn": "instance-2", "status": "ACTIVE"},
        ]
    }
    mock_get_client.return_value = mock_ecs

    # Call list_container_instances
    result = await list_container_instances({"cluster": "test-cluster"})

    # Verify get_aws_client was called
    mock_get_client.assert_called_once_with("ecs")

    # Verify list_container_instances was called with correct parameters
    mock_ecs.list_container_instances.assert_called_once_with(cluster="test-cluster")

    # Verify the result
    assert len(result["container_instances"]) == 2
    assert result["count"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_list_container_instances_missing_cluster(mock_get_client):
    """Test list_container_instances function with missing cluster."""
    # Call list_container_instances without cluster
    result = await list_container_instances({})

    # Verify the result
    assert "error" in result
    assert "Cluster is required" in result["error"]
    assert result["container_instances"] == []
    assert result["count"] == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
async def test_describe_container_instance(mock_get_client):
    """Test describe_container_instance function."""
    # Mock get_aws_client
    mock_ecs = MagicMock()
    mock_ecs.describe_container_instances.return_value = {
        "containerInstances": [
            {"containerInstanceArn": "instance-1", "status": "ACTIVE", "ec2InstanceId": "i-12345"}
        ]
    }
    mock_ecs.list_tasks.return_value = {"taskArns": ["task-1"]}

    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_ec2.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"InstanceId": "i-12345", "InstanceType": "t2.micro"}]}]
    }

    # Return different clients based on service name
    def get_client_side_effect(service_name):
        if service_name == "ecs":
            return mock_ecs
        elif service_name == "ec2":
            return mock_ec2
        return MagicMock()

    mock_get_client.side_effect = get_client_side_effect

    # Call describe_container_instance
    result = await describe_container_instance("instance-1", {"cluster": "test-cluster"})

    # Verify get_aws_client was called
    assert mock_get_client.call_count == 2
    mock_get_client.assert_any_call("ecs")
    mock_get_client.assert_any_call("ec2")

    # Verify describe_container_instances was called with correct parameters
    mock_ecs.describe_container_instances.assert_called_once_with(
        cluster="test-cluster", containerInstances=["instance-1"]
    )

    # Verify the result
    assert result["container_instance"]["containerInstanceArn"] == "instance-1"
    assert result["container_instance"]["status"] == "ACTIVE"
    assert result["ec2_instance"]["InstanceId"] == "i-12345"
    assert result["running_task_count"] == 1
