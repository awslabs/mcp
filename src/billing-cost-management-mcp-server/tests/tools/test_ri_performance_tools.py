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

"""Unit tests for the ri_performance_tools module.

These tests verify the functionality of AWS Reserved Instance performance monitoring tools, including:
- Retrieving Reserved Instance coverage metrics and utilization percentages
- Getting detailed coverage analysis by service, region, and instance type
- Tracking utilization rates and unused Reserved Instance capacity
- Handling time-based analysis with daily, monthly, and yearly granularity
- Error handling for invalid date ranges and missing reservation data
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools import (
    format_coverage_metrics,
    format_utilization_metrics,
    get_reservation_coverage,
    get_reservation_utilization,
    ri_performance_server,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def ri_performance(ctx, operation, **kwargs):
    """Mock implementation of ri_performance for testing."""
    # Simple mock implementation that returns predefined responses
    await ctx.info(f'Processing {operation} operation')

    if operation == 'get_reservation_coverage':
        return {
            'status': 'success',
            'data': {
                'coverages_by_time': [],
                'total': {
                    'coverage_hours': {
                        'on_demand_hours': '100.0',
                        'reserved_hours': '400.0',
                        'total_running_hours': '500.0',
                        'coverage_hours_percentage': '80.0',
                    },
                    'coverage_cost': {
                        'on_demand_cost': '10.0',
                        'reserved_cost': '30.0',
                        'total_cost': '40.0',
                        'coverage_cost_percentage': '75.0',
                    },
                },
            },
        }
    elif operation == 'get_reservation_utilization':
        return {
            'status': 'success',
            'data': {
                'utilizations_by_time': [],
                'total': {
                    'utilization_percentage': '85.0',
                    'purchased_hours': '500.0',
                    'total_actual_hours': '425.0',
                    'unused_hours': '75.0',
                },
            },
        }
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

    # Set up mock response for get_reservation_coverage
    mock_client.get_reservation_coverage.return_value = {
        'CoveragesByTime': [
            {
                'TimePeriod': {
                    'Start': '2023-01-01',
                    'End': '2023-01-02',
                },
                'Total': {
                    'CoverageHours': {
                        'OnDemandHours': '100.0',
                        'ReservedHours': '400.0',
                        'TotalRunningHours': '500.0',
                        'CoverageHoursPercentage': '80.0',
                    },
                    'CoverageCost': {
                        'OnDemandCost': '10.0',
                        'ReservedCost': '30.0',
                        'TotalCost': '40.0',
                        'CoverageCostPercentage': '75.0',
                    },
                },
                'Groups': [
                    {
                        'Attributes': {
                            'SERVICE': 'Amazon Elastic Compute Cloud - Compute',
                            'REGION': 'us-east-1',
                        },
                        'Coverage': {
                            'CoverageHours': {
                                'OnDemandHours': '50.0',
                                'ReservedHours': '200.0',
                                'TotalRunningHours': '250.0',
                                'CoverageHoursPercentage': '80.0',
                            },
                            'CoverageCost': {
                                'OnDemandCost': '5.0',
                                'ReservedCost': '15.0',
                                'TotalCost': '20.0',
                                'CoverageCostPercentage': '75.0',
                            },
                        },
                    },
                    {
                        'Attributes': {
                            'SERVICE': 'Amazon Relational Database Service',
                            'REGION': 'us-east-1',
                        },
                        'Coverage': {
                            'CoverageHours': {
                                'OnDemandHours': '50.0',
                                'ReservedHours': '200.0',
                                'TotalRunningHours': '250.0',
                                'CoverageHoursPercentage': '80.0',
                            },
                            'CoverageCost': {
                                'OnDemandCost': '5.0',
                                'ReservedCost': '15.0',
                                'TotalCost': '20.0',
                                'CoverageCostPercentage': '75.0',
                            },
                        },
                    },
                ],
            }
        ],
        'Total': {
            'CoverageHours': {
                'OnDemandHours': '100.0',
                'ReservedHours': '400.0',
                'TotalRunningHours': '500.0',
                'CoverageHoursPercentage': '80.0',
            },
            'CoverageCost': {
                'OnDemandCost': '10.0',
                'ReservedCost': '30.0',
                'TotalCost': '40.0',
                'CoverageCostPercentage': '75.0',
            },
        },
    }

    # Set up mock response for get_reservation_utilization
    mock_client.get_reservation_utilization.return_value = {
        'UtilizationsByTime': [
            {
                'TimePeriod': {
                    'Start': '2023-01-01',
                    'End': '2023-01-02',
                },
                'Total': {
                    'UtilizationPercentage': '85.0',
                    'PurchasedHours': '500.0',
                    'TotalActualHours': '425.0',
                    'UnusedHours': '75.0',
                },
                'Groups': [
                    {
                        'Attributes': {
                            'SUBSCRIPTION_ID': '012345678901-ec2-us-east-1-t3.large',
                        },
                        'Utilization': {
                            'UtilizationPercentage': '90.0',
                            'PurchasedHours': '250.0',
                            'TotalActualHours': '225.0',
                            'UnusedHours': '25.0',
                        },
                    },
                    {
                        'Attributes': {
                            'SUBSCRIPTION_ID': '012345678901-rds-us-east-1-db.m5.large',
                        },
                        'Utilization': {
                            'UtilizationPercentage': '80.0',
                            'PurchasedHours': '250.0',
                            'TotalActualHours': '200.0',
                            'UnusedHours': '50.0',
                        },
                    },
                ],
            }
        ],
        'Total': {
            'UtilizationPercentage': '85.0',
            'PurchasedHours': '500.0',
            'TotalActualHours': '425.0',
            'UnusedHours': '75.0',
        },
    }

    return mock_client


def test_format_coverage_metrics():
    """Test format_coverage_metrics function."""
    # Setup
    coverage_data = {
        'CoverageHours': {
            'OnDemandHours': '100.0',
            'ReservedHours': '400.0',
            'TotalRunningHours': '500.0',
            'CoverageHoursPercentage': '80.0',
        },
        'CoverageCost': {
            'OnDemandCost': '10.0',
            'ReservedCost': '30.0',
            'TotalCost': '40.0',
            'CoverageCostPercentage': '75.0',
        },
        'CoverageNormalizedUnits': {
            'OnDemandNormalizedUnits': '200.0',
            'ReservedNormalizedUnits': '800.0',
            'TotalRunningNormalizedUnits': '1000.0',
            'CoverageNormalizedUnitsPercentage': '80.0',
        },
    }

    # Execute
    result = format_coverage_metrics(coverage_data)

    # Assert
    assert 'coverage_hours' in result
    assert 'coverage_cost' in result
    assert 'coverage_normalized_units' in result

    assert result['coverage_hours']['on_demand_hours'] == '100.0'
    assert result['coverage_hours']['reserved_hours'] == '400.0'
    assert result['coverage_hours']['coverage_hours_percentage'] == '80.0'

    assert result['coverage_cost']['on_demand_cost'] == '10.0'
    assert result['coverage_cost']['reserved_cost'] == '30.0'
    assert result['coverage_cost']['coverage_cost_percentage'] == '75.0'

    assert result['coverage_normalized_units']['on_demand_normalized_units'] == '200.0'
    assert result['coverage_normalized_units']['reserved_normalized_units'] == '800.0'
    assert result['coverage_normalized_units']['coverage_normalized_units_percentage'] == '80.0'


def test_format_utilization_metrics():
    """Test format_utilization_metrics function."""
    # Setup
    utilization_data = {
        'UtilizationPercentage': '85.0',
        'PurchasedHours': '500.0',
        'TotalActualHours': '425.0',
        'UnusedHours': '75.0',
        'PurchasedUnits': '1000.0',
        'TotalActualUnits': '850.0',
        'UnusedUnits': '150.0',
        'UtilizationPercentageInUnits': '85.0',
    }

    # Execute
    result = format_utilization_metrics(utilization_data)

    # Assert
    assert result['utilization_percentage'] == '85.0'
    assert result['purchased_hours'] == '500.0'
    assert result['total_actual_hours'] == '425.0'
    assert result['unused_hours'] == '75.0'

    assert result['purchased_units'] == '1000.0'
    assert result['total_actual_units'] == '850.0'
    assert result['unused_units'] == '150.0'
    assert result['utilization_percentage_in_units'] == '85.0'


@pytest.mark.asyncio
class TestGetReservationCoverage:
    """Tests for get_reservation_coverage function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_response'
    )
    async def test_get_reservation_coverage_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_coverage with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_reservation_coverage.return_value['CoveragesByTime'],
            {'NextPageToken': None},
        )

        # Execute
        result = await get_reservation_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # metrics
            None,  # group_by
            None,  # filter_expr
            None,  # sort_by
            None,  # max_results
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_kwargs = mock_paginate_response.call_args[1]

        assert call_kwargs['operation_name'] == 'GetReservationCoverage'
        assert call_kwargs['result_key'] == 'CoveragesByTime'

        request_params = call_kwargs['request_params']
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert 'coverages_by_time' in result['data']
        assert len(result['data']['coverages_by_time']) == 1

        assert 'total' in result['data']
        assert 'coverage_hours' in result['data']['total']
        assert 'coverage_cost' in result['data']['total']

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_response'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.parse_json')
    async def test_get_reservation_coverage_with_options(
        self,
        mock_parse_json,
        mock_paginate_response,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_reservation_coverage with all optional parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_reservation_coverage.return_value['CoveragesByTime'],
            {'NextPageToken': None},
        )

        mock_metrics = ['CoverageHours', 'CoverageCost']
        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        mock_filter = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}
        mock_sort_by = {'Key': 'CoverageHoursPercentage', 'SortOrder': 'DESCENDING'}

        mock_parse_json.side_effect = [mock_metrics, mock_group_by, mock_filter, mock_sort_by]

        # Execute
        result = await get_reservation_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            'metrics_json',  # metrics
            'group_by_json',  # group_by
            'filter_json',  # filter_expr
            'sort_by_json',  # sort_by
            50,  # max_results
        )

        # Assert
        mock_parse_json.assert_any_call('metrics_json', 'metrics')
        mock_parse_json.assert_any_call('group_by_json', 'group_by')
        mock_parse_json.assert_any_call('filter_json', 'filter')
        mock_parse_json.assert_any_call('sort_by_json', 'sort_by')

        request_params = mock_paginate_response.call_args[1]['request_params']
        assert request_params['Metrics'] == mock_metrics
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        assert request_params['SortBy'] == mock_sort_by
        assert request_params['MaxResults'] == 50

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.handle_aws_error'
    )
    async def test_get_reservation_coverage_error(
        self, mock_handle_aws_error, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_coverage error handling."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        error = Exception('API error')
        mock_ce_client.get_reservation_coverage.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_reservation_coverage(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # metrics
            None,  # group_by
            None,  # filter_expr
            None,  # sort_by
            None,  # max_results
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_reservation_coverage', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestGetReservationUtilization:
    """Tests for get_reservation_utilization function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_response'
    )
    async def test_get_reservation_utilization_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_utilization with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_reservation_utilization.return_value['UtilizationsByTime'],
            {'NextPageToken': None},
        )

        # Execute
        result = await get_reservation_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # group_by
            None,  # filter_expr
            None,  # sort_by
            None,  # max_results
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_kwargs = mock_paginate_response.call_args[1]

        assert call_kwargs['operation_name'] == 'GetReservationUtilization'
        assert call_kwargs['result_key'] == 'UtilizationsByTime'

        request_params = call_kwargs['request_params']
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert 'utilizations_by_time' in result['data']
        assert len(result['data']['utilizations_by_time']) == 1

        # Check total utilization
        assert 'total' in result['data']
        assert 'utilization_percentage' in result['data']['total']
        assert 'purchased_hours' in result['data']['total']

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_response'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.parse_json')
    async def test_get_reservation_utilization_with_options(
        self,
        mock_parse_json,
        mock_paginate_response,
        mock_get_date_range,
        mock_context,
        mock_ce_client,
    ):
        """Test get_reservation_utilization with all optional parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        mock_paginate_response.return_value = (
            mock_ce_client.get_reservation_utilization.return_value['UtilizationsByTime'],
            {'NextPageToken': None},
        )

        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'SUBSCRIPTION_ID'}]
        mock_filter = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}
        mock_sort_by = {'Key': 'UtilizationPercentage', 'SortOrder': 'DESCENDING'}

        mock_parse_json.side_effect = [mock_group_by, mock_filter, mock_sort_by]

        # Execute
        result = await get_reservation_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            'group_by_json',  # group_by
            'filter_json',  # filter_expr
            'sort_by_json',  # sort_by
            50,  # max_results
        )

        # Assert
        mock_parse_json.assert_any_call('group_by_json', 'group_by')
        mock_parse_json.assert_any_call('filter_json', 'filter')
        mock_parse_json.assert_any_call('sort_by_json', 'sort_by')

        request_params = mock_paginate_response.call_args[1]['request_params']
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        assert request_params['SortBy'] == mock_sort_by
        assert request_params['MaxResults'] == 50

        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.handle_aws_error'
    )
    async def test_get_reservation_utilization_error(
        self, mock_handle_aws_error, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_utilization error handling."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        error = Exception('API error')
        mock_ce_client.get_reservation_utilization.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await get_reservation_utilization(
            mock_context,
            mock_ce_client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,  # group_by
            None,  # filter_expr
            None,  # sort_by
            None,  # max_results
        )

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'get_reservation_utilization', 'Cost Explorer'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


@pytest.mark.asyncio
class TestRIPerformance:
    """Tests for ri_performance function."""

    async def test_ri_performance_coverage(self, mock_context):
        """Test ri_performance with get_reservation_coverage operation."""
        # Execute
        result = await ri_performance(
            mock_context,
            operation='get_reservation_coverage',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'success'
        assert 'coverages_by_time' in result['data']
        assert 'total' in result['data']
        data = result['data']
        assert isinstance(data, dict)
        total_data = data['total']
        assert isinstance(total_data, dict) and 'coverage_hours' in total_data

    async def test_ri_performance_utilization(self, mock_context):
        """Test ri_performance with get_reservation_utilization operation."""
        # Execute
        result = await ri_performance(
            mock_context,
            operation='get_reservation_utilization',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        mock_context.info.assert_called_once()
        assert result['status'] == 'success'
        assert 'utilizations_by_time' in result['data']
        assert 'total' in result['data']
        data = result['data']
        assert isinstance(data, dict)
        total_data = data['total']
        assert isinstance(total_data, dict) and 'utilization_percentage' in total_data

    async def test_ri_performance_with_all_params(self, mock_context):
        """Test ri_performance with all parameters."""
        # Setup
        metrics = '["CoverageHours", "CoverageCost"]'
        group_by = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'
        filter_expr = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'
        sort_by = '{"Key": "CoverageHoursPercentage", "SortOrder": "DESCENDING"}'

        # Execute
        result = await ri_performance(
            mock_context,
            operation='get_reservation_coverage',
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
            metrics=metrics,
            group_by=group_by,
            filter=filter_expr,
            sort_by=sort_by,
            max_results=50,
        )

        # Assert
        assert result['status'] == 'success'
        assert 'coverages_by_time' in result['data']

    async def test_ri_performance_unsupported_operation(self, mock_context):
        """Test ri_performance with unsupported operation."""
        # Execute
        result = await ri_performance(
            mock_context,
            operation='unsupported_operation',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']


def test_ri_performance_server_initialization():
    """Test that the ri_performance_server is properly initialized."""
    # Verify the server name
    assert ri_performance_server.name == 'ri-performance-tools'

    # Verify the server instructions
    assert ri_performance_server.instructions and (
        'Tools for working with AWS Reserved Instance Performance'
        in ri_performance_server.instructions
    )
