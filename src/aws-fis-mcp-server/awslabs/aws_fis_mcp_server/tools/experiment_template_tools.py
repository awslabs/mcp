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
    from awslabs.aws_fis_mcp_server.server import allow_writes, aws_fis

    if aws_fis is None:
        raise Exception(
            'AWS FIS client not initialized. Please ensure the server is properly configured.'
        )

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

        from awslabs.aws_fis_mcp_server.server import aws_fis

        if aws_fis is None:
            raise Exception(
                'AWS FIS client not initialized. Please ensure the server is properly configured.'
            )
        response = aws_fis.update_experiment_template(**update_params)
        await ctx.info(f'Successfully updated experiment template: {id}')
        return response
    except Exception as e:
        await ctx.error(f'Error updating experiment template: {str(e)}')
        raise
