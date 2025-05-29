"""
Test script for the image pull failure detection functionality.

This script tests the new functionality for detecting image pull failures
in ECS deployments. It can be used to verify that the enhanced troubleshooting
tools correctly identify and diagnose image pull issues.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import boto3
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    discover_resources,
    get_task_definitions,
    validate_container_images,
)


class TestImagePullFailureDetection(unittest.TestCase):
    """Test the image pull failure detection functionality."""

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.boto3.client"
    )
    async def test_discover_resources(self, mock_boto3_client):
        """Test discovering related resources."""
        # Mock the ECS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {
            "clusterArns": [
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-failure-cluster-prbqv",
                "arn:aws:ecs:us-west-2:123456789012:cluster/another-cluster",
            ]
        }

        # Mock the paginator for list_task_definitions
        mock_task_paginator = MagicMock()
        mock_task_paginator.paginate.return_value = [
            {
                "taskDefinitionArns": [
                    (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/"
                        "test-failure-task-def-prbqv:1"
                    ),
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/other-task:1",
                ]
            }
        ]

        def get_paginator_side_effect(operation_name):
            if operation_name == "list_task_definitions":
                return mock_task_paginator
            return MagicMock()

        mock_ecs.get_paginator.side_effect = get_paginator_side_effect

        # Mock describe_task_definition for the task definitions
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-failure-task-def-prbqv:1"
                ),
                "family": "test-failure-task-def-prbqv",
                "revision": 1,
            }
        }

        # Mock the ELBv2 client
        mock_elbv2 = MagicMock()
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerName": "test-failure-lb-prbqv"},
                {"LoadBalancerName": "other-lb"},
            ]
        }

        # Configure mock boto3 client to return our mocks
        def mock_client(service_name):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2
            return MagicMock()

        mock_boto3_client.side_effect = mock_client

        result, _ = await discover_resources("test-failure")

        # Verify the result
        self.assertIn("test-failure-cluster-prbqv", result["clusters"])
        self.assertIn("test-failure-task-def-prbqv:1", result["task_definitions"])
        self.assertIn("test-failure-lb-prbqv", result["load_balancers"])

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.boto3.client"
    )
    async def test_get_task_definitions(self, mock_boto3_client):
        """Test getting related task definitions."""
        # Mock the ECS client
        mock_ecs = MagicMock()

        # Mock paginator for list_task_definitions
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "taskDefinitionArns": [
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-failure-prbqv:1"
                ]
            }
        ]
        mock_ecs.get_paginator.return_value = mock_paginator

        # Mock describe_task_definition
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-failure-prbqv:1"
                ),
                "family": "test-failure-prbqv",
                "revision": 1,
                "containerDefinitions": [
                    {"name": "web", "image": "non-existent-repo/non-existent-image:latest"}
                ],
            }
        }

        # Configure mock boto3 client to return our mock
        mock_boto3_client.return_value = mock_ecs

        # Call the function
        result = await get_task_definitions("test-failure-prbqv")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["family"], "test-failure-prbqv")
        self.assertEqual(
            result[0]["containerDefinitions"][0]["image"],
            "non-existent-repo/non-existent-image:latest",
        )

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.boto3.client"
    )
    async def test_validate_container_images(self, mock_boto3_client):
        """Test validating container images."""
        # Mock the ECR client
        mock_ecr = MagicMock()

        # Configure the mock to fail for the test repo
        def mock_describe_repositories(repositoryNames):
            if repositoryNames[0] == "non-existent-image":
                error = {"Error": {"Code": "RepositoryNotFoundException"}}
                raise boto3.client("ecr").exceptions.RepositoryNotFoundException(
                    error, "DescribeRepositories"
                )
            return {"repositories": [{"repositoryName": repositoryNames[0]}]}

        mock_ecr.describe_repositories.side_effect = mock_describe_repositories

        # Configure mock boto3 client to return our mock
        mock_boto3_client.return_value = mock_ecr

        # Create test task definitions
        task_defs = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/failing-task-def-prbqv:1"
                ),
                "family": "failing-task-def-prbqv",
                "containerDefinitions": [
                    {"name": "web", "image": "non-existent-repo/non-existent-image:latest"}
                ],
            }
        ]

        # Call the function
        result = await validate_container_images(task_defs)

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["image"], "non-existent-repo/non-existent-image:latest")
        self.assertEqual(result[0]["exists"], "unknown")  # External images have unknown status
        self.assertEqual(result[0]["repository_type"], "external")

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures(self, mock_validate_images, mock_find_task_defs):
        """Test the detect_image_pull_failures function."""
        # Mock the task definitions
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/failing-task-def-prbqv:1"
                ),
                "family": "failing-task-def-prbqv",
                "containerDefinitions": [
                    {"name": "web", "image": "non-existent-repo/non-existent-image:latest"}
                ],
            }
        ]

        # Mock the image check results
        mock_validate_images.return_value = [
            {
                "image": "non-existent-repo/non-existent-image:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/failing-task-def-prbqv:1"
                ),
                "container_name": "web",
                "exists": "unknown",
                "error": "Repository not found in ECR",
                "repository_type": "external",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-failure-prbqv")

        # Verify the result
        self.assertTrue("success" in result["status"])
        self.assertTrue(len(result["image_issues"]) > 0)
        self.assertIn("container image", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)

        # Make sure it contains a specific recommendation
        found_recommendation = False
        for recommendation in result["recommendations"]:
            if "non-existent-repo/non-existent-image" in recommendation and (
                "accessible" in recommendation.lower() or "verify" in recommendation.lower()
            ):
                found_recommendation = True
                break
        self.assertTrue(
            found_recommendation, "Should recommend verifying the external image accessibility"
        )


if __name__ == "__main__":
    unittest.main()
