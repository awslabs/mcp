# Prometheus MCP Server

The Prometheus MCP Server provides a robust interface for interacting with AWS Managed Prometheus, enabling users to execute PromQL queries, list metrics, and retrieve server information with AWS SigV4 authentication support.

This MCP server is designed to be fully compatible with Amazon Q developer CLI, allowing seamless integration of Prometheus monitoring capabilities into your Amazon Q workflows. You can load the server directly into Amazon Q to leverage its powerful querying and metric analysis features through the familiar Q interface.

## Features

- Execute instant PromQL queries against AWS Managed Prometheus
- Execute range queries with start time, end time, and step interval
- List all available metrics in your Prometheus instance
- Get server configuration information
- AWS SigV4 authentication for secure access
- Automatic retries with exponential backoff

## Installation

### Prerequisites

- Python 3.10 or higher
- AWS credentials configured with appropriate permissions
- AWS Managed Prometheus workspace

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp

# Install the package
pip install -e src/prometheus-mcp-server
```

## Configuration

The server can be configured using:

1. Command-line arguments:
```bash
python -m awslabs.prometheus_mcp_server.server --url https://your-prometheus-endpoint --region us-east-1 --profile your-profile
```

2. Environment variables:
```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
export PROMETHEUS_URL=https://your-prometheus-endpoint
```

3. Configuration file (JSON format):
```json
{
  "aws_profile": "your-profile",
  "aws_region": "us-east-1",
  "prometheus_url": "https://your-prometheus-endpoint",
  "service_name": "aps",
  "max_retries": 3,
  "retry_delay": 1
}
```

## Usage with Amazon Q

To use this MCP server with Amazon Q:

1. Create a configuration file:
```bash
mkdir -p ~/.aws/amazoq/
```

2. Add the following to `~/.aws/amazoq/mcp.json`:
```json
{
  "mcpServers": {
    "prometheus": {
      "command": "python",
      "args": [
        "-m",
        "awslabs.prometheus_mcp_server.server",
        "--url",
        "https://your-prometheus-endpoint",
        "--region",
        "us-east-1",
        "--profile",
        "your-profile"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

3. In Amazon Q, you can now use the Prometheus MCP server to query your metrics.

## Available Tools

1. **execute_query**
   - Execute instant PromQL queries against Prometheus
   - Parameters: query (required), time (optional)

2. **execute_range_query**
   - Execute PromQL queries over a time range
   - Parameters: query, start time, end time, step interval

3. **list_metrics**
   - Retrieve all available metric names from Prometheus
   - Returns: Sorted list of metric names

4. **get_server_info**
   - Retrieve server configuration details
   - Returns: URL, region, profile, and service information

## Example Queries

```python
# Execute an instant query
result = await execute_query("up")

# Execute a range query
data = await execute_range_query(
    query="rate(node_cpu_seconds_total[5m])",
    start="2023-01-01T00:00:00Z",
    end="2023-01-01T01:00:00Z",
    step="1m"
)

# List available metrics
metrics = await list_metrics()

# Get server information
info = await get_server_info()
```

## Troubleshooting

Common issues and solutions:

1. **AWS Credentials Not Found**
   - Check ~/.aws/credentials
   - Set AWS_PROFILE environment variable
   - Verify IAM permissions

2. **Connection Errors**
   - Verify Prometheus URL is correct
   - Check network connectivity
   - Ensure AWS VPC access is configured correctly

3. **Authentication Failures**
   - Verify AWS credentials are current
   - Check system clock synchronization
   - Ensure correct AWS region is specified

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.