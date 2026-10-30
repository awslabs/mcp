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

"""Unit tests for the cost_comparison_tools module.

These tests verify the functionality of cost comparison tools, including:
- Comparing costs between different time periods with variance analysis
- Generating cost breakdowns by service, region, and account dimensions
- Calculating cost trends and percentage changes over time
- Handling multi-dimensional cost analysis and filtering
- Error handling for invalid date ranges and comparison parameters
"""

import boto3
import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools import (
    COMPARISON_METRICS,
    DRIVER_METRICS,
    GET_COST_AND_USAGE_COMPARISONS,
    GET_COST_COMPARISON_DRIVERS,
    MAX_FILTER_DEPTH,
    _months_before,
    _utc_today,
    cost_comparison,
    cost_comparison_server,
    get_cost_and_usage_comparisons,
    get_cost_comparison_drivers,
    validate_comparison_filter,
    validate_comparison_request,
)
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    MODIFY_REQUEST,
    add_retry_guidance,
)
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from datetime import date
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


MODULE = 'awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools'
OPERATIONS = ['getCostAndUsageComparisons', 'getCostComparisonDrivers']
CE_METHOD = {
    'getCostAndUsageComparisons': 'get_cost_and_usage_comparisons',
    'getCostComparisonDrivers': 'get_cost_comparison_drivers',
}


def month_start(months_back: int) -> str:
    """First day of the month `months_back` months before the current UTC month."""
    return _months_before(_utc_today().replace(day=1), months_back).isoformat()


def month(months_back: int):
    """(start, end) of one whole calendar month, `months_back` months before this one."""
    return month_start(months_back), month_start(months_back - 1)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    context.debug = AsyncMock()
    return context


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_cost_and_usage_comparisons
    mock_client.get_cost_and_usage_comparisons.return_value = {
        'CostAndUsageComparisons': [
            {
                'CostAndUsageSelector': {'Key': 'SERVICE', 'Values': ['Amazon EC2']},
                'Metrics': {
                    'BlendedCost': {
                        'BaselineTimePeriodAmount': '500.0',
                        'ComparisonTimePeriodAmount': '600.0',
                        'Difference': '100.0',
                        'Unit': 'USD',
                    }
                },
            },
            {
                'CostAndUsageSelector': {'Key': 'SERVICE', 'Values': ['Amazon S3']},
                'Metrics': {
                    'BlendedCost': {
                        'BaselineTimePeriodAmount': '100.0',
                        'ComparisonTimePeriodAmount': '80.0',
                        'Difference': '-20.0',
                        'Unit': 'USD',
                    }
                },
            },
        ],
        'TotalCostAndUsage': {
            'BlendedCost': {
                'BaselineTimePeriodAmount': '600.0',
                'ComparisonTimePeriodAmount': '680.0',
                'Difference': '80.0',
                'Unit': 'USD',
            }
        },
        'NextPageToken': None,
    }

    # Set up mock response for get_cost_comparison_drivers
    mock_client.get_cost_comparison_drivers.return_value = {
        'CostComparisonDrivers': [
            {
                'CostSelector': {'Key': 'SERVICE', 'Values': ['Amazon EC2']},
                'Metrics': {
                    'BlendedCost': {
                        'BaselineTimePeriodAmount': '500.0',
                        'ComparisonTimePeriodAmount': '600.0',
                        'Difference': '100.0',
                        'Unit': 'USD',
                    }
                },
                'CostDrivers': [
                    {
                        'Name': 'BoxUsage:t2.micro',
                        'Type': 'USAGE_TYPE',
                        'Metrics': {
                            'BlendedCost': {
                                'BaselineTimePeriodAmount': '200.0',
                                'ComparisonTimePeriodAmount': '250.0',
                                'Difference': '50.0',
                                'Unit': 'USD',
                            }
                        },
                    },
                    {
                        'Name': 'BoxUsage:t3.medium',
                        'Type': 'USAGE_TYPE',
                        'Metrics': {
                            'BlendedCost': {
                                'BaselineTimePeriodAmount': '300.0',
                                'ComparisonTimePeriodAmount': '350.0',
                                'Difference': '50.0',
                                'Unit': 'USD',
                            }
                        },
                    },
                ],
            }
        ],
        'NextPageToken': None,
    }

    return mock_client


@pytest.mark.asyncio
class TestGetCostAndUsageComparisons:
    """Tests for get_cost_and_usage_comparisons function."""

    async def test_get_cost_and_usage_comparisons_basic(self, mock_context, mock_ce_client):
        """Test get_cost_and_usage_comparisons with basic parameters."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        # Execute
        result = await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]

        assert 'BaselineTimePeriod' in call_kwargs
        assert call_kwargs['BaselineTimePeriod']['Start'] == baseline_start_date
        assert call_kwargs['BaselineTimePeriod']['End'] == baseline_end_date

        assert 'ComparisonTimePeriod' in call_kwargs
        assert call_kwargs['ComparisonTimePeriod']['Start'] == comparison_start_date
        assert call_kwargs['ComparisonTimePeriod']['End'] == comparison_end_date

        assert call_kwargs['MetricForComparison'] == metric_for_comparison
        assert call_kwargs['MaxResults'] == 2000  # largest page without max_items

        assert result['status'] == 'success'
        assert 'cost_and_usage_comparisons' in result['data']
        assert len(result['data']['cost_and_usage_comparisons']) == 2
        assert 'total_cost_and_usage' in result['data']

    async def test_get_cost_and_usage_comparisons_with_group_by(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons with group_by parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        group_by = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'

        # Execute
        await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            group_by,
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'GroupBy' in call_kwargs
        assert isinstance(call_kwargs['GroupBy'], list)
        assert call_kwargs['GroupBy'][0]['Type'] == 'DIMENSION'
        assert call_kwargs['GroupBy'][0]['Key'] == 'SERVICE'

    async def test_get_cost_and_usage_comparisons_with_filter(self, mock_context, mock_ce_client):
        """Test get_cost_and_usage_comparisons with filter parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        filter_expr = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        # Execute
        await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            filter_expr,
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'Filter' in call_kwargs
        assert call_kwargs['Filter']['Dimensions']['Key'] == 'SERVICE'
        assert 'Amazon EC2' in call_kwargs['Filter']['Dimensions']['Values']

    async def test_get_cost_and_usage_comparisons_with_max_items(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons with max_items below the page maximum."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        max_items = 5

        # Execute
        await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            max_items,
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert call_kwargs['MaxResults'] == 5

    async def test_get_cost_and_usage_comparisons_with_billing_view_arn(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons with billing_view_arn parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        billing_view_arn = 'arn:aws:ce::123456789012:billingview/view-1'

        # Execute
        await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            billing_view_arn,
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'BillingViewArn' in call_kwargs
        assert call_kwargs['BillingViewArn'] == billing_view_arn

    async def test_get_cost_and_usage_comparisons_with_pagination(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons handles pagination correctly."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        # Set up multi-page response
        mock_ce_client.get_cost_and_usage_comparisons.side_effect = [
            {
                'CostAndUsageComparisons': [
                    {'CostAndUsageSelector': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}
                ],
                'TotalCostAndUsage': {'BlendedCost': {'BaselineTimePeriodAmount': '100.0'}},
                'NextPageToken': 'page2token',
            },
            {
                'CostAndUsageComparisons': [
                    {'CostAndUsageSelector': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}
                ],
                'NextPageToken': None,
            },
        ]

        # Execute
        result = await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        assert mock_ce_client.get_cost_and_usage_comparisons.call_count == 2
        assert len(result['data']['cost_and_usage_comparisons']) == 2

        # The second call repeats the request and adds the token.
        calls = [c.kwargs for c in mock_ce_client.get_cost_and_usage_comparisons.call_args_list]
        assert calls[1] == {**calls[0], 'NextPageToken': 'page2token'}
        assert 'NextPageToken' not in calls[0]
        # The total comes from the first page.
        assert (
            result['data']['total_cost_and_usage']['BlendedCost']['baseline_time_period_amount']
            == '100.0'
        )
        assert 'complete_dataset' not in result['data']
        assert result['data']['pagination']['complete_dataset'] is True
        assert result['data']['pagination']['items_returned'] == 2

    async def test_get_cost_and_usage_comparisons_max_items_stop_and_continue(
        self, mock_context, mock_ce_client
    ):
        """max_items stops with the service token; the continuation resends the request."""
        mock_ce_client.get_cost_and_usage_comparisons.side_effect = [
            {
                'CostAndUsageComparisons': [{'CostAndUsageSelector': {'a': 1}}],
                'TotalCostAndUsage': {'BlendedCost': {'Difference': '5'}},
                'NextPageToken': 't1',
            },
            {'CostAndUsageComparisons': [{'CostAndUsageSelector': {'b': 2}}]},
        ]
        args = (
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-02-01',
            '2023-02-01',
            '2023-03-01',
            'BlendedCost',
            '[{"Type": "DIMENSION", "Key": "SERVICE"}]',
            None,
        )

        first = await get_cost_and_usage_comparisons(*args, 1, None, None)
        token = first['data']['pagination']['next_token']
        second = await get_cost_and_usage_comparisons(*args, 1, token, None)

        assert list(first['data'])[:2] == ['complete_dataset', 'warning']
        assert first['data']['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't1',
            'items_returned': 1,
        }
        assert second['data']['pagination']['complete_dataset'] is True
        # The continuation's first page carries no total, so none is reported.
        assert 'total_cost_and_usage' not in second['data']
        calls = [c.kwargs for c in mock_ce_client.get_cost_and_usage_comparisons.call_args_list]
        assert calls[0]['MaxResults'] == 1
        assert calls[1] == {**calls[0], 'NextPageToken': 't1'}

    async def test_get_cost_and_usage_comparisons_invalid_next_token(
        self, mock_context, mock_ce_client
    ):
        """A rejected caller token maps to invalid_next_token."""
        from botocore.exceptions import ClientError

        mock_ce_client.get_cost_and_usage_comparisons.side_effect = ClientError(
            {'Error': {'Code': 'RequestChangedException', 'Message': 'changed'}},
            'GetCostAndUsageComparisons',
        )

        result = await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-02-01',
            '2023-02-01',
            '2023-03-01',
            'BlendedCost',
            None,
            None,
            None,
            'stale',
            None,
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools.handle_aws_error'
    )
    async def test_get_cost_and_usage_comparisons_error_handling(
        self, mock_handle_aws_error, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons error handling."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        error = Exception('API error')
        mock_ce_client.get_cost_and_usage_comparisons.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_cost_and_usage_comparisons(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_cost_and_usage_comparisons', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestGetCostComparisonDrivers:
    """Tests for get_cost_comparison_drivers function."""

    async def test_get_cost_comparison_drivers_basic(self, mock_context, mock_ce_client):
        """Test get_cost_comparison_drivers with basic parameters."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        # Execute
        result = await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]

        assert 'BaselineTimePeriod' in call_kwargs
        assert call_kwargs['BaselineTimePeriod']['Start'] == baseline_start_date
        assert call_kwargs['BaselineTimePeriod']['End'] == baseline_end_date

        assert 'ComparisonTimePeriod' in call_kwargs
        assert call_kwargs['ComparisonTimePeriod']['Start'] == comparison_start_date
        assert call_kwargs['ComparisonTimePeriod']['End'] == comparison_end_date

        assert call_kwargs['MetricForComparison'] == metric_for_comparison
        assert call_kwargs['MaxResults'] == 10  # largest page without max_items

        assert result['status'] == 'success'
        assert 'cost_comparison_drivers' in result['data']
        assert len(result['data']['cost_comparison_drivers']) == 1
        assert 'cost_drivers' in result['data']['cost_comparison_drivers'][0]
        assert len(result['data']['cost_comparison_drivers'][0]['cost_drivers']) == 2

    async def test_get_cost_comparison_drivers_with_group_by(self, mock_context, mock_ce_client):
        """Test get_cost_comparison_drivers with group_by parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        group_by = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'

        # Execute
        await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            group_by,
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'GroupBy' in call_kwargs
        assert isinstance(call_kwargs['GroupBy'], list)
        assert call_kwargs['GroupBy'][0]['Type'] == 'DIMENSION'
        assert call_kwargs['GroupBy'][0]['Key'] == 'SERVICE'

    async def test_get_cost_comparison_drivers_with_filter(self, mock_context, mock_ce_client):
        """Test get_cost_comparison_drivers with filter parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        filter_expr = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        # Execute
        await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            filter_expr,
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'Filter' in call_kwargs
        assert call_kwargs['Filter']['Dimensions']['Key'] == 'SERVICE'
        assert 'Amazon EC2' in call_kwargs['Filter']['Dimensions']['Values']

    async def test_get_cost_comparison_drivers_with_max_items(self, mock_context, mock_ce_client):
        """Test get_cost_comparison_drivers with max_items below the page maximum."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        max_items = 5

        # Execute
        await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            max_items,
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert call_kwargs['MaxResults'] == 5

    async def test_get_cost_comparison_drivers_with_billing_view_arn(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_comparison_drivers with billing_view_arn parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        billing_view_arn = 'arn:aws:ce::123456789012:billingview/view-1'

        # Execute
        await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            billing_view_arn,
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'BillingViewArn' in call_kwargs
        assert call_kwargs['BillingViewArn'] == billing_view_arn

    async def test_get_cost_comparison_drivers_with_pagination(self, mock_context, mock_ce_client):
        """Test get_cost_comparison_drivers handles pagination correctly."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        # Set up multi-page response
        mock_ce_client.get_cost_comparison_drivers.side_effect = [
            {
                'CostComparisonDrivers': [
                    {'CostSelector': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}
                ],
                'NextPageToken': 'page2token',
            },
            {
                'CostComparisonDrivers': [
                    {'CostSelector': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}
                ],
                'NextPageToken': None,
            },
        ]

        # Execute
        result = await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        assert mock_ce_client.get_cost_comparison_drivers.call_count == 2
        assert len(result['data']['cost_comparison_drivers']) == 2

        # The second call repeats the request and adds the token.
        calls = [c.kwargs for c in mock_ce_client.get_cost_comparison_drivers.call_args_list]
        assert calls[1] == {**calls[0], 'NextPageToken': 'page2token'}
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_get_cost_comparison_drivers_max_items_stops(self, mock_context, mock_ce_client):
        """max_items sizes the last page to the remainder and stops with the token."""
        mock_ce_client.get_cost_comparison_drivers.side_effect = [
            {'CostComparisonDrivers': [{'CostSelector': {}}] * 10, 'NextPageToken': 't1'},
            {'CostComparisonDrivers': [{'CostSelector': {}}] * 5, 'NextPageToken': 't2'},
        ]

        result = await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-02-01',
            '2023-02-01',
            '2023-03-01',
            'BlendedCost',
            None,
            None,
            15,
            None,
            None,
        )

        calls = [c.kwargs for c in mock_ce_client.get_cost_comparison_drivers.call_args_list]
        assert [c['MaxResults'] for c in calls] == [10, 5]
        assert calls[1]['NextPageToken'] == 't1'
        assert len(result['data']['cost_comparison_drivers']) == 15
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't2'
        assert result['data']['pagination']['items_returned'] == 15

    async def test_get_cost_comparison_drivers_continuation_sends_caller_token(
        self, mock_context, mock_ce_client
    ):
        """A continuation sends the caller's token and otherwise identical params."""
        await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-02-01',
            '2023-02-01',
            '2023-03-01',
            'BlendedCost',
            None,
            None,
            None,
            'caller-token',
            None,
        )

        mock_ce_client.get_cost_comparison_drivers.assert_called_once_with(
            BaselineTimePeriod={'Start': '2023-01-01', 'End': '2023-02-01'},
            ComparisonTimePeriod={'Start': '2023-02-01', 'End': '2023-03-01'},
            MetricForComparison='BlendedCost',
            MaxResults=10,
            NextPageToken='caller-token',
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools.handle_aws_error'
    )
    async def test_get_cost_comparison_drivers_error_handling(
        self, mock_handle_aws_error, mock_context, mock_ce_client
    ):
        """Test get_cost_comparison_drivers error handling."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'

        error = Exception('API error')
        mock_ce_client.get_cost_comparison_drivers.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_cost_comparison_drivers(
            mock_context,
            mock_ce_client,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            None,  # group_by
            None,  # filter_expr
            None,  # max_items
            None,  # next_token
            None,  # billing_view_arn
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_cost_comparison_drivers', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


# Two consecutive whole months that pass the dispatcher's local date checks.
_COMPARISON_ARGS = {
    'baseline_start_date': month(2)[0],
    'baseline_end_date': month(2)[1],
    'comparison_start_date': month(1)[0],
    'comparison_end_date': month(1)[1],
    'metric_for_comparison': 'BlendedCost',
}


@pytest.fixture
def real_cost_comparison():
    """Yield the cost_comparison_tools module with the undecorated cost_comparison tool.

    The module is reloaded with FastMCP.tool patched to an identity decorator, then
    reloaded again on teardown so the registered server is restored.
    """
    import fastmcp
    import importlib
    from awslabs.billing_cost_management_mcp_server.tools import cost_comparison_tools as mod

    with patch.object(fastmcp.FastMCP, 'tool', lambda self, *a, **k: lambda fn: fn):
        importlib.reload(mod)
    try:
        yield mod
    finally:
        importlib.reload(mod)


@pytest.mark.asyncio
class TestCostComparison:
    """Tests for the cost_comparison tool dispatcher."""

    @pytest.mark.parametrize(
        'operation,handler,other',
        [
            (
                'getCostAndUsageComparisons',
                'get_cost_and_usage_comparisons',
                'get_cost_comparison_drivers',
            ),
            (
                'getCostComparisonDrivers',
                'get_cost_comparison_drivers',
                'get_cost_and_usage_comparisons',
            ),
        ],
    )
    async def test_routes_operation_with_all_parameters(
        self, mock_context, real_cost_comparison, operation, handler, other
    ):
        """Each operation calls its own handler with every argument in order."""
        mod = real_cost_comparison
        ce_client = MagicMock()
        handler_mock = AsyncMock(return_value={'status': 'success', 'data': {}})
        other_mock = AsyncMock()
        group_by = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'
        view_arn = 'arn:aws:billing::123456789012:billingview/view-1'

        with (
            patch.object(mod, 'create_aws_client', return_value=ce_client),
            patch.object(mod, handler, handler_mock),
            patch.object(mod, other, other_mock),
        ):
            result = await mod.cost_comparison(  # type: ignore[reportCallIssue]
                mock_context,
                operation=operation,
                group_by=group_by,
                filter=filter_json,
                max_items=50,
                billing_view_arn=view_arn,
                **_COMPARISON_ARGS,
            )

        assert result == {'status': 'success', 'data': {}}
        other_mock.assert_not_called()
        assert handler_mock.call_args.args == (
            mock_context,
            ce_client,
            *_COMPARISON_ARGS.values(),
            group_by,
            filter_json,
            50,
            None,
            view_arn,
        )

    async def test_unsupported_operation(self, mock_context, real_cost_comparison):
        """An unknown operation returns an error without calling either handler."""
        mod = real_cost_comparison
        with (
            patch.object(mod, 'create_aws_client', return_value=MagicMock()),
            patch.object(mod, 'get_cost_and_usage_comparisons', AsyncMock()) as comparisons,
            patch.object(mod, 'get_cost_comparison_drivers', AsyncMock()) as drivers,
        ):
            result = await mod.cost_comparison(  # type: ignore[reportCallIssue]
                mock_context, operation='unsupportedOperation', **_COMPARISON_ARGS
            )

        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']
        # A request error the caller can fix: modify_request, not do_not_retry.
        assert result['error_type'] == 'validation_error'
        assert add_retry_guidance(result)['retry_strategy'] == MODIFY_REQUEST
        comparisons.assert_not_called()
        drivers.assert_not_called()

    async def test_handler_exception_returns_error_response(
        self, mock_context, real_cost_comparison
    ):
        """An exception from a handler comes back as an error response."""
        mod = real_cost_comparison
        with (
            patch.object(mod, 'create_aws_client', return_value=MagicMock()),
            patch.object(
                mod,
                'get_cost_and_usage_comparisons',
                AsyncMock(side_effect=RuntimeError('API error')),
            ),
        ):
            result = await mod.cost_comparison(  # type: ignore[reportCallIssue]
                mock_context, operation='getCostAndUsageComparisons', **_COMPARISON_ARGS
            )

        assert result['status'] == 'error'
        assert 'API error' in result['message']


def test_cost_comparison_server_initialization():
    """Test that the cost_comparison_server is properly initialized."""
    # Verify the server name
    assert cost_comparison_server.name == 'cost-comparison-tools'

    # Verify the server instructions
    instructions = cost_comparison_server.instructions
    assert instructions is not None
    assert (
        'Tools for working with AWS Cost Comparison API' in instructions if instructions else False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation,handler',
    [
        ('getCostAndUsageComparisons', 'get_cost_and_usage_comparisons'),
        ('getCostComparisonDrivers', 'get_cost_comparison_drivers'),
    ],
)
async def test_cost_comparison_tool_passes_pagination_params(mock_context, operation, handler):
    """The tool passes max_items and next_token through to the operation handler."""
    import fastmcp
    import importlib
    from awslabs.billing_cost_management_mcp_server.tools import cost_comparison_tools as mod

    def _identity_tool(self, *args, **kwargs):
        return lambda fn: fn

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(mod)
    try:
        mock_handler = AsyncMock(return_value={'status': 'success', 'data': {}})
        with (
            patch.object(mod, 'create_aws_client', return_value=MagicMock()),
            patch.object(mod, handler, mock_handler),
        ):
            result = await mod.cost_comparison(  # type: ignore[reportCallIssue]
                mock_context,
                operation=operation,
                baseline_start_date=month(2)[0],
                baseline_end_date=month(2)[1],
                comparison_start_date=month(1)[0],
                comparison_end_date=month(1)[1],
                metric_for_comparison='BlendedCost',
                max_items=7,
                next_token='tok',
            )
    finally:
        importlib.reload(mod)

    assert result['status'] == 'success'
    assert mock_handler.call_args.args[9:11] == (7, 'tok')


# ---------------------------------------------------------------------------
# The real cost-comparison dispatcher: local checks of the rules Cost Explorer's
# comparison APIs enforce. Dates are relative to today so the tests don't rot.
# ---------------------------------------------------------------------------


@pytest.fixture
def dispatch_ce_client():
    """A CE client whose comparison calls succeed with an empty page."""
    client = MagicMock()
    client.get_cost_and_usage_comparisons.return_value = {'CostAndUsageComparisons': []}
    client.get_cost_comparison_drivers.return_value = {'CostComparisonDrivers': []}
    return client


async def _call(ctx, client, operation, baseline, comparison, **kwargs):
    with patch(f'{MODULE}.create_aws_client', return_value=client) as create:
        client.created = create
        return await cost_comparison(
            ctx,
            operation=operation,
            baseline_start_date=baseline[0],
            baseline_end_date=baseline[1],
            comparison_start_date=comparison[0],
            comparison_end_date=comparison[1],
            metric_for_comparison=kwargs.pop('metric_for_comparison', 'UnblendedCost'),
            **kwargs,
        )


def _assert_local_validation_error(result, client, *needles):
    assert result['status'] == 'error'
    assert result.get('error_type') == 'validation_error', result
    assert add_retry_guidance(result)['retry_strategy'] == 'modify_request'
    for needle in needles:
        assert needle in result['message'], (needle, result['message'])
    client.get_cost_and_usage_comparisons.assert_not_called()
    client.get_cost_comparison_drivers.assert_not_called()
    created = getattr(client, 'created', None)
    if created is not None:
        created.assert_not_called()


def _client_error(code, message, request_id='r1'):
    return ClientError(
        {
            'Error': {'Code': code, 'Message': message},
            'ResponseMetadata': {'RequestId': request_id, 'HTTPStatusCode': 400},
        },
        'GetCostComparisonDrivers',
    )


MISALIGNED = {
    'baseline_mid_month': ((month_start(2)[:8] + '15', month_start(1)[:8] + '15'), month(1)),
    'baseline_two_months': ((month_start(3), month_start(1)), month(1)),
    'comparison_end_second_of_month': (month(2), (month_start(1), month_start(0)[:8] + '02')),
    'comparison_reversed_bounds': (month(2), (month_start(0), month_start(1))),
    'baseline_not_a_date': (('last month', month_start(1)), month(1)),
    'baseline_impossible_date': ((month_start(2)[:8] + '32', month_start(1)), month(1)),
}


@pytest.mark.asyncio
class TestCostComparisonDispatcherValidation:
    """Requests CE would reject fail locally, naming the rule, with no AWS call."""

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('case', list(MISALIGNED))
    async def test_month_misaligned_period_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation, case
    ):
        """U1: a period that is not one whole calendar month points to getCostAndUsage."""
        baseline, comparison = MISALIGNED[case]
        result = await _call(mock_context, dispatch_ce_client, operation, baseline, comparison)
        _assert_local_validation_error(
            result, dispatch_ce_client, 'whole calendar months', 'getCostAndUsage'
        )

    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_same_month_twice_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation
    ):
        """CE rejects a baseline equal to the comparison period."""
        result = await _call(mock_context, dispatch_ce_client, operation, month(1), month(1))
        _assert_local_validation_error(result, dispatch_ce_client, 'same month')

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('months_back', [0, -1], ids=['current_month', 'next_month'])
    async def test_current_or_future_comparison_period_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation, months_back
    ):
        """U2: CE compares completed months only (current month included, per its code)."""
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(1), month(months_back)
        )
        _assert_local_validation_error(
            result, dispatch_ce_client, 'current or a future month', month(1)[0]
        )

    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_future_baseline_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation
    ):
        """The completed-month rule applies to the baseline period too."""
        result = await _call(mock_context, dispatch_ce_client, operation, month(-2), month(1))
        _assert_local_validation_error(result, dispatch_ce_client, 'baseline period')

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('months_back', [39, 40])
    async def test_baseline_beyond_38_months_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation, months_back
    ):
        """U3: no setting makes a month older than 38 months available."""
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(months_back), month(1)
        )
        _assert_local_validation_error(result, dispatch_ce_client, '38 months')

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('months_back', [14, 37])
    async def test_baseline_14_to_37_months_back_is_not_rejected_locally(
        self, mock_context, dispatch_ce_client, operation, months_back
    ):
        """U4: the MCP can't see the multi-year setting, so CE decides for 14-38 months."""
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(months_back), month(1)
        )
        assert result['status'] == 'success'
        getattr(dispatch_ce_client, CE_METHOD[operation]).assert_called_once()

    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_baseline_later_than_comparison_reaches_ce(
        self, mock_context, dispatch_ce_client, operation
    ):
        """CE accepts a baseline later than the comparison period (live-verified)."""
        result = await _call(mock_context, dispatch_ce_client, operation, month(1), month(2))
        assert result['status'] == 'success'
        getattr(dispatch_ce_client, CE_METHOD[operation]).assert_called_once()

    async def test_data_unavailable_for_old_baseline_gets_multi_year_hint(
        self, mock_context, dispatch_ce_client
    ):
        """U5: CE's DataUnavailableException for a >13-month period names multi-year data."""
        dispatch_ce_client.get_cost_comparison_drivers.side_effect = _client_error(
            'DataUnavailableException', 'Cost data unavailable.'
        )
        result = await _call(
            mock_context, dispatch_ce_client, 'getCostComparisonDrivers', month(14), month(13)
        )
        assert result['error_type'] == 'DataUnavailableException'
        assert result['message'] == 'Cost data unavailable.'
        assert 'multi-year' in result['hint']
        assert add_retry_guidance(result)['hint'] == result['hint']

    async def test_data_unavailable_for_recent_months_has_no_multi_year_hint(
        self, mock_context, dispatch_ce_client
    ):
        """Within 13 months the multi-year setting isn't the cause, so no hint is added."""
        dispatch_ce_client.get_cost_and_usage_comparisons.side_effect = _client_error(
            'DataUnavailableException', 'Cost data unavailable.'
        )
        result = await _call(
            mock_context, dispatch_ce_client, 'getCostAndUsageComparisons', month(2), month(1)
        )
        assert result['error_type'] == 'DataUnavailableException'
        assert 'hint' not in result

    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_valid_month_pair_reaches_ce_unchanged(
        self, mock_context, dispatch_ce_client, operation
    ):
        """U8: a valid request is sent as given, with the API's largest page size."""
        baseline, comparison = month(2), month(1)
        result = await _call(mock_context, dispatch_ce_client, operation, baseline, comparison)
        assert result['status'] == 'success'
        kwargs = getattr(dispatch_ce_client, CE_METHOD[operation]).call_args[1]
        assert kwargs['BaselineTimePeriod'] == {'Start': baseline[0], 'End': baseline[1]}
        assert kwargs['ComparisonTimePeriod'] == {'Start': comparison[0], 'End': comparison[1]}
        assert kwargs['MetricForComparison'] == 'UnblendedCost'
        assert (
            kwargs['MaxResults']
            == {
                'getCostAndUsageComparisons': 2000,
                'getCostComparisonDrivers': 10,
            }[operation]
        )

    @pytest.mark.parametrize(
        'operation,max_items,page_size',
        [('getCostAndUsageComparisons', 5000, 2000), ('getCostComparisonDrivers', 20, 10)],
    )
    async def test_large_max_items_never_sends_more_than_the_page_cap(
        self, mock_context, dispatch_ce_client, operation, max_items, page_size
    ):
        """U6/U7: max_items above the API cap pages instead of sending MaxResults > cap."""
        await _call(
            mock_context, dispatch_ce_client, operation, month(2), month(1), max_items=max_items
        )
        kwargs = getattr(dispatch_ce_client, CE_METHOD[operation]).call_args[1]
        assert kwargs['MaxResults'] == page_size

    @pytest.mark.parametrize('metric', ['unblendedCost', 'unblended_cost', 'Cost', ''])
    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_metric_outside_supported_set_rejected_without_aws_call(
        self, mock_context, dispatch_ce_client, operation, metric
    ):
        """U10: metric names are exact-case; the message lists the supported ones."""
        result = await _call(
            mock_context,
            dispatch_ce_client,
            operation,
            month(2),
            month(1),
            metric_for_comparison=metric,
        )
        _assert_local_validation_error(result, dispatch_ce_client, 'UnblendedCost', operation)

    @pytest.mark.parametrize(
        'metric', ['UsageQuantity', 'NormalizedUsageAmount', 'USAGE_QUANTITY']
    )
    async def test_usage_metrics_rejected_for_drivers_without_aws_call(
        self, mock_context, dispatch_ce_client, metric
    ):
        """CE's drivers API accepts cost metrics only (INVALID_COST_METRIC, live-verified)."""
        result = await _call(
            mock_context,
            dispatch_ce_client,
            'getCostComparisonDrivers',
            month(2),
            month(1),
            metric_for_comparison=metric,
        )
        _assert_local_validation_error(result, dispatch_ce_client, 'NetAmortizedCost')
        assert 'UsageQuantity' not in result['message'].split('Use one of')[1]

    @pytest.mark.parametrize('operation', OPERATIONS)
    async def test_every_supported_metric_reaches_ce(
        self, mock_context, dispatch_ce_client, operation
    ):
        """U11: every documented metric, and its UPPER_SNAKE alias, reaches CE."""
        metrics = (
            COMPARISON_METRICS if operation == 'getCostAndUsageComparisons' else DRIVER_METRICS
        )
        aliases = {'UnblendedCost': 'UNBLENDED_COST', 'NetAmortizedCost': 'NET_AMORTIZED_COST'}
        for metric in [*metrics, *aliases.values()]:
            result = await _call(
                mock_context,
                dispatch_ce_client,
                operation,
                month(2),
                month(1),
                metric_for_comparison=metric,
            )
            assert result['status'] == 'success', (metric, result)
        assert getattr(dispatch_ce_client, CE_METHOD[operation]).call_count == len(metrics) + 2

    async def test_malformed_filter_shape_is_not_reported_as_transient(self, mock_context):
        """U9: botocore's ParamValidationError is a validation error, not a connection one."""
        client = boto3.client(
            'ce', region_name='us-east-1', aws_access_key_id='x', aws_secret_access_key='y'
        )
        with Stubber(client) as stubber:
            # A queued response gets the call past the Stubber to botocore's validation.
            stubber.add_response('get_cost_and_usage_comparisons', {})
            result = await _call(
                mock_context,
                client,
                'getCostAndUsageComparisons',
                month(2),
                month(1),
                filter='{"Dimensions": {"Key": "SERVICE", "MatchValue": "Amazon EC2"}}',
            )
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert add_retry_guidance(result)['retry_strategy'] == 'modify_request'

    async def test_ce_validation_exception_message_survives(
        self, mock_context, dispatch_ce_client
    ):
        """U12: CE's own message, error_type and request_id reach the agent unchanged."""
        dispatch_ce_client.get_cost_comparison_drivers.side_effect = _client_error(
            'ValidationException', 'Invalid GroupBy dimension.', request_id='r2'
        )
        result = await _call(
            mock_context, dispatch_ce_client, 'getCostComparisonDrivers', month(2), month(1)
        )
        assert result['error_type'] == 'ValidationException'
        assert result['message'] == 'Invalid GroupBy dimension.'
        assert result['request_id'] == 'r2'
        assert add_retry_guidance(result)['retry_strategy'] == 'modify_request'
        assert 'hint' not in result

    async def test_unsupported_operation_makes_no_aws_client(self, mock_context):
        """An unknown operation is rejected before dates are checked or a client is made."""
        with patch(f'{MODULE}.create_aws_client') as create:
            result = await cost_comparison(
                mock_context,
                operation='unsupportedOperation',
                baseline_start_date='x',
                baseline_end_date='x',
                comparison_start_date='x',
                comparison_end_date='x',
                metric_for_comparison='BlendedCost',
            )
        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']
        assert result['error_type'] == 'validation_error'
        assert add_retry_guidance(result)['retry_strategy'] == 'modify_request'
        create.assert_not_called()


EC2 = 'Amazon Elastic Compute Cloud - Compute'


def _service(values, match_options=None):
    """A SERVICE Dimensions filter, optionally with MatchOptions."""
    dimensions = {'Key': 'SERVICE', 'Values': values}
    if match_options is not None:
        dimensions['MatchOptions'] = match_options
    return {'Dimensions': dimensions}


def _nest(expression, how):
    """``expression`` at the top level or inside each logical operator."""
    other = _service([EC2])
    return {
        'top': expression,
        'not': {'Not': expression},
        'and': {'And': [other, expression]},
        'or': {'Or': [other, expression]},
        'or_not': {'Or': [other, {'Not': expression}]},
    }[how]


NESTINGS = ['top', 'not', 'and', 'or', 'or_not']


@pytest.mark.asyncio
class TestCostComparisonFilterValidation:
    """Filters the comparison APIs mishandle fail locally with no AWS call."""

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('how', NESTINGS)
    @pytest.mark.parametrize(
        'option', ['CASE_INSENSITIVE', 'STARTS_WITH', 'ENDS_WITH', 'CONTAINS', 'ABSENT']
    )
    async def test_ignored_dimension_match_option_rejected(
        self, mock_context, dispatch_ce_client, operation, how, option
    ):
        """CE ignores these MatchOptions and matches values exactly: a silent $0 or total."""
        flt = _nest(_service([EC2.lower()], ['EQUALS', option]), how)
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(2), month(1), filter=json.dumps(flt)
        )
        _assert_local_validation_error(
            result, dispatch_ce_client, option, 'exactly', 'getDimensionValues'
        )

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('kind', ['Tags', 'CostCategories'])
    @pytest.mark.parametrize('option', ['CASE_INSENSITIVE', 'STARTS_WITH', 'CONTAINS'])
    async def test_ignored_tag_and_cost_category_match_option_rejected(
        self, mock_context, dispatch_ce_client, operation, kind, option
    ):
        """Tags and cost categories honor only ABSENT besides the default."""
        flt = {kind: {'Key': 'team', 'Values': ['web'], 'MatchOptions': [option]}}
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(2), month(1), filter=json.dumps(flt)
        )
        _assert_local_validation_error(result, dispatch_ce_client, option, kind)

    @pytest.mark.parametrize('kind', ['Tags', 'CostCategories'])
    @pytest.mark.parametrize('how', NESTINGS)
    async def test_absent_with_values_rejected(self, mock_context, dispatch_ce_client, kind, how):
        """The comparison APIs drop Values when ABSENT is set, so the result ignores them."""
        flt = _nest({kind: {'Key': 'team', 'Values': ['web'], 'MatchOptions': ['ABSENT']}}, how)
        result = await _call(
            mock_context,
            dispatch_ce_client,
            'getCostAndUsageComparisons',
            month(2),
            month(1),
            filter=json.dumps(flt),
        )
        _assert_local_validation_error(result, dispatch_ce_client, 'ABSENT ignores its Values')

    async def test_filter_nested_too_deep_rejected(self, mock_context, dispatch_ce_client):
        """A filter nested deep enough to fail in Cost Explorer fails locally; one level less passes.

        Live, getCostComparisonDrivers accepts 96 Not, And or Or levels and returns
        InternalFailure at 97; both operations reject 98 with "Value is too deeply nested".
        """
        assert MAX_FILTER_DEPTH == 97
        deepest_allowed = _service([EC2])
        for _ in range(MAX_FILTER_DEPTH - 1):
            deepest_allowed = {'Not': deepest_allowed}
        validate_comparison_filter(deepest_allowed)
        too_deep = (
            '{"Not": ' * MAX_FILTER_DEPTH + json.dumps(_service([EC2])) + '}' * MAX_FILTER_DEPTH
        )
        result = await _call(
            mock_context,
            dispatch_ce_client,
            'getCostAndUsageComparisons',
            month(2),
            month(1),
            filter=too_deep,
        )
        _assert_local_validation_error(
            result, dispatch_ce_client, f'nested {MAX_FILTER_DEPTH} or more'
        )
        too_wide_and = _service([EC2])
        for _ in range(MAX_FILTER_DEPTH):
            too_wide_and = {'And': [_service([EC2]), too_wide_and]}
        with pytest.raises(ValueError, match='or more And/Or/Not levels'):
            validate_comparison_filter(too_wide_and)

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize('how', NESTINGS)
    async def test_resource_id_filter_rejected(
        self, mock_context, dispatch_ce_client, operation, how
    ):
        """CE fails a RESOURCE_ID filter with InternalFailure, which retrying never fixes."""
        flt = _nest({'Dimensions': {'Key': 'RESOURCE_ID', 'Values': ['i-0abc']}}, how)
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(2), month(1), filter=json.dumps(flt)
        )
        _assert_local_validation_error(
            result, dispatch_ce_client, 'RESOURCE_ID', 'getCostAndUsageWithResources'
        )

    @pytest.mark.parametrize('operation', OPERATIONS)
    @pytest.mark.parametrize(
        'flt',
        [
            _service([EC2]),
            _service([EC2], ['EQUALS']),
            _service([EC2], ['EQUALS', 'CASE_SENSITIVE']),
            {'Not': _service([EC2], [])},
            {'Dimensions': {'Key': 'USAGE_TYPE_GROUP', 'Values': ['EC2: Running Hours']}},
            {'Tags': {'Key': 'team', 'MatchOptions': ['ABSENT']}},
            {'CostCategories': {'Key': 'env', 'Values': ['prod'], 'MatchOptions': ['EQUALS']}},
            {'CostCategories': {'Key': 'env', 'MatchOptions': ['ABSENT']}},
            {'And': [_service([EC2]), {'Tags': {'Key': 'team', 'Values': ['web']}}]},
        ],
        ids=[
            'no_options',
            'equals',
            'equals_case_sensitive',
            'not_empty_options',
            'usage_type_group',
            'tag_absent',
            'cost_category_equals',
            'cost_category_absent',
            'and',
        ],
    )
    async def test_supported_filter_reaches_ce_unchanged(
        self, mock_context, dispatch_ce_client, operation, flt
    ):
        """Filters the comparison APIs honor are sent as given."""
        result = await _call(
            mock_context, dispatch_ce_client, operation, month(2), month(1), filter=json.dumps(flt)
        )
        assert result['status'] == 'success', result
        call = getattr(dispatch_ce_client, CE_METHOD[operation])
        assert call.call_args.kwargs['Filter'] == flt

    async def test_shapes_left_to_botocore_are_skipped(self):
        """Non-dict children are botocore's to reject; checks still reach the dict ones."""
        validate_comparison_filter({'And': ['junk', 3, None], 'Not': [], 'Or': 'x'})
        validate_comparison_filter({'Dimensions': {'Key': 'SERVICE', 'MatchOptions': 'x'}})
        with pytest.raises(ValueError, match='RESOURCE_ID'):
            validate_comparison_filter(
                {'And': ['junk', 3, None, {'Dimensions': {'Key': 'RESOURCE_ID', 'Values': []}}]}
            )

    async def test_invalid_filter_json_is_a_validation_error(
        self, mock_context, dispatch_ce_client
    ):
        """A filter that is not JSON still fails locally, as before."""
        result = await _call(
            mock_context,
            dispatch_ce_client,
            'getCostAndUsageComparisons',
            month(2),
            month(1),
            filter='{not json',
        )
        _assert_local_validation_error(result, dispatch_ce_client, 'Invalid JSON format')


class TestValidateComparisonRequest:
    """Boundaries of the rules, at a fixed date."""

    TODAY = date(2026, 10, 23)

    def _validate(self, baseline, comparison, today=TODAY, metric='UnblendedCost'):
        (baseline_start, baseline_end), (comparison_start, comparison_end) = baseline, comparison
        validate_comparison_request(
            'getCostAndUsageComparisons',
            baseline_start,
            baseline_end,
            comparison_start,
            comparison_end,
            metric,
            today=today,
        )

    def test_oldest_allowed_start_is_today_minus_38_months(self):
        """CE rejects a start before today minus 38 months, to the day."""
        self._validate(('2023-09-01', '2023-10-01'), ('2026-09-01', '2026-10-01'))
        with pytest.raises(ValueError, match='before 2023-08-23'):
            self._validate(('2023-08-01', '2023-09-01'), ('2026-09-01', '2026-10-01'))

    def test_month_38_back_is_allowed_on_the_first(self):
        """On the 1st, the month exactly 38 months back is still in range."""
        self._validate(
            ('2023-08-01', '2023-09-01'), ('2026-09-01', '2026-10-01'), today=date(2026, 10, 1)
        )

    def test_last_month_is_allowed_on_the_first(self):
        """A period ending today (the 1st) is complete."""
        self._validate(
            ('2026-08-01', '2026-09-01'), ('2026-09-01', '2026-10-01'), today=date(2026, 10, 1)
        )

    def test_december_to_january_is_one_month(self):
        """A period may span the year boundary."""
        self._validate(('2025-12-01', '2026-01-01'), ('2026-09-01', '2026-10-01'))

    def test_timestamp_form_is_accepted(self):
        """CE accepts YYYY-MM-DDThh:mm:ssZ as well as YYYY-MM-DD."""
        self._validate(
            ('2026-08-01T00:00:00Z', '2026-09-01T00:00:00Z'), ('2026-09-01', '2026-10-01')
        )

    def test_months_before_clamps_to_month_end(self):
        """Like Java's minusMonths, the day clamps to the shorter month."""
        assert _months_before(date(2026, 3, 31), 1) == date(2026, 2, 28)
        assert _months_before(date(2026, 1, 15), -1) == date(2026, 2, 15)


def test_page_caps_match_botocore_max_results():
    """U13: the page sizes the tool sends match the botocore model's MaxResults caps."""
    shapes = boto3.client(
        'ce', region_name='us-east-1', aws_access_key_id='x', aws_secret_access_key='y'
    ).meta.service_model
    assert (
        shapes.shape_for('CostAndUsageComparisonsMaxResults').metadata['max']
        == GET_COST_AND_USAGE_COMPARISONS.page_max
    )
    assert (
        shapes.shape_for('CostComparisonDriversMaxResults').metadata['max']
        == GET_COST_COMPARISON_DRIVERS.page_max
    )


@pytest.mark.asyncio
async def test_description_states_the_enforced_rules():
    """The served description names the rules the tool now enforces."""
    tool = await cost_comparison_server.get_tool('cost-comparison')
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert 'the current month and future months are rejected' in description
    assert 'The two periods must be different months' in description
    assert 'more than 38 months ago is rejected locally' in description
    assert 'getCostComparisonDrivers accepts only the five cost metrics' in description
    assert (
        'UsageQuantity: Usage amounts in their respective units. getCostAndUsageComparisons only'
        in description
    )
    assert 'MatchOptions other than EQUALS and CASE_SENSITIVE (the default)' in description
    assert 'ABSENT together with Values' in description
    assert 'A RESOURCE_ID filter' in description
    assert 'Nesting of 97 or more And/Or/Not levels' in description
    assert 'Keys and values match exactly, including case' in description
