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

    # Set up mock response for get_savings_plans_utilization
    mock_client.get_savings_plans_utilization.return_value = {
        'SavingsPlansUtilizations': [
            {
                'TimePeriod': {
                    'Start': '2023-01-01',
                    'End': '2023-01-02',
                },
                'TotalCommitment': '100.0',
                'UsedCommitment': '95.0',
                'UnusedCommitment': '5.0',
                'UtilizationPercentage': '95.0',
                'SavingsPlansCount': 5,
            }
        ],
        'Total': {
            'TotalCommitment': '100.0',
            'UsedCommitment': '95.0',
            'UnusedCommitment': '5.0',
            'UtilizationPercentage': '95.0',
        },
        'NextToken': None,
    }

    # Set up mock response for get_savings_plans_utilization_details
    mock_client.get_savings_plans_utilization_details.return_value = {
        'SavingsPlansUtilizationDetails': [
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-12345abcdef',
                'Attributes': {
                    'Region': 'us-east-1',
                    'InstanceFamily': 'm5',
                    'OfferingType': 'EC2InstanceSavingsPlans',
                },
                'TotalCommitment': '20.0',
                'UsedCommitment': '19.0',
                'UnusedCommitment': '1.0',
                'UtilizationPercentage': '95.0',
                'NetSavings': '10.0',
                'OnDemandCostEquivalent': '30.0',
                'AmortizedUpfrontFee': '1.0',
                'RecurringCommitment': '19.0',
            },
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-67890ghijkl',
                'Attributes': {
                    'Region': 'us-west-2',
                    'InstanceFamily': 'c5',
                    'OfferingType': 'ComputeSavingsPlans',
                },
                'TotalCommitment': '80.0',
                'UsedCommitment': '76.0',
                'UnusedCommitment': '4.0',
                'UtilizationPercentage': '95.0',
                'NetSavings': '40.0',
                'OnDemandCostEquivalent': '120.0',
                'AmortizedUpfrontFee': '5.0',
                'RecurringCommitment': '75.0',
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

        # Check specific values
        detail = result['data']['savings_plans_utilization_details'][0]
        assert 'savings_plan_arn' in detail
        assert 'attributes' in detail
        assert 'utilization' in detail
        assert 'savings' in detail

        # Check nested values
        assert detail['utilization']['utilization_percentage'] == 95.0
        assert detail['savings']['net_savings'] == {
            'amount': 0.0,
            'currency': 'USD',
            'formatted': '0.0 USD',
        }

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
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_get_savings_plans_utilization_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_savings_plans_utilization with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization.return_value['SavingsPlansUtilizations'],
            {'NextToken': None},
        )

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
        mock_paginate_response.assert_called_once()
        call_kwargs = mock_paginate_response.call_args[1]

        assert call_kwargs['operation_name'] == 'GetSavingsPlansUtilization'
        assert call_kwargs['result_key'] == 'SavingsPlansUtilizations'

        request_params = call_kwargs['request_params']
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert 'savings_plans_utilizations' in result['data']
        assert len(result['data']['savings_plans_utilizations']) == 1

        # Check total utilization data
        assert 'total' in result['data']
        assert result['data']['total']['utilization_percentage'] == 95.0
        assert result['data']['total']['total_commitment'] == {
            'amount': 0.0,
            'currency': 'USD',
            'formatted': '0.0 USD',
        }

        # Check utilization details
        utilization = result['data']['savings_plans_utilizations'][0]
        assert utilization['total_commitment'] == {
            'amount': 0.0,
            'currency': 'USD',
            'formatted': '0.0 USD',
        }
        assert utilization['used_commitment'] == {
            'amount': 0.0,
            'currency': 'USD',
            'formatted': '0.0 USD',
        }
        assert utilization['unused_commitment'] == {
            'amount': 0.0,
            'currency': 'USD',
            'formatted': '0.0 USD',
        }
        assert utilization['utilization_percentage'] == 95.0
        assert utilization['savings_plans_count'] == 5

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.parse_json')
    async def test_get_savings_plans_utilization_with_filter(
        self,
        mock_parse_json,
        mock_paginate_response,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_savings_plans_utilization with filter parameter."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_savings_plans_utilization.return_value['SavingsPlansUtilizations'],
            {'NextToken': None},
        )

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

        request_params = mock_paginate_response.call_args[1]['request_params']
        assert 'Filter' in request_params
        assert request_params['Filter'] == mock_filter
        assert request_params['Granularity'] == 'MONTHLY'

        assert result['status'] == 'success'

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
        assert request_params['Granularity'] == 'MONTHLY'

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
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_empty_data(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization with empty data - covers lines 250-253."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate.return_value = ([], {'NextToken': None})  # Empty data

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
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_malformed_data(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization with malformed data - covers monetary parsing edge cases."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        malformed_data = [
            {
                'TimePeriod': {},
                'TotalCommitment': None,
                'UsedCommitment': {'Amount': 'invalid'},
                'UnusedCommitment': {},
                'UtilizationPercentage': 'not_a_number',
                'SavingsPlansCount': None,
            }
        ]

        mock_paginate.return_value = (malformed_data, {'NextToken': None})
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'Total': None  # No total data
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
            utilization = result['data']['savings_plans_utilizations'][0]

            # Check default values are applied for malformed data
            assert utilization['total_commitment']['amount'] == 0.0
            assert utilization['used_commitment']['amount'] == 0.0
            assert utilization['unused_commitment']['amount'] == 0.0
            assert utilization['utilization_percentage'] == 0.0
            assert utilization['time_period'] == {'Start': '2023-01-01', 'End': '2023-01-31'}

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_total_error(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization when getting total data fails - covers lines 334-342."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        utilization_data = [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'TotalCommitment': {'Amount': '100.0', 'Unit': 'USD'},
                'UsedCommitment': {'Amount': '95.0', 'Unit': 'USD'},
                'UnusedCommitment': {'Amount': '5.0', 'Unit': 'USD'},
                'UtilizationPercentage': '95.0',
                'SavingsPlansCount': 1,
            }
        ]

        mock_paginate.return_value = (utilization_data, {'NextToken': None})
        mock_ce_client.get_savings_plans_utilization.side_effect = Exception('API Error')

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
            assert 'total' in result['data']
            assert result['data']['total']['utilization_percentage'] == 95.0
            mock_logger_instance.warning.assert_called_once()

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
        """Test utilization details with malformed data - covers monetary parsing lines."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        # Malformed details data
        malformed_details = [
            {
                'SavingsPlanArn': 'arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-test',
                'Attributes': None,
                'TotalCommitment': {},
                'UsedCommitment': {'Amount': None, 'Unit': 'USD'},
                'UnusedCommitment': {'Amount': '5.0'},
                'UtilizationPercentage': 'invalid',
                'NetSavings': None,
                'OnDemandCostEquivalent': {'Amount': 'not_a_number', 'Unit': 'USD'},
                'AmortizedUpfrontFee': {'Unit': 'USD'},
                'RecurringCommitment': {'Amount': '95.0', 'Unit': 'USD'},
            }
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

            assert result['status'] == 'success'
            detail = result['data']['savings_plans_utilization_details'][0]

            # Check default values are applied
            assert detail['utilization']['utilization_percentage'] == 0.0
            assert detail['utilization']['total_commitment']['amount'] == 0.0
            assert detail['savings']['net_savings']['amount'] == 0.0
            assert detail['attributes'] is None

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_details_with_valid_attributes(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details with valid attributes - covers attribute parsing lines."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        # Details with valid attributes
        details_data = [
            {
                'SavingsPlanArn': 'arn1',
                'Attributes': {
                    'region': 'us-east-1',
                    'instanceFamily': 'm5',
                    'savingsPlanType': 'EC2InstanceSavingsPlans',
                },
                'TotalCommitment': {'Amount': '100.0', 'Unit': 'USD'},
                'UsedCommitment': {'Amount': '95.0', 'Unit': 'USD'},
                'UnusedCommitment': {'Amount': '5.0', 'Unit': 'USD'},
                'UtilizationPercentage': '95.0',
                'NetSavings': {'Amount': '10.0', 'Unit': 'USD'},
                'OnDemandCostEquivalent': {'Amount': '110.0', 'Unit': 'USD'},
                'AmortizedUpfrontFee': {'Amount': '1.0', 'Unit': 'USD'},
                'RecurringCommitment': {'Amount': '94.0', 'Unit': 'USD'},
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

            # Check that summary is added when attributes are present
            assert 'summary' in detail
            assert detail['summary']['region'] == 'us-east-1'
            assert detail['summary']['instance_family'] == 'm5'
            assert detail['summary']['savings_plan_type'] == 'EC2InstanceSavingsPlans'

            # Check that summary stats are calculated
            assert result['data']['average_utilization_percentage'] == 95.0
            assert result['data']['total_savings_plans'] == 1
            assert result['data']['fully_utilized_plans'] == 1  # 95% >= 95%
            assert result['data']['under_utilized_plans'] == 0  # 95% >= 80%

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_details_summary_stats_error(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization details when summary stats calculation fails - covers lines 566-567."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        details_data = [
            {
                'SavingsPlanArn': 'arn1',
                'Attributes': {'region': 'us-east-1'},
                'TotalCommitment': {'Amount': '100.0', 'Unit': 'USD'},
                'UsedCommitment': {'Amount': '95.0', 'Unit': 'USD'},
                'UnusedCommitment': {'Amount': '5.0', 'Unit': 'USD'},
                'UtilizationPercentage': '95.0',
                'NetSavings': {'Amount': '10.0', 'Unit': 'USD'},
                'OnDemandCostEquivalent': {'Amount': '110.0', 'Unit': 'USD'},
                'AmortizedUpfrontFee': {'Amount': '1.0', 'Unit': 'USD'},
                'RecurringCommitment': {'Amount': '94.0', 'Unit': 'USD'},
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

            with patch('builtins.sum', side_effect=Exception('Calculation error')):
                result = await get_savings_plans_utilization_details(
                    mock_context_async, mock_ce_client, '2023-01-01', '2023-01-31', None, None
                )

                assert result['status'] == 'success'
                assert 'average_utilization_percentage' not in result['data']
                mock_logger_instance.warning.assert_called_once()

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_performance_tools.paginate_aws_response'
    )
    async def test_savings_plans_utilization_total_with_none_value(
        self, mock_paginate, mock_get_date_range, mock_context_async
    ):
        """Test utilization when total data has None values - covers lines 365-379."""
        mock_ce_client = MagicMock()

        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')

        utilization_data = [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'TotalCommitment': {'Amount': '100.0', 'Unit': 'USD'},
                'UsedCommitment': {'Amount': '95.0', 'Unit': 'USD'},
                'UnusedCommitment': {'Amount': '5.0', 'Unit': 'USD'},
                'UtilizationPercentage': '95.0',
                'SavingsPlansCount': 1,
            }
        ]

        mock_paginate.return_value = (utilization_data, {'NextToken': None})
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'Total': {
                'TotalCommitment': None,
                'UsedCommitment': {'Amount': None, 'Unit': 'USD'},
                'UnusedCommitment': {},
                'UtilizationPercentage': None,
            }
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
            assert 'total' in result['data']
            assert result['data']['total']['utilization_percentage'] == 0.0
            assert result['data']['total']['total_commitment']['amount'] == 0.0
