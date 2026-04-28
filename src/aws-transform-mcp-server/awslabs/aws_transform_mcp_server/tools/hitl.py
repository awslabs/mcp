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

"""HITL (Human-in-the-Loop) tool handler for AWS Transform MCP server.

Ported from tools/hitl.ts. Provides the complete_task tool with 8-step flow:
  1. Fetch task -> extract uxComponentId, severity
  2. Validate action against severity
  3. Upload file if provided
  4. Download agent artifact for validation
  5. Build response content
  6. Validate and format
  7. Upload response artifact
  8. Route to correct API based on action
"""

import httpx
import json
import os
import uuid
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.file_validation import validate_read_path
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_task, format_and_validate
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.upload_helper import (
    infer_file_type,
    upload_file_artifact,
    upload_json_artifact,
)
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


async def download_agent_artifact(
    workspace_id: str,
    job_id: str,
    artifact_id: str,
) -> Dict[str, Any]:
    """Download the agent artifact content as a parsed JSON object.

    Returns a dict with optional keys: content, rawText, warning.
    """
    try:
        url_result = await call_fes(
            'CreateArtifactDownloadUrl',
            {
                'workspaceId': workspace_id,
                'jobId': job_id,
                'artifactId': artifact_id,
            },
        )
        async with httpx.AsyncClient() as client:
            s3_response = await client.get(url_result['s3PreSignedUrl'], follow_redirects=True)
            if s3_response.status_code >= 400:
                return {
                    'warning': (
                        f'Agent artifact download failed (HTTP {s3_response.status_code}). '
                        'Field validation skipped.'
                    )
                }
            text = s3_response.text
            try:
                import json

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
        audited_tool(mcp, 'complete_task')(self.complete_task)

    async def complete_task(
        self,
        ctx: Context,
        workspaceId: str = Field(..., description='The workspace identifier'),
        jobId: str = Field(..., description='The job identifier'),
        taskId: str = Field(..., description='The task identifier'),
        content: JsonContent = Field(
            None,
            description=(
                "JSON response data matching the component's _responseTemplate. "
                'Omit for display-only components (server auto-submits {}). '
                'For file upload tasks: omit this and use filePath instead.'
            ),
        ),
        filePath: Optional[str] = Field(
            None,
            description=(
                'Local file path to upload as an artifact before submitting. '
                'The server uploads the file and returns the artifactId in the result.'
            ),
        ),
        fileType: Optional[str] = Field(
            None,
            description='File type (default: auto-detected from extension)',
        ),
        action: str = Field(
            'APPROVE',
            description=(
                'APPROVE (default): submit and approve. '
                'REJECT: submit and reject. '
                'SEND_FOR_APPROVAL: CRITICAL tasks -- send to admin for review. '
                'SAVE_DRAFT: save progress without submitting.'
            ),
        ),
    ) -> Dict[str, Any]:
        """Complete a Human-in-the-Loop (HITL) task.

        8-step flow: fetch task, validate, upload file, download artifact,
        build content, validate+format, upload response, route to API.
        """
        if not is_configured():
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
            task_result = await call_fes(
                'GetHitlTask',
                {
                    'workspaceId': workspaceId,
                    'jobId': jobId,
                    'taskId': taskId,
                },
            )
            task = task_result['task']
            ux_component_id = task.get('uxComponentId')
            severity = task.get('severity')

            # ── Step 1b: Validate action against severity/category ──────
            category = task.get('category')
            if action == 'SEND_FOR_APPROVAL' and category == 'TOOL_APPROVAL':
                return error_result(
                    'VALIDATION_ERROR',
                    'SEND_FOR_APPROVAL is not supported for TOOL_APPROVAL tasks.',
                    'Use APPROVE or REJECT instead.',
                )
            if action == 'SEND_FOR_APPROVAL' and severity != 'CRITICAL':
                return error_result(
                    'VALIDATION_ERROR',
                    'SEND_FOR_APPROVAL is only valid for CRITICAL severity tasks.',
                    'Use APPROVE or REJECT for STANDARD tasks.',
                )

            # ── Step 2: Upload file if provided ─────────────────────────
            uploaded_artifact_id: Optional[str] = None
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

            # ── Step 3: Download agent artifact for validation ──────────
            agent_artifact_content: Optional[Dict[str, Any]] = None
            artifact_warning: Optional[str] = None
            agent_artifact = task.get('agentArtifact')
            if isinstance(agent_artifact, dict) and agent_artifact.get('artifactId'):
                dl = await download_agent_artifact(
                    workspace_id=workspaceId,
                    job_id=jobId,
                    artifact_id=agent_artifact['artifactId'],
                )
                agent_artifact_content = dl.get('content')
                artifact_warning = dl.get('warning')

            # ── Step 4: Build response content ──────────────────────────
            response_content = content or '{}'

            # ── Step 5: Validate and format ─────────────────────────────
            fmt_result = format_and_validate(
                ux_component_id,
                response_content,
                agent_artifact_content,
            )
            if not fmt_result.ok:
                return error_result('VALIDATION_ERROR', fmt_result.error)

            # ── Step 6: Upload response artifact ────────────────────────
            has_content = bool(content or filePath)
            response_artifact_id: Optional[str] = None
            if action != 'SAVE_DRAFT' or has_content:
                response_artifact_id = await upload_json_artifact(
                    workspace_id=workspaceId,
                    job_id=jobId,
                    content=fmt_result.content,
                )

            # ── Step 7: Route to correct API based on action ────────────
            if action == 'SAVE_DRAFT':
                update_body: Dict[str, Any] = {
                    'workspaceId': workspaceId,
                    'jobId': jobId,
                    'taskId': taskId,
                }
                if response_artifact_id:
                    update_body['humanArtifact'] = {'artifactId': response_artifact_id}
                await call_fes('UpdateHitlTask', update_body)

            elif action == 'SEND_FOR_APPROVAL':
                await call_fes(
                    'UpdateHitlTask',
                    {
                        'workspaceId': workspaceId,
                        'jobId': jobId,
                        'taskId': taskId,
                        'humanArtifact': {'artifactId': response_artifact_id},
                        'postUpdateAction': 'SEND_FOR_APPROVAL',
                    },
                )

            else:
                # APPROVE or REJECT
                operation = (
                    'SubmitCriticalHitlTask'
                    if severity == 'CRITICAL'
                    else 'SubmitStandardHitlTask'
                )
                await call_fes(
                    operation,
                    {
                        'workspaceId': workspaceId,
                        'jobId': jobId,
                        'taskId': taskId,
                        'action': action,
                        'humanArtifact': {'artifactId': response_artifact_id},
                        'idempotencyToken': str(uuid.uuid4()),
                    },
                )

            # ── Step 8: Return enriched result ──────────────────────────
            updated_result = await call_fes(
                'GetHitlTask',
                {
                    'workspaceId': workspaceId,
                    'jobId': jobId,
                    'taskId': taskId,
                },
            )
            result_data = enrich_task(updated_result['task'])
            if uploaded_artifact_id:
                result_data['uploadedArtifactId'] = uploaded_artifact_id
            if artifact_warning:
                result_data['_warning'] = artifact_warning
            return success_result(result_data)

        except Exception as error:
            return failure_result(error)
