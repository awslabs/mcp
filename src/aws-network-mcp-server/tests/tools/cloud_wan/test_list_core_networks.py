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

"""Test cases for the list_core_networks tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
core_networks_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.list_core_networks'
)


class TestListCoreNetworks:
    """Test cases for list_core_networks function."""

    @pytest.fixture
    def mock_nm_client(self):
        """Mock NetworkManager client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_core_networks(self):
        """Sample core networks fixture."""
        return [
            {
                'CoreNetworkId': 'core-network-12345678',
                'CoreNetworkArn': 'arn:aws:networkmanager::123456789012:core-network/core-network-12345678',
                'Description': 'Production core network',
                'State': 'AVAILABLE',
            },
            {
                'CoreNetworkId': 'core-network-87654321',
                'CoreNetworkArn': 'arn:aws:networkmanager::123456789012:core-network/core-network-87654321',
                'Description': 'Staging core network',
                'State': 'CREATING',
            },
        ]

    @patch.object(core_networks_module, 'get_aws_client')
    async def test_success(self, mock_get_client, mock_nm_client, sample_core_networks):
        """Test successful core networks listing."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}

        result = await core_networks_module.list_core_networks(region='us-east-1')

        assert result['core_networks'] == sample_core_networks
        assert result['region'] == 'us-east-1'
        assert result['total_count'] == 2
        mock_get_client.assert_called_once_with('networkmanager', 'us-east-1', None)

    @patch.object(core_networks_module, 'get_aws_client')
    async def test_with_profile(self, mock_get_client, mock_nm_client, sample_core_networks):
        """Test with AWS profile."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.list_core_networks.return_value = {'CoreNetworks': sample_core_networks}

        await core_networks_module.list_core_networks(
            region='eu-west-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('networkmanager', 'eu-west-1', 'test-profile')

    @patch.object(core_networks_module, 'get_aws_client')
    async def test_empty_response(self, mock_get_client, mock_nm_client):
        """Test when no core networks exist."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.list_core_networks.return_value = {'CoreNetworks': []}

        with pytest.raises(
            ToolError, match='No CloudWAN core networks found.*VALIDATE PARAMETERS'
        ):
            await core_networks_module.list_core_networks(region='us-west-2')

    @patch.object(core_networks_module, 'get_aws_client')
    async def test_missing_core_networks_key(self, mock_get_client, mock_nm_client):
        """Test when response missing CoreNetworks key."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.list_core_networks.return_value = {}

        with pytest.raises(ToolError, match='No CloudWAN core networks found'):
            await core_networks_module.list_core_networks(region='us-east-1')

    @patch.object(core_networks_module, 'get_aws_client')
    async def test_aws_exception(self, mock_get_client, mock_nm_client):
        """Test AWS API exception handling."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.list_core_networks.side_effect = Exception('ServiceUnavailable')

        with pytest.raises(
            ToolError, match='Error listing CloudWAN core networks.*ServiceUnavailable'
        ):
            await core_networks_module.list_core_networks(region='us-east-1')

    async def test_missing_region(self):
        """Test missing required region parameter."""
        with pytest.raises(TypeError):
            await core_networks_module.list_core_networks()
