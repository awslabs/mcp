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

"""Pydantic models for Amazon Bedrock Agent Core MCP Server."""

from .consts import (
    DEFAULT_AWS_REGION,
    GATEWAY_TARGET_LAMBDA,
    GATEWAY_TARGET_OPENAPI,
    GATEWAY_TARGET_SMITHY,
    MEMORY_STRATEGY_EPISODIC,
    MEMORY_STRATEGY_SEMANTIC,
    MEMORY_STRATEGY_SUMMARY,
    STATUS_ACTIVE,
    STATUS_CREATING,
    STATUS_DELETING,
    STATUS_FAILED,
    STATUS_UPDATING,
)
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional


class AgentStatus(str, Enum):
    """Agent deployment status enumeration."""

    ACTIVE = STATUS_ACTIVE
    CREATING = STATUS_CREATING
    UPDATING = STATUS_UPDATING
    DELETING = STATUS_DELETING
    FAILED = STATUS_FAILED


class MemoryStrategy(str, Enum):
    """Memory strategy types for agent memory."""

    SEMANTIC = MEMORY_STRATEGY_SEMANTIC
    SUMMARY = MEMORY_STRATEGY_SUMMARY
    EPISODIC = MEMORY_STRATEGY_EPISODIC


class GatewayTargetType(str, Enum):
    """Gateway target type enumeration."""

    LAMBDA = GATEWAY_TARGET_LAMBDA
    OPENAPI_SCHEMA = GATEWAY_TARGET_OPENAPI
    SMITHY_MODEL = GATEWAY_TARGET_SMITHY


class CredentialProviderType(str, Enum):
    """Credential provider type enumeration."""

    API_KEY = 'API_KEY'  # pragma: allowlist secret
    OAUTH = 'OAUTH'
    CUSTOM = 'CUSTOM'


class AgentConfig(BaseModel):
    """Configuration for an AgentCore agent."""

    name: str = Field(description='Agent name')
    description: Optional[str] = Field(default=None, description='Agent description')
    region: str = Field(default=DEFAULT_AWS_REGION, description='AWS region')
    enable_oauth: bool = Field(default=False, description='Enable OAuth authentication')
    memory_enabled: bool = Field(default=False, description='Enable memory capabilities')

    @field_validator('name')
    def validate_name(cls, v):
        """Ensure agent name is not empty."""
        if not v or not v.strip():
            raise ValueError('Agent name cannot be empty')
        return v


class GatewayConfig(BaseModel):
    """Configuration for an AgentCore gateway."""

    name: str = Field(description='Gateway name')
    target_type: GatewayTargetType = Field(description='Gateway target type')
    description: Optional[str] = Field(default=None, description='Gateway description')
    region: str = Field(default=DEFAULT_AWS_REGION, description='AWS region')
    smithy_model: Optional[str] = Field(
        default=None, description='Smithy model name for AWS services'
    )
    openapi_spec: Optional[Dict[str, Any]] = Field(
        default=None, description='OpenAPI specification'
    )
    api_key: Optional[str] = Field(
        default=None, description='API key for authentication'
    )  # pragma: allowlist secret


class DeploymentResult(BaseModel):
    """Result of an agent deployment operation."""

    success: bool = Field(description='Whether deployment succeeded')
    agent_name: str = Field(description='Agent name')
    agent_arn: Optional[str] = Field(default=None, description='Agent ARN if successful')
    message: str = Field(description='Deployment message')
    oauth_enabled: bool = Field(default=False, description='Whether OAuth is enabled')
