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

"""Get resource tool handler — retrieves a single AWS Transform resource."""

import asyncio
import json
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.tool_utils import (
    READ_ONLY,
    download_s3_content,
    error_result,
    failure_result,
    format_job_response,
    success_result,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import (
    BatchGetMessageRequest,
    CreateArtifactDownloadUrlRequest,
    CreateAssetDownloadUrlRequest,
    GetConnectorRequest,
    GetHitlTaskRequest,
    GetJobRequest,
    GetWorkspaceRequest,
    ListJobPlanStepsRequest,
    ListPlanUpdatesRequest,
)
from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


# ── Constants ──────────────────────────────────────────────────────────────


def NOT_CONFIGURED() -> Dict[str, Any]:
    """Return error result for unconfigured state."""
    return error_result(
        'NOT_CONFIGURED',
        'Not connected to AWS Transform.',
        'Call configure with authMode "cookie" or "sso".',
    )


# ── Enum types ─────────────────────────────────────────────────────────────


class GetResourceType(str, Enum):
    """Allowed resource types for get_resource."""

    session = 'session'
    workspace = 'workspace'
    job = 'job'
    connector = 'connector'
    task = 'task'
    artifact = 'artifact'
    asset = 'asset'
    messages = 'messages'
    plan = 'plan'


# ── Session helper (inlined from session.ts) ───────────────────────────────


async def get_session() -> Dict[str, Any]:
    """Verify the current API session.

    Returns:
        A dict with ``success: True`` and session data, or ``success: False``
        with an error object.
    """
    try:
        session = await call_transform_api('VerifySession')
        return {'success': True, 'data': {'session': session}}
    except Exception as error:
        msg = str(error)
        return {'success': False, 'error': {'code': 'REQUEST_FAILED', 'message': msg}}


# ── Handler class ──────────────────────────────────────────────────────────


TOOL_DESCRIPTION = (
    'Retrieves a specific AWS Transform resource by type.\n\n'
    'Required parameters per resource:\n'
    '- session → (none)\n'
    '- workspace → workspaceId\n'
    '- job → workspaceId, jobId. Returns basic job metadata. To check job status or '
    'determine next steps, use send_message scoped to the job instead.\n'
    '- connector → workspaceId, connectorId\n'
    '- task → workspaceId, jobId, taskId\n'
    '- artifact → workspaceId, jobId, artifactId\n'
    '- asset → workspaceId, jobId, connectorId, assetKey\n'
    '- messages → workspaceId, messageIds (array of strings, e.g. ["msg-abc", "msg-def"]). '
    'Use this after list_resources(resource="messages") to hydrate message IDs into full content. '
    'When retrying after a send_message timeout, look for parentMessageId matching the '
    'sentMessageId and messageType="FINAL_RESPONSE".\n'
    '- plan → workspaceId, jobId\n\n'
    'IMPORTANT (task): After fetching a task, ALWAYS present the details and artifact content '
    'to the user and wait for their decision before calling complete_task.\n'
    'Task responses include: _responseTemplate (example response), '
    '_responseHint (guidance text),\n'
    'and _outputSchema (full JSON Schema with field descriptions, types, enums, and required '
    'fields). Use _outputSchema to construct the correct content JSON for complete_task.\n'
    'If agentArtifactContent is empty ({}), the agent may still be generating content — '
    'check worklogs for status.'
)


class GetResourceHandler:
    """Registers and handles the get_resource tool."""

    def __init__(self, mcp: Any) -> None:
        """Register the get_resource tool on the given MCP server."""
        audited_tool(
            mcp,
            'get_resource',
            title='Get Resource',
            annotations=READ_ONLY,
            description=TOOL_DESCRIPTION,
        )(self.get_resource)

    async def get_resource(
        self,
        ctx: Context,
        resource: Annotated[GetResourceType, Field(description='The type of resource to get')],
        workspaceId: Annotated[
            Optional[str],
            Field(
                description=(
                    'Workspace ID. REQUIRED for: job, connector, task, artifact, asset, plan'
                )
            ),
        ] = None,
        jobId: Annotated[
            Optional[str],
            Field(description='Job ID. REQUIRED for: job, task, artifact, asset, plan'),
        ] = None,
        connectorId: Annotated[
            Optional[str],
            Field(description='Connector ID. REQUIRED for: connector, asset'),
        ] = None,
        taskId: Annotated[
            Optional[str],
            Field(description='Task ID. REQUIRED for: task'),
        ] = None,
        artifactId: Annotated[
            Optional[str],
            Field(description='Artifact ID. REQUIRED for: artifact'),
        ] = None,
        assetKey: Annotated[
            Optional[str],
            Field(description='S3 asset key. REQUIRED for: asset'),
        ] = None,
        messageIds: Annotated[
            Optional[List[str]],
            Field(
                description=(
                    'Message IDs to retrieve (messages only, max 100). '
                    'Pass as an array of strings, e.g. ["msg-abc", "msg-def"].'
                )
            ),
        ] = None,
        savePath: Annotated[
            Optional[str],
            Field(description='Local path to save artifact file (artifact only)'),
        ] = None,
        fileName: Annotated[
            Optional[str],
            Field(description='File name when saving (defaults to artifactId)'),
        ] = None,
    ) -> Dict[str, Any]:
        """Retrieve a specific AWS Transform resource by type."""
        if not is_fes_available():
            return NOT_CONFIGURED()

        # Nudge: if a jobId is provided but load_instructions hasn't been called for it.
        # Need to remove this when we add agent plugins.
        nudge = job_needs_check(jobId)
        if nudge and resource not in (
            GetResourceType.session,
            GetResourceType.workspace,
            GetResourceType.connector,
            GetResourceType.job,
        ):
            return error_result(
                'INSTRUCTIONS_REQUIRED',
                nudge,
                f'Call load_instructions with workspaceId and jobId="{jobId}".',
            )

        try:
            if resource == GetResourceType.session:
                result = await get_session()
                return {
                    'content': [{'type': 'text', 'text': json.dumps(result, default=str)}],
                    'isError': not result.get('success', False),
                }

            # ── workspace ──────────────────────────────────────────────────
            elif resource == GetResourceType.workspace:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting a workspace.'
                    )
                return success_result(
                    await call_transform_api('GetWorkspace', GetWorkspaceRequest(id=workspaceId))
                )

            # ── job ────────────────────────────────────────────────────────
            elif resource == GetResourceType.job:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting a job.'
                    )
                if not jobId:
                    return error_result('VALIDATION_ERROR', 'jobId is required for getting a job.')

                return success_result(
                    format_job_response(
                        await call_transform_api(
                            'GetJob',
                            GetJobRequest(workspaceId=workspaceId, jobId=jobId),
                        )
                    )
                )

            # ── connector ──────────────────────────────────────────────────
            elif resource == GetResourceType.connector:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting a connector.'
                    )
                if not connectorId:
                    return error_result(
                        'VALIDATION_ERROR', 'connectorId is required for getting a connector.'
                    )
                return success_result(
                    await call_transform_api(
                        'GetConnector',
                        GetConnectorRequest(workspaceId=workspaceId, connectorId=connectorId),
                    )
                )

            # ── task ───────────────────────────────────────────────────────
            elif resource == GetResourceType.task:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting a task.'
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for getting a task.'
                    )
                if not taskId:
                    return error_result(
                        'VALIDATION_ERROR', 'taskId is required for getting a task.'
                    )

                task_result = await call_transform_api(
                    'GetHitlTask',
                    GetHitlTaskRequest(workspaceId=workspaceId, jobId=jobId, taskId=taskId),
                )
                task_data = task_result.get('task', {}) if isinstance(task_result, dict) else {}

                # Guard: hitl_schemas may not exist yet
                try:
                    from awslabs.aws_transform_mcp_server.hitl_schemas import (
                        build_dynamic_output_schema,
                        enrich_task,
                    )

                    enriched_task = enrich_task(task_data)
                except ImportError:
                    enriched_task = dict(task_data) if isinstance(task_data, dict) else {}

                # Download agent artifact if present
                agent_artifact = (
                    task_data.get('agentArtifact') if isinstance(task_data, dict) else None
                )
                agent_artifact_content: Any = None
                artifact_download_warning: Optional[str] = None

                if isinstance(agent_artifact, dict) and agent_artifact.get('artifactId'):
                    try:
                        from awslabs.aws_transform_mcp_server.tools.hitl import (
                            download_agent_artifact,
                        )

                        dl = await download_agent_artifact(
                            workspace_id=workspaceId,
                            job_id=jobId,
                            artifact_id=agent_artifact['artifactId'],
                        )
                        if dl.get('content'):
                            agent_artifact_content = dl['content']
                        elif dl.get('rawText'):
                            agent_artifact_content = dl['rawText']
                        artifact_download_warning = dl.get('warning')
                    except ImportError:
                        logger.warning('hitl module not available, skipping artifact download')

                # Build dynamic output schema from agent artifact
                if agent_artifact_content and isinstance(agent_artifact_content, dict):
                    component_id = enriched_task.get('uxComponentId')
                    if component_id:
                        try:
                            from awslabs.aws_transform_mcp_server.hitl_schemas import (
                                build_dynamic_output_schema,
                            )

                            dynamic_schema = build_dynamic_output_schema(
                                component_id, agent_artifact_content
                            )
                            if dynamic_schema:
                                enriched_task['_outputSchema'] = dynamic_schema
                                props = dynamic_schema.get('properties', {})
                                concrete_template: Dict[str, str] = {}
                                for f in props:
                                    concrete_template[f] = '<value>'
                                enriched_task['_responseTemplate'] = concrete_template
                                enriched_task['_responseHint'] = (
                                    f'{dynamic_schema.get("description", "")}. '
                                    f'Valid fields: {", ".join(props.keys())}. '
                                    'Do NOT wrap in {"properties": ...} or {"data": ...} '
                                    '— the server handles wrapping automatically.'
                                )
                            elif '_responseTemplate' not in enriched_task:
                                artifact_props = agent_artifact_content.get('properties')
                                if isinstance(artifact_props, dict):
                                    enriched_task['_responseTemplate'] = artifact_props
                                    enriched_task['_responseHint'] = (
                                        'Provide your response as a flat JSON object. '
                                        "These are the agent's input fields (output field "
                                        f'names may differ): {", ".join(artifact_props.keys())}. '
                                        'Do NOT wrap in {"properties": ...} — provide just '
                                        'the response data.'
                                    )
                        except ImportError:
                            pass

                if task_data.get('category') == 'TOOL_APPROVAL':
                    enriched_task['_responseHint'] = (
                        'TOOL_APPROVAL task — agent is requesting permission to execute a tool. '
                        'Present the agentArtifactContent to the user, then call '
                        'complete_task with action=APPROVE or REJECT. '
                        'Do NOT provide content or filePath — the server skips artifact '
                        'upload for TOOL_APPROVAL tasks.'
                    )
                    enriched_task.pop('_responseTemplate', None)
                    enriched_task.pop('_outputSchema', None)

                result_data: Dict[str, Any] = {
                    'task': enriched_task,
                    'agentArtifactContent': agent_artifact_content,
                }
                if artifact_download_warning:
                    result_data['_warning'] = artifact_download_warning

                return success_result(result_data)

            # ── artifact ───────────────────────────────────────────────────
            elif resource == GetResourceType.artifact:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR',
                        'workspaceId is required for downloading an artifact.',
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for downloading an artifact.'
                    )
                if not artifactId:
                    return error_result(
                        'VALIDATION_ERROR',
                        'artifactId is required for downloading an artifact.',
                    )

                url_result = await call_transform_api(
                    'CreateArtifactDownloadUrl',
                    CreateArtifactDownloadUrlRequest(
                        workspaceId=workspaceId,
                        jobId=jobId,
                        artifactId=artifactId,
                    ),
                )
                s3_url = (
                    url_result.get('s3PreSignedUrl', '') if isinstance(url_result, dict) else ''
                )
                dl_result = await download_s3_content(
                    s3_url,
                    save_path=savePath,
                    file_name=fileName,
                    default_name=artifactId,
                )
                return success_result({'artifactId': artifactId, **dl_result})

            # ── asset ──────────────────────────────────────────────────────
            elif resource == GetResourceType.asset:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR',
                        'workspaceId is required for downloading an asset.',
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for downloading an asset.'
                    )
                if not connectorId:
                    return error_result(
                        'VALIDATION_ERROR',
                        'connectorId is required for downloading an asset.',
                    )
                if not assetKey:
                    return error_result(
                        'VALIDATION_ERROR', 'assetKey is required for downloading an asset.'
                    )

                url_result = await call_transform_api(
                    'CreateAssetDownloadUrl',
                    CreateAssetDownloadUrlRequest(
                        workspaceId=workspaceId,
                        jobId=jobId,
                        connectorId=connectorId,
                        assetKey=assetKey,
                    ),
                )
                s3_url = (
                    url_result.get('s3PreSignedUrl', '') if isinstance(url_result, dict) else ''
                )
                default_name = assetKey.split('/')[-1] if '/' in assetKey else assetKey
                dl_result = await download_s3_content(
                    s3_url,
                    save_path=savePath,
                    file_name=fileName,
                    default_name=default_name or 'asset',
                )
                return success_result({'assetKey': assetKey, **dl_result})

            # ── messages ───────────────────────────────────────────────────
            elif resource == GetResourceType.messages:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting messages.'
                    )

                # If messageIds is a string, parse it as JSON
                resolved_ids = messageIds
                if isinstance(messageIds, str):
                    try:
                        resolved_ids = json.loads(messageIds)
                    except json.JSONDecodeError:
                        resolved_ids = None

                if not resolved_ids or len(resolved_ids) == 0:
                    return error_result(
                        'VALIDATION_ERROR',
                        'messageIds is required for getting messages (array of up to 100 IDs).',
                    )
                return success_result(
                    await call_transform_api(
                        'BatchGetMessage',
                        BatchGetMessageRequest(
                            messageIds=resolved_ids,
                            workspaceId=workspaceId,
                        ),
                    )
                )

            # ── plan ───────────────────────────────────────────────────────
            elif resource == GetResourceType.plan:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting the plan.'
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for getting the plan.'
                    )

                results = await asyncio.gather(
                    call_transform_api(
                        'ListJobPlanSteps',
                        ListJobPlanStepsRequest(workspaceId=workspaceId, jobId=jobId),
                    ),
                    call_transform_api(
                        'ListPlanUpdates',
                        ListPlanUpdatesRequest(
                            workspaceId=workspaceId,
                            jobId=jobId,
                            planVersion='1',
                            timestamp=0,
                        ),
                    ),
                    return_exceptions=True,
                )

                plan_steps = None if isinstance(results[0], Exception) else results[0]
                plan_updates = None if isinstance(results[1], Exception) else results[1]

                if not plan_steps and not plan_updates:
                    return error_result(
                        'NOT_FOUND',
                        'No plan data available. The job may not have started yet.',
                        'Check job status with get_resource resource="job".',
                    )

                merged: Dict[str, Any] = {}
                if plan_steps:
                    merged['planSteps'] = plan_steps
                if plan_updates:
                    merged['planUpdates'] = plan_updates

                return success_result(merged)

            else:
                return error_result('VALIDATION_ERROR', f'Unknown resource type: {resource}')

        except Exception as error:
            return failure_result(error)
