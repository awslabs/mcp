# Amazon Connect MCP Server

A Model Context Protocol (MCP) server for Amazon Connect that generates realtime and historical contact center reports from natural language. It wraps read-only Amazon Connect APIs so an assistant (for example, in Amazon Q) can answer questions about agents, calls, queues, and other contact center data.

## Features

- **Resource discovery**: Find the instances, queues, agents, and routing profiles you can report on.
- **Realtime reporting**: Inspect current queue depth, oldest contact age, agent availability, and per-agent status.
- **Historical reporting**: Build reports over the last 90 days (contacts handled/abandoned, average handle time, service level, occupancy, and more) grouped by queue, channel, agent, or routing profile. Ranges wider than 24 hours are automatically split into 24-hour intervals.
- **Read-only and least privilege**: Every tool issues only describe/list/get calls. The server never mutates Connect configuration or contacts.
- **Multi-profile / multi-region**: Each tool accepts optional `region` and `profile_name` arguments and otherwise honors `AWS_REGION` / `AWS_PROFILE`.

## Tools

### Discovery

| Tool | Description |
|------|-------------|
| `list_connect_instances` | List the Amazon Connect instances in the account/region. Returns the `instance_id` needed by other tools. |
| `list_queues` | List queues in an instance (optionally filtered by `STANDARD`/`AGENT`). |
| `list_agents` | List agents (users) in an instance. |
| `list_routing_profiles` | List routing profiles in an instance. |

### Realtime (current) reporting

| Tool | Underlying API | Description |
|------|----------------|-------------|
| `get_current_metric_data` | `GetCurrentMetricData` | Current metrics such as `CONTACTS_IN_QUEUE`, `OLDEST_CONTACT_AGE`, `AGENTS_AVAILABLE`, `AGENTS_ONLINE`, optionally grouped by `QUEUE`, `CHANNEL`, or `ROUTING_PROFILE`. |
| `get_current_agent_status` | `GetCurrentUserData` | Current agent status (Available, On Contact, ACW, Offline), time in status, routing profile, available slots, and active contacts. |

### Historical reporting

| Tool | Underlying API | Description |
|------|----------------|-------------|
| `get_historical_metric_data` | `GetMetricDataV2` | Historical metrics (e.g., `CONTACTS_HANDLED`, `CONTACTS_ABANDONED`, `AVG_HANDLE_TIME`, `SERVICE_LEVEL`, `ABANDONMENT_RATE`, `AGENT_OCCUPANCY`) over a time window, grouped by queue, channel, agent, or routing profile. |

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/).
2. Install Python 3.10 or newer: `uv python install 3.10`.
3. Configure AWS credentials with permission to call Amazon Connect read APIs.

### Required IAM permissions

The credentials used by the server need read-only access to Amazon Connect. A minimal policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "connect:ListInstances",
        "connect:DescribeInstance",
        "connect:ListQueues",
        "connect:ListUsers",
        "connect:ListRoutingProfiles",
        "connect:GetCurrentMetricData",
        "connect:GetCurrentUserData",
        "connect:GetMetricDataV2"
      ],
      "Resource": "*"
    }
  ]
}
```

Scope `Resource` to specific instance ARNs where possible.

## Installation

Add the server to your MCP client configuration.

### Kiro (`~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "awslabs.amazon-connect-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-connect-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Amazon Q

Register the same `command`/`args`/`env` block in your Amazon Q MCP configuration. Once connected, ask questions in natural language, for example:

- "How many contacts are waiting in the Sales queue right now?"
- "Which agents are currently available in instance abcd-1234?"
- "Show me the average handle time and service level by queue for yesterday."
- "What was the abandonment rate per channel over the last 7 days?"

## Local development

Run directly from source:

```json
{
  "mcpServers": {
    "awslabs.amazon-connect-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/src/amazon-connect-mcp-server/awslabs/amazon_connect_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Build and test:

```bash
cd src/amazon-connect-mcp-server
uv venv && uv sync --all-groups
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## Usage notes

- `get_historical_metric_data` retains data for the **last 90 days**; older `start_time` values are rejected. The Amazon Connect API limits a single request to a 24-hour window, so the tool automatically splits wider ranges into consecutive 24-hour intervals and returns one set of result rows per interval (each tagged with `interval_start`/`interval_end`). Average and rate metrics are reported per interval and are not aggregated across intervals.
- `get_current_agent_status` requires at least one of `queue_ids` or `agent_ids` to scope the request.
- Metric names and groupings are validated against the Amazon Connect API catalog. See the [GetMetricDataV2](https://docs.aws.amazon.com/connect/latest/APIReference/API_GetMetricDataV2.html) and [GetCurrentMetricData](https://docs.aws.amazon.com/connect/latest/APIReference/API_GetCurrentMetricData.html) references for the full set.

## License

This project is licensed under the Apache-2.0 License.
