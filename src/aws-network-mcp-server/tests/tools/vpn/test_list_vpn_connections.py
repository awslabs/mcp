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

import importlib
import pytest
from botocore.exceptions import ClientError
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
vpn_list_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.vpn.list_vpn_connections'
)


class TestListVpnConnections:
    """Test cases for list_vpn_connections function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_success(self, mock_get_client, mock_ec2_client):
        """Test successful VPN connections listing with security filtering."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {
            'VpnConnections': [
                {
                    'VpnConnectionId': 'vpn-12345678',
                    'State': 'available',
                    'Type': 'ipsec.1',
                    'CustomerGatewayId': 'cgw-12345678',
                    'VpnGatewayId': 'vgw-12345678',
                    'CustomerGatewayConfiguration': '<xml>sensitive-config</xml>',
                }
            ]
        }

        result = await vpn_list_module.list_vpn_connections(vpn_region='us-east-1')

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['VpnConnectionId'] == 'vpn-12345678'
        assert 'CustomerGatewayConfiguration' not in result[0]
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_empty(self, mock_get_client, mock_ec2_client):
        """Test empty VPN connections list."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {'VpnConnections': []}

        result = await vpn_list_module.list_vpn_connections(vpn_region='us-west-2')

        assert result == []
        mock_get_client.assert_called_once_with('ec2', 'us-west-2', None)

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_multiple(self, mock_get_client, mock_ec2_client):
        """Test multiple VPN connections."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {
            'VpnConnections': [
                {'VpnConnectionId': 'vpn-1', 'State': 'available'},
                {
                    'VpnConnectionId': 'vpn-2',
                    'State': 'pending',
                    'CustomerGatewayConfiguration': 'config',
                },
            ]
        }

        result = await vpn_list_module.list_vpn_connections(vpn_region='eu-west-1')

        assert len(result) == 2
        assert result[0]['VpnConnectionId'] == 'vpn-1'
        assert result[1]['VpnConnectionId'] == 'vpn-2'
        assert 'CustomerGatewayConfiguration' not in result[1]

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_with_profile(self, mock_get_client, mock_ec2_client):
        """Test VPN connections listing with custom profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {'VpnConnections': []}

        await vpn_list_module.list_vpn_connections(
            vpn_region='us-east-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', 'test-profile')

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_client_error(self, mock_get_client, mock_ec2_client):
        """Test AWS ClientError handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'DescribeVpnConnections',
        )

        with pytest.raises(ToolError, match='Error listing VPN connections'):
            await vpn_list_module.list_vpn_connections(vpn_region='us-east-1')

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_generic_error(self, mock_get_client, mock_ec2_client):
        """Test generic exception handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.side_effect = Exception('Network error')

        with pytest.raises(ToolError, match='Error listing VPN connections'):
            await vpn_list_module.list_vpn_connections(vpn_region='us-east-1')

    @patch.object(vpn_list_module, 'get_aws_client')
    async def test_list_vpn_connections_no_customer_config(self, mock_get_client, mock_ec2_client):
        """Test VPN connection without CustomerGatewayConfiguration."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpn_connections.return_value = {
            'VpnConnections': [{'VpnConnectionId': 'vpn-12345678', 'State': 'available'}]
        }

        result = await vpn_list_module.list_vpn_connections(vpn_region='us-east-1')

        assert len(result) == 1
        assert result[0]['VpnConnectionId'] == 'vpn-12345678'
        assert 'CustomerGatewayConfiguration' not in result[0]
