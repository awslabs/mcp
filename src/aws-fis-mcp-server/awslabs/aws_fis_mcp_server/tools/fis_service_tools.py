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

from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


"""AWS FIS Experiment Management Tools.

This section provides MCP tools for interacting with AWS Fault Injection Simulator (FIS)
experiments and templates. These tools enable listing, retrieving, and executing FIS experiments
to help design and conduct controlled chaos engineering tests.

The tools handle AWS API interactions, error handling, and provide structured responses
suitable for consumption by LLMs. They implement polling mechanisms with exponential backoff
for long-running operations and proper pagination handling for list operations.
"""


# @mcp.tool(name='list_fis_experiments')
async def list_all_fis_experiments(ctx: Context) -> Dict[str, Dict[str, Any]]:
    """Retrieves a list of Experiments available in the AWS FIS service.

    This tool fetches all FIS experiments in the current AWS account and region,
    organizing them by name for easy reference. It handles pagination automatically.

    Returns:
    Dict containing experiment details organized by name
    """
    try:
        from awslabs.aws_fis_mcp_server.server import aws_fis

        if aws_fis is None:
            raise Exception(
                'AWS FIS client not initialized. Please ensure the server is properly configured.'
            )
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


# @mcp.tool(name='get_experiment')
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
        from awslabs.aws_fis_mcp_server.server import aws_fis

        response = aws_fis.get_experiment(id=id)
        return response.get('experiment', {})
    except Exception as e:
        await ctx.error(f'Error getting experiment details: {str(e)}')
        raise


# @mcp.tool(name='list_experiment_templates')
async def list_experiment_templates(ctx: Context) -> List[Dict[str, Any]]:
    """List all experiment templates.

    This tool retrieves all FIS experiment templates in the current AWS account and region.
    It handles pagination automatically to ensure all templates are returned.

    Returns:
        List of experiment templates with their details
    """
    try:
        all_templates = []
        from awslabs.aws_fis_mcp_server.server import aws_fis

        if aws_fis is None:
            raise Exception(
                'AWS FIS client not initialized. Please ensure the server is properly configured.'
            )
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


# @mcp.tool(name='get_experiment_template')
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
        from awslabs.aws_fis_mcp_server.server import aws_fis

        if aws_fis is None:
            raise Exception(
                'AWS FIS client not initialized. Please ensure the server is properly configured.'
            )
        response = aws_fis.get_experiment_template(id=id)
        return response
    except Exception as e:
        await ctx.error(f'Error getting experiment template: {str(e)}')
        raise


# @mcp.tool('start_experiment')
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
    from awslabs.aws_fis_mcp_server.server import allow_writes, aws_fis

    if aws_fis is None:
        raise Exception(
            'AWS FIS client not initialized. Please ensure the server is properly configured.'
        )

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
