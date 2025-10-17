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

"""Pydantic models for AWS Security MCP Server."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    """Response status enumeration."""

    SUCCESS = "success"
    ERROR = "error"


class ServiceName(str, Enum):
    """AWS service names."""

    GUARDDUTY = "GuardDuty"
    SECURITY_HUB = "SecurityHub"
    AWS_STS = "AWS STS"


class GuardDutyFinding(BaseModel):
    """GuardDuty finding model."""

    id: str = Field(..., description="Unique identifier for the finding")
    type: str = Field(..., description="Type of threat detected")
    severity: float = Field(..., description="Severity score of the finding")


class SecurityHubFinding(BaseModel):
    """Security Hub finding model."""

    title: str = Field(..., description="Title of the security finding")
    severity: str = Field(..., description="Severity level of the finding")
    resource: str = Field(..., description="AWS resource affected by the finding")
    workflow_status: str = Field(..., description="Current workflow status")


class McpResponse(BaseModel):
    """Standard MCP response format."""

    status: ResponseStatus = Field(..., description="Response status")
    service: ServiceName = Field(..., description="AWS service name")
    data: dict[str, Any] = Field(..., description="Response data")


class HealthCheckData(BaseModel):
    """Health check response data."""

    aws_account: str = Field(..., description="AWS account ID")
    aws_user_arn: str = Field(..., description="AWS user ARN")
    aws_profile: str = Field(..., description="AWS profile being used")


class FindingsData(BaseModel):
    """Findings response data."""

    findings: list[dict[str, Any]] = Field(..., description="List of findings")
    total_count: int = Field(..., description="Total number of findings")
    message: str | None = Field(None, description="Optional message")
