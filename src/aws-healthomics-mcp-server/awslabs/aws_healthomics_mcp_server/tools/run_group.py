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

"""Run group management tools for the AWS HealthOmics MCP server."""

import uuid
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import (
    handle_tool_error,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


async def create_run_group(
    ctx: Context,
    name: Optional[str] = Field(None, description='Name for the run group (1-128 characters)'),
    max_cpus: Optional[int] = Field(
        None, description='Maximum CPUs for the run group (1-100000)', ge=1, le=100000
    ),
    max_gpus: Optional[int] = Field(
        None, description='Maximum GPUs for the run group (1-100000)', ge=1, le=100000
    ),
    max_duration: Optional[int] = Field(
        None, description='Maximum duration in minutes (1-100000)', ge=1, le=100000
    ),
    max_runs: Optional[int] = Field(
        None, description='Maximum concurrent runs (1-100000)', ge=1, le=100000
    ),
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the run group'),
) -> Dict[str, Any]:
    """Create a new HealthOmics run group.

    Args:
        ctx: MCP context for error reporting
        name: Name for the run group (1-128 characters)
        max_cpus: Maximum CPUs for the run group (1-100000)
        max_gpus: Maximum GPUs for the run group (1-100000)
        max_duration: Maximum duration in minutes (1-100000)
        max_runs: Maximum concurrent runs (1-100000)
        tags: Tags to apply to the run group

    Returns:
        Dictionary containing the created run group's id, arn, and tags, or error dict
    """
    try:
        client = get_omics_client()

        params: Dict[str, Any] = {
            'requestId': str(uuid.uuid4()),
        }

        if name is not None:
            params['name'] = name

        if max_cpus is not None:
            params['maxCpus'] = max_cpus

        if max_gpus is not None:
            params['maxGpus'] = max_gpus

        if max_duration is not None:
            params['maxDuration'] = max_duration

        if max_runs is not None:
            params['maxRuns'] = max_runs

        if tags is not None:
            params['tags'] = tags

        logger.info(f'Creating run group with params: {params}')
        response = client.create_run_group(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'tags': response.get('tags'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating run group')


async def get_run_group(
    ctx: Context,
    run_group_id: str = Field(..., description='ID of the run group to retrieve'),
) -> Dict[str, Any]:
    """Get details of a specific HealthOmics run group.

    Args:
        ctx: MCP context for error reporting
        run_group_id: ID of the run group to retrieve

    Returns:
        Dictionary containing the run group details, or error dict
    """
    try:
        client = get_omics_client()

        logger.info(f'Getting run group: {run_group_id}')
        response = client.get_run_group(id=run_group_id)

        creation_time = response.get('creationTime')
        if creation_time is not None:
            creation_time = creation_time.isoformat()

        return {
            'arn': response.get('arn'),
            'id': response.get('id'),
            'name': response.get('name'),
            'maxCpus': response.get('maxCpus'),
            'maxGpus': response.get('maxGpus'),
            'maxDuration': response.get('maxDuration'),
            'maxRuns': response.get('maxRuns'),
            'tags': response.get('tags'),
            'creationTime': creation_time,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting run group')


async def list_run_groups(
    ctx: Context,
    name: Optional[str] = Field(None, description='Filter by run group name'),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None, description='Token for pagination from a previous response'
    ),
) -> Dict[str, Any]:
    """List HealthOmics run groups.

    Args:
        ctx: MCP context for error reporting
        name: Filter by run group name
        max_results: Maximum number of results to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing run group summaries and next token if available, or error dict
    """
    try:
        client = get_omics_client()

        params: Dict[str, Any] = {
            'maxResults': max_results,
        }

        if name is not None:
            params['name'] = name

        if next_token is not None:
            params['startingToken'] = next_token

        logger.info(f'Listing run groups with params: {params}')
        response = client.list_run_groups(**params)

        run_groups = []
        for item in response.get('items', []):
            creation_time = item.get('creationTime')
            run_group_info = {
                'id': item.get('id'),
                'arn': item.get('arn'),
                'name': item.get('name'),
                'maxCpus': item.get('maxCpus'),
                'maxGpus': item.get('maxGpus'),
                'maxDuration': item.get('maxDuration'),
                'maxRuns': item.get('maxRuns'),
                'creationTime': creation_time.isoformat() if creation_time is not None else None,
            }
            run_groups.append(run_group_info)

        result: Dict[str, Any] = {'runGroups': run_groups}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing run groups')


async def update_run_group(
    ctx: Context,
    run_group_id: str = Field(..., description='ID of the run group to update'),
    name: Optional[str] = Field(None, description='New name for the run group'),
    max_cpus: Optional[int] = Field(None, description='New maximum CPUs', ge=1, le=100000),
    max_gpus: Optional[int] = Field(None, description='New maximum GPUs', ge=1, le=100000),
    max_duration: Optional[int] = Field(
        None, description='New maximum duration in minutes', ge=1, le=100000
    ),
    max_runs: Optional[int] = Field(
        None, description='New maximum concurrent runs', ge=1, le=100000
    ),
) -> Dict[str, Any]:
    """Update an existing HealthOmics run group.

    Args:
        ctx: MCP context for error reporting
        run_group_id: ID of the run group to update
        name: New name for the run group
        max_cpus: New maximum CPUs
        max_gpus: New maximum GPUs
        max_duration: New maximum duration in minutes
        max_runs: New maximum concurrent runs

    Returns:
        Dictionary containing the run group ID and update status, or error dict
    """
    try:
        client = get_omics_client()

        params: Dict[str, Any] = {
            'id': run_group_id,
        }

        if name is not None:
            params['name'] = name

        if max_cpus is not None:
            params['maxCpus'] = max_cpus

        if max_gpus is not None:
            params['maxGpus'] = max_gpus

        if max_duration is not None:
            params['maxDuration'] = max_duration

        if max_runs is not None:
            params['maxRuns'] = max_runs

        logger.info(f'Updating run group {run_group_id} with params: {params}')
        client.update_run_group(**params)

        return {
            'id': run_group_id,
            'status': 'updated',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error updating run group')
