# Cost Explorer MCP Server

MCP server for analyzing AWS costs and usage data through the AWS Cost Explorer API.

## Features

### Analyze AWS costs and usage data

- Get detailed breakdown of your AWS costs by service, region, and other dimensions
- Understand how costs are distributed across various services
- Query historical cost data for specific time periods
- Filter costs by various dimensions, tags, and cost categories


### Compare costs between time periods

- **NEW AWS Feature**: Leverage AWS Cost Explorer's new [Cost Comparison feature](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-cost-comparison.html)
- Compare costs between two time periods to identify changes and trends
- Analyze cost drivers to understand what caused cost increases or decreases
- Get detailed insights into the top 10 most significant cost change drivers automatically
- Identify specific usage types, discount changes, and infrastructure changes affecting costs

### Forecast future costs

- Generate cost forecasts based on historical usage patterns
- Get predictions with confidence intervals (80% or 95%)
- Support for daily and monthly forecast granularity
- Plan budgets and anticipate future AWS spending

### Query cost data with natural language

- Ask questions about your AWS costs in plain English
- Get instant answers about your AWS spending patterns
- Retrieve historical cost data with simple queries


## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS Cost Explorer
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access AWS Cost Explorer API

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.cost-explorer-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY29zdC1leHBsb3Jlci1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cost-explorer-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-explorer-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/cost-explorer-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
```

```json
{
  "mcpServers": {
    "awslabs.cost-explorer-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/cost-explorer-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

NOTE: Your credentials will need to be kept refreshed from your host

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the AWS Cost Explorer API. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.

## Cost Considerations

**Important:** AWS Cost Explorer API incurs charges on a per-request basis. Each API call made by this MCP server will result in charges to your AWS account.

- **Cost Explorer API Pricing:** The AWS Cost Explorer API lets you directly access the interactive, ad-hoc query engine that powers AWS Cost Explorer. Each request will incur a cost of $0.01.
- Each tool invocation that queries Cost Explorer (get_dimension_values, get_tag_values, get_cost_and_usage) will generate at least one billable API request
- Complex queries with multiple filters or large date ranges may result in multiple API calls

For current pricing information, please refer to the [AWS Cost Explorer Pricing page](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/).


## Security Considerations

### Required IAM Permissions
The following IAM permissions are required for this MCP server:
- ce:GetCostAndUsage
- ce:GetDimensionValues
- ce:GetTags
- ce:GetCostForecast
- ce:GetCostAndUsageComparisons
- ce:GetCostComparisonDrivers



## Available Tools

The Cost Explorer MCP Server provides the following tools:

1. `get_today_date` - Get the current date and month to determine relevent data when answering last month.
2. `get_dimension_values` - Get available values for a specific dimension (e.g., SERVICE, REGION)
3. `get_tag_values` - Get available values for a specific tag key
4. `get_cost_and_usage` - Retrieve AWS cost and usage data with filtering and grouping options
5. `get_cost_and_usage_comparisons` - Compare costs between two time periods to identify changes and trends
6. `get_cost_comparison_drivers` - Analyze what drove cost changes between periods (top 10 most significant drivers)
7. `get_cost_forecast` - Generate cost forecasts based on historical usage patterns

## Example Usage

Here are some examples of how to use the Cost Explorer MCP Server through natural language queries:

### Cost Analysis Examples

```
Show me my AWS costs for the last 3 months grouped by service in us-east-1 region
Break down my S3 costs by storage class for Q1 2025
Show me costs for production resources tagged with Environment=prod
What were my costs for reserved instances vs on-demand in May?
What was my EC2 instance usage by instance type?
```

### Cost Comparison Examples

```
Compare my AWS costs between April and May 2025
How did my EC2 costs change from last month to this month?
Why did my AWS bill increase in June compared to May?
What caused the spike in my S3 costs last month?
```

### Forecasting Examples

```
Forecast my AWS costs for next month
Predict my EC2 spending for the next quarter
What will my total AWS bill be for the rest of 2025?
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
