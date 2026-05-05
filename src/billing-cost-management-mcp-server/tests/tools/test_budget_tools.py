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

import pytest
from awslabs.billing_cost_management_mcp_server.tools.budget_tools import (
    budget_server,
    describe_budgets,
    format_budgets,
    get_aws_account_id,
)
from datetime import datetime
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
        """Test get_aws_account_id handles errors properly."""
        # Setup
        error = Exception('Failed to get caller identity')
        mock_create_aws_client.side_effect = error

        # Execute and Assert
        with pytest.raises(Exception) as excinfo:
            await get_aws_account_id(mock_context)

        assert 'Failed to retrieve AWS account ID' in str(excinfo.value)
        assert str(error) in str(excinfo.value)


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
        assert result['data']['total_count'] == 2
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
        """Test describe_budgets filters by budget name."""
        # Setup
        mock_create_aws_client.return_value = mock_budgets_client
        account_id = '123456789012'
        budget_name = 'S3 Budget'

        # Execute
        result = await describe_budgets(mock_context, account_id, budget_name, 100)

        # Assert
        assert result['status'] == 'success'
        assert len(result['data']['budgets']) == 1
        assert result['data']['total_count'] == 1
        assert result['data']['budgets'][0]['budget_name'] == 'S3 Budget'

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


def test_budget_server_initialization():
    """Test that the budget_server is properly initialized."""
    # Verify the server name
    assert budget_server.name == 'budget-tools'

    # Verify the server instructions
    instructions = budget_server.instructions
    assert instructions is not None
    assert 'Tools for working with AWS Budgets API' in instructions if instructions else False
