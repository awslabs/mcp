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

"""Pydantic models for GuardDuty MCP responses."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class GuardDutyDetector(BaseModel):
    """GuardDuty detector metadata."""

    detector_id: str = Field(..., description='The GuardDuty detector ID')
    region: Optional[str] = Field(None, description='The AWS region used for the request')


class GuardDutyFinding(BaseModel):
    """LLM-friendly subset of a GuardDuty finding."""

    account_id: Optional[str] = Field(None, description='AWS account associated with the finding')
    arn: Optional[str] = Field(None, description='Finding ARN')
    confidence: Optional[float] = Field(None, description='GuardDuty confidence score')
    created_at: Optional[str] = Field(None, description='Finding creation timestamp')
    description: Optional[str] = Field(None, description='Finding description')
    finding_id: str = Field(..., description='GuardDuty finding ID')
    region: Optional[str] = Field(None, description='AWS region for the finding')
    resource_type: Optional[str] = Field(None, description='Primary resource type involved')
    resource: Dict[str, Any] = Field(default_factory=dict, description='Raw resource object')
    service: Dict[str, Any] = Field(default_factory=dict, description='Raw service object')
    severity: Optional[float] = Field(None, description='GuardDuty severity score')
    title: Optional[str] = Field(None, description='Finding title')
    type: Optional[str] = Field(None, description='Finding type')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')


class GuardDutyFindingSummary(BaseModel):
    """Compact summary of a finding for list responses."""

    finding_id: str = Field(..., description='GuardDuty finding ID')
    severity: Optional[float] = Field(None, description='GuardDuty severity score')
    title: Optional[str] = Field(None, description='Finding title')
    type: Optional[str] = Field(None, description='Finding type')
    region: Optional[str] = Field(None, description='AWS region for the finding')
    account_id: Optional[str] = Field(None, description='AWS account associated with the finding')
    resource_type: Optional[str] = Field(None, description='Primary resource type involved')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')


class ListDetectorsResponse(BaseModel):
    """Response for listing GuardDuty detectors."""

    detectors: List[GuardDutyDetector] = Field(default_factory=list)
    count: int = Field(..., description='Number of detectors returned')


class ListFindingsResponse(BaseModel):
    """Response for listing GuardDuty findings."""

    detector_id: str = Field(..., description='Detector used for the request')
    finding_ids: List[str] = Field(default_factory=list, description='Finding IDs from GuardDuty')
    findings: List[GuardDutyFindingSummary] = Field(
        default_factory=list, description='Summaries for returned findings'
    )
    count: int = Field(..., description='Number of findings returned')
    next_token: Optional[str] = Field(None, description='Pagination token for the next page')


class GetFindingsResponse(BaseModel):
    """Response for fetching full GuardDuty findings."""

    detector_id: str = Field(..., description='Detector used for the request')
    findings: List[GuardDutyFinding] = Field(default_factory=list)
    count: int = Field(..., description='Number of findings returned')
