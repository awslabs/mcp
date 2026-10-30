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

"""Tests that invoke the MCP tool functions directly."""

import pytest
from awslabs.agent_cost_mcp_server.ledger import Ledger
from awslabs.agent_cost_mcp_server.server import (
    budget_status,
    compare_models_for_task,
    estimate_run_cost,
    price_usage,
    record_spend,
)


def test_price_usage_tool():
    """The price_usage tool prices a usage record."""
    result = price_usage('anthropic.claude-haiku-4-5', 1_000_000, 1_000_000)
    assert result['cost_usd'] == 6.0


def test_estimate_run_cost_tool():
    """The estimate_run_cost tool prices a run plus alternatives."""
    result = estimate_run_cost('openai.gpt-5-mini', 10_000, 2_000)
    assert result['model'] == 'openai.gpt-5-mini'
    assert len(result['alternatives']) == 17


def test_compare_models_for_task_tool():
    """The compare tool ranks every model in the snapshot."""
    result = compare_models_for_task(10_000, 2_000)
    assert len(result['ranked']) == 18
    costs = [r['cost_per_success_usd'] for r in result['ranked']]
    assert costs == sorted(costs)


def test_record_spend_and_budget_status_tools():
    """Spend recorded through the tool is visible to budget_status."""
    entry = record_spend('tools-test-task', 'anthropic.claude-haiku-4-5', 1_000_000, 0)
    assert entry['cost_usd'] == 1.0

    status = budget_status('tools-test-task', 2.0)
    assert status['spent_usd'] == 1.0
    assert status['over_budget'] is False


def test_ledger_rejects_negative_budget(tmp_path):
    """A negative budget is rejected."""
    ledger = Ledger(path=tmp_path / 'ledger.json')
    with pytest.raises(ValueError, match='non-negative'):
        ledger.status('task-1', budget_usd=-1.0)


def test_ledger_load_missing_and_empty_file(tmp_path):
    """Missing and empty ledger files both read as no entries."""
    missing = Ledger(path=tmp_path / 'missing.json')
    assert missing.status('task-1', budget_usd=1.0)['calls'] == 0

    empty_path = tmp_path / 'empty.json'
    empty_path.write_text('')
    empty = Ledger(path=empty_path)
    assert empty.status('task-1', budget_usd=1.0)['spent_usd'] == 0
