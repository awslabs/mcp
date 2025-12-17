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

"""Pydantic models for HealthImaging MCP server."""

# Standard library imports
# Third-party imports
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional


# HealthImaging constants
DATASTORE_ID_LENGTH = 32  # AWS HealthImaging datastore ID length


class DatastoreFilter(BaseModel):
    """Filter for listing datastores."""

    status: Optional[str] = Field(None, pattern='^(CREATING|ACTIVE|DELETING|DELETED)$')


class SearchImageSetsRequest(BaseModel):
    """Request to search image sets."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    search_criteria: Optional[Dict[str, Any]] = None
    max_results: int = Field(default=50, ge=1, le=100)

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class ImageSetRequest(BaseModel):
    """Request for image set operations."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class ImageSetMetadataRequest(BaseModel):
    """Request for image set metadata."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    version_id: Optional[str] = None

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class ImageFrameRequest(BaseModel):
    """Request for image frame operations."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    image_frame_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class ImageSetVersionsRequest(BaseModel):
    """Request for listing image set versions."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    max_results: int = Field(default=50, ge=1, le=100)

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


# NEW MODELS FOR ADDITIONAL OPERATIONS


class DeleteImageSetRequest(BaseModel):
    """Request to delete an image set."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class DeletePatientStudiesRequest(BaseModel):
    """Request to delete all studies for a patient."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    patient_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class DeleteStudyRequest(BaseModel):
    """Request to delete a study."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    study_instance_uid: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class UpdateImageSetMetadataRequest(BaseModel):
    """Request to update image set metadata."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    version_id: str
    updates: Dict[str, Any]

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class RemoveSeriesRequest(BaseModel):
    """Request to remove a series from an image set."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    series_instance_uid: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class RemoveInstanceRequest(BaseModel):
    """Request to remove an instance from an image set."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    image_set_id: str
    sop_instance_uid: str
    series_instance_uid: Optional[str] = None

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class SearchByPatientRequest(BaseModel):
    """Request to search by patient ID."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    patient_id: str
    include_primary_only: bool = Field(default=False)

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class SearchByStudyRequest(BaseModel):
    """Request to search by study UID."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    study_instance_uid: str
    include_primary_only: bool = Field(default=False)

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class SearchBySeriesRequest(BaseModel):
    """Request to search by series UID."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    series_instance_uid: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class GetPatientStudiesRequest(BaseModel):
    """Request to get patient studies."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    patient_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class GetPatientSeriesRequest(BaseModel):
    """Request to get patient series."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    patient_id: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class GetStudyPrimaryImageSetsRequest(BaseModel):
    """Request to get primary image sets for a study."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    study_instance_uid: str

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class BulkUpdatePatientMetadataRequest(BaseModel):
    """Request to bulk update patient metadata."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    patient_id: str
    new_metadata: Dict[str, Any]

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v


class BulkDeleteByCriteriaRequest(BaseModel):
    """Request to bulk delete by search criteria."""

    datastore_id: str = Field(..., min_length=DATASTORE_ID_LENGTH, max_length=DATASTORE_ID_LENGTH)
    search_criteria: Dict[str, Any]

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore ID is alphanumeric."""
        if not v.isalnum():
            raise ValueError('Datastore ID must be alphanumeric')
        return v
