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
"""Test cases for simulate_cloud_wan_route_change tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
simulate_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.simulate_cloud_wan_route_change'
)


class TestSimulateCloudWanRouteChange:
    """Test cases for simulate_cloud_wan_route_change function."""

    @pytest.fixture
    def mock_core_network(self):
        """Mock core network response."""
        return {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-network-123',
                'Segments': [
                    {'Name': 'segment-a', 'EdgeLocations': ['us-east-1', 'us-west-2']},
                    {'Name': 'segment-b', 'EdgeLocations': ['us-east-1']},
                ],
            }
        }

    @pytest.fixture
    def mock_routes(self):
        """Mock network routes response."""
        return {
            'NetworkRoutes': [
                {
                    'DestinationCidrBlock': '10.0.0.0/16',
                    'Destinations': [{'CoreNetworkAttachmentId': 'attachment-123'}],
                    'Type': 'PROPAGATED',
                    'State': 'ACTIVE',
                },
                {
                    'DestinationCidrBlock': '10.1.0.0/16',
                    'Destinations': [{'TransitGatewayAttachmentId': 'attachment-456'}],
                    'Type': 'PROPAGATED',
                    'State': 'ACTIVE',
                },
            ]
        }

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_move_attachment_between_segments(
        self, mock_format_routes, mock_get_client, mock_core_network
    ):
        """Test moving attachment from one segment to another."""

        def mock_get_routes(**kwargs):
            segment_name = kwargs['RouteTableIdentifier']['CoreNetworkSegmentEdge']['SegmentName']
            if segment_name == 'segment-a':
                return {
                    'NetworkRoutes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'Destinations': [{'CoreNetworkAttachmentId': 'attachment-123'}],
                            'Type': 'PROPAGATED',
                            'State': 'ACTIVE',
                        }
                    ]
                }
            return {'NetworkRoutes': []}

        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.side_effect = mock_get_routes
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        changes = [{'attachment_id': 'attachment-123', 'segment': 'segment-b'}]

        result = await simulate_module.simulate_cwan_route_change(
            changes=changes,
            region='us-east-1',
            cloudwan_region='us-east-1',
            core_network_id='core-123',
        )

        assert result['summary']['total_routes_moved'] == 1
        assert result['summary']['region'] == 'us-east-1'
        assert result['changes'][0]['action'] == 'moved'
        assert result['changes'][0]['from'] == 'segment-a'
        assert result['changes'][0]['to'] == 'segment-b'

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_remove_attachment(self, mock_format_routes, mock_get_client, mock_core_network):
        """Test removing attachment completely."""

        def mock_get_routes(**kwargs):
            segment_name = kwargs['RouteTableIdentifier']['CoreNetworkSegmentEdge']['SegmentName']
            if segment_name == 'segment-a':
                return {
                    'NetworkRoutes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'Destinations': [{'CoreNetworkAttachmentId': 'attachment-123'}],
                            'Type': 'PROPAGATED',
                            'State': 'ACTIVE',
                        }
                    ]
                }
            return {'NetworkRoutes': []}

        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.side_effect = mock_get_routes
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        changes = [{'attachment_id': 'attachment-123'}]

        result = await simulate_module.simulate_cwan_route_change(
            changes=changes,
            region='us-east-1',
            cloudwan_region='us-east-1',
            core_network_id='core-123',
        )

        assert result['summary']['total_routes_moved'] == 1
        assert result['changes'][0]['action'] == 'removed'
        assert result['changes'][0]['from'] == 'segment-a'
        assert 'to' not in result['changes'][0]

    @patch.object(simulate_module, 'get_aws_client')
    @pytest.mark.asyncio
    async def test_core_network_error(self, mock_get_client):
        """Test error handling when getting core network fails."""
        mock_client = MagicMock()
        mock_client.get_core_network.side_effect = Exception('Network error')
        mock_get_client.return_value = mock_client

        with pytest.raises(ToolError) as exc_info:
            await simulate_module.simulate_cwan_route_change(
                changes=[],
                region='us-east-1',
                cloudwan_region='us-east-1',
                core_network_id='core-123',
            )

        assert 'There was an error when trying to get the core network details' in str(
            exc_info.value
        )

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_no_matching_attachments(
        self, mock_format_routes, mock_get_client, mock_core_network
    ):
        """Test when no attachments match the changes."""
        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = {'NetworkRoutes': []}
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        changes = [{'attachment_id': 'non-existent', 'segment': 'segment-b'}]

        result = await simulate_module.simulate_cwan_route_change(
            changes=changes,
            region='us-east-1',
            cloudwan_region='us-east-1',
            core_network_id='core-123',
        )

        assert result['summary']['total_routes_moved'] == 0
        assert len(result['changes']) == 0

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_region_not_in_segment(self, mock_format_routes, mock_get_client):
        """Test when region is not in any segment edge locations."""
        mock_core_network = {
            'CoreNetwork': {
                'GlobalNetworkId': 'global-network-123',
                'Segments': [{'Name': 'segment-a', 'EdgeLocations': ['us-west-2']}],
            }
        }

        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        result = await simulate_module.simulate_cwan_route_change(
            changes=[], region='us-east-1', cloudwan_region='us-east-1', core_network_id='core-123'
        )

        assert result['summary']['total_routes_moved'] == 0
        mock_client.get_network_routes.assert_not_called()

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_multiple_changes(self, mock_format_routes, mock_get_client, mock_core_network):
        """Test multiple attachment changes."""

        def mock_get_routes(**kwargs):
            segment_name = kwargs['RouteTableIdentifier']['CoreNetworkSegmentEdge']['SegmentName']
            if segment_name == 'segment-a':
                return {
                    'NetworkRoutes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'Destinations': [{'CoreNetworkAttachmentId': 'attachment-123'}],
                            'Type': 'PROPAGATED',
                            'State': 'ACTIVE',
                        },
                        {
                            'DestinationCidrBlock': '10.1.0.0/16',
                            'Destinations': [{'TransitGatewayAttachmentId': 'attachment-456'}],
                            'Type': 'PROPAGATED',
                            'State': 'ACTIVE',
                        },
                    ]
                }
            return {'NetworkRoutes': []}

        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.side_effect = mock_get_routes
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        changes = [
            {'attachment_id': 'attachment-123', 'segment': 'segment-b'},
            {'attachment_id': 'attachment-456'},
        ]

        result = await simulate_module.simulate_cwan_route_change(
            changes=changes,
            region='us-east-1',
            cloudwan_region='us-east-1',
            core_network_id='core-123',
        )

        assert result['summary']['total_routes_moved'] == 2
        assert len(result['changes']) == 2
        assert result['changes'][0]['action'] == 'moved'
        assert result['changes'][1]['action'] == 'removed'

    @patch.object(simulate_module, 'get_aws_client')
    @patch.object(simulate_module, 'format_routes')
    @pytest.mark.asyncio
    async def test_with_profile_name(self, mock_format_routes, mock_get_client, mock_core_network):
        """Test function with profile name parameter."""
        mock_client = MagicMock()
        mock_client.get_core_network.return_value = mock_core_network
        mock_client.get_network_routes.return_value = {'NetworkRoutes': []}
        mock_get_client.return_value = mock_client
        mock_format_routes.side_effect = lambda x, y: x

        await simulate_module.simulate_cwan_route_change(
            changes=[],
            region='us-east-1',
            cloudwan_region='us-east-1',
            core_network_id='core-123',
            profile_name='test-profile',
        )

        mock_get_client.assert_called_with('networkmanager', 'us-east-1', 'test-profile')
