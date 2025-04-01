# Cost Analysis MCP Server

An AWS Labs Model Context Protocol (MCP) server for Cost Analysis of the AWS services

## Features

- **Analyze and visualize AWS costs** - Get detailed breakdown of your AWS costs by service, region and tier
  - Understand how costs are distributed across various services

- **Query cost data with natural language** - Ask questions about your AWS costs in plain English, no complex query languages required
  -  Get instant answers fetched from pricing webpage and AWS Pricing API, for questions related to AWS services

- **Generate cost reports and insights** -  Generate comprehensive cost reports based on your IaC implementation
  - Get cost optimization recommendations

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`
3. Set up AWS credentials with access to Amazon Bedrock
   - You need an AWS account with Amazon Bedrock and desired models enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas

## Installation

Install the MCP server:

Add the server to your MCP client config (e.g. for Amazon Q CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cost-analysis-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",  // Optional: specify AWS profile
        "AWS_REGION": "us-east-1"           // Required: region where Bedrock is available
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
  "AWS_PROFILE": "your-aws-profile",  // Specify which AWS profile to use
  "AWS_REGION": "us-east-1"           // Region where Bedrock is available
}
```

Make sure the AWS profile has permissions to access Amazon Bedrock and desired model. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for using the Amazon Bedrock model APIs.
