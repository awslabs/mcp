# Changelog

All notable changes to the AWS IAM MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
