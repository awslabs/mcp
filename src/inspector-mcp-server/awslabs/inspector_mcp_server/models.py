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
    inspector_score_details: Optional[Dict[str, Any]] = Field(None, alias='inspectorScoreDetails')
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


class CvssMetrics(BaseModel):
    """Model for CVSS score breakdown."""

    base_score: Optional[float] = None
    base_severity: Optional[str] = None
    vector_string: Optional[str] = None
    attack_vector: Optional[str] = None
    attack_complexity: Optional[str] = None
    privileges_required: Optional[str] = None
    user_interaction: Optional[str] = None
    scope: Optional[str] = None
    confidentiality_impact: Optional[str] = None
    integrity_impact: Optional[str] = None
    availability_impact: Optional[str] = None
    exploitability_score: Optional[float] = None
    impact_score: Optional[float] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class CveReference(BaseModel):
    """Model for a CVE reference link."""

    url: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class AffectedVersion(BaseModel):
    """Model for an affected product version range."""

    criteria: Optional[str] = None
    version_start_including: Optional[str] = None
    version_end_excluding: Optional[str] = None
    version_end_including: Optional[str] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class CveDetails(BaseModel):
    """Model for full CVE information from NVD."""

    cve_id: str
    description: Optional[str] = None
    published: Optional[str] = None
    last_modified: Optional[str] = None
    nvd_url: str
    cvss_v31: Optional[CvssMetrics] = None
    cvss_v2: Optional[CvssMetrics] = None
    weaknesses: Optional[List[str]] = None
    affected_versions: Optional[List[AffectedVersion]] = None
    references: Optional[List[CveReference]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class FindingExplanation(BaseModel):
    """Model for an explained Inspector finding with CVE enrichment."""

    finding_arn: str
    title: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    finding_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    inspector_score: Optional[float] = None
    exploit_available: Optional[str] = None
    fix_available: Optional[str] = None
    remediation: Optional[Dict[str, Any]] = None
    cve_details: Optional[CveDetails] = None
    cve_ids: Optional[List[str]] = None
    cve_links: Optional[List[str]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class SecuritySummary(BaseModel):
    """Model for a security posture summary report."""

    generated_at: str
    region: str
    account_status: Optional[Dict] = None
    coverage_statistics: Optional[Dict] = None
    finding_counts_by_severity: Optional[Dict] = None
    top_critical_findings: Optional[List[Dict]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class DigestFinding(BaseModel):
    """Model for a single finding entry within a findings digest."""

    finding_arn: Optional[str] = None
    title: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    inspector_score: Optional[float] = None
    exploit_available: Optional[str] = None
    fix_available: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    cve_ids: Optional[List[str]] = None
    cve_links: Optional[List[str]] = None
    remediation: Optional[Dict[str, Any]] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class FindingsDigest(BaseModel):
    """Model for a findings digest report over a time range."""

    generated_at: str
    region: str
    time_range: Dict[str, str]
    total_findings: int
    severity_breakdown: Dict[str, int]
    findings: List[DigestFinding]

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
    inspector_score_details: Optional[Dict[str, Any]] = Field(None, alias='inspectorScoreDetails')
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
