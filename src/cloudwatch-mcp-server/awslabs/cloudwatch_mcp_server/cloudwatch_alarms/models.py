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

"""Data models for CloudWatch Alarms MCP tools."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List


class MetricAlarmSummary(BaseModel):
    """Summary information for a CloudWatch metric alarm in ALARM state."""

    alarm_name: str = Field(..., description='Name of the alarm')
    alarm_description: str | None = Field(default=None, description='Description of the alarm')
    state_value: str = Field(..., description='Current state of the alarm (ALARM)')
    state_reason: str = Field(..., description='Reason for the current state')
    metric_name: str | None = Field(default=None, description='Name of the metric being monitored')
    namespace: str | None = Field(default=None, description='Namespace of the metric')
    dimensions: List[Dict[str, str]] = Field(
        default_factory=list, description='Key dimensions for the metric'
    )
    threshold: float = Field(..., description='Threshold value for the alarm')
    comparison_operator: str = Field(..., description='Comparison operator used')
    state_updated_timestamp: datetime = Field(
        ..., description='When the alarm state was last updated'
    )
    alarm_type: str = Field(default='MetricAlarm', description='Type of alarm')


class CompositeAlarmSummary(BaseModel):
    """Summary information for a CloudWatch composite alarm in ALARM state."""

    alarm_name: str = Field(..., description='Name of the composite alarm')
    alarm_description: str | None = Field(default=None, description='Description of the alarm')
    state_value: str = Field(..., description='Current state of the alarm')
    state_reason: str = Field(..., description='Reason for the current state')
    alarm_rule: str = Field(..., description='Rule expression for the composite alarm')
    state_updated_timestamp: datetime = Field(
        ..., description='When the alarm state was last updated'
    )
    alarm_type: str = Field(default='CompositeAlarm', description='Type of alarm')


class ActiveAlarmsResponse(BaseModel):
    """Response containing active CloudWatch alarms."""

    metric_alarms: List[MetricAlarmSummary] = Field(
        default_factory=list, description='List of active metric alarms'
    )
    composite_alarms: List[CompositeAlarmSummary] = Field(
        default_factory=list, description='List of active composite alarms'
    )
    has_more_results: bool = Field(
        default=False, description='Whether more alarms are available than the requested max_items'
    )
    message: str | None = Field(None, description='Informational message about the results')


class AlarmHistoryItem(BaseModel):
    """Represents a processed CloudWatch alarm history item."""

    alarm_name: str = Field(..., description='Name of the alarm')
    alarm_type: str = Field(..., description='Type of alarm (MetricAlarm or CompositeAlarm)')
    timestamp: datetime = Field(..., description='Timestamp of the history item')
    history_item_type: str = Field(
        ..., description='Type of history item (StateUpdate, ConfigurationUpdate, Action)'
    )
    history_summary: str = Field(..., description='Human-readable summary of the history item')
    old_state: str | None = Field(
        None, description='Previous state of the alarm (for StateUpdate items)'
    )
    new_state: str | None = Field(
        None, description='New state of the alarm (for StateUpdate items)'
    )
    state_reason: str | None = Field(
        None, description='Reason for the state change (for StateUpdate items)'
    )


class AlarmDetails(BaseModel):
    """Represents key details about a CloudWatch alarm."""

    alarm_name: str = Field(..., description='Name of the alarm')
    alarm_description: str | None = Field(default=None, description='Description of the alarm')
    alarm_type: str = Field(..., description='Type of alarm (MetricAlarm or CompositeAlarm)')
    current_state: str = Field(..., description='Current state of the alarm')
    metric_name: str | None = Field(
        default=None, description='Name of the metric (for MetricAlarm)'
    )
    namespace: str | None = Field(
        default=None, description='Namespace of the metric (for MetricAlarm)'
    )
    dimensions: List[Dict[str, str]] = Field(
        default_factory=list, description='Dimensions of the metric (for MetricAlarm)'
    )
    threshold: float | None = Field(default=None, description='Threshold value (for MetricAlarm)')
    comparison_operator: str | None = Field(
        default=None, description='Comparison operator (for MetricAlarm)'
    )
    evaluation_periods: int | None = Field(
        default=None, description='Number of evaluation periods (for MetricAlarm)'
    )
    period: int | None = Field(default=None, description='Period in seconds (for MetricAlarm)')
    statistic: str | None = Field(default=None, description='Statistic used (for MetricAlarm)')
    alarm_rule: str | None = Field(
        default=None, description='Rule expression (for CompositeAlarm)'
    )


class TimeRangeSuggestion(BaseModel):
    """Represents a suggested time range for investigation."""

    start_time: datetime = Field(..., description='Start time for investigation')
    end_time: datetime = Field(..., description='End time for investigation')
    reason: str = Field(..., description='Reason for this time range suggestion')


class AlarmHistoryResponse(BaseModel):
    """Response containing alarm history and related information."""

    alarm_details: AlarmDetails = Field(..., description='Details about the alarm')
    history_items: List[AlarmHistoryItem] = Field(
        default_factory=list, description='List of alarm history items'
    )
    time_range_suggestions: List[TimeRangeSuggestion] = Field(
        default_factory=list, description='Suggested time ranges for investigation'
    )
    has_more_results: bool = Field(
        default=False, description='Whether more history items are available'
    )
    message: str | None = Field(None, description='Informational message about the results')


class CompositeAlarmComponentResponse(BaseModel):
    """Response containing component alarm details for a composite alarm."""

    composite_alarm_name: str = Field(..., description='Name of the composite alarm')
    component_alarms: List[str] = Field(
        default_factory=list, description='Names of component alarms'
    )
    alarm_rule: str = Field(..., description='Rule expression for the composite alarm')
    component_details: List[AlarmDetails] | None = Field(
        None, description='Details about component alarms'
    )
