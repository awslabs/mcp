# AWS Infrastructure as Code MCP Server

Get started with this MCP server for creating and troubleshooting AWS infrastructure as code. Tools include CloudFormation template validation, compliance checking, deployment troubleshooting, CloudFormation documentation search, AWS CDK documentation search with official CDK knowledge bases, CDK code samples and constructs, and CDK and CloudFormation best practices.

## MCP highlights

- **Validate CloudFormation templates** before deployment to catch errors early
- **Debug failed CloudFormation deployments** with intelligent failure analysis and resolution guidance
- **Ensure security compliance** of your CloudFormation templates against AWS best practices
- **Search CloudFormation documentation** for resource types, properties, and template syntax
- **Search CDK documentation** and find AWS approved code examples for AWS CDK development
- **Find CDK code samples and community constructs** for common implementation patterns
- **Access CDK best practices** for secure and efficient infrastructure development
- **Get specific fix suggestions** with line numbers for CloudFormation template validation errors
- **Access CloudTrail deep links** for CloudFormation deployment troubleshooting


## Features

### Template Validation
- **Syntax and Schema Validation** - Validate CloudFormation templates using cfn-lint
- Catch syntax errors, invalid properties, and schema violations with specific fix suggestions

### Compliance Checking
- **Security and Compliance Rules** - Validate templates against security standards using cfn-guard
- Check against AWS Guard Rules Registry and Control Tower proactive controls

### Deployment Troubleshooting
- **Intelligent Failure Analysis** - Analyze and resolve CloudFormation deployment failures
- Pattern matching against 30+ known failure cases with CloudTrail deep links

### CloudFormation Documentation Search
- **CloudFormation Knowledge Access** - Search official CloudFormation documentation for resource types, properties, and syntax
- Find implementation guidance and examples for CloudFormation templates

### CDK Documentation Search
- **CDK Knowledge Access** - Search AWS CDK documentation, API references, and best practices
- Access to CDK API Reference, Best Practices Guide, Code Samples & Patterns, and CDK-NAG security checks

### CDK Code Samples & Constructs
- **Working Code Examples** - Find CDK code samples and community constructs for common patterns
- Search across multiple programming languages (TypeScript, Python, Java, C#, Go)

### CDK Best Practices
- **Security and Development Guidelines** - Access comprehensive CDK best practices for application configuration, coding, constructs, security, and testing
- Follow AWS-recommended patterns for secure and efficient infrastructure

## Available MCP Tools

### Read Documentation Tool

#### read_iac_documentation_page
Fetches and converts any Infrastructure as Code (CDK or CloudFormation) documentation page to markdown format.

**Use this tool to:**
- Read complete CDK documentation pages rather than just excerpts
- Read complete CloudFormation resource type documentation and property references
- Get detailed CloudFormation template syntax and examples
- Access CloudFormation API reference documentation
- Read CloudFormation hooks and lifecycle management guides
- Review CFN Guard policy validation rules and syntax
- Access CloudFormation CLI documentation and usage patterns

### CloudFormation Tools

#### validate_cloudformation_template
Validates CloudFormation template syntax, schema, and resource properties using cfn-lint.

**Use this tool to:**
- Validate AI-generated CloudFormation templates before deployment
- Get specific fix suggestions with line numbers for each error

**Parameters:**
- `template_content` (required): CloudFormation template as string
- `regions` (optional): List of AWS regions to validate against
- `ignore_checks` (optional): List of cfn-lint check IDs to ignore

#### check_cloudformation_template_compliance
Validates CloudFormation templates against security and compliance rules using cfn-guard.

**Use this tool to:**
- Ensure templates meet security and compliance requirements
- Get detailed remediation guidance for violations

**Parameters:**
- `template_content` (required): CloudFormation template as string
- `custom_rules` (optional): Custom cfn-guard rules to apply

#### troubleshoot_cloudformation_deployment
Analyzes failed CloudFormation stacks and provides resolution guidance.

**Use this tool to:**
- Diagnose deployment failures with pattern matching against 30+ known cases
- Get CloudTrail deep links and specific resolution steps

**Parameters:**
- `stack_name` (required): Name of the failed CloudFormation stack
- `region` (required): AWS region where the stack exists
- `include_cloudtrail` (optional): Whether to include CloudTrail analysis (defaults to true)

#### search_cloudformation_documentation
Searches AWS CloudFormation documentation knowledge bases and returns relevant best practices.

#### get_cloudformation_pre_deploy_validation_instructions
Returns instructions for CloudFormation's pre-deployment validation feature that validates templates during change set creation.

**Parameters:**
None - returns JSON with CLI commands and remediation guidance.

### CDK Tools

#### search_cdk_documentation
Searches AWS CDK documentation knowledge bases and returns relevant excerpts.

**Use this tool to:**
- Find specific information about CDK constructs, APIs, and implementation patterns
- Get implementation guidance from official CDK documentation
- Look up syntax and examples for CDK patterns
- Research best practices and architectural guidelines

**Documentation Sources:**
- AWS CDK API Reference
- AWS CDK Best Practices Guide
- AWS CDK Code Samples & Patterns
- CDK-NAG validation rules

**Parameters:**
- `query` (required): Search query for CDK documentation

**Search Tips:**
- Use specific construct names (e.g., "aws-lambda.Function", "aws-s3.Bucket")
- Include service names for better targeting (e.g., "S3 AND encryption")
- Use boolean operators: "DynamoDB AND table", "Lambda OR Function"
- Search for specific properties: "bucket encryption", "lambda environment variables"


**Parameters:**
- `url` (required): URL from search results to read the full page content
- `starting_index` (optional): Starting character index for pagination (default: 0)

#### search_cdk_samples_and_constructs
Searches CDK code samples, examples, constructs, and patterns documentation.

**Parameters:**
- `query` (required): Search query for CDK samples and constructs
- `language` (optional): Programming language filter (default: "typescript")

#### cdk_best_practices
Provides CDK best practices for application configuration, coding, constructs, security, and testing.

**Parameters:**
- None

## Usage Examples

### CloudFormation Examples

#### Validate a Template
```
Validate this CloudFormation template:
[paste your template content]
```

#### Check Compliance
```
Check this template for security and compliance issues:
[paste your template content]
```

#### Troubleshoot a Failed Deployment
```
Troubleshoot my CloudFormation stack named "my-app-stack" in us-east-1
```

#### Search CloudFormation Documentation
```
Search CloudFormation documentation for AWS::Lambda::Function properties
```

### CDK Examples

#### Search CDK Documentation
```
Search CDK documentation for S3 bucket encryption best practices
```

```
Find CDK examples for Lambda function with VPC configuration
```

```
Show me CDK constructs for DynamoDB table with encryption
```

#### Read Infrastructure as Code Documentation Page
```
Read the full CDK documentation for aws-s3.Bucket from this URL: [URL from search results]
```

```
Read the complete CloudFormation documentation for AWS::S3::Bucket from this URL: [URL from search results]
```

#### Search CDK Samples and Constructs
```
Find CDK code samples for serverless API with TypeScript
```

```
Show me Python CDK examples for API Gateway with Lambda integration
```

#### Consult CDK Best Practices
```
Suggest improvements to my CDK setup based on the best practices
```

```
What are the CDK security best practices for S3 buckets?
```

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Configure AWS credentials:
   - Via AWS CLI: `aws configure`
   - Or set environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
4. Ensure your IAM role or user has the necessary permissions for CloudFormation and CloudTrail access

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iac-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-named-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-iac-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlhYy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItbmFtZWQtcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Infrastructure%20as%20Code%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-named-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-iac-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-iac-mcp-server@latest",
        "awslabs.aws-iac-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

or docker after a successful `docker build -t awslabs/aws-iac-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

NOTE: Docker installation is optional

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_PROFILE=your-aws-profile",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--volume",
        "${HOME}/.aws:/root/.aws:ro",
        "awslabs/aws-iac-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

NOTE: Your credentials will need to be kept refreshed from your host

## Security Considerations

⚠️ **Privacy Notice**: This MCP server executes AWS API calls using your credentials and shares the response data with your third-party AI model provider (e.g., Kiro, Claude Desktop, Cursor, VS Code). Users are responsible for understanding your AI provider's data handling practices and ensuring compliance with your organization's security and privacy requirements when using this tool with AWS resources.

### IAM Permissions

The MCP server requires the following AWS permissions:

**For Template Validation and Compliance:**
- No AWS permissions required (local validation only)

**For Deployment Troubleshooting:**
- `cloudformation:DescribeStacks`
- `cloudformation:DescribeStackEvents`
- `cloudformation:DescribeStackResources`
- `cloudtrail:LookupEvents` (for CloudTrail deep links)

Example IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Development

### Local Development

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iac-mcp-server

# Install dependencies
uv sync

# Run the server
uv run awslabs.aws-iac-mcp-server
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.aws_iac_mcp_server --cov-report=term-missing
```

## Contributing

See [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-iac-mcp-server/LICENSE) file for details.
