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
    get_tgw_details,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetTgwDetails:
    """Test cases for get_tgw_details function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_tgw_data(self):
        """Sample Transit Gateway data fixture."""
        from datetime import datetime

        return {
            'TransitGatewayId': 'tgw-12345678',
            'TransitGatewayArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-12345678',
            'State': 'available',
            'OwnerId': '123456789012',
            'Description': 'Test transit gateway',
            'CreationTime': datetime(2023, 1, 1, 0, 0, 0),
            'Options': {
                'AmazonSideAsn': 64512,
                'AutoAcceptSharedAttachments': 'disable',
                'DefaultRouteTableAssociation': 'enable',
                'DefaultRouteTablePropagation': 'enable',
                'DnsSupport': 'enable',
                'MulticastSupport': 'disable',
                'AssociationDefaultRouteTableId': 'tgw-rtb-association-123',
                'PropagationDefaultRouteTableId': 'tgw-rtb-propagation-123',
            },
            'Tags': [
                {'Key': 'Name', 'Value': 'test-tgw'},
                {'Key': 'Environment', 'Value': 'test'},
            ],
        }

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_get_tgw_details_success(
        self, mock_get_client, mock_ec2_client, sample_tgw_data
    ):
        """Test successful Transit Gateway details retrieval."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {
            'TransitGateways': [sample_tgw_data]
        }

        result = await get_tgw_details(transit_gateway_id='tgw-12345678', region='us-east-1')

        # Verify the formatted result structure
        assert result['transit_gateway_id'] == 'tgw-12345678'
        assert result['state'] == 'available'
        assert result['owner_id'] == '123456789012'
        assert result['description'] == 'Test transit gateway'
        assert result['amazon_side_asn'] == 64512
        assert result['creation_time'] == '2023-01-01T00:00:00'
        assert result['tags'] == {'Name': 'test-tgw', 'Environment': 'test'}

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_transit_gateways.assert_called_once_with(
            TransitGatewayIds=['tgw-12345678']
        )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_get_tgw_details_not_found(self, mock_get_client, mock_ec2_client):
        """Test error handling when Transit Gateway is not found."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {'TransitGateways': []}

        with pytest.raises(ToolError) as exc_info:
            await get_tgw_details(transit_gateway_id='tgw-nonexistent', region='us-east-1')

        assert (
            'Transit Gateway was not found with the given details. VALIDATE PARAMETERS BEFORE CONTINUING.'
            in str(exc_info.value)
        )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_get_tgw_details_with_profile(
        self, mock_get_client, mock_ec2_client, sample_tgw_data
    ):
        """Test Transit Gateway details retrieval with specific AWS profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.return_value = {
            'TransitGateways': [sample_tgw_data]
        }

        result = await get_tgw_details(
            transit_gateway_id='tgw-12345678', region='us-west-2', profile_name='test-profile'
        )

        # Check formatted output, not raw input
        assert result['transit_gateway_id'] == 'tgw-12345678'
        assert result['state'] == 'available'
        mock_get_client.assert_called_once_with('ec2', 'us-west-2', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_get_tgw_details_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.side_effect = Exception(
            'InvalidTransitGatewayID.NotFound'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_tgw_details(transit_gateway_id='tgw-invalid', region='us-east-1')

        assert (
            'There was an error getting AWS Transit Gateway details. Error: InvalidTransitGatewayID.NotFound'
            in str(exc_info.value)
        )

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_get_tgw_details_access_denied(self, mock_get_client, mock_ec2_client):
        """Test access denied error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_transit_gateways.side_effect = Exception('UnauthorizedOperation')

        with pytest.raises(ToolError) as exc_info:
            await get_tgw_details(transit_gateway_id='tgw-12345678', region='us-east-1')

        assert (
            'There was an error getting AWS Transit Gateway details. Error: UnauthorizedOperation'
            in str(exc_info.value)
        )

    async def test_parameter_validation(self):
        """Test parameter validation for required fields."""
        with pytest.raises(TypeError):
            await get_tgw_details()  # Missing required parameters

        with pytest.raises(TypeError):
            await get_tgw_details(transit_gateway_id='tgw-test')  # Missing region
