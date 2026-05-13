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

"""Shared tool-result builders and utility functions."""

import httpx
import json
import os
from typing import Any, Dict, Optional


# ── MCP tool annotations ─────────────────────────────────────────────────

READ_ONLY: Dict[str, bool] = {
    'readOnlyHint': True,
    'destructiveHint': False,
    'idempotentHint': True,
}

CREATE: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': False,
    'idempotentHint': True,
}

MUTATE: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': False,
    'idempotentHint': False,
}

DELETE: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': True,
    'idempotentHint': False,
}

DELETE_IDEMPOTENT: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': True,
    'idempotentHint': True,
}

SUBMIT: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': True,
    'idempotentHint': False,
}

SUBMIT_IDEMPOTENT: Dict[str, bool] = {
    'readOnlyHint': False,
    'destructiveHint': True,
    'idempotentHint': True,
}


# ── Job response trimming ─────────────────────────────────────────────

_JOB_FIELDS = ('jobId', 'jobName', 'statusDetails', 'workspaceId', 'restartable')


def format_job_response(response: object) -> object:
    """Extract essential fields from a GetJob response or a ListJobEntry."""
    if not isinstance(response, dict):
        return response
    job = response.get('job', response.get('jobInfo', response))
    if not isinstance(job, dict):
        return job
    return {k: job[k] for k in _JOB_FIELDS if k in job}


_TASK_LIST_FIELDS = (
    'taskId',
    'title',
    'description',
    'status',
    'severity',
    'category',
    'uxComponentId',
    'createdAt',
    '_responseHint',
)


def format_task_summary(task: object) -> object:
    """Extract essential fields from a HitlTask for list browsing."""
    if not isinstance(task, dict):
        return task
    summary = {k: task[k] for k in _TASK_LIST_FIELDS if k in task}
    if task.get('category') == 'TOOL_APPROVAL':
        summary['_responseHint'] = (
            'TOOL_APPROVAL task — agent is requesting permission to execute a tool. '
            'Use get_resource to see the agent artifact, then call '
            'complete_task with action=APPROVE or REJECT. '
            'Do NOT provide content or filePath.'
        )
    return summary


_WORKLOG_FIELDS = ('description', 'timestamp', 'worklogType')


def format_worklog(worklog: object) -> object:
    """Extract essential fields from a Worklog."""
    if not isinstance(worklog, dict):
        return worklog
    return {k: worklog[k] for k in _WORKLOG_FIELDS if k in worklog}


_CONNECTOR_LIST_FIELDS = ('connectorId', 'connectorName', 'connectorType', 'accountConnection')


def format_connector_summary(connector: object) -> object:
    """Extract essential fields from a Connector for list browsing."""
    if not isinstance(connector, dict):
        return connector
    return {k: connector[k] for k in _CONNECTOR_LIST_FIELDS if k in connector}


_MESSAGE_LIST_FIELDS = (
    'messageId',
    'text',
    'messageOrigin',
    'createdAt',
    'parentMessageId',
    'processingInfo',
    'interactions',
)


def format_message_summary(message: object) -> object:
    """Extract essential fields from a Message for list browsing."""
    if not isinstance(message, dict):
        return message
    return {k: message[k] for k in _MESSAGE_LIST_FIELDS if k in message}


# ── Result builders ──────────────────────────────────────────────────────


def text_result(payload: Any, is_error: bool = False) -> Dict[str, Any]:
    """Build an MCP-compatible text result envelope."""
    return {
        'content': [{'type': 'text', 'text': json.dumps(payload, default=str)}],
        'isError': is_error,
    }


def success_result(data: Any) -> Dict[str, Any]:
    """Wrap *data* in a ``{success: true, data: ...}`` envelope."""
    return text_result({'success': True, 'data': data}, is_error=False)


def error_result(
    code: str,
    message: str,
    suggested_action: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a structured error result."""
    error_obj: Dict[str, Any] = {'code': code, 'message': message}
    if suggested_action is not None:
        error_obj['suggestedAction'] = suggested_action
    return text_result({'success': False, 'error': error_obj}, is_error=True)


def failure_result(error: Exception, hint: Optional[str] = None) -> Dict[str, Any]:
    """Extract details from an exception and return a structured failure.

    If *error* carries ``status_code`` and ``body`` attributes (e.g. an HttpError),
    those are included in the response.
    """
    from awslabs.aws_transform_mcp_server.transform_api_client import (
        AuthConflict,
        ProfileSelectionRequired,
    )

    if isinstance(error, AuthConflict):
        return text_result(
            {
                'success': False,
                'error': {
                    'code': 'AUTH_CONFLICT',
                    'message': (
                        f'{error.failed_method.upper()} auth failed: {error.original_error}. '
                        f'Alternative auth methods are available.'
                    ),
                    'suggestedAction': (
                        'Run configure(authMode="reset") to clear the stale session and '
                        'switch to AWS credential auth, or configure(authMode="sso") to '
                        're-authenticate with IAM Identity Center.'
                    ),
                },
                'failedMethod': error.failed_method,
                'availableMethods': error.available_methods,
            },
            is_error=True,
        )

    if isinstance(error, ProfileSelectionRequired):
        from awslabs.aws_transform_mcp_server.config_store import derive_transform_api_endpoint

        return text_result(
            {
                'success': False,
                'error': {
                    'code': 'PROFILE_SELECTION_REQUIRED',
                    'message': 'Multiple regions available. Please choose one.',
                    'suggestedAction': ('Call switch_profile to select a region.'),
                },
                'availableRegions': [
                    {'region': r, 'endpoint': derive_transform_api_endpoint(r)}
                    for r in error.regions
                ],
            },
            is_error=True,
        )

    msg = str(error)
    error_obj: Dict[str, Any] = {'code': 'REQUEST_FAILED', 'message': msg}
    status = getattr(error, 'status_code', None)
    body = getattr(error, 'body', None)
    if status is not None:
        error_obj['httpStatus'] = status
    if body is not None:
        error_obj['details'] = body
    result: Dict[str, Any] = {'success': False, 'error': error_obj}
    if hint is not None:
        result['hint'] = hint
    return text_result(result, is_error=True)


# ── S3 download helper ───────────────────────────────────────────────────


async def download_s3_content(
    s3_url: str,
    save_path: Optional[str] = None,
    file_name: Optional[str] = None,
    default_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Download content from a pre-signed S3 URL.

    If *save_path* is provided the raw bytes are written to disk and the
    function returns ``{"savedTo": ..., "sizeBytes": ...}``.  Otherwise the
    content is returned as ``{"content": ...}``.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(s3_url, follow_redirects=True)
        response.raise_for_status()

        if save_path is not None:
            resolved_name = file_name or default_name or 'download'
            if save_path.endswith('/') or '.' not in os.path.basename(save_path):
                full_path = os.path.join(save_path, resolved_name)
            else:
                full_path = save_path
            with open(full_path, 'wb') as fh:
                fh.write(response.content)
            return {'savedTo': full_path, 'sizeBytes': len(response.content)}

        return {'content': response.text}
