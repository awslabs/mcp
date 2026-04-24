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

"""List resources tool handler — dispatches to FES/TCP based on resource type."""

import asyncio
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import (
    is_configured,
    is_sigv4_configured,
)
from awslabs.aws_transform_mcp_server.fes_client import FESOperation, call_fes, paginate_all
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.tcp_client import call_tcp
from awslabs.aws_transform_mcp_server.tool_utils import (
    READ_ONLY,
    error_result,
    failure_result,
    success_result,
)
from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Callable, Dict, Optional


# ── Constants ──────────────────────────────────────────────────────────────


def SIGV4_NOT_CONFIGURED() -> Dict[str, Any]:
    """Return error result for unconfigured SigV4 state."""
    return error_result(
        'SIGV4_NOT_CONFIGURED',
        'SigV4 credentials not configured.',
        'Call "configure_sigv4" to set up AWS credentials.',
    )


def NOT_CONFIGURED() -> Dict[str, Any]:
    """Return error result for unconfigured state."""
    return error_result(
        'NOT_CONFIGURED',
        'Not connected to AWS Transform.',
        'Call configure with authMode "cookie" or "sso".',
    )


# ── Enum types ─────────────────────────────────────────────────────────────


class ResourceType(str, Enum):
    """Allowed resource types for list_resources."""

    workspaces = 'workspaces'
    jobs = 'jobs'
    connectors = 'connectors'
    tasks = 'tasks'
    artifacts = 'artifacts'
    messages = 'messages'
    worklogs = 'worklogs'
    plan = 'plan'
    account_connectors = 'account_connectors'
    profiles = 'profiles'
    agents = 'agents'
    collaborators = 'collaborators'
    users = 'users'


class TaskTypeEnum(str, Enum):
    """Task type filter."""

    NORMAL = 'NORMAL'
    DASHBOARD = 'DASHBOARD'


class CategoryEnum(str, Enum):
    """Category filter for tasks."""

    REGULAR = 'REGULAR'
    TOOL_APPROVAL = 'TOOL_APPROVAL'


class SourceEnum(str, Enum):
    """Artifact source for mainframe jobs."""

    connector = 'connector'
    artifact_store = 'artifact_store'


class AgentTypeEnum(str, Enum):
    """Agent type filter."""

    ORCHESTRATOR_AGENT = 'ORCHESTRATOR_AGENT'
    SUB_AGENT = 'SUB_AGENT'


class OwnerTypeEnum(str, Enum):
    """Owner type filter."""

    INTERNAL_AGENT = 'INTERNAL_AGENT'
    DIRECT_AGENT = 'DIRECT_AGENT'
    MARKETPLACE_AGENT = 'MARKETPLACE_AGENT'


class AgentConfigAvailEnum(str, Enum):
    """Agent configuration availability filter."""

    RUNTIME_CONFIGURATION_AVAILABLE = 'RUNTIME_CONFIGURATION_AVAILABLE'
    NEEDS_RUNTIME_CONFIGURATION = 'NEEDS_RUNTIME_CONFIGURATION'
    ANY = 'ANY'


# ── Pagination helpers ─────────────────────────────────────────────────────


def with_pagination(
    body: Dict[str, Any],
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Add pagination fields to a request body if provided."""
    if max_results is not None:
        body['maxResults'] = max_results
    if next_token is not None:
        body['nextToken'] = next_token
    return body


async def paginated_fes(
    api: FESOperation,
    body: Dict[str, Any],
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    token_remap: Optional[Dict[str, str]] = None,
    transform: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, Any]:
    """Call FES with pagination and optional post-processing.

    Args:
        api: FES operation name.
        body: Request body (mutated in place with pagination fields).
        max_results: Optional max results.
        next_token: Optional pagination token.
        token_remap: Rename response keys (e.g. outputToken -> nextToken).
        transform: Optional transform function applied to the result.

    Returns:
        MCP-formatted success result.
    """
    with_pagination(body, max_results, next_token)
    raw = await call_fes(api, body)

    if raw is None or not isinstance(raw, dict):
        return success_result(transform(raw) if transform else raw)

    result = raw
    if token_remap:
        for from_key, to_key in token_remap.items():
            if from_key in result:
                result[to_key] = result[from_key]
                del result[from_key]

    return success_result(transform(result) if transform else result)


# ── Handler class ──────────────────────────────────────────────────────────


TOOL_DESCRIPTION = (
    'Lists AWS Transform resources by type. Auto-paginates server-side for: '
    'workspaces, jobs, connectors, tasks, artifacts, worklogs, agents, collaborators. '
    'These return ALL results in one call — do NOT pass nextToken. '
    'Manual pagination (nextToken) is used by: messages, plan '
    '(stepsNextToken/updatesNextToken), account_connectors '
    '(sourceNextToken/targetNextToken).\n\n'
    'Use this to browse collections. Use get_resource to fetch a single item with '
    'full details. Do NOT use this in a polling loop for messages — use poll_message instead.\n\n'
    'Resource types and required parameters:\n'
    '- workspaces → (none)\n'
    '- jobs → workspaceId\n'
    '- connectors → workspaceId\n'
    '- tasks → workspaceId, jobId\n'
    '- artifacts → workspaceId, jobId. For mainframe jobs, you MUST specify source '
    '("connector" for job output files, "artifact_store" for managed/HITL artifacts). '
    'Connector assets include connectorId and assetKey — use '
    'get_resource resource="asset" to download them.\n'
    '- messages → workspaceId (jobId optional). Returns full message content. '
    'Uses nextToken for pagination (not auto-paginated).\n'
    '- worklogs → workspaceId, jobId (optional: stepId OR startTime/endTime)\n'
    '- plan → workspaceId, jobId. Uses stepsNextToken/updatesNextToken (not auto-paginated).\n'
    '- account_connectors → (none, requires SigV4 auth). Uses sourceNextToken/targetNextToken.\n'
    '- profiles → awsAccountId (requires SigV4 auth)\n'
    '- agents → (none). Optional filters: agentType, ownerType, or jobOrchestrator.\n'
    '- collaborators → workspaceId. Returns members with enriched user details '
    '(userName, displayName, email).\n'
    '- users → searchTerm. Search by username or email. Use this to find a userId '
    'before calling manage_collaborator.\n\n'
    'Errors: NOT_CONFIGURED (call configure first), INSTRUCTIONS_REQUIRED '
    '(call load_instructions for the job first), VALIDATION_ERROR (missing required params), '
    'SOURCE_REQUIRED (mainframe artifacts need source param).'
)


class ListResourcesHandler:
    """Registers and handles the list_resources tool."""

    def __init__(self, mcp: Any) -> None:
        """Register the list_resources tool on the given MCP server."""
        audited_tool(
            mcp,
            'list_resources',
            title='List Resources',
            annotations=READ_ONLY,
            description=TOOL_DESCRIPTION,
        )(self.list_resources)

    async def list_resources(
        self,
        ctx: Context,
        resource: Annotated[ResourceType, Field(description='The type of resource to list')],
        workspaceId: Annotated[
            Optional[str],
            Field(
                description='Workspace ID. REQUIRED for: jobs, connectors, tasks, artifacts, plan'
            ),
        ] = None,
        jobId: Annotated[
            Optional[str],
            Field(
                description=(
                    'Job ID. REQUIRED for: tasks, plan. Optional filter for: artifacts, messages'
                )
            ),
        ] = None,
        taskType: Annotated[
            Optional[TaskTypeEnum],
            Field(description='Task type filter (tasks only, default: NORMAL)'),
        ] = None,
        category: Annotated[
            Optional[CategoryEnum],
            Field(
                description=(
                    'Category filter (tasks only). REGULAR = standard HITL tasks (default). '
                    'TOOL_APPROVAL = tasks requiring human approval before an agent can execute '
                    'a tool — shown in the webapp Approvals tab.'
                )
            ),
        ] = None,
        planStepId: Annotated[
            Optional[str],
            Field(description='Plan step filter (artifacts only)'),
        ] = None,
        pathPrefix: Annotated[
            Optional[str],
            Field(
                description=(
                    'S3 path prefix for browsing files (artifacts only). Usually auto-constructed '
                    '— only provide to drill into a subfolder returned by a previous listing.'
                )
            ),
        ] = None,
        source: Annotated[
            Optional[SourceEnum],
            Field(
                description=(
                    'Where to list artifacts from (artifacts only). '
                    '"connector" = job output files from the S3 connector '
                    '(mainframe jobs). "artifact_store" = managed/HITL '
                    'artifacts. Required for mainframe jobs; ignored for '
                    'non-mainframe.'
                )
            ),
        ] = None,
        startTimestamp: Annotated[
            Optional[str],
            Field(description='ISO 8601 timestamp filter (messages only)'),
        ] = None,
        stepId: Annotated[
            Optional[str],
            Field(description='Plan step ID filter (worklogs only)'),
        ] = None,
        startTime: Annotated[
            Optional[str],
            Field(
                description=(
                    'ISO 8601 start time filter (worklogs only, mutually exclusive with stepId)'
                )
            ),
        ] = None,
        endTime: Annotated[
            Optional[str],
            Field(
                description=(
                    'ISO 8601 end time filter (worklogs only, mutually exclusive with stepId)'
                )
            ),
        ] = None,
        sourceNextToken: Annotated[
            Optional[str],
            Field(description='Pagination token for source connectors (account_connectors only)'),
        ] = None,
        targetNextToken: Annotated[
            Optional[str],
            Field(description='Pagination token for target connectors (account_connectors only)'),
        ] = None,
        awsAccountId: Annotated[
            Optional[str],
            Field(description='AWS account ID (REQUIRED for profiles)'),
        ] = None,
        agentType: Annotated[
            Optional[AgentTypeEnum],
            Field(
                description=(
                    'Filter by agent type/role (agents only). '
                    'ORCHESTRATOR_AGENT manages workflows and can create '
                    'jobs; SUB_AGENT handles subtasks within a job.'
                )
            ),
        ] = None,
        ownerType: Annotated[
            Optional[OwnerTypeEnum],
            Field(description='Filter by owner type (agents only)'),
        ] = None,
        jobOrchestrator: Annotated[
            Optional[bool],
            Field(
                description=(
                    'Filter by job orchestration capability (agents only). true = agents that can '
                    'orchestrate jobs, false = agents that cannot.'
                )
            ),
        ] = None,
        agentConfigurationAvailability: Annotated[
            Optional[AgentConfigAvailEnum],
            Field(description='Filter by runtime configuration status (agents only)'),
        ] = None,
        stepsNextToken: Annotated[
            Optional[str],
            Field(description='Pagination token for plan steps (plan only)'),
        ] = None,
        updatesNextToken: Annotated[
            Optional[str],
            Field(description='Pagination token for plan updates (plan only)'),
        ] = None,
        searchTerm: Annotated[
            Optional[str],
            Field(description='Search term for users resource. Required when resource="users".'),
        ] = None,
        maxResults: Annotated[
            Optional[int],
            Field(
                description=(
                    'Max results per page. Only used by: messages, plan, '
                    'account_connectors, profiles. Ignored for auto-paginated resources.'
                )
            ),
        ] = None,
        nextToken: Annotated[
            Optional[str],
            Field(
                description=(
                    'Pagination token. Only used by: messages, account_connectors, '
                    'profiles. For plan use stepsNextToken/updatesNextToken. '
                    'Ignored for auto-paginated resources.'
                )
            ),
        ] = None,
    ) -> Dict[str, Any]:
        """List AWS Transform resources by type."""
        # ── account_connectors: TCP / SigV4 ────────────────────────────────
        if resource == ResourceType.account_connectors:
            if not is_sigv4_configured():
                return SIGV4_NOT_CONFIGURED()
            try:
                body: Dict[str, Any] = {}
                if sourceNextToken:
                    body['sourceNextToken'] = sourceNextToken
                if targetNextToken:
                    body['targetNextToken'] = targetNextToken
                if maxResults is not None:
                    body['maxResults'] = maxResults
                return success_result(await call_tcp('ListConnectors', body))
            except Exception as error:
                return failure_result(error)

        # ── profiles: TCP / SigV4 ──────────────────────────────────────────
        if resource == ResourceType.profiles:
            if not is_sigv4_configured():
                return SIGV4_NOT_CONFIGURED()
            if not awsAccountId:
                return error_result(
                    'VALIDATION_ERROR',
                    'awsAccountId is required for listing profiles.',
                )
            try:
                body = with_pagination(
                    {'retrieveDetails': True, 'awsAccountId': awsAccountId},
                    maxResults,
                    nextToken,
                )
                return success_result(await call_tcp('ListProfiles', body))
            except Exception as error:
                return failure_result(error)

        # ── All other resources: FES ───────────────────────────────────────
        if not is_configured():
            return NOT_CONFIGURED()

        # Nudge: if a jobId is provided but load_instructions hasn't been called for it
        nudge = job_needs_check(jobId)
        if nudge and resource not in (
            ResourceType.workspaces,
            ResourceType.jobs,
            ResourceType.connectors,
            ResourceType.agents,
        ):
            return error_result(
                'INSTRUCTIONS_REQUIRED',
                nudge,
                f'Call load_instructions with workspaceId and jobId="{jobId}".',
            )

        try:
            if resource == ResourceType.workspaces:
                return success_result(await paginate_all('ListWorkspaces', {}, 'items'))

            elif resource == ResourceType.jobs:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing jobs.'
                    )
                return success_result(
                    await paginate_all('ListJobs', {'workspaceId': workspaceId}, 'jobList')
                )

            elif resource == ResourceType.connectors:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing connectors.'
                    )
                return success_result(
                    await paginate_all(
                        'ListConnectors', {'workspaceId': workspaceId}, 'connectors'
                    )
                )

            elif resource == ResourceType.tasks:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing tasks.'
                    )
                if not jobId:
                    return error_result('VALIDATION_ERROR', 'jobId is required for listing tasks.')

                task_body: Dict[str, Any] = {
                    'workspaceId': workspaceId,
                    'jobId': jobId,
                    'taskType': taskType.value if taskType else 'NORMAL',
                }
                if category:
                    task_body['taskFilter'] = {'categories': [category.value]}

                data = await paginate_all('ListHitlTasks', task_body, 'hitlTasks')
                try:
                    from awslabs.aws_transform_mcp_server.hitl_schemas import enrich_tasks

                    data = enrich_tasks(data)
                except ImportError:
                    pass
                return success_result(data)

            elif resource == ResourceType.artifacts:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing artifacts.'
                    )

                resolved_path_prefix = pathPrefix
                if jobId and not pathPrefix:
                    job = await call_fes('GetJob', {'workspaceId': workspaceId, 'jobId': jobId})
                    job_type = job.get('jobType', '') if isinstance(job, dict) else ''
                    is_mainframe = 'MAINFRAME' in job_type.upper()

                    if is_mainframe and not source:
                        return error_result(
                            'SOURCE_REQUIRED',
                            'This is a mainframe job which has two artifact sources. '
                            'Please specify source:\n'
                            '- "connector" → job output files from the S3 connector\n'
                            '- "artifact_store" → managed/HITL task artifacts',
                            'Re-call with source="connector" to browse output files, '
                            'or source="artifact_store" for managed artifacts.',
                        )

                    if is_mainframe and source == SourceEnum.connector:
                        resolved_path_prefix = f'transform-output/{jobId}/'

                body = {'workspaceId': workspaceId}
                if jobId:
                    job_filter: Dict[str, Any] = {'jobId': jobId}
                    if planStepId:
                        job_filter['planStepId'] = planStepId
                    body['jobFilter'] = job_filter
                if resolved_path_prefix:
                    body['pathPrefix'] = resolved_path_prefix

                return success_result(await paginate_all('ListArtifacts', body, 'artifacts'))

            elif resource == ResourceType.messages:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing messages.'
                    )
                workspace: Dict[str, Any] = {'workspaceId': workspaceId}
                if jobId:
                    workspace['jobs'] = [{'jobId': jobId, 'focusState': 'ACTIVE'}]
                body = {'metadata': {'resourcesOnScreen': {'workspace': workspace}}}
                if startTimestamp is not None:
                    body['startTimestamp'] = startTimestamp
                with_pagination(body, maxResults, nextToken)
                list_result = await call_fes('ListMessages', body)
                message_ids = (
                    list_result.get('messageIds', []) if isinstance(list_result, dict) else []
                )
                if not message_ids:
                    result_data: Dict[str, Any] = {'messages': []}
                    list_next = (
                        list_result.get('nextToken') if isinstance(list_result, dict) else None
                    )
                    if list_next:
                        result_data['nextToken'] = list_next
                    return success_result(result_data)

                # BatchGetMessage accepts max 100 IDs per call
                all_messages = []
                for i in range(0, len(message_ids), 100):
                    batch = message_ids[i : i + 100]
                    batch_result = await call_fes(
                        'BatchGetMessage',
                        {'messageIds': batch, 'workspaceId': workspaceId},
                    )
                    if isinstance(batch_result, dict):
                        all_messages.extend(batch_result.get('messages', []))

                result_data: Dict[str, Any] = {'messages': all_messages}
                list_next = list_result.get('nextToken') if isinstance(list_result, dict) else None
                if list_next:
                    result_data['nextToken'] = list_next
                return success_result(result_data)

            elif resource == ResourceType.worklogs:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing worklogs.'
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for listing worklogs.'
                    )

                body = {'workspaceId': workspaceId, 'jobId': jobId}
                if stepId:
                    body['worklogFilter'] = {'stepIdFilter': {'stepId': stepId}}
                elif startTime or endTime:
                    if startTime and endTime and startTime >= endTime:
                        return error_result(
                            'VALIDATION_ERROR',
                            'startTime must be before endTime.',
                            f'Got startTime={startTime}, endTime={endTime}.',
                        )
                    time_filter: Dict[str, Any] = {}
                    if startTime:
                        time_filter['startTime'] = startTime
                    if endTime:
                        time_filter['endTime'] = endTime
                    body['worklogFilter'] = {'timeFilter': time_filter}

                return success_result(
                    await paginate_all('ListWorklogs', body, 'worklogs', token_key='outputToken')
                )

            elif resource == ResourceType.plan:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for getting the plan.'
                    )
                if not jobId:
                    return error_result(
                        'VALIDATION_ERROR', 'jobId is required for getting the plan.'
                    )

                steps_body = with_pagination(
                    {'workspaceId': workspaceId, 'jobId': jobId},
                    maxResults,
                    stepsNextToken or nextToken,
                )
                updates_body = with_pagination(
                    {'workspaceId': workspaceId, 'jobId': jobId},
                    maxResults,
                    updatesNextToken or nextToken,
                )

                results = await asyncio.gather(
                    call_fes('ListJobPlanSteps', steps_body),
                    call_fes('ListPlanUpdates', updates_body),
                    return_exceptions=True,
                )

                plan_steps_result = results[0]
                plan_updates_result = results[1]

                if isinstance(plan_steps_result, Exception):
                    logger.error(f'ListJobPlanSteps failed: {plan_steps_result}')
                    plan_steps = None
                else:
                    plan_steps = plan_steps_result

                if isinstance(plan_updates_result, Exception):
                    logger.error(f'ListPlanUpdates failed: {plan_updates_result}')
                    plan_updates = None
                else:
                    plan_updates = plan_updates_result

                if not plan_steps and not plan_updates:
                    return error_result(
                        'NOT_FOUND',
                        'No plan data available. The job may not have started yet.',
                        'Check job status with list_resources resource="jobs".',
                    )

                # Extract and remap nested nextToken fields
                steps_token = None
                updates_token = None
                if isinstance(plan_steps, dict):
                    steps_token = plan_steps.pop('nextToken', None)
                if isinstance(plan_updates, dict):
                    updates_token = plan_updates.pop('nextToken', None)

                merged: Dict[str, Any] = {}
                if plan_steps:
                    merged['planSteps'] = plan_steps
                if plan_updates:
                    merged['planUpdates'] = plan_updates
                if steps_token:
                    merged['stepsNextToken'] = steps_token
                if updates_token:
                    merged['updatesNextToken'] = updates_token

                return success_result(merged)

            elif resource == ResourceType.agents:
                body = {}
                # Filter is a union — only one can be set at a time
                if agentType:
                    body['agentFilter'] = {'agentTypeFilter': {'agentType': agentType.value}}
                elif ownerType:
                    body['agentFilter'] = {'ownerTypeFilter': {'ownerType': ownerType.value}}
                elif jobOrchestrator is not None:
                    body['agentFilter'] = {
                        'jobOrchestratorFilter': {'jobOrchestrator': jobOrchestrator}
                    }

                if agentConfigurationAvailability:
                    body['agentConfigurationAvailability'] = agentConfigurationAvailability.value

                data = await paginate_all('ListAgents', body, 'items')
                return success_result(data)

            elif resource == ResourceType.collaborators:
                if not workspaceId:
                    return error_result(
                        'VALIDATION_ERROR', 'workspaceId is required for listing collaborators.'
                    )
                all_data = await paginate_all(
                    'ListUserRoleMappings',
                    {'workspaceId': workspaceId},
                    'items',
                )
                items = all_data.get('items', [])
                details_by_id: Dict[str, Any] = {}
                if items:
                    details = await call_fes(
                        'BatchGetUserDetails',
                        {'userIdList': [i['userId'] for i in items if 'userId' in i]},
                    )
                    for d in (
                        details.get('successfulUserDetails', [])
                        if isinstance(details, dict)
                        else []
                    ):
                        uid = d.get('userId')
                        if uid:
                            details_by_id[uid] = d
                enriched = [{**i, **details_by_id.get(i.get('userId', ''), {})} for i in items]
                return success_result({'items': enriched})

            elif resource == ResourceType.users:
                if not searchTerm:
                    return error_result(
                        'VALIDATION_ERROR', 'searchTerm is required for listing users.'
                    )
                return success_result(
                    await call_fes(
                        'SearchUsersTypeahead',
                        {'searchTerm': searchTerm, 'searchKey': 'USERNAME_OR_EMAIL_ADDRESS'},
                    )
                )

            else:
                return error_result('VALIDATION_ERROR', f'Unknown resource type: {resource}')

        except Exception as error:
            return failure_result(error)
