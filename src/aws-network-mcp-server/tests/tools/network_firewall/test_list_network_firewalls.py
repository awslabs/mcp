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

"""Test cases for the list_network_firewalls tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
nfw_list_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls'
)


class TestListNetworkFirewalls:
    """Test cases for list_network_firewalls function."""

    @pytest.fixture
    def mock_client(self):
        """Mock Network Firewall client."""
        return MagicMock()

    @pytest.fixture
    def sample_firewalls(self):
        """Sample firewall response."""
        return [
            {
                'FirewallName': 'test-firewall',
                'FirewallArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall',
            }
        ]

    @patch.object(nfw_list_module, 'get_aws_client')
    async def test_success(self, mock_get_client, mock_client, sample_firewalls):
        """Test successful listing."""
        mock_get_client.return_value = mock_client
        mock_client.list_firewalls.return_value = {'Firewalls': sample_firewalls}

        result = await nfw_list_module.list_firewalls(region='us-east-1')

        assert result == {'firewalls': sample_firewalls, 'region': 'us-east-1', 'total_count': 1}
        mock_get_client.assert_called_once_with('network-firewall', 'us-east-1', None)

    @patch.object(nfw_list_module, 'get_aws_client')
    async def test_empty_response(self, mock_get_client, mock_client):
        """Test empty firewall list."""
        mock_get_client.return_value = mock_client
        mock_client.list_firewalls.return_value = {'Firewalls': []}

        result = await nfw_list_module.list_firewalls(region='us-west-2')

        assert result['firewalls'] == []
        assert result['total_count'] == 0

    @patch.object(nfw_list_module, 'get_aws_client')
    async def test_missing_firewalls_key(self, mock_get_client, mock_client):
        """Test response without Firewalls key."""
        mock_get_client.return_value = mock_client
        mock_client.list_firewalls.return_value = {}

        result = await nfw_list_module.list_firewalls(region='us-east-1')

        assert result['firewalls'] == []
        assert result['total_count'] == 0

    @patch.object(nfw_list_module, 'get_aws_client')
    async def test_with_profile(self, mock_get_client, mock_client):
        """Test with profile parameter."""
        mock_get_client.return_value = mock_client
        mock_client.list_firewalls.return_value = {'Firewalls': []}

        await nfw_list_module.list_firewalls(region='eu-west-1', profile_name='test-profile')

        mock_get_client.assert_called_once_with('network-firewall', 'eu-west-1', 'test-profile')

    @patch.object(nfw_list_module, 'get_aws_client')
    async def test_aws_error(self, mock_get_client, mock_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_client
        mock_client.list_firewalls.side_effect = Exception('API Error')

        with pytest.raises(ToolError, match='Error listing Network Firewalls: API Error'):
            await nfw_list_module.list_firewalls(region='us-east-1')
