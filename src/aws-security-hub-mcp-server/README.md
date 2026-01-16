# AWS Security Hub MCP Server

A Model Context Protocol (MCP) server for AWS Security Hub that provides comprehensive security findings analysis, compliance reporting, security posture management, and historical trend analysis with 10 specialized tools.

This MCP server enables AI assistants to interact with AWS Security Hub through official APIs, providing complete data access with proper pagination for security monitoring, compliance assessment, and trend analysis.

## Available Tools

The AWS Security Hub MCP server provides 10 comprehensive tools for security analysis and compliance management:

### Core Data Retrieval Tools
- **get-security-findings**: Retrieve and filter security findings from Security Hub
- **get-finding-statistics**: Analyze security findings with aggregated statistics
- **get-security-score**: Calculate overall security posture score
- **get-enabled-standards**: List currently enabled security standards
- **list-security-control-definitions**: Browse available security controls
- **get-finding-history**: Track changes to specific findings over time
- **describe-standards-controls**: Get detailed control information for standards

### Advanced Report Generation Tools
- **generate-security-report**: Comprehensive security analysis with executive summary, findings breakdown, and actionable recommendations
- **generate-compliance-report**: Standards-focused compliance analysis with control status and compliance recommendations
- **generate-security-trends-report**: Historical trend analysis to identify patterns and security posture changes over time

## Features

### Core Data Retrieval Tools
- **Get Security Findings**: Retrieve and filter security findings from Security Hub
- **Get Finding Statistics**: Analyze security findings with aggregated statistics
- **Get Security Score**: Calculate overall security posture score
- **Get Enabled Standards**: List currently enabled security standards
- **List Security Control Definitions**: Browse available security controls
- **Get Finding History**: Track changes to specific findings over time
- **Describe Standards Controls**: Get detailed control information for standards

### Advanced Report Generation Tools
- **Generate Security Report**: Comprehensive security analysis with executive summary, findings breakdown, and actionable recommendations
- **Generate Compliance Report**: Standards-focused compliance analysis with control status and compliance recommendations
- **Generate Security Trends Report**: Historical trend analysis to identify patterns and security posture changes over time

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
3. AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
4. AWS Security Hub enabled in your AWS account
5. Appropriate IAM permissions for Security Hub operations

### Required IAM Permissions

**Minimum Required Permissions (Recommended):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "securityhub:GetFindings",
                "securityhub:GetFindingHistory",
                "securityhub:DescribeStandards",
                "securityhub:DescribeStandardsControls",
                "securityhub:GetEnabledStandards",
                "securityhub:ListSecurityControlDefinitions"
            ],
            "Resource": [
                "arn:aws:securityhub:*:*:hub/*",
                "arn:aws:securityhub:*:*:finding/*",
                "arn:aws:securityhub:*:*:standard/*"
            ]
        }
    ]
}
```

## Installation

| Kiro   | Cursor  | VS Code |
|:------:|:-------:|:-------:|
| [![Install Kiro](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-security-hub-mcp-server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.aws-security-hub-mcp-server%40latest%22%5D%2C%20%22env%22%3A%20%7B%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%2C%20%22AWS_PROFILE%22%3A%20%22default%22%2C%20%22AWS_REGION%22%3A%20%22us-east-1%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-security-hub-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXNlY3VyaXR5LWh1Yi1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Security%20Hub%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-security-hub-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

> **Note:** The install buttons above configure `AWS_REGION` to `us-east-1` and `AWS_PROFILE` to `default` by default. Update these values in your MCP configuration after installation if you need different settings.

Add the MCP server to your configuration file (for [Kiro](https://kiro.dev/docs/mcp/) add to `.kiro/settings/mcp.json` - see [configuration path](https://kiro.dev/docs/cli/mcp/configuration/#mcp-server-loading-priority)):

```json
{
  "mcpServers": {
    "awslabs.aws-security-hub-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-security-hub-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-security-hub-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-security-hub-mcp-server@latest",
        "awslabs.aws-security-hub-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Configuration

### Environment Variables

- `AWS_PROFILE`: AWS profile to use (optional, defaults to "default" profile)
- `AWS_REGION`: AWS region to use (optional, defaults to us-east-1)
- `FASTMCP_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `SECURITY_HUB_MAX_RESULTS`: Maximum number of results to return per query (default: 50)

## Tools

### Core Data Retrieval Tools

### get-security-findings
Retrieves security findings from AWS Security Hub with comprehensive filtering capabilities. You can filter by severity levels (CRITICAL, HIGH, MEDIUM, LOW), compliance status (PASSED, FAILED), workflow status (NEW, NOTIFIED, RESOLVED), resource types, and time ranges. This tool supports pagination to handle large datasets and returns detailed finding information including remediation guidance and affected resources.

**Example:** *"Show me all CRITICAL and HIGH severity findings from the last 7 days that are still NEW"*

### get-finding-statistics
Provides aggregated statistical analysis of your security findings, helping you understand trends and distributions across your security posture. You can group statistics by severity level, workflow status, product name, resource type, or compliance status. This tool is perfect for generating security dashboards and identifying patterns in your security findings over time.

**Example:** *"Get security finding statistics grouped by severity for the last 30 days to see our security trend"*

### get-security-score
Calculates your overall security score based on the severity distribution of active findings in your environment. The score uses a weighted algorithm that considers the number and severity of findings to provide a single metric (0-100) representing your security posture. This helps track security improvements over time and compare security status across different time periods.

**Example:** *"What's my current security score and how has it changed over the past month?"*

### get-enabled-standards
Lists all security standards currently enabled in your AWS Security Hub configuration, such as AWS Foundational Security Best Practices, CIS AWS Foundations Benchmark, and PCI DSS. For each standard, it shows the enablement status, subscription details, and any configuration issues that might prevent proper compliance checking.

**Example:** *"Show me which security standards are enabled and their current status"*

### list-security-control-definitions
Browses the complete catalog of available security controls in AWS Security Hub, providing detailed information about each control including its purpose, severity rating, remediation guidance, and regional availability. This tool helps you understand what security checks are available and plan your security standard implementations.

**Example:** *"List all available security controls related to S3 and their severity ratings"*

### get-finding-history
Tracks the complete change history for specific security findings, showing how findings have evolved over time. This includes status changes, severity updates, workflow modifications, and compliance status transitions. It's essential for understanding the lifecycle of security issues and demonstrating remediation progress for compliance reporting.

**Example:** *"Show me the complete history of changes for finding arn:aws:securityhub:us-east-1:123456789012:finding/abc123"*

### describe-standards-controls
Provides detailed information about the specific controls within enabled security standards, including their current status (ENABLED/DISABLED), control requirements, related compliance frameworks, and configuration parameters. This tool helps you understand exactly what each standard is checking and manage control configurations.

**Example:** *"Show me all controls in the AWS Foundational Security Best Practices standard and their current status"*

### Advanced Report Generation Tools

### generate-security-report
Creates comprehensive security analysis reports with executive summaries, findings breakdown by severity, actionable recommendations, and security standards status. This tool provides structured insights perfect for security dashboards, executive briefings, and security posture assessments. You can customize the level of detail and limit findings per severity level.

**Key Features:**
- Executive summary with security score and findings overview
- Detailed findings by severity level with remediation guidance
- Actionable security recommendations prioritized by risk
- Security standards status and compliance analysis
- Customizable detail level and finding limits

**Example:** *"Generate a comprehensive security report for the last 30 days with detailed findings for executive review"*

### generate-compliance-report
Produces standards-focused compliance reports analyzing adherence to enabled security standards, control status, and compliance recommendations. This tool categorizes compliance findings by type (Configuration, Access Control, Monitoring, etc.) and provides compliance-specific recommendations based on AWS Security Hub compliance data.

**Key Features:**
- Overall compliance percentage and standards analysis
- Control-level compliance details with status tracking
- Compliance findings categorized by security domain
- Standards-specific compliance status and recommendations
- Integration with AWS Config and Security Hub compliance data

**Example:** *"Create a compliance report showing our adherence to CIS and AWS Foundational Security standards"*

### generate-security-trends-report
Generates historical trend analysis reports to identify patterns, improvements, or deteriorations in security posture over multiple time periods. This tool uses only actual Security Hub data to prevent hallucination and provides statistical analysis, period comparisons, and actionable insights based on trend patterns.

**Key Features:**
- Historical analysis across multiple time periods (7, 14, 30, 90 days by default)
- Trend analysis for severity levels, compliance status, and resource types
- Security score progression over time with statistical insights
- Period-to-period comparisons and change analysis
- Actionable insights and recommendations based on detected trends
- Data quality assessment and reliability scoring

**Example:** *"Analyze security trends over the past 90 days to identify if our security posture is improving or declining"*

## Development

### Local Development

1. Clone the repository
2. Navigate to the server directory: `cd src/aws-security-hub-mcp-server`
3. Install dependencies: `uv sync --all-groups`
4. Run tests: `uv run pytest`
5. Run the server locally: `uv run awslabs.aws-security-hub-mcp-server`

### Testing

The server includes comprehensive tests:

- **Unit tests**: Mock-based tests for all 10 tools covering success cases, error handling, and edge cases (`test_mcp_server_functions.py`)
- **Integration tests**: MCP protocol tests for server functionality (`test_mcp_integration.py`)
- **Fixture tests**: Tests for all mock fixtures and test utilities (`test_fixtures_and_mocks.py`)

Run tests with:
```bash
# Run all available tests
uv run pytest

# Run with coverage reporting
uv run pytest --cov --cov-branch --cov-report=term-missing

# Run only unit tests (recommended for development)
uv run pytest tests/test_mcp_server_functions.py -v

# Run MCP integration tests
uv run pytest tests/test_mcp_integration.py -v

# Run fixture and mock tests
uv run pytest tests/test_fixtures_and_mocks.py -v
```

### Integration Testing with Real AWS

For integration testing with real AWS Security Hub data, use:

```bash
# Requires valid AWS credentials configured
python test_integration_with_aws.py
```

**Important:** This integration test requires:
- Valid AWS credentials (via environment variables, AWS credentials file, or IAM role)
- Appropriate Security Hub permissions
- Access to a real AWS account with Security Hub enabled

**Security Note:** Never commit real AWS credentials to version control. Use environment variables or AWS credential files for testing.

## Security Considerations

When using this MCP server, you should consider:

### AWS Shared Responsibility Model
This MCP server operates under the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/). AWS is responsible for Security Hub service security, while you are responsible for secure configuration of IAM policies, credential management, and proper use of this server.

### Data Security
- Security findings contain sensitive information about vulnerabilities and security posture
- All data is processed in memory only with no persistent storage
- Data transmission uses HTTPS encryption via AWS SDK
- Implement data classification procedures according to your organization's policy

### Authentication and Access Control
- Use IAM roles with temporary credentials in production environments
- Follow the principle of least privilege with scoped IAM policies
- Implement credential rotation for long-lived access keys
- Monitor credential usage with CloudTrail logging

### IAM Policy Best Practices
- Use resource-specific ARNs instead of wildcards when possible
- Implement condition statements to restrict access by region or time
- Regularly review and audit IAM policies
- Test policies using IAM policy simulator before deployment

### Monitoring and Auditing
- Enable CloudTrail logging for all Security Hub API calls
- Set up CloudWatch monitoring for unusual access patterns
- Implement application logging with appropriate log levels
- Review access logs regularly for security incidents

### Network Security
- Deploy in private subnets when running on AWS infrastructure
- Use VPC endpoints for Security Hub API calls
- Implement security groups restricting inbound access
- Enable VPC Flow Logs for network monitoring

Before using this server in production environments, conduct your own independent assessment to ensure compliance with your organization's security and quality control practices, as well as applicable laws, rules, and regulations.

## Troubleshooting

### Common Issues

1. **AccessDenied errors**: Ensure your AWS credentials have the required Security Hub permissions
2. **Security Hub not enabled**: Enable Security Hub in your AWS account and region
3. **No findings returned**: Check if Security Hub has findings in the specified region and time range
4. **Rate limiting**: The server implements appropriate rate limiting and pagination for AWS API calls
5. **Finding history not available**: Some findings may not have history records if they haven't been updated

### Debug Mode

Enable debug logging by setting `FASTMCP_LOG_LEVEL=DEBUG` to see detailed API calls and responses.

## Contributing

See the main repository [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](https://github.com/awslabs/mcp/blob/main/LICENSE) for details.
