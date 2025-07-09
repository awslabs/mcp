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
import time
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
from botocore.config import Config
from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


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


# Initialize MCP server
mcp = FastMCP(
    name='awslabs.aws-fis-mcp-server',
    instructions="""An MCP Server that enables LLMs to plan, create, and execute AWS Fault Injection Simulator (FIS) experiments.

    This server provides tools for:
    - Listing and managing FIS experiments
    - Creating and executing experiment templates
    - Exploring AWS resources for fault injection
    - Working with CloudFormation stacks

    Use these tools to help users design resilient systems through controlled fault injection.

    When invoking methods in the classes do not use the self argument as it is not meant to take arguments but rather refers to the class itself.
    """,
)


"""AWS FIS Experiment Management Tools.

This section provides MCP tools for interacting with AWS Fault Injection Simulator (FIS)
experiments and templates. These tools enable listing, retrieving, and executing FIS experiments
to help design and conduct controlled chaos engineering tests.

The tools handle AWS API interactions, error handling, and provide structured responses
suitable for consumption by LLMs. They implement polling mechanisms with exponential backoff
for long-running operations and proper pagination handling for list operations.
"""


@mcp.tool(name='list_fis_experiments')
async def list_all_fis_experiments(ctx: Context) -> Dict[str, Dict[str, Any]]:
    """Retrieves a list of Experiments available in the AWS FIS service.

    This tool fetches all FIS experiments in the current AWS account and region,
    organizing them by name for easy reference. It handles pagination automatically.

    Returns:
    Dict containing experiment details organized by name
    """
    try:
        response = aws_fis.list_experiments()
        experiments = response.get('experiments', [])
        formatted_results = {}

        for item in experiments:
            # Handle case where Name tag might not exist
            experiment_name = item.get('tags', {}).get('Name', item.get('id', 'Unknown'))
            formatted_results[experiment_name] = {
                'id': item.get('id'),
                'arn': str(item.get('arn')),
                'experimentTemplateId': str(item.get('experimentTemplateId')),
                'state': item.get('state'),
                'experimentOptions': item.get('experimentOptions'),
            }

        # Handle pagination if needed
        while 'nextToken' in response:
            response = aws_fis.list_experiments(nextToken=response['nextToken'])
            for item in response.get('experiments', []):
                experiment_name = item.get('tags', {}).get('Name', item.get('id', 'Unknown'))
                formatted_results[experiment_name] = {
                    'id': item.get('id'),
                    'arn': str(item.get('arn')),
                    'experimentTemplateId': str(item.get('experimentTemplateId')),
                    'state': item.get('state'),
                    'experimentOptions': item.get('experimentOptions'),
                }

        return formatted_results
    except Exception as e:
        await ctx.error(f'Error listing FIS experiments: {str(e)}')
        raise


@mcp.tool(name='get_experiment')
async def get_experiment_details(
    ctx: Context,
    id: str = Field(..., description='The experiment ID to retrieve details for'),
) -> Dict[str, Any]:
    """Get detailed information about a specific experiment.

    This tool retrieves comprehensive information about a single FIS experiment
    identified by its ID.

    Args:
        ctx: The MCP context for logging and communication
        id: The experiment ID

    Returns:
        Dict containing experiment details
    """
    try:
        response = aws_fis.get_experiment(id=id)
        return response.get('experiment', {})
    except Exception as e:
        await ctx.error(f'Error getting experiment details: {str(e)}')
        raise


@mcp.tool(name='list_experiment_templates')
async def list_experiment_templates(ctx: Context) -> List[Dict[str, Any]]:
    """List all experiment templates.

    This tool retrieves all FIS experiment templates in the current AWS account and region.
    It handles pagination automatically to ensure all templates are returned.

    Returns:
        List of experiment templates with their details
    """
    try:
        all_templates = []
        response = aws_fis.list_experiment_templates()
        all_templates.extend(response.get('experimentTemplates', []))

        # Handle pagination
        while 'nextToken' in response:
            response = aws_fis.list_experiment_templates(nextToken=response['nextToken'])
            all_templates.extend(response.get('experimentTemplates', []))

        return all_templates
    except Exception as e:
        await ctx.error(f'Error listing experiment templates: {str(e)}')
        raise


@mcp.tool(name='get_experiment_template')
async def get_experiment_template(
    ctx: Context,
    id: str = Field(..., description='The experiment template ID to retrieve'),
) -> Dict[str, Any]:
    """Get detailed information about a specific experiment template.

    This tool retrieves comprehensive information about a single FIS experiment template
    identified by its ID.

    Args:
        ctx: The MCP context for logging and communication
        id: The experiment template ID

    Returns:
        Dict containing experiment template details
    """
    try:
        response = aws_fis.get_experiment_template(id=id)
        return response
    except Exception as e:
        await ctx.error(f'Error getting experiment template: {str(e)}')
        raise


@mcp.tool('start_experiment')
async def start_experiment(
    ctx: Context,
    id: str = Field(..., description='The experiment template ID to execute'),
    name: str = Field(
        ..., description='Required name for the experiment (will be added as Name tag)'
    ),
    tags: Optional[Dict[str, str]] = Field(
        None, description='Optional additional tags to apply to the experiment'
    ),
    action: Optional[str] = Field(
        'run-all',
        description='The actions mode for experiment execution (run-all, skip-all, or stop-on-failure)',
    ),
) -> Dict[str, Any]:
    """Starts an AWS FIS experiment and returns immediately after starting.

    Args:
        ctx: The MCP context for logging and communication
        id: The experiment template ID
        name: Required name for the experiment
        tags: Optional additional tags to apply to the experiment
        action: The actions mode (default: 'run-all')

    Returns:
        Dict containing experiment start response

    Raises:
        Exception: For AWS API errors or when writes are disabled
    """
    global allow_writes

    # Check if writes are allowed
    if not allow_writes:
        error_msg = 'Write operations are disabled. Use --allow-writes flag to enable destructive operations like starting FIS experiments.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

    try:
        # Start with Name tag as required
        experiment_tags = {'Name': name}

        # Add any additional tags if provided
        if tags:
            experiment_tags.update(tags)

        response = aws_fis.start_experiment(
            experimentTemplateId=id,
            experimentOptions={'actionsMode': action},
            tags=experiment_tags,
        )

        experiment_id = response['experiment']['id']
        await ctx.info(f'Started experiment "{name}" with ID: {experiment_id}')

        return {
            'experiment_id': experiment_id,
            'name': name,
            'status': 'started',
            'template_id': id,
            'tags': experiment_tags,
            'message': f'Experiment "{name}" started successfully. Use get_experiment tool to check status.',
        }

    except Exception as e:
        await ctx.error(f'Error starting experiment: {str(e)}')
        raise


"""AWS Resource Discovery Tools.

This section provides MCP tools for discovering AWS resources using CloudFormation and
Resource Explorer services. These tools enable the identification of potential targets
for fault injection experiments across the AWS account.

The tools offer methods to list resources from different sources, create and manage
Resource Explorer views, and filter resources based on specific criteria. They handle
pagination for large result sets and provide structured responses suitable for
consumption by LLMs.

This consolidated approach allows for more flexible resource discovery, making it easier
to design comprehensive resilience testing scenarios regardless of how resources were
provisioned.
"""


@mcp.tool(name='list_cfn_stacks')
async def list_cfn_stacks(ctx: Context) -> Dict[str, Any]:
    """Retrieve all AWS CloudFormation Stacks.

    This tool lists all CloudFormation stacks in the current AWS account and region,
    providing information that can help identify potential targets for fault injection.

    Returns:
        Dict containing CloudFormation stack information
    """
    try:
        all_stacks = []
        cfn = cloudformation
        response = cfn.list_stacks()
        all_stacks.extend(response.get('StackSummaries', []))

        # Handle pagination
        while 'NextToken' in response:
            response = cfn.list_stacks(NextToken=response['NextToken'])
            all_stacks.extend(response.get('StackSummaries', []))

        return {'stacks': all_stacks}
    except Exception as e:
        await ctx.error(f'Error listing CloudFormation stacks: {str(e)}')
        raise


@mcp.tool(name='get_stack_resources')
async def get_stack_resources(
    ctx: Context,
    stack_name: str = Field(
        ..., description='Name of the CloudFormation stack to retrieve resources from'
    ),
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves the resources that have been created by an individual stack.

    This tool lists all resources within a specific CloudFormation stack,
    which can be useful for identifying potential targets for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        stack_name: Name of the CloudFormation stack

    Returns:
        Dict containing stack resources
    """
    try:
        all_resources = []
        cfn = cloudformation
        response = cfn.list_stack_resources(StackName=stack_name)
        all_resources.extend(response.get('StackResourceSummaries', []))

        # Handle pagination
        while 'NextToken' in response:
            response = cfn.list_stack_resources(
                StackName=stack_name, NextToken=response['NextToken']
            )
            all_resources.extend(response.get('StackResourceSummaries', []))

        return {'resources': all_resources}
    except Exception as e:
        await ctx.error(f'Error getting stack resources: {str(e)}')
        raise


@mcp.tool(name='list_resource_explorer_views')
async def list_views(ctx: Context) -> List[Dict[str, Any]]:
    """List Resource Explorer views.

    This tool retrieves all Resource Explorer views in the current AWS account and region,
    which can be used to find and filter resources for fault injection experiments.

    Returns:
        List of Resource Explorer views
    """
    try:
        all_views = []
        response = resource_explorer.list_views()
        all_views.extend(response.get('Views', []))

        # Handle pagination
        while 'NextToken' in response:
            response = resource_explorer.list_views(NextToken=response['NextToken'])
            all_views.extend(response.get('Views', []))

        return all_views
    except Exception as e:
        await ctx.error(f'Error listing Resource Explorer views: {str(e)}')
        raise


@mcp.tool(name='search_resources')
async def search_resources(
    ctx: Context,
    query_string: str = Field(..., description='The query string to search for resources'),
    view_arn: str = Field(..., description='The ARN of the Resource Explorer view to use'),
    max_results: int = Field(100, description='Maximum number of results to return'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
) -> Dict[str, Any]:
    """Search for AWS resources using Resource Explorer.

    This tool searches for AWS resources using Resource Explorer based on a query string
    and view ARN. It can be used to find specific resources for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        query_string: The query string to search for resources
        view_arn: The ARN of the Resource Explorer view to use
        max_results: Maximum number of results to return (default: 100)
        next_token: Token for pagination (optional)

    Returns:
        Dict containing search results and pagination information
    """
    try:
        # Build search parameters
        search_params = {
            'QueryString': query_string,
            'ViewArn': view_arn,
            'MaxResults': max_results,
        }

        # Add next token if provided
        if next_token:
            search_params['NextToken'] = next_token

        # Execute search
        response = resource_explorer.search(**search_params)

        # Format results
        result = {
            'resources': response.get('Resources', []),
            'query_string': query_string,
            'view_arn': view_arn,
            'count': len(response.get('Resources', [])),
        }

        # Only include next_token if it exists in the response
        if 'NextToken' in response:
            result['next_token'] = response['NextToken']

        await ctx.info(f'Found {result["count"]} resources matching query: {query_string}')
        return result
    except Exception as e:
        await ctx.error(f'Error searching resources: {str(e)}')
        raise


@mcp.tool(name='create_resource_explorer_view')
async def create_view(
    ctx: Context,
    query: str = Field(..., description='Filter string for the view'),
    view_name: str = Field(..., description='Name of the view'),
    name: str = Field(..., description='Required name for the view (will be added as Name tag)'),
    tags: Optional[Dict[str, str]] = Field(
        None, description='Optional additional tags to apply to the view'
    ),
    scope: Optional[str] = Field(None, description='Scope of the view'),
    client_token: Optional[str] = Field(None, description='Client token for idempotency'),
) -> Dict[str, Any]:
    """Create a Resource Explorer view.

    This tool creates a new Resource Explorer view that can be used to find
    and filter resources for fault injection experiments.

    Args:
        ctx: The MCP context for logging and communication
        query: Filter string for the view
        view_name: Name of the view
        name: Required name for the view (will be added as Name tag)
        tags: Optional additional tags to apply to the view
        scope: Scope of the view
        client_token: Client token for idempotency

    Returns:
        Dict containing the created view details

    Raises:
        Exception: For AWS API errors or when writes are disabled
    """
    global allow_writes

    # Check if writes are allowed
    if not allow_writes:
        error_msg = 'Write operations are disabled. Use --allow-writes flag to enable Resource Explorer view creation.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

    try:
        # Start with Name tag as required
        view_tags = {'Name': name}

        # Add any additional tags if provided
        if tags:
            view_tags.update(tags)

        # Generate client token if not provided
        if not client_token:
            client_token = f'create-view-{int(time.time())}'

        response = resource_explorer.create_view(
            ClientToken=client_token,
            Filters={'FilterString': query},
            Scope=scope,
            Tags=view_tags,
            ViewName=view_name,
        )

        await ctx.info(f'Created Resource Explorer view "{name}" with name: {view_name}')
        return response
    except Exception as e:
        await ctx.error(f'Error creating Resource Explorer view: {str(e)}')
        raise


@mcp.tool(name='discover_resource_relationships')
async def discover_relationships(
    ctx: Context,
    resource_type: str = Field(
        ...,
        description='AWS resource type (e.g., AWS::EC2::Instance, AWS::ElasticLoadBalancingV2::LoadBalancer)',
    ),
    resource_id: str = Field(..., description='AWS resource ID to discover relationships for'),
    limit: Optional[int] = Field(
        10, description='Maximum number of configuration items to retrieve'
    ),
    chronological_order: Optional[str] = Field(
        'Reverse', description='Order of configuration items (Reverse or Forward)'
    ),
) -> Dict[str, Any]:
    """Discover relationships for a specific AWS resource using AWS Config.

    This tool retrieves the configuration history for a specific AWS resource
    and returns its relationships with other resources. This is useful for
    understanding resource dependencies, such as finding which subnet an ALB
    is placed in or which security groups are attached to an instance.

    Args:
        ctx: The MCP context for logging and communication
        resource_type: AWS resource type (e.g., AWS::EC2::Instance)
        resource_id: AWS resource ID to discover relationships for
        limit: Maximum number of configuration items to retrieve
        chronological_order: Order of configuration items (Reverse or Forward)

    Returns:
        Dict containing resource relationships and configuration details
    """
    try:
        # Get resource configuration history
        params = {
            'resourceType': resource_type,
            'resourceId': resource_id,
            'chronologicalOrder': chronological_order,
        }

        if limit:
            params['limit'] = limit

        response = aws_config_client.get_resource_config_history(**params)

        result = {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'relationships': [],
            'configuration_items': [],
        }

        # Process configuration items
        config_items = response.get('configurationItems', [])

        if not config_items:
            result['message'] = 'No configuration items found for the specified resource'
            return result

        # Extract relationships from the most recent configuration item
        latest_config = config_items[0] if config_items else {}
        relationships = latest_config.get('relationships', [])

        result['relationships'] = relationships

        # Include configuration item details (without sensitive data)
        for item in config_items:
            config_summary = {
                'configuration_item_capture_time': str(
                    item.get('configurationItemCaptureTime', '')
                ),
                'configuration_state_id': item.get('configurationStateId'),
                'aws_region': item.get('awsRegion'),
                'availability_zone': item.get('availabilityZone'),
                'resource_creation_time': str(item.get('resourceCreationTime', '')),
                'tags': item.get('tags', {}),
                'relationships_count': len(item.get('relationships', [])),
            }
            result['configuration_items'].append(config_summary)

        # Add summary statistics
        result['summary'] = {
            'total_relationships': len(relationships),
            'total_configuration_items': len(config_items),
            'relationship_types': list({rel.get('relationshipName', '') for rel in relationships}),
        }

        await ctx.info(
            f'Found {len(relationships)} relationships for {resource_type} {resource_id}'
        )
        return result

    except Exception as e:
        await ctx.error(f'Error discovering resource relationships: {str(e)}')
        raise


"""AWS FIS Experiment Template Management Tools.

This section provides MCP tools for creating and managing AWS Fault Injection Simulator (FIS)
experiment templates. Experiment templates define the parameters for fault injection
experiments, including targets, actions, and stop conditions.

These tools allow for the creation of complex experiment templates with full configuration
options. They handle the AWS API interactions, error handling, and provide structured
responses suitable for consumption by LLMs.

Experiment templates created through these tools can later be used to run
actual fault injection experiments using the FIS experiment management tools.
"""


@mcp.tool(name='create_experiment_template')
async def create_experiment_template(
    ctx: Context,
    clientToken: str = Field(..., description='Client token for idempotency'),
    description: str = Field(..., description='Description of the experiment template'),
    role_arn: str = Field(..., description='IAM role ARN for experiment execution'),
    name: str = Field(
        ...,
        description='Required name for the experiment template (will be added as Name tag)',
    ),
    tags: Optional[Dict[str, str]] = Field(
        None, description='Optional additional tags to apply to the template'
    ),
    stop_conditions: Optional[List[Dict[str, str]]] = Field(
        None, description='Conditions that stop the experiment'
    ),
    targets: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description='Target resources for the experiment'
    ),
    actions: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description='Actions to perform during the experiment'
    ),
    log_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Configuration for experiment logging'
    ),
    experiment_options: Optional[Dict[str, str]] = Field(
        None, description='Additional experiment options'
    ),
    report_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Configuration for experiment reporting'
    ),
) -> Dict[str, Any]:
    """Create a new AWS FIS experiment template.

    This tool creates a new experiment template that defines the parameters for
    fault injection experiments, including targets, actions, and stop conditions.

    Args:
        ctx: The MCP context for logging and communication
        clientToken: Client token for idempotency
        description: Description of the experiment template
        role_arn: IAM role ARN for experiment execution
        name: Required name for the experiment template (will be added as Name tag)
        tags: Optional additional tags to apply to the template
        stop_conditions: Conditions that stop the experiment
        targets: Target resources for the experiment
        actions: Actions to perform during the experiment
        log_configuration: Configuration for experiment logging
        experiment_options: Additional experiment options
        report_configuration: Configuration for experiment reporting

    Returns:
        Dict containing the created experiment template

    Raises:
        Exception: For AWS API errors or when writes are disabled
    """
    global allow_writes

    # Check if writes are allowed
    if not allow_writes:
        error_msg = (
            'Write operations are disabled. Use --allow-writes flag to enable template creation.'
        )
        await ctx.error(error_msg)
        raise Exception(error_msg)

    try:
        # Start with Name tag as required
        template_tags = {'Name': name}

        # Add any additional tags if provided
        if tags:
            template_tags.update(tags)

        # Default empty collections
        stop_conditions = stop_conditions or []
        targets = targets or {}
        actions = actions or {}

        response = aws_fis.create_experiment_template(
            clientToken=clientToken,
            description=description,
            stopConditions=stop_conditions,
            targets=targets,
            actions=actions,
            roleArn=role_arn,
            tags=template_tags,
            logConfiguration=log_configuration,
            experimentOptions=experiment_options,
            experimentReportConfiguration=report_configuration,
        )

        await ctx.info(
            f'Created experiment template "{name}" with ID: {response.get("experimentTemplate", {}).get("id", "unknown")}'
        )
        return response
    except Exception as e:
        await ctx.error(f'Error creating experiment template: {str(e)}')
        raise


@mcp.tool(name='update_experiment_template')
async def update_experiment_template(
    ctx: Context,
    id: str = Field(..., description='ID of the experiment template to update'),
    description: Optional[str] = Field(
        None, description='Updated description of the experiment template'
    ),
    stop_conditions: Optional[List[Dict[str, str]]] = Field(
        None, description='Updated conditions that stop the experiment'
    ),
    targets: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description='Updated target resources for the experiment'
    ),
    actions: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description='Updated actions to perform during the experiment'
    ),
    role_arn: Optional[str] = Field(
        None, description='Updated IAM role ARN for experiment execution'
    ),
    log_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Updated configuration for experiment logging'
    ),
    experiment_options: Optional[Dict[str, str]] = Field(
        None, description='Updated experiment options'
    ),
    experiment_report_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Updated configuration for experiment reporting'
    ),
) -> Dict[str, Any]:
    """Update an existing AWS FIS experiment template.

    This tool updates an existing experiment template with new parameters for
    fault injection experiments, including targets, actions, and stop conditions.

    Args:
        ctx: The MCP context for logging and communication
        id: ID of the experiment template to update
        description: Updated description of the experiment template
        stop_conditions: Updated conditions that stop the experiment
        targets: Updated target resources for the experiment
        actions: Updated actions to perform during the experiment
        role_arn: Updated IAM role ARN for experiment execution
        log_configuration: Updated configuration for experiment logging
        experiment_options: Updated experiment options
        experiment_report_configuration: Updated configuration for experiment reporting

    Returns:
        Dict containing the updated experiment template
    """
    try:
        # Build the update parameters, only including non-None values
        update_params: Dict[str, Any] = {'id': id}

        if description is not None:
            update_params['description'] = description

        if stop_conditions is not None:
            update_params['stopConditions'] = stop_conditions

        if targets is not None:
            update_params['targets'] = targets

        if actions is not None:
            update_params['actions'] = actions

        if role_arn is not None:
            update_params['roleArn'] = role_arn

        if log_configuration is not None:
            update_params['logConfiguration'] = log_configuration

        if experiment_options is not None:
            update_params['experimentOptions'] = experiment_options

        if experiment_report_configuration is not None:
            update_params['experimentReportConfiguration'] = experiment_report_configuration

        response = aws_fis.update_experiment_template(**update_params)
        await ctx.info(f'Successfully updated experiment template: {id}')
        return response
    except Exception as e:
        await ctx.error(f'Error updating experiment template: {str(e)}')
        raise


def main():
    """Run the AWS FIS MCP Server with CLI argument support.

    This function initializes and starts the AWS FIS MCP Server, which provides
    a set of tools for interacting with AWS Fault Injection Simulator (FIS) and
    related services through the Model Context Protocol (MCP).

    CLI Arguments:
        --aws-profile: AWS profile to use for credentials
        --aws-region: AWS region to use (overrides environment variables)
        --allow-writes: Allow destructive operations like starting experiments

    The server is configured with the FastMCP framework and exposes a collection
    of tools organized into classes for different functional areas:
    - AwsFisActions: For managing FIS experiments and templates
    - ExperimentTemplates: For creating and managing experiment templates
    - ResourceDiscovery: Consolidated class for discovering AWS resources from
      CloudFormation and Resource Explorer

    When executed, the server starts listening for MCP requests and responds
    with the results of the requested operations.
    """
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

    # Initialize AWS clients with the determined configuration
    initialize_aws_clients(effective_region, aws_profile_override)

    # Start the MCP server
    logger.info('Starting AWS FIS MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
