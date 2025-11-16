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

"""Test cases for the list_vpn_connections tool."""

import pytest
from unittest.mock import MagicMock, patch
from fastmcp.exceptions import ToolError
from awslabs.aws_network_mcp_server.tools.vpn.list_vpn_connections import list_vpn_connections


class TestListVpnConnections:
    """Test cases for list_vpn_connections function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_vpn_connections(self):
        """Sample VPN connections fixture."""
        return [
            {
                'VpnConnectionId': 'vpn-12345678',
                'State': 'available',
                'Type': 'ipsec.1',
                'CustomerGatewayId': 'cgw-12345678',
                'VpnGatewayId': 'vgw-12345678',
                'TransitGatewayId': 'tgw-12345678',
                'CustomerGatewayConfiguration': '<xml>sensitive-config</xml>'
            }
        ]

    @pytest.fixture
    def expected_vpn_connections(self):
        """Expected VPN connections after security filtering."""
        return [
            {
                'VpnConnectionId': 'vpn-12345678',
                'State': 'available',
                'Type': 'ipsec.1',
                'CustomerGatewayId': 'cgw-12345678',
                'VpnGatewayId': 'vgw-12345678',
                'TransitGatewayId': 'tgw-12345678'
                # Note: CustomerGatewayConfiguration removed for security
            }
        ]

    @patch('awslabs.aws_network_mcp_server.tools.vpn.list_vpn_connections.get_aws_client')
    async def test_list_vpn_connections_success(
        self, mock_get_client, mock_ec2_client, sample_vpn_connections, expected_vpn_connections
    ):
        """Test successful VPN connections listing with security filtering."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {
            'VpnConnections': sample_vpn_connections.copy()  # Copy to avoid modifying fixture
        }

        result = await list_vpn_connections(vpn_region='us-east-1')

        # Function returns the list directly, not wrapped in dict
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['VpnConnectionId'] == 'vpn-12345678'
        # CustomerGatewayConfiguration should be removed for security
        assert 'CustomerGatewayConfiguration' not in result[0]

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_vpn_connections.assert_called_once()

    @patch('awslabs.aws_network_mcp_server.tools.vpn.list_vpn_connections.get_aws_client')
    async def test_list_vpn_connections_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError):
            await list_vpn_connections(vpn_region='us-east-1')