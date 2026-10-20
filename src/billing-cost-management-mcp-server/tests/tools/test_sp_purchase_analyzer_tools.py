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

"""Tests for the Savings Plans Purchase Analyzer tools.

start_commitment_purchase_analysis is the only nested request in the Savings Plans family,
so these tests fix the shape of CommitmentPurchaseAnalysisConfiguration and the analysis
type spelling, which is TARGET_AVERAGE_COVERAGE rather than the shorter name that reads more
naturally. They also fix the pagination token spelling, which is NextPageToken on Cost
Explorer and lowercase nextToken on the Savings Plans service.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools import (
    get_commitment_purchase_analysis,
    list_commitment_purchase_analyses,
    sp_purchase_analyzer,
    sp_purchase_analyzer_server,
    start_commitment_purchase_analysis,
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
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    client = MagicMock()
    client.start_commitment_purchase_analysis.return_value = {
        'AnalysisId': '23a6da4c-c5f8-448b-8e69-31c27d0f2603',
        'AnalysisStartedTime': '2026-08-11T22:13:33Z',
        'EstimatedCompletionTime': '2026-08-11T22:13:42Z',
    }
    client.get_commitment_purchase_analysis.return_value = {
        'AnalysisId': '23a6da4c-c5f8-448b-8e69-31c27d0f2603',
        'AnalysisStatus': 'SUCCEEDED',
        'AnalysisStartedTime': '2026-08-11T22:13:33Z',
        'AnalysisCompletionTime': '2026-08-11T22:13:38Z',
        'AnalysisDetails': {
            'SavingsPlansPurchaseAnalysisDetails': {
                'CurrentAverageCoverage': '5.62',
                'EstimatedAverageCoverage': '84.37',
                'EstimatedAverageUtilization': '96.16',
                'UpfrontCost': '0.0',
            }
        },
    }
    client.list_commitment_purchase_analyses.return_value = {
        'AnalysisSummaryList': [
            {
                'AnalysisId': '23a6da4c-c5f8-448b-8e69-31c27d0f2603',
                'AnalysisStatus': 'SUCCEEDED',
                'AnalysisStartedTime': '2026-08-11T22:13:33Z',
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

COMPUTE_SP_TO_ADD = [
    {'SavingsPlansType': 'COMPUTE_SP', 'TermInYears': 'ONE_YEAR', 'PaymentOption': 'NO_UPFRONT'}
]


def _analysis_config(mock_ce_client):
    """Pull the nested analysis configuration out of the recorded call."""
    kwargs = mock_ce_client.start_commitment_purchase_analysis.call_args[1]
    return kwargs['CommitmentPurchaseAnalysisConfiguration'][
        'SavingsPlansPurchaseAnalysisConfiguration'
    ]


@pytest.mark.asyncio
class TestStartCommitmentPurchaseAnalysis:
    """Tests for start_commitment_purchase_analysis."""

    async def test_max_savings(self, mock_context, mock_ce_client):
        """MAX_SAVINGS still requires SavingsPlansToAdd and a lookback window."""
        result = await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
            'MAX_SAVINGS',
            COMPUTE_SP_TO_ADD,
            None,
            '2026-07-15',
            '2026-08-14',
            None,
            None,
            None,
        )

        config = _analysis_config(mock_ce_client)
        assert config['AnalysisType'] == 'MAX_SAVINGS'
        assert config['SavingsPlansToAdd'] == COMPUTE_SP_TO_ADD
        assert config['LookBackTimePeriod'] == {'Start': '2026-07-15', 'End': '2026-08-14'}
        # A commitment target is not sent unless the caller asked for one.
        assert 'SavingsPlansTargetCoverage' not in config

        assert result['status'] == 'success'
        assert result['data']['AnalysisId'] == '23a6da4c-c5f8-448b-8e69-31c27d0f2603'
        assert result['data']['EstimatedCompletionTime'] == '2026-08-11T22:13:42Z'

    async def test_target_average_coverage(self, mock_context, mock_ce_client):
        """The coverage target is an integer percentage on the nested configuration."""
        await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
            'TARGET_AVERAGE_COVERAGE',
            COMPUTE_SP_TO_ADD,
            None,
            '2026-07-15',
            '2026-08-14',
            85,
            'PAYER',
            None,
        )

        config = _analysis_config(mock_ce_client)
        assert config['AnalysisType'] == 'TARGET_AVERAGE_COVERAGE'
        assert config['SavingsPlansTargetCoverage'] == 85
        assert config['AccountScope'] == 'PAYER'

    async def test_excluding_a_plan_models_an_expiry(self, mock_context, mock_ce_client):
        """SavingsPlansToExclude takes plan ARNs and reaches the config unchanged."""
        await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
            'MAX_SAVINGS',
            COMPUTE_SP_TO_ADD,
            ['arn:aws:savingsplans::123456789012:savingsplan/d6a9a682'],
            '2026-07-15',
            '2026-08-14',
            None,
            'LINKED',
            '123456789012',
        )

        config = _analysis_config(mock_ce_client)
        assert config['SavingsPlansToExclude'] == [
            'arn:aws:savingsplans::123456789012:savingsplan/d6a9a682'
        ]
        assert config['AccountId'] == '123456789012'
        assert config['AccountScope'] == 'LINKED'

    async def test_missing_required_parameters_are_rejected_by_botocore(
        self, mock_context, mock_ce_client
    ):
        """The tool does not invent a scenario, so no analysis is spent."""
        mock_ce_client.start_commitment_purchase_analysis.side_effect = Exception(
            'Parameter validation failed: Missing required parameter in '
            'CommitmentPurchaseAnalysisConfiguration.'
            'SavingsPlansPurchaseAnalysisConfiguration: "LookBackTimePeriod"'
        )

        result = await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
            'MAX_SAVINGS',
            COMPUTE_SP_TO_ADD,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'error'

    async def test_omitted_required_fields_are_left_out_of_the_config(
        self, mock_context, mock_ce_client
    ):
        """A missing field is left out entirely, so botocore names it rather than typing None.

        The API rejects the empty configuration; the point of this test is that the tool builds
        the config from only what it was given, letting the service report exactly what is missing.
        """
        mock_ce_client.start_commitment_purchase_analysis.side_effect = Exception(
            'Parameter validation failed: Missing required parameter'
        )

        result = await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
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
        config = _analysis_config(mock_ce_client)
        assert 'AnalysisType' not in config
        assert 'SavingsPlansToAdd' not in config
        assert 'LookBackTimePeriod' not in config

    async def test_error(self, mock_context, mock_ce_client):
        """An analysis already in flight is reported rather than raised."""
        mock_ce_client.start_commitment_purchase_analysis.side_effect = Exception(
            'GenerationExistsException'
        )

        result = await start_commitment_purchase_analysis(
            mock_context,
            mock_ce_client,
            'MAX_SAVINGS',
            COMPUTE_SP_TO_ADD,
            None,
            '2026-07-15',
            '2026-08-14',
            None,
            None,
            None,
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestGetCommitmentPurchaseAnalysis:
    """Tests for get_commitment_purchase_analysis."""

    async def test_basic(self, mock_context, mock_ce_client):
        """The analysis is fetched by id and returned as the API shapes it."""
        result = await get_commitment_purchase_analysis(
            mock_context, mock_ce_client, '23a6da4c-c5f8-448b-8e69-31c27d0f2603'
        )

        mock_ce_client.get_commitment_purchase_analysis.assert_called_once_with(
            AnalysisId='23a6da4c-c5f8-448b-8e69-31c27d0f2603'
        )
        assert result['status'] == 'success'
        assert result['data']['AnalysisStatus'] == 'SUCCEEDED'
        details = result['data']['AnalysisDetails']['SavingsPlansPurchaseAnalysisDetails']
        assert details['EstimatedAverageCoverage'] == '84.37'

    async def test_error(self, mock_context, mock_ce_client):
        """An unknown id is reported rather than raised."""
        mock_ce_client.get_commitment_purchase_analysis.side_effect = Exception(
            'AnalysisNotFoundException'
        )

        result = await get_commitment_purchase_analysis(mock_context, mock_ce_client, 'missing-id')

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestListCommitmentPurchaseAnalyses:
    """Tests for list_commitment_purchase_analyses, run through the real pagination helper."""

    async def test_basic(self, mock_context, mock_ce_client):
        """Analyses come back under AnalysisSummaryList with a complete pagination block."""
        analyses = mock_ce_client.list_commitment_purchase_analyses.return_value[
            'AnalysisSummaryList'
        ]

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, None, None
        )

        assert result['status'] == 'success'
        assert result['data']['AnalysisSummaryList'] == analyses
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        # Without max_items the largest page is requested.
        mock_ce_client.list_commitment_purchase_analyses.assert_called_once_with(PageSize=600)

    async def test_no_max_items_fetches_every_page(self, mock_context, mock_ce_client):
        """Every page is fetched, following NextPageToken (Cost Explorer's spelling)."""
        mock_ce_client.list_commitment_purchase_analyses.side_effect = [
            {'AnalysisSummaryList': [{'AnalysisId': 'a'}], 'NextPageToken': 't1'},
            {'AnalysisSummaryList': [{'AnalysisId': 'b'}]},
        ]

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, 'SUCCEEDED', None, None, None
        )

        data = result['data']
        assert [a['AnalysisId'] for a in data['AnalysisSummaryList']] == ['a', 'b']
        assert 'complete_dataset' not in data
        assert data['pagination']['items_returned'] == 2
        calls = mock_ce_client.list_commitment_purchase_analyses.call_args_list
        assert calls[0].kwargs == {'AnalysisStatus': 'SUCCEEDED', 'PageSize': 600}
        assert calls[1].kwargs == {
            'AnalysisStatus': 'SUCCEEDED',
            'PageSize': 600,
            'NextPageToken': 't1',
        }

    async def test_max_items_stops_and_returns_the_token(self, mock_context, mock_ce_client):
        """max_items sizes the page, and the service token comes back for continuation."""
        mock_ce_client.list_commitment_purchase_analyses.return_value = {
            'AnalysisSummaryList': [{'AnalysisId': 'a'}, {'AnalysisId': 'b'}],
            'NextPageToken': 'more',
        }

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, 2, None
        )

        data = result['data']
        assert data['complete_dataset'] is False
        assert 'Partial data' in data['warning']
        assert data['pagination']['next_token'] == 'more'
        mock_ce_client.list_commitment_purchase_analyses.assert_called_once_with(PageSize=2)

    async def test_continuation_sends_caller_token_and_identical_params(
        self, mock_context, mock_ce_client
    ):
        """Listing what has already run is cheaper than starting another analysis."""
        await list_commitment_purchase_analyses(
            mock_context,
            mock_ce_client,
            'SUCCEEDED',
            ['23a6da4c-c5f8-448b-8e69-31c27d0f2603'],
            None,
            'token-from-caller',
        )

        mock_ce_client.list_commitment_purchase_analyses.assert_called_once_with(
            AnalysisStatus='SUCCEEDED',
            AnalysisIds=['23a6da4c-c5f8-448b-8e69-31c27d0f2603'],
            PageSize=600,
            NextPageToken='token-from-caller',
        )

    async def test_rejected_token_maps_to_invalid_next_token(self, mock_context, mock_ce_client):
        """A stale caller token is reported as invalid_next_token."""
        from botocore.exceptions import ClientError

        mock_ce_client.list_commitment_purchase_analyses.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'ListCommitmentPurchaseAnalyses',
        )

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, None, 'stale'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    async def test_error(self, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_ce_client.list_commitment_purchase_analyses.side_effect = Exception(
            'AccessDeniedException'
        )

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestSpPurchaseAnalyzerDispatch:
    """Tests for the sp_purchase_analyzer dispatcher."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.start_commitment_purchase_analysis'
    )
    async def test_routes_to_start_analysis(self, mock_impl, mock_create_client, mock_context):
        """The analysis configuration parameters arrive in order."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_purchase_analyzer(
            mock_context,
            operation='start_commitment_purchase_analysis',
            analysis_type='TARGET_AVERAGE_COVERAGE',
            savings_plans_to_add=COMPUTE_SP_TO_ADD,
            look_back_start='2026-07-15',
            look_back_end='2026-08-14',
            savings_plans_target_coverage=85,
        )

        args = mock_impl.await_args[0]
        assert args[2] == 'TARGET_AVERAGE_COVERAGE'
        assert args[3] == COMPUTE_SP_TO_ADD
        assert args[5] == '2026-07-15'
        assert args[6] == '2026-08-14'
        assert args[7] == 85

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.get_commitment_purchase_analysis'
    )
    async def test_routes_to_get_analysis(self, mock_impl, mock_create_client, mock_context):
        """The analysis id is the only parameter this operation takes."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_purchase_analyzer(
            mock_context,
            operation='get_commitment_purchase_analysis',
            analysis_id='23a6da4c',
        )

        assert mock_impl.await_args[0][2] == '23a6da4c'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.list_commitment_purchase_analyses'
    )
    async def test_routes_to_list_analyses(self, mock_impl, mock_create_client, mock_context):
        """The status filter, max_items and next_token arrive."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_purchase_analyzer(
            mock_context,
            operation='list_commitment_purchase_analyses',
            analysis_status='PROCESSING',
            max_items=2,
            next_token='tok',
        )

        args = mock_impl.await_args[0]
        assert args[2] == 'PROCESSING'
        assert args[4] == 2
        assert args[5] == 'tok'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.create_aws_client'
    )
    async def test_unsupported_operation_lists_the_valid_ones(
        self, mock_create_client, mock_context
    ):
        """An unknown operation names the three that exist."""
        result = await sp_purchase_analyzer(mock_context, operation='delete_commitment_purchase')

        assert result['status'] == 'error'
        message = result['message']
        assert 'start_commitment_purchase_analysis' in message
        assert 'get_commitment_purchase_analysis' in message
        assert 'list_commitment_purchase_analyses' in message

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.create_aws_client'
    )
    async def test_client_creation_failure_is_reported(self, mock_create_client, mock_context):
        """A client that cannot be built surfaces as an error, not a crash."""
        mock_create_client.side_effect = ValueError("Service 'ce' is not allowed")

        result = await sp_purchase_analyzer(
            mock_context, operation='list_commitment_purchase_analyses'
        )

        assert result['status'] == 'error'


def test_sp_purchase_analyzer_server_initialization():
    """The server is named and carries instructions."""
    assert sp_purchase_analyzer_server.name == 'sp-purchase-analyzer-tools'
    assert sp_purchase_analyzer_server.instructions is not None
