"""
Unit tests for VPC management module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.vpc_management import (
    list_vpcs,
    get_default_vpc,
    find_suitable_subnet,
    delete_vpc,
    list_subnets,
    register_module
)


@pytest.fixture
def mock_vpc_data():
    """Mock VPC data for testing."""
    return {
        "VpcId": "vpc-12345678",
        "CidrBlock": "10.0.0.0/16",
        "State": "available",
        "IsDefault": True,
        "InstanceTenancy": "default",
        "DhcpOptionsId": "dopt-12345678",
        "Tags": [{"Key": "Name", "Value": "test-vpc"}]
    }


@pytest.fixture
def mock_subnet_data():
    """Mock subnet data for testing."""
    return {
        "SubnetId": "subnet-12345678",
        "VpcId": "vpc-12345678",
        "CidrBlock": "10.0.1.0/24",
        "AvailabilityZone": "us-east-1a",
        "State": "available",
        "AvailableIpAddressCount": 250,
        "MapPublicIpOnLaunch": True,
        "DefaultForAz": False,
        "Tags": [{"Key": "Name", "Value": "test-subnet"}]
    }


class TestListVpcs:
    """Tests for list_vpcs function."""

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_vpcs_success(self, mock_aws_client, mock_vpc_data):
        """Test successful VPC listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {
            "Vpcs": [mock_vpc_data]
        }

        result = await list_vpcs()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["vpcs"]) == 1
        assert result["vpcs"][0]["vpc_id"] == "vpc-12345678"
        assert result["vpcs"][0]["cidr_block"] == "10.0.0.0/16"
        assert result["vpcs"][0]["is_default"] is True

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_vpcs_with_ids(self, mock_aws_client, mock_vpc_data):
        """Test VPC listing with specific IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {
            "Vpcs": [mock_vpc_data]
        }

        vpc_ids = ["vpc-12345678"]
        result = await list_vpcs(vpc_ids=vpc_ids)

        assert result["status"] == "success"
        mock_client.describe_vpcs.assert_called_once_with(VpcIds=vpc_ids)

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_vpcs_with_filters(self, mock_aws_client, mock_vpc_data):
        """Test VPC listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {
            "Vpcs": [mock_vpc_data]
        }

        filters = [{"Name": "is-default", "Values": ["true"]}]
        result = await list_vpcs(filters=filters)

        assert result["status"] == "success"
        mock_client.describe_vpcs.assert_called_once_with(Filters=filters)

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_vpcs_client_error(self, mock_aws_client):
        """Test VPC listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidVpcID", "Message": "Invalid VPC ID"}},
            operation_name="DescribeVpcs"
        )

        result = await list_vpcs()

        assert result["status"] == "error"
        assert result["error"] == "InvalidVpcID"


class TestGetDefaultVpc:
    """Tests for get_default_vpc function."""

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_get_default_vpc_success(self, mock_aws_client, mock_vpc_data):
        """Test successful default VPC retrieval."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {
            "Vpcs": [mock_vpc_data]
        }

        result = await get_default_vpc()

        assert result["status"] == "success"
        assert result["vpc"]["vpc_id"] == "vpc-12345678"
        assert result["vpc"]["is_default"] is True

        # Verify the correct filter was applied
        call_args = mock_client.describe_vpcs.call_args[1]
        assert call_args["Filters"] == [{"Name": "is-default", "Values": ["true"]}]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_get_default_vpc_not_found(self, mock_aws_client):
        """Test default VPC when none exists."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {"Vpcs": []}

        result = await get_default_vpc()

        assert result["status"] == "error"
        assert "No default VPC found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_get_default_vpc_client_error(self, mock_aws_client):
        """Test default VPC with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_vpcs.side_effect = ClientError(
            error_response={"Error": {"Code": "UnauthorizedOperation", "Message": "Not authorized"}},
            operation_name="DescribeVpcs"
        )

        result = await get_default_vpc()

        assert result["status"] == "error"
        assert result["error"] == "UnauthorizedOperation"


class TestFindSuitableSubnet:
    """Tests for find_suitable_subnet function."""

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_with_vpc_id(self, mock_aws_client, mock_subnet_data):
        """Test finding subnet with specific VPC ID."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        result = await find_suitable_subnet(vpc_id="vpc-12345678")

        assert result["status"] == "success"
        assert result["subnet"]["subnet_id"] == "subnet-12345678"
        assert result["vpc_id"] == "vpc-12345678"

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.get_default_vpc")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_without_vpc_id(self, mock_aws_client, mock_get_default_vpc, mock_subnet_data):
        """Test finding subnet without VPC ID (uses default VPC)."""
        mock_get_default_vpc.return_value = {
            "status": "success",
            "vpc": {"vpc_id": "vpc-12345678"}
        }
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        result = await find_suitable_subnet()

        assert result["status"] == "success"
        assert result["vpc_id"] == "vpc-12345678"
        mock_get_default_vpc.assert_called_once()

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.get_default_vpc")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_default_vpc_error(self, mock_get_default_vpc):
        """Test finding subnet when default VPC retrieval fails."""
        mock_get_default_vpc.return_value = {
            "status": "error",
            "message": "No default VPC found"
        }

        result = await find_suitable_subnet()

        assert result["status"] == "error"
        assert "No default VPC found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_with_az(self, mock_aws_client, mock_subnet_data):
        """Test finding subnet with specific availability zone."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        result = await find_suitable_subnet(
            vpc_id="vpc-12345678",
            availability_zone="us-east-1a"
        )

        assert result["status"] == "success"
        
        # Verify AZ filter was applied
        call_args = mock_client.describe_subnets.call_args[1]
        az_filter = next(f for f in call_args["Filters"] if f["Name"] == "availability-zone")
        assert az_filter["Values"] == ["us-east-1a"]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_require_public(self, mock_aws_client, mock_subnet_data):
        """Test finding public subnet."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }
        # Mock route table with IGW route
        mock_client.describe_route_tables.return_value = {
            "RouteTables": [{
                "Routes": [
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "GatewayId": "igw-12345678"
                    }
                ]
            }]
        }

        result = await find_suitable_subnet(
            vpc_id="vpc-12345678",
            require_public=True
        )

        assert result["status"] == "success"
        assert result["subnet"]["subnet_id"] == "subnet-12345678"

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_require_private(self, mock_aws_client, mock_subnet_data):
        """Test finding private subnet."""
        # Make subnet not auto-assign public IPs
        mock_subnet_data["MapPublicIpOnLaunch"] = False
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }
        # Mock route table without IGW route
        mock_client.describe_route_tables.return_value = {
            "RouteTables": [{
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.0.0.0/16",
                        "GatewayId": "local"
                    }
                ]
            }]
        }

        result = await find_suitable_subnet(
            vpc_id="vpc-12345678",
            require_public=False
        )

        assert result["status"] == "success"
        assert result["subnet"]["subnet_id"] == "subnet-12345678"

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_no_subnets(self, mock_aws_client):
        """Test finding subnet when none exist."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {"Subnets": []}

        result = await find_suitable_subnet(vpc_id="vpc-12345678")

        assert result["status"] == "error"
        assert "No available subnets found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_no_matching_type(self, mock_aws_client, mock_subnet_data):
        """Test finding subnet when none match public/private requirement."""
        # Make subnet public but require private
        mock_subnet_data["MapPublicIpOnLaunch"] = True
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }
        mock_client.describe_route_tables.return_value = {
            "RouteTables": [{
                "Routes": [
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "GatewayId": "igw-12345678"
                    }
                ]
            }]
        }

        result = await find_suitable_subnet(
            vpc_id="vpc-12345678",
            require_public=False
        )

        assert result["status"] == "error"
        assert "No suitable private subnets found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_find_suitable_subnet_multiple_subnets_sorted(self, mock_aws_client):
        """Test that multiple subnets are sorted by available IP count."""
        subnet1 = {
            "SubnetId": "subnet-11111111",
            "VpcId": "vpc-12345678",
            "CidrBlock": "10.0.1.0/24",
            "AvailabilityZone": "us-east-1a",
            "State": "available",
            "AvailableIpAddressCount": 100,
            "MapPublicIpOnLaunch": False,
            "DefaultForAz": False,
            "Tags": []
        }
        subnet2 = {
            "SubnetId": "subnet-22222222",
            "VpcId": "vpc-12345678",
            "CidrBlock": "10.0.2.0/24",
            "AvailabilityZone": "us-east-1b",
            "State": "available",
            "AvailableIpAddressCount": 250,
            "MapPublicIpOnLaunch": False,
            "DefaultForAz": False,
            "Tags": []
        }
        
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [subnet1, subnet2]  # subnet1 has fewer IPs
        }

        result = await find_suitable_subnet(vpc_id="vpc-12345678")

        assert result["status"] == "success"
        # Should return subnet2 because it has more available IPs
        assert result["subnet"]["subnet_id"] == "subnet-22222222"
        assert result["subnet"]["available_ip_address_count"] == 250
        assert len(result["all_suitable_subnets"]) == 2


class TestDeleteVpc:
    """Tests for delete_vpc function."""

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.validate_vpc_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_delete_vpc_success(self, mock_aws_client, mock_validate):
        """Test successful VPC deletion."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await delete_vpc("vpc-12345678")

        assert result["status"] == "success"
        assert "Successfully deleted VPC" in result["message"]
        assert result["vpc_id"] == "vpc-12345678"
        mock_client.delete_vpc.assert_called_once_with(VpcId="vpc-12345678")

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.validate_vpc_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_delete_vpc_client_error(self, mock_aws_client, mock_validate):
        """Test VPC deletion with client error."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.delete_vpc.side_effect = ClientError(
            error_response={"Error": {"Code": "DependencyViolation", "Message": "VPC has dependencies"}},
            operation_name="DeleteVpc"
        )

        result = await delete_vpc("vpc-12345678")

        assert result["status"] == "error"
        assert result["error"] == "DependencyViolation"


class TestListSubnets:
    """Tests for list_subnets function."""

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_subnets_success(self, mock_aws_client, mock_subnet_data):
        """Test successful subnet listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        result = await list_subnets()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["subnets"]) == 1
        assert result["subnets"][0]["subnet_id"] == "subnet-12345678"
        assert result["subnets"][0]["vpc_id"] == "vpc-12345678"

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_subnets_with_ids(self, mock_aws_client, mock_subnet_data):
        """Test subnet listing with specific IDs."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        subnet_ids = ["subnet-12345678"]
        result = await list_subnets(subnet_ids=subnet_ids)

        assert result["status"] == "success"
        mock_client.describe_subnets.assert_called_once_with(SubnetIds=subnet_ids)

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_subnets_with_filters(self, mock_aws_client, mock_subnet_data):
        """Test subnet listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.return_value = {
            "Subnets": [mock_subnet_data]
        }

        filters = [{"Name": "vpc-id", "Values": ["vpc-12345678"]}]
        result = await list_subnets(filters=filters)

        assert result["status"] == "success"
        mock_client.describe_subnets.assert_called_once_with(Filters=filters)

    @patch("awslabs.ec2_mcp_server.modules.vpc_management.aws_client")
    @pytest.mark.asyncio
    async def test_list_subnets_client_error(self, mock_aws_client):
        """Test subnet listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidSubnetID", "Message": "Invalid subnet ID"}},
            operation_name="DescribeSubnets"
        )

        result = await list_subnets()

        assert result["status"] == "error"
        assert result["error"] == "InvalidSubnetID"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_vpcs",
            "get_default_vpc",
            "find_suitable_subnet",
            "delete_vpc",
            "list_subnets"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls