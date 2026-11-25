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

"""awslabs Agent Cost MCP Server implementation.

Tools to estimate, budget, and compare the cost of LLM work before and
during an agent run — the model-spend counterpart to AWS infrastructure
cost tooling. Self-contained: a maintained pricing snapshot ships with
the server, no AWS account or API key is needed, all state is a local
JSON ledger, and no network calls are made at runtime.

Pricing and the cost-per-success model are a port of tokenecon
(https://pypi.org/project/tokenecon/, paper:
https://doi.org/10.5281/zenodo.23195511).
"""

from awslabs.agent_cost_mcp_server import ledger as ledger_mod
from awslabs.agent_cost_mcp_server import pricing
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.agent-cost-mcp-server',
    instructions=(
        'Tools for estimating, budgeting, and comparing the cost of LLM work per task. '
        'Use price_usage to price a concrete usage record, estimate_run_cost to price an '
        'expected workload across models, compare_models_for_task to rank models by cost '
        'per successful task, record_spend to log actual usage in a local per-task '
        'ledger, and budget_status to check recorded spend against a budget.'
    ),
    dependencies=[
        'loguru',
        'pydantic',
    ],
)

_table = pricing.PricingTable()
_ledger = ledger_mod.Ledger()


@mcp.tool()
def price_usage(
    model_id: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0
) -> dict:
    """Price a concrete usage record at a model's list rates.

    Args:
        model_id: Model identifier from the pricing snapshot, e.g.
            "anthropic.claude-sonnet-4-5" or "openai.gpt-5-mini".
            Unknown models are refused with an error naming the model.
        input_tokens: Input (prompt) tokens consumed, including any
            cached input tokens.
        output_tokens: Output (completion) tokens consumed.
        cached_input_tokens: The part of input_tokens served from the
            provider's prompt cache. Billed at the model's published
            cache-read rate where the snapshot carries one, otherwise
            at the standard input rate; reported separately either way.

    Returns the input/output/total cost in USD, the cached/uncached
    input split, and the date the model's prices were last checked
    (with a stale flag when that check is over 90 days old).
    """
    return pricing.price_usage(_table, model_id, input_tokens, output_tokens, cached_input_tokens)


@mcp.tool()
def estimate_run_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    expected_attempts: float | None = None,
    attempts_source: str | None = None,
    cached_input_tokens: int = 0,
) -> dict:
    """Estimate what one run of a workload will cost on a model.

    Args:
        model_id: Model to price the workload on.
        input_tokens: Expected input tokens for one run.
        output_tokens: Expected output tokens for one run.
        expected_attempts: Optional expected attempts per solved task
            (at least 1.0). When given, the response also carries
            cost_per_solved_task_usd — the per-run cost times the
            attempts term — kept separate from the per-run cost.
        attempts_source: Where expected_attempts comes from: 'measured'
            for observed run history, 'prior' for an assumption. The
            label is returned with the estimate.
        cached_input_tokens: The part of input_tokens served from the
            provider's prompt cache, priced as in price_usage.

    Returns the model's cost plus the same workload priced on every
    other model in the snapshot, cheapest first. Every priced response
    carries the price source date and confidence.
    """
    return pricing.estimate_run_cost(
        _table,
        model_id,
        input_tokens,
        output_tokens,
        expected_attempts,
        attempts_source,
        cached_input_tokens,
    )


@mcp.tool()
def compare_models_for_task(
    input_tokens: int,
    output_tokens: int,
    success_rates: dict[str, float] | None = None,
    quality_floor: float | None = None,
    cached_input_tokens: int = 0,
) -> dict:
    """Rank models for a task by expected cost per successful task.

    Cost per token is the wrong ranking for agent work: a cheap model
    that fails half its tasks costs more per success than a pricier,
    reliable one. Pass measured success rates (0-1 per model_id) if you
    have them; models without a supplied rate are ranked on raw cost.
    Each row carries expected_attempts (1 / success rate).

    Args:
        input_tokens: Input tokens for one attempt at the task.
        output_tokens: Output tokens for one attempt at the task.
        success_rates: Optional map of model_id to success rate in (0, 1].
        quality_floor: Optional hard floor on the success rate in
            (0, 1]. Models below it — and models with no supplied rate
            to check against it — are excluded before ranking and
            reported in excluded_by_quality_floor.
        cached_input_tokens: The part of input_tokens served from the
            provider's prompt cache, priced as in price_usage. Cache
            billing can change which model wins.

    A success_rates entry naming a model outside the snapshot is an
    error naming the model, not a silent omission.
    """
    return pricing.compare_models_for_task(
        _table, input_tokens, output_tokens, success_rates, quality_floor, cached_input_tokens
    )


@mcp.tool()
def record_spend(
    task_id: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> dict:
    """Record a run's actual token usage in the local per-task ledger.

    Args:
        task_id: Caller-chosen identifier grouping one task's runs.
        model_id: Model the run used. Unknown models are refused with
            an error naming the model — an unpriced model is never
            booked into the ledger as $0.
        input_tokens: Actual input tokens consumed, including any
            cached input tokens.
        output_tokens: Actual output tokens consumed.
        cached_input_tokens: The part of input_tokens served from the
            provider's prompt cache, priced as in price_usage.

    Returns the recorded entry, priced at the model's list rates.
    """
    priced = pricing.price_usage(
        _table, model_id, input_tokens, output_tokens, cached_input_tokens
    )
    return _ledger.record(
        task_id, model_id, input_tokens, output_tokens, priced['cost_usd'], cached_input_tokens
    )


@mcp.tool()
def budget_status(task_id: str, budget_usd: float) -> dict:
    """Check a task's recorded spend against a budget.

    Args:
        task_id: The task identifier used with record_spend.
        budget_usd: The budget for the task, in USD.

    Returns spent, remaining, call count, and whether the task is over
    budget. This server supplies the numbers; enforcing the budget
    (stopping a run) belongs to the agent framework.
    """
    return _ledger.status(task_id, budget_usd)


def main() -> None:
    """Run the MCP server with CLI argument support."""
    logger.info('Starting awslabs.agent-cost-mcp-server')
    mcp.run()


if __name__ == '__main__':
    main()
