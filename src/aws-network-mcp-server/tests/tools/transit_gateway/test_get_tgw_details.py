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

"""Test cases for the get_tgw_details tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details import (
    get_tgw,
)
from datetime import datetime
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetTgwDetails:
    """Test cases for get_tgw_details function."""

    @pytest.fixture
    def sample_tgw_response(self):
        """Sample Transit Gateway API response."""
        return {
            'TransitGateways': [
                {
                    'TransitGatewayId': 'tgw-12345678',
                    'TransitGatewayArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-12345678',
                    'State': 'available',
                    'OwnerId': '123456789012',
                    'Description': 'Test transit gateway',
                    'CreationTime': datetime(2023, 1, 1, 0, 0, 0),
                    'Options': {
                        'AmazonSideAsn': 64512,
                        'DefaultRouteTableAssociation': 'enable',
                        'DefaultRouteTablePropagation': 'enable',
                        'AssociationDefaultRouteTableId': 'tgw-rtb-assoc-123',
                        'PropagationDefaultRouteTableId': 'tgw-rtb-prop-123',
                        'AutoAcceptSharedAttachments': 'disable',
                        'DnsSupport': 'enable',
                        'VpnEcmpSupport': 'enable',
                        'MulticastSupport': 'disable',
                        'SecurityGroupReferencingSupport': 'disable',
                        'TransitGatewayCidrBlocks': ['10.0.0.0/16'],
                    },
                    'Tags': [
                        {'Key': 'Name', 'Value': 'test-tgw'},
                        {'Key': 'Environment', 'Value': 'test'},
                    ],
                }
            ]
        }

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_success(self, mock_get_client, sample_tgw_response):
        """Test successful retrieval."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_transit_gateways.return_value = sample_tgw_response

        result = await get_tgw('tgw-12345678', 'us-east-1')

        assert result['transit_gateway_id'] == 'tgw-12345678'
        assert result['state'] == 'available'
        assert result['amazon_side_asn'] == 64512
        assert result['creation_time'] == '2023-01-01T00:00:00'
        assert result['tags'] == {'Name': 'test-tgw', 'Environment': 'test'}
        assert result['transit_gateway_cidr_blocks'] == ['10.0.0.0/16']
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_with_profile(self, mock_get_client, sample_tgw_response):
        """Test with custom profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_transit_gateways.return_value = sample_tgw_response

        await get_tgw('tgw-12345678', 'us-west-2', 'test-profile')

        mock_get_client.assert_called_once_with('ec2', 'us-west-2', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_not_found(self, mock_get_client):
        """Test TGW not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_transit_gateways.return_value = {'TransitGateways': []}

        with pytest.raises(ToolError, match='Transit Gateway was not found'):
            await get_tgw('tgw-nonexistent', 'us-east-1')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_aws_error(self, mock_get_client):
        """Test AWS API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_transit_gateways.side_effect = Exception(
            'InvalidTransitGatewayID.NotFound'
        )

        with pytest.raises(
            ToolError, match='There was an error getting AWS Transit Gateway details'
        ):
            await get_tgw('tgw-invalid', 'us-east-1')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_minimal_response(self, mock_get_client):
        """Test with minimal TGW response (missing optional fields)."""
        minimal_response = {
            'TransitGateways': [
                {
                    'TransitGatewayId': 'tgw-minimal',
                    'State': 'available',
                    'OwnerId': '123456789012',
                    'CreationTime': datetime(2023, 1, 1),
                    'Options': {
                        'AmazonSideAsn': 64512,
                        'DefaultRouteTableAssociation': 'enable',
                        'DefaultRouteTablePropagation': 'enable',
                    },
                }
            ]
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_transit_gateways.return_value = minimal_response

        result = await get_tgw('tgw-minimal', 'us-east-1')

        assert result['transit_gateway_id'] == 'tgw-minimal'
        assert result['transit_gateway_arn'] == ''
        assert result['description'] == ''
        assert result['association_default_route_table_id'] == ''
        assert result['auto_accept_shared_attachments'] == 'disable'
        assert result['dns_support'] == 'enable'
        assert result['transit_gateway_cidr_blocks'] == []
        assert result['tags'] == {}
