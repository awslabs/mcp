# AWS Pricing MCP Server

MCP server for accessing real-time AWS pricing information and providing cost analysis capabilities

**Important Note**: This server provides real-time pricing data from the AWS Pricing API. We cannot guarantee that AI assistants will always construct filters correctly or identify the absolute cheapest options. All calls are free of charge.

## Features

### AWS Pricing Discovery & Information

- **Service catalog exploration**: Discover all AWS services with available pricing information
- **Pricing attribute discovery**: Identify filterable dimensions (instance types, regions, storage classes, etc.) for any AWS service
- **Real-time pricing queries**: Access current pricing data with advanced filtering capabilities including multi-option comparisons and pattern matching
- **Multi-region pricing comparisons**: Compare pricing across different AWS regions in a single query
- **Bulk pricing data access**: Download complete pricing datasets in CSV/JSON formats for historical analysis and offline processing

### Cost Analysis & Planning

- **Detailed cost report generation**: Create comprehensive cost analysis reports with unit pricing, calculation breakdowns, and usage scenarios
- **Infrastructure project analysis**: Scan CDK and Terraform projects to automatically identify AWS services and their configurations
- **Architecture pattern guidance**: Get detailed architecture patterns and cost considerations, especially for Amazon Bedrock services
- **Cost optimization recommendations**: Receive AWS Well-Architected Framework aligned suggestions for cost optimization

### Query pricing data with natural language

- Ask questions about AWS pricing in plain English, no complex query languages required
- Get instant answers from the AWS Pricing API for any AWS service
- Retrieve comprehensive pricing information with flexible filtering options

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has `pricing:*` permissions to access the AWS Pricing API

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-pricing-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYXdzLXByaWNpbmctbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Pricing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### ⚡ Using uv

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):


**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
         "awslabs.aws-pricing-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
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
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
         "--from",
         "awslabs.aws-pricing-mcp-server@latest",
         "awslabs.aws-pricing-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using Docker

or docker after a successful `docker build -t awslabs/aws-pricing-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
AWS_REGION=us-east-1
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

The MCP server requires specific AWS permissions and configuration:

#### Required Permissions
Your AWS IAM role or user must have `pricing:*` permissions to access the AWS Pricing API. The server only accesses generally available AWS pricing information and does not retrieve any user-specific data. All pricing API calls are **free of charge** and do not incur any costs.

#### Configuration
The server uses two key environment variables:

- **`AWS_PROFILE`**: Specifies the AWS profile to use from your AWS configuration file. If not provided, it defaults to the "default" profile.
- **`AWS_REGION`**: Determines the geographically closest AWS Pricing API endpoint to use. This improves performance by routing requests to the nearest regional endpoint.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```
