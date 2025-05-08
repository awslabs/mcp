# AWS Labs postgres MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora Postgres

## Features

### Natural language to Postgres SQL query

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured Aurora Postgres database.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Aurora Postgres Cluster with Postgres username and password stored in AWS Secrets Manager
4. Enable RDS Data API for your Aurora Postgres Cluster, see [instructions here](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html)
5. This MCP server can only be run locally on the same host as your LLM client.
6. Docker runtime
7. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.postgres-mcp-server@latest",
        "--resource_arn", "[your data]",
        "--secret_arn", "[your data]",
        "--database", "[your data]",
        "--region", "[your data]",
        "--readonly", "True"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Build and install docker image locally on the same host of your LLM client

1. 'git clone https://github.com/awslabs/mcp.git'
2. Go to sub-directory 'src/postgres-mcp-server/'
3. Run 'docker build -t awslabs/postgres-mcp-server:latest .'

### Add or update your LLM client's config with following:
<pre><code>
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_ACCESS_KEY_ID=[your data]",
        "-e", "AWS_SECRET_ACCESS_KEY=[your data]",
        "-e", "AWS_REGION=[your data]",
        "awslabs/postgres-mcp-server:latest",
        "--resource_arn", "[your data]",
        "--secret_arn", "[your data]",
        "--database", "[your data]",
        "--region", "[your data]",
        "--readonly", "True"
      ]
    }
  }
}
</code></pre>

NOTE: By default, only read-only queries are allowed and it is controlled by --readonly parameter above. Set it to False if you also want to allow writable DML or DDL.

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the [RDS data API](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html#data-api.access), and the secret from AWS Secrets Manager. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.
