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

"""Unit tests for the compute_optimizer_tools module.

These tests verify the functionality of the AWS Compute Optimizer tools, including:
- Retrieving EC2 instance optimization recommendations with performance metrics
- Getting Auto Scaling Group recommendations for instance type optimization
- Fetching EBS volume recommendations for storage optimization
- Getting Lambda function recommendations for memory optimization
- Handling recommendation filters, account scoping, and performance risk assessment
- Error handling for API exceptions and invalid parameters
"""

import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
    compute_optimizer_server,
    get_ec2_instance_recommendations,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_co_client():
    """Create a mock Compute Optimizer boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_ec2_instance_recommendations.return_value = {
        'instanceRecommendations': [
            {
                'accountId': '123456789012',
                'currentInstanceType': 't3.micro',
                'finding': 'OVERPROVISIONED',
                'instanceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890',
                'instanceName': 'test-instance',
                'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
                'recommendationOptions': [
                    {
                        'instanceType': 't2.nano',
                        'performanceRisk': 'LOW',
                        'projectedUtilization': 45.0,
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 30.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 10.50,
                            },
                        },
                    }
                ],
            }
        ],
        'nextToken': 'next-token-123',
    }

    mock_client.get_auto_scaling_group_recommendations.return_value = {
        'autoScalingGroupRecommendations': [
            {
                'accountId': '123456789012',
                'autoScalingGroupArn': 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:123',
                'autoScalingGroupName': 'test-asg',
                'currentInstanceType': 't3.medium',
                'finding': 'NOT_OPTIMIZED',
                'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
                'recommendationOptions': [
                    {
                        'instanceType': 't3.small',
                        'performanceRisk': 'MEDIUM',
                        'projectedUtilization': 60.0,
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 25.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 15.75,
                            },
                        },
                    }
                ],
            }
        ],
    }

    mock_client.get_ebs_volume_recommendations.return_value = {
        'volumeRecommendations': [
            {
                'accountId': '123456789012',
                'volumeArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-0abcdef1234567890',
                'currentConfiguration': {
                    'volumeType': 'gp2',
                    'volumeSize': 100,
                    'volumeBaselineIOPS': 300,
                    'volumeBurstIOPS': 3000,
                },
                'finding': 'OVERPROVISIONED',
                'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
                'recommendationOptions': [
                    {
                        'configuration': {
                            'volumeType': 'gp3',
                            'volumeSize': 50,
                            'volumeBaselineIOPS': 3000,
                        },
                        'performanceRisk': 'LOW',
                        'savingsOpportunity': {
                            'savingsOpportunityPercentage': 40.0,
                            'estimatedMonthlySavings': {
                                'currency': 'USD',
                                'value': 8.20,
                            },
                        },
                    }
                ],
            }
        ],
    }

    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


# We're not directly testing the compute_optimizer decorated function anymore
# Instead, we test the individual functions directly


@pytest.mark.asyncio
class TestGetEC2InstanceRecommendations:
    """Tests for get_ec2_instance_recommendations function."""

    async def test_get_ec2_instance_recommendations_with_filters(
        self, mock_context, mock_co_client
    ):
        """Test get_ec2_instance_recommendations with filters."""
        # Setup
        filters = '[{"Name":"Finding","Values":["OVERPROVISIONED"]}]'
        account_ids = '["123456789012"]'
        max_results = 10
        next_token = 'token-123'

        # Execute
        result = await get_ec2_instance_recommendations(
            mock_context,
            mock_co_client,
            max_results,
            filters,
            account_ids,
            next_token,
        )

        # Assert
        mock_co_client.get_ec2_instance_recommendations.assert_called_once()
        call_kwargs = mock_co_client.get_ec2_instance_recommendations.call_args[1]

        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['filters'] == json.loads(filters)
        assert call_kwargs['accountIds'] == json.loads(account_ids)
        assert call_kwargs['nextToken'] == next_token

        # Check result format
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert len(result['data']['recommendations']) == 1
        assert result['data']['next_token'] == 'next-token-123'


def test_compute_optimizer_server_initialization():
    """Test that the compute_optimizer_server is properly initialized."""
    # Verify the server name
    assert compute_optimizer_server.name == 'compute-optimizer-tools'

    # Verify the server instructions
    assert compute_optimizer_server.instructions and (
        'Tools for working with AWS Compute Optimizer API' in compute_optimizer_server.instructions
    )
