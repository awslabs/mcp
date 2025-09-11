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

"""Pydantic models for AWS Security Hub MCP Server."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Finding(BaseModel):
    """Represents a Security Hub finding."""

    id: str = Field(description='The finding ID')
    product_arn: str = Field(description='The ARN of the product that generated the finding')
    generator_id: str = Field(
        description='The identifier for the solution-specific component that generated the finding'
    )
    aws_account_id: str = Field(description='The AWS account ID that the finding belongs to')
    title: str = Field(description="A finding's title")
    description: str = Field(description="A finding's description")
    severity: Dict[str, Any] = Field(description='The severity of the finding')
    compliance: Optional[Dict[str, Any]] = Field(
        default=None, description='Compliance details for the finding'
    )
    workflow_state: str = Field(description='The workflow state of the finding')
    record_state: str = Field(description='The record state of the finding')
    created_at: datetime = Field(description='The date and time when the finding was created')
    updated_at: datetime = Field(description='The date and time when the finding was last updated')
    resources: List[Dict[str, Any]] = Field(
        description='A set of resource data types that describe the resources that the finding refers to'
    )


class ComplianceCheck(BaseModel):
    """Represents a compliance check result."""

    control_id: str = Field(description='The identifier of the security standard control')
    title: str = Field(description='The title of the control')
    description: str = Field(description='The description of the control')
    compliance_status: str = Field(description='The compliance status of the control')
    severity_rating: str = Field(description='The severity rating of the control')
    workflow_status: str = Field(description='The workflow status of the control')
    updated_at: datetime = Field(description='The date and time when the control was last updated')


class SecurityStandard(BaseModel):
    """Represents a security standard."""

    standards_arn: str = Field(description='The ARN of the standard')
    name: str = Field(description='The name of the standard')
    description: str = Field(description='The description of the standard')
    enabled_by_default: bool = Field(description='Whether the standard is enabled by default')


class Insight(BaseModel):
    """Represents a Security Hub insight."""

    insight_arn: str = Field(description='The ARN of the insight')
    name: str = Field(description='The name of the insight')
    filters: Dict[str, Any] = Field(
        description='The filters used to identify the findings that the insight applies to'
    )
    group_by_attribute: str = Field(
        description="The grouping attribute for the insight's findings"
    )


class FindingFilter(BaseModel):
    """Represents filters for finding queries."""

    product_arn: Optional[List[str]] = Field(
        default=None, description='The ARN of the product that generated the finding'
    )
    aws_account_id: Optional[List[str]] = Field(
        default=None, description='The AWS account ID that the finding belongs to'
    )
    generator_id: Optional[List[str]] = Field(
        default=None, description='The identifier for the solution-specific component'
    )
    severity_label: Optional[List[str]] = Field(
        default=None, description='The severity label of the finding'
    )
    compliance_status: Optional[List[str]] = Field(
        default=None, description='The compliance status of the finding'
    )
    workflow_state: Optional[List[str]] = Field(
        default=None, description='The workflow state of the finding'
    )
    record_state: Optional[List[str]] = Field(
        default=None, description='The record state of the finding'
    )
    resource_type: Optional[List[str]] = Field(
        default=None, description='The type of resource that the finding refers to'
    )
    resource_id: Optional[List[str]] = Field(
        default=None, description='The identifier of the resource that the finding refers to'
    )
    title: Optional[List[str]] = Field(default=None, description="A finding's title")
    created_at_start: Optional[datetime] = Field(
        default=None, description='Start date for finding creation time filter'
    )
    created_at_end: Optional[datetime] = Field(
        default=None, description='End date for finding creation time filter'
    )
    updated_at_start: Optional[datetime] = Field(
        default=None, description='Start date for finding update time filter'
    )
    updated_at_end: Optional[datetime] = Field(
        default=None, description='End date for finding update time filter'
    )
