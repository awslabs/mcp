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

"""Pydantic response models for AgentCore Runtime MCP tools."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Shared
# ------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Structured error returned by any Runtime tool on failure."""

    status: str = 'error'
    message: str = ''
    error_type: str = 'Unknown'
    error_code: str = ''


# ------------------------------------------------------------------
# Runtime lifecycle
# ------------------------------------------------------------------


class CreateRuntimeResponse(BaseModel):
    """Response from create_agent_runtime."""

    status: str
    agent_runtime_arn: str = ''
    agent_runtime_id: str = ''
    agent_runtime_version: str = ''
    created_at: str = ''
    workload_identity_arn: str = ''
    message: str = ''


class GetRuntimeResponse(BaseModel):
    """Response from get_agent_runtime."""

    status: str
    agent_runtime_arn: str = ''
    agent_runtime_id: str = ''
    agent_runtime_name: str = ''
    agent_runtime_version: str = ''
    description: str = ''
    role_arn: str = ''
    runtime_status: str = ''
    failure_reason: str = ''
    created_at: str = ''
    last_updated_at: str = ''
    protocol: str = ''
    network_mode: str = ''
    lifecycle_configuration: Optional[Dict[str, Any]] = None
    environment_variables: Optional[Dict[str, str]] = None
    workload_identity_arn: str = ''
    message: str = ''


class UpdateRuntimeResponse(BaseModel):
    """Response from update_agent_runtime."""

    status: str
    agent_runtime_arn: str = ''
    agent_runtime_id: str = ''
    agent_runtime_version: str = ''
    last_updated_at: str = ''
    message: str = ''


class DeleteRuntimeResponse(BaseModel):
    """Response from delete_agent_runtime."""

    status: str
    agent_runtime_id: str = ''
    runtime_status: str = ''
    message: str = ''


class RuntimeSummary(BaseModel):
    """Summary of a single runtime in list results."""

    agent_runtime_arn: str = ''
    agent_runtime_id: str = ''
    agent_runtime_name: str = ''
    agent_runtime_version: str = ''
    description: str = ''
    last_updated_at: str = ''
    runtime_status: str = ''


class ListRuntimesResponse(BaseModel):
    """Response from list_agent_runtimes."""

    status: str
    runtimes: List[RuntimeSummary] = Field(default_factory=list)
    next_token: Optional[str] = None
    message: str = ''


class ListRuntimeVersionsResponse(BaseModel):
    """Response from list_agent_runtime_versions."""

    status: str
    versions: List[RuntimeSummary] = Field(default_factory=list)
    next_token: Optional[str] = None
    message: str = ''


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


class CreateEndpointResponse(BaseModel):
    """Response from create_agent_runtime_endpoint."""

    status: str
    agent_runtime_endpoint_arn: str = ''
    agent_runtime_id: str = ''
    endpoint_name: str = ''
    endpoint_status: str = ''
    target_version: str = ''
    created_at: str = ''
    message: str = ''


class GetEndpointResponse(BaseModel):
    """Response from get_agent_runtime_endpoint."""

    status: str
    agent_runtime_endpoint_arn: str = ''
    agent_runtime_arn: str = ''
    endpoint_id: str = ''
    endpoint_name: str = ''
    description: str = ''
    endpoint_status: str = ''
    live_version: str = ''
    target_version: str = ''
    failure_reason: str = ''
    created_at: str = ''
    last_updated_at: str = ''
    message: str = ''


class UpdateEndpointResponse(BaseModel):
    """Response from update_agent_runtime_endpoint."""

    status: str
    agent_runtime_endpoint_arn: str = ''
    endpoint_status: str = ''
    live_version: str = ''
    target_version: str = ''
    message: str = ''


class DeleteEndpointResponse(BaseModel):
    """Response from delete_agent_runtime_endpoint."""

    status: str
    agent_runtime_id: str = ''
    endpoint_name: str = ''
    endpoint_status: str = ''
    message: str = ''


class EndpointSummary(BaseModel):
    """Summary of a single endpoint in list results."""

    agent_runtime_endpoint_arn: str = ''
    name: str = ''
    endpoint_id: str = ''
    live_version: str = ''
    target_version: str = ''
    endpoint_status: str = ''
    description: str = ''
    created_at: str = ''
    last_updated_at: str = ''


class ListEndpointsResponse(BaseModel):
    """Response from list_agent_runtime_endpoints."""

    status: str
    endpoints: List[EndpointSummary] = Field(default_factory=list)
    next_token: Optional[str] = None
    message: str = ''


# ------------------------------------------------------------------
# Invocation / Sessions (data plane)
# ------------------------------------------------------------------


class InvokeRuntimeResponse(BaseModel):
    """Response from invoke_agent_runtime."""

    status: str
    runtime_session_id: str = ''
    content_type: str = ''
    response_body: str = ''
    message: str = ''


class StopSessionResponse(BaseModel):
    """Response from stop_runtime_session."""

    status: str
    runtime_session_id: str = ''
    message: str = ''


# ------------------------------------------------------------------
# Guide
# ------------------------------------------------------------------


class GuideResponse(BaseModel):
    """Response from get_runtime_guide."""

    status: str = 'success'
    guide: str = ''
