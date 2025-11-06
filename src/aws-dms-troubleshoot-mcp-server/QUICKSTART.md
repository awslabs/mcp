# Quick Start Guide

Get started with the AWS DMS Troubleshooting MCP Server in minutes.

## Installation

```bash
# Install using uvx (recommended)
uvx awslabs.aws-dms-troubleshoot-mcp-server

# Or install with pip
pip install awslabs.aws-dms-troubleshoot-mcp-server
```

## Setup AWS Credentials

Ensure your AWS credentials are configured:

```bash
# Option 1: Use AWS CLI
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

## Configure MCP Client

Add to your MCP client configuration (e.g., `~/Library/Application Support/Claude/claude_desktop_config.json` for Claude Desktop):

```json
{
  "mcpServers": {
    "aws-dms-troubleshoot": {
      "command": "uvx",
      "args": ["awslabs.aws-dms-troubleshoot-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Basic Usage Examples

### Example 1: Find and Diagnose a Failed Task

```plaintext
User: "Show me all failed DMS replication tasks"

Assistant uses: list_replication_tasks(status_filter="failed")

User: "Diagnose the first one"

Assistant uses: diagnose_replication_issue(task_identifier="task-123")

Output: Comprehensive root cause analysis with recommendations
```

### Example 2: Analyze Error Logs

```plaintext
User: "Get the error logs from my-replication-task"

Assistant uses: get_task_cloudwatch_logs(
    task_identifier="my-replication-task",
    filter_pattern="ERROR",
    hours_back=24
)

Output: List of error events with timestamps and messages
```

### Example 3: Check Endpoint Configuration

```plaintext
User: "Check if my source endpoint is configured correctly"

Assistant uses: get_replication_task_details(task_identifier="my-task")
Then: analyze_endpoint(endpoint_arn="<source_endpoint_arn>")

Output: Configuration analysis with potential issues and recommendations
```

### Example 4: Get Help for Specific Errors

```plaintext
User: "I'm getting connection timeout errors, what should I do?"

Assistant uses: get_troubleshooting_recommendations(
    error_pattern="connection timeout"
)

Output: Step-by-step troubleshooting guide with documentation links
```

## Common Workflows

### Post-Migration Troubleshooting

1. **Identify Issues**
   ```
   list_replication_tasks(status_filter="failed")
   ```

2. **Diagnose Root Cause**
   ```
   diagnose_replication_issue(task_identifier="your-task")
   ```

3. **Review Detailed Logs**
   ```
   get_task_cloudwatch_logs(task_identifier="your-task", filter_pattern="ERROR")
   ```

4. **Get Recommendations**
   ```
   get_troubleshooting_recommendations(error_pattern="<error_from_logs>")
   ```

### CDC Replication Issues

1. **Check Task Status**
   ```
   get_replication_task_details(task_identifier="cdc-task")
   ```

2. **Analyze Both Endpoints**
   ```
   analyze_endpoint(endpoint_arn="source-arn")
   analyze_endpoint(endpoint_arn="target-arn")
   ```

3. **Review CDC-specific Logs**
   ```
   get_task_cloudwatch_logs(
       task_identifier="cdc-task",
       filter_pattern="CDC OR binlog OR WAL"
   )
   ```

## Docker Usage

```bash
# Build the image
docker build -t aws-dms-troubleshoot-mcp-server .

# Run the server
docker run -e AWS_ACCESS_KEY_ID=<key> \
           -e AWS_SECRET_ACCESS_KEY=<secret> \
           -e AWS_REGION=us-east-1 \
           aws-dms-troubleshoot-mcp-server
```

## Troubleshooting

### Server won't start
- Check AWS credentials are valid
- Verify IAM permissions are correct
- Check AWS_REGION is set

### No tasks found
- Confirm you're in the correct AWS region
- Verify DMS tasks exist in that region
- Check IAM permissions

### Cannot retrieve logs
- Ensure task has been started (logs only exist after running)
- Verify CloudWatch Logs permissions
- Check log retention hasn't expired

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Review [CHANGELOG.md](CHANGELOG.md) for version information
- Check AWS permissions match requirements
- Test with your existing DMS tasks

## Support

- AWS DMS Documentation: https://docs.aws.amazon.com/dms/
- GitHub Issues: https://github.com/awslabs/mcp/issues
- AWS Support: https://aws.amazon.com/support/
