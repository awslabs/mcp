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

"""Analysis data models for cost analysis, recommendations, and aggregation."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class TimeUnit(str, Enum):
    """Time units for timeline visualization."""

    SECONDS = 'sec'
    MINUTES = 'min'
    HOURS = 'hr'
    DAYS = 'day'


class TaskCostMetrics(BaseModel):
    """Cost and recommendation metrics for a task."""

    taskName: str
    taskArn: str
    instanceType: str
    runningSeconds: float
    estimatedUSD: float
    recommendedInstanceType: str
    recommendedCpus: int
    recommendedMemoryGiB: float
    minimumUSD: float
    potentialSavingsUSD: float
    isHighPrioritySaving: bool = Field(description='True if savings exceed 10% of original cost')


class RunCostSummary(BaseModel):
    """Cost summary for a workflow run."""

    runId: str
    runName: str
    totalEstimatedUSD: float
    taskCostUSD: float
    storageCostUSD: float
    totalPotentialSavingsUSD: float
    peakConcurrentCpus: float
    peakConcurrentMemoryGiB: float
    averageConcurrentCpus: float
    averageConcurrentMemoryGiB: float


class AggregatedTaskMetrics(BaseModel):
    """Aggregated metrics for scattered tasks."""

    baseTaskName: str
    count: int
    meanRunningSeconds: float
    maximumRunningSeconds: float
    stdDevRunningSeconds: Optional[float] = None
    maximumCpuUtilizationRatio: float
    meanCpuUtilizationRatio: float
    maximumMemoryUtilizationRatio: float
    meanMemoryUtilizationRatio: float
    recommendedCpus: int
    recommendedMemoryGiB: float
    recommendedInstanceType: str
    totalEstimatedUSD: float
    meanEstimatedUSD: float
    maximumEstimatedUSD: float


class CrossRunAggregate(BaseModel):
    """Cross-run aggregate metrics."""

    baseTaskName: str
    runCount: int
    totalTaskCount: int
    meanRunningSeconds: float
    maximumRunningSeconds: float
    meanCpuUtilizationRatio: float
    meanMemoryUtilizationRatio: float
    totalEstimatedUSD: float
    recommendedInstanceType: str
