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
    'pages_fetched': 1,
    'total_results': 1,
    'has_more': False,
    'next_token': None,
    'duration_ms': 1,
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
    """Tests for list_commitment_purchase_analyses."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_ce_client):
        """Analyses page through AnalysisSummaryList."""
        analyses = mock_ce_client.list_commitment_purchase_analyses.return_value[
            'AnalysisSummaryList'
        ]
        mock_paginate.return_value = (analyses, PAGINATION_COMPLETE)

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, None, None, None
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'ListCommitmentPurchaseAnalyses'
        assert call_kwargs['result_key'] == 'AnalysisSummaryList'
        assert call_kwargs['token_param'] == 'NextPageToken'
        assert call_kwargs['token_key'] == 'NextPageToken'

        assert result['status'] == 'success'
        assert result['data']['AnalysisSummaryList'] == analyses
        assert result['data']['pagination']['complete_dataset'] is True

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.paginate_aws_response'
    )
    async def test_optional_parameters(self, mock_paginate, mock_context, mock_ce_client):
        """Listing what has already run is cheaper than starting another analysis."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await list_commitment_purchase_analyses(
            mock_context,
            mock_ce_client,
            'SUCCEEDED',
            ['23a6da4c-c5f8-448b-8e69-31c27d0f2603'],
            'token-from-caller',
            10,
            2,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['AnalysisStatus'] == 'SUCCEEDED'
        assert request_params['AnalysisIds'] == ['23a6da4c-c5f8-448b-8e69-31c27d0f2603']
        assert request_params['NextPageToken'] == 'token-from-caller'
        assert request_params['PageSize'] == 10
        assert mock_paginate.call_args[1]['max_pages'] == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_ce_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('AccessDeniedException')

        result = await list_commitment_purchase_analyses(
            mock_context, mock_ce_client, None, None, None, None, None
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
        """The status filter and max_pages arrive."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_purchase_analyzer(
            mock_context,
            operation='list_commitment_purchase_analyses',
            analysis_status='PROCESSING',
            max_pages=2,
        )

        args = mock_impl.await_args[0]
        assert args[2] == 'PROCESSING'
        assert args[6] == 2

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
