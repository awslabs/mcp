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

"""Core HealthOmics data models for workflows, runs, and storage."""

from awslabs.aws_healthomics_mcp_server.consts import (
    ERROR_STATIC_STORAGE_REQUIRES_CAPACITY,
)
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator
from typing import Any, Dict, List, Optional


class WorkflowType(str, Enum):
    """Enum for workflow languages."""

    WDL = 'WDL'
    NEXTFLOW = 'NEXTFLOW'
    CWL = 'CWL'


class StorageType(str, Enum):
    """Enum for storage types."""

    STATIC = 'STATIC'
    DYNAMIC = 'DYNAMIC'


class CacheBehavior(str, Enum):
    """Enum for cache behaviors."""

    CACHE_ALWAYS = 'CACHE_ALWAYS'
    CACHE_ON_FAILURE = 'CACHE_ON_FAILURE'


class SourceReferenceType(str, Enum):
    """Enum for source reference types in repository definitions."""

    COMMIT_ID = 'COMMIT_ID'
    BRANCH = 'BRANCH'
    TAG = 'TAG'


class SourceReference(BaseModel):
    """Model for repository source reference."""

    type: SourceReferenceType
    value: str

    @field_validator('value')
    @classmethod
    def validate_value_not_empty(cls, v: str) -> str:
        """Validate that value is not empty."""
        if not v or not v.strip():
            raise ValueError('source_reference.value cannot be empty')
        return v


class DefinitionRepository(BaseModel):
    """Model for Git repository definition configuration."""

    connection_arn: str
    full_repository_id: str
    source_reference: SourceReference
    exclude_file_patterns: Optional[List[str]] = None

    @field_validator('connection_arn')
    @classmethod
    def validate_connection_arn(cls, v: str) -> str:
        """Validate that connection_arn is a valid AWS CodeConnection ARN."""
        if not v.startswith('arn:aws:codeconnections:') and not v.startswith(
            'arn:aws:codestar-connections:'
        ):
            raise ValueError(f'connection_arn must be a valid AWS CodeConnection ARN, got: {v}')
        return v

    @field_validator('full_repository_id')
    @classmethod
    def validate_repository_id_not_empty(cls, v: str) -> str:
        """Validate that full_repository_id is not empty."""
        if not v or not v.strip():
            raise ValueError('full_repository_id cannot be empty')
        return v


class RunStatus(str, Enum):
    """Enum for run statuses."""

    PENDING = 'PENDING'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class ExportType(str, Enum):
    """Enum for export types."""

    DEFINITION = 'DEFINITION'
    PARAMETER_TEMPLATE = 'PARAMETER_TEMPLATE'


class WorkflowSummary(BaseModel):
    """Summary information about a workflow."""

    id: str
    arn: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: str
    type: str
    storageType: Optional[str] = None
    storageCapacity: Optional[int] = None
    creationTime: datetime


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: List[WorkflowSummary]
    nextToken: Optional[str] = None


class RunSummary(BaseModel):
    """Summary information about a run."""

    id: str
    arn: str
    name: Optional[str] = None
    parameters: Optional[dict] = None
    status: str
    workflowId: str
    workflowType: str
    creationTime: datetime
    startTime: Optional[datetime] = None
    stopTime: Optional[datetime] = None


class RunListResponse(BaseModel):
    """Response model for listing runs."""

    runs: List[RunSummary]
    nextToken: Optional[str] = None


class TaskSummary(BaseModel):
    """Summary information about a task."""

    taskId: str
    status: str
    name: str
    cpus: int
    memory: int
    startTime: Optional[datetime] = None
    stopTime: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""

    tasks: List[TaskSummary]
    nextToken: Optional[str] = None


class LogEvent(BaseModel):
    """Log event model."""

    timestamp: datetime
    message: str


class LogResponse(BaseModel):
    """Response model for retrieving logs."""

    events: List[LogEvent]
    nextToken: Optional[str] = None


class StorageRequest(BaseModel):
    """Model for storage requests."""

    storageType: StorageType
    storageCapacity: Optional[int] = None

    @model_validator(mode='after')
    def validate_storage_capacity(self):
        """Validate storage capacity."""
        if self.storageType == StorageType.STATIC and self.storageCapacity is None:
            raise ValueError(ERROR_STATIC_STORAGE_REQUIRES_CAPACITY)
        return self


class AnalysisResult(BaseModel):
    """Model for run analysis results."""

    taskName: str
    count: int
    meanRunningSeconds: float
    maximumRunningSeconds: float
    stdDevRunningSeconds: float
    maximumCpuUtilizationRatio: float
    meanCpuUtilizationRatio: float
    maximumMemoryUtilizationRatio: float
    meanMemoryUtilizationRatio: float
    recommendedCpus: int
    recommendedMemoryGiB: float
    recommendedInstanceType: str
    maximumEstimatedUSD: float
    meanEstimatedUSD: float


class AnalysisResponse(BaseModel):
    """Response model for run analysis."""

    results: List[AnalysisResult]


class RegistryMapping(BaseModel):
    """Model for registry mapping configuration."""

    upstreamRegistryUrl: str
    ecrRepositoryPrefix: str
    upstreamRepositoryPrefix: Optional[str]
    ecrAccountId: Optional[str]


class ImageMapping(BaseModel):
    """Model for image mapping configuration."""

    sourceImage: str
    destinationImage: str


class ContainerRegistryMap(BaseModel):
    """Model for container registry mapping configuration."""

    registryMappings: List[RegistryMapping] = []
    imageMappings: List[ImageMapping] = []

    @field_validator('registryMappings', 'imageMappings', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v: Any) -> List[Any]:
        """Convert None values to empty lists for consistency."""
        return [] if v is None else v


class RunGroupSummary(BaseModel):
    """Summary information about a run group."""

    id: str
    arn: str
    name: Optional[str] = None
    maxCpus: Optional[int] = None
    maxGpus: Optional[int] = None
    maxDuration: Optional[int] = None
    maxRuns: Optional[int] = None
    creationTime: datetime


class RunGroupDetail(RunGroupSummary):
    """Detailed run group information including tags."""

    tags: Optional[Dict[str, str]] = None


class RunGroupListResponse(BaseModel):
    """Response model for listing run groups."""

    runGroups: List[RunGroupSummary]
    nextToken: Optional[str] = None


class RunCacheStatus(str, Enum):
    """Enum for run cache statuses."""

    ACTIVE = 'ACTIVE'
    DELETED = 'DELETED'
    FAILED = 'FAILED'


class RunCacheSummary(BaseModel):
    """Summary information about a run cache."""

    id: str
    arn: str
    name: Optional[str] = None
    status: str
    cacheBehavior: Optional[str] = None
    creationTime: datetime


class RunCacheDetail(RunCacheSummary):
    """Detailed run cache information."""

    cacheS3Uri: Optional[str] = None
    cacheBucketOwnerId: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class RunCacheListResponse(BaseModel):
    """Response model for listing run caches."""

    runCaches: List[RunCacheSummary]
    nextToken: Optional[str] = None
