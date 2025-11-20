"""
Unit tests for security analysis API functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    ClusterNotFoundError,
    collect_cluster_configuration,
    format_clusters_for_display,
    get_clusters_with_metadata,
    get_target_region,
    validate_clusters,
)


@patch.dict("os.environ", {"AWS_REGION": "eu-central-1"})
def test_get_target_region_from_env():
    """Test get_target_region when using environment variable."""
    result = get_target_region()

    assert result == "eu-central-1"


@patch.dict("os.environ", {}, clear=True)
def test_get_target_region_default():
    """Test get_target_region when no region specified and no env var."""
    result = get_target_region()

    assert result == "us-east-1"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_get_clusters_with_metadata_success(mock_ecs_api):
    """Test get_clusters_with_metadata with successful response."""
    # Mock ListClusters response
    mock_ecs_api.side_effect = [
        {
            "clusterArns": [
                "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-1",
                "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-2",
            ]
        },
        {
            "clusters": [
                {
                    "clusterName": "test-cluster-1",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-1",
                    "status": "ACTIVE",
                    "runningTasksCount": 5,
                    "pendingTasksCount": 0,
                    "activeServicesCount": 3,
                    "registeredContainerInstancesCount": 2,
                    "tags": [{"key": "Environment", "value": "Production"}],
                },
                {
                    "clusterName": "test-cluster-2",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-2",
                    "status": "ACTIVE",
                    "runningTasksCount": 2,
                    "pendingTasksCount": 1,
                    "activeServicesCount": 1,
                    "registeredContainerInstancesCount": 1,
                    "tags": [],
                },
            ]
        },
    ]

    result = await get_clusters_with_metadata("us-east-1")

    assert len(result) == 2
    assert result[0]["cluster_name"] == "test-cluster-1"
    assert result[0]["status"] == "ACTIVE"
    assert result[0]["running_tasks_count"] == 5
    assert result[0]["tags"] == {"Environment": "Production"}
    assert result[1]["cluster_name"] == "test-cluster-2"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_get_clusters_with_metadata_empty(mock_ecs_api):
    """Test get_clusters_with_metadata when no clusters exist."""
    mock_ecs_api.return_value = {"clusterArns": []}

    result = await get_clusters_with_metadata("us-east-1")

    assert result == []
    mock_ecs_api.assert_called_once()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_get_clusters_with_metadata_error(mock_ecs_api):
    """Test get_clusters_with_metadata when API call fails."""
    mock_ecs_api.side_effect = Exception("API Error")

    with pytest.raises(Exception) as exc_info:
        await get_clusters_with_metadata("us-east-1")

    assert "Failed to retrieve clusters" in str(exc_info.value)


def test_format_clusters_for_display_with_clusters():
    """Test format_clusters_for_display with multiple clusters."""
    clusters = [
        {
            "cluster_name": "prod-cluster",
            "status": "ACTIVE",
            "running_tasks_count": 10,
            "active_services_count": 5,
        },
        {
            "cluster_name": "staging-cluster",
            "status": "ACTIVE",
            "running_tasks_count": 3,
            "active_services_count": 2,
        },
    ]

    result = format_clusters_for_display(clusters, "us-east-1")

    assert "ECS CLUSTERS IN REGION: us-east-1" in result
    assert "Found 2 cluster(s)" in result
    assert "prod-cluster" in result
    assert "staging-cluster" in result
    assert "Running Tasks: 10" in result
    assert "Active Services: 5" in result


def test_format_clusters_for_display_empty():
    """Test format_clusters_for_display with no clusters."""
    result = format_clusters_for_display([], "us-west-2")

    assert "No ECS clusters found in region: us-west-2" in result
    assert "create-cluster" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_validate_clusters_success(mock_ecs_api):
    """Test validate_clusters with successful validation."""
    mock_ecs_api.return_value = {
        "clusters": [
            {
                "clusterName": "test-cluster-1",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-1",
            },
            {
                "clusterName": "test-cluster-2",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-2",
            },
        ],
        "failures": [],
    }

    result = await validate_clusters(["test-cluster-1", "test-cluster-2"], "us-east-1")

    assert len(result) == 2
    assert "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-1" in result
    assert "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-2" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_validate_clusters_not_found(mock_ecs_api):
    """Test validate_clusters when clusters are not found."""
    mock_ecs_api.return_value = {
        "clusters": [],
        "failures": [
            {"arn": "nonexistent-cluster", "reason": "MISSING"},
        ],
    }

    with pytest.raises(ClusterNotFoundError) as exc_info:
        await validate_clusters(["nonexistent-cluster"], "us-east-1")

    assert "Clusters not found" in str(exc_info.value)
    assert "nonexistent-cluster" in str(exc_info.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_validate_clusters_partial_failure(mock_ecs_api):
    """Test validate_clusters with partial failures."""
    mock_ecs_api.return_value = {
        "clusters": [
            {
                "clusterName": "test-cluster-1",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster-1",
            }
        ],
        "failures": [],
    }

    with pytest.raises(ClusterNotFoundError) as exc_info:
        await validate_clusters(["test-cluster-1", "test-cluster-2"], "us-east-1")

    assert "Clusters not found" in str(exc_info.value)
    assert "test-cluster-2" in str(exc_info.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_success(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with successful collection."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "runningTasksCount": 5,
                    "tags": [{"key": "Environment", "value": "Test"}],
                    "settings": [],
                    "configuration": {},
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response
        {
            "services": [
                {
                    "serviceName": "test-service",
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                    ),
                    "desiredCount": 2,
                    "networkConfiguration": {
                        "awsvpcConfiguration": {"securityGroups": ["sg-12345"]}
                    },
                    "tags": [],
                }
            ]
        },
        # DescribeTaskDefinition response
        {
            "taskDefinition": {
                "family": "test-task",
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                ),
                "revision": 1,
                "status": "ACTIVE",
                "networkMode": "awsvpc",
                "containerDefinitions": [
                    {
                        "name": "test-container",
                        "image": "nginx:latest",
                        "memory": 512,
                    }
                ],
            },
            "tags": [],
        },
    ]

    # Mock EC2 client for security groups
    mock_ec2_client = MagicMock()
    mock_ec2_client.describe_security_groups.return_value = {
        "SecurityGroups": [
            {
                "GroupId": "sg-12345",
                "GroupName": "test-sg",
                "Description": "Test security group",
                "VpcId": "vpc-12345",
                "IpPermissions": [],
                "IpPermissionsEgress": [],
                "Tags": [],
            }
        ]
    }
    mock_boto3.client.return_value = mock_ec2_client

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    assert result["cluster_name"] == "test-cluster"
    assert result["region"] == "us-east-1"
    assert len(result["services"]) == 1
    assert len(result["task_definitions"]) == 1
    assert len(result["security_groups"]) == 1
    assert result["services"][0]["service_name"] == "test-service"
    assert result["task_definitions"][0]["family"] == "test-task"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_cluster_configuration_cluster_not_found(mock_ecs_api):
    """Test collect_cluster_configuration when cluster is not found."""
    mock_ecs_api.return_value = {"clusters": []}

    result = await collect_cluster_configuration("us-east-1", "nonexistent-cluster")

    assert result["cluster_name"] == "nonexistent-cluster"
    assert len(result["collection_errors"]) > 0
    assert "not found" in str(result["collection_errors"])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_cluster_configuration_partial_failure(mock_ecs_api):
    """Test collect_cluster_configuration with partial failures."""
    # Mock successful cluster describe but failed services
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices fails
        Exception("Service listing failed"),
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    assert result["cluster_name"] == "test-cluster"
    assert len(result["collection_errors"]) > 0
    assert "Service listing failed" in str(result["collection_errors"])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_no_services(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with no services."""
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response - empty
        {"serviceArns": []},
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    assert result["cluster_name"] == "test-cluster"
    assert len(result["services"]) == 0
    assert len(result["task_definitions"]) == 0
    assert len(result["security_groups"]) == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_validate_clusters_api_error(mock_ecs_api):
    """Test validate_clusters with API error."""
    mock_ecs_api.side_effect = Exception("API error")

    with pytest.raises(Exception) as exc_info:
        await validate_clusters(["test-cluster"], "us-east-1")

    assert "Failed to validate clusters" in str(exc_info.value)
    assert "API error" in str(exc_info.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_security_group_error(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with security group error."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response
        {
            "services": [
                {
                    "serviceName": "test-service",
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                    ),
                    "desiredCount": 2,
                    "networkConfiguration": {
                        "awsvpcConfiguration": {"securityGroups": ["sg-12345"]}
                    },
                    "tags": [],
                }
            ]
        },
    ]

    # Mock EC2 client to raise error
    mock_ec2_client = MagicMock()
    mock_ec2_client.describe_security_groups.side_effect = Exception("Security group error")
    mock_boto3.client.return_value = mock_ec2_client

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should still return data but with errors
    assert result["cluster_name"] == "test-cluster"
    assert len(result["collection_errors"]) > 0
    assert any("Security group error" in str(e) for e in result["collection_errors"])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_cluster_configuration_service_processing_error(mock_ecs_api):
    """Test collect_cluster_configuration with service processing error."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices fails
        Exception("Service describe error"),
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should still return data but with errors
    assert result["cluster_name"] == "test-cluster"
    assert len(result["collection_errors"]) > 0
    assert any("Service describe error" in str(e) for e in result["collection_errors"])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_cluster_configuration_task_definition_error(mock_ecs_api):
    """Test collect_cluster_configuration with task definition error."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response
        {
            "services": [
                {
                    "serviceName": "test-service",
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                    ),
                    "desiredCount": 2,
                    "networkConfiguration": {},
                    "tags": [],
                }
            ]
        },
        # DescribeTaskDefinition fails
        Exception("Task definition error"),
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should still return data but with errors
    assert result["cluster_name"] == "test-cluster"
    assert len(result["collection_errors"]) > 0
    assert any("Task definition error" in str(e) for e in result["collection_errors"])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_service_config_error(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with service config building error."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response with malformed service
        {
            "services": [
                {
                    # Missing serviceName to trigger error in processing
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "ACTIVE",
                }
            ]
        },
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should handle the error gracefully
    assert result["cluster_name"] == "test-cluster"
    # May have errors depending on how the service is processed


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_with_draining_service(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with DRAINING service status."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response with DRAINING status
        {
            "services": [
                {
                    "serviceName": "test-service",
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "DRAINING",
                    "taskDefinition": (
                        "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                    ),
                    "desiredCount": 0,
                    "networkConfiguration": {},
                    "tags": [],
                }
            ]
        },
        # DescribeTaskDefinition response
        {
            "taskDefinition": {
                "family": "test-task",
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                ),
                "revision": 1,
                "status": "ACTIVE",
                "networkMode": "awsvpc",
                "containerDefinitions": [],
            },
            "tags": [],
        },
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should successfully collect even with DRAINING service
    assert result["cluster_name"] == "test-cluster"
    assert len(result["services"]) == 1
    assert result["services"][0]["status"] == "DRAINING"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_with_inactive_service(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with INACTIVE service status."""
    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response
        {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"]},
        # DescribeServices response with INACTIVE status
        {
            "services": [
                {
                    "serviceName": "test-service",
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service"
                    ),
                    "status": "INACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                    ),
                    "desiredCount": 0,
                    "networkConfiguration": {},
                    "tags": [],
                }
            ]
        },
        # DescribeTaskDefinition response
        {
            "taskDefinition": {
                "family": "test-task",
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"
                ),
                "revision": 1,
                "status": "ACTIVE",
                "networkMode": "awsvpc",
                "containerDefinitions": [],
            },
            "tags": [],
        },
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should successfully collect even with INACTIVE service
    assert result["cluster_name"] == "test-cluster"
    assert len(result["services"]) == 1
    assert result["services"][0]["status"] == "INACTIVE"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@patch("awslabs.ecs_mcp_server.api.security_analysis.boto3")
async def test_collect_cluster_configuration_batch_services(mock_boto3, mock_ecs_api):
    """Test collect_cluster_configuration with multiple service batches."""
    # Create 15 service ARNs to test batch processing (batch size is 10)
    service_arns = [
        f"arn:aws:ecs:us-east-1:123456789012:service/test-cluster/service-{i}" for i in range(15)
    ]

    # Mock ECS API responses
    mock_ecs_api.side_effect = [
        # DescribeClusters response
        {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "tags": [],
                    "settings": [],
                }
            ]
        },
        # ListServices response with 15 services
        {"serviceArns": service_arns},
        # First batch (10 services)
        {
            "services": [
                {
                    "serviceName": f"service-{i}",
                    "serviceArn": service_arns[i],
                    "status": "ACTIVE",
                    "taskDefinition": (
                        f"arn:aws:ecs:us-east-1:123456789012:task-definition/task-{i}:1"
                    ),
                    "desiredCount": 1,
                    "networkConfiguration": {},
                    "tags": [],
                }
                for i in range(10)
            ]
        },
        # Second batch (5 services)
        {
            "services": [
                {
                    "serviceName": f"service-{i}",
                    "serviceArn": service_arns[i],
                    "status": "ACTIVE",
                    "taskDefinition": (
                        f"arn:aws:ecs:us-east-1:123456789012:task-definition/task-{i}:1"
                    ),
                    "desiredCount": 1,
                    "networkConfiguration": {},
                    "tags": [],
                }
                for i in range(10, 15)
            ]
        },
    ] + [
        # DescribeTaskDefinition responses for each unique task definition
        {
            "taskDefinition": {
                "family": f"task-{i}",
                "taskDefinitionArn": (
                    f"arn:aws:ecs:us-east-1:123456789012:task-definition/task-{i}:1"
                ),
                "revision": 1,
                "status": "ACTIVE",
                "networkMode": "awsvpc",
                "containerDefinitions": [],
            },
            "tags": [],
        }
        for i in range(15)
    ]

    result = await collect_cluster_configuration("us-east-1", "test-cluster")

    # Should successfully collect all 15 services across 2 batches
    assert result["cluster_name"] == "test-cluster"
    assert len(result["services"]) == 15
    assert len(result["task_definitions"]) == 15
