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
"""Data models for the AWS Trusted Advisor MCP Server."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class RecommendationPillarSpecificAggregates(BaseModel):
    """Pillar-specific aggregation data for a recommendation."""

    cost_optimizing: Optional[Dict[str, Any]] = Field(
        None,
        alias='costOptimizing',
        description='Cost optimization specific aggregates including estimated monthly savings',
    )

    class Config:
        populate_by_name = True


class RecommendationResourcesAggregates(BaseModel):
    """Aggregated resource counts for a recommendation."""

    ok_count: int = Field(0, alias='okCount', description='Number of OK resources')
    warning_count: int = Field(0, alias='warningCount', description='Number of warning resources')
    error_count: int = Field(0, alias='errorCount', description='Number of error resources')

    class Config:
        populate_by_name = True


class RecommendationSummary(BaseModel):
    """Summary of a Trusted Advisor recommendation."""

    arn: str = Field(..., description='The ARN of the recommendation')
    name: str = Field(..., description='The name of the recommendation')
    status: str = Field(..., description='The status: ok, warning, or error')
    pillar: Optional[str] = Field(None, description='The Well-Architected pillar')
    aws_service: Optional[str] = Field(
        None, alias='awsService', description='The related AWS service'
    )
    source: Optional[str] = Field(None, description='The source of the recommendation')
    resources_aggregates: Optional[RecommendationResourcesAggregates] = Field(
        None, alias='resourcesAggregates', description='Aggregated resource counts'
    )
    pillar_specific_aggregates: Optional[RecommendationPillarSpecificAggregates] = Field(
        None, alias='pillarSpecificAggregates', description='Pillar-specific aggregates'
    )
    last_updated_at: Optional[str] = Field(
        None, alias='lastUpdatedAt', description='When the recommendation was last updated'
    )

    class Config:
        populate_by_name = True


class RecommendationDetail(BaseModel):
    """Detailed information about a Trusted Advisor recommendation."""

    arn: str = Field(..., description='The ARN of the recommendation')
    name: str = Field(..., description='The name of the recommendation')
    description: Optional[str] = Field(None, description='A description of the recommendation')
    status: str = Field(..., description='The status: ok, warning, or error')
    pillar: Optional[str] = Field(None, description='The Well-Architected pillar')
    aws_service: Optional[str] = Field(
        None, alias='awsService', description='The related AWS service'
    )
    source: Optional[str] = Field(None, description='The source of the recommendation')
    resources_aggregates: Optional[RecommendationResourcesAggregates] = Field(
        None, alias='resourcesAggregates', description='Aggregated resource counts'
    )
    pillar_specific_aggregates: Optional[RecommendationPillarSpecificAggregates] = Field(
        None, alias='pillarSpecificAggregates', description='Pillar-specific aggregates'
    )
    lifecycle_stage: Optional[str] = Field(
        None, alias='lifecycleStage', description='The lifecycle stage of the recommendation'
    )
    resolved_at: Optional[str] = Field(
        None, alias='resolvedAt', description='When the recommendation was resolved'
    )
    last_updated_at: Optional[str] = Field(
        None, alias='lastUpdatedAt', description='When the recommendation was last updated'
    )
    created_at: Optional[str] = Field(
        None, alias='createdAt', description='When the recommendation was created'
    )
    updated_on_behalf_of: Optional[str] = Field(
        None, alias='updatedOnBehalfOf', description='The principal that last updated the recommendation'
    )
    updated_on_behalf_of_job_title: Optional[str] = Field(
        None,
        alias='updatedOnBehalfOfJobTitle',
        description='The job title of the principal that last updated the recommendation',
    )
    update_reason: Optional[str] = Field(
        None, alias='updateReason', description='The reason for the last update'
    )

    class Config:
        populate_by_name = True


class RecommendationResource(BaseModel):
    """A resource affected by a Trusted Advisor recommendation."""

    arn: str = Field(..., description='The ARN of the resource')
    aws_resource_id: str = Field(
        ..., alias='awsResourceId', description='The AWS resource identifier'
    )
    region_code: str = Field(
        ..., alias='regionCode', description='The AWS region code for the resource'
    )
    status: str = Field(..., description='The status of the resource: ok, warning, or error')
    metadata: Optional[Dict[str, str]] = Field(
        None, description='Additional metadata about the resource'
    )
    last_updated_at: Optional[str] = Field(
        None, alias='lastUpdatedAt', description='When the resource status was last updated'
    )
    recommendation_arn: Optional[str] = Field(
        None, alias='recommendationArn', description='The ARN of the parent recommendation'
    )
    is_excluded_from_recommendation: Optional[bool] = Field(
        None,
        alias='isExcludedFromRecommendation',
        description='Whether the resource is excluded from the recommendation',
    )

    class Config:
        populate_by_name = True


class CheckSummary(BaseModel):
    """Summary of a Trusted Advisor check."""

    arn: str = Field(..., description='The ARN of the check')
    id: str = Field(..., description='The ID of the check')
    name: str = Field(..., description='The name of the check')
    description: Optional[str] = Field(None, description='A description of the check')
    pillar: Optional[str] = Field(None, description='The Well-Architected pillar')
    aws_service: Optional[str] = Field(
        None, alias='awsService', description='The related AWS service'
    )
    source: Optional[str] = Field(None, description='The source of the check')

    class Config:
        populate_by_name = True


class OrganizationRecommendation(BaseModel):
    """Organization-wide recommendation from Trusted Advisor."""

    arn: str = Field(..., description='The ARN of the organization recommendation')
    name: str = Field(..., description='The name of the recommendation')
    status: str = Field(..., description='The status: ok, warning, or error')
    pillar: Optional[str] = Field(None, description='The Well-Architected pillar')
    aws_service: Optional[str] = Field(
        None, alias='awsService', description='The related AWS service'
    )
    source: Optional[str] = Field(None, description='The source of the recommendation')
    resources_aggregates: Optional[RecommendationResourcesAggregates] = Field(
        None, alias='resourcesAggregates', description='Aggregated resource counts'
    )
    pillar_specific_aggregates: Optional[RecommendationPillarSpecificAggregates] = Field(
        None, alias='pillarSpecificAggregates', description='Pillar-specific aggregates'
    )
    lifecycle_stage: Optional[str] = Field(
        None, alias='lifecycleStage', description='The lifecycle stage'
    )
    last_updated_at: Optional[str] = Field(
        None, alias='lastUpdatedAt', description='When the recommendation was last updated'
    )

    class Config:
        populate_by_name = True


class CostOptimizationSummary(BaseModel):
    """Summary of cost optimization recommendations."""

    total_recommendations: int = Field(
        0, description='Total number of cost optimization recommendations'
    )
    total_estimated_monthly_savings: float = Field(
        0.0, description='Total estimated monthly savings in USD'
    )
    currency: str = Field('USD', description='The currency for savings estimates')
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of cost optimization recommendations sorted by savings'
    )


class SecuritySummary(BaseModel):
    """Summary of security recommendations."""

    total_recommendations: int = Field(0, description='Total number of security recommendations')
    ok_count: int = Field(0, description='Number of recommendations with OK status')
    warning_count: int = Field(0, description='Number of recommendations with warning status')
    error_count: int = Field(0, description='Number of recommendations with error status')
    active_issues: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of active security issues'
    )


class ServiceLimitsSummary(BaseModel):
    """Summary of service limits recommendations."""

    total_recommendations: int = Field(
        0, description='Total number of service limits recommendations'
    )
    services_at_risk: int = Field(
        0, description='Number of services approaching or exceeding limits'
    )
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of service limit recommendations'
    )
