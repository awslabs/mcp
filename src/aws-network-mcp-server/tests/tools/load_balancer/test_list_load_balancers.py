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

"""Test cases for the list_load_balancers tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
lb_list_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.load_balancer.list_load_balancers'
)


class TestListLoadBalancers:
    """Test cases for list_load_balancers function."""

    @pytest.fixture
    def sample_load_balancers(self):
        """Sample load balancers fixture."""
        return [
            {
                'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/1234567890',
                'LoadBalancerName': 'my-alb',
                'Type': 'application',
                'Scheme': 'internet-facing',
                'State': {'Code': 'active'},
                'DNSName': 'my-alb-123.us-east-1.elb.amazonaws.com',
                'VpcId': 'vpc-12345678',
                'AvailabilityZones': [
                    {'ZoneName': 'us-east-1a', 'SubnetId': 'subnet-111'},
                    {'ZoneName': 'us-east-1b', 'SubnetId': 'subnet-222'},
                ],
                'SecurityGroups': ['sg-12345678'],
            },
            {
                'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/my-nlb/0987654321',
                'LoadBalancerName': 'my-nlb',
                'Type': 'network',
                'Scheme': 'internal',
                'State': {'Code': 'active'},
                'DNSName': 'my-nlb-456.us-east-1.elb.amazonaws.com',
                'VpcId': 'vpc-87654321',
                'AvailabilityZones': [
                    {'ZoneName': 'us-east-1a', 'SubnetId': 'subnet-333'},
                ],
            },
        ]

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_success(self, mock_get_client, sample_load_balancers):
        """Test successful load balancers listing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'LoadBalancers': sample_load_balancers}]

        result = await lb_list_module.list_load_balancers(region='us-east-1')

        assert result == {
            'load_balancers': sample_load_balancers,
            'count': 2,
            'region': 'us-east-1',
        }
        mock_get_client.assert_called_once_with('elbv2', 'us-east-1', None)

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_empty(self, mock_get_client):
        """Test listing when no load balancers exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'LoadBalancers': []}]

        result = await lb_list_module.list_load_balancers(region='us-west-2')

        assert result == {'load_balancers': [], 'count': 0, 'region': 'us-west-2'}

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_with_profile(self, mock_get_client, sample_load_balancers):
        """Test load balancers listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'LoadBalancers': sample_load_balancers}]

        await lb_list_module.list_load_balancers(
            region='eu-central-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('elbv2', 'eu-central-1', 'test-profile')

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_filter_by_type(
        self, mock_get_client, sample_load_balancers
    ):
        """Test filtering load balancers by type."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'LoadBalancers': sample_load_balancers}]

        result = await lb_list_module.list_load_balancers(
            region='us-east-1', lb_type='application'
        )

        assert result['count'] == 1
        assert result['load_balancers'][0]['Type'] == 'application'

    async def test_list_load_balancers_invalid_type(self):
        """Test invalid lb_type validation."""
        with pytest.raises(
            ToolError,
            match='Invalid lb_type "invalid"',
        ):
            await lb_list_module.list_load_balancers(region='us-east-1', lb_type='invalid')

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(
            ToolError,
            match='Error listing load balancers. Error: ServiceUnavailableException. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await lb_list_module.list_load_balancers(region='us-east-1')

    @patch.object(lb_list_module, 'get_aws_client')
    async def test_list_load_balancers_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(
            ToolError,
            match='Error listing load balancers. Error: Invalid credentials. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await lb_list_module.list_load_balancers(region='us-east-1')
