# MCP Server Setup Instructions

This skill uses two MCP servers:
- **CloudWatch MCP Server** — CloudWatch Logs Insights queries, log group discovery, metrics
- **Application Signals MCP Server** (optional) — Application Signals traces and service maps for correlated trace views

## Prerequisites

```bash
uv --version
```

**If missing:** Install from [Astral](https://docs.astral.sh/uv/getting-started/installation/)

## General MCP Configuration

### CloudWatch Only (minimum required)

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### CloudWatch + Application Signals (recommended)

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "cloudwatch-appsignals": {
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-applicationsignals-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Optional Environment Variables

| Variable | When Needed |
|----------|-------------|
| `AWS_PROFILE` | Non-default AWS profile |
| `AWS_REGION` | Override default region for CloudWatch queries |

## Example: Kiro CLI

[Kiro CLI](https://kiro.dev/docs/cli/) supports MCP servers via agent definitions. To use this skill with Kiro, create an agent that references the CloudWatch MCP servers.

### Agent definition

Create `~/.kiro/agents/agentcore-investigator.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/aws/amazon-q-developer-cli/refs/heads/main/schemas/agent-v1.json",
  "name": "agentcore-investigator",
  "description": "Investigate AgentCore runtime sessions via CloudWatch Logs Insights",
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "cloudwatch-appsignals": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-applicationsignals-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  },
  "resources": [
    "skill://.kiro/skills/cloudwatch-agentcore-investigator/SKILL.md"
  ],
  "tools": [
    "fs_read",
    "fs_write",
    "execute_bash",
    "@cloudwatch",
    "@cloudwatch-appsignals"
  ]
}
```

### Launch

```bash
kiro-cli chat --agent agentcore-investigator
```

### Verification

The agent welcome message should confirm MCP servers are connected. Run `investigate session <SESSION_ID>` to test.
