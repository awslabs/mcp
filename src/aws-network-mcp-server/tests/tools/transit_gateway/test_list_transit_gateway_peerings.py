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

"""Test cases for the list_transit_gateway_peerings tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings import (
    list_tgw_peerings,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestListTransitGatewayPeerings:
    """Test cases for list_tgw_peerings function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_peerings(self):
        """Sample TGW peerings fixture."""
        return [
            {
                'TransitGatewayAttachmentId': 'tgw-attach-peering-12345678',
                'RequesterTgwInfo': {
                    'TransitGatewayId': 'tgw-12345678',
                    'Region': 'us-east-1',
                    'OwnerId': '123456789012',
                },
                'AccepterTgwInfo': {
                    'TransitGatewayId': 'tgw-87654321',
                    'Region': 'us-west-2',
                    'OwnerId': '123456789012',
                },
                'State': 'available',
                'CreationTime': '2024-01-01T00:00:00Z',
                'Tags': [{'Key': 'Name', 'Value': 'test-peering'}],
            }
        ]

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_success(
        self, mock_get_client, mock_ec2_client, sample_peerings
    ):
        """Test successful TGW peerings listing."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.return_value = {
            'TransitGatewayPeeringAttachments': sample_peerings
        }

        result = await list_tgw_peerings(
            transit_gateway_id='tgw-12345678', transit_gateway_region='us-east-1'
        )

        assert result == sample_peerings
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_transit_gateway_peering_attachments.assert_called_once_with(
            Filters=[{'Name': 'transit-gateway-id', 'Values': ['tgw-12345678']}]
        )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_with_profile(
        self, mock_get_client, mock_ec2_client, sample_peerings
    ):
        """Test TGW peerings listing with custom profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.return_value = {
            'TransitGatewayPeeringAttachments': sample_peerings
        }

        result = await list_tgw_peerings(
            transit_gateway_id='tgw-12345678',
            transit_gateway_region='us-west-2',
            profile_name='test-profile',
        )

        assert result == sample_peerings
        mock_get_client.assert_called_once_with('ec2', 'us-west-2', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_empty_results(self, mock_get_client, mock_ec2_client):
        """Test handling of empty peering results."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.return_value = {
            'TransitGatewayPeeringAttachments': []
        }

        result = await list_tgw_peerings(
            transit_gateway_id='tgw-12345678', transit_gateway_region='us-east-1'
        )

        assert result == []

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_missing_key(self, mock_get_client, mock_ec2_client):
        """Test handling of missing TransitGatewayPeeringAttachments key."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.return_value = {}

        result = await list_tgw_peerings(
            transit_gateway_id='tgw-12345678', transit_gateway_region='us-east-1'
        )

        assert result == []

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.side_effect = Exception(
            'AccessDenied'
        )

        with pytest.raises(ToolError, match='Error listing Transit Gateway peerings'):
            await list_tgw_peerings(
                transit_gateway_id='tgw-12345678', transit_gateway_region='us-east-1'
            )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client'
    )
    async def test_list_tgw_peerings_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(ToolError, match='Error listing Transit Gateway peerings'):
            await list_tgw_peerings(
                transit_gateway_id='tgw-12345678', transit_gateway_region='us-east-1'
            )
