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

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.postgres-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucG9zdGdyZXMtbWNwLXNlcnZlckBsYXRlc3QgLS1jb25uZWN0aW9uLXN0cmluZyBwb3N0Z3Jlc3FsOi8vW3VzZXJuYW1lXTpbcGFzc3dvcmRdQFtob3N0XTpbcG9ydF0vW2RhdGFiYXNlXSIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdLCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJhdXRvU3RhcnQiOnRydWV9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=PostgreSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A%2F%2F%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D%2F%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%2C%22transportType%22%3A%22stdio%22%2C%22autoStart%22%3Atrue%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

### Option 1: Using RDS Data API Connection (for Aurora Postgres)

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

### Option 2: Using Direct PostgreSQL(psycopg) Connection (for Aurora Postgres and RDS Postgres)

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.postgres-mcp-server@latest",
        "--hostname", "[your data]",
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

Note: The `--port` parameter is optional and defaults to 5432 (the standard PostgreSQL port). You only need to specify it if your PostgreSQL instance uses a non-standard port.

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.postgres-mcp-server@latest",
        "awslabs.postgres-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Build and install docker image locally on the same host of your LLM client

1. 'git clone https://github.com/awslabs/mcp.git'
2. Go to sub-directory 'src/postgres-mcp-server/'
3. Run 'docker build -t awslabs/postgres-mcp-server:latest .'

### Add or update your LLM client's config with following:

#### Option 1: Using RDS Data API Connection (for Aurora Postgres)

```json
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
```

#### Option 2: Using Direct PostgreSQL (psycopg) Connection (for Aurora Postgres and RDS Postgres)

```
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
        "--hostname", "[your data]",
        "--secret_arn", "[your data]",
        "--database", "[your data]",
        "--region", "[your data]",
        "--readonly", "True"
      ]
    }
  }
}
```

Note: The `--port` parameter is optional and defaults to 5432 (the standard PostgreSQL port). You only need to specify it if your PostgreSQL instance uses a non-standard port.

NOTE: By default, only read-only queries are allowed and it is controlled by --readonly parameter above. Set it to False if you also want to allow writable DML or DDL.

## Connection Methods

This MCP server supports two connection methods:

1. **RDS Data API Connection** (using `--resource_arn`): Uses the AWS RDS Data API to connect to Aurora PostgreSQL. This method requires that your Aurora cluster has the Data API enabled.

2. **Direct PostgreSQL Connection** (using `--hostname`): Uses psycopg to connect directly to any PostgreSQL database, including Aurora PostgreSQL, RDS PostgreSQL, or self-hosted PostgreSQL instances. This method provides better performance for frequent queries but requires direct network access to the database.

Choose the connection method that best fits your environment and requirements.

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the [RDS data API](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html#data-api.access), and the secret from AWS Secrets Manager. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.
