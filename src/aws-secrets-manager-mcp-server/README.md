# AWS Secrets Manager MCP Server

A comprehensive Model Context Protocol (MCP) server for AWS Secrets Manager that provides secure secret lifecycle management through natural language interactions.

## Overview

This MCP server enables AI assistants to securely manage AWS Secrets Manager operations, including creating, retrieving, updating, and rotating secrets. It provides a complete interface for secret lifecycle management while maintaining security best practices.

## Key Features

### 🔐 Complete Secret Lifecycle Management
- **Create secrets** with structured or simple values
- **Retrieve secret values** with version control
- **Update secrets** with automatic versioning
- **Delete and restore** secrets with recovery windows
- **List and search** secrets with filtering capabilities

### 🔄 Automatic Rotation Support
- **Enable/disable rotation** with Lambda functions
- **Manual rotation triggers** for immediate updates
- **Rotation monitoring** and status tracking
- **Configurable rotation intervals** (1-365 days)

### 🏷️ Organization and Access Control
- **Tag management** for cost allocation and organization
- **Resource-based policies** for fine-grained access control
- **Cross-account access** configuration
- **Compliance and audit** support

### 🛡️ Security Best Practices
- **Encryption at rest** with AWS KMS integration
- **Encryption in transit** with TLS
- **Audit logging** through AWS CloudTrail
- **Access validation** and error handling
- **Secure password generation** with customizable requirements

## Installation

### Prerequisites

- Python 3.10 or higher
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Appropriate IAM permissions for Secrets Manager operations

### Install from PyPI

```bash
pip install awslabs.aws-secrets-manager-mcp-server
```

### Install from Source

```bash
git clone <repository-url>
cd aws-secrets-manager-mcp-server
pip install -e .
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Secrets Manager operations | `us-east-1` |
| `AWS_PROFILE` | AWS profile to use for authentication | None |
| `FASTMCP_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `WARNING` |

### AWS Credentials

The server supports all standard AWS credential methods:

1. **AWS CLI Configuration**
   ```bash
   aws configure
   ```

2. **Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **IAM Roles** (for EC2/Lambda/ECS deployments)

4. **AWS Profiles**
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:CreateSecret",
                "secretsmanager:GetSecretValue",
                "secretsmanager:UpdateSecret",
                "secretsmanager:DeleteSecret",
                "secretsmanager:RestoreSecret",
                "secretsmanager:ListSecrets",
                "secretsmanager:DescribeSecret",
                "secretsmanager:RotateSecret",
                "secretsmanager:GetRandomPassword",
                "secretsmanager:TagResource",
                "secretsmanager:UntagResource",
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:PutResourcePolicy",
                "secretsmanager:DeleteResourcePolicy"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:Encrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": "secretsmanager.*.amazonaws.com"
                }
            }
        }
    ]
}
```

## Usage

### Running the Server

```bash
# Run directly
awslabs.aws-secrets-manager-mcp-server

# Or with Python module
python -m awslabs.aws_secrets_manager_mcp_server.server
```

### Integration with MCP Clients

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "aws-secrets-manager": {
      "command": "awslabs.aws-secrets-manager-mcp-server",
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Available Tools

### Secret Management

#### `create-secret`
Create a new secret with optional configuration.

**Parameters:**
- `name` (required): Secret name (supports hierarchical naming like `prod/database/mysql`)
- `secret_value` (required): Secret value as string or JSON object
- `description` (optional): Human-readable description
- `kms_key_id` (optional): Custom KMS key for encryption
- `tags` (optional): List of tags for organization
- `region` (optional): AWS region override

**Examples:**
```python
# Simple API key
create_secret(
    name="prod/api-keys/stripe",
    secret_value="sk_live_abc123...",
    description="Stripe production API key"
)

# Database credentials
create_secret(
    name="prod/database/mysql",
    secret_value={
        "username": "admin",
        "password": "secure_password_123",
        "host": "db.example.com",
        "port": 3306,
        "dbname": "production"
    },
    tags=[
        {"Key": "Environment", "Value": "production"},
        {"Key": "Service", "Value": "database"}
    ]
)
```

## Best Practices

### Secret Naming
- Use hierarchical naming with forward slashes: `environment/service/component`
- Examples: `prod/database/mysql`, `staging/api/stripe`, `dev/cache/redis`
- Keep names descriptive but not revealing sensitive information

### Secret Structure
- Use JSON format for structured secrets (database credentials, API configurations)
- Include all necessary connection parameters
- Use consistent key naming across similar secrets

```json
{
    "username": "admin",
    "password": "secure_password",
    "host": "database.example.com",
    "port": 5432,
    "database": "production",
    "ssl_mode": "require"
}
```

### Security Considerations
- Never log or expose secret values in application logs
- Use customer-managed KMS keys for additional control
- Implement proper error handling to avoid information disclosure
- Regularly audit secret access patterns

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
