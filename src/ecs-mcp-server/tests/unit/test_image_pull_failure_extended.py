"""
Extended test script for the image pull failure detection functionality.

This script provides additional tests for the detect_image_pull_failures function
to increase test coverage.
"""

import unittest
from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)


class TestImagePullFailureDetectionExtended(unittest.TestCase):
    """Extended tests for the image pull failure detection functionality."""

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_no_task_definitions(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when no task definitions are found."""
        # Mock the task definitions to return empty list
        mock_find_task_defs.return_value = []

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 0)
        self.assertIn("No task definitions found", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertIn(
            "Check if your task definition is named differently", result["recommendations"][0]
        )

        # Verify that validate_container_images was not called
        mock_validate_images.assert_not_called()

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_all_images_valid(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when all images are valid."""
        # Mock the task definitions
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/valid-task-def:1"
                ),
                "family": "valid-task-def",
                "containerDefinitions": [{"name": "web", "image": "valid-repo/valid-image:latest"}],
            }
        ]

        # Mock the image check results - all valid
        mock_validate_images.return_value = [
            {
                "image": "valid-repo/valid-image:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/valid-task-def:1"
                ),
                "container_name": "web",
                "exists": "true",
                "repository_type": "external",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 0)
        self.assertIn("All container images appear to be valid", result["assessment"])
        self.assertEqual(len(result["recommendations"]), 0)

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_ecr_image_not_found(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when an ECR image is not found."""
        # Mock the task definitions
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/ecr-task-def:1"
                ),
                "family": "ecr-task-def",
                "containerDefinitions": [
                    {
                        "name": "web",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/missing-repo:latest",
                    }
                ],
            }
        ]

        # Mock the image check results - ECR image not found
        mock_validate_images.return_value = [
            {
                "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/missing-repo:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/ecr-task-def:1"
                ),
                "container_name": "web",
                "exists": "false",
                "error": "Repository not found in ECR",
                "repository_type": "ecr",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 1)
        self.assertIn("Found 1 container image", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertIn("ECR image", result["recommendations"][0])
        self.assertIn("not found", result["recommendations"][0])

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_external_image_unknown(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when an external image has unknown status."""
        # Mock the task definitions
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/external-task-def:1"
                ),
                "family": "external-task-def",
                "containerDefinitions": [
                    {"name": "web", "image": "docker.io/unknown-repo/unknown-image:latest"}
                ],
            }
        ]

        # Mock the image check results - external image with unknown status
        mock_validate_images.return_value = [
            {
                "image": "docker.io/unknown-repo/unknown-image:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/external-task-def:1"
                ),
                "container_name": "web",
                "exists": "unknown",
                "repository_type": "external",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 1)
        self.assertIn("Found 1 container image", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertIn("External image", result["recommendations"][0])
        self.assertIn("cannot be verified", result["recommendations"][0])

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_other_image_issue(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when an image has other issues."""
        # Mock the task definitions
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/issue-task-def:1"
                ),
                "family": "issue-task-def",
                "containerDefinitions": [{"name": "web", "image": "problem-image:latest"}],
            }
        ]

        # Mock the image check results - image with other issues
        mock_validate_images.return_value = [
            {
                "image": "problem-image:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/issue-task-def:1"
                ),
                "container_name": "web",
                "exists": "false",
                "error": "Invalid image reference",
                "repository_type": "unknown",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 1)
        self.assertIn("Found 1 container image", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertIn("Image 'problem-image:latest'", result["recommendations"][0])
        self.assertIn("has issues", result["recommendations"][0])

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.validate_container_images"
    )
    async def test_detect_image_pull_failures_missing_execution_role(
        self, mock_validate_images, mock_find_task_defs
    ):
        """Test detect_image_pull_failures when task definition is missing execution role."""
        # Mock the task definitions - missing execution role
        mock_find_task_defs.return_value = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/no-role-task-def:1"
                ),
                "family": "no-role-task-def",
                # No executionRoleArn
                "containerDefinitions": [
                    {
                        "name": "web",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/valid-repo:latest",
                    }
                ],
            }
        ]

        # Mock the image check results - valid image
        mock_validate_images.return_value = [
            {
                "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/valid-repo:latest",
                "task_definition": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/no-role-task-def:1"
                ),
                "container_name": "web",
                "exists": "true",
                "repository_type": "ecr",
            }
        ]

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["image_issues"]), 0)
        self.assertIn("All container images appear to be valid", result["assessment"])
        self.assertTrue(len(result["recommendations"]) > 0)
        self.assertIn("does not have an execution role", result["recommendations"][0])
        self.assertIn("Add an executionRole", result["recommendations"][0])

    @pytest.mark.anyio
    @patch(
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures.get_task_definitions"
    )
    async def test_detect_image_pull_failures_exception(self, mock_find_task_defs):
        """Test detect_image_pull_failures when an exception occurs."""
        # Mock the task definitions to raise an exception
        mock_find_task_defs.side_effect = Exception("Test exception")

        # Call the function
        result = await detect_image_pull_failures("test-app")

        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Test exception")
        self.assertIn("Error checking for image pull failures", result["assessment"])
        self.assertEqual(len(result["image_issues"]), 0)


if __name__ == "__main__":
    unittest.main()
