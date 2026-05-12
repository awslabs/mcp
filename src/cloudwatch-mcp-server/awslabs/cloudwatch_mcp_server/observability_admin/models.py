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

"""Data models for Observability Admin MCP tools."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class TelemetryEvaluationStatusResponse(BaseModel):
    """Response for telemetry evaluation status."""

    status: str = Field(
        ...,
        description='Onboarding status: NOT_STARTED, STARTING, FAILED_START, RUNNING, STOPPING, FAILED_STOP, or STOPPED',
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description='Reason for failure, populated only when status is FAILED_START or FAILED_STOP',
    )


class TelemetryConfiguration(BaseModel):
    """Telemetry configuration state for a single resource."""

    account_identifier: str = Field(..., description='AWS account ID containing the resource')
    resource_type: str = Field(
        ..., description='Resource type, e.g. AWS::EC2::Instance, AWS::Lambda::Function'
    )
    resource_identifier: str = Field(
        ..., description='Resource identifier, e.g. i-0e979d278b040f856'
    )
    telemetry_configuration_state: Dict[str, str] = Field(
        ...,
        description='Telemetry state per type, e.g. {Logs: Enabled, Metrics: Disabled, Traces: NotApplicable}',
    )
    resource_tags: Dict[str, str] = Field(
        default_factory=dict, description='Tags associated with the resource'
    )
    last_update_timestamp: Optional[int] = Field(
        default=None, description='Timestamp of last telemetry config change'
    )
    telemetry_source_type: Optional[str] = Field(
        default=None,
        description='Telemetry source type for the resource, e.g. VPC_FLOW_LOGS, EKS_AUDIT_LOGS',
    )


class ListResourceTelemetryResponse(BaseModel):
    """Response for listing resource telemetry configurations."""

    telemetry_configurations: List[TelemetryConfiguration] = Field(
        default_factory=list, description='List of resource telemetry configurations'
    )
    has_more_results: bool = Field(default=False, description='Whether more results are available')
    message: Optional[str] = Field(default=None, description='Status message')


class TelemetryRuleSummary(BaseModel):
    """Summary of a telemetry rule."""

    rule_name: str = Field(..., description='Name of the telemetry rule')
    rule_arn: str = Field(..., description='ARN of the telemetry rule')
    resource_type: str = Field(..., description='Resource type the rule applies to')
    telemetry_type: str = Field(..., description='Telemetry type: Logs, Metrics, or Traces')
    telemetry_source_types: List[str] = Field(
        default_factory=list,
        description='Telemetry source types, e.g. VPC_FLOW_LOGS, EKS_AUDIT_LOGS',
    )
    created_timestamp: Optional[int] = Field(
        default=None, description='Timestamp when the rule was created'
    )
    last_update_timestamp: Optional[int] = Field(
        default=None, description='Timestamp when the rule was last modified'
    )


class ListTelemetryRulesResponse(BaseModel):
    """Response for listing telemetry rules."""

    telemetry_rule_summaries: List[TelemetryRuleSummary] = Field(
        default_factory=list, description='List of telemetry rule summaries'
    )
    has_more_results: bool = Field(default=False, description='Whether more results are available')
    message: Optional[str] = Field(default=None, description='Status message')


class DestinationConfiguration(BaseModel):
    """Configuration specifying where and how telemetry data should be delivered."""

    destination_type: Optional[str] = Field(
        default=None, description='Destination type, e.g. cloud-watch-logs'
    )
    destination_pattern: Optional[str] = Field(
        default=None,
        description='Pattern used to generate the destination path, supporting macros like <resourceId> and <accountId>',
    )
    retention_in_days: Optional[int] = Field(
        default=None, description='Number of days to retain telemetry data in the destination'
    )
    vpc_flow_log_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description='VPC Flow Log specific parameters'
    )
    cloudtrail_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description='CloudTrail specific parameters'
    )
    elb_load_balancer_logging_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description='ELB load balancer logging parameters'
    )
    waf_logging_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description='WAF logging parameters'
    )
    log_delivery_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description='Bedrock AgentCore log delivery parameters'
    )


class TelemetryRuleDetail(BaseModel):
    """Detailed configuration of a telemetry rule."""

    resource_type: str = Field(
        ..., description='AWS resource type, e.g. AWS::EC2::VPC, AWS::EKS::Cluster'
    )
    telemetry_type: str = Field(..., description='Telemetry type: Logs, Metrics, or Traces')
    telemetry_source_types: List[str] = Field(
        default_factory=list,
        description='Specific telemetry source types, e.g. VPC_FLOW_LOGS, EKS_AUDIT_LOGS',
    )
    destination_configuration: Optional[DestinationConfiguration] = Field(
        default=None, description='Configuration for telemetry data delivery destination'
    )
    scope: Optional[str] = Field(
        default=None, description='Organizational scope the rule applies to'
    )
    selection_criteria: Optional[str] = Field(
        default=None, description='Criteria for selecting which resources the rule applies to'
    )


class GetTelemetryRuleResponse(BaseModel):
    """Response for getting a telemetry rule."""

    rule_name: str = Field(..., description='Name of the telemetry rule')
    rule_arn: str = Field(..., description='ARN of the telemetry rule')
    created_timestamp: Optional[int] = Field(
        default=None, description='Timestamp when the rule was created'
    )
    last_update_timestamp: Optional[int] = Field(
        default=None, description='Timestamp when the rule was last modified'
    )
    telemetry_rule: Optional[TelemetryRuleDetail] = Field(
        default=None, description='The full configuration details of the telemetry rule'
    )
