"""
Extended unit tests for delete infrastructure functionality.

This file contains additional tests for the delete_infrastructure function in the ECS MCP Server
to improve code coverage.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.delete import delete_infrastructure


class TestDeleteInfrastructureExtended(unittest.TestCase):
    """Extended tests for the delete_infrastructure function."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open")
    async def test_delete_infrastructure_file_read_error(self, mock_file, mock_get_aws_client):
        """Test error handling when template file cannot be read."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
        mock_get_aws_client.return_value = mock_cf_client

        # Mock file open to raise an exception
        mock_file.side_effect = IOError("File not found")

        # Call the function
        result = await delete_infrastructure(
            app_name="test-app",
            ecr_template_path="/path/to/ecr-template.json",
            ecs_template_path="/path/to/ecs-template.json",
        )

        # Verify the result
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["ecr_stack"]["status"], "not_found")
        self.assertIn("Error comparing templates", result["ecr_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_get_template_error(self, mock_file, mock_get_aws_client):
        """Test error handling when get_template API call fails."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            ]
        }
        mock_cf_client.get_template.side_effect = ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}}, "GetTemplate"
        )
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
        self.assertIn("Error comparing templates", result["ecr_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.get_template.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_dict_template_body(self, mock_file, mock_get_aws_client):
        """Test template comparison when template body is a dict."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            ]
        }
        mock_cf_client.get_template.return_value = {
            "TemplateBody": {"test": "template"}  # Dict instead of string
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
        self.assertEqual(result["ecr_stack"]["status"], "deleting")

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    async def test_delete_infrastructure_invalid_json_template(
        self, mock_file, mock_get_aws_client
    ):
        """Test template comparison when provided template is not valid JSON."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": {"test": "template"}}  # Dict
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
        self.assertIn("does not match", result["ecr_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_not_called()

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_only_ecr_stack(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when only ECR stack exists."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
                # No ECS stack
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
        self.assertEqual(result["ecs_stack"]["status"], "not_found")

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_only_ecs_stack(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when only ECS stack exists."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                # No ECR stack
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"}
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
        self.assertEqual(result["ecr_stack"]["status"], "not_found")
        self.assertEqual(result["ecs_stack"]["status"], "deleting")

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecs-infrastructure")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_mixed_template_match(self, mock_file, mock_get_aws_client):
        """Test deleting infrastructure when one template matches and one doesn't."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "test-app-ecs-infrastructure", "StackStatus": "CREATE_COMPLETE"},
            ]
        }

        # Mock get_template to return different responses for different stacks
        def mock_get_template_side_effect(StackName, **kwargs):
            if StackName == "test-app-ecr-infrastructure":
                return {"TemplateBody": '{"test": "template"}'}  # Match
            else:
                return {"TemplateBody": '{"test": "different"}'}  # No match

        mock_cf_client.get_template.side_effect = mock_get_template_side_effect
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
        self.assertEqual(result["ecs_stack"]["status"], "not_found")
        self.assertIn("does not match", result["ecs_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        self.assertEqual(mock_cf_client.get_template.call_count, 2)
        mock_cf_client.delete_stack.assert_called_once_with(StackName="test-app-ecr-infrastructure")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.delete.get_aws_client")
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "template"}')
    async def test_delete_infrastructure_delete_stack_client_error(
        self, mock_file, mock_get_aws_client
    ):
        """Test error handling when delete_stack API call fails with ClientError."""
        # Mock CloudFormation client
        mock_cf_client = MagicMock()
        mock_cf_client.list_stacks.return_value = {
            "StackSummaries": [
                {"StackName": "test-app-ecr-infrastructure", "StackStatus": "CREATE_COMPLETE"}
            ]
        }
        mock_cf_client.get_template.return_value = {"TemplateBody": '{"test": "template"}'}
        mock_cf_client.delete_stack.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "User not authorized to perform cloudformation:DeleteStack",
                }
            },
            "DeleteStack",
        )
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
        self.assertIn("AccessDenied", result["ecr_stack"]["message"])

        # Verify CloudFormation client was called correctly
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cf_client.list_stacks.assert_called_once()
        mock_cf_client.delete_stack.assert_called_once()


if __name__ == "__main__":
    unittest.main()
