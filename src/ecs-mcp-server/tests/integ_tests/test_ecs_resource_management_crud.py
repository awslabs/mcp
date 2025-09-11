"""
Integration tests for ECS Resource Management CRUD operations.

This test suite creates a test ECS cluster and performs comprehensive
CRUD operations on ECS services to validate the ecs_resource_management tool.
"""

import json
import logging
import time
from pathlib import Path

import pytest

from .mcp_inspector_framework import MCPInspectorFramework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestECSResourceManagementCRUD:
    """Test CRUD operations for ECS resources using the MCP server."""

    framework: MCPInspectorFramework
    test_cluster_name: str = "mcp-test-cluster"
    test_service_name: str = "mcp-test-service"
    test_task_definition_family: str = "mcp-test-task"

    @classmethod
    def setup_class(cls):
        """Set up the test framework and create test cluster."""
        logger.info("Setting up ECS CRUD test suite")

        # Get the server path
        server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"

        # Initialize the framework with config file approach and us-west-2
        cls.framework = MCPInspectorFramework(
            server_path=str(server_path),
            timeout=120,  # Longer timeout for CRUD operations
            use_config_file=True,
        )

        # Enable write operations for CRUD tests
        cls.framework._update_config_for_write_operations()

        logger.info("Framework initialized for CRUD operations")

    @classmethod
    def teardown_class(cls):
        """Clean up test resources."""
        logger.info("Cleaning up ECS CRUD test resources")

        try:
            # Clean up in reverse order: service -> cluster
            # Only clean up if all tests have run
            cls._cleanup_test_service()
            cls._cleanup_test_cluster()
        except Exception as e:
            logger.warning(f"Cleanup encountered issues: {e}")

    @classmethod
    def _cleanup_test_service(cls):
        """Clean up the test service."""
        try:
            # Check if service exists first
            result = cls.framework.call_tool(
                "ecs_resource_management",
                {
                    "api_operation": "DescribeServices",
                    "api_params": json.dumps(
                        {"cluster": cls.test_cluster_name, "services": [cls.test_service_name]}
                    ),
                },
            )

            if not result.success:
                logger.info("Service doesn't exist, skipping cleanup")
                return

            content = result.parsed_json.get("content", [])
            if not content:
                return

            response_text = content[0].get("text", "")
            service_response = json.loads(response_text)
            services = service_response.get("services", [])

            if not services or services[0].get("status") == "INACTIVE":
                logger.info("Service already inactive, skipping cleanup")
                return

            # First, scale service to 0
            logger.info(f"Scaling down service {cls.test_service_name}")
            cls.framework.call_tool(
                "ecs_resource_management",
                {
                    "api_operation": "UpdateService",
                    "api_params": json.dumps(
                        {
                            "cluster": cls.test_cluster_name,
                            "service": cls.test_service_name,
                            "desiredCount": 0,
                        }
                    ),
                },
            )

            # Wait for service to scale down
            time.sleep(30)

            # Delete the service
            logger.info(f"Deleting service {cls.test_service_name}")
            cls.framework.call_tool(
                "ecs_resource_management",
                {
                    "api_operation": "DeleteService",
                    "api_params": json.dumps(
                        {"cluster": cls.test_cluster_name, "service": cls.test_service_name}
                    ),
                },
            )

        except Exception as e:
            logger.warning(f"Service cleanup failed: {e}")

    @classmethod
    def _cleanup_test_cluster(cls):
        """Clean up the test cluster."""
        try:
            # Check if cluster exists first
            result = cls.framework.call_tool(
                "ecs_resource_management",
                {
                    "api_operation": "DescribeClusters",
                    "api_params": json.dumps({"clusters": [cls.test_cluster_name]}),
                },
            )

            if not result.success:
                logger.info("Cluster doesn't exist, skipping cleanup")
                return

            content = result.parsed_json.get("content", [])
            if not content:
                return

            response_text = content[0].get("text", "")
            cluster_response = json.loads(response_text)
            clusters = cluster_response.get("clusters", [])

            if not clusters or clusters[0].get("status") == "INACTIVE":
                logger.info("Cluster already inactive, skipping cleanup")
                return

            logger.info(f"Deleting cluster {cls.test_cluster_name}")
            cls.framework.call_tool(
                "ecs_resource_management",
                {
                    "api_operation": "DeleteCluster",
                    "api_params": json.dumps({"cluster": cls.test_cluster_name}),
                },
            )
        except Exception as e:
            logger.warning(f"Cluster cleanup failed: {e}")

    def test_01_create_test_cluster(self):
        """Create a test ECS cluster for CRUD operations."""
        logger.info(f"Creating test cluster: {self.test_cluster_name}")

        # First check if cluster already exists
        existing_result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "DescribeClusters",
                "api_params": json.dumps({"clusters": [self.test_cluster_name]}),
            },
        )

        if existing_result.success:
            content = existing_result.parsed_json.get("content", [])
            if content:
                response_text = content[0].get("text", "")
                cluster_response = json.loads(response_text)
                clusters = cluster_response.get("clusters", [])

                # If cluster exists and is active, skip creation
                if clusters and clusters[0].get("status") == "ACTIVE":
                    logger.info(f"Cluster {self.test_cluster_name} already exists and is active")
                    return

        # Create the cluster
        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "CreateCluster",
                "api_params": json.dumps(
                    {
                        "clusterName": self.test_cluster_name,
                        "tags": [
                            {"key": "Purpose", "value": "MCP-Testing"},
                            {"key": "CreatedBy", "value": "ECS-MCP-Server-Tests"},
                        ],
                    }
                ),
            },
        )

        # Validate cluster creation
        assert result.success, f"Failed to create cluster: {result.stderr}"
        assert result.parsed_json is not None, "No JSON response received"

        content = result.parsed_json.get("content", [])
        assert len(content) > 0, "No content returned"

        response_text = content[0].get("text", "")
        cluster_response = json.loads(response_text)

        # Validate cluster response
        assert "cluster" in cluster_response, "Response should contain cluster info"
        cluster_info = cluster_response["cluster"]
        assert cluster_info["clusterName"] == self.test_cluster_name
        assert cluster_info["status"] in ["ACTIVE", "PROVISIONING"]

        logger.info(f"✅ Successfully created cluster: {self.test_cluster_name}")

        # Wait for cluster to become active
        if cluster_info["status"] == "PROVISIONING":
            logger.info("Waiting for cluster to become active...")
            time.sleep(10)

    def test_02_verify_cluster_exists(self):
        """Verify the test cluster exists and is active."""
        logger.info(f"Verifying cluster exists: {self.test_cluster_name}")

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "DescribeClusters",
                "api_params": json.dumps({"clusters": [self.test_cluster_name]}),
            },
        )

        assert result.success, f"Failed to describe cluster: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        cluster_response = json.loads(response_text)

        clusters = cluster_response.get("clusters", [])
        assert len(clusters) == 1, f"Expected 1 cluster, got {len(clusters)}"

        cluster = clusters[0]
        assert cluster["clusterName"] == self.test_cluster_name
        assert cluster["status"] == "ACTIVE"

        logger.info(f"✅ Cluster verified as active: {self.test_cluster_name}")

    def test_03_register_task_definition(self):
        """Register a simple task definition for testing services."""
        logger.info(f"Registering task definition: {self.test_task_definition_family}")

        # Simple task definition that doesn't require external resources
        task_definition = {
            "family": self.test_task_definition_family,
            "networkMode": "bridge",  # Use bridge mode to avoid VPC requirements
            "requiresCompatibilities": [
                "EC2"
            ],  # Use EC2 instead of Fargate to avoid VPC requirements
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [
                {
                    "name": "test-container",
                    "image": "nginx:latest",
                    "memory": 512,
                    "portMappings": [
                        {
                            "containerPort": 80,
                            "hostPort": 0,  # Dynamic port mapping
                            "protocol": "tcp",
                        }
                    ],
                    "essential": True,
                }
            ],
        }

        result = self.framework.call_tool(
            "ecs_resource_management",
            {"api_operation": "RegisterTaskDefinition", "api_params": json.dumps(task_definition)},
        )

        assert result.success, f"Failed to register task definition: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        task_def_response = json.loads(response_text)

        assert "taskDefinition" in task_def_response
        task_def = task_def_response["taskDefinition"]
        assert task_def["family"] == self.test_task_definition_family
        assert task_def["status"] == "ACTIVE"

        logger.info(f"✅ Task definition registered: {task_def['taskDefinitionArn']}")

    def test_04_create_service(self):
        """Create a test ECS service (CREATE operation)."""
        logger.info(f"Creating service: {self.test_service_name}")

        # Simple service definition that works with EC2 launch type
        service_definition = {
            "cluster": self.test_cluster_name,
            "serviceName": self.test_service_name,
            "taskDefinition": self.test_task_definition_family,
            "desiredCount": 1,
            "launchType": "EC2",  # Use EC2 launch type
            "tags": [
                {"key": "Purpose", "value": "MCP-Testing"},
                {"key": "CreatedBy", "value": "ECS-MCP-Server-Tests"},
            ],
        }

        result = self.framework.call_tool(
            "ecs_resource_management",
            {"api_operation": "CreateService", "api_params": json.dumps(service_definition)},
        )

        # Note: This might fail if there are no EC2 instances in the cluster
        # That's expected and we'll handle it gracefully
        if not result.success:
            logger.warning("Service creation failed - likely no EC2 instances in cluster")
            logger.info("This is expected for a test cluster without EC2 instances")
            # Skip the rest of the service tests
            pytest.skip("No EC2 instances available for service deployment")
            return

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        assert "service" in service_response
        service = service_response["service"]
        assert service["serviceName"] == self.test_service_name
        assert service["clusterArn"].endswith(self.test_cluster_name)

        logger.info(f"✅ Service created: {service['serviceArn']}")

    def test_05_read_service(self):
        """Read the created service (READ operation)."""
        logger.info(f"Reading service: {self.test_service_name}")

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "DescribeServices",
                "api_params": json.dumps(
                    {"cluster": self.test_cluster_name, "services": [self.test_service_name]}
                ),
            },
        )

        assert result.success, f"Failed to describe service: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        services = service_response.get("services", [])
        assert len(services) == 1, f"Expected 1 service, got {len(services)}"

        service = services[0]
        assert service["serviceName"] == self.test_service_name
        assert service["status"] in ["ACTIVE", "PENDING"]
        assert service["desiredCount"] == 1

        logger.info(
            f"✅ Service read successfully: {service['status']} "
            f"with {service['runningCount']} running tasks"
        )

    def test_06_update_service(self):
        """Update the service (UPDATE operation)."""
        logger.info(f"Updating service: {self.test_service_name}")

        # Update desired count to 2
        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "UpdateService",
                "api_params": json.dumps(
                    {
                        "cluster": self.test_cluster_name,
                        "service": self.test_service_name,
                        "desiredCount": 2,
                    }
                ),
            },
        )

        assert result.success, f"Failed to update service: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        assert "service" in service_response
        service = service_response["service"]
        assert service["serviceName"] == self.test_service_name
        assert service["desiredCount"] == 2

        logger.info(f"✅ Service updated: desired count changed to {service['desiredCount']}")

    def test_07_list_services_in_cluster(self):
        """List services in the cluster to verify our service exists."""
        logger.info(f"Listing services in cluster: {self.test_cluster_name}")

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "ListServices",
                "api_params": json.dumps({"cluster": self.test_cluster_name}),
            },
        )

        assert result.success, f"Failed to list services: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        services_response = json.loads(response_text)

        service_arns = services_response.get("serviceArns", [])
        assert len(service_arns) >= 1, "Should have at least our test service"

        # Check that our service is in the list
        service_names = [arn.split("/")[-1] for arn in service_arns]
        assert self.test_service_name in service_names, (
            f"Test service not found in: {service_names}"
        )

        logger.info(f"✅ Service found in cluster listing: {len(service_arns)} total services")

    def test_08_scale_service_to_zero(self):
        """Scale service to zero before deletion (preparation for DELETE)."""
        logger.info(f"Scaling service to zero: {self.test_service_name}")

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "UpdateService",
                "api_params": json.dumps(
                    {
                        "cluster": self.test_cluster_name,
                        "service": self.test_service_name,
                        "desiredCount": 0,
                    }
                ),
            },
        )

        assert result.success, f"Failed to scale service to zero: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        service = service_response["service"]
        assert service["desiredCount"] == 0

        logger.info("✅ Service scaled to zero tasks")

        # Wait for tasks to stop
        logger.info("Waiting for tasks to stop...")
        time.sleep(30)

    def test_09_delete_service(self):
        """Delete the service (DELETE operation)."""
        logger.info(f"Deleting service: {self.test_service_name}")

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "DeleteService",
                "api_params": json.dumps(
                    {"cluster": self.test_cluster_name, "service": self.test_service_name}
                ),
            },
        )

        assert result.success, f"Failed to delete service: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        assert "service" in service_response
        service = service_response["service"]
        assert service["serviceName"] == self.test_service_name
        assert service["status"] in ["DRAINING", "INACTIVE"]

        logger.info(f"✅ Service deletion initiated: {service['status']}")

    def test_10_verify_service_deleted(self):
        """Verify the service no longer exists or is inactive."""
        logger.info(f"Verifying service deletion: {self.test_service_name}")

        # Wait a bit for deletion to process
        time.sleep(10)

        result = self.framework.call_tool(
            "ecs_resource_management",
            {
                "api_operation": "DescribeServices",
                "api_params": json.dumps(
                    {"cluster": self.test_cluster_name, "services": [self.test_service_name]}
                ),
            },
        )

        assert result.success, f"Failed to describe service: {result.stderr}"

        content = result.parsed_json.get("content", [])
        response_text = content[0].get("text", "")
        service_response = json.loads(response_text)

        services = service_response.get("services", [])
        if services:
            service = services[0]
            # Service should be INACTIVE after deletion
            assert service["status"] == "INACTIVE", f"Expected INACTIVE, got {service['status']}"
            logger.info("✅ Service confirmed as INACTIVE")
        else:
            logger.info("✅ Service no longer exists")


# Standalone test function for quick CRUD testing
def test_ecs_crud_quick():
    """Quick CRUD test for development."""
    logger.info("Running quick ECS CRUD test")

    server_path = Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"
    framework = MCPInspectorFramework(
        server_path=str(server_path), timeout=60, use_config_file=True
    )

    # Test basic cluster listing (READ operation)
    result = framework.call_tool("ecs_resource_management", {"api_operation": "ListClusters"})

    print(f"ListClusters success: {result.success}")
    if result.success and result.parsed_json:
        content = result.parsed_json.get("content", [])
        if content:
            response_text = content[0].get("text", "")
            ecs_response = json.loads(response_text)
            cluster_count = len(ecs_response.get("clusterArns", []))
            print(f"Found {cluster_count} existing clusters")

    return result


if __name__ == "__main__":
    # Run the quick test when executed directly
    test_ecs_crud_quick()
