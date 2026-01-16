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
    severity_score: float | None = Field(description="Numeric severity score (0-100)")
    workflow_status: WorkflowStatus = Field(description="Current workflow status")
    record_state: RecordState = Field(description="Record state of the finding")
    compliance_status: ComplianceStatus | None = Field(description="Compliance status")
    created_at: datetime = Field(description="When the finding was created")
    updated_at: datetime = Field(description="When the finding was last updated")
    resource_type: str | None = Field(description="Type of AWS resource")
    resource_id: str | None = Field(description="ID of the affected resource")
    remediation_url: str | None = Field(description="URL with remediation guidance")
    source_url: str | None = Field(description="URL to the original finding source")


class FindingStatistics(BaseModel):
    """Statistics about security findings."""

    group_key: str = Field(description="The grouping key (e.g., severity, product)")
    count: int = Field(description="Number of findings in this group")
    percentage: float = Field(description="Percentage of total findings")


class SecurityScore(BaseModel):
    """Overall security score information."""

    current_score: float = Field(description="Current security score (0-100)")
    max_score: float = Field(description="Maximum possible score")
    score_date: str = Field(description="Date when the score was calculated")
    control_findings_count: int = Field(description="Number of control findings")
    security_score_percentage: float = Field(description="Security score as percentage")


class EnabledStandard(BaseModel):
    """Represents an enabled security standard."""

    standards_arn: str = Field(description="ARN of the security standard")
    standards_subscription_arn: str = Field(description="ARN of the standards subscription")
    standards_status: str = Field(description="Status of the standard (ENABLED/DISABLED)")
    standards_status_reason: str | None = Field(description="Reason for the status")
    name: str = Field(description="Name of the security standard")
    description: str | None = Field(description="Description of the security standard")


class SecurityControlDefinition(BaseModel):
    """Represents a security control definition."""

    security_control_id: str = Field(description="ID of the security control")
    title: str = Field(description="Title of the security control")
    description: str = Field(description="Description of the security control")
    remediation_url: str | None = Field(description="URL with remediation guidance")
    severity_rating: SeverityLabel = Field(description="Severity rating of the control")
    current_region_availability: str = Field(description="Availability in current region")
