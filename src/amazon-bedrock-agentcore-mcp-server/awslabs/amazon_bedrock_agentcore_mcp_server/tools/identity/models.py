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

"""Pydantic response models for AgentCore Identity tools."""

from pydantic import BaseModel, Field
from typing import Any


class ErrorResponse(BaseModel):
    """Structured error response returned when an API call fails."""

    status: str = Field(default='error', description='Always "error"')
    message: str = Field(..., description='Human-readable error message')
    error_type: str = Field(default='Unknown', description='Error code or exception type')
    error_code: str = Field(default='', description='HTTP status code if available')


# ---------------------------------------------------------------------------
# Workload Identity response models
# ---------------------------------------------------------------------------


class WorkloadIdentityResponse(BaseModel):
    """Response for single-workload-identity operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    workload_identity: dict[str, Any] = Field(
        default_factory=dict, description='Workload identity details'
    )


class DeleteWorkloadIdentityResponse(BaseModel):
    """Response for delete_workload_identity."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    name: str = Field(default='', description='Deleted workload identity name')


class ListWorkloadIdentitiesResponse(BaseModel):
    """Response for list_workload_identities."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    workload_identities: list[dict[str, Any]] = Field(
        default_factory=list, description='List of workload identity summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


# ---------------------------------------------------------------------------
# API Key credential provider response models
# ---------------------------------------------------------------------------


class ApiKeyProviderResponse(BaseModel):
    """Response for single API-key credential provider operations."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    provider: dict[str, Any] = Field(
        default_factory=dict, description='API key credential provider details'
    )


class DeleteApiKeyProviderResponse(BaseModel):
    """Response for delete_api_key_credential_provider."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    name: str = Field(default='', description='Deleted provider name')


class ListApiKeyProvidersResponse(BaseModel):
    """Response for list_api_key_credential_providers."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    providers: list[dict[str, Any]] = Field(
        default_factory=list, description='List of API key credential provider summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


# ---------------------------------------------------------------------------
# OAuth2 credential provider response models
# ---------------------------------------------------------------------------


class Oauth2ProviderResponse(BaseModel):
    """Response for single OAuth2 credential provider operations."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    provider: dict[str, Any] = Field(
        default_factory=dict, description='OAuth2 credential provider details'
    )


class DeleteOauth2ProviderResponse(BaseModel):
    """Response for delete_oauth2_credential_provider."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    name: str = Field(default='', description='Deleted provider name')


class ListOauth2ProvidersResponse(BaseModel):
    """Response for list_oauth2_credential_providers."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    providers: list[dict[str, Any]] = Field(
        default_factory=list, description='List of OAuth2 credential provider summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


# ---------------------------------------------------------------------------
# Token vault response models
# ---------------------------------------------------------------------------


class TokenVaultResponse(BaseModel):
    """Response for get_token_vault and set_token_vault_cmk."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    token_vault: dict[str, Any] = Field(
        default_factory=dict, description='Token vault details including KMS config'
    )


# ---------------------------------------------------------------------------
# Resource policy response models
# ---------------------------------------------------------------------------


class ResourcePolicyResponse(BaseModel):
    """Response for put_resource_policy and get_resource_policy."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    resource_arn: str = Field(default='', description='ARN of the resource')
    policy: dict[str, Any] = Field(default_factory=dict, description='Resource policy document')


class DeleteResourcePolicyResponse(BaseModel):
    """Response for delete_resource_policy."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    resource_arn: str = Field(default='', description='ARN of the resource')


# ---------------------------------------------------------------------------
# Guide response model
# ---------------------------------------------------------------------------


class IdentityGuideResponse(BaseModel):
    """Response for the get_identity_guide tool."""

    status: str = Field(default='success', description='Operation status')
    guide: str = Field(..., description='The comprehensive Identity guide content')
