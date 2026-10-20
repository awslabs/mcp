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

"""Tests for the spend ledger and the MCP tool surface."""

import asyncio
from awslabs.agent_cost_mcp_server.ledger import Ledger
from awslabs.agent_cost_mcp_server.server import mcp


def test_record_and_status(tmp_path):
    """Recorded spend is summed per task and checked against the budget."""
    ledger = Ledger(path=tmp_path / 'ledger.json')
    ledger.record('task-1', 'anthropic.claude-haiku-4-5', 1_000_000, 0, 1.0)
    ledger.record('task-1', 'anthropic.claude-haiku-4-5', 0, 1_000_000, 5.0)
    ledger.record('task-2', 'openai.gpt-5-mini', 100, 100, 0.01)

    status = ledger.status('task-1', budget_usd=10.0)
    assert status['spent_usd'] == 6.0
    assert status['remaining_usd'] == 4.0
    assert status['calls'] == 2
    assert status['over_budget'] is False
    assert status['models_used'] == ['anthropic.claude-haiku-4-5']


def test_over_budget_and_unknown_task(tmp_path):
    """Over-budget tasks are flagged; unknown tasks report zero spend."""
    ledger = Ledger(path=tmp_path / 'ledger.json')
    ledger.record('task-1', 'openai.gpt-5', 1_000_000, 1_000_000, 11.25)
    assert ledger.status('task-1', budget_usd=10.0)['over_budget'] is True

    empty = ledger.status('never-seen', budget_usd=5.0)
    assert empty['spent_usd'] == 0
    assert empty['calls'] == 0


def test_all_five_tools_registered():
    """The server exposes exactly the five RFC tools."""
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        'price_usage',
        'estimate_run_cost',
        'compare_models_for_task',
        'record_spend',
        'budget_status',
    }
