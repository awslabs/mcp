# AWS Security Hub MCP Server

Model Context Protocol (MCP) server for AWS Security Hub

This MCP server provides tools to interact with AWS Security Hub, enabling security findings analysis, compliance reporting, and security posture management through AI assistants.

## Features

- **Get Security Findings**: Retrieve and filter security findings from Security Hub
- **Get Compliance Summary**: Get compliance status across security standards
- **Get Insights**: Access Security Hub insights and custom insights
- **Manage Standards**: Enable/disable security standards and controls
- **Get Finding Statistics**: Analyze security findings with aggregated statistics
- **Update Findings**: Update finding workflow status and add notes
- **Get Security Score**: Retrieve overall security score and trends

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

### AWS Requirements

1. AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
2. AWS Security Hub enabled in your AWS account
3. Appropriate IAM permissions for Security Hub operations

#### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "securityhub:GetFindings",
                "securityhub:GetInsights",
                "securityhub:GetInsightResults",
                "securityhub:BatchUpdateFindings",
                "securityhub:GetComplianceDetails",
                "securityhub:DescribeStandards",
                "securityhub:DescribeStandardsControls",
                "securityhub:GetEnabledStandards",
                "securityhub:BatchEnableStandards",
                "securityhub:BatchDisableStandards",
                "securityhub:UpdateStandardsControl"
            ],
            "Resource": "*"
        }
    ]
}
```

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-security-hub-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXNlY3VyaXR5LWh1Yi1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Security%20Hub%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-security-hub-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.aws-security-hub-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-security-hub-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

For [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html), add the MCP client configuration and tool command to the agent file in `~/.aws/amazonq/cli-agents`.

Example, `~/.aws/amazonq/cli-agents/default.json`

```json
{
  "version": "1.0",
  "mcpServers": {
    "awslabs.aws-security-hub-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-security-hub-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Configuration

### Environment Variables

- `AWS_PROFILE`: AWS profile to use (optional, defaults to default profile)
- `AWS_REGION`: AWS region to use (optional, defaults to us-east-1)
- `FASTMCP_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `SECURITY_HUB_MAX_RESULTS`: Maximum number of results to return per query (default: 100)

## Usage Examples

### Get Recent Critical Findings

```
Get all critical severity findings from the last 7 days
```

### Check Compliance Status

```
Show me the compliance summary for AWS Foundational Security Standard
```

### Analyze Security Trends

```
Get security finding statistics grouped by severity for the last 30 days
```

### Update Finding Status

```
Mark finding with ID "arn:aws:securityhub:us-east-1:123456789012:finding/..." as resolved
```

## Tools

### get_security_findings
Retrieve security findings with filtering options including severity, compliance status, workflow status, and time ranges.

### get_compliance_summary
Get compliance status summary across enabled security standards and controls.

### get_insights
Retrieve Security Hub insights including both AWS-managed and custom insights.

### get_finding_statistics
Get aggregated statistics about security findings with grouping options.

### update_finding_workflow
Update the workflow status of security findings and add notes.

### manage_standards
Enable or disable security standards and individual controls.

### get_security_score
Retrieve the overall security score and trends over time.

## Development

### Local Development

1. Clone the repository
2. Navigate to the server directory: `cd src/aws-security-hub-mcp-server`
3. Install dependencies: `uv sync --all-groups`
4. Run tests: `uv run pytest`
5. Run the server locally: `uv run awslabs.aws-security-hub-mcp-server`

### Testing

The server includes comprehensive tests:

- Unit tests for all tools and utilities
- Integration tests with mocked AWS services
- Live tests (require AWS credentials and Security Hub setup)

Run tests with:
```bash
uv run pytest --cov --cov-branch --cov-report=term-missing
```

## Security Considerations

- This server requires AWS credentials with Security Hub permissions
- All API calls are made using the configured AWS credentials
- Findings data may contain sensitive security information
- Use appropriate IAM policies to limit access to necessary Security Hub resources
- Consider using AWS IAM roles with temporary credentials in production environments

## Troubleshooting

### Common Issues

1. **AccessDenied errors**: Ensure your AWS credentials have the required Security Hub permissions
2. **Security Hub not enabled**: Enable Security Hub in your AWS account and region
3. **No findings returned**: Check if Security Hub has findings in the specified region and time range
4. **Rate limiting**: The server implements appropriate rate limiting for AWS API calls

### Debug Mode

Enable debug logging by setting `FASTMCP_LOG_LEVEL=DEBUG` to see detailed API calls and responses.

## Contributing

See the main repository [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.