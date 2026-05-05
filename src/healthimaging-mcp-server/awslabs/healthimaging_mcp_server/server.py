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

"""AWS HealthImaging MCP Server implementation."""

from . import healthimaging_operations
from .models import (
    CopyImageSetRequest,
    CopyImageSetResponse,
    CreateDatastoreRequest,
    CreateDatastoreResponse,
    DatastoreStatus,
    DeleteDatastoreRequest,
    DeleteDatastoreResponse,
    DeleteImageSetRequest,
    DeleteImageSetResponse,
    GetDatastoreRequest,
    GetDatastoreResponse,
    GetDICOMExportJobRequest,
    GetDICOMExportJobResponse,
    GetDICOMImportJobRequest,
    GetDICOMImportJobResponse,
    GetImageFrameRequest,
    GetImageFrameResponse,
    GetImageSetMetadataRequest,
    GetImageSetMetadataResponse,
    GetImageSetRequest,
    GetImageSetResponse,
    JobStatus,
    ListDatastoresRequest,
    ListDatastoresResponse,
    ListDICOMExportJobsRequest,
    ListDICOMExportJobsResponse,
    ListDICOMImportJobsRequest,
    ListDICOMImportJobsResponse,
    ListImageSetVersionsRequest,
    ListImageSetVersionsResponse,
    ListTagsForResourceRequest,
    ListTagsForResourceResponse,
    SearchImageSetsRequest,
    SearchImageSetsResponse,
    StartDICOMExportJobRequest,
    StartDICOMExportJobResponse,
    StartDICOMImportJobRequest,
    StartDICOMImportJobResponse,
    TagResourceRequest,
    TagResourceResponse,
    UntagResourceRequest,
    UntagResourceResponse,
    UpdateImageSetMetadataRequest,
    UpdateImageSetMetadataResponse,
)
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


def _handle_field_value(value):
    """Convert FieldInfo objects to None, otherwise return the value as-is."""
    return None if isinstance(value, FieldInfo) else value


def _convert_to_datastore_status(value: Optional[str]) -> Optional[DatastoreStatus]:
    """Convert string to DatastoreStatus enum."""
    if value is None:
        return None
    try:
        return DatastoreStatus(value)
    except ValueError:
        return None


def _convert_to_job_status(value: Optional[str]) -> Optional[JobStatus]:
    """Convert string to JobStatus enum."""
    if value is None:
        return None
    try:
        return JobStatus(value)
    except ValueError:
        return None


# Define server instructions
SERVER_INSTRUCTIONS = """The official MCP Server for AWS HealthImaging

This server provides 39 comprehensive tools for managing AWS HealthImaging resources including:

**Standard AWS API Operations (21 tools):**
- Datastore management (create, delete, get, list)
- DICOM import/export jobs (start, get, list)
- Image sets and metadata management (search, get, update, delete, copy, versions)
- Image frame retrieval with base64 encoding
- Resource tagging (list, add, remove tags)

**Advanced DICOM Operations (18 tools):**
- Enhanced search methods (patient, study, series level searches)
- Data analysis tools (patient studies, series analysis, primary image sets)
- Delete operations (patient studies, studies, series, instances)
- Bulk operations (metadata updates, criteria-based deletions)
- DICOM hierarchy operations (series/instance removal)
- DICOMweb integration and metadata updates

All tools provide comprehensive error handling, type safety with Pydantic models,
and support for medical imaging workflows with DICOM-aware operations.

Available Tools:
- create_datastore: Create a new data store
- delete_datastore: Delete a data store
- get_datastore: Get data store information
- list_datastores: List all data stores
- start_dicom_import_job: Start a DICOM import job
- get_dicom_import_job: Get import job details
- list_dicom_import_jobs: List import jobs
- start_dicom_export_job: Start a DICOM export job
- get_dicom_export_job: Get export job details
- list_dicom_export_jobs: List export jobs
- search_image_sets: Search for image sets
- get_image_set: Get image set information
- get_image_set_metadata: Get image set metadata
- list_image_set_versions: List image set versions
- update_image_set_metadata: Update image set metadata
- delete_image_set: Delete an image set
- copy_image_set: Copy an image set
- get_image_frame: Get a specific image frame
- list_tags_for_resource: List resource tags
- tag_resource: Add tags to a resource
- untag_resource: Remove tags from a resource
- search_by_patient_id: Search by patient ID
- search_by_study_uid: Search by study UID
- search_by_series_uid: Search by series UID
- get_patient_studies: Get all studies for a patient
- get_patient_series: Get all series for a patient
- get_study_primary_image_sets: Get primary image sets for study
- delete_patient_studies: Delete all studies for a patient
- delete_study: Delete all image sets for a study
- delete_series_by_uid: Delete series by UID
- get_series_primary_image_set: Get primary image set for series
- get_patient_dicomweb_studies: Get DICOMweb study info
- delete_instance_in_study: Delete instance in study
- delete_instance_in_series: Delete instance in series
- update_patient_study_metadata: Update patient/study metadata
- bulk_update_patient_metadata: Bulk update patient metadata
- bulk_delete_by_criteria: Bulk delete by criteria
- remove_series_from_image_set: Remove series from image set
- remove_instance_from_image_set: Remove instance from image set
"""


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.healthimaging-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
    )


app = create_server()


@app.tool()
def create_datastore(
    datastore_name: str = Field(description='Name for the new datastore'),
    kms_key_arn: Optional[str] = Field(None, description='KMS key ARN for encryption'),
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the datastore'),
) -> CreateDatastoreResponse:
    """Create a new data store in AWS HealthImaging."""
    request = CreateDatastoreRequest(
        datastore_name=datastore_name,
        kms_key_arn=_handle_field_value(kms_key_arn),
        tags=_handle_field_value(tags),
    )
    return healthimaging_operations.create_datastore(request)


@app.tool()
def delete_datastore(
    datastore_id: str = Field(description='ID of the datastore to delete'),
) -> DeleteDatastoreResponse:
    """Delete a data store from AWS HealthImaging."""
    request = DeleteDatastoreRequest(datastore_id=datastore_id)
    return healthimaging_operations.delete_datastore(request)


@app.tool()
def get_datastore(
    datastore_id: str = Field(description='ID of the datastore to retrieve'),
) -> GetDatastoreResponse:
    """Get information about a specific data store."""
    request = GetDatastoreRequest(datastore_id=datastore_id)
    return healthimaging_operations.get_datastore(request)


@app.tool()
def list_datastores(
    datastore_status: Optional[str] = Field(
        None, description='Filter by datastore status (CREATING, ACTIVE, DELETING, DELETED)'
    ),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (1-100)'
    ),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
) -> ListDatastoresResponse:
    """List all data stores in the account."""
    request = ListDatastoresRequest(
        datastore_status=_convert_to_datastore_status(_handle_field_value(datastore_status)),
        max_results=_handle_field_value(max_results),
        next_token=_handle_field_value(next_token),
    )
    return healthimaging_operations.list_datastores(request)


@app.tool()
def start_dicom_import_job(
    datastore_id: str = Field(description='ID of the target datastore'),
    data_access_role_arn: str = Field(description='IAM role ARN for data access'),
    input_s3_uri: str = Field(description='S3 URI of the input data'),
    job_name: Optional[str] = Field(None, description='Name for the import job'),
    client_token: Optional[str] = Field(None, description='Client token for idempotency'),
    output_s3_uri: Optional[str] = Field(None, description='S3 URI for the output data'),
    input_owner_account_id: Optional[str] = Field(None, description='Input owner account ID'),
) -> StartDICOMImportJobResponse:
    """Start a DICOM import job."""
    request = StartDICOMImportJobRequest(
        datastore_id=datastore_id,
        data_access_role_arn=data_access_role_arn,
        input_s3_uri=input_s3_uri,
        job_name=_handle_field_value(job_name),
        client_token=_handle_field_value(client_token),
        output_s3_uri=_handle_field_value(output_s3_uri),
        input_owner_account_id=_handle_field_value(input_owner_account_id),
    )
    return healthimaging_operations.start_dicom_import_job(request)


@app.tool()
def get_dicom_import_job(
    datastore_id: str = Field(description='ID of the datastore'),
    job_id: str = Field(description='ID of the import job'),
) -> GetDICOMImportJobResponse:
    """Get information about a DICOM import job."""
    request = GetDICOMImportJobRequest(datastore_id=datastore_id, job_id=job_id)
    return healthimaging_operations.get_dicom_import_job(request)


@app.tool()
def list_dicom_import_jobs(
    datastore_id: str = Field(description='ID of the datastore'),
    job_status: Optional[str] = Field(
        None, description='Filter by job status (SUBMITTED, IN_PROGRESS, COMPLETED, FAILED)'
    ),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (1-50)'
    ),
) -> ListDICOMImportJobsResponse:
    """List DICOM import jobs for a data store."""
    request = ListDICOMImportJobsRequest(
        datastore_id=datastore_id,
        job_status=_convert_to_job_status(_handle_field_value(job_status)),
        next_token=_handle_field_value(next_token),
        max_results=_handle_field_value(max_results),
    )
    return healthimaging_operations.list_dicom_import_jobs(request)


@app.tool()
def search_image_sets(
    datastore_id: str = Field(description='ID of the datastore'),
    search_criteria: Optional[Dict[str, Any]] = Field(None, description='Search criteria'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (1-50)'
    ),
) -> SearchImageSetsResponse:
    """Search for image sets in a data store."""
    request = SearchImageSetsRequest(
        datastore_id=datastore_id,
        search_criteria=_handle_field_value(search_criteria),
        next_token=_handle_field_value(next_token),
        max_results=_handle_field_value(max_results),
    )
    return healthimaging_operations.search_image_sets(request)


@app.tool()
def get_image_set(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    version_id: Optional[str] = Field(None, description='Version ID of the image set'),
) -> GetImageSetResponse:
    """Get information about a specific image set."""
    request = GetImageSetRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        version_id=_handle_field_value(version_id),
    )
    return healthimaging_operations.get_image_set(request)


@app.tool()
def get_image_set_metadata(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    version_id: Optional[str] = Field(None, description='Version ID of the image set'),
) -> GetImageSetMetadataResponse:
    """Get metadata for a specific image set."""
    request = GetImageSetMetadataRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        version_id=_handle_field_value(version_id),
    )
    return healthimaging_operations.get_image_set_metadata(request)


@app.tool()
def list_image_set_versions(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (1-50)'
    ),
) -> ListImageSetVersionsResponse:
    """List versions of an image set."""
    request = ListImageSetVersionsRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        next_token=_handle_field_value(next_token),
        max_results=_handle_field_value(max_results),
    )
    return healthimaging_operations.list_image_set_versions(request)


@app.tool()
def update_image_set_metadata(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    latest_version_id: str = Field(description='Latest version ID of the image set'),
    update_image_set_metadata_updates: Dict[str, Any] = Field(description='Metadata updates'),
) -> UpdateImageSetMetadataResponse:
    """Update metadata for an image set."""
    request = UpdateImageSetMetadataRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        latest_version_id=latest_version_id,
        update_image_set_metadata_updates=update_image_set_metadata_updates,
    )
    return healthimaging_operations.update_image_set_metadata(request)


@app.tool()
def delete_image_set(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    version_id: Optional[str] = Field(None, description='Version ID of the image set'),
) -> DeleteImageSetResponse:
    """Delete an image set."""
    request = DeleteImageSetRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        version_id=_handle_field_value(version_id),
    )
    return healthimaging_operations.delete_image_set(request)


@app.tool()
def copy_image_set(
    datastore_id: str = Field(description='ID of the destination datastore'),
    source_image_set_id: str = Field(description='ID of the source image set'),
    copy_image_set_information: Dict[str, Any] = Field(description='Copy information'),
    source_datastore_id: Optional[str] = Field(None, description='ID of the source datastore'),
) -> CopyImageSetResponse:
    """Copy an image set."""
    request = CopyImageSetRequest(
        datastore_id=datastore_id,
        source_image_set_id=source_image_set_id,
        copy_image_set_information=copy_image_set_information,
        source_datastore_id=_handle_field_value(source_datastore_id),
    )
    return healthimaging_operations.copy_image_set(request)


@app.tool()
def get_image_frame(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    image_frame_information: Dict[str, str] = Field(description='Image frame information'),
) -> GetImageFrameResponse:
    """Get a specific image frame."""
    request = GetImageFrameRequest(
        datastore_id=datastore_id,
        image_set_id=image_set_id,
        image_frame_information=image_frame_information,
    )
    return healthimaging_operations.get_image_frame(request)


@app.tool()
def list_tags_for_resource(
    resource_arn: str = Field(description='The ARN of the resource to list tags for'),
) -> ListTagsForResourceResponse:
    """List tags for a resource."""
    request = ListTagsForResourceRequest(resource_arn=resource_arn)
    return healthimaging_operations.list_tags_for_resource(request)


@app.tool()
def tag_resource(
    resource_arn: str = Field(description='The ARN of the resource to tag'),
    tags: Dict[str, str] = Field(description='The tags to apply to the resource'),
) -> TagResourceResponse:
    """Add tags to a resource."""
    request = TagResourceRequest(resource_arn=resource_arn, tags=tags)
    return healthimaging_operations.tag_resource(request)


@app.tool()
def untag_resource(
    resource_arn: str = Field(description='The ARN of the resource to untag'),
    tag_keys: List[str] = Field(description='The tag keys to remove from the resource'),
) -> UntagResourceResponse:
    """Remove tags from a resource."""
    request = UntagResourceRequest(resource_arn=resource_arn, tag_keys=tag_keys)
    return healthimaging_operations.untag_resource(request)


@app.tool()
def start_dicom_export_job(
    datastore_id: str = Field(description='ID of the source datastore'),
    data_access_role_arn: str = Field(description='IAM role ARN for data access'),
    output_s3_uri: str = Field(description='S3 URI for the output data'),
    job_name: Optional[str] = Field(None, description='Name for the export job'),
    client_token: Optional[str] = Field(None, description='Client token for idempotency'),
    study_instance_uid: Optional[str] = Field(None, description='Study instance UID to export'),
    series_instance_uid: Optional[str] = Field(None, description='Series instance UID to export'),
    sop_instance_uid: Optional[str] = Field(None, description='SOP instance UID to export'),
    submitted_before: Optional[str] = Field(
        None, description='Export images submitted before this date'
    ),
    submitted_after: Optional[str] = Field(
        None, description='Export images submitted after this date'
    ),
) -> StartDICOMExportJobResponse:
    """Start a DICOM export job."""
    request = StartDICOMExportJobRequest(
        datastore_id=datastore_id,
        data_access_role_arn=data_access_role_arn,
        output_s3_uri=output_s3_uri,
        job_name=_handle_field_value(job_name),
        client_token=_handle_field_value(client_token),
        study_instance_uid=_handle_field_value(study_instance_uid),
        series_instance_uid=_handle_field_value(series_instance_uid),
        sop_instance_uid=_handle_field_value(sop_instance_uid),
        submitted_before=_handle_field_value(submitted_before),
        submitted_after=_handle_field_value(submitted_after),
    )
    return healthimaging_operations.start_dicom_export_job(request)


@app.tool()
def get_dicom_export_job(
    datastore_id: str = Field(description='ID of the datastore'),
    job_id: str = Field(description='ID of the export job'),
) -> GetDICOMExportJobResponse:
    """Get information about a DICOM export job."""
    request = GetDICOMExportJobRequest(datastore_id=datastore_id, job_id=job_id)
    return healthimaging_operations.get_dicom_export_job(request)


@app.tool()
def list_dicom_export_jobs(
    datastore_id: str = Field(description='ID of the datastore'),
    job_status: Optional[str] = Field(
        None, description='Filter by job status (SUBMITTED, IN_PROGRESS, COMPLETED, FAILED)'
    ),
    next_token: Optional[str] = Field(None, description='Token for pagination'),
    max_results: Optional[int] = Field(
        None, description='Maximum number of results to return (1-50)'
    ),
) -> ListDICOMExportJobsResponse:
    """List DICOM export jobs for a data store."""
    request = ListDICOMExportJobsRequest(
        datastore_id=datastore_id,
        job_status=_convert_to_job_status(_handle_field_value(job_status)),
        next_token=_handle_field_value(next_token),
        max_results=_handle_field_value(max_results),
    )
    return healthimaging_operations.list_dicom_export_jobs(request)


# Advanced DICOM Operations - Complex business logic operations


@app.tool()
def delete_patient_studies(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID'),
) -> Dict[str, Any]:
    """Delete all studies for a specific patient."""
    return healthimaging_operations.delete_patient_studies(datastore_id, patient_id)


@app.tool()
def delete_study(
    datastore_id: str = Field(description='ID of the datastore'),
    study_instance_uid: str = Field(description='DICOM Study Instance UID'),
) -> Dict[str, Any]:
    """Delete all image sets for a specific study."""
    return healthimaging_operations.delete_study(datastore_id, study_instance_uid)


@app.tool()
def search_by_patient_id(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID'),
    max_results: int = Field(50, description='Maximum number of results to return'),
) -> Dict[str, Any]:
    """Search for image sets by patient ID."""
    return healthimaging_operations.search_by_patient_id(datastore_id, patient_id, max_results)


@app.tool()
def search_by_study_uid(
    datastore_id: str = Field(description='ID of the datastore'),
    study_instance_uid: str = Field(description='DICOM Study Instance UID'),
    max_results: int = Field(50, description='Maximum number of results to return'),
) -> Dict[str, Any]:
    """Search for image sets by study instance UID."""
    return healthimaging_operations.search_by_study_uid(
        datastore_id, study_instance_uid, max_results
    )


@app.tool()
def search_by_series_uid(
    datastore_id: str = Field(description='ID of the datastore'),
    series_instance_uid: str = Field(description='DICOM Series Instance UID'),
    max_results: int = Field(50, description='Maximum number of results to return'),
) -> Dict[str, Any]:
    """Search for image sets by series instance UID."""
    return healthimaging_operations.search_by_series_uid(
        datastore_id, series_instance_uid, max_results
    )


@app.tool()
def get_patient_studies(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID'),
) -> Dict[str, Any]:
    """Get all studies for a specific patient."""
    return healthimaging_operations.get_patient_studies(datastore_id, patient_id)


@app.tool()
def get_patient_series(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID'),
) -> Dict[str, Any]:
    """Get all series for a specific patient."""
    return healthimaging_operations.get_patient_series(datastore_id, patient_id)


@app.tool()
def get_study_primary_image_sets(
    datastore_id: str = Field(description='ID of the datastore'),
    study_instance_uid: str = Field(description='DICOM Study Instance UID'),
) -> Dict[str, Any]:
    """Get primary image sets for a specific study."""
    return healthimaging_operations.get_study_primary_image_sets(datastore_id, study_instance_uid)


@app.tool()
def delete_series_by_uid(
    datastore_id: str = Field(description='ID of the datastore'),
    series_instance_uid: str = Field(description='DICOM Series Instance UID to delete'),
) -> Dict[str, Any]:
    """Delete a series by SeriesInstanceUID using metadata updates."""
    return healthimaging_operations.delete_series_by_uid(datastore_id, series_instance_uid)


@app.tool()
def get_series_primary_image_set(
    datastore_id: str = Field(description='ID of the datastore'),
    series_instance_uid: str = Field(description='DICOM Series Instance UID'),
) -> Dict[str, Any]:
    """Get the primary image set for a given series."""
    return healthimaging_operations.get_series_primary_image_set(datastore_id, series_instance_uid)


@app.tool()
def get_patient_dicomweb_studies(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID'),
) -> Dict[str, Any]:
    """Retrieve DICOMweb SearchStudies level information for a given patient ID."""
    return healthimaging_operations.get_patient_dicomweb_studies(datastore_id, patient_id)


@app.tool()
def delete_instance_in_study(
    datastore_id: str = Field(description='ID of the datastore'),
    study_instance_uid: str = Field(description='DICOM Study Instance UID'),
    sop_instance_uid: str = Field(description='DICOM SOP Instance UID to delete'),
) -> Dict[str, Any]:
    """Delete a specific instance in a study."""
    return healthimaging_operations.delete_instance_in_study(
        datastore_id, study_instance_uid, sop_instance_uid
    )


@app.tool()
def delete_instance_in_series(
    datastore_id: str = Field(description='ID of the datastore'),
    series_instance_uid: str = Field(description='DICOM Series Instance UID'),
    sop_instance_uid: str = Field(description='DICOM SOP Instance UID to delete'),
) -> Dict[str, Any]:
    """Delete a specific instance in a series."""
    return healthimaging_operations.delete_instance_in_series(
        datastore_id, series_instance_uid, sop_instance_uid
    )


@app.tool()
def update_patient_study_metadata(
    datastore_id: str = Field(description='ID of the datastore'),
    study_instance_uid: str = Field(description='DICOM Study Instance UID'),
    patient_updates: Dict[str, Any] = Field(description='Patient-level DICOM metadata updates'),
    study_updates: Dict[str, Any] = Field(description='Study-level DICOM metadata updates'),
) -> Dict[str, Any]:
    """Update Patient/Study metadata for an entire study."""
    return healthimaging_operations.update_patient_study_metadata(
        datastore_id, study_instance_uid, patient_updates, study_updates
    )


# Bulk Operations - Major Value Add


@app.tool()
def bulk_update_patient_metadata(
    datastore_id: str = Field(description='ID of the datastore'),
    patient_id: str = Field(description='DICOM Patient ID to update metadata for'),
    metadata_updates: Dict[str, Any] = Field(
        description='Patient metadata updates to apply across all studies'
    ),
) -> Dict[str, Any]:
    """Update patient metadata across all studies for a patient."""
    return healthimaging_operations.bulk_update_patient_metadata(
        datastore_id, patient_id, metadata_updates
    )


@app.tool()
def bulk_delete_by_criteria(
    datastore_id: str = Field(description='ID of the datastore'),
    criteria: Dict[str, Any] = Field(
        description="Search criteria for image sets to delete (e.g., {'DICOMPatientId': 'patient123'})"
    ),
    max_deletions: int = Field(
        100, description='Maximum number of image sets to delete (safety limit)'
    ),
) -> Dict[str, Any]:
    """Delete multiple image sets matching specified criteria."""
    return healthimaging_operations.bulk_delete_by_criteria(datastore_id, criteria, max_deletions)


# DICOM Hierarchy Operations - Domain Expertise


@app.tool()
def remove_series_from_image_set(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    series_instance_uid: str = Field(
        description='DICOM Series Instance UID to remove from the image set'
    ),
) -> Dict[str, Any]:
    """Remove a specific series from an image set using DICOM hierarchy operations."""
    return healthimaging_operations.remove_series_from_image_set(
        datastore_id, image_set_id, series_instance_uid
    )


@app.tool()
def remove_instance_from_image_set(
    datastore_id: str = Field(description='ID of the datastore'),
    image_set_id: str = Field(description='ID of the image set'),
    series_instance_uid: str = Field(
        description='DICOM Series Instance UID containing the instance'
    ),
    sop_instance_uid: str = Field(
        description='DICOM SOP Instance UID to remove from the image set'
    ),
) -> Dict[str, Any]:
    """Remove a specific instance from an image set using DICOM hierarchy operations."""
    return healthimaging_operations.remove_instance_from_image_set(
        datastore_id, image_set_id, series_instance_uid, sop_instance_uid
    )


def main():
    """Main entry point for the MCP server application."""
    app.run()


if __name__ == '__main__':
    main()
