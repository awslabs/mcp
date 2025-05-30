# Prometheus MCP Server - A Command-Line Interface for AWS Prometheus Monitoring

The Prometheus MCP Server provides a robust command-line interface for interacting with AWS Managed Prometheus, enabling users to execute PromQL queries, list metrics, and retrieve server information with AWS SigV4 authentication support.

This MCP server is designed to be fully compatible with Amazon Q developer CLI, allowing seamless integration of Prometheus monitoring capabilities into your Amazon Q workflows. You can load the server directly into Amazon Q to leverage its powerful querying and metric analysis features through the familiar Q interface.

This project simplifies interaction with AWS Managed Prometheus by providing a set of command-line tools that handle authentication, request signing, and error handling. It supports both instant and range queries, metric discovery, and server information retrieval, making it ideal for automation scripts and interactive monitoring tasks.

## Repository Structure
```
.
├── check_imports.py      # Dependency validation script
├── pyproject.toml       # Python project configuration and dependencies
├── README.md           # Project documentation
├── server.py          # Main server implementation with MCP tools
└── uv.lock           # Package version lock file
```

## Setup and Integration with Amazon Q

Follow these steps to set up and integrate the MCP server with Amazon Q:

1. **Clone the Repository**
```bash
git clone <repository-url>
cd prometheus-mcp-server
```

2. **Create Configuration File**
Create a new file named `mcp.json` in the `~/.aws/amazoq/` directory:
```bash
mkdir -p ~/.aws/amazoq/
touch ~/.aws/amazoq/mcp.json
```

3. **Configure MCP Server**
Add the following content to `mcp.json`, replacing the placeholders with your values:
```json
{
  "mcpServers": {
    "prometheus": {
      "command": "uv",
      "args": [
        "--directory",
        "/full/path/to/prometheus-mcp-server",
        "run",
        "server.py",
        "--profile",
        "default",
        "--region",
        "us-east-1",
        "--url",
        "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-XXXX-XXXX-XXXX-XXXX"
      ]
    }
  }
}
```

4. **Update Configuration**
- Replace `/full/path/to/prometheus-mcp-server` with the absolute path to your cloned repository
- Update the `--url` parameter with your AWS Managed Prometheus workspace URL
- Adjust the region and profile as needed

5. **Verify AWS Prometheus Workspace**
Ensure you have an active AWS Managed Prometheus workspace and note its URL for the configuration file.

## Usage Instructions
### Prerequisites
- Python 3.10 or higher
- AWS credentials configured with appropriate permissions
- The following Python packages:
  - boto3 >= 1.38.7
  - httpx >= 0.28.1
  - mcp[cli] >= 1.7.0
  - requests >= 2.32.3

### Authentication
The server uses AWS credentials for authentication with AWS Managed Prometheus. You can configure authentication using:

1. AWS Profile (Recommended):
```bash
export AWS_PROFILE=your-profile    # Defaults to 'default' if not specified
```

2. Configuration File:
```json
{
  "mcpServers": {
    "prometheus": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/prometheus_mcp_server",
        "run",
        "server.py",
        "--profile",
        "default",
        "--region",
        "us-east-1",
        "--url",
        "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-XXXX-XXXX-XXXX-XXXX"
      ]
    }
  }
}
```

### Installation
There are two ways to install the project:

#### Option 1: Using uv (Recommended)
1. Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Create and set up the project:
```bash
uv init project-name
cd project-name
uv venv
source .venv/bin/activate
uv add "mcp[cli]" httpx
```

#### Option 2: Using pip
```bash
git clone <repository-url>
cd prometheus-mcp-server
pip install -r requirements.txt
```

### Quick Start
1. Set up your AWS credentials:
```bash
export AWS_PROFILE=your-profile
export AWS_REGION=your-region
export PROMETHEUS_URL=your-prometheus-url
```

2. Run the server:
```bash
python server.py --url https://your-prometheus-endpoint --region us-east-1
```

### More Detailed Examples
1. Execute an instant query:
```python
await execute_query("up")
```

2. Execute a range query:
```python
await execute_range_query(
    query="rate(node_cpu_seconds_total[5m])",
    start="2023-01-01T00:00:00Z",
    end="2023-01-01T01:00:00Z",
    step="1m"
)
```

3. List available metrics:
```python
metrics = await list_metrics()
print("\n".join(metrics))
```

## Available Tools
The MCP server provides the following command-line tools:

1. **execute_query**
   - Purpose: Execute instant PromQL queries against Prometheus
   - Usage: Provides immediate query results for current metrics
   - Parameters: query (required), time (optional)

2. **execute_range_query**
   - Purpose: Execute PromQL queries over a time range
   - Usage: Retrieves metric data across specified time periods
   - Parameters: query, start time, end time, step interval

3. **list_metrics**
   - Purpose: Retrieve all available metric names from Prometheus
   - Usage: Lists all metrics that can be queried
   - Returns: Sorted list of metric names

4. **get_server_info**
   - Purpose: Retrieve server configuration details
   - Usage: Shows current Prometheus and AWS settings
   - Returns: URL, region, profile, and service information

### Troubleshooting
Common issues and solutions:

1. AWS Credentials Not Found
```
Error: AWS credentials not found
Solution: Ensure AWS credentials are properly configured:
- Check ~/.aws/credentials
- Set AWS_PROFILE environment variable
- Verify IAM permissions
```

2. Connection Errors
```
Error: Connection failed after max retries
Solutions:
- Verify Prometheus URL is correct
- Check network connectivity
- Ensure AWS VPC access is configured correctly
```

3. Authentication Failures
```
Error: SignatureDoesNotMatch
Solutions:
- Verify AWS credentials are current
- Check system clock synchronization
- Ensure correct AWS region is specified
```

## Data Flow
The server handles requests through a secure AWS authentication flow, transforming PromQL queries into authenticated AWS requests.

```ascii
Client -> MCP Server -> AWS SigV4 Auth -> AWS Prometheus
   ^                                           |
   |                                           v
   +-------------- JSON Response <-------------+
```

Component interactions:
- Client sends PromQL query to MCP server
- Server validates and processes the request
- AWS SigV4 authentication is applied
- Request is sent to AWS Prometheus
- Response is parsed and returned to client
- Error handling and retries are managed automatically
- Results are formatted as JSON