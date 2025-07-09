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

"""Defines data models, Pydantic models, and validation logic."""

from awslabs.aws_healthomics_mcp_server.consts import (
    ERROR_STATIC_STORAGE_REQUIRES_CAPACITY,
)
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, model_validator
from typing import List, Optional


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
