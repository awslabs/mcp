# AWS Well-Architected Security Pillar Review MCP Server

This Model Context Protocol (MCP) server provides tools for assessing AWS environments against the AWS Well-Architected Framework Security Pillar.

## Features

- Check status of AWS security services (GuardDuty, Security Hub, Inspector, IAM Access Analyzer)
- Retrieve security findings from AWS security services
- Analyze security posture against Well-Architected Framework recommendations
- Explore AWS resources across multiple services and regions
- Get resource compliance status against AWS Config rules

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd aws-wa-sec-review-mcp-server

# Install the package
pip install -e .
```

## Usage

### Environment Variables

The server uses the following environment variables:

- `AWS_REGION` - AWS region to use (default: 'us-east-1')
- `AWS_PROFILE` - AWS profile to use (default: 'default')
- `FASTMCP_LOG_LEVEL` - Log level for the MCP server (default: 'DEBUG')

### Running the Server

```bash
# Run with default settings
python main.py

# Run with SSE transport
python main.py --sse

# Run on a specific port
python main.py --port 8889
```

### Available Tools

1. **CheckSecurityServices** - Verify if AWS security services are enabled
2. **GetSecurityFindings** - Retrieve findings from AWS security services
3. **GetResourceComplianceStatus** - Check compliance status of AWS resources
4. **GetStoredSecurityContext** - Access stored security context data
5. **ExploreAwsResources** - Inventory AWS resources across services and regions
6. **AnalyzeSecurityPosture** - Perform comprehensive security assessment

## AWS Permissions

This tool requires read-only permissions to analyze the AWS environment. For specific IAM policies, refer to the AWS documentation for each service being analyzed.

## License

Licensed under the Apache License, Version 2.0.
