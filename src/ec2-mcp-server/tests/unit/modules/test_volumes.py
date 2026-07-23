"""
Unit tests for volumes module.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.volumes import (
    list_volumes,
    create_volume,
    delete_volume,
    attach_volume,
    detach_volume,
    register_module
)


@pytest.fixture
def mock_volume_data():
    """Mock volume data for testing."""
    return {
        "VolumeId": "vol-1234567890abcdef0",
        "VolumeType": "gp3",
        "Size": 20,
        "State": "available",
        "AvailabilityZone": "us-east-1a",
        "Encrypted": False,
        "Iops": 3000,
        "Throughput": 125,
        "Attachments": [],
        "CreateTime": datetime(2023, 1, 1, 12, 0, 0),
        "Tags": [{"Key": "Name", "Value": "test-volume"}]
    }


@pytest.fixture
def mock_create_volume_response():
    """Mock create volume response."""
    return {
        "VolumeId": "vol-1234567890abcdef0",
        "AvailabilityZone": "us-east-1a",
        "Size": 20,
        "VolumeType": "gp3",
        "State": "creating"
    }


@pytest.fixture
def mock_attach_volume_response():
    """Mock attach volume response."""
    return {
        "VolumeId": "vol-1234567890abcdef0",
        "InstanceId": "i-1234567890abcdef0",
        "Device": "/dev/sdf",
        "State": "attaching"
    }


@pytest.fixture
def mock_detach_volume_response():
    """Mock detach volume response."""
    return {
        "VolumeId": "vol-1234567890abcdef0",
        "InstanceId": "i-1234567890abcdef0",
        "Device": "/dev/sdf",
        "State": "detaching"
    }


class TestListVolumes:
    """Tests for list_volumes function."""

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_success(self, mock_aws_client, mock_volume_data):
        """Test successful volumes listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {
            "Volumes": [mock_volume_data]
        }

        result = await list_volumes()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["volumes"]) == 1
        assert result["volumes"][0]["volume_id"] == "vol-1234567890abcdef0"
        assert result["volumes"][0]["volume_type"] == "gp3"
        assert result["volumes"][0]["size"] == 20
        assert result["volumes"][0]["state"] == "available"
        assert result["volumes"][0]["encrypted"] is False
        assert result["volumes"][0]["iops"] == 3000
        assert result["volumes"][0]["throughput"] == 125

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_with_volume_ids(self, mock_aws_client, mock_volume_data):
        """Test volumes listing with specific volume IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {
            "Volumes": [mock_volume_data]
        }

        volume_ids = ["vol-1234567890abcdef0"]
        result = await list_volumes(volume_ids=volume_ids)

        assert result["status"] == "success"
        mock_client.describe_volumes.assert_called_once_with(VolumeIds=volume_ids)

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_with_filters(self, mock_aws_client, mock_volume_data):
        """Test volumes listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {
            "Volumes": [mock_volume_data]
        }

        filters = [{"Name": "state", "Values": ["available"]}]
        result = await list_volumes(filters=filters)

        assert result["status"] == "success"
        mock_client.describe_volumes.assert_called_once_with(Filters=filters)

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_with_both_params(self, mock_aws_client, mock_volume_data):
        """Test volumes listing with both volume IDs and filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {
            "Volumes": [mock_volume_data]
        }

        volume_ids = ["vol-1234567890abcdef0"]
        filters = [{"Name": "state", "Values": ["available"]}]
        
        result = await list_volumes(volume_ids=volume_ids, filters=filters)

        assert result["status"] == "success"
        mock_client.describe_volumes.assert_called_once_with(
            VolumeIds=volume_ids,
            Filters=filters
        )

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_empty_result(self, mock_aws_client):
        """Test volumes listing with empty result."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {"Volumes": []}

        result = await list_volumes()

        assert result["status"] == "success"
        assert result["count"] == 0
        assert len(result["volumes"]) == 0

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_with_missing_optional_fields(self, mock_aws_client):
        """Test volumes listing with missing optional fields."""
        volume_data = {
            "VolumeId": "vol-1234567890abcdef0",
            "VolumeType": "gp2",
            "Size": 8,
            "State": "available",
            "AvailabilityZone": "us-east-1a",
            "Encrypted": False,
            "Attachments": [],
            "Tags": []
        }
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.return_value = {
            "Volumes": [volume_data]
        }

        result = await list_volumes()

        assert result["status"] == "success"
        assert result["volumes"][0]["iops"] is None
        assert result["volumes"][0]["throughput"] is None
        assert result["volumes"][0]["create_time"] is None

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_list_volumes_client_error(self, mock_aws_client):
        """Test volumes listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_volumes.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidVolume.NotFound", "Message": "Volume not found"}},
            operation_name="DescribeVolumes"
        )

        result = await list_volumes()

        assert result["status"] == "error"
        assert result["error"] == "InvalidVolume.NotFound"


class TestCreateVolume:
    """Tests for create_volume function."""

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_minimal_params(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with minimal parameters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=20
        )

        assert result["status"] == "success"
        assert "Successfully created volume" in result["message"]
        assert result["volume_id"] == "vol-1234567890abcdef0"
        assert result["availability_zone"] == "us-east-1a"
        assert result["size"] == 20
        assert result["volume_type"] == "gp3"
        assert result["state"] == "creating"

        call_args = mock_client.create_volume.call_args[1]
        assert call_args["AvailabilityZone"] == "us-east-1a"
        assert call_args["Size"] == 20
        assert call_args["VolumeType"] == "gp3"  # Default
        assert call_args["Encrypted"] is False  # Default

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_with_custom_type(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with custom volume type."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=100,
            volume_type="io2"
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert call_args["VolumeType"] == "io2"

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_with_iops(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with IOPS."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=100,
            volume_type="io2",
            iops=1000
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert call_args["Iops"] == 1000

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_with_throughput(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with throughput."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=100,
            volume_type="gp3",
            throughput=250
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert call_args["Throughput"] == 250

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_encrypted(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with encryption."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=20,
            encrypted=True
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert call_args["Encrypted"] is True

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_with_tags(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with tags."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        tags = {"Environment": "test", "Purpose": "testing"}
        result = await create_volume(
            availability_zone="us-east-1a",
            size=20,
            tags=tags
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert "TagSpecifications" in call_args
        tag_specs = call_args["TagSpecifications"][0]
        assert tag_specs["ResourceType"] == "volume"
        assert len(tag_specs["Tags"]) == 2

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_with_all_params(self, mock_aws_client, mock_create_volume_response):
        """Test volume creation with all parameters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.return_value = mock_create_volume_response

        result = await create_volume(
            availability_zone="us-east-1a",
            size=100,
            volume_type="gp3",
            iops=3000,
            throughput=125,
            encrypted=True,
            tags={"Name": "test-volume"}
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_volume.call_args[1]
        assert call_args["AvailabilityZone"] == "us-east-1a"
        assert call_args["Size"] == 100
        assert call_args["VolumeType"] == "gp3"
        assert call_args["Iops"] == 3000
        assert call_args["Throughput"] == 125
        assert call_args["Encrypted"] is True
        assert "TagSpecifications" in call_args

    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_create_volume_client_error(self, mock_aws_client):
        """Test volume creation with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_volume.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidParameterValue", "Message": "Invalid size"}},
            operation_name="CreateVolume"
        )

        result = await create_volume(
            availability_zone="us-east-1a",
            size=0  # Invalid size
        )

        assert result["status"] == "error"
        assert result["error"] == "InvalidParameterValue"


class TestDeleteVolume:
    """Tests for delete_volume function."""

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_delete_volume_success(self, mock_aws_client, mock_validate):
        """Test successful volume deletion."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await delete_volume("vol-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully deleted volume" in result["message"]
        assert result["volume_id"] == "vol-1234567890abcdef0"
        
        mock_validate.assert_called_once_with("vol-1234567890abcdef0")
        mock_client.delete_volume.assert_called_once_with(VolumeId="vol-1234567890abcdef0")

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_delete_volume_client_error(self, mock_aws_client, mock_validate):
        """Test volume deletion with client error."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.delete_volume.side_effect = ClientError(
            error_response={"Error": {"Code": "VolumeInUse", "Message": "Volume is in use"}},
            operation_name="DeleteVolume"
        )

        result = await delete_volume("vol-1234567890abcdef0")

        assert result["status"] == "error"
        assert result["error"] == "VolumeInUse"


class TestAttachVolume:
    """Tests for attach_volume function."""

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_attach_volume_success(self, mock_aws_client, mock_validate_volume, mock_validate_instance, mock_attach_volume_response):
        """Test successful volume attachment."""
        mock_validate_volume.return_value = True
        mock_validate_instance.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.attach_volume.return_value = mock_attach_volume_response

        result = await attach_volume(
            volume_id="vol-1234567890abcdef0",
            instance_id="i-1234567890abcdef0",
            device="/dev/sdf"
        )

        assert result["status"] == "success"
        assert "Successfully attached volume" in result["message"]
        assert result["volume_id"] == "vol-1234567890abcdef0"
        assert result["instance_id"] == "i-1234567890abcdef0"
        assert result["device"] == "/dev/sdf"
        assert result["state"] == "attaching"

        mock_validate_volume.assert_called_once_with("vol-1234567890abcdef0")
        mock_validate_instance.assert_called_once_with("i-1234567890abcdef0")
        mock_client.attach_volume.assert_called_once_with(
            VolumeId="vol-1234567890abcdef0",
            InstanceId="i-1234567890abcdef0",
            Device="/dev/sdf"
        )

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_attach_volume_client_error(self, mock_aws_client, mock_validate_volume, mock_validate_instance):
        """Test volume attachment with client error."""
        mock_validate_volume.return_value = True
        mock_validate_instance.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.attach_volume.side_effect = ClientError(
            error_response={"Error": {"Code": "VolumeInUse", "Message": "Volume already attached"}},
            operation_name="AttachVolume"
        )

        result = await attach_volume(
            volume_id="vol-1234567890abcdef0",
            instance_id="i-1234567890abcdef0",
            device="/dev/sdf"
        )

        assert result["status"] == "error"
        assert result["error"] == "VolumeInUse"


class TestDetachVolume:
    """Tests for detach_volume function."""

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_minimal_params(self, mock_aws_client, mock_validate, mock_detach_volume_response):
        """Test volume detachment with minimal parameters."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.return_value = mock_detach_volume_response

        result = await detach_volume("vol-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully detached volume" in result["message"]
        assert result["volume_id"] == "vol-1234567890abcdef0"
        assert result["instance_id"] == "i-1234567890abcdef0"
        assert result["device"] == "/dev/sdf"
        assert result["state"] == "detaching"

        mock_validate.assert_called_once_with("vol-1234567890abcdef0")
        call_args = mock_client.detach_volume.call_args[1]
        assert call_args["VolumeId"] == "vol-1234567890abcdef0"
        assert call_args["Force"] is False
        assert "InstanceId" not in call_args
        assert "Device" not in call_args

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_with_instance_id(self, mock_aws_client, mock_validate, mock_detach_volume_response):
        """Test volume detachment with instance ID."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.return_value = mock_detach_volume_response

        result = await detach_volume(
            volume_id="vol-1234567890abcdef0",
            instance_id="i-1234567890abcdef0"
        )

        assert result["status"] == "success"
        
        call_args = mock_client.detach_volume.call_args[1]
        assert call_args["InstanceId"] == "i-1234567890abcdef0"

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_with_device(self, mock_aws_client, mock_validate, mock_detach_volume_response):
        """Test volume detachment with device."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.return_value = mock_detach_volume_response

        result = await detach_volume(
            volume_id="vol-1234567890abcdef0",
            device="/dev/sdf"
        )

        assert result["status"] == "success"
        
        call_args = mock_client.detach_volume.call_args[1]
        assert call_args["Device"] == "/dev/sdf"

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_with_force(self, mock_aws_client, mock_validate, mock_detach_volume_response):
        """Test volume detachment with force."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.return_value = mock_detach_volume_response

        result = await detach_volume(
            volume_id="vol-1234567890abcdef0",
            force=True
        )

        assert result["status"] == "success"
        
        call_args = mock_client.detach_volume.call_args[1]
        assert call_args["Force"] is True

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_with_all_params(self, mock_aws_client, mock_validate, mock_detach_volume_response):
        """Test volume detachment with all parameters."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.return_value = mock_detach_volume_response

        result = await detach_volume(
            volume_id="vol-1234567890abcdef0",
            instance_id="i-1234567890abcdef0",
            device="/dev/sdf",
            force=True
        )

        assert result["status"] == "success"
        
        call_args = mock_client.detach_volume.call_args[1]
        assert call_args["VolumeId"] == "vol-1234567890abcdef0"
        assert call_args["InstanceId"] == "i-1234567890abcdef0"
        assert call_args["Device"] == "/dev/sdf"
        assert call_args["Force"] is True

    @patch("awslabs.ec2_mcp_server.modules.volumes.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.volumes.aws_client")
    @pytest.mark.asyncio
    async def test_detach_volume_client_error(self, mock_aws_client, mock_validate):
        """Test volume detachment with client error."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.detach_volume.side_effect = ClientError(
            error_response={"Error": {"Code": "VolumeNotFound", "Message": "Volume not found"}},
            operation_name="DetachVolume"
        )

        result = await detach_volume("vol-1234567890abcdef0")

        assert result["status"] == "error"
        assert result["error"] == "VolumeNotFound"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_volumes",
            "create_volume",
            "delete_volume",
            "attach_volume",
            "detach_volume"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls