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

"""Tests for deterministic scenario forecasting."""

import pytest
from awslabs.aws_pricing_mcp_server.forecast import (
    MAX_MONTHLY_COST,
    ForecastCostComponent,
    calculate_forecast,
)
from awslabs.aws_pricing_mcp_server.server import calculate_cost_scenario, mcp
from decimal import Decimal
from mcp.types import TextContent
from pydantic import ValidationError


def test_mixed_fixed_and_independent_growth_components():
    """Keep fixed architecture flat while hosting and AI use different ramps."""
    components = [
        ForecastCostComponent(
            name='Fixed architecture',
            category='hosting',
            monthly_cost=827.09,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
        ForecastCostComponent(
            name='Usage-driven hosting',
            category='hosting',
            monthly_cost=1074.42,
            scaling_behavior='linear',
            end_multiplier=5,
        ),
        ForecastCostComponent(
            name='AI tokens',
            category='ai',
            monthly_cost=98.130498,
            scaling_behavior='linear',
            end_multiplier=150,
        ),
    ]

    result = calculate_forecast(components, months=12, currency='USD')

    assert result['summary'] == {
        'forecast_months': 12,
        'baseline_monthly_cost': '1999.64',
        'average_monthly_cost': '11459.20',
        'forecast_total': '137510.42',
        'ending_monthly_cost': '20918.76',
    }
    assert result['months'][0]['by_category'] == {'ai': '98.13', 'hosting': '1901.51'}
    assert result['months'][-1]['by_category'] == {'ai': '14719.57', 'hosting': '6199.19'}
    assert result['months'][0]['by_component']['Fixed architecture'] == '827.09'
    assert result['months'][-1]['by_component']['Fixed architecture'] == '827.09'


@pytest.mark.asyncio
async def test_mcp_tool_returns_forecast():
    """Expose the deterministic calculation through the MCP tool wrapper."""
    components = [
        ForecastCostComponent(
            name='Control plane',
            category='hosting',
            monthly_cost=72,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
        ForecastCostComponent(
            name='Compute',
            category='hosting',
            monthly_cost=100,
            scaling_behavior='linear',
            end_multiplier=3,
        ),
    ]

    result = await calculate_cost_scenario(components, months=3, currency='USD', decimal_places=2)

    assert result['summary']['forecast_total'] == '816.00'
    assert [month['total'] for month in result['months']] == ['172.00', '272.00', '372.00']


@pytest.mark.asyncio
async def test_mcp_tool_applies_field_defaults_on_direct_calls():
    """Unwrap Field defaults so non-MCP callers get a forecast, not a FieldInfo."""
    components = [
        ForecastCostComponent(
            name='Control plane',
            category=None,
            monthly_cost=10,
            scaling_behavior='fixed',
            end_multiplier=1,
        )
    ]

    result = await calculate_cost_scenario(components)

    assert result['summary']['forecast_months'] == 12
    assert result['currency'] == 'USD'
    assert result['decimal_places'] == 2
    assert result['summary']['forecast_total'] == '120.00'


def test_linear_component_can_scale_down():
    """Support planned reductions as well as growth."""
    component = ForecastCostComponent(
        name='Legacy workload',
        category=None,
        monthly_cost=100,
        scaling_behavior='linear',
        end_multiplier=0,
    )

    result = calculate_forecast([component], months=3, currency='USD')

    assert [month['total'] for month in result['months']] == ['100.00', '50.00', '0.00']
    assert result['summary']['forecast_total'] == '150.00'


def test_rounded_breakdowns_reconcile_with_forecast_total():
    """Derive every monetary view from the same rounded component ledger."""
    components = [
        ForecastCostComponent(
            name='Requests',
            category='usage',
            monthly_cost=0.005,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
        ForecastCostComponent(
            name='Storage',
            category='usage',
            monthly_cost=0.005,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
    ]

    result = calculate_forecast(components, months=3, currency='USD')

    for month in result['months']:
        assert sum(map(Decimal, month['by_component'].values())) == Decimal(month['total'])
        assert sum(map(Decimal, month['by_category'].values())) == Decimal(month['total'])
    assert sum(Decimal(month['total']) for month in result['months']) == Decimal(
        result['summary']['forecast_total']
    )


def test_fixed_precision_breakdowns_reconcile_exactly():
    """Keep component arithmetic exact for decimal values that floats cannot sum."""
    components = [
        ForecastCostComponent(
            name=name,
            category=category,
            monthly_cost=cost,
            scaling_behavior='fixed',
            end_multiplier=1,
        )
        for name, category, cost in (
            ('Compute', 'hosting', 10.10),
            ('Storage', 'hosting', 20.20),
            ('Requests', 'usage', 0.30),
        )
    ]

    result = calculate_forecast(components, months=3, currency='USD')

    for month in result['months']:
        assert sum(map(Decimal, month['by_component'].values())) == Decimal(month['total'])
        assert sum(map(Decimal, month['by_category'].values())) == Decimal(month['total'])
    assert sum(Decimal(month['total']) for month in result['months']) == Decimal(
        result['summary']['forecast_total']
    )


def test_large_forecast_is_preserved_as_fixed_precision_strings():
    """Preserve significant digits at the schema ceiling without float conversion."""
    components = [
        ForecastCostComponent(
            name=f'Component {index}',
            category=None,
            monthly_cost=MAX_MONTHLY_COST,
            scaling_behavior='linear',
            end_multiplier=1_000_000,
        )
        for index in range(4)
    ]

    result = calculate_forecast(components, months=12, currency='USD', decimal_places=6)

    assert result['months'][-1]['total'] == '4000000000000000.000000'
    assert Decimal(result['summary']['forecast_total']) == sum(
        Decimal(month['total']) for month in result['months']
    )


def test_every_published_value_has_fixed_decimal_precision():
    """Publish every monetary amount with the requested fixed precision."""
    components = [
        ForecastCostComponent(
            name='Compute',
            category='hosting',
            monthly_cost=1234.567891,
            scaling_behavior='linear',
            end_multiplier=7.5,
        ),
        ForecastCostComponent(
            name='Tokens',
            category='ai',
            monthly_cost=98.765432,
            scaling_behavior='linear',
            end_multiplier=40,
        ),
    ]

    result = calculate_forecast(components, months=12, currency='USD', decimal_places=6)

    published = [
        value
        for month in result['months']
        for value in [
            month['total'],
            *month['by_category'].values(),
            *month['by_component'].values(),
        ]
    ]
    published.extend(result['summary'][key] for key in ('forecast_total', 'average_monthly_cost'))

    for value in published:
        assert isinstance(value, str)
        assert len(value.rpartition('.')[2]) == 6


def test_many_large_components_reconcile_at_six_decimal_places():
    """Keep aggregate arithmetic exact near the former float guard."""
    components = [
        ForecastCostComponent(
            name=f'Component {index}',
            category='hosting',
            monthly_cost=9_990_491.047545,
            scaling_behavior='fixed',
            end_multiplier=1,
        )
        for index in range(50)
    ]

    result = calculate_forecast(components, months=2, currency='USD', decimal_places=6)
    month = result['months'][0]

    assert sum(map(Decimal, month['by_component'].values())) == Decimal(month['total'])
    assert Decimal(month['by_category']['hosting']) == Decimal(month['total'])


@pytest.mark.parametrize(
    ('currency', 'decimal_places', 'expected'),
    [('JPY', 0, '1'), ('KWD', 3, '1.234')],
)
def test_currency_labels_use_explicit_decimal_places(currency, decimal_places, expected):
    """Do not assume that every currency uses two decimal places."""
    component = ForecastCostComponent(
        name='Usage',
        category=None,
        monthly_cost=1.234,
        scaling_behavior='fixed',
        end_multiplier=1,
    )

    result = calculate_forecast(
        [component], months=2, currency=currency, decimal_places=decimal_places
    )

    assert result['decimal_places'] == decimal_places
    assert result['months'][0]['total'] == expected


def test_duplicate_component_names_are_rejected():
    """Reject duplicate names that would make component output ambiguous."""
    components = [
        ForecastCostComponent(
            name='Compute',
            category=None,
            monthly_cost=10,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
        ForecastCostComponent(
            name='Compute',
            category=None,
            monthly_cost=20,
            scaling_behavior='fixed',
            end_multiplier=1,
        ),
    ]

    with pytest.raises(ValueError, match='component names must be unique'):
        calculate_forecast(components, months=2, currency='USD')


def test_fixed_component_rejects_non_one_multiplier():
    """Reject contradictory fixed-component input."""
    with pytest.raises(ValidationError, match='fixed components must use end_multiplier=1'):
        ForecastCostComponent(
            name='Control plane',
            category=None,
            monthly_cost=72,
            scaling_behavior='fixed',
            end_multiplier=5,
        )


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan')])
def test_non_finite_costs_are_rejected(value):
    """Reject values that cannot produce a meaningful financial forecast."""
    with pytest.raises(ValidationError):
        ForecastCostComponent(
            name='Invalid',
            category=None,
            monthly_cost=value,
            scaling_behavior='fixed',
            end_multiplier=1,
        )


def test_monthly_cost_boundary_is_safe_for_maximum_multiplier():
    """Keep the largest schema-valid input inside the supported Decimal range."""
    component = ForecastCostComponent(
        name='Maximum',
        category=None,
        monthly_cost=MAX_MONTHLY_COST,
        scaling_behavior='linear',
        end_multiplier=1_000_000,
    )

    result = calculate_forecast([component], months=120, currency='USD')

    assert result['months'][-1]['total'] == '1000000000000000.00'


def test_maximum_monthly_cost_is_accepted_without_a_multiplier():
    """Keep realistic large baselines inside the publishable range."""
    component = ForecastCostComponent(
        name='Maximum',
        category=None,
        monthly_cost=MAX_MONTHLY_COST,
        scaling_behavior='fixed',
        end_multiplier=1,
    )

    result = calculate_forecast([component], months=120, currency='USD')

    assert result['months'][-1]['total'] == '1000000000.00'
    assert result['summary']['forecast_total'] == '120000000000.00'


def test_monthly_cost_above_supported_bound_is_rejected():
    """Reject large finite inputs before Decimal quantization can fail."""
    with pytest.raises(ValidationError):
        ForecastCostComponent(
            name='Too large',
            category=None,
            monthly_cost=MAX_MONTHLY_COST + 1,
            scaling_behavior='fixed',
            end_multiplier=1,
        )


def test_oversized_forecast_response_is_rejected():
    """Reject worst-case encoded labels without allocating the complete JSON string."""
    components = [
        ForecastCostComponent(
            name=('🧾' * 196) + f'{index:04d}',
            category=('💰' * 96) + f'{index:04d}',
            monthly_cost=1,
            scaling_behavior='fixed',
            end_multiplier=1,
        )
        for index in range(100)
    ]

    with pytest.raises(ValueError, match='100,000-character limit'):
        calculate_forecast(components, months=120, currency='USD')


@pytest.mark.asyncio
async def test_mcp_response_budget_counts_the_only_emitted_representation():
    """Avoid duplicating a near-limit result as text and structured content."""
    components = [
        {
            'name': f'{index:02d}' + ('n' * 98),
            'category': f'{index:02d}' + ('c' * 98),
            'monthly_cost': 1,
            'scaling_behavior': 'fixed',
        }
        for index in range(10)
    ]

    content = await mcp.call_tool(
        'calculate_cost_scenario', {'components': components, 'months': 37}
    )

    assert isinstance(content, list)
    assert len(content) == 1
    assert isinstance(content[0], TextContent)
    assert len(content[0].text) <= 100_000


def test_decimal_places_outside_supported_range_is_rejected():
    """Keep direct calls within the advertised monetary precision range."""
    component = ForecastCostComponent(
        name='Compute',
        category=None,
        monthly_cost=1,
        scaling_behavior='fixed',
        end_multiplier=1,
    )

    with pytest.raises(ValueError, match='decimal_places must be'):
        calculate_forecast([component], months=2, currency='USD', decimal_places=7)


@pytest.mark.parametrize(
    ('components', 'months', 'currency', 'message'),
    [
        ([], 12, 'USD', 'components must contain'),
        (
            [
                ForecastCostComponent(
                    name=f'Compute {index}',
                    category=None,
                    monthly_cost=1,
                    scaling_behavior='fixed',
                    end_multiplier=1,
                )
                for index in range(101)
            ],
            12,
            'USD',
            'components must contain',
        ),
        (
            [
                ForecastCostComponent(
                    name='Compute',
                    category=None,
                    monthly_cost=1,
                    scaling_behavior='fixed',
                    end_multiplier=1,
                )
            ],
            1,
            'USD',
            'months must be',
        ),
        (
            [
                ForecastCostComponent(
                    name='Compute',
                    category=None,
                    monthly_cost=1,
                    scaling_behavior='fixed',
                    end_multiplier=1,
                )
            ],
            12,
            'usd',
            'currency must be',
        ),
    ],
)
def test_calculate_forecast_rejects_invalid_direct_calls(components, months, currency, message):
    """Keep the pure calculation boundary safe outside MCP validation."""
    with pytest.raises(ValueError, match=message):
        calculate_forecast(components, months=months, currency=currency)
