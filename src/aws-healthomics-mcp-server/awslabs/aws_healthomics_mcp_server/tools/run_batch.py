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
    DEFAULT_SCRATCH_STORAGE_MODE,
    ERROR_CONFIGURATION_NAME_REQUIRES_VPC_MODE,
    ERROR_INVALID_BATCH_RUN_SETTINGS,
    ERROR_INVALID_BATCH_STATUS,
    ERROR_INVALID_NETWORKING_MODE,
    ERROR_INVALID_RUN_LOG_LEVEL,
    ERROR_INVALID_SCRATCH_STORAGE_MODE,
    ERROR_INVALID_SUBMISSION_STATUS,
    ERROR_INVALID_WORKFLOW_TYPE,
    ERROR_VPC_MODE_REQUIRES_CONFIGURATION_NAME,
    GET_WORKFLOW_TYPES,
    NETWORKING_MODE_VPC,
    NETWORKING_MODES,
    RUN_LOG_LEVELS,
    SCRATCH_STORAGE_MODES,
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
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    normalize_session_policy,
)
from loguru import logger
from mcp.server.mcpserver import Context
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


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


def _validate_networking(
    networking_mode: Optional[str], configuration_name: Optional[str]
) -> Optional[str]:
    """Validate the networking mode and configuration name pairing for a batch.

    Args:
        networking_mode: The requested networking mode (RESTRICTED or VPC), or None
        configuration_name: The requested configuration name, or None

    Returns:
        Error message if validation fails, None if valid
    """
    if networking_mode is not None and networking_mode not in NETWORKING_MODES:
        return ERROR_INVALID_NETWORKING_MODE.format(NETWORKING_MODES)
    if networking_mode == NETWORKING_MODE_VPC and not configuration_name:
        return ERROR_VPC_MODE_REQUIRES_CONFIGURATION_NAME
    if networking_mode != NETWORKING_MODE_VPC and configuration_name is not None:
        return ERROR_CONFIGURATION_NAME_REQUIRES_VPC_MODE
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
    workflow_type: Optional[str] = Field(
        None,
        description=(
            'Workflow type: PRIVATE (a workflow in your account or shared with you) or '
            'READY2RUN (a HealthOmics Ready2Run workflow). This is not the workflow language.'
        ),
    ),
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
    scratch_storage_mode: Optional[str] = Field(
        None,
        description=(
            'Scratch storage mode applied to all runs in the batch. Allowed values: '
            'LOCAL (mount local EBS ephemeral scratch storage at /tmp for CPU tasks) or '
            'SHARED (use shared scratch storage). '
            'Defaults to LOCAL when omitted (the MCP server default; note the HealthOmics '
            'API default is SHARED).'
        ),
    ),
    networking_mode: Optional[str] = Field(
        None,
        description=(
            'Networking mode applied to all runs in the batch: RESTRICTED (the HealthOmics '
            'default) or VPC. VPC requires configuration_name.'
        ),
    ),
    configuration_name: Optional[str] = Field(
        None,
        description=(
            'Name of the HealthOmics configuration that supplies the VPC settings '
            '(required when networking_mode is VPC, not allowed otherwise)'
        ),
    ),
    log_level: Optional[str] = Field(
        None,
        description=(
            'Log level applied to all runs in the batch. Allowed values: OFF, FATAL, ERROR, '
            'ALL. When omitted, the HealthOmics API default applies.'
        ),
    ),
    engine_settings: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            'Workflow engine settings applied to all runs in the batch, for example '
            'Nextflow profiles. Passed through to the API as a JSON document.'
        ),
    ),
    workflow_owner_id: Optional[str] = Field(
        None,
        description=(
            '12-digit AWS account ID of the workflow owner, for running a workflow that '
            'another account shared with you'
        ),
    ),
    output_bucket_owner_id: Optional[str] = Field(
        None,
        description=(
            '12-digit AWS account ID of the expected owner of the output S3 bucket, for '
            'writing outputs to a bucket in another account'
        ),
    ),
    priority: Optional[int] = Field(
        None,
        description='Priority applied to all runs in the batch (0 to 100000)',
        ge=0,
        le=100000,
    ),
    run_name: Optional[str] = Field(
        None,
        description=(
            'Default name for the runs in the batch. A per-run name in batch_run_settings '
            'overrides it.'
        ),
    ),
    run_tags: Optional[Dict[str, str]] = Field(
        None,
        description=(
            'Tags applied to each run in the batch. These are separate from tags, which '
            'only tag the batch resource and are not inherited by its runs.'
        ),
    ),
    request_id: Optional[str] = Field(None, description='Idempotency token'),
    tags: Optional[Dict[str, str]] = Field(
        None,
        description=(
            'Tags for the batch resource only. They are not applied to the runs in the '
            'batch; use run_tags to tag the runs.'
        ),
    ),
    session_policy: Optional[Union[str, Dict[str, Any]]] = Field(
        None,
        description=(
            'Optional inline IAM session policy (JSON string or object, max 2048 characters) '
            'applied to all runs in the batch to scope down the permissions of role_arn. '
            'The effective permissions are the intersection of the role policy and the '
            'session policy.'
        ),
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
    """Start a new HealthOmics run batch.

    Run batches do not support an output path layout option (outputUriPrefixMode).
    Batch runs always use the HealthOmics default layout, output_uri/<runId>/out/.
    To write outputs directly under an output URI, start individual runs with
    StartAHORun and output_uri_prefix_mode instead.

    Settings passed here form the batch's defaultRunSetting and apply to every run.
    Per-run entries in batch_run_settings can override only name, outputUri, priority,
    parameters, outputBucketOwnerId, runTags and engineSettings; all other settings,
    including networking and log level, apply uniformly to the whole batch.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow to run
        role_arn: IAM role ARN for the batch runs
        output_uri: S3 URI for output files
        batch_run_settings: Batch run settings with inlineSettings or s3UriSettings
        batch_name: Optional name for the batch
        workflow_type: Optional workflow type (PRIVATE or READY2RUN)
        workflow_version_name: Optional version name of the workflow
        parameters: Optional default parameters for all runs
        storage_type: Optional storage type (STATIC or DYNAMIC)
        storage_capacity: Optional storage capacity in GB
        run_group_id: Optional run group ID
        cache_id: Optional run cache ID
        cache_behavior: Optional cache behavior
        retention_mode: Optional retention mode
        scratch_storage_mode: Optional scratch storage mode (LOCAL or SHARED); defaults to LOCAL
        networking_mode: Optional networking mode (RESTRICTED or VPC) for all runs
        configuration_name: Optional configuration name (required when networking_mode is VPC)
        log_level: Optional log level for all runs (OFF, FATAL, ERROR, or ALL)
        engine_settings: Optional workflow engine settings, such as Nextflow profiles
        workflow_owner_id: Optional account ID of the workflow owner (shared workflows)
        output_bucket_owner_id: Optional account ID of the output bucket owner
        priority: Optional run priority (0 to 100000)
        run_name: Optional default name for the runs in the batch
        run_tags: Optional tags applied to each run in the batch
        request_id: Optional idempotency token
        tags: Optional tags for the batch resource (not inherited by its runs)
        session_policy: Optional inline IAM session policy (JSON string or dict) applied
            to all runs in the batch
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

        # Resolve and validate scratch storage mode before any API call
        effective_scratch_storage_mode = (
            scratch_storage_mode
            if scratch_storage_mode is not None
            else DEFAULT_SCRATCH_STORAGE_MODE
        )
        if effective_scratch_storage_mode not in SCRATCH_STORAGE_MODES:
            return await handle_tool_error(
                ctx,
                ValueError(
                    ERROR_INVALID_SCRATCH_STORAGE_MODE.format(
                        effective_scratch_storage_mode, SCRATCH_STORAGE_MODES
                    )
                ),
                'Invalid scratch storage mode',
            )

        if workflow_type is not None and workflow_type not in GET_WORKFLOW_TYPES:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_INVALID_WORKFLOW_TYPE.format(GET_WORKFLOW_TYPES)),
                'Invalid workflow type',
            )

        networking_error = _validate_networking(networking_mode, configuration_name)
        if networking_error:
            return await handle_tool_error(
                ctx, ValueError(networking_error), 'Invalid networking configuration'
            )

        if log_level is not None and log_level not in RUN_LOG_LEVELS:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_INVALID_RUN_LOG_LEVEL.format(RUN_LOG_LEVELS)),
                'Invalid log level',
            )

        # Validate and serialize the session policy before any API call
        try:
            effective_session_policy = normalize_session_policy(session_policy)
        except ValueError as e:
            return await handle_tool_error(ctx, e, 'Invalid session policy')

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        # Build defaultRunSetting
        default_run_setting: Dict[str, Any] = {
            'workflowId': workflow_id,
            'roleArn': role_arn,
            'outputUri': output_uri,
        }

        optional_settings = {
            'workflowType': workflow_type,
            'workflowVersionName': workflow_version_name,
            'parameters': parameters,
            'storageType': storage_type,
            'storageCapacity': storage_capacity,
            'runGroupId': run_group_id,
            'cacheId': cache_id,
            'cacheBehavior': cache_behavior,
            'retentionMode': retention_mode,
            'sessionPolicy': effective_session_policy,
            'networkingMode': networking_mode,
            'configurationName': configuration_name,
            'logLevel': log_level,
            'engineSettings': engine_settings,
            'workflowOwnerId': workflow_owner_id,
            'outputBucketOwnerId': output_bucket_owner_id,
            'priority': priority,
            'name': run_name,
            'runTags': run_tags,
        }
        default_run_setting.update({k: v for k, v in optional_settings.items() if v is not None})

        # Always inject the effective scratch storage mode so all runs in the batch
        # use the MCP server default (LOCAL) unless the caller overrides it.
        default_run_setting['scratchStorageMode'] = effective_scratch_storage_mode

        # Build API params
        params: Dict[str, Any] = {
            'defaultRunSetting': default_run_setting,
            'batchRunSettings': batch_run_settings,
        }

        if batch_name is not None:
            params['batchName'] = batch_name

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
