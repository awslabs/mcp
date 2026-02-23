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

"""Pydantic models for Inspector MCP Server."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Any, Dict, List, Optional


class Finding(BaseModel):
    """Model for an Inspector finding."""

    finding_arn: Optional[str] = Field(None, alias='findingArn')
    aws_account_id: Optional[str] = Field(None, alias='awsAccountId')
    description: Optional[str] = Field(None, alias='description')
    first_observed_at: Optional[datetime] = Field(None, alias='firstObservedAt')
    last_observed_at: Optional[datetime] = Field(None, alias='lastObservedAt')
    remediation: Optional[Dict[str, Any]] = Field(None, alias='remediation')
    resources: Optional[List[Dict[str, Any]]] = Field(None, alias='resources')
    severity: Optional[str] = Field(None, alias='severity')
    status: Optional[str] = Field(None, alias='status')
    title: Optional[str] = Field(None, alias='title')
    type: Optional[str] = Field(None, alias='type')
    inspector_score: Optional[float] = Field(None, alias='inspectorScore')
    inspector_score_details: Optional[Dict[str, Any]] = Field(
        None, alias='inspectorScoreDetails'
    )
    network_reachability_details: Optional[Dict[str, Any]] = Field(
        None, alias='networkReachabilityDetails'
    )
    package_vulnerability_details: Optional[Dict[str, Any]] = Field(
        None, alias='packageVulnerabilityDetails'
    )
    code_vulnerability_details: Optional[Dict[str, Any]] = Field(
        None, alias='codeVulnerabilityDetails'
    )
    exploit_available: Optional[str] = Field(None, alias='exploitAvailable')
    fix_available: Optional[str] = Field(None, alias='fixAvailable')
    updated_at: Optional[datetime] = Field(None, alias='updatedAt')

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer('first_observed_at', 'last_observed_at', 'updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class FindingDetail(BaseModel):
    """Model for a detailed Inspector finding from batch_get_findings."""

    finding_arn: Optional[str] = Field(None, alias='findingArn')
    aws_account_id: Optional[str] = Field(None, alias='awsAccountId')
    description: Optional[str] = Field(None, alias='description')
    first_observed_at: Optional[datetime] = Field(None, alias='firstObservedAt')
    last_observed_at: Optional[datetime] = Field(None, alias='lastObservedAt')
    remediation: Optional[Dict[str, Any]] = Field(None, alias='remediation')
    resources: Optional[List[Dict[str, Any]]] = Field(None, alias='resources')
    severity: Optional[str] = Field(None, alias='severity')
    status: Optional[str] = Field(None, alias='status')
    title: Optional[str] = Field(None, alias='title')
    type: Optional[str] = Field(None, alias='type')
    inspector_score: Optional[float] = Field(None, alias='inspectorScore')
    inspector_score_details: Optional[Dict[str, Any]] = Field(
        None, alias='inspectorScoreDetails'
    )
    network_reachability_details: Optional[Dict[str, Any]] = Field(
        None, alias='networkReachabilityDetails'
    )
    package_vulnerability_details: Optional[Dict[str, Any]] = Field(
        None, alias='packageVulnerabilityDetails'
    )
    code_vulnerability_details: Optional[Dict[str, Any]] = Field(
        None, alias='codeVulnerabilityDetails'
    )
    exploit_available: Optional[str] = Field(None, alias='exploitAvailable')
    fix_available: Optional[str] = Field(None, alias='fixAvailable')
    updated_at: Optional[datetime] = Field(None, alias='updatedAt')

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer('first_observed_at', 'last_observed_at', 'updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class FindingAggregation(BaseModel):
    """Model for Inspector finding aggregation results."""

    aggregation_type: str
    counts: Optional[List[Dict[str, Any]]] = None
    next_token: Optional[str] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class CoverageResource(BaseModel):
    """Model for an Inspector coverage resource."""

    account_id: Optional[str] = Field(None, alias='accountId')
    resource_id: Optional[str] = Field(None, alias='resourceId')
    resource_type: Optional[str] = Field(None, alias='resourceType')
    scan_status: Optional[Dict[str, str]] = Field(None, alias='scanStatus')
    scan_type: Optional[str] = Field(None, alias='scanType')
    resource_metadata: Optional[Dict[str, Any]] = Field(None, alias='resourceMetadata')

    model_config = ConfigDict(populate_by_name=True)

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class AccountStatus(BaseModel):
    """Model for Inspector account status."""

    account_id: Optional[str] = Field(None, alias='accountId')
    resource_state: Optional[Dict[str, Any]] = Field(None, alias='resourceState')
    state: Optional[Dict[str, str]] = Field(None, alias='state')

    model_config = ConfigDict(populate_by_name=True)

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class ReportResult(BaseModel):
    """Model for Inspector findings report result."""

    report_id: str
    status: Optional[str] = None
    error_message: Optional[str] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    report_format: Optional[str] = None
    s3_destination: Optional[Dict[str, str]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)
