"""
Unit tests for AMIs module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.amis import (
    list_amis,
    get_popular_amis,
    create_image,
    deregister_image,
    register_module
)


class TestListAmis:
    """Tests for list_amis function."""

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_default_behavior(self, mock_aws_client, mock_ami_data):
        """Test default behavior - should list only user's own AMIs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {
            "Images": [mock_ami_data]
        }

        result = await list_amis()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["total_available"] == 1
        assert result["showing_latest"] == 10
        assert len(result["amis"]) == 1
        assert result["amis"][0]["ami_id"] == "ami-12345678"
        
        # Verify default filters applied
        call_args = mock_client.describe_images.call_args[1]
        assert call_args["Owners"] == ["self"]
        assert any(f["Name"] == "state" for f in call_args["Filters"])
        assert any(f["Name"] == "architecture" for f in call_args["Filters"])

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_with_specific_ids(self, mock_aws_client, mock_ami_data):
        """Test listing AMIs with specific IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {
            "Images": [mock_ami_data]
        }

        ami_ids = ["ami-12345678", "ami-87654321"]
        result = await list_amis(ami_ids=ami_ids)

        assert result["status"] == "success"
        
        # When specific IDs are provided, Owners should not be set
        call_args = mock_client.describe_images.call_args[1]
        assert call_args["ImageIds"] == ami_ids
        assert "Owners" not in call_args

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_include_public(self, mock_aws_client, mock_ami_data):
        """Test listing AMIs with public AMIs included."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {
            "Images": [mock_ami_data]
        }

        result = await list_amis(include_public=True)

        assert result["status"] == "success"
        assert result["filters_applied"]["include_public"] is True
        
        # Should include both amazon and self when public is enabled
        call_args = mock_client.describe_images.call_args[1]
        assert call_args["Owners"] == ["amazon", "self"]

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_custom_owners(self, mock_aws_client, mock_ami_data):
        """Test listing AMIs with custom owners."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {
            "Images": [mock_ami_data]
        }

        owners = ["123456789012", "amazon"]
        result = await list_amis(owners=owners)

        assert result["status"] == "success"
        
        call_args = mock_client.describe_images.call_args[1]
        assert call_args["Owners"] == owners

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_max_results_limit(self, mock_aws_client):
        """Test that results are limited to max_results."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Create 100 mock AMIs
        mock_amis = []
        for i in range(100):
            mock_amis.append({
                "ImageId": f"ami-{i:08d}",
                "Name": f"test-ami-{i}",
                "OwnerId": "123456789012",
                "State": "available",
                "Architecture": "x86_64",
                "RootDeviceType": "ebs",
                "VirtualizationType": "hvm",
                "CreationDate": f"2023-01-{i+1:02d}T12:00:00Z",
                "Public": False,
                "Tags": []
            })
        
        mock_client.describe_images.return_value = {"Images": mock_amis}

        result = await list_amis(max_results=10)

        assert result["status"] == "success"
        assert result["count"] == 10  # Limited to max_results
        assert result["total_available"] == 100  # Total available
        assert result["showing_latest"] == 10

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_custom_filters(self, mock_aws_client, mock_ami_data):
        """Test listing AMIs with custom filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {
            "Images": [mock_ami_data]
        }

        custom_filters = [{"Name": "name", "Values": ["my-custom-ami*"]}]
        result = await list_amis(filters=custom_filters)

        assert result["status"] == "success"
        
        call_args = mock_client.describe_images.call_args[1]
        assert call_args["Filters"] == custom_filters

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_general_exception(self, mock_aws_client):
        """Test list AMIs with general exception."""
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await list_amis()

        assert result["status"] == "error"


class TestGetPopularAmis:
    """Tests for get_popular_amis function."""

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_success(self, mock_aws_client):
        """Test successful retrieval of popular AMIs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock responses for different AMI queries
        def mock_describe_images(**kwargs):
            if "al2023-ami-" in str(kwargs.get("Filters", [])):
                return {
                    "Images": [{
                        "ImageId": "ami-amazon123",
                        "Name": "al2023-ami-2023.1.20230101.0-kernel-6.1-x86_64",
                        "Architecture": "x86_64",
                        "CreationDate": "2023-01-01T12:00:00Z"
                    }]
                }
            elif "ubuntu/images/hvm-ssd/ubuntu-jammy" in str(kwargs.get("Filters", [])):
                return {
                    "Images": [{
                        "ImageId": "ami-ubuntu123",
                        "Name": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20230101",
                        "Architecture": "x86_64",
                        "CreationDate": "2023-01-01T12:00:00Z"
                    }]
                }
            elif "Windows_Server-2022" in str(kwargs.get("Filters", [])):
                return {
                    "Images": [{
                        "ImageId": "ami-windows123",
                        "Name": "Windows_Server-2022-English-Full-Base-2023.01.01",
                        "Architecture": "x86_64",
                        "CreationDate": "2023-01-01T12:00:00Z"
                    }]
                }
            return {"Images": []}
        
        mock_client.describe_images.side_effect = mock_describe_images

        result = await get_popular_amis()

        assert result["status"] == "success"
        assert result["count"] == 3
        assert len(result["popular_amis"]) == 3
        
        # Check categories
        categories = [ami["category"] for ami in result["popular_amis"]]
        assert "Amazon Linux" in categories
        assert "Ubuntu" in categories
        assert "Windows Server" in categories

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_partial_results(self, mock_aws_client):
        """Test popular AMIs with only some results available."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock only Amazon Linux response
        def mock_describe_images(**kwargs):
            if "al2023-ami-" in str(kwargs.get("Filters", [])):
                return {
                    "Images": [{
                        "ImageId": "ami-amazon123",
                        "Name": "al2023-ami-2023.1.20230101.0-kernel-6.1-x86_64",
                        "Architecture": "x86_64",
                        "CreationDate": "2023-01-01T12:00:00Z"
                    }]
                }
            return {"Images": []}  # No other AMIs found
        
        mock_client.describe_images.side_effect = mock_describe_images

        result = await get_popular_amis()

        assert result["status"] == "success"
        assert result["count"] == 1  # Only Amazon Linux found
        assert len(result["popular_amis"]) == 1
        assert result["popular_amis"][0]["category"] == "Amazon Linux"

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_with_exception_handling(self, mock_aws_client):
        """Test popular AMIs with exception handling for specific AMI types."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock describe_images to raise exception for Amazon Linux but succeed for others
        def mock_describe_images(**kwargs):
            if "al2023-ami-" in str(kwargs.get("Filters", [])):
                raise ClientError(
                    error_response={"Error": {"Code": "RequestLimitExceeded", "Message": "Rate limit exceeded"}},
                    operation_name="DescribeImages"
                )
            elif "ubuntu/images/hvm-ssd/ubuntu-jammy" in str(kwargs.get("Filters", [])):
                return {
                    "Images": [{
                        "ImageId": "ami-ubuntu123",
                        "Name": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20230101",
                        "Architecture": "x86_64",
                        "CreationDate": "2023-01-01T12:00:00Z"
                    }]
                }
            return {"Images": []}
        
        mock_client.describe_images.side_effect = mock_describe_images

        result = await get_popular_amis()

        assert result["status"] == "success"
        assert result["count"] == 1  # Only Ubuntu found (Amazon Linux failed)
        assert len(result["popular_amis"]) == 1
        assert result["popular_amis"][0]["category"] == "Ubuntu"

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_all_fail(self, mock_aws_client):
        """Test popular AMIs when all AMI type queries fail."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock all describe_images calls to raise exceptions
        mock_client.describe_images.side_effect = ClientError(
            error_response={"Error": {"Code": "RequestLimitExceeded", "Message": "Rate limit exceeded"}},
            operation_name="DescribeImages"
        )

        result = await get_popular_amis()

        assert result["status"] == "success"
        assert result["count"] == 0  # No AMIs found due to exceptions
        assert len(result["popular_amis"]) == 0

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_client_error(self, mock_aws_client):
        """Test popular AMIs with general client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.side_effect = ClientError(
            error_response={"Error": {"Code": "UnauthorizedOperation", "Message": "Not authorized"}},
            operation_name="GetClient"
        )

        result = await get_popular_amis()

        assert result["status"] == "error"
        assert result["error"] == "UnauthorizedOperation"


class TestCreateImage:
    """Tests for create_image function."""

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.amis.validate_instance_id")
    @pytest.mark.asyncio
    async def test_create_image_success(self, mock_validate, mock_aws_client):
        """Test successful AMI creation."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_image.return_value = {
            "ImageId": "ami-12345678"
        }

        result = await create_image(
            instance_id="i-1234567890abcdef0",
            name="test-ami",
            description="Test AMI",
            no_reboot=True,
            tags={"Environment": "test"}
        )

        assert result["status"] == "success"
        assert "Successfully created AMI" in result["message"]
        assert result["ami_id"] == "ami-12345678"
        assert result["name"] == "test-ami"
        assert result["instance_id"] == "i-1234567890abcdef0"

        # Verify API call parameters
        call_args = mock_client.create_image.call_args[1]
        assert call_args["InstanceId"] == "i-1234567890abcdef0"
        assert call_args["Name"] == "test-ami"
        assert call_args["Description"] == "Test AMI"
        assert call_args["NoReboot"] is True
        assert "TagSpecifications" in call_args

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.amis.validate_instance_id")
    @pytest.mark.asyncio
    async def test_create_image_general_exception(self, mock_validate, mock_aws_client):
        """Test create image with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await create_image(
            instance_id="i-1234567890abcdef0",
            name="test-ami"
        )

        assert result["status"] == "error"


class TestDeregisterImage:
    """Tests for deregister_image function."""

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.amis.validate_ami_id")
    @pytest.mark.asyncio
    async def test_deregister_image_success(self, mock_validate, mock_aws_client):
        """Test successful AMI deregistration."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await deregister_image("ami-12345678")

        assert result["status"] == "success"
        assert "Successfully deregistered AMI" in result["message"]
        assert result["ami_id"] == "ami-12345678"

        mock_client.deregister_image.assert_called_once_with(ImageId="ami-12345678")

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.amis.validate_ami_id")
    @pytest.mark.asyncio
    async def test_deregister_image_general_exception(self, mock_validate, mock_aws_client):
        """Test deregister image with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await deregister_image("ami-12345678")

        assert result["status"] == "error"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_amis",
            "get_popular_amis",
            "create_image",
            "deregister_image"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls


class TestAdditionalAMICases:
    """Additional tests to improve coverage."""

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_list_amis_empty_result(self, mock_aws_client):
        """Test listing AMIs with empty result."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_images.return_value = {"Images": []}

        result = await list_amis()

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["amis"] == []

    @patch("awslabs.ec2_mcp_server.modules.amis.validate_instance_id")
    @pytest.mark.asyncio
    async def test_create_image_invalid_instance_id(self, mock_validate):
        """Test create image with invalid instance ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")
        
        result = await create_image("invalid-instance-id", "test-image")
        
        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-instance-id")

    @patch("awslabs.ec2_mcp_server.modules.amis.validate_ami_id")
    @pytest.mark.asyncio  
    async def test_deregister_image_invalid_ami_id(self, mock_validate):
        """Test deregister image with invalid AMI ID format."""
        mock_validate.side_effect = Exception("Invalid AMI ID format")
        
        result = await deregister_image("invalid-ami-id")
        
        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-ami-id")

    @patch("awslabs.ec2_mcp_server.modules.amis.aws_client")
    @pytest.mark.asyncio
    async def test_get_popular_amis_partial_failure(self, mock_aws_client):
        """Test get popular AMIs with partial failures."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock some AMI searches to succeed and others to fail
        def mock_describe_images(**kwargs):
            filters = kwargs.get('Filters', [])
            for f in filters:
                if f.get('Name') == 'name' and f.get('Values'):
                    ami_name = f['Values'][0]
                    if 'ubuntu' in ami_name.lower():
                        return {"Images": [{
                            "ImageId": "ami-ubuntu123", 
                            "Name": "ubuntu-test", 
                            "CreationDate": "2023-01-01T12:00:00Z",
                            "Architecture": "x86_64"
                        }]}
            # Return empty for other searches
            return {"Images": []}
        
        mock_client.describe_images.side_effect = mock_describe_images

        result = await get_popular_amis()

        # Should succeed even with partial failures
        assert result["status"] == "success"
        assert "popular_amis" in result
        # Should have some AMIs (at least the Ubuntu one)
        assert len(result["popular_amis"]) >= 1