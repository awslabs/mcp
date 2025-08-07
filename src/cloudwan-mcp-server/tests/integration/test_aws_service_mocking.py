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

"""Comprehensive AWS API mocking for NetworkManager and EC2 services following AWS Labs patterns."""

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_routes,
    discover_vpcs,
    get_aws_client,
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
)


class TestNetworkManagerServiceMocking:
    """Test comprehensive NetworkManager service mocking following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_manager_list_core_networks_detailed_mock(self) -> None:
        """Test NetworkManager list_core_networks with detailed mocking."""
        # Create comprehensive mock response
        mock_core_networks = [
            {
                "CoreNetworkId": "core-network-01234567890abcdef",
                "GlobalNetworkId": "global-network-01234567890abcdef",
                "State": "AVAILABLE",
                "Description": "Production CloudWAN Core Network",
                "CreatedAt": datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
                "Tags": [{"Key": "Environment", "Value": "Production"}, {"Key": "Team", "Value": "NetworkOps"}],
            },
            {
                "CoreNetworkId": "core-network-fedcba0987654321",
                "GlobalNetworkId": "global-network-fedcba0987654321",
                "State": "UPDATING",
                "Description": "Development CloudWAN Core Network",
                "CreatedAt": datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC),
                "Tags": [{"Key": "Environment", "Value": "Development"}, {"Key": "Team", "Value": "DevOps"}],
            },
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": mock_core_networks, "NextToken": None}
            mock_get_client.return_value = mock_client

            result = await list_core_networks(region="us-east-1")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 2
            assert len(parsed["core_networks"]) == 2

            # Verify detailed network attributes
            prod_network = next((n for n in parsed["core_networks"] if n["State"] == "AVAILABLE"), None)
            assert prod_network is not None
            assert prod_network["Description"] == "Production CloudWAN Core Network"

            # Verify API call parameters
            mock_client.list_core_networks.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_manager_global_networks_with_filters(self) -> None:
        """Test NetworkManager describe_global_networks with filter scenarios."""
        mock_global_networks = [
            {
                "GlobalNetworkId": "global-network-01234567890abcdef",
                "State": "AVAILABLE",
                "Description": "Multi-region global network",
                "CreatedAt": datetime(2024, 1, 10, 9, 0, 0, tzinfo=UTC),
                "Tags": [{"Key": "Region", "Value": "us-east-1"}],
            }
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.return_value = {
                "GlobalNetworks": mock_global_networks,
                "NextToken": None,
            }
            mock_get_client.return_value = mock_client

            result = await get_global_networks(region="us-east-1")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 1
            assert parsed["global_networks"][0]["State"] == "AVAILABLE"

            # Verify service and region parameters
            mock_get_client.assert_called_with("networkmanager", "us-east-1")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_manager_core_network_policy_detailed(self) -> None:
        """Test NetworkManager get_core_network_policy with complex policy document."""
        complex_policy_doc = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555", "65000-65010"],
                "edge-locations": [
                    {"location": "us-east-1", "asn": 64512},
                    {"location": "us-west-2", "asn": 64513},
                    {"location": "eu-west-1", "asn": 64514},
                ],
                "vpn-ecmp-support": True,
                "inside-cidr-blocks": ["169.254.0.0/16"],
            },
            "segments": [
                {"name": "production", "require-attachment-acceptance": False, "isolate-attachments": False},
                {"name": "development", "require-attachment-acceptance": True, "isolate-attachments": True},
            ],
            "segment-actions": [{"action": "share", "segment": "production", "share-with": ["development"]}],
        }

        mock_policy_response = {
            "CoreNetworkPolicy": {
                "PolicyVersionId": "3",
                "Alias": "LIVE",
                "PolicyDocument": json.dumps(complex_policy_doc),
                "Description": "Multi-segment production policy",
                "CreatedAt": datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
                "ChangeSetState": "READY_TO_EXECUTE",
            }
        }

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.return_value = mock_policy_response
            mock_get_client.return_value = mock_client

            result = await get_core_network_policy("core-network-01234567890abcdef", alias="LIVE")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["policy_version_id"] == "3"
            assert parsed["alias"] == "LIVE"

            # Verify policy document structure
            policy_doc = json.loads(parsed["policy_document"])
            assert policy_doc["version"] == "2021.12"
            assert len(policy_doc["segments"]) == 2
            assert len(policy_doc["core-network-configuration"]["edge-locations"]) == 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_manager_api_error_scenarios(self) -> None:
        """Test NetworkManager API comprehensive error scenario mocking."""
        error_scenarios = [
            {"error_code": "ThrottlingException", "error_message": "Rate exceeded", "operation": "ListCoreNetworks"},
            {
                "error_code": "ValidationException",
                "error_message": "Invalid parameter format",
                "operation": "GetCoreNetworkPolicy",
            },
            {
                "error_code": "ConflictException",
                "error_message": "Resource is being modified",
                "operation": "UpdateCoreNetwork",
            },
            {
                "error_code": "ServiceQuotaExceededException",
                "error_message": "Quota exceeded for core networks",
                "operation": "CreateCoreNetwork",
            },
        ]

        for scenario in error_scenarios:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()
                mock_client.list_core_networks.side_effect = ClientError(
                    {
                        "Error": {"Code": scenario["error_code"], "Message": scenario["error_message"]},
                        "ResponseMetadata": {"RequestId": f"req-{scenario['error_code']}-123", "HTTPStatusCode": 400},
                    },
                    scenario["operation"],
                )
                mock_get_client.return_value = mock_client

                result = await list_core_networks()

                parsed = json.loads(result)
                assert parsed["success"] is False
                assert scenario["error_code"] == parsed["error_code"]
                assert scenario["error_message"] in parsed["error"]


class TestEC2ServiceMocking:
    """Test comprehensive EC2 service mocking following AWS Labs patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ec2_describe_vpcs_comprehensive_mock(self) -> None:
        """Test EC2 describe_vpcs with comprehensive VPC attributes."""
        mock_vpcs = [
            {
                "VpcId": "vpc-01234567890abcdef0",
                "State": "available",
                "CidrBlock": "10.0.0.0/16",
                "DhcpOptionsId": "dopt-12345678",
                "InstanceTenancy": "default",
                "IsDefault": False,
                "Tags": [
                    {"Key": "Name", "Value": "Production VPC"},
                    {"Key": "Environment", "Value": "prod"},
                    {"Key": "CostCenter", "Value": "12345"},
                ],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": "vpc-cidr-assoc-12345678",
                        "CidrBlock": "10.0.0.0/16",
                        "CidrBlockState": {"State": "associated"},
                    }
                ],
            },
            {
                "VpcId": "vpc-fedcba0987654321f",
                "State": "available",
                "CidrBlock": "172.16.0.0/12",
                "DhcpOptionsId": "dopt-87654321",
                "InstanceTenancy": "default",
                "IsDefault": False,
                "Tags": [{"Key": "Name", "Value": "Development VPC"}, {"Key": "Environment", "Value": "dev"}],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": "vpc-cidr-assoc-87654321",
                        "CidrBlock": "172.16.0.0/12",
                        "CidrBlockState": {"State": "associated"},
                    },
                    {
                        "AssociationId": "vpc-cidr-assoc-secondary",
                        "CidrBlock": "192.168.0.0/16",
                        "CidrBlockState": {"State": "associated"},
                    },
                ],
            },
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_vpcs.return_value = {"Vpcs": mock_vpcs, "NextToken": None}
            mock_get_client.return_value = mock_client

            result = await discover_vpcs(region="us-west-2")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 2
            assert parsed["region"] == "us-west-2"

            # Verify VPC details
            prod_vpc = next(
                (v for v in parsed["vpcs"] if v.get("Tags", [{}])[0].get("Value") == "Production VPC"), None
            )
            assert prod_vpc is not None
            assert prod_vpc["CidrBlock"] == "10.0.0.0/16"
            assert prod_vpc["State"] == "available"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ec2_transit_gateway_routes_detailed_mock(self) -> None:
        """Test EC2 search_transit_gateway_routes with detailed route information."""
        mock_routes = [
            {
                "DestinationCidrBlock": "10.0.0.0/16",
                "TransitGatewayAttachments": [
                    {
                        "TransitGatewayAttachmentId": "tgw-attach-01234567890abcdef",
                        "ResourceId": "vpc-01234567890abcdef0",
                        "ResourceType": "vpc",
                    }
                ],
                "Type": "propagated",
                "State": "active",
                "RouteOrigin": "EnableVgwRoutePropagation",
            },
            {
                "DestinationCidrBlock": "172.16.0.0/12",
                "TransitGatewayAttachments": [
                    {
                        "TransitGatewayAttachmentId": "tgw-attach-fedcba0987654321",
                        "ResourceId": "vpc-fedcba0987654321f",
                        "ResourceType": "vpc",
                    }
                ],
                "Type": "static",
                "State": "active",
                "RouteOrigin": "CreateRoute",
            },
            {
                "DestinationCidrBlock": "192.168.0.0/16",
                "TransitGatewayAttachments": [],
                "Type": "static",
                "State": "blackhole",
                "RouteOrigin": "CreateRoute",
            },
        ]

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.return_value = {
                "Routes": mock_routes,
                "AdditionalRoutesAvailable": False,
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("tgw-rtb-01234567890abcdef")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["analysis"]["total_routes"] == 3
            assert parsed["analysis"]["active_routes"] == 2
            assert parsed["analysis"]["blackholed_routes"] == 1

            # Verify route details are preserved
            route_details = parsed["analysis"]["route_details"]
            active_routes = [r for r in route_details if r["State"] == "active"]
            assert len(active_routes) == 2

            blackhole_routes = [r for r in route_details if r["State"] == "blackhole"]
            assert len(blackhole_routes) == 1
            assert blackhole_routes[0]["DestinationCidrBlock"] == "192.168.0.0/16"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ec2_transit_gateway_peering_detailed_mock(self) -> None:
        """Test EC2 describe_transit_gateway_peering_attachments with detailed peering info."""
        mock_peering_attachment = {
            "TransitGatewayAttachmentId": "tgw-attach-01234567890abcdef",
            "RequesterTgwInfo": {
                "TransitGatewayId": "tgw-01234567890abcdef",
                "OwnerId": "123456789012",
                "Region": "us-east-1",
            },
            "AccepterTgwInfo": {
                "TransitGatewayId": "tgw-fedcba0987654321",
                "OwnerId": "210987654321",
                "Region": "us-west-2",
            },
            "Status": {"Code": "available", "Message": "Peering attachment is available"},
            "State": "available",
            "CreatedAt": datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
            "Tags": [{"Key": "Name", "Value": "Cross-region peering"}, {"Key": "Purpose", "Value": "DR connectivity"}],
        }

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": [mock_peering_attachment]
            }
            mock_get_client.return_value = mock_client

            # Import the function that we need to test
            from awslabs.cloudwan_mcp_server.server import analyze_tgw_peers

            result = await analyze_tgw_peers("tgw-attach-01234567890abcdef")

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["peer_analysis"]["state"] == "available"
            assert parsed["peer_analysis"]["status"] == "available"

            # Verify requester and accepter info
            requester_info = parsed["peer_analysis"]["requester_tgw_info"]
            assert requester_info["Region"] == "us-east-1"
            assert requester_info["TransitGatewayId"] == "tgw-01234567890abcdef"

            accepter_info = parsed["peer_analysis"]["accepter_tgw_info"]
            assert accepter_info["Region"] == "us-west-2"
            assert accepter_info["TransitGatewayId"] == "tgw-fedcba0987654321"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ec2_region_availability_mock(self) -> None:
        """Test EC2 describe_regions with comprehensive region information."""
        mock_regions = [
            {
                "RegionName": "us-east-1",
                "Endpoint": "ec2.us-east-1.amazonaws.com",
                "OptInStatus": "opt-in-not-required",
            },
            {
                "RegionName": "us-west-2",
                "Endpoint": "ec2.us-west-2.amazonaws.com",
                "OptInStatus": "opt-in-not-required",
            },
            {
                "RegionName": "eu-west-1",
                "Endpoint": "ec2.eu-west-1.amazonaws.com",
                "OptInStatus": "opt-in-not-required",
            },
            {
                "RegionName": "ap-southeast-1",
                "Endpoint": "ec2.ap-southeast-1.amazonaws.com",
                "OptInStatus": "opt-in-not-required",
            },
        ]

        with patch("boto3.Session") as mock_session_class:
            mock_session = Mock()
            mock_client = Mock()
            mock_client.describe_regions.return_value = {"Regions": mock_regions}
            mock_session.client.return_value = mock_client
            mock_session_class.return_value = mock_session

            # Test region validation through aws_config_manager
            from awslabs.cloudwan_mcp_server.server import aws_config_manager

            result = await aws_config_manager("set_region", region="eu-west-1")

            parsed = json.loads(result)
            # Should succeed because eu-west-1 is in the mocked regions list
            assert parsed["success"] is True
            assert parsed["new_region"] == "eu-west-1"


class TestIntegratedServiceMocking:
    """Test integrated NetworkManager and EC2 service interactions."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_service_workflow_mock(self) -> None:
        """Test workflow involving both NetworkManager and EC2 services."""
        # Mock NetworkManager core networks
        mock_core_networks = [
            {
                "CoreNetworkId": "core-network-01234567890abcdef",
                "GlobalNetworkId": "global-network-01234567890abcdef",
                "State": "AVAILABLE",
            }
        ]

        # Mock EC2 VPCs
        mock_vpcs = [{"VpcId": "vpc-01234567890abcdef0", "State": "available", "CidrBlock": "10.0.0.0/16"}]

        def mock_client_factory(service, region=None):
            """Factory function to return appropriate mocked client."""
            mock_client = Mock()

            if service == "networkmanager":
                mock_client.list_core_networks.return_value = {"CoreNetworks": mock_core_networks}
            elif service == "ec2":
                mock_client.describe_vpcs.return_value = {"Vpcs": mock_vpcs}

            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=mock_client_factory):
            # Test both operations in sequence
            core_networks_result = await list_core_networks()
            vpcs_result = await discover_vpcs()

            # Verify both operations succeeded
            core_parsed = json.loads(core_networks_result)
            vpcs_parsed = json.loads(vpcs_result)

            assert core_parsed["success"] is True
            assert vpcs_parsed["success"] is True
            assert core_parsed["total_count"] == 1
            assert vpcs_parsed["total_count"] == 1

    @pytest.mark.integration
    def test_aws_client_service_isolation_mock(self) -> None:
        """Test AWS client service isolation with comprehensive mocking."""
        with patch("awslabs.cloudwan_mcp_server.server.boto3.client") as mock_boto_client:
            # Test different services get different clients
            mock_nm_client = Mock()
            mock_ec2_client = Mock()

            def client_side_effect(service, **kwargs):
                if service == "networkmanager":
                    return mock_nm_client
                elif service == "ec2":
                    return mock_ec2_client
                else:
                    return Mock()

            mock_boto_client.side_effect = client_side_effect

            # Test client retrieval
            nm_client = get_aws_client("networkmanager", region="us-east-1")
            ec2_client = get_aws_client("ec2", region="us-east-1")

            assert nm_client == mock_nm_client
            assert ec2_client == mock_ec2_client
            assert nm_client != ec2_client

            # Verify proper service calls
            assert mock_boto_client.call_count == 2
            calls = mock_boto_client.call_args_list
            assert calls[0][0][0] == "networkmanager"
            assert calls[1][0][0] == "ec2"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_error_handling_patterns(self) -> None:
        """Test comprehensive service error handling patterns."""
        error_patterns = [
            # NetworkManager specific errors
            {
                "service": "networkmanager",
                "operation": "list_core_networks",
                "error_code": "CoreNetworkPolicyException",
                "error_message": "Policy validation failed",
                "function": list_core_networks,
            },
            # EC2 specific errors
            {
                "service": "ec2",
                "operation": "describe_vpcs",
                "error_code": "InvalidVpcID.NotFound",
                "error_message": "The vpc ID does not exist",
                "function": discover_vpcs,
            },
        ]

        for pattern in error_patterns:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()

                # Set up the appropriate method based on the service
                if pattern["service"] == "networkmanager":
                    mock_client.list_core_networks.side_effect = ClientError(
                        {"Error": {"Code": pattern["error_code"], "Message": pattern["error_message"]}},
                        pattern["operation"],
                    )
                elif pattern["service"] == "ec2":
                    mock_client.describe_vpcs.side_effect = ClientError(
                        {"Error": {"Code": pattern["error_code"], "Message": pattern["error_message"]}},
                        pattern["operation"],
                    )

                mock_get_client.return_value = mock_client

                result = await pattern["function"]()

                parsed = json.loads(result)
                assert parsed["success"] is False
                assert pattern["error_code"] == parsed["error_code"]
                assert pattern["error_message"] in parsed["error"]
