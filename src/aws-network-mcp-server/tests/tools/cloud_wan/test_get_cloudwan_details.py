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

"""Test cases for the get_cloudwan_details tool."""

import json
import pytest
from awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details import (
    get_cloudwan_details,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetCloudwanDetails:
    """Test cases for get_cloudwan_details function."""

    @pytest.fixture
    def mock_nm_client(self):
        """Mock NetworkManager client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_core_network(self):
        """Sample core network fixture."""
        return {
            'CoreNetworkId': 'core-network-12345678',
            'CoreNetworkArn': 'arn:aws:networkmanager::123456789012:core-network/core-network-12345678',
            'Description': 'Test core network',
            'State': 'AVAILABLE',
            'Segments': [
                {'Name': 'production', 'EdgeLocations': ['us-east-1', 'us-west-2']},
                {'Name': 'staging', 'EdgeLocations': ['us-east-1']},
            ],
            'Edges': [
                {'EdgeLocation': 'us-east-1', 'Asn': 64512},
                {'EdgeLocation': 'us-west-2', 'Asn': 64513},
            ],
        }

    @pytest.fixture
    def sample_policy_document(self):
        """Sample policy document fixture."""
        return {
            'version': '2021.12',
            'core-network-configuration': {
                'asn-ranges': ['64512-65534'],
                'edge-locations': [{'location': 'us-east-1'}, {'location': 'us-west-2'}],
            },
            'segments': [
                {'name': 'production', 'require-attachment-acceptance': False},
                {'name': 'staging', 'require-attachment-acceptance': True},
            ],
            'segment-actions': [
                {
                    'action': 'create-route',
                    'segment': 'production',
                    'destination-cidr-blocks': ['10.0.0.0/8'],
                }
            ],
        }

    @pytest.fixture
    def sample_attachments(self):
        """Sample attachments fixture."""
        return [
            {
                'AttachmentId': 'attachment-12345678',
                'CoreNetworkId': 'core-network-12345678',
                'AttachmentType': 'VPC',
                'State': 'AVAILABLE',
                'ResourceArn': 'arn:aws:ec2:us-east-1:123456789012:vpc/vpc-12345678',
                'SegmentName': 'production',
            },
            {
                'AttachmentId': 'attachment-87654321',
                'CoreNetworkId': 'core-network-12345678',
                'AttachmentType': 'SITE_TO_SITE_VPN',
                'State': 'AVAILABLE',
                'ResourceArn': 'arn:aws:ec2:us-west-2:123456789012:vpn-connection/vpn-12345678',
                'SegmentName': 'staging',
            },
        ]

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_success(
        self,
        mock_get_client,
        mock_nm_client,
        sample_core_network,
        sample_policy_document,
        sample_attachments,
    ):
        """Test successful Cloud WAN details retrieval."""
        mock_get_client.return_value = mock_nm_client

        mock_nm_client.get_core_network.return_value = {'CoreNetwork': sample_core_network}
        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(sample_policy_document)}
        }
        mock_nm_client.list_attachments.return_value = {
            'Attachments': sample_attachments,
            'NextToken': None,
        }

        result = await get_cloudwan_details(
            core_network_id='core-network-12345678', core_network_region='us-east-1'
        )

        assert 'core_network' in result
        assert 'live_policy' in result
        assert 'attachments' in result
        assert 'next_token' in result

        assert result['core_network'] == sample_core_network
        assert result['live_policy'] == sample_policy_document
        assert result['attachments'] == sample_attachments
        assert result['next_token'] is None

        mock_get_client.assert_called_once_with('networkmanager', 'us-east-1', None)
        mock_nm_client.get_core_network.assert_called_once_with(
            CoreNetworkId='core-network-12345678'
        )
        mock_nm_client.get_core_network_policy.assert_called_once_with(
            CoreNetworkId='core-network-12345678', Alias='LIVE'
        )
        mock_nm_client.list_attachments.assert_called_once_with(
            CoreNetworkId='core-network-12345678'
        )

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_with_next_token(
        self, mock_get_client, mock_nm_client, sample_attachments
    ):
        """Test pagination with next_token parameter."""
        mock_get_client.return_value = mock_nm_client

        mock_nm_client.list_attachments.return_value = {
            'Attachments': sample_attachments[1:],  # Second page of results
            'NextToken': None,  # No more pages
        }

        result = await get_cloudwan_details(
            core_network_id='core-network-12345678',
            core_network_region='us-east-1',
            next_token='some-token',
        )

        # Should only return attachments when next_token is provided
        assert 'attachments' in result
        assert 'next_token' in result
        assert 'core_network' not in result
        assert 'live_policy' not in result

        assert result['attachments'] == sample_attachments[1:]
        assert result['next_token'] is None

        mock_nm_client.list_attachments.assert_called_once_with(
            CoreNetworkId='core-network-12345678', NextToken='some-token'
        )
        # Should not call other methods when paginating
        mock_nm_client.get_core_network.assert_not_called()
        mock_nm_client.get_core_network_policy.assert_not_called()

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_with_profile(
        self,
        mock_get_client,
        mock_nm_client,
        sample_core_network,
        sample_policy_document,
        sample_attachments,
    ):
        """Test Cloud WAN details retrieval with AWS profile."""
        mock_get_client.return_value = mock_nm_client

        mock_nm_client.get_core_network.return_value = {'CoreNetwork': sample_core_network}
        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(sample_policy_document)}
        }
        mock_nm_client.list_attachments.return_value = {
            'Attachments': sample_attachments,
            'NextToken': 'next-page-token',
        }

        result = await get_cloudwan_details(
            core_network_id='core-network-12345678',
            core_network_region='us-west-2',
            profile_name='test-profile',
        )

        assert result['next_token'] == 'next-page-token'
        mock_get_client.assert_called_once_with('networkmanager', 'us-west-2', 'test-profile')

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_core_network_not_found(
        self, mock_get_client, mock_nm_client
    ):
        """Test error handling when core network is not found."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network.side_effect = Exception(
            'CoreNetworkNotFoundException: Core network not found'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_cloudwan_details(
                core_network_id='core-network-nonexistent', core_network_region='us-east-1'
            )

        assert 'There was an error getting AWS Core Network details' in str(exc_info.value)
        assert 'VALIDATE parameter information before continuing' in str(exc_info.value)
        assert 'CoreNetworkNotFoundException: Core network not found' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_policy_parse_error(
        self, mock_get_client, mock_nm_client, sample_core_network
    ):
        """Test error handling for invalid policy JSON."""
        mock_get_client.return_value = mock_nm_client

        mock_nm_client.get_core_network.return_value = {'CoreNetwork': sample_core_network}
        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': 'invalid-json{'}
        }

        with pytest.raises(ToolError) as exc_info:
            await get_cloudwan_details(
                core_network_id='core-network-12345678', core_network_region='us-east-1'
            )

        assert 'There was an error getting AWS Core Network details' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_access_denied(self, mock_get_client, mock_nm_client):
        """Test error handling for access denied."""
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network.side_effect = Exception(
            'AccessDenied: User not authorized'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_cloudwan_details(
                core_network_id='core-network-12345678', core_network_region='us-east-1'
            )

        assert 'There was an error getting AWS Core Network details' in str(exc_info.value)
        assert 'AccessDenied: User not authorized' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_get_cloudwan_details_empty_attachments(
        self, mock_get_client, mock_nm_client, sample_core_network, sample_policy_document
    ):
        """Test handling of core network with no attachments."""
        mock_get_client.return_value = mock_nm_client

        mock_nm_client.get_core_network.return_value = {'CoreNetwork': sample_core_network}
        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(sample_policy_document)}
        }
        mock_nm_client.list_attachments.return_value = {'Attachments': [], 'NextToken': None}

        result = await get_cloudwan_details(
            core_network_id='core-network-12345678', core_network_region='us-east-1'
        )

        assert result['attachments'] == []
        assert result['next_token'] is None

    async def test_parameter_validation(self):
        """Test parameter validation for required fields."""
        # This test checks that the function signature enforces required parameters
        with pytest.raises(TypeError):
            await get_cloudwan_details()  # Missing required parameters

        with pytest.raises(TypeError):
            await get_cloudwan_details(core_network_id='test')  # Missing core_network_region
