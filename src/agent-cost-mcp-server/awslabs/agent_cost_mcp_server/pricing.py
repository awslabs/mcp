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

"""Pricing snapshot loading and cost math for the agent cost MCP server.

The pricing/cost-per-success approach is a port of tokenecon
(https://pypi.org/project/tokenecon/): price concrete usage at a model's
list rates, and rank models by expected cost per *successful* task
(cost per attempt divided by the success rate), not cost per token.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


_PRICING_FILE = Path(__file__).with_name('pricing.json')


@dataclass(frozen=True)
class ModelPrice:
    """List prices for a single model, in USD per million tokens."""

    model_id: str
    display_name: str
    provider: str
    input_per_mtok: float  # USD per million input tokens
    output_per_mtok: float  # USD per million output tokens

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        """Return the total cost in USD for the given token counts."""
        return (
            input_tokens / 1_000_000 * self.input_per_mtok
            + output_tokens / 1_000_000 * self.output_per_mtok
        )

    def breakdown(self, input_tokens: int, output_tokens: int) -> dict:
        """Return a priced usage record with input/output cost split."""
        input_cost = input_tokens / 1_000_000 * self.input_per_mtok
        output_cost = output_tokens / 1_000_000 * self.output_per_mtok
        return {
            'model': self.model_id,
            'display_name': self.display_name,
            'provider': self.provider,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'cost_usd': round(input_cost + output_cost, 6),
        }


class PricingTable:
    """A versioned snapshot of model list prices, loaded once at startup."""

    def __init__(self, path: Path | None = None) -> None:
        """Load the pricing snapshot from the given path or the bundled file."""
        data = json.loads((path or _PRICING_FILE).read_text())
        self.snapshot_version = data['snapshot_version']
        self.snapshot_date = data['snapshot_date']
        self._models: dict[str, ModelPrice] = {
            m['model_id']: ModelPrice(
                model_id=m['model_id'],
                display_name=m['display_name'],
                provider=m['provider'],
                input_per_mtok=m['input_per_mtok'],
                output_per_mtok=m['output_per_mtok'],
            )
            for m in data['models']
        }

    def get(self, model_id: str) -> ModelPrice:
        """Return the price for a model, raising ValueError if unknown."""
        try:
            return self._models[model_id]
        except KeyError:
            known = ', '.join(sorted(self._models))
            raise ValueError(f'Unknown model_id {model_id!r}. Known models: {known}') from None

    def all(self) -> list[ModelPrice]:
        """Return every model in the snapshot."""
        return list(self._models.values())


def _check_tokens(input_tokens: int, output_tokens: int) -> None:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError('token counts must be non-negative')


def price_usage(table: PricingTable, model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Price one concrete usage record at a model's list rates."""
    _check_tokens(input_tokens, output_tokens)
    return table.get(model_id).breakdown(input_tokens, output_tokens)


def estimate_run_cost(
    table: PricingTable, model_id: str, input_tokens: int, output_tokens: int
) -> dict:
    """Price an expected workload on one model.

    Also prices the same workload on every other model in the snapshot
    so callers can compare without a second call.
    """
    _check_tokens(input_tokens, output_tokens)
    primary = table.get(model_id).breakdown(input_tokens, output_tokens)
    alternatives = sorted(
        (m.breakdown(input_tokens, output_tokens) for m in table.all() if m.model_id != model_id),
        key=lambda r: r['cost_usd'],
    )
    return {
        **primary,
        'alternatives': [{'model': a['model'], 'cost_usd': a['cost_usd']} for a in alternatives],
        'pricing_snapshot': f'v{table.snapshot_version} ({table.snapshot_date})',
    }


def compare_models_for_task(
    table: PricingTable,
    input_tokens: int,
    output_tokens: int,
    success_rates: dict[str, float] | None = None,
) -> dict:
    """Rank models by expected cost per successful task.

    A model that costs $0.01 per attempt but only succeeds half the time
    costs $0.02 per success in expectation. Where the caller supplies no
    success rate for a model, its rate is taken as 1.0 (ranked on raw
    cost) — callers who have measured rates get the true ranking.
    """
    _check_tokens(input_tokens, output_tokens)
    rates = success_rates or {}
    for mid, rate in rates.items():
        if not 0.0 < rate <= 1.0:
            raise ValueError(f'success rate for {mid!r} must be in (0, 1], got {rate}')
    rows = []
    for model in table.all():
        per_run = model.cost(input_tokens, output_tokens)
        rate = rates.get(model.model_id, 1.0)
        rows.append(
            {
                'model': model.model_id,
                'display_name': model.display_name,
                'cost_per_run_usd': round(per_run, 6),
                'success_rate': rate,
                'cost_per_success_usd': round(per_run / rate, 6),
            }
        )
    rows.sort(key=lambda r: r['cost_per_success_usd'])
    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'ranked': rows,
        'pricing_snapshot': f'v{table.snapshot_version} ({table.snapshot_date})',
    }
