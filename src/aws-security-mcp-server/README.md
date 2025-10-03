# AWS Security MCP Server

[![PyPI version](https://badge.fury.io/py/aws-security-mcp-server.svg)](https://badge.fury.io/py/aws-security-mcp-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

MCP Server for integrating with AWS Security services including Amazon GuardDuty and AWS Security Hub. This server provides tools to query security findings and monitor threats across your AWS environment.

## Features

- **Health Check**: Verify AWS connectivity and account information
- **GuardDuty Integration**: List and analyze threat detection findings
- **Security Hub Integration**: Access centralized security findings across AWS services
- **AWS Profile Support**: Use different AWS profiles for secure credential management
- **Structured Responses**: Consistent JSON responses with proper error handling

## Installation

### Using uv (recommended)

```bash
uv add aws-security-mcp-server
```

### Using pip

```bash
pip install aws-security-mcp-server
```

## Configuration

### AWS Credentials

Configure your AWS credentials using one of these methods:

1. **AWS CLI Profile** (recommended):
   ```bash
   aws configure --profile security-readonly
   ```

2. **Environment Variables**:
   ```bash
   export AWS_PROFILE=security-readonly
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **IAM Roles**: Use IAM roles when running on EC2 instances

### Required IAM Permissions

The server requires read-only permissions. Create an IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "securityhub:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}
```

## Usage

### Running the Server

```bash
# Using default AWS profile
aws-security-mcp-server

# Using specific AWS profile
AWS_PROFILE=security-readonly aws-security-mcp-server
```

### MCP Client Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "aws-security": {
      "command": "aws-security-mcp-server",
      "env": {
        "AWS_PROFILE": "security-readonly"
      }
    }
  }
}
```

## Available Tools

### health_check

Check server health status and AWS connectivity.

**Response:**
```json
{
  "status": "success",
  "service": "AWS STS",
  "data": {
    "aws_account": "123456789012",
    "aws_user_arn": "arn:aws:iam::123456789012:user/security-user",
    "aws_profile": "security-readonly"
  }
}
```

### list_guardduty_findings

List GuardDuty findings with IDs, threat types, and severity scores.

**Response:**
```json
{
  "status": "success",
  "service": "GuardDuty",
  "data": {
    "findings": [
      {
        "id": "abc123def456...",
        "type": "Backdoor:EC2/C&CActivity.B!DNS",
        "severity": 8.5
      }
    ],
    "total_count": 1
  }
}
```

### list_securityhub_findings

List Security Hub findings with title, severity, resource, and workflow status.

**Response:**
```json
{
  "status": "success",
  "service": "SecurityHub",
  "data": {
    "findings": [
      {
        "title": "EC2 instance has unrestricted access to the internet",
        "severity": "HIGH",
        "resource": "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        "workflow_status": "NEW"
      }
    ],
    "total_count": 1
  }
}
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-security-mcp-server

# Install dependencies
uv sync --all-groups

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov --cov-branch --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_server.py -v
```

### Code Quality

```bash
# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .

# Run type checking
uv run mypy .
```

## Troubleshooting

### Common Issues

1. **"No GuardDuty detectors found"**
   - Enable GuardDuty in your AWS account
   - Ensure you have the correct region configured

2. **"Account not subscribed to AWS Security Hub"**
   - Enable Security Hub in your AWS account
   - Configure Security Hub standards

3. **"AccessDenied" errors**
   - Verify IAM permissions are correctly configured
   - Check that your AWS profile has the required permissions

### Logging

The server logs to `aws_security_mcp.log` file. Check this file for detailed error information:

```bash
tail -f aws_security_mcp.log
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Security

See [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications) for information on reporting security issues.
