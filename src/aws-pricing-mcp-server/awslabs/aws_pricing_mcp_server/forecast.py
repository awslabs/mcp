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

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Dict, List, Literal, Optional


MAX_COMPONENTS = 100
MAX_DECIMAL_PLACES = 6
MAX_MONTHLY_COST = 1_000_000_000
MAX_MONTHS = 120
MAX_RESPONSE_CHARACTERS = 100_000


def _round_money(value: Decimal, quantum: Decimal) -> Decimal:
    """Round a decimal monetary value to the requested minor unit."""
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _format_money(value: Decimal, decimal_places: int) -> str:
    """Preserve a rounded monetary value as a fixed-precision decimal string."""
    return f'{value:.{decimal_places}f}'


def _fits_response_budget(value: Dict) -> bool:
    """Count emitted characters without allocating an oversized JSON string."""
    encoded_characters = 0
    for chunk in json.JSONEncoder(indent=2, ensure_ascii=False).iterencode(value):
        encoded_characters += len(chunk)
        if encoded_characters > MAX_RESPONSE_CHARACTERS:
            return False
    return True


class ForecastCostComponent(BaseModel):
    """A baseline monthly cost and its behavior over a forecast horizon."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., min_length=1, max_length=200, description='Component name')
    category: Optional[str] = Field(
        None, min_length=1, max_length=100, description='Optional grouping label'
    )
    monthly_cost: float = Field(
        ...,
        ge=0,
        le=MAX_MONTHLY_COST,
        allow_inf_nan=False,
        description='Baseline monthly cost',
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
    components: List[ForecastCostComponent],
    months: int,
    currency: str,
    decimal_places: int = 2,
) -> Dict:
    """Calculate a linear scenario forecast without querying external services."""
    if not 2 <= months <= MAX_MONTHS:
        raise ValueError(f'months must be between 2 and {MAX_MONTHS}')
    if not 1 <= len(components) <= MAX_COMPONENTS:
        raise ValueError(f'components must contain between 1 and {MAX_COMPONENTS} items')
    if not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('currency must be a three-letter uppercase display label')
    if not 0 <= decimal_places <= MAX_DECIMAL_PLACES:
        raise ValueError(f'decimal_places must be between 0 and {MAX_DECIMAL_PLACES}')

    component_names = [component.name for component in components]
    if len(component_names) != len(set(component_names)):
        raise ValueError('component names must be unique')

    quantum = Decimal(1).scaleb(-decimal_places)
    component_rows = []
    monthly_rows = []
    monthly_totals = []
    component_totals = {component.name: Decimal('0') for component in components}
    component_first_costs: Dict[str, Decimal] = {}
    component_last_costs: Dict[str, Decimal] = {}

    for month_index in range(months):
        progress = Decimal(month_index) / Decimal(months - 1)
        component_costs: Dict[str, str] = {}
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
            cost = _round_money(baseline * factor, quantum)
            component_costs[component.name] = _format_money(cost, decimal_places)
            category = component.category or 'uncategorized'
            category_costs[category] = category_costs.get(category, Decimal('0')) + cost
            month_total += cost
            component_totals[component.name] += cost
            component_first_costs.setdefault(component.name, cost)
            component_last_costs[component.name] = cost

        monthly_totals.append(month_total)
        monthly_rows.append(
            {
                'month': month_index + 1,
                'total': _format_money(month_total, decimal_places),
                'by_category': {
                    category: _format_money(cost, decimal_places)
                    for category, cost in sorted(category_costs.items())
                },
                'by_component': component_costs,
            }
        )

    for component in components:
        end_multiplier = Decimal(str(component.end_multiplier))
        component_rows.append(
            {
                'name': component.name,
                'category': component.category or 'uncategorized',
                'scaling_behavior': component.scaling_behavior,
                'baseline_monthly_cost': _format_money(
                    component_first_costs[component.name], decimal_places
                ),
                'end_multiplier': float(end_multiplier),
                'average_monthly_cost': _format_money(
                    _round_money(component_totals[component.name] / Decimal(months), quantum),
                    decimal_places,
                ),
                'ending_monthly_cost': _format_money(
                    component_last_costs[component.name], decimal_places
                ),
            }
        )

    forecast_total = sum(monthly_totals, Decimal('0'))

    response = {
        'status': 'success',
        'currency': currency,
        'decimal_places': decimal_places,
        'assumption': (
            'Each linear component ramps independently from 1x to its end multiplier using '
            'a constant effective rate; tiering, free allowances, commitments, capacity steps, '
            'and price changes must be modeled separately.'
        ),
        'months': monthly_rows,
        'components': component_rows,
        'summary': {
            'forecast_months': months,
            'baseline_monthly_cost': _format_money(monthly_totals[0], decimal_places),
            'average_monthly_cost': _format_money(
                _round_money(forecast_total / Decimal(months), quantum), decimal_places
            ),
            'forecast_total': _format_money(forecast_total, decimal_places),
            'ending_monthly_cost': _format_money(monthly_totals[-1], decimal_places),
        },
    }
    if not _fits_response_budget(response):
        raise ValueError(
            f'forecast response exceeds the {MAX_RESPONSE_CHARACTERS:,}-character limit; '
            'reduce components, months, or label lengths'
        )
    return response
