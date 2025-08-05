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

"""Individual CloudWAN API operation tests following AWS Labs patterns."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    analyze_network_function_group,
    analyze_segment_routes,
    analyze_tgw_peers,
    analyze_tgw_routes,
    discover_vpcs,
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
    list_network_function_groups,
    manage_tgw_routes,
    trace_network_path,
    validate_cloudwan_policy,
    validate_ip_cidr,
)


class TestListCoreNetworksOperation:
    """Test list_core_networks operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_core_networks_success_empty(self) -> None:
        """Test list_core_networks with empty result."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_get_client.return_value = mock_client

            result = await list_core_networks()

            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert "message" in parsed
            assert parsed["core_networks"] == []
            assert "region" in parsed
            mock_client.list_core_networks.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_core_networks_success_with_data(self) -> None:
        """Test list_core_networks with sample core networks."""
        sample_networks = [
            {
                "CoreNetworkId": "core-network-01234567890abcdef",
                "GlobalNetworkId": "global-network-01234567890abcdef",
                "State": "AVAILABLE",
                "CreatedAt": datetime(2024, 1, 15, 10, 30, 45),
                "Description": "Production core network",
            },
            {
                "CoreNetworkId": "core-network-fedcba0987654321",
                "GlobalNetworkId": "global-network-fedcba0987654321",
                "State": "AVAILABLE",
                "CreatedAt": datetime(2024, 1, 16, 11, 45, 30),
                "Description": "Development core network",
            },
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": sample_networks}
            mock_get_client.return_value = mock_client

            result = await list_core_networks(region="us-west-2")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 2
            assert len(parsed["core_networks"]) == 2
            assert parsed["region"] == "us-west-2"
            assert parsed["core_networks"][0]["CoreNetworkId"] == "core-network-01234567890abcdef"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_core_networks_client_error(self) -> None:
        """Test list_core_networks with AWS ClientError."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "User not authorized"}}, "ListCoreNetworks"
            )
            mock_get_client.return_value = mock_client

            result = await list_core_networks()

            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "User not authorized" in parsed["error"]
            assert parsed["error_code"] == "AccessDenied"


class TestGetGlobalNetworksOperation:
    """Test get_global_networks operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_global_networks_success(self) -> None:
        """Test get_global_networks with successful response."""
        sample_networks = [
            {
                "GlobalNetworkId": "global-network-01234567890abcdef",
                "State": "AVAILABLE",
                "CreatedAt": datetime(2024, 1, 15, 10, 30, 45),
                "Description": "Main global network",
            }
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.return_value = {"GlobalNetworks": sample_networks}
            mock_get_client.return_value = mock_client

            result = await get_global_networks(region="eu-west-1")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 1
            assert parsed["region"] == "eu-west-1"
            assert len(parsed["global_networks"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_global_networks_empty_result(self) -> None:
        """Test get_global_networks with no global networks."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.return_value = {"GlobalNetworks": []}
            mock_get_client.return_value = mock_client

            result = await get_global_networks()

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 0
            assert parsed["global_networks"] == []


class TestGetCoreNetworkPolicyOperation:
    """Test get_core_network_policy operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_core_network_policy_success(self) -> None:
        """Test get_core_network_policy with successful response."""
        sample_policy = {
            "PolicyVersionId": "1",
            "PolicyDocument": json.dumps(
                {
                    "version": "2021.12",
                    "core-network-configuration": {
                        "asn-ranges": ["64512-64555"],
                        "edge-locations": [{"location": "us-east-1"}],
                    },
                }
            ),
            "Description": "Production network policy",
            "CreatedAt": datetime(2024, 1, 15, 10, 30, 45),
        }

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.return_value = {"CoreNetworkPolicy": sample_policy}
            mock_get_client.return_value = mock_client

            result = await get_core_network_policy("core-network-123", alias="LIVE")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["core_network_id"] == "core-network-123"
            assert parsed["alias"] == "LIVE"
            assert parsed["policy_version_id"] == "1"
            assert "policy_document" in parsed
            mock_client.get_core_network_policy.assert_called_once_with(CoreNetworkId="core-network-123", Alias="LIVE")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_core_network_policy_not_found(self) -> None:
        """Test get_core_network_policy with resource not found."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Core network not found"}},
                "GetCoreNetworkPolicy",
            )
            mock_get_client.return_value = mock_client

            result = await get_core_network_policy("invalid-network")

            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "Core network not found" in parsed["error"]
            assert parsed["error_code"] == "ResourceNotFoundException"


class TestDiscoverVPCsOperation:
    """Test discover_vpcs operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_discover_vpcs_success(self) -> None:
        """Test discover_vpcs with multiple VPCs."""
        sample_vpcs = [
            {
                "VpcId": "vpc-01234567890abcdef0",
                "State": "available",
                "CidrBlock": "10.0.0.0/16",
                "Tags": [{"Key": "Name", "Value": "Production VPC"}],
            },
            {
                "VpcId": "vpc-fedcba0987654321",
                "State": "available",
                "CidrBlock": "172.16.0.0/12",
                "Tags": [{"Key": "Name", "Value": "Development VPC"}],
            },
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_vpcs.return_value = {"Vpcs": sample_vpcs}
            mock_get_client.return_value = mock_client

            result = await discover_vpcs(region="us-east-1")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 2
            assert parsed["region"] == "us-east-1"
            assert len(parsed["vpcs"]) == 2
            mock_client.describe_vpcs.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_discover_vpcs_empty(self) -> None:
        """Test discover_vpcs with no VPCs found."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_vpcs.return_value = {"Vpcs": []}
            mock_get_client.return_value = mock_client

            result = await discover_vpcs()

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 0
            assert parsed["vpcs"] == []


class TestTraceNetworkPathOperation:
    """Test trace_network_path operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_trace_network_path_success(self) -> None:
        """Test trace_network_path with valid IPs."""
        result = await trace_network_path("10.0.1.100", "172.16.1.200", region="us-west-2")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["source_ip"] == "10.0.1.100"
        assert parsed["destination_ip"] == "172.16.1.200"
        assert parsed["region"] == "us-west-2"
        assert "path_trace" in parsed
        assert parsed["total_hops"] >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_trace_network_path_invalid_ip(self) -> None:
        """Test trace_network_path with invalid IP address."""
        result = await trace_network_path("invalid-ip", "10.0.1.1")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "trace_network_path failed:" in parsed["error"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_trace_network_path_ipv6(self) -> None:
        """Test trace_network_path with IPv6 addresses."""
        result = await trace_network_path("2001:db8::1", "2001:db8::2")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["source_ip"] == "2001:db8::1"
        assert parsed["destination_ip"] == "2001:db8::2"


class TestValidateIPCIDROperation:
    """Test validate_ip_cidr operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_ip_cidr_valid_ip(self) -> None:
        """Test validate_ip_cidr with valid IP validation."""
        result = await validate_ip_cidr("validate_ip", ip="192.168.1.100")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["operation"] == "validate_ip"
        assert parsed["ip_address"] == "192.168.1.100"
        assert parsed["version"] == 4
        assert parsed["is_private"] is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_ip_cidr_valid_cidr(self) -> None:
        """Test validate_ip_cidr with valid CIDR validation."""
        result = await validate_ip_cidr("validate_cidr", cidr="10.0.0.0/24")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["operation"] == "validate_cidr"
        assert parsed["network"] == "10.0.0.0/24"
        assert parsed["network_address"] == "10.0.0.0"
        assert parsed["broadcast_address"] == "10.0.0.255"
        assert parsed["num_addresses"] == 256

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_ip_cidr_invalid_operation(self) -> None:
        """Test validate_ip_cidr with invalid operation."""
        result = await validate_ip_cidr("invalid_operation")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Invalid operation or missing parameters" in parsed["error"]
        assert "valid_operations" in parsed

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_ip_cidr_invalid_cidr(self) -> None:
        """Test validate_ip_cidr with invalid CIDR."""
        result = await validate_ip_cidr("validate_cidr", cidr="invalid/cidr")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "validate_ip_cidr failed:" in parsed["error"]


class TestAnalyzeTGWRoutesOperation:
    """Test analyze_tgw_routes operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tgw_routes_success(self) -> None:
        """Test analyze_tgw_routes with successful response."""
        sample_routes = [
            {"DestinationCidrBlock": "10.0.0.0/16", "State": "active", "Type": "static"},
            {"DestinationCidrBlock": "172.16.0.0/12", "State": "blackhole", "Type": "static"},
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.return_value = {"Routes": sample_routes}
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("tgw-rtb-123456789")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["route_table_id"] == "tgw-rtb-123456789"
            assert parsed["analysis"]["total_routes"] == 2
            assert parsed["analysis"]["active_routes"] == 1
            assert parsed["analysis"]["blackholed_routes"] == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tgw_routes_access_denied(self) -> None:
        """Test analyze_tgw_routes with access denied."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.side_effect = ClientError(
                {"Error": {"Code": "UnauthorizedOperation", "Message": "Not authorized"}}, "SearchTransitGatewayRoutes"
            )
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("tgw-rtb-invalid")

            parsed = json.loads(result)
            assert parsed["success"] is False
            assert parsed["error_code"] == "UnauthorizedOperation"


class TestAnalyzeTGWPeersOperation:
    """Test analyze_tgw_peers operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_success(self) -> None:
        """Test analyze_tgw_peers with successful response."""
        sample_attachment = {
            "TransitGatewayAttachmentId": "tgw-attach-123456789",
            "State": "available",
            "Status": {"Code": "available"},
            "CreatedAt": datetime(2024, 1, 15, 10, 30, 45),
            "AccepterTgwInfo": {"TransitGatewayId": "tgw-987654321"},
            "RequesterTgwInfo": {"TransitGatewayId": "tgw-123456789"},
            "Tags": [],
        }

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": [sample_attachment]
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_peers("tgw-attach-123456789")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["peer_id"] == "tgw-attach-123456789"
            assert parsed["peer_analysis"]["state"] == "available"
            assert parsed["peer_analysis"]["status"] == "available"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_not_found(self) -> None:
        """Test analyze_tgw_peers with peering attachment not found."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": []
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_peers("invalid-peer-id")

            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "No peering attachment found" in parsed["error"]


class TestValidateCloudWANPolicyOperation:
    """Test validate_cloudwan_policy operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_cloudwan_policy_valid(self) -> None:
        """Test validate_cloudwan_policy with valid policy document."""
        valid_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1"}, {"location": "us-west-2"}],
            },
        }

        result = await validate_cloudwan_policy(valid_policy)

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["overall_status"] == "valid"
        assert parsed["policy_version"] == "2021.12"
        assert len(parsed["validation_results"]) >= 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_cloudwan_policy_missing_fields(self) -> None:
        """Test validate_cloudwan_policy with missing required fields."""
        invalid_policy = {
            "version": "2021.12"
            # Missing 'core-network-configuration'
        }

        result = await validate_cloudwan_policy(invalid_policy)

        parsed = json.loads(result)
        assert parsed["success"] is True  # Function succeeds but validation fails
        assert parsed["overall_status"] == "invalid"

        # Check that missing field is reported
        validation_results = parsed["validation_results"]
        missing_core_config = next((r for r in validation_results if r["field"] == "core-network-configuration"), None)
        assert missing_core_config is not None
        assert missing_core_config["status"] == "invalid"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validate_cloudwan_policy_empty(self) -> None:
        """Test validate_cloudwan_policy with empty policy document."""
        result = await validate_cloudwan_policy({})

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["overall_status"] == "invalid"
        assert parsed["policy_version"] == "unknown"


class TestManageTGWRoutesOperation:
    """Test manage_tgw_routes operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_manage_tgw_routes_create(self) -> None:
        """Test manage_tgw_routes with route creation."""
        result = await manage_tgw_routes("create", "tgw-rtb-123456789", "10.0.0.0/16", region="us-east-1")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["operation"] == "create"
        assert parsed["route_table_id"] == "tgw-rtb-123456789"
        assert parsed["destination_cidr"] == "10.0.0.0/16"
        assert parsed["result"]["status"] == "completed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_manage_tgw_routes_invalid_cidr(self) -> None:
        """Test manage_tgw_routes with invalid CIDR block."""
        result = await manage_tgw_routes("create", "tgw-rtb-123456789", "invalid-cidr")

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "manage_tgw_routes failed:" in parsed["error"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_manage_tgw_routes_blackhole(self) -> None:
        """Test manage_tgw_routes with blackhole operation."""
        result = await manage_tgw_routes("blackhole", "tgw-rtb-123456789", "192.168.0.0/24")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["operation"] == "blackhole"
        assert parsed["destination_cidr"] == "192.168.0.0/24"


class TestAnalyzeSegmentRoutesOperation:
    """Test analyze_segment_routes operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_segment_routes_success(self) -> None:
        """Test analyze_segment_routes with successful analysis."""
        sample_policy = {
            "CoreNetworkPolicy": {
                "PolicyVersionId": "2",
                "PolicyDocument": json.dumps(
                    {"version": "2021.12", "segments": [{"name": "production", "require-attachment-acceptance": False}]}
                ),
            }
        }

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.return_value = sample_policy
            mock_get_client.return_value = mock_client

            result = await analyze_segment_routes("core-network-123", "production")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["core_network_id"] == "core-network-123"
            assert parsed["segment_name"] == "production"
            assert "analysis" in parsed
            assert "route_optimization" in parsed["analysis"]
            assert "recommendations" in parsed["analysis"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_segment_routes_policy_not_found(self) -> None:
        """Test analyze_segment_routes with policy not found."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Policy not found"}}, "GetCoreNetworkPolicy"
            )
            mock_get_client.return_value = mock_client

            result = await analyze_segment_routes("invalid-network", "production")

            parsed = json.loads(result)
            assert parsed["success"] is False
            assert parsed["error_code"] == "ResourceNotFoundException"


class TestListNetworkFunctionGroupsOperation:
    """Test list_network_function_groups operation following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_network_function_groups_success(self) -> None:
        """Test list_network_function_groups with successful response."""
        result = await list_network_function_groups(region="ap-southeast-1")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["region"] == "ap-southeast-1"
        assert "network_function_groups" in parsed
        assert isinstance(parsed["network_function_groups"], list)

        # Check simulated data structure
        if parsed["network_function_groups"]:
            nfg = parsed["network_function_groups"][0]
            assert "name" in nfg
            assert "description" in nfg
            assert "status" in nfg

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_network_function_group_success(self) -> None:
        """Test analyze_network_function_group with successful analysis."""
        result = await analyze_network_function_group("production-nfg", region="us-east-1")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["group_name"] == "production-nfg"
        assert parsed["region"] == "us-east-1"
        assert "analysis" in parsed
        assert "routing_policies" in parsed["analysis"]
        assert "security_policies" in parsed["analysis"]
        assert "performance_metrics" in parsed["analysis"]
