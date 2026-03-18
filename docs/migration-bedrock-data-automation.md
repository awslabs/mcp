# Migration Guide: AWS Bedrock Data Automation MCP Server

This guide helps you migrate from `awslabs.aws-bedrock-data-automation-mcp-server`.

## Why We're Deprecating

This server has very low usage (~1.5K PyPI downloads/month) and no dedicated service team maintaining it. The Amazon Bedrock Data Automation service continues to evolve independently with its own APIs and SDKs.

## Recommended Alternatives

### Use the Bedrock Data Automation API Directly

The most reliable approach is to use the Amazon Bedrock Data Automation API directly through boto3:

```python
import boto3

# Use bedrock-data-automation for project management
client = boto3.client('bedrock-data-automation', region_name='us-east-1')

# List projects
projects = client.list_data_automation_projects()

# Use bedrock-data-automation-runtime for invocations
runtime_client = boto3.client('bedrock-data-automation-runtime', region_name='us-east-1')

# Analyze an asset
response = runtime_client.invoke_data_automation_async(
    inputConfiguration={'s3Uri': 's3://your-bucket/your-file.pdf'},
    dataAutomationConfiguration={'dataAutomationProjectArn': 'your-project-arn'},
    outputConfiguration={'s3Uri': 's3://your-bucket/output/'}
)
```

### Use the AWS API MCP Server

The [aws-api-mcp-server](https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server) provides generic access to any AWS API, including Bedrock Data Automation:

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-api-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Tool Mapping

| Old Tool | Alternative |
|---|---|
| `getprojects` | `boto3.client('bedrock-data-automation').list_data_automation_projects()` |
| `getprojectdetails` | `boto3.client('bedrock-data-automation').get_data_automation_project()` |
| `analyzeasset` | `boto3.client('bedrock-data-automation-runtime').invoke_data_automation_async()` |

## Summary

For continued access to Bedrock Data Automation capabilities, use the boto3 API directly or the generic aws-api-mcp-server. Refer to the [Amazon Bedrock Data Automation documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/data-automation.html) for the latest API reference.
