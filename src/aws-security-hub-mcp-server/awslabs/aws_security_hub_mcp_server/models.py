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
"""Data models for AWS Security Hub MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SeverityLabel(str, Enum):
    """Security finding severity levels."""
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkflowStatus(str, Enum):
    """Security finding workflow status."""
    NEW = "NEW"
    NOTIFIED = "NOTIFIED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class ComplianceStatus(str, Enum):
    """Compliance status for findings."""
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class RecordState(str, Enum):
    """Record state for findings."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class SecurityFinding(BaseModel):
    """Represents a Security Hub finding."""
    id: str = Field(description="Unique identifier for the finding")
    product_arn: str = Field(description="ARN of the product that generated the finding")
    generator_id: str = Field(description="ID of the finding generator")
    aws_account_id: str = Field(description="AWS account ID where the finding was generated")
    region: str = Field(description="AWS region where the finding was generated")
    title: str = Field(description="Title of the finding")
    description: str = Field(description="Description of the finding")
    severity_label: SeverityLabel = Field(description="Severity level of the finding")
    severity_score: Optional[float] = Field(description="Numeric severity score (0-100)")
    workflow_status: WorkflowStatus = Field(description="Current workflow status")
    record_state: RecordState = Field(description="Record state of the finding")
    compliance_status: Optional[ComplianceStatus] = Field(description="Compliance status")
    created_at: datetime = Field(description="When the finding was created")
    updated_at: datetime = Field(description="When the finding was last updated")
    resource_type: Optional[str] = Field(description="Type of AWS resource")
    resource_id: Optional[str] = Field(description="ID of the affected resource")
    remediation_url: Optional[str] = Field(description="URL with remediation guidance")
    source_url: Optional[str] = Field(description="URL to the original finding source")


class ComplianceSummary(BaseModel):
    """Summary of compliance status across standards."""
    standard_name: str = Field(description="Name of the security standard")
    standard_arn: str = Field(description="ARN of the security standard")
    enabled: bool = Field(description="Whether the standard is enabled")
    passed_controls: int = Field(description="Number of controls that passed")
    failed_controls: int = Field(description="Number of controls that failed")
    warning_controls: int = Field(description="Number of controls with warnings")
    not_available_controls: int = Field(description="Number of controls not available")
    total_controls: int = Field(description="Total number of controls")
    compliance_percentage: float = Field(description="Overall compliance percentage")


class SecurityInsight(BaseModel):
    """Represents a Security Hub insight."""
    insight_arn: str = Field(description="ARN of the insight")
    name: str = Field(description="Name of the insight")
    filters: Dict[str, Any] = Field(description="Filters used by the insight")
    group_by_attribute: str = Field(description="Attribute used for grouping results")


class FindingStatistics(BaseModel):
    """Statistics about security findings."""
    group_key: str = Field(description="The grouping key (e.g., severity, product)")
    count: int = Field(description="Number of findings in this group")
    percentage: float = Field(description="Percentage of total findings")


class SecurityScore(BaseModel):
    """Overall security score information."""
    current_score: float = Field(description="Current security score (0-100)")
    max_score: float = Field(description="Maximum possible score")
    score_date: datetime = Field(description="Date when the score was calculated")
    control_findings_count: int = Field(description="Number of control findings")
    security_score_percentage: float = Field(description="Security score as percentage")


class StandardControl(BaseModel):
    """Represents a security standard control."""
    control_id: str = Field(description="ID of the control")
    title: str = Field(description="Title of the control")
    description: str = Field(description="Description of the control")
    control_status: str = Field(description="Status of the control (ENABLED/DISABLED)")
    severity_rating: SeverityLabel = Field(description="Severity rating of the control")
    related_requirements: List[str] = Field(description="Related compliance requirements")


class UpdateFindingRequest(BaseModel):
    """Request to update finding workflow status."""
    finding_identifiers: List[str] = Field(description="List of finding ARNs to update")
    workflow_status: WorkflowStatus = Field(description="New workflow status")
    note: Optional[str] = Field(description="Note to add to the finding")