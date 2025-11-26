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

"""Test cases for the get_cloudwan_routes tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
routes_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_routes'
)


class TestGetCloudwanRoutes:
    """Test cases for get_cloudwan_routes function."""

    @pytest.fixture
    def mock_core_network(self):
        """Mock core network response."""
        return {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-network-123',
                'Segments': [{'Name': 'segment-a'}, {'Name': 'segment-b'}],
                'NetworkFunctionGroups': [{'Name': 'nfg-1'}, {'Name': 'nfg-2'}],
            }
        }

    @pytest.fixture
    def mock_routes_response(self):
        """Mock routes response."""
        return {
            'NetworkRoutes': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    'Destinations': [{'CoreNetworkAttachmentId': 'attachment-123'}],
                    'Type': 'PROPAGATED',
                    'State': 'ACTIVE',
                },
                {
                    'DestinationCidrBlock': '192.168.0.0/24',
                    'Destinations': [{'ResourceId': 'resource-456'}],
                    'Type': 'STATIC',
                    'State': 'BLACKHOLE',
                },
            ]
        }

    async def test_missing_parameters(self):
        """Test error when neither segment nor network_function_group provided."""
        with pytest.raises(ToolError, match='Please provide a segment or network_function_group'):
            await routes_module.get_cwan_routes(
                core_network_id='core-network-123', region='us-east-1'
            )

    @patch.object(routes_module, 'get_aws_client')
    async def test_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='There was an error getting AWS Core Network details'):
            await routes_module.get_cwan_routes(
                core_network_id='core-network-123', region='us-east-1', segment='segment-a'
            )

    @patch.object(routes_module, 'get_aws_client')
    async def test_invalid_segment(self, mock_get_client, mock_core_network):
        """Test error when segment not found in core network."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network

        with pytest.raises(ToolError, match='Segment invalid-segment not found'):
            await routes_module.get_cwan_routes(
                core_network_id='core-network-123', region='us-east-1', segment='invalid-segment'
            )

    @patch.object(routes_module, 'get_aws_client')
    async def test_invalid_nfg(self, mock_get_client, mock_core_network):
        """Test error when network function group not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network

        with pytest.raises(ToolError, match='Network function group invalid-nfg not found'):
            await routes_module.get_cwan_routes(
                core_network_id='core-network-123',
                region='us-east-1',
                network_function_group='invalid-nfg',
            )

    @patch.object(routes_module, 'get_aws_client')
    async def test_segment_with_routes(
        self, mock_get_client, mock_core_network, mock_routes_response
    ):
        """Test successful segment route retrieval."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = mock_routes_response

        result = await routes_module.get_cwan_routes(
            core_network_id='core-network-123', region='us-east-1', segment='segment-a'
        )

        assert result['core_network_id'] == 'core-network-123'
        assert result['region'] == 'us-east-1'
        assert result['segment']['name'] == 'segment-a'
        assert len(result['segment']['routes']) == 2
        assert result['segment']['routes'][0]['destination'] == '10.0.0.0/16'
        assert result['segment']['routes'][0]['target'] == 'attachment-123'
        assert result['segment']['routes'][0]['type'] == 'propagated'
        assert result['segment']['routes'][0]['state'] == 'active'

    @patch.object(routes_module, 'get_aws_client')
    async def test_nfg_with_routes(self, mock_get_client, mock_core_network, mock_routes_response):
        """Test successful NFG route retrieval."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = mock_routes_response

        result = await routes_module.get_cwan_routes(
            core_network_id='core-network-123', region='us-east-1', network_function_group='nfg-1'
        )

        assert result['network_function_group']['name'] == 'nfg-1'
        assert len(result['network_function_group']['routes']) == 2

    @patch.object(routes_module, 'get_aws_client')
    async def test_both_segment_and_nfg(
        self, mock_get_client, mock_core_network, mock_routes_response
    ):
        """Test with both segment and NFG provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = mock_routes_response

        result = await routes_module.get_cwan_routes(
            core_network_id='core-network-123',
            region='us-east-1',
            segment='segment-a',
            network_function_group='nfg-1',
        )

        assert 'segment' in result
        assert 'network_function_group' in result
        assert result['segment']['name'] == 'segment-a'
        assert result['network_function_group']['name'] == 'nfg-1'

    @patch.object(routes_module, 'get_aws_client')
    async def test_no_routes_found(self, mock_get_client, mock_core_network):
        """Test when no routes are found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = {'NetworkRoutes': []}

        result = await routes_module.get_cwan_routes(
            core_network_id='core-network-123', region='us-east-1', segment='segment-a'
        )

        assert result['segment']['routes'] == 'No network routes found with the given parameters.'

    @patch.object(routes_module, 'get_aws_client')
    async def test_with_profile_name(
        self, mock_get_client, mock_core_network, mock_routes_response
    ):
        """Test with custom profile name."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = mock_routes_response

        await routes_module.get_cwan_routes(
            core_network_id='core-network-123',
            region='us-east-1',
            segment='segment-a',
            profile_name='test-profile',
        )

        mock_get_client.assert_called_with(
            'networkmanager', region_name='us-east-1', profile_name='test-profile'
        )
