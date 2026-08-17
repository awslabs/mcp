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

This tool is read-only: it retrieves analyses that were started elsewhere. These tests
fix that boundary, and the pagination token spelling, which is NextPageToken on Cost
Explorer and lowercase nextToken on the Savings Plans service.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.sp_purchase_analyzer_tools import (
    get_commitment_purchase_analysis,
    list_commitment_purchase_analyses,
    sp_purchase_analyzer,
    sp_purchase_analyzer_server,
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
        """Starting an analysis is a mutation, so the dispatcher rejects it."""
        result = await sp_purchase_analyzer(
            mock_context, operation='start_commitment_purchase_analysis'
        )

        assert result['status'] == 'error'
        message = result['message']
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
