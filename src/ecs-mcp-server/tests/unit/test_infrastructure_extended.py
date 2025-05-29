"""
Extended unit tests for infrastructure module.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecr_infrastructure,
    create_ecs_infrastructure,
    create_infrastructure,
    prepare_template_files,
)


class TestInfrastructureExtended(unittest.TestCase):
    """Extended unit tests for infrastructure module."""

    @patch("os.makedirs")
    @patch("os.path.join")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_templates_dir")
    @patch("builtins.open", new_callable=mock_open, read_data="template content")
    def test_prepare_template_files(
        self, mock_file, mock_get_templates_dir, mock_join, mock_makedirs
    ):
        """Test preparing template files."""
        # Setup mocks
        mock_get_templates_dir.return_value = "/templates"
        mock_join.side_effect = lambda *args: "/".join(args)

        # Call the function
        result = prepare_template_files(app_name="test-app", app_path="/app")

        # Verify directories were created
        mock_makedirs.assert_called_once_with("/app/cloudformation-templates", exist_ok=True)

        # Verify template files were read and written
        self.assertEqual(mock_file.call_count, 4)  # 2 reads and 2 writes
        self.assertIn("ecr_template_path", result)
        self.assertIn("ecs_template_path", result)
        self.assertIn("ecr_template_content", result)
        self.assertIn("ecs_template_content", result)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    async def test_create_infrastructure_no_force_deploy(self, mock_prepare_templates):
        """Test creating infrastructure without force deploy."""
        # Setup mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/app/cloudformation-templates/test-app-ecr-infrastructure.json",
            "ecs_template_path": "/app/cloudformation-templates/test-app-ecs-infrastructure.json",
            "ecr_template_content": "ecr template",
            "ecs_template_content": "ecs template",
        }

        # Call the function
        result = await create_infrastructure(
            app_name="test-app", app_path="/app", force_deploy=False
        )

        # Verify the result
        self.assertEqual(result["operation"], "generate_templates")
        self.assertIn("template_paths", result)
        self.assertIn("guidance", result)
        self.assertIn("next_steps", result["guidance"])
        self.assertIn("aws_cli_commands", result["guidance"])

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
    @patch("awslabs.ecs_mcp_server.utils.docker.build_and_push_image")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure")
    async def test_create_infrastructure_with_force_deploy_success(
        self, mock_create_ecs, mock_build_push, mock_create_ecr, mock_prepare_templates
    ):
        """Test creating infrastructure with force deploy - success case."""
        # Setup mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/app/cloudformation-templates/test-app-ecr-infrastructure.json",
            "ecs_template_path": "/app/cloudformation-templates/test-app-ecs-infrastructure.json",
            "ecr_template_content": "ecr template",
            "ecs_template_content": "ecs template",
        }
        mock_create_ecr.return_value = {
            "stack_name": "test-app-ecr-infrastructure",
            "stack_id": "ecr-stack-id",
            "operation": "create",
            "resources": {
                "ecr_repository": "test-app-repo",
                "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            },
        }
        mock_build_push.return_value = "latest"
        mock_create_ecs.return_value = {
            "stack_name": "test-app-ecs-infrastructure",
            "stack_id": "ecs-stack-id",
            "operation": "create",
            "vpc_id": "vpc-12345",
            "subnet_ids": ["subnet-1", "subnet-2"],
            "resources": {
                "cluster": "test-app-cluster",
                "service": "test-app-service",
                "task_definition": "test-app-task",
                "load_balancer": "test-app-alb",
            },
        }

        # Call the function
        result = await create_infrastructure(
            app_name="test-app", app_path="/app", force_deploy=True
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecs-infrastructure")
        self.assertEqual(result["stack_id"], "ecs-stack-id")
        self.assertEqual(result["operation"], "create")
        self.assertIn("template_paths", result)
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertEqual(result["resources"]["cluster"], "test-app-cluster")
        self.assertEqual(result["resources"]["service"], "test-app-service")

        # Verify function calls
        mock_create_ecr.assert_called_once_with(
            app_name="test-app", template_content="ecr template"
        )
        mock_build_push.assert_called_once()
        mock_create_ecs.assert_called_once()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
    @patch("awslabs.ecs_mcp_server.utils.docker.build_and_push_image")
    async def test_create_infrastructure_with_docker_build_failure(
        self, mock_build_push, mock_create_ecr, mock_prepare_templates
    ):
        """Test creating infrastructure with force deploy - Docker build failure."""
        # Setup mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/app/cloudformation-templates/test-app-ecr-infrastructure.json",
            "ecs_template_path": "/app/cloudformation-templates/test-app-ecs-infrastructure.json",
            "ecr_template_content": "ecr template",
            "ecs_template_content": "ecs template",
        }
        mock_create_ecr.return_value = {
            "stack_name": "test-app-ecr-infrastructure",
            "stack_id": "ecr-stack-id",
            "operation": "create",
            "resources": {
                "ecr_repository": "test-app-repo",
                "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            },
        }
        mock_build_push.side_effect = Exception("Docker build failed")

        # Call the function
        result = await create_infrastructure(
            app_name="test-app", app_path="/app", force_deploy=True
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["operation"], "create")
        self.assertIn("template_paths", result)
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertIn("Docker image build failed", result["message"])

        # Verify function calls
        mock_create_ecr.assert_called_once_with(
            app_name="test-app", template_content="ecr template"
        )
        mock_build_push.assert_called_once()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
    @patch("awslabs.ecs_mcp_server.utils.docker.build_and_push_image")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure")
    async def test_create_infrastructure_with_ecs_failure(
        self, mock_create_ecs, mock_build_push, mock_create_ecr, mock_prepare_templates
    ):
        """Test creating infrastructure with force deploy - ECS creation failure."""
        # Setup mocks
        mock_prepare_templates.return_value = {
            "ecr_template_path": "/app/cloudformation-templates/test-app-ecr-infrastructure.json",
            "ecs_template_path": "/app/cloudformation-templates/test-app-ecs-infrastructure.json",
            "ecr_template_content": "ecr template",
            "ecs_template_content": "ecs template",
        }
        mock_create_ecr.return_value = {
            "stack_name": "test-app-ecr-infrastructure",
            "stack_id": "ecr-stack-id",
            "operation": "create",
            "resources": {
                "ecr_repository": "test-app-repo",
                "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            },
        }
        mock_build_push.return_value = "latest"
        mock_create_ecs.side_effect = Exception("ECS creation failed")

        # Call the function
        result = await create_infrastructure(
            app_name="test-app", app_path="/app", force_deploy=True
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["operation"], "create")
        self.assertIn("template_paths", result)
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertIn("ECS infrastructure creation failed", result["message"])

        # Verify function calls
        mock_create_ecr.assert_called_once_with(
            app_name="test-app", template_content="ecr template"
        )
        mock_build_push.assert_called_once()
        mock_create_ecs.assert_called_once()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    async def test_create_ecr_infrastructure_new_stack(
        self, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECR infrastructure - new stack."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.side_effect = mock_cf_client.exceptions.ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}},
            "DescribeStacks",
        )
        mock_cf_client.create_stack.return_value = {"StackId": "stack-id"}
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": (
                                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo"
                            ),
                        }
                    ]
                }
            ]
        }
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["operation"], "create")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertEqual(
            result["resources"]["ecr_repository_uri"],
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
        )

        # Verify function calls
        mock_cf_client.create_stack.assert_called_once()
        mock_cf_client.describe_stacks.assert_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    async def test_create_ecr_infrastructure_existing_stack(
        self, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECR infrastructure - existing stack."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": (
                                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo"
                            ),
                        }
                    ]
                }
            ]
        }
        mock_cf_client.update_stack.return_value = {"StackId": "stack-id"}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["operation"], "update")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertEqual(
            result["resources"]["ecr_repository_uri"],
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
        )

        # Verify function calls
        mock_cf_client.update_stack.assert_called_once()
        mock_cf_client.describe_stacks.assert_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    async def test_create_ecr_infrastructure_no_updates(
        self, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECR infrastructure - no updates needed."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": (
                                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo"
                            ),
                        }
                    ]
                }
            ]
        }
        mock_cf_client.update_stack.side_effect = mock_cf_client.exceptions.ClientError(
            {"Error": {"Code": "ValidationError", "Message": "No updates are to be performed"}},
            "UpdateStack",
        )
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecr-infrastructure")
        self.assertEqual(result["operation"], "no_update_required")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["ecr_repository"], "test-app-repo")
        self.assertEqual(
            result["resources"]["ecr_repository_uri"],
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
        )

        # Verify function calls
        mock_cf_client.update_stack.assert_called_once()
        mock_cf_client.describe_stacks.assert_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_route_tables_for_vpc")
    async def test_create_ecs_infrastructure_new_stack(
        self, mock_get_route_tables, mock_get_vpc, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECS infrastructure - new stack."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"
        mock_get_vpc.return_value = {
            "vpc_id": "vpc-12345",
            "subnet_ids": ["subnet-1", "subnet-2"],
        }
        mock_get_route_tables.return_value = ["rt-1", "rt-2"]

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.side_effect = mock_cf_client.exceptions.ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}},
            "DescribeStacks",
        )
        mock_cf_client.create_stack.return_value = {"StackId": "stack-id"}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            image_tag="latest",
            template_content="{}",
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecs-infrastructure")
        self.assertEqual(result["operation"], "create")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["cluster"], "test-app-cluster")
        self.assertEqual(result["resources"]["service"], "test-app-service")

        # Verify function calls
        mock_cf_client.create_stack.assert_called_once()
        mock_get_vpc.assert_called_once()
        mock_get_route_tables.assert_called_once_with("vpc-12345")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    async def test_create_ecs_infrastructure_existing_stack(
        self, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECS infrastructure - existing stack."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.return_value = {"Stacks": [{}]}
        mock_cf_client.update_stack.return_value = {"StackId": "stack-id"}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            image_tag="latest",
            vpc_id="vpc-12345",
            subnet_ids=["subnet-1", "subnet-2"],
            route_table_ids=["rt-1", "rt-2"],
            template_content="{}",
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecs-infrastructure")
        self.assertEqual(result["operation"], "update")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["cluster"], "test-app-cluster")
        self.assertEqual(result["resources"]["service"], "test-app-service")

        # Verify function calls
        mock_cf_client.update_stack.assert_called_once()
        mock_cf_client.describe_stacks.assert_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    async def test_create_ecs_infrastructure_no_updates(
        self, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECS infrastructure - no updates needed."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"

        mock_cf_client = MagicMock()
        mock_cf_client.describe_stacks.return_value = {"Stacks": [{}]}
        mock_cf_client.update_stack.side_effect = mock_cf_client.exceptions.ClientError(
            {"Error": {"Code": "ValidationError", "Message": "No updates are to be performed"}},
            "UpdateStack",
        )
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            image_tag="latest",
            vpc_id="vpc-12345",
            subnet_ids=["subnet-1", "subnet-2"],
            route_table_ids=["rt-1", "rt-2"],
            template_content="{}",
        )

        # Verify the result
        self.assertEqual(result["stack_name"], "test-app-ecs-infrastructure")
        self.assertEqual(result["operation"], "no_update_required")
        self.assertIn("resources", result)
        self.assertEqual(result["resources"]["cluster"], "test-app-cluster")
        self.assertEqual(result["resources"]["service"], "test-app-service")

        # Verify function calls
        mock_cf_client.update_stack.assert_called_once()
        mock_cf_client.describe_stacks.assert_called()


if __name__ == "__main__":
    unittest.main()
