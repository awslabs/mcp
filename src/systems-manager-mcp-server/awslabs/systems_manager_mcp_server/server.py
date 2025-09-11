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

"""AWS Systems Manager MCP Server implementation."""

import argparse
import logging
from awslabs.systems_manager_mcp_server.context import Context

# Import and register tools
from awslabs.systems_manager_mcp_server.tools.automation import (
    register_tools as register_automation_tools,
)
from awslabs.systems_manager_mcp_server.tools.commands import (
    register_tools as register_command_tools,
)
from awslabs.systems_manager_mcp_server.tools.documents import (
    register_tools as register_document_tools,
)
from mcp.server.fastmcp import FastMCP


# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create main MCP server with comprehensive instructions
mcp = FastMCP(
    'awslabs.systems-manager-mcp-server',
    instructions="""
    # AWS Systems Manager MCP Server

    This MCP server provides comprehensive AWS Systems Manager (SSM) capabilities for managing infrastructure and applications at scale, with a focus on CloudOps automation workflows.

    ## Core Features:

    ### Document Management
    - Create, update, and delete SSM documents
    - List and search documents with advanced filtering
    - Manage document permissions and sharing
    - Support for all document types (Command, Automation, Policy, etc.)

    ### Automation Execution
    - Start and stop automation executions for CloudOps workflows
    - Monitor automation execution status and progress
    - Send signals to interactive automations
    - List and filter automation executions
    - Support for rate-controlled and parallel executions

    ### Command Execution
    - Send commands to EC2 instances and on-premises servers
    - Monitor command execution status and results
    - Cancel running commands
    - List and filter command executions
    - Support for targeted and bulk operations

    ### Parameter Store Management
    - Store and retrieve configuration parameters
    - Support for String, StringList, and SecureString types
    - Bulk parameter operations
    - Secure handling of encrypted parameters

    ### Security & Compliance
    - Role-based access control with admin and non-admin tools
    - Read-only mode for safe operations
    - Comprehensive error handling and validation
    - Security best practices enforcement

    ### Integration Capabilities
    - Context-aware AWS configuration
    - Support for multiple AWS profiles and regions
    - Comprehensive logging and monitoring
    - CLI argument support for flexible deployment

    ## Available Tools:

    ### Administrative Tools (Full Access)
    - `list_documents`: List all documents with comprehensive filtering
    - `get_document`: Retrieve document content and metadata
    - `create_document`: Create new SSM documents
    - `update_document`: Update existing documents
    - `delete_document`: Remove documents
    - `describe_document_permission`: View document permissions
    - `modify_document_permission`: Manage document sharing

    ### User Tools (Controlled Access)
    - `list_admin_documents`: List documents owned by current user
    - `list_approved_documents`: List documents tagged as approved for use
    - `document_security_best_practices`: Security guidelines and best practices

    ## Configuration:

    ### Environment Variables
    - `AWS_REGION`: AWS region for operations
    - `AWS_PROFILE`: AWS profile to use
    - `SSM_MCP_READONLY`: Enable read-only mode (true/false)
    - `FASTMCP_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

    ### CLI Arguments
    - `--readonly`: Enable read-only mode
    - `--region`: Set AWS region
    - `--profile`: Set AWS profile
    - `--log-level`: Set logging level
    - `--allow-write`: Allow write operations (overrides readonly)
    - `--allow-sensitive-data-access`: Allow access to sensitive operations

    ## Use Cases:
    - Infrastructure automation and management
    - Configuration management at scale
    - Compliance and security enforcement
    - Application deployment automation
    - Security compliance enforcement
    - Infrastructure provisioning
    - Backup and recovery operations
    """,
    dependencies=['pydantic', 'boto3', 'botocore', 'mcp'],
)


# Register all tools with the main MCP instance
register_document_tools(mcp)
register_automation_tools(mcp)
register_command_tools(mcp)


def main():
    """Main entry point for the AWS Systems Manager MCP Server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='AWS Systems Manager MCP Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in read-only mode
  %(prog)s --readonly

  # Run with specific AWS profile and region
  %(prog)s --profile myprofile --region us-west-2

  # Run with write access and debug logging
  %(prog)s --allow-write --log-level DEBUG

  # Run with all permissions
  %(prog)s --allow-write --allow-sensitive-data-access

Environment Variables:
  AWS_REGION                 AWS region for operations
  AWS_PROFILE                AWS profile to use
  SSM_MCP_READONLY          Enable read-only mode (true/false)
  FASTMCP_LOG_LEVEL         Logging level (DEBUG, INFO, WARNING, ERROR)
        """,
    )

    parser.add_argument(
        '--readonly', action='store_true', help='Enable read-only mode (no write operations)'
    )

    parser.add_argument('--region', type=str, help='AWS region to use')

    parser.add_argument('--profile', type=str, help='AWS profile to use')

    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set logging level'
    )

    parser.add_argument(
        '--allow-write',
        action='store_true',
        help='Allow write operations (overrides readonly mode)',
    )

    parser.add_argument(
        '--allow-sensitive-data-access',
        action='store_true',
        help='Allow access to sensitive operations',
    )

    args = parser.parse_args()

    # Configure context based on CLI arguments and environment
    context = Context()

    # Set read-only mode
    if args.readonly:
        context.set_readonly(True)
    elif args.allow_write:
        context.set_readonly(False)

    # Set AWS configuration
    if args.region:
        context.set_aws_region(args.region)
    if args.profile:
        context.set_aws_profile(args.profile)

    # Set logging level
    if args.log_level:
        context.set_log_level(args.log_level)
        logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Log configuration
    logger.info('Starting AWS Systems Manager MCP Server')
    logger.info(f'Read-only mode: {context.is_readonly()}')
    logger.info(f'AWS Region: {context._aws_region}')
    logger.info(f'AWS Profile: {context._aws_profile}')
    logger.info(f'Log Level: {context._log_level}')

    # Run the server
    mcp.run()


if __name__ == '__main__':
    main()
