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

"""Tests for the budget-performance-history tool (DescribeBudgetPerformanceHistory)."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.budget_tools import (
    budget_server,
    format_budget_period,
)
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from fastmcp.tools import FunctionTool
from unittest.mock import AsyncMock, MagicMock, patch


CLIENT_PATH = 'awslabs.billing_cost_management_mcp_server.tools.budget_tools.create_aws_client'
ACCOUNT_ID = '123456789012'


def _period(month: int, budgeted: str, actual=None):
    """One monthly period of 2026; month 12 ends on 2027-01-01."""
    end = datetime(2026 + month // 12, month % 12 + 1, 1, tzinfo=timezone.utc)
    entry = {
        'BudgetedAmount': {'Amount': budgeted, 'Unit': 'USD'},
        'TimePeriod': {'Start': datetime(2026, month, 1, tzinfo=timezone.utc), 'End': end},
    }
    if actual is not None:
        entry['ActualAmount'] = {'Amount': actual, 'Unit': 'USD'}
    return entry


def _history(periods, **extra):
    return {
        'BudgetPerformanceHistory': {
            'BudgetName': 'Monthly',
            'BudgetType': 'COST',
            'TimeUnit': 'MONTHLY',
            'BudgetedAndActualAmountsList': periods,
            **extra,
        }
    }


def _client_error(code: str, message: str) -> ClientError:
    return ClientError(
        {'Error': {'Code': code, 'Message': message}}, 'DescribeBudgetPerformanceHistory'
    )


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


async def _tool() -> FunctionTool:
    tool = await budget_server.get_tool('budget-performance-history')
    assert isinstance(tool, FunctionTool)
    return tool


async def _call(mock_context, client, **kwargs):
    tool = await _tool()
    kwargs.setdefault('account_id', ACCOUNT_ID)
    with patch(CLIENT_PATH, return_value=client):
        return await tool.fn(mock_context, **kwargs)


class TestBudgetPerformanceHistory:
    """The tool wraps DescribeBudgetPerformanceHistory."""

    async def test_returns_each_period(self, mock_context):
        """Each period carries its dates, budgeted amount and actual amount."""
        client = MagicMock()
        client.describe_budget_performance_history.return_value = _history(
            [_period(8, '100.0', '120.5'), _period(9, '150.0', '90.0')]
        )

        result = await _call(mock_context, client, budget_name='Monthly')

        client.describe_budget_performance_history.assert_called_once_with(
            AccountId=ACCOUNT_ID, BudgetName='Monthly', MaxResults=100
        )
        assert result['status'] == 'success'
        data = result['data']
        assert data['budget_name'] == 'Monthly'
        assert data['budget_type'] == 'COST'
        assert data['time_unit'] == 'MONTHLY'
        assert data['account_id'] == ACCOUNT_ID
        assert data['periods'] == [
            {
                'start': '2026-08-01',
                'end': '2026-09-01',
                'budgeted_amount': {'amount': '100.0', 'unit': 'USD'},
                'actual_amount': {'amount': '120.5', 'unit': 'USD'},
            },
            {
                'start': '2026-09-01',
                'end': '2026-10-01',
                'budgeted_amount': {'amount': '150.0', 'unit': 'USD'},
                'actual_amount': {'amount': '90.0', 'unit': 'USD'},
            },
        ]
        assert data['pagination']['complete_dataset'] is True

    async def test_period_without_actual_amount(self, mock_context):
        """A period with no actual amount returns actual_amount null."""
        client = MagicMock()
        client.describe_budget_performance_history.return_value = _history([_period(9, '150.0')])

        result = await _call(mock_context, client, budget_name='Monthly')

        assert result['data']['periods'][0]['actual_amount'] is None

    async def test_time_unit_missing_from_response(self, mock_context):
        """Current-form budgets (metrics or a filter expression) return no TimeUnit; time_unit is null."""
        client = MagicMock()
        history = _history([_period(9, '150.0', '1.0')])
        del history['BudgetPerformanceHistory']['TimeUnit']
        client.describe_budget_performance_history.return_value = history

        result = await _call(mock_context, client, budget_name='Monthly')

        assert result['data']['time_unit'] is None

    async def test_pages_until_no_token(self, mock_context):
        """Without max_items every page is fetched; budget fields come from the first page."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = [
            {**_history([_period(8, '100.0', '1.0')]), 'NextToken': 't2'},
            _history([_period(9, '100.0', '2.0')]),
        ]

        result = await _call(mock_context, client, budget_name='Monthly')

        second = client.describe_budget_performance_history.call_args_list[1].kwargs
        assert second == {
            'AccountId': ACCOUNT_ID,
            'BudgetName': 'Monthly',
            'MaxResults': 100,
            'NextToken': 't2',
        }
        assert [p['start'] for p in result['data']['periods']] == ['2026-08-01', '2026-09-01']
        assert result['data']['budget_name'] == 'Monthly'

    async def test_max_items_and_next_token(self, mock_context):
        """max_items sizes the page; a remaining token marks the result partial."""
        client = MagicMock()
        client.describe_budget_performance_history.return_value = {
            **_history([_period(9, '100.0', '2.0')]),
            'NextToken': 't3',
        }

        result = await _call(
            mock_context, client, budget_name='Monthly', max_items=1, next_token='t2'
        )

        client.describe_budget_performance_history.assert_called_once_with(
            AccountId=ACCOUNT_ID, BudgetName='Monthly', MaxResults=1, NextToken='t2'
        )
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't3'

    async def test_account_id_from_sts_when_omitted(self, mock_context):
        """The account ID is looked up when not given."""
        budgets_client = MagicMock()
        budgets_client.describe_budget_performance_history.return_value = _history([])
        sts_client = MagicMock()
        sts_client.get_caller_identity.return_value = {'Account': ACCOUNT_ID}
        tool = await _tool()

        with patch(
            CLIENT_PATH,
            side_effect=lambda service, **_: sts_client if service == 'sts' else budgets_client,
        ):
            result = await tool.fn(mock_context, budget_name='Monthly')

        assert result['status'] == 'success'
        assert result['data']['account_id'] == ACCOUNT_ID

    @pytest.mark.parametrize(
        'message',
        [
            # CUSTOM budgets; ANNUALLY budgets with history get the same text.
            'Budget history for Custom in account 123456789012 does not support custom '
            'time periods.',
            'Budget history for Annual in account 123456789012 does not support custom '
            'time periods.',
        ],
    )
    async def test_unsupported_time_unit_is_validation_error(self, mock_context, message):
        """CUSTOM (and ANNUALLY) budgets have no history: a clear validation_error."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = _client_error(
            'InvalidParameterException', message
        )

        result = await _call(mock_context, client, budget_name='Custom')

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        for text in ('DAILY', 'MONTHLY', 'QUARTERLY', 'CUSTOM', 'ANNUALLY'):
            assert text in result['message']
        assert result['data']['budget_name'] == 'Custom'

    async def test_annual_budget_without_history_is_validation_error(self, mock_context):
        """An ANNUALLY budget the API answers with no periods gets the same validation_error."""
        client = MagicMock()
        client.describe_budget_performance_history.return_value = _history([], TimeUnit='ANNUALLY')

        result = await _call(mock_context, client, budget_name='Annual')

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'ANNUALLY' in result['message']

    async def test_monthly_budget_without_periods_is_success(self, mock_context):
        """A MONTHLY budget with no periods is a success with an empty list."""
        client = MagicMock()
        client.describe_budget_performance_history.return_value = _history([])

        result = await _call(mock_context, client, budget_name='Monthly')

        assert result['status'] == 'success'
        assert result['data']['periods'] == []

    async def test_later_page_failure_keeps_earlier_periods(self, mock_context):
        """A failure after the first page returns the periods read so far, marked partial."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = [
            {**_history([_period(8, '100.0', '1.0')]), 'NextToken': 't2'},
            _client_error('ThrottlingException', 'Rate exceeded'),
        ]

        result = await _call(mock_context, client, budget_name='Monthly')

        assert result['status'] == 'success'
        assert len(result['data']['periods']) == 1
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't2'

    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """InvalidNextTokenException on the caller's token maps to invalid_next_token."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = _client_error(
            'InvalidNextTokenException', 'Unable to decode the next token.'
        )

        result = await _call(mock_context, client, budget_name='Monthly', next_token='stale')

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    async def test_other_invalid_parameter_stays_aws_error(self, mock_context):
        """Other InvalidParameterException errors keep the AWS code and message."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = _client_error(
            'InvalidParameterException', 'SPEND_LIMIT is not in the supported budget type set'
        )

        result = await _call(mock_context, client, budget_name='Odd')

        assert result['status'] == 'error'
        assert result['error_type'] == 'InvalidParameterException'

    async def test_unknown_budget_is_not_found(self, mock_context):
        """An unknown budget name comes back as NotFoundException."""
        client = MagicMock()
        client.describe_budget_performance_history.side_effect = _client_error(
            'NotFoundException', "Unable to get budget: Nope - the budget doesn't exist."
        )

        result = await _call(mock_context, client, budget_name='Nope')

        assert result['status'] == 'error'
        assert result['error_type'] == 'NotFoundException'

    @pytest.mark.parametrize('budget_name', ['', '   '])
    async def test_empty_budget_name_is_rejected(self, mock_context, budget_name):
        """An empty budget_name is refused before any AWS call."""
        client = MagicMock()

        result = await _call(mock_context, client, budget_name=budget_name)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        client.describe_budget_performance_history.assert_not_called()


async def test_description_documents_history_rules():
    """The served description states the supported time units, window and gotchas."""
    tool = await _tool()
    description = ' '.join((tool.description or '').split())

    for text in (
        'DescribeBudgetPerformanceHistory',
        'DAILY',
        'MONTHLY',
        'QUARTERLY',
        'CUSTOM',
        'ANNUALLY',
        'validation_error',
        '13',
        'end is exclusive',
        'the one containing today',
        'budgeted_amount',
        'null when the budget had none for it',
        'actual_amount',
        'Read-only',
        'History starts when the budget was created',
        "nothing in a budget's definition shows which",
    ):
        assert text in description, text
    # A new ANNUALLY budget is rejected like CUSTOM, and the service's TimeUnit omission does not
    # follow the budget's visible definition (checked live).
    for text in ('no history yet', 'null for budgets defined with metrics', 'usually still in'):
        assert text not in description, text
    assert tool.parameters['required'] == ['budget_name']


async def test_existing_budget_tools_unchanged():
    """The three existing budget tools are still served with their parameters."""
    for name in ('budgets', 'budget-actions', 'budget-notifications'):
        tool = await budget_server.get_tool(name)
        assert isinstance(tool, FunctionTool)
        assert set(tool.parameters['properties']) == {
            'budget_name',
            'account_id',
            'max_items',
            'next_token',
        }


class TestFormatBudgetPeriod:
    """format_budget_period renders boundaries as UTC dates."""

    def test_converts_aware_datetimes_to_utc(self):
        """Midnight UTC given in a UTC-8 zone still renders as the UTC date."""
        minus_eight = timezone(timedelta(hours=-8))
        period = format_budget_period(
            {
                'TimePeriod': {
                    'Start': datetime(2026, 8, 31, 16, tzinfo=minus_eight),
                    'End': datetime(2026, 9, 30, 16, tzinfo=minus_eight),
                }
            }
        )
        assert (period['start'], period['end']) == ('2026-09-01', '2026-10-01')

    def test_naive_datetimes_and_strings_pass_through(self):
        """A naive datetime is formatted as is, and a string is left unchanged."""
        period = format_budget_period(
            {'TimePeriod': {'Start': datetime(2026, 9, 1), 'End': '2026-10-01'}}
        )
        assert (period['start'], period['end']) == ('2026-09-01', '2026-10-01')
        assert period['budgeted_amount'] is None
        assert period['actual_amount'] is None
