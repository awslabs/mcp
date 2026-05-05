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

"""Run batch management tools for the AWS HealthOmics MCP server."""

from awslabs.aws_healthomics_mcp_server.consts import (
    BATCH_STATUSES,
    DEFAULT_MAX_RESULTS,
    ERROR_INVALID_BATCH_RUN_SETTINGS,
    ERROR_INVALID_BATCH_STATUS,
    ERROR_INVALID_SUBMISSION_STATUS,
    SUBMISSION_STATUSES,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.datetime_utils import (
    datetime_to_iso,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import (
    handle_tool_error,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


def _validate_batch_run_settings(batch_run_settings: Dict[str, Any]) -> Optional[str]:
    """Validate that batchRunSettings has exactly one of inlineSettings or s3UriSettings.

    Args:
        batch_run_settings: The batch run settings dictionary

    Returns:
        Error message if validation fails, None if valid
    """
    has_inline = 'inlineSettings' in batch_run_settings
    has_s3 = 's3UriSettings' in batch_run_settings

    if has_inline == has_s3:  # Both present or both absent
        return ERROR_INVALID_BATCH_RUN_SETTINGS
    return None


async def start_run_batch(
    ctx: Context,
    workflow_id: str = Field(..., description='ID of the workflow to run'),
    role_arn: str = Field(..., description='IAM role ARN for the batch runs'),
    output_uri: str = Field(..., description='S3 URI for output files'),
    batch_run_settings: Dict[str, Any] = Field(
        ...,
        description='Batch run settings with either inlineSettings (list of up to 100 run configs) or s3UriSettings (S3 URI for configs)',
    ),
    batch_name: Optional[str] = Field(None, description='Name for the batch'),
    workflow_type: Optional[str] = Field(None, description='Workflow type: WDL, NEXTFLOW, or CWL'),
    workflow_version_name: Optional[str] = Field(None, description='Version name of the workflow'),
    parameters: Optional[Dict[str, Any]] = Field(
        None, description='Default parameters for all runs in the batch'
    ),
    storage_type: Optional[str] = Field(None, description='Storage type: STATIC or DYNAMIC'),
    storage_capacity: Optional[int] = Field(
        None, description='Storage capacity in GB (required for STATIC storage)'
    ),
    run_group_id: Optional[str] = Field(None, description='Run group ID'),
    cache_id: Optional[str] = Field(None, description='Run cache ID'),
    cache_behavior: Optional[str] = Field(
        None, description='Cache behavior: CACHE_ALWAYS or CACHE_ON_FAILURE'
    ),
    retention_mode: Optional[str] = Field(None, description='Retention mode: RETAIN or REMOVE'),
    request_id: Optional[str] = Field(None, description='Idempotency token'),
    tags: Optional[Dict[str, str]] = Field(None, description='Tags for the batch'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Start a new HealthOmics run batch.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow to run
        role_arn: IAM role ARN for the batch runs
        output_uri: S3 URI for output files
        batch_run_settings: Batch run settings with inlineSettings or s3UriSettings
        batch_name: Optional name for the batch
        workflow_type: Optional workflow type (WDL, NEXTFLOW, CWL)
        workflow_version_name: Optional version name of the workflow
        parameters: Optional default parameters for all runs
        storage_type: Optional storage type (STATIC or DYNAMIC)
        storage_capacity: Optional storage capacity in GB
        run_group_id: Optional run group ID
        cache_id: Optional run cache ID
        cache_behavior: Optional cache behavior
        retention_mode: Optional retention mode
        request_id: Optional idempotency token
        tags: Optional tags for the batch
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing id, arn, status, uuid, and tags, or error dict
    """
    try:
        # Validate batch_run_settings
        validation_error = _validate_batch_run_settings(batch_run_settings)
        if validation_error:
            return await handle_tool_error(ctx, ValueError(validation_error), 'Invalid parameters')

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        # Build defaultRunSetting
        default_run_setting: Dict[str, Any] = {
            'workflowId': workflow_id,
            'roleArn': role_arn,
            'outputUri': output_uri,
        }

        if workflow_type is not None:
            default_run_setting['workflowType'] = workflow_type

        if workflow_version_name is not None:
            default_run_setting['workflowVersionName'] = workflow_version_name

        if parameters is not None:
            default_run_setting['parameters'] = parameters

        if storage_type is not None:
            default_run_setting['storageType'] = storage_type

        if storage_capacity is not None:
            default_run_setting['storageCapacity'] = storage_capacity

        if run_group_id is not None:
            default_run_setting['runGroupId'] = run_group_id

        if cache_id is not None:
            default_run_setting['cacheId'] = cache_id

        if cache_behavior is not None:
            default_run_setting['cacheBehavior'] = cache_behavior

        if retention_mode is not None:
            default_run_setting['retentionMode'] = retention_mode

        # Build API params
        params: Dict[str, Any] = {
            'defaultRunSetting': default_run_setting,
            'batchRunSettings': batch_run_settings,
        }

        if batch_name is not None:
            params['name'] = batch_name

        if request_id is not None:
            params['requestId'] = request_id

        if tags is not None:
            params['tags'] = tags

        logger.info(f'Starting run batch with workflow {workflow_id}')
        response = client.start_run_batch(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'uuid': response.get('uuid'),
            'tags': response.get('tags'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error starting run batch')


async def get_batch(
    ctx: Context,
    batch_id: str = Field(..., description='ID of the batch to retrieve'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Get details of a specific HealthOmics batch.

    Args:
        ctx: MCP context for error reporting
        batch_id: ID of the batch to retrieve
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing batch details, or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Getting batch: {batch_id}')
        response = client.get_batch(id=batch_id)

        result: Dict[str, Any] = {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'uuid': response.get('uuid'),
            'name': response.get('name'),
            'status': response.get('status'),
            'totalRuns': response.get('totalRuns'),
            'defaultRunSetting': response.get('defaultRunSetting'),
            'submissionSummary': response.get('submissionSummary'),
            'runSummary': response.get('runSummary'),
            'creationTime': datetime_to_iso(response.get('creationTime')),
            'startTime': datetime_to_iso(response.get('startTime')),
            'stopTime': datetime_to_iso(response.get('stopTime')),
            'tags': response.get('tags'),
        }

        # Include failureReason if batch status is FAILED
        if response.get('failureReason'):
            result['failureReason'] = response.get('failureReason')

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting batch')


async def list_batches(
    ctx: Context,
    status: Optional[str] = Field(None, description='Filter by batch status'),
    name: Optional[str] = Field(None, description='Filter by batch name'),
    run_group_id: Optional[str] = Field(None, description='Filter by run group ID'),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None, description='Token for pagination from a previous response'
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List HealthOmics batches.

    Args:
        ctx: MCP context for error reporting
        status: Optional filter by batch status
        name: Optional filter by batch name
        run_group_id: Optional filter by run group ID
        max_results: Maximum number of results to return
        next_token: Token for pagination from a previous response
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing batch summaries and next token if available, or error dict
    """
    try:
        # Validate status filter
        if status is not None and status not in BATCH_STATUSES:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_INVALID_BATCH_STATUS.format(', '.join(BATCH_STATUSES))),
                'Invalid parameters',
            )

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {
            'maxResults': max_results,
        }

        if status is not None:
            params['status'] = status

        if name is not None:
            params['name'] = name

        if run_group_id is not None:
            params['runGroupId'] = run_group_id

        if next_token is not None:
            params['startingToken'] = next_token

        logger.info(f'Listing batches with params: {params}')
        response = client.list_batch(**params)

        batches: List[Dict[str, Any]] = []
        for item in response.get('items', []):
            batch_info: Dict[str, Any] = {
                'id': item.get('id'),
                'arn': item.get('arn'),
                'name': item.get('name'),
                'status': item.get('status'),
                'creationTime': datetime_to_iso(item.get('creationTime')),
                'startTime': datetime_to_iso(item.get('startTime')),
                'stopTime': datetime_to_iso(item.get('stopTime')),
            }
            batches.append(batch_info)

        result: Dict[str, Any] = {'batches': batches}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing batches')


async def list_runs_in_batch(
    ctx: Context,
    batch_id: str = Field(..., description='ID of the batch'),
    submission_status: Optional[str] = Field(None, description='Filter by submission status'),
    run_setting_id: Optional[str] = Field(None, description='Filter by run setting ID'),
    run_id: Optional[str] = Field(None, description='Filter by run ID'),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None, description='Token for pagination from a previous response'
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List runs within a HealthOmics batch.

    Args:
        ctx: MCP context for error reporting
        batch_id: ID of the batch
        submission_status: Optional filter by submission status
        run_setting_id: Optional filter by run setting ID
        run_id: Optional filter by run ID
        max_results: Maximum number of results to return
        next_token: Token for pagination from a previous response
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing run details and next token if available, or error dict
    """
    try:
        # Validate submission_status filter
        if submission_status is not None and submission_status not in SUBMISSION_STATUSES:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_INVALID_SUBMISSION_STATUS.format(', '.join(SUBMISSION_STATUSES))),
                'Invalid parameters',
            )

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {
            'id': batch_id,
            'maxResults': max_results,
        }

        if submission_status is not None:
            params['submissionStatus'] = submission_status

        if run_setting_id is not None:
            params['runSettingId'] = run_setting_id

        if run_id is not None:
            params['runId'] = run_id

        if next_token is not None:
            params['startingToken'] = next_token

        logger.info(f'Listing runs in batch {batch_id} with params: {params}')
        response = client.list_runs_in_batch(**params)

        runs: List[Dict[str, Any]] = []
        for item in response.get('items', []):
            run_info: Dict[str, Any] = {
                'runSettingId': item.get('runSettingId'),
                'submissionStatus': item.get('submissionStatus'),
            }
            # Include optional fields if present
            if item.get('runId'):
                run_info['runId'] = item.get('runId')
            if item.get('runArn'):
                run_info['runArn'] = item.get('runArn')
            if item.get('submissionFailureReason'):
                run_info['submissionFailureReason'] = item.get('submissionFailureReason')
            if item.get('submissionFailureMessage'):
                run_info['submissionFailureMessage'] = item.get('submissionFailureMessage')
            runs.append(run_info)

        result: Dict[str, Any] = {'runs': runs}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error listing runs in batch {batch_id}')


async def cancel_run_batch(
    ctx: Context,
    batch_id: str = Field(..., description='ID of the batch to cancel'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Cancel all runs in a HealthOmics batch.

    Args:
        ctx: MCP context for error reporting
        batch_id: ID of the batch to cancel
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing batchId and status, or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Cancelling run batch: {batch_id}')
        client.cancel_run_batch(id=batch_id)

        return {
            'batchId': batch_id,
            'status': 'cancelling',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error cancelling run batch {batch_id}')


async def delete_run_batch(
    ctx: Context,
    batch_id: str = Field(..., description='ID of the batch whose runs to delete'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Delete all runs in a HealthOmics batch.

    Args:
        ctx: MCP context for error reporting
        batch_id: ID of the batch whose runs to delete
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing batchId and status, or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Deleting runs in batch: {batch_id}')
        client.delete_run_batch(id=batch_id)

        return {
            'batchId': batch_id,
            'status': 'deleting',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error deleting runs in batch {batch_id}')


async def delete_batch(
    ctx: Context,
    batch_id: str = Field(..., description='ID of the batch to delete'),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Delete a HealthOmics batch metadata (does not delete runs).

    Args:
        ctx: MCP context for error reporting
        batch_id: ID of the batch to delete
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing batchId and status, or error dict
    """
    try:
        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        logger.info(f'Deleting batch: {batch_id}')
        client.delete_batch(id=batch_id)

        return {
            'batchId': batch_id,
            'status': 'deleted',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, f'Error deleting batch {batch_id}')
