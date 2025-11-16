#!/usr/bin/env python3
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
from unittest.mock import MagicMock, patch
from fastmcp.exceptions import ToolError
from awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings import list_tgw_peerings


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
                'TransitGatewayPeeringAttachmentId': 'tgw-attach-peering-12345678',
                'RequesterTgwInfo': {
                    'TransitGatewayId': 'tgw-12345678',
                    'Region': 'us-east-1'
                },
                'AccepterTgwInfo': {
                    'TransitGatewayId': 'tgw-87654321',
                    'Region': 'us-west-2'
                },
                'State': 'available'
            }
        ]

    @patch('awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client')
    async def test_list_tgw_peerings_success(
        self, mock_get_client, mock_ec2_client, sample_peerings
    ):
        """Test successful TGW peerings listing."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.return_value = {
            'TransitGatewayPeeringAttachments': sample_peerings
        }

        result = await list_tgw_peerings(region='us-east-1')

        assert 'peering_attachments' in result
        assert result['peering_attachments'] == sample_peerings

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_transit_gateway_peering_attachments.assert_called_once()

    @patch('awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateway_peerings.get_aws_client')
    async def test_list_tgw_peerings_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateway_peering_attachments.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError):
            await list_tgw_peerings(region='us-east-1')