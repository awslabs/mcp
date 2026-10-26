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
    'has_more': False,
    'next_token': None,
    'items_returned': 1,
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
        )

        request_params = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert request_params == {
            'SavingsPlansType': 'COMPUTE_SP',
            'TermInYears': 'ONE_YEAR',
            'PaymentOption': 'NO_UPFRONT',
            'LookbackPeriodInDays': 'THIRTY_DAYS',
            # Without max_items the largest page is requested.
            'PageSize': 6000,
        }

        assert result['status'] == 'success'
        # The generation timestamp lives on Metadata, not on the recommendation.
        assert result['data']['Metadata']['GenerationTimestamp'] == '2026-08-09T00:00:00Z'
        # A single page is returned as the API shaped it, with pagination added alongside.
        assert (
            result['data']['SavingsPlansPurchaseRecommendation']
            == (sample_recommendation['SavingsPlansPurchaseRecommendation'])
        )
        assert result['data']['pagination'] == PAGINATION_COMPLETE

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
            25,
            'token-from-caller',
        )

        request_params = mock_ce_client.get_savings_plans_purchase_recommendation.call_args[1]
        assert request_params['AccountScope'] == 'PAYER'
        assert request_params['Filter'] == {
            'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111122223333']}
        }
        # The caller's token is sent unchanged, and max_items sizes the page.
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
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        assert 'complete_dataset' not in {k for k in result['data'] if k != 'pagination'}
        # Every page repeats the request; only the token changes.
        calls = mock_ce_client.get_savings_plans_purchase_recommendation.call_args_list
        assert all(
            {k: v for k, v in c[1].items() if k != 'NextPageToken'} == calls[0][1] for c in calls
        )
        # The merged result reports paging through pagination, not a stray top-level token.
        assert 'NextPageToken' not in result['data']

    async def test_max_items_stops_and_reports_the_token(self, mock_context, mock_ce_client):
        """Stopping short is reported, so a truncated recommendation cannot read as complete."""
        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = [
            {
                'SavingsPlansPurchaseRecommendation': {
                    'SavingsPlansPurchaseRecommendationDetails': [
                        {'RecommendationDetailId': f'd{page}'}
                    ]
                },
                'NextPageToken': token,
            }
            for page, token in ((1, 'page-2'), (2, 'more-to-come'))
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
            2,
            None,
        )

        # One detail per page: the page sizes are 2 then 1, and the run stops at 2 items.
        calls = mock_ce_client.get_savings_plans_purchase_recommendation.call_args_list
        assert [c[1]['PageSize'] for c in calls] == [2, 1]
        assert result['data']['complete_dataset'] is False
        assert 'Partial data' in result['data']['warning']
        assert result['data']['pagination']['complete_dataset'] is False
        assert result['data']['pagination']['has_more'] is True
        assert result['data']['pagination']['next_token'] == 'more-to-come'

    async def test_empty_string_token_on_last_page_ends_pagination(
        self, mock_context, mock_ce_client
    ):
        """An empty-string token on the final page reads as complete, not as more pages.

        Some AWS APIs return ``NextPageToken: ""`` on the last page rather than omitting it. The
        loop already stops on a falsy token, so no request is made for an empty page, but the
        metadata must report the run as complete rather than offering ``""`` as a resume token.
        """

        def page(detail_id, token):
            return {
                'SavingsPlansPurchaseRecommendation': {
                    'SavingsPlansPurchaseRecommendationDetails': [
                        {'RecommendationDetailId': detail_id}
                    ]
                },
                'NextPageToken': token,
            }

        mock_ce_client.get_savings_plans_purchase_recommendation.side_effect = [
            page('detail-1', 'token-1'),
            page('detail-2', ''),
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
        )

        # The empty-token page is consumed and no further request is made for an empty token.
        assert mock_ce_client.get_savings_plans_purchase_recommendation.call_count == 2
        pagination = result['data']['pagination']
        assert pagination['has_more'] is False
        assert pagination['next_token'] is None
        assert pagination['complete_dataset'] is True
        assert pagination['items_returned'] == 2

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
        )

        assert result['status'] == 'success'
        recommendation = result['data']['SavingsPlansPurchaseRecommendation']
        assert recommendation['SavingsPlansPurchaseRecommendationDetails'] == [
            {'RecommendationDetailId': 'detail-1'}
        ]
        assert result['data']['pagination']['items_returned'] == 1

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

    async def test_basic(self, mock_context, mock_ce_client):
        """Generations come back under GenerationSummaryList at the largest page size."""
        generations = (
            mock_ce_client.list_savings_plans_purchase_recommendation_generation.return_value[
                'GenerationSummaryList'
            ]
        )

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, None, None, None, None
        )

        assert result['status'] == 'success'
        assert result['data']['GenerationSummaryList'] == generations
        assert result['data']['pagination']['complete_dataset'] is True
        mock_ce_client.list_savings_plans_purchase_recommendation_generation.assert_called_once_with(
            PageSize=6000
        )

    async def test_no_max_items_fetches_every_page(self, mock_context, mock_ce_client):
        """Cost Explorer uses NextPageToken; every page is followed."""
        method = mock_ce_client.list_savings_plans_purchase_recommendation_generation
        method.side_effect = [
            {'GenerationSummaryList': [{'RecommendationId': 'a'}], 'NextPageToken': 't1'},
            {'GenerationSummaryList': [{'RecommendationId': 'b'}]},
        ]

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, 'SUCCEEDED', None, None, None
        )

        data = result['data']
        assert [g['RecommendationId'] for g in data['GenerationSummaryList']] == ['a', 'b']
        assert 'complete_dataset' not in data
        assert method.call_args_list[1][1] == {
            'GenerationStatus': 'SUCCEEDED',
            'PageSize': 6000,
            'NextPageToken': 't1',
        }

    async def test_max_items_stops_and_returns_the_token(self, mock_context, mock_ce_client):
        """max_items sizes the page and the service token comes back."""
        method = mock_ce_client.list_savings_plans_purchase_recommendation_generation
        method.return_value = {
            'GenerationSummaryList': [{'RecommendationId': 'a'}],
            'NextPageToken': 'more',
        }

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, None, None, 1, None
        )

        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 'more'
        method.assert_called_once_with(PageSize=1)

    async def test_continuation_sends_caller_token_and_identical_params(
        self, mock_context, mock_ce_client
    ):
        """Status and id filters are forwarded with the caller's token."""
        await list_savings_plans_purchase_recommendation_generation(
            mock_context,
            mock_ce_client,
            'SUCCEEDED',
            ['a1b2c3d4-1111-2222-3333-444455556666'],
            None,
            'token-from-caller',
        )

        mock_ce_client.list_savings_plans_purchase_recommendation_generation.assert_called_once_with(
            GenerationStatus='SUCCEEDED',
            RecommendationIds=['a1b2c3d4-1111-2222-3333-444455556666'],
            PageSize=6000,
            NextPageToken='token-from-caller',
        )

    async def test_error(self, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_ce_client.list_savings_plans_purchase_recommendation_generation.side_effect = (
            Exception('LimitExceededException')
        )

        result = await list_savings_plans_purchase_recommendation_generation(
            mock_context, mock_ce_client, None, None, None, None
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
        # max_items and next_token default to None (fetch everything from the start).
        assert args[8:] == (None, None)

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
        """The generation status filter, max_items and next_token arrive."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_recommendation(
            mock_context,
            operation='list_savings_plans_purchase_recommendation_generation',
            generation_status='FAILED',
            max_items=2,
            next_token='tok',
        )

        args = mock_impl.await_args[0]
        assert args[2] == 'FAILED'
        assert args[4:6] == (2, 'tok')

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
