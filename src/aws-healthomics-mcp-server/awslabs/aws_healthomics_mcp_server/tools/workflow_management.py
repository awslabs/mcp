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

"""Workflow management tools for the AWS HealthOmics MCP server."""

import botocore
import botocore.exceptions
import os
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_REGION,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    decode_from_base64,
    get_aws_session,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


def get_omics_client():
    """Get an AWS HealthOmics client.

    Returns:
        boto3.client: Configured HealthOmics client
    """
    region = os.environ.get('AWS_REGION', DEFAULT_REGION)
    session = get_aws_session(region)
    try:
        return session.client('omics')
    except Exception as e:
        logger.error(f'Failed to create HealthOmics client: {str(e)}')
        raise


async def list_workflows(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics workflows.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination

    Returns:
        Dictionary containing workflow information and next token if available
    """
    client = get_omics_client()

    params: dict[str, Any] = {'maxResults': max_results}
    if next_token:
        params['startingToken'] = next_token

    try:
        response = client.list_workflows(**params)

        # Transform the response to a more user-friendly format
        workflows = []
        for workflow in response.get('items', []):
            creation_time = workflow.get('creationTime')
            workflows.append(
                {
                    'id': workflow.get('id'),
                    'arn': workflow.get('arn'),
                    'name': workflow.get('name'),
                    'description': workflow.get('description'),
                    'status': workflow.get('status'),
                    'parameters': workflow.get('parameters'),
                    'storageType': workflow.get('storageType'),
                    'storageCapacity': workflow.get('storageCapacity'),
                    'type': workflow.get('type'),
                    'creationTime': creation_time.isoformat()
                    if creation_time is not None
                    else None,
                }
            )

        result: Dict[str, Any] = {'workflows': workflows}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error listing workflows: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error listing workflows: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def create_workflow(
    ctx: Context,
    name: str = Field(
        ...,
        description='Name of the workflow',
    ),
    definition_zip_base64: str = Field(
        ...,
        description='Base64-encoded workflow definition ZIP file',
    ),
    description: Optional[str] = Field(
        None,
        description='Optional description of the workflow',
    ),
    parameter_template: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional parameter template for the workflow',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics workflow.

    Args:
        ctx: MCP context for error reporting
        name: Name of the workflow
        definition_zip_base64: Base64-encoded workflow definition ZIP file
        description: Optional description of the workflow
        parameter_template: Optional parameter template for the workflow

    Returns:
        Dictionary containing the created workflow information
    """
    client = get_omics_client()

    try:
        definition_zip = decode_from_base64(definition_zip_base64)
    except Exception as e:
        error_message = f'Failed to decode base64 workflow definition: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    params = {
        'name': name,
        'definitionZip': definition_zip,
    }

    if description:
        params['description'] = description

    if parameter_template:
        params['parameterTemplate'] = parameter_template

    try:
        response = client.create_workflow(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'name': name,
            'description': description,
        }
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error creating workflow: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error creating workflow: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def get_workflow(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow to retrieve',
    ),
    export_definition: bool = Field(
        False,
        description='Whether to include a presigned URL for downloading the workflow definition ZIP file',
    ),
) -> Dict[str, Any]:
    """Get details about a specific workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow to retrieve
        export_definition: Whether to include a presigned URL for downloading the workflow definition ZIP file

    Returns:
        Dictionary containing workflow details. When export_definition=True, includes a 'definition'
        field with a presigned URL for downloading the workflow definition ZIP file.
    """
    client = get_omics_client()

    params: dict[str, Any] = {'id': workflow_id}

    if export_definition:
        params['export'] = ['DEFINITION']

    try:
        response = client.get_workflow(**params)

        result = {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'status': response.get('status'),
            'type': response.get('type'),
            'creationTime': response.get('creationTime').isoformat()
            if response.get('creationTime')
            else None,
        }

        if 'description' in response:
            result['description'] = response['description']

        if 'statusMessage' in response:
            result['statusMessage'] = response['statusMessage']

        if 'parameterTemplate' in response:
            result['parameterTemplate'] = response['parameterTemplate']

        if 'definition' in response:
            result['definition'] = response['definition']

        return result
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error getting workflow {workflow_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error getting workflow {workflow_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def create_workflow_version(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow',
    ),
    version_name: str = Field(
        ...,
        description='Name for the new version',
    ),
    definition_zip_base64: str = Field(
        ...,
        description='Base64-encoded workflow definition ZIP file',
    ),
    description: Optional[str] = Field(
        None,
        description='Optional description of the workflow version',
    ),
    parameter_template: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional parameter template for the workflow',
    ),
    storage_type: Optional[str] = Field(
        'DYNAMIC',
        description='Storage type (STATIC or DYNAMIC)',
    ),
    storage_capacity: Optional[int] = Field(
        None,
        description='Storage capacity in GB (required for STATIC)',
        ge=1,
    ),
) -> Dict[str, Any]:
    """Create a new version of an existing workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow
        version_name: Name for the new version
        definition_zip_base64: Base64-encoded workflow definition ZIP file
        description: Optional description of the workflow version
        parameter_template: Optional parameter template for the workflow
        storage_type: Storage type (STATIC or DYNAMIC)
        storage_capacity: Storage capacity in GB (required for STATIC)

    Returns:
        Dictionary containing the created workflow version information
    """
    client = get_omics_client()

    try:
        definition_zip = decode_from_base64(definition_zip_base64)
    except Exception as e:
        error_message = f'Failed to decode base64 workflow definition: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    params = {
        'workflowId': workflow_id,
        'versionName': version_name,
        'definitionZip': definition_zip,
        'storageType': storage_type,
    }

    if description:
        params['description'] = description

    if parameter_template:
        params['parameterTemplate'] = parameter_template

    if storage_type == 'STATIC':
        if not storage_capacity:
            error_message = 'Storage capacity is required when storage type is STATIC'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)
        params['storageCapacity'] = storage_capacity

    try:
        response = client.create_workflow_version(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'name': response.get('name'),
            'versionName': version_name,
            'description': description,
        }
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error creating workflow version: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error creating workflow version: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def list_workflow_versions(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List versions of a workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination

    Returns:
        Dictionary containing workflow version information and next token if available
    """
    client = get_omics_client()

    params = {
        'workflowId': workflow_id,
        'maxResults': max_results,
    }

    if next_token:
        params['startingToken'] = next_token

    try:
        response = client.list_workflow_versions(**params)

        # Transform the response to a more user-friendly format
        versions = []
        for version in response.get('items', []):
            creation_time = version.get('creationTime')
            versions.append(
                {
                    'id': version.get('id'),
                    'arn': version.get('arn'),
                    'name': version.get('name'),
                    'versionName': version.get('versionName'),
                    'status': version.get('status'),
                    'type': version.get('type'),
                    'creationTime': (
                        creation_time
                        if isinstance(creation_time, str)
                        else creation_time.isoformat()
                        if creation_time is not None
                        else None
                    ),
                }
            )

        result: Dict[str, Any] = {'versions': versions}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error listing workflow versions for workflow {workflow_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = (
            f'Unexpected error listing workflow versions for workflow {workflow_id}: {str(e)}'
        )
        logger.error(error_message)
        await ctx.error(error_message)
        raise
