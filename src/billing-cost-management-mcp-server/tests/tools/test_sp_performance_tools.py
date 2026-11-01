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

"""Unit tests for the sp_performance_tools module.

These tests verify the functionality of AWS Savings Plans performance monitoring tools, including:
- Retrieving Savings Plans coverage metrics and spend analysis
- Getting detailed utilization tracking and commitment usage patterns
- Analyzing Savings Plans performance by individual plan and aggregated totals
- Handling time-based coverage analysis with various granularity options
- Error handling for missing Savings Plans data and invalid filter parameters
"""

import botocore.session
import json
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools import (
    get_savings_plans_coverage,
    get_savings_plans_utilization,
    get_savings_plans_utilization_details,
    sp_performance_server,
)
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from fastmcp.tools import FunctionTool
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


PAGINATION_COMPLETE = {
    'complete_dataset': True,
    'has_more': False,
    'next_token': None,
    'items_returned': 1,
}


SP_TOOLS = 'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools'


async def _call_tool(client, ctx, operation, **kwargs):
    """Call the registered sp-performance tool with a mocked Cost Explorer client."""
    tool = await sp_performance_server.get_tool('sp-performance')
    assert isinstance(tool, FunctionTool)
    with patch(f'{SP_TOOLS}.create_aws_client', return_value=client):
        return await tool.fn(
            ctx, operation=operation, start_date='2023-01-01', end_date='2023-01-31', **kwargs
        )


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
    mock_client = MagicMock()

    # Set up mock response for get_savings_plans_coverage
    mock_client.get_savings_plans_coverage.return_value = {
        'SavingsPlansCoverages': [
            {
                'TimePeriod': {
                    'Start': '2023-01-01',
                    'End': '2023-01-02',
                },
                'SpendCoveredBySavingsPlans': '75.0',
                'OnDemandCost': '100.0',
                'TotalCost': '400.0',
                'CoveragePercentage': '75.0',
                'Groups': [
                    {
                        'Attributes': {
                            'SERVICE': 'Amazon Elastic Compute Cloud - Compute',
                            'REGION': 'us-east-1',
                        },
                        'Coverage': {
                            'SpendCoveredBySavingsPlans': '60.0',
                            'OnDemandCost': '80.0',
                            'TotalCost': '300.0',
                            'CoveragePercentage': '75.0',
                        },
                    },
                    {
                        'Attributes': {
                            'SERVICE': 'AWS Lambda',
                            'REGION': 'us-east-1',
                        },
                        'Coverage': {
                            'SpendCoveredBySavingsPlans': '15.0',
                            'OnDemandCost': '20.0',
                            'TotalCost': '100.0',
                            'CoveragePercentage': '75.0',
                        },
                    },
                ],
            }
        ],
    }

    # Set up mock response for get_savings_plans_utilization.
    # This mirrors the documented GetSavingsPlansUtilization response: the member
    # is SavingsPlansUtilizationsByTime, the figures nest under Utilization /
    # Savings / AmortizedCommitment, every monetary value is a decimal string,
    # and there is no continuation token because the operation is not paginated.
    mock_client.get_savings_plans_utilization.return_value = {
        'SavingsPlansUtilizationsByTime': [
            {
                'TimePeriod': {
                    'Start': '2023-01-01',
                    'End': '2023-01-02',
                },
                'Utilization': {
                    'TotalCommitment': '100.0',
                    'UsedCommitment': '95.0',
                    'UnusedCommitment': '5.0',
                    'UtilizationPercentage': '95.0',
                },
                'Savings': {
                    'NetSavings': '10.0',
                    'OnDemandCostEquivalent': '110.0',
                },
                'AmortizedCommitment': {
                    'AmortizedRecurringCommitment': '80.0',
                    'AmortizedUpfrontCommitment': '20.0',
                    'TotalAmortizedCommitment': '100.0',
                },
            }
        ],
        'Total': {
            'Utilization': {
                'TotalCommitment': '100.0',
                'UsedCommitment': '95.0',
                'UnusedCommitment': '5.0',
                'UtilizationPercentage': '95.0',
            },
            'Savings': {
                'NetSavings': '10.0',
                'OnDemandCostEquivalent': '110.0',
            },
            'AmortizedCommitment': {
                'AmortizedRecurringCommitment': '80.0',
                'AmortizedUpfrontCommitment': '20.0',
                'TotalAmortizedCommitment': '100.0',
            },
        },
    }

    # Set up mock response for get_savings_plans_utilization_details
    mock_client.get_savings_plans_utilization_details.return_value = {
        'SavingsPlansUtilizationDetails': [
            # Shaped as GetSavingsPlansUtilizationDetails actually responds: the
            # figures nest under `Utilization`, `Savings` and
            # `AmortizedCommitment`, and each monetary value is a decimal string.
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-12345abcdef',
                'Attributes': {
                    'Region': 'us-east-1',
                    'InstanceFamily': 'm5',
                    'SavingsPlansType': 'EC2InstanceSavingsPlans',
                },
                'Utilization': {
                    'TotalCommitment': '20.0',
                    'UsedCommitment': '19.0',
                    'UnusedCommitment': '1.0',
                    'UtilizationPercentage': '95.0',
                },
                'Savings': {
                    'NetSavings': '10.0',
                    'OnDemandCostEquivalent': '30.0',
                },
                'AmortizedCommitment': {
                    'AmortizedRecurringCommitment': '19.0',
                    'AmortizedUpfrontCommitment': '1.0',
                    'TotalAmortizedCommitment': '20.0',
                },
            },
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-67890ghijkl',
                'Attributes': {
                    'Region': 'us-west-2',
                    'InstanceFamily': 'c5',
                    'SavingsPlansType': 'ComputeSavingsPlans',
                },
                'Utilization': {
                    'TotalCommitment': '80.0',
                    'UsedCommitment': '60.0',
                    'UnusedCommitment': '20.0',
                    'UtilizationPercentage': '75.0',
                },
                'Savings': {
                    'NetSavings': '40.0',
                    'OnDemandCostEquivalent': '120.0',
                },
                'AmortizedCommitment': {
                    'AmortizedRecurringCommitment': '75.0',
                    'AmortizedUpfrontCommitment': '5.0',
                    'TotalAmortizedCommitment': '80.0',
                },
            },
        ],
        'NextToken': None,
    }

    return mock_client


@pytest.mark.asyncio
class TestGetSavingsPlansUtilizationDetails:
    """Tests for get_savings_plans_utilization_details function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_get_savings_plans_utilization_details_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization_details with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization_details.return_value[
                'SavingsPlansUtilizationDetails'
            ],
            [],
            PAGINATION_COMPLETE,
        )

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,  # filter_expr
            None,  # max_items
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_args = mock_paginate_response.call_args[0]

        assert call_args[1] == 'GetSavingsPlansUtilizationDetails'
        assert call_args[4].result_key == 'SavingsPlansUtilizationDetails'

        request_params = call_args[3]
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        # Page size and token are the helper's to set.
        assert 'MaxResults' not in request_params

        assert result['status'] == 'success'
        assert 'savings_plans_utilization_details' in result['data']
        assert len(result['data']['savings_plans_utilization_details']) == 2
        # The item count is reported as pagination.items_returned, never as a total.
        assert 'total_count' not in result['data']

        # Rows come back as the API sent them, so the nested blocks and the
        # decimal-string precision of every monetary value are preserved.
        detail = result['data']['savings_plans_utilization_details'][0]
        assert (
            detail['SavingsPlanArn']
            == 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-12345abcdef'
        )
        assert detail['Attributes']['SavingsPlansType'] == 'EC2InstanceSavingsPlans'
        assert detail['Utilization'] == {
            'TotalCommitment': '20.0',
            'UsedCommitment': '19.0',
            'UnusedCommitment': '1.0',
            'UtilizationPercentage': '95.0',
        }
        assert detail['Savings'] == {
            'NetSavings': '10.0',
            'OnDemandCostEquivalent': '30.0',
        }
        # Previously discarded entirely.
        assert detail['AmortizedCommitment']['TotalAmortizedCommitment'] == '20.0'

        # No derived statistics are reported. The commitment-weighted aggregate
        # over these rows is what GetSavingsPlansUtilization returns; an
        # unweighted mean of the per-plan percentages is a different figure that
        # disagrees with it, and the utilized/underutilized counters applied
        # thresholds the service does not define.
        assert 'average_utilization_percentage' not in result['data']
        assert 'total_savings_plans' not in result['data']
        assert 'fully_utilized_plans' not in result['data']
        assert 'under_utilized_plans' not in result['data']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_utilization_and_savings_are_not_zeroed(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """A real-shaped row must surface its figures rather than reporting zeros.

        Regression test for the per-plan detail defect: the figures were read from
        the top level of each row and required an ``{Amount, Unit}`` mapping, but
        the API nests them and sends decimal strings. Every lookup therefore
        missed and fell back to a 0.0 default, so a fully utilized Savings Plan
        was reported as 0% utilized with $0 of savings -- as a success response,
        with no error signal. Attributes were unaffected, which made the response
        look populated.
        """
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            [
                {
                    'SavingsPlanArn': 'arn:aws:savingsplans::111122223333:savingsplan/sp-abc',
                    'Attributes': {'Region': 'Any', 'SavingsPlansType': 'ComputeSavingsPlans'},
                    'Utilization': {
                        'TotalCommitment': '0.096',
                        'UsedCommitment': '0.084',
                        'UnusedCommitment': '0.012',
                        'UtilizationPercentage': '87.5',
                    },
                    'Savings': {
                        'NetSavings': '-0.0854923752',
                        'OnDemandCostEquivalent': '0.0105076248',
                    },
                    'AmortizedCommitment': {
                        'AmortizedRecurringCommitment': '0.096',
                        'AmortizedUpfrontCommitment': '0.0',
                        'TotalAmortizedCommitment': '0.096',
                    },
                }
            ],
            [],
            PAGINATION_COMPLETE,
        )

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context, mock_ce_client, '2023-01-01', '2023-01-31', None, None
        )

        # Assert
        detail = result['data']['savings_plans_utilization_details'][0]
        assert detail['Utilization']['UsedCommitment'] == '0.084'
        assert detail['Utilization']['UtilizationPercentage'] == '87.5'
        # Full precision retained; float conversion would have truncated these.
        assert detail['Savings']['NetSavings'] == '-0.0854923752'
        assert detail['Savings']['OnDemandCostEquivalent'] == '0.0105076248'
        assert detail['AmortizedCommitment']['TotalAmortizedCommitment'] == '0.096'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_rows_without_a_percentage_pass_through(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Rows carrying no usable percentage are returned as-is, not dropped or coerced.

        The API sends an empty ``Utilization`` block for a plan in ``Returned``
        status, so this is a live response shape rather than a hypothetical.
        Every row must survive to the caller and nothing may raise.
        """
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        rows = [
            {'Utilization': {'UtilizationPercentage': '100'}},
            {'Utilization': {'UtilizationPercentage': None}},
            {'Utilization': {}},
            {},
        ]
        mock_paginate_response.return_value = (rows, [], PAGINATION_COMPLETE)

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context, mock_ce_client, '2023-01-01', '2023-01-31', None, None
        )

        # Assert
        assert result['status'] == 'success'
        assert result['data']['savings_plans_utilization_details'] == rows
        assert len(result['data']['savings_plans_utilization_details']) == 4

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_filter')
    async def test_get_savings_plans_utilization_details_with_filter(
        self,
        mock_parse_filter,
        mock_parse_json,
        mock_paginate_response,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_savings_plans_utilization_details with filter parameter."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization_details.return_value[
                'SavingsPlansUtilizationDetails'
            ],
            [],
            PAGINATION_COMPLETE,
        )

        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}
        mock_parse_filter.return_value = mock_filter

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'filter_json',  # filter_expr
            None,  # max_items
        )

        # Assert
        mock_parse_filter.assert_called_once_with('filter_json')

        request_params = mock_paginate_response.call_args[0][3]
        assert 'Filter' in request_params
        assert request_params['Filter'] == mock_filter

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_get_savings_plans_utilization_details_with_max_items(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """max_items and next_token go to the pagination helper, not into the request."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization_details.return_value[
                'SavingsPlansUtilizationDetails'
            ],
            [],
            PAGINATION_COMPLETE,
        )

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,  # filter_expr
            50,  # max_items
            'caller-token',  # next_token
        )

        # Assert
        request_params = mock_paginate_response.call_args[0][3]
        assert 'MaxResults' not in request_params
        assert 'NextToken' not in request_params
        assert mock_paginate_response.call_args[1] == {
            'max_items': 50,
            'next_token': 'caller-token',
        }

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.handle_aws_error'
    )
    async def test_get_savings_plans_utilization_details_error(
        self, mock_handle_aws_error, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization_details error handling."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        error = Exception('API error')
        mock_ce_client.get_savings_plans_utilization_details.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,  # filter_expr
            None,  # max_items
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_savings_plans_utilization_details', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestGetSavingsPlansUtilization:
    """Tests for get_savings_plans_utilization function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_get_savings_plans_utilization_basic(
        self, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        # Execute
        result = await get_savings_plans_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # filter_expr
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')

        request_params = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert len(result['data']['savings_plans_utilizations']) == 1
        assert result['data']['requested_time_period'] == {
            'start': '2023-01-01',
            'end': '2023-01-31',
        }
        # GetSavingsPlansUtilization has no top-level TimePeriod to report.
        assert 'time_period' not in result['data']

        # The utilization figures nest under Utilization and are decimal strings.
        # Reading them from the top level, or parsing them into floats, is what
        # made this tool report a fully utilized account as having no data.
        utilization = result['data']['savings_plans_utilizations'][0]
        assert utilization['Utilization'] == {
            'TotalCommitment': '100.0',
            'UsedCommitment': '95.0',
            'UnusedCommitment': '5.0',
            'UtilizationPercentage': '95.0',
        }
        assert utilization['Savings']['NetSavings'] == '10.0'
        assert utilization['AmortizedCommitment']['TotalAmortizedCommitment'] == '100.0'

        # Total is carried by the same response, and keeps the same three blocks.
        assert result['data']['total']['Utilization']['UtilizationPercentage'] == '95.0'
        assert result['data']['total']['Savings']['OnDemandCostEquivalent'] == '110.0'
        assert (
            result['data']['total']['AmortizedCommitment']['AmortizedRecurringCommitment']
            == '80.0'
        )

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_utilization_is_fetched_in_a_single_call(
        self, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Total accompanies the rows, so asking for it must not repeat the request."""
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        result = await get_savings_plans_utilization(
            mock_context, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
        )

        assert result['status'] == 'success'
        assert 'total' in result['data']
        assert mock_ce_client.get_savings_plans_utilization.call_count == 1

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_filter')
    async def test_get_savings_plans_utilization_with_filter(
        self,
        mock_parse_filter,
        mock_parse_json,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_savings_plans_utilization with filter parameter."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}
        mock_parse_filter.return_value = mock_filter

        # Execute
        result = await get_savings_plans_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'MONTHLY',
            'filter_json',  # filter_expr
        )

        # Assert
        mock_parse_filter.assert_called_once_with('filter_json')

        request_params = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert request_params['Filter'] == mock_filter
        assert request_params['Granularity'] == 'MONTHLY'

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_window_is_passed_through_without_local_revalidation(
        self, mock_get_date_range, mock_context, mock_ce_client
    ):
        """The service owns its date bounds, so the requested window reaches it unaltered.

        A local copy of the upper bound risks being stricter than the real one and
        refusing a working query, and narrowing the window silently would truncate
        the period under analysis.
        """
        future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%d')
        mock_get_date_range.return_value = ('2026-08-01', future)

        await get_savings_plans_utilization(
            mock_context, mock_ce_client, '2026-08-01', future, 'MONTHLY', None
        )

        request_params = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert request_params['TimePeriod'] == {'Start': '2026-08-01', 'End': future}

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_granularity_is_passed_through_without_local_gatekeeping(
        self, mock_get_date_range, mock_context, mock_ce_client
    ):
        """HOURLY reaches the service rather than being refused here.

        HOURLY is an opt-in Cost Explorer feature, not an unsupported one, so a
        local allowlist would refuse a working query for an account that has
        enabled it. The service reports the opt-in requirement itself.
        """
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        await get_savings_plans_utilization(
            mock_context, mock_ce_client, '2023-01-01', '2023-01-31', 'HOURLY', None
        )

        request_params = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert request_params['Granularity'] == 'HOURLY'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.handle_aws_error'
    )
    async def test_get_savings_plans_utilization_error(
        self, mock_handle_aws_error, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization error handling."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        error = Exception('API error')
        mock_ce_client.get_savings_plans_utilization.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_savings_plans_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # filter_expr
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_savings_plans_utilization', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestGetSavingsPlansCoverage:
    """Tests for get_savings_plans_coverage function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_get_savings_plans_coverage_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_coverage with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        first_page = mock_ce_client.get_savings_plans_coverage.return_value
        mock_paginate_response.return_value = (
            first_page['SavingsPlansCoverages'],
            [first_page],
            PAGINATION_COMPLETE,
        )

        # Execute
        result = await get_savings_plans_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # metrics
            None,  # group_by
            None,  # filter_expr
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_args = mock_paginate_response.call_args[0]

        assert call_args[1] == 'GetSavingsPlansCoverage'
        assert call_args[4].result_key == 'SavingsPlansCoverages'

        request_params = call_args[3]
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'
        assert request_params['Metrics'] == ['SpendCoveredBySavingsPlans']  # Default metric

        assert result['status'] == 'success'
        assert 'savings_plans_coverages' in result['data']
        assert len(result['data']['savings_plans_coverages']) == 1

        # GetSavingsPlansCoverage returns no Total, so none is reported and no extra request
        # is made for one.
        mock_ce_client.get_savings_plans_coverage.assert_not_called()
        assert 'total' not in result['data']
        assert result['data']['requested_time_period'] == {
            'start': '2023-01-01',
            'end': '2023-01-31',
        }
        assert 'time_period' not in result['data']
        assert result['data']['granularity'] == 'DAILY'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_filter')
    async def test_get_savings_plans_coverage_with_options(
        self,
        mock_parse_filter,
        mock_parse_json,
        mock_paginate_response,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_savings_plans_coverage with all optional parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_coverage.return_value['SavingsPlansCoverages'],
            [],
            PAGINATION_COMPLETE,
        )

        mock_metrics = ['SpendCoveredBySavingsPlans']
        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        mock_parse_json.side_effect = [mock_metrics, mock_group_by]
        mock_parse_filter.return_value = mock_filter

        # Execute
        result = await get_savings_plans_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'MONTHLY',
            'metrics_json',  # metrics
            'group_by_json',  # group_by
            'filter_json',  # filter_expr
        )

        # Assert
        mock_parse_json.assert_any_call('metrics_json', 'metrics')
        mock_parse_json.assert_any_call('group_by_json', 'group_by')
        mock_parse_filter.assert_called_once_with('filter_json')

        request_params = mock_paginate_response.call_args[0][3]
        assert request_params['Metrics'] == mock_metrics
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        # Granularity and GroupBy are mutually exclusive for GetSavingsPlansCoverage:
        # when GroupBy is set, Granularity must not be sent.
        assert 'Granularity' not in request_params

        assert result['status'] == 'success'
        # Granularity was not sent, so the response does not claim one.
        assert 'granularity' not in result['data']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.handle_aws_error'
    )
    async def test_get_savings_plans_coverage_error(
        self, mock_handle_aws_error, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_coverage error handling."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        error = Exception('API error')
        mock_ce_client.get_savings_plans_coverage.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_savings_plans_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # metrics
            None,  # group_by
            None,  # filter_expr
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_savings_plans_coverage', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestSPPerformance:
    """Tests for the registered sp-performance tool's operation dispatch."""

    async def test_sp_performance_coverage(self, mock_context, mock_ce_client):
        """Coverage is dispatched to GetSavingsPlansCoverage and reports no total."""
        result = await _call_tool(mock_ce_client, mock_context, 'get_savings_plans_coverage')

        assert result['status'] == 'success'
        assert len(result['data']['savings_plans_coverages']) == 1
        assert 'total' not in result['data']
        mock_ce_client.get_savings_plans_coverage.assert_called_once()

    async def test_sp_performance_utilization(self, mock_context, mock_ce_client):
        """Utilization is dispatched to GetSavingsPlansUtilization and keeps the API Total."""
        result = await _call_tool(mock_ce_client, mock_context, 'get_savings_plans_utilization')

        assert result['status'] == 'success'
        assert len(result['data']['savings_plans_utilizations']) == 1
        assert result['data']['total']['Utilization']['UtilizationPercentage'] == '95.0'
        mock_ce_client.get_savings_plans_utilization.assert_called_once()

    async def test_sp_performance_utilization_details(self, mock_context, mock_ce_client):
        """Utilization details is dispatched to GetSavingsPlansUtilizationDetails."""
        result = await _call_tool(
            mock_ce_client, mock_context, 'get_savings_plans_utilization_details'
        )

        assert result['status'] == 'success'
        assert len(result['data']['savings_plans_utilization_details']) == 2
        mock_ce_client.get_savings_plans_utilization_details.assert_called_once()

    async def test_sp_performance_unsupported_operation(self, mock_context, mock_ce_client):
        """An unknown operation is rejected without calling Cost Explorer."""
        result = await _call_tool(mock_ce_client, mock_context, 'unsupported_operation')

        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']
        assert not mock_ce_client.method_calls


def test_sp_performance_server_initialization():
    """Test that the sp_performance_server is properly initialized."""
    # Verify the server name
    assert sp_performance_server.name == 'sp-performance-tools'

    # Verify the server instructions
    assert sp_performance_server.instructions and (
        'Tools for working with AWS Savings Plans Performance'
        in sp_performance_server.instructions
    )


@pytest.fixture
def mock_context_async():
    """Create a proper async mock context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    return context


@pytest.mark.asyncio
class TestCoverageGaps:
    """Tests targeting specific uncovered lines."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_savings_plans_utilization_empty_data(
        self, mock_get_date_range, mock_context_async
    ):
        """Test utilization when the account genuinely has no Savings Plans."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': []
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_context_logger'
        ) as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await get_savings_plans_utilization(
                mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
            )

            assert result['status'] == 'success'
            assert result['data']['savings_plans_utilizations'] == []
            assert 'No Savings Plans utilization data found' in result['data']['message']
            mock_logger_instance.warning.assert_called_once()

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_utilization_present_is_never_reported_as_no_data(
        self, mock_get_date_range, mock_context_async
    ):
        """Rows returned by the API must never trigger the "no data" message.

        Reading the wrong response member returned an empty list silently, so a
        fully utilized account was reported as having no Savings Plans at all.
        """
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {
                    'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                    'Utilization': {
                        'TotalCommitment': '100.0',
                        'UsedCommitment': '100.0',
                        'UnusedCommitment': '0.0',
                        'UtilizationPercentage': '100.0',
                    },
                }
            ],
            'Total': {'Utilization': {'UtilizationPercentage': '100.0'}},
        }

        result = await get_savings_plans_utilization(
            mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
        )

        assert result['status'] == 'success'
        assert 'message' not in result['data']
        assert len(result['data']['savings_plans_utilizations']) == 1
        assert result['data']['total']['Utilization']['UtilizationPercentage'] == '100.0'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_savings_plans_utilization_partial_blocks(
        self, mock_get_date_range, mock_context_async
    ):
        """Savings and AmortizedCommitment are optional and their absence is not invented."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {
                    'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                    'Utilization': {'TotalCommitment': '100.0'},
                }
            ],
            'Total': {'Utilization': {'TotalCommitment': '100.0'}},
        }

        result = await get_savings_plans_utilization(
            mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
        )

        assert result['status'] == 'success'
        utilization = result['data']['savings_plans_utilizations'][0]
        assert utilization['Utilization'] == {'TotalCommitment': '100.0'}
        assert 'Savings' not in utilization
        assert 'AmortizedCommitment' not in utilization

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_savings_plans_utilization_api_error_is_surfaced(
        self, mock_get_date_range, mock_context_async
    ):
        """An API failure is reported as an error, not as an absence of Savings Plans."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_ce_client.get_savings_plans_utilization.side_effect = Exception('API Error')

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.handle_aws_error'
        ) as mock_handle_error:
            mock_handle_error.return_value = {'status': 'error', 'message': 'API Error'}

            result = await get_savings_plans_utilization(
                mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
            )

            assert result['status'] == 'error'
            mock_handle_error.assert_called_once()

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_savings_plans_utilization_details_empty_data(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details with empty data - covers lines 447-450."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_context_logger'
        ) as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await get_savings_plans_utilization_details(
                mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', None, None
            )

            assert result['status'] == 'success'
            assert result['data']['savings_plans_utilization_details'] == []
            assert len(result['data']['savings_plans_utilization_details']) == 0
            assert 'No Savings Plans utilization details found' in result['data']['message']
            mock_logger_instance.warning.assert_called_once()

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_savings_plans_utilization_details_malformed_data(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details with malformed data - null and empty nested blocks."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        # Null and empty nested blocks, plus an unparseable percentage.
        malformed_details = [
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-test',
                'Attributes': None,
                'Utilization': None,
                'Savings': {},
            },
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-bad',
                'Utilization': {'UtilizationPercentage': 'invalid'},
            },
        ]

        mock_paginate.return_value = (malformed_details, [], PAGINATION_COMPLETE)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_context_logger'
        ) as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await get_savings_plans_utilization_details(
                mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', None, None
            )

            # Rows are passed through untouched and nothing raises.
            assert result['status'] == 'success'
            assert result['data']['savings_plans_utilization_details'] == malformed_details
            assert len(result['data']['savings_plans_utilization_details']) == 2

            # Malformed rows reach the caller intact; no derived statistic is
            # fabricated from them.
            assert 'average_utilization_percentage' not in result['data']
            assert 'under_utilized_plans' not in result['data']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_items'
    )
    async def test_savings_plans_utilization_details_with_valid_attributes(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details with valid attributes - attributes pass through intact."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        # Attribute keys are capitalized in the API response, and `Attributes`
        # carries considerably more than the three fields the old response
        # summarized, so it is returned verbatim.
        attributes = {
            'AccountId': '123456789012',
            'Region': 'us-east-1',
            'InstanceFamily': 'm5',
            'SavingsPlansType': 'EC2InstanceSavingsPlans',
            'HourlyCommitment': '0.1',
            'PaymentOption': 'No Upfront',
            'Status': 'Active',
        }
        details_data = [
            {
                'SavingsPlanArn': 'arn1',
                'Attributes': attributes,
                'Utilization': {
                    'TotalCommitment': '100.0',
                    'UsedCommitment': '95.0',
                    'UnusedCommitment': '5.0',
                    'UtilizationPercentage': '95.0',
                },
                'Savings': {'NetSavings': '10.0', 'OnDemandCostEquivalent': '110.0'},
                'AmortizedCommitment': {'TotalAmortizedCommitment': '100.0'},
            }
        ]

        mock_paginate.return_value = (details_data, [], PAGINATION_COMPLETE)

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_context_logger'
        ) as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger_instance.info = AsyncMock()
            mock_logger_instance.warning = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await get_savings_plans_utilization_details(
                mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', None, None
            )

            assert result['status'] == 'success'
            detail = result['data']['savings_plans_utilization_details'][0]

            # Every attribute survives, including the account that owns the plan.
            assert detail['Attributes'] == attributes
            assert detail['Attributes']['AccountId'] == '123456789012'

            # The figures are reported once, on the row, in the shape and
            # precision the API sent them.
            assert detail['Utilization']['UtilizationPercentage'] == '95.0'
            assert len(result['data']['savings_plans_utilization_details']) == 1
            assert 'average_utilization_percentage' not in result['data']
            assert 'total_savings_plans' not in result['data']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    async def test_savings_plans_utilization_total_absent(
        self, mock_get_date_range, mock_context_async
    ):
        """A response carrying rows but no Total omits the key rather than fabricating zeros.

        Reporting an absent total as 0.0 would let it be summarized as a real
        figure, which is worse than its absence being visible.
        """
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {
                    'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                    'Utilization': {'TotalCommitment': '100.0', 'UtilizationPercentage': '95.0'},
                }
            ]
        }

        result = await get_savings_plans_utilization(
            mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', 'DAILY', None
        )

        assert result['status'] == 'success'
        assert 'total' not in result['data']
        assert 'message' not in result['data']
        assert len(result['data']['savings_plans_utilizations']) == 1


# (function, boto3 method, result key, response key) for the two paginated operations.
SP_PAGED_OPERATIONS = [
    (
        get_savings_plans_coverage,
        'get_savings_plans_coverage',
        'SavingsPlansCoverages',
        'savings_plans_coverages',
    ),
    (
        get_savings_plans_utilization_details,
        'get_savings_plans_utilization_details',
        'SavingsPlansUtilizationDetails',
        'savings_plans_utilization_details',
    ),
]


async def _call_paged(function, client, ctx, max_items=None, next_token=None, sort_by=None):
    if function is get_savings_plans_coverage:
        return await function(
            ctx,
            client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,
            None,
            None,
            max_items,
            next_token,
            sort_by,
        )
    return await function(
        ctx, client, '2023-01-01', '2023-01-31', None, max_items, next_token, sort_by
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('function,method,result_key,response_key', SP_PAGED_OPERATIONS)
class TestSpPerformancePagination:
    """The real pagination helper drives coverage and utilization details."""

    async def test_no_max_items_fetches_every_page_with_one_call_per_page(
        self, mock_context, function, method, result_key, response_key
    ):
        """Every page is fetched at MaxResults=10000, with exactly one call per page."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            {result_key: [{'n': 1}], 'NextToken': 't1'},
            {result_key: [{'n': 2}]},
        ]

        result = await _call_paged(function, client, mock_context)

        data = result['data']
        assert result['status'] == 'success'
        assert data[response_key] == [{'n': 1}, {'n': 2}]
        assert 'complete_dataset' not in data
        assert data['pagination']['items_returned'] == 2
        calls = getattr(client, method).call_args_list
        # Exactly the two pages: the old code made a third call for Total.
        assert len(calls) == 2
        assert calls[0].kwargs['MaxResults'] == 10000
        assert calls[1].kwargs['NextToken'] == 't1'

    async def test_max_items_stops_and_returns_the_token(
        self, mock_context, function, method, result_key, response_key
    ):
        """max_items sizes the page and the service token is returned for continuation."""
        client = MagicMock()
        getattr(client, method).return_value = {
            result_key: [{'n': 1}, {'n': 2}],
            'NextToken': 'more',
        }

        result = await _call_paged(function, client, mock_context, max_items=2)

        data = result['data']
        assert data['complete_dataset'] is False
        assert 'Partial data' in data['warning']
        assert data['pagination']['next_token'] == 'more'
        getattr(client, method).assert_called_once()
        assert getattr(client, method).call_args.kwargs['MaxResults'] == 2

    async def test_continuation_sends_caller_token_and_identical_params(
        self, mock_context, function, method, result_key, response_key
    ):
        """A continuation repeats the first call's parameters plus the caller's token."""
        client = MagicMock()
        getattr(client, method).return_value = {result_key: [{'n': 1}]}

        await _call_paged(function, client, mock_context)
        first = dict(getattr(client, method).call_args.kwargs)
        await _call_paged(function, client, mock_context, next_token='caller-token')
        second = dict(getattr(client, method).call_args.kwargs)

        assert second.pop('NextToken') == 'caller-token'
        assert second == first

    async def test_sort_by_is_sent_on_every_page(
        self, mock_context, function, method, result_key, response_key
    ):
        """The API sorts across pages only if every page request carries the same SortBy."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            {result_key: [{'n': 1}], 'NextToken': 't1'},
            {result_key: [{'n': 2}]},
        ]
        key = 'CoveragePercentage' if function is get_savings_plans_coverage else 'NetSavings'
        sort = {'Key': key, 'SortOrder': 'DESCENDING'}

        await _call_paged(function, client, mock_context, sort_by=json.dumps(sort))

        calls = getattr(client, method).call_args_list
        assert len(calls) == 2
        assert all(call.kwargs['SortBy'] == sort for call in calls)


API_DETAILS_TOTAL = {
    'Utilization': {
        'TotalCommitment': '100.0',
        'UsedCommitment': '30.47',
        'UnusedCommitment': '69.53',
        'UtilizationPercentage': '30.47',
    }
}
API_DETAILS_PERIOD = {'Start': '2026-09-01', 'End': '2026-10-01'}


@pytest.mark.asyncio
class TestSpPerformanceEnvelope:
    """Envelope fields come from the API response; request values are labelled as such."""

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_details_single_complete_page_returns_api_total_and_time_period(
        self, mock_dates, mock_context
    ):
        """One complete page: its Total covers every plan, so total and time_period are the API's."""
        mock_dates.return_value = ('2026-09-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization_details.return_value = {
            'SavingsPlansUtilizationDetails': [{'n': 1}, {'n': 2}],
            'Total': API_DETAILS_TOTAL,
            'TimePeriod': API_DETAILS_PERIOD,
        }

        result = await get_savings_plans_utilization_details(
            mock_context, client, '2026-09-01', '2026-10-01', None
        )

        data = result['data']
        assert data['total'] == API_DETAILS_TOTAL
        assert data['time_period'] == API_DETAILS_PERIOD
        assert data['requested_time_period'] == {'start': '2026-09-01', 'end': '2026-10-01'}

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_details_across_pages_omits_the_page_scoped_total(
        self, mock_dates, mock_context
    ):
        """Each page's Total covers only that page's plans, so a multi-page result has no total.

        Observed live with MaxResults=3: each page's Total.TotalCommitment was the sum of
        that page's rows, and the page totals added up to the single-page query's Total.
        """
        mock_dates.return_value = ('2026-09-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization_details.side_effect = [
            {
                'SavingsPlansUtilizationDetails': [{'n': 1}],
                'Total': {'page': 1},
                'TimePeriod': API_DETAILS_PERIOD,
                'NextToken': 'tok',
            },
            {
                'SavingsPlansUtilizationDetails': [{'n': 2}],
                'Total': {'page': 2},
                'TimePeriod': API_DETAILS_PERIOD,
            },
        ]

        result = await get_savings_plans_utilization_details(
            mock_context, client, '2026-09-01', '2026-10-01', None
        )

        data = result['data']
        assert client.get_savings_plans_utilization_details.call_count == 2
        assert data['savings_plans_utilization_details'] == [{'n': 1}, {'n': 2}]
        assert 'total' not in data
        assert data['time_period'] == API_DETAILS_PERIOD

    @pytest.mark.parametrize(
        'max_items,next_token,response',
        [
            (1, None, {'NextToken': 'more'}),
            (None, 'caller-token', {}),
        ],
        ids=['partial', 'continuation'],
    )
    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_details_partial_or_continued_page_omits_total(
        self, mock_dates, mock_context, max_items, next_token, response
    ):
        """A partial first page, or a later page reached by next_token, has a page-scoped Total."""
        mock_dates.return_value = ('2026-09-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization_details.return_value = {
            'SavingsPlansUtilizationDetails': [{'n': 1}],
            'Total': {'page': 1},
            'TimePeriod': API_DETAILS_PERIOD,
            **response,
        }

        result = await get_savings_plans_utilization_details(
            mock_context, client, '2026-09-01', '2026-10-01', None, max_items, next_token
        )

        assert 'total' not in result['data']
        assert result['data']['time_period'] == API_DETAILS_PERIOD

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_details_omits_period_and_total_the_api_did_not_send(
        self, mock_dates, mock_context
    ):
        """No API TimePeriod or Total means neither key, never the request echo in their place."""
        mock_dates.return_value = ('2026-09-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization_details.return_value = {
            'SavingsPlansUtilizationDetails': [{'n': 1}]
        }

        result = await get_savings_plans_utilization_details(
            mock_context, client, '2026-09-01', '2026-10-01', None
        )

        data = result['data']
        assert 'time_period' not in data
        assert 'total' not in data
        assert data['requested_time_period'] == {'start': '2026-09-01', 'end': '2026-10-01'}

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_details_empty_result_echoes_request_as_requested_time_period(
        self, mock_dates, mock_context
    ):
        """The no-plans response labels the request window as requested, not as the API's."""
        mock_dates.return_value = ('2026-09-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization_details.return_value = {
            'SavingsPlansUtilizationDetails': []
        }

        result = await get_savings_plans_utilization_details(
            mock_context, client, '2026-09-01', '2026-10-01', None
        )

        data = result['data']
        assert data['savings_plans_utilization_details'] == []
        assert data['requested_time_period'] == {'start': '2026-09-01', 'end': '2026-10-01'}
        assert 'time_period' not in data
        assert 'No Savings Plans utilization details found' in data['message']

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_utilization_request_echo_is_requested_time_period(
        self, mock_dates, mock_context
    ):
        """MONTHLY entries are labelled by calendar month; the request window is echoed as such."""
        mock_dates.return_value = ('2026-08-17', '2026-10-01')
        client = MagicMock()
        entries = [
            {'TimePeriod': {'Start': '2026-08-01', 'End': '2026-09-01'}},
            {'TimePeriod': {'Start': '2026-09-01', 'End': '2026-10-01'}},
        ]
        client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': entries,
            'Total': API_DETAILS_TOTAL,
        }

        result = await get_savings_plans_utilization(
            mock_context, client, '2026-08-17', '2026-10-01', 'MONTHLY', None
        )

        data = result['data']
        assert 'time_period' not in data
        assert data['requested_time_period'] == {'start': '2026-08-17', 'end': '2026-10-01'}
        # The calendar-month labels reach the caller untouched.
        assert data['savings_plans_utilizations'] == entries
        assert (
            'first entry, labelled 2026-08-01 to 2026-09-01, covers only 2026-08-17'
            in (data['period_note'])
        )

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_utilization_flags_a_snapped_end(self, mock_dates, mock_context):
        """A mid-month end is labelled with the whole month too; period_note says so."""
        mock_dates.return_value = ('2026-08-01', '2026-09-10')
        client = MagicMock()
        client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {'TimePeriod': {'Start': '2026-08-01', 'End': '2026-09-01'}},
                {'TimePeriod': {'Start': '2026-09-01', 'End': '2026-10-01'}},
            ],
            'Total': API_DETAILS_TOTAL,
        }

        result = await get_savings_plans_utilization(
            mock_context, client, '2026-08-01', '2026-09-10', 'MONTHLY', None
        )

        note = result['data']['period_note']
        assert (
            'last entry, labelled 2026-09-01 to 2026-10-01, covers only the days before 2026-09-10'
            in (note)
        )
        assert 'first entry' not in note

    @patch(f'{SP_TOOLS}.get_date_range')
    async def test_utilization_matching_request_has_no_note(self, mock_dates, mock_context):
        """Whole-month requests need no note."""
        mock_dates.return_value = ('2026-08-01', '2026-10-01')
        client = MagicMock()
        client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {'TimePeriod': {'Start': '2026-08-01', 'End': '2026-09-01'}},
                {'TimePeriod': {'Start': '2026-09-01', 'End': '2026-10-01'}},
            ],
            'Total': API_DETAILS_TOTAL,
        }

        result = await get_savings_plans_utilization(
            mock_context, client, '2026-08-01', '2026-10-01', 'MONTHLY', None
        )

        assert 'period_note' not in result['data']

    @pytest.mark.parametrize('pages', [1, 2])
    async def test_coverage_makes_one_call_per_page_and_reports_no_total(
        self, mock_context, pages
    ):
        """Coverage costs one GetSavingsPlansCoverage call per page and invents no total."""
        client = MagicMock()
        responses = [
            {'SavingsPlansCoverages': [{'n': i}], 'NextToken': f't{i}'} for i in range(pages)
        ]
        del responses[-1]['NextToken']
        client.get_savings_plans_coverage.side_effect = responses

        result = await _call_tool(client, mock_context, 'get_savings_plans_coverage')

        assert client.get_savings_plans_coverage.call_count == pages
        assert 'total' not in result['data']
        assert len(result['data']['savings_plans_coverages']) == pages

    async def test_grouped_coverage_omits_granularity(self, mock_context):
        """With group_by, Granularity is neither sent nor reported."""
        client = MagicMock()
        client.get_savings_plans_coverage.return_value = {'SavingsPlansCoverages': []}

        result = await _call_tool(
            client,
            mock_context,
            'get_savings_plans_coverage',
            granularity='MONTHLY',
            group_by='[{"Type": "DIMENSION", "Key": "SERVICE"}]',
        )

        assert 'Granularity' not in client.get_savings_plans_coverage.call_args.kwargs
        assert 'granularity' not in result['data']

    async def test_ungrouped_coverage_reports_granularity_it_sent(self, mock_context):
        """Without group_by, the reported granularity is the one sent."""
        client = MagicMock()
        client.get_savings_plans_coverage.return_value = {'SavingsPlansCoverages': []}

        result = await _call_tool(
            client, mock_context, 'get_savings_plans_coverage', granularity='MONTHLY'
        )

        assert client.get_savings_plans_coverage.call_args.kwargs['Granularity'] == 'MONTHLY'
        assert result['data']['granularity'] == 'MONTHLY'

    async def test_linked_account_filter_passes_through_without_group_by(self, mock_context):
        """The documented per-account path: a LINKED_ACCOUNT filter, sent as-is."""
        client = MagicMock()
        client.get_savings_plans_coverage.return_value = {'SavingsPlansCoverages': []}
        account_filter = '{"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": ["111122223333"]}}'

        await _call_tool(client, mock_context, 'get_savings_plans_coverage', filter=account_filter)

        kwargs = client.get_savings_plans_coverage.call_args.kwargs
        assert kwargs['Filter'] == {
            'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': ['111122223333']}
        }
        assert 'GroupBy' not in kwargs


CE_MODEL = botocore.session.get_session().get_service_model('ce')


def _output_members(operation: str) -> set:
    """Member names of a Cost Explorer operation's output shape."""
    shape: Any = CE_MODEL.operation_model(operation).output_shape
    return set(shape.members)


@pytest.mark.parametrize(
    'operation,method',
    [
        ('GetSavingsPlansCoverage', 'get_savings_plans_coverage'),
        ('GetSavingsPlansUtilization', 'get_savings_plans_utilization'),
        ('GetSavingsPlansUtilizationDetails', 'get_savings_plans_utilization_details'),
    ],
)
def test_mock_ce_responses_only_use_botocore_output_members(mock_ce_client, operation, method):
    """Fixture responses carry only members the API can return (coverage has no Total)."""
    members = _output_members(operation)
    response = getattr(mock_ce_client, method).return_value

    assert set(response) <= members, f'{method} fixture invents {set(response) - members}'


def test_ce_sp_response_shapes_pin():
    """Pin the output shapes the envelope relies on."""
    assert 'Total' not in _output_members('GetSavingsPlansCoverage')
    assert 'TimePeriod' not in _output_members('GetSavingsPlansUtilization')
    assert {'Total', 'TimePeriod'} <= _output_members('GetSavingsPlansUtilizationDetails')


@pytest.mark.asyncio
class TestSpPerformanceDescription:
    """The tool description tells the caller what the API accepts and what it returns."""

    @staticmethod
    async def _description() -> str:
        tool = await sp_performance_server.get_tool('sp-performance')
        assert tool is not None and tool.description
        return tool.description

    async def test_states_the_data_lag_and_data_unavailable_causes(self):
        """The lag is 2-3 days (excluding today is not enough), and unmatched filters fail too."""
        description = ' '.join((await self._description()).split())
        assert 'lags roughly one day' not in description
        assert 'then the window resolves' not in description
        assert 'most recent 2-3 days (counting today) is not processed yet' in description
        assert 'excluding only today is not enough' in description
        assert 'succeeds but silently leaves them out' in description
        assert 'the last DAILY entry can end before end_date' in description
        assert (
            'A start_date at least 3 days before today is usually past that delay' in description
        )
        assert 'an unknown SAVINGS_PLANS_TYPE, for example, returns this error' in description
        assert 'not zero utilization or coverage' in description

    async def test_end_date_doc_states_the_data_lag(self):
        """The end_date arg doc no longer says excluding today is enough."""
        tool = await sp_performance_server.get_tool('sp-performance')
        assert tool is not None
        end_date_doc = tool.parameters['properties']['end_date'].get('description', '')
        assert 'lags ~1 day' not in end_date_doc
        assert 'last 2-3 days (counting today) is not processed yet' in end_date_doc

    async def test_lists_utilization_details_filter_dimensions(self):
        """Every GetSavingsPlansUtilizationDetails filter dimension is named."""
        description = await self._description()
        for dimension in (
            'LINKED_ACCOUNT',
            'SAVINGS_PLAN_ARN',
            'REGION',
            'PAYMENT_OPTION',
            'INSTANCE_TYPE_FAMILY',
        ):
            assert dimension in description

    async def test_explains_requested_time_period_versus_api_period(self):
        """The request echo is named and the caller is pointed at the API's periods."""
        description = await self._description()
        assert 'requested_time_period' in description
        flat = ' '.join(description.split())
        assert 'figures cover only the requested days' in flat
        assert 'holding only the days before 2026-09-10' in flat
        assert '`period_note` says when this happened' in flat
        assert "the current month's entry ends at the first day without data" in flat
        assert 'from the requested start to the requested end' not in flat
        assert 'they are not snapped' in description
        assert 'covers only the Savings Plans on its own page' in description
        assert 'Coverage has no `total`' in description


@pytest.mark.asyncio
class TestSpPerformanceDimensionsAndSort:
    """Coverage names INSTANCE_TYPE_FAMILY, utilization filters are listed, sort_by passes through."""

    @staticmethod
    async def _tool():
        tool = await sp_performance_server.get_tool('sp-performance')
        assert isinstance(tool, FunctionTool) and tool.description
        return tool

    async def test_no_instance_family_anywhere(self):
        """INSTANCE_FAMILY is not a Cost Explorer dimension; only INSTANCE_TYPE_FAMILY is."""
        tool = await self._tool()
        description = tool.description or ''
        params = tool.parameters['properties']
        for text in (
            description,
            params['group_by']['description'],
            params['filter']['description'],
            params['sort_by']['description'],
        ):
            assert re.search(r'\bINSTANCE_FAMILY\b', text) is None

    async def test_coverage_names_instance_type_family(self):
        """The coverage group_by and filter lists, and their arg docs, name INSTANCE_TYPE_FAMILY."""
        tool = await self._tool()
        flat = ' '.join((tool.description or '').split())
        assert 'group_by accepts ONLY INSTANCE_TYPE_FAMILY, REGION, or SERVICE' in flat
        assert 'filter accepts LINKED_ACCOUNT, REGION, SERVICE, INSTANCE_TYPE_FAMILY' in flat
        assert 'coverage are SERVICE, REGION, or INSTANCE_TYPE_FAMILY' in flat
        assert 'SAVINGS_PLANS_TYPE is not a coverage dimension' in flat
        params = tool.parameters['properties']
        assert 'SERVICE, REGION, or INSTANCE_TYPE_FAMILY' in params['group_by']['description']
        assert 'SERVICE, INSTANCE_TYPE_FAMILY' in params['filter']['description']

    async def test_and_is_the_only_compound_expression_named(self):
        """Or is not a supported SP filter expression, so no text implies it works."""
        tool = await self._tool()
        assert 'And/Or' not in (tool.description or '')
        assert 'And/Or' not in tool.parameters['properties']['filter']['description']

    async def test_lists_utilization_filters_and_grammar(self):
        """Utilization filter dimensions are listed, with the expressions it rejects."""
        flat = ' '.join(((await self._tool()).description or '').split())
        section = flat.split('UTILIZATION filters (get_savings_plans_utilization):')[1]
        section = section.split('UTILIZATION DETAILS')[0]
        for dimension in (
            'LINKED_ACCOUNT',
            'SAVINGS_PLAN_ARN',
            'SAVINGS_PLANS_TYPE',
            'REGION',
            'PAYMENT_OPTION',
            'INSTANCE_TYPE_FAMILY',
        ):
            assert dimension in section
        assert 'Only Dimensions, And and Not are allowed' in section
        assert 'Or, Tags or CostCategories expression returns a ValidationException' in section

    async def test_lists_utilization_details_plan_type_and_end_date_filters(self):
        """Details also filters on SAVINGS_PLANS_TYPE and the plan end-date bounds."""
        flat = ' '.join(((await self._tool()).description or '').split())
        section = flat.split(
            'UTILIZATION DETAILS filters (get_savings_plans_utilization_details):'
        )[1]
        section = section.split('- The filter is')[0]
        for dimension in (
            'LINKED_ACCOUNT',
            'SAVINGS_PLAN_ARN',
            'SAVINGS_PLANS_TYPE',
            'REGION',
            'PAYMENT_OPTION',
            'INSTANCE_TYPE_FAMILY',
            'AGREEMENT_END_DATE_TIME_AFTER',
            'AGREEMENT_END_DATE_TIME_BEFORE',
        ):
            assert dimension in section
        assert "one YYYY-MM-DD value each, compared with each plan's end date" in section
        assert (
            'SAVINGS_PLANS_TYPE (get_savings_plans_utilization and '
            'get_savings_plans_utilization_details; not accepted by coverage)'
        ) in flat

    async def test_says_sort_happens_before_max_items(self):
        """sort_by + max_items=N is the top N by the key, not N items sorted afterwards."""
        tool = await self._tool()
        flat = ' '.join((tool.description or '').split())
        assert (
            'Order of operations: the API sorts every matching item by the key first, then '
            'pages; max_items=N keeps the first N of that sorted order.'
        ) in flat
        assert 'not N arbitrary items sorted afterwards' in flat
        params = tool.parameters['properties']
        sort_doc = ' '.join(params['sort_by']['description'].split())
        max_doc = ' '.join(params['max_items']['description'].split())
        assert 'Applied before max_items, so sort_by + max_items=N returns the top N.' in sort_doc
        assert (
            'With sort_by, these are the first N items in the requested SortOrder (the top N)'
            in max_doc
        )

    async def test_coverage_dimension_sort_keys_need_group_by(self):
        """Sorting coverage by a dimension key needs that dimension in group_by."""
        flat = ' '.join(((await self._tool()).description or '').split())
        assert (
            'Sorting coverage by InstanceFamily, Region or Service needs that dimension in '
            'group_by (INSTANCE_TYPE_FAMILY, REGION or SERVICE); otherwise the API returns a '
            'ValidationException'
        ) in flat

    async def test_gives_value_spellings_and_the_wrong_spelling_error(self):
        """PAYMENT_OPTION and SAVINGS_PLANS_TYPE values, and what another spelling returns."""
        flat = ' '.join(((await self._tool()).description or '').split())
        assert 'PAYMENT_OPTION: "No Upfront", "Partial Upfront", "All Upfront"' in flat
        assert (
            '"ComputeSavingsPlans", "EC2InstanceSavingsPlans", '
            '"SageMakerSavingsPlans", "DatabaseSavingsPlans"'
        ) in flat
        assert (
            'returns a DataUnavailableException, which the service sends without a message, '
            'not a ValidationException'
        ) in flat
        assert 'check these spellings before changing the window' in flat

    async def test_documents_sort_keys_per_operation(self):
        """Both sortable operations list their keys; utilization says it ignores sort_by."""
        tool = await self._tool()
        flat = ' '.join((tool.description or '').split())
        assert (
            'Coverage keys: CoveragePercentage, SpendCoveredBySavingsPlan (singular, unlike the '
            'metric), OnDemandCost, TotalCost, InstanceFamily, Region, Service'
        ) in flat
        assert (
            'Utilization details keys: UtilizationPercentage, TotalCommitment, UsedCommitment, '
            'UnusedCommitment, NetSavings, AmortizedRecurringCommitment, AmortizedUpfrontCommitment'
        ) in flat
        assert 'get_savings_plans_utilization ignores sort_by' in flat
        sort_by = tool.parameters['properties']['sort_by']
        assert sort_by.get('default') is None
        assert 'sort_by' not in tool.parameters.get('required', [])
        assert 'see SORTING' in sort_by['description']
        assert 'ignored by get_savings_plans_utilization' in sort_by['description']
        assert 'sort by InstanceFamily, group by INSTANCE_TYPE_FAMILY' in flat

    @pytest.mark.parametrize(
        'operation, api, key',
        [
            ('get_savings_plans_coverage', 'get_savings_plans_coverage', 'CoveragePercentage'),
            (
                'get_savings_plans_utilization_details',
                'get_savings_plans_utilization_details',
                'UtilizationPercentage',
            ),
        ],
    )
    async def test_sort_by_is_sent_as_sort_by(
        self, operation, api, key, mock_context, mock_ce_client
    ):
        """sort_by reaches the API unchanged as SortBy."""
        sort = {'Key': key, 'SortOrder': 'ASCENDING'}
        result = await _call_tool(
            mock_ce_client, mock_context, operation, sort_by=json.dumps(sort)
        )

        assert result['status'] == 'success'
        assert getattr(mock_ce_client, api).call_args.kwargs['SortBy'] == sort

    @pytest.mark.parametrize(
        'operation, api',
        [
            ('get_savings_plans_coverage', 'get_savings_plans_coverage'),
            ('get_savings_plans_utilization', 'get_savings_plans_utilization'),
            ('get_savings_plans_utilization_details', 'get_savings_plans_utilization_details'),
        ],
    )
    async def test_no_sort_by_sends_no_sort_by(self, operation, api, mock_context, mock_ce_client):
        """Without sort_by the request is unchanged."""
        result = await _call_tool(mock_ce_client, mock_context, operation)

        assert result['status'] == 'success'
        assert 'SortBy' not in getattr(mock_ce_client, api).call_args.kwargs

    async def test_utilization_ignores_sort_by(self, mock_context, mock_ce_client):
        """Utilization keeps its periods in date order, so sort_by is not sent."""
        result = await _call_tool(
            mock_ce_client,
            mock_context,
            'get_savings_plans_utilization',
            sort_by='{"Key": "UtilizationPercentage", "SortOrder": "ASCENDING"}',
        )

        assert result['status'] == 'success'
        assert 'SortBy' not in mock_ce_client.get_savings_plans_utilization.call_args.kwargs

    async def test_malformed_sort_by_is_rejected_before_the_api(
        self, mock_context, mock_ce_client
    ):
        """A sort_by that is not JSON returns an error and makes no call."""
        result = await _call_tool(
            mock_ce_client, mock_context, 'get_savings_plans_coverage', sort_by='{not json'
        )

        assert result['status'] == 'error'
        assert 'sort_by' in result['message']
        mock_ce_client.get_savings_plans_coverage.assert_not_called()
