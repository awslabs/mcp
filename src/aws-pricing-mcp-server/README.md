# AWS Pricing MCP Server

MCP server for generating upfront AWS service cost estimates and providing cost insights

**Important Note**: This server provides estimated pricing based on AWS pricing APIs and web pages. These estimates are for pre-deployment planning purposes and do not reflect the actual expenses of deployed cloud services.

## Features

### Analyze and visualize AWS costs

- Get detailed breakdown of your AWS costs by service, region and tier
- Understand how costs are distributed across various services
- Provide pre-deployment cost estimates for infrastructure planning
- Support for analyzing both CDK and Terraform projects to identify AWS services

### Query cost data with natural language

- Ask questions about your AWS costs in plain English, no complex query languages required
- Get instant answers fetched from pricing webpage and AWS Pricing API, for questions related to AWS services
- Retrieve estimated pricing information before actual cloud service deployment

### Generate cost reports and insights

- Generate comprehensive cost estimates based on your IaC implementation
- Get cost optimization recommendations for potential cloud infrastructure
- Provide upfront pricing analysis to support informed decision-making

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access AWS Pricing API

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aws-pricing-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY29zdC1hbmFseXNpcy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-pricing-mcp-server@latest"],
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

or docker after a successful `docker build -t awslabs/aws-pricing-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.aws-pricing-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/aws-pricing-mcp-server:latest"
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

Make sure the AWS profile has permissions to access the AWS Pricing API. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.
