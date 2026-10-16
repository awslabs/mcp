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

import pytest
from awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools import (
    get_savings_plans_coverage,
    get_savings_plans_utilization,
    get_savings_plans_utilization_details,
    sp_performance_server,
)
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def sp_performance(ctx, operation, **kwargs):
    """Mock implementation of sp_performance for testing."""
    # Simple mock implementation that returns predefined responses
    await ctx.info(f'Processing {operation} operation')

    if operation == 'get_savings_plans_coverage':
        return {
            'status': 'success',
            'data': {
                'savings_plans_coverages': [],
                'total': {
                    'SpendCoveredBySavingsPlans': '75.0',
                    'OnDemandCost': '100.0',
                    'TotalCost': '400.0',
                    'CoveragePercentage': '75.0',
                },
            },
        }
    elif operation == 'get_savings_plans_utilization':
        return {
            'status': 'success',
            'data': {
                'savings_plans_utilizations': [],
                'total': {
                    'total_commitment': '100.0',
                    'used_commitment': '95.0',
                    'unused_commitment': '5.0',
                    'utilization_percentage': '95.0',
                },
            },
        }
    elif operation == 'get_savings_plans_utilization_details':
        return {'status': 'success', 'data': {'savings_plans_utilization_details': []}}
    else:
        return {'status': 'error', 'message': f'Unsupported operation: {operation}'}


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
        'Total': {
            'SpendCoveredBySavingsPlans': '75.0',
            'OnDemandCost': '100.0',
            'TotalCost': '400.0',
            'CoveragePercentage': '75.0',
        },
        'NextToken': None,
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
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
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
            {'NextToken': None},
        )

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,  # filter_expr
            None,  # max_results
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_kwargs = mock_paginate_response.call_args[1]

        assert call_kwargs['operation_name'] == 'GetSavingsPlansUtilizationDetails'
        assert call_kwargs['result_key'] == 'SavingsPlansUtilizationDetails'

        request_params = call_kwargs['request_params']
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['MaxResults'] == 20  # Default value

        assert result['status'] == 'success'
        assert 'savings_plans_utilization_details' in result['data']
        assert len(result['data']['savings_plans_utilization_details']) == 2
        assert result['data']['total_count'] == 2

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
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
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
            {'NextToken': None},
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
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
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
        mock_paginate_response.return_value = (rows, {'NextToken': None})

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context, mock_ce_client, '2023-01-01', '2023-01-31', None, None
        )

        # Assert
        assert result['status'] == 'success'
        assert result['data']['savings_plans_utilization_details'] == rows
        assert result['data']['total_count'] == 4

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    async def test_get_savings_plans_utilization_details_with_filter(
        self,
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
            {'NextToken': None},
        )

        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}
        mock_parse_json.return_value = mock_filter

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'filter_json',  # filter_expr
            None,  # max_results
        )

        # Assert
        mock_parse_json.assert_called_once_with('filter_json', 'filter')

        request_params = mock_paginate_response.call_args[1]['request_params']
        assert 'Filter' in request_params
        assert request_params['Filter'] == mock_filter

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_get_savings_plans_utilization_details_with_max_results(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization_details with max_results parameter."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization_details.return_value[
                'SavingsPlansUtilizationDetails'
            ],
            {'NextToken': None},
        )

        # Execute
        result = await get_savings_plans_utilization_details(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            None,  # filter_expr
            50,  # max_results
        )

        # Assert
        request_params = mock_paginate_response.call_args[1]['request_params']
        assert 'MaxResults' in request_params
        assert request_params['MaxResults'] == 50

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
            None,  # max_results
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
        assert result['data']['time_period'] == {'start': '2023-01-01', 'end': '2023-01-31'}

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
    async def test_get_savings_plans_utilization_with_filter(
        self,
        mock_parse_json,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_savings_plans_utilization with filter parameter."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}
        mock_parse_json.return_value = mock_filter

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
        mock_parse_json.assert_called_once_with('filter_json', 'filter')

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
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_get_savings_plans_coverage_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_coverage with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_coverage.return_value['SavingsPlansCoverages'],
            {'NextToken': None},
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
        call_kwargs = mock_paginate_response.call_args[1]

        assert call_kwargs['operation_name'] == 'GetSavingsPlansCoverage'
        assert call_kwargs['result_key'] == 'SavingsPlansCoverages'

        request_params = call_kwargs['request_params']
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'
        assert request_params['Metrics'] == ['SpendCoveredBySavingsPlans']  # Default metric

        assert result['status'] == 'success'
        assert 'savings_plans_coverages' in result['data']
        assert len(result['data']['savings_plans_coverages']) == 1

        # Check total coverage
        assert 'total' in result['data']
        assert result['data']['total']['SpendCoveredBySavingsPlans'] == '75.0'
        assert result['data']['total']['CoveragePercentage'] == '75.0'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    async def test_get_savings_plans_coverage_with_options(
        self,
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
            {'NextToken': None},
        )

        mock_metrics = ['SpendCoveredBySavingsPlans']
        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        mock_filter = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        mock_parse_json.side_effect = [mock_metrics, mock_group_by, mock_filter]

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
        mock_parse_json.assert_any_call('filter_json', 'filter')

        request_params = mock_paginate_response.call_args[1]['request_params']
        assert request_params['Metrics'] == mock_metrics
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        # Granularity and GroupBy are mutually exclusive for GetSavingsPlansCoverage:
        # when GroupBy is set, Granularity must not be sent.
        assert 'Granularity' not in request_params

        assert result['status'] == 'success'

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
    """Tests for sp_performance function."""

    async def test_sp_performance_coverage(self, mock_context):
        """Test sp_performance with get_savings_plans_coverage operation."""
        # Execute
        result = await sp_performance(
            mock_context,
            operation='get_savings_plans_coverage',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'success'
        assert 'savings_plans_coverages' in result['data']
        assert 'total' in result['data']
        data = result['data']
        assert isinstance(data, dict)
        total_data = data['total']
        assert isinstance(total_data, dict) and 'SpendCoveredBySavingsPlans' in total_data

    async def test_sp_performance_utilization(self, mock_context):
        """Test sp_performance with get_savings_plans_utilization operation."""
        # Execute
        result = await sp_performance(
            mock_context,
            operation='get_savings_plans_utilization',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'success'
        assert 'savings_plans_utilizations' in result['data']
        assert 'total' in result['data']
        data = result['data']
        assert isinstance(data, dict)
        total_data = data['total']
        assert isinstance(total_data, dict) and 'utilization_percentage' in total_data

    async def test_sp_performance_utilization_details(self, mock_context):
        """Test sp_performance with get_savings_plans_utilization_details operation."""
        # Execute
        result = await sp_performance(
            mock_context,
            operation='get_savings_plans_utilization_details',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'success'
        assert 'savings_plans_utilization_details' in result['data']

    async def test_sp_performance_unsupported_operation(self, mock_context):
        """Test sp_performance with unsupported operation."""
        # Execute
        result = await sp_performance(
            mock_context,
            operation='unsupported_operation',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']


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

    async def test_sp_performance_unsupported_operation(self, mock_context_async):
        """Test sp_performance with unsupported operation - covers error path."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.create_aws_client'
        ):
            result = await sp_performance(mock_context_async, operation='unsupported_operation')

            assert result['status'] == 'error'
            assert 'Unsupported operation' in result['message']

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
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_details_empty_data(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details with empty data - covers lines 447-450."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate.return_value = ([], {'NextToken': None})

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
            assert result['data']['total_count'] == 0
            assert 'No Savings Plans utilization details found' in result['data']['message']
            mock_logger_instance.warning.assert_called_once()

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
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

        mock_paginate.return_value = (malformed_details, {'NextToken': None})

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
            assert result['data']['total_count'] == 2

            # Malformed rows reach the caller intact; no derived statistic is
            # fabricated from them.
            assert 'average_utilization_percentage' not in result['data']
            assert 'under_utilized_plans' not in result['data']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
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

        mock_paginate.return_value = (details_data, {'NextToken': None})

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
            assert result['data']['total_count'] == 1
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
