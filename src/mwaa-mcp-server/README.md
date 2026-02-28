# awslabs.mwaa-mcp-server

An AWS Labs Model Context Protocol (MCP) server for Amazon Managed Workflows for Apache Airflow (MWAA).

## Features

- **MWAA Environment Management**: List, describe, create, update, and delete MWAA environments
- **Airflow DAG Operations**: List DAGs, view details, get source code, trigger runs, pause/unpause
- **DAG Run Monitoring**: List and inspect DAG runs, task instances, and task logs
- **Configuration Access**: View Airflow connections (with password redaction) and variables
- **Error Diagnostics**: Retrieve DAG import/parsing errors
- **Secure by Design**: All Airflow API operations go through AWS `invoke_rest_api` — no CLI or web tokens are exposed
- **Read-only by Default**: Write operations require the `--allow-write` flag

## Prerequisites

- Python 3.10+
- AWS credentials configured (via environment variables, AWS CLI profile, or IAM role)
- An Amazon MWAA environment (Airflow 2.x or 3.x)

## Installation

### Using uvx (recommended)

```bash
uvx awslabs.mwaa-mcp-server
```

### Using pip

```bash
pip install awslabs.mwaa-mcp-server
```

### Using Docker

```bash
docker build -t awslabs.mwaa-mcp-server .
docker run -it awslabs.mwaa-mcp-server
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for API calls | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile name | Default credential chain |
| `MWAA_ENVIRONMENT` | Default MWAA environment name (avoids per-call specification) | Auto-detect |
| `FASTMCP_LOG_LEVEL` | Log level (ERROR, WARNING, INFO, DEBUG) | `WARNING` |

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--allow-write` | Enable write operations (trigger DAG runs, pause/unpause DAGs, create/update/delete environments) |

## Usage with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "awslabs.mwaa-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.mwaa-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "my-profile",
        "MWAA_ENVIRONMENT": "my-environment",
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

For write access:

```json
{
  "mcpServers": {
    "awslabs.mwaa-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.mwaa-mcp-server", "--allow-write"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "my-profile",
        "MWAA_ENVIRONMENT": "my-environment",
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Tool Reference

### Environment Management Tools

| Tool | Description | Access |
|------|-------------|--------|
| `list-environments` | List all MWAA environments in the region | Read |
| `get-environment` | Get detailed information about an environment | Read |
| `create-environment` | Create a new MWAA environment | Write |
| `update-environment` | Update an existing MWAA environment | Write |
| `delete-environment` | Delete an MWAA environment | Write |

### Airflow Tools

| Tool | Description | Access |
|------|-------------|--------|
| `list-dags` | List all DAGs in an environment | Read |
| `get-dag` | Get details of a specific DAG | Read |
| `get-dag-source` | Get the source code of a DAG file | Read |
| `list-dag-runs` | List DAG runs for a specific DAG | Read |
| `get-dag-run` | Get details of a specific DAG run | Read |
| `list-task-instances` | List task instances for a DAG run | Read |
| `get-task-instance` | Get details of a specific task instance | Read |
| `get-task-logs` | Get logs for a task instance try | Read |
| `list-connections` | List Airflow connections (passwords redacted) | Read |
| `list-variables` | List Airflow variables (sensitive values redacted) | Read |
| `get-import-errors` | Get DAG import/parsing errors | Read |
| `trigger-dag-run` | Trigger a new DAG run | Write |
| `pause-dag` | Pause a DAG | Write |
| `unpause-dag` | Unpause a DAG | Write |
| `clear-task-instances` | Clear task instances for a DAG, allowing re-runs | Write |

## IAM Permissions

### Minimum Read-only Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "airflow:GetEnvironment",
        "airflow:ListEnvironments",
        "airflow:InvokeRestApi"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Access Policy (Read + Write)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "airflow:GetEnvironment",
        "airflow:ListEnvironments",
        "airflow:CreateEnvironment",
        "airflow:UpdateEnvironment",
        "airflow:DeleteEnvironment",
        "airflow:InvokeRestApi"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security

- **No token exposure**: Unlike other MWAA tools, this server does not expose `create_cli_token` or `create_web_login_token` as tools. All Airflow API operations go through the AWS-native `invoke_rest_api`.
- **Password redaction**: Connection passwords and extra fields are automatically redacted in responses.
- **Variable redaction**: Variable values with sensitive keys (matching patterns like `secret`, `password`, `token`, `api_key`) are automatically redacted.
- **Input validation**: Environment names and path parameters are validated to prevent injection.
- **Read-only by default**: Write operations are disabled unless `--allow-write` is explicitly passed.

## License

Apache-2.0
