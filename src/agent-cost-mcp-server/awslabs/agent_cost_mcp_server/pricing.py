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
from datetime import date
from pathlib import Path


_PRICING_FILE = Path(__file__).with_name('pricing.json')


# A snapshot row whose prices were last checked more than this many
# days ago is flagged stale in responses, so callers can decide how
# much to trust the estimate instead of treating it as current.
STALE_AFTER_DAYS = 90


def _is_stale(checked_date: str, today: date | None = None) -> bool:
    """Return True when a row's checked date is older than the threshold.

    A row with no parseable checked date counts as stale: unknown
    provenance should not read as fresh.
    """
    try:
        checked = date.fromisoformat(checked_date)
    except (TypeError, ValueError):
        return True
    return ((today or date.today()) - checked).days > STALE_AFTER_DAYS


@dataclass(frozen=True)
class ModelPrice:
    """List prices for a single model, in USD per million tokens."""

    model_id: str
    display_name: str
    provider: str
    input_per_mtok: float  # USD per million input tokens
    output_per_mtok: float  # USD per million output tokens
    # USD per million cached (cache-read) input tokens, where the
    # provider publishes a separate cache rate. None means no published
    # cache rate in the snapshot: cached tokens are then billed at the
    # standard input rate, never silently at $0.
    cached_input_per_mtok: float | None = None
    # Date this row's prices were last checked against the provider.
    checked_date: str = ''

    def _input_cost(self, input_tokens: int, cached_input_tokens: int) -> float:
        uncached = input_tokens - cached_input_tokens
        cache_rate = (
            self.cached_input_per_mtok
            if self.cached_input_per_mtok is not None
            else self.input_per_mtok
        )
        return (
            uncached / 1_000_000 * self.input_per_mtok
            + cached_input_tokens / 1_000_000 * cache_rate
        )

    def cost(
        self, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0
    ) -> float:
        """Return the total cost in USD for the given token counts."""
        return self._input_cost(input_tokens, cached_input_tokens) + (
            output_tokens / 1_000_000 * self.output_per_mtok
        )

    def breakdown(
        self, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0
    ) -> dict:
        """Return a priced usage record with the cost split out.

        Cached input tokens are reported separately from uncached
        input: after the first turn of an agent run most input is
        cached context, and billing it at the full input rate
        overstates the run several times over.
        """
        cache_rate = (
            self.cached_input_per_mtok
            if self.cached_input_per_mtok is not None
            else self.input_per_mtok
        )
        uncached_cost = (input_tokens - cached_input_tokens) / 1_000_000 * self.input_per_mtok
        cached_cost = cached_input_tokens / 1_000_000 * cache_rate
        output_cost = output_tokens / 1_000_000 * self.output_per_mtok
        return {
            'model': self.model_id,
            'display_name': self.display_name,
            'provider': self.provider,
            'input_tokens': input_tokens,
            'cached_input_tokens': cached_input_tokens,
            'uncached_input_tokens': input_tokens - cached_input_tokens,
            'output_tokens': output_tokens,
            'input_cost_usd': round(uncached_cost + cached_cost, 6),
            'cached_input_cost_usd': round(cached_cost, 6),
            'cache_rate_applied': self.cached_input_per_mtok is not None,
            'output_cost_usd': round(output_cost, 6),
            'cost_usd': round(uncached_cost + cached_cost + output_cost, 6),
            'price_checked_date': self.checked_date,
            'price_stale': _is_stale(self.checked_date),
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
                cached_input_per_mtok=m.get('cached_input_per_mtok'),
                checked_date=m.get('checked_date') or data['snapshot_date'],
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


def _check_tokens(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> None:
    if input_tokens < 0 or output_tokens < 0 or cached_input_tokens < 0:
        raise ValueError('token counts must be non-negative')
    if cached_input_tokens > input_tokens:
        raise ValueError(
            f'cached_input_tokens ({cached_input_tokens}) cannot exceed '
            f'input_tokens ({input_tokens})'
        )


def _price_meta(table: PricingTable) -> dict:
    """Provenance carried on every priced response.

    Prices are provider list prices captured in the bundled snapshot, so
    the confidence label is 'list': the rates are the published list
    rates as of the snapshot date, not negotiated or measured prices.
    """
    return {
        'price_source_date': table.snapshot_date,
        'price_confidence': 'list',
    }


def price_usage(
    table: PricingTable,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> dict:
    """Price one concrete usage record at a model's list rates.

    Unknown models are refused with an error naming the model: pricing
    an unlisted model at $0 would let the newest (usually most
    expensive) model sail through every budget check as free.
    """
    _check_tokens(input_tokens, output_tokens, cached_input_tokens)
    return {
        **table.get(model_id).breakdown(input_tokens, output_tokens, cached_input_tokens),
        **_price_meta(table),
    }


def estimate_run_cost(
    table: PricingTable,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    expected_attempts: float | None = None,
    attempts_source: str | None = None,
    cached_input_tokens: int = 0,
) -> dict:
    """Price an expected workload on one model.

    Also prices the same workload on every other model in the snapshot
    so callers can compare without a second call.

    Cost per run is not cost per solved task: a workload that needs
    several attempts per success costs proportionally more. Pass
    expected_attempts (with attempts_source 'measured' if it comes from
    observed run history, 'prior' if it is an assumption) to get
    cost_per_solved_task_usd alongside the per-run cost. The source is
    carried in the response because a measured attempts term and an
    assumed one deserve different confidence.
    """
    _check_tokens(input_tokens, output_tokens, cached_input_tokens)
    if expected_attempts is not None and expected_attempts < 1.0:
        raise ValueError(f'expected_attempts must be at least 1.0, got {expected_attempts}')
    if attempts_source is not None and attempts_source not in ('prior', 'measured'):
        raise ValueError(f"attempts_source must be 'prior' or 'measured', got {attempts_source!r}")
    attempts = expected_attempts if expected_attempts is not None else 1.0
    primary = table.get(model_id).breakdown(input_tokens, output_tokens, cached_input_tokens)
    alternatives = sorted(
        (
            m.breakdown(input_tokens, output_tokens, cached_input_tokens)
            for m in table.all()
            if m.model_id != model_id
        ),
        key=lambda r: r['cost_usd'],
    )
    return {
        **primary,
        'expected_attempts': attempts,
        'attempts_source': attempts_source or 'prior',
        'cost_per_solved_task_usd': round(primary['cost_usd'] * attempts, 6),
        'alternatives': [{'model': a['model'], 'cost_usd': a['cost_usd']} for a in alternatives],
        'pricing_snapshot': f'v{table.snapshot_version} ({table.snapshot_date})',
        **_price_meta(table),
    }


def compare_models_for_task(
    table: PricingTable,
    input_tokens: int,
    output_tokens: int,
    success_rates: dict[str, float] | None = None,
    quality_floor: float | None = None,
    cached_input_tokens: int = 0,
) -> dict:
    """Rank models by expected cost per successful task.

    A model that costs $0.01 per attempt but only succeeds half the time
    costs $0.02 per success in expectation. Where the caller supplies no
    success rate for a model, its rate is taken as 1.0 (ranked on raw
    cost) — callers who have measured rates get the true ranking. Each
    row also carries expected_attempts (1 / success rate), the attempts
    term behind the per-success cost.

    quality_floor is a hard filter on the success rate, applied before
    ranking: a model below the floor is excluded no matter how cheap it
    is, and so is a model with no supplied rate, because the floor
    cannot be checked for it. Excluded models are reported in
    excluded_by_quality_floor with the reason, never silently dropped.
    """
    _check_tokens(input_tokens, output_tokens, cached_input_tokens)
    rates = success_rates or {}
    for mid, rate in rates.items():
        if not 0.0 < rate <= 1.0:
            raise ValueError(f'success rate for {mid!r} must be in (0, 1], got {rate}')
    unknown = sorted(mid for mid in rates if mid not in {m.model_id for m in table.all()})
    if unknown:
        raise ValueError(
            f'success_rates names models not in the pricing snapshot: {unknown}. '
            'Refusing to rank: an unpriced model must not be silently dropped '
            'or priced at $0.'
        )
    if quality_floor is not None and not 0.0 < quality_floor <= 1.0:
        raise ValueError(f'quality_floor must be in (0, 1], got {quality_floor}')
    rows = []
    excluded = []
    for model in table.all():
        if quality_floor is not None:
            if model.model_id not in rates:
                excluded.append({'model': model.model_id, 'reason': 'no_success_rate'})
                continue
            if rates[model.model_id] < quality_floor:
                excluded.append({'model': model.model_id, 'reason': 'below_quality_floor'})
                continue
        per_run = model.cost(input_tokens, output_tokens, cached_input_tokens)
        rate = rates.get(model.model_id, 1.0)
        rows.append(
            {
                'model': model.model_id,
                'display_name': model.display_name,
                'cost_per_run_usd': round(per_run, 6),
                'success_rate': rate,
                'expected_attempts': round(1.0 / rate, 4),
                'cost_per_success_usd': round(per_run / rate, 6),
                'price_checked_date': model.checked_date,
                'price_stale': _is_stale(model.checked_date),
            }
        )
    rows.sort(key=lambda r: r['cost_per_success_usd'])
    return {
        'input_tokens': input_tokens,
        'cached_input_tokens': cached_input_tokens,
        'output_tokens': output_tokens,
        'ranked': rows,
        'quality_floor': quality_floor,
        'excluded_by_quality_floor': excluded,
        'pricing_snapshot': f'v{table.snapshot_version} ({table.snapshot_date})',
        **_price_meta(table),
    }
