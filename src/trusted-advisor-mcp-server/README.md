# AWS Trusted Advisor MCP Server

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that gives AI assistants direct access to [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/) recommendations. Ask plain questions about your AWS account health and get real-time answers backed by live Trusted Advisor data.

## Features

- **List Checks** - Browse all available Trusted Advisor checks, optionally filtered by pillar or service
- **List Recommendations** - View current findings with status, affected resources, and estimated savings
- **Deep Dive** - Get detailed info for any recommendation including all affected resources
- **Cost Optimization Summary** - Total estimated monthly/annual savings in one call
- **Security Summary** - Quick security posture snapshot with active issues highlighted
- **Service Limits Summary** - Identify services approaching or exceeding their quotas
- **Lifecycle Management** - Update recommendation status (dismiss, resolve, mark in progress)
- **Organization Support** - View recommendations across all accounts in AWS Organizations (management account only)

## Requirements

- **Python**: 3.10 or higher
- **AWS Credentials**: Configured via environment variables, AWS CLI profiles, or IAM roles
- **AWS Support Plan**: Business, Enterprise On-Ramp, or Enterprise Support (required for Trusted Advisor API access)

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/trusted-advisor-mcp-server
uv sync
```

After `uv sync`, the `awslabs.trusted-advisor-mcp-server` entry point is registered and `uv run` handles the virtual environment automatically — no manual activation needed.

### Using uvx (once published to PyPI)

```bash
uvx awslabs.trusted-advisor-mcp-server
```

## MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "trusted-advisor": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/trusted-advisor-mcp-server",
        "awslabs.trusted-advisor-mcp-server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Kiro CLI (Amazon Q Developer)

Create `~/.kiro/agents/trusted-advisor.json`:

```json
{
  "name": "trusted-advisor",
  "description": "AWS account health analysis via Trusted Advisor — security, cost, performance, and service limits",
  "mcpServers": {
    "trusted-advisor": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/trusted-advisor-mcp-server",
        "awslabs.trusted-advisor-mcp-server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  },
  "tools": ["*"],
  "allowedTools": [
    "trusted-advisor__list_trusted_advisor_checks",
    "trusted-advisor__list_recommendations",
    "trusted-advisor__get_recommendation",
    "trusted-advisor__get_security_summary",
    "trusted-advisor__get_cost_optimization_summary",
    "trusted-advisor__get_service_limits_summary",
    "trusted-advisor__list_organization_recommendations"
  ],
  "resources": [],
  "hooks": { "userPromptSubmit": [], "agentSpawn": [] },
  "toolsSettings": {},
  "useLegacyMcpJson": true
}
```

Then run:

```bash
cd /path/to/trusted-advisor-mcp-server
kiro-cli chat --agent=trusted-advisor
```

### Amazon Q Developer CLI / Cursor / VS Code

```json
{
  "mcpServers": {
    "trusted-advisor": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/trusted-advisor-mcp-server",
        "awslabs.trusted-advisor-mcp-server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

> **Note:** Replace `/path/to/trusted-advisor-mcp-server` with the actual clone path. Add `"AWS_PROFILE": "your-profile"` to `env` if you need a specific AWS profile. The Trusted Advisor API is a global service — `us-east-1` is the recommended region.

## Example Conversations

These examples show real responses from a live AWS account.

### Security review

> **You:** "Show me the security status of our AWS account"

```
Security Summary (23 checks total)

✅ OK:       15
⚠️  Warning:   3
🔴 Error:     5

Errors (immediate action needed):
  - Lambda deprecated runtimes          9 functions affected
  - IAM Access Analyzer not enabled    17 regions missing
  - Security Groups unrestricted        3 groups
  - Security Groups specific ports      2 groups
  - Well-Architected high risk issue    1 finding

Warnings:
  - ALB Target Group protocol           3 resources
  - CloudFront origin SSL certificate   3 distributions
  - IAM access key rotation             1 key
```

### Drilling into a finding

> **You:** "Tell me more about the IAM Access Analyzer issue"

```
IAM Access Analyzer is not enabled in 17 regions:
ap-east-1, ap-northeast-1, ap-northeast-2, ap-northeast-3,
ap-south-1, ap-southeast-1, ap-southeast-2, eu-central-1,
eu-north-1, eu-west-1, eu-west-2, eu-west-3, sa-east-1,
us-east-1, us-east-2, us-west-1, us-west-2

Without it, externally accessible resources (S3 buckets, IAM roles,
Lambda functions, etc.) won't be detected automatically.
This is a free feature — enable it across all regions with a single CLI loop.
```

### Cost optimization

> **You:** "How much could I save on my AWS bill?"

```
Cost Optimization Opportunities

Estimated savings:  $270.60/month  ($3,247/year)
Total findings:     10 recommendations

Top items:
  1. Underutilized EC2 instances     $150.61/mo   2 instances
  2. Idle EBS volumes                 $57.71/mo  12 volumes
  3. EBS volume type optimization     $35.93/mo   9 volumes
  4. EC2 rightsizing                  $24.45/mo   4 instances
  5. Fargate rightsizing               $1.89/mo   1 task

Additional (savings not estimated):
  - S3 incomplete multipart uploads   52 objects
  - Idle VPC interface endpoints      15 endpoints
  - Idle NAT Gateways                  2 gateways
  - Lambda over-provisioned memory     1 function
```

### Service limits check

> **You:** "Am I approaching any AWS service limits?"

The assistant runs `get_service_limits_summary` and lists any services near their quotas.

### Account health score

> **You:** "Give me an overall health score for this AWS account"

The assistant calls `get_account_score` and returns something like:

```
## AWS Trusted Advisor Account Score

Overall Score: 72/100  (Grade: C)

Total checks: 125  |  ✅ OK: 112  |  ⚠️ Warning: 7  |  🔴 Error: 6

### Pillar Breakdown
- Security: 68/100  [██████░░░░]
  ✅ 15  ⚠️ 3  🔴 5
- Cost Optimization: 74/100  [███████░░░]
  ✅ 57  ⚠️ 5  🔴 0
- Fault Tolerance: 61/100  [██████░░░░]
  ✅ 12  ⚠️ 0  🔴 2
...

Several findings need attention. Review warnings and errors.
```

### Organization-wide analysis (management account only)

> **You:** "Show me priority recommendations across our organization"

The assistant calls `list_organization_recommendations` with `pillar="security"`.

> **Note:** This tool requires **Trusted Advisor Priority**, which is available to AWS Enterprise Support customers and must be activated by your Technical Account Manager (TAM). It is separate from the standard Organizational view in the Trusted Advisor console.

### Workflow integration

> **You:** "Dismiss the S3 versioning recommendation — we manage versioning ourselves"

The assistant confirms and calls `update_recommendation_lifecycle` with `lifecycle_stage="dismissed"` and records the reason.

## Limitations

- **AWS Support plan required**: All Trusted Advisor API features require Business, Enterprise On-Ramp, or Enterprise Support. Developer and Basic plans have access to only a limited set of checks.
- **Organization-wide view**: The `list_organization_recommendations` tool uses the [Trusted Advisor Priority API](https://docs.aws.amazon.com/trustedadvisor/latest/APIReference/API_ListOrganizationRecommendations.html), which is only available with **Trusted Advisor Priority** (Enterprise Support + TAM activation). Standard Organizational view is not supported by this API.
- **Account score**: `get_account_score` calculates a score from live recommendation data. It is not the same as the score shown in the Trusted Advisor console, which uses an internal weighting model.


## Available Tools

| Tool | Description |
|------|-------------|
| `list_trusted_advisor_checks` | List all available checks with optional pillar or service filter |
| `list_recommendations` | List current recommendations filtered by status, pillar, service, or date |
| `get_recommendation` | Get detailed recommendation info including all affected resources |
| `get_cost_optimization_summary` | Aggregate cost findings with total estimated monthly/annual savings |
| `get_security_summary` | Security posture overview with counts by status and active issues |
| `get_service_limits_summary` | Services approaching or exceeding their AWS service quotas |
| `update_recommendation_lifecycle` | Update recommendation stage (dismissed, resolved, in_progress) |
| `get_account_score` | Overall health score (0-100) with per-pillar breakdown and letter grade |
| `list_organization_recommendations` | Priority recommendations across AWS Organizations (requires Trusted Advisor Priority) |

## IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "trustedadvisor:ListChecks",
        "trustedadvisor:ListRecommendations",
        "trustedadvisor:GetRecommendation",
        "trustedadvisor:ListRecommendationResources",
        "trustedadvisor:UpdateRecommendationLifecycle",
        "trustedadvisor:ListOrganizationRecommendations",
        "trustedadvisor:ListOrganizationRecommendationAccounts",
        "trustedadvisor:ListOrganizationRecommendationResources"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Tip:** For read-only access, omit `UpdateRecommendationLifecycle`.

## Development

### Setup

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/trusted-advisor-mcp-server
uv sync
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=awslabs --cov-report=term-missing

# Specific file
pytest tests/test_formatters.py
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
