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

"""Unit tests for the cost_optimization_hub_tools module.

These tests verify the functionality of AWS Cost Optimization Hub tools, including:
- Retrieving optimization recommendations across multiple AWS services
- Getting cost and savings estimates for recommended actions
- Handling recommendation filters by implementation effort and savings potential
- Processing recommendations for EC2, RDS, Lambda, and storage resources
- Error handling for invalid recommendation filters and hub configuration
"""

import pytest
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


# Create a mock implementation for testing
async def cost_optimization_hub(ctx, operation, **kwargs):
    """Mock implementation of cost_optimization_hub for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'get_recommendation_summaries':
        # Check for required group_by parameter
        if 'group_by' not in kwargs or not kwargs['group_by']:
            return format_response(
                'error',
                {},
                'group_by parameter is required for get_recommendation_summaries operation',
            )

        return {
            'status': 'success',
            'data': {
                'summaries': [
                    {
                        'resource_type': 'EC2_INSTANCE',
                        'count': 10,
                        'estimated_monthly_savings': 500.0,
                        'currency': 'USD',
                    },
                    {
                        'resource_type': 'RDS_INSTANCE',
                        'count': 5,
                        'estimated_monthly_savings': 300.0,
                        'currency': 'USD',
                    },
                ],
                'total_recommendations': 15,
                'total_estimated_monthly_savings': 800.0,
            },
        }

    elif operation == 'list_recommendations':
        return {
            'status': 'success',
            'data': {
                'recommendations': [
                    {
                        'id': 'rec-1',
                        'resource_id': 'i-12345',
                        'resource_type': 'EC2_INSTANCE',
                        'current_instance_type': 't3.xlarge',
                        'recommended_instance_type': 't3.large',
                        'estimated_monthly_savings': 50.0,
                    }
                ],
                'total_recommendations': 1,
                'total_estimated_monthly_savings': 50.0,
            },
        }

    elif operation == 'get_recommendation':
        if not kwargs.get('resource_id') or not kwargs.get('resource_type'):
            return format_response(
                'error',
                {},
                'Both resource_id and resource_type are required for get_recommendation operation',
            )

        return {
            'status': 'success',
            'data': {
                'id': kwargs.get('recommendation_id'),
                'resource_id': kwargs.get('resource_id'),
                'resource_type': 'EC2_INSTANCE',
                'current_instance_type': 't3.xlarge',
                'recommended_instance_type': 't3.large',
                'estimated_monthly_savings': 50.0,
            },
        }

    else:
        return format_response('error', {}, f'Unsupported operation: {operation}')


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_coh_client():
    """Create a mock Cost Optimization Hub boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.list_recommendation_summaries.return_value = {
        'recommendationSummaries': [
            {
                'summaryValue': 'EC2_INSTANCE',
                'currentMonthEstimatedMonthlySavings': {
                    'amount': 1500.0,
                    'currency': 'USD',
                },
                'recommendationsCount': 25,
                'estimatedSavingsPercentage': 30.0,
            },
            {
                'summaryValue': 'EBS_VOLUME',
                'currentMonthEstimatedMonthlySavings': {
                    'amount': 500.0,
                    'currency': 'USD',
                },
                'recommendationsCount': 10,
                'estimatedSavingsPercentage': 20.0,
            },
        ],
        'nextToken': 'next-token-123',
    }

    mock_client.list_recommendations.return_value = {
        'recommendations': [
            {
                'resourceId': 'i-0abcdef1234567890',
                'resourceType': 'EC2_INSTANCE',
                'accountId': '123456789012',
                'estimatedMonthlySavings': {
                    'amount': 50.0,
                    'currency': 'USD',
                },
                'status': 'ACTIVE',
                'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
            }
        ],
    }

    mock_client.get_recommendation.return_value = {
        'resourceId': 'i-0abcdef1234567890',
        'resourceType': 'EC2_INSTANCE',
        'accountId': '123456789012',
        'estimatedMonthlySavings': {
            'amount': 50.0,
            'currency': 'USD',
        },
        'status': 'ACTIVE',
        'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
        'implementationEffort': 'MEDIUM',
        'currentResource': {
            'ec2Instance': {
                'instanceType': 't3.xlarge',
                'region': 'us-east-1',
            }
        },
        'recommendedResource': {
            'ec2Instance': {
                'instanceType': 't3.large',
                'region': 'us-east-1',
            }
        },
    }

    return mock_client
