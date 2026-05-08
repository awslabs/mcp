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

"""Pydantic request models for Transform API operations.

These are hand-written (not generated) models that mirror the C2J service
model for the subset of request shapes this MCP server actually sends.

Drift is guarded by ``tests/test_transform_api_models_match_c2j.py`` which cross-checks
every model against ``_service_model/.../service-2.json``:

- Every field present on a Pydantic model must exist in the C2J input shape.
- Every C2J-required field must be required on the Pydantic model.

All models use ``extra='forbid'`` so a typo in a field name raises at
construction time rather than silently producing a malformed wire payload.

Response shapes are intentionally NOT modeled — ``call_fes`` returns
``dict`` / ``Any`` and callers access fields via ``.get(...)``. The value of
typing is almost entirely on the request side where it prevents wrong keys
going on the wire.
"""

from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional


# ── Base class ────────────────────────────────────────────────────────────


class FESRequest(BaseModel):
    """Base for every FES request model.

    Config:
      * ``extra='forbid'`` — unknown fields fail fast at construction.
      * ``populate_by_name=True`` — allow both attribute and alias (for now no
        aliases are used since the wire format is already camelCase matching
        the Python attribute names).
    """

    model_config = ConfigDict(extra='forbid', populate_by_name=True)


# ── Shared nested models ──────────────────────────────────────────────────


class ExecutionPlanFilter(FESRequest):
    """Filter ListJobs by execution plan."""

    executionPlanId: str


class AwsAccountConnectionRequest(FESRequest):
    """AWS account portion of an account connection request."""

    awsAccountId: Optional[str] = None


class AccountConnectionRequest(FESRequest):
    """Account connection request wrapper for CreateConnector."""

    awsAccountConnectionRequest: Optional[AwsAccountConnectionRequest] = None


class HitlTaskArtifact(FESRequest):
    """Artifact reference for HITL task submissions."""

    artifactId: Optional[str] = None


class HitlTaskFilter(FESRequest):
    """Filter for ListHitlTasks."""

    blockingType: Optional[str] = None
    categories: Optional[List[str]] = None
    planStepId: Optional[str] = None
    tag: Optional[str] = None
    taskStatuses: Optional[List[str]] = None


class ArtifactType(FESRequest):
    """Category + file type for an artifact reference."""

    categoryType: str
    fileType: str
    schemaType: Optional[str] = None


class ArtifactReference(FESRequest):
    """Reference used when creating an artifact upload URL."""

    artifactId: Optional[str] = None
    artifactType: Optional[ArtifactType] = None


class ContentDigest(FESRequest):
    """Content integrity digest."""

    Sha256: Optional[str] = None


class FileMetadata(FESRequest):
    """File metadata for artifact uploads.

    NOTE: the C2J model defines ``path`` and ``description`` only. There is no
    ``fileName`` field — do not add one.
    """

    description: Optional[str] = None
    path: str


class JobFilter(FESRequest):
    """Filter for ListArtifacts."""

    categoryType: Optional[str] = None
    jobId: Optional[str] = None
    planStepId: Optional[str] = None


class ChatArtifactMetadata(FESRequest):
    """Artifact metadata inside a chat job metadata block."""

    artifactId: Optional[str] = None


class ChatHitlTaskMetadata(FESRequest):
    """HITL task metadata inside a chat job metadata block."""

    focusState: Optional[str] = None
    hitlTaskId: Optional[str] = None


class ChatWorklogStepMetadata(FESRequest):
    """Worklog step metadata inside a chat job metadata block."""

    focusState: Optional[str] = None
    stepId: Optional[str] = None


class ChatJobMetadata(FESRequest):
    """Job metadata entry under workspace.jobs[]."""

    artifact: Optional[ChatArtifactMetadata] = None
    focusState: Optional[str] = None
    hitl: Optional[ChatHitlTaskMetadata] = None
    jobId: Optional[str] = None
    worklog: Optional[ChatWorklogStepMetadata] = None


class ConnectorMetadata(FESRequest):
    """Connector metadata entry under workspace.connectors[]."""

    connectorId: Optional[str] = None
    focusState: Optional[str] = None


class WorkspaceMetadata(FESRequest):
    """Workspace metadata for chat resourcesOnScreen."""

    connectors: Optional[List[ConnectorMetadata]] = None
    jobs: Optional[List[ChatJobMetadata]] = None
    workspaceId: Optional[str] = None


class ResourcesOnScreen(FESRequest):
    """Top-level resourcesOnScreen wrapper for chat metadata."""

    workspace: Optional[WorkspaceMetadata] = None


class Metadata(FESRequest):
    """Chat metadata wrapper."""

    resourcesOnScreen: Optional[ResourcesOnScreen] = None


class ChatArtifactReference(FESRequest):
    """Artifact reference attached to a SendMessage call."""

    artifactId: str
    jobId: str
    workspaceId: str


class Attachments(FESRequest):
    """Attachments block on SendMessage."""

    artifactReferences: Optional[List[ChatArtifactReference]] = None


class Option(FESRequest):
    """Select-option value used inside interactions."""

    label: Optional[str] = None
    value: Optional[str] = None


class InteractionResult(FESRequest):
    """Single interaction result on SendMessage.interactionResults."""

    interactionId: Optional[str] = None
    invokedStatus: Optional[str] = None
    selectedOption: Optional[Option] = None


class InteractionResults(FESRequest):
    """Wrapper for SendMessage.interactionResults."""

    interactionOriginId: Optional[str] = None
    interactionResults: Optional[List[InteractionResult]] = None


class InvokeApi(FESRequest):
    """Invoke-api data for an interaction."""

    label: Optional[str] = None
    operationName: Optional[str] = None
    operationParams: Optional[Dict[str, str]] = None


class InvokeInteractionData(FESRequest):
    """Invoke branch of InteractionData."""

    invokeApi: Optional[InvokeApi] = None


class SelectInteractionData(FESRequest):
    """Select branch of InteractionData."""

    options: Optional[List[Option]] = None


class GroupInteractionData(FESRequest):
    """Group branch of InteractionData.

    Holds a list of child Interactions. Typed as ``Any`` to avoid a cyclic
    model reference; nested interactions are free-form dicts at this depth.
    """

    children: Optional[List[Any]] = None
    groupDescription: Optional[str] = None
    groupName: Optional[str] = None


class InteractionData(FESRequest):
    """Union wrapper for an Interaction's data payload."""

    groupInteractionData: Optional[GroupInteractionData] = None
    invokeInteractionData: Optional[InvokeInteractionData] = None
    selectInteractionData: Optional[SelectInteractionData] = None


class Interaction(FESRequest):
    """Single interaction on SendMessage.interactions."""

    actionType: Optional[str] = None
    data: Optional[InteractionData] = None
    interactionId: Optional[str] = None
    target: Optional[str] = None


class StepIdFilter(FESRequest):
    """Worklog step-id filter."""

    stepId: str
    timeFilter: Optional['TimeFilter'] = None


class TimeFilter(FESRequest):
    """Worklog time filter."""

    endTime: Optional[Any] = None
    startTime: Optional[Any] = None


class WorklogFilter(FESRequest):
    """Filter for ListWorklogs."""

    stepIdFilter: Optional[StepIdFilter] = None
    timeFilter: Optional[TimeFilter] = None


class AccessControlTypeFilter(FESRequest):
    """Filter branch for ListAgents by access control type."""

    accessControlType: str


class AgentTypeFilter(FESRequest):
    """Filter branch for ListAgents by agent type."""

    agentType: str


class JobOrchestratorFilter(FESRequest):
    """Filter branch for ListAgents by orchestrator capability."""

    jobOrchestrator: bool


class OwnerTypeFilter(FESRequest):
    """Filter branch for ListAgents by owner type."""

    accessControlType: Optional[str] = None
    ownerType: str


class ListAgentFilter(FESRequest):
    """Union filter for ListAgents (only one branch should be set)."""

    accessControlFilter: Optional[AccessControlTypeFilter] = None
    agentTypeFilter: Optional[AgentTypeFilter] = None
    jobOrchestratorFilter: Optional[JobOrchestratorFilter] = None
    ownerTypeFilter: Optional[OwnerTypeFilter] = None


# Rebuild models that have forward references.
StepIdFilter.model_rebuild()


# ── Request models ────────────────────────────────────────────────────────


# ── Message operations ──
class BatchGetMessageRequest(FESRequest):
    """Request model for BatchGetMessage."""

    messageIds: List[str]
    workspaceId: Optional[str] = None


class SendMessageRequest(FESRequest):
    """Request model for SendMessage."""

    attachments: Optional[Attachments] = None
    idempotencyToken: Optional[str] = None
    interactionResults: Optional[InteractionResults] = None
    interactions: Optional[List[Interaction]] = None
    metadata: Optional[Metadata] = None
    text: Optional[str] = None


class ListMessagesRequest(FESRequest):
    """Request model for ListMessages."""

    maxResults: Optional[int] = None
    metadata: Optional[Metadata] = None
    nextToken: Optional[str] = None
    startTimestamp: Optional[Any] = None


# ── Workspace operations ──
class CreateWorkspaceRequest(FESRequest):
    """Request model for CreateWorkspace."""

    description: Optional[str] = None
    idempotencyToken: Optional[str] = None
    name: Optional[str] = None


class DeleteWorkspaceRequest(FESRequest):
    """Request model for DeleteWorkspace."""

    id: str


class GetWorkspaceRequest(FESRequest):
    """Request model for GetWorkspace."""

    id: str


class ListWorkspacesRequest(FESRequest):
    """Request model for ListWorkspaces."""

    maxResults: Optional[int] = None
    nextToken: Optional[str] = None


# ── Job operations ──
class CreateJobRequest(FESRequest):
    """Request model for CreateJob."""

    executionPlanId: Optional[str] = None
    idempotencyToken: Optional[str] = None
    intent: str
    jobName: str
    jobType: Optional[str] = None
    objective: str
    orchestratorAgent: Optional[str] = None
    workspaceId: str


class DeleteJobRequest(FESRequest):
    """Request model for DeleteJob."""

    jobId: str
    workspaceId: str


class GetJobRequest(FESRequest):
    """Request model for GetJob."""

    includeObjective: Optional[bool] = None
    jobId: str
    workspaceId: str


class ListJobsRequest(FESRequest):
    """Request model for ListJobs."""

    executionPlanFilter: Optional[ExecutionPlanFilter] = None
    nextToken: Optional[str] = None
    workspaceId: str


class StartJobRequest(FESRequest):
    """Request model for StartJob."""

    idempotencyToken: Optional[str] = None
    jobId: str
    workspaceId: str


class StopJobRequest(FESRequest):
    """Request model for StopJob."""

    idempotencyToken: Optional[str] = None
    jobId: str
    workspaceId: str


# ── Connector operations ──
class CreateConnectorRequest(FESRequest):
    """Request model for CreateConnector."""

    accountConnectionRequest: AccountConnectionRequest
    configuration: Dict[str, str]
    connectorName: str
    connectorType: str
    description: Optional[str] = None
    idempotencyToken: Optional[str] = None
    targetRegions: Optional[List[str]] = None
    workspaceId: str


class GetConnectorRequest(FESRequest):
    """Request model for GetConnector."""

    connectorId: str
    workspaceId: str


class ListConnectorsRequest(FESRequest):
    """Request model for ListConnectors."""

    nextToken: Optional[str] = None
    requesterAgentInvocationId: Optional[str] = None
    workspaceId: str


# ── HITL operations ──
class GetHitlTaskRequest(FESRequest):
    """Request model for GetHitlTask."""

    jobId: str
    taskId: str
    workspaceId: str


class ListHitlTasksRequest(FESRequest):
    """Request model for ListHitlTasks."""

    jobId: str
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    taskFilter: Optional[HitlTaskFilter] = None
    taskType: str
    workspaceId: str


class UpdateHitlTaskRequest(FESRequest):
    """Request model for UpdateHitlTask."""

    humanArtifact: Optional[HitlTaskArtifact] = None
    idempotencyToken: Optional[str] = None
    jobId: str
    postUpdateAction: Optional[str] = None
    taskId: str
    workspaceId: str


class SubmitCriticalHitlTaskRequest(FESRequest):
    """Request model for SubmitCriticalHitlTask."""

    action: str
    humanArtifact: Optional[HitlTaskArtifact] = None
    idempotencyToken: Optional[str] = None
    jobId: str
    taskId: str
    workspaceId: str


class SubmitStandardHitlTaskRequest(FESRequest):
    """Request model for SubmitStandardHitlTask."""

    action: str
    humanArtifact: Optional[HitlTaskArtifact] = None
    idempotencyToken: Optional[str] = None
    jobId: str
    taskId: str
    workspaceId: str


# ── Artifact operations ──
class CreateArtifactDownloadUrlRequest(FESRequest):
    """Request model for CreateArtifactDownloadUrl."""

    artifactId: str
    jobId: Optional[str] = None
    workspaceId: str


class CreateArtifactUploadUrlRequest(FESRequest):
    """Request model for CreateArtifactUploadUrl."""

    artifactReference: ArtifactReference
    connectorId: Optional[str] = None
    contentDigest: ContentDigest
    fileMetadata: Optional[FileMetadata] = None
    jobId: Optional[str] = None
    planStepId: Optional[str] = None
    workspaceId: str


class CompleteArtifactUploadRequest(FESRequest):
    """Request model for CompleteArtifactUpload."""

    artifactId: str
    jobId: Optional[str] = None
    workspaceId: str


class CreateAssetDownloadUrlRequest(FESRequest):
    """Request model for CreateAssetDownloadUrl."""

    assetKey: str
    connectorId: str
    jobId: Optional[str] = None
    workspaceId: str


class ListArtifactsRequest(FESRequest):
    """Request model for ListArtifacts."""

    jobFilter: Optional[JobFilter] = None
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    pathPrefix: Optional[str] = None
    workspaceId: str


# ── Plan operations ──
class ListJobPlanStepsRequest(FESRequest):
    """Request model for ListJobPlanSteps."""

    jobId: str
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    parentStepId: Optional[str] = None
    workspaceId: str


class ListPlanUpdatesRequest(FESRequest):
    """Request model for ListPlanUpdates."""

    jobId: str
    nextToken: Optional[str] = None
    planVersion: str
    timestamp: int
    workspaceId: str


# ── Worklog operations ──
class ListWorklogsRequest(FESRequest):
    """Request model for ListWorklogs."""

    jobId: str
    nextToken: Optional[str] = None
    worklogFilter: Optional[WorklogFilter] = None
    workspaceId: str


# ── Agent operations ──
class ListAgentsRequest(FESRequest):
    """Request model for ListAgents."""

    agentConfigurationAvailability: Optional[str] = None
    agentFilter: Optional[ListAgentFilter] = None
    maxResults: Optional[int] = None
    nextToken: Optional[str] = None


# ── User / collaborator operations ──
class BatchGetUserDetailsRequest(FESRequest):
    """Request model for BatchGetUserDetails."""

    userIdList: List[str]


class ListUserRoleMappingsRequest(FESRequest):
    """Request model for ListUserRoleMappings."""

    maxResults: Optional[int] = None
    nextToken: Optional[str] = None
    roleFilters: Optional[List[str]] = None
    workspaceId: str


class PutUserRoleMappingsRequest(FESRequest):
    """Request model for PutUserRoleMappings."""

    roles: List[str]
    userId: str
    workspaceId: str


class DeleteUserRoleMappingsRequest(FESRequest):
    """Request model for DeleteUserRoleMappings."""

    userId: str
    workspaceId: str


class DeleteSelfRoleMappingsRequest(FESRequest):
    """Request model for DeleteSelfRoleMappings."""

    workspaceId: str


class SearchUsersTypeaheadRequest(FESRequest):
    """Request model for SearchUsersTypeahead."""

    searchKey: str
    searchTerm: str
