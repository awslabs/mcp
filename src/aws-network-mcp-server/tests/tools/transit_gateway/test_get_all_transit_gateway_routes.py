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

"""Test cases for the get_all_transit_gateway_routes tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes import (
    get_all_tgw_routes,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetAllTransitGatewayRoutes:
    """Test cases for get_all_tgw_routes function."""

    @pytest.fixture
    def mock_cloudwan_client(self):
        """Mock CloudWAN client fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_core_networks(self):
        """Sample core networks fixture."""
        return [{'GlobalNetworkId': 'global-network-123', 'State': 'AVAILABLE'}]

    @pytest.fixture
    def sample_tgw_registrations(self):
        """Sample TGW registrations fixture."""
        return [
            {
                'TransitGatewayArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-12345678'
            }
        ]

    @pytest.fixture
    def sample_route_tables(self):
        """Sample route tables fixture."""
        return [
            {
                'TransitGatewayRouteTableId': 'tgw-rtb-12345678',
                'State': 'available',
                'Tags': [{'Key': 'Name', 'Value': 'test-rt'}],
            }
        ]

    @pytest.fixture
    def sample_network_routes(self):
        """Sample network routes fixture."""
        return [
            {
                'DestinationCidrBlock': '10.0.0.0/16',
                'Destinations': [
                    {
                        'TransitGatewayAttachmentId': 'tgw-attach-12345678',
                        'ResourceType': 'vpc',
                    }
                ],
                'Type': 'PROPAGATED',
                'State': 'ACTIVE',
            }
        ]

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_success(
        self,
        mock_get_client,
        mock_cloudwan_client,
        mock_ec2_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_route_tables,
        sample_network_routes,
    ):
        """Test successful retrieval of all TGW routes."""
        mock_get_client.side_effect = [mock_cloudwan_client, mock_ec2_client]
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = {
            'TransitGatewayRouteTables': sample_route_tables
        }
        mock_cloudwan_client.get_network_routes.return_value = {
            'NetworkRoutes': sample_network_routes
        }

        result = await get_all_tgw_routes(
            transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
        )

        assert result['transit_gateway_id'] == 'tgw-12345678'
        assert result['transit_gateway_region'] == 'us-east-1'
        assert result['global_network_id'] == 'global-network-123'
        assert result['route_count'] == 1
        assert 'tgw-rtb-12345678' in result['routes']
        assert result['routes']['tgw-rtb-12345678']['name'] == 'test-rt'
        assert len(result['routes']['tgw-rtb-12345678']['routes']) == 1

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_with_profiles(
        self,
        mock_get_client,
        mock_cloudwan_client,
        mock_ec2_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_route_tables,
        sample_network_routes,
    ):
        """Test with custom profiles."""
        mock_get_client.side_effect = [mock_cloudwan_client, mock_ec2_client]
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = {
            'TransitGatewayRouteTables': sample_route_tables
        }
        mock_cloudwan_client.get_network_routes.return_value = {
            'NetworkRoutes': sample_network_routes
        }

        await get_all_tgw_routes(
            transit_gateway_id='tgw-12345678',
            global_network_region='us-west-2',
            tgw_account_profile_name='tgw-profile',
            cloudwan_account_profile_name='cloudwan-profile',
        )

        assert mock_get_client.call_count == 2
        mock_get_client.assert_any_call('networkmanager', 'us-west-2', 'cloudwan-profile')
        mock_get_client.assert_any_call('ec2', 'us-east-1', 'tgw-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_no_global_networks(
        self, mock_get_client, mock_cloudwan_client
    ):
        """Test error when no global networks found."""
        mock_get_client.return_value = mock_cloudwan_client
        mock_cloudwan_client.list_core_networks.return_value = {'CoreNetworks': []}

        with pytest.raises(
            ToolError, match='No Cloud WAN Global Networks found in this account and region'
        ):
            await get_all_tgw_routes(
                transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_tgw_not_registered(
        self, mock_get_client, mock_cloudwan_client, sample_core_networks
    ):
        """Test error when TGW is not registered."""
        mock_get_client.return_value = mock_cloudwan_client
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': []
        }

        with pytest.raises(
            ToolError, match='Transit Gateway is not registered to Cloud WAN Global Network'
        ):
            await get_all_tgw_routes(
                transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_pagination(
        self,
        mock_get_client,
        mock_cloudwan_client,
        mock_ec2_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_network_routes,
    ):
        """Test pagination handling for route tables."""
        mock_get_client.side_effect = [mock_cloudwan_client, mock_ec2_client]
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }

        # First call returns NextToken, second call returns remaining data
        mock_ec2_client.describe_transit_gateway_route_tables.side_effect = [
            {
                'TransitGatewayRouteTables': [
                    {
                        'TransitGatewayRouteTableId': 'tgw-rtb-1',
                        'State': 'available',
                        'Tags': [{'Key': 'Name', 'Value': 'rt-1'}],
                    }
                ],
                'NextToken': 'token123',
            },
            {
                'TransitGatewayRouteTables': [
                    {
                        'TransitGatewayRouteTableId': 'tgw-rtb-2',
                        'State': 'available',
                        'Tags': [{'Key': 'Name', 'Value': 'rt-2'}],
                    }
                ]
            },
        ]
        mock_cloudwan_client.get_network_routes.return_value = {
            'NetworkRoutes': sample_network_routes
        }

        result = await get_all_tgw_routes(
            transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
        )

        assert len(result['routes']) == 2
        assert 'tgw-rtb-1' in result['routes']
        assert 'tgw-rtb-2' in result['routes']

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_no_name_tag(
        self,
        mock_get_client,
        mock_cloudwan_client,
        mock_ec2_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_network_routes,
    ):
        """Test handling route table without Name tag."""
        mock_get_client.side_effect = [mock_cloudwan_client, mock_ec2_client]
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = {
            'TransitGatewayRouteTables': [
                {
                    'TransitGatewayRouteTableId': 'tgw-rtb-12345678',
                    'State': 'available',
                    'Tags': [{'Key': 'Environment', 'Value': 'test'}],
                }
            ]
        }
        mock_cloudwan_client.get_network_routes.return_value = {
            'NetworkRoutes': sample_network_routes
        }

        result = await get_all_tgw_routes(
            transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
        )

        assert 'name' not in result['routes']['tgw-rtb-12345678']

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_empty_routes(
        self,
        mock_get_client,
        mock_cloudwan_client,
        mock_ec2_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_route_tables,
    ):
        """Test handling empty routes."""
        mock_get_client.side_effect = [mock_cloudwan_client, mock_ec2_client]
        mock_cloudwan_client.list_core_networks.return_value = {
            'CoreNetworks': sample_core_networks
        }
        mock_cloudwan_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = {
            'TransitGatewayRouteTables': sample_route_tables
        }
        mock_cloudwan_client.get_network_routes.return_value = {'NetworkRoutes': []}

        result = await get_all_tgw_routes(
            transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
        )

        assert result['route_count'] == 0
        assert len(result['routes']['tgw-rtb-12345678']['routes']) == 0

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_aws_error(self, mock_get_client, mock_cloudwan_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_cloudwan_client
        mock_cloudwan_client.list_core_networks.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='There was an error getting Transit Gateway routes'):
            await get_all_tgw_routes(
                transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_all_transit_gateway_routes.get_aws_client'
    )
    async def test_get_all_tgw_routes_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(ToolError, match='There was an error getting Transit Gateway routes'):
            await get_all_tgw_routes(
                transit_gateway_id='tgw-12345678', global_network_region='us-east-1'
            )
