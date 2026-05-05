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

"""Data models for the HealthImaging MCP Server."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional


class DatastoreStatus(str, Enum):
    """Status values for HealthImaging datastores."""

    CREATING = 'CREATING'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class JobStatus(str, Enum):
    """Status values for HealthImaging jobs."""

    SUBMITTED = 'SUBMITTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class ImageSetState(str, Enum):
    """State values for HealthImaging image sets."""

    ACTIVE = 'ACTIVE'
    LOCKED = 'LOCKED'
    DELETED = 'DELETED'


# Data Models
class DatastoreProperties(BaseModel):
    """Properties of a HealthImaging datastore."""

    datastore_id: str = Field(..., description='Unique identifier for the datastore')
    datastore_name: str = Field(..., description='Name of the datastore')
    datastore_status: DatastoreStatus = Field(..., description='Current status of the datastore')
    kms_key_arn: Optional[str] = Field(None, description='KMS key ARN for encryption')
    datastore_arn: Optional[str] = Field(None, description='ARN of the datastore')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')


class DatastoreSummary(BaseModel):
    """Summary information about a HealthImaging datastore."""

    datastore_id: str = Field(..., description='Unique identifier for the datastore')
    datastore_name: str = Field(..., description='Name of the datastore')
    datastore_status: DatastoreStatus = Field(..., description='Current status of the datastore')
    datastore_arn: Optional[str] = Field(None, description='ARN of the datastore')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')


class DICOMImportJobProperties(BaseModel):
    """Properties of a DICOM import job."""

    job_id: str = Field(..., description='Unique identifier for the job')
    job_name: Optional[str] = Field(None, description='Name of the job')
    job_status: JobStatus = Field(..., description='Current status of the job')
    datastore_id: str = Field(..., description='ID of the target datastore')
    data_access_role_arn: str = Field(..., description='IAM role ARN for data access')
    ended_at: Optional[str] = Field(None, description='Job completion timestamp')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')
    input_s3_uri: Optional[str] = Field(None, description='Input S3 URI')
    output_s3_uri: Optional[str] = Field(None, description='Output S3 URI')
    message: Optional[str] = Field(None, description='Job message or error details')


class DICOMImportJobSummary(BaseModel):
    """Summary information about a DICOM import job."""

    job_id: str = Field(..., description='Unique identifier for the job')
    job_name: Optional[str] = Field(None, description='Name of the job')
    job_status: JobStatus = Field(..., description='Current status of the job')
    datastore_id: str = Field(..., description='ID of the target datastore')
    ended_at: Optional[str] = Field(None, description='Job completion timestamp')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')
    message: Optional[str] = Field(None, description='Job message or error details')


class ImageSetProperties(BaseModel):
    """Properties of a HealthImaging image set."""

    image_set_id: str = Field(..., description='Unique identifier for the image set')
    version_id: str = Field(..., description='Version identifier for the image set')
    image_set_state: ImageSetState = Field(..., description='Current state of the image set')
    image_set_workflow_status: Optional[str] = Field(None, description='Workflow status')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')
    deleted_at: Optional[str] = Field(None, description='Deletion timestamp')
    message: Optional[str] = Field(None, description='Status message')


class ImageSetsMetadataSummary(BaseModel):
    """Summary metadata for image sets."""

    image_set_id: str = Field(..., description='Unique identifier for the image set')
    version: int = Field(..., description='Version number of the image set')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')
    dicom_tags: Optional[Dict[str, Any]] = Field(None, description='DICOM tags')


class DICOMExportJobProperties(BaseModel):
    """Properties of a DICOM export job."""

    job_id: str = Field(..., description='Unique identifier for the job')
    job_name: Optional[str] = Field(None, description='Name of the job')
    job_status: JobStatus = Field(..., description='Current status of the job')
    datastore_id: str = Field(..., description='ID of the source datastore')
    data_access_role_arn: str = Field(..., description='IAM role ARN for data access')
    ended_at: Optional[str] = Field(None, description='Job completion timestamp')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')
    output_s3_uri: Optional[str] = Field(None, description='Output S3 URI')
    message: Optional[str] = Field(None, description='Job message or error details')


class DICOMExportJobSummary(BaseModel):
    """Summary information about a DICOM export job."""

    job_id: str = Field(..., description='Unique identifier for the job')
    job_name: Optional[str] = Field(None, description='Name of the job')
    job_status: JobStatus = Field(..., description='Current status of the job')
    datastore_id: str = Field(..., description='ID of the source datastore')
    ended_at: Optional[str] = Field(None, description='Job completion timestamp')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')
    message: Optional[str] = Field(None, description='Job message or error details')


# Request Models
class CreateDatastoreRequest(BaseModel):
    """Request model for creating a new datastore."""

    datastore_name: str = Field(..., description='Name for the new datastore')
    kms_key_arn: Optional[str] = Field(None, description='KMS key ARN for encryption')
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the datastore')


class DeleteDatastoreRequest(BaseModel):
    """Request model for deleting a datastore."""

    datastore_id: str = Field(..., description='ID of the datastore to delete')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class GetDatastoreRequest(BaseModel):
    """Request model for getting datastore details."""

    datastore_id: str = Field(..., description='ID of the datastore to retrieve')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class ListDatastoresRequest(BaseModel):
    """Request model for listing datastores."""

    datastore_status: Optional[DatastoreStatus] = Field(
        None, description='Filter by datastore status'
    )
    next_token: Optional[str] = Field(None, description='Token for pagination')
    max_results: Optional[int] = Field(None, description='Maximum number of results to return')

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Validate that max_results is within valid range."""
        if v is not None:
            if v < 1 or v > 50:
                raise ValueError('max_results must be between 1 and 50')
        return v


class StartDICOMImportJobRequest(BaseModel):
    """Request model for starting a DICOM import job."""

    job_name: Optional[str] = Field(None, description='Name for the import job')
    datastore_id: str = Field(..., description='ID of the target datastore')
    data_access_role_arn: str = Field(..., description='IAM role ARN for data access')
    client_token: Optional[str] = Field(None, description='Client token for idempotency')
    input_s3_uri: str = Field(..., description='S3 URI of the input data')
    output_s3_uri: Optional[str] = Field(None, description='S3 URI for the output data')
    input_owner_account_id: Optional[str] = Field(None, description='Input owner account ID')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class GetDICOMImportJobRequest(BaseModel):
    """Request model for getting DICOM import job details."""

    datastore_id: str = Field(..., description='ID of the datastore')
    job_id: str = Field(..., description='ID of the import job')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class ListDICOMImportJobsRequest(BaseModel):
    """Request model for listing DICOM import jobs."""

    datastore_id: str = Field(..., description='ID of the datastore')
    job_status: Optional[JobStatus] = Field(None, description='Filter by job status')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    max_results: Optional[int] = Field(None, description='Maximum number of results to return')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Validate that max_results is within valid range."""
        if v is not None:
            if v < 1 or v > 50:
                raise ValueError('max_results must be between 1 and 50')
        return v


class SearchImageSetsRequest(BaseModel):
    """Request model for searching image sets."""

    datastore_id: str = Field(..., description='ID of the datastore')
    search_criteria: Optional[Dict[str, Any]] = Field(None, description='Search criteria')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    max_results: Optional[int] = Field(None, description='Maximum number of results to return')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Validate that max_results is within valid range."""
        if v is not None:
            if v < 1 or v > 50:
                raise ValueError('max_results must be between 1 and 50')
        return v


class GetImageSetRequest(BaseModel):
    """Request model for getting image set details."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    version_id: Optional[str] = Field(None, description='Version ID of the image set')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class DeleteImageSetRequest(BaseModel):
    """Request model for deleting an image set."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    version_id: Optional[str] = Field(None, description='Version ID of the image set')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class ListImageSetVersionsRequest(BaseModel):
    """Request model for listing image set versions."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    max_results: Optional[int] = Field(None, description='Maximum number of results to return')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Validate that max_results is within valid range."""
        if v is not None:
            if v < 1 or v > 50:
                raise ValueError('max_results must be between 1 and 50')
        return v


class UpdateImageSetMetadataRequest(BaseModel):
    """Request model for updating image set metadata."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    latest_version_id: str = Field(..., description='Latest version ID of the image set')
    update_image_set_metadata_updates: Dict[str, Any] = Field(..., description='Metadata updates')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class GetImageSetMetadataRequest(BaseModel):
    """Request model for getting image set metadata."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    version_id: Optional[str] = Field(None, description='Version ID of the image set')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class CopyImageSetRequest(BaseModel):
    """Request model for copying an image set."""

    datastore_id: str = Field(..., description='ID of the destination datastore')
    source_image_set_id: str = Field(..., description='ID of the source image set')
    source_datastore_id: Optional[str] = Field(None, description='ID of the source datastore')
    copy_image_set_information: Dict[str, Any] = Field(..., description='Copy information')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class GetImageFrameRequest(BaseModel):
    """Request model for getting an image frame."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    image_frame_information: Dict[str, str] = Field(..., description='Image frame information')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class StartDICOMExportJobRequest(BaseModel):
    """Request model for starting a DICOM export job."""

    job_name: Optional[str] = Field(None, description='Name for the export job')
    datastore_id: str = Field(..., description='ID of the source datastore')
    data_access_role_arn: str = Field(..., description='IAM role ARN for data access')
    client_token: Optional[str] = Field(None, description='Client token for idempotency')
    output_s3_uri: str = Field(..., description='S3 URI for the output data')
    study_instance_uid: Optional[str] = Field(None, description='Study instance UID to export')
    series_instance_uid: Optional[str] = Field(None, description='Series instance UID to export')
    sop_instance_uid: Optional[str] = Field(None, description='SOP instance UID to export')
    submitted_before: Optional[str] = Field(
        None, description='Export images submitted before this date'
    )
    submitted_after: Optional[str] = Field(
        None, description='Export images submitted after this date'
    )

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class GetDICOMExportJobRequest(BaseModel):
    """Request model for getting DICOM export job details."""

    datastore_id: str = Field(..., description='ID of the datastore')
    job_id: str = Field(..., description='ID of the export job')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v


class ListDICOMExportJobsRequest(BaseModel):
    """Request model for listing DICOM export jobs."""

    datastore_id: str = Field(..., description='ID of the datastore')
    job_status: Optional[JobStatus] = Field(None, description='Filter by job status')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    max_results: Optional[int] = Field(None, description='Maximum number of results to return')

    @field_validator('datastore_id')
    @classmethod
    def validate_datastore_id(cls, v):
        """Validate that datastore_id is not empty and has correct length."""
        if not v or len(v.strip()) == 0:
            raise ValueError('datastore_id cannot be empty')
        if len(v) != 32:
            raise ValueError('datastore_id must be exactly 32 characters long')
        return v

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v):
        """Validate that max_results is within valid range."""
        if v is not None:
            if v < 1 or v > 50:
                raise ValueError('max_results must be between 1 and 50')
        return v


# Tagging Request Models
class ListTagsForResourceRequest(BaseModel):
    """Request model for listing tags for a resource."""

    resource_arn: str = Field(..., description='The ARN of the resource to list tags for')


class TagResourceRequest(BaseModel):
    """Request model for tagging a resource."""

    resource_arn: str = Field(..., description='The ARN of the resource to tag')
    tags: Dict[str, str] = Field(..., description='The tags to apply to the resource')


class UntagResourceRequest(BaseModel):
    """Request model for untagging a resource."""

    resource_arn: str = Field(..., description='The ARN of the resource to untag')
    tag_keys: List[str] = Field(..., description='The tag keys to remove from the resource')


# Response Models
class CreateDatastoreResponse(BaseModel):
    """Response model for datastore creation."""

    datastore_id: str = Field(..., description='ID of the created datastore')
    datastore_status: DatastoreStatus = Field(..., description='Status of the created datastore')


class DeleteDatastoreResponse(BaseModel):
    """Response model for datastore deletion."""

    datastore_id: str = Field(..., description='ID of the deleted datastore')
    datastore_status: DatastoreStatus = Field(..., description='Status of the deleted datastore')


class GetDatastoreResponse(BaseModel):
    """Response model for getting datastore details."""

    datastore_properties: DatastoreProperties = Field(
        ..., description='Properties of the datastore'
    )


class ListDatastoresResponse(BaseModel):
    """Response model for listing datastores."""

    datastore_summaries: List[DatastoreSummary] = Field(
        ..., description='List of datastore summaries'
    )
    next_token: Optional[str] = Field(None, description='Token for next page of results')


class StartDICOMImportJobResponse(BaseModel):
    """Response model for starting a DICOM import job."""

    datastore_id: str = Field(..., description='ID of the target datastore')
    job_id: str = Field(..., description='ID of the started job')
    job_status: JobStatus = Field(..., description='Status of the started job')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')


class GetDICOMImportJobResponse(BaseModel):
    """Response model for getting DICOM import job details."""

    job_properties: DICOMImportJobProperties = Field(
        ..., description='Properties of the import job'
    )


class ListDICOMImportJobsResponse(BaseModel):
    """Response model for listing DICOM import jobs."""

    job_summaries: List[DICOMImportJobSummary] = Field(
        ..., description='List of import job summaries'
    )
    next_token: Optional[str] = Field(None, description='Token for next page of results')


class SearchImageSetsResponse(BaseModel):
    """Response model for searching image sets."""

    image_sets_metadata_summaries: List[ImageSetsMetadataSummary] = Field(
        ..., description='List of image set metadata summaries'
    )
    next_token: Optional[str] = Field(None, description='Token for next page of results')


class GetImageSetResponse(BaseModel):
    """Response model for getting image set details."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    version_id: str = Field(..., description='Version ID of the image set')
    image_set_state: ImageSetState = Field(..., description='State of the image set')
    image_set_workflow_status: Optional[str] = Field(None, description='Workflow status')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')
    deleted_at: Optional[str] = Field(None, description='Deletion timestamp')
    message: Optional[str] = Field(None, description='Status message')


class DeleteImageSetResponse(BaseModel):
    """Response model for deleting an image set."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the deleted image set')
    image_set_state: ImageSetState = Field(..., description='State of the deleted image set')


class ListImageSetVersionsResponse(BaseModel):
    """Response model for listing image set versions."""

    image_set_properties_list: List[ImageSetProperties] = Field(
        ..., description='List of image set properties'
    )
    next_token: Optional[str] = Field(None, description='Token for next page of results')


class UpdateImageSetMetadataResponse(BaseModel):
    """Response model for updating image set metadata."""

    datastore_id: str = Field(..., description='ID of the datastore')
    image_set_id: str = Field(..., description='ID of the image set')
    latest_version_id: str = Field(..., description='Latest version ID after update')
    image_set_state: ImageSetState = Field(..., description='State of the image set')
    image_set_workflow_status: Optional[str] = Field(None, description='Workflow status')
    created_at: Optional[str] = Field(None, description='Creation timestamp')
    updated_at: Optional[str] = Field(None, description='Last update timestamp')
    message: Optional[str] = Field(None, description='Status message')


class GetImageSetMetadataResponse(BaseModel):
    """Response model for getting image set metadata."""

    image_set_metadata_blob: str = Field(
        ..., description='Image set metadata as base64-encoded string'
    )
    content_type: Optional[str] = Field(None, description='Content type of the metadata')
    content_encoding: Optional[str] = Field(None, description='Content encoding of the metadata')


class CopyImageSetResponse(BaseModel):
    """Response model for copying an image set."""

    datastore_id: str = Field(..., description='ID of the datastore')
    source_image_set_properties: ImageSetProperties = Field(
        ..., description='Properties of the source image set'
    )
    destination_image_set_properties: ImageSetProperties = Field(
        ..., description='Properties of the destination image set'
    )


class GetImageFrameResponse(BaseModel):
    """Response model for getting an image frame."""

    image_frame_blob: str = Field(..., description='Image frame data as base64-encoded string')
    content_type: Optional[str] = Field(None, description='Content type of the image frame')


class StartDICOMExportJobResponse(BaseModel):
    """Response model for starting a DICOM export job."""

    datastore_id: str = Field(..., description='ID of the source datastore')
    job_id: str = Field(..., description='ID of the started job')
    job_status: JobStatus = Field(..., description='Status of the started job')
    submitted_at: Optional[str] = Field(None, description='Job submission timestamp')


class GetDICOMExportJobResponse(BaseModel):
    """Response model for getting DICOM export job details."""

    job_properties: DICOMExportJobProperties = Field(
        ..., description='Properties of the export job'
    )


class ListDICOMExportJobsResponse(BaseModel):
    """Response model for listing DICOM export jobs."""

    job_summaries: List[DICOMExportJobSummary] = Field(
        ..., description='List of export job summaries'
    )
    next_token: Optional[str] = Field(None, description='Token for next page of results')


# Tagging Response Models
class ListTagsForResourceResponse(BaseModel):
    """Response model for listing tags for a resource."""

    tags: Dict[str, str] = Field(..., description='The tags associated with the resource')


class TagResourceResponse(BaseModel):
    """Response model for tagging a resource."""

    success: bool = Field(..., description='Whether the tagging operation was successful')


class UntagResourceResponse(BaseModel):
    """Response model for untagging a resource."""

    success: bool = Field(..., description='Whether the untagging operation was successful')
