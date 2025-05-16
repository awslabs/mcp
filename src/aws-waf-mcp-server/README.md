# AWS WAF MCP Server

MCP server for creating firewall rules in AWS WAF

## Features

### Create WAF ACL

- Use natural language to create an ACL. The tool include instructions with best practices for performance and costs

### Associate WAF ACL to ALB

- Associate the created web ACL using the name of the ALB.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python and dependencies using `uv python install 3.13` and `uv sync`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions. Ensure your IAM role/user has permissions to create WAF ACLs and associate resources.
   - Configure AWS credentials profile with `aws configure` or environment variables

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
    "mcpServers": {
        "aws_waf": {
            "command": "your-absolute-path/uv",
            "args": [
                "--directory",
                "your-absolute-path/mcp/src/aws-waf-mcp-server/awslabs/aws_waf_mcp_server",
                "run",
                "server.py"
            ],
            "env": {
                "AWS_PROFILE": "your-aws-profile",
                "AWS_DEAFULT_REGION": "your-region"
            }
        }
    }
}


```

### AWS Authentication

The MCP server uses the AWS profile and region specified in the `AWS_PROFILE` and `AWS_DEAFULT_REGION` environment variables.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_DEAFULT_REGION": "your-region"
}
```

### Tests

```bash
uv run pytest -s
```
