"""
Unit tests for delete infrastructure functionality.

This file contains tests for the delete_infrastructure function in the ECS MCP Server.
It tests various scenarios for deleting ECS and ECR infrastructure.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from awslabs.ecs_mcp_server.api.delete import delete_infrastructure


class TestDeleteInfrastructure(unittest.TestCase):
    """Tests for the delete_infrastructure function."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    async def test_delete_infrastructure_no_stacks(self, mock_get_aws_client):
        """Test deleting infrastructure when no stacks exist."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {"StackSummaries": []}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "not_found")
        self.assertEqual(result["ecs_stack"]["status"], "not_found")

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_with_stacks(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when stacks exist and templates match."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "deleting")
        self.assertEqual(result["ecs_stack"]["status"], "deleting")

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        self.assertEqual(mock_cf_client.delete_stack.call_count, 2)
        mock_cf_client.delete_stack.assert_any_call(StackName="test-app-ecs-infrastructure")
        mock_cf_client.delete_stack.assert_any_call(StackName="test-app-ecr-infrastructure")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_template_mismatch(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when templates don't match."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }
        mock_cf_client.get_template.return_value = {
            "TemplateBody": '{"test": "different-template"}'
        }
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "not_found")
        self.assertEqual(result["ecs_stack"]["status"], "not_found")
        self.assertIn("does not match", result["ecr_stack"]["message"])
        self.assertIn("does not match", result["ecs_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_stack_in_progress(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when stacks are in progress."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_IN_PROGRESS"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "UPDATE_IN_PROGRESS"},
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "skipped")
        self.assertEqual(result["ecs_stack"]["status"], "skipped")
        self.assertIn("CREATE_IN_PROGRESS", result["ecr_stack"]["message"])
        self.assertIn("UPDATE_IN_PROGRESS", result["ecs_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    async def test_delete_infrastructure_list_stacks_error(self, mock_get_aws_client):
        """Test error handling when listing stacks fails."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.side_effect = Exception("API Error")
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["status"], "error")
        self.assertIn("Error listing CloudFormation stacks", result["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_delete_error(self, mock_file, mock_get_aws_client):
        """Test error handling when deleting stacks fails."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
        mock_cf_client.delete_stack.side_effect = Exception("Delete failed")
        mock_get_aws_client.return_value = mock_cf_client

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "error")
        self.assertEqual(result["ecs_stack"]["status"], "error")
        self.assertIn("Error deleting stack", result["ecr_stack"]["message"])
        self.assertIn("Error deleting stack", result["ecs_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        self.assertEqual(mock_cf_client.delete_stack.call_count, 2)
