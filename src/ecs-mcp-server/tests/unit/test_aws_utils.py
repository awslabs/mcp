"""
Unit tests for AWS utility functions.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import (
    create_ecr_repository,
    get_aws_account_id,
    get_aws_client,
    get_default_vpc_and_subnets,
    get_ecr_login_password,
)


class TestAWSUtils(unittest.TestCase):
    """Tests for AWS utility functions."""

    @pytest.mark.anyio
    @patch("boto3.client")
    async def test_get_aws_client(self, mock_boto_client):
        """Test get_aws_client function."""
        # Mock boto3.client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Call get_aws_client
        client = await get_aws_client("s3")

        # Verify boto3.client was called with the correct parameters
        mock_boto_client.assert_called_once()
        args, kwargs = mock_boto_client.call_args
        self.assertEqual(args[0], "s3")
        self.assertIn("region_name", kwargs)

        # Verify the client was returned
        self.assertEqual(client, mock_client)

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    async def test_get_aws_account_id(self, mock_get_client):
        """Test get_aws_account_id function."""
        # Mock get_aws_client
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_get_client.return_value = mock_sts

        # Call get_aws_account_id
        account_id = await get_aws_account_id()

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("sts")

        # Verify get_caller_identity was called
        mock_sts.get_caller_identity.assert_called_once()

        # Verify the account ID was returned
        self.assertEqual(account_id, "123456789012")

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    async def test_get_default_vpc_and_subnets(self, mock_get_client):
        """Test get_default_vpc_and_subnets function."""
        # Mock get_aws_client
        mock_ec2 = MagicMock()
        mock_ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-12345678"}]}
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-12345678"}, {"SubnetId": "subnet-87654321"}]
        }
        mock_get_client.return_value = mock_ec2

        # Call get_default_vpc_and_subnets
        vpc_info = await get_default_vpc_and_subnets()

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ec2")

        # Verify describe_vpcs was called with the correct parameters
        mock_ec2.describe_vpcs.assert_called_once()
        args, kwargs = mock_ec2.describe_vpcs.call_args
        self.assertIn("Filters", kwargs)
        self.assertEqual(kwargs["Filters"][0]["Name"], "isDefault")
        self.assertEqual(kwargs["Filters"][0]["Values"], ["true"])

        # Verify describe_subnets was called
        self.assertEqual(mock_ec2.describe_subnets.call_count, 1)

        # Verify the VPC info was returned
        self.assertIn("vpc_id", vpc_info)
        self.assertIn("subnet_ids", vpc_info)
        self.assertEqual(vpc_info["vpc_id"], "vpc-12345678")
        self.assertEqual(len(vpc_info["subnet_ids"]), 2)
        self.assertIn("subnet-12345678", vpc_info["subnet_ids"])
        self.assertIn("subnet-87654321", vpc_info["subnet_ids"])

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    async def test_create_ecr_repository_existing(self, mock_get_client):
        """Test create_ecr_repository function with existing repository."""
        # Mock get_aws_client
        mock_ecr = MagicMock()
        mock_ecr.describe_repositories.return_value = {
            "repositories": [
                {
                    "repositoryName": "test-repo",
                    "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
                }
            ]
        }
        mock_get_client.return_value = mock_ecr

        # Call create_ecr_repository
        repo = await create_ecr_repository("test-repo")

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ecr")

        # Verify describe_repositories was called with the correct parameters
        mock_ecr.describe_repositories.assert_called_once()
        args, kwargs = mock_ecr.describe_repositories.call_args
        self.assertIn("repositoryNames", kwargs)
        self.assertEqual(kwargs["repositoryNames"], ["test-repo"])

        # Verify create_repository was not called
        mock_ecr.create_repository.assert_not_called()

        # Verify the repository info was returned
        self.assertEqual(repo["repositoryName"], "test-repo")
        self.assertEqual(
            repo["repositoryUri"], "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo"
        )

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    async def test_create_ecr_repository_new(self, mock_get_client):
        """Test create_ecr_repository function with new repository."""
        # Mock get_aws_client
        mock_ecr = MagicMock()
        error_response = {
            "Error": {"Code": "RepositoryNotFoundException", "Message": "Repository not found"}
        }
        mock_ecr.describe_repositories.side_effect = ClientError(
            error_response, "DescribeRepositories"
        )
        mock_ecr.create_repository.return_value = {
            "repository": {
                "repositoryName": "test-repo",
                "repositoryUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
            }
        }
        mock_get_client.return_value = mock_ecr

        # Call create_ecr_repository
        repo = await create_ecr_repository("test-repo")

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ecr")

        # Verify describe_repositories was called with the correct parameters
        mock_ecr.describe_repositories.assert_called_once()

        # Verify create_repository was called with the correct parameters
        mock_ecr.create_repository.assert_called_once()
        args, kwargs = mock_ecr.create_repository.call_args
        self.assertIn("repositoryName", kwargs)
        self.assertEqual(kwargs["repositoryName"], "test-repo")
        self.assertIn("imageScanningConfiguration", kwargs)
        self.assertTrue(kwargs["imageScanningConfiguration"]["scanOnPush"])

        # Verify the repository info was returned
        self.assertEqual(repo["repositoryName"], "test-repo")
        self.assertEqual(
            repo["repositoryUri"], "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo"
        )

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
    @patch("base64.b64decode")
    async def test_get_ecr_login_password(self, mock_b64decode, mock_get_client):
        """Test get_ecr_login_password function."""
        # Mock get_aws_client
        mock_ecr = MagicMock()
        mock_ecr.get_authorization_token.return_value = {
            "authorizationData": [{"authorizationToken": "QVdTOmVjcnBhc3N3b3Jk"}]
        }
        mock_get_client.return_value = mock_ecr

        # Mock base64.b64decode
        mock_b64decode.return_value = b"AWS:ecrpassword"

        # Call get_ecr_login_password
        password = await get_ecr_login_password()

        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ecr")

        # Verify get_authorization_token was called
        mock_ecr.get_authorization_token.assert_called_once()

        # Verify base64.b64decode was called with the correct parameters
        mock_b64decode.assert_called_once_with("QVdTOmVjcnBhc3N3b3Jk")

        # Verify the password was returned
        self.assertEqual(password, "ecrpassword")


if __name__ == "__main__":
    unittest.main()
