# AWS Labs Aurora DSQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora DSQL

## Features

- Converting human-readable questions and commands into structured Postgres-compatible SQL queries and executing them against the configured Aurora DSQL database.
- Read-only by default, transactions enabled with `--allow-writes`
- Connection reuse between requests for improved performance

## Prerequisites

1. An AWS account with an [Aurora DSQL Cluster](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html)
1. This MCP server can only be run locally on the same host as your LLM client.
1. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aurora-dsql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXVyb3JhLWRzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1jbHVzdGVyX2VuZHBvaW50IFt5b3VyIGRzcWwgY2x1c3RlciBlbmRwb2ludF0gLS1yZWdpb24gW3lvdXIgZHNxbCBjbHVzdGVyIHJlZ2lvbiwgZS5nLiB1cy1lYXN0LTFdIC0tZGF0YWJhc2VfdXNlciBbeW91ciBkc3FsIHVzZXJuYW1lXSAtLXByb2ZpbGUgZGVmYXVsdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

### Using `uv`

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

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
        "--profile", "default"
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

### Using Docker

1. 'git clone https://github.com/awslabs/mcp.git'
2. Go to sub-directory 'src/aurora-dsql-mcp-server/'
3. Run 'docker build -t awslabs/aurora-dsql-mcp-server:latest .'
4. Create a env file with tempoary credentials:

Either manually:
```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

Or using `aws configure`:

```bash
aws configure export-credentials --profile your-profile-name --format env > temp_aws_credentials.env | sed 's/^export //' > temp_aws_credentials.env
```

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/aurora-dsql-mcp-server:latest",
        "--cluster_endpoint", "[your data]",
        "--database_user", "[your data]",
        "--region", "[your data]"
      ]
    }
  }
}
```

## Server Configuration options

### `--allow-writes`

By default, the dsql mcp server does not allow write operations. Any invocations of transact tool will fail in this mode. To use transact tool, allow writes by passing `--allow-writes` parameter.

### `--cluster_endpoint`

This is mandatory parameter to specify the cluster to connect to. This should be the full endpoint of your cluster, e.g., `01abc2ldefg3hijklmnopqurstu.dsql.us-east-1.on.aws`

### `--database_user`

This is a mandatory parameter to specify the user to connect as. For example
`admin`, or `my_user`. Note that the AWS credentials you are using must have
permission to login as that user. For more information on setting up and using
database roles in DSQL, see [Using database roles with IAM roles](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html).

### `--profile`

You can specify the aws profile to use for your credentials. Note that this is
not supported for docker installation.

Using the `AWS_PROFILE` environment variable in your MCP configuration is also
supported:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

If neither is provided, the MCP server defaults to using the "default" profile in your AWS configuration file.

### `--region`

This is a mandatory parameter to specify the region of your DSQL database.
