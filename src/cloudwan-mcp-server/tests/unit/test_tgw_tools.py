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

"""Unit tests for Transit Gateway tools."""

import json
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_tgw_route_table() -> dict:
    """Mock TGW route table fixture."""
    return {
        "TransitGatewayRouteTableId": "tgw-rtb-1234567890abcdef0",
        "TransitGatewayId": "tgw-1234567890abcdef0",
        "State": "available",
        "DefaultAssociationRouteTable": True,
        "DefaultPropagationRouteTable": True,
        "CreationTime": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_tgw_routes() -> list[dict]:
    """Mock TGW routes fixture."""
    return [
        {
            "DestinationCidrBlock": "10.0.0.0/16",
            "TransitGatewayAttachmentId": "tgw-attach-1234567890abcdef0",
            "Type": "propagated",
            "State": "active",
        },
        {
            "DestinationCidrBlock": "192.168.1.0/24",
            "TransitGatewayAttachmentId": "tgw-attach-0987654321fedcba0",
            "Type": "static",
            "State": "blackhole",
        },
    ]


@pytest.fixture
def mock_tgw_peers() -> list[dict]:
    """Mock TGW peering attachments fixture."""
    return [
        {
            "TransitGatewayAttachmentId": "tgw-attach-peer-1234567890abcdef0",
            "RequesterTgwInfo": {
                "TransitGatewayId": "tgw-1234567890abcdef0",
                "OwnerId": "123456789012",
                "Region": "us-east-1",
            },
            "AccepterTgwInfo": {
                "TransitGatewayId": "tgw-0987654321fedcba0",
                "OwnerId": "210987654321",
                "Region": "us-west-2",
            },
            "State": "available",
            "CreationTime": "2023-01-01T00:00:00Z",
        }
    ]


@pytest.fixture
def mock_aws_client():
    """Mock AWS client fixture."""
    client = Mock()
    return client


@pytest.fixture
def mock_get_aws_client() -> Generator:
    """Mock the get_aws_client function with EC2 responses for TGW."""

    def _mock_client(service, region=None):
        client = Mock()

        if service == "ec2":
            # Mock search transit gateway routes
            client.search_transit_gateway_routes.return_value = {
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.0.0.0/16",
                        "TransitGatewayAttachmentId": "tgw-attach-1234567890abcdef0",
                        "Type": "propagated",
                        "State": "active",
                    },
                    {
                        "DestinationCidrBlock": "192.168.1.0/24",
                        "TransitGatewayAttachmentId": "tgw-attach-0987654321fedcba0",
                        "Type": "static",
                        "State": "blackhole",
                    },
                ]
            }

            # Mock TGW peering attachments
            client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": [
                    {
                        "TransitGatewayAttachmentId": "tgw-attach-peer-1234567890abcdef0",
                        "RequesterTgwInfo": {
                            "TransitGatewayId": "tgw-1234567890abcdef0",
                            "OwnerId": "123456789012",
                            "Region": "us-east-1",
                        },
                        "AccepterTgwInfo": {
                            "TransitGatewayId": "tgw-0987654321fedcba0",
                            "OwnerId": "210987654321",
                            "Region": "us-west-2",
                        },
                        "State": "available",
                        "Status": {"Code": "available"},
                        "CreationTime": "2023-01-01T00:00:00Z",
                        "Tags": [],
                    }
                ]
            }

        return client

    with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=_mock_client) as mock:
        yield mock


from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_peers,
    analyze_tgw_routes,
    manage_tgw_routes,
)


class TestTransitGatewayRoutes:
    """Test Transit Gateway route management tools."""

    @pytest.mark.asyncio
    async def test_manage_tgw_routes_create_success(self, mock_get_aws_client: Generator) -> None:
        """Test successful TGW route creation."""
        result = await manage_tgw_routes("create", "tgw-rtb-1234567890abcdef0", "10.1.0.0/16", "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["operation"] == "create"
        assert response["route_table_id"] == "tgw-rtb-1234567890abcdef0"
        assert response["destination_cidr"] == "10.1.0.0/16"
        assert response["region"] == "us-east-1"
        assert response["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_manage_tgw_routes_delete(self, mock_get_aws_client: Generator) -> None:
        """Test TGW route deletion."""
        result = await manage_tgw_routes("delete", "tgw-rtb-1234567890abcdef0", "192.168.0.0/16")
        response = json.loads(result)

        assert response["success"] is True
        assert response["operation"] == "delete"
        assert "Route operation 'delete' completed successfully" in response["result"]["message"]

    @pytest.mark.asyncio
    async def test_manage_tgw_routes_blackhole(self, mock_get_aws_client: Generator) -> None:
        """Test TGW route blackhole operation."""
        result = await manage_tgw_routes("blackhole", "tgw-rtb-1234567890abcdef0", "172.16.0.0/12")
        response = json.loads(result)

        assert response["success"] is True
        assert response["operation"] == "blackhole"

    @pytest.mark.asyncio
    async def test_manage_tgw_routes_invalid_cidr(self, mock_get_aws_client: Generator) -> None:
        """Test TGW route management with invalid CIDR."""
        result = await manage_tgw_routes("create", "tgw-rtb-1234567890abcdef0", "invalid-cidr")
        response = json.loads(result)

        assert response["success"] is False
        assert "manage_tgw_routes failed" in response["error"]

    @pytest.mark.asyncio
    async def test_analyze_tgw_routes_success(self, mock_get_aws_client: Generator) -> None:
        """Test successful TGW route analysis."""
        result = await analyze_tgw_routes("tgw-rtb-1234567890abcdef0", "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["route_table_id"] == "tgw-rtb-1234567890abcdef0"
        assert response["region"] == "us-east-1"

        analysis = response["analysis"]
        assert analysis["total_routes"] == 2
        assert analysis["active_routes"] == 1
        assert analysis["blackholed_routes"] == 1
        assert "route_details" in analysis

        # Verify route details
        routes = analysis["route_details"]
        assert len(routes) == 2

        active_route = next(r for r in routes if r["State"] == "active")
        assert active_route["DestinationCidrBlock"] == "10.0.0.0/16"

        blackhole_route = next(r for r in routes if r["State"] == "blackhole")
        assert blackhole_route["DestinationCidrBlock"] == "192.168.1.0/24"

    @pytest.mark.asyncio
    async def test_analyze_tgw_routes_empty(self) -> None:
        """Test TGW route analysis with no routes."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.return_value = {"Routes": []}
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("tgw-rtb-empty123456789", "us-west-1")
            response = json.loads(result)

            assert response["success"] is True
            assert response["analysis"]["total_routes"] == 0
            assert response["analysis"]["active_routes"] == 0
            assert response["analysis"]["blackholed_routes"] == 0

    @pytest.mark.asyncio
    async def test_analyze_tgw_routes_client_error(self) -> None:
        """Test TGW route analysis with client error."""
        error_response = {
            "Error": {"Code": "InvalidRouteTableID.NotFound", "Message": "The route table ID does not exist"}
        }
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.side_effect = ClientError(
                error_response, "SearchTransitGatewayRoutes"
            )
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("invalid-rtb")
            response = json.loads(result)

            assert response["success"] is False
            assert "analyze_tgw_routes failed" in response["error"]
            assert response["error_code"] == "InvalidRouteTableID.NotFound"

    @pytest.mark.asyncio
    async def test_analyze_tgw_routes(self, mock_get_aws_client: Generator) -> None:
        route_table_id = "tgw-rtb-1234567890abcdef0"

        result = await analyze_tgw_routes(route_table_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["route_table_id"] == route_table_id
        assert response["region"] == "us-east-1"
        assert response["analysis"]["total_routes"] == 2
        assert response["analysis"]["active_routes"] == 1
        assert response["analysis"]["blackholed_routes"] == 1


class TestTransitGatewayPeers:
    """Test Transit Gateway peering tools."""

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_success(self, mock_get_aws_client: Generator) -> None:
        """Test successful TGW peer analysis."""
        peer_id = "tgw-attach-peer-1234567890abcdef0"
        result = await analyze_tgw_peers(peer_id, "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["peer_id"] == peer_id
        assert response["region"] == "us-east-1"

        analysis = response["peer_analysis"]
        assert analysis["state"] == "available"
        assert analysis["status"] == "available"

        # Verify requester TGW info
        requester_info = analysis["requester_tgw_info"]
        assert requester_info["TransitGatewayId"] == "tgw-1234567890abcdef0"
        assert requester_info["OwnerId"] == "123456789012"
        assert requester_info["Region"] == "us-east-1"

        # Verify accepter TGW info
        accepter_info = analysis["accepter_tgw_info"]
        assert accepter_info["TransitGatewayId"] == "tgw-0987654321fedcba0"
        assert accepter_info["OwnerId"] == "210987654321"
        assert accepter_info["Region"] == "us-west-2"

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_not_found(self) -> None:
        """Test TGW peer analysis with non-existent peer."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": []
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_peers("tgw-attach-peer-nonexistent", "us-east-1")
            response = json.loads(result)

            assert response["success"] is False
            assert "No peering attachment found with ID" in response["error"]

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_invalid_id(self) -> None:
        """Test TGW peer analysis with invalid peer ID."""
        error_response = {
            "Error": {
                "Code": "InvalidTransitGatewayAttachmentID.NotFound",
                "Message": "The transit gateway attachment ID invalid-id does not exist",
            }
        }
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.side_effect = ClientError(
                error_response, "DescribeTransitGatewayPeeringAttachments"
            )
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_peers("invalid-id", "us-east-1")
            response = json.loads(result)

            assert response["success"] is False
            assert "analyze_tgw_peers failed" in response["error"]
            assert response["error_code"] == "InvalidTransitGatewayAttachmentID.NotFound"

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers_default_region(self) -> None:
        """Test TGW peer analysis with default region."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": [
                    {
                        "TransitGatewayAttachmentId": "tgw-attach-peer-1234567890abcdef0",
                        "RequesterTgwInfo": {
                            "TransitGatewayId": "tgw-1234567890abcdef0",
                            "OwnerId": "123456789012",
                            "Region": "us-east-1",
                        },
                        "AccepterTgwInfo": {
                            "TransitGatewayId": "tgw-0987654321fedcba0",
                            "OwnerId": "210987654321",
                            "Region": "us-west-2",
                        },
                        "State": "available",
                        "Status": {"Code": "available"},
                        "CreationTime": "2023-01-01T00:00:00Z",
                        "Tags": [],
                    }
                ]
            }
            mock_get_client.return_value = mock_client

            with patch.dict("os.environ", {"AWS_DEFAULT_REGION": "eu-west-1"}, clear=True):
                with patch("awslabs.cloudwan_mcp_server.server.aws_config") as mock_aws_config:
                    mock_aws_config.default_region = "eu-west-1"

                    result = await analyze_tgw_peers("tgw-attach-peer-1234567890abcdef0")
                    response = json.loads(result)

                    assert response["success"] is True
                    assert response["region"] == "eu-west-1"

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers(self, mock_get_aws_client: Generator) -> None:
        peer_id = "tgw-attach-1234567890abcdef0"

        result = await analyze_tgw_peers(peer_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["peer_id"] == peer_id
        assert response["region"] == "us-east-1"
        assert response["peer_analysis"]["state"] == "available"
        assert response["peer_analysis"]["status"] == "available"
        assert response["peer_analysis"]["creation_time"] == "2023-01-01T00:00:00Z"


class TestTGWTools:
    """Test Transit Gateway analysis tools."""

    @pytest.mark.asyncio
    async def test_analyze_tgw_routes(self, mock_get_aws_client: Generator) -> None:
        """Test TGW route analysis tool."""
        from awslabs.cloudwan_mcp_server.server import analyze_tgw_routes

        route_table_id = "tgw-rtb-1234567890abcdef0"

        result = await analyze_tgw_routes(route_table_id, "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["route_table_id"] == route_table_id
        assert response["region"] == "us-east-1"
        assert "analysis" in response
        assert response["analysis"]["total_routes"] == 2
        assert response["analysis"]["active_routes"] == 1
        assert response["analysis"]["blackholed_routes"] == 1

    @pytest.mark.asyncio
    async def test_analyze_tgw_peers(self, mock_get_aws_client: Generator) -> None:
        """Test TGW peering analysis tool."""
        from awslabs.cloudwan_mcp_server.server import analyze_tgw_peers

        peer_id = "tgw-attach-peer-1234567890abcdef0"

        result = await analyze_tgw_peers(peer_id, "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["peer_id"] == peer_id
        assert response["region"] == "us-east-1"
        assert "peer_analysis" in response
        assert response["peer_analysis"]["state"] == "available"
        assert response["peer_analysis"]["requester_tgw_info"]["Region"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_manage_tgw_routes(self, mock_get_aws_client: Generator) -> None:
        """Test TGW route management tool."""
        from awslabs.cloudwan_mcp_server.server import manage_tgw_routes

        result = await manage_tgw_routes("create", "tgw-rtb-1234567890abcdef0", "10.2.0.0/16", "us-east-1")
        response = json.loads(result)

        assert response["success"] is True
        assert response["operation"] == "create"
        assert response["destination_cidr"] == "10.2.0.0/16"

    @pytest.mark.asyncio
    async def test_tgw_tools_error_handling(self) -> None:
        """Test TGW tools error handling."""
        from botocore.exceptions import ClientError

        from awslabs.cloudwan_mcp_server.server import analyze_tgw_routes

        # Mock client error with explicit patch
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.side_effect = ClientError(
                error_response={"Error": {"Code": "InvalidRouteTableID.NotFound", "Message": "Route table not found"}},
                operation_name="SearchTransitGatewayRoutes",
            )
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("invalid-route-table-id")
            response = json.loads(result)

            assert response["success"] is False
            assert "analyze_tgw_routes failed" in response["error"]
            assert response["error_code"] == "InvalidRouteTableID.NotFound"

    @pytest.mark.asyncio
    async def test_tgw_peers_not_found(self) -> None:
        """Test TGW peers analysis when peer not found."""
        from awslabs.cloudwan_mcp_server.server import analyze_tgw_peers

        # Mock empty response with explicit patch
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": []
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_peers("nonexistent-peer-id", "us-east-1")
            response = json.loads(result)

            assert response["success"] is False
            assert "No peering attachment found" in response["error"]
            assert response["error_code"] == "ResourceNotFound"

    @pytest.mark.asyncio
    @patch("awslabs.cloudwan_mcp_server.server.boto3")  # Corrected path
    async def test_list_tgw_attachments(self, mock_boto3: Mock) -> None:
        """Test TGW attachment listing."""
        # ... existing code ...
        # ... existing code ...
