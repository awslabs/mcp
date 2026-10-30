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
def price_usage(model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Price a concrete usage record at a model's list rates.

    Args:
        model_id: Model identifier from the pricing snapshot, e.g.
            "anthropic.claude-sonnet-4-5" or "openai.gpt-5-mini".
        input_tokens: Input (prompt) tokens consumed.
        output_tokens: Output (completion) tokens consumed.

    Returns the input/output/total cost in USD.
    """
    return pricing.price_usage(_table, model_id, input_tokens, output_tokens)


@mcp.tool()
def estimate_run_cost(model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Estimate what one run of a workload will cost on a model.

    Args:
        model_id: Model to price the workload on.
        input_tokens: Expected input tokens for one run.
        output_tokens: Expected output tokens for one run.

    Returns the model's cost plus the same workload priced on every
    other model in the snapshot, cheapest first.
    """
    return pricing.estimate_run_cost(_table, model_id, input_tokens, output_tokens)


@mcp.tool()
def compare_models_for_task(
    input_tokens: int,
    output_tokens: int,
    success_rates: dict[str, float] | None = None,
) -> dict:
    """Rank models for a task by expected cost per successful task.

    Cost per token is the wrong ranking for agent work: a cheap model
    that fails half its tasks costs more per success than a pricier,
    reliable one. Pass measured success rates (0-1 per model_id) if you
    have them; models without a supplied rate are ranked on raw cost.

    Args:
        input_tokens: Input tokens for one attempt at the task.
        output_tokens: Output tokens for one attempt at the task.
        success_rates: Optional map of model_id to success rate in (0, 1].
    """
    return pricing.compare_models_for_task(_table, input_tokens, output_tokens, success_rates)


@mcp.tool()
def record_spend(task_id: str, model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Record a run's actual token usage in the local per-task ledger.

    Args:
        task_id: Caller-chosen identifier grouping one task's runs.
        model_id: Model the run used.
        input_tokens: Actual input tokens consumed.
        output_tokens: Actual output tokens consumed.

    Returns the recorded entry, priced at the model's list rates.
    """
    priced = pricing.price_usage(_table, model_id, input_tokens, output_tokens)
    return _ledger.record(task_id, model_id, input_tokens, output_tokens, priced['cost_usd'])


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
