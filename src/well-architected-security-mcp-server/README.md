# AWS Well-Architected Security Assessment Tool MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.well-architected-security-mcp-server.svg)](https://pypi.org/project/awslabs.well-architected-security-mcp-server/)

A Model Context Protocol (MCP) server that provides operational tools for monitoring and assessing AWS environments against the AWS Well-Architected Framework Security Pillar. This server enables AI assistants to help operations teams evaluate security posture, monitor compliance status, and optimize security costs while maintaining operational excellence according to the Well-Architected Framework.

## Features

- **Operational Security Monitoring**: Monitor status of AWS security services (GuardDuty, Security Hub, Inspector, IAM Access Analyzer) across your infrastructure
- **Security Operations Dashboard**: Retrieve and analyze security findings from AWS services for operational visibility
- **Compliance Operations**: Continuously assess security posture against Well-Architected Framework for operational compliance
- **Resource Operations**: Discover and monitor AWS resources across multiple services and regions for security operations
- **Cost-Effective Data Protection**: Monitor storage configuration for encryption compliance while optimizing security costs
- **Network Operations Security**: Verify network configuration for encryption compliance in operational environments
- **Compliance Monitoring**: Monitor compliance status of AWS resources against security standards for operational reporting
- **Security Operations Context**: Access stored security context data for operational analysis and trending

Operations teams can use the `CheckSecurityServices` tool to monitor if critical AWS security services are operational across their infrastructure. The `GetSecurityFindings` tool provides operational visibility into security findings, while `AnalyzeSecurityPosture` delivers comprehensive security operations reporting against the Well-Architected Framework. The `ExploreAwsResources` tool provides operational inventory capabilities across services and regions to ensure complete operational visibility and cost optimization of the AWS environment.

## Installation

```bash
# Install using uv
uv pip install awslabs.well-architected-security-mcp-server

# Or install using pip
pip install awslabs.well-architected-security-mcp-server
```

You can also run the MCP server directly from a local clone of the GitHub repository:

```bash
# Clone the awslabs repository
git clone https://github.com/awslabs/mcp.git

# Run the server directly using uv
uv --directory /path/to/well-architected-security-mcp-server/src/well-architected-security-mcp-server/awslabs/well_architected_security_mcp_server run server.py
```

## Usage Environments

The AWS Well-Architected Security Assessment Tool MCP Server is designed for operational use across the following environments:

- **Production Operations**: Monitor security posture and compliance status in production environments for operational excellence.
- **Compliance Operations**: Perform ongoing compliance monitoring and reporting for regulatory and internal requirements.
- **Security Operations Center (SOC)**: Integrate with SOC workflows for continuous security monitoring and incident response.
- **Cost Optimization**: Monitor security service costs and optimize security spending while maintaining compliance.
- **Operational Reporting**: Generate security operations reports and dashboards for stakeholders and management.

**Operational Considerations**:
- **Automated Remediation**: While the tool provides operational visibility, automated remediation should be implemented through separate operational workflows.
- **Monitoring Integration**: Designed for integration with existing monitoring and alerting systems for comprehensive operational coverage.

**Important Note on Security Data**: When connecting to any environment, especially production, always prevent accidental exposure of sensitive security information.

## Operational Deployment Considerations

The AWS Well-Architected Security Assessment Tool MCP Server is designed for operational deployment across various environments with appropriate operational controls.

### Operational Use Cases

The tool is well-suited for operational deployment in the following scenarios:

1. **Security Operations Monitoring**: Continuous monitoring of security posture and compliance status
2. **Operational Compliance Reporting**: Regular compliance verification and reporting workflows
3. **Cost Operations**: Monitoring security service costs and optimizing security spending
4. **Operational Dashboards**: Integration with operational dashboards and monitoring systems

### Operational Best Practices

For optimal operational deployment:

1. **Rate Limiting**: Implement appropriate rate limiting to avoid impacting AWS API limits
2. **Monitoring Integration**: Integrate with existing operational monitoring and alerting systems
3. **Access Controls**: Implement proper IAM controls and operational access patterns
4. **Cost Monitoring**: Monitor API costs and optimize query patterns for cost efficiency

## Configuration


| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.well-architected-security-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMud2VsbC1hcmNoaXRlY3RlZC1zZWN1cml0eS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0K) | [![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Well-Architected%20Security%20Assessment%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.well-architected-security-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Add the AWS Well-Architected Security Assessment Tool MCP Server to your MCP client configuration:

```json
{
  "mcpServers": {
    "well-architected-security-mcp-server": {
      "command": "uvx",
      "args": ["--from", "awslabs.well-architected-security-mcp-server", "well-architected-security-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile", // Optional - uses your local AWS configuration if not specified
        "AWS_REGION": "your-aws-region", // Optional - uses your local AWS configuration if not specified
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

If running from a local repository, configure the MCP client like this:

```json
{
  "mcpServers": {
    "well-architected-security-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/well-architected-security-mcp-server/src/well-architected-security-mcp-server/awslabs/well_architected_security_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "your-aws-region",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Security Controls

The AWS Well-Architected Security Assessment Tool MCP Server includes security controls in your MCP client configuration to limit access to sensitive data:

### IAM Best Practices

We strongly recommend creating dedicated IAM roles with least-privilege permissions when using the AWS Well-Architected Security Assessment Tool MCP Server:

1. **Create a dedicated IAM role** specifically for security assessment operations
2. **Apply least-privilege permissions** by attaching only the necessary read-only policies
3. **Use scoped-down resource policies** whenever possible
4. **Apply a permission boundary** to limit the maximum permissions

For detailed example IAM policies tailored for security assessment use cases, see the AWS documentation for each security service being analyzed.

## MCP Tools

### Security Operations Tools

These operational tools help you monitor and manage your AWS security posture against the Well-Architected Framework Security Pillar.

- **CheckSecurityServices**: Monitor AWS security services operational status
  - Monitors operational status of GuardDuty, Security Hub, Inspector, and IAM Access Analyzer
  - Identifies service availability across regions for operational visibility
  - Provides operational recommendations for maintaining security service coverage

- **GetSecurityFindings**: Operational security findings retrieval
  - Collects operational security findings from Security Hub, GuardDuty, and Inspector
  - Filters findings for operational prioritization by severity, resource type, or service
  - Provides operational context and cost-effective remediation guidance

- **GetResourceComplianceStatus**: Operational compliance monitoring
  - Monitors resources against security standards for operational compliance
  - Identifies non-compliant resources for operational remediation workflows
  - Provides compliance metrics and operational improvement recommendations

- **GetStoredSecurityContext**: Historical security operations data
  - Retrieves historical security operations data for trend analysis
  - Enables operational comparison of security posture over time
  - Provides operational context for security findings and cost optimization

- **ExploreAwsResources**: Operational resource inventory
  - Discovers resources across AWS services for operational visibility
  - Maps resource relationships for operational security context
  - Identifies resources requiring operational security attention

- **AnalyzeSecurityPosture**: Comprehensive security operations analysis
  - Evaluates operational security posture against Well-Architected Framework
  - Provides operational recommendations for security improvements and cost optimization
  - Generates operational security metrics and prioritized action items

## Example Prompts

### Security Operations Monitoring

- "Monitor the operational status of AWS security services across my account"
- "Generate an operational security report against the Well-Architected Security Pillar"
- "Show me current security findings that require operational attention"
- "Monitor encryption compliance across my S3 buckets for operational reporting"
- "Verify network encryption compliance for operational security standards"

### Operational Resource Management

- "Provide an operational inventory of all resources in my AWS account"
- "Identify resources with security issues that need operational attention"
- "List all EC2 instances across regions for security operations review"
- "Monitor which resources are not compliant with operational security standards"

### Security Operations Analysis

- "Analyze operational security posture against Well-Architected best practices"
- "What security improvements should operations prioritize for cost optimization?"
- "Compare current security operations metrics with last month's operational baseline"
- "Generate an operational security dashboard for management reporting"
- "Monitor security service costs and recommend optimization opportunities"

## Requirements

- Python 3.10+
- AWS credentials with read-only permissions for security services
- AWS CLI configured with appropriate profiles (optional)

## Testing

The AWS Well-Architected Security Assessment Tool MCP Server includes a comprehensive test suite to ensure functionality and reliability. The tests are organized by module and use pytest with mocks to avoid making actual AWS API calls.

### Test Structure

- `test_prompt_utils.py`: Tests for prompt template utilities
- `test_resource_utils.py`: Tests for AWS resource operations
- `test_storage_security.py`: Tests for storage encryption checks
- `test_network_security.py`: Tests for network security checks
- `test_security_services.py`: Tests for AWS security services

### Running Tests

The easiest way to run all tests is to use the provided script:

```bash
# Make the script executable if needed
chmod +x run_tests.sh

# Run the tests
./run_tests.sh
```

This script will:
1. Install required dependencies (pytest, pytest-asyncio, pytest-cov)
2. Run all tests with coverage reporting

For more detailed information about testing, see the tests/README.md file in the project repository.

## License

This project is licensed under the Apache License, Version 2.0.
