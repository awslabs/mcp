# Multi-Profile Support Guide

## Overview

CloudWatch MCP Server now supports multiple AWS profiles in a single server instance, enabling seamless interaction with multiple AWS accounts.

## Features

- 🔄 **Dynamic Profile Switching** - Change AWS accounts per tool call
- 🚀 **Single Server Instance** - No need for multiple MCP servers
- 🔒 **Secure** - Uses standard AWS credential chain
- ✅ **Backward Compatible** - Existing configurations continue to work
- 🎯 **All Tools Supported** - Works across all 11 CloudWatch tools

## Installation

```bash
# Install via uvx (recommended)
uvx awslabs.cloudwatch-mcp-server

# Or install via pip
pip install awslabs.cloudwatch-mcp-server
```

## Configuration

### Method 1: Multi-Profile (New)

Configure MCP server **without** `AWS_PROFILE` environment variable:

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

Then specify `profile_name` in each tool call:

```python
# Query production account
logs = await describe_log_groups(
    region='us-west-2',
    profile_name='production',
    max_items=10
)

# Query staging account in the same session
logs_staging = await describe_log_groups(
    region='us-west-2',
    profile_name='staging',
    max_items=10
)
```

### Method 2: Single Profile (Backward Compatible)

Configure with `AWS_PROFILE` environment variable (existing behavior):

```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server"],
      "env": {
        "AWS_PROFILE": "production",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

All tool calls will use the `production` profile by default. You can still override with `profile_name` parameter.

## AWS Credentials Setup

Ensure your `~/.aws/credentials` file contains the profiles:

```ini
[production]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
# Optional: session token for temporary credentials
aws_session_token = YOUR_SESSION_TOKEN

[staging]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

[development]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

## Tool Usage Examples

### CloudWatch Logs

```python
# Describe log groups in production
production_logs = await describe_log_groups(
    region='us-west-2',
    profile_name='production',
    max_items=20
)

# Execute log insights query in staging
staging_query = await execute_log_insights_query(
    start_time='2025-12-01T00:00:00Z',
    end_time='2025-12-02T00:00:00Z',
    query_string='fields @timestamp, @message | limit 10',
    log_group_names=['/aws/lambda/my-function'],
    region='us-west-2',
    profile_name='staging'
)
```

### CloudWatch Alarms

```python
# Get active alarms from production
prod_alarms = await get_active_alarms(
    region='us-west-2',
    profile_name='production',
    max_items=10
)

# Get alarm history from staging
staging_history = await get_alarm_history(
    alarm_name='my-critical-alarm',
    region='us-west-2',
    profile_name='staging',
    max_items=50
)
```

### CloudWatch Metrics

```python
# Get metric data from production
prod_metrics = await get_metric_data(
    namespace='AWS/Lambda',
    metric_name='Invocations',
    start_time='2025-12-01T00:00:00Z',
    end_time='2025-12-02T00:00:00Z',
    statistic='Sum',
    region='us-west-2',
    profile_name='production'
)

# Analyze metrics in development
dev_analysis = await analyze_metric(
    namespace='AWS/EC2',
    metric_name='CPUUtilization',
    region='us-west-2',
    profile_name='development'
)
```

## Supported Tools

All 11 CloudWatch MCP tools support the `profile_name` parameter:

### CloudWatch Logs (5 tools)
- ✅ `describe_log_groups`
- ✅ `analyze_log_group`
- ✅ `execute_log_insights_query`
- ✅ `get_logs_insight_query_results`
- ✅ `cancel_logs_insight_query`

### CloudWatch Metrics (4 tools)
- ✅ `get_metric_data`
- ✅ `get_metric_metadata`
- ✅ `analyze_metric`
- ✅ `get_recommended_metric_alarms`

### CloudWatch Alarms (2 tools)
- ✅ `get_active_alarms`
- ✅ `get_alarm_history`

## Use Cases

### Cross-Account Monitoring

Monitor resources across multiple AWS accounts from a single interface:

```python
accounts = ['production', 'staging', 'development']
all_alarms = []

for account in accounts:
    alarms = await get_active_alarms(
        region='us-west-2',
        profile_name=account,
        max_items=100
    )
    all_alarms.extend(alarms)
```

### Multi-Region, Multi-Account Queries

Query logs from different accounts and regions:

```python
configs = [
    {'profile': 'production', 'region': 'us-west-2'},
    {'profile': 'production', 'region': 'eu-west-1'},
    {'profile': 'staging', 'region': 'us-west-2'},
]

for config in configs:
    logs = await describe_log_groups(
        region=config['region'],
        profile_name=config['profile'],
        max_items=10
    )
```

### Automated Reporting

Generate reports spanning multiple AWS accounts:

```python
async def generate_daily_report():
    report = {}
    
    for profile in ['prod-account-a', 'prod-account-b']:
        # Get active alarms
        alarms = await get_active_alarms(
            region='us-west-2',
            profile_name=profile
        )
        
        # Get log groups
        logs = await describe_log_groups(
            region='us-west-2',
            profile_name=profile
        )
        
        report[profile] = {
            'active_alarms': len(alarms.metric_alarms),
            'log_groups': len(logs.log_group_metadata)
        }
    
    return report
```

## Security Considerations

1. **Credential Storage**: Profiles use standard AWS credential chain - credentials are stored in `~/.aws/credentials`
2. **IAM Permissions**: Each profile must have appropriate IAM permissions for CloudWatch operations
3. **Session Tokens**: Supports temporary credentials with session tokens (for MFA-enabled accounts)
4. **Profile Isolation**: Each tool call is isolated - credentials don't leak between profiles

## Troubleshooting

### Issue: "ExpiredToken" errors

**Solution**: Refresh your AWS credentials, especially if using temporary session tokens:

```bash
# For MFA-enabled accounts, generate new session tokens
aws sts get-session-token --profile production --serial-number <MFA_ARN> --token-code <MFA_CODE>
```

### Issue: "Profile not found"

**Solution**: Verify the profile exists in `~/.aws/credentials`:

```bash
aws configure list-profiles
```

### Issue: Different results than expected

**Solution**: Verify you're using the correct profile and region:

```python
# Check which account you're querying
identity = await get_caller_identity(profile_name='production')
print(f"Account: {identity['Account']}")
```

## Performance

- **No Performance Degradation**: Dynamic profile switching adds minimal overhead
- **Connection Pooling**: boto3 handles connection reuse automatically
- **Memory Efficient**: Single server instance reduces overall memory footprint

## Limitations

- Each tool call creates a new boto3 session for the specified profile
- Large-scale multi-account operations should consider rate limits
- Some AWS APIs may cache credentials briefly (boto3 behavior)

## Migration Guide

### From Multiple Server Instances

**Before:**
```json
{
  "mcpServers": {
    "cloudwatch-production": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server"],
      "env": { "AWS_PROFILE": "production" }
    },
    "cloudwatch-staging": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server"],
      "env": { "AWS_PROFILE": "staging" }
    }
  }
}
```

**After:**
```json
{
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server"]
    }
  }
}
```

Then use `profile_name` in tool calls instead of different server names.

## Contributing

Found an issue or have a suggestion? Please open an issue or submit a PR!

## License

Same as CloudWatch MCP Server - Apache 2.0

