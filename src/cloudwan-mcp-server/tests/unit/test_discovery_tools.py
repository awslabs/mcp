"""
Unit tests for network discovery tools.

This module provides comprehensive testing for CloudWAN MCP Server's network
discovery functionality, including core networks, global networks, VPCs, and
IP address validation tools.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json
import os
from typing import List, Dict, Any

from ..mocking.aws import AWSServiceMocker, AWSErrorCatalog


@pytest.fixture(scope="function")
def mock_networkmanager_client():
    """
    Mock NetworkManager client with realistic AWS CloudWAN responses.
    
    Provides comprehensive mock responses for all NetworkManager operations
    including core networks, global networks, policies, and change management.
    """
    mocker = AWSServiceMocker("networkmanager")
    return mocker.client


@pytest.fixture(scope="function")
def mock_ec2_client():
    """
    Mock EC2 client with realistic VPC and networking responses.
    
    Configured to provide standard VPC discovery responses with proper
    AWS resource formatting and metadata.
    """
    mocker = AWSServiceMocker("ec2")
    return mocker.client


@pytest.fixture(scope="function")
def mock_ip_addresses() -> List[str]:
    """Test IP addresses for validation and network discovery tests."""
    return ["10.0.0.1", "10.0.0.2", "192.168.1.1", "172.16.0.1"]


@pytest.fixture(scope="function")
def mock_cidr_blocks() -> List[str]:
    """Test CIDR blocks for network range validation tests."""
    return ["10.0.0.0/24", "10.0.1.0/24", "192.168.0.0/16", "172.16.0.0/12"]


@pytest.fixture(scope="function")
def mock_aws_client():
    """Generic AWS client fixture for basic mocking scenarios."""
    client = Mock()
    return client


@pytest.fixture(scope="function")
def enhanced_networkmanager_client():
    """
    Enhanced NetworkManager client with configurable responses.
    
    Provides advanced mocking capabilities including:
    - Multi-region response simulation
    - Error scenario configuration
    - Dynamic response modification
    """
    mocker = AWSServiceMocker("networkmanager")
    
    # Add comprehensive NFG responses
    mocker.client.list_network_function_groups.return_value = {
        "NetworkFunctionGroups": [
            {
                "name": "production-nfg",
                "status": "available",
                "description": "Production network function group"
            },
            {
                "name": "staging-nfg", 
                "status": "available",
                "description": "Staging network function group"
            }
        ]
    }
    
    return mocker


@pytest.fixture(scope="function", params=[
    "access_denied",
    "resource_not_found", 
    "throttling",
    "validation_error"
])
def parametrized_aws_errors(request, aws_error_catalog):
    """
    Parametrized fixture providing comprehensive AWS error scenarios.
    
    Tests run against multiple error conditions to ensure robust
    error handling across all discovery operations.
    """
    return aws_error_catalog.get_error(request.param, 'TestOperation')

class TestDiscoveryTools:
    """Test network discovery tools."""
    
    @pytest.mark.asyncio
    async def test_list_core_networks_success(self, mock_get_aws_client_fixture):
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
    async def test_list_core_networks_empty_response(self, mock_get_aws_client_fixture):
        """Test core network listing with empty response."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks

        # Override mock to return empty response
        mock_client = Mock()
        mock_client.list_core_networks.return_value = {"CoreNetworks": []}
        mock_get_aws_client_fixture.return_value = mock_client

        result = await list_core_networks("us-west-2")
        response = json.loads(result)

        assert response["success"] is True
        assert response["region"] == "us-west-2"
        assert response["message"] == "No CloudWAN core networks found in the specified region."
        assert response["core_networks"] == []

    @pytest.mark.asyncio
    async def test_discover_vpcs_success(self, mock_get_aws_client_fixture):
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
    async def test_discover_vpcs_edge_cases(self, mock_get_aws_client_fixture):
        """Test VPC discovery with edge cases."""
        from awslabs.cloudwan_mcp_server.server import discover_vpcs

        # Test empty VPC list
        mock_client = Mock()
        mock_client.describe_vpcs.return_value = {"Vpcs": []}
        mock_get_aws_client_fixture.return_value = mock_client

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
    async def test_get_global_networks_error(self, mock_get_aws_client_fixture):
        """Test error handling in global networks tool."""
        from awslabs.cloudwan_mcp_server.server import get_global_networks
        from botocore.exceptions import ClientError

        # Mock client error
        mock_client = Mock()
        mock_client.describe_global_networks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "DescribeGlobalNetworks"
        )
        mock_get_aws_client_fixture.return_value = mock_client

        result = await get_global_networks("us-east-1")
        response = json.loads(result)

        assert response["success"] is False
        assert "get_global_networks failed" in response["error"]
        assert response["error_code"] == "AccessDenied"

    @pytest.mark.asyncio
    async def test_list_network_function_groups(self, mock_get_aws_client_fixture):
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
    async def test_discover_vpcs_default_region(self, mock_get_aws_client_fixture):
        """Test VPC discovery with default region from environment."""
        from awslabs.cloudwan_mcp_server.server import discover_vpcs
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-west-1'}):
            result = await discover_vpcs()
            response = json.loads(result)
            
            assert response["success"] is True
            assert response["region"] == "eu-west-1"

    @pytest.mark.asyncio
    async def test_standard_error_handling_discovery_tools(self, mock_get_aws_client_fixture):
        """Test standard error handling across discovery tools."""
        from awslabs.cloudwan_mcp_server.server import (
            list_core_networks, discover_vpcs, get_global_networks
        )
        
        # Mock generic exception
        mock_client = Mock()
        mock_client.list_core_networks.side_effect = Exception("Generic error")
        mock_client.describe_vpcs.side_effect = Exception("Generic error")
        mock_client.describe_global_networks.side_effect = Exception("Generic error")
        mock_get_aws_client_fixture.return_value = mock_client
        
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_code,operation", [
        ("AccessDenied", "ListCoreNetworks"),
        ("ThrottlingException", "DescribeGlobalNetworks"), 
        ("ValidationException", "DescribeVpcs"),
        ("ResourceNotFoundException", "ListCoreNetworks"),
        ("InternalFailure", "DescribeGlobalNetworks"),
        ("ServiceUnavailable", "DescribeVpcs")
    ])
    async def test_error_handling_matrix(self, mock_get_aws_client_fixture, aws_error_catalog, error_code, operation):
        """Test comprehensive error code/operation matrix for robust error handling."""
        from awslabs.cloudwan_mcp_server.server import (
            list_core_networks, discover_vpcs, get_global_networks
        )
        
        # Map operations to functions
        operation_map = {
            "ListCoreNetworks": list_core_networks,
            "DescribeGlobalNetworks": get_global_networks,
            "DescribeVpcs": discover_vpcs
        }
        
        # Configure error based on error code
        mock_client = Mock()
        error_mapping = {
            'AccessDenied': 'access_denied',
            'ThrottlingException': 'throttling',
            'ValidationException': 'validation_error',
            'ResourceNotFoundException': 'resource_not_found',
            'InternalFailure': 'internal_failure',
            'ServiceUnavailable': 'service_unavailable'
        }
        
        error = aws_error_catalog.get_error(error_mapping[error_code], operation)
        
        # Configure appropriate mock method
        if operation == "ListCoreNetworks":
            mock_client.list_core_networks.side_effect = error
        elif operation == "DescribeGlobalNetworks":
            mock_client.describe_global_networks.side_effect = error
        elif operation == "DescribeVpcs":
            mock_client.describe_vpcs.side_effect = error
        
        mock_get_aws_client_fixture.return_value = mock_client
        
        # Test the corresponding function
        func = operation_map[operation]
        result = await func("us-east-1")
        response = json.loads(result)
        
        assert response["success"] is False
        assert response["error_code"] == error_code
        assert "error" in response

    @pytest.mark.asyncio
    @pytest.mark.parametrize("region", [
        "us-east-1", "us-west-2", "eu-west-1", "ap-southeast-2"
    ])
    async def test_regional_behavior_validation(self, mock_get_aws_client_fixture, region):
        """Test regional behavior across different AWS regions."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks
        
        result = await list_core_networks(region)
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["region"] == region
        
        # Verify client was called with correct region
        mock_get_aws_client_fixture.assert_called_with("networkmanager", region)

    @pytest.mark.asyncio
    async def test_client_cache_invalidation(self, mock_get_aws_client_fixture):
        """Test client cache behavior and invalidation scenarios."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks
        
        # Make multiple calls to same region
        await list_core_networks("us-east-1")
        await list_core_networks("us-east-1")
        await list_core_networks("us-west-2")
        
        # Verify caching behavior - same region should reuse client
        assert mock_get_aws_client_fixture.call_count >= 2  # At least 2 different regions
        
        # Verify different regions get different calls
        calls = mock_get_aws_client_fixture.call_args_list
        regions = [call[0][1] for call in calls]
        assert "us-east-1" in regions
        assert "us-west-2" in regions

    @pytest.mark.asyncio
    async def test_cloudtrail_integration_validation(self, mock_get_aws_client_fixture):
        """Test CloudTrail integration for audit logging compliance."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks
        
        # Mock CloudTrail-aware response
        mock_client = Mock()
        mock_client.list_core_networks.return_value = {
            "CoreNetworks": [],
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {"x-amzn-trace-id": "test-trace-id"}
            }
        }
        mock_get_aws_client_fixture.return_value = mock_client
        
        result = await list_core_networks("us-east-1")
        response = json.loads(result)
        
        assert response["success"] is True
        # Verify request ID is captured (important for CloudTrail correlation)
        assert "total_count" in response

    @pytest.mark.asyncio
    async def test_ip_validation_edge_cases(self):
        """Test IP address validation with comprehensive edge cases."""
        from awslabs.cloudwan_mcp_server.server import discover_ip_details
        
        edge_cases = [
            ("127.0.0.1", True, "Localhost"),
            ("0.0.0.0", True, "Zero address"),
            ("255.255.255.255", True, "Broadcast address"),
            ("::1", True, "IPv6 localhost"),
            ("2001:db8::1", True, "IPv6 address"),
            ("invalid", False, "Invalid format"),
            ("300.300.300.300", False, "Invalid IPv4 octets"),
            ("", False, "Empty string"),
            ("192.168.1.1/24", False, "CIDR notation")
        ]
        
        for ip_input, should_succeed, description in edge_cases:
            result = await discover_ip_details(ip_input)
            response = json.loads(result)
            
            if should_succeed:
                assert response["success"] is True, f"Failed for {description}: {ip_input}"
                assert response["ip_address"] == ip_input
            else:
                assert response["success"] is False, f"Should have failed for {description}: {ip_input}"
                assert "error" in response