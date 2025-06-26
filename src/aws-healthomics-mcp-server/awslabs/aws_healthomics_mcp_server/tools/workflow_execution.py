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

"""Workflow execution tools for the AWS HealthOmics MCP server."""

import botocore.exceptions
import os
from awslabs.aws_healthomics_mcp_server.consts import (
    CACHE_BEHAVIORS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_REGION,
    ERROR_INVALID_CACHE_BEHAVIOR,
    ERROR_INVALID_RUN_STATUS,
    ERROR_INVALID_STORAGE_TYPE,
    ERROR_STATIC_STORAGE_REQUIRES_CAPACITY,
    RUN_STATUSES,
    STORAGE_TYPE_STATIC,
    STORAGE_TYPES,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import ensure_s3_uri_ends_with_slash
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO datetime string to datetime object.

    Args:
        iso_string: ISO format datetime string

    Returns:
        datetime object

    Raises:
        ValueError: If the datetime string is invalid
    """
    try:
        # Handle both with and without timezone info
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        elif '+' not in iso_string and iso_string.count(':') == 2:
            # Add timezone if missing
            iso_string += '+00:00'
        return datetime.fromisoformat(iso_string)
    except ValueError as e:
        raise ValueError(f"Invalid datetime format '{iso_string}': {str(e)}")


def filter_runs_by_creation_time(
    runs: List[Dict[str, Any]],
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter runs by creation time.

    Args:
        runs: List of run dictionaries
        created_after: ISO datetime string for filtering runs created after this time
        created_before: ISO datetime string for filtering runs created before this time

    Returns:
        Filtered list of runs
    """
    if not created_after and not created_before:
        return runs

    filtered_runs = []

    # Parse filter datetimes
    after_dt = None
    before_dt = None

    if created_after:
        after_dt = parse_iso_datetime(created_after)
    if created_before:
        before_dt = parse_iso_datetime(created_before)

    for run in runs:
        creation_time_str = run.get('creationTime')
        if not creation_time_str:
            continue

        try:
            creation_time = parse_iso_datetime(creation_time_str)

            # Apply filters
            if after_dt and creation_time <= after_dt:
                continue
            if before_dt and creation_time >= before_dt:
                continue

            filtered_runs.append(run)
        except ValueError:
            # Skip runs with invalid creation times
            logger.warning(
                f'Skipping run {run.get("id")} with invalid creation time: {creation_time_str}'
            )
            continue

    return filtered_runs


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


async def start_run(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow to run',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM role to use for the run',
    ),
    name: str = Field(
        ...,
        description='Name for the run',
    ),
    output_uri: str = Field(
        ...,
        description='S3 URI for the run outputs',
    ),
    parameters: Optional[Dict[str, Any]] = Field(
        description="""Parameters for the workflow. Parameter names must match one of the keys in the workflow's parameter template.
       All non-optional parameters must be present, if they are not provided the workflow run will not start. No other parameter names are allowed.
       The descriptions of the parameters in the parameter template may provide clues to the type of the parameter. It may be
       necessary to inspect the workflow definition to determine the appropriate parameter type.
       """,
    ),
    workflow_version_name: Optional[str] = Field(
        None,
        description='Optional version name to run',
    ),
    storage_type: str = Field(
        'DYNAMIC',
        description='Storage type (STATIC or DYNAMIC). DYNAMIC is preferred except for runs with very large inputs (TiBs).',
    ),
    storage_capacity: Optional[int] = Field(
        None,
        description='Storage capacity in GB (required for STATIC). Storage is allocated in 1200 GiB chunks',
        ge=1200,
    ),
    cache_id: Optional[str] = Field(
        None,
        description='Optional ID of a run cache to use',
    ),
    cache_behavior: Optional[str] = Field(
        None,
        description='Optional cache behavior (CACHE_ALWAYS or CACHE_ON_FAILURE)',
    ),
) -> Dict[str, Any]:
    """Start a workflow run.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow to run
        role_arn: ARN of the IAM role to use for the run
        name: Name for the run
        output_uri: S3 URI for the run outputs
        parameters: Parameters for the workflow.
           Parameter names must match one of the keys in the workflow's parameter template.
           All non-optional parameters must be present, if they are not provided the workflow run will not start. No other parameter
           names are allowed.
           The descriptions of the parameters in the parameter template may provide clues to the type of the parameter. It may be
           necessary to inspect the workflow definition to determine the appropriate parameter type.
        workflow_version_name: Optional version name to run
        storage_type: Storage type (STATIC or DYNAMIC)
        storage_capacity: Storage capacity in GB (required for STATIC)
        cache_id: Optional ID of a run cache to use
        cache_behavior: Optional cache behavior (CACHE_ALWAYS or CACHE_ON_FAILURE)

    Returns:
        Dictionary containing the run information
    """
    client = get_omics_client()

    # Validate storage type
    if storage_type not in STORAGE_TYPES:
        error_message = ERROR_INVALID_STORAGE_TYPE.format(STORAGE_TYPES)
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate storage capacity for STATIC storage
    if storage_type == STORAGE_TYPE_STATIC and storage_capacity is None:
        error_message = ERROR_STATIC_STORAGE_REQUIRES_CAPACITY
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate cache behavior
    if cache_behavior and cache_behavior not in CACHE_BEHAVIORS:
        error_message = ERROR_INVALID_CACHE_BEHAVIOR.format(CACHE_BEHAVIORS)
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Ensure output URI ends with a slash
    try:
        output_uri = ensure_s3_uri_ends_with_slash(output_uri)
    except ValueError as e:
        error_message = f'Invalid S3 URI: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise

    params = {
        'workflowId': workflow_id,
        'roleArn': role_arn,
        'name': name,
        'outputUri': output_uri,
        'parameters': parameters,
        'storageType': storage_type,
    }

    if workflow_version_name:
        params['workflowVersionName'] = workflow_version_name

    if storage_type == STORAGE_TYPE_STATIC and storage_capacity:
        params['storageCapacity'] = storage_capacity

    if cache_id:
        params['cacheId'] = cache_id

        if cache_behavior:
            params['cacheBehavior'] = cache_behavior

    try:
        response = client.start_run(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'name': name,
            'workflowId': workflow_id,
            'workflowVersionName': workflow_version_name,
            'outputUri': output_uri,
        }
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error starting run: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error starting run: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def list_runs(
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
    status: Optional[str] = Field(
        None,
        description='Filter by run status',
    ),
    created_after: Optional[str] = Field(
        None,
        description='Filter for runs created after this timestamp (ISO format)',
    ),
    created_before: Optional[str] = Field(
        None,
        description='Filter for runs created before this timestamp (ISO format)',
    ),
) -> Dict[str, Any]:
    """List workflow runs.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination
        status: Filter by run status
        created_after: Filter for runs created after this timestamp (ISO format)
        created_before: Filter for runs created before this timestamp (ISO format)

    Returns:
        Dictionary containing run information and next token if available
    """
    client = get_omics_client()

    # Validate status
    if status and status not in RUN_STATUSES:
        error_message = ERROR_INVALID_RUN_STATUS.format(RUN_STATUSES)
        logger.error(error_message)
        await ctx.error(error_message)
        raise ValueError(error_message)

    # Validate datetime filters
    if created_after:
        try:
            parse_iso_datetime(created_after)
        except ValueError as e:
            error_message = f'Invalid created_after datetime: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)

    if created_before:
        try:
            parse_iso_datetime(created_before)
        except ValueError as e:
            error_message = f'Invalid created_before datetime: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise ValueError(error_message)

    # Determine if we need client-side filtering
    needs_filtering = created_after or created_before

    try:
        all_runs = []
        current_token = next_token

        # If we need filtering, collect more runs to reduce API calls
        # Use a larger batch size when filtering
        batch_size = 100 if needs_filtering else max_results

        while True:
            params: dict[str, Any] = {'maxResults': batch_size}

            if current_token:
                params['startingToken'] = current_token

            if status:
                params['status'] = status

            response = client.list_runs(**params)

            # Transform the response to a more user-friendly format
            batch_runs = []
            for run in response.get('items', []):
                creation_time = run.get('creationTime')
                run_info = {
                    'id': run.get('id'),
                    'arn': run.get('arn'),
                    'name': run.get('name'),
                    'status': run.get('status'),
                    'workflowId': run.get('workflowId'),
                    'workflowType': run.get('workflowType'),
                    'creationTime': creation_time.isoformat()
                    if creation_time is not None
                    else None,
                }

                if 'startTime' in run and run['startTime'] is not None:
                    run_info['startTime'] = run['startTime'].isoformat()

                if 'stopTime' in run and run['stopTime'] is not None:
                    run_info['stopTime'] = run['stopTime'].isoformat()

                batch_runs.append(run_info)

            all_runs.extend(batch_runs)

            # Check if we have more pages
            current_token = response.get('nextToken')

            # If no filtering needed, return first batch
            if not needs_filtering:
                result: Dict[str, Any] = {'runs': all_runs}
                if current_token:
                    result['nextToken'] = current_token
                return result

            # If filtering, continue until we have enough results or no more pages
            if not current_token:
                break

            # If we have enough filtered results, we can stop early
            if needs_filtering:
                filtered_so_far = filter_runs_by_creation_time(
                    all_runs, created_after, created_before
                )
                if len(filtered_so_far) >= max_results:
                    break

        # Apply client-side filtering if needed
        if needs_filtering:
            filtered_runs = filter_runs_by_creation_time(all_runs, created_after, created_before)

            # Apply max_results limit to filtered results
            result_runs = filtered_runs[:max_results]

            result = {'runs': result_runs}

            # If we have more filtered results than max_results, we could implement
            # a custom pagination token, but for simplicity we'll omit nextToken
            # when client-side filtering is applied
            if len(filtered_runs) > max_results:
                logger.info(
                    f'Client-side filtering returned {len(filtered_runs)} results, '
                    f'truncated to {max_results}. Pagination not supported with date filters.'
                )

            return result
        else:
            # No filtering needed, return all collected runs
            result: Dict[str, Any] = {'runs': all_runs}
            if current_token:
                result['nextToken'] = current_token
            return result

    except botocore.exceptions.ClientError as e:
        error_message = f'AWS error listing runs: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error listing runs: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error listing runs: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def get_run(
    ctx: Context,
    run_id: str = Field(
        ...,
        description='ID of the run to retrieve',
    ),
) -> Dict[str, Any]:
    """Get details about a specific run.

    Args:
        ctx: MCP context for error reporting
        run_id: ID of the run to retrieve

    Returns:
        Dictionary containing run details including:
        - Basic run information (id, arn, name, status)
        - Workflow information (workflowId, workflowType, workflowVersionName)
        - Timing information (creationTime, startTime, stopTime)
        - Output locations (outputUri, runOutputUri)
        - IAM role (roleArn)
        - Run parameters and metadata
        - Status messages and failure reasons (if applicable)
    """
    client = get_omics_client()

    try:
        response = client.get_run(id=run_id)

        result = {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'status': response.get('status'),
            'workflowId': response.get('workflowId'),
            'workflowType': response.get('workflowType'),
            'creationTime': response.get('creationTime').isoformat()
            if response.get('creationTime')
            else None,
            'outputUri': response.get('outputUri'),
            'roleArn': response.get('roleArn'),
            'runOutputUri': response.get('runOutputUri'),
        }

        if 'parameters' in response:
            result['parameters'] = response['parameters']

        if 'uuid' in response:
            result['uuid'] = response['uuid']

        # Handle optional datetime fields
        for field in ['startTime', 'stopTime']:
            if field in response and response[field] is not None:
                result[field] = response[field].isoformat()

        # Handle optional string fields
        for field in ['statusMessage', 'failureReason', 'workflowVersionName']:
            if field in response:
                result[field] = response[field]

        return result
    except botocore.exceptions.ClientError as e:
        error_message = f'AWS error getting run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error getting run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error getting run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def list_run_tasks(
    ctx: Context,
    run_id: str = Field(
        ...,
        description='ID of the run',
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
    status: Optional[str] = Field(
        None,
        description='Filter by task status',
    ),
) -> Dict[str, Any]:
    """List tasks for a specific run.

    Args:
        ctx: MCP context for error reporting
        run_id: ID of the run
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination
        status: Filter by task status

    Returns:
        Dictionary containing task information and next token if available
    """
    client = get_omics_client()

    params = {
        'id': run_id,
        'maxResults': max_results,
    }

    if next_token:
        params['startingToken'] = next_token

    if status:
        params['status'] = status

    try:
        response = client.list_run_tasks(**params)

        # Transform the response to a more user-friendly format
        tasks = []
        for task in response.get('items', []):
            task_info = {
                'taskId': task.get('taskId'),
                'status': task.get('status'),
                'name': task.get('name'),
                'cpus': task.get('cpus'),
                'memory': task.get('memory'),
            }

            if 'startTime' in task:
                task_info['startTime'] = task['startTime'].isoformat()

            if 'stopTime' in task:
                task_info['stopTime'] = task['stopTime'].isoformat()

            tasks.append(task_info)

        result: Dict[str, Any] = {'tasks': tasks}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error listing tasks for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error listing tasks for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def get_run_task(
    ctx: Context,
    run_id: str = Field(
        ...,
        description='ID of the run',
    ),
    task_id: str = Field(
        ...,
        description='ID of the task',
    ),
) -> Dict[str, Any]:
    """Get details about a specific task.

    Args:
        ctx: MCP context for error reporting
        run_id: ID of the run
        task_id: ID of the task

    Returns:
        Dictionary containing task details
    """
    client = get_omics_client()

    try:
        response = client.get_run_task(id=run_id, taskId=task_id)

        result = {
            'taskId': response.get('taskId'),
            'status': response.get('status'),
            'name': response.get('name'),
            'cpus': response.get('cpus'),
            'memory': response.get('memory'),
        }

        if 'startTime' in response:
            result['startTime'] = response['startTime'].isoformat()

        if 'stopTime' in response:
            result['stopTime'] = response['stopTime'].isoformat()

        if 'statusMessage' in response:
            result['statusMessage'] = response['statusMessage']

        if 'logStream' in response:
            result['logStream'] = response['logStream']

        return result
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error getting task {task_id} for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error getting task {task_id} for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
