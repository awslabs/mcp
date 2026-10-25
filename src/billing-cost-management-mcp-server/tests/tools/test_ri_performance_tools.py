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

import botocore.session
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools import (
    format_coverage_metrics,
    format_utilization_metrics,
    get_reservation_coverage,
    get_reservation_utilization,
    ri_performance_server,
)
from fastmcp import Context
from fastmcp.tools import FunctionTool
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch


PAGINATION_COMPLETE = {
    'complete_dataset': True,
    'has_more': False,
    'next_token': None,
    'items_returned': 1,
}


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
                            'SUBSCRIPTION_ID': '359809062',
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
                            'SUBSCRIPTION_ID': '359809070',
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


def _undeclared_members(value, shape, path='') -> list:
    """Paths in a mocked response that the botocore output shape does not declare."""
    if shape.type_name == 'structure' and isinstance(value, dict):
        found = []
        for key, item in value.items():
            if key not in shape.members:
                found.append(f'{path}.{key}')
            else:
                found += _undeclared_members(item, shape.members[key], f'{path}.{key}')
        return found
    if shape.type_name == 'list' and isinstance(value, list):
        return [
            p
            for i, item in enumerate(value)
            for p in _undeclared_members(item, shape.member, f'{path}[{i}]')
        ]
    if shape.type_name == 'map' and isinstance(value, dict):
        return [
            p
            for k, item in value.items()
            for p in _undeclared_members(item, shape.value, f'{path}[{k}]')
        ]
    return []


@pytest.mark.parametrize(
    'method,operation',
    [
        ('get_reservation_coverage', 'GetReservationCoverage'),
        ('get_reservation_utilization', 'GetReservationUtilization'),
    ],
)
def test_mock_ce_responses_only_use_botocore_output_members(mock_ce_client, method, operation):
    """Mocked Cost Explorer responses hold only members the real API can return."""
    output_shape = (
        botocore.session.get_session()
        .get_service_model('ce')
        .operation_model(operation)
        .output_shape
    )
    assert _undeclared_members(getattr(mock_ce_client, method).return_value, output_shape) == []


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

    # CoverageCost has only OnDemandCost; no always-null reserved/total/percentage keys.
    assert result['coverage_cost'] == {'on_demand_cost': '10.0'}

    assert result['coverage_normalized_units']['on_demand_normalized_units'] == '200.0'
    assert result['coverage_normalized_units']['reserved_normalized_units'] == '800.0'
    assert result['coverage_normalized_units']['coverage_normalized_units_percentage'] == '80.0'


def _full_utilization_data():
    """Return every field ReservationAggregates carries, as the API returns them.

    All seventeen are decimal strings. The nine monetary ones were previously
    dropped by the formatter, which left RI cost and savings invisible.
    """
    return {
        'UtilizationPercentage': '85.0',
        'PurchasedHours': '500.0',
        'TotalActualHours': '425.0',
        'UnusedHours': '75.0',
        'PurchasedUnits': '1000.0',
        'TotalActualUnits': '850.0',
        'UnusedUnits': '150.0',
        'UtilizationPercentageInUnits': '85.0',
        'AmortizedUpfrontFee': '0.0',
        'AmortizedRecurringFee': '0.580902',
        'TotalAmortizedFee': '0.580902',
        'NetRISavings': '0.194098',
        'TotalPotentialRISavings': '0.912345',
        'RealizedSavings': '0.194098',
        'UnrealizedSavings': '0.100000',
        'OnDemandCostOfRIHoursUsed': '0.775000',
        'RICostForUnusedHours': '0.087135',
    }


def test_format_utilization_metrics():
    """Test format_utilization_metrics function."""
    # Setup
    utilization_data = _full_utilization_data()

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


def test_format_utilization_metrics_surfaces_every_monetary_field():
    """No metric the API returns is discarded.

    Dropping these made RI cost invisible: the response reported how many
    reservation hours went unused without ever reporting what they cost.
    """
    result = format_utilization_metrics(_full_utilization_data())

    assert result['on_demand_cost_of_ri_hours_used'] == '0.775000'
    assert result['net_ri_savings'] == '0.194098'
    assert result['total_potential_ri_savings'] == '0.912345'
    assert result['amortized_upfront_fee'] == '0.0'
    assert result['amortized_recurring_fee'] == '0.580902'
    assert result['total_amortized_fee'] == '0.580902'
    assert result['ri_cost_for_unused_hours'] == '0.087135'
    assert result['realized_savings'] == '0.194098'
    assert result['unrealized_savings'] == '0.100000'


def test_format_utilization_metrics_preserves_decimal_strings():
    """Values are passed through unconverted so no precision is lost."""
    result = format_utilization_metrics(_full_utilization_data())

    assert isinstance(result['amortized_recurring_fee'], str)
    assert result['amortized_recurring_fee'] == '0.580902'


def test_format_utilization_metrics_omits_absent_metrics():
    """A metric the API did not return is omitted, never defaulted to zero.

    Reporting an absent fee as 0.0 would be indistinguishable from a real zero,
    letting "no data" be summarized as "no cost".
    """
    result = format_utilization_metrics(
        {
            'UtilizationPercentage': '100.0',
            'PurchasedHours': '24.0',
            'NetRISavings': '1.23',
        }
    )

    assert result == {
        'utilization_percentage': '100.0',
        'purchased_hours': '24.0',
        'net_ri_savings': '1.23',
    }


@pytest.mark.asyncio
class TestGetReservationCoverage:
    """Tests for get_reservation_coverage function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_items'
    )
    async def test_get_reservation_coverage_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_coverage with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        first_page = mock_ce_client.get_reservation_coverage.return_value
        mock_paginate_response.return_value = (
            first_page['CoveragesByTime'],
            [first_page],
            PAGINATION_COMPLETE,
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
            None,  # max_items
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_args = mock_paginate_response.call_args[0]

        assert call_args[1] == 'GetReservationCoverage'
        assert call_args[4].result_key == 'CoveragesByTime'

        request_params = call_args[3]
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert 'coverages_by_time' in result['data']
        assert len(result['data']['coverages_by_time']) == 1

        # Total comes from the first page: no extra request is made for it.
        mock_ce_client.get_reservation_coverage.assert_not_called()
        assert 'total' in result['data']
        assert 'coverage_hours' in result['data']['total']
        assert 'coverage_cost' in result['data']['total']

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_items'
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
        first_page = mock_ce_client.get_reservation_coverage.return_value
        mock_paginate_response.return_value = (
            first_page['CoveragesByTime'],
            [first_page],
            PAGINATION_COMPLETE,
        )

        mock_metrics = ['CoverageHours', 'CoverageCost']
        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'INSTANCE_TYPE'}]
        mock_filter = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute']}
        }
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
            50,  # max_items
        )

        # Assert
        mock_parse_json.assert_any_call('metrics_json', 'metrics')
        mock_parse_json.assert_any_call('group_by_json', 'group_by')
        mock_parse_json.assert_any_call('filter_json', 'filter')
        mock_parse_json.assert_any_call('sort_by_json', 'sort_by')

        request_params = mock_paginate_response.call_args[0][3]
        assert request_params['Metrics'] == mock_metrics
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        assert request_params['SortBy'] == mock_sort_by
        # Page size and token are the helper's to set; max_items goes to it.
        assert 'MaxResults' not in request_params
        assert mock_paginate_response.call_args[1] == {'max_items': 50, 'next_token': None}
        # Grouped requests page over groups.
        assert mock_paginate_response.call_args[0][4].page_size_param == 'MaxResults'
        # Granularity and GroupBy are mutually exclusive for GetReservationCoverage:
        # when GroupBy is set, Granularity must not be sent.
        assert 'Granularity' not in request_params

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
            None,  # max_items
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
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_items'
    )
    async def test_get_reservation_utilization_basic(
        self, mock_paginate_response, mock_get_date_range, mock_context, mock_ce_client
    ):
        """Test get_reservation_utilization with basic parameters."""
        # Setup
        mock_get_date_range.return_value = ('2023-01-01', '2023-01-31')
        first_page = mock_ce_client.get_reservation_utilization.return_value
        mock_paginate_response.return_value = (
            first_page['UtilizationsByTime'],
            [first_page],
            PAGINATION_COMPLETE,
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
            None,  # max_items
        )

        # Assert
        mock_get_date_range.assert_called_once_with('2023-01-01', '2023-01-31')
        mock_paginate_response.assert_called_once()
        call_args = mock_paginate_response.call_args[0]

        assert call_args[1] == 'GetReservationUtilization'
        assert call_args[4].result_key == 'UtilizationsByTime'

        request_params = call_args[3]
        assert request_params['TimePeriod']['Start'] == '2023-01-01'
        assert request_params['TimePeriod']['End'] == '2023-01-31'
        assert request_params['Granularity'] == 'DAILY'

        assert result['status'] == 'success'
        assert 'utilizations_by_time' in result['data']
        assert len(result['data']['utilizations_by_time']) == 1

        # Check total utilization: from the first page, with no extra request.
        mock_ce_client.get_reservation_utilization.assert_not_called()
        assert 'total' in result['data']
        assert 'utilization_percentage' in result['data']['total']
        assert 'purchased_hours' in result['data']['total']

    @patch('awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.get_date_range')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.paginate_aws_items'
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
        first_page = mock_ce_client.get_reservation_utilization.return_value
        mock_paginate_response.return_value = (
            first_page['UtilizationsByTime'],
            [first_page],
            PAGINATION_COMPLETE,
        )

        mock_group_by = [{'Type': 'DIMENSION', 'Key': 'SUBSCRIPTION_ID'}]
        mock_filter = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute']}
        }
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
            max_pages=2,
        )

        # Assert
        mock_parse_json.assert_any_call('group_by_json', 'group_by')
        mock_parse_json.assert_any_call('filter_json', 'filter')
        mock_parse_json.assert_any_call('sort_by_json', 'sort_by')

        request_params = mock_paginate_response.call_args[0][3]
        assert request_params['GroupBy'] == mock_group_by
        assert request_params['Filter'] == mock_filter
        assert request_params['SortBy'] == mock_sort_by
        # Page size and token are the helper's to set; max_pages goes to it.
        assert 'MaxResults' not in request_params
        assert mock_paginate_response.call_args[1] == {'next_token': None, 'max_pages': 2}
        # Grouped requests page over groups.
        assert mock_paginate_response.call_args[0][4].page_size_param == 'MaxResults'
        # Granularity and GroupBy are mutually exclusive for GetReservationUtilization:
        # when GroupBy is set, Granularity must not be sent.
        assert 'Granularity' not in request_params

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
            None,  # max_items
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
        group_by = '[{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"}]'
        filter_expr = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}'
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
            max_items=50,
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


GROUP_BY_SUBSCRIPTION = '[{"Type": "DIMENSION", "Key": "SUBSCRIPTION_ID"}]'
PERIOD = {'Start': '2023-01-01', 'End': '2023-01-31'}


def _grouped_page(key, metric, groups, token=None, total=None):
    """One page of a grouped RI response: a single period entry holding some groups.

    As in the API, a grouped page has no top-level Total; the period entry's Total sums only
    the groups on this page.
    """
    page = {
        key: [
            {
                'TimePeriod': PERIOD,
                'Groups': [{'Attributes': {'id': g}, metric: {}} for g in groups],
                'Total': total or {},
            }
        ]
    }
    if token:
        page['NextPageToken'] = token
    return page


async def _call_ri(
    function, client, ctx, group_by=None, max_items=None, next_token=None, max_pages=None
):
    if function is get_reservation_coverage:
        return await function(
            ctx,
            client,
            '2023-01-01',
            '2023-01-31',
            'DAILY',
            None,
            group_by,
            None,
            None,
            max_items,
            next_token,
            max_pages,
        )
    return await function(
        ctx,
        client,
        '2023-01-01',
        '2023-01-31',
        'DAILY',
        group_by,
        None,
        None,
        max_items,
        next_token,
        max_pages,
    )


# (function, boto3 method, result key, group metric key, page size sent without max_items)
RI_OPERATIONS = [
    (get_reservation_coverage, 'get_reservation_coverage', 'CoveragesByTime', 'Coverage', 10000),
    (
        get_reservation_utilization,
        'get_reservation_utilization',
        'UtilizationsByTime',
        'Utilization',
        500,
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('function,method,key,metric,page_size', RI_OPERATIONS)
class TestRIPerformancePagination:
    """The real pagination helper drives both grouped RI operations."""

    async def test_no_max_items_fetches_every_page_and_merges_the_period(
        self, mock_context, function, method, key, metric, page_size
    ):
        """Every page is fetched; the groups of the single period are gathered under one entry."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            _grouped_page(
                key, metric, ['a', 'b'], token='t1', total={'UtilizationPercentage': '1'}
            ),
            _grouped_page(key, metric, ['c'], total={'UtilizationPercentage': '2'}),
        ]

        result = await _call_ri(function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION)

        data = result['data']
        periods = data[
            'coverages_by_time' if function is get_reservation_coverage else 'utilizations_by_time'
        ]
        assert len(periods) == 1
        assert [g['attributes']['id'] for g in periods[0]['groups']] == ['a', 'b', 'c']
        assert 'complete_dataset' not in data
        # Items are groups, not periods.
        assert data['pagination']['items_returned'] == 3
        calls = getattr(client, method).call_args_list
        # Two pages only: Total is taken from page 1 rather than re-requested.
        assert len(calls) == 2
        assert calls[0].kwargs['MaxResults'] == page_size
        assert calls[1].kwargs['MaxResults'] == page_size
        assert calls[1].kwargs['NextPageToken'] == 't1'

    async def test_page_limit_stops_and_returns_the_token(
        self, mock_context, function, method, key, metric, page_size
    ):
        """max_items (coverage) or max_pages (utilization) stops and returns the token."""
        client = MagicMock()
        getattr(client, method).return_value = _grouped_page(key, metric, ['a', 'b'], token='more')
        limit = {'max_items': 2} if function is get_reservation_coverage else {'max_pages': 1}

        result = await _call_ri(
            function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION, **limit
        )

        data = result['data']
        assert data['complete_dataset'] is False
        assert data['pagination']['next_token'] == 'more'
        getattr(client, method).assert_called_once()
        sent = getattr(client, method).call_args.kwargs['MaxResults']
        # Utilization's token is bound to MaxResults, so its page size never shrinks.
        assert sent == (2 if function is get_reservation_coverage else 500)

    async def test_continuation_sends_caller_token_and_identical_params(
        self, mock_context, function, method, key, metric, page_size
    ):
        """A continuation repeats the first call's parameters plus the caller's token."""
        client = MagicMock()
        getattr(client, method).return_value = _grouped_page(key, metric, ['a'])

        await _call_ri(function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION)
        first = dict(getattr(client, method).call_args.kwargs)
        await _call_ri(
            function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION, next_token='caller'
        )
        second = dict(getattr(client, method).call_args.kwargs)

        assert second.pop('NextPageToken') == 'caller'
        assert second == first

    async def test_ungrouped_returns_every_period_in_one_call(
        self, mock_context, function, method, key, metric, page_size
    ):
        """Without GroupBy no page size is sent and the single response is complete."""
        client = MagicMock()
        getattr(client, method).return_value = {
            key: [{'TimePeriod': PERIOD, 'Groups': [], 'Total': {}}] * 3,
            'Total': {},
        }

        result = await _call_ri(function, client, mock_context)

        getattr(client, method).assert_called_once()
        assert 'MaxResults' not in getattr(client, method).call_args.kwargs
        assert result['data']['pagination']['complete_dataset'] is True


def _page_total(function, value):
    """A period Total in the API's shape for the operation."""
    if function is get_reservation_coverage:
        return {'CoverageHours': {'TotalRunningHours': value}}
    return {'UtilizationPercentage': value}


def _format_total(function, total):
    if function is get_reservation_coverage:
        return format_coverage_metrics(total)
    return format_utilization_metrics(total)


def _periods(function, data):
    return data[
        'coverages_by_time' if function is get_reservation_coverage else 'utilizations_by_time'
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize('function,method,key,metric,page_size', RI_OPERATIONS)
class TestRIPerformancePageTotals:
    """A grouped page's Total sums only that page's groups, so it is kept only for a whole query."""

    async def test_single_complete_page_keeps_the_period_total(
        self, mock_context, function, method, key, metric, page_size
    ):
        """When the whole query is one page, its Total covers every group of the period."""
        client = MagicMock()
        getattr(client, method).return_value = _grouped_page(
            key, metric, ['a', 'b'], total=_page_total(function, '7')
        )

        result = await _call_ri(function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION)

        period = _periods(function, result['data'])[0]
        assert period['total'] == _format_total(function, _page_total(function, '7'))

    async def test_multi_page_omits_the_page_total(
        self, mock_context, function, method, key, metric, page_size
    ):
        """Page 1's Total covers only page 1's groups, so a merged period reports no total."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            _grouped_page(key, metric, ['a', 'b'], token='t1', total=_page_total(function, '3')),
            _grouped_page(key, metric, ['c'], total=_page_total(function, '4')),
        ]

        result = await _call_ri(function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION)

        data = result['data']
        assert data['pagination']['complete_dataset'] is True
        period = _periods(function, data)[0]
        assert [g['attributes']['id'] for g in period['groups']] == ['a', 'b', 'c']
        assert 'total' not in period
        assert 'total' not in data

    async def test_partial_result_omits_the_page_total(
        self, mock_context, function, method, key, metric, page_size
    ):
        """A result cut short by max_items or max_pages covers only some of the groups."""
        client = MagicMock()
        getattr(client, method).return_value = _grouped_page(
            key, metric, ['a', 'b'], token='more', total=_page_total(function, '3')
        )
        limit = {'max_items': 2} if function is get_reservation_coverage else {'max_pages': 1}

        result = await _call_ri(
            function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION, **limit
        )

        data = result['data']
        assert data['complete_dataset'] is False
        assert 'total' not in _periods(function, data)[0]

    async def test_continuation_omits_the_page_total(
        self, mock_context, function, method, key, metric, page_size
    ):
        """The last page of a continuation is complete but holds only that page's groups."""
        client = MagicMock()
        getattr(client, method).return_value = _grouped_page(
            key, metric, ['c'], total=_page_total(function, '4')
        )

        result = await _call_ri(
            function, client, mock_context, group_by=GROUP_BY_SUBSCRIPTION, next_token='caller'
        )

        data = result['data']
        assert data['pagination']['complete_dataset'] is True
        assert 'total' not in _periods(function, data)[0]

    async def test_ungrouped_keeps_every_total(
        self, mock_context, function, method, key, metric, page_size
    ):
        """Without GroupBy the single response covers the whole query, so its Totals are kept."""
        client = MagicMock()
        getattr(client, method).return_value = {
            key: [{'TimePeriod': PERIOD, 'Groups': [], 'Total': _page_total(function, '5')}],
            'Total': _page_total(function, '5'),
        }

        result = await _call_ri(function, client, mock_context)

        data = result['data']
        expected = _format_total(function, _page_total(function, '5'))
        assert data['total'] == expected
        assert _periods(function, data)[0]['total'] == expected


@pytest.mark.asyncio
async def test_description_says_when_total_is_returned():
    """The description no longer claims that page 1's total covers the whole query."""
    tool = await ri_performance_server.get_tool('ri-performance')
    assert tool is not None
    description = tool.description or ''
    assert 'returned only when the whole query came back in one page' in description
    assert 'covers the whole query; it is not repeated' not in description


# GetReservationCoverage GroupBy keys per SERVICE filter value, as the service validates
# them (Service.coverageGroupByDims) and confirmed by live calls. The API reference and
# botocore list one flat set that includes INVOICING_ENTITY and OPERATING_SYSTEM, which no
# service accepts, and omits INSTANCE_TYPE_FAMILY.
COVERAGE_GROUP_BY_BY_SERVICE = {
    'Amazon Elastic Compute Cloud - Compute': {
        'AZ',
        'INSTANCE_TYPE',
        'INSTANCE_TYPE_FAMILY',
        'LINKED_ACCOUNT',
        'PLATFORM',
        'REGION',
        'TENANCY',
    },
    'Amazon Relational Database Service': {
        'AZ',
        'INSTANCE_TYPE',
        'LINKED_ACCOUNT',
        'DATABASE_ENGINE',
        'REGION',
        'DEPLOYMENT_OPTION',
    },
    'Amazon ElastiCache': {'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'CACHE_ENGINE', 'REGION'},
    'Amazon MemoryDB': {'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'CACHE_ENGINE', 'REGION'},
    'Amazon Redshift': {'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'REGION'},
    'Amazon OpenSearch Service': {'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'REGION'},
    'Amazon Elasticsearch Service': {'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT', 'REGION'},
}


async def _ri_description() -> str:
    tool = await ri_performance_server.get_tool('ri-performance')
    assert tool is not None
    return tool.description or ''


# The "<scope> only" suffixes the coverage attribute list uses, and the services each names.
COVERAGE_SCOPES = {
    'EC2': {'Amazon Elastic Compute Cloud - Compute'},
    'RDS': {'Amazon Relational Database Service'},
    'ElastiCache and MemoryDB': {'Amazon ElastiCache', 'Amazon MemoryDB'},
}


def _documented_coverage_group_by(description: str) -> Dict[str, set]:
    """Per service, the coverage attributes documented for it ("<scope> only" or every service)."""
    block = description.split('GROUPING get_reservation_coverage (group_by):', 1)[1]
    documented: Dict[str, set] = {service: set() for service in COVERAGE_GROUP_BY_BY_SERVICE}
    for line in block.split('\n\n', 1)[0].splitlines():
        match = re.match(r'- ([A-Z_]+): .*?(?:\. ([A-Za-z0-9 ]+) only)?$', line)
        if match:
            key, scope = match.groups()
            for service in COVERAGE_SCOPES[scope] if scope else documented:
                documented[service].add(key)
    return documented


@pytest.mark.asyncio
async def test_description_lists_coverage_group_by_keys_per_service():
    """Each service's documented coverage group_by keys equal the keys the service accepts."""
    assert _documented_coverage_group_by(await _ri_description()) == COVERAGE_GROUP_BY_BY_SERVICE


@pytest.mark.asyncio
async def test_description_names_keys_no_service_accepts_for_coverage():
    """SERVICE, INVOICING_ENTITY and OPERATING_SYSTEM are called out as invalid for every service."""
    description = ' '.join((await _ri_description()).split())
    assert (
        'SERVICE, INVOICING_ENTITY and OPERATING_SYSTEM are NOT valid group_by attributes here'
        in description
    )
    assert 'call once per service to compare across services' in description


@pytest.mark.asyncio
async def test_description_states_subscription_id_format_and_error():
    """SubscriptionId is digits only; an ARN or UUID is rejected, not silently unmatched."""
    description = ' '.join((await _ri_description()).split())
    assert 'GetReservationUtilization groups ONLY by SUBSCRIPTION_ID' in description
    assert 'is a NUMERIC id' in description
    assert 'must contain only digits' in description
    assert 'returns no match' not in description
    # Utilization accepts several SERVICE values; only coverage caps them at 2.
    assert 'SERVICE filter takes a single value' not in description


@pytest.mark.asyncio
async def test_ungrouped_utilization_ignores_max_items_and_next_token(mock_context):
    """GetReservationUtilization rejects any token without GroupBy, so none is sent."""
    client = MagicMock()
    client.get_reservation_utilization.return_value = {'UtilizationsByTime': []}

    await _call_ri(
        get_reservation_utilization, client, mock_context, max_items=1, next_token='stale'
    )

    assert 'NextPageToken' not in client.get_reservation_utilization.call_args.kwargs


async def _call_tool(client, ctx, **kwargs):
    """Call the registered ri-performance tool with a mocked Cost Explorer client."""
    tool = await ri_performance_server.get_tool('ri-performance')
    assert isinstance(tool, FunctionTool)
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.ri_performance_tools.create_aws_client',
        return_value=client,
    ):
        return await tool.fn(ctx, start_date='2023-01-01', end_date='2023-01-31', **kwargs)


@pytest.mark.asyncio
class TestReservationCoverageRequest:
    """GetReservationCoverage request construction reaches the Cost Explorer client intact."""

    async def test_grouped_coverage_omits_granularity_from_api_call(self, mock_context):
        """Cost Explorer rejects Granularity with GroupBy, so it is never sent."""
        client = MagicMock()
        client.get_reservation_coverage.return_value = {'CoveragesByTime': []}

        await _call_tool(
            client,
            mock_context,
            operation='get_reservation_coverage',
            granularity='MONTHLY',
            group_by='[{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"}]',
        )

        kwargs = client.get_reservation_coverage.call_args.kwargs
        assert kwargs['GroupBy'] == [{'Type': 'DIMENSION', 'Key': 'INSTANCE_TYPE'}]
        assert 'Granularity' not in kwargs

    async def test_ungrouped_coverage_sends_granularity_to_api_call(self, mock_context):
        """Without GroupBy, the requested granularity remains part of the API call."""
        client = MagicMock()
        client.get_reservation_coverage.return_value = {'CoveragesByTime': []}

        await _call_tool(
            client,
            mock_context,
            operation='get_reservation_coverage',
            granularity='MONTHLY',
        )

        kwargs = client.get_reservation_coverage.call_args.kwargs
        assert 'GroupBy' not in kwargs
        assert kwargs['Granularity'] == 'MONTHLY'


@pytest.mark.asyncio
class TestMaxPages:
    """get_reservation_utilization takes max_pages; coverage keeps max_items."""

    async def test_grouped_utilization_max_pages_fetches_whole_pages(self, mock_context):
        """max_pages=2 makes two calls at MaxResults=500 and returns the token from page 2."""
        client = MagicMock()
        key, metric = 'UtilizationsByTime', 'Utilization'
        client.get_reservation_utilization.side_effect = [
            _grouped_page(key, metric, [f'a{n}' for n in range(500)], token='t1'),
            _grouped_page(key, metric, [f'b{n}' for n in range(500)], token='t2'),
            _grouped_page(key, metric, ['c']),
        ]

        result = await _call_tool(
            client,
            mock_context,
            operation='get_reservation_utilization',
            group_by=GROUP_BY_SUBSCRIPTION,
            max_pages=2,
        )

        calls = client.get_reservation_utilization.call_args_list
        assert [call.kwargs['MaxResults'] for call in calls] == [500, 500]
        assert 'NextPageToken' not in calls[0].kwargs
        assert calls[1].kwargs['NextPageToken'] == 't1'
        data = result['data']
        assert data['pagination']['next_token'] == 't2'
        assert data['pagination']['items_returned'] == 1000
        assert data['complete_dataset'] is False
        assert 'Call again with a larger max_pages' in data['warning']

    async def test_grouped_utilization_rejects_max_items(self, mock_context):
        """max_items on grouped utilization is a validation error and no call is made."""
        client = MagicMock()

        result = await _call_tool(
            client,
            mock_context,
            operation='get_reservation_utilization',
            group_by=GROUP_BY_SUBSCRIPTION,
            max_items=10,
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['message'] == (
            'get_reservation_utilization pages in fixed pages of 500 groups: use max_pages '
            'instead of max_items.'
        )
        client.get_reservation_utilization.assert_not_called()

    async def test_coverage_rejects_max_pages(self, mock_context):
        """max_pages on coverage is a validation error and no call is made."""
        client = MagicMock()

        result = await _call_tool(
            client,
            mock_context,
            operation='get_reservation_coverage',
            group_by='[{"Type": "DIMENSION", "Key": "REGION"}]',
            max_pages=1,
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['message'] == (
            'max_pages applies only to get_reservation_utilization; use max_items.'
        )
        client.get_reservation_coverage.assert_not_called()

    async def test_ungrouped_utilization_ignores_max_pages(self, mock_context):
        """Without GroupBy everything comes in one response, so max_pages is ignored."""
        client = MagicMock()
        client.get_reservation_utilization.return_value = {'UtilizationsByTime': []}

        result = await _call_tool(
            client,
            mock_context,
            operation='get_reservation_utilization',
            max_pages=1,
            next_token='stale',
        )

        assert result['status'] == 'success'
        kwargs = client.get_reservation_utilization.call_args.kwargs
        assert 'NextPageToken' not in kwargs
        assert 'MaxResults' not in kwargs

    async def test_description_names_max_pages(self):
        """The tool description and schema tell the agent to use max_pages for utilization."""
        tool = await ri_performance_server.get_tool('ri-performance')
        assert tool is not None
        assert 'max_pages' in tool.parameters['properties']
        description = tool.description or ''
        assert 'get_reservation_utilization takes max_pages (pages of 500 groups)' in description
        assert 'rounded up' not in description
