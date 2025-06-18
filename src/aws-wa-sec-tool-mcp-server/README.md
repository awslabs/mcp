# AWS Well-Architected Security Assessment Tool MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.aws-wa-sec-tool-mcp-server.svg)](https://pypi.org/project/awslabs.aws-wa-sec-tool-mcp-server/)

A Model Context Protocol (MCP) server that provides tools for assessing AWS environments against the AWS Well-Architected Framework Security Pillar. This server enables AI assistants to help users evaluate their AWS security posture, identify potential vulnerabilities, and implement best practices according to the Well-Architected Framework.

## Features

- **Security Service Status**: Check status of AWS security services (GuardDuty, Security Hub, Inspector, IAM Access Analyzer)
- **Security Findings**: Retrieve and analyze findings from AWS security services
- **Well-Architected Analysis**: Analyze security posture against Well-Architected Framework recommendations
- **Resource Discovery**: Explore AWS resources across multiple services and regions through Resource Explorer
- **Data Protection**: Check storage configuration for encryption of data at rest
- **Network Security**: Verify network configuration for encryption of data in transit
- **Compliance Verification**: Check compliance status of AWS resources against security standards
- **Security Context**: Access stored security context data for comprehensive analysis

Customers can use the `CheckSecurityServices` tool to verify if critical AWS security services are enabled in their environment. The `GetSecurityFindings` tool retrieves findings from these services, while `AnalyzeSecurityPosture` performs a comprehensive security assessment against the Well-Architected Framework. The `ExploreAwsResources` tool provides inventory capabilities across services and regions to ensure complete visibility of the AWS environment.

## Installation

```bash
# Install using uv
uv pip install awslabs.aws-wa-sec-tool-mcp-server

# Or install using pip
pip install awslabs.aws-wa-sec-tool-mcp-server
```

You can also run the MCP server directly from a local clone of the GitHub repository:

```bash
# Clone the awslabs repository
git clone https://github.com/awslabs/mcp.git

# Run the server directly using uv
uv --directory /path/to/aws-wa-sec-tool-mcp-server/src/aws-wa-sec-tool-mcp-server/awslabs/aws_wa_sec_review_mcp_server run server.py
```

## Usage Environments

The AWS Well-Architected Security Assessment Tool MCP Server is designed for the following environments:

- **Development and Testing**: Ideal for security posture assessment in development and test environments.
- **Security Audits**: Excellent for performing security audits and preparing for compliance reviews.
- **Well-Architected Reviews**: Perfect companion for conducting Well-Architected Framework reviews with a focus on the Security Pillar.
- **Security Baseline Establishment**: Useful for establishing security baselines across AWS environments.

**Not Recommended For**:
- **Production Remediation**: While the tool can identify issues in production environments, remediation actions should be carefully planned and executed outside the tool.
- **Continuous Monitoring**: The tool is designed for point-in-time assessments rather than continuous security monitoring.

**Important Note on Security Data**: When connecting to any environment, especially production, always prevent accidental exposure of sensitive security information.

## Production Considerations

While the AWS Well-Architected Security Assessment Tool MCP Server is primarily designed for security assessments, certain components can be considered for controlled production use with appropriate safeguards.

### When to Consider Production Use

The AWS Well-Architected Security Assessment Tool may be appropriate for production environments in the following scenarios:

1. **Security audits**: Periodic security posture assessments
2. **Compliance verification**: Checking resources against security standards
3. **Well-Architected reviews**: As part of scheduled Well-Architected Framework reviews

### When to Avoid Production Use

Avoid using the tool in production for:

1. High-frequency or continuous scanning that may impact performance
2. During critical business operations or peak traffic periods
3. On highly sensitive environments without proper IAM restrictions

## Configuration

Add the AWS Well-Architected Security Assessment Tool MCP Server to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.aws-wa-sec-tool-mcp-server": {
      "command": "uvx",
      "args": ["--from", "awslabs-aws-wa-sec-tool-mcp-server", "aws-wa-sec-tool-mcp-server"],
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
    "awslabs.aws-wa-sec-tool-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/aws-wa-sec-tool-mcp-server/src/aws-wa-sec-tool-mcp-server/awslabs/aws_wa_sec_review_mcp_server",
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

### Security Assessment Tools

These tools help you assess your AWS environment against the Well-Architected Framework Security Pillar.

- **CheckSecurityServices**: Verify if AWS security services are enabled
  - Checks status of GuardDuty, Security Hub, Inspector, and IAM Access Analyzer
  - Identifies which regions have services enabled or disabled
  - Provides recommendations for enabling critical security services

- **GetSecurityFindings**: Retrieve findings from AWS security services
  - Collects findings from Security Hub, GuardDuty, and Inspector
  - Filters findings by severity, resource type, or service
  - Provides context and remediation guidance for identified issues

- **GetResourceComplianceStatus**: Check compliance status of AWS resources
  - Evaluates resources against security standards and best practices
  - Identifies non-compliant resources and configuration issues
  - Provides compliance scores and improvement recommendations

- **GetStoredSecurityContext**: Access stored security context data
  - Retrieves previously collected security assessment data
  - Enables comparison of security posture over time
  - Provides historical context for security findings

- **ExploreAwsResources**: Inventory AWS resources across services and regions
  - Discovers resources across multiple AWS services
  - Maps relationships between resources for security context
  - Identifies resources that may not be properly secured

- **AnalyzeSecurityPosture**: Perform comprehensive security assessment
  - Evaluates overall security posture against Well-Architected Framework
  - Provides detailed recommendations for security improvements
  - Generates security score and prioritized action items

## Example Prompts

### Security Assessment

- "Check if AWS security services are enabled in my account"
- "Analyze my AWS environment against the Well-Architected Security Pillar"
- "Get security findings from my AWS account"
- "Check if my S3 buckets are properly encrypted"
- "Verify that my network traffic is encrypted in transit"

### Resource Exploration

- "Show me all resources in my AWS account"
- "Find resources that might have security issues"
- "List all EC2 instances across all regions"
- "Check which resources are not compliant with security standards"

### Security Analysis

- "Analyze my security posture against Well-Architected best practices"
- "What security improvements should I prioritize?"
- "Compare my current security posture with last month's assessment"
- "Generate a security report for my AWS environment"

## Requirements

- Python 3.10+
- AWS credentials with read-only permissions for security services
- AWS CLI configured with appropriate profiles (optional)

## License

This project is licensed under the Apache License, Version 2.0.
