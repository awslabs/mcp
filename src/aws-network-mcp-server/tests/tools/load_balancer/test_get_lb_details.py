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

"""Test cases for the get_lb_details tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
lb_details_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.load_balancer.get_lb_details'
)

SAMPLE_ALB_ARN = (
    'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/1234567890'
)


class TestGetLbDetails:
    """Test cases for get_lb_details function."""

    @pytest.fixture
    def sample_alb(self):
        """Sample ALB fixture."""
        return {
            'LoadBalancerArn': SAMPLE_ALB_ARN,
            'LoadBalancerName': 'my-alb',
            'Type': 'application',
            'Scheme': 'internet-facing',
            'State': {'Code': 'active'},
            'DNSName': 'my-alb-123.us-east-1.elb.amazonaws.com',
            'VpcId': 'vpc-12345678',
            'SecurityGroups': ['sg-12345678'],
            'AvailabilityZones': [
                {'ZoneName': 'us-east-1a', 'SubnetId': 'subnet-111'},
            ],
        }

    @pytest.fixture
    def sample_listeners(self):
        """Sample listeners fixture."""
        return [
            {
                'ListenerArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/my-alb/1234567890/1111111111',
                'Protocol': 'HTTPS',
                'Port': 443,
                'DefaultActions': [{'Type': 'forward'}],
            },
        ]

    @pytest.fixture
    def sample_target_groups(self):
        """Sample target groups fixture."""
        return [
            {
                'TargetGroupArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890',
                'TargetGroupName': 'my-tg',
                'Protocol': 'HTTPS',
                'Port': 443,
            },
        ]

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_success(
        self, mock_get_client, sample_alb, sample_listeners, sample_target_groups
    ):
        """Test successful load balancer details retrieval."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.return_value = {'LoadBalancers': [sample_alb]}

        mock_paginator_listeners = MagicMock()
        mock_paginator_tgs = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'describe_listeners':
                return mock_paginator_listeners
            elif api_name == 'describe_target_groups':
                return mock_paginator_tgs
            return MagicMock()

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        mock_paginator_listeners.paginate.return_value = [{'Listeners': sample_listeners}]
        mock_paginator_tgs.paginate.return_value = [{'TargetGroups': sample_target_groups}]

        result = await lb_details_module.get_lb_details(lb_arn=SAMPLE_ALB_ARN, region='us-east-1')

        assert result['load_balancer']['LoadBalancerName'] == 'my-alb'
        assert result['listeners'] == sample_listeners
        assert result['listeners_error'] is None
        assert result['target_groups'] == sample_target_groups
        assert result['target_groups_error'] is None
        assert result['region'] == 'us-east-1'
        mock_get_client.assert_called_once_with('elbv2', 'us-east-1', None)

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_with_profile(self, mock_get_client, sample_alb):
        """Test load balancer details with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.return_value = {'LoadBalancers': [sample_alb]}
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Listeners': [], 'TargetGroups': []}]

        await lb_details_module.get_lb_details(
            lb_arn=SAMPLE_ALB_ARN, region='us-east-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('elbv2', 'us-east-1', 'test-profile')

    async def test_get_lb_details_invalid_arn(self):
        """Test invalid ARN validation."""
        with pytest.raises(
            ToolError,
            match='Invalid lb_arn format',
        ):
            await lb_details_module.get_lb_details(lb_arn='invalid-arn', region='us-east-1')

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_not_found(self, mock_get_client):
        """Test load balancer not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.return_value = {'LoadBalancers': []}

        with pytest.raises(
            ToolError,
            match='Load balancer not found',
        ):
            await lb_details_module.get_lb_details(lb_arn=SAMPLE_ALB_ARN, region='us-east-1')

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_partial_failure_listeners(
        self, mock_get_client, sample_alb, sample_target_groups
    ):
        """Test partial failure when listeners retrieval fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.return_value = {'LoadBalancers': [sample_alb]}

        mock_paginator_listeners = MagicMock()
        mock_paginator_tgs = MagicMock()

        def get_paginator_side_effect(api_name):
            if api_name == 'describe_listeners':
                return mock_paginator_listeners
            elif api_name == 'describe_target_groups':
                return mock_paginator_tgs
            return MagicMock()

        mock_client.get_paginator.side_effect = get_paginator_side_effect
        mock_paginator_listeners.paginate.side_effect = Exception('AccessDenied')
        mock_paginator_tgs.paginate.return_value = [{'TargetGroups': sample_target_groups}]

        result = await lb_details_module.get_lb_details(lb_arn=SAMPLE_ALB_ARN, region='us-east-1')

        assert result['listeners'] is None
        assert result['listeners_error'] == 'AccessDenied'
        assert result['target_groups'] == sample_target_groups
        assert result['target_groups_error'] is None

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_glb_no_security_groups(self, mock_get_client):
        """Test GLB has security groups set to None."""
        glb = {
            'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/gwy/my-glb/1234567890',
            'LoadBalancerName': 'my-glb',
            'Type': 'gateway',
            'Scheme': 'internal',
            'State': {'Code': 'active'},
            'DNSName': 'my-glb.us-east-1.elb.amazonaws.com',
            'VpcId': 'vpc-12345678',
        }
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.return_value = {'LoadBalancers': [glb]}
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Listeners': [], 'TargetGroups': []}]

        result = await lb_details_module.get_lb_details(
            lb_arn='arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/gwy/my-glb/1234567890',
            region='us-east-1',
        )

        assert result['load_balancer']['SecurityGroups'] is None

    @patch.object(lb_details_module, 'get_aws_client')
    async def test_get_lb_details_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_load_balancers.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(
            ToolError,
            match='Error getting load balancer details. Error: ServiceUnavailableException. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await lb_details_module.get_lb_details(lb_arn=SAMPLE_ALB_ARN, region='us-east-1')
