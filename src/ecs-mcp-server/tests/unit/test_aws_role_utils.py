"""
Unit tests for AWS role utility functions.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.aws import (
    assume_ecr_role,
    get_aws_client_with_role,
    get_ecr_login_password,
)


class TestAWSRoleUtils(unittest.TestCase):
    """Tests for AWS role-based utility functions."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    async def test_assume_ecr_role(self, mock_get_client):
        """Test assume_ecr_role function."""
        # Mock get_aws_client and STS client
        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }
        mock_get_client.return_value = mock_sts

        # Call assume_ecr_role
        test_role_arn = "arn:aws:iam::123456789012:role/test-role"
        credentials = await assume_ecr_role(test_role_arn)

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("sts")

        # Verify assume_role was called with the correct parameters
        mock_sts.assume_role.assert_called_once()
        args, kwargs = mock_sts.assume_role.call_args
        self.assertEqual(kwargs["RoleArn"], test_role_arn)
        self.assertEqual(kwargs["RoleSessionName"], "ECSMCPServerECRSession")

        # Verify the credentials were returned
        self.assertEqual(credentials["aws_access_key_id"], "test-access-key")
        self.assertEqual(credentials["aws_secret_access_key"], "test-secret-key")
        self.assertEqual(credentials["aws_session_token"], "test-session-token")

    @pytest.mark.anyio
    @patch("boto3.client")
    @patch("awslabs.ecs_mcp_server.utils.aws.assume_ecr_role")
    async def test_get_aws_client_with_role(self, mock_assume_role, mock_boto_client):
        """Test get_aws_client_with_role function."""
        # Mock assume_ecr_role
        mock_assume_role.return_value = {
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "aws_session_token": "test-session-token",
        }

        # Mock boto3.client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Call get_aws_client_with_role
        test_role_arn = "arn:aws:iam::123456789012:role/test-role"
        client = await get_aws_client_with_role("ecr", test_role_arn)

        # Verify assume_ecr_role was called with the correct parameters
        mock_assume_role.assert_called_once_with(test_role_arn)

        # Verify boto3.client was called with the correct parameters
        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], "ecr")
        self.assertIn("aws_access_key_id", kwargs)
        self.assertEqual(kwargs["aws_access_key_id"], "test-access-key")
        self.assertIn("aws_secret_access_key", kwargs)
        self.assertEqual(kwargs["aws_secret_access_key"], "test-secret-key")
        self.assertIn("aws_session_token", kwargs)
        self.assertEqual(kwargs["aws_session_token"], "test-session-token")

        # Verify the client was returned
        self.assertEqual(client, mock_client)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client_with_role")
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    @patch("base64.b64decode")
    async def test_get_ecr_login_password_with_role(
        self, mock_b64decode, mock_get_client, mock_get_client_with_role
    ):
        """Test get_ecr_login_password function with a role."""
        # Mock get_aws_client_with_role
        mock_ecr_with_role = MagicMock()
        mock_ecr_with_role.get_authorization_token.return_value = {
            "authorizationData": [{"authorizationToken": "QVdTOnJvbGVwYXNzd29yZA=="}]
        }
        mock_get_client_with_role.return_value = mock_ecr_with_role

        # Mock base64.b64decode
        mock_b64decode.return_value = b"AWS:rolepassword"

        # Call get_ecr_login_password with role
        test_role_arn = "arn:aws:iam::123456789012:role/test-role"
        password = await get_ecr_login_password(test_role_arn)

        # Verify get_aws_client_with_role was called with the correct parameters
        mock_get_client_with_role.assert_called_once_with("ecr", test_role_arn)

        # Verify get_aws_client was not called
        mock_get_client.assert_not_called()

        # Verify get_authorization_token was called
        mock_ecr_with_role.get_authorization_token.assert_called_once()

        # Verify base64.b64decode was called with the correct parameters
        mock_b64decode.assert_called_once_with("QVdTOnJvbGVwYXNzd29yZA==")

        # Verify the password was returned
        self.assertEqual(password, "rolepassword")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client_with_role")
    @patch("base64.b64decode")
    async def test_get_ecr_login_password_without_role(
        self, mock_b64decode, mock_get_client_with_role, mock_get_client
    ):
        """Test get_ecr_login_password function without a role."""
        # Mock get_aws_client
        mock_ecr = MagicMock()
        mock_ecr.get_authorization_token.return_value = {
            "authorizationData": [{"authorizationToken": "QVdTOmVjcnBhc3N3b3Jk"}]
        }
        mock_get_client.return_value = mock_ecr

        # Mock base64.b64decode
        mock_b64decode.return_value = b"AWS:ecrpassword"

        # Call get_ecr_login_password without role
        password = await get_ecr_login_password()

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ecr")

        # Verify get_aws_client_with_role was not called
        mock_get_client_with_role.assert_not_called()

        # Verify get_authorization_token was called
        mock_ecr.get_authorization_token.assert_called_once()

        # Verify base64.b64decode was called with the correct parameters
        mock_b64decode.assert_called_once_with("QVdTOmVjcnBhc3N3b3Jk")

        # Verify the password was returned
        self.assertEqual(password, "ecrpassword")


if __name__ == "__main__":
    unittest.main()
