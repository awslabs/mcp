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


"""Unit tests for validation tools."""

import json
from typing import Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_ip_addresses() -> list[str]:  # Added return type
    """Mock IP addresses fixture with realistic test data."""
    return [
        "10.0.0.1",
        "192.168.1.10",
        "172.16.0.5",
        "8.8.8.8",
        "2001:db8::1",  # IPv6 address
    ]


@pytest.fixture
def mock_cidr_blocks() -> list[str]:  # Added return type
    """Mock CIDR blocks fixture with realistic test data."""
    return [
        "10.0.0.0/24",
        "192.168.1.0/24",
        "172.16.0.0/16",
        "10.1.0.0/8",
        "2001:db8::/32",  # IPv6 CIDR
    ]


@pytest.fixture
def mock_aws_client():
    """Mock AWS client fixture."""
    client = Mock()
    return client


@pytest.fixture
def mock_get_aws_client() -> Generator:  # Added return type
    """Mock the get_aws_client function."""

    def _mock_client(service, region=None):
        return Mock()

    with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=_mock_client) as mock:
        yield mock


class TestValidationTools:
    """Test validation and utility tools."""

    @pytest.mark.asyncio
    async def test_validate_ip_cidr_validate_ip(self, mock_get_aws_client: Generator) -> None:  # Added type
        """Test IP validation functionality."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        result = await validate_ip_cidr("validate_ip", ip="10.0.0.1")
        response = json.loads(result)

        assert response["success"] is True  # noqa: S101
        assert response["operation"] == "validate_ip"
        assert response["ip_address"] == "10.0.0.1"
        assert response["version"] == 4
        assert response["is_private"] is True

    @pytest.mark.asyncio
    async def test_validate_ip_cidr_validate_cidr(self, mock_get_aws_client: Generator) -> None:  # Added type
        """Test CIDR validation functionality."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        result = await validate_ip_cidr("validate_cidr", cidr="10.0.0.0/24")
        response = json.loads(result)

        assert response["success"] is True  # noqa: S101
        assert response["operation"] == "validate_cidr"
        assert response["network"] == "10.0.0.0/24"
        assert response["num_addresses"] == 256

    @pytest.mark.asyncio
    async def test_validate_ip_cidr_invalid_operation(self, mock_get_aws_client: Generator) -> None:  # Added type
        """Test invalid operation handling."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        result = await validate_ip_cidr("invalid_operation")
        response = json.loads(result)

        assert response["success"] is False  # noqa: S101
        assert "Invalid operation" in response["error"]
        assert "valid_operations" in response

    @pytest.mark.asyncio
    async def test_validate_cloudwan_policy(self, mock_get_aws_client: Generator) -> None:  # Added type
        """Test CloudWAN policy validation."""
        from awslabs.cloudwan_mcp_server.server import validate_cloudwan_policy

        test_policy = {"version": "2021.12", "core-network-configuration": {"asn-ranges": ["64512-65534"]}}

        result = await validate_cloudwan_policy(test_policy)
        response = json.loads(result)

        assert response["success"] is True  # noqa: S101
        assert response["overall_status"] == "valid"
        assert response["policy_version"] == "2021.12"

    @pytest.mark.asyncio
    async def test_ip_validation_with_fixtures(self, mock_ip_addresses: list[str], mock_get_aws_client: Generator) -> None:  # Added types
        """Test IP validation using fixture data."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        for ip in mock_ip_addresses[:3]:  # Test first 3 IPs
            result = await validate_ip_cidr("validate_ip", ip=ip)
            response = json.loads(result)

            assert response["success"] is True  # noqa: S101
            assert response["ip_address"] == ip

    @pytest.mark.asyncio
    async def test_cidr_validation_with_fixtures(self, mock_cidr_blocks: list[str], mock_get_aws_client: Generator) -> None:  # Added types
        """Test CIDR validation using fixture data."""
        from awslabs.cloudwan_mcp_server.server import validate_ip_cidr

        for cidr in mock_cidr_blocks[:3]:  # Test first 3 CIDRs
            result = await validate_ip_cidr("validate_cidr", cidr=cidr)
            response = json.loads(result)

            assert response["success"] is True  # noqa: S101
            assert response["network"] == cidr

    @pytest.mark.asyncio
    async def test_manage_tgw_routes_edge_cases(self, mock_aws_client) -> None:
        """Test TGW route management edge cases."""
        from awslabs.cloudwan_mcp_server.server import manage_tgw_routes

        # Test invalid CIDR
        result = await manage_tgw_routes("create", "rtb-123", "invalid_cidr")
        response = json.loads(result)
        assert response["success"] is False

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_error(self, mock_aws_client) -> None:
        """Test TGW peer analysis error handling."""
        from awslabs.cloudwan_mcp_server.server import analyze_tgw_peers

        mock_aws_client.describe_transit_gateway_peering_attachments.side_effect = Exception("API error")
        result = await analyze_tgw_peers("invalid-peer")
        response = json.loads(result)
        assert response["success"] is False
