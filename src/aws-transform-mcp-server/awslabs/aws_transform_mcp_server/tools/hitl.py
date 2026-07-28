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


import httpx
import json
import os
import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.file_validation import validate_read_path
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.hitl_schemas import format_and_validate
from awslabs.aws_transform_mcp_server.tool_utils import (
    SUBMIT,
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    CreateArtifactDownloadUrlRequest,
    GetHitlTaskRequest,
    HitlTaskArtifact,
    SubmitCriticalHitlTaskRequest,
    SubmitStandardHitlTaskRequest,
    UpdateHitlTaskRequest,
)
from awslabs.aws_transform_mcp_server.upload_helper import (
    infer_file_type,
    upload_file_artifact,
    upload_json_artifact,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import BeforeValidator, Field
from typing import Annotated, Any, Dict, Optional


_NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
_NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
_NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'


def _coerce_to_json_string(value: Any) -> Any:
    """Accept dict/list from lenient MCP hosts; serialize to JSON string.

    Some MCP hosts (e.g. Kiro) auto-parse string arguments that look like JSON
    into objects before the JSON-RPC request is built. The advertised schema
    for `content` is `string` (matching the TS server), so we coerce non-string
    values back to a JSON string before Pydantic validates the type.
    """
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value)


JsonContent = Annotated[Optional[str], BeforeValidator(_coerce_to_json_string)]


# Max artifact size (bytes) to return inline. Larger artifacts are skipped.
_ARTIFACT_INLINE_MAX_BYTES = 100_000  # 100 KB


async def download_agent_artifact(
    workspace_id: str,
    job_id: str,
    artifact_id: str,
) -> Dict[str, Any]:
    """Download the agent artifact content as a parsed JSON object.

    Returns a dict with optional keys: content, rawText, warning, sizeBytes.
    For artifacts exceeding the inline size threshold, the content is NOT
    downloaded — only size metadata is returned so the caller can prompt the
    user to download via get_resource(resource="artifact", savePath=...).
    """
    try:
        url_result = await call_transform_api(
            'CreateArtifactDownloadUrl',
            CreateArtifactDownloadUrlRequest(
                workspaceId=workspace_id,
                jobId=job_id,
                artifactId=artifact_id,
            ),
        )
        s3_url = url_result['s3PreSignedUrl']

        async with httpx.AsyncClient() as client:
            # Stream GET to check Content-Length before reading body
            async with client.stream('GET', s3_url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    return {
                        'warning': (
                            f'Agent artifact download failed (HTTP {resp.status_code}). '
                            'Field validation skipped.'
                        )
                    }

                content_length = (
                    int(resp.headers['content-length'])
                    if 'content-length' in resp.headers
                    else None
                )
                logger.info(
                    f'Agent artifact stream: status={resp.status_code}, '
                    f'content-length={content_length}'
                )

                if content_length is not None and content_length > _ARTIFACT_INLINE_MAX_BYTES:
                    size_mb = content_length / (1024 * 1024)
                    return {
                        'sizeBytes': content_length,
                        'warning': (
                            f'Agent artifact is large ({size_mb:.1f} MB). '
                            'Content not included inline to avoid context overflow. '
                            'Ask the user for a local file path to save the artifact, '
                            'then call get_resource with resource="artifact", '
                            f'workspaceId="{workspace_id}", jobId="{job_id}", '
                            f'artifactId="{artifact_id}", and savePath set to '
                            'the path they provide.'
                        ),
                    }

                # Small artifact — read inline
                text = (await resp.aread()).decode()

            try:
                return {'content': json.loads(text), 'rawText': text}
            except (ValueError, TypeError):
                return {
                    'rawText': text,
                    'warning': 'Agent artifact is not JSON. Field validation skipped.',
                }
    except Exception as err:
        msg = str(err)
        return {'warning': f'Agent artifact download failed: {msg}. Field validation skipped.'}


class HitlHandler:
    """Registers HITL-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register HITL tools on the MCP server."""
        audited_tool(mcp, 'complete_task', title='Complete HITL Task', annotations=SUBMIT)(
            self.complete_task
        )

    async def complete_task(
        self,
        ctx: Context,
        workspaceId: Annotated[str, Field(description='The workspace identifier')],
        jobId: Annotated[str, Field(description='The job identifier')],
        taskId: Annotated[str, Field(description='The task identifier')],
        content: Annotated[
            JsonContent,
            Field(
                description=(
                    "JSON response data matching the component's _responseTemplate. "
                    'Omit for display-only components (server auto-submits {}). '
                    'For file upload tasks: omit this and use filePath instead.'
                ),
            ),
        ] = None,
        filePath: Annotated[
            Optional[str],
            Field(
                description=(
                    'Local file path to upload as an artifact before submitting. '
                    'The server uploads the file and returns the artifactId in the result.'
                ),
            ),
        ] = None,
        fileType: Annotated[
            Optional[str],
            Field(
                description='File type (default: auto-detected from extension)',
            ),
        ] = None,
        action: Annotated[
            str,
            Field(
                description=(
                    'APPROVE (default): submit and approve. '
                    'REJECT: submit and reject. '
                    'SEND_FOR_APPROVAL: CRITICAL tasks -- send to admin for review. '
                    'SAVE_DRAFT: save progress without submitting. '
                    'For TOOL_APPROVAL tasks, only APPROVE and REJECT are valid.'
                ),
            ),
        ] = 'APPROVE',
    ) -> Dict[str, Any]:
        """Complete a Human-in-the-Loop (HITL) task.

        ⚠️ REQUIRES EXPLICIT USER CONFIRMATION. Before calling this tool you
        MUST present the full task details, agent artifact, and all available
        options to the user and wait for their explicit decision. If the task
        contains selectable options, list every option and ask the user which
        one to choose — do NOT reuse a previously selected value or guess.
        Never call this tool without the user's approval.

        8-step flow: fetch task, validate, upload file, download artifact,
        build content, validate+format, upload response, route to API.
        """
        if not is_fes_available():
            return error_result(_NOT_CONFIGURED_CODE, _NOT_CONFIGURED_MSG, _NOT_CONFIGURED_ACTION)

        nudge = job_needs_check(jobId)
        if nudge:
            return error_result(
                'INSTRUCTIONS_REQUIRED',
                nudge,
                f'Call load_instructions with workspaceId and jobId="{jobId}".',
            )

        try:
            # ── Step 1: Fetch the task ──────────────────────────────────
            task_result = await call_transform_api(
                'GetHitlTask',
                GetHitlTaskRequest(
                    workspaceId=workspaceId,
                    jobId=jobId,
                    taskId=taskId,
                ),
            )
            task = task_result['task']
            ux_component_id = task.get('uxComponentId')
            severity = task.get('severity')

            # ── Step 1b: Validate action against severity/category ──────
            category = task.get('category')
            is_tool_approval = category == 'TOOL_APPROVAL'

            if action == 'SEND_FOR_APPROVAL' and is_tool_approval:
                return error_result(
                    'VALIDATION_ERROR',
                    'SEND_FOR_APPROVAL is not supported for TOOL_APPROVAL tasks.',
                    'Use APPROVE or REJECT instead.',
                )
            if action == 'SAVE_DRAFT' and is_tool_approval:
                return error_result(
                    'VALIDATION_ERROR',
                    'SAVE_DRAFT is not supported for TOOL_APPROVAL tasks.',
                    'Use APPROVE or REJECT instead.',
                )
            if action == 'SEND_FOR_APPROVAL' and severity != 'CRITICAL':
                return error_result(
                    'VALIDATION_ERROR',
                    'SEND_FOR_APPROVAL is only valid for CRITICAL severity tasks.',
                    'Use APPROVE or REJECT for STANDARD tasks.',
                )

            uploaded_artifact_id: Optional[str] = None
            agent_artifact_content: Optional[Dict[str, Any]] = None
            artifact_warning: Optional[str] = None
            response_artifact_id: Optional[str] = None

            # ── TOOL_APPROVAL fast path ─────────────────────────────────
            # Backend rejects humanArtifact for TOOL_APPROVAL tasks, so
            # skip artifact upload/download/validation and submit directly.
            if is_tool_approval:
                task_status = task.get('status')
                if task_status != 'AWAITING_APPROVAL':
                    return error_result(
                        'WRONG_STATUS',
                        f'Task {taskId} is in status "{task_status}", not AWAITING_APPROVAL.',
                        'Only TOOL_APPROVAL tasks in AWAITING_APPROVAL status can be approved or denied.',
                    )
                await call_transform_api(
                    'SubmitCriticalHitlTask',
                    SubmitCriticalHitlTaskRequest(
                        workspaceId=workspaceId,
                        jobId=jobId,
                        taskId=taskId,
                        action=action,
                        idempotencyToken=str(uuid.uuid4()),
                    ),
                )
            else:
                # ── Step 2: Upload file if provided ─────────────────────
                if filePath:
                    if not os.path.exists(filePath):
                        return error_result(
                            'FILE_NOT_FOUND',
                            f'File not found: {filePath}',
                            'Check the file path and try again.',
                        )
                    validated_path = validate_read_path(filePath)
                    uploaded_artifact_id = await upload_file_artifact(
                        workspace_id=workspaceId,
                        job_id=jobId,
                        file_path=validated_path,
                        file_type=fileType or infer_file_type(validated_path),
                    )

                # ── Step 3: Download agent artifact for validation ──────
                agent_artifact = task.get('agentArtifact')
                if isinstance(agent_artifact, dict) and agent_artifact.get('artifactId'):
                    dl = await download_agent_artifact(
                        workspace_id=workspaceId,
                        job_id=jobId,
                        artifact_id=agent_artifact['artifactId'],
                    )
                    agent_artifact_content = dl.get('content')
                    artifact_warning = dl.get('warning')

                # ── Step 4: Build response content ──────────────────────
                response_content = content or '{}'

                # ── Step 5: Validate and format ─────────────────────────
                fmt_result = format_and_validate(
                    ux_component_id,
                    response_content,
                    agent_artifact_content,
                )
                if not fmt_result.ok:
                    return error_result('VALIDATION_ERROR', fmt_result.error)

                # ── Step 6: Upload response artifact ────────────────────
                has_content = bool(content or filePath)
                if action != 'SAVE_DRAFT' or has_content:
                    response_artifact_id = await upload_json_artifact(
                        workspace_id=workspaceId,
                        job_id=jobId,
                        content=fmt_result.content,
                    )

                # ── Step 7: Route to correct API based on action ────────
                if action == 'SAVE_DRAFT':
                    update_req = UpdateHitlTaskRequest(
                        workspaceId=workspaceId,
                        jobId=jobId,
                        taskId=taskId,
                        humanArtifact=(
                            HitlTaskArtifact(artifactId=response_artifact_id)
                            if response_artifact_id
                            else None
                        ),
                    )
                    await call_transform_api('UpdateHitlTask', update_req)

                elif action == 'SEND_FOR_APPROVAL':
                    await call_transform_api(
                        'UpdateHitlTask',
                        UpdateHitlTaskRequest(
                            workspaceId=workspaceId,
                            jobId=jobId,
                            taskId=taskId,
                            humanArtifact=HitlTaskArtifact(artifactId=response_artifact_id),
                            postUpdateAction='SEND_FOR_APPROVAL',
                        ),
                    )

                else:
                    # APPROVE or REJECT
                    if severity == 'CRITICAL':
                        await call_transform_api(
                            'SubmitCriticalHitlTask',
                            SubmitCriticalHitlTaskRequest(
                                workspaceId=workspaceId,
                                jobId=jobId,
                                taskId=taskId,
                                action=action,
                                humanArtifact=HitlTaskArtifact(artifactId=response_artifact_id),
                                idempotencyToken=str(uuid.uuid4()),
                            ),
                        )
                    else:
                        await call_transform_api(
                            'SubmitStandardHitlTask',
                            SubmitStandardHitlTaskRequest(
                                workspaceId=workspaceId,
                                jobId=jobId,
                                taskId=taskId,
                                action=action,
                                humanArtifact=HitlTaskArtifact(artifactId=response_artifact_id),
                                idempotencyToken=str(uuid.uuid4()),
                            ),
                        )

            updated_result = await call_transform_api(
                'GetHitlTask',
                GetHitlTaskRequest(
                    workspaceId=workspaceId,
                    jobId=jobId,
                    taskId=taskId,
                ),
            )
            task_data = updated_result.get('task', {}) if isinstance(updated_result, dict) else {}
            result_data: Dict[str, Any] = {
                'taskId': task_data.get('taskId', taskId),
                'status': task_data.get('status'),
                'action': task_data.get('action', action),
                'title': task_data.get('title'),
            }
            if uploaded_artifact_id:
                result_data['uploadedArtifactId'] = uploaded_artifact_id
            if artifact_warning:
                result_data['_warning'] = artifact_warning
            return success_result(result_data)

        except Exception as error:
            return failure_result(error)
