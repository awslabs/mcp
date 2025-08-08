# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""AWS EC2 MCP Server - Main entry point."""

import logging
import os
import sys
from awslabs.ec2_mcp_server.modules import (
    amis,
    instances,
    key_pairs,
    security_groups,
    snapshots,
    volumes,
    vpc_management,
)
from awslabs.ec2_mcp_server.utils.config import get_config
from awslabs.ec2_mcp_server.utils.security import (
    PERMISSION_NONE,
    PERMISSION_WRITE,
    secure_tool,
)
from mcp.server.fastmcp import FastMCP


# Configure logging
log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'INFO')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = os.environ.get('FASTMCP_LOG_FILE')

# Set up basic configuration
logging.basicConfig(
    level=log_level,
    format=log_format,
)

# Add file handler if log file path is specified
if log_file:
    try:
        # Create directory for log file if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
        logging.info(f'Logging to file: {log_file}')
    except Exception as e:
        logging.error(f'Failed to set up log file {log_file}: {e}')

logger = logging.getLogger('ec2-mcp-server')

# Load configuration
config = get_config()

# Create the MCP server
mcp = FastMCP(
    name='AWS EC2 MCP Server',
    description=(
        'A server for managing AWS EC2 instances, AMIs, security groups, volumes, and related infrastructure'
    ),
    version='0.1.0',
    instructions="""Use this server to manage AWS EC2 infrastructure. This comprehensive MCP server provides tools for complete EC2 lifecycle management.

    ## AVAILABLE TOOLS:

    ###  EC2 INSTANCES (9 tools):
    - `list_instances` - List EC2 instances with filtering options
    - `get_instance_details` - Get detailed information about a specific instance
    - `launch_instance` - Launch new EC2 instances with full configuration
    - `terminate_instance` - Terminate EC2 instances permanently
    - `start_instance` - Start stopped instances
    - `stop_instance` - Stop running instances (with optional force flag)
    - `reboot_instance` - Reboot running instances
    - `get_subnet_info` - Get subnet information for networking
    - `list_subnets` - List available subnets for instance placement

    ###  SECURITY GROUPS (5 tools):
    - `list_security_groups` - List security groups with filtering
    - `get_security_group_details` - Get detailed security group configuration
    - `create_security_group` - Create new security groups with descriptions
    - `delete_security_group` - Delete security groups
    - `modify_security_group_rules` - Add/remove inbound and outbound rules

    ### KEY PAIRS (3 tools) -  SECURE STORAGE MANDATORY:
    - `list_key_pairs` - List available EC2 key pairs
    - `create_key_pair` - **SECURE STORAGE IS MANDATORY FOR SECURITY**
    * Private keys are AUTOMATICALLY stored securely (no option to retrieve directly)
    * Must specify storage_method: Choose "secrets_manager" OR "s3_encrypted" OR "parameter_store" (NO DEFAULTS)
    * Supports RSA and ED25519 key types
    * Automatic rollback if storage fails
    - `delete_key_pair` - Delete key pairs and optionally their stored private keys

    ###  EBS VOLUMES (5 tools):
    - `list_volumes` - List EBS volumes with status and attachment info
    - `create_volume` - Create new EBS volumes with specified size and type
    - `delete_volume` - Delete EBS volumes (must be unattached)
    - `attach_volume` - Attach volumes to EC2 instances
    - `detach_volume` - Detach volumes from instances

    ### EBS SNAPSHOTS (2 tools):
    - `list_snapshots` - List EBS snapshots with filtering
    - `create_snapshot` - Create snapshots from EBS volumes

    ### AMIs - AMAZON MACHINE IMAGES (4 tools):
    - `list_amis` - List AMIs with ownership and filtering options
    - `get_popular_amis` - Get popular public AMIs (Amazon Linux, Ubuntu, Windows, RHEL)
    - `create_image` - Create custom AMIs from running instances
    - `deregister_image` - Deregister/delete AMIs

    ### VPC & NETWORKING (5 tools):
    - `list_vpcs` - List Virtual Private Clouds
    - `get_default_vpc` - Get the default VPC for the region
    - `find_suitable_subnet` - Find appropriate subnets for instance placement
    - `delete_vpc` - Delete VPCs (advanced operation)
    - `list_subnets` - List subnets with VPC filtering

    ## WORKFLOW EXAMPLES:

    ### Launch a Web Server:
    1. `get_popular_amis` - Find latest Amazon Linux AMI
    2. `create_key_pair` - YOU MUST CHOOSE: storage_method="secrets_manager" OR "s3_encrypted" OR "parameter_store"
    3. `create_security_group` for HTTP/SSH access
    4. `launch_instance` with the AMI, key pair, and security group

    ### Create Custom AMI:
    1. `list_instances` - Find your configured instance
    2. `stop_instance` - Stop for consistent snapshot
    3. `create_image` - Create AMI from instance
    4. `start_instance` - Restart original instance

    ### Volume Management:
    1. `create_volume` - Create additional storage
    2. `attach_volume` - Attach to running instance
    3. `create_snapshot` - Backup volume datas

    ## IMPORTANT CONFIGURATION:

    ### Required Environment Variables:
    - **AWS Credentials**: Must be configured via AWS CLI, environment variables, or IAM roles
    - **ALLOW_WRITE=true**: Required to enable create/modify/delete operations
    - **ALLOW_SENSITIVE_DATA=true**: Required for detailed resource information

    ### Key Pair Storage Requirements:
    - **SECURE STORAGE IS MANDATORY** for create_key_pair (enhanced security)
    - Private keys are NEVER exposed through MCP interface
    - Choose from: "secrets_manager", "s3_encrypted" (KMS), "parameter_store" (required parameter)
    - Ensure you have appropriate AWS permissions for your chosen storage method
    - Access stored keys directly through AWS Console/CLI only


    ### Regional Considerations:
    - All operations are region-specific
    - Configure AWS_REGION or use region parameter where available
    - Popular AMIs vary by region - use get_popular_amis to find region-appropriate images""",
)

# Apply security wrappers to write operations
# Instance operations
instances.launch_instance = secure_tool(config, PERMISSION_WRITE, 'launch_instance')(
    instances.launch_instance
)
instances.terminate_instance = secure_tool(config, PERMISSION_WRITE, 'terminate_instance')(
    instances.terminate_instance
)
instances.start_instance = secure_tool(config, PERMISSION_WRITE, 'start_instance')(
    instances.start_instance
)
instances.stop_instance = secure_tool(config, PERMISSION_WRITE, 'stop_instance')(
    instances.stop_instance
)
instances.reboot_instance = secure_tool(config, PERMISSION_WRITE, 'reboot_instance')(
    instances.reboot_instance
)

# Security group operations
security_groups.create_security_group = secure_tool(
    config, PERMISSION_WRITE, 'create_security_group'
)(security_groups.create_security_group)
security_groups.delete_security_group = secure_tool(
    config, PERMISSION_WRITE, 'delete_security_group'
)(security_groups.delete_security_group)
security_groups.modify_security_group_rules = secure_tool(
    config, PERMISSION_WRITE, 'modify_security_group_rules'
)(security_groups.modify_security_group_rules)

# Key pair operations
key_pairs.create_key_pair = secure_tool(config, PERMISSION_WRITE, 'create_key_pair')(
    key_pairs.create_key_pair
)
key_pairs.delete_key_pair = secure_tool(config, PERMISSION_WRITE, 'delete_key_pair')(
    key_pairs.delete_key_pair
)

# Volume operations
volumes.create_volume = secure_tool(config, PERMISSION_WRITE, 'create_volume')(
    volumes.create_volume
)
volumes.delete_volume = secure_tool(config, PERMISSION_WRITE, 'delete_volume')(
    volumes.delete_volume
)
volumes.attach_volume = secure_tool(config, PERMISSION_WRITE, 'attach_volume')(
    volumes.attach_volume
)
volumes.detach_volume = secure_tool(config, PERMISSION_WRITE, 'detach_volume')(
    volumes.detach_volume
)

# AMI operations
amis.create_image = secure_tool(config, PERMISSION_WRITE, 'create_image')(amis.create_image)
amis.deregister_image = secure_tool(config, PERMISSION_WRITE, 'deregister_image')(
    amis.deregister_image
)

# VPC operations
vpc_management.get_default_vpc = secure_tool(config, PERMISSION_NONE, 'get_default_vpc')(
    vpc_management.get_default_vpc
)
vpc_management.find_suitable_subnet = secure_tool(config, PERMISSION_NONE, 'find_suitable_subnet')(
    vpc_management.find_suitable_subnet
)
vpc_management.delete_vpc = secure_tool(config, PERMISSION_WRITE, 'delete_vpc')(
    vpc_management.delete_vpc
)

# Register all modules
instances.register_module(mcp)
security_groups.register_module(mcp)
key_pairs.register_module(mcp)
volumes.register_module(mcp)
snapshots.register_module(mcp)
amis.register_module(mcp)
vpc_management.register_module(mcp)


def main() -> None:
    """Main entry point for the EC2 MCP Server."""
    try:
        # Start the server
        logger.info('EC2 MCP Server started')
        logger.info(f'Write operations enabled: {config.get("allow-write", False)}')
        logger.info(f'Sensitive data access enabled: {config.get("allow-sensitive-data", False)}')
        mcp.run()
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Error starting server: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
