# AWS Labs Aurora DSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora DSQL

## Features

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured Aurora DSQL database.
- Read-only mode via --read-only
- Connection reuse between requests for improved performance

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. An AWS account with an [Aurora DSQL Cluster](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html)
4. This MCP server can only be run locally on the same host as your LLM client.
5. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

Example for Amazon Q Developer CLI (~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "uvx",
      "args": [
         "awslabs.aurora-dsql-mcp-server@latest",
         "--cluster_endpoint",
         "[your dsql cluster endpoint]",
         "--region",
         "[your dsql cluster region, e.g. us-east-1]",
         "--database_user",
         "[your dsql username]",
         "--profile",
         "[optional: your AWS profile name]"
      ],
      "env": {
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
2. Go to sub-directory 'src/aurora-dsql-mcp-server/'
3. Run 'docker build -t awslabs/aurora-dsql-mcp-server:latest .'

### Add or update your LLM client's config with following:
```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_ACCESS_KEY_ID=[your data]",
        "-e", "AWS_SECRET_ACCESS_KEY=[your data]",
        "-e", "AWS_SESSION_TOKEN=[your data]",
        "-e", "AWS_REGION=[your data]",
        "awslabs/aurora-dsql-mcp-server:latest",
        "--cluster_endpoint", "[your data]",
        "--database_user", "[your data]",
        "--region", "[your data]",
        "--profile", "[optional: your AWS profile name]"
      ]
    }
  }
}
```

NOTE: By default, mcp server does not allow write operations. Any invocations of transact tool will fail in this mode. To use transact tool, allow writes by passing --allow-writes parameter.

## AWS Credentials

You can specify AWS credentials in two ways:

1. Using the `--profile` command-line option to specify an AWS profile from your AWS configuration file:

```
--profile your-aws-profile
```

2. Using the `AWS_PROFILE` environment variable in your MCP configuration:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

If neither is provided, the MCP server defaults to using the "default" profile in your AWS configuration file.
