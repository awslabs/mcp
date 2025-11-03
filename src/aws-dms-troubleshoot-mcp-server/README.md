# AWS DMS Troubleshooting MCP Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server for AWS Database Migration Service (DMS) troubleshooting and Root Cause Analysis (RCA). This server helps customers diagnose and resolve DMS replication issues through automated analysis of replication tasks, CloudWatch logs, and endpoint configurations.

## Overview

The AWS DMS Troubleshooting MCP Server is designed to assist with post-migration troubleshooting, particularly for:
- Failed or stopped replication tasks
- CDC (Change Data Capture) replication issues
- Connection and authentication problems
- Performance and latency issues
- Configuration errors

## Features

- **Replication Task Management**
  - List all DMS replication tasks with status filtering
  - Get detailed task information including statistics and configuration
  - Analyze task performance and progress

- **CloudWatch Logs Analysis**
  - Retrieve and filter DMS task logs
  - Identify error patterns and frequencies
  - Search logs by time range and severity

- **Endpoint Analysis**
  - Validate source and target endpoint configurations
  - Test endpoint connectivity
  - Identify common configuration issues

- **Root Cause Analysis**
  - Comprehensive diagnosis of failed tasks
  - Pattern-based error identification
  - Actionable recommendations based on AWS best practices

- **Documentation Integration**
  - Context-aware troubleshooting recommendations
  - Links to relevant AWS documentation
  - Best practice guidance

## Installation

### Using uvx (Recommended)

```bash
uvx awslabs.aws-dms-troubleshoot-mcp-server
```

### Using pip

```bash
pip install awslabs.aws-dms-troubleshoot-mcp-server
```

### From Source

```bash
cd src/aws-dms-troubleshoot-mcp-server
pip install -e .
```

## Configuration

### Environment Variables

```bash
# Required: AWS region where your DMS resources are located
export AWS_REGION=us-east-1

# Optional: AWS CLI profile to use
export AWS_PROFILE=default

# Optional: Logging level
export FASTMCP_LOG_LEVEL=INFO
```

### AWS Credentials

The server uses standard AWS credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (when running on EC2, ECS, or Lambda)

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "aws-dms-troubleshoot": {
      "command": "uvx",
      "args": ["awslabs.aws-dms-troubleshoot-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

## AWS Permissions Required

The IAM user or role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:DescribeReplicationTasks",
        "dms:DescribeReplicationInstances",
        "dms:DescribeEndpoints",
        "dms:TestConnection"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:dms-tasks-*"
    }
  ]
}
```

## Available Tools

### 1. list_replication_tasks

List all DMS replication tasks with their current status.

**Parameters:**
- `region` (string, optional): AWS region (default: from environment)
- `aws_profile` (string, optional): AWS profile to use
- `status_filter` (string, optional): Filter by status (running, stopped, failed, etc.)

**Example:**
```python
await list_replication_tasks(
    region="us-east-1",
    status_filter="failed"
)
```

### 2. get_replication_task_details

Get comprehensive details about a specific replication task.

**Parameters:**
- `task_identifier` (string, required): Task identifier or ARN
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await get_replication_task_details(
    task_identifier="my-replication-task",
    region="us-east-1"
)
```

### 3. get_task_cloudwatch_logs

Retrieve CloudWatch logs for a replication task.

**Parameters:**
- `task_identifier` (string, required): Task identifier
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use
- `hours_back` (integer, optional): Hours of logs to retrieve (default: 24)
- `filter_pattern` (string, optional): Log filter pattern (e.g., "ERROR")
- `max_events` (integer, optional): Maximum events to return (default: 100)

**Example:**
```python
await get_task_cloudwatch_logs(
    task_identifier="my-replication-task",
    hours_back=48,
    filter_pattern="ERROR",
    max_events=100
)
```

### 4. analyze_endpoint

Analyze a DMS endpoint configuration for potential issues.

**Parameters:**
- `endpoint_arn` (string, required): Endpoint ARN
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await analyze_endpoint(
    endpoint_arn="arn:aws:dms:us-east-1:123456789012:endpoint:ABCDEFG",
    region="us-east-1"
)
```

### 5. diagnose_replication_issue

Perform comprehensive Root Cause Analysis for a replication task.

**Parameters:**
- `task_identifier` (string, required): Task identifier to diagnose
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await diagnose_replication_issue(
    task_identifier="my-failing-task",
    region="us-east-1"
)
```

### 6. get_troubleshooting_recommendations

Get recommendations based on error patterns.

**Parameters:**
- `error_pattern` (string, required): Error message or pattern

**Example:**
```python
await get_troubleshooting_recommendations(
    error_pattern="connection timeout"
)
```

## Usage Examples

### Example 1: Diagnose a Failed Replication Task

```python
# Step 1: List all failed tasks
tasks = await list_replication_tasks(status_filter="failed")

# Step 2: Get detailed diagnosis for a specific task
diagnosis = await diagnose_replication_issue(
    task_identifier=tasks['tasks'][0]['task_identifier']
)

# Step 3: Review root causes and recommendations
print("Root Causes:", diagnosis['root_causes'])
print("Recommendations:", diagnosis['recommendations'])
```

### Example 2: Analyze Error Logs

```python
# Get recent error logs
logs = await get_task_cloudwatch_logs(
    task_identifier="my-task",
    hours_back=24,
    filter_pattern="ERROR OR FATAL",
    max_events=50
)

# Analyze error patterns
for event in logs['log_events']:
    print(f"{event['timestamp']}: {event['message']}")

# Get recommendations for common errors
if logs['log_events']:
    error_message = logs['log_events'][0]['message']
    recommendations = await get_troubleshooting_recommendations(
        error_pattern=error_message
    )
```

### Example 3: Validate Endpoint Configuration

```python
# Get task details to find endpoint ARNs
task = await get_replication_task_details(
    task_identifier="my-task"
)

# Analyze source endpoint
source_analysis = await analyze_endpoint(
    endpoint_arn=task['source_endpoint_arn']
)

# Analyze target endpoint
target_analysis = await analyze_endpoint(
    endpoint_arn=task['target_endpoint_arn']
)

# Review findings
print("Source Issues:", source_analysis['potential_issues'])
print("Target Issues:", target_analysis['potential_issues'])
```

## Common Use Cases

### Post-Migration Troubleshooting

When a replication task fails after migration:

1. Use `list_replication_tasks` to identify failed tasks
2. Run `diagnose_replication_issue` for comprehensive RCA
3. Review `get_task_cloudwatch_logs` for detailed error context
4. Use `get_troubleshooting_recommendations` for specific errors
5. Apply recommended fixes and monitor results

### CDC Replication Issues

For Change Data Capture problems:

1. Check task status with `get_replication_task_details`
2. Analyze logs for CDC-specific errors
3. Verify endpoint configurations support CDC
4. Review recommendations for binlog/WAL configuration
5. Check network connectivity and permissions

### Performance Optimization

To investigate slow replication:

1. Review task statistics from `get_replication_task_details`
2. Check CloudWatch logs for warnings
3. Analyze endpoint configurations for optimization opportunities
4. Get performance-related recommendations

## Troubleshooting

### Server Won't Start

**Issue:** Server fails to start or authenticate

**Solution:**
- Verify AWS credentials are configured correctly
- Check IAM permissions match requirements
- Ensure AWS_REGION is set
- Review logs with `FASTMCP_LOG_LEVEL=DEBUG`

### No Tasks Found

**Issue:** `list_replication_tasks` returns empty

**Solution:**
- Verify you're using the correct AWS region
- Check that DMS tasks exist in the specified region
- Confirm IAM permissions include `dms:DescribeReplicationTasks`

### Log Group Not Found

**Issue:** CloudWatch logs cannot be retrieved

**Solution:**
- Verify task has been started (logs only exist after task runs)
- Check task identifier is correct
- Ensure CloudWatch Logs permissions are granted
- Confirm logs retention hasn't expired

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=awslabs.aws_dms_troubleshoot_mcp_server tests/
```

### Code Style

This project uses:
- `ruff` for linting and formatting
- `pyright` for type checking
- `pre-commit` for automated checks

```bash
# Format code
ruff format .

# Run linter
ruff check .

# Type check
pyright
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- [AWS DMS Documentation](https://docs.aws.amazon.com/dms/)
- [AWS DMS Troubleshooting Guide](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting.html)
- [GitHub Issues](https://github.com/awslabs/mcp/issues)
- [AWS Support](https://aws.amazon.com/support/)

## Related Resources

- [AWS DMS Best Practices](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_BestPractices.html)
- [AWS DMS Security](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Servers Collection](https://github.com/awslabs/mcp)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.