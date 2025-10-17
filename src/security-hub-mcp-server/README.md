# AWS Security Hub MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Security Hub that provides comprehensive security finding management, compliance monitoring, and security insights capabilities.

## Features

This MCP server provides tools to interact with AWS Security Hub, including:

- **Finding Management**: Retrieve, filter, and update security findings
- **Compliance Monitoring**: Check compliance status across security standards
- **Security Standards**: Manage and monitor enabled security standards
- **Insights & Analytics**: Access Security Hub insights and generate security scores
- **Workflow Management**: Update finding workflow states for remediation tracking

## Tools

### GetFindings
Retrieve Security Hub findings with comprehensive filtering options.

**Parameters:**
- `region` (optional): AWS region to query (default: us-east-1)
- `max_results` (optional): Maximum number of findings to return (1-100, default: 50)
- `severity_labels` (optional): Filter by severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL)
- `workflow_states` (optional): Filter by workflow state (NEW, NOTIFIED, RESOLVED, SUPPRESSED)
- `record_states` (optional): Filter by record state (ACTIVE, ARCHIVED)
- `compliance_statuses` (optional): Filter by compliance status (PASSED, WARNING, FAILED, NOT_AVAILABLE)
- `resource_type` (optional): Filter by AWS resource type
- `aws_account_id` (optional): Filter by AWS account ID
- `days_back` (optional): Filter findings updated in the last N days

### GetComplianceByConfigRule
Get compliance information for AWS Config rules used by Security Hub.

**Parameters:**
- `region` (optional): AWS region to query
- `config_rule_names` (optional): List of Config rule names to check
- `compliance_types` (optional): Filter by compliance types
- `max_results` (optional): Maximum number of results to return

### GetEnabledStandards
Retrieve all enabled security standards in Security Hub.

**Parameters:**
- `region` (optional): AWS region to query
- `max_results` (optional): Maximum number of standards to return

### GetInsights
Get Security Hub insights for identifying security trends and patterns.

**Parameters:**
- `region` (optional): AWS region to query
- `insight_arns` (optional): List of specific insight ARNs to retrieve
- `max_results` (optional): Maximum number of insights to return

### GetInsightResults
Get the results of a specific Security Hub insight.

**Parameters:**
- `insight_arn` (required): The ARN of the insight to get results for
- `region` (optional): AWS region to query

### GetSecurityScore
Calculate an overall security score based on finding compliance ratios.

**Parameters:**
- `region` (optional): AWS region to query

### UpdateFindingWorkflowState
Update the workflow state of Security Hub findings for remediation tracking.

**Parameters:**
- `finding_identifiers` (required): List of finding identifiers (Id and ProductArn pairs)
- `workflow_state` (required): New workflow state (NEW, NOTIFIED, RESOLVED, SUPPRESSED)
- `note` (optional): Optional note about the workflow update
- `region` (optional): AWS region to update findings in

## Prerequisites

1. **AWS Security Hub**: Must be enabled in your AWS account and region
2. **AWS Credentials**: Properly configured AWS credentials with Security Hub permissions
3. **IAM Permissions**: Required permissions include:
   - `securityhub:GetFindings`
   - `securityhub:GetEnabledStandards`
   - `securityhub:GetInsights`
   - `securityhub:GetInsightResults`
   - `securityhub:BatchUpdateFindings`
   - `securityhub:DescribeStandardsControls`

## Installation

### Using uv (recommended)

```bash
# Install the server
uv add awslabs.security-hub-mcp-server

# Or install from source
git clone <repository-url>
cd security-hub-mcp-server
uv sync --all-groups
```

### Using pip

```bash
pip install awslabs.security-hub-mcp-server
```

## Configuration

### Environment Variables

- `AWS_REGION`: Default AWS region (optional, defaults to us-east-1)
- `AWS_PROFILE`: AWS profile to use (optional)
- `FASTMCP_LOG_LEVEL`: Logging level (optional, defaults to WARNING)

### AWS Credentials

Ensure your AWS credentials are configured via one of:
- AWS credentials file (`~/.aws/credentials`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- IAM roles (for EC2/Lambda execution)
- AWS SSO

## Usage

### Running the Server

```bash
# Run directly
awslabs.security-hub-mcp-server

# Or with uv
uv run awslabs.security-hub-mcp-server

# With custom region
AWS_REGION=eu-west-1 awslabs.security-hub-mcp-server
```

### Example MCP Client Configuration

Add this to your MCP client configuration:

```json
{
  "awslabs.security-hub-mcp-server": {
    "command": "awslabs.security-hub-mcp-server",
    "env": {
      "AWS_REGION": "us-east-1",
      "FASTMCP_LOG_LEVEL": "INFO"
    }
  }
}
```

## Example Usage

### Get Critical Security Findings

```python
# Get all critical findings in the last 7 days
findings = await get_findings(
    severity_labels=["CRITICAL"],
    workflow_states=["NEW", "NOTIFIED"],
    days_back=7,
    max_results=50
)
```

### Monitor Compliance Status

```python
# Get failed compliance findings
compliance_issues = await get_findings(
    compliance_statuses=["FAILED"],
    record_states=["ACTIVE"],
    max_results=100
)
```

### Update Finding Workflow

```python
# Mark findings as resolved
await update_finding_workflow_state(
    finding_identifiers=[
        {"Id": "finding-id-1", "ProductArn": "product-arn"},
        {"Id": "finding-id-2", "ProductArn": "product-arn"}
    ],
    workflow_state="RESOLVED",
    note="Issues remediated by security team"
)
```

### Get Security Score

```python
# Get overall security posture
score = await get_security_score(region="us-east-1")
```

## Error Handling

The server provides comprehensive error handling for common AWS Security Hub scenarios:

- **Access Denied**: Check IAM permissions and Security Hub enablement
- **Invalid Input**: Verify parameter values and formats
- **Resource Not Found**: Ensure resources exist in the specified region
- **Service Limits**: Respect API rate limits and pagination

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd security-hub-mcp-server

# Install dependencies
uv sync --all-groups

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.security_hub_mcp_server

# Run only unit tests (skip live AWS calls)
uv run pytest -m "not live"
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run pyright
```

## Security Considerations

- **Least Privilege**: Grant only necessary IAM permissions
- **Credential Management**: Use IAM roles when possible, avoid hardcoded credentials
- **Network Security**: Consider VPC endpoints for Security Hub API calls
- **Audit Logging**: Enable CloudTrail for Security Hub API calls
- **Data Sensitivity**: Security findings may contain sensitive information

## Troubleshooting

### Common Issues

1. **Security Hub Not Enabled**
   ```
   Error: InvalidAccessException - Security Hub is not enabled
   ```
   Solution: Enable Security Hub in the AWS Console or via CLI

2. **Insufficient Permissions**
   ```
   Error: Access denied for get findings
   ```
   Solution: Add required IAM permissions for Security Hub operations

3. **Region Mismatch**
   ```
   Error: Resource not found
   ```
   Solution: Ensure Security Hub is enabled in the specified region

4. **Rate Limiting**
   ```
   Error: Service limit exceeded
   ```
   Solution: Implement exponential backoff and reduce request frequency

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the AWS Security Hub documentation
- Review AWS IAM permissions for Security Hub

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
