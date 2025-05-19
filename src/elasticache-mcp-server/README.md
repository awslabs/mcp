# AWS ElastiCache MCP Server

The official MCP Server for interacting with AWS ElastiCache

## Available MCP Tools

### Replication Group Operations
- `create-replication-group` - Create an Amazon ElastiCache replication group with specified configuration
- `delete-replication-group` - Delete an ElastiCache replication group with optional final snapshot
- `describe-replication-groups` - Get detailed information about one or more replication groups
- `modify-replication-group` - Modify settings of an existing replication group
- `modify-replication-group-shard-configuration` - Modify the shard configuration of a replication group
- `connect-jump-host-replication-group` - Configure an EC2 instance as a jump host for replication group access
- `create-jump-host-replication-group` - Create an EC2 jump host to access a replication group via SSH tunnel
- `get-ssh-tunnel-command-replication-group` - Generate SSH tunnel command for replication group access

### Cache Cluster Operations
- `create-cache-cluster` - Create a new ElastiCache cache cluster
- `delete-cache-cluster` - Delete a cache cluster with optional final snapshot
- `describe-cache-clusters` - Get detailed information about one or more cache clusters
- `modify-cache-cluster` - Modify settings of an existing cache cluster
- `connect-jump-host-cache-cluster` - Configure an EC2 instance as a jump host for cluster access
- `create-jump-host-cache-cluster` - Create an EC2 jump host to access a cluster via SSH tunnel
- `get-ssh-tunnel-command-cache-cluster` - Generate SSH tunnel command for cluster access

### Serverless Cache Operations
- `create-serverless-cache` - Create a new ElastiCache serverless cache
- `delete-serverless-cache` - Delete a serverless cache
- `describe-serverless-caches` - Get information about serverless caches
- `modify-serverless-cache` - Modify settings of a serverless cache
- `connect-jump-host-serverless-cache` - Configure an EC2 instance as a jump host for serverless cache access
- `create-jump-host-serverless-cache` - Create an EC2 jump host to access a serverless cache via SSH tunnel
- `get-ssh-tunnel-command-serverless-cache` - Generate SSH tunnel command for serverless cache access

### CloudWatch Operations
- `get-metric-statistics` - Get CloudWatch metric statistics for ElastiCache resources with customizable time periods and dimensions

### CloudWatch Logs Operations
- `describe-log-groups` - List and describe CloudWatch Logs log groups
- `create-log-group` - Create a new CloudWatch Logs log group
- `describe-log-streams` - List and describe log streams in a log group
- `filter-log-events` - Search and filter log events across log streams
- `get-log-events` - Retrieve log events from a specific log stream

### Firehose Operations
- `list-delivery-streams` - List your Kinesis Data Firehose delivery streams

### Cost Explorer Operations
- `get-cost-and-usage` - Get cost and usage data for ElastiCache resources with customizable time periods and granularity

### Misc Operations
- `describe-cache-engine-versions` - List available cache engines and their versions
- `describe-engine-default-parameters` - Get default parameters for a cache engine family
- `describe-events` - Get events related to clusters, security groups, and parameters
- `describe-service-updates` - Get information about available service updates
- `batch-apply-update-action` - Apply service updates to resources
- `batch-stop-update-action` - Stop service updates on resources

## Instructions

The official MCP Server for interacting with AWS ElastiCache provides a comprehensive set of tools for managing ElastiCache resources. Each tool maps directly to ElastiCache API operations and supports all relevant parameters.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for ElastiCache operations. The server will automatically use credentials from environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) or other standard AWS credential sources.

All tools support an optional `region_name` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable or default to 'us-west-2'.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

## Installation

Add the MCP to your favorite agentic tools. e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.elasticache-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/elasticache-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/elasticache-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration

### AWS Configuration

Configure AWS credentials and region:

```bash
# AWS settings
AWS_PROFILE=default              # AWS credential profile to use
AWS_REGION=us-east-1            # AWS region to connect to
```

### Connection Settings

Configure connection behavior and timeouts:

```bash
# Connection settings
ELASTICACHE_MAX_RETRIES=3        # Maximum number of retry attempts for AWS API calls
ELASTICACHE_RETRY_MODE=standard  # AWS SDK retry mode for API calls
ELASTICACHE_CONNECT_TIMEOUT=5    # Connection timeout in seconds
ELASTICACHE_READ_TIMEOUT=10      # Read timeout in seconds

# Cost Explorer settings
COST_EXPLORER_MAX_RETRIES=3      # Maximum number of retry attempts for Cost Explorer API calls
COST_EXPLORER_RETRY_MODE=standard # AWS SDK retry mode for Cost Explorer API calls
COST_EXPLORER_CONNECT_TIMEOUT=5   # Connection timeout in seconds for Cost Explorer
COST_EXPLORER_READ_TIMEOUT=10     # Read timeout in seconds for Cost Explorer

# CloudWatch settings
CLOUDWATCH_MAX_RETRIES=3         # Maximum number of retry attempts for CloudWatch API calls
CLOUDWATCH_RETRY_MODE=standard    # AWS SDK retry mode for CloudWatch API calls
CLOUDWATCH_CONNECT_TIMEOUT=5      # Connection timeout in seconds for CloudWatch
CLOUDWATCH_READ_TIMEOUT=10        # Read timeout in seconds for CloudWatch

# CloudWatch Logs settings
CLOUDWATCH_LOGS_MAX_RETRIES=3     # Maximum number of retry attempts for CloudWatch Logs API calls
CLOUDWATCH_LOGS_RETRY_MODE=standard # AWS SDK retry mode for CloudWatch Logs API calls
CLOUDWATCH_LOGS_CONNECT_TIMEOUT=5  # Connection timeout in seconds for CloudWatch Logs
CLOUDWATCH_LOGS_READ_TIMEOUT=10    # Read timeout in seconds for CloudWatch Logs

# Firehose settings
FIREHOSE_MAX_RETRIES=3            # Maximum number of retry attempts for Firehose API calls
FIREHOSE_RETRY_MODE=standard      # AWS SDK retry mode for Firehose API calls
FIREHOSE_CONNECT_TIMEOUT=5        # Connection timeout in seconds for Firehose
FIREHOSE_READ_TIMEOUT=10          # Read timeout in seconds for Firehose
```

The server automatically handles:
- AWS authentication and credential management
- Connection establishment and management
- Automatic retrying of failed operations
- Timeout enforcement and error handling

## Development

### Running Tests
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Building Docker Image
```bash
docker build -t awslabs/elasticache-mcp-server .
```

### Running Docker Container
```bash
docker run -p 8080:8080 \
  -e AWS_PROFILE=default \
  -e AWS_REGION=us-west-2 \
  awslabs/elasticache-mcp-server
