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

"""Test cases for the get_all_cloudwan_routes tool."""

import importlib
import pytest
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
routes_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_all_cloudwan_routes'
)


@pytest.fixture
def mock_client():
    """Create a mock AWS client."""
    client = MagicMock()
    with patch.object(routes_module, 'get_aws_client', return_value=client):
        yield client


class TestGetAllCloudwanRoutes:
    """Test cases for get_all_cloudwan_routes function."""

    async def test_success_with_routes(self, mock_client):
        """Test successful retrieval with routes."""
        mock_client.get_core_network.return_value = {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-123',
                'Segments': [{'Name': 'seg-a'}],
                'Edges': [{'EdgeLocation': 'us-east-1'}],
            }
        }
        mock_client.get_network_routes.return_value = {
            'NetworkRoutes': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    'Type': 'PROPAGATED',
                    'State': 'ACTIVE',
                    'Destinations': [{'CoreNetworkAttachmentId': 'att-123'}],
                }
            ]
        }

        result = await routes_module.get_all_cwan_routes('us-east-1', 'core-123')

        assert result['core_network_id'] == 'core-123'
        routes = result['regions']['us-east-1']['segments']['seg-a']['routes']
        assert len(routes) == 1
        assert routes[0]['destination'] == '10.0.0.0/16'
        assert routes[0]['target'] == 'att-123'

    async def test_empty_segments_and_edges(self, mock_client):
        """Test handling of empty segments and edges."""
        mock_client.get_core_network.return_value = {
            'CoreNetwork': {'GlobalNetworkId': 'global-123', 'Segments': [], 'Edges': []}
        }

        result = await routes_module.get_all_cwan_routes('us-east-1', 'core-123')

        assert result['regions'] == {}

    async def test_no_routes(self, mock_client):
        """Test handling when segments have no routes."""
        mock_client.get_core_network.return_value = {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-123',
                'Segments': [{'Name': 'seg-a'}],
                'Edges': [{'EdgeLocation': 'us-east-1'}],
            }
        }
        mock_client.get_network_routes.return_value = {'NetworkRoutes': []}

        result = await routes_module.get_all_cwan_routes('us-east-1', 'core-123')

        assert result['regions']['us-east-1']['segments']['seg-a']['routes'] == []

    async def test_route_error_handling(self, mock_client):
        """Test handling of route retrieval errors."""
        mock_client.get_core_network.return_value = {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-123',
                'Segments': [{'Name': 'seg-a'}],
                'Edges': [{'EdgeLocation': 'us-east-1'}],
            }
        }
        mock_client.get_network_routes.side_effect = Exception('Access denied')

        result = await routes_module.get_all_cwan_routes('us-east-1', 'core-123')

        assert result['regions']['us-east-1']['segments']['seg-a']['routes'] == []

    async def test_missing_fields(self, mock_client):
        """Test handling of routes with missing fields."""
        mock_client.get_core_network.return_value = {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-123',
                'Segments': [{'Name': 'seg-a'}],
                'Edges': [{'EdgeLocation': 'us-east-1'}],
            }
        }
        mock_client.get_network_routes.return_value = {
            'NetworkRoutes': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    # Missing Type, State, and Destinations
                }
            ]
        }

        result = await routes_module.get_all_cwan_routes('us-east-1', 'core-123')

        routes = result['regions']['us-east-1']['segments']['seg-a']['routes']
        assert routes[0]['type'] == ''
        assert routes[0]['state'] == ''
        assert routes[0]['target'] is None
