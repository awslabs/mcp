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

"""Test cases for the get_cloudwan_peering_details tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
peering_details_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_peering_details'
)


class TestGetCloudwanPeeringDetails:
    """Test cases for get_cloudwan_peering_details function."""

    @pytest.fixture
    def peering_response(self):
        """Sample peering API response."""
        return {
            'TransitGatewayPeering': {
                'PeeringId': 'peering-123',
                'TransitGatewayArn': 'arn:aws:ec2:us-west-2:123456789012:transit-gateway/tgw-123',
                'TransitGatewayPeeringAttachmentId': 'tgw-attach-123',
                'Peering': {'SegmentName': 'production', 'EdgeLocation': 'us-west-2'},
            }
        }

    @pytest.fixture
    def tgw_response(self):
        """Sample Transit Gateway response."""
        return {
            'TransitGateways': [
                {'TransitGatewayId': 'tgw-123', 'State': 'available', 'AmazonSideAsn': 64512}
            ]
        }

    @pytest.fixture
    def route_tables_response(self):
        """Sample route tables response."""
        return {
            'TransitGatewayRouteTables': [
                {'TransitGatewayRouteTableId': 'tgw-rtb-123', 'State': 'available'}
            ]
        }

    @pytest.fixture
    def associations_response(self):
        """Sample associations response."""
        return {
            'Associations': [
                {'TransitGatewayAttachmentId': 'tgw-attach-123', 'State': 'associated'}
            ]
        }

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_success(
        self,
        mock_get_client,
        peering_response,
        tgw_response,
        route_tables_response,
        associations_response,
    ):
        """Test successful peering details retrieval."""
        mock_nm_client = MagicMock()
        mock_ec2_client = MagicMock()
        mock_get_client.side_effect = [mock_nm_client, mock_ec2_client]

        mock_nm_client.get_transit_gateway_peering.return_value = peering_response
        mock_ec2_client.describe_transit_gateways.return_value = tgw_response
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = route_tables_response
        mock_ec2_client.get_transit_gateway_route_table_associations.return_value = (
            associations_response
        )

        result = await peering_details_module.get_cwan_peering('peering-123', 'us-east-1')

        assert result['cloudwan_peering'] == peering_response['TransitGatewayPeering']
        assert result['cloudwan_segment'] == 'production'
        assert result['cloudwan_edge_location'] == 'us-west-2'
        assert result['transit_gateway'] == tgw_response['TransitGateways'][0]
        assert result['peering_route_table_id'] == 'tgw-rtb-123'
        assert result['peering_attachment_id'] == 'tgw-attach-123'

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_no_attachment_id(self, mock_get_client, tgw_response):
        """Test when peering has no attachment ID."""
        mock_nm_client = MagicMock()
        mock_ec2_client = MagicMock()
        mock_get_client.side_effect = [mock_nm_client, mock_ec2_client]

        peering_response = {
            'TransitGatewayPeering': {
                'PeeringId': 'peering-123',
                'TransitGatewayArn': 'arn:aws:ec2:us-west-2:123456789012:transit-gateway/tgw-123',
                'Peering': {'SegmentName': 'production', 'EdgeLocation': 'us-west-2'},
            }
        }

        mock_nm_client.get_transit_gateway_peering.return_value = peering_response
        mock_ec2_client.describe_transit_gateways.return_value = tgw_response

        result = await peering_details_module.get_cwan_peering('peering-123', 'us-east-1')

        assert result['peering_attachment_id'] is None
        assert result['peering_route_table_id'] is None

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_no_tgw_found(self, mock_get_client, peering_response):
        """Test when Transit Gateway is not found."""
        mock_nm_client = MagicMock()
        mock_ec2_client = MagicMock()
        mock_get_client.side_effect = [mock_nm_client, mock_ec2_client]

        mock_nm_client.get_transit_gateway_peering.return_value = peering_response
        mock_ec2_client.describe_transit_gateways.return_value = {'TransitGateways': []}

        result = await peering_details_module.get_cwan_peering('peering-123', 'us-east-1')

        assert result['transit_gateway'] is None

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_no_route_table_association(
        self, mock_get_client, peering_response, tgw_response, route_tables_response
    ):
        """Test when no route table is associated with peering attachment."""
        mock_nm_client = MagicMock()
        mock_ec2_client = MagicMock()
        mock_get_client.side_effect = [mock_nm_client, mock_ec2_client]

        mock_nm_client.get_transit_gateway_peering.return_value = peering_response
        mock_ec2_client.describe_transit_gateways.return_value = tgw_response
        mock_ec2_client.describe_transit_gateway_route_tables.return_value = route_tables_response
        mock_ec2_client.get_transit_gateway_route_table_associations.return_value = {
            'Associations': []
        }

        result = await peering_details_module.get_cwan_peering('peering-123', 'us-east-1')

        assert result['peering_route_table_id'] is None

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_peering_not_found(self, mock_get_client):
        """Test when peering is not found."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_transit_gateway_peering.side_effect = Exception('Peering not found')

        with pytest.raises(ToolError, match='Error getting Cloud WAN peering details'):
            await peering_details_module.get_cwan_peering('invalid-peering', 'us-east-1')

    @patch.object(peering_details_module, 'get_aws_client')
    async def test_with_profile(self, mock_get_client, peering_response, tgw_response):
        """Test with custom AWS profile."""
        mock_nm_client = MagicMock()
        mock_ec2_client = MagicMock()
        mock_get_client.side_effect = [mock_nm_client, mock_ec2_client]

        mock_nm_client.get_transit_gateway_peering.return_value = peering_response
        mock_ec2_client.describe_transit_gateways.return_value = tgw_response

        await peering_details_module.get_cwan_peering('peering-123', 'us-east-1', 'custom-profile')

        mock_get_client.assert_any_call('networkmanager', 'us-east-1', 'custom-profile')
        mock_get_client.assert_any_call('ec2', 'us-west-2', 'custom-profile')
