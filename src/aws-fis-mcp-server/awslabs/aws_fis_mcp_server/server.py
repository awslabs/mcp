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

import asyncio
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
    DEFAULT_MAX_RESOURCES,
    ENV_AWS_REGION,
    ENV_FASTMCP_LOG_LEVEL,
    SERVICE_CLOUDFORMATION,
    SERVICE_FIS,
    SERVICE_RESOURCE_EXPLORER,
    SERVICE_S3,
)
from botocore.config import Config
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field
from typing import Any, Dict, List, Optional


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv(ENV_FASTMCP_LOG_LEVEL, 'WARNING'))

# Load environment variables
load_dotenv()

# Get region from environment or default to us-east-1
AWS_REGION = os.getenv(ENV_AWS_REGION, DEFAULT_AWS_REGION)

# Create AWS session
try:
    session = boto3.Session(region_name=AWS_REGION)

    # Create AWS config
    aws_config = Config(
        region_name=AWS_REGION,
        signature_version=AWS_CONFIG_SIGNATURE_VERSION,
        retries={'max_attempts': AWS_CONFIG_MAX_ATTEMPTS, 'mode': AWS_CONFIG_RETRY_MODE},
        user_agent_extra=f'awslabs/mcp/aws-fis-mcp-server/{__version__}',
    )

    # Initialize AWS clients
    aws_fis = session.client(SERVICE_FIS, config=aws_config)
    s3 = session.client(SERVICE_S3, config=aws_config)
    resource_explorer = session.client(SERVICE_RESOURCE_EXPLORER, config=aws_config)
    cloudformation = session.client(SERVICE_CLOUDFORMATION, config=aws_config)

    logger.info(f'AWS clients initialized successfully in region {AWS_REGION}')

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


class AwsFisActions:
    """Class for AWS FIS experiment actions and operations.

    This class provides tools for interacting with AWS Fault Injection Simulator (FIS)
    experiments and templates. It enables listing, retrieving, and executing FIS experiments
    through a set of static methods exposed as MCP tools.

    The class handles AWS API interactions, error handling, and provides structured responses
    suitable for consumption by LLMs. It implements polling mechanisms with exponential backoff
    for long-running operations and proper pagination handling for list operations.
    """

    @mcp.tool(name='list_fis_experiments')
    @staticmethod
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
    @staticmethod
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
    @staticmethod
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
    @staticmethod
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
    @staticmethod
    async def start_experiment(
        ctx: Context,
        id: str = Field(..., description='The experiment template ID to execute'),
        tags: Optional[Dict[str, str]] = Field(
            None, description='Optional tags to apply to the experiment'
        ),
        action: Optional[str] = Field(
            'run-all',
            description='The actions mode for experiment execution (run-all, skip-all, or stop-on-failure)',
        ),
        max_timeout_seconds: int = Field(
            3600,
            description='Maximum time in seconds to wait for experiment completion (default: 1 hour)',
        ),
        initial_poll_interval: int = Field(
            5, description='Starting poll interval in seconds for status checks'
        ),
        max_poll_interval: int = Field(
            60, description='Maximum poll interval in seconds for status checks'
        ),
    ) -> Dict[str, Any]:
        """Starts an AWS FIS experiment and polls its status until completion.

        Args:
            ctx: The MCP context for logging and communication
            id: The experiment template ID
            tags: Optional tags to apply to the experiment
            action: The actions mode (default: 'run-all')
            max_timeout_seconds: Maximum time to wait for experiment completion
            initial_poll_interval: Starting poll interval in seconds
            max_poll_interval: Maximum poll interval in seconds

        Returns:
            Dict containing experiment results

        Raises:
            TimeoutError: If experiment doesn't complete within timeout
            Exception: For other AWS API errors
        """
        try:
            # Default to empty dict if tags is None
            tags = tags or {}

            response = aws_fis.start_experiment(
                experimentTemplateId=id, experimentOptions={'actionsMode': action}, tags=tags
            )

            experiment_id = response['experiment']['id']
            await ctx.info(f'Started experiment with ID: {experiment_id}')

            # Track polling with exponential backoff
            start_time = time.time()
            poll_interval = initial_poll_interval

            # Poll experiment status until it's no longer in progress
            while True:
                # Check if we've exceeded timeout
                if time.time() - start_time > max_timeout_seconds:
                    await ctx.error(
                        f'Experiment polling timed out after {max_timeout_seconds} seconds'
                    )
                    raise TimeoutError(f'Experiment {experiment_id} polling timed out')

                try:
                    status_response = aws_fis.get_experiment(id=experiment_id)
                    state = status_response['experiment']['state']['status']

                    if state in ['pending', 'initiating', 'running']:
                        await ctx.info(f'Experiment is still active. Current Status: {state}')
                        # Use asyncio.sleep instead of time.sleep to avoid blocking
                        await asyncio.sleep(poll_interval)

                        # Implement exponential backoff with max limit
                        poll_interval = min(poll_interval * 1.5, max_poll_interval)
                    else:
                        # Handle terminal states
                        if state == 'completed':
                            await ctx.info('Experiment completed successfully.')
                            return status_response['experiment']
                        elif state == 'stopped':
                            await ctx.warning('Experiment was stopped.')
                            return status_response['experiment']
                        elif state == 'failed':
                            error_message = (
                                status_response['experiment']
                                .get('state', {})
                                .get('reason', 'Unknown reason')
                            )
                            await ctx.error(f'Experiment failed: {error_message}')
                            raise Exception(f'Experiment failed: {error_message}')
                        else:
                            await ctx.error(f'Experiment ended with unknown status: {state}')
                            raise Exception(f'Unknown experiment status: {state}')

                except Exception as e:
                    if 'experiment not found' in str(e).lower():
                        await ctx.error(f'Experiment {experiment_id} not found')
                        raise

                    # For transient errors, log and continue polling
                    await ctx.warning(f'Error polling experiment status: {str(e)}. Retrying...')
                    await asyncio.sleep(poll_interval)

        except Exception as e:
            await ctx.error(f'Error in start_experiment: {str(e)}')
            raise


class ResourceDiscovery:
    """Class for AWS resource discovery operations.

    This class provides a unified interface for discovering AWS resources using both
    CloudFormation and Resource Explorer services. It enables the identification of
    potential targets for fault injection experiments across the AWS account.

    The class offers methods to list resources from different sources, create and manage
    Resource Explorer views, and filter resources based on specific criteria. It handles
    pagination for large result sets and provides structured responses suitable for
    consumption by LLMs.

    This consolidated approach allows for more flexible resource discovery, making it easier
    to design comprehensive resilience testing scenarios regardless of how resources were
    provisioned.
    """

    @mcp.tool(name='discover_resources')
    @staticmethod
    async def discover_resources(
        ctx: Context,
        source: str = Field(
            ...,
            description="Source to discover resources from: 'cloudformation', 'resource-explorer', or 'all'",
        ),
        stack_name: Optional[str] = Field(
            None,
            description="Name of the CloudFormation stack (required if source is 'cloudformation')",
        ),
        query: Optional[str] = Field(
            None,
            description="Filter query for Resource Explorer (optional for 'resource-explorer' source)",
        ),
        max_results: int = Field(
            DEFAULT_MAX_RESOURCES, description='Maximum number of resources to return'
        ),
    ) -> Dict[str, Any]:
        """Discover AWS resources from specified source(s).

        This unified tool discovers resources from CloudFormation stacks, Resource Explorer,
        or both, providing a comprehensive view of available resources for fault injection.

        Args:
            ctx: The MCP context for logging and communication
            source: Source to discover resources from ('cloudformation', 'resource-explorer', or 'all')
            stack_name: Name of the CloudFormation stack (required if source is 'cloudformation')
            query: Filter query for Resource Explorer (optional for 'resource-explorer' source)
            max_results: Maximum number of resources to return

        Returns:
            Dict containing discovered resources organized by source
        """
        result: Dict[str, Any] = {'resources': []}

        try:
            if source.lower() in ['cloudformation', 'all']:
                if source.lower() == 'cloudformation' and not stack_name:
                    raise ValueError("stack_name is required when source is 'cloudformation'")

                if stack_name:
                    # Get resources from specific stack
                    cfn_resources = await ResourceDiscovery.get_stack_resources(ctx, stack_name)
                    for resource in cfn_resources.get('resources', []):
                        result['resources'].append(
                            {
                                'source': 'cloudformation',
                                'stack_name': stack_name,
                                'resource_type': resource.get('ResourceType'),
                                'logical_id': resource.get('LogicalResourceId'),
                                'physical_id': resource.get('PhysicalResourceId'),
                                'status': resource.get('ResourceStatus'),
                            }
                        )
                elif source.lower() == 'all':
                    # List all stacks and get their resources
                    stacks_response = await ResourceDiscovery.list_cfn_stacks(ctx)
                    stacks = stacks_response.get('stacks', [])

                    # Limit the number of stacks to process to avoid timeouts
                    for stack in stacks[: min(5, len(stacks))]:
                        stack_name = stack.get('StackName')
                        if not stack_name:
                            continue
                        try:
                            stack_resources = await ResourceDiscovery.get_stack_resources(
                                ctx, stack_name
                            )
                            for resource in stack_resources.get('resources', [])[
                                : max_results // 2
                            ]:  # Limit resources per stack
                                result['resources'].append(
                                    {
                                        'source': 'cloudformation',
                                        'stack_name': stack_name,
                                        'resource_type': resource.get('ResourceType'),
                                        'logical_id': resource.get('LogicalResourceId'),
                                        'physical_id': resource.get('PhysicalResourceId'),
                                        'status': resource.get('ResourceStatus'),
                                    }
                                )
                        except Exception as e:
                            await ctx.warning(
                                f'Error getting resources for stack {stack_name}: {str(e)}'
                            )

            if source.lower() in ['resource-explorer', 'all']:
                # Get resources from Resource Explorer
                try:
                    params: Dict[str, Any] = {
                        'MaxResults': max_results // 2 if source.lower() == 'all' else max_results
                    }
                    if query:
                        params['QueryString'] = query

                    response = resource_explorer.search(**params)
                    resources = response.get('Resources', [])

                    for item in resources:
                        result['resources'].append(
                            {
                                'source': 'resource-explorer',
                                'service': item.get('Service'),
                                'region': item.get('Region'),
                                'resource_type': item.get('ResourceType'),
                                'arn': item.get('Arn'),
                            }
                        )

                    # Handle pagination
                    while 'NextToken' in response and len(result['resources']) < max_results:
                        params['NextToken'] = response['NextToken']
                        response = resource_explorer.search(**params)
                        for item in response.get('Resources', []):
                            result['resources'].append(
                                {
                                    'source': 'resource-explorer',
                                    'service': item.get('Service'),
                                    'region': item.get('Region'),
                                    'resource_type': item.get('ResourceType'),
                                    'arn': item.get('Arn'),
                                }
                            )
                            if len(result['resources']) >= max_results:
                                break
                except Exception as e:
                    await ctx.warning(
                        f'Error searching resources with Resource Explorer: {str(e)}'
                    )

            # Add metadata about the discovery
            result['metadata'] = {
                'total_resources': len(result['resources']),
                'sources_used': source,
                'max_results': max_results,
            }

            return result
        except Exception as e:
            await ctx.error(f'Resource discovery failed: {str(e)}')
            raise

    # @mcp.tool(name='list_cfn_stacks')
    @staticmethod
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
            response = cfn.list_stacks()  # Remove await here
            all_stacks.extend(response.get('StackSummaries', []))

            # Handle pagination
            while 'NextToken' in response:
                response = cfn.list_stacks(NextToken=response['NextToken'])  # Remove await here
                all_stacks.extend(response.get('StackSummaries', []))

            return {'stacks': all_stacks}
        except Exception as e:
            await ctx.error(f'Error listing CloudFormation stacks: {str(e)}')
            raise

    # @mcp.tool(name='get_stack_resources')
    @staticmethod
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
            response = cfn.list_stack_resources(StackName=stack_name)  # Remove await here
            all_resources.extend(response.get('StackResourceSummaries', []))

            # Handle pagination
            while 'NextToken' in response:
                response = cfn.list_stack_resources(  # Remove await here
                    StackName=stack_name, NextToken=response['NextToken']
                )
                all_resources.extend(response.get('StackResourceSummaries', []))

            return {'resources': all_resources}
        except Exception as e:
            await ctx.error(f'Error getting stack resources: {str(e)}')
            raise

    # @mcp.tool(name='list_resource_explorer_views')
    @staticmethod
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

    @mcp.tool(name='create_resource_explorer_view')
    @staticmethod
    async def create_view(
        ctx: Context,
        query: str = Field(..., description='Filter string for the view'),
        view_name: str = Field(..., description='Name of the view'),
        tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the view'),
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
            tags: Tags to apply to the view
            scope: Scope of the view
            client_token: Client token for idempotency

        Returns:
            Dict containing the created view details
        """
        try:
            # Default empty dict for tags
            tags = tags or {}

            # Generate client token if not provided
            if not client_token:
                client_token = f'create-view-{int(time.time())}'

            response = resource_explorer.create_view(
                ClientToken=client_token,
                Filters={'FilterString': query},
                Scope=scope,
                Tags=tags,
                ViewName=view_name,
            )

            return response
        except Exception as e:
            await ctx.error(f'Error creating Resource Explorer view: {str(e)}')
            raise


class ExperimentTemplates:
    """Class for managing AWS FIS experiment templates.

    This class provides tools for creating and managing AWS Fault Injection Simulator (FIS)
    experiment templates. Experiment templates define the parameters for fault injection
    experiments, including targets, actions, and stop conditions.

    The class exposes methods as MCP tools that allow for the creation of complex
    experiment templates with full configuration options. It handles the AWS API interactions,
    error handling, and provides structured responses suitable for consumption by LLMs.

    Experiment templates created through this class can later be used to run
    actual fault injection experiments using the AwsFisActions class.
    """

    @mcp.tool(name='create_experiment_template')
    @staticmethod
    async def create_experiment_template(
        ctx: Context,
        clientToken: str = Field(..., description='Client token for idempotency'),
        description: str = Field(..., description='Description of the experiment template'),
        role_arn: str = Field(..., description='IAM role ARN for experiment execution'),
        tags: Optional[Dict[str, str]] = Field(
            None, description='Optional tags to apply to the template'
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
            tags: Optional tags to apply to the template
            stop_conditions: Conditions that stop the experiment
            targets: Target resources for the experiment
            actions: Actions to perform during the experiment
            role_arn: IAM role ARN for experiment execution
            log_configuration: Configuration for experiment logging
            experiment_options: Additional experiment options
            report_configuration: Configuration for experiment reporting

        Returns:
            Dict containing the created experiment template
        """
        try:
            # Default empty collections
            tags = tags or {}
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
                tags=tags,
                logConfiguration=log_configuration,
                experimentOptions=experiment_options,
                experimentReportConfiguration=report_configuration,
            )

            return response
        except Exception as e:
            await ctx.error(f'Error creating experiment template: {str(e)}')
            raise

    @mcp.tool(name='update_experiment_template')
    @staticmethod
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


# Initialize class instances for MCP tool registration
aws_fis_actions = AwsFisActions()
resource_discovery = ResourceDiscovery()
experiment_templates = ExperimentTemplates()


def main():
    """Run the AWS FIS MCP Server with CLI argument support.

    This function initializes and starts the AWS FIS MCP Server, which provides
    a set of tools for interacting with AWS Fault Injection Simulator (FIS) and
    related services through the Model Context Protocol (MCP).

    The server is configured with the FastMCP framework and exposes a collection
    of tools organized into classes for different functional areas:
    - AwsFisActions: For managing FIS experiments and templates
    - ExperimentTemplates: For creating and managing experiment templates
    - ResourceDiscovery: Consolidated class for discovering AWS resources from
      CloudFormation and Resource Explorer

    When executed, the server starts listening for MCP requests and responds
    with the results of the requested operations.
    """
    logger.info('Starting AWS FIS MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
