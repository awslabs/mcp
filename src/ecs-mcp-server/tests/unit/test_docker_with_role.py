"""
Unit tests for Docker utility functions with role-based authentication.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.docker import build_and_push_image


class TestDockerWithRole(unittest.TestCase):
    """Tests for Docker utility functions with role-based auth."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
    @patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
    @patch("subprocess.run")
    async def test_build_and_push_image_with_role(
        self, mock_subprocess_run, mock_get_ecr_login_password, mock_get_aws_account_id
    ):
        """Test build_and_push_image function with a role ARN."""
        # Mock get_aws_account_id
        mock_get_aws_account_id.return_value = "123456789012"

        # Mock get_ecr_login_password
        mock_get_ecr_login_password.return_value = "rolepassword"

        # Mock subprocess.run
        mock_build_result = MagicMock()
        mock_build_result.returncode = 0
        mock_build_result.stdout = "Build successful"

        mock_push_result = MagicMock()
        mock_push_result.returncode = 0
        mock_push_result.stdout = "Push successful"

        mock_verify_result = MagicMock()
        mock_verify_result.returncode = 0
        mock_verify_result.stdout = '{"imageTag": "123456789"}'

        mock_subprocess_run.side_effect = [
            mock_build_result,  # docker login
            mock_build_result,  # docker build
            mock_push_result,  # docker push
            mock_verify_result,  # aws ecr list-images
        ]

        # Call build_and_push_image with role
        test_role_arn = "arn:aws:iam::123456789012:role/test-role"
        repository_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo"
        app_path = "/path/to/app"
        tag = "1.0.0"

        result_tag = await build_and_push_image(
            app_path=app_path, repository_uri=repository_uri, tag=tag, role_arn=test_role_arn
        )

        # Verify get_aws_account_id was called
        mock_get_aws_account_id.assert_called_once()

        # Verify get_ecr_login_password was called with the role ARN
        mock_get_ecr_login_password.assert_called_once_with(test_role_arn)

        # Verify subprocess.run calls
        self.assertEqual(mock_subprocess_run.call_count, 4)

        # Verify docker login
        login_call_args = mock_subprocess_run.call_args_list[0][1]
        self.assertEqual(login_call_args["input"], "rolepassword")

        # Verify docker build
        build_call_args = mock_subprocess_run.call_args_list[1][0][0]
        self.assertIn("docker", build_call_args)
        self.assertIn("build", build_call_args)
        self.assertIn(f"{repository_uri}:{tag}", build_call_args)
        self.assertIn(app_path, build_call_args)

        # Verify docker push
        push_call_args = mock_subprocess_run.call_args_list[2][0][0]
        self.assertIn("docker", push_call_args)
        self.assertIn("push", push_call_args)
        self.assertIn(f"{repository_uri}:{tag}", push_call_args)

        # Verify aws ecr list-images (with role-arn parameter)
        verify_call_args = mock_subprocess_run.call_args_list[3][0][0]
        self.assertIn("aws", verify_call_args)
        self.assertIn("ecr", verify_call_args)
        self.assertIn("list-images", verify_call_args)
        self.assertIn("--role-arn", verify_call_args)
        self.assertIn(test_role_arn, verify_call_args)

        # Verify the tag was returned
        self.assertEqual(result_tag, tag)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
    @patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
    @patch("subprocess.run")
    async def test_build_and_push_image_without_role(
        self, mock_subprocess_run, mock_get_ecr_login_password, mock_get_aws_account_id
    ):
        """Test build_and_push_image function without a role ARN."""
        # Mock get_aws_account_id
        mock_get_aws_account_id.return_value = "123456789012"

        # Mock get_ecr_login_password
        mock_get_ecr_login_password.return_value = "ecrpassword"

        # Mock subprocess.run
        mock_build_result = MagicMock()
        mock_build_result.returncode = 0
        mock_build_result.stdout = "Build successful"

        mock_push_result = MagicMock()
        mock_push_result.returncode = 0
        mock_push_result.stdout = "Push successful"

        mock_verify_result = MagicMock()
        mock_verify_result.returncode = 0
        mock_verify_result.stdout = '{"imageTag": "123456789"}'

        mock_subprocess_run.side_effect = [
            mock_build_result,  # docker login
            mock_build_result,  # docker build
            mock_push_result,  # docker push
            mock_verify_result,  # aws ecr list-images
        ]

        # Call build_and_push_image without role
        repository_uri = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo"
        app_path = "/path/to/app"
        tag = "1.0.0"

        result_tag = await build_and_push_image(
            app_path=app_path, repository_uri=repository_uri, tag=tag
        )

        # Verify get_aws_account_id was called
        mock_get_aws_account_id.assert_called_once()

        # Verify get_ecr_login_password was called without role ARN
        mock_get_ecr_login_password.assert_called_once_with(None)

        # Verify subprocess.run calls
        self.assertEqual(mock_subprocess_run.call_count, 4)

        # Verify docker login
        login_call_args = mock_subprocess_run.call_args_list[0][1]
        self.assertEqual(login_call_args["input"], "ecrpassword")

        # Verify aws ecr list-images (without role-arn parameter)
        verify_call_args = mock_subprocess_run.call_args_list[3][0][0]
        self.assertIn("aws", verify_call_args)
        self.assertIn("ecr", verify_call_args)
        self.assertIn("list-images", verify_call_args)
        self.assertNotIn("--role-arn", verify_call_args)

        # Verify the tag was returned
        self.assertEqual(result_tag, tag)


if __name__ == "__main__":
    unittest.main()
