"""
Unit tests for key pairs module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.key_pairs import (
    list_key_pairs,
    create_key_pair,
    delete_key_pair,
    register_module
)


@pytest.fixture
def mock_key_pair_data():
    """Mock key pair data for testing."""
    return {
        "KeyName": "test-key",
        "KeyPairId": "key-1234567890abcdef0",
        "KeyFingerprint": "aa:bb:cc:dd:ee:ff:11:22:33:44:55:66:77:88:99:00",
        "KeyType": "rsa",
        "Tags": [{"Key": "Environment", "Value": "test"}]
    }


@pytest.fixture
def mock_create_key_pair_response():
    """Mock create key pair response."""
    return {
        "KeyName": "test-key",
        "KeyPairId": "key-1234567890abcdef0",
        "KeyFingerprint": "aa:bb:cc:dd:ee:ff:11:22:33:44:55:66:77:88:99:00",
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    }


class TestListKeyPairs:
    """Tests for list_key_pairs function."""

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_list_key_pairs_success(self, mock_aws_client, mock_key_pair_data):
        """Test successful key pairs listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_key_pairs.return_value = {
            "KeyPairs": [mock_key_pair_data]
        }

        result = await list_key_pairs()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["key_pairs"]) == 1
        assert result["key_pairs"][0]["key_name"] == "test-key"
        assert result["key_pairs"][0]["key_pair_id"] == "key-1234567890abcdef0"
        assert result["key_pairs"][0]["key_type"] == "rsa"

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_list_key_pairs_client_error(self, mock_aws_client):
        """Test key pairs listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_key_pairs.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidKeyPair.NotFound", "Message": "Key pair not found"}},
            operation_name="DescribeKeyPairs"
        )

        result = await list_key_pairs()

        assert result["status"] == "error"
        assert result["error"] == "InvalidKeyPair.NotFound"


class TestCreateKeyPair:
    """Tests for create_key_pair function."""

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.key_storage")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.validate_key_pair_name")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_create_key_pair_success_with_storage(self, mock_aws_client, mock_validate, mock_key_storage, mock_create_key_pair_response):
        """Test successful key pair creation with storage."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_key_pair.return_value = mock_create_key_pair_response
        
        # Mock successful storage
        mock_key_storage.store_private_key = AsyncMock(return_value={
            "status": "success",
            "storage_location": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test-key-abc123"
        })
        mock_key_storage.STORAGE_METHODS = {
            "secrets_manager": "AWS Secrets Manager"
        }

        result = await create_key_pair(
            key_name="test-key",
            storage_method="secrets_manager",
            tags={"Environment": "test"}
        )

        assert result["status"] == "success"
        assert "Successfully created key pair" in result["message"]
        assert result["key_name"] == "test-key"
        assert result["key_pair_id"] == "key-1234567890abcdef0"
        assert result["private_key_stored"] is True
        assert result["storage_method"] == "secrets_manager"

        # Verify API calls
        mock_validate.assert_called_once_with("test-key")
        mock_client.create_key_pair.assert_called_once()
        mock_key_storage.store_private_key.assert_called_once()

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.key_storage")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.validate_key_pair_name")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_create_key_pair_storage_failure_rollback(self, mock_aws_client, mock_validate, mock_key_storage, mock_create_key_pair_response):
        """Test key pair creation with storage failure and rollback."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_key_pair.return_value = mock_create_key_pair_response
        
        # Mock storage failure
        mock_key_storage.store_private_key = AsyncMock(return_value={
            "status": "error",
            "message": "Storage service unavailable"
        })

        result = await create_key_pair(
            key_name="test-key",
            storage_method="secrets_manager",
            tags={"Environment": "test"}
        )

        assert result["status"] == "error"
        assert "storage error" in result["message"]
        assert "rollback" in result
        
        # Verify rollback was attempted
        mock_client.delete_key_pair.assert_called_once_with(KeyName="test-key")


class TestDeleteKeyPair:
    """Tests for delete_key_pair function."""

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.validate_key_pair_name")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_delete_key_pair_success_without_storage_info(self, mock_aws_client, mock_validate):
        """Test successful key pair deletion without storage info provided."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await delete_key_pair("test-key")

        assert result["status"] == "success"
        assert "Successfully deleted key pair" in result["message"]
        assert result["key_name"] == "test-key"
        assert "warning" in result
        assert "Private key may still exist in AWS storage" in result["warning"]
        
        mock_client.delete_key_pair.assert_called_once_with(KeyName="test-key")

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.key_storage")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.validate_key_pair_name")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_delete_key_pair_with_stored_key_success(self, mock_aws_client, mock_validate, mock_key_storage):
        """Test key pair deletion with successful stored key deletion."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        mock_key_storage.delete_stored_key = AsyncMock(return_value={"status": "success"})

        result = await delete_key_pair(
            key_name="test-key",
            storage_method="secrets_manager",
            storage_location="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-key-abc123",
            delete_stored_key=True
        )

        assert result["status"] == "success"
        assert "and stored private key deleted" in result["message"]
        assert result["stored_key_deleted"] is True

    @patch("awslabs.ec2_mcp_server.modules.key_pairs.validate_key_pair_name")
    @patch("awslabs.ec2_mcp_server.modules.key_pairs.aws_client")
    @pytest.mark.asyncio
    async def test_delete_key_pair_without_deleting_stored_key(self, mock_aws_client, mock_validate):
        """Test key pair deletion when explicitly not deleting stored key."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await delete_key_pair(
            key_name="test-key",
            delete_stored_key=False
        )

        assert result["status"] == "success"
        assert "Successfully deleted key pair" in result["message"]
        assert "warning" not in result
        
        mock_client.delete_key_pair.assert_called_once_with(KeyName="test-key")


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_key_pairs",
            "create_key_pair",
            "delete_key_pair"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls