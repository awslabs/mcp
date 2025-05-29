"""
Additional unit tests for ECS resource management module.

This file contains tests for container instance and capacity provider operations.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.resource_management import (
    describe_capacity_provider,
    describe_container_instance,
    ecs_resource_management,
    list_capacity_providers,
    list_container_instances,
)


class TestContainerInstanceOperations(unittest.TestCase):
    """Tests for container instance operations."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.list_container_instances")
    async def test_resource_management_list_container_instances(
        self, mock_list_container_instances
    ):
        """Test routing to list_container_instances handler."""
        # Setup mock
        mock_list_container_instances.return_value = {"container_instances": [], "count": 0}

        # Define filters
        filters = {"cluster": "test-cluster"}

        # Call the function through the main routing function
        result = await ecs_resource_management("list", "container_instance", filters=filters)

        # Verify list_container_instances was called with correct filters
        mock_list_container_instances.assert_called_once_with(filters)

        # Verify result was returned correctly
        self.assertEqual(result, {"container_instances": [], "count": 0})

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_container_instances(self, mock_get_client):
        """Test list_container_instances function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_container_instances.return_value = {
            "containerInstanceArns": [
                "arn:aws:ecs:us-east-1:123456789012:container-instance/test-cluster/instance-1"
            ]
        }
        mock_ecs.describe_container_instances.return_value = {
            "containerInstances": [
                {
                    "containerInstanceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:container-instance/test-cluster/instance-1"
                    ),
                    "ec2InstanceId": "i-12345678",
                    "status": "ACTIVE",
                }
            ]
        }
        mock_get_client.return_value = mock_ecs

        # Call list_container_instances with filters
        filters = {"cluster": "test-cluster", "status": "ACTIVE"}
        result = await list_container_instances(filters)

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify list_container_instances was called with correct parameters
        mock_ecs.list_container_instances.assert_called_once()
        args, kwargs = mock_ecs.list_container_instances.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        self.assertEqual(kwargs["status"], "ACTIVE")

        # Verify describe_container_instances was called
        mock_ecs.describe_container_instances.assert_called_once()

        # Verify the result
        self.assertIn("container_instances", result)
        self.assertEqual(len(result["container_instances"]), 1)
        self.assertEqual(result["count"], 1)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_container_instances_missing_cluster(self, mock_get_client):
        """Test list_container_instances function with missing cluster."""
        # Call list_container_instances without cluster filter
        result = await list_container_instances({})

        # Verify get_aws_client was not called
        mock_get_client.assert_not_called()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["container_instances"], [])
        self.assertEqual(result["count"], 0)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_container_instances_empty(self, mock_get_client):
        """Test list_container_instances function with empty result."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_container_instances.return_value = {"containerInstanceArns": []}
        mock_get_client.return_value = mock_ecs

        # Call list_container_instances
        result = await list_container_instances({"cluster": "test-cluster"})

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify list_container_instances was called
        mock_ecs.list_container_instances.assert_called_once()

        # Verify describe_container_instances was not called
        mock_ecs.describe_container_instances.assert_not_called()

        # Verify the result
        self.assertIn("container_instances", result)
        self.assertEqual(len(result["container_instances"]), 0)
        self.assertEqual(result["count"], 0)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_container_instances_error(self, mock_get_client):
        """Test list_container_instances function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_container_instances.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs

        # Call list_container_instances
        result = await list_container_instances({"cluster": "test-cluster"})

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify list_container_instances was called
        mock_ecs.list_container_instances.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["container_instances"], [])
        self.assertEqual(result["count"], 0)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_container_instance(self, mock_get_client):
        """Test describe_container_instance function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_container_instances.return_value = {
            "containerInstances": [
                {
                    "containerInstanceArn": (
                        "arn:aws:ecs:us-east-1:123456789012:container-instance/test-cluster/instance-1"
                    ),
                    "ec2InstanceId": "i-12345678",
                    "status": "ACTIVE",
                }
            ]
        }

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [{"InstanceId": "i-12345678", "InstanceType": "t2.micro"}]}
            ]
        }

        mock_get_client.side_effect = [mock_ecs, mock_ec2, mock_ecs]

        mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}

        # Call describe_container_instance
        result = await describe_container_instance("instance-1", {"cluster": "test-cluster"})

        # Verify get_aws_client was called multiple times
        self.assertEqual(mock_get_client.call_count, 3)

        # Verify describe_container_instances was called with correct parameters
        mock_ecs.describe_container_instances.assert_called_once()
        args, kwargs = mock_ecs.describe_container_instances.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        self.assertEqual(kwargs["containerInstances"], ["instance-1"])

        # Verify describe_instances was called
        mock_ec2.describe_instances.assert_called_once()

        # Verify list_tasks was called
        mock_ecs.list_tasks.assert_called_once()

        # Verify the result
        self.assertIn("container_instance", result)
        self.assertIn("ec2_instance", result)
        self.assertEqual(result["container_instance"]["ec2InstanceId"], "i-12345678")
        self.assertEqual(result["ec2_instance"]["InstanceType"], "t2.micro")
        self.assertEqual(result["running_task_count"], 2)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_container_instance_not_found(self, mock_get_client):
        """Test describe_container_instance function with non-existent instance."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_container_instances.return_value = {"containerInstances": []}
        mock_get_client.return_value = mock_ecs

        # Call describe_container_instance
        result = await describe_container_instance(
            "non-existent-instance", {"cluster": "test-cluster"}
        )

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_container_instances was called
        mock_ecs.describe_container_instances.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["container_instance"], None)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_container_instance_error(self, mock_get_client):
        """Test describe_container_instance function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_container_instances.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs

        # Call describe_container_instance
        result = await describe_container_instance("instance-1", {"cluster": "test-cluster"})

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_container_instances was called
        mock_ecs.describe_container_instances.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["container_instance"], None)


class TestCapacityProviderOperations(unittest.TestCase):
    """Tests for capacity provider operations."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.list_capacity_providers")
    async def test_resource_management_list_capacity_providers(self, mock_list_capacity_providers):
        """Test routing to list_capacity_providers handler."""
        # Setup mock
        mock_list_capacity_providers.return_value = {"capacity_providers": [], "count": 0}

        # Call the function through the main routing function
        result = await ecs_resource_management("list", "capacity_provider")

        # Verify list_capacity_providers was called with empty filters
        mock_list_capacity_providers.assert_called_once_with({})

        # Verify result was returned correctly
        self.assertEqual(result, {"capacity_providers": [], "count": 0})

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_capacity_providers(self, mock_get_client):
        """Test list_capacity_providers function."""
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
                },
                {
                    "capacityProviderArn": (
                        "arn:aws:ecs:us-east-1:123456789012:capacity-provider/FARGATE_SPOT"
                    ),
                    "name": "FARGATE_SPOT",
                    "status": "ACTIVE",
                },
            ],
            "nextToken": "next-token",
        }
        mock_get_client.return_value = mock_ecs

        # Call list_capacity_providers
        result = await list_capacity_providers({})

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_capacity_providers was called
        mock_ecs.describe_capacity_providers.assert_called_once()

        # Verify the result
        self.assertIn("capacity_providers", result)
        self.assertEqual(len(result["capacity_providers"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["next_token"], "next-token")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_capacity_providers_error(self, mock_get_client):
        """Test list_capacity_providers function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_capacity_providers.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs

        # Call list_capacity_providers
        result = await list_capacity_providers({})

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_capacity_providers was called
        mock_ecs.describe_capacity_providers.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["capacity_providers"], [])
        self.assertEqual(result["count"], 0)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_capacity_provider(self, mock_get_client):
        """Test describe_capacity_provider function."""
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

        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}

        mock_ecs.describe_clusters.side_effect = [
            {
                "clusters": [
                    {
                        "clusterName": "cluster-1",
                        "clusterArn": "cluster-1",
                        "capacityProviders": ["FARGATE"],
                    }
                ]
            },
            {
                "clusters": [
                    {
                        "clusterName": "cluster-2",
                        "clusterArn": "cluster-2",
                        "capacityProviders": ["FARGATE_SPOT"],
                    }
                ]
            },
        ]

        mock_get_client.return_value = mock_ecs

        # Call describe_capacity_provider
        result = await describe_capacity_provider("FARGATE")

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_capacity_providers was called with correct parameters
        mock_ecs.describe_capacity_providers.assert_called_once()
        args, kwargs = mock_ecs.describe_capacity_providers.call_args
        self.assertEqual(kwargs["capacityProviders"], ["FARGATE"])

        # Verify list_clusters was called
        mock_ecs.list_clusters.assert_called_once()

        # Verify describe_clusters was called twice
        self.assertEqual(mock_ecs.describe_clusters.call_count, 2)

        # Verify the result
        self.assertIn("capacity_provider", result)
        self.assertEqual(result["capacity_provider"]["name"], "FARGATE")
        self.assertEqual(len(result["clusters_using"]), 1)
        self.assertEqual(result["clusters_using"][0]["cluster_name"], "cluster-1")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_capacity_provider_not_found(self, mock_get_client):
        """Test describe_capacity_provider function with non-existent provider."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_capacity_providers.return_value = {"capacityProviders": []}
        mock_get_client.return_value = mock_ecs

        # Call describe_capacity_provider
        result = await describe_capacity_provider("non-existent-provider")

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_capacity_providers was called
        mock_ecs.describe_capacity_providers.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["capacity_provider"], None)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_capacity_provider_error(self, mock_get_client):
        """Test describe_capacity_provider function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_capacity_providers.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs

        # Call describe_capacity_provider
        result = await describe_capacity_provider("FARGATE")

        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")

        # Verify describe_capacity_providers was called
        mock_ecs.describe_capacity_providers.assert_called_once()

        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["capacity_provider"], None)


if __name__ == "__main__":
    unittest.main()
