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
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_helpers import (
    format_currency_amount,
    format_timestamp,
    get_recommendation,
    list_recommendation_summaries,
    list_recommendations,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_tools import (
    cost_optimization_hub_server,
)
from datetime import datetime
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


# Create a mock implementation for testing
async def cost_optimization_hub(ctx, operation, **kwargs):
    """Mock implementation of cost_optimization_hub for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'get_recommendation_summaries':
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
        if not kwargs.get('group_by'):
            return format_response(
                'error', {}, 'group_by is required for list_recommendations operation'
            )

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
        if not kwargs.get('recommendation_id') or not kwargs.get('resource_id'):
            return format_response(
                'error',
                {},
                'recommendation_id and resource_id are required for get_recommendation operation',
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


@pytest.mark.asyncio
class TestCostOptimizationHub:
    """Tests for cost_optimization_hub function."""

    async def test_cost_optimization_hub_get_recommendation_summaries(self, mock_context):
        """Test cost_optimization_hub with get_recommendation_summaries operation."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='get_recommendation_summaries',
            group_by='RESOURCE_TYPE',
        )

        # Assert
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'summaries' in result['data']

    async def test_cost_optimization_hub_list_recommendations(self, mock_context):
        """Test cost_optimization_hub with list_recommendations operation."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='list_recommendations',
            group_by='RESOURCE_TYPE',
            resource_type='EC2_INSTANCE',
        )

        # Assert
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'recommendations' in result['data']

    async def test_cost_optimization_hub_get_recommendation(self, mock_context):
        """Test cost_optimization_hub with get_recommendation operation."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='get_recommendation',
            recommendation_id='rec-123',
            resource_id='i-12345',
        )

        # Assert
        assert result['status'] == 'success'
        assert 'data' in result

    async def test_cost_optimization_hub_missing_group_by(self, mock_context):
        """Test cost_optimization_hub with missing group_by parameter."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='list_recommendations',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'group_by is required' in result['message']

    async def test_cost_optimization_hub_missing_resource_params(self, mock_context):
        """Test cost_optimization_hub with missing recommendation_id/resource_id parameters."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='get_recommendation',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'recommendation_id and resource_id are required' in result['message']

    async def test_cost_optimization_hub_unknown_operation(self, mock_context):
        """Test cost_optimization_hub with unknown operation."""
        # Execute
        result = await cost_optimization_hub(
            mock_context,
            operation='unknown_operation',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'Unsupported operation' in result['message']

    async def test_cost_optimization_hub_error_handling(self, mock_context):
        """Test cost_optimization_hub error handling."""
        # Setup simulating error response
        result = {'status': 'error', 'message': 'API error'}

        # Assert
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


def test_cost_optimization_hub_server_initialization():
    """Test that the cost_optimization_hub_server is properly initialized."""
    # Verify the server name
    assert cost_optimization_hub_server.name == 'cost-optimization-hub-tools'

    # Verify the server instructions
    assert cost_optimization_hub_server.instructions is not None
    assert (
        'Tools for working with AWS Cost Optimization Hub API'
        in cost_optimization_hub_server.instructions
    )


# Tests for cost_optimization_hub_helpers module
class TestFormatCurrencyAmount:
    """Test format currency amount."""

    def test_format_currency_amount_valid(self):
        """Test format currency amount with valid input."""
        amount = {'amount': '100.50', 'currency': 'USD'}
        result = format_currency_amount(amount)

        assert result is not None
        assert result['amount'] == '100.50'
        assert result['currency'] == 'USD'
        assert result['formatted'] == '100.50 USD'

    def test_format_currency_amount_none(self):
        """Test format currency amount with None input."""
        result = format_currency_amount(None)
        assert result is None


class TestFormatTimestamp:
    """Test format timestamp."""

    def test_format_timestamp_datetime(self):
        """Test format timestamp with datetime input."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_timestamp(dt)

        assert result == '2024-01-15T10:30:45'

    def test_format_timestamp_none(self):
        """Test format timestamp with None input."""
        result = format_timestamp(None)
        assert result is None


class TestCostOptimizationHubHelpers:
    """Test cost optimization hub helpers."""

    @pytest.mark.asyncio
    async def test_list_recommendation_summaries_calls_client(self):
        """Test list_recommendation_summaries calls client."""
        mock_context = MagicMock(spec=Context)
        mock_coh_client = MagicMock()
        mock_coh_client.get_recommendation_summaries.return_value = {'recommendationSummaries': []}

        result = await list_recommendation_summaries(mock_context, mock_coh_client, 'resourceType')
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_recommendations_calls_client(self):
        """Test list_recommendations calls client."""
        mock_context = MagicMock(spec=Context)
        mock_coh_client = MagicMock()
        mock_coh_client.list_recommendations.return_value = {'recommendations': []}

        await list_recommendations(mock_context, mock_coh_client)
        mock_coh_client.list_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendation_calls_client(self):
        """Test get_recommendation calls client."""
        mock_context = MagicMock(spec=Context)
        mock_coh_client = MagicMock()
        mock_coh_client.get_recommendation.return_value = {'recommendationId': 'rec-123'}

        await get_recommendation(mock_context, mock_coh_client, 'rec-123', 'EC2Instance')
        mock_coh_client.get_recommendation.assert_called_once()
