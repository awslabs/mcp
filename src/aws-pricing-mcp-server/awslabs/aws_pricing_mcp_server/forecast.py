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

"""Deterministic scenario forecasting for fixed and usage-scaled costs."""

import re
from decimal import ROUND_HALF_UP, Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Dict, List, Literal, Optional


MONEY = Decimal('0.01')
MAX_COMPONENTS = 100
MAX_MONTHS = 120


def _money(value: Decimal) -> float:
    """Round a decimal monetary value to cents for JSON output."""
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP))


class ForecastCostComponent(BaseModel):
    """A baseline monthly cost and its behavior over a forecast horizon."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., min_length=1, max_length=200, description='Component name')
    category: Optional[str] = Field(
        None, min_length=1, max_length=100, description='Optional grouping label'
    )
    monthly_cost: float = Field(
        ..., ge=0, allow_inf_nan=False, description='Baseline monthly cost'
    )
    scaling_behavior: Literal['fixed', 'linear'] = Field(
        ...,
        description='fixed holds cost constant; linear ramps from 1x to end_multiplier',
    )
    end_multiplier: float = Field(
        1,
        ge=0,
        le=1_000_000,
        allow_inf_nan=False,
        description='Final-month multiplier for a linear component',
    )

    @model_validator(mode='after')
    def validate_fixed_multiplier(self):
        """Reject contradictory fixed-component configuration."""
        if self.scaling_behavior == 'fixed' and self.end_multiplier != 1:
            raise ValueError('fixed components must use end_multiplier=1')
        return self


def calculate_forecast(
    components: List[ForecastCostComponent], months: int, currency: str
) -> Dict:
    """Calculate a linear scenario forecast without querying external services."""
    if not 2 <= months <= MAX_MONTHS:
        raise ValueError(f'months must be between 2 and {MAX_MONTHS}')
    if not 1 <= len(components) <= MAX_COMPONENTS:
        raise ValueError(f'components must contain between 1 and {MAX_COMPONENTS} items')
    if not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('currency must be a three-letter uppercase ISO 4217 code')

    component_names = [component.name for component in components]
    if len(component_names) != len(set(component_names)):
        raise ValueError('component names must be unique')

    component_rows = []
    monthly_rows = []
    unrounded_monthly_totals = []

    for month_index in range(months):
        progress = Decimal(month_index) / Decimal(months - 1)
        component_costs: Dict[str, float] = {}
        category_costs: Dict[str, Decimal] = {}
        month_total = Decimal('0')

        for component in components:
            baseline = Decimal(str(component.monthly_cost))
            end_multiplier = Decimal(str(component.end_multiplier))
            factor = (
                Decimal('1')
                if component.scaling_behavior == 'fixed'
                else Decimal('1') + (end_multiplier - Decimal('1')) * progress
            )
            cost = baseline * factor
            component_costs[component.name] = _money(cost)
            category = component.category or 'uncategorized'
            category_costs[category] = category_costs.get(category, Decimal('0')) + cost
            month_total += cost

        unrounded_monthly_totals.append(month_total)
        monthly_rows.append(
            {
                'month': month_index + 1,
                'total': _money(month_total),
                'by_category': {
                    category: _money(cost) for category, cost in sorted(category_costs.items())
                },
                'by_component': component_costs,
            }
        )

    for component in components:
        baseline = Decimal(str(component.monthly_cost))
        end_multiplier = Decimal(str(component.end_multiplier))
        average_factor = (
            Decimal('1')
            if component.scaling_behavior == 'fixed'
            else (Decimal('1') + end_multiplier) / Decimal('2')
        )
        component_rows.append(
            {
                'name': component.name,
                'category': component.category or 'uncategorized',
                'scaling_behavior': component.scaling_behavior,
                'baseline_monthly_cost': _money(baseline),
                'end_multiplier': float(end_multiplier),
                'average_monthly_cost': _money(baseline * average_factor),
                'ending_monthly_cost': _money(baseline * end_multiplier),
            }
        )

    annual_total = sum(unrounded_monthly_totals, Decimal('0'))
    return {
        'status': 'success',
        'currency': currency,
        'assumption': 'Each linear component ramps independently from 1x to its end multiplier.',
        'months': monthly_rows,
        'components': component_rows,
        'summary': {
            'forecast_months': months,
            'baseline_monthly_cost': _money(unrounded_monthly_totals[0]),
            'average_monthly_cost': _money(annual_total / Decimal(months)),
            'forecast_total': _money(annual_total),
            'ending_monthly_cost': _money(unrounded_monthly_totals[-1]),
        },
    }
