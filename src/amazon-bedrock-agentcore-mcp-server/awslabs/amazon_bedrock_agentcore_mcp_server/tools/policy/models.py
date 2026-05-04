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

"""Pydantic response models for AgentCore Policy tools."""

from pydantic import BaseModel, Field
from typing import Any


class ErrorResponse(BaseModel):
    """Structured error response returned when an API call fails."""

    status: str = Field(default='error', description='Always "error"')
    message: str = Field(..., description='Human-readable error message')
    error_type: str = Field(default='Unknown', description='Error code or exception type')
    error_code: str = Field(default='', description='HTTP status code if available')


class PolicyEngineResponse(BaseModel):
    """Response for single policy engine operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_engine: dict[str, Any] = Field(
        default_factory=dict, description='Policy engine resource details'
    )


class DeletePolicyEngineResponse(BaseModel):
    """Response for delete_policy_engine."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_engine_id: str = Field(default='', description='Deleted policy engine ID')
    policy_engine_status: str = Field(
        default='', description='Policy engine status after deletion'
    )


class ListPolicyEnginesResponse(BaseModel):
    """Response for list_policy_engines."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_engines: list[dict[str, Any]] = Field(
        default_factory=list, description='List of policy engine summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class PolicyResponse(BaseModel):
    """Response for single policy operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy: dict[str, Any] = Field(default_factory=dict, description='Policy resource details')


class DeletePolicyResponse(BaseModel):
    """Response for delete_policy."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_id: str = Field(default='', description='Deleted policy ID')
    policy_status: str = Field(default='', description='Policy status after deletion')


class ListPoliciesResponse(BaseModel):
    """Response for list_policies."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policies: list[dict[str, Any]] = Field(
        default_factory=list, description='List of policy summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class PolicyGenerationResponse(BaseModel):
    """Response for single policy generation operations (start, get)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_generation: dict[str, Any] = Field(
        default_factory=dict, description='Policy generation details'
    )


class ListPolicyGenerationsResponse(BaseModel):
    """Response for list_policy_generations."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_generations: list[dict[str, Any]] = Field(
        default_factory=list, description='List of policy generation summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class ListPolicyGenerationAssetsResponse(BaseModel):
    """Response for list_policy_generation_assets."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    policy_generation_assets: list[dict[str, Any]] = Field(
        default_factory=list, description='List of generated policy asset details'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class PolicyGuideResponse(BaseModel):
    """Response for get_policy_guide."""

    guide: str = Field(..., description='The comprehensive Policy reference guide')
