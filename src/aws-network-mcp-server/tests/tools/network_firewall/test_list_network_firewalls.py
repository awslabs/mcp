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

import pytest
from awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls import (
    list_network_firewalls,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestListNetworkFirewalls:
    """Test cases for list_network_firewalls function."""

    @pytest.fixture
    def mock_nfw_client(self):
        """Mock Network Firewall client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_firewalls(self):
        """Sample network firewalls fixture."""
        return [
            {
                'FirewallName': 'prod-firewall',
                'FirewallArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/prod-firewall',
            },
            {
                'FirewallName': 'staging-firewall',
                'FirewallArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/staging-firewall',
            },
        ]

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls.get_aws_client'
    )
    async def test_list_network_firewalls_success(
        self, mock_get_client, mock_nfw_client, sample_firewalls
    ):
        """Test successful network firewalls listing."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.list_firewalls.return_value = {'Firewalls': sample_firewalls}

        result = await list_network_firewalls(region='us-east-1')

        assert 'firewalls' in result
        assert result['firewalls'] == sample_firewalls
        assert 'total_count' in result
        assert result['total_count'] == 2

        mock_get_client.assert_called_once_with('network-firewall', 'us-east-1', None)
        mock_nfw_client.list_firewalls.assert_called_once()

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls.get_aws_client'
    )
    async def test_list_network_firewalls_empty(self, mock_get_client, mock_nfw_client):
        """Test listing when no network firewalls exist."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.list_firewalls.return_value = {'Firewalls': []}

        result = await list_network_firewalls(region='us-west-2')

        assert result['firewalls'] == []
        assert result['total_count'] == 0

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls.get_aws_client'
    )
    async def test_list_network_firewalls_with_profile(
        self, mock_get_client, mock_nfw_client, sample_firewalls
    ):
        """Test network firewalls listing with specific AWS profile."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.list_firewalls.return_value = {'Firewalls': sample_firewalls}

        await list_network_firewalls(region='eu-west-1', profile_name='test-profile')

        mock_get_client.assert_called_once_with('network-firewall', 'eu-west-1', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls.get_aws_client'
    )
    async def test_list_network_firewalls_aws_error(self, mock_get_client, mock_nfw_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.list_firewalls.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(ToolError) as exc_info:
            await list_network_firewalls(region='us-east-1')

        # Check for the actual error message format from implementation
        assert 'Error listing Network Firewalls:' in str(exc_info.value)

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.list_network_firewalls.get_aws_client'
    )
    async def test_list_network_firewalls_access_denied(self, mock_get_client, mock_nfw_client):
        """Test access denied error handling."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.list_firewalls.side_effect = Exception('AccessDenied: User not authorized')

        with pytest.raises(ToolError) as exc_info:
            await list_network_firewalls(region='us-east-1')

        assert 'Error listing Network Firewalls:' in str(exc_info.value)

    async def test_parameter_validation(self):
        """Test parameter validation for required fields."""
        with pytest.raises(TypeError):
            await list_network_firewalls()  # Missing required region parameter
