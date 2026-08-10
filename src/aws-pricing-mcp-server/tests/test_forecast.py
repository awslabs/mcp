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
    ForecastCostComponent,
    calculate_forecast,
)
from awslabs.aws_pricing_mcp_server.server import calculate_cost_scenario
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
        'baseline_monthly_cost': 1999.64,
        'average_monthly_cost': 11459.2,
        'forecast_total': 137510.43,
        'ending_monthly_cost': 20918.76,
    }
    assert result['months'][0]['by_category'] == {'ai': 98.13, 'hosting': 1901.51}
    assert result['months'][-1]['by_category'] == {'ai': 14719.57, 'hosting': 6199.19}
    assert result['months'][0]['by_component']['Fixed architecture'] == 827.09
    assert result['months'][-1]['by_component']['Fixed architecture'] == 827.09


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

    result = await calculate_cost_scenario(components, months=3, currency='USD')

    assert result['summary']['forecast_total'] == 816.0
    assert [month['total'] for month in result['months']] == [172.0, 272.0, 372.0]


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

    assert [month['total'] for month in result['months']] == [100.0, 50.0, 0.0]
    assert result['summary']['forecast_total'] == 150.0


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
