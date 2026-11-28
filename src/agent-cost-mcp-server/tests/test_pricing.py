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

"""Tests for the pricing snapshot and cost math."""

import pytest
from awslabs.agent_cost_mcp_server.pricing import (
    PricingTable,
    compare_models_for_task,
    estimate_run_cost,
    price_usage,
)


TABLE = PricingTable()


def test_price_usage_math():
    """Claude Haiku 4.5: $1.00 in / $5.00 out per 1M tokens."""
    result = price_usage(TABLE, 'anthropic.claude-haiku-4-5', 1_000_000, 1_000_000)
    assert result['input_cost_usd'] == 1.0
    assert result['output_cost_usd'] == 5.0
    assert result['cost_usd'] == 6.0


def test_price_usage_unknown_model():
    """Unknown model ids raise a ValueError listing the known models."""
    with pytest.raises(ValueError, match='Unknown model_id'):
        price_usage(TABLE, 'nope.not-a-model', 100, 100)


def test_negative_tokens_rejected():
    """Negative token counts are rejected."""
    with pytest.raises(ValueError, match='non-negative'):
        price_usage(TABLE, 'anthropic.claude-haiku-4-5', -1, 100)


def test_estimate_includes_sorted_alternatives():
    """Estimates price the primary model and sort alternatives by cost."""
    result = estimate_run_cost(TABLE, 'anthropic.claude-sonnet-4-5', 10_000, 2_000)
    assert result['model'] == 'anthropic.claude-sonnet-4-5'
    assert result['cost_usd'] == pytest.approx(0.06)
    costs = [a['cost_usd'] for a in result['alternatives']]
    assert costs == sorted(costs)
    assert all(a['model'] != 'anthropic.claude-sonnet-4-5' for a in result['alternatives'])


def test_compare_ranks_by_cost_per_success_not_per_token():
    """A cheap but unreliable model loses to a pricier reliable one."""
    # Haiku is 3x cheaper per run, but at a 25% success rate its expected
    # cost per success ($0.08) beats nothing — Sonnet at 100% ($0.06) wins.
    result = compare_models_for_task(
        TABLE,
        10_000,
        2_000,
        success_rates={
            'anthropic.claude-haiku-4-5': 0.25,
            'anthropic.claude-sonnet-4-5': 1.0,
        },
    )
    ranked = result['ranked']
    sonnet = next(r for r in ranked if r['model'] == 'anthropic.claude-sonnet-4-5')
    haiku = next(r for r in ranked if r['model'] == 'anthropic.claude-haiku-4-5')
    assert haiku['cost_per_run_usd'] < sonnet['cost_per_run_usd']
    assert haiku['cost_per_success_usd'] == pytest.approx(0.08)
    assert sonnet['cost_per_success_usd'] == pytest.approx(0.06)
    assert ranked.index(sonnet) < ranked.index(haiku)


def test_compare_rejects_bad_success_rate():
    """Success rates outside (0, 1] are rejected."""
    with pytest.raises(ValueError, match='success rate'):
        compare_models_for_task(TABLE, 100, 100, success_rates={'x': 0})


def test_price_usage_carries_price_source_and_confidence():
    """Every priced response names the price source date and confidence."""
    result = price_usage(TABLE, 'anthropic.claude-haiku-4-5', 1_000, 1_000)
    assert result['price_source_date'] == TABLE.snapshot_date
    assert result['price_confidence'] == 'list'


def test_estimate_defaults_to_one_attempt():
    """Without an attempts term, cost per solved task equals cost per run."""
    result = estimate_run_cost(TABLE, 'anthropic.claude-sonnet-4-5', 10_000, 2_000)
    assert result['expected_attempts'] == 1.0
    assert result['cost_per_solved_task_usd'] == result['cost_usd']
    assert result['price_source_date'] == TABLE.snapshot_date


def test_estimate_applies_expected_attempts():
    """Cost per solved task is the per-run cost times expected attempts."""
    result = estimate_run_cost(
        TABLE,
        'anthropic.claude-sonnet-4-5',
        10_000,
        2_000,
        expected_attempts=2.5,
        attempts_source='measured',
    )
    assert result['expected_attempts'] == 2.5
    assert result['attempts_source'] == 'measured'
    assert result['cost_per_solved_task_usd'] == pytest.approx(result['cost_usd'] * 2.5)


def test_estimate_attempts_source_defaults_to_prior():
    """An attempts term without a named source is labeled a prior."""
    result = estimate_run_cost(
        TABLE, 'anthropic.claude-sonnet-4-5', 10_000, 2_000, expected_attempts=2.0
    )
    assert result['attempts_source'] == 'prior'


def test_estimate_rejects_bad_attempts():
    """Expected attempts below 1 and unknown sources are rejected."""
    with pytest.raises(ValueError, match='expected_attempts'):
        estimate_run_cost(TABLE, 'anthropic.claude-sonnet-4-5', 100, 100, expected_attempts=0.5)
    with pytest.raises(ValueError, match='attempts_source'):
        estimate_run_cost(
            TABLE,
            'anthropic.claude-sonnet-4-5',
            100,
            100,
            expected_attempts=2.0,
            attempts_source='guessed',
        )


def test_compare_rows_carry_expected_attempts():
    """Each ranked row exposes its expected attempts (1 / success rate)."""
    result = compare_models_for_task(
        TABLE, 10_000, 2_000, success_rates={'anthropic.claude-haiku-4-5': 0.25}
    )
    haiku = next(r for r in result['ranked'] if r['model'] == 'anthropic.claude-haiku-4-5')
    assert haiku['expected_attempts'] == pytest.approx(4.0)
    assert result['price_source_date'] == TABLE.snapshot_date


def test_compare_quality_floor_is_a_hard_filter():
    """Models below the floor — or with no rate to check — are excluded."""
    result = compare_models_for_task(
        TABLE,
        10_000,
        2_000,
        success_rates={
            'anthropic.claude-haiku-4-5': 0.25,
            'anthropic.claude-sonnet-4-5': 1.0,
        },
        quality_floor=0.5,
    )
    ranked_ids = [r['model'] for r in result['ranked']]
    assert ranked_ids == ['anthropic.claude-sonnet-4-5']
    excluded = {e['model']: e['reason'] for e in result['excluded_by_quality_floor']}
    assert excluded['anthropic.claude-haiku-4-5'] == 'below_quality_floor'
    assert 'no_success_rate' in excluded.values()
    assert result['quality_floor'] == 0.5


def test_compare_rejects_bad_quality_floor():
    """Quality floors outside (0, 1] are rejected."""
    with pytest.raises(ValueError, match='quality_floor'):
        compare_models_for_task(TABLE, 100, 100, quality_floor=0)
    with pytest.raises(ValueError, match='quality_floor'):
        compare_models_for_task(TABLE, 100, 100, quality_floor=1.5)


def _fixture_table(tmp_path, models):
    """Build a PricingTable from an inline snapshot written to tmp_path."""
    import json

    path = tmp_path / 'pricing.json'
    path.write_text(
        json.dumps(
            {'snapshot_version': 99, 'snapshot_date': '2026-01-01', 'models': models}
        )
    )
    return PricingTable(path)


def test_compare_rejects_unknown_model_in_success_rates():
    """A success rate for an unlisted model is refused, not silently dropped."""
    with pytest.raises(ValueError, match='not in the pricing snapshot'):
        compare_models_for_task(
            TABLE, 100, 100, success_rates={'nope.not-a-model': 0.5}
        )


def test_price_usage_carries_row_checked_date():
    """Priced responses carry the row's own checked date and stale flag."""
    result = price_usage(TABLE, 'anthropic.claude-haiku-4-5', 1_000, 1_000)
    row = next(m for m in TABLE.all() if m.model_id == 'anthropic.claude-haiku-4-5')
    assert result['price_checked_date'] == row.checked_date
    assert result['price_stale'] is False


def test_stale_flag_after_threshold(tmp_path):
    """Rows checked more than 90 days ago are flagged stale; fresh rows are not."""
    from datetime import date, timedelta

    fresh = date.today().isoformat()
    stale = (date.today() - timedelta(days=200)).isoformat()
    table = _fixture_table(
        tmp_path,
        [
            {
                'model_id': 'x.fresh',
                'display_name': 'Fresh',
                'provider': 'x',
                'input_per_mtok': 1.0,
                'output_per_mtok': 1.0,
                'checked_date': fresh,
            },
            {
                'model_id': 'x.stale',
                'display_name': 'Stale',
                'provider': 'x',
                'input_per_mtok': 1.0,
                'output_per_mtok': 1.0,
                'checked_date': stale,
            },
        ],
    )
    assert price_usage(table, 'x.fresh', 100, 100)['price_stale'] is False
    assert price_usage(table, 'x.stale', 100, 100)['price_stale'] is True
    rows = {r['model']: r for r in compare_models_for_task(table, 100, 100)['ranked']}
    assert rows['x.fresh']['price_checked_date'] == fresh
    assert rows['x.stale']['price_stale'] is True


def test_cached_input_split_math():
    """Sonnet 4.5: cached input bills at the $0.30 cache-read rate, not $3.00."""
    result = price_usage(
        TABLE, 'anthropic.claude-sonnet-4-5', 1_000_000, 0, cached_input_tokens=900_000
    )
    assert result['uncached_input_tokens'] == 100_000
    assert result['cached_input_tokens'] == 900_000
    assert result['cached_input_cost_usd'] == pytest.approx(0.27)
    assert result['input_cost_usd'] == pytest.approx(0.30 + 0.27)
    assert result['cache_rate_applied'] is True


def test_cached_input_without_published_rate_bills_full_rate():
    """No cache rate in the snapshot: cached tokens bill at the input rate, never $0."""
    plain = price_usage(TABLE, 'anthropic.claude-haiku-3-5', 1_000_000, 0)
    cached = price_usage(
        TABLE, 'anthropic.claude-haiku-3-5', 1_000_000, 0, cached_input_tokens=900_000
    )
    assert cached['cache_rate_applied'] is False
    assert cached['cost_usd'] == plain['cost_usd'] == pytest.approx(0.8)


def test_cached_tokens_cannot_exceed_input():
    """Cached input is a subset of input; a larger count is rejected."""
    with pytest.raises(ValueError, match='cannot exceed'):
        price_usage(TABLE, 'anthropic.claude-haiku-4-5', 100, 0, cached_input_tokens=101)


def test_cache_billing_flips_compare_winner(tmp_path):
    """Cache billing changes which model wins a cache-heavy comparison."""
    table = _fixture_table(
        tmp_path,
        [
            {
                'model_id': 'x.plain',
                'display_name': 'Plain',
                'provider': 'x',
                'input_per_mtok': 1.0,
                'output_per_mtok': 0.0,
                'checked_date': '2026-01-01',
            },
            {
                'model_id': 'x.cache',
                'display_name': 'Cache',
                'provider': 'x',
                'input_per_mtok': 2.0,
                'output_per_mtok': 0.0,
                'cached_input_per_mtok': 0.1,
                'checked_date': '2026-01-01',
            },
        ],
    )
    uncached = compare_models_for_task(table, 1_000_000, 0)
    assert uncached['ranked'][0]['model'] == 'x.plain'
    cached = compare_models_for_task(table, 1_000_000, 0, cached_input_tokens=900_000)
    assert cached['ranked'][0]['model'] == 'x.cache'
    assert cached['ranked'][0]['cost_per_run_usd'] == pytest.approx(0.29)
