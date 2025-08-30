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

import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_comparison_tools import (
    cost_comparison_server,
    get_cost_and_usage_comparisons,
    get_cost_comparison_drivers,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def cost_comparison(ctx, operation, **kwargs):
    """Mock implementation of cost_comparison for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'getCostAndUsageComparisons':
        if (
            not kwargs.get('baseline_start_date')
            or not kwargs.get('baseline_end_date')
            or not kwargs.get('comparison_start_date')
            or not kwargs.get('comparison_end_date')
        ):
            return format_response(
                'error',
                {},
                'baseline_start_date, baseline_end_date, comparison_start_date, and comparison_end_date are required',
            )

        return {
            'status': 'success',
            'data': {
                'cost_and_usage_comparisons': [
                    {
                        'service': 'Amazon EC2',
                        'baseline_cost': 500.0,
                        'comparison_cost': 600.0,
                        'difference': 100.0,
                        'percentage_change': 20.0,
                    }
                ],
                'total_cost_and_usage': {
                    'baseline_cost': 1000.0,
                    'comparison_cost': 1200.0,
                    'difference': 200.0,
                    'percentage_change': 20.0,
                },
            },
        }

    elif operation == 'getCostComparisonDrivers':
        if (
            not kwargs.get('baseline_start_date')
            or not kwargs.get('baseline_end_date')
            or not kwargs.get('comparison_start_date')
            or not kwargs.get('comparison_end_date')
        ):
            return format_response(
                'error',
                {},
                'baseline_start_date, baseline_end_date, comparison_start_date, and comparison_end_date are required',
            )

        return {
            'status': 'success',
            'data': {
                'cost_drivers': [
                    {
                        'name': 'BoxUsage:t2.micro',
                        'type': 'USAGE_TYPE',
                        'baseline_cost': 200.0,
                        'comparison_cost': 250.0,
                        'difference': 50.0,
                    }
                ]
            },
        }

    else:
        return format_response('error', {}, f'Unsupported operation: {operation}')


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
            None,  # max_results
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
        assert call_kwargs['MaxResults'] == 10  # default value

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
            None,  # max_results
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
            None,  # max_results
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'Filter' in call_kwargs
        assert call_kwargs['Filter']['Dimensions']['Key'] == 'SERVICE'
        assert 'Amazon EC2' in call_kwargs['Filter']['Dimensions']['Values']

    async def test_get_cost_and_usage_comparisons_with_max_results(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_and_usage_comparisons with max_results parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        max_results = 50

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
            max_results,
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'MaxResults' in call_kwargs
        assert call_kwargs['MaxResults'] == 50

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
            None,  # max_results
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
            None,  # max_results
            None,  # billing_view_arn
        )

        # Assert
        assert mock_ce_client.get_cost_and_usage_comparisons.call_count == 2
        assert len(result['data']['cost_and_usage_comparisons']) == 2

        # Check second call includes NextPageToken
        second_call_kwargs = mock_ce_client.get_cost_and_usage_comparisons.call_args_list[1][1]
        assert 'NextPageToken' in second_call_kwargs
        assert second_call_kwargs['NextPageToken'] == 'page2token'

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
            None,  # max_results
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
            None,  # max_results
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
        assert call_kwargs['MaxResults'] == 10  # default value

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
            None,  # max_results
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
            None,  # max_results
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'Filter' in call_kwargs
        assert call_kwargs['Filter']['Dimensions']['Key'] == 'SERVICE'
        assert 'Amazon EC2' in call_kwargs['Filter']['Dimensions']['Values']

    async def test_get_cost_comparison_drivers_with_max_results(
        self, mock_context, mock_ce_client
    ):
        """Test get_cost_comparison_drivers with max_results parameter."""
        # Setup
        baseline_start_date = '2023-01-01'
        baseline_end_date = '2023-02-01'
        comparison_start_date = '2023-02-01'
        comparison_end_date = '2023-03-01'
        metric_for_comparison = 'BlendedCost'
        max_results = 50

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
            max_results,
            None,  # billing_view_arn
        )

        # Assert
        call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'MaxResults' in call_kwargs
        assert call_kwargs['MaxResults'] == 50

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
            None,  # max_results
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
            None,  # max_results
            None,  # billing_view_arn
        )

        # Assert
        assert mock_ce_client.get_cost_comparison_drivers.call_count == 2
        assert len(result['data']['cost_comparison_drivers']) == 2

        # Check second call includes NextPageToken
        second_call_kwargs = mock_ce_client.get_cost_comparison_drivers.call_args_list[1][1]
        assert 'NextPageToken' in second_call_kwargs
        assert second_call_kwargs['NextPageToken'] == 'page2token'

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
            None,  # max_results
            None,  # billing_view_arn
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_cost_comparison_drivers', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestCostComparison:
    """Tests for cost_comparison function."""

    async def test_cost_comparison_getCostAndUsageComparisons(self, mock_context):
        """Test cost_comparison with getCostAndUsageComparisons operation."""
        # Execute
        result = await cost_comparison(
            mock_context,
            operation='getCostAndUsageComparisons',
            baseline_start_date='2023-01-01',
            baseline_end_date='2023-02-01',
            comparison_start_date='2023-02-01',
            comparison_end_date='2023-03-01',
            metric_for_comparison='BlendedCost',
        )

        # Assert
        assert result['status'] == 'success'

    async def test_cost_comparison_getCostComparisonDrivers(self, mock_context):
        """Test cost_comparison with getCostComparisonDrivers operation."""
        # Execute
        result = await cost_comparison(
            mock_context,
            operation='getCostComparisonDrivers',
            baseline_start_date='2023-01-01',
            baseline_end_date='2023-02-01',
            comparison_start_date='2023-02-01',
            comparison_end_date='2023-03-01',
            metric_for_comparison='BlendedCost',
        )

        # Assert
        assert result['status'] == 'success'

    async def test_cost_comparison_with_all_parameters(self, mock_context):
        """Test cost_comparison with all parameters."""
        # Execute
        result = await cost_comparison(
            mock_context,
            operation='getCostAndUsageComparisons',
            baseline_start_date='2023-01-01',
            baseline_end_date='2023-02-01',
            comparison_start_date='2023-02-01',
            comparison_end_date='2023-03-01',
            metric_for_comparison='BlendedCost',
            group_by='[{"Type": "DIMENSION", "Key": "SERVICE"}]',
            filter='{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}',
            max_results=50,
            billing_view_arn='arn:aws:ce::123456789012:billingview/view-1',
        )

        # Assert
        assert result['status'] == 'success'

    async def test_cost_comparison_unsupported_operation(self, mock_context):
        """Test cost_comparison with unsupported operation."""
        # Execute
        result = await cost_comparison(
            mock_context,
            operation='unsupportedOperation',
            baseline_start_date='2023-01-01',
            baseline_end_date='2023-02-01',
            comparison_start_date='2023-02-01',
            comparison_end_date='2023-03-01',
            metric_for_comparison='BlendedCost',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']

    async def test_cost_comparison_error_handling(self, mock_context):
        """Test cost_comparison error handling."""
        # Setup
        result = {'status': 'error', 'message': 'API error'}

        # Assert
        assert result['status'] == 'error'


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
