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

"""Test cases for the list_transit_gateways tool."""

import pytest
from unittest.mock import MagicMock, patch
from fastmcp.exceptions import ToolError
from awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateways import list_transit_gateways


class TestListTransitGateways:
    """Test cases for list_transit_gateways function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_tgws(self):
        """Sample Transit Gateways fixture."""
        return [
            {
                'TransitGatewayId': 'tgw-12345678',
                'State': 'available',
                'OwnerId': '123456789012'
            }
        ]

    @patch('awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateways.get_aws_client')
    async def test_list_transit_gateways_success(
        self, mock_get_client, mock_ec2_client, sample_tgws
    ):
        """Test successful Transit Gateways listing."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {
            'TransitGateways': sample_tgws
        }

        result = await list_transit_gateways(region='us-east-1')

        assert 'transit_gateways' in result
        assert result['transit_gateways'] == sample_tgws

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_transit_gateways.assert_called_once()

    @patch('awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateways.get_aws_client')
    async def test_list_transit_gateways_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.side_effect = Exception('ServiceUnavailable')

        with pytest.raises(ToolError):
            await list_transit_gateways(region='us-east-1')