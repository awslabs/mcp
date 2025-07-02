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

"""Troubleshooting tools for the AWS HealthOmics MCP server."""

import botocore
import botocore.exceptions
import os
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_REGION
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    get_run_engine_logs_internal,
    get_run_manifest_logs_internal,
    get_task_logs_internal,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from datetime import datetime, timedelta
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict


def safe_datetime_to_iso(dt_obj):
    """Safely convert datetime object to ISO format string."""
    if dt_obj is None:
        return None
    if hasattr(dt_obj, 'isoformat'):
        return dt_obj.isoformat()
    # If it's already a string, return as-is
    if isinstance(dt_obj, str):
        return dt_obj
    # For any other type, convert to string
    return str(dt_obj)


def calculate_log_time_window(start_time, end_time, buffer_minutes=5):
    """Calculate time window for log retrieval with buffer around start and end times.

    Args:
        start_time: Start datetime (can be datetime object or string)
        end_time: End datetime (can be datetime object or string)
        buffer_minutes: Minutes to add before start and after end (default: 5)

    Returns:
        Tuple of (start_time_iso, end_time_iso) strings or (None, None) if inputs invalid
    """
    try:
        # Convert to datetime objects if they're strings
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        elif hasattr(start_time, 'replace'):  # datetime object
            start_dt = start_time
        else:
            return None, None

        if isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        elif hasattr(end_time, 'replace'):  # datetime object
            end_dt = end_time
        else:
            return None, None

        # Add buffer time
        buffer_delta = timedelta(minutes=buffer_minutes)
        log_start = start_dt - buffer_delta
        log_end = end_dt + buffer_delta

        # Convert back to ISO format strings
        return log_start.isoformat(), log_end.isoformat()

    except Exception as e:
        logger.warning(f'Failed to calculate log time window: {str(e)}')
        return None, None


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


async def diagnose_run_failure(
    ctx: Context,
    run_id: str = Field(
        ...,
        description='ID of the failed run',
    ),
) -> Dict[str, Any]:
    """Provides comprehensive diagnostic information for a failed workflow run.

    This function collects multiple sources of diagnostic information including:
    - Run details and failure reason
    - Engine logs from CloudWatch
    - Run manifest logs containing workflow summary and resource metrics
    - Task logs from all failed tasks
    - Actionable recommendations for troubleshooting

    Args:
        ctx: MCP context for error reporting
        run_id: ID of the failed run

    Returns:
        Dictionary containing comprehensive diagnostic information including:
        - runId: The run identifier
        - status: Current run status
        - failureReason: AWS-provided failure reason
        - runUuid: Run UUID for log stream identification
        - engineLogs: Engine execution logs
        - manifestLogs: Run manifest logs with workflow summary
        - failedTasks: List of failed tasks with their logs
        - recommendations: Troubleshooting recommendations
    """
    try:
        omics_client = get_omics_client()

        # Get run details
        run_response = omics_client.get_run(id=run_id)

        # Check if the run actually failed
        if run_response.get('status') != 'FAILED':
            return {
                'status': run_response.get('status'),
                'message': f'Run is not in FAILED state. Current status: {run_response.get("status")}',
            }

        # Extract run details
        failure_reason = run_response.get('failureReason', 'No failure reason provided')
        run_uuid = run_response.get('uuid')

        logger.info(f'Diagnosing failed run {run_id} with UUID {run_uuid}')

        # Calculate time window for log retrieval (5 minutes before creation to 5 minutes after stop)
        creation_time = run_response.get('creationTime')
        stop_time = run_response.get('stopTime')
        log_start_time, log_end_time = calculate_log_time_window(creation_time, stop_time)

        if log_start_time and log_end_time:
            logger.info(f'Using log time window: {log_start_time} to {log_end_time}')
        else:
            logger.warning(
                'Could not calculate log time window, retrieving logs without time filter'
            )

        # Get engine logs using the workflow_analysis function
        engine_logs = []
        try:
            engine_logs_response = await get_run_engine_logs_internal(
                run_id=run_id,
                start_time=log_start_time,
                end_time=log_end_time,
                limit=100,
                start_from_head=False,  # Get the most recent logs
            )

            # Extract just the messages for backward compatibility
            engine_logs = [
                event.get('message', '') for event in engine_logs_response.get('events', [])
            ]
            logger.info(f'Retrieved {len(engine_logs)} engine log entries')
        except Exception as e:
            error_message = f'Error retrieving engine logs: {str(e)}'
            logger.error(error_message)
            engine_logs = [error_message]

        # Get run manifest logs if UUID is available
        manifest_logs = []
        if run_uuid:
            try:
                manifest_logs_response = await get_run_manifest_logs_internal(
                    run_id=run_id,
                    run_uuid=run_uuid,
                    start_time=log_start_time,
                    end_time=log_end_time,
                    limit=100,
                    start_from_head=False,  # Get the most recent logs
                )

                # Extract just the messages for backward compatibility
                manifest_logs = [
                    event.get('message', '') for event in manifest_logs_response.get('events', [])
                ]
                logger.info(f'Retrieved {len(manifest_logs)} manifest log entries')
            except Exception as e:
                error_message = f'Error retrieving manifest logs: {str(e)}'
                logger.error(error_message)
                manifest_logs = [error_message]
        else:
            logger.warning(f'No UUID available for run {run_id}, skipping manifest logs')
            manifest_logs = ['No run UUID available - manifest logs cannot be retrieved']

        # Get all failed tasks (not just the first 10)
        failed_tasks = []
        next_token = None

        while True:
            list_tasks_params = {
                'id': run_id,
                'status': 'FAILED',
                'maxResults': 100,  # Get more tasks per request
            }
            if next_token:
                list_tasks_params['startingToken'] = next_token

            tasks_response = omics_client.list_run_tasks(**list_tasks_params)

            for task in tasks_response.get('items', []):
                task_id = task.get('taskId')
                task_name = task.get('name')
                task_status_message = task.get('statusMessage', 'No status message')

                if not task_id:
                    logger.warning(f'Skipping task with missing taskId: {task_name}')
                    continue

                logger.info(f'Processing failed task {task_id} ({task_name})')

                # Calculate task-specific time window if possible, otherwise use run time window
                task_start_time = log_start_time
                task_end_time = log_end_time

                # Try to get more detailed task information for better time scoping
                try:
                    task_details = omics_client.get_run_task(id=run_id, taskId=task_id)
                    task_creation_time = task_details.get('creationTime')
                    task_stop_time = task_details.get('stopTime')

                    if task_creation_time and task_stop_time:
                        task_start_time, task_end_time = calculate_log_time_window(
                            task_creation_time, task_stop_time
                        )
                        logger.info(
                            f'Using task-specific time window for {task_id}: {task_start_time} to {task_end_time}'
                        )
                except Exception as e:
                    logger.debug(
                        f'Could not get detailed task timing for {task_id}, using run time window: {str(e)}'
                    )

                # Get task logs using the workflow_analysis function
                task_logs = []
                try:
                    task_logs_response = await get_task_logs_internal(
                        run_id=run_id,
                        task_id=task_id,
                        start_time=task_start_time,
                        end_time=task_end_time,
                        limit=100,  # Get more logs per task
                        start_from_head=False,  # Get the most recent logs
                    )

                    # Extract just the messages for backward compatibility
                    task_logs = [
                        event.get('message', '') for event in task_logs_response.get('events', [])
                    ]
                    logger.info(f'Retrieved {len(task_logs)} log entries for task {task_id}')
                except Exception as e:
                    error_message = f'Error retrieving task logs for {task_id}: {str(e)}'
                    logger.error(error_message)
                    task_logs = [error_message]

                failed_tasks.append(
                    {
                        'taskId': task_id,
                        'name': task_name,
                        'statusMessage': task_status_message,
                        'logs': task_logs,
                        'logCount': len(task_logs),
                    }
                )

            # Check if there are more tasks to retrieve
            next_token = tasks_response.get('nextToken')
            if not next_token:
                break

        logger.info(f'Found {len(failed_tasks)} failed tasks for run {run_id}')

        # Enhanced recommendations based on common failure patterns
        recommendations = [
            'Check IAM role permissions for S3 access and CloudWatch Logs',
            'Verify container images are accessible from the HealthOmics service',
            "Ensure input files exist and are accessible by the run's IAM role",
            'Check for syntax errors in workflow definition',
            'Verify parameter values match the expected types and formats',
            'Review manifest logs for resource allocation and utilization issues',
            'Check task logs for application-specific error messages',
            "Verify that output S3 locations are writable by the run's IAM role",
            'Consider increasing resource allocations if tasks failed due to memory/CPU limits',
            'Check for network connectivity issues if tasks failed during data transfer',
        ]

        # Helper function to safely convert datetime objects to ISO format
        def safe_datetime_to_iso(dt_obj):
            """Safely convert datetime object to ISO format string."""
            if dt_obj is None:
                return None
            if hasattr(dt_obj, 'isoformat'):
                return dt_obj.isoformat()
            # If it's already a string, return as-is
            if isinstance(dt_obj, str):
                return dt_obj
            # For any other type, convert to string
            return str(dt_obj)

        # Compile comprehensive diagnostic information
        diagnosis = {
            'runId': run_id,
            'runUuid': run_uuid,
            'status': run_response.get('status'),
            'failureReason': failure_reason,
            'creationTime': safe_datetime_to_iso(run_response.get('creationTime')),
            'startTime': safe_datetime_to_iso(run_response.get('startTime')),
            'stopTime': safe_datetime_to_iso(run_response.get('stopTime')),
            'workflowId': run_response.get('workflowId'),
            'workflowType': run_response.get('workflowType'),
            'engineLogs': engine_logs,
            'engineLogCount': len(engine_logs),
            'manifestLogs': manifest_logs,
            'manifestLogCount': len(manifest_logs),
            'failedTasks': failed_tasks,
            'failedTaskCount': len(failed_tasks),
            'recommendations': recommendations,
            'summary': {
                'totalFailedTasks': len(failed_tasks),
                'hasManifestLogs': bool(
                    run_uuid
                    and len(manifest_logs) > 0
                    and 'Error retrieving manifest logs' not in str(manifest_logs)
                ),
                'hasEngineLogs': len(engine_logs) > 0
                and 'Error retrieving engine logs' not in str(engine_logs),
            },
        }

        logger.info(
            f'Diagnosis complete for run {run_id}: {len(failed_tasks)} failed tasks, {len(engine_logs)} engine logs, {len(manifest_logs)} manifest logs'
        )
        return diagnosis

    except botocore.exceptions.ClientError as e:
        error_message = f'AWS error diagnosing run failure for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error diagnosing run failure for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
    except Exception as e:
        error_message = f'Unexpected error diagnosing run failure for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
