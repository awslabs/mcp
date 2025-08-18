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
from awslabs.billing_cost_management_mcp_server.tools.cost_optimization_hub_helpers import (
    format_currency_amount,
    format_timestamp,
    get_recommendation,
    list_recommendation_summaries,
    list_recommendations,
)
from datetime import datetime
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


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

    # Setup mock for enrollment status check
    client.get_enrollment_status.return_value = {'status': 'ENROLLED'}

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
        ]
        # No nextToken to stop pagination
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
        ]
        # No nextToken to stop pagination
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
        mock_context.info.assert_called()

        # Verify response structure
        assert result['status'] == 'success'
        assert 'recommendations' in result['data']
        assert 'page_count' in result['data']
        assert 'total_recommendations' in result['data']

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
        """Test list_recommendations with filters."""
        filters = {'accountIds': ['123456789012']}

        await list_recommendations(
            mock_context,
            mock_coh_client,
            max_results=10,
            filters=filters,
            include_all_recommendations=True,
        )

        # Verify the client was called with the right parameters
        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert call_kwargs['maxResults'] == 10
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
        assert (
            rec['current_resource']['resource_details']['EC2Instance']['instanceType']
            == 't3.large'
        )

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
        mock_context.info.assert_called()

        # Verify response structure
        assert result['status'] == 'success'
        assert 'summaries' in result['data']
        assert 'page_count' in result['data']
        assert 'total_summaries' in result['data']
        assert 'group_by' in result['data']
        assert result['data']['group_by'] == 'RESOURCE_TYPE'

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
        """Test list_recommendation_summaries with filters."""
        filters = {'accountIds': ['123456789012']}

        await list_recommendation_summaries(
            mock_context,
            mock_coh_client,
            group_by='ACCOUNT_ID',
            max_results=10,
            filters=filters,
        )

        # Verify the client was called with the right parameters
        call_kwargs = mock_coh_client.list_recommendation_summaries.call_args[1]
        assert call_kwargs['groupBy'] == 'ACCOUNT_ID'
        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['filter'] == filters


@pytest.mark.asyncio
class TestListRecommendationsErrorHandling:
    """Test error handling scenarios for list_recommendations."""

    async def test_enrollment_not_enrolled(self, mock_context, mock_coh_client):
        """Test list_recommendations when Cost Optimization Hub is not enrolled."""
        # Mock enrollment status as not enrolled
        mock_coh_client.get_enrollment_status.return_value = {'status': 'NOT_ENROLLED'}

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'warning'
        assert result['data']['enrollment_status'] == 'NOT_ENROLLED'
        assert result['data']['recommendations'] == []
        assert 'not enrolled' in result['message']

    async def test_enrollment_check_access_denied(self, mock_context, mock_coh_client):
        """Test list_recommendations when enrollment check returns access denied."""
        from botocore.exceptions import ClientError

        mock_coh_client.get_enrollment_status.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='GetEnrollmentStatus',
        )
        mock_coh_client.list_recommendations.return_value = {'recommendations': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        # Should continue and make the list_recommendations call
        assert result['status'] == 'success'
        mock_coh_client.list_recommendations.assert_called_once()

    async def test_enrollment_check_other_error(self, mock_context, mock_coh_client):
        """Test list_recommendations when enrollment check returns other ClientError."""
        from botocore.exceptions import ClientError

        mock_coh_client.get_enrollment_status.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}
            },
            operation_name='GetEnrollmentStatus',
        )
        mock_coh_client.list_recommendations.return_value = {'recommendations': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        # Should continue and make the list_recommendations call
        assert result['status'] == 'success'
        mock_coh_client.list_recommendations.assert_called_once()

    async def test_enrollment_check_non_client_error(self, mock_context, mock_coh_client):
        """Test list_recommendations when enrollment check returns non-ClientError."""
        mock_coh_client.get_enrollment_status.side_effect = ValueError('Some other error')
        mock_coh_client.list_recommendations.return_value = {'recommendations': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        # Should continue and make the list_recommendations call
        assert result['status'] == 'success'
        mock_coh_client.list_recommendations.assert_called_once()

    async def test_empty_recommendations(self, mock_context, mock_coh_client):
        """Test list_recommendations with empty response."""
        mock_coh_client.list_recommendations.return_value = {'recommendations': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'success'
        assert result['data']['recommendations'] == []
        assert 'No recommendations found' in result['data']['message']

    async def test_pagination_with_max_results(self, mock_context, mock_coh_client):
        """Test list_recommendations pagination with max_results limit."""
        # Setup multi-page response
        mock_coh_client.list_recommendations.side_effect = [
            {
                'recommendations': [
                    {
                        'resourceId': f'i-{i}',
                        'resourceType': 'EC2_INSTANCE',
                        'accountId': '123456789012',
                    }
                    for i in range(50)
                ],
                'nextToken': 'page2token',
            },
            {
                'recommendations': [
                    {
                        'resourceId': f'i-{i}',
                        'resourceType': 'EC2_INSTANCE',
                        'accountId': '123456789012',
                    }
                    for i in range(50, 100)
                ],
                'nextToken': None,
            },
        ]

        result = await list_recommendations(mock_context, mock_coh_client, max_results=75)

        assert result['status'] == 'success'
        assert len(result['data']['recommendations']) == 75  # Truncated to max_results
        assert result['data']['page_count'] == 2  # Actually fetches 2 pages but truncates

    async def test_validation_exception(self, mock_context, mock_coh_client):
        """Test list_recommendations ValidationException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendations.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Invalid filter'}},
            operation_name='ListRecommendations',
        )

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ValidationException'
        assert 'validation error' in result['message']

    async def test_access_denied_exception(self, mock_context, mock_coh_client):
        """Test list_recommendations AccessDeniedException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendations.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='ListRecommendations',
        )

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'AccessDeniedException'
        assert 'Access denied' in result['message']

    async def test_resource_not_found_exception(self, mock_context, mock_coh_client):
        """Test list_recommendations ResourceNotFoundException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendations.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}
            },
            operation_name='ListRecommendations',
        )

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ResourceNotFoundException'
        assert 'may not be enabled' in result['message']

    async def test_other_client_error_reraise(self, mock_context, mock_coh_client):
        """Test list_recommendations other ClientError gets re-raised."""
        from botocore.exceptions import ClientError

        error = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'}},
            operation_name='ListRecommendations',
        )
        mock_coh_client.list_recommendations.side_effect = error

        with pytest.raises(ClientError):
            await list_recommendations(mock_context, mock_coh_client)

    async def test_non_client_error_reraise(self, mock_context, mock_coh_client):
        """Test list_recommendations non-ClientError gets re-raised."""
        error = ValueError('Some unexpected error')
        mock_coh_client.list_recommendations.side_effect = error

        with pytest.raises(ValueError):
            await list_recommendations(mock_context, mock_coh_client)


@pytest.mark.asyncio
class TestGetRecommendationErrorHandling:
    """Test error handling scenarios for get_recommendation."""

    async def test_empty_recommendation_response(self, mock_context, mock_coh_client):
        """Test get_recommendation with empty recommendation in response."""
        mock_coh_client.get_recommendation.return_value = {'recommendation': {}}

        result = await get_recommendation(
            mock_context, mock_coh_client, 'i-1234567890abcdef0', 'EC2_INSTANCE'
        )

        assert result['status'] == 'warning'
        assert result['data']['resource_id'] == 'i-1234567890abcdef0'
        assert 'No recommendation found' in result['message']

    async def test_no_recommendation_key(self, mock_context, mock_coh_client):
        """Test get_recommendation with no recommendation key in response."""
        mock_coh_client.get_recommendation.return_value = {}

        result = await get_recommendation(
            mock_context, mock_coh_client, 'i-1234567890abcdef0', 'EC2_INSTANCE'
        )

        assert result['status'] == 'warning'
        assert 'No recommendation found' in result['message']

    async def test_validation_exception(self, mock_context, mock_coh_client):
        """Test get_recommendation ValidationException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.get_recommendation.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid resource'}
            },
            operation_name='GetRecommendation',
        )

        result = await get_recommendation(
            mock_context, mock_coh_client, 'invalid-id', 'EC2_INSTANCE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ValidationException'
        assert 'validation error' in result['message']

    async def test_access_denied_exception(self, mock_context, mock_coh_client):
        """Test get_recommendation AccessDeniedException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.get_recommendation.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='GetRecommendation',
        )

        result = await get_recommendation(
            mock_context, mock_coh_client, 'i-1234567890abcdef0', 'EC2_INSTANCE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'AccessDeniedException'
        assert 'Access denied' in result['message']

    async def test_resource_not_found_exception(self, mock_context, mock_coh_client):
        """Test get_recommendation ResourceNotFoundException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.get_recommendation.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}
            },
            operation_name='GetRecommendation',
        )

        result = await get_recommendation(
            mock_context, mock_coh_client, 'i-nonexistent', 'EC2_INSTANCE'
        )

        assert result['status'] == 'warning'
        assert result['data']['error_code'] == 'ResourceNotFoundException'
        assert 'not found' in result['message']

    async def test_other_client_error_reraise(self, mock_context, mock_coh_client):
        """Test get_recommendation other ClientError gets re-raised."""
        from botocore.exceptions import ClientError

        error = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'}},
            operation_name='GetRecommendation',
        )
        mock_coh_client.get_recommendation.side_effect = error

        with pytest.raises(ClientError):
            await get_recommendation(
                mock_context, mock_coh_client, 'i-1234567890abcdef0', 'EC2_INSTANCE'
            )

    async def test_non_client_error_reraise(self, mock_context, mock_coh_client):
        """Test get_recommendation non-ClientError gets re-raised."""
        error = ValueError('Some unexpected error')
        mock_coh_client.get_recommendation.side_effect = error

        with pytest.raises(ValueError):
            await get_recommendation(
                mock_context, mock_coh_client, 'i-1234567890abcdef0', 'EC2_INSTANCE'
            )


@pytest.mark.asyncio
class TestListRecommendationSummariesErrorHandling:
    """Test error handling scenarios for list_recommendation_summaries."""

    async def test_empty_summaries(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries with empty response."""
        mock_coh_client.list_recommendation_summaries.return_value = {'summaries': []}

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'success'
        assert result['data']['summaries'] == []
        assert 'No recommendation summaries found' in result['data']['message']

    async def test_pagination_with_max_results(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries pagination with max_results limit."""
        # Setup multi-page response
        mock_coh_client.list_recommendation_summaries.side_effect = [
            {
                'summaries': [
                    {
                        'dimensionValue': f'TYPE_{i}',
                        'recommendationCount': 5,
                        'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
                    }
                    for i in range(50)
                ],
                'nextToken': 'page2token',
            },
            {
                'summaries': [
                    {
                        'dimensionValue': f'TYPE_{i}',
                        'recommendationCount': 5,
                        'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
                    }
                    for i in range(50, 100)
                ],
                'nextToken': None,
            },
        ]

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE', max_results=75
        )

        assert result['status'] == 'success'
        assert len(result['data']['summaries']) == 75  # Truncated to max_results
        assert result['data']['page_count'] == 2  # Actually fetches 2 pages but truncates

    async def test_validation_exception(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries ValidationException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendation_summaries.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid group_by'}
            },
            operation_name='ListRecommendationSummaries',
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'INVALID_GROUP'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ValidationException'
        assert 'Invalid parameters' in result['message']
        assert 'valid_group_by_values' in result['data']

    async def test_access_denied_exception(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries AccessDeniedException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendation_summaries.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='ListRecommendationSummaries',
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'AccessDeniedException'
        assert 'Access denied' in result['message']

    async def test_unauthorized_exception(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries UnauthorizedException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendation_summaries.side_effect = ClientError(
            error_response={'Error': {'Code': 'UnauthorizedException', 'Message': 'Unauthorized'}},
            operation_name='ListRecommendationSummaries',
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'UnauthorizedException'
        assert 'Access denied' in result['message']

    async def test_resource_not_found_exception(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries ResourceNotFoundException handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendation_summaries.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}
            },
            operation_name='ListRecommendationSummaries',
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ResourceNotFoundException'
        assert 'may not be enabled' in result['message']

    async def test_other_aws_error(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries other AWS error handling."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_recommendation_summaries.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'},
                'ResponseMetadata': {'RequestId': 'test-request-id'},
            },
            operation_name='ListRecommendationSummaries',
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'InternalServerError'
        assert result['data']['request_id'] == 'test-request-id'
        assert 'AWS Error' in result['message']

    async def test_non_aws_error(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries non-AWS error handling."""
        mock_coh_client.list_recommendation_summaries.side_effect = ValueError(
            'Some unexpected error'
        )

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'error'
        assert result['data']['error_type'] == 'service_error'
        assert result['data']['service'] == 'Cost Optimization Hub'
        assert 'Try using list_recommendations' in result['message']


@pytest.mark.asyncio
class TestRecommendationFormatting:
    """Test detailed recommendation formatting scenarios."""

    async def test_recommendation_without_optional_fields(self, mock_context, mock_coh_client):
        """Test get_recommendation with minimal recommendation data."""
        mock_coh_client.get_recommendation.return_value = {
            'recommendation': {
                'resourceId': 'i-minimal',
                'resourceType': 'EC2_INSTANCE',
                'accountId': '123456789012',
                'status': 'ADOPTED',
                'recommendationId': 'rec-minimal',
                # Missing optional fields: source, lookbackPeriodInDays, estimatedMonthlySavings
                'currentResource': {'resourceDetails': {}},
                'recommendedResources': [],
            }
        }

        result = await get_recommendation(
            mock_context, mock_coh_client, 'i-minimal', 'EC2_INSTANCE'
        )

        assert result['status'] == 'success'
        rec = result['data']
        assert rec['resource_id'] == 'i-minimal'
        assert 'source' not in rec
        assert 'lookback_period_in_days' not in rec
        assert rec['estimated_monthly_savings'] is None
        assert rec['recommended_resources'] == []

    async def test_recommendation_with_cost_breakdown_no_implementation(
        self, mock_context, mock_coh_client
    ):
        """Test get_recommendation with cost breakdown but no implementation effort."""
        mock_coh_client.get_recommendation.return_value = {
            'recommendation': {
                'resourceId': 'i-test',
                'resourceType': 'EC2_INSTANCE',
                'accountId': '123456789012',
                'status': 'ADOPTED',
                'recommendationId': 'rec-test',
                'currentResource': {'resourceDetails': {}},
                'recommendedResources': [
                    {
                        'resourceDetails': {},
                        'estimatedMonthlySavings': {'amount': 50.0, 'currency': 'USD'},
                        'costBreakdown': [
                            {
                                'description': 'CPU savings',
                                'amount': {'amount': 30.0, 'currency': 'USD'},
                            },
                            {
                                'description': 'Memory savings',
                                'amount': {'amount': 20.0, 'currency': 'USD'},
                            },
                        ],
                    }
                ],
                # Missing implementationEffort
            }
        }

        result = await get_recommendation(mock_context, mock_coh_client, 'i-test', 'EC2_INSTANCE')

        assert result['status'] == 'success'
        rec = result['data']
        assert len(rec['recommended_resources']) == 1
        assert len(rec['recommended_resources'][0]['cost_breakdown']) == 2
        assert 'implementation_effort' not in rec


@pytest.mark.asyncio
class TestPaginationEdgeCases:
    """Test pagination edge cases."""

    async def test_list_recommendations_single_page_no_token(self, mock_context, mock_coh_client):
        """Test list_recommendations with single page (no nextToken)."""
        mock_coh_client.list_recommendations.return_value = {
            'recommendations': [
                {
                    'resourceId': 'i-single',
                    'resourceType': 'EC2_INSTANCE',
                    'accountId': '123456789012',
                }
            ]
            # No nextToken
        }

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'success'
        assert result['data']['page_count'] == 1
        assert len(result['data']['recommendations']) == 1

    async def test_list_recommendation_summaries_single_page_no_token(
        self, mock_context, mock_coh_client
    ):
        """Test list_recommendation_summaries with single page (no nextToken)."""
        mock_coh_client.list_recommendation_summaries.return_value = {
            'summaries': [
                {
                    'dimensionValue': 'EC2_INSTANCE',
                    'recommendationCount': 5,
                    'estimatedMonthlySavings': {'amount': 100.0, 'currency': 'USD'},
                }
            ]
            # No nextToken
        }

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'success'
        assert result['data']['page_count'] == 1
        assert len(result['data']['summaries']) == 1


class TestFormatHelpersEdgeCases:
    """Test edge cases for format helper functions."""

    def test_format_currency_amount_with_empty_dict(self):
        """Test format_currency_amount with empty dictionary."""
        result = format_currency_amount({})
        # format_currency_amount returns None for empty dict since if not amount: return None
        assert result is None

    def test_format_currency_amount_with_missing_keys(self):
        """Test format_currency_amount with missing keys."""
        amount = {'amount': 100.0}  # Missing 'currency'
        result = format_currency_amount(amount)
        assert result is not None
        assert result['amount'] == 100.0
        assert result['currency'] is None
        assert result['formatted'] == '100.0 None'
