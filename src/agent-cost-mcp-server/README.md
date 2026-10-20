# Agent Cost MCP Server

MCP server for estimating, budgeting, and comparing the cost of LLM work before and during an agent run — the model-spend counterpart to AWS infrastructure cost tooling.

Agent frameworks decide for themselves how many model calls a task takes, so the cost of a run is usually only visible after the bill arrives. This server answers, from inside your tooling:

- *What will this task cost on model A vs model B?*
- *Which model is cheapest per **successful** task, not per token?*
- *Has this run already burned its budget?*

The server is self-contained: a maintained pricing snapshot ships with it, no AWS account or API key is needed, all state is a local JSON ledger, and it makes no network calls at runtime.

## Features

- **Usage pricing**: Price a concrete usage record (model, input/output tokens) at list rates, with the input/output cost split
- **Run cost estimation**: Estimate one run of a workload on a model, with the same workload priced on every other model in the snapshot, cheapest first
- **Cost-per-success ranking**: Rank models by expected cost per successful task (cost per attempt ÷ success rate), using measured success rates where you have them
- **Per-task spend ledger**: Record actual token usage per task in a local JSON ledger, priced at list rates
- **Budget checks**: Check a task's recorded spend against a budget — spent, remaining, call count, and over-budget flag

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

No AWS account, credentials, or network access are required — pricing data ships with the server as a versioned snapshot.

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.agent-cost-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.agent-cost-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.agent-cost-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYWdlbnQtY29zdC1tY3Atc2VydmVyQGxhdGVzdCIsCiAgICAiZW52IjogewogICAgICAgICJGQVNUTUNQX0xPR19MRVZFTCI6ICJFUlJPUiIKICAgIH0sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJhdXRvQXBwcm92ZSI6IFtdCn0=) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Agent%20Cost%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.agent-cost-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### ⚡ Using uv

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.agent-cost-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.agent-cost-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**For Windows users:**

```json
{
  "mcpServers": {
    "awslabs.agent-cost-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.agent-cost-mcp-server@latest",
        "awslabs.agent-cost-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using Docker

After a successful `docker build -t awslabs/agent-cost-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.agent-cost-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/agent-cost-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Tools

### price_usage

Price a concrete usage record at a model's list rates.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `model_id` | string | Model identifier from the pricing snapshot, e.g. `anthropic.claude-sonnet-4-5` or `openai.gpt-5-mini` |
| `input_tokens` | integer | Input (prompt) tokens consumed |
| `output_tokens` | integer | Output (completion) tokens consumed |

**Returns:** The model, token counts, and the input, output, and total cost in USD.

### estimate_run_cost

Estimate what one run of a workload will cost on a model.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `model_id` | string | Model to price the workload on |
| `input_tokens` | integer | Expected input tokens for one run |
| `output_tokens` | integer | Expected output tokens for one run |

**Returns:** The model's cost for the run, plus the same workload priced on every other model in the snapshot, cheapest first, and the pricing snapshot version.

### compare_models_for_task

Rank models for a task by expected cost per successful task.

Cost per token is the wrong ranking for agent work: a cheap model that fails half its tasks costs more per success than a pricier, reliable one. Pass measured success rates if you have them; models without a supplied rate are ranked on raw cost.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `input_tokens` | integer | Input tokens for one attempt at the task |
| `output_tokens` | integer | Output tokens for one attempt at the task |
| `success_rates` | object | Optional map of `model_id` to success rate in (0, 1] |

**Returns:** All models ranked by cost per successful task, with cost per run and the success rate used for each.

### record_spend

Record a run's actual token usage in the local per-task ledger.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Caller-chosen identifier grouping one task's runs |
| `model_id` | string | Model the run used |
| `input_tokens` | integer | Actual input tokens consumed |
| `output_tokens` | integer | Actual output tokens consumed |

**Returns:** The recorded ledger entry, priced at the model's list rates, with a UTC timestamp.

### budget_status

Check a task's recorded spend against a budget.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | The task identifier used with `record_spend` |
| `budget_usd` | number | The budget for the task, in USD |

**Returns:** Spent, budget, remaining, over-budget flag, call count, and the models used. This server supplies the numbers; enforcing the budget (stopping a run) belongs to the agent framework.

## Pricing snapshot

Prices live in `awslabs/agent_cost_mcp_server/pricing.json` — a versioned snapshot of list prices (USD per 1M tokens) for major Amazon Bedrock and OpenAI-compatible models, dated in the file. Prices change; verify against the provider's pricing page before making spending decisions. Updating the snapshot is a one-file change, and the server reads it at startup.

## Ledger

`record_spend` appends to a local JSON ledger at `~/.agent-cost-mcp-server/ledger.json`. Set `AGENT_COST_LEDGER_PATH` to use a different file. Nothing leaves the machine.

## Background

The pricing and cost-per-success model are a port of [tokenecon](https://pypi.org/project/tokenecon/), an open-source library for per-task agent cost accounting (paper: [doi.org/10.5281/zenodo.23195511](https://doi.org/10.5281/zenodo.23195511)), including a Strands integration that prices live agent runs. This server exposes the same math over MCP so any agent or IDE can call it, and implements [RFC #4772](https://github.com/awslabs/mcp/issues/4772). A standalone version is maintained at [karmendra8386/agent-cost-mcp-server](https://github.com/karmendra8386/agent-cost-mcp-server).

## Development

```bash
uv sync --all-groups
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
