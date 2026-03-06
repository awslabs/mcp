# MWAA MCP Server

[![PyPI](https://img.shields.io/pypi/v/awslabs.mwaa-mcp-server.svg)](https://pypi.org/project/awslabs.mwaa-mcp-server/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Model Context Protocol (MCP) server for Amazon Managed Workflows for Apache Airflow (MWAA).

This MCP server provides comprehensive tools for managing MWAA environments and interacting with Apache Airflow through a unified interface. It enables AI assistants to help with workflow orchestration, DAG management, and operational tasks.

## Features

### MWAA Environment Management

- **List and describe environments** - View all MWAA environments and their configurations
- **Create and update environments** - Deploy new environments or modify existing ones
- **Delete environments** - Clean up unused environments
- **Generate access tokens** - Create CLI and web UI access tokens

### Airflow Operations

- **DAG Management** - List, view, and trigger DAGs
- **DAG Runs** - Monitor and manage workflow executions
- **Task Instances** - Track individual task status and logs
- **Connections & Variables** - View Airflow connections and variables
- **Import Errors** - Diagnose DAG parsing issues

### Expert Guidance

- **Best Practices** - Get MWAA and Airflow best practices
- **DAG Design** - Expert guidance on workflow design patterns

## Prerequisites

- **AWS Credentials**: Configure AWS credentials with appropriate permissions for MWAA
- **Python**: Python 3.10 or higher
- **uv**: Install uv for package management (recommended)

## Installation

## Configuration

### Environment Variables

- `AWS_PROFILE` - AWS credential profile to use (default: uses AWS credential chain)
- `AWS_REGION` - AWS region for MWAA operations (default: us-east-1)
- `MWAA_MCP_READONLY` - Set to "true" for read-only mode
- `FASTMCP_LOG_LEVEL` - Logging level: ERROR, WARNING, INFO, DEBUG (default: ERROR)

### MCP Client Configuration

Add to your MCP client configuration file:

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
`%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "mwaa": {
      "command": "uvx",
      "args": ["path/to/mwaa-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1",
        "MWAA_MCP_READONLY": "false",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

or docker after a successful `docker build -t mwaa-mcp-server .`:

```json
{
  "mcpServers": {
    "mwaa": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_PROFILE=your-profile",
        "--env",
        "AWS_REGION=us-east-1",
        "--env",
        "MWAA_MCP_READONLY=false",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "-v",
        "~/.aws:/home/app/.aws:ro",
        "mwaa-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### Other MCP Clients

Refer to your MCP client's documentation for configuration details.

## Usage Examples

### Environment Management

```
"List all MWAA environments in my account"
"Show me details about the 'production-airflow' environment"
"Create a new MWAA environment called 'dev-airflow' with 2 schedulers"
"Update the production environment to use Airflow 2.7.2"
```

### DAG Operations

```
"List all DAGs in the production environment"
"Show me the source code for the 'etl_pipeline' DAG"
"Trigger the 'daily_report' DAG with config {'date': '2024-01-01'}"
"Check the status of the latest run for 'data_processing' DAG"
```

### Monitoring and Troubleshooting

```
"Show me failed DAG runs from the last 24 hours"
"Get logs for the 'extract_data' task that failed"
"List all import errors in the development environment"
"Show me all Airflow connections configured in production"
```

### Best Practices

```
"What are the best practices for MWAA environment sizing?"
"How should I design a DAG for parallel data processing?"
"Give me guidance on handling errors in Airflow tasks"
```

## Required AWS Permissions

The IAM user or role needs the following permissions:

### MWAA Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "airflow:CreateCliToken",
        "airflow:CreateWebLoginToken",
        "airflow:GetEnvironment",
        "airflow:ListEnvironments"
      ],
      "Resource": "*"
    }
  ]
}
```

### Additional Permissions for Write Operations

```json
{
  "Effect": "Allow",
  "Action": [
    "airflow:CreateEnvironment",
    "airflow:UpdateEnvironment",
    "airflow:DeleteEnvironment"
  ],
  "Resource": "*"
}
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/paschmaria/mwaa-mcp-server.git
cd mwaa-mcp-server

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dev dependencies
uv sync --dev

# Or using pip
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=awslabs.mwaa_mcp_server

# Run specific test
pytest tests/test_tools.py::test_list_environments
```

### Building Docker Image

```bash
# Build image
docker build -t mwaa-mcp-server .

# Run container with all environment variables
docker run -it --rm \
  -e AWS_PROFILE=default \
  -e AWS_REGION=us-east-1 \
  -e MWAA_MCP_READONLY=false \
  -e FASTMCP_LOG_LEVEL=ERROR \
  -v ~/.aws:/home/app/.aws:ro \
  mwaa-mcp-server
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify AWS credentials are configured correctly
   - Check IAM permissions for MWAA operations
   - Ensure the correct AWS region is specified

2. **Connection Timeouts**
   - Check VPC and security group configurations
   - Verify MWAA environment is in AVAILABLE state
   - Ensure your network can reach MWAA endpoints

3. **Import Errors in DAGs**
   - Use the `get_import_errors` tool to diagnose
   - Check CloudWatch logs for detailed error messages
   - Verify all dependencies are in requirements.txt

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
