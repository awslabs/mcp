# AWS DMS Troubleshooting MCP Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server for AWS Database Migration Service (DMS) troubleshooting and Root Cause Analysis (RCA). This server helps customers diagnose and resolve DMS replication issues through automated analysis of replication tasks, CloudWatch logs, and endpoint configurations.

## Overview

The AWS DMS Troubleshooting MCP Server is designed to assist with post-migration troubleshooting, particularly for:
- Failed or stopped replication tasks
- CDC (Change Data Capture) replication issues
- Connection and authentication problems
- Network connectivity and security group issues
- VPC routing and configuration problems
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

- **Network Diagnostics**
  - Analyze security group rules for DMS connectivity
  - Diagnose network connectivity issues between replication instances and endpoints
  - Check VPC routing, network ACLs, and connectivity options
  - Identify VPC peering and Transit Gateway configurations

- **Root Cause Analysis**
  - Comprehensive diagnosis of failed tasks
  - Pattern-based error identification
  - Network-level diagnostics integration
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSecurityGroupRules",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "ec2:DescribeNetworkAcls",
        "ec2:DescribeVpcs",
        "ec2:DescribeVpcPeeringConnections",
        "ec2:DescribeTransitGatewayAttachments",
        "ec2:DescribeNatGateways",
        "ec2:DescribeInternetGateways"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** Network diagnostic features require EC2 read permissions. If these permissions are not available, the server will still function but network diagnostic tools will return permission errors.

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

### 7. analyze_security_groups

Analyze security group rules for DMS replication instance connectivity.

**Parameters:**
- `replication_instance_arn` (string, required): DMS Replication Instance ARN
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await analyze_security_groups(
    replication_instance_arn="arn:aws:dms:us-east-1:123456789012:rep:ABCDEFG",
    region="us-east-1"
)
```

### 8. diagnose_network_connectivity

Perform comprehensive network connectivity diagnostics for a DMS task.

**Parameters:**
- `task_identifier` (string, required): Task identifier to diagnose
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await diagnose_network_connectivity(
    task_identifier="my-replication-task",
    region="us-east-1"
)
```

### 9. check_vpc_configuration

Analyze VPC routing, network ACLs, and connectivity configuration.

**Parameters:**
- `vpc_id` (string, required): VPC ID to analyze
- `region` (string, optional): AWS region
- `aws_profile` (string, optional): AWS profile to use

**Example:**
```python
await check_vpc_configuration(
    vpc_id="vpc-12345678",
    region="us-east-1"
)
```
## Common Use Cases

### Post-Migration Troubleshooting

When a replication task fails after migration:

1. Use `list_replication_tasks` to identify failed tasks
2. Run `diagnose_replication_issue` for comprehensive RCA
3. Review `get_task_cloudwatch_logs` for detailed error context
4. Use `diagnose_network_connectivity` to check for network issues
5. Use `get_troubleshooting_recommendations` for specific errors
6. Apply recommended fixes and monitor results

### Network Connectivity Issues

When experiencing connection timeouts or network errors:

1. Run `diagnose_network_connectivity` for the failing task
2. Use `analyze_security_groups` to verify security group rules
3. Check `check_vpc_configuration` to validate VPC routing
4. Verify DNS resolution for endpoint hostnames
5. Ensure proper VPC peering or Transit Gateway configuration
6. Validate NAT gateway or internet gateway setup

### CDC Replication Issues

For Change Data Capture problems:

1. Check task status with `get_replication_task_details`
2. Analyze logs for CDC-specific errors
3. Verify endpoint configurations support CDC
4. Review recommendations for binlog/WAL configuration
5. Use `diagnose_network_connectivity` to ensure continuous connectivity
6. Check network connectivity and permissions

### Performance Optimization

To investigate slow replication:

1. Review task statistics from `get_replication_task_details`
2. Check CloudWatch logs for warnings
3. Analyze endpoint configurations for optimization opportunities
4. Use `diagnose_network_connectivity` to identify network bottlenecks
5. Get performance-related recommendations

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
