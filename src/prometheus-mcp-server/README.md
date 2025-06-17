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

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.prometheus-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucHJvbWV0aGV1cy1tY3Atc2VydmVyQGxhdGVzdCAtLXVybCBodHRwczovL2Fwcy13b3Jrc3BhY2VzLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3dvcmtzcGFjZXMvd3MtPFdvcmtzcGFjZSBJRD4gLS1yZWdpb24gPFlvdXIgQVdTIFJlZ2lvbj4gLS1wcm9maWxlIDxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiREVCVUciLCJBV1NfUFJPRklMRSI6IjxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIn19)

### Prerequisites

- Python 3.10 or higher
- AWS credentials configured with appropriate permissions
- AWS Managed Prometheus workspace



## Configuration

The server is configured through the Amazon Q MCP configuration file as shown in the Usage section below.

## Usage with Amazon Q

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon:

1. Create a configuration file:
```bash
mkdir -p ~/.aws/amazonq/
```

2. Add the following to `~/.aws/amazonq/mcp.json`:
```json
{
  "mcpServers": {
    "awslabs.prometheus-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.prometheus-mcp-server@latest",
        "--url",
        "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-<Workspace ID>",
        "--region",
        "<Your AWS Region>",
        "--profile",
        "<Your CLI Profile [default] if no profile is used>"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "AWS_PROFILE": "<Your CLI Profile [default] if no profile is used>"
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
