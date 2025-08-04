# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for CloudWAN network analysis tools."""

import json
import os
import pytest
from unittest.mock import patch, Mock

from awslabs.cloudwan_mcp_server.server import (
    discover_vpcs,
    discover_ip_details,
    validate_ip_cidr,
    trace_network_path,
    list_network_function_groups,
    list_core_networks,
    get_global_networks
)


@pytest.fixture
def mock_ip_addresses():
    """Mock IP addresses fixture with realistic test data."""
    return {
        "valid_ipv4": "10.0.1.100",
        "valid_ipv6": "2001:4860:4860::8888",
        "public_ipv4": "8.8.8.8",
        "loopback": "127.0.0.1",
        "multicast": "224.0.0.1",
        "invalid": "invalid_ip"
    }


@pytest.fixture
def mock_cidr_blocks():
    """Mock CIDR blocks fixture with realistic test data."""
    return {
        "valid_ipv4": "10.0.0.0/16",
        "single_host": "192.168.1.100/32",
        "invalid": "invalid_cidr"
    }


@pytest.fixture
def mock_aws_client():
    """Mock AWS client fixture."""
    client = Mock()
    
    # Mock EC2 responses
    client.describe_vpcs.return_value = {
        "Vpcs": [
            {
                "VpcId": "vpc-1234567890abcdef0",
                "State": "available",
                "CidrBlock": "10.0.0.0/16",
                "IsDefault": False,
                "Tags": [{"Key": "Name", "Value": "test-vpc"}]
            }
        ]
    }
    
    # Mock NetworkManager responses
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
    
    client.list_network_function_groups.return_value = {
        "NetworkFunctionGroups": [
            {
                "Name": "production-nfg",
                "Status": "available",
                "CreatedAt": "2023-01-01T00:00:00Z"
            },
            {
                "Name": "staging-nfg",
                "Status": "available",
                "CreatedAt": "2023-01-01T00:00:00Z"
            }
        ]
    }
    
    return client


@pytest.fixture
def mock_get_aws_client(mock_aws_client):
    """Mock the get_aws_client function."""
    with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', return_value=mock_aws_client) as mock:
        yield mock


class TestNetworkDiscovery:
    """Test network discovery and analysis tools."""

    @pytest.mark.asyncio
    async def test_discover_vpcs_success(self, mock_get_aws_client):
        """Test successful VPC discovery."""
        result = await discover_vpcs("us-east-1")
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["region"] == "us-east-1"
        assert response["total_count"] == 1
        assert "vpcs" in response
        
        vpc = response["vpcs"][0]
        assert vpc["VpcId"] == "vpc-1234567890abcdef0"
        assert vpc["State"] == "available"
        assert vpc["CidrBlock"] == "10.0.0.0/16"

    @pytest.mark.asyncio
    async def test_discover_vpcs_empty_result(self, mock_get_aws_client):
        """Test VPC discovery with no VPCs found."""
        mock_get_aws_client.return_value.describe_vpcs.return_value = {"Vpcs": []}
        
        result = await discover_vpcs("us-west-2")
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["total_count"] == 0
        assert response["vpcs"] == []

    @pytest.mark.asyncio
    async def test_list_network_function_groups(self, mock_get_aws_client):
        """Test NFG listing tool."""
        from awslabs.cloudwan_mcp_server.server import list_network_function_groups
        
        result = await list_network_function_groups("us-east-1")
        response = json.loads(result)
        
        assert response["success"] is True
        assert "network_function_groups" in response
        assert len(response["network_function_groups"]) == 2
        assert response["network_function_groups"][0]["status"] == "available"

    @pytest.mark.asyncio
    async def test_discover_ip_details_valid_ipv4(self, mock_ip_addresses):
        """Test IP details discovery with valid IPv4."""
        result = await discover_ip_details(mock_ip_addresses["valid_ipv4"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["ip_address"] == "10.0.1.100"
        assert response["ip_version"] == 4
        assert response["is_private"] is True
        assert response["is_multicast"] is False
        assert response["is_loopback"] is False

    @pytest.mark.asyncio
    async def test_discover_ip_details_valid_ipv6(self, mock_ip_addresses):
        """Test IP details discovery with valid IPv6."""
        result = await discover_ip_details(mock_ip_addresses["valid_ipv6"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["ip_address"] == "2001:4860:4860::8888"
        assert response["ip_version"] == 6
        assert response["is_private"] is False
        assert response["is_multicast"] is False
        assert response["is_loopback"] is False

    @pytest.mark.asyncio
    async def test_discover_ip_details_loopback(self, mock_ip_addresses):
        """Test IP details discovery with loopback address."""
        result = await discover_ip_details(mock_ip_addresses["loopback"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["is_loopback"] is True
        assert response["is_private"] is True

    @pytest.mark.asyncio
    async def test_discover_ip_details_multicast(self, mock_ip_addresses):
        """Test IP details discovery with multicast address."""
        result = await discover_ip_details(mock_ip_addresses["multicast"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["is_multicast"] is True

    @pytest.mark.asyncio
    async def test_discover_ip_details_validation(self, mock_get_aws_client):
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
    async def test_discover_ip_details_invalid_ip(self, mock_ip_addresses):
        """Test IP details discovery with invalid IP."""
        result = await discover_ip_details(mock_ip_addresses["invalid"])
        response = json.loads(result)
        
        assert response["success"] is False
        assert "discover_ip_details failed" in response["error"]

    @pytest.mark.asyncio
    async def test_trace_network_path_success(self, mock_ip_addresses):
        """Test successful network path tracing."""
        source = mock_ip_addresses["valid_ipv4"]
        destination = mock_ip_addresses["public_ipv4"]
        
        result = await trace_network_path(source, destination, "us-east-1")
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["source_ip"] == source
        assert response["destination_ip"] == destination
        assert response["region"] == "us-east-1"
        assert response["total_hops"] == 4
        assert response["status"] == "reachable"
        
        # Verify path trace structure
        assert "path_trace" in response
        assert len(response["path_trace"]) == 4
        
        # Check first hop
        first_hop = response["path_trace"][0]
        assert first_hop["hop"] == 1
        assert first_hop["ip"] == source
        assert first_hop["description"] == "Source endpoint"

    @pytest.mark.asyncio
    async def test_trace_network_path_invalid_source(self, mock_ip_addresses):
        """Test network path tracing with invalid source IP."""
        result = await trace_network_path(
            mock_ip_addresses["invalid"], 
            mock_ip_addresses["valid_ipv4"]
        )
        response = json.loads(result)
        
        assert response["success"] is False
        assert "trace_network_path failed" in response["error"]

    @pytest.mark.asyncio
    async def test_trace_network_path_invalid_destination(self, mock_ip_addresses):
        """Test network path tracing with invalid destination IP."""
        result = await trace_network_path(
            mock_ip_addresses["valid_ipv4"],
            mock_ip_addresses["invalid"]
        )
        response = json.loads(result)
        
        assert response["success"] is False
        assert "trace_network_path failed" in response["error"]

    @pytest.mark.asyncio
    async def test_discover_vpcs_default_region(self, mock_get_aws_client):
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-west-1'}):
            result = await discover_vpcs()
            response = json.loads(result)
            
            assert response["success"] is True
            assert response["region"] == "eu-west-1"

    @pytest.mark.asyncio
    async def test_standard_error_handling_discovery_tools(self, mock_get_aws_client):
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


class TestIPCIDRValidation:
    """Test IP and CIDR validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_ip_success(self, mock_ip_addresses):
        """Test successful IP validation."""
        result = await validate_ip_cidr("validate_ip", ip=mock_ip_addresses["valid_ipv4"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["operation"] == "validate_ip"
        assert response["ip_address"] == "10.0.1.100"
        assert response["version"] == 4
        assert response["is_private"] is True

    @pytest.mark.asyncio
    async def test_validate_ip_ipv6(self, mock_ip_addresses):
        """Test IPv6 validation."""
        result = await validate_ip_cidr("validate_ip", ip=mock_ip_addresses["valid_ipv6"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["version"] == 6
        assert response["is_private"] is False

    @pytest.mark.asyncio
    async def test_validate_cidr_success(self, mock_cidr_blocks):
        """Test successful CIDR validation."""
        result = await validate_ip_cidr("validate_cidr", cidr=mock_cidr_blocks["valid_ipv4"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["operation"] == "validate_cidr"
        assert response["network"] == "10.0.0.0/16"
        assert response["network_address"] == "10.0.0.0"
        assert response["broadcast_address"] == "10.0.255.255"
        assert response["num_addresses"] == 65536
        assert response["is_private"] is True

    @pytest.mark.asyncio
    async def test_validate_cidr_single_host(self, mock_cidr_blocks):
        """Test CIDR validation with single host."""
        result = await validate_ip_cidr("validate_cidr", cidr=mock_cidr_blocks["single_host"])
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["num_addresses"] == 1

    @pytest.mark.asyncio
    async def test_validate_ip_invalid_operation(self):
        """Test validation with invalid operation."""
        result = await validate_ip_cidr("invalid_operation")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "Invalid operation or missing parameters" in response["error"]
        assert "valid_operations" in response

    @pytest.mark.asyncio
    async def test_validate_ip_missing_parameter(self):
        """Test IP validation without IP parameter."""
        result = await validate_ip_cidr("validate_ip")
        response = json.loads(result)
        
        assert response["success"] is False

    @pytest.mark.asyncio
    async def test_validate_cidr_missing_parameter(self):
        """Test CIDR validation without CIDR parameter."""
        result = await validate_ip_cidr("validate_cidr")
        response = json.loads(result)
        
        assert response["success"] is False

    @pytest.mark.asyncio
    async def test_validate_invalid_ip(self, mock_ip_addresses):
        """Test validation with invalid IP address."""
        result = await validate_ip_cidr("validate_ip", ip=mock_ip_addresses["invalid"])
        response = json.loads(result)
        
        assert response["success"] is False
        assert "validate_ip_cidr failed" in response["error"]

    @pytest.mark.asyncio
    async def test_validate_invalid_cidr(self, mock_cidr_blocks):
        """Test validation with invalid CIDR block."""
        result = await validate_ip_cidr("validate_cidr", cidr=mock_cidr_blocks["invalid"])
        response = json.loads(result)
        
        assert response["success"] is False
        assert "validate_ip_cidr failed" in response["error"]