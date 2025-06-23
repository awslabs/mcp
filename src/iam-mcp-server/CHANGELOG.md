# Changelog

All notable changes to the AWS IAM MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-06-23

### Added
- **Inline Policy Management**: Full CRUD operations for user and role inline policies
  - `put_user_policy` - Create or update inline policies for IAM users
  - `get_user_policy` - Retrieve inline policy documents for users
  - `delete_user_policy` - Delete inline policies from users
  - `list_user_policies` - List all inline policies for a user
  - `put_role_policy` - Create or update inline policies for IAM roles
  - `get_role_policy` - Retrieve inline policy documents for roles
  - `delete_role_policy` - Delete inline policies from roles
  - `list_role_policies` - List all inline policies for a role
- New data models for inline policy operations:
  - `InlinePolicy` - Model for inline policy data
  - `InlinePolicyResponse` - Response model for inline policy operations
  - `InlinePolicyListResponse` - Response model for listing inline policies
- Comprehensive test coverage for all inline policy operations
- Enhanced documentation with usage examples and best practices
- Demo script showing inline policy management capabilities

### Enhanced
- Updated server instructions to include inline policy management guidance
- Added security best practices for inline policy usage
- Enhanced error handling and validation for policy documents
- Updated required IAM permissions documentation

## [1.0.0] - 2025-06-18

### Added
- Initial release of AWS IAM MCP Server
- User management tools:
  - `list_users` - List IAM users with filtering options
  - `get_user` - Get detailed user information including policies and access keys
  - `create_user` - Create new IAM users with optional permissions boundary
  - `delete_user` - Delete users with optional force cleanup
- Role management tools:
  - `list_roles` - List IAM roles with filtering options
  - `create_role` - Create new IAM roles with trust policies
- Policy management tools:
  - `list_policies` - List managed and customer policies
  - `attach_user_policy` - Attach managed policies to users
  - `detach_user_policy` - Detach managed policies from users
- Access key management tools:
  - `create_access_key` - Create new access keys for users
  - `delete_access_key` - Delete access keys
- Security analysis tools:
  - `simulate_principal_policy` - Test policy permissions before applying
- Comprehensive error handling and validation
- Security best practices integration
- Support for permissions boundaries
- AWS credential configuration support
- Detailed documentation and examples

### Security
- Implements AWS IAM security best practices
- Provides warnings for sensitive operations
- Supports principle of least privilege
- Includes policy simulation for safe testing
- Validates JSON trust policies
- Secure access key handling with warnings
