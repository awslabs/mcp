# Changelog

All notable changes to the AWS EC2 MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2025-01-27

### Added
- **SSH Key Pair Management**: Secure key storage and management
  - `list_key_pairs` - List available SSH key pairs
  - `create_key_pair` - Generate new key pairs with secure storage options
  - `delete_key_pair` - Remove key pairs with optional private key cleanup
  - Multiple storage backends: AWS Secrets Manager, S3 with KMS encryption, Parameter Store
- **AMI Management**: Extended capabilities
  - `get_popular_amis` - Get curated list of popular AMIs (Amazon Linux, Ubuntu, Windows, RHEL)
  - `create_ami` - Create custom AMIs from instances
  - `deregister_ami` - Remove unused AMIs

### Enhanced
- **EC2 Instance Management**: Added advanced lifecycle operations
  - `start_instance` - Start stopped instances
  - `stop_instance` - Stop running instances with optional force parameter
  - `reboot_instance` - Reboot instances for maintenance operations
- **VPC and Networking**: Enhanced networking capabilities
  - `find_suitable_subnet` - Intelligent subnet selection for instance placement
  - `get_subnet_info` - Get detailed subnet configuration and capacity
- **Security Groups**: Extended rule management
  - `modify_security_group_rules` - Add/remove inbound and outbound rules dynamically

### Security
- **Data Protection**: Implemented comprehensive data sanitization to prevent sensitive information exposure
- **Access Controls**: Added permission-based security controls for write operations
- **Credential Security**: Enhanced AWS credentials handling with multiple authentication methods
- **Input Validation**: Rigorous validation for all AWS resource identifiers and parameters
- **Audit Logging**: Enhanced logging for security monitoring and compliance
- **Error Handling**: Secure error responses that prevent information leakage

### Fixed
- Resolved potential security vulnerabilities through code review and cleanup
- Improved logging consistency across all modules and components
- Enhanced error handling in key storage operations with proper rollback mechanisms
- Fixed edge cases in subnet selection and VPC management

## [0.1.2] - 2025-01-15

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
- **VPC and Networking**: Network infrastructure management
  - `list_vpcs` - List Virtual Private Clouds with configuration details
  - `get_default_vpc` - Retrieve default VPC information
  - `list_subnets` - List available subnets with availability zone information

### Enhanced
- Improved subnet selection algorithms
- Enhanced error handling for edge cases
- Better AWS credential support via environment variables, profiles, and IAM roles

## [0.1.1] - 2025-01-10

### Added
- **Security Group Management**: Network security configuration tools
  - `list_security_groups` - List security groups with filtering capabilities
  - `get_security_group_details` - Get detailed security group rules and associations
  - `create_security_group` - Create new security groups with descriptions
  - `delete_security_group` - Remove unused security groups
- **AMI Management**: Basic AMI operations
  - `list_amis` - List available AMIs with owner and architecture filters

### Enhanced
- Enhanced Pydantic models with comprehensive validation
- Improved error handling with async/await patterns
- Updated tool naming to use kebab-case format

## [0.1.0] - 2024-12-20

### Added
- **Initial release of AWS EC2 MCP Server**
- **EC2 Instance Management**: Core instance operations
  - `list_instances` - List EC2 instances with basic filtering options
  - `get_instance_details` - Retrieve detailed instance information and metadata
  - `launch_instance` - Launch new instances with basic configuration options
  - `terminate_instance` - Safely terminate instances with confirmation
- **Core Infrastructure**:
  - Core AWS client integration with credential management
  - Initial Pydantic models for EC2 resources
  - Basic error handling and logging framework
  - Docker support with basic configuration
  - Comprehensive input validation using Pydantic models
  - MCP protocol compliance and tool registration