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

"""Test cases for the list_hosted_zones tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


hz_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.route53.list_hosted_zones'
)


class TestListHostedZones:
    """Test cases for list_hosted_zones function."""

    @pytest.fixture
    def sample_zones(self):
        """Sample hosted zones fixture."""
        return [
            {
                'Id': '/hostedzone/Z1234PUBLIC',
                'Name': 'example.com.',
                'ResourceRecordSetCount': 10,
                'Config': {'PrivateZone': False, 'Comment': 'Public zone'},
            },
            {
                'Id': '/hostedzone/Z5678PRIVATE',
                'Name': 'internal.example.com.',
                'ResourceRecordSetCount': 5,
                'Config': {'PrivateZone': True, 'Comment': 'Private zone'},
            },
        ]

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_success(self, mock_get_client, sample_zones):
        """Test successful hosted zones listing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HostedZones': sample_zones}]
        mock_client.get_hosted_zone.return_value = {
            'VPCs': [{'VPCId': 'vpc-123', 'VPCRegion': 'us-east-1'}]
        }

        result = await hz_module.list_hosted_zones()

        assert result['count'] == 2
        assert len(result['hosted_zones']) == 2
        assert result['hosted_zones'][0]['is_private'] is False
        assert result['hosted_zones'][0]['vpcs'] is None
        assert result['hosted_zones'][1]['is_private'] is True
        assert result['hosted_zones'][1]['vpcs'] == [
            {'vpc_id': 'vpc-123', 'vpc_region': 'us-east-1'}
        ]
        mock_get_client.assert_called_once_with('route53', None, None)

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_empty(self, mock_get_client):
        """Test listing when no hosted zones exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HostedZones': []}]

        result = await hz_module.list_hosted_zones()

        assert result == {'hosted_zones': [], 'count': 0}

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_with_profile(self, mock_get_client, sample_zones):
        """Test hosted zones listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HostedZones': sample_zones}]
        mock_client.get_hosted_zone.return_value = {'VPCs': []}

        await hz_module.list_hosted_zones(profile_name='test-profile')

        mock_get_client.assert_called_once_with('route53', None, 'test-profile')

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_filter_public(self, mock_get_client, sample_zones):
        """Test filtering by public zone type."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HostedZones': sample_zones}]

        result = await hz_module.list_hosted_zones(zone_type='public')

        assert result['count'] == 1
        assert result['hosted_zones'][0]['name'] == 'example.com.'
        assert result['hosted_zones'][0]['is_private'] is False

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_filter_private(self, mock_get_client, sample_zones):
        """Test filtering by private zone type with VPC associations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'HostedZones': sample_zones}]
        mock_client.get_hosted_zone.return_value = {
            'VPCs': [
                {'VPCId': 'vpc-aaa', 'VPCRegion': 'us-east-1'},
                {'VPCId': 'vpc-bbb', 'VPCRegion': 'us-west-2'},
            ]
        }

        result = await hz_module.list_hosted_zones(zone_type='private')

        assert result['count'] == 1
        assert result['hosted_zones'][0]['is_private'] is True
        assert len(result['hosted_zones'][0]['vpcs']) == 2

    async def test_list_hosted_zones_invalid_zone_type(self):
        """Test invalid zone_type validation."""
        with pytest.raises(ToolError, match='Invalid zone_type "invalid"'):
            await hz_module.list_hosted_zones(zone_type='invalid')

    @patch.object(hz_module, 'get_aws_client')
    async def test_list_hosted_zones_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error listing hosted zones.*AccessDenied'):
            await hz_module.list_hosted_zones()
