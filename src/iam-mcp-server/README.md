# AWS IAM MCP Server

A Model Context Protocol (MCP) server for comprehensive AWS Identity and Access Management (IAM) operations. This server provides AI assistants with the ability to manage IAM users, roles, policies, and permissions while following security best practices.

## Features

### Core IAM Management
- **User Management**: Create, list, retrieve, and delete IAM users
- **Role Management**: Create, list, and manage IAM roles with trust policies
- **Group Management**: Create, list, retrieve, and delete IAM groups with member management
- **Policy Management**: List and manage IAM policies (managed and inline)
- **Inline Policy Management**: Full CRUD operations for user and role inline policies
- **Permission Management**: Attach/detach policies to users and roles
- **Access Key Management**: Create and delete access keys for users
- **Security Simulation**: Test policy permissions before applying them

### Security Features
- **Policy Simulation**: Test permissions without making changes
- **Force Delete**: Safely remove users with all associated resources
- **Permissions Boundary Support**: Set permission boundaries for enhanced security
- **Trust Policy Validation**: Validate JSON trust policies for roles
- **Read-Only Mode**: Run server in read-only mode to prevent any modifications

### Best Practices Integration
- Follows AWS IAM security best practices
- Supports principle of least privilege
- Provides warnings for sensitive operations
- Includes comprehensive error handling

## Installation

```bash
# Install using uv (recommended)
uv tool install awslabs.iam-mcp-server

# Or install using pip
pip install awslabs.iam-mcp-server
```

## Configuration

### AWS Credentials
The server requires AWS credentials to be configured. You can use any of the following methods:

1. **AWS Profile** (recommended):
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **IAM Roles** (for EC2/Lambda):
   The server will automatically use IAM roles when running on AWS services.

### Required IAM Permissions

The AWS credentials used by this server need the following IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ListUsers",
                "iam:GetUser",
                "iam:CreateUser",
                "iam:DeleteUser",
                "iam:ListRoles",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:ListGroups",
                "iam:GetGroup",
                "iam:CreateGroup",
                "iam:DeleteGroup",
                "iam:AddUserToGroup",
                "iam:RemoveUserFromGroup",
                "iam:AttachGroupPolicy",
                "iam:DetachGroupPolicy",
                "iam:ListAttachedGroupPolicies",
                "iam:ListGroupPolicies",
                "iam:ListPolicies",
                "iam:GetPolicy",
                "iam:CreatePolicy",
                "iam:DeletePolicy",
                "iam:AttachUserPolicy",
                "iam:DetachUserPolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:ListAttachedUserPolicies",
                "iam:ListAttachedRolePolicies",
                "iam:ListUserPolicies",
                "iam:ListRolePolicies",
                "iam:GetUserPolicy",
                "iam:GetRolePolicy",
                "iam:PutUserPolicy",
                "iam:PutRolePolicy",
                "iam:GetGroupsForUser",
                "iam:ListAccessKeys",
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey",
                "iam:SimulatePrincipalPolicy",
                "iam:RemoveUserFromGroup",
                "iam:DeleteUserPolicy",
                "iam:DeleteRolePolicy"
            ],
            "Resource": "*"
        }
    ]
}
```

### MCP Client Configuration

#### Amazon Q CLI
Add to your `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

#### Cline
Add to your `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

#### Cursor
[![Install in Cursor](https://img.shields.io/badge/Install%20in-Cursor-blue?style=flat-square&logo=cursor)](cursor://mcp/install?config=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImF3c2xhYnMuaWFtLW1jcC1zZXJ2ZXIiOiB7CiAgICAgICJjb21tYW5kIjogInV2eCIsCiAgICAgICJhcmdzIjogWyJhd3NsYWJzLmlhbS1tY3Atc2VydmVyQGxhdGVzdCJdLAogICAgICAiZW52IjogewogICAgICAgICJBV1NfUFJPRklMRSI6ICJ5b3VyLWF3cy1wcm9maWxlIiwKICAgICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiLAogICAgICAgICJGQVNUTUNQX0xPR19MRVZFTCI6ICJFUlJPUiIKICAgICAgfQogICAgfQogIH0KfQo=)

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Read-Only Mode

The server supports a read-only mode that prevents all mutating operations while still allowing read operations. This is useful for:

- **Safety**: Preventing accidental modifications in production environments
- **Testing**: Allowing safe exploration of IAM resources without risk of changes
- **Auditing**: Running the server in environments where only read access should be allowed

### Enabling Read-Only Mode

Add the `--readonly` flag when starting the server:

```bash
# Using uvx
uvx awslabs.iam-mcp-server@latest --readonly

# Or if installed locally
python -m awslabs.iam_mcp_server.server --readonly
```

### MCP Client Configuration with Read-Only Mode

#### Amazon Q CLI
```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### Other MCP Clients
Simply add `"--readonly"` to the args array in your MCP configuration.

### Operations Blocked in Read-Only Mode

When read-only mode is enabled, the following operations will return an error:
- `create_user`
- `delete_user`
- `create_role`
- `attach_user_policy`
- `detach_user_policy`
- `create_access_key`
- `delete_access_key`

### Operations Available in Read-Only Mode

These operations continue to work normally:
- `list_users`
- `get_user`
- `list_roles`
- `list_policies`
- `simulate_principal_policy`

## Available Tools

### User Management

#### `list_users`
List IAM users in the account with optional filtering.

**Parameters:**
- `path_prefix` (optional): Path prefix to filter users (e.g., "/division_abc/")
- `max_items` (optional): Maximum number of users to return (default: 100)

#### `get_user`
Get detailed information about a specific IAM user including attached policies, groups, and access keys.

**Parameters:**
- `user_name`: The name of the IAM user to retrieve

#### `create_user`
Create a new IAM user.

**Parameters:**
- `user_name`: The name of the new IAM user
- `path` (optional): The path for the user (default: "/")
- `permissions_boundary` (optional): ARN of the permissions boundary policy

#### `delete_user`
Delete an IAM user with optional force cleanup.

**Parameters:**
- `user_name`: The name of the IAM user to delete
- `force` (optional): Force delete by removing all attached resources first (default: false)

### Role Management

#### `list_roles`
List IAM roles in the account with optional filtering.

**Parameters:**
- `path_prefix` (optional): Path prefix to filter roles (e.g., "/service-role/")
- `max_items` (optional): Maximum number of roles to return (default: 100)

#### `create_role`
Create a new IAM role with a trust policy.

**Parameters:**
- `role_name`: The name of the new IAM role
- `assume_role_policy_document`: The trust policy document in JSON format
- `path` (optional): The path for the role (default: "/")
- `description` (optional): Description of the role
- `max_session_duration` (optional): Maximum session duration in seconds (default: 3600)
- `permissions_boundary` (optional): ARN of the permissions boundary policy

### Group Management

#### `list_groups`
List IAM groups in the account with optional filtering.

**Parameters:**
- `path_prefix` (optional): Path prefix to filter groups (e.g., "/division_abc/")
- `max_items` (optional): Maximum number of groups to return (default: 100)

#### `get_group`
Get detailed information about a specific IAM group including members, attached policies, and inline policies.

**Parameters:**
- `group_name`: The name of the IAM group to retrieve

#### `create_group`
Create a new IAM group.

**Parameters:**
- `group_name`: The name of the new IAM group
- `path` (optional): The path for the group (default: "/")

#### `delete_group`
Delete an IAM group with optional force cleanup.

**Parameters:**
- `group_name`: The name of the IAM group to delete
- `force` (optional): Force delete by removing all members and policies first (default: false)

#### `add_user_to_group`
Add a user to an IAM group.

**Parameters:**
- `group_name`: The name of the IAM group
- `user_name`: The name of the IAM user

#### `remove_user_from_group`
Remove a user from an IAM group.

**Parameters:**
- `group_name`: The name of the IAM group
- `user_name`: The name of the IAM user

#### `attach_group_policy`
Attach a managed policy to an IAM group.

**Parameters:**
- `group_name`: The name of the IAM group
- `policy_arn`: The ARN of the policy to attach

#### `detach_group_policy`
Detach a managed policy from an IAM group.

**Parameters:**
- `group_name`: The name of the IAM group
- `policy_arn`: The ARN of the policy to detach

### Policy Management

#### `list_policies`
List IAM policies in the account.

**Parameters:**
- `scope` (optional): Scope of policies to list: "All", "AWS", or "Local" (default: "Local")
- `only_attached` (optional): Only return policies that are attached (default: false)
- `path_prefix` (optional): Path prefix to filter policies
- `max_items` (optional): Maximum number of policies to return (default: 100)

#### `attach_user_policy`
Attach a managed policy to an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `policy_arn`: The ARN of the policy to attach

#### `detach_user_policy`
Detach a managed policy from an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `policy_arn`: The ARN of the policy to detach

### Access Key Management

#### `create_access_key`
Create a new access key for an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user

**⚠️ Security Warning:** The secret access key is only returned once and cannot be retrieved again.

#### `delete_access_key`
Delete an access key for an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `access_key_id`: The access key ID to delete

### Security Analysis

#### `simulate_principal_policy`
Simulate IAM policy evaluation for a principal to test permissions.

**Parameters:**
- `policy_source_arn`: ARN of the user or role to simulate
- `action_names`: List of actions to simulate
- `resource_arns` (optional): List of resource ARNs to test against
- `context_entries` (optional): Context entries for the simulation

### Inline Policy Management

#### `put_user_policy`
Create or update an inline policy for an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `policy_name`: The name of the inline policy
- `policy_document`: The policy document in JSON format (string or dict)

#### `get_user_policy`
Retrieve an inline policy for an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `policy_name`: The name of the inline policy

#### `delete_user_policy`
Delete an inline policy from an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user
- `policy_name`: The name of the inline policy to delete

#### `list_user_policies`
List all inline policies for an IAM user.

**Parameters:**
- `user_name`: The name of the IAM user

#### `put_role_policy`
Create or update an inline policy for an IAM role.

**Parameters:**
- `role_name`: The name of the IAM role
- `policy_name`: The name of the inline policy
- `policy_document`: The policy document in JSON format (string or dict)

#### `get_role_policy`
Retrieve an inline policy for an IAM role.

**Parameters:**
- `role_name`: The name of the IAM role
- `policy_name`: The name of the inline policy

#### `delete_role_policy`
Delete an inline policy from an IAM role.

**Parameters:**
- `role_name`: The name of the IAM role
- `policy_name`: The name of the inline policy to delete

#### `list_role_policies`
List all inline policies for an IAM role.

**Parameters:**
- `role_name`: The name of the IAM role

## Usage Examples

### Basic User Management
```python
# List all users
users = await list_users()

# Get specific user details
user_details = await get_user(user_name="john.doe")

# Create a new user
new_user = await create_user(
    user_name="jane.smith",
    path="/developers/"
)

# Delete a user (with force cleanup)
await delete_user(user_name="old.user", force=True)
```

### Role Management
```python
# Create a role for EC2 instances
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

role = await create_role(
    role_name="EC2-S3-Access-Role",
    assume_role_policy_document=json.dumps(trust_policy),
    description="Role for EC2 instances to access S3"
)
```

### Group Management
```python
# Create a new group
group = await create_group(
    group_name="Developers",
    path="/teams/"
)

# Add users to the group
await add_user_to_group(
    group_name="Developers",
    user_name="john.doe"
)

# Attach a policy to the group
await attach_group_policy(
    group_name="Developers",
    policy_arn="arn:aws:iam::123456789012:policy/DeveloperPolicy"
)

# Get group details including members
group_details = await get_group(group_name="Developers")
```

### Policy Management
```python
# List customer managed policies
policies = await list_policies(scope="Local", only_attached=True)

# Attach a policy to a user
await attach_user_policy(
    user_name="developer",
    policy_arn="arn:aws:iam::123456789012:policy/DeveloperPolicy"
)
```

### Security Testing
```python
# Test if a user can perform specific actions
simulation = await simulate_principal_policy(
    policy_source_arn="arn:aws:iam::123456789012:user/developer",
    action_names=["s3:GetObject", "s3:PutObject"],
    resource_arns=["arn:aws:s3:::my-bucket/*"]
)
```

### Inline Policy Management
```python
# Create an inline policy for a user
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::my-bucket/*"
        }
    ]
}

await put_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy",
    policy_document=policy_document
)

# Retrieve an inline policy
policy = await get_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy"
)

# List all inline policies for a user
policies = await list_user_policies(user_name="developer")

# Create an inline policy for a role
await put_role_policy(
    role_name="EC2-S3-Access-Role",
    policy_name="S3ReadOnlyPolicy",
    policy_document={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": "*"
            }
        ]
    }
)

# Delete an inline policy
await delete_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy"
)
```

## Security Best Practices

1. **Principle of Least Privilege**: Always grant the minimum permissions necessary
2. **Use Roles for Applications**: Prefer IAM roles over users for applications
3. **Regular Access Reviews**: Periodically review and clean up unused users and permissions
4. **Access Key Rotation**: Regularly rotate access keys
5. **Enable MFA**: Use multi-factor authentication where possible
6. **Permissions Boundaries**: Use permissions boundaries to set maximum permissions
7. **Policy Simulation**: Test policies before applying them to production
8. **Prefer Managed Policies**: Use managed policies over inline policies for reusable permissions
9. **Inline Policy Guidelines**: Use inline policies only for permissions unique to a single identity

## Error Handling

The server provides comprehensive error handling with descriptive messages:

- **Authentication Errors**: Clear messages for credential issues
- **Permission Errors**: Specific information about missing permissions
- **Resource Not Found**: Helpful messages when resources don't exist
- **Validation Errors**: Detailed feedback on invalid parameters

## Development

### Running Tests
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=awslabs.iam_mcp_server
```

### Local Development
```bash
# Install in development mode
uv pip install -e .

# Run the server directly
python -m awslabs.iam_mcp_server.server
```

## Contributing

Contributions are welcome! Please see the main repository's [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [AWS IAM documentation](https://docs.aws.amazon.com/iam/)
2. Review the [MCP specification](https://modelcontextprotocol.io/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
