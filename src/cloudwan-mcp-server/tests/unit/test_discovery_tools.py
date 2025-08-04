"""Unit tests for network discovery tools."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import json
import os

@pytest.fixture
def mock_networkmanager_client():
    """Mock NetworkManager client with realistic responses."""
    client = Mock()
    
    # Mock successful core networks response
    client.list_core_networks.return_value = {
        "CoreNetworks": [
            {
                "CoreNetworkId": "core-network-1234567890abcdef0",
                "GlobalNetworkId": "global-network-1234567890abcdef0",
                "State": "AVAILABLE",
                "Description": "Test core network",
                "CreatedAt": "2023-01-01T00:00:00Z"
            }
        ]
    }
    
    # Mock global networks response
    client.describe_global_networks.return_value = {
        "GlobalNetworks": [
            {
                "GlobalNetworkId": "global-network-1234567890abcdef0",
                "State": "AVAILABLE",
                "Description": "Test global network",
                "CreatedAt": "2023-01-01T00:00:00Z"
            }
        ]
    }
    
    return client

@pytest.fixture
def mock_ec2_client():
    """Mock EC2 client with realistic VPC responses."""
    client = Mock()
    
    # Mock VPC response
    client.describe_vpcs.return_value = {
        "Vpcs": [
            {
                "VpcId": "vpc-12345678",
                "State": "available",
                "CidrBlock": "10.0.0.0/16",
                "IsDefault": False,
                "Tags": [{"Key": "Name", "Value": "test-vpc"}]
            }
        ]
    }
    
    return client

@pytest.fixture
def mock_ip_addresses():
    """Mock IP address fixture."""
    return ["10.0.0.1", "10.0.0.2"]

@pytest.fixture
def mock_cidr_blocks():
    """Mock CIDR blocks fixture."""
    return ["10.0.0.0/24", "10.0.1.0/24"]

@pytest.fixture
def mock_aws_client():
    """Mock AWS client fixture."""
    client = Mock()
    return client

@pytest.fixture
def mock_get_aws_client():
    """Mock the get_aws_client function."""
    def _mock_client(service, region=None):
        if service == "networkmanager":
            return mock_networkmanager_client()
        elif service == "ec2":
            return mock_ec2_client()
        else:
            return Mock()
    
    with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=_mock_client) as mock:
        yield mock

class TestDiscoveryTools:
    """Test network discovery tools."""
    
    @pytest.mark.asyncio
    async def test_list_core_networks_success(self, mock_get_aws_client):
        """Test successful core network listing."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks

        result = await list_core_networks("us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["region"] == "us-east-1"
        assert response["total_count"] == 1
        assert len(response["core_networks"]) == 1

        # Verify core network details
        core_network = response["core_networks"][0]
        assert core_network["CoreNetworkId"] == "core-network-1234567890abcdef0"
        assert core_network["State"] == "AVAILABLE"

    @pytest.mark.asyncio
    async def test_list_core_networks_empty_response(self, mock_get_aws_client):
        """Test core network listing with empty response."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks

        # Override mock to return empty response
        mock_client = Mock()
        mock_client.list_core_networks.return_value = {"CoreNetworks": []}
        mock_get_aws_client.return_value = mock_client

        result = await list_core_networks("us-west-2")
        response = json.loads(result)

        assert response["success"] is True
        assert response["region"] == "us-west-2"
        assert response["message"] == "No CloudWAN core networks found in the specified region."
        assert response["core_networks"] == []

    @pytest.mark.asyncio
    async def test_discover_vpcs_success(self, mock_get_aws_client):
        """Test successful VPC discovery."""
        from awslabs.cloudwan_mcp_server.server import discover_vpcs

        result = await discover_vpcs("us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["region"] == "us-east-1"
        assert response["total_count"] == 1
        assert len(response["vpcs"]) == 1

        # Verify VPC details
        vpc = response["vpcs"][0]
        assert vpc["VpcId"] == "vpc-12345678"
        assert vpc["State"] == "available"

    @pytest.mark.asyncio
    async def test_discover_vpcs_edge_cases(self, mock_get_aws_client):
        """Test VPC discovery with edge cases."""
        from awslabs.cloudwan_mcp_server.server import discover_vpcs

        # Test empty VPC list
        mock_client = Mock()
        mock_client.describe_vpcs.return_value = {"Vpcs": []}
        mock_get_aws_client.return_value = mock_client

        result = await discover_vpcs("us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["total_count"] == 0
        assert response["vpcs"] == []

    @pytest.mark.asyncio
    async def test_discover_ip_details_validation(self):
        """Test IP details validation."""
        from awslabs.cloudwan_mcp_server.server import discover_ip_details

        # Test valid IP
        result = await discover_ip_details("10.0.0.1")
        response = json.loads(result)
        assert response["success"] is True
        assert response["ip_address"] == "10.0.0.1"
        assert response["ip_version"] == 4
        assert response["is_private"] is True

        # Test invalid IP
        result = await discover_ip_details("invalid_ip")
        response = json.loads(result)
        assert response["success"] is False
        assert "error" in response

    @pytest.mark.asyncio
    async def test_get_global_networks_error(self, mock_get_aws_client):
        """Test error handling in global networks tool."""
        from awslabs.cloudwan_mcp_server.server import get_global_networks
        from botocore.exceptions import ClientError

        # Mock client error
        mock_client = Mock()
        mock_client.describe_global_networks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "DescribeGlobalNetworks"
        )
        mock_get_aws_client.return_value = mock_client

        result = await get_global_networks("us-east-1")
        response = json.loads(result)

        assert response["success"] is False
        assert "get_global_networks failed" in response["error"]
        assert response["error_code"] == "AccessDenied"

    @pytest.mark.asyncio
    async def test_list_network_function_groups(self, mock_get_aws_client):
        """Test NFG listing tool."""
        from awslabs.cloudwan_mcp_server.server import list_network_function_groups
        
        result = await list_network_function_groups("us-east-1")
        response = json.loads(result)
        
        assert response["success"] is True
        assert len(response["network_function_groups"]) == 2
        
        # Verify NFG details
        nfg = response["network_function_groups"][0]
        assert nfg["name"] == "production-nfg"
        assert nfg["status"] == "available"

    @pytest.mark.asyncio
    async def test_discover_vpcs_default_region(self, mock_get_aws_client):
        """Test VPC discovery with default region from environment."""
        from awslabs.cloudwan_mcp_server.server import discover_vpcs
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-west-1'}):
            result = await discover_vpcs()
            response = json.loads(result)
            
            assert response["success"] is True
            assert response["region"] == "eu-west-1"

    @pytest.mark.asyncio
    async def test_standard_error_handling_discovery_tools(self, mock_get_aws_client):
        """Test standard error handling across discovery tools."""
        from awslabs.cloudwan_mcp_server.server import (
            list_core_networks, discover_vpcs, get_global_networks
        )
        
        # Mock generic exception
        mock_client = Mock()
        mock_client.list_core_networks.side_effect = Exception("Generic error")
        mock_client.describe_vpcs.side_effect = Exception("Generic error")
        mock_client.describe_global_networks.side_effect = Exception("Generic error")
        mock_get_aws_client.return_value = mock_client
        
        tools_and_args = [
            (list_core_networks, ["us-east-1"]),
            (discover_vpcs, ["us-east-1"]),
            (get_global_networks, ["us-east-1"])
        ]
        
        for tool_func, args in tools_and_args:
            result = await tool_func(*args)
            response = json.loads(result)
            
            assert response["success"] is False
            assert "error" in response
            assert "Generic error" in response["error"]