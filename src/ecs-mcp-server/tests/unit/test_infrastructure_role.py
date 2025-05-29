"""
Unit tests for infrastructure module with ECR role.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecr_infrastructure,
    create_infrastructure,
)


class TestInfrastructureWithRole(unittest.TestCase):
    """Tests for infrastructure module with ECR role support."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    async def test_create_ecr_infrastructure_role_output(self, mock_get_client):
        """Test create_ecr_infrastructure returns the role ARN."""
        # Mock get_aws_client
        mock_cloudformation = MagicMock()
        mock_cloudformation.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": (
                                "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-app-repo"
                            ),
                        },
                        {
                            "OutputKey": "ECRPushPullRoleArn",
                            "OutputValue": (
                                "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
                            ),
                        },
                    ]
                }
            ]
        }
        mock_get_client.return_value = mock_cloudformation

        # Call create_ecr_infrastructure
        result = await create_ecr_infrastructure("test-app", '{"template":"content"}')

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_with("cloudformation")

        # Verify describe_stacks was called
        mock_cloudformation.describe_stacks.assert_called()

        # Verify the resources were returned
        self.assertIn("resources", result)
        self.assertIn("ecr_repository", result["resources"])
        self.assertIn("ecr_repository_uri", result["resources"])
        self.assertIn("ecr_push_pull_role_arn", result["resources"])
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertEqual(
            result["resources"]["ecr_repository_uri"],
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-app-repo",
        )
        self.assertEqual(
            result["resources"]["ecr_push_pull_role_arn"],
            "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        )

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.validate_cloudformation_template")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.build_and_push_image")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure")
    async def test_create_infrastructure_uses_role(
        self,
        mock_create_ecs,
        mock_build_push,
        mock_create_ecr,
        mock_prepare_templates,
        mock_validate,
    ):
        """Test create_infrastructure uses the ECR role ARN for Docker images."""
        # Set up mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/path/to/ecr-template.json",
            "ecs_template_path": "/path/to/ecs-template.json",
            "ecr_template_content": '{"template":"ecr content"}',
            "ecs_template_content": '{"template":"ecs content"}',
        }

        mock_create_ecr.return_value = {
            "stack_name": "test-app-ecr-infrastructure",
            "operation": "create",
            "resources": {
                "ecr_repository": "test-app-repo",
                "ecr_repository_uri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-app-repo",
                "ecr_push_pull_role_arn": (
                    "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
                ),
            },
        }

        mock_build_push.return_value = "1.0.0"

        mock_create_ecs.return_value = {
            "stack_name": "test-app-ecs-infrastructure",
            "operation": "create",
            "vpc_id": "vpc-12345",
            "resources": {
                "cluster": "test-app-cluster",
                "service": "test-app-service",
            },
        }

        # Call create_infrastructure
        result = await create_infrastructure(
            app_name="test-app", app_path="/path/to/app", force_deploy=True
        )

        # Verify prepare_template_files was called
        mock_prepare_templates.assert_called_once_with("test-app", "/path/to/app")

        # Verify create_ecr_infrastructure was called
        mock_create_ecr.assert_called_once_with(
            app_name="test-app",
            template_content='{"template":"ecr content"}',
        )

        # Verify build_and_push_image was called with the role ARN
        mock_build_push.assert_called_once()
        args, kwargs = mock_build_push.call_args
        self.assertEqual(kwargs["app_path"], "/path/to/app")
        self.assertEqual(
            kwargs["repository_uri"], "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-app-repo"
        )
        self.assertEqual(
            kwargs["role_arn"], "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
        )

        # Verify create_ecs_infrastructure was called
        mock_create_ecs.assert_called_once()

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecs-infrastructure")
        self.assertEqual(result["step"], 3)  # Step 3 is the final step
        self.assertIn("resources", result)
        self.assertIn("ecr_repository", result["resources"])
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.validate_cloudformation_template")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
    async def test_create_infrastructure_step_1_with_role(
        self,
        mock_create_ecr,
        mock_prepare_templates,
        mock_validate,
    ):
        """Test create_infrastructure with step 1 uses the ECR role ARN."""
        # Set up mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/path/to/ecr-template.json",
            "ecs_template_path": "/path/to/ecs-template.json",
            "ecr_template_content": '{"template":"ecr content"}',
            "ecs_template_content": '{"template":"ecs content"}',
        }

        mock_create_ecr.return_value = {
            "stack_name": "test-app-ecr-infrastructure",
            "operation": "create",
            "resources": {
                "ecr_repository": "test-app-repo",
                "ecr_repository_uri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-app-repo",
                "ecr_push_pull_role_arn": (
                    "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
                ),
            },
        }

        # Call create_infrastructure with step 1
        result = await create_infrastructure(
            app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=1
        )

        # Verify prepare_template_files was called
        mock_prepare_templates.assert_called_once_with("test-app", "/path/to/app")

        # Verify create_ecr_infrastructure was called
        mock_create_ecr.assert_called_once_with(
            app_name="test-app",
            template_content='{"template":"ecr content"}',
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["step"], 1)
        self.assertEqual(result["next_step"], 2)
        self.assertIn("resources", result)
        self.assertIn("ecr_repository", result["resources"])
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertIn("ecr_push_pull_role_arn", result["resources"])
        self.assertEqual(
            result["resources"]["ecr_push_pull_role_arn"],
            "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        )


if __name__ == "__main__":
    unittest.main()
