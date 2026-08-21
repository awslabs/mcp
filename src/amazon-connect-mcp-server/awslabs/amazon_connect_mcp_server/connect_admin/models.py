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

"""Data models for Amazon Connect administration / discovery tools."""

from pydantic import BaseModel, Field
from typing import List


class InstanceSummary(BaseModel):
    """Summary information for an Amazon Connect instance."""

    instance_id: str = Field(..., description='The identifier of the Connect instance')
    instance_arn: str = Field(..., description='The ARN of the Connect instance')
    instance_alias: str | None = Field(default=None, description='The alias of the instance')
    service_role: str | None = Field(default=None, description='The service role of the instance')
    instance_status: str | None = Field(default=None, description='The state of the instance')


class ListInstancesResponse(BaseModel):
    """Response containing Amazon Connect instances."""

    instances: List[InstanceSummary] = Field(
        default_factory=list, description='List of Connect instances'
    )
    message: str | None = Field(None, description='Informational message about the results')


class QueueSummary(BaseModel):
    """Summary information for an Amazon Connect queue."""

    queue_id: str = Field(..., description='The identifier of the queue')
    queue_arn: str = Field(..., description='The ARN of the queue')
    name: str | None = Field(default=None, description='The name of the queue')
    queue_type: str | None = Field(
        default=None, description='The type of the queue (STANDARD or AGENT)'
    )


class ListQueuesResponse(BaseModel):
    """Response containing Amazon Connect queues."""

    queues: List[QueueSummary] = Field(default_factory=list, description='List of queues')
    has_more_results: bool = Field(
        default=False, description='Whether more queues are available than the requested max_items'
    )
    message: str | None = Field(None, description='Informational message about the results')


class AgentSummary(BaseModel):
    """Summary information for an Amazon Connect agent (user)."""

    user_id: str = Field(..., description='The identifier of the user')
    user_arn: str = Field(..., description='The ARN of the user')
    username: str | None = Field(default=None, description='The login name of the user')


class ListAgentsResponse(BaseModel):
    """Response containing Amazon Connect agents (users)."""

    agents: List[AgentSummary] = Field(default_factory=list, description='List of agents')
    has_more_results: bool = Field(
        default=False, description='Whether more agents are available than the requested max_items'
    )
    message: str | None = Field(None, description='Informational message about the results')


class RoutingProfileSummary(BaseModel):
    """Summary information for an Amazon Connect routing profile."""

    routing_profile_id: str = Field(..., description='The identifier of the routing profile')
    routing_profile_arn: str = Field(..., description='The ARN of the routing profile')
    name: str | None = Field(default=None, description='The name of the routing profile')


class ListRoutingProfilesResponse(BaseModel):
    """Response containing Amazon Connect routing profiles."""

    routing_profiles: List[RoutingProfileSummary] = Field(
        default_factory=list, description='List of routing profiles'
    )
    has_more_results: bool = Field(
        default=False, description='Whether more routing profiles are available'
    )
    message: str | None = Field(None, description='Informational message about the results')
