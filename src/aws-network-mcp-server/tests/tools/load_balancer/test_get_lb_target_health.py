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

"""Test cases for the get_lb_target_health tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
lb_health_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.load_balancer.get_lb_target_health'
)

SAMPLE_TG_ARN = 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890'


class TestGetLbTargetHealth:
    """Test cases for get_lb_target_health function."""

    @pytest.fixture
    def sample_target_group(self):
        """Sample target group fixture."""
        return {
            'TargetGroupArn': SAMPLE_TG_ARN,
            'TargetGroupName': 'my-tg',
            'Protocol': 'HTTP',
            'Port': 80,
            'HealthCheckProtocol': 'HTTP',
            'HealthCheckPort': '80',
            'HealthCheckPath': '/health',
            'LoadBalancerArns': [
                'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/1234567890'
            ],
        }

    @pytest.fixture
    def sample_target_health(self):
        """Sample target health descriptions fixture."""
        return [
            {
                'Target': {'Id': 'i-1234567890abcdef0', 'Port': 80},
                'TargetHealth': {'State': 'healthy'},
            },
            {
                'Target': {'Id': 'i-0987654321fedcba0', 'Port': 80},
                'TargetHealth': {
                    'State': 'unhealthy',
                    'Reason': 'Target.ResponseCodeMismatch',
                    'Description': 'Health checks failed with these codes: [503]',
                },
            },
        ]

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_success(
        self, mock_get_client, sample_target_group, sample_target_health
    ):
        """Test successful target health retrieval."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_target_groups.return_value = {'TargetGroups': [sample_target_group]}
        mock_client.describe_target_health.return_value = {
            'TargetHealthDescriptions': sample_target_health
        }

        result = await lb_health_module.get_lb_target_health(
            target_group_arn=SAMPLE_TG_ARN, region='us-east-1'
        )

        assert result['target_group'] == sample_target_group
        assert result['targets'] == sample_target_health
        assert result['region'] == 'us-east-1'
        mock_get_client.assert_called_once_with('elbv2', 'us-east-1', None)

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_empty_targets(self, mock_get_client, sample_target_group):
        """Test target group with no registered targets."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_target_groups.return_value = {'TargetGroups': [sample_target_group]}
        mock_client.describe_target_health.return_value = {'TargetHealthDescriptions': []}

        result = await lb_health_module.get_lb_target_health(
            target_group_arn=SAMPLE_TG_ARN, region='us-east-1'
        )

        assert result['targets'] == []

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_with_profile(self, mock_get_client, sample_target_group):
        """Test target health with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_target_groups.return_value = {'TargetGroups': [sample_target_group]}
        mock_client.describe_target_health.return_value = {'TargetHealthDescriptions': []}

        await lb_health_module.get_lb_target_health(
            target_group_arn=SAMPLE_TG_ARN,
            region='eu-central-1',
            profile_name='test-profile',
        )

        mock_get_client.assert_called_once_with('elbv2', 'eu-central-1', 'test-profile')

    async def test_get_lb_target_health_invalid_arn(self):
        """Test invalid target group ARN validation."""
        with pytest.raises(
            ToolError,
            match='Invalid target_group_arn format',
        ):
            await lb_health_module.get_lb_target_health(
                target_group_arn='invalid-arn', region='us-east-1'
            )

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_not_found(self, mock_get_client):
        """Test target group not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_target_groups.return_value = {'TargetGroups': []}

        with pytest.raises(
            ToolError,
            match='Target group not found',
        ):
            await lb_health_module.get_lb_target_health(
                target_group_arn=SAMPLE_TG_ARN, region='us-east-1'
            )

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_target_groups.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(
            ToolError,
            match='Error getting target health. Error: ServiceUnavailableException. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await lb_health_module.get_lb_target_health(
                target_group_arn=SAMPLE_TG_ARN, region='us-east-1'
            )

    @patch.object(lb_health_module, 'get_aws_client')
    async def test_get_lb_target_health_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(
            ToolError,
            match='Error getting target health. Error: Invalid credentials. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await lb_health_module.get_lb_target_health(
                target_group_arn=SAMPLE_TG_ARN, region='us-east-1'
            )
