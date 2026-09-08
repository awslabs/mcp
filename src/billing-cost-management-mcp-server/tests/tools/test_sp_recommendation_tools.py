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

"""Tests for the Savings Plans purchase recommendation tools.

Cost Explorer requires four parameters for a recommendation and none of them has a
default, because each one changes the recommended commitment. These tests fix that
contract, and the pagination token spelling, which is NextPageToken here and
lowercase nextToken on the Savings Plans service.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools import (
    get_savings_plan_purchase_recommendation_details,
    get_savings_plans_purchase_recommendation,
    list_savings_plans_purchase_recommendation_generation,
    sp_recommendation,
    sp_recommendation_server,
    start_savings_plans_purchase_recommendation_generation,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def sample_recommendation():
    """A recommendation response, shaped as Cost Explorer returns it."""
    return {
        'Metadata': {
            'RecommendationId': 'a1b2c3d4-1111-2222-3333-444455556666',
            'GenerationTimestamp': '2026-08-09T00:00:00Z',
        },
        'SavingsPlansPurchaseRecommendation': {
            'AccountScope': 'PAYER',
            'SavingsPlansType': 'COMPUTE_SP',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'NO_UPFRONT',
            'LookbackPeriodInDays': 'THIRTY_DAYS',
            'SavingsPlansPurchaseRecommendationDetails': [
                {
                    'RecommendationDetailId': 'd1e2f3a4-5555-6666-7777-888899990000',
                    'HourlyCommitmentToPurchase': '0.174',
                    'EstimatedAverageUtilization': '96.16',
                    'EstimatedAverageCoverage': '84.37',
                    'EstimatedMonthlySavingsAmount': '11.47',
                }
            ],
            'SavingsPlansPurchaseRecommendationSummary': {
                'HourlyCommitmentToPurchase': '0.174',
                'EstimatedSavingsPercentage': '6.91',
            },
        },
    }


@pytest.fixture
def sample_recommendation_details():
    """A recommendation detail response with a short hourly series."""
    return {
        'RecommendationDetailId': 'd1e2f3a4-5555-6666-7777-888899990000',
        'RecommendationDetailData': {
            'SavingsPlansType': 'COMPUTE_SP',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'NO_UPFRONT',
            'HourlyCommitmentToPurchase': '0.174',
            'EstimatedAverageCoverage': '84.37',
            'MetricsOverLookbackPeriod': [
                {
                    'StartTime': '2026-07-15T00:00:00Z',
                    'EstimatedOnDemandCost': '0.2199',
                    'CurrentCoverage': '5.62',
                    'EstimatedCoverage': '84.37',
                    'EstimatedNewCommitmentUtilization': '100.0',
                },
            ],
        },
    }


@pytest.fixture
def mock_ce_client(sample_recommendation, sample_recommendation_details):
    """Create a mock Cost Explorer boto3 client."""
    client = MagicMock()
    client.get_savings_plans_purchase_recommendation.return_value = sample_recommendation
    client.get_savings_plan_purchase_recommendation_details.return_value = (
        sample_recommendation_details
    )
    client.start_savings_plans_purchase_recommendation_generation.return_value = {
        'RecommendationId': 'a1b2c3d4-1111-2222-3333-444455556666',
        'GenerationStartedTime': '2026-08-18T00:00:00Z',
        'EstimatedCompletionTime': '2026-08-18T00:05:00Z',
    }
    client.list_savings_plans_purchase_recommendation_generation.return_value = {
        'GenerationSummaryList': [
            {
                'RecommendationId': 'a1b2c3d4-1111-2222-3333-444455556666',
                'GenerationStatus': 'SUCCEEDED',
                'GenerationStartedTime': '2026-08-09T00:00:00Z',
                'GenerationCompletionTime': '2026-08-09T00:04:00Z',
            }
        ],
    }
    return client


PAGINATION_COMPLETE = {
    'complete_dataset': True,
    'pages_fetched': 1,
    'total_results': 1,
    'has_more': False,
    'next_token': None,
    'duration_ms': 1,
}


@pytest.mark.asyncio
class TestGetSavingsPlansPurchaseRecommendation:
    """Tests for get_savings_plans_purchase_recommendation."""

    async def test_basic(self, mock_context, mock_ce_client, sample_recommendation):
        """The four required parameters reach the API and the response keeps its shape."""
        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'COMPUTE_SP',
            'ONE_YEAR',
            'NO_UPFRONT',
            'THIRTY_DAYS',
            None,
            None,
            None,
            None,
            None,
        )

        request_params = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert request_params == {
            'SavingsPlansType': 'COMPUTE_SP',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'NO_UPFRONT',
            'LookbackPeriodInDays': 'THIRTY_DAYS',
        }

        assert result['status'] == 'success'
        # The generation timestamp lives on Metadata, not on the recommendation.
        assert result['data']['Metadata']['GenerationTimestamp'] == '2026-08-09T00:00:00Z'
        # A single page is returned as the API shaped it, with pagination added alongside.
        assert (
            result['data']['SavingsPlansPurchaseRecommendation']
            == (sample_recommendation['SavingsPlansPurchaseRecommendation'])
        )
        assert result['data']['pagination']['complete_dataset'] is True
        assert result['data']['pagination']['pages_fetched'] == 1
        assert result['data']['pagination']['total_results'] == 1

    async def test_optional_parameters(self, mock_context, mock_ce_client):
        """Account scope, filter, and paging are added only when supplied."""
        await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'EC2_INSTANCE_SP',
            'THREE_YEARS',
            'ALL_UPFRONT',
            'SIXTY_DAYS',
            'PAYER',
            {'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111122223333']}},
            'token-from-caller',
            25,
            None,
        )

        request_params = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert request_params['AccountScope'] == 'PAYER'
        assert request_params['Filter'] == {
            'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111122223333']}
        }
        assert request_params['NextPageToken'] == 'token-from-caller'
        assert request_params['PageSize'] == 25

    async def test_details_are_merged_across_pages(self, mock_context, mock_ce_client):
        """The details list spans pages while the fields around it repeat.

        The list this operation pages over is nested inside SavingsPlansPurchaseRecommendation, so
        merging means rebuilding that structure rather than returning the list on its own. The term
        and the summary are read from the first page, which is sound because a token is tied to the
        recommendation version it was generated against.
        """

        def page(detail_id, token):
            return {
                'Metadata': {'RecommendationId': 'a1b2c3d4-1111-2222-3333-444455556666'},
                'SavingsPlansPurchaseRecommendation': {
                    'TermInYears': 'ONE_YEAR',
                    'SavingsPlansPurchaseRecommendationDetails': [
                        {'RecommendationDetailId': detail_id}
                    ],
                    'SavingsPlansPurchaseRecommendationSummary': {
                        'HourlyCommitmentToPurchase': '0.522'
                    },
                },
                **({'NextPageToken': token} if token else {}),
            }

        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = [
            page('detail-1', 'token-1'),
            page('detail-2', 'token-2'),
            page('detail-3', None),
        ]

        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'COMPUTE_SP',
            'ONE_YEAR',
            'NO_UPFRONT',
            'THIRTY_DAYS',
            None,
            None,
            None,
            None,
            None,
        )

        recommendation = result['data']['SavingsPlansPurchaseRecommendation']
        assert [
            d['RecommendationDetailId']
            for d in recommendation['SavingsPlansPurchaseRecommendationDetails']
        ] == ['detail-1', 'detail-2', 'detail-3']
        assert recommendation['TermInYears'] == 'ONE_YEAR'
        # The summary covers the whole recommendation, so it is not accumulated.
        assert recommendation['SavingsPlansPurchaseRecommendationSummary'] == {
            'HourlyCommitmentToPurchase': '0.522'
        }

        # Each page after the first carries the token the previous one returned.
        tokens = [
            call[1].get('NextPageToken')
            for call in mock_ce_client.get_savings_plans_purchase_recommendation.call_args_list
        ]
        assert tokens == [None, 'token-1', 'token-2']

        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'pages_fetched': 3,
            'total_results': 3,
            'has_more': False,
            'next_token': None,
            'duration_ms': result['data']['pagination']['duration_ms'],
        }
        # The merged result reports paging through pagination, not a stray top-level token.
        assert 'NextPageToken' not in result['data']

    async def test_max_pages_stops_early_and_reports_the_token(self, mock_context, mock_ce_client):
        """Stopping short is reported, so a truncated recommendation cannot read as complete."""
        mock_ce_client.get_savings_plans_purchase_recommendation.return_value = {
            'SavingsPlansPurchaseRecommendation': {
                'SavingsPlansPurchaseRecommendationDetails': [{'RecommendationDetailId': 'd'}]
            },
            'NextPageToken': 'more-to-come',
        }

        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'COMPUTE_SP',
            'ONE_YEAR',
            'NO_UPFRONT',
            'THIRTY_DAYS',
            None,
            None,
            None,
            None,
            2,
        )

        assert mock_ce_client.get_savings_plans_purchase_recommendation.call_count == 2
        assert result['data']['pagination']['complete_dataset'] is False
        assert result['data']['pagination']['has_more'] is True
        assert result['data']['pagination']['next_token'] == 'more-to-come'

    async def test_a_page_without_details_is_not_treated_as_a_list(
        self, mock_context, mock_ce_client
    ):
        """A response can carry a token while leaving the details out entirely."""
        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = [
            {'SavingsPlansPurchaseRecommendation': {}, 'NextPageToken': 'token-1'},
            {
                'SavingsPlansPurchaseRecommendation': {
                    'SavingsPlansPurchaseRecommendationDetails': [
                        {'RecommendationDetailId': 'detail-1'}
                    ]
                }
            },
        ]

        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'DATABASE_SP',
            'THREE_YEARS',
            'ALL_UPFRONT',
            'THIRTY_DAYS',
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'success'
        recommendation = result['data']['SavingsPlansPurchaseRecommendation']
        assert recommendation['SavingsPlansPurchaseRecommendationDetails'] == [
            {'RecommendationDetailId': 'detail-1'}
        ]
        assert result['data']['pagination']['total_results'] == 1

    async def test_missing_required_parameters_are_rejected_by_botocore(
        self, mock_context, mock_ce_client
    ):
        """The tool does not guess a scenario when a required parameter is absent.

        botocore validates required members client-side, so the failure costs no API
        call and names every field that was left out.
        """
        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = Exception(
            'Parameter validation failed: Missing required parameter in input: "TermInYears"'
        )

        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'COMPUTE_SP',
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'error'

    async def test_error(self, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = Exception(
            'AccessDeniedException'
        )

        result = await get_savings_plans_purchase_recommendation(
            mock_context,
            mock_ce_client,
            'COMPUTE_SP',
            'ONE_YEAR',
            'NO_UPFRONT',
            'THIRTY_DAYS',
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestGetSavingsPlanPurchaseRecommendationDetails:
    """Tests for get_savings_plan_purchase_recommendation_details."""

    async def test_basic(self, mock_context, mock_ce_client, sample_recommendation_details):
        """The hourly series is returned as the API shapes it."""
        result = await get_savings_plan_purchase_recommendation_details(
            mock_context, mock_ce_client, 'd1e2f3a4-5555-6666-7777-888899990000'
        )

        mock_ce_client.get_savings_plan_purchase_recommendation_details.assert_called_once_with(
            RecommendationDetailId='d1e2f3a4-5555-6666-7777-888899990000'
        )

        assert result['status'] == 'success'
        assert result['data'] == sample_recommendation_details
        # MetricsOverLookbackPeriod keeps its API name so callers can match the docs.
        series = result['data']['RecommendationDetailData']['MetricsOverLookbackPeriod']
        assert series[0]['EstimatedNewCommitmentUtilization'] == '100.0'

    async def test_error(self, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_ce_client.get_savings_plan_purchase_recommendation_details.side_effect = Exception(
            'DataUnavailableException'
        )

        result = await get_savings_plan_purchase_recommendation_details(
            mock_context, mock_ce_client, 'missing-id'
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestStartSavingsPlansPurchaseRecommendationGeneration:
    """Tests for start_savings_plans_purchase_recommendation_generation."""

    async def test_basic(self, mock_context, mock_ce_client):
        """The refresh takes no parameters and returns the generation identifiers."""
        result = await start_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client
        )

        mock_ce_client.start_savings_plans_purchase_recommendation_generation.assert_called_once_with()
        assert result['status'] == 'success'
        # The RecommendationId is the handle for polling the generation history; the refreshed
        # recommendation itself comes from get_savings_plans_purchase_recommendation afterwards.
        assert result['data']['RecommendationId'] == 'a1b2c3d4-1111-2222-3333-444455556666'
        assert result['data']['EstimatedCompletionTime'] == '2026-08-18T00:05:00Z'

    async def test_error(self, mock_context, mock_ce_client):
        """Exceeding the three-a-day refresh limit is reported rather than raised."""
        mock_ce_client.start_savings_plans_purchase_recommendation_generation.side_effect = (
            Exception('GenerationExistsException')
        )

        result = await start_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestListSavingsPlansPurchaseRecommendationGeneration:
    """Tests for list_savings_plans_purchase_recommendation_generation."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_ce_client):
        """Generations page through GenerationSummaryList."""
        generations = (
            mock_ce_client.list_savings_plans_purchase_recommendation_generation.return_value[
                'GenerationSummaryList'
            ]
        )
        mock_paginate.return_value = (generations, PAGINATION_COMPLETE)

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, None, None, None, None, None
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'ListSavingsPlansPurchaseRecommendationGeneration'
        assert call_kwargs['result_key'] == 'GenerationSummaryList'
        # Cost Explorer uses NextPageToken; the Savings Plans service uses nextToken.
        assert call_kwargs['token_param'] == 'NextPageToken'
        assert call_kwargs['token_key'] == 'NextPageToken'

        assert result['status'] == 'success'
        assert result['data']['GenerationSummaryList'] == generations
        assert result['data']['pagination']['complete_dataset'] is True

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.paginate_aws_response'
    )
    async def test_optional_parameters(self, mock_paginate, mock_context, mock_ce_client):
        """Status and id filters are decoded and forwarded."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await list_savings_plans_purchase_recommendation_generation(
            mock_context,
            mock_ce_client,
            'SUCCEEDED',
            ['a1b2c3d4-1111-2222-3333-444455556666'],
            'token-from-caller',
            10,
            2,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['GenerationStatus'] == 'SUCCEEDED'
        assert request_params['RecommendationIds'] == ['a1b2c3d4-1111-2222-3333-444455556666']
        assert request_params['NextPageToken'] == 'token-from-caller'
        assert request_params['PageSize'] == 10
        assert mock_paginate.call_args[1]['max_pages'] == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('LimitExceededException')

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, None, None, None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestSpRecommendationDispatch:
    """Tests for the sp_recommendation dispatcher."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.get_savings_plans_purchase_recommendation'
    )
    async def test_routes_to_get_recommendation(self, mock_impl, mock_create_client, mock_context):
        """The four required parameters arrive in order."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        result = await sp_recommendation(
            mock_context,
            operation='get_savings_plans_purchase_recommendation',
            savings_plans_type='COMPUTE_SP',
            term_in_years='ONE_YEAR',
            payment_option='NO_UPFRONT',
            lookback_period_in_days='THIRTY_DAYS',
        )

        assert result['status'] == 'success'
        mock_create_client.assert_called_once_with('ce', region_name='us-east-1')
        args = mock_impl.await_args[0]
        assert args[2:6] == ('COMPUTE_SP', 'ONE_YEAR', 'NO_UPFRONT', 'THIRTY_DAYS')

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.get_savings_plan_purchase_recommendation_details'
    )
    async def test_routes_to_get_details(self, mock_impl, mock_create_client, mock_context):
        """The detail id is the only parameter this operation takes."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_recommendation(
            mock_context,
            operation='get_savings_plan_purchase_recommendation_details',
            recommendation_detail_id='d1e2f3a4',
        )

        assert mock_impl.await_args[0][2] == 'd1e2f3a4'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.start_savings_plans_purchase_recommendation_generation'
    )
    async def test_routes_to_start_generation(self, mock_impl, mock_create_client, mock_context):
        """The refresh takes no parameters beyond the client."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_recommendation(
            mock_context,
            operation='start_savings_plans_purchase_recommendation_generation',
        )

        mock_impl.assert_awaited_once()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.list_savings_plans_purchase_recommendation_generation'
    )
    async def test_routes_to_list_generations(self, mock_impl, mock_create_client, mock_context):
        """The generation status filter and max_pages arrive."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_recommendation(
            mock_context,
            operation='list_savings_plans_purchase_recommendation_generation',
            generation_status='FAILED',
            max_pages=2,
        )

        args = mock_impl.await_args[0]
        assert args[2] == 'FAILED'
        assert args[6] == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    async def test_unsupported_operation_lists_the_valid_ones(
        self, mock_create_client, mock_context
    ):
        """An unknown operation names the four that exist."""
        result = await sp_recommendation(mock_context, operation='delete_recommendation')

        assert result['status'] == 'error'
        message = result['message']
        assert 'get_savings_plans_purchase_recommendation' in message
        assert 'get_savings_plan_purchase_recommendation_details' in message
        assert 'start_savings_plans_purchase_recommendation_generation' in message
        assert 'list_savings_plans_purchase_recommendation_generation' in message

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_recommendation_tools.create_aws_client'
    )
    async def test_client_creation_failure_is_reported(self, mock_create_client, mock_context):
        """A client that cannot be built surfaces as an error, not a crash."""
        mock_create_client.side_effect = ValueError("Service 'ce' is not allowed")

        result = await sp_recommendation(
            mock_context, operation='get_savings_plans_purchase_recommendation'
        )

        assert result['status'] == 'error'


def test_sp_recommendation_server_initialization():
    """The server is named and carries instructions."""
    assert sp_recommendation_server.name == 'sp-recommendation-tools'
    assert sp_recommendation_server.instructions is not None
