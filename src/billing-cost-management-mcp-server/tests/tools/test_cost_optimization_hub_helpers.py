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

"""Unit tests for cost_optimization_hub_helpers module."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_helpers import (
    format_currency_amount,
    format_timestamp,
    list_recommendations,
    get_recommendation,
    list_recommendation_summaries,
)
from fastmcp import Context


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    return context


@pytest.fixture
def mock_coh_client():
    """Create a mock Cost Optimization Hub client."""
    client = MagicMock()

    # Setup mock responses for list_recommendations
    client.list_recommendations.return_value = {
        'recommendations': [
            {
                'resourceId': 'i-1234567890abcdef0',
                'resourceType': 'EC2_INSTANCE',
                'accountId': '123456789012',
                'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
                'status': 'ADOPTED',
                'lastRefreshTimestamp': datetime(2023, 1, 1),
                'recommendationId': 'rec-12345',
                'source': 'COMPUTE_OPTIMIZER',
                'lookbackPeriodInDays': 14,
            }
        ],
        'nextToken': 'next-token-123',
    }

    # Setup mock response for get_recommendation
    client.get_recommendation.return_value = {
        'recommendation': {
            'resourceId': 'i-1234567890abcdef0',
            'resourceType': 'EC2_INSTANCE',
            'accountId': '123456789012',
            'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
            'status': 'ADOPTED',
            'lastRefreshTimestamp': datetime(2023, 1, 1),
            'recommendationId': 'rec-12345',
            'source': 'COMPUTE_OPTIMIZER',
            'lookbackPeriodInDays': 14,
            'currentResource': {
                'resourceDetails': {
                    'EC2Instance': {
                        'instanceType': 't3.large',
                    }
                }
            },
            'recommendedResources': [
                {
                    'resourceDetails': {
                        'EC2Instance': {
                            'instanceType': 't3.small',
                        }
                    },
                    'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
                    'costBreakdown': [
                        {
                            'description': 'Instance savings',
                            'amount': {'amount': 100.0, 'currency': 'USD'},
                        }
                    ],
                }
            ],
            'implementationEffort': {
                'effortLevel': 'MEDIUM',
                'requiredActions': ['Stop instance', 'Change instance type', 'Start instance'],
            },
        }
    }

    # Setup mock response for list_recommendation_summaries
    client.list_recommendation_summaries.return_value = {
        'summaries': [
            {
                'dimensionValue': 'EC2_INSTANCE',
                'recommendationCount': 10,
                'estimatedMonthlySavings': {'amount': 500.0, 'currency': 'USD'},
            },
            {
                'dimensionValue': 'RDS',
                'recommendationCount': 5,
                'estimatedMonthlySavings': {'amount': 300.0, 'currency': 'USD'},
            },
        ],
        'nextToken': 'next-token-summaries',
    }

    return client


class TestFormatHelpers:
    """Tests for the format helper functions."""

    def test_format_currency_amount_with_valid_input(self):
        """Test format_currency_amount with valid input."""
        amount = {'amount': 100.0, 'currency': 'USD'}
        result = format_currency_amount(amount)
        # Check that the result is not None before accessing attributes
        assert result is not None
        assert result['amount'] == 100.0
        assert result['currency'] == 'USD'
        assert result['formatted'] == '100.0 USD'

    def test_format_currency_amount_with_none_input(self):
        """Test format_currency_amount with None input."""
        result = format_currency_amount(None)
        assert result is None

    def test_format_timestamp_with_datetime(self):
        """Test format_timestamp with datetime object."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        result = format_timestamp(timestamp)
        assert result == '2023-01-01T12:00:00'

    def test_format_timestamp_with_string(self):
        """Test format_timestamp with string."""
        timestamp = '2023-01-01'
        result = format_timestamp(timestamp)
        assert result == '2023-01-01'

    def test_format_timestamp_with_none(self):
        """Test format_timestamp with None input."""
        result = format_timestamp(None)
        assert result is None


@pytest.mark.asyncio
class TestListRecommendations:
    """Tests for the list_recommendations function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to list_recommendations."""
        result = await list_recommendations(
            mock_context,
            mock_coh_client,
            max_results=10,
        )

        # Verify the client was called correctly
        mock_coh_client.list_recommendations.assert_called_once()
        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['includeAllRecommendations'] is False

        # Verify the context was informed
        mock_context.info.assert_called_once()
        
        # Verify response structure
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert 'next_token' in result['data']
        assert result['data']['next_token'] == 'next-token-123'
        
        # Verify recommendation data
        recs = result['data']['recommendations']
        assert len(recs) == 1
        rec = recs[0]
        assert rec['resource_id'] == 'i-1234567890abcdef0'
        assert rec['resource_type'] == 'EC2_INSTANCE'
        assert rec['account_id'] == '123456789012'
        assert rec['status'] == 'ADOPTED'
        assert rec['source'] == 'COMPUTE_OPTIMIZER'
        assert rec['lookback_period_in_days'] == 14
        
        # Verify formatted currency
        assert rec['estimated_monthly_savings']['amount'] == 100.0
        assert rec['estimated_monthly_savings']['currency'] == 'USD'
        assert rec['estimated_monthly_savings']['formatted'] == '100.0 USD'

    async def test_with_filters_and_next_token(self, mock_context, mock_coh_client):
        """Test list_recommendations with filters and next_token."""
        filters = {'accountIds': ['123456789012']}
        
        result = await list_recommendations(
            mock_context,
            mock_coh_client,
            max_results=10,
            next_token='page-token',
            filters=filters,
            include_all_recommendations=True,
        )

        # Verify the client was called with the right parameters
        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['nextToken'] == 'page-token'
        assert call_kwargs['filter'] == filters
        assert call_kwargs['includeAllRecommendations'] is True


@pytest.mark.asyncio
class TestGetRecommendation:
    """Tests for the get_recommendation function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to get_recommendation."""
        result = await get_recommendation(
            mock_context,
            mock_coh_client,
            resource_id='i-1234567890abcdef0',
            resource_type='EC2_INSTANCE',
        )

        # Verify the client was called correctly
        mock_coh_client.get_recommendation.assert_called_once()
        call_kwargs = mock_coh_client.get_recommendation.call_args[1]
        assert call_kwargs['resourceId'] == 'i-1234567890abcdef0'
        assert call_kwargs['resourceType'] == 'EC2_INSTANCE'

        # Verify the context was informed
        mock_context.info.assert_called_once()
        
        # Verify response structure
        assert result['status'] == 'success'
        assert 'resource_id' in result['data']
        assert 'resource_type' in result['data']
        
        # Verify basic recommendation data
        rec = result['data']
        assert rec['resource_id'] == 'i-1234567890abcdef0'
        assert rec['resource_type'] == 'EC2_INSTANCE'
        assert rec['account_id'] == '123456789012'
        assert rec['status'] == 'ADOPTED'
        assert rec['source'] == 'COMPUTE_OPTIMIZER'
        assert rec['lookback_period_in_days'] == 14
        
        # Verify formatted currency
        assert rec['estimated_monthly_savings']['amount'] == 100.0
        assert rec['estimated_monthly_savings']['currency'] == 'USD'
        assert rec['estimated_monthly_savings']['formatted'] == '100.0 USD'
        
        # Verify current resource details
        assert 'current_resource' in rec
        assert 'resource_details' in rec['current_resource']
        assert 'EC2Instance' in rec['current_resource']['resource_details']
        assert rec['current_resource']['resource_details']['EC2Instance']['instanceType'] == 't3.large'
        
        # Verify recommended resources
        assert 'recommended_resources' in rec
        assert len(rec['recommended_resources']) == 1
        rec_resource = rec['recommended_resources'][0]
        assert 'resource_details' in rec_resource
        assert 'EC2Instance' in rec_resource['resource_details']
        assert rec_resource['resource_details']['EC2Instance']['instanceType'] == 't3.small'
        
        # Verify cost breakdown
        assert 'cost_breakdown' in rec_resource
        assert len(rec_resource['cost_breakdown']) == 1
        cost_item = rec_resource['cost_breakdown'][0]
        assert cost_item['description'] == 'Instance savings'
        assert cost_item['amount']['amount'] == 100.0
        
        # Verify implementation effort
        assert 'implementation_effort' in rec
        assert rec['implementation_effort']['effort_level'] == 'MEDIUM'
        assert len(rec['implementation_effort']['required_actions']) == 3
        assert 'Stop instance' in rec['implementation_effort']['required_actions']


@pytest.mark.asyncio
class TestListRecommendationSummaries:
    """Tests for the list_recommendation_summaries function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to list_recommendation_summaries."""
        result = await list_recommendation_summaries(
            mock_context,
            mock_coh_client,
            group_by='RESOURCE_TYPE',
        )

        # Verify the client was called correctly
        mock_coh_client.list_recommendation_summaries.assert_called_once()
        call_kwargs = mock_coh_client.list_recommendation_summaries.call_args[1]
        assert call_kwargs['groupBy'] == 'RESOURCE_TYPE'

        # Verify the context was informed
        mock_context.info.assert_called_once()
        
        # Verify response structure
        assert result['status'] == 'success'
        assert 'summaries' in result['data']
        assert 'next_token' in result['data']
        assert result['data']['next_token'] == 'next-token-summaries'
        
        # Verify summaries data
        summaries = result['data']['summaries']
        assert len(summaries) == 2
        
        # Verify first summary (EC2_INSTANCE)
        ec2_summary = summaries[0]
        assert ec2_summary['dimension_value'] == 'EC2_INSTANCE'
        assert ec2_summary['recommendation_count'] == 10
        assert ec2_summary['estimated_monthly_savings']['amount'] == 500.0
        assert ec2_summary['estimated_monthly_savings']['currency'] == 'USD'
        assert ec2_summary['estimated_monthly_savings']['formatted'] == '500.0 USD'
        
        # Verify second summary (RDS)
        rds_summary = summaries[1]
        assert rds_summary['dimension_value'] == 'RDS'
        assert rds_summary['recommendation_count'] == 5
        assert rds_summary['estimated_monthly_savings']['amount'] == 300.0
        assert rds_summary['estimated_monthly_savings']['currency'] == 'USD'
        assert rds_summary['estimated_monthly_savings']['formatted'] == '300.0 USD'

    async def test_with_filters_and_pagination(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries with filters and pagination."""
        filters = {'accountIds': ['123456789012']}
        
        result = await list_recommendation_summaries(
            mock_context,
            mock_coh_client,
            group_by='ACCOUNT_ID',
            max_results=10,
            next_token='page-token',
            filters=filters,
        )

        # Verify the client was called with the right parameters
        call_kwargs = mock_coh_client.list_recommendation_summaries.call_args[1]
        assert call_kwargs['groupBy'] == 'ACCOUNT_ID'
        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['nextToken'] == 'page-token'
        assert call_kwargs['filter'] == filters