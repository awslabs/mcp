# AWS EC2 MCP Server

A comprehensive Model Context Protocol (MCP) server for managing AWS EC2 infrastructure including instances, AMIs, security groups, EBS volumes, snapshots, VPC networking, and SSH key pairs with secure storage options.

## Features

This MCP server acts as a **bridge** between MCP clients and AWS EC2, allowing generative AI models to create, configure, and manage EC2 resources. The server provides a secure way to interact with AWS EC2 resources while maintaining proper access controls and resource validation.

### Core Capabilities

- **EC2 Instances**: Complete lifecycle management - launch, terminate, start, stop, reboot, and detailed monitoring
- **Security Groups**: Full CRUD operations - create, modify, delete security groups and manage inbound/outbound rules
- **Key Pairs**: Create SSH key pairs with mandatory secure storage (Secrets Manager, S3+KMS, Parameter Store)
- **EBS Volumes**: Complete volume management - create, attach, detach, delete with support for different volume types
- **EBS Snapshots**: Create and list volume snapshots for backup and recovery
- **AMIs (Amazon Machine Images)**: Create custom AMIs from instances, list popular AMIs, and manage lifecycle
- **VPC & Networking**: Comprehensive networking support - manage VPCs, subnets, and find suitable placement options

### Security Features

- **Input Validation**: Comprehensive validation for all AWS resource IDs using regex patterns
- **Permission-Based Access Control**: Environment variable controls for write operations and sensitive data access
- **Response Sanitization**: Automatic sanitization to prevent sensitive information leakage (passwords, keys, etc.)
- **Secure Key Storage**: Mandatory private key storage with three options:
  - **AWS Secrets Manager**: Enterprise-grade secret management
  - **S3 + KMS Encryption**: Cost-effective storage with automatic encryption
  - **Parameter Store**: Simple parameter storage with encryption
- **Security Validation**: Comprehensive validation decorators and error handling
- **Write Operation Protection**: Configurable protection requiring explicit enabling of destructive operations

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate EC2 management permissions
2. **AWS Credentials**: Properly configured AWS credentials via:
   - AWS CLI (`aws configure`)
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - IAM roles (for EC2 instances)
   - AWS credential files
3. **Python 3.10+**: Required for running the MCP server
4. **Network Access**: Outbound internet access to AWS APIs

## Installation

|                                                                                                                                                                                                                                     Cursor                                                                                                                                                                                                                                     |                                                                                                                                                                                                                                                                 VS Code                                                                                                                                                                                                                                                                 |
| :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.ec2-mcp-server&config=ewogICJjb21tYW5kIjogInV2eCIsCiAgImFyZ3MiOiBbImF3c2xhYnMuZWMyLW1jcC1zZXJ2ZXJAbGF0ZXN0Il0sCiAgImVudiI6IHsKICAgICJBV1NfUFJPRklMRSI6ICJkZWZhdWx0IiwKICAgICJBV1NfUkVHSU9OIjogInVzLXdlc3QtMiIsCiAgICAiRkFTVE1DUF9MT0dfTEVWRUwiOiAiSU5GTyIsCiAgICAiQUxMT1dfV1JJVEUiOiAidHJ1ZSIsCiAgICAiQUxMT1dfU0VOU0lUSVZFX0RBVEEiOiAiZmFsc2UiCiAgfQp9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20EC2%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ec2-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%2C%22ALLOW_WRITE%22%3A%22true%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) |

### Using uvx (Recommended)

Configure the MCP server in your MCP client configuration (e.g., for Claude Desktop, edit the configuration file):

```json
{
  "mcpServers": {
    "awslabs.ec2-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ec2-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO",
        "ALLOW_WRITE": "true",
        "ALLOW_SENSITIVE_DATA": "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using Docker

First, build the Docker image:

```bash
docker build -t awslabs/ec2-mcp-server .
```

Then configure with Docker in your MCP client:

```json
{
  "mcpServers": {
    "awslabs.ec2-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env-file", "/path/to/.env",
        "awslabs/ec2-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration Options

### Environment Variables

#### Core Configuration
- **`AWS_PROFILE`**: AWS profile name (default: "default")
- **`AWS_REGION`**: AWS region for operations (default: "us-east-1")
- **`ALLOW_WRITE`**: Enable write operations like create/modify/delete (default: "false", **REQUIRED** for most operations)
- **`ALLOW_SENSITIVE_DATA`**: Enable access to sensitive resource data (default: "false")

#### Logging Configuration
- **`FASTMCP_LOG_LEVEL`**: Logging verbosity - DEBUG, INFO, WARNING, ERROR (default: "INFO")
- **`FASTMCP_LOG_FILE`**: Optional log file path for persistent logging

#### Key Storage Configuration (for create_key_pair)
- **`S3_KEYPAIR_BUCKET`**: S3 bucket for encrypted private keys (default: auto-generated)
- **`S3_KEYPAIR_PREFIX`**: S3 object prefix for organization (default: "private-keys")
- **`KMS_KEY_ID`**: Custom KMS key ID for S3 encryption (default: aws/s3)

### Security Settings

**Important**: Write operations are disabled by default for security. Set `ALLOW_WRITE=true` to enable resource creation/modification/deletion.

### Key Pair Storage Configuration

When creating key pairs, you must specify a storage method. Configure these environment variables for S3 KMS encrypted storage:

**S3 with KMS Encryption (Recommended - Most Cost-Effective):**

- **`S3_KEYPAIR_BUCKET`**: S3 bucket name for storing encrypted private keys (optional: defaults to `ec2-mcp-keypairs-{region}`)
- **`S3_KEYPAIR_PREFIX`**: S3 key prefix for organizing stored keys (default: "private-keys")
- **`KMS_KEY_ID`**: Custom KMS key ID (optional: defaults to aws/s3 default key)

**S3 Features:**
- **Automatic KMS encryption** with default aws/s3 key or custom KMS key
- **Tag support** - EC2 key pair tags are automatically applied to S3 objects (when provided)
- **URL encoding** - Special characters in tags are properly encoded
- **Secure storage** - Private keys stored as `.pem` files with proper content type

**Cost Comparison (1000 key pairs):**

- **S3 + KMS**: ~$0.003/month (99.9% cheaper!)
- Parameter Store: $0-50/month
- Secrets Manager: $400/month

## Available Tools

The server provides **33 tools** across 7 categories for comprehensive EC2 management:

### 🖥️ EC2 Instances (9 tools)

- **`list_instances`** - List EC2 instances with advanced filtering and status information
- **`get_instance_details`** - Get comprehensive instance details including networking and security
- **`launch_instance`** - Launch new instances with full configuration (AMI, type, security, networking)
- **`terminate_instance`** - Permanently terminate instances (requires ALLOW_WRITE=true)
- **`start_instance`** - Start stopped instances
- **`stop_instance`** - Stop running instances with optional force flag
- **`reboot_instance`** - Reboot running instances
- **`get_subnet_info`** - Get detailed subnet information for networking decisions
- **`list_subnets`** - List available subnets with filtering and VPC association

### 🔒 Security Groups (5 tools)

- **`list_security_groups`** - List security groups with filtering by ID, name, or VPC
- **`get_security_group_details`** - Get detailed security group rules and configuration
- **`create_security_group`** - Create new security groups with description and VPC association
- **`delete_security_group`** - Delete security groups (requires ALLOW_WRITE=true)
- **`modify_security_group_rules`** - Add/remove inbound and outbound rules with protocol/port configuration

### 🔑 Key Pairs (3 tools) - **SECURE STORAGE MANDATORY**

- **`list_key_pairs`** - List available EC2 key pairs with fingerprints and metadata
- **`create_key_pair`** - Create SSH key pairs with **mandatory secure storage**
  - **REQUIRED**: `storage_method` parameter (no default provided for security)
  - **Options**: "secrets_manager", "s3_encrypted", or "parameter_store"
  - **Key Types**: Supports RSA and ED25519 key generation
  - **S3 Features**: Automatic KMS encryption, tag propagation, proper content types
  - **Security**: Private keys never exposed through MCP interface
- **`delete_key_pair`** - Delete key pairs and optionally remove stored private keys

### 💾 EBS Volumes (5 tools)

- **`list_volumes`** - List EBS volumes with status, attachment info, and encryption details
- **`create_volume`** - Create new EBS volumes with size, type (gp2/gp3/io1/io2), and encryption
- **`delete_volume`** - Delete EBS volumes (must be unattached, requires ALLOW_WRITE=true)
- **`attach_volume`** - Attach volumes to EC2 instances with device specification
- **`detach_volume`** - Detach volumes from instances safely

### 📸 EBS Snapshots (2 tools)

- **`list_snapshots`** - List EBS snapshots with filtering by owner, volume, and status
- **`create_snapshot`** - Create point-in-time snapshots from EBS volumes for backup

### 📀 AMIs - Amazon Machine Images (4 tools)

- **`list_amis`** - List AMIs with ownership filtering and detailed metadata
- **`get_popular_amis`** - Get curated popular public AMIs (Amazon Linux, Ubuntu, Windows, RHEL)
- **`create_image`** - Create custom AMIs from running instances with reboot options
- **`deregister_image`** - Deregister/delete AMIs (requires ALLOW_WRITE=true)

### 🌐 VPC & Networking (5 tools)

- **`list_vpcs`** - List Virtual Private Clouds with CIDR and default status
- **`get_default_vpc`** - Get the default VPC for the current region
- **`find_suitable_subnet`** - Find appropriate subnets for instance placement based on requirements
- **`delete_vpc`** - Delete VPCs with dependency checking (advanced operation)
- **`list_subnets`** - List subnets with VPC filtering and availability zone information

## Common Workflows

### 🚀 Launch a Web Server

1. **`get_popular_amis`** - Find the latest Amazon Linux 2023 AMI
2. **`create_key_pair`** - Create SSH access (MUST choose storage: "secrets_manager", "s3_encrypted", or "parameter_store")
3. **`create_security_group`** - Create security group allowing HTTP (port 80) and SSH (port 22)
4. **`launch_instance`** - Launch instance with AMI, key pair, and security group
5. **`get_instance_details`** - Verify instance is running and get public IP

### 🎯 Create Custom AMI

1. **`list_instances`** - Find your pre-configured instance
2. **`stop_instance`** - Stop instance for consistent snapshot (optional but recommended)
3. **`create_image`** - Create AMI from the stopped instance
4. **`start_instance`** - Restart the original instance if stopped
5. **`list_amis`** - Verify AMI creation progress

### 📦 Volume Management & Backup

1. **`create_volume`** - Create additional EBS storage
2. **`attach_volume`** - Attach to running instance (specify device like /dev/sdf)
3. **`create_snapshot`** - Create backup snapshot of the volume
4. **`list_snapshots`** - Monitor snapshot progress and manage backups

### 🔧 Security Group Management

1. **`create_security_group`** - Create new security group with description
2. **`modify_security_group_rules`** - Add inbound rules (e.g., port 80, 443, 22)
3. **`list_security_groups`** - Review security group configurations
4. **`get_security_group_details`** - Examine specific rule details

## Required AWS Permissions

The server requires comprehensive IAM permissions for EC2 management and secure key storage:

### Minimum Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:PutParameter",
        "ssm:DeleteParameter",
        "ssm:AddTagsToResource"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/ec2/keypairs/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:CreateBucket",
        "s3:PutBucketEncryption",
        "s3:PutPublicAccessBlock",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ec2-mcp-keypairs-*",
        "arn:aws:s3:::ec2-mcp-keypairs-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:CreateSecret",
        "secretsmanager:DeleteSecret",
        "secretsmanager:TagResource"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:ec2/keypairs/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": [
            "s3.*.amazonaws.com",
            "secretsmanager.*.amazonaws.com",
            "ssm.*.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

### 🔒 Security Considerations

- **Principle of Least Privilege**: The above permissions can be further restricted to specific resources
- **Production Use**: Consider limiting `ec2:*` to specific actions needed for your use case
- **Key Storage**: Choose appropriate storage method based on your security and cost requirements
- **Region Restriction**: Add region conditions to limit operations to specific AWS regions

## License

This project is licensed under the Apache License, Version 2.0.
