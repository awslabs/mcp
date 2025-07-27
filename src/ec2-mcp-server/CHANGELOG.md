# Changelog

All notable changes to the AWS EC2 MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2025-07-28

### Added
- **EBS Volume Operations**: Complete storage management capabilities
  - `list_volumes` - List EBS volumes with status and attachment information
  - `create_volume` - Create new EBS volumes with encryption options
  - `delete_volume` - Remove unused volumes with safety checks
  - `attach_volume` - Attach volumes to instances with device mapping
  - `detach_volume` - Safely detach volumes from instances
- **Snapshot Management**: Backup and recovery tools
  - `list_snapshots` - List available snapshots with filtering
  - `create_snapshot` - Create point-in-time snapshots of volumes
- **AMI Management**: Extended capabilities
  - `get_popular_amis` - Get curated list of popular AMIs (Amazon Linux, Ubuntu, Windows, RHEL)
  - `create_ami` - Create custom AMIs from instances
  - `deregister_ami` - Remove unused AMIs
- **SSH Key Pair Management**: Secure key storage and management
  - `list_key_pairs`, `create_key_pair`, `delete_key_pair`
  - Supports storage in AWS Secrets Manager, S3 with KMS encryption, and Parameter Store

### Enhanced
- Improved subnet selection algorithms
- Enhanced error handling for edge cases
- Better AWS credential support via environment variables, profiles, and IAM roles
- **Audit Logging**: Enhanced logging for security monitoring and compliance
- **Credential Security**: Improved handling with multiple authentication methods

### Security
- Implemented data sanitization to prevent sensitive information exposure
- Added permission-based access controls for write operations
- Rigorous input validation for all AWS identifiers and parameters
- Secure error responses to avoid information leakage
- Added rollback mechanisms in key storage error scenarios

## [0.1.1] - 2025-07-26

### Added
- **Security Group Management**: Network security configuration tools
  - `list_security_groups`, `get_security_group_details`
  - `create_security_group`, `delete_security_group`
- **AMI Management**: Basic AMI operations
  - `list_amis` - List AMIs with owner and architecture filters
- **VPC and Networking**: Core VPC functionalities
  - `list_vpcs`, `get_default_vpc`, `list_subnets`
  - `find_suitable_subnet` - Intelligent subnet selection for instance placement
  - `get_subnet_info` - View subnet configuration and capacity

### Enhanced
- Pydantic models updated with comprehensive validation
- Error handling improved using async/await patterns
- Logging consistency improved across all modules
- Tool naming convention updated to kebab-case
- **Security Groups**: Added dynamic rule modification via `modify_security_group_rules`

## [0.1.0] - 2025-07-26

### Added
- **Initial release of AWS EC2 MCP Server**
- **EC2 Instance Management**: Core instance operations
  - `list_instances`, `get_instance_details`
  - `launch_instance`, `terminate_instance`
- **Lifecycle Management Enhancements**:
  - `start_instance`, `stop_instance` (with force), `reboot_instance`
- **Core Infrastructure**:
  - Integrated AWS clients with credential management
  - Initial Pydantic models for EC2 resources
  - Basic error handling and logging framework
  - Docker support with configuration
  - Comprehensive input validation using Pydantic
  - MCP protocol compliance and tool registration
