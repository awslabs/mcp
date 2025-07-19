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

"""AWS FIS MCP Server implementation."""

import argparse
import boto3
import os
import sys
from awslabs.aws_fis_mcp_server import __version__
from awslabs.aws_fis_mcp_server.consts import (
    AWS_CONFIG_MAX_ATTEMPTS,
    AWS_CONFIG_RETRY_MODE,
    AWS_CONFIG_SIGNATURE_VERSION,
    DEFAULT_AWS_REGION,
    ENV_AWS_REGION,
    ENV_FASTMCP_LOG_LEVEL,
    SERVICE_CLOUDFORMATION,
    SERVICE_CONFIG,
    SERVICE_FIS,
    SERVICE_RESOURCE_EXPLORER,
    SERVICE_S3,
)
from awslabs.aws_fis_mcp_server.tools.experiment_template_tools import (
    create_experiment_template,
    update_experiment_template,
)
from awslabs.aws_fis_mcp_server.tools.fis_service_tools import (
    get_experiment_details,
    get_experiment_template,
    list_all_fis_experiments,
    list_experiment_templates,
    start_experiment,
)
from awslabs.aws_fis_mcp_server.tools.resource_discovery_tools import (
    create_view,
    discover_relationships,
    get_stack_resources,
    list_cfn_stacks,
    list_views,
    search_resources,
)
from botocore.config import Config
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Optional


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv(ENV_FASTMCP_LOG_LEVEL, 'WARNING'))

# Load environment variables
load_dotenv()

# Global variables for CLI arguments
allow_writes = False
aws_profile_override = None
aws_region_override = None

# Global variables for AWS clients
aws_fis: Any = None
s3: Any = None
resource_explorer: Any = None
cloudformation: Any = None
aws_config_client: Any = None

# Get region from environment or default to us-east-1
AWS_REGION = os.getenv(ENV_AWS_REGION, DEFAULT_AWS_REGION)


# Initialize AWS clients at module level with default configuration
def init_default_clients():
    """Initialize AWS clients with default configuration."""
    global aws_fis, s3, resource_explorer, cloudformation, aws_config_client

    try:
        # Use default region from environment
        region = os.getenv(ENV_AWS_REGION, DEFAULT_AWS_REGION)

        # Create AWS session
        session = boto3.Session(region_name=region)

        # Create AWS config
        aws_config = Config(
            region_name=region,
            signature_version=AWS_CONFIG_SIGNATURE_VERSION,
            retries={'max_attempts': AWS_CONFIG_MAX_ATTEMPTS, 'mode': AWS_CONFIG_RETRY_MODE},
            user_agent_extra=f'awslabs/mcp/aws-fis-mcp-server/{__version__}',
        )

        # Initialize AWS clients
        aws_fis = session.client(SERVICE_FIS, config=aws_config)
        s3 = session.client(SERVICE_S3, config=aws_config)
        resource_explorer = session.client(SERVICE_RESOURCE_EXPLORER, config=aws_config)
        cloudformation = session.client(SERVICE_CLOUDFORMATION, config=aws_config)
        aws_config_client = session.client(SERVICE_CONFIG, config=aws_config)

        logger.info(f'AWS clients initialized with default configuration in region {region}')

    except Exception as e:
        logger.error(f'Error initializing default AWS clients: {str(e)}')
        # Don't raise here, let the tools handle the error gracefully


# Initialize clients at module load time
init_default_clients()


def initialize_aws_clients(region: str, profile: Optional[str] = None):
    """Initialize AWS clients with the specified region and profile."""
    global aws_fis, s3, resource_explorer, cloudformation, aws_config_client

    try:
        # Create AWS session with optional profile
        session = (
            boto3.Session(profile_name=profile, region_name=region)
            if profile
            else boto3.Session(region_name=region)
        )

        # Create AWS config
        aws_config = Config(
            region_name=region,
            signature_version=AWS_CONFIG_SIGNATURE_VERSION,
            retries={'max_attempts': AWS_CONFIG_MAX_ATTEMPTS, 'mode': AWS_CONFIG_RETRY_MODE},
            user_agent_extra=f'awslabs/mcp/aws-fis-mcp-server/{__version__}',
        )

        # Initialize AWS clients
        aws_fis = session.client(SERVICE_FIS, config=aws_config)
        s3 = session.client(SERVICE_S3, config=aws_config)
        resource_explorer = session.client(SERVICE_RESOURCE_EXPLORER, config=aws_config)
        cloudformation = session.client(SERVICE_CLOUDFORMATION, config=aws_config)
        aws_config_client = session.client(SERVICE_CONFIG, config=aws_config)

        logger.info(f'AWS clients initialized successfully in region {region}')

    except Exception as e:
        logger.error(f'Error initializing AWS clients: {str(e)}')
        raise


mcp = FastMCP(
    'awslabs.aws-fis-mcp-server',
    instructions="""
# AWS FIS MCP Server

This MCP server provides tools for creating, managing, and executing AWS Fault Injection Simulator (FIS) experiments. It enables AI assistants to help users design resilient systems through controlled fault injection.

## Available Tools

### FIS Experiment Management
- **ListFISExperiments**: List all FIS experiments
- **GetFISExperiment**: Get details about a specific experiment
- **StartFISExperiment**: Start a FIS experiment from a template
- **ListFISExperimentTemplates**: List available experiment templates
- **GetFISExperimentTemplate**: Get details about a specific experiment template

### Experiment Template Management
- **CreateFISExperimentTemplate**: Create a new experiment template
- **UpdateFISExperimentTemplate**: Update an existing experiment template

### Resource Discovery
- **ListCloudFormationStacks**: List CloudFormation stacks
- **GetStackResources**: Get resources from a specific stack
- **ListResourceExplorerViews**: List Resource Explorer views
- **SearchResources**: Search for resources using Resource Explorer
- **CreateResourceExplorerView**: Create a new Resource Explorer view
- **DiscoverResourceRelationships**: Discover relationships between resources

## Service Availability
AWS FIS is available in select AWS regions. The server will use the configured region for all operations.
""",
    dependencies=[
        'boto3',
        'botocore',
        'pydantic',
        'loguru',
        'python-dotenv',
    ],
)

# Register FIS service tools
mcp.tool(name='ListFISExperiments')(list_all_fis_experiments)
mcp.tool(name='GetFISExperiment')(get_experiment_details)
mcp.tool(name='ListFISExperimentTemplates')(list_experiment_templates)
mcp.tool(name='GetFISExperimentTemplate')(get_experiment_template)
mcp.tool(name='StartFISExperiment')(start_experiment)

# Register experiment template tools
mcp.tool(name='CreateFISExperimentTemplate')(create_experiment_template)
mcp.tool(name='UpdateFISExperimentTemplate')(update_experiment_template)

# Register resource discovery tools
mcp.tool(name='ListCloudFormationStacks')(list_cfn_stacks)
mcp.tool(name='GetStackResources')(get_stack_resources)
mcp.tool(name='ListResourceExplorerViews')(list_views)
mcp.tool(name='SearchResources')(search_resources)
mcp.tool(name='CreateResourceExplorerView')(create_view)
mcp.tool(name='DiscoverResourceRelationships')(discover_relationships)


def main():
    """Run the MCP server with CLI argument support."""
    global allow_writes, aws_profile_override, aws_region_override

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AWS Fault Injection Simulator (FIS) MCP Server')
    parser.add_argument(
        '--aws-profile',
        help='AWS profile to use for credentials (default: uses default profile or environment)',
    )
    parser.add_argument(
        '--aws-region',
        help='AWS region to use (default: us-east-1 or AWS_REGION environment variable)',
    )
    parser.add_argument(
        '--allow-writes',
        action='store_true',
        help='Allow destructive operations such as starting FIS experiments and creating templates',
    )

    args = parser.parse_args()

    # Store arguments in global variables
    allow_writes = args.allow_writes
    aws_profile_override = args.aws_profile
    aws_region_override = args.aws_region

    # Determine AWS region (priority: CLI arg > env var > default)
    effective_region = aws_region_override or os.getenv(ENV_AWS_REGION, DEFAULT_AWS_REGION)

    logger.info(
        'AWS FIS MCP Server starting with AWS_PROFILE: %s, AWS_REGION: %s, ALLOW_WRITES: %s',
        aws_profile_override or 'default',
        effective_region,
        allow_writes,
    )

    # Re-initialize AWS clients if custom parameters are provided
    if aws_profile_override or aws_region_override:
        initialize_aws_clients(effective_region, aws_profile_override)

    # Start the MCP server
    logger.info('AWS FIS MCP server starting')
    mcp.run()


if __name__ == '__main__':
    main()
