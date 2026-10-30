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

"""An empty filter expression is rejected by every operation that takes one, never dropped."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import (
    cost_comparison_tools,
    cost_explorer_operations,
    free_tier_usage_tools,
    ri_performance_tools,
    sp_performance_tools,
    sp_recommendation_tools,
)
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


MONTH = {'start_date': '2026-09-01', 'end_date': '2026-10-01'}
COMPARISON = {
    'baseline_start_date': '2026-08-01',
    'baseline_end_date': '2026-09-01',
    'comparison_start_date': '2026-09-01',
    'comparison_end_date': '2026-10-01',
    'metric_for_comparison': 'UnblendedCost',
    'group_by': None,
    'max_items': None,
    'next_token': None,
    'billing_view_arn': None,
}

# Every call site that sends a filter Expression, with the arguments it needs besides the filter.
OPERATIONS = [
    (cost_explorer_operations.get_cost_and_usage, MONTH),
    (cost_explorer_operations.get_cost_and_usage_with_resources, MONTH),
    (cost_explorer_operations.get_dimension_values, {'dimension': 'SERVICE', **MONTH}),
    (cost_explorer_operations.get_cost_forecast, {'metric': 'UNBLENDED_COST'}),
    (cost_explorer_operations.get_usage_forecast, {'metric': 'USAGE_QUANTITY'}),
    (cost_explorer_operations.get_savings_plans_utilization, MONTH),
    (cost_comparison_tools.get_cost_and_usage_comparisons, COMPARISON),
    (cost_comparison_tools.get_cost_comparison_drivers, COMPARISON),
    (
        sp_performance_tools.get_savings_plans_coverage,
        {**MONTH, 'granularity': 'MONTHLY', 'metrics': None, 'group_by': None},
    ),
    (sp_performance_tools.get_savings_plans_utilization, {**MONTH, 'granularity': 'MONTHLY'}),
    (sp_performance_tools.get_savings_plans_utilization_details, MONTH),
    (
        ri_performance_tools.get_reservation_coverage,
        {**MONTH, 'granularity': 'MONTHLY', 'metrics': None, 'group_by': None, 'sort_by': None},
    ),
    (
        ri_performance_tools.get_reservation_utilization,
        {**MONTH, 'granularity': 'MONTHLY', 'group_by': None, 'sort_by': None},
    ),
    (free_tier_usage_tools.get_free_tier_usage_data, {}),
    (
        sp_recommendation_tools.get_savings_plans_purchase_recommendation,
        {
            'savings_plans_type': 'COMPUTE_SP',
            'term_in_years': 'ONE_YEAR',
            'payment_option': 'NO_UPFRONT',
            'lookback_period_in_days': 'THIRTY_DAYS',
            'account_scope': None,
            'max_items': None,
            'next_token': None,
        },
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('operation, kwargs', OPERATIONS, ids=lambda v: getattr(v, '__name__', ''))
@pytest.mark.parametrize('empty', ['', '  ', '{}', {}, '[]', [], 'null'], ids=repr)
async def test_empty_filter_is_a_validation_error(ctx, operation, kwargs, empty):
    """An empty filter would otherwise run the query unfiltered, so no request is sent."""
    client = MagicMock()

    result = await operation(ctx, client, filter_expr=empty, **kwargs)

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert result['message'].startswith('filter is empty')
    assert client.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize('operation, kwargs', OPERATIONS, ids=lambda v: getattr(v, '__name__', ''))
async def test_python_repr_filter_gets_a_double_quote_hint(ctx, operation, kwargs):
    """A dict repr with single quotes is not JSON; the error says what to change."""
    client = MagicMock()

    result = await operation(
        ctx, client, filter_expr="{'Dimensions': {'Key': 'SERVICE', 'Values': ['x']}}", **kwargs
    )

    assert result['error_type'] == 'validation_error'
    assert 'double quotes' in result['message']
    assert client.mock_calls == []


LEAF = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}


def _sent_filters(client):
    """Every Filter (or filter) value the operation sent to the client."""
    return [
        kwargs[key]
        for _, _, kwargs in client.mock_calls
        for key in ('Filter', 'filter')
        if key in kwargs
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize('operation, kwargs', OPERATIONS, ids=lambda v: getattr(v, '__name__', ''))
async def test_omitted_filter_sends_no_filter(ctx, operation, kwargs):
    """Omitting the filter still means no filter: the request carries none."""
    client = MagicMock()

    await operation(ctx, client, filter_expr=None, **kwargs)

    assert client.mock_calls
    assert _sent_filters(client) == []


@pytest.mark.asyncio
@pytest.mark.parametrize('operation, kwargs', OPERATIONS, ids=lambda v: getattr(v, '__name__', ''))
@pytest.mark.parametrize(
    'value', [LEAF, '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}']
)
async def test_filter_is_sent_as_parsed(ctx, operation, kwargs, value):
    """An object filter passes through unchanged, and a JSON string is sent parsed."""
    client = MagicMock()

    await operation(ctx, client, filter_expr=value, **kwargs)

    assert _sent_filters(client)[:1] == [LEAF]
