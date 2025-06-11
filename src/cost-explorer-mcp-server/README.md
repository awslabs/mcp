# Cost Explorer MCP Server

MCP server for analyzing AWS costs and usage data through the AWS Cost Explorer API.

## Features

### Analyze AWS costs and usage data

- Get detailed breakdown of your AWS costs by service, region, and other dimensions
- Understand how costs are distributed across various services
- Query historical cost data for specific time periods
- Filter costs by various dimensions, tags, and cost categories

### Query cost data with natural language

- Ask questions about your AWS costs in plain English
- Get instant answers about your AWS spending patterns
- Retrieve historical cost data with simple queries

### Generate cost reports and insights

- Generate comprehensive cost reports based on your AWS Cost Explorer data
- Get cost breakdowns by various dimensions (service, region, account, etc.)
- Analyze usage patterns and spending trends

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS Cost Explorer
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access AWS Cost Explorer API

## Installation

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



## Available Tools

The Cost Explorer MCP Server provides the following tools:

1. `get_today_date` - Get the current date and month to determine relevent data when answering last month.
2. `get_dimension_values` - Get available values for a specific dimension (e.g., SERVICE, REGION)
3. `get_tag_values` - Get available values for a specific tag key
4. `get_cost_and_usage` - Retrieve AWS cost and usage data with filtering and grouping options

## Example Usage

Here are some examples of how to use the Cost Explorer MCP Server:


### Get dimension values

```
What AWS services did I use last month?
```

### Generate a cost report

```
Show me my AWS costs for the last 3 months grouped by service in us-east-1 region
```

```
What were my EC2 costs excluding us-east-2 for January 2025?
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
