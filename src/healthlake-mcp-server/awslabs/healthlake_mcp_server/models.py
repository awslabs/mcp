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

"""Pydantic models for HealthLake MCP server."""

# Standard library imports
# Local imports
from .fhir_operations import DATASTORE_ID_LENGTH

# Third-party imports
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional


class FHIRResource(BaseModel):
    """Base FHIR resource model."""

    resourceType: str
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class SearchParameters(BaseModel):
    """FHIR search parameters."""

    parameters: Dict[str, str] = Field(default_factory=dict)
    count: int = Field(default=100, ge=1, le=100)


class CreateResourceRequest(BaseModel):
    """Request to create a FHIR resource."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    resource_type: str
    resource_data: Dict[str, Any]

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class UpdateResourceRequest(BaseModel):
    """Request to update a FHIR resource."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    resource_type: str
    resource_id: str
    resource_data: Dict[str, Any]

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class DatastoreFilter(BaseModel):
    """Filter for listing datastores."""

    status: Optional[str] = Field(None, pattern='^(CREATING|ACTIVE|DELETING|DELETED)$')


class ImportJobConfig(BaseModel):
    """Configuration for FHIR import job."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    input_data_config: Dict[str, Any]
    data_access_role_arn: str
    job_name: Optional[str] = None

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class ExportJobConfig(BaseModel):
    """Configuration for FHIR export job."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    output_data_config: Dict[str, Any]
    data_access_role_arn: str
    job_name: Optional[str] = None

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class JobFilter(BaseModel):
    """Filter for listing jobs."""

    job_status: Optional[str] = Field(
        None, pattern='^(SUBMITTED|IN_PROGRESS|COMPLETED|FAILED|STOP_REQUESTED|STOPPED)$'
    )
    job_type: Optional[str] = Field(None, pattern='^(IMPORT|EXPORT)$')
