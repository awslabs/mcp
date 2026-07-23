"""
Unit tests for snapshots module.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.snapshots import (
    list_snapshots,
    create_snapshot,
    register_module
)


@pytest.fixture
def mock_snapshot_data():
    """Mock snapshot data for testing."""
    return {
        "SnapshotId": "snap-1234567890abcdef0",
        "VolumeId": "vol-1234567890abcdef0",
        "State": "completed",
        "Progress": "100%",
        "StartTime": datetime(2023, 1, 1, 12, 0, 0),
        "Description": "Test snapshot",
        "OwnerId": "123456789012",
        "VolumeSize": 20,
        "Encrypted": False,
        "Tags": [{"Key": "Name", "Value": "test-snapshot"}]
    }


@pytest.fixture
def mock_create_snapshot_response():
    """Mock create snapshot response."""
    return {
        "SnapshotId": "snap-1234567890abcdef0",
        "VolumeId": "vol-1234567890abcdef0",
        "State": "pending",
        "StartTime": datetime(2023, 1, 1, 12, 0, 0),
        "Description": "Test snapshot"
    }


class TestListSnapshots:
    """Tests for list_snapshots function."""

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_success(self, mock_aws_client, mock_snapshot_data):
        """Test successful snapshots listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [mock_snapshot_data]
        }

        result = await list_snapshots()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["snapshots"]) == 1
        assert result["snapshots"][0]["snapshot_id"] == "snap-1234567890abcdef0"
        assert result["snapshots"][0]["volume_id"] == "vol-1234567890abcdef0"
        assert result["snapshots"][0]["state"] == "completed"
        assert result["snapshots"][0]["progress"] == "100%"
        assert result["snapshots"][0]["volume_size"] == 20
        assert result["snapshots"][0]["encrypted"] is False

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_with_snapshot_ids(self, mock_aws_client, mock_snapshot_data):
        """Test snapshots listing with specific snapshot IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [mock_snapshot_data]
        }

        snapshot_ids = ["snap-1234567890abcdef0"]
        result = await list_snapshots(snapshot_ids=snapshot_ids)

        assert result["status"] == "success"
        mock_client.describe_snapshots.assert_called_once_with(SnapshotIds=snapshot_ids)

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_with_owner_ids(self, mock_aws_client, mock_snapshot_data):
        """Test snapshots listing with specific owner IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [mock_snapshot_data]
        }

        owner_ids = ["123456789012"]
        result = await list_snapshots(owner_ids=owner_ids)

        assert result["status"] == "success"
        mock_client.describe_snapshots.assert_called_once_with(OwnerIds=owner_ids)

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_with_filters(self, mock_aws_client, mock_snapshot_data):
        """Test snapshots listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [mock_snapshot_data]
        }

        filters = [{"Name": "state", "Values": ["completed"]}]
        result = await list_snapshots(filters=filters)

        assert result["status"] == "success"
        mock_client.describe_snapshots.assert_called_once_with(Filters=filters)

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_with_all_params(self, mock_aws_client, mock_snapshot_data):
        """Test snapshots listing with all parameters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [mock_snapshot_data]
        }

        snapshot_ids = ["snap-1234567890abcdef0"]
        owner_ids = ["123456789012"]
        filters = [{"Name": "state", "Values": ["completed"]}]
        
        result = await list_snapshots(
            snapshot_ids=snapshot_ids,
            owner_ids=owner_ids,
            filters=filters
        )

        assert result["status"] == "success"
        mock_client.describe_snapshots.assert_called_once_with(
            SnapshotIds=snapshot_ids,
            OwnerIds=owner_ids,
            Filters=filters
        )

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_empty_result(self, mock_aws_client):
        """Test snapshots listing with empty result."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {"Snapshots": []}

        result = await list_snapshots()

        assert result["status"] == "success"
        assert result["count"] == 0
        assert len(result["snapshots"]) == 0

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_with_missing_start_time(self, mock_aws_client):
        """Test snapshots listing with missing start time."""
        snapshot_data = {
            "SnapshotId": "snap-1234567890abcdef0",
            "VolumeId": "vol-1234567890abcdef0",
            "State": "completed",
            "Progress": "100%",
            "Description": "Test snapshot",
            "OwnerId": "123456789012",
            "VolumeSize": 20,
            "Encrypted": False,
            "Tags": []
        }
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.return_value = {
            "Snapshots": [snapshot_data]
        }

        result = await list_snapshots()

        assert result["status"] == "success"
        assert result["snapshots"][0]["start_time"] is None

    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_list_snapshots_client_error(self, mock_aws_client):
        """Test snapshots listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_snapshots.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidSnapshot.NotFound", "Message": "Snapshot not found"}},
            operation_name="DescribeSnapshots"
        )

        result = await list_snapshots()

        assert result["status"] == "error"
        assert result["error"] == "InvalidSnapshot.NotFound"


class TestCreateSnapshot:
    """Tests for create_snapshot function."""

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_success_minimal(self, mock_aws_client, mock_validate, mock_create_snapshot_response):
        """Test successful snapshot creation with minimal parameters."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_snapshot.return_value = mock_create_snapshot_response

        result = await create_snapshot("vol-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully created snapshot" in result["message"]
        assert result["snapshot_id"] == "snap-1234567890abcdef0"
        assert result["volume_id"] == "vol-1234567890abcdef0"
        assert result["state"] == "pending"
        
        mock_validate.assert_called_once_with("vol-1234567890abcdef0")
        mock_client.create_snapshot.assert_called_once_with(VolumeId="vol-1234567890abcdef0")

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_with_description(self, mock_aws_client, mock_validate, mock_create_snapshot_response):
        """Test snapshot creation with description."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_snapshot.return_value = mock_create_snapshot_response

        result = await create_snapshot(
            volume_id="vol-1234567890abcdef0",
            description="My test snapshot"
        )

        assert result["status"] == "success"
        assert result["description"] == "Test snapshot"
        
        call_args = mock_client.create_snapshot.call_args[1]
        assert call_args["VolumeId"] == "vol-1234567890abcdef0"
        assert call_args["Description"] == "My test snapshot"

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_with_tags(self, mock_aws_client, mock_validate, mock_create_snapshot_response):
        """Test snapshot creation with tags."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_snapshot.return_value = mock_create_snapshot_response

        tags = {"Environment": "test", "Purpose": "backup"}
        result = await create_snapshot(
            volume_id="vol-1234567890abcdef0",
            tags=tags
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_snapshot.call_args[1]
        assert "TagSpecifications" in call_args
        tag_specs = call_args["TagSpecifications"][0]
        assert tag_specs["ResourceType"] == "snapshot"
        assert len(tag_specs["Tags"]) == 2

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_with_all_params(self, mock_aws_client, mock_validate, mock_create_snapshot_response):
        """Test snapshot creation with all parameters."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_snapshot.return_value = mock_create_snapshot_response

        result = await create_snapshot(
            volume_id="vol-1234567890abcdef0",
            description="Complete test snapshot",
            tags={"Environment": "test"}
        )

        assert result["status"] == "success"
        
        call_args = mock_client.create_snapshot.call_args[1]
        assert call_args["VolumeId"] == "vol-1234567890abcdef0"
        assert call_args["Description"] == "Complete test snapshot"
        assert "TagSpecifications" in call_args

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_with_missing_start_time(self, mock_aws_client, mock_validate):
        """Test snapshot creation with missing start time in response."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        response_without_start_time = {
            "SnapshotId": "snap-1234567890abcdef0",
            "VolumeId": "vol-1234567890abcdef0",
            "State": "pending",
            "Description": "Test snapshot"
        }
        mock_client.create_snapshot.return_value = response_without_start_time

        result = await create_snapshot("vol-1234567890abcdef0")

        assert result["status"] == "success"
        assert result["start_time"] is None

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_validation_error(self, mock_aws_client, mock_validate):
        """Test snapshot creation with validation error."""
        mock_validate.side_effect = ValueError("Invalid volume ID format")
        
        result = await create_snapshot("invalid-volume-id")

        assert result["status"] == "error"
        # The validation error would be caught by the general exception handler

    @patch("awslabs.ec2_mcp_server.modules.snapshots.validate_volume_id")
    @patch("awslabs.ec2_mcp_server.modules.snapshots.aws_client")
    @pytest.mark.asyncio
    async def test_create_snapshot_client_error(self, mock_aws_client, mock_validate):
        """Test snapshot creation with client error."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_snapshot.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidVolume.NotFound", "Message": "Volume not found"}},
            operation_name="CreateSnapshot"
        )

        result = await create_snapshot("vol-1234567890abcdef0")

        assert result["status"] == "error"
        assert result["error"] == "InvalidVolume.NotFound"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_snapshots",
            "create_snapshot"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls