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
    format_timestamp,
    get_recommendation,
    list_efficiency_metrics,
    list_recommendation_summaries,
    list_recommendations,
)
from datetime import datetime
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def disable_sql_offload(monkeypatch):
    """Keep list_recommendations responses inline for existing assertions.

    FORCE_SQL_CONVERSION defaults to True at module import, which would otherwise
    push every test response — even single-item ones — into a SQLite table.
    Tests that want to exercise the offload path explicitly bypass this fixture
    by re-patching should_convert_to_sql at the call site.
    """
    monkeypatch.setattr(
        'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
        lambda _size: False,
    )


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
    }

    return client


class TestFormatHelpers:
    """Tests for the format helper functions."""

    def test_format_timestamp_with_datetime(self):
        """Test format_timestamp with datetime object."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        result = format_timestamp(timestamp)
        assert result == '2023-01-01T12:00:00'

    def test_format_timestamp_with_none(self):
        """Test format_timestamp with None input."""
        result = format_timestamp(None)
        assert result is None


@pytest.mark.asyncio
class TestListRecommendations:
    """Tests for the list_recommendations function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to list_recommendations."""
        # Setup mock response
        mock_coh_client.list_recommendations.return_value = {
            'items': [
                {
                    'recommendationId': 'rec-123',
                    'resourceId': 'i-123',
                    'accountId': '123456789012',
                    'region': 'us-east-1',
                    'actionType': 'Rightsize',
                    'estimatedMonthlySavings': 50.0,
                    'recommendationLookbackPeriodInDays': 14,
                }
            ]
        }

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

        # Verify recommendation data
        recs = result['data']['recommendations']
        assert len(recs) == 1
        rec = recs[0]
        assert rec['resource_id'] == 'i-123'
        assert rec['recommendation_id'] == 'rec-123'
        assert rec['account_id'] == '123456789012'
        assert rec['region'] == 'us-east-1'
        assert rec['action_type'] == 'Rightsize'
        assert rec['lookback_period_in_days'] == 14
        assert rec['estimated_monthly_savings'] == 50.0

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

    async def test_order_by_passthrough(self, mock_context, mock_coh_client):
        """``order_by`` is forwarded to boto3 as the ``orderBy`` structure."""
        mock_coh_client.list_recommendations.return_value = {'items': []}
        order_by = {'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'}

        await list_recommendations(mock_context, mock_coh_client, order_by=order_by)

        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert call_kwargs['orderBy'] == order_by

    async def test_order_by_omitted_when_absent(self, mock_context, mock_coh_client):
        """No ``orderBy`` key is sent when ``order_by`` is not provided."""
        mock_coh_client.list_recommendations.return_value = {'items': []}

        await list_recommendations(mock_context, mock_coh_client)

        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert 'orderBy' not in call_kwargs


@pytest.mark.asyncio
class TestGetRecommendation:
    """Tests for the get_recommendation function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to get_recommendation."""
        # Setup mock response
        mock_coh_client.get_recommendation.return_value = {
            'recommendationId': 'rec-123',
            'resourceId': 'i-1234567890abcdef0',
            'accountId': '123456789012',
            'region': 'us-east-1',
            'actionType': 'Rightsize',
            'estimatedMonthlySavings': 50.0,
        }

        result = await get_recommendation(
            mock_context,
            mock_coh_client,
            recommendation_id='i-1234567890abcdef0',
        )

        # Verify the client was called correctly
        mock_coh_client.get_recommendation.assert_called_once()
        call_kwargs = mock_coh_client.get_recommendation.call_args[1]
        assert call_kwargs['recommendationId'] == 'i-1234567890abcdef0'
        # resource_type is not part of the API contract and must not be sent
        assert 'resource_type' not in call_kwargs
        assert 'resourceType' not in call_kwargs

        # Verify the context was informed
        mock_context.info.assert_called_once()

        # Verify response structure
        assert result['status'] == 'success'
        assert 'resource_id' in result['data']

        # Verify basic recommendation data
        rec = result['data']
        assert rec['resource_id'] == 'i-1234567890abcdef0'
        assert rec['account_id'] == '123456789012'
        assert rec['source'] is None
        assert rec['lookback_period_in_days'] is None

        # Verify formatted currency
        assert rec['estimated_monthly_savings'] == 50.0

    async def test_includes_current_and_recommended_resource_details(
        self, mock_context, mock_coh_client
    ):
        """Test get_recommendation surfaces current and recommended resource details."""
        current_details = {'ec2Instance': {'configuration': {'instance': {'type': 'm5.2xlarge'}}}}
        recommended_details = {
            'ec2Instance': {'configuration': {'instance': {'type': 'm5.large'}}}
        }
        mock_coh_client.get_recommendation.return_value = {
            'recommendationId': 'rec-123',
            'resourceId': 'i-1234567890abcdef0',
            'currentResourceDetails': current_details,
            'recommendedResourceDetails': recommended_details,
        }

        result = await get_recommendation(
            mock_context,
            mock_coh_client,
            recommendation_id='i-1234567890abcdef0',
        )

        assert result['status'] == 'success'
        rec = result['data']
        assert rec['current_resource_details'] == current_details
        assert rec['recommended_resource_details'] == recommended_details


@pytest.mark.asyncio
class TestListRecommendationSummaries:
    """Tests for the list_recommendation_summaries function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Test basic call to list_recommendation_summaries."""
        # Setup mock response
        mock_coh_client.list_recommendation_summaries.return_value = {
            'items': [
                {
                    'group': 'EC2_INSTANCE',
                    'estimatedMonthlySavings': 100.0,
                    'recommendationCount': 5,
                },
                {'group': 'EBS_VOLUME', 'estimatedMonthlySavings': 50.0, 'recommendationCount': 3},
            ],
            'groupBy': 'RESOURCE_TYPE',
            'currencyCode': 'USD',
        }

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
        assert 'group_by' in result['data']
        assert result['data']['group_by'] == 'RESOURCE_TYPE'

        # Verify summaries data
        summaries = result['data']['summaries']
        assert len(summaries) == 2

        # Verify first summary (EC2_INSTANCE)
        ec2_summary = summaries[0]
        assert ec2_summary['group'] == 'EC2_INSTANCE'
        assert ec2_summary['recommendation_count'] == 5
        assert ec2_summary['estimated_monthly_savings'] == 100.0

        # Verify second summary (EBS_VOLUME)
        ebs_summary = summaries[1]
        assert ebs_summary['group'] == 'EBS_VOLUME'
        assert ebs_summary['recommendation_count'] == 3
        assert ebs_summary['estimated_monthly_savings'] == 50.0

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
        mock_coh_client.list_recommendations.return_value = {'items': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'success'
        assert result['data']['recommendations'] == []

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
        mock_coh_client.list_recommendations.return_value = {'items': []}

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'success'
        assert result['data']['recommendations'] == []

    async def test_pagination_with_max_pages(self, mock_context, mock_coh_client):
        """``max_pages`` caps the number of API calls and surfaces resumption state.

        Pages 1 and 2 both return ``nextToken``; with ``max_pages=2`` the helper
        stops after page 2 and returns the combined recommendations alongside a
        ``Pagination`` envelope (matching the Cost Explorer pattern) so the
        caller can resume.
        """
        mock_coh_client.list_recommendations.side_effect = [
            {
                'items': [
                    {'recommendationId': f'rec-{i}', 'accountId': '123456789012'} for i in range(3)
                ],
                'nextToken': 'page2token',
            },
            {
                'items': [
                    {'recommendationId': f'rec-{i}', 'accountId': '123456789012'}
                    for i in range(3, 6)
                ],
                'nextToken': 'page3token',
            },
        ]

        result = await list_recommendations(mock_context, mock_coh_client, max_pages=2)

        assert result['status'] == 'success'
        # All items across the two fetched pages are returned (no truncation).
        assert len(result['data']['recommendations']) == 6
        # Boto3 was called exactly twice — max_pages stopped further fetches.
        assert mock_coh_client.list_recommendations.call_count == 2
        # Resumption state is plumbed through under the canonical ``Pagination``
        # envelope so the caller can continue from page 3.
        pagination = result['data'].get('Pagination', {})
        assert pagination.get('has_more') is True
        assert pagination.get('next_token') == 'page3token'
        assert pagination.get('pages_fetched') == 2

    async def test_pagination_with_next_token_seeds_first_request(
        self, mock_context, mock_coh_client
    ):
        """``next_token`` is injected into the first boto3 call to resume mid-stream."""
        mock_coh_client.list_recommendations.return_value = {
            'items': [{'recommendationId': 'rec-0', 'accountId': '123456789012'}],
            'nextToken': None,
        }

        await list_recommendations(mock_context, mock_coh_client, next_token='resume-from-here')

        call_kwargs = mock_coh_client.list_recommendations.call_args[1]
        assert call_kwargs['nextToken'] == 'resume-from-here'

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
        # The service's own message is surfaced verbatim (no bespoke mapping).
        assert result['message'] == 'Invalid filter'

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
        assert result['message'] == 'Access denied'

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
        assert result['message'] == 'Resource not found'

    async def test_other_client_error_returns_service_message(self, mock_context, mock_coh_client):
        """Any ClientError now returns the service's code/message instead of re-raising."""
        from botocore.exceptions import ClientError

        error = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'}},
            operation_name='ListRecommendations',
        )
        mock_coh_client.list_recommendations.side_effect = error

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'InternalServerError'
        assert result['message'] == 'Internal error'

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
        mock_coh_client.get_recommendation.return_value = {}

        result = await get_recommendation(mock_context, mock_coh_client, 'i-1234567890abcdef0')

        assert result['status'] == 'warning'

    async def test_no_recommendation_key(self, mock_context, mock_coh_client):
        """Test get_recommendation with no recommendation key in response."""
        mock_coh_client.get_recommendation.return_value = {}

        result = await get_recommendation(mock_context, mock_coh_client, 'i-1234567890abcdef0')

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

        result = await get_recommendation(mock_context, mock_coh_client, 'invalid-id')

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

        result = await get_recommendation(mock_context, mock_coh_client, 'i-1234567890abcdef0')

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

        result = await get_recommendation(mock_context, mock_coh_client, 'i-nonexistent')

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
            await get_recommendation(mock_context, mock_coh_client, 'i-1234567890abcdef0')

    async def test_non_client_error_reraise(self, mock_context, mock_coh_client):
        """Test get_recommendation non-ClientError gets re-raised."""
        error = ValueError('Some unexpected error')
        mock_coh_client.get_recommendation.side_effect = error

        with pytest.raises(ValueError):
            await get_recommendation(mock_context, mock_coh_client, 'i-1234567890abcdef0')


@pytest.mark.asyncio
class TestListRecommendationSummariesErrorHandling:
    """Test error handling scenarios for list_recommendation_summaries."""

    async def test_empty_summaries(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries with empty response."""
        mock_coh_client.list_recommendation_summaries.return_value = {'items': []}

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'success'
        assert result['data']['summaries'] == []

    async def test_pagination_with_max_pages(self, mock_context, mock_coh_client):
        """``max_pages`` caps the number of API calls and surfaces resumption state.

        Pages 1 and 2 both return ``nextToken``; with ``max_pages=2`` the helper
        stops after page 2 and returns the combined summaries alongside a
        ``Pagination`` envelope (matching the Cost Explorer pattern). The
        top-level aggregate fields are read from the FIRST response — per
        AWS the values are page-invariant, but giving the two mock pages
        different ``estimatedTotalDedupedSavings`` values lets the test
        actually prove which page was consulted.
        """
        mock_coh_client.list_recommendation_summaries.side_effect = [
            {
                'items': [
                    {
                        'group': f'TYPE_{i}',
                        'recommendationCount': 5,
                        'estimatedMonthlySavings': 100.0,
                    }
                    for i in range(3)
                ],
                'groupBy': 'RESOURCE_TYPE',
                'currencyCode': 'USD',
                # First response: this is what the helper should read.
                'estimatedTotalDedupedSavings': 600.0,
                'nextToken': 'page2token',
            },
            {
                'items': [
                    {
                        'group': f'TYPE_{i}',
                        'recommendationCount': 5,
                        'estimatedMonthlySavings': 100.0,
                    }
                    for i in range(3, 6)
                ],
                'groupBy': 'RESOURCE_TYPE',
                'currencyCode': 'USD',
                # Second response: different value so a last-response read
                # would be visibly wrong.
                'estimatedTotalDedupedSavings': 999.0,
                'nextToken': 'page3token',
            },
        ]

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE', max_pages=2
        )

        assert result['status'] == 'success'
        # All items across the two fetched pages are returned (no truncation).
        assert len(result['data']['summaries']) == 6
        # Boto3 was called exactly twice — max_pages stopped further fetches.
        assert mock_coh_client.list_recommendation_summaries.call_count == 2
        # Aggregate header comes from the FIRST response, not the last.
        assert result['data']['estimated_total_savings'] == 600.0
        # Resumption state is plumbed through under ``Pagination`` so the
        # caller can continue from page 3.
        pagination = result['data'].get('Pagination', {})
        assert pagination.get('has_more') is True
        assert pagination.get('next_token') == 'page3token'
        assert pagination.get('pages_fetched') == 2

    async def test_pagination_with_next_token_seeds_first_request(
        self, mock_context, mock_coh_client
    ):
        """``next_token`` is injected into the first boto3 call to resume mid-stream."""
        mock_coh_client.list_recommendation_summaries.return_value = {
            'items': [
                {
                    'group': 'EC2_INSTANCE',
                    'recommendationCount': 1,
                    'estimatedMonthlySavings': 10.0,
                }
            ],
            'groupBy': 'RESOURCE_TYPE',
            'currencyCode': 'USD',
            'estimatedTotalDedupedSavings': 10.0,
            'nextToken': None,
        }

        await list_recommendation_summaries(
            mock_context,
            mock_coh_client,
            'RESOURCE_TYPE',
            next_token='resume-from-here',
        )

        call_kwargs = mock_coh_client.list_recommendation_summaries.call_args[1]
        assert call_kwargs['nextToken'] == 'resume-from-here'

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
        # The service's own message is surfaced verbatim (no bespoke mapping).
        assert result['message'] == 'Invalid group_by'

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
        assert result['message'] == 'Access denied'

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
        assert result['message'] == 'Unauthorized'

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
        assert result['message'] == 'Resource not found'

    async def test_other_aws_error(self, mock_context, mock_coh_client):
        """Test list_recommendation_summaries other AWS error surfaces the service message."""
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
        assert result['message'] == 'Internal error'

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
            'resourceId': 'i-minimal',
            'currentResourceType': 'Ec2Instance',
            'accountId': '123456789012',
            'recommendationId': 'rec-minimal',
            # Missing optional fields: source, lookbackPeriodInDays, estimatedMonthlySavings
        }

        result = await get_recommendation(mock_context, mock_coh_client, 'i-minimal')

        assert result['status'] == 'success'
        rec = result['data']
        assert rec['resource_id'] == 'i-minimal'
        assert rec['source'] is None
        assert rec['lookback_period_in_days'] is None
        assert rec['estimated_monthly_savings'] is None

    async def test_recommendation_with_cost_breakdown_no_implementation(
        self, mock_context, mock_coh_client
    ):
        """Test get_recommendation with cost breakdown but no implementation effort."""
        mock_coh_client.get_recommendation.return_value = {
            'resourceId': 'i-test',
            'currentResourceType': 'Ec2Instance',
            'accountId': '123456789012',
            'recommendationId': 'rec-test',
            'estimatedMonthlySavings': 50.0,
            # Missing implementationEffort
        }

        result = await get_recommendation(mock_context, mock_coh_client, 'i-test')

        assert result['status'] == 'success'
        rec = result['data']
        assert rec['resource_id'] == 'i-test'
        assert rec['estimated_monthly_savings'] == 50.0
        assert rec['implementation_effort'] is None


@pytest.mark.asyncio
class TestPaginationEdgeCases:
    """Test pagination edge cases."""

    async def test_list_recommendations_single_page_no_token(self, mock_context, mock_coh_client):
        """Test list_recommendations with single page (no nextToken)."""
        mock_coh_client.list_recommendations.return_value = {
            'items': [
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
        assert len(result['data']['recommendations']) == 1
        assert len(result['data']['recommendations']) == 1

    async def test_list_recommendation_summaries_single_page_no_token(
        self, mock_context, mock_coh_client
    ):
        """Test list_recommendation_summaries with single page (no nextToken)."""
        mock_coh_client.list_recommendation_summaries.return_value = {
            'items': [
                {
                    'group': 'EC2_INSTANCE',
                    'recommendationCount': 5,
                    'estimatedMonthlySavings': 100.0,
                }
            ]
            # No nextToken
        }

        result = await list_recommendation_summaries(
            mock_context, mock_coh_client, 'RESOURCE_TYPE'
        )

        assert result['status'] == 'success'
        assert len(result['data']['summaries']) == 1
        assert len(result['data']['summaries']) == 1


@pytest.mark.asyncio
class TestListRecommendationsSqlOffload:
    """Tests for the SQL-offload path on list_recommendations.

    The default autouse fixture disables offload so existing assertions on
    inline data keep working. These tests re-enable should_convert_to_sql to
    drive the actual offload through utilities/sql_utils.py.
    """

    @pytest.fixture
    def force_offload(self, monkeypatch):
        """Re-enable should_convert_to_sql for tests that need the offload path."""
        monkeypatch.setattr(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
            lambda _size: True,
        )

    async def test_offload_returns_table_sentinel(
        self, mock_context, mock_coh_client, force_offload
    ):
        """Large response is offloaded to SQLite; caller gets table metadata."""
        mock_coh_client.list_recommendations.return_value = {
            'items': [
                {
                    'recommendationId': f'rec-{i}',
                    'accountId': '123456789012',
                    'region': 'us-east-1',
                    'resourceId': f'i-{i:04d}',
                    'resourceArn': f'arn:aws:ec2:us-east-1:123456789012:instance/i-{i:04d}',
                    'actionType': 'Rightsize',
                    'currentResourceType': 'Ec2Instance',
                    'recommendedResourceType': 'Ec2Instance',
                    'currentResourceSummary': 'm5.2xlarge',
                    'recommendedResourceSummary': 'm5.large',
                    'estimatedMonthlySavings': 12.34 + i,
                    'estimatedSavingsPercentage': 25.0,
                    'estimatedMonthlyCost': 99.0,
                    'currencyCode': 'USD',
                    'implementationEffort': 'Low',
                    'lastRefreshTimestamp': datetime(2024, 1, 1),
                    'recommendationLookbackPeriodInDays': 14,
                }
                for i in range(3)
            ]
        }

        result = await list_recommendations(mock_context, mock_coh_client)

        assert result['status'] == 'success'
        data = result['data']
        assert data.get('data_stored') is True
        assert 'table_name' in data
        assert data['table_name'].startswith('cost_optimization_hub_list_recommendations_')
        assert data['row_count'] == 3
        # Sample queries are produced for the COH converter type.
        sample_names = {q['name'] for q in data.get('sample_queries', [])}
        assert 'Top 20 savings opportunities' in sample_names

    async def test_offload_preview_has_flattened_columns(
        self, mock_context, mock_coh_client, force_offload
    ):
        """Preview rows expose the scalar columns; resource summaries pass through as strings."""
        mock_coh_client.list_recommendations.return_value = {
            'items': [
                {
                    'recommendationId': 'rec-only',
                    'accountId': '111122223333',
                    'region': 'eu-west-1',
                    'resourceId': 'i-aaaaaaaa',
                    'actionType': 'Stop',
                    'currentResourceType': 'Ec2Instance',
                    'currentResourceSummary': 't3.large',
                    'estimatedMonthlySavings': 7.5,
                    'currencyCode': 'USD',
                    'implementationEffort': 'VeryLow',
                    'recommendationLookbackPeriodInDays': 14,
                }
            ]
        }

        result = await list_recommendations(mock_context, mock_coh_client)

        preview = result['data']['preview']
        assert len(preview) == 1
        row = preview[0]
        assert row['recommendation_id'] == 'rec-only'
        assert row['account_id'] == '111122223333'
        assert row['action_type'] == 'Stop'
        assert row['estimated_monthly_savings'] == 7.5
        assert row['implementation_effort'] == 'VeryLow'
        assert row['current_resource_summary'] == 't3.large'


@pytest.mark.asyncio
class TestListEfficiencyMetrics:
    """Tests for the list_efficiency_metrics function."""

    async def test_basic_call(self, mock_context, mock_coh_client):
        """Request params are sent as camelCase and the response is flattened."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [
                {
                    'group': 'us-east-1',
                    'message': None,
                    'metricsByTime': [
                        {
                            'timestamp': '2026-06',
                            'score': 82.5,
                            'savings': 1200.0,
                            'spend': 34000.0,
                        },
                        {
                            'timestamp': '2026-07',
                            'score': 85.0,
                            'savings': 1000.0,
                            'spend': 33000.0,
                        },
                    ],
                }
            ]
        }

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='Region',
            order_by={'dimension': 'Score', 'order': 'Desc'},
            max_results=25,
        )

        # Verify the client was called with camelCase params.
        mock_coh_client.list_efficiency_metrics.assert_called_once()
        call_kwargs = mock_coh_client.list_efficiency_metrics.call_args[1]
        assert call_kwargs['granularity'] == 'Monthly'
        assert call_kwargs['timePeriod'] == {'start': '2026-06', 'end': '2026-08'}
        assert call_kwargs['groupBy'] == 'Region'
        assert call_kwargs['orderBy'] == {'dimension': 'Score', 'order': 'Desc'}
        assert call_kwargs['maxResults'] == 25

        # Verify response transform.
        assert result['status'] == 'success'
        data = result['data']
        assert data['granularity'] == 'Monthly'
        assert data['time_period'] == {'start': '2026-06', 'end': '2026-08'}
        assert data['group_by'] == 'Region'
        assert len(data['groups']) == 1
        group = data['groups'][0]
        assert group['group'] == 'us-east-1'
        assert group['message'] is None
        assert len(group['metrics_by_time']) == 2
        point = group['metrics_by_time'][0]
        assert point['timestamp'] == '2026-06'
        assert point['score'] == 82.5
        assert point['savings'] == 1200.0
        assert point['spend'] == 34000.0

    async def test_minimal_request_omits_optional_params(self, mock_context, mock_coh_client):
        """Only granularity + timePeriod are sent when optionals are absent."""
        mock_coh_client.list_efficiency_metrics.return_value = {'efficiencyMetricsByGroup': []}

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Daily',
            start_date='2026-05-01',
            end_date='2026-05-31',
        )

        call_kwargs = mock_coh_client.list_efficiency_metrics.call_args[1]
        assert call_kwargs['granularity'] == 'Daily'
        assert call_kwargs['timePeriod'] == {'start': '2026-05-01', 'end': '2026-05-31'}
        assert 'groupBy' not in call_kwargs
        assert 'orderBy' not in call_kwargs
        assert 'maxResults' not in call_kwargs
        assert 'nextToken' not in call_kwargs
        assert result['status'] == 'success'
        assert result['data']['groups'] == []
        assert result['data']['group_by'] is None

    async def test_group_without_metrics_passes_message(self, mock_context, mock_coh_client):
        """A group with null metricsByTime still surfaces its explanatory message."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [
                {
                    'group': '123456789012',
                    'message': 'Insufficient data for the specified time period.',
                    'metricsByTime': None,
                }
            ]
        }

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='AccountId',
        )

        group = result['data']['groups'][0]
        assert group['group'] == '123456789012'
        assert group['message'] == 'Insufficient data for the specified time period.'
        assert group['metrics_by_time'] == []

    async def test_pagination_with_max_pages(self, mock_context, mock_coh_client):
        """``max_pages`` caps API calls and returns a ``Pagination`` envelope."""
        mock_coh_client.list_efficiency_metrics.side_effect = [
            {
                'efficiencyMetricsByGroup': [
                    {'group': f'acct-{i}', 'message': None, 'metricsByTime': []} for i in range(3)
                ],
                'nextToken': 'page2token',
            },
            {
                'efficiencyMetricsByGroup': [
                    {'group': f'acct-{i}', 'message': None, 'metricsByTime': []}
                    for i in range(3, 6)
                ],
                'nextToken': 'page3token',
            },
        ]

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='AccountId',
            max_pages=2,
        )

        assert result['status'] == 'success'
        assert len(result['data']['groups']) == 6
        assert mock_coh_client.list_efficiency_metrics.call_count == 2
        pagination = result['data'].get('Pagination', {})
        assert pagination.get('has_more') is True
        assert pagination.get('next_token') == 'page3token'
        assert pagination.get('pages_fetched') == 2

    async def test_pagination_with_next_token_seeds_first_request(
        self, mock_context, mock_coh_client
    ):
        """``next_token`` is injected into the first boto3 call to resume mid-stream."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [],
            'nextToken': None,
        }

        await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            next_token='resume-from-here',
        )

        call_kwargs = mock_coh_client.list_efficiency_metrics.call_args[1]
        assert call_kwargs['nextToken'] == 'resume-from-here'

    async def test_single_page_surfaces_next_token(self, mock_context, mock_coh_client):
        """A single-page response with a ``nextToken`` exposes it for resumption."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [
                {'group': 'us-east-1', 'message': None, 'metricsByTime': []}
            ],
            'nextToken': 'more-groups',
        }

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='Region',
        )

        assert result['status'] == 'success'
        # No next_token/max_pages passed -> single boto3 call, token surfaced inline.
        assert mock_coh_client.list_efficiency_metrics.call_count == 1
        assert result['data']['nextToken'] == 'more-groups'
        assert 'Pagination' not in result['data']

    async def test_validation_exception(self, mock_context, mock_coh_client):
        """ValidationException surfaces the service's own message verbatim."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_efficiency_metrics.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid timePeriod'}
            },
            operation_name='ListEfficiencyMetrics',
        )

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ValidationException'
        assert result['message'] == 'Invalid timePeriod'

    async def test_access_denied_exception(self, mock_context, mock_coh_client):
        """AccessDeniedException surfaces the service's own message verbatim."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_efficiency_metrics.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='ListEfficiencyMetrics',
        )

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'AccessDeniedException'
        assert result['message'] == 'Access denied'

    async def test_resource_not_found_exception(self, mock_context, mock_coh_client):
        """ResourceNotFoundException surfaces the service's own message verbatim."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_efficiency_metrics.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}
            },
            operation_name='ListEfficiencyMetrics',
        )

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'ResourceNotFoundException'
        assert result['message'] == 'Not found'

    async def test_other_client_error_returns_service_message(self, mock_context, mock_coh_client):
        """Any ClientError now returns the service's code/message instead of re-raising."""
        from botocore.exceptions import ClientError

        mock_coh_client.list_efficiency_metrics.side_effect = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'Internal error'}},
            operation_name='ListEfficiencyMetrics',
        )

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
        )

        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'InternalServerError'
        assert result['message'] == 'Internal error'

    async def test_non_client_error_reraise(self, mock_context, mock_coh_client):
        """Non-ClientError exceptions are re-raised."""
        mock_coh_client.list_efficiency_metrics.side_effect = ValueError('boom')

        with pytest.raises(ValueError):
            await list_efficiency_metrics(
                mock_context,
                mock_coh_client,
                granularity='Monthly',
                start_date='2026-06',
                end_date='2026-08',
            )


@pytest.mark.asyncio
class TestListEfficiencyMetricsSqlOffload:
    """Tests for the SQL-offload path on list_efficiency_metrics.

    The default autouse fixture disables offload so the inline-shape
    assertions above keep working. These tests re-enable
    should_convert_to_sql to drive the real offload through
    utilities/sql_utils.py (which exercises real SQLite CREATE/INSERT — so
    it also guards the reserved-word ``group`` -> ``group_value`` mapping).
    """

    @pytest.fixture
    def force_offload(self, monkeypatch):
        """Re-enable should_convert_to_sql for tests that need the offload path."""
        monkeypatch.setattr(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
            lambda _size: True,
        )

    async def test_offload_denormalizes_groups_to_rows(
        self, mock_context, mock_coh_client, force_offload
    ):
        """Grouped response is offloaded: one row per (group, timestamp)."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [
                {
                    'group': 'us-east-1',
                    'metricsByTime': [
                        {
                            'timestamp': f'2026-06-0{i + 1}',
                            'score': 80.0 + i,
                            'savings': 100.0 * i,
                            'spend': 1000.0,
                        }
                        for i in range(3)
                    ],
                },
                {
                    'group': 'us-west-2',
                    'metricsByTime': [
                        {
                            'timestamp': f'2026-06-0{i + 1}',
                            'score': 50.0 + i,
                            'savings': 10.0 * i,
                            'spend': 20.0,
                        }
                        for i in range(3)
                    ],
                },
            ]
        }

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Daily',
            start_date='2026-06-01',
            end_date='2026-06-04',
            group_by='Region',
        )

        assert result['status'] == 'success'
        data = result['data']
        assert data.get('data_stored') is True
        assert data['table_name'].startswith('cost_optimization_hub_list_efficiency_metrics_')
        # 2 groups x 3 timestamps = 6 denormalized rows.
        assert data['row_count'] == 6
        sample_names = {q['name'] for q in data.get('sample_queries', [])}
        assert 'Latest efficiency metrics by group (ranked by score)' in sample_names

    async def test_offload_preserves_no_data_group(
        self, mock_context, mock_coh_client, force_offload
    ):
        """A group with an empty series survives offload as one null-metric row."""
        mock_coh_client.list_efficiency_metrics.return_value = {
            'efficiencyMetricsByGroup': [
                {
                    'group': 'us-east-1',
                    'metricsByTime': [
                        {'timestamp': '2026-06-01', 'score': 80.0, 'savings': 0.0, 'spend': 1000.0}
                    ],
                },
                {
                    'group': 'ap-northeast-1',
                    'message': 'Insufficient data to compute efficiency metrics.',
                    'metricsByTime': [],
                },
            ]
        }

        result = await list_efficiency_metrics(
            mock_context,
            mock_coh_client,
            granularity='Daily',
            start_date='2026-06-01',
            end_date='2026-06-02',
            group_by='Region',
        )

        assert result['status'] == 'success'
        # 1 data row + 1 preserved no-data row = 2 rows (the no-data group is
        # not dropped).
        assert result['data']['row_count'] == 2
