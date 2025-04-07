# AWS Terraform MCP Server

MCP server for Terraform on AWS best practices, infrastructure as code patterns, and security compliance with Checkov.

## Features

- **Terraform Best Practices** - Get prescriptive Terraform advice for building applications on AWS
  - AWS Well-Architected guidance for Terraform configurations
  - Security and compliance recommendations
  - AWSCC provider prioritization for consistent API behavior

- **Checkov Integration** - Work with Checkov for security and compliance scanning
  - Run security scans on Terraform code to identify vulnerabilities
  - Automatically fix identified security issues when possible
  - Get detailed remediation guidance for compliance issues

- **AWS Provider Documentation** - Search for AWS and AWSCC provider resources
  - Find documentation for specific resources and attributes
  - Get example snippets and implementation guidance
  - Compare AWS and AWSCC provider capabilities

- **AWS-IA GenAI Modules** - Access specialized modules for AI/ML workloads
  - Amazon Bedrock module for generative AI applications
  - OpenSearch Serverless for vector search capabilities
  - SageMaker endpoint deployment for ML model hosting
  - Serverless Streamlit application deployment for AI interfaces

- **Terraform Workflow Execution** - Run Terraform commands directly
  - Initialize, plan, validate, apply, and destroy operations
  - Pass variables and specify AWS regions
  - Get formatted command output for analysis

## Tools and Resources

- **AWS Provider Resources**: Access resource listings via `terraform://aws_provider_resources_listing`
- **AWSCC Provider Resources**: Access resource listings via `terraform://awscc_provider_resources_listing`
- **Terraform Workflow Guide**: Get command guidance via `terraform://workflow_guide`

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Install Terraform CLI for workflow execution

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.terraform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.terraform-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Security Considerations

When using this MCP server, you should consider:

- Reviewing all Checkov warnings and errors manually
- Fixing security issues rather than ignoring them whenever possible
- Documenting clear justifications for any necessary exceptions
- Using the RunCheckovScan tool regularly to verify security compliance
- Preferring the AWSCC provider for its consistent API behavior and better security defaults

Before applying Terraform changes to production environments, you should conduct your own independent assessment to ensure that your infrastructure would comply with your own specific security and quality control practices and standards, as well as the local laws, rules, and regulations that govern you and your content.
