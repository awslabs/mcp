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

"""Pydantic response models for AgentCore Gateway tools."""

from pydantic import BaseModel, Field
from typing import Any


class ErrorResponse(BaseModel):
    """Structured error response returned when an API call fails."""

    status: str = Field(default='error', description='Always "error"')
    message: str = Field(..., description='Human-readable error message')
    error_type: str = Field(default='Unknown', description='Error code or exception type')
    error_code: str = Field(default='', description='HTTP status code if available')


class GatewayResponse(BaseModel):
    """Response for single-gateway operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    gateway: dict[str, Any] = Field(default_factory=dict, description='Gateway resource details')


class DeleteGatewayResponse(BaseModel):
    """Response for delete_gateway."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    gateway_id: str = Field(default='', description='Deleted gateway ID')
    gateway_status: str = Field(default='', description='Gateway status after deletion')


class ListGatewaysResponse(BaseModel):
    """Response for list_gateways."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    gateways: list[dict[str, Any]] = Field(
        default_factory=list, description='List of gateway summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class GatewayTargetResponse(BaseModel):
    """Response for single gateway-target operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    target: dict[str, Any] = Field(default_factory=dict, description='Gateway target details')


class DeleteGatewayTargetResponse(BaseModel):
    """Response for delete_gateway_target."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    target_id: str = Field(default='', description='Deleted target ID')
    target_status: str = Field(default='', description='Target status after deletion')


class ListGatewayTargetsResponse(BaseModel):
    """Response for list_gateway_targets."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    targets: list[dict[str, Any]] = Field(
        default_factory=list, description='List of target summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class SynchronizeTargetsResponse(BaseModel):
    """Response for synchronize_gateway_targets."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    targets: list[dict[str, Any]] = Field(
        default_factory=list, description='Synchronized target details'
    )


class ResourcePolicyResponse(BaseModel):
    """Response for put/get resource policy operations."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy: str = Field(default='', description='Resource policy document')


class DeleteResourcePolicyResponse(BaseModel):
    """Response for delete_resource_policy."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    resource_arn: str = Field(default='', description='Resource ARN of deleted policy')


class GatewayGuideResponse(BaseModel):
    """Response for get_gateway_guide."""

    status: str = Field(default='success', description='Operation status')
    guide: str = Field(..., description='Comprehensive Gateway guide content')
