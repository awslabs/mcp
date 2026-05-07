# AWS Calculator MCP Server

An AWS Labs MCP server that automates [AWS Pricing Calculator](https://calculator.aws) via Playwright to generate **shareable estimate links** with accurate pricing for all 159 AWS services.

## Overview

This server uses browser automation (Playwright + Chromium) to interact with the real AWS Pricing Calculator UI. Given a list of services and their configurations, it navigates, fills forms, saves the estimate, and returns a public shareable link with monthly costs.

```
Input:  "2x RDS PostgreSQL db.m6i.xlarge Multi-AZ, 100GB, sa-east-1"
Output: https://calculator.aws/#/estimate?id=8af239081d6d21010b29ecfb218657c2e73dfca1
        → $848.16 USD/month
```

## Prerequisites

- Python 3.10+
- Chromium browser (installed via `playwright install chromium`)

## Installation

```bash
# Via uvx (once published)
uvx awslabs.aws-calculator-mcp-server@latest

# Local development
cd src/aws-calculator-mcp-server
uv venv && uv sync --all-groups
uv run playwright install chromium
```

## Configuration

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "awslabs.aws-calculator-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-calculator-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Local Development

```json
{
  "mcpServers": {
    "awslabs.aws-calculator-mcp-server": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp/src/aws-calculator-mcp-server",
        "run", "awslabs.aws-calculator-mcp-server"
      ]
    }
  }
}
```

## Tools

### `create_estimate`

Creates a full AWS Pricing Calculator estimate with one or more services and returns a shareable link.

**Parameters:**
- `services` (list): List of service configurations, each with:
  - `service_name` (str): Exact service name from calculator (use `list_service_fields` to discover)
  - `region` (str, optional): Region display name (default: "South America (Sao Paulo)")
  - `config` (dict): Field label → value pairs

**Returns:** `{ estimate_url, monthly_cost, services: [{service_name, status, monthly_cost}] }`

**Example:**
```python
services=[
    {
        "service_name": "Amazon RDS for PostgreSQL",
        "region": "US East (N. Virginia)",
        "config": {
            "Nodes": "2",
            "_autosuggest:Select an instance": "db.m6i.xlarge",
            "Utilization (On-Demand only)": "100",
            "Storage amount": "200"
        }
    },
    {
        "service_name": "AWS Lambda",
        "config": {
            "Number of requests": "10",
            "_change:per month": "million per month",
            "Duration of each request (in ms)": "200",
            "Amount of memory allocated": "1024"
        }
    }
]
```

### `list_service_fields`

Lists all 159 supported services and their configurable fields.

**Parameters:**
- `service_name` (str, optional): Filter by service name substring

**Example:**
```python
list_service_fields(service_name="Lambda")
# Returns: {"AWS Lambda": {"description": "...", "fields": {...}}}
```

## Supported Services (159)

| Category | Count | Examples |
|----------|-------|----------|
| Compute | 16 | EC2, Lambda, Fargate, EKS, App Runner, Lightsail, EMR |
| Databases | 22 | RDS (6 engines), Aurora, DynamoDB, ElastiCache, Neptune, Redshift |
| Storage | 14 | S3, EBS, EFS, FSx (4 types), ECR, Backup |
| Networking | 11 | VPC, ELB, CloudFront, Route 53, API Gateway, Direct Connect |
| Messaging | 9 | SQS, SNS, EventBridge, Kinesis, MSK, MQ |
| Analytics | 12 | Athena, Glue, OpenSearch, EMR, QuickSight, Lake Formation |
| ML/AI | 21 | Bedrock, SageMaker, Rekognition, Textract, Comprehend, Polly |
| Security | 19 | WAF, Shield, GuardDuty, Inspector, KMS, Cognito, Macie |
| DevOps | 19 | CloudWatch, CloudTrail, CodeBuild, Step Functions, Config |
| IoT | 6 | IoT Core, Analytics, Greengrass, SiteWise |
| Media | 5 | MediaLive, MediaConvert, MediaConnect, MediaPackage |
| Other | 5 | WorkSpaces, Location Service, Directory Service |

## Config Field Syntax

Fields use the **exact label text** from the calculator UI. Special prefixes handle non-standard inputs:

| Prefix | Purpose | Example |
|--------|---------|---------|
| _(none)_ | Fill input by label | `"Storage amount": "100"` |
| `_autosuggest:` | Instance type search | `"_autosuggest:Select an instance": "db.m6i.xlarge"` |
| `_radio` | Click radio button | `"_radio": "Network Address Translation (NAT) Gateway"` |
| `_change:` | Change dropdown by visible text | `"_change:per month": "million per month"` |
| `<field>_unit` | Set unit dropdown for field | `"Storage amount_unit": "TB"` |

## Unit Dropdowns

Many calculator fields have multiplier units. Important defaults:

| Service | Field | Default Unit | Value Meaning |
|---------|-------|-------------|---------------|
| SQS | Standard queue requests | million per month | `1` = 1M requests |
| Lambda | Number of requests | per month | `100` = 100 requests |
| Kinesis | Number of records | per second | `1000` = 1K/s ≈ 2.6B/month |
| S3 | Storage | GB | Absolute value |
| RDS | Storage amount | GB | Absolute value |

## Pricing Accuracy

Cross-validated against the AWS Pricing Bulk API:

| Service | Calculator | API Price | Status |
|---------|-----------|-----------|--------|
| SQS (1M requests) | $0.40 | $0.40 | ✅ Exact |
| Lambda (100M req, 200ms, 1GB) | $346.47 | $346.47 | ✅ Exact |
| S3 (1TB + 1M PUT + 10M GET) | $32.00 | $32.00 | ✅ Exact |
| ElastiCache (2× cache.r6g.large) | $300.76 | $300.76 | ✅ Exact |
| Secrets Manager (50 secrets) | $20.50 | $20.50 | ✅ Exact |
| RDS PG (m6i.xl Multi-AZ) | $848.16 | $724 + Ext. Support | ✅ Correct |

## Testing

400 BDD certification scenarios covering all services and configuration variants.

```bash
cd src/aws-calculator-mcp-server
uv venv && uv sync --all-groups
uv run playwright install chromium

# Run all 400 scenarios
uv run pytest tests/ --tb=short

# Run by category
uv run pytest tests/ -m compute
uv run pytest tests/ -m database

# Run specific service
uv run pytest tests/ -k "rds_for_postgresql"

# Run specific variant
uv run pytest tests/ -k "Single-AZ-General Purpose SSD (gp3)"
```

## Architecture

```
awslabs/aws_calculator_mcp_server/
├── server.py           # MCP server entry point (FastMCP)
├── calculator.py       # Playwright browser automation
└── service_fields.py   # 159 services × 694 fields configuration

tests/
├── features/calculator_services.feature  # 400 Gherkin scenarios
├── step_defs/test_calculator_steps.py    # Step implementations
└── conftest.py                           # Shared browser fixture
```

## How It Works

1. **Search** — navigates to calculator.aws and searches for the service
2. **Configure** — clicks the Configure button (matched by `aria-label`)
3. **Region** — selects region from the Cloudscape dropdown
4. **Fill fields** — fills inputs by `aria-label` match, handles autosuggests and radio buttons
5. **Save** — clicks "Save and add service"
6. **Share** — navigates to estimate page, clicks Share, extracts the public URL

## Limitations

- Requires Chromium browser (headless) — adds ~20-30 seconds per service
- Calculator UI may change — field labels are scraped and may need updates
- Some services have complex conditional forms (fields appear after radio selections)
- Unit dropdowns must be understood by the caller (see table above)

## License

Apache-2.0
