# AWS Labs postgres Extended MCP Server

An AWS Labs Model Context Protocol (MCP) server for PostgreSQL databases, supporting both direct connections via psycopg3(for RDS Postgres and Aurora Postgres) and RDS Data API connections(urora Postgres).

## Features

### Natural language to Postgres SQL query

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured PostgreSQL database.

### Connection Options

This MCP server supports two connection methods:

1. **Direct Connection** using psycopg3:
   - Connect directly to PostgreSQL databases using reader/writer endpoints
   - Supports connection pooling for efficient resource management
   - Uses reader endpoint for read-only operations, writer endpoint for write operations
   - Credentials retrieved from AWS Secrets Manager

2. **RDS Data API** (original implementation):
   - Connect to Aurora PostgreSQL using resource ARN and secret ARN
   - Uses AWS RDS Data API for executing queries

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. PostgreSQL database (RDS PostgreSQL or Aurora PostgreSQL) Enable RDS Data API for your Aurora Postgres Cluster, see [instructions here](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html)
4. AWS Secrets Manager secret containing database credentials (username and password)
5. This MCP server can only be run locally on the same host as your LLM client.
6. Docker runtime
7. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

### Configuration

The postgres-extended-mcp-server supports two connection methods in a single configuration:

1. **Direct Connection** using psycopg3 (if reader_endpoint or writer_endpoint is provided)
2. **RDS Data API** (if resource_arn is provided and no endpoints are provided)

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.postgres-mcp-server@latest",
        "--reader_endpoint", "your-postgres-reader-endpoint",  // Required for readonly=True if not using resource_arn
        "--writer_endpoint", "your-postgres-writer-endpoint",  // Optional: Required for readonly=False if not using resource_arn
        "--secret_arn", "[your data]",                         // Required in all cases
        "--resource_arn", "[your data]",                       // Required for RDS Data API, not needed if using endpoints
        "--database", "[your data]",
        "--region", "[your data]",
        "--readonly", "True",
        "--port", "5432",                                      // Optional: Default is 5432
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "your-aws-region",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Connection Method Selection Logic:**
- If `--reader_endpoint` is provided and `--readonly` is `True`, direct connection is used with the reader endpoint
- If `--writer_endpoint` is provided and `--readonly` is `False`, direct connection is used with the writer endpoint
- If neither endpoint is provided but `--resource_arn` is provided, RDS Data API connection is used
- In all cases, `--secret_arn`, `--database`, and `--region` are required

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
        "--reader_endpoint", "your-postgres-reader-endpoint",  // Required for readonly=True if not using resource_arn
        "--writer_endpoint", "your-postgres-writer-endpoint",  // Optional: Required for readonly=False if not using resource_arn
        "--secret_arn", "[your data]",                         // Required in all cases
        "--resource_arn", "[your data]",                       // Required for RDS Data API, not needed if using endpoints
        "--database", "[your data]",
        "--region", "[your data]",
        "--readonly", "True",
        "--port", "5432"                                       // Optional: Default is 5432
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
