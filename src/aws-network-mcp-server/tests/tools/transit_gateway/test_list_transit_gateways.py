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

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
tgw_list_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.transit_gateway.list_transit_gateways'
)


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
                'OwnerId': '123456789012',
                'AmazonSideAsn': 64512,
                'Tags': [{'Key': 'Name', 'Value': 'test-tgw'}],
            },
            {
                'TransitGatewayId': 'tgw-87654321',
                'State': 'pending',
                'OwnerId': '123456789012',
                'AmazonSideAsn': 64513,
            },
        ]

    @patch.object(tgw_list_module, 'get_aws_client')
    async def test_list_transit_gateways_success(
        self, mock_get_client, mock_ec2_client, sample_tgws
    ):
        """Test successful Transit Gateways listing."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {'TransitGateways': sample_tgws}

        result = await tgw_list_module.list_transit_gateways(region='us-east-1')

        assert result['transit_gateways'] == sample_tgws
        assert result['region'] == 'us-east-1'
        assert result['total_count'] == 2
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)

    @patch.object(tgw_list_module, 'get_aws_client')
    async def test_list_transit_gateways_empty(self, mock_get_client, mock_ec2_client):
        """Test empty Transit Gateways response."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {'TransitGateways': []}

        result = await tgw_list_module.list_transit_gateways(region='us-west-2')

        assert result['transit_gateways'] == []
        assert result['total_count'] == 0

    @patch.object(tgw_list_module, 'get_aws_client')
    async def test_list_transit_gateways_with_profile(self, mock_get_client, mock_ec2_client):
        """Test with custom profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {'TransitGateways': []}

        await tgw_list_module.list_transit_gateways(
            region='eu-west-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('ec2', 'eu-west-1', 'test-profile')

    @patch.object(tgw_list_module, 'get_aws_client')
    async def test_list_transit_gateways_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.side_effect = Exception('ServiceUnavailable')

        with pytest.raises(ToolError, match='Error listing Transit Gateways'):
            await tgw_list_module.list_transit_gateways(region='us-east-1')

    @patch.object(tgw_list_module, 'get_aws_client')
    async def test_list_transit_gateways_missing_key(self, mock_get_client, mock_ec2_client):
        """Test response without TransitGateways key."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {}

        result = await tgw_list_module.list_transit_gateways(region='us-east-1')

        assert result['transit_gateways'] == []
        assert result['total_count'] == 0
