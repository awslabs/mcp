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

"""Data models for SSM for SAP application tools."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ApplicationSummary(BaseModel):
    """Summary of an SSM for SAP application."""

    id: str = Field(..., description='Application ID')
    type: str = Field(..., description='Application type (HANA or SAP_ABAP)')
    arn: Optional[str] = Field(default=None, description='Application ARN')
    discovery_status: Optional[str] = Field(default=None, description='Discovery status')


class ListApplicationsResponse(BaseModel):
    """Response from listing SSM for SAP applications."""

    applications: List[ApplicationSummary] = Field(
        default_factory=list, description='List of applications'
    )
    message: Optional[str] = Field(default=None, description='Informational message')


class ApplicationDetail(BaseModel):
    """Detailed information about an SSM for SAP application."""

    id: str = Field(..., description='Application ID')
    type: str = Field(..., description='Application type')
    arn: Optional[str] = Field(default=None, description='Application ARN')
    status: str = Field(..., description='Application status')
    discovery_status: str = Field(..., description='Discovery status')
    status_message: Optional[str] = Field(default=None, description='Status message')
    components: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='Application components'
    )
    associated_application_arns: Optional[List[str]] = Field(
        default=None, description='ARNs of associated applications'
    )
    last_updated: Optional[str] = Field(default=None, description='Last updated timestamp')


class ComponentDetail(BaseModel):
    """Detailed information about an application component."""

    component_id: str = Field(..., description='Component ID')
    component_type: str = Field(..., description='Component type')
    status: str = Field(..., description='Component status')
    sid: Optional[str] = Field(default=None, description='SAP System ID')
    hosts: Optional[List[Dict[str, Any]]] = Field(default=None, description='Host details')


class OperationDetail(BaseModel):
    """Details of an SSM for SAP operation."""

    id: str = Field(..., description='Operation ID')
    type: Optional[str] = Field(default=None, description='Operation type')
    status: str = Field(..., description='Operation status')
    start_time: Optional[str] = Field(default=None, description='Start time')
    end_time: Optional[str] = Field(default=None, description='End time')
    status_message: Optional[str] = Field(default=None, description='Status message')


class RegisterApplicationResponse(BaseModel):
    """Response from registering an SAP application."""

    status: str = Field(..., description='Registration status (success or error)')
    message: str = Field(..., description='Status message')
    application_id: Optional[str] = Field(default=None, description='Application ID')
    application_arn: Optional[str] = Field(default=None, description='Application ARN')
    operation_id: Optional[str] = Field(default=None, description='Operation ID')


class CascadeStopDetail(BaseModel):
    """Details of a cascaded stop operation for an associated application."""

    application_id: str = Field(..., description='Associated application ID')
    application_type: str = Field(..., description='Application type (SAP_ABAP)')
    operation_id: Optional[str] = Field(default=None, description='Stop operation ID')
    status: str = Field(..., description='Stop operation status')
    start_time: Optional[str] = Field(default=None, description='Stop operation start time')
    end_time: Optional[str] = Field(default=None, description='Stop operation end time')


class StartStopApplicationResponse(BaseModel):
    """Response from starting or stopping an SAP application."""

    status: str = Field(..., description='Operation status (success or error)')
    message: str = Field(..., description='Status message')
    operation_id: Optional[str] = Field(default=None, description='Operation ID')
    application_id: str = Field(..., description='Application ID')
    associated_app_stop_details: Optional[List[CascadeStopDetail]] = Field(
        default=None, description='Details of associated applications stopped before this one'
    )
