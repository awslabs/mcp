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

"""Data models for Amazon Connect realtime metric tools."""

from pydantic import BaseModel, Field
from typing import Dict, List


class CurrentMetricValue(BaseModel):
    """A single current (realtime) metric value."""

    name: str = Field(..., description='The name of the metric (e.g., CONTACTS_IN_QUEUE)')
    unit: str = Field(..., description='The unit of the metric (COUNT, SECONDS, PERCENT)')
    value: float | None = Field(default=None, description='The current value of the metric')


class CurrentMetricResult(BaseModel):
    """A grouped set of current metric values for a dimension (e.g., a queue)."""

    dimensions: Dict[str, str] = Field(
        default_factory=dict,
        description='The dimensions for this result (e.g., queue id/arn, channel)',
    )
    collections: List[CurrentMetricValue] = Field(
        default_factory=list, description='The metric values for this dimension'
    )


class CurrentMetricDataResponse(BaseModel):
    """Response containing realtime metric data from Amazon Connect."""

    instance_id: str = Field(..., description='The Connect instance the metrics belong to')
    data_snapshot_time: str | None = Field(
        default=None, description='ISO 8601 timestamp of when the metrics were sampled'
    )
    results: List[CurrentMetricResult] = Field(
        default_factory=list, description='The grouped current metric results'
    )
    has_more_results: bool = Field(
        default=False, description='Whether more results are available than were returned'
    )
    message: str | None = Field(None, description='Informational message about the results')


class AgentRealtimeStatus(BaseModel):
    """Realtime status snapshot for a single agent."""

    agent_id: str | None = Field(default=None, description='The identifier of the agent')
    agent_arn: str | None = Field(default=None, description='The ARN of the agent (user)')
    status_name: str | None = Field(
        default=None, description='The current agent status name (e.g., Available, Offline)'
    )
    status_start_timestamp: str | None = Field(
        default=None, description='ISO 8601 timestamp when the current status started'
    )
    routing_profile_name: str | None = Field(
        default=None, description='The routing profile assigned to the agent'
    )
    available_slots_by_channel: Dict[str, int] = Field(
        default_factory=dict, description='Available concurrency slots per channel'
    )
    active_contacts: int = Field(
        default=0, description='Number of contacts currently handled by the agent'
    )


class AgentRealtimeStatusResponse(BaseModel):
    """Response containing realtime agent status data from Amazon Connect."""

    instance_id: str = Field(..., description='The Connect instance the data belongs to')
    agents: List[AgentRealtimeStatus] = Field(
        default_factory=list, description='Realtime status of agents'
    )
    has_more_results: bool = Field(
        default=False, description='Whether more agents are available than were returned'
    )
    message: str | None = Field(None, description='Informational message about the results')
