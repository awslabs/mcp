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

"""Unit tests for the budget_tools module.

These tests verify the functionality of the AWS Budgets API tools, including:
- Retrieving AWS budgets information across accounts
- Describing budget details including limits, alerts, and notifications
- Handling account ID resolution for multi-account scenarios
- Error handling for API exceptions and invalid inputs
- Formatting budget data for display and analysis
"""

import asyncio
import boto3
import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.budget_tools import (
    _describe_budget_by_name,
    budget_server,
    budgets,
    describe_budgets,
    format_budgets,
    get_aws_account_id,
)
from botocore.awsrequest import AWSResponse
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_budgets_client():
    """Create a mock Budgets boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.describe_budgets.return_value = {
        'Budgets': [
            {
                'BudgetName': 'Monthly EC2 Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '500.0',
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '350.0',
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '450.0',
                        'Unit': 'USD',
                    },
                },
                'CostFilters': {
                    'Service': ['Amazon Elastic Compute Cloud - Compute'],
                },
                'TimePeriod': {
                    'Start': datetime(2023, 1, 1),
                    'End': datetime(2023, 12, 31),
                },
            },
            {
                'BudgetName': 'S3 Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '100.0',
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '120.0',
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '150.0',
                        'Unit': 'USD',
                    },
                },
                'CostFilters': {
                    'Service': ['Amazon Simple Storage Service'],
                },
                'TimePeriod': {
                    'Start': datetime(2023, 1, 1),
                    'End': datetime(2023, 12, 31),
                },
            },
        ],
        'NextToken': None,
    }

    return mock_client


@pytest.fixture
def mock_sts_client():
    """Create a mock STS boto3 client."""
    mock_client = MagicMock()

    # Set up mock response for get_caller_identity
    mock_client.get_caller_identity.return_value = {
        'UserId': 'AIDAXXXXXXXXXXXXXXXXX',
        'Account': '123456789012',
        'Arn': 'arn:aws:iam::123456789012:user/test-user',
    }

    return mock_client


@pytest.mark.asyncio
class TestGetAwsAccountId:
    """Tests for get_aws_account_id function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_get_aws_account_id_success(
        self, mock_create_aws_client, mock_context, mock_sts_client
    ):
        """Test get_aws_account_id successfully retrieves account ID."""
        # Setup
        mock_create_aws_client.return_value = mock_sts_client

        # Execute
        account_id = await get_aws_account_id(mock_context)

        # Assert
        mock_create_aws_client.assert_called_once_with('sts')
        mock_context.info.assert_called_once()
        mock_sts_client.get_caller_identity.assert_called_once()
        assert account_id == '123456789012'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_get_aws_account_id_error(self, mock_create_aws_client, mock_context):
        """STS errors propagate unwrapped so handle_aws_error keeps the AWS error code."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}}, 'GetCallerIdentity'
        )
        mock_create_aws_client.return_value.get_caller_identity.side_effect = error

        # Execute and Assert
        with pytest.raises(ClientError) as excinfo:
            await get_aws_account_id(mock_context)

        assert excinfo.value is error


class TestFormatBudgets:
    """Tests for format_budgets function."""

    def test_format_budgets_basic_fields(self):
        """Test format_budgets correctly formats basic budget fields."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert len(result) == 1
        assert result[0]['budget_name'] == 'Test Budget'
        assert result[0]['budget_type'] == 'COST'
        assert result[0]['time_unit'] == 'MONTHLY'

    def test_format_budgets_with_limit(self):
        """Test format_budgets correctly formats budget limits."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '500.0',
                    'Unit': 'USD',
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'budget_limit' in result[0]
        assert result[0]['budget_limit']['amount'] == '500.0'
        assert result[0]['budget_limit']['unit'] == 'USD'
        assert result[0]['budget_limit']['formatted'] == '500.0 USD'

    def test_format_budgets_with_calculated_spend(self):
        """Test format_budgets correctly formats calculated spend."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '350.0',
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '450.0',
                        'Unit': 'USD',
                    },
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'calculated_spend' in result[0]
        assert result[0]['calculated_spend']['actual_spend']['amount'] == '350.0'
        assert result[0]['calculated_spend']['forecasted_spend']['amount'] == '450.0'

    def test_format_budgets_with_time_period(self):
        """Test format_budgets correctly formats time period."""
        # Setup
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'TimePeriod': {
                    'Start': start_date,
                    'End': end_date,
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'time_period' in result[0]
        assert result[0]['time_period']['start'] == '2023-01-01'
        assert result[0]['time_period']['end'] == '2023-12-31'

    def test_format_budgets_with_cost_filters(self):
        """Test format_budgets correctly formats cost filters."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'CostFilters': {
                    'Service': ['Amazon EC2', 'Amazon S3'],
                    'Region': ['us-east-1'],
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'cost_filters' in result[0]
        assert 'Service' in result[0]['cost_filters']
        assert 'Region' in result[0]['cost_filters']
        assert 'Amazon EC2' in result[0]['cost_filters']['Service']

    def test_format_budgets_with_filter_expression(self):
        """A budget scoped by FilterExpression keeps its filter, metric and billing view.

        Such a budget has no CostFilters, so dropping these fields made it look account-wide.
        """
        filter_expression = {
            'And': [
                {'CostCategories': {'Key': 'Team', 'Values': ['Analytics']}},
                {'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit', 'Refund']}}},
            ]
        }
        billing_view_arn = 'arn:aws:billing::123456789012:billingview/billing-group-210987654321'
        budgets_list = [
            {
                'BudgetName': 'Team Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'FilterExpression': filter_expression,
                'Metrics': ['NetUnblendedCost'],
                'BillingViewArn': billing_view_arn,
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['filter_expression'] == filter_expression
        assert result[0]['metrics'] == ['NetUnblendedCost']
        assert result[0]['billing_view_arn'] == billing_view_arn
        assert 'cost_filters' not in result[0]
        assert 'cost_types' not in result[0]

    def test_format_budgets_with_health_status(self):
        """An unhealthy budget says why, without the raw timestamp."""
        budgets_list = [
            {
                'BudgetName': 'View Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'HealthStatus': {
                    'Status': 'UNHEALTHY',
                    'StatusReason': 'BILLING_VIEW_NO_ACCESS',
                    'LastUpdatedTime': datetime(2026, 1, 15),
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['health_status'] == {
            'status': 'UNHEALTHY',
            'status_reason': 'BILLING_VIEW_NO_ACCESS',
        }

    def test_format_budgets_healthy_budget_has_no_status_reason(self):
        """A healthy budget has no StatusReason, so none is returned."""
        budgets_list = [
            {
                'BudgetName': 'View Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'HealthStatus': {'Status': 'HEALTHY', 'LastUpdatedTime': datetime(2026, 1, 15)},
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['health_status'] == {'status': 'HEALTHY'}

    def test_format_budgets_with_cost_types(self):
        """A budget using the deprecated CostFilters form keeps its CostTypes."""
        cost_types = {'IncludeCredit': False, 'IncludeRefund': False, 'UseAmortized': True}
        budgets_list = [
            {
                'BudgetName': 'Legacy Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'CostFilters': {'Service': ['Amazon Elastic Compute Cloud - Compute']},
                'CostTypes': cost_types,
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['cost_filters'] == {'Service': ['Amazon Elastic Compute Cloud - Compute']}
        assert result[0]['cost_types'] == cost_types
        assert 'filter_expression' not in result[0]
        assert 'metrics' not in result[0]

    def test_format_budgets_omits_empty_scope_fields(self):
        """Empty scope fields are left out, as an empty CostFilters already was.

        A regression guard: the old code emitted none of these except cost_filters.
        FilterExpression is not among them: an unfiltered budget has none, and a present but
        empty one is a filter the SDK could not read (TestFilterExpressionIncomplete).
        """
        budgets_list = [
            {
                'BudgetName': 'Account Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'CostFilters': {},
                'Metrics': [],
                'CostTypes': {},
                'BillingViewArn': '',
                'HealthStatus': {},
            }
        ]

        result = format_budgets(budgets_list)

        for key in (
            'cost_filters',
            'metrics',
            'cost_types',
            'billing_view_arn',
            'health_status',
        ):
            assert key not in result[0]

    def test_format_budgets_with_planned_budget_limits(self):
        """A planned budget returns its per-period limits, oldest first, keyed by UTC date.

        Without them a planned budget's budget_limit looked like a fixed limit.
        """
        budgets_list = [
            {
                'BudgetName': 'Planned Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '200.0', 'Unit': 'USD'},
                'PlannedBudgetLimits': {
                    # 2026-02-01 and 2026-01-01 00:00 UTC, out of order as a map may be.
                    '1769904000': {'Amount': '200.0', 'Unit': 'USD'},
                    '1767225600': {'Amount': '100.0', 'Unit': 'USD'},
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['planned_budget_limits'] == [
            {'period_start': '2026-01-01', 'amount': '100.0', 'unit': 'USD'},
            {'period_start': '2026-02-01', 'amount': '200.0', 'unit': 'USD'},
        ]
        assert result[0]['budget_limit']['amount'] == '200.0'

    def test_format_budgets_planned_limit_with_unparseable_key(self):
        """A key that is not epoch seconds, or an empty limit, is kept rather than dropped."""
        budgets_list = [
            {
                'BudgetName': 'Planned Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'PlannedBudgetLimits': {
                    'not-a-number': {'Amount': '5.0', 'Unit': 'USD'},
                    '1767225600': None,
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['planned_budget_limits'] == [
            {'period_start': '2026-01-01', 'amount': None, 'unit': None},
            {'period_start': 'not-a-number', 'amount': '5.0', 'unit': 'USD'},
        ]

    def test_format_budgets_with_auto_adjust(self):
        """An auto-adjusting budget says how its limit is recomputed and when it last was."""
        budgets_list = [
            {
                'BudgetName': 'Auto Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '150.0', 'Unit': 'USD'},
                'AutoAdjustData': {
                    'AutoAdjustType': 'HISTORICAL',
                    'HistoricalOptions': {
                        'BudgetAdjustmentPeriod': 6,
                        'LookBackAvailablePeriods': 4,
                    },
                    # boto3 returns a zone-aware local time; the output is UTC.
                    'LastAutoAdjustTime': datetime(
                        2026, 10, 3, 8, 30, tzinfo=timezone(timedelta(hours=-4))
                    ),
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['auto_adjust'] == {
            'auto_adjust_type': 'HISTORICAL',
            'budget_adjustment_period': 6,
            'look_back_available_periods': 4,
            'last_auto_adjust_time': '2026-10-03T12:30:00',
        }

    def test_format_budgets_auto_adjust_epoch_time(self):
        """An epoch-seconds LastAutoAdjustTime is returned as the same UTC string."""
        budgets_list = [
            {
                'BudgetName': 'Auto Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'AutoAdjustData': {
                    'AutoAdjustType': 'HISTORICAL',
                    'HistoricalOptions': {'BudgetAdjustmentPeriod': 3},
                    'LastAutoAdjustTime': 1791030600,
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['auto_adjust'] == {
            'auto_adjust_type': 'HISTORICAL',
            'budget_adjustment_period': 3,
            'last_auto_adjust_time': '2026-10-03T12:30:00',
        }

    def test_format_budgets_forecast_auto_adjust_without_history(self):
        """A FORECAST budget has no HistoricalOptions, so only the fields present are returned."""
        budgets_list = [
            {
                'BudgetName': 'Forecast Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'AutoAdjustData': {'AutoAdjustType': 'FORECAST'},
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['auto_adjust'] == {'auto_adjust_type': 'FORECAST'}

    def test_format_budgets_fixed_budget_has_no_plan_or_auto_adjust(self):
        """A fixed budget, or one with empty plan fields, gets neither field."""
        budgets_list = [
            {
                'BudgetName': 'Fixed Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '100.0', 'Unit': 'USD'},
            },
            {
                'BudgetName': 'Empty Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'PlannedBudgetLimits': {},
                'AutoAdjustData': {},
            },
        ]

        result = format_budgets(budgets_list)

        for budget in result:
            assert 'planned_budget_limits' not in budget
            assert 'auto_adjust' not in budget

    def test_format_budgets_status_exceeded(self):
        """Test format_budgets correctly calculates EXCEEDED status."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '100.0',
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '120.0',  # Exceeds limit
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '150.0',
                        'Unit': 'USD',
                    },
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'status' in result[0]
        assert result[0]['status'] == 'EXCEEDED'

    def test_format_budgets_status_forecasted_to_exceed(self):
        """Test format_budgets correctly calculates FORECASTED_TO_EXCEED status."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '100.0',
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '80.0',  # Under limit
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '120.0',  # But forecast exceeds limit
                        'Unit': 'USD',
                    },
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'status' in result[0]
        assert result[0]['status'] == 'FORECASTED_TO_EXCEED'

    def test_format_budgets_status_ok(self):
        """Test format_budgets correctly calculates OK status."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': '100.0',
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': '50.0',  # Under limit
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': '80.0',  # Forecast under limit
                        'Unit': 'USD',
                    },
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert 'status' in result[0]
        assert result[0]['status'] == 'OK'

    @pytest.mark.parametrize(
        'actual_amount,forecast_amount,budget_limit,expected_status',
        [
            ('50.0', '80.0', '100.0', 'OK'),  # Under budget
            ('100.0', '120.0', '100.0', 'EXCEEDED'),  # At limit, exceeded
            ('101.0', '150.0', '100.0', 'EXCEEDED'),  # Over budget
            ('80.0', '120.0', '100.0', 'FORECASTED_TO_EXCEED'),  # Under but forecast exceeds
            ('50.0', '100.0', '100.0', 'FORECASTED_TO_EXCEED'),  # Forecast at limit
        ],
    )
    def test_format_budgets_status_calculation(
        self, actual_amount, forecast_amount, budget_limit, expected_status
    ):
        """Test budget status calculation based on actual and forecasted spend."""
        # Setup
        budgets_list = [
            {
                'BudgetName': 'Test Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {
                    'Amount': budget_limit,
                    'Unit': 'USD',
                },
                'CalculatedSpend': {
                    'ActualSpend': {
                        'Amount': actual_amount,
                        'Unit': 'USD',
                    },
                    'ForecastedSpend': {
                        'Amount': forecast_amount,
                        'Unit': 'USD',
                    },
                },
            }
        ]

        # Execute
        result = format_budgets(budgets_list)

        # Assert
        assert isinstance(result, list), 'Result should be a list'
        assert len(result) == 1, 'Result should contain one budget'
        assert 'status' in result[0], 'Result should have a status field'
        assert result[0]['status'] == expected_status, (
            f'Budget with actual={actual_amount}, forecast={forecast_amount}, limit={budget_limit} should have status {expected_status}'
        )

    def test_format_budgets_status_usage_budget(self):
        """A USAGE budget gets a status, since more usage is worse, as it is for COST."""
        budgets_list = [
            {
                'BudgetName': 'Usage Budget',
                'BudgetType': 'USAGE',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '1000.0', 'Unit': 'GB'},
                'CalculatedSpend': {'ActualSpend': {'Amount': '1200.0', 'Unit': 'GB'}},
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['status'] == 'EXCEEDED'

    @pytest.mark.parametrize(
        'budget_type',
        [
            'RI_UTILIZATION',
            'RI_COVERAGE',
            'SAVINGS_PLANS_UTILIZATION',
            'SAVINGS_PLANS_COVERAGE',
        ],
    )
    @pytest.mark.parametrize('actual_amount', ['100.0', '20.0'])
    def test_format_budgets_no_status_for_utilization_and_coverage(
        self, budget_type, actual_amount
    ):
        """Utilization and coverage budgets get no status.

        Their limit is always 100 PERCENTAGE and a higher actual is better, so a
        spend-vs-limit status read 100% as EXCEEDED and 20% as OK.
        """
        budgets_list = [
            {
                'BudgetName': 'Commitment Budget',
                'BudgetType': budget_type,
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '100.0', 'Unit': 'PERCENTAGE'},
                'CalculatedSpend': {
                    'ActualSpend': {'Amount': actual_amount, 'Unit': 'PERCENTAGE'}
                },
            }
        ]

        result = format_budgets(budgets_list)

        assert 'status' not in result[0]
        assert result[0]['calculated_spend']['actual_spend']['amount'] == actual_amount
        assert result[0]['budget_limit']['amount'] == '100.0'

    def test_format_budgets_no_status_for_unknown_budget_type(self):
        """Status is derived only for known spend types, so a new budget type gets none."""
        budgets_list = [
            {
                'BudgetName': 'Future Budget',
                'BudgetType': 'SOME_FUTURE_TYPE',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '100.0', 'Unit': 'PERCENTAGE'},
                'CalculatedSpend': {'ActualSpend': {'Amount': '100.0', 'Unit': 'PERCENTAGE'}},
            }
        ]

        result = format_budgets(budgets_list)

        assert 'status' not in result[0]

    def test_format_budgets_status_ok_without_forecast(self):
        """A spend budget under its limit with no forecast is OK."""
        budgets_list = [
            {
                'BudgetName': 'Cost Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'BudgetLimit': {'Amount': '100.0', 'Unit': 'USD'},
                'CalculatedSpend': {'ActualSpend': {'Amount': '50.0', 'Unit': 'USD'}},
            }
        ]

        result = format_budgets(budgets_list)

        assert result[0]['status'] == 'OK'


@pytest.mark.asyncio
class TestDescribeBudgets:
    """Tests for describe_budgets function."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budgets_success(
        self, mock_create_aws_client, mock_context, mock_budgets_client
    ):
        """Test describe_budgets returns formatted budgets."""
        # Setup
        mock_create_aws_client.return_value = mock_budgets_client
        account_id = '123456789012'

        # Execute
        result = await describe_budgets(mock_context, account_id, None, 100)

        # Assert
        mock_create_aws_client.assert_called_once_with('budgets', region_name='us-east-1')
        mock_budgets_client.describe_budgets.assert_called_once_with(
            AccountId='123456789012', MaxResults=100
        )

        assert result['status'] == 'success'
        assert 'budgets' in result['data']
        assert len(result['data']['budgets']) == 2
        assert result['data']['pagination']['items_returned'] == 2
        assert result['data']['account_id'] == '123456789012'

        # Check budget details
        assert result['data']['budgets'][0]['budget_name'] == 'Monthly EC2 Budget'
        assert result['data']['budgets'][1]['budget_name'] == 'S3 Budget'

        # Check status calculation
        assert result['data']['budgets'][0]['status'] == 'OK'  # Under budget
        assert result['data']['budgets'][1]['status'] == 'EXCEEDED'  # Over budget

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budgets_with_name_filter(
        self, mock_create_aws_client, mock_context, mock_budgets_client
    ):
        """A budget name is read with DescribeBudget, so no page cut can hide it."""
        # Setup
        mock_create_aws_client.return_value = mock_budgets_client
        s3_budget = mock_budgets_client.describe_budgets.return_value['Budgets'][1]
        mock_budgets_client.describe_budget.return_value = {'Budget': s3_budget}
        account_id = '123456789012'
        budget_name = 'S3 Budget'

        # Execute
        result = await describe_budgets(mock_context, account_id, budget_name, 1)

        # Assert
        mock_budgets_client.describe_budget.assert_called_once_with(
            AccountId=account_id, BudgetName=budget_name
        )
        mock_budgets_client.describe_budgets.assert_not_called()
        assert result['status'] == 'success'
        assert len(result['data']['budgets']) == 1
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 1,
        }
        assert result['data']['budgets'][0]['budget_name'] == 'S3 Budget'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budget_by_name_keeps_filter_expression(
        self, mock_create_aws_client, mock_context, mock_budgets_client
    ):
        """The DescribeBudget path returns the budget's FilterExpression scope too."""
        mock_create_aws_client.return_value = mock_budgets_client
        filter_expression = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}
        mock_budgets_client.describe_budget.return_value = {
            'Budget': {
                'BudgetName': 'S3 Budget',
                'BudgetType': 'COST',
                'TimeUnit': 'MONTHLY',
                'FilterExpression': filter_expression,
                'Metrics': ['UnblendedCost'],
            }
        }

        result = await describe_budgets(mock_context, '123456789012', 'S3 Budget')

        budget = result['data']['budgets'][0]
        assert budget['filter_expression'] == filter_expression
        assert budget['metrics'] == ['UnblendedCost']

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budgets_unknown_name_returns_empty_list(
        self, mock_create_aws_client, mock_context
    ):
        """An unknown budget name is an empty result, not an error."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.describe_budget.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'not found'}}, 'DescribeBudget'
        )
        mock_create_aws_client.return_value = client

        result = await describe_budgets(mock_context, '123456789012', 'missing')

        assert result['status'] == 'success'
        assert result['data']['budgets'] == []
        assert result['data']['pagination']['complete_dataset'] is True

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budget_other_error_is_an_error(
        self, mock_create_aws_client, mock_context
    ):
        """A failure other than not-found is reported as an error."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.describe_budget.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}}, 'DescribeBudget'
        )
        mock_create_aws_client.return_value = client

        result = await describe_budgets(mock_context, '123456789012', 'b1')

        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budgets_with_pagination(
        self, mock_create_aws_client, mock_context, mock_budgets_client
    ):
        """Test describe_budgets handles pagination correctly."""
        # Setup
        mock_create_aws_client.return_value = mock_budgets_client
        account_id = '123456789012'

        # Set up multi-page response
        mock_budgets_client.describe_budgets.side_effect = [
            {
                'Budgets': [{'BudgetName': 'Budget1'}],
                'NextToken': 'page2token',
            },
            {
                'Budgets': [{'BudgetName': 'Budget2'}],
                'NextToken': None,
            },
        ]

        # Execute
        result = await describe_budgets(mock_context, account_id, None, 100)

        # Assert
        assert mock_budgets_client.describe_budgets.call_count == 2
        assert result['status'] == 'success'
        assert len(result['data']['budgets']) == 2

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.handle_aws_error')
    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_describe_budgets_error(
        self, mock_create_aws_client, mock_handle_aws_error, mock_context
    ):
        """Test describe_budgets error handling."""
        # Setup
        error = Exception('API error')
        mock_create_aws_client.side_effect = error
        mock_handle_aws_error.return_value = {'status': 'error', 'message': 'API error'}

        # Execute
        result = await describe_budgets(mock_context, '123456789012', None, 100)

        # Assert
        mock_handle_aws_error.assert_called_once_with(
            mock_context, error, 'describe_budgets', 'AWS Budgets'
        )
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


class _WireBody:
    """Raw HTTP body for botocore's AWSResponse."""

    def __init__(self, body: bytes):
        self._body = body

    def stream(self, **kwargs):
        yield self._body


class TestBudgetFilterExpressionParsing:
    """The installed botocore must parse every FilterExpression member the service returns.

    botocore silently drops a response member its service model does not define. Before
    botocore 1.43.110 the budgets model had no ProductAttributes, so a budget scoped by a
    product attribute came back with that filter node as an empty dict.

    Stubber would bypass the response parser, so these tests stub the HTTP send instead and let
    botocore parse the wire JSON.
    """

    @pytest.fixture(autouse=True)
    def _no_ambient_profile(self, monkeypatch):
        monkeypatch.delenv('AWS_PROFILE', raising=False)
        monkeypatch.delenv('AWS_DEFAULT_PROFILE', raising=False)

    FILTER_EXPRESSION = {
        'And': [
            {'ProductAttributes': {'Key': 'feature', 'Values': ['On-demand Inference']}},
            {'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit', 'Refund']}}},
        ]
    }

    def _client_returning(self, payload):
        """A real budgets client whose HTTP send returns ``payload`` as the wire response."""
        client = boto3.Session(
            aws_access_key_id='a', aws_secret_access_key='b', region_name='us-east-1'
        ).client('budgets')
        body = json.dumps(payload).encode()

        def send(request, **kwargs):
            return AWSResponse(request.url, 200, {}, _WireBody(body))

        client.meta.events.register('before-send.budgets', send)
        return client

    def _budget(self):
        return {
            'BudgetName': 'Feature Budget',
            'BudgetType': 'COST',
            'TimeUnit': 'MONTHLY',
            'FilterExpression': self.FILTER_EXPRESSION,
        }

    def test_describe_budget_keeps_product_attributes(self):
        """DescribeBudget (the budget_name path) keeps the ProductAttributes leaf."""
        client = self._client_returning({'Budget': self._budget()})

        result = _describe_budget_by_name(client, '123456789012', 'Feature Budget')

        assert result[0]['FilterExpression'] == self.FILTER_EXPRESSION

    def test_describe_budgets_keeps_product_attributes(self):
        """DescribeBudgets (the listing path) keeps the ProductAttributes leaf."""
        client = self._client_returning({'Budgets': [self._budget()]})

        response = client.describe_budgets(AccountId='123456789012')

        assert response['Budgets'][0]['FilterExpression'] == self.FILTER_EXPRESSION

    @pytest.mark.parametrize(
        'wire_filter, parsed_filter',
        [
            ({'FutureLeaf': {'Key': 'k'}}, {}),
            (
                {'And': [{'FutureLeaf': {}}, {'Tags': {'Key': 'team'}}]},
                {'And': [{}, {'Tags': {'Key': 'team'}}]},
            ),
            ({'Not': {'FutureLeaf': {}}}, {'Not': {}}),
        ],
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_unknown_filter_member_is_flagged_incomplete(
        self, mock_create_aws_client, mock_context, wire_filter, parsed_filter
    ):
        """A filter member this botocore does not know parses as {} and is flagged, not dropped.

        At the top level the parsed filter is falsy, so without the flag the budget read as
        unfiltered.
        """
        budget = {**self._budget(), 'FilterExpression': wire_filter}
        mock_create_aws_client.return_value = self._client_returning({'Budget': budget})

        result = await describe_budgets(mock_context, '123456789012', 'Feature Budget')

        formatted = result['data']['budgets'][0]
        assert formatted['filter_expression'] == parsed_filter
        assert formatted['filter_expression_incomplete'] is True
        assert 'could not be read' in formatted['filter_expression_note']


class TestFilterExpressionIncomplete:
    """format_budgets flags a filter with an unreadable node and leaves a readable one alone."""

    def _budget(self, filter_expression):
        return {
            'BudgetName': 'b',
            'BudgetType': 'COST',
            'TimeUnit': 'MONTHLY',
            'FilterExpression': filter_expression,
        }

    @pytest.mark.parametrize(
        'filter_expression',
        [
            {},
            {'And': [{}, {'Tags': {'Key': 'team', 'Values': ['a']}}]},
            {'Or': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['x']}}, None]},
            {'Not': {}},
            {'And': [{'Not': {}}, {'Tags': {'Key': 'team', 'Values': ['a']}}]},
        ],
    )
    def test_unreadable_node_is_flagged(self, filter_expression):
        """An empty or null node anywhere in the tree flags the filter as incomplete."""
        result = format_budgets([self._budget(filter_expression)])[0]

        assert result['filter_expression'] == filter_expression
        assert result['filter_expression_incomplete'] is True
        assert 'calculated_spend' in result['filter_expression_note']

    @pytest.mark.parametrize(
        'filter_expression',
        [
            {'Dimensions': {'Key': 'SERVICE', 'Values': []}},
            {
                'And': [
                    {'ProductAttributes': {'Key': 'model', 'Values': ['m']}},
                    {'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit']}}},
                ]
            },
            {'Or': [{'CostCategories': {'Key': 'c', 'Values': ['v']}}, {'Tags': {'Key': 't'}}]},
        ],
    )
    def test_readable_filter_is_not_flagged(self, filter_expression):
        """A filter whose every node has a member is returned without the flag."""
        result = format_budgets([self._budget(filter_expression)])[0]

        assert result['filter_expression'] == filter_expression
        assert 'filter_expression_incomplete' not in result
        assert 'filter_expression_note' not in result

    def test_budget_without_filter_has_no_filter_fields(self):
        """An unfiltered budget (the API omits FilterExpression) gets no filter field or note."""
        budget = {'BudgetName': 'b', 'BudgetType': 'COST', 'TimeUnit': 'MONTHLY'}

        result = format_budgets([budget])[0]

        for key in (
            'filter_expression',
            'filter_expression_incomplete',
            'filter_expression_note',
            'forecast_note',
        ):
            assert key not in result

    def test_product_attributes_and_unreadable_node_get_both_notes(self):
        """A filter with a ProductAttributes leaf and an unreadable node carries both notes."""
        filter_expression = {'And': [{'ProductAttributes': {'Key': 'model', 'Values': ['m']}}, {}]}

        result = format_budgets([self._budget(filter_expression)])[0]

        assert result['filter_expression_incomplete'] is True
        assert 'forecast_note' in result


class TestProductAttributesForecastNote:
    """COST and USAGE budgets filtered by product attributes get no forecast, and say so."""

    PA_LEAF = {'ProductAttributes': {'Key': 'feature', 'Values': ['On-demand Inference']}}

    def _budget(self, filter_expression, budget_type='COST', forecast=False):
        spend: Dict[str, Any] = {'ActualSpend': {'Amount': '10.0', 'Unit': 'USD'}}
        if forecast:
            spend['ForecastedSpend'] = {'Amount': '20.0', 'Unit': 'USD'}
        return {
            'BudgetName': 'b',
            'BudgetType': budget_type,
            'TimeUnit': 'MONTHLY',
            'BudgetLimit': {'Amount': '15.0', 'Unit': 'USD'},
            'CalculatedSpend': spend,
            'FilterExpression': filter_expression,
        }

    @pytest.mark.parametrize('budget_type', ['COST', 'USAGE'])
    @pytest.mark.parametrize(
        'filter_expression',
        [
            PA_LEAF,
            {
                'And': [
                    PA_LEAF,
                    {'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit']}}},
                ]
            },
            {'Or': [{'Tags': {'Key': 't', 'Values': ['a']}}, PA_LEAF]},
            {'Not': PA_LEAF},
        ],
    )
    def test_product_attribute_budget_gets_forecast_note(self, budget_type, filter_expression):
        """A ProductAttributes leaf at any depth adds the note; status stays from actual spend."""
        result = format_budgets([self._budget(filter_expression, budget_type)])[0]

        assert result['status'] == 'OK'
        assert 'forecasted_spend' not in result['calculated_spend']
        assert 'does not forecast' in result['forecast_note']
        assert 'FORECASTED_TO_EXCEED' in result['forecast_note']

    def test_product_attribute_budget_with_a_forecast_gets_no_note(self):
        """If a response ever carries a forecast, the note is left out so it cannot contradict status."""
        result = format_budgets([self._budget(self.PA_LEAF, forecast=True)])[0]

        assert result['status'] == 'FORECASTED_TO_EXCEED'
        assert 'forecast_note' not in result

    @pytest.mark.parametrize(
        'filter_expression, budget_type',
        [
            ({'Dimensions': {'Key': 'SERVICE', 'Values': ['x']}}, 'COST'),
            ({'Not': {'Tags': {'Key': 't', 'Values': ['a']}}}, 'USAGE'),
            (PA_LEAF, 'RI_UTILIZATION'),
        ],
    )
    def test_other_budgets_get_no_forecast_note(self, filter_expression, budget_type):
        """No ProductAttributes leaf, or a budget type without spend forecasts: no note."""
        result = format_budgets([self._budget(filter_expression, budget_type)])[0]

        assert 'forecast_note' not in result


def test_budget_server_initialization():
    """Test that the budget_server is properly initialized."""
    # Verify the server name
    assert budget_server.name == 'budget-tools'

    # Verify the server instructions
    instructions = budget_server.instructions
    assert instructions is not None
    assert 'Tools for working with AWS Budgets API' in instructions if instructions else False


def test_budgets_description_states_scope_and_health():
    """The description names every Expression member and what UNHEALTHY does to the spend."""
    tool = asyncio.run(budget_server.get_tool('budgets'))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert 'Dimensions, Tags, CostCategories and ProductAttributes' in description
    assert "means AWS has stopped updating the budget's spend" in description
    assert 'cannot read its billing view or filter' not in description


def test_budgets_description_states_product_attribute_and_incomplete_filter_gotchas():
    """The description says product-attribute budgets have no forecast and explains the flag."""
    tool = asyncio.run(budget_server.get_tool('budgets'))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert (
        'AWS does not forecast a COST or USAGE budget filtered by ProductAttributes' in description
    )
    assert 'its alerts can fire only on actual spend, not on a forecast' in description
    assert '`filter_expression_incomplete` is true' in description


# ---------------------------------------------------------------------------
# budget-actions + budget-notifications tools
# ---------------------------------------------------------------------------

from awslabs.billing_cost_management_mcp_server.tools.budget_tools import (  # noqa: E402
    budget_actions,
    budget_notifications,
    describe_budget_actions,
    describe_budget_notifications,
    format_action,
    format_notification,
)


class TestFormatAction:
    """Tests for format_action / format_action_definition."""

    def test_iam_action_verbatim_identifiers(self):
        """IAM action identifiers (policy ARN, execution role, roles) survive verbatim."""
        formatted = format_action(
            {
                'ActionId': 'a-1',
                'BudgetName': 'b1',
                'ActionType': 'APPLY_IAM_POLICY',
                'ApprovalModel': 'AUTOMATIC',
                'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/BudgetRole',
                'Status': 'STANDBY',
                'ActionThreshold': {
                    'ActionThresholdValue': 80.0,
                    'ActionThresholdType': 'PERCENTAGE',
                },
                'Definition': {
                    'IamActionDefinition': {
                        'PolicyArn': 'arn:aws:iam::123456789012:policy/DenyExpensive',
                        'Roles': ['dev-role'],
                        'Groups': ['dev-group'],
                        'Users': ['dev-user'],
                    }
                },
                'Subscribers': [
                    {'SubscriptionType': 'SNS', 'Address': 'arn:aws:sns:us-east-1:123456789012:t'}
                ],
            }
        )
        assert formatted['action_type'] == 'APPLY_IAM_POLICY'
        assert formatted['approval_model'] == 'AUTOMATIC'
        # Load-bearing identifiers must survive verbatim.
        assert formatted['execution_role_arn'] == 'arn:aws:iam::123456789012:role/BudgetRole'
        assert (
            formatted['definition']['iam_action_definition']['policy_arn']
            == 'arn:aws:iam::123456789012:policy/DenyExpensive'
        )
        assert formatted['definition']['iam_action_definition']['roles'] == ['dev-role']
        assert formatted['definition']['iam_action_definition']['groups'] == ['dev-group']
        assert formatted['definition']['iam_action_definition']['users'] == ['dev-user']
        assert formatted['action_threshold']['action_threshold_value'] == 80.0
        assert formatted['subscribers'][0]['address'].endswith(':t')

    def test_scp_and_ssm_definitions(self):
        """SCP and SSM action definitions map to their snake_case sub-objects."""
        scp = format_action(
            {'Definition': {'ScpActionDefinition': {'PolicyId': 'p-abc', 'TargetIds': ['ou-1']}}}
        )
        assert scp['definition']['scp_action_definition']['policy_id'] == 'p-abc'
        ssm = format_action(
            {
                'Definition': {
                    'SsmActionDefinition': {
                        'ActionSubType': 'STOP_EC2_INSTANCES',
                        'InstanceIds': ['i-abc'],
                        'Region': 'us-east-1',
                    }
                }
            }
        )
        assert (
            ssm['definition']['ssm_action_definition']['action_sub_type'] == 'STOP_EC2_INSTANCES'
        )


class TestFormatNotification:
    """Tests for format_notification."""

    def test_maps_fields(self):
        """Notification fields map to their snake_case equivalents."""
        n = format_notification(
            {
                'NotificationType': 'ACTUAL',
                'ComparisonOperator': 'GREATER_THAN',
                'Threshold': 80.0,
                'ThresholdType': 'PERCENTAGE',
                'NotificationState': 'ALARM',
            }
        )
        assert n == {
            'notification_type': 'ACTUAL',
            'comparison_operator': 'GREATER_THAN',
            'threshold': 80.0,
            'threshold_type': 'PERCENTAGE',
            'notification_state': 'ALARM',
        }


@pytest.mark.asyncio
class TestBudgetActionsTool:
    """The budget-actions tool — routes by budget_name (ForBudget vs ForAccount)."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_tool_resolves_account_and_audits(self, mock_create, mock_get_id, mock_context):
        """With no budget_name the tool resolves the account ID and audits account-wide."""
        mock_get_id.return_value = '123456789012'
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.return_value = {
            'Actions': [{'BudgetName': 'b1', 'ActionId': 'a1'}]
        }
        result = await budget_actions(mock_context)
        assert result['status'] == 'success'
        assert result['data']['actions'][0]['budget_name'] == 'b1'
        assert 'budget_name' not in result['data']
        client.describe_budget_actions_for_budget.assert_not_called()

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_audit_paginates_and_keeps_budget_name(self, mock_create, mock_context):
        """The account audit paginates and preserves each action's budget name."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.side_effect = [
            {'Actions': [{'BudgetName': 'b1', 'ActionId': 'a1'}], 'NextToken': 'tok'},
            {'Actions': [{'BudgetName': 'b2', 'ActionId': 'a2'}]},
        ]
        result = await describe_budget_actions(mock_context, '123456789012', None, 100)
        assert [a['budget_name'] for a in result['data']['actions']] == ['b1', 'b2']
        assert result['data']['pagination']['items_returned'] == 2
        assert client.describe_budget_actions_for_account.call_count == 2

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_single_budget_uses_per_budget_api(self, mock_create, mock_context):
        """Passing budget_name calls DescribeBudgetActionsForBudget, not the account API."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_budget.return_value = {
            'Actions': [{'BudgetName': 'b2', 'ActionId': 'a2'}]
        }
        result = await describe_budget_actions(mock_context, '123456789012', 'b2', 100)
        assert [a['budget_name'] for a in result['data']['actions']] == ['b2']
        assert result['data']['budget_name'] == 'b2'
        # Routed to the per-budget API with the name bound; account API untouched.
        client.describe_budget_actions_for_budget.assert_called()
        assert client.describe_budget_actions_for_budget.call_args.kwargs['BudgetName'] == 'b2'
        client.describe_budget_actions_for_account.assert_not_called()

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_empty_actions_is_success_not_error(self, mock_create, mock_context):
        """A budget with no actions returns an empty list, not an error."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.return_value = {'Actions': []}
        result = await describe_budget_actions(mock_context, '123456789012', None, 100)
        assert result['status'] == 'success'
        assert result['data']['actions'] == []

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_api_error_returns_error_envelope(self, mock_create, mock_context):
        """An API failure is surfaced as an error envelope, not a raised exception."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.side_effect = Exception('AccessDenied')
        result = await describe_budget_actions(mock_context, '123456789012', None, 100)
        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    async def test_entrypoint_error_is_handled(self, mock_get_id, mock_context):
        """A failure resolving the account ID is caught by the tool entrypoint."""
        mock_get_id.side_effect = Exception('sts down')
        result = await budget_actions(mock_context)
        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_next_token_is_passed_through(self, mock_create, mock_context):
        """A caller-supplied next_token is forwarded to the account API request."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.return_value = {'Actions': []}
        await describe_budget_actions(mock_context, '123456789012', None, 100, next_token='tok')
        assert client.describe_budget_actions_for_account.call_args.kwargs['NextToken'] == 'tok'

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch(
        'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
        return_value=True,
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_large_response_offloads_to_sql_rows(
        self, mock_create, _mock_should, mock_conn, mock_context
    ):
        """An oversized account audit offloads to SQL as one queryable row per action."""
        import sqlite3

        conn = sqlite3.connect(':memory:')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_info '
            '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
            'query TEXT, row_count INTEGER)'
        )
        mock_conn.return_value = (conn, conn.cursor())

        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_actions_for_account.return_value = {
            'Actions': [
                {'BudgetName': 'b1', 'ActionId': 'a1', 'Status': 'STANDBY'},
                {'BudgetName': 'b2', 'ActionId': 'a2', 'Status': 'PENDING'},
            ]
        }
        result = await describe_budget_actions(mock_context, '123456789012', None, 100)
        assert result['status'] == 'success'
        # Offloaded (not returned inline) as one row per action, with real columns.
        assert result['data']['data_stored'] is True
        assert result['data']['row_count'] == 2
        assert 'action_id' in result['data']['schema']


@pytest.mark.asyncio
class TestBudgetNotificationsTool:
    """The budget-notifications tool — routes by budget_name (per-budget vs account-wide)."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_no_budget_name_audits_account_wide(
        self, mock_create, mock_get_id, mock_context
    ):
        """With no budget_name the tool flattens DescribeBudgetNotificationsForAccount."""
        mock_get_id.return_value = '123456789012'
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_notifications_for_account.return_value = {
            'BudgetNotificationsForAccount': [
                {
                    'BudgetName': 'b1',
                    'Notifications': [{'NotificationType': 'ACTUAL', 'Threshold': 80.0}],
                },
                {
                    'BudgetName': 'b2',
                    'Notifications': [{'NotificationType': 'FORECASTED', 'Threshold': 100.0}],
                },
            ]
        }
        result = await budget_notifications(mock_context)
        assert result['status'] == 'success'
        assert result['data']['pagination']['items_returned'] == 2
        # Each flattened notification is stamped with its owning budget.
        assert {n['budget_name'] for n in result['data']['notifications']} == {'b1', 'b2'}
        client.describe_notifications_for_budget.assert_not_called()

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_returns_formatted_notifications(self, mock_create, mock_context):
        """Passing budget_name uses the per-budget API and stamps the budget name."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_notifications_for_budget.return_value = {
            'Notifications': [
                {'NotificationType': 'ACTUAL', 'Threshold': 80.0, 'ThresholdType': 'PERCENTAGE'}
            ]
        }
        result = await describe_budget_notifications(mock_context, '123456789012', 'b1', 100)
        assert result['status'] == 'success'
        assert result['data']['notifications'][0]['threshold'] == 80.0
        assert result['data']['notifications'][0]['budget_name'] == 'b1'
        assert result['data']['pagination']['items_returned'] == 1
        client.describe_budget_notifications_for_account.assert_not_called()

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_api_error_returns_error_envelope(self, mock_create, mock_context):
        """An API failure is surfaced as an error envelope, not a raised exception."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_budget_notifications_for_account.side_effect = Exception('AccessDenied')
        result = await describe_budget_notifications(mock_context, '123456789012', None, 100)
        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    async def test_entrypoint_error_is_handled(self, mock_get_id, mock_context):
        """A failure resolving the account ID is caught by the tool entrypoint."""
        mock_get_id.side_effect = Exception('sts down')
        result = await budget_notifications(mock_context)
        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client')
    async def test_next_token_is_passed_through(self, mock_create, mock_context):
        """A caller-supplied next_token is forwarded to the per-budget API request."""
        client = MagicMock()
        mock_create.return_value = client
        client.describe_notifications_for_budget.return_value = {'Notifications': []}
        await describe_budget_notifications(
            mock_context, '123456789012', 'b1', 100, next_token='tok'
        )
        assert client.describe_notifications_for_budget.call_args.kwargs['NextToken'] == 'tok'


# ---------------------------------------------------------------------------
# Pagination contract: max_items / next_token
# ---------------------------------------------------------------------------

PATCH_BUDGETS_CLIENT = (
    'awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client'
)
ACCOUNT = '123456789012'


def _budgets_page(count, token=None, start=0):
    page = {'Budgets': [{'BudgetName': f'b{i}'} for i in range(start, start + count)]}
    if token:
        page['NextToken'] = token
    return page


def _actions_page(count, token=None, start=0):
    page = {
        'Actions': [{'ActionId': f'a{i}', 'BudgetName': 'b'} for i in range(start, start + count)]
    }
    if token:
        page['NextToken'] = token
    return page


def _account_notifications_page(per_budget, token=None):
    """One DescribeBudgetNotificationsForAccount page: one entry per budget."""
    page = {
        'BudgetNotificationsForAccount': [
            {
                'BudgetName': f'b{i}',
                'Notifications': [
                    {'NotificationType': 'ACTUAL', 'Threshold': t} for t in range(n)
                ],
            }
            for i, n in enumerate(per_budget)
        ]
    }
    if token:
        page['NextToken'] = token
    return page


def _strip_paging(kwargs):
    return {k: v for k, v in kwargs.items() if k not in ('NextToken', 'MaxResults')}


@pytest.mark.asyncio
class TestBudgetsPaginationContract:
    """budgets / budget-actions / budget-notifications follow the max_items contract."""

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_budgets_without_max_items_fetches_every_page(self, mock_create, mock_context):
        """Short and empty pages with a token keep paging at MaxResults=1000."""
        client = MagicMock()
        client.describe_budgets.side_effect = [
            _budgets_page(2, token='t2'),
            _budgets_page(0, token='t3'),  # an empty page that still carries a token
            _budgets_page(1, start=2),
        ]
        mock_create.return_value = client

        result = await describe_budgets(mock_context, ACCOUNT, None)

        sizes = [c.kwargs['MaxResults'] for c in client.describe_budgets.call_args_list]
        assert sizes == [1000, 1000, 1000]
        assert len(result['data']['budgets']) == 3
        assert result['data']['pagination']['complete_dataset'] is True
        assert 'warning' not in result['data']

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_budgets_max_items_stops_with_service_token(self, mock_create, mock_context):
        """max_items asks for the remainder and returns the service token when it stops."""
        client = MagicMock()
        client.describe_budgets.side_effect = [
            _budgets_page(3, token='t2'),
            _budgets_page(2, token='t3', start=3),
        ]
        mock_create.return_value = client

        result = await describe_budgets(mock_context, ACCOUNT, None, max_items=5)

        sizes = [c.kwargs['MaxResults'] for c in client.describe_budgets.call_args_list]
        assert sizes == [5, 2]
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't3',
            'items_returned': 5,
        }

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_budgets_continuation_sends_caller_token(self, mock_create, mock_context):
        """A continuation starts from the caller's token with otherwise identical params."""
        client = MagicMock()
        client.describe_budgets.side_effect = [
            _budgets_page(1, token='t2'),
            _budgets_page(1, start=1),
        ]
        mock_create.return_value = client

        await describe_budgets(mock_context, ACCOUNT, None, next_token='caller-token')

        first, second = (c.kwargs for c in client.describe_budgets.call_args_list)
        assert first['NextToken'] == 'caller-token'
        assert second['NextToken'] == 't2'
        assert _strip_paging(first) == _strip_paging(second) == {'AccountId': ACCOUNT}

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    async def test_budgets_tool_entrypoint_error_is_handled(self, mock_get_id, mock_context):
        """A failure resolving the account ID is returned as an error, not raised."""
        mock_get_id.side_effect = Exception('sts down')

        result = await budgets(mock_context)

        mock_get_id.assert_awaited_once()
        assert result['status'] == 'error'

    @patch('awslabs.billing_cost_management_mcp_server.tools.budget_tools.get_aws_account_id')
    @patch(PATCH_BUDGETS_CLIENT)
    async def test_budgets_tool_resolves_account_and_forwards_paging(
        self, mock_create, mock_get_id, mock_context
    ):
        """The budgets tool resolves the account and passes max_items and next_token through."""
        mock_get_id.return_value = ACCOUNT
        client = MagicMock()
        client.describe_budgets.return_value = _budgets_page(2, token='t3')
        mock_create.return_value = client

        result = await budgets(mock_context, max_items=2, next_token='caller-token')

        client.describe_budgets.assert_called_once_with(
            AccountId=ACCOUNT, NextToken='caller-token', MaxResults=2
        )
        assert [b['budget_name'] for b in result['data']['budgets']] == ['b0', 'b1']
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't3'

    @pytest.mark.parametrize(
        'budget_name,method',
        [
            (None, 'describe_budget_actions_for_account'),
            ('b1', 'describe_budget_actions_for_budget'),
        ],
    )
    @patch(PATCH_BUDGETS_CLIENT)
    async def test_actions_contract(self, mock_create, mock_context, budget_name, method):
        """Both action APIs page fully without max_items, stop at it, and resend params."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            _actions_page(1, token='t2'),
            _actions_page(0, token='t3'),
            _actions_page(1, start=1),
        ]
        mock_create.return_value = client

        result = await describe_budget_actions(
            mock_context, ACCOUNT, budget_name, next_token='caller-token'
        )

        calls = [c.kwargs for c in getattr(client, method).call_args_list]
        assert [c['MaxResults'] for c in calls] == [100, 100, 100]
        assert [c['NextToken'] for c in calls] == ['caller-token', 't2', 't3']
        assert all(_strip_paging(c) == _strip_paging(calls[0]) for c in calls)
        assert result['data']['pagination']['items_returned'] == 2
        assert result['data']['pagination']['complete_dataset'] is True

        getattr(client, method).side_effect = [_actions_page(2, token='more')]
        result = await describe_budget_actions(mock_context, ACCOUNT, budget_name, max_items=2)
        assert getattr(client, method).call_args.kwargs['MaxResults'] == 2
        assert result['data']['pagination']['next_token'] == 'more'
        assert result['data']['complete_dataset'] is False

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_per_budget_notifications_contract(self, mock_create, mock_context):
        """DescribeNotificationsForBudget pages at 100 and resends the budget name."""
        client = MagicMock()
        client.describe_notifications_for_budget.side_effect = [
            {'Notifications': [{'NotificationType': 'ACTUAL'}], 'NextToken': 't2'},
            {'Notifications': [{'NotificationType': 'FORECASTED'}]},
        ]
        mock_create.return_value = client

        result = await describe_budget_notifications(
            mock_context, ACCOUNT, 'b1', next_token='caller-token'
        )

        calls = [c.kwargs for c in client.describe_notifications_for_budget.call_args_list]
        assert [c['NextToken'] for c in calls] == ['caller-token', 't2']
        assert [c['MaxResults'] for c in calls] == [100, 100]
        assert _strip_paging(calls[0]) == _strip_paging(calls[1])
        assert calls[0]['BudgetName'] == 'b1'
        assert result['data']['pagination']['items_returned'] == 2

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_account_notifications_count_notifications_not_budgets(
        self, mock_create, mock_context
    ):
        """Account-level pages count budgets, so MaxResults is the remainder over 10."""
        client = MagicMock()
        client.describe_budget_notifications_for_account.side_effect = [
            _account_notifications_page([10, 10, 5], token='t2'),
            _account_notifications_page([3], token='t3'),
            _account_notifications_page([3], token='t4'),
        ]
        mock_create.return_value = client

        result = await describe_budget_notifications(mock_context, ACCOUNT, None, max_items=40)

        calls = [c.kwargs for c in client.describe_budget_notifications_for_account.call_args_list]
        # 40 notifications fit 4 budgets of 10. After 25 and then 28, one more budget of up to
        # 10 still fits; after 31 it would not (31 + 10 > 40), so the call stops.
        assert [c['MaxResults'] for c in calls] == [4, 1, 1]
        assert len(result['data']['notifications']) == 31
        assert result['data']['pagination']['items_returned'] == 31
        assert result['data']['pagination']['next_token'] == 't4'
        assert result['data']['pagination']['has_more'] is True

    @patch(PATCH_BUDGETS_CLIENT)
    async def test_account_notifications_without_max_items_fetch_every_page(
        self, mock_create, mock_context
    ):
        """Without max_items every page is fetched at the 1000-budget page size."""
        client = MagicMock()
        client.describe_budget_notifications_for_account.side_effect = [
            _account_notifications_page([2], token='t2'),
            _account_notifications_page([1]),
        ]
        mock_create.return_value = client

        result = await describe_budget_notifications(mock_context, ACCOUNT, None)

        calls = [c.kwargs for c in client.describe_budget_notifications_for_account.call_args_list]
        assert [c['MaxResults'] for c in calls] == [1000, 1000]
        assert len(result['data']['notifications']) == 3
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_tool_schemas_follow_the_max_items_contract(self):
        """All three budget tools take max_items + next_token and no page parameters."""
        tools = {t.name: t for t in await budget_server.list_tools()}
        for name in ('budgets', 'budget-actions', 'budget-notifications'):
            params = set(tools[name].parameters['properties'])
            assert {'max_items', 'next_token'} <= params, name
            assert not {'max_results', 'max_pages'} & params, name


@pytest.mark.asyncio
async def test_budgets_description_names_zero_spend_traps_and_limit_fields():
    """The description warns that a filtered 0 can be a filter matching nothing.

    It also states the CostTypes credit and refund default and names the planned and
    auto-adjusting limit fields, which the old description left out.
    """
    tools = {t.name: t for t in await budget_server.list_tools()}
    description = ' '.join((tools['budgets'].description or '').split())

    for text in (
        'An `actual_spend` of 0 on a filtered budget does not prove there was no spend',
        'service codes such as `AmazonEC2`',
        '`Amazon Elastic Compute Cloud - Compute`',
        '`cost_filters` keys are combined with AND',
        'run the equivalent filter, metric and billing view with `cost-explorer`',
        'a tag value of `""` matches costs that have no value for that tag key',
        '`IncludeCredit` and `IncludeRefund` default to true',
        '`planned_budget_limits`',
        '`auto_adjust`',
        'when an RI or Savings Plans budget returns it',
        'past periods are included',
        'periods before the first one with cost are left out',
    ):
        assert text in description, text


@pytest.mark.asyncio
async def test_budgets_description_drops_disproved_claims():
    """Claims the service contradicts stay out of the description.

    A SERVICE_CODE filter fails in the budget's spend calculation, so it is not a fix for a
    service-code filter; planned limits include past periods; and an RI or Savings Plans budget
    in the filter-expression form returns no cost_types at all.
    """
    tools = {t.name: t for t in await budget_server.list_tools()}
    description = ' '.join((tools['budgets'].description or '').split())

    for text in (
        'service codes belong under',
        'current or future period',
        'it is always `IncludeSubscription`',
        'is how many had cost data',
    ):
        assert text not in description, text
