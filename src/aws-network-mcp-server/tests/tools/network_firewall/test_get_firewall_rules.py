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

"""Test cases for the get_firewall_rules tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.network_firewall.get_firewall_rules import (
    get_firewall_rules,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetFirewallRules:
    """Test cases for get_firewall_rules function."""

    @pytest.fixture
    def mock_nfw_client(self):
        """Mock Network Firewall client fixture."""
        return MagicMock()

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.get_firewall_rules.get_aws_client'
    )
    async def test_get_firewall_rules_success(self, mock_get_client, mock_nfw_client):
        """Test successful firewall rules retrieval."""
        mock_get_client.return_value = mock_nfw_client

        # Mock firewall description
        mock_nfw_client.describe_firewall.return_value = {
            'Firewall': {
                'FirewallName': 'test-firewall',
                'FirewallArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall',
                'FirewallPolicyArn': 'arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/test-policy',
            }
        }

        result = await get_firewall_rules(firewall_name='test-firewall', region='us-east-1')

        assert 'firewall_info' in result
        mock_get_client.assert_called_once_with('network-firewall', 'us-east-1', None)

    @patch(
        'awslabs.aws_network_mcp_server.tools.network_firewall.get_firewall_rules.get_aws_client'
    )
    async def test_get_firewall_rules_aws_error(self, mock_get_client, mock_nfw_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_nfw_client
        mock_nfw_client.describe_firewall.side_effect = Exception('ResourceNotFoundException')

        with pytest.raises(ToolError):
            await get_firewall_rules(firewall_name='nonexistent-firewall', region='us-east-1')
