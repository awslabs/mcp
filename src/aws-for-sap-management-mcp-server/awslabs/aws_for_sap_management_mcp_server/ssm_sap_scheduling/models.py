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

"""Data models for SSM for SAP scheduling tools."""

from pydantic import BaseModel, Field
from typing import List, Optional


class ScheduleDetail(BaseModel):
    """Details of an EventBridge Scheduler schedule."""

    schedule_name: str = Field(..., description='Schedule name')
    schedule_arn: Optional[str] = Field(default=None, description='Schedule ARN')
    state: str = Field(..., description='Schedule state (ENABLED or DISABLED)')
    schedule_expression: str = Field(..., description='Schedule expression (rate or cron)')
    operation_type: str = Field(..., description='Type of operation scheduled')
    description: Optional[str] = Field(default=None, description='Schedule description')
    next_execution: Optional[str] = Field(default=None, description='Next execution time')
    timezone: Optional[str] = Field(default='UTC', description='Schedule timezone')


class CreateScheduleResponse(BaseModel):
    """Response from creating a schedule."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Status message')
    schedule_name: str = Field(..., description='Created schedule name')
    schedule_arn: Optional[str] = Field(default=None, description='Schedule ARN')
    application_id: str = Field(..., description='Target application ID')
    schedule_expression: str = Field(..., description='Schedule expression')


class DeleteScheduleResponse(BaseModel):
    """Response from deleting a schedule."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Status message')
    schedule_name: str = Field(..., description='Deleted schedule name')


class UpdateScheduleStateResponse(BaseModel):
    """Response from enabling or disabling a schedule."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Status message')
    schedule_name: str = Field(..., description='Schedule name')
    previous_state: Optional[str] = Field(default=None, description='Previous state')
    new_state: str = Field(..., description='New state')


class ListSchedulesResponse(BaseModel):
    """Response from listing schedules for an application."""

    application_id: str = Field(..., description='Application ID')
    total_schedules: int = Field(default=0, description='Total number of schedules')
    enabled_count: int = Field(default=0, description='Number of enabled schedules')
    disabled_count: int = Field(default=0, description='Number of disabled schedules')
    schedules: List[ScheduleDetail] = Field(default_factory=list, description='List of schedules')
