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

"""Data models for CloudWatch Contributor Insights MCP tools."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class InsightRuleSummary(BaseModel):
    """Summary of a CloudWatch Contributor Insights rule."""

    name: str = Field(..., description='Name of the insight rule')
    state: str = Field(..., description='State of the rule (ENABLED or DISABLED)')
    schema_version: str = Field(default='', description='Schema version of the rule definition')
    definition: str = Field(default='', description='JSON rule definition body')
    managed_rule: bool = Field(default=False, description='Whether this is a managed rule')


class DescribeInsightRulesResponse(BaseModel):
    """Response containing Contributor Insights rules."""

    insight_rules: List[InsightRuleSummary] = Field(
        default_factory=list, description='List of insight rules'
    )
    has_more_results: bool = Field(default=False, description='Whether more rules are available')
    message: Optional[str] = Field(None, description='Informational message about the results')


class InsightRuleContributor(BaseModel):
    """A contributor found by a Contributor Insights rule."""

    keys: List[str] = Field(default_factory=list, description='Contributor key values')
    approximate_aggregate_value: float = Field(
        default=0.0, description='Aggregated metric value for this contributor'
    )
    datapoints: List[Dict[str, Any]] = Field(
        default_factory=list, description='Data points for this contributor'
    )


class InsightRuleMetricDatapoint(BaseModel):
    """A data point from a Contributor Insights rule report."""

    timestamp: datetime = Field(..., description='Timestamp of the data point')
    unique_contributors: Optional[float] = Field(None, description='Number of unique contributors')
    max_contributor_value: Optional[float] = Field(
        None, description='Maximum value from a single contributor'
    )
    sample_count: Optional[float] = Field(None, description='Number of data points matched')
    average: Optional[float] = Field(None, description='Average value from all contributors')
    sum: Optional[float] = Field(None, description='Sum of values from all contributors')
    minimum: Optional[float] = Field(None, description='Minimum value observed')
    maximum: Optional[float] = Field(None, description='Maximum value observed')


class GetInsightRuleReportResponse(BaseModel):
    """Response containing a Contributor Insights rule report."""

    key_labels: List[str] = Field(
        default_factory=list, description='Labels for the contributor keys'
    )
    aggregation_statistic: str = Field(
        default='', description='Aggregation statistic used (Sum, Maximum, etc.)'
    )
    aggregate_value: Optional[float] = Field(
        None, description='Approximate aggregate value across all contributors'
    )
    approximate_unique_count: int = Field(
        default=0, description='Approximate number of unique contributors'
    )
    contributors: List[InsightRuleContributor] = Field(
        default_factory=list, description='Top contributors'
    )
    metric_datapoints: List[InsightRuleMetricDatapoint] = Field(
        default_factory=list, description='Time-series metric data points'
    )
    message: Optional[str] = Field(None, description='Informational message about the results')


class ManagedInsightRuleSummary(BaseModel):
    """Summary of a managed Contributor Insights rule for a specific resource."""

    template_name: str = Field(default='', description='Name of the managed rule template')
    resource_arn: str = Field(default='', description='ARN of the resource this rule monitors')
    rule_state: str = Field(default='', description='State of the managed rule')


class ListManagedInsightRulesResponse(BaseModel):
    """Response containing managed Contributor Insights rules for a resource."""

    managed_rules: List[ManagedInsightRuleSummary] = Field(
        default_factory=list, description='List of managed insight rules'
    )
    has_more_results: bool = Field(default=False, description='Whether more rules are available')
    message: Optional[str] = Field(None, description='Informational message about the results')


class PutInsightRuleResponse(BaseModel):
    """Response from creating or updating a Contributor Insights rule."""

    success: bool = Field(default=True, description='Whether the operation succeeded')
    rule_name: str = Field(..., description='Name of the rule that was created or updated')
    message: Optional[str] = Field(None, description='Informational message')


class PartialFailure(BaseModel):
    """A partial failure when operating on multiple rules."""

    failure_resource: Optional[str] = Field(None, description='Rule name that failed')
    exception_type: Optional[str] = Field(None, description='Type of exception')
    failure_code: Optional[str] = Field(None, description='Failure code')
    failure_description: Optional[str] = Field(None, description='Description of the failure')


class ModifyInsightRulesResponse(BaseModel):
    """Response from enabling or disabling Contributor Insights rules."""

    failures: List[PartialFailure] = Field(
        default_factory=list, description='List of rules that failed to be modified'
    )
    message: Optional[str] = Field(None, description='Informational message')
