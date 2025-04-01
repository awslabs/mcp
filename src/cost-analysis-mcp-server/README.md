# Cost Analysis MCP Server

MCP server for analyzing AWS service costs and generating cost reports

## Features

- **Analyze and visualize AWS costs** - Get detailed breakdown of your AWS costs by service, region and tier
  - Understand how costs are distributed across various services

- **Query cost data with natural language** - Ask questions about your AWS costs in plain English, no complex query languages required
  - Get instant answers fetched from pricing webpage and AWS Pricing API, for questions related to AWS services

- **Generate cost reports and insights** - Generate comprehensive cost reports based on your IaC implementation
  - Get cost optimization recommendations

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access AWS Pricing API

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
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

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the AWS Pricing API. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.
