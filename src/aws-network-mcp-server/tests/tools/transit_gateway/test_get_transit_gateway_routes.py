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

"""Test cases for the get_transit_gateway_routes tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes import (
    get_tgw_routes,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetTransitGatewayRoutes:
    """Test cases for get_tgw_routes function."""

    @pytest.fixture
    def mock_client(self):
        """Mock CloudWAN client fixture."""
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
            },
            {
                'DestinationCidrBlock': '192.168.0.0/16',
                'Destinations': [
                    {
                        'TransitGatewayAttachmentId': 'tgw-attach-87654321',
                        'ResourceType': 'vpn',
                    }
                ],
                'Type': 'STATIC',
                'State': 'BLACKHOLE',
            },
        ]

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_success(
        self,
        mock_get_client,
        mock_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_network_routes,
    ):
        """Test successful retrieval of TGW routes."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_client.get_network_routes.return_value = {'NetworkRoutes': sample_network_routes}

        result = await get_tgw_routes(
            global_network_region='us-west-2',
            transit_gateway_id='tgw-12345678',
            route_table_id='tgw-rtb-12345678',
        )

        assert result['transit_gateway_id'] == 'tgw-12345678'
        assert result['global_network_id'] == 'global-network-123'
        assert result['global_network_region'] == 'us-west-2'
        assert result['route_count'] == 2
        assert 'tgw-rtb-12345678' in result['routes']
        assert len(result['routes']['tgw-rtb-12345678']['routes']) == 2

        routes = result['routes']['tgw-rtb-12345678']['routes']
        assert routes[0]['destination'] == '10.0.0.0/16'
        assert routes[0]['attachment_id'] == 'tgw-attach-12345678'
        assert routes[0]['resource_type'] == 'vpc'
        assert routes[0]['type'] == 'propagated'
        assert routes[0]['state'] == 'active'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_with_filters(
        self,
        mock_get_client,
        mock_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_network_routes,
    ):
        """Test with route state and type filters."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_client.get_network_routes.return_value = {'NetworkRoutes': sample_network_routes}

        await get_tgw_routes(
            global_network_region='us-west-2',
            transit_gateway_id='tgw-12345678',
            route_table_id='tgw-rtb-12345678',
            route_state='ACTIVE',
            route_type='PROPAGATED',
        )

        mock_client.get_network_routes.assert_called_once_with(
            GlobalNetworkId='global-network-123',
            RouteTableIdentifier={
                'TransitGatewayRouteTableArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway-route-table/tgw-rtb-12345678'
            },
            States=['ACTIVE'],
            Types=['PROPAGATED'],
        )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_with_profile(
        self,
        mock_get_client,
        mock_client,
        sample_core_networks,
        sample_tgw_registrations,
        sample_network_routes,
    ):
        """Test with custom profile."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_client.get_network_routes.return_value = {'NetworkRoutes': sample_network_routes}

        await get_tgw_routes(
            global_network_region='us-west-2',
            transit_gateway_id='tgw-12345678',
            route_table_id='tgw-rtb-12345678',
            cloudwan_account_profile_name='test-profile',
        )

        mock_get_client.assert_called_once_with('networkmanager', 'us-west-2', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_no_global_networks(self, mock_get_client, mock_client):
        """Test error when no global networks found."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': []}

        with pytest.raises(
            ToolError, match='No Cloud WAN Global Networks found in this account and region'
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_unavailable_global_network(self, mock_get_client, mock_client):
        """Test with unavailable global network."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {
            'CoreNetworks': [{'GlobalNetworkId': 'global-network-123', 'State': 'PENDING'}]
        }

        with pytest.raises(
            ToolError, match='No Cloud WAN Global Networks found in this account and region'
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_tgw_not_registered(
        self, mock_get_client, mock_client, sample_core_networks
    ):
        """Test error when TGW is not registered."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': []
        }

        with pytest.raises(
            ToolError, match='Transit Gateway is not registered to Cloud WAN Global Network'
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_wrong_tgw_registered(
        self, mock_get_client, mock_client, sample_core_networks
    ):
        """Test when different TGW is registered."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': [
                {
                    'TransitGatewayArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-87654321'
                }
            ]
        }

        with pytest.raises(
            ToolError, match='Transit Gateway is not registered to Cloud WAN Global Network'
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_invalid_route_state(
        self, mock_get_client, mock_client, sample_core_networks, sample_tgw_registrations
    ):
        """Test error with invalid route state."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }

        with pytest.raises(
            ToolError,
            match='Route state value not valid. Only ACTIVE and BLACKHOLE are allowed. VALIDATE PARAMETERS BEFORE CONTINUING.',
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
                route_state='INVALID',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_invalid_route_type(
        self, mock_get_client, mock_client, sample_core_networks, sample_tgw_registrations
    ):
        """Test error with invalid route type."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }

        with pytest.raises(
            ToolError,
            match='Route type value not valid. Only PROPAGATED and STATIC are allowed. VALIDATE PARAMETERS BEFORE CONTINUING.',
        ):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
                route_type='INVALID',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_empty_routes(
        self,
        mock_get_client,
        mock_client,
        sample_core_networks,
        sample_tgw_registrations,
    ):
        """Test handling empty routes."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}
        mock_client.get_transit_gateway_registrations.return_value = {
            'TransitGatewayRegistrations': sample_tgw_registrations
        }
        mock_client.get_network_routes.return_value = {'NetworkRoutes': []}

        result = await get_tgw_routes(
            global_network_region='us-west-2',
            transit_gateway_id='tgw-12345678',
            route_table_id='tgw-rtb-12345678',
        )

        assert result['route_count'] == 0
        assert len(result['routes']['tgw-rtb-12345678']['routes']) == 0

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_aws_error(self, mock_get_client, mock_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_client
        mock_client.list_core_networks.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error getting Transit Gateway routes'):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_routes.get_aws_client'
    )
    async def test_get_tgw_routes_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(ToolError, match='Error getting Transit Gateway routes'):
            await get_tgw_routes(
                global_network_region='us-west-2',
                transit_gateway_id='tgw-12345678',
                route_table_id='tgw-rtb-12345678',
            )
