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

"""AWS HealthImaging operations implementation."""

import boto3
from . import __version__
from .models import (
    CopyImageSetRequest,
    CopyImageSetResponse,
    CreateDatastoreRequest,
    CreateDatastoreResponse,
    # Additional model classes used in operations
    DatastoreProperties,
    DatastoreSummary,
    DeleteDatastoreRequest,
    DeleteDatastoreResponse,
    DeleteImageSetRequest,
    DeleteImageSetResponse,
    DICOMExportJobProperties,
    DICOMExportJobSummary,
    DICOMImportJobProperties,
    DICOMImportJobSummary,
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
    ImageSetProperties,
    ImageSetsMetadataSummary,
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
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict


# optimize this (maybe with a singleton to avoid so many creations)?
def get_medical_imaging_client():
    """Get a medical imaging client with proper user agent."""
    client = boto3.client(
        'medical-imaging',
        config=Config(user_agent_extra=f'awslabs/mcp/healthimaging-mcp-server/{__version__}'),
    )
    return client


# Constants
DATASTORE_ID_LENGTH = 32
MAX_SEARCH_COUNT = 100  # Maximum number of resources per search request


def _convert_datetime_to_string(dt_obj):
    """Convert datetime object to ISO format string if it's a datetime object."""
    if dt_obj is None:
        return None
    if hasattr(dt_obj, 'isoformat'):
        # Handle datetime objects (including timezone-aware ones)
        return dt_obj.isoformat()
    # If it's already a string, return as-is
    return str(dt_obj)


def create_datastore_operation(request: CreateDatastoreRequest) -> CreateDatastoreResponse:
    """Create a new data store in AWS HealthImaging."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {'datastoreName': request.datastore_name}

    if request.tags:
        kwargs['tags'] = request.tags  # type: ignore[assignment]
    if request.kms_key_arn:
        kwargs['kmsKeyArn'] = request.kms_key_arn

    response = client.create_datastore(**kwargs)

    return CreateDatastoreResponse(
        datastore_id=response['datastoreId'], datastore_status=response['datastoreStatus']
    )


def delete_datastore_operation(request: DeleteDatastoreRequest) -> DeleteDatastoreResponse:
    """Delete a data store from AWS HealthImaging."""
    client = get_medical_imaging_client()

    response = client.delete_datastore(datastoreId=request.datastore_id)

    return DeleteDatastoreResponse(
        datastore_id=response['datastoreId'], datastore_status=response['datastoreStatus']
    )


def get_datastore_operation(request: GetDatastoreRequest) -> GetDatastoreResponse:
    """Get information about a specific data store."""
    client = get_medical_imaging_client()

    response = client.get_datastore(datastoreId=request.datastore_id)

    datastore_properties_data = response['datastoreProperties']

    datastore_properties = DatastoreProperties(
        datastore_id=datastore_properties_data['datastoreId'],
        datastore_name=datastore_properties_data['datastoreName'],
        datastore_status=datastore_properties_data['datastoreStatus'],
        datastore_arn=datastore_properties_data.get('datastoreArn'),
        created_at=_convert_datetime_to_string(datastore_properties_data.get('createdAt')),
        updated_at=_convert_datetime_to_string(datastore_properties_data.get('updatedAt')),
        kms_key_arn=datastore_properties_data.get('kmsKeyArn'),
    )

    return GetDatastoreResponse(datastore_properties=datastore_properties)


def list_datastores_operation(request: ListDatastoresRequest) -> ListDatastoresResponse:
    """List all data stores in the account."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {}
    if request.datastore_status:
        kwargs['datastoreStatus'] = request.datastore_status
    if request.next_token:
        kwargs['nextToken'] = request.next_token
    if request.max_results:
        kwargs['maxResults'] = request.max_results  # type: ignore[assignment]

    response = client.list_datastores(**kwargs)

    datastores = []
    for ds in response.get('datastoreSummaries', []):
        # Convert datetime objects to ISO format strings
        created_at = _convert_datetime_to_string(ds.get('createdAt'))
        updated_at = _convert_datetime_to_string(ds.get('updatedAt'))

        datastores.append(
            DatastoreSummary(
                datastore_id=ds['datastoreId'],
                datastore_name=ds['datastoreName'],
                datastore_status=ds['datastoreStatus'],
                datastore_arn=ds.get('datastoreArn'),
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    return ListDatastoresResponse(
        datastore_summaries=datastores, next_token=response.get('nextToken')
    )


def start_dicom_import_job_operation(
    request: StartDICOMImportJobRequest,
) -> StartDICOMImportJobResponse:
    """Start a DICOM import job."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'dataAccessRoleArn': request.data_access_role_arn,
        'inputS3Uri': request.input_s3_uri,
        'outputS3Uri': request.output_s3_uri,
    }

    if request.client_token:
        kwargs['clientToken'] = request.client_token
    if request.job_name:
        kwargs['jobName'] = request.job_name

    response = client.start_dicom_import_job(**kwargs)

    return StartDICOMImportJobResponse(
        datastore_id=response['datastoreId'],
        job_id=response['jobId'],
        job_status=response['jobStatus'],
        submitted_at=_convert_datetime_to_string(response.get('submittedAt')),
    )


def get_dicom_import_job_operation(request: GetDICOMImportJobRequest) -> GetDICOMImportJobResponse:
    """Get information about a DICOM import job."""
    client = get_medical_imaging_client()

    response = client.get_dicom_import_job(datastoreId=request.datastore_id, jobId=request.job_id)

    job_properties_data = response['jobProperties']

    job_properties = DICOMImportJobProperties(
        job_id=job_properties_data['jobId'],
        job_name=job_properties_data.get('jobName', ''),
        job_status=job_properties_data['jobStatus'],
        datastore_id=job_properties_data['datastoreId'],
        data_access_role_arn=job_properties_data.get('dataAccessRoleArn', ''),
        ended_at=_convert_datetime_to_string(job_properties_data.get('endedAt')),
        submitted_at=_convert_datetime_to_string(job_properties_data.get('submittedAt')),
        input_s3_uri=job_properties_data.get('inputS3Uri'),
        output_s3_uri=job_properties_data.get('outputS3Uri'),
        message=job_properties_data.get('message'),
    )

    return GetDICOMImportJobResponse(job_properties=job_properties)


def list_dicom_import_jobs_operation(
    request: ListDICOMImportJobsRequest,
) -> ListDICOMImportJobsResponse:
    """List DICOM import jobs for a data store."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {'datastoreId': request.datastore_id}

    if request.job_status:
        kwargs['jobStatus'] = request.job_status
    if request.next_token:
        kwargs['nextToken'] = request.next_token
    if request.max_results:
        kwargs['maxResults'] = request.max_results  # type: ignore[assignment]

    response = client.list_dicom_import_jobs(**kwargs)

    job_summaries = []
    for job in response.get('jobSummaries', []):
        job_summaries.append(
            DICOMImportJobSummary(
                job_id=job['jobId'],
                job_name=job.get('jobName'),
                job_status=job['jobStatus'],
                datastore_id=job['datastoreId'],
                ended_at=_convert_datetime_to_string(job.get('endedAt')),
                submitted_at=_convert_datetime_to_string(job.get('submittedAt')),
                message=job.get('message'),
            )
        )

    return ListDICOMImportJobsResponse(
        job_summaries=job_summaries, next_token=response.get('nextToken')
    )


def search_image_sets_operation(request: SearchImageSetsRequest) -> SearchImageSetsResponse:
    """Search for image sets in a data store."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {'datastoreId': request.datastore_id}

    if request.search_criteria:
        kwargs['searchCriteria'] = request.search_criteria  # type: ignore[assignment]
    if request.next_token:
        kwargs['nextToken'] = request.next_token
    if request.max_results:
        kwargs['maxResults'] = request.max_results  # type: ignore[assignment]

    response = client.search_image_sets(**kwargs)

    image_sets_metadata_summaries = []
    for summary in response.get('imageSetsMetadataSummaries', []):
        image_sets_metadata_summaries.append(
            ImageSetsMetadataSummary(
                image_set_id=summary['imageSetId'],
                version=summary.get('version'),
                created_at=_convert_datetime_to_string(summary.get('createdAt')),
                updated_at=_convert_datetime_to_string(summary.get('updatedAt')),
                dicom_tags=summary.get('DICOMTags', {}),
            )
        )

    return SearchImageSetsResponse(
        image_sets_metadata_summaries=image_sets_metadata_summaries,
        next_token=response.get('nextToken'),
    )


def get_image_set_operation(request: GetImageSetRequest) -> GetImageSetResponse:
    """Get information about a specific image set."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'imageSetId': request.image_set_id,
    }

    if request.version_id:
        kwargs['versionId'] = request.version_id

    response = client.get_image_set(**kwargs)

    return GetImageSetResponse(
        datastore_id=response['datastoreId'],
        image_set_id=response['imageSetId'],
        version_id=response['versionId'],
        image_set_state=response['imageSetState'],
        image_set_workflow_status=response.get('imageSetWorkflowStatus'),
        created_at=_convert_datetime_to_string(response.get('createdAt')),
        updated_at=_convert_datetime_to_string(response.get('updatedAt')),
        deleted_at=_convert_datetime_to_string(response.get('deletedAt')),
        message=response.get('message'),
    )


def get_image_set_metadata_operation(
    request: GetImageSetMetadataRequest,
) -> GetImageSetMetadataResponse:
    """Get metadata for a specific image set."""
    import base64

    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'imageSetId': request.image_set_id,
    }

    if request.version_id:
        kwargs['versionId'] = request.version_id

    response = client.get_image_set_metadata(**kwargs)

    # Handle the streaming body properly
    metadata_blob = response.get('imageSetMetadataBlob')
    if metadata_blob is not None:
        try:
            # Check if it's a StreamingBody object
            if hasattr(metadata_blob, 'read'):
                # Read all content from the stream
                content = metadata_blob.read()
                # Ensure it's bytes
                if isinstance(content, str):
                    metadata_bytes = content.encode('utf-8')
                else:
                    metadata_bytes = content
            elif isinstance(metadata_blob, bytes):
                # Already bytes, use as-is
                metadata_bytes = metadata_blob
            else:
                # Convert to bytes
                metadata_bytes = str(metadata_blob).encode('utf-8')

            # Base64 encode for JSON serialization
            metadata_blob = base64.b64encode(metadata_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f'Error reading metadata blob: {e}')
            # Fallback to empty base64 string
            metadata_blob = base64.b64encode(b'').decode('utf-8')
    else:
        # Default to empty base64 string if None
        metadata_blob = base64.b64encode(b'').decode('utf-8')

    return GetImageSetMetadataResponse(
        image_set_metadata_blob=metadata_blob,
        content_type=response.get('contentType'),
        content_encoding=response.get('contentEncoding'),
    )


def list_image_set_versions_operation(
    request: ListImageSetVersionsRequest,
) -> ListImageSetVersionsResponse:
    """List versions of an image set."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'imageSetId': request.image_set_id,
    }

    if request.next_token:
        kwargs['nextToken'] = request.next_token
    if request.max_results:
        kwargs['maxResults'] = request.max_results  # type: ignore[assignment]

    response = client.list_image_set_versions(**kwargs)

    image_set_properties_list = []
    for props in response.get('imageSetPropertiesList', []):
        image_set_properties_list.append(
            ImageSetProperties(
                image_set_id=props['imageSetId'],
                version_id=props['versionId'],
                image_set_state=props['imageSetState'],
                image_set_workflow_status=props.get('imageSetWorkflowStatus'),
                created_at=_convert_datetime_to_string(props.get('createdAt')),
                updated_at=_convert_datetime_to_string(props.get('updatedAt')),
                deleted_at=_convert_datetime_to_string(props.get('deletedAt')),
                message=props.get('message'),
            )
        )

    return ListImageSetVersionsResponse(
        image_set_properties_list=image_set_properties_list, next_token=response.get('nextToken')
    )


def update_image_set_metadata_operation(
    request: UpdateImageSetMetadataRequest,
) -> UpdateImageSetMetadataResponse:
    """Update metadata for an image set."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'imageSetId': request.image_set_id,
        'latestVersionId': request.latest_version_id,
        'updateImageSetMetadataUpdates': request.update_image_set_metadata_updates,
    }

    response = client.update_image_set_metadata(**kwargs)

    return UpdateImageSetMetadataResponse(
        datastore_id=response['datastoreId'],
        image_set_id=response['imageSetId'],
        latest_version_id=response['latestVersionId'],
        image_set_state=response['imageSetState'],
        image_set_workflow_status=response.get('imageSetWorkflowStatus'),
        created_at=_convert_datetime_to_string(response.get('createdAt')),
        updated_at=_convert_datetime_to_string(response.get('updatedAt')),
        message=response.get('message'),
    )


def delete_image_set_operation(request: DeleteImageSetRequest) -> DeleteImageSetResponse:
    """Delete an image set."""
    client = get_medical_imaging_client()

    response = client.delete_image_set(
        datastoreId=request.datastore_id, imageSetId=request.image_set_id
    )

    return DeleteImageSetResponse(
        datastore_id=response['datastoreId'],
        image_set_id=response['imageSetId'],
        image_set_state=response['imageSetState'],
    )


def copy_image_set_operation(request: CopyImageSetRequest) -> CopyImageSetResponse:
    """Copy an image set."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'sourceDatastoreId': request.source_datastore_id,
        'sourceImageSetId': request.source_image_set_id,
        'destinationDatastoreId': request.datastore_id,
    }

    if request.copy_image_set_information:
        kwargs['copyImageSetInformation'] = request.copy_image_set_information

    response = client.copy_image_set(**kwargs)

    # Create ImageSetProperties objects from the response
    source_props = ImageSetProperties(
        image_set_id=response['sourceImageSetProperties']['imageSetId'],
        version_id=response['sourceImageSetProperties']['versionId'],
        image_set_state=response['sourceImageSetProperties'].get('imageSetState', 'ACTIVE'),
        image_set_workflow_status=response['sourceImageSetProperties'].get(
            'imageSetWorkflowStatus'
        ),
        created_at=_convert_datetime_to_string(
            response['sourceImageSetProperties'].get('createdAt')
        ),
        updated_at=_convert_datetime_to_string(
            response['sourceImageSetProperties'].get('updatedAt')
        ),
        deleted_at=_convert_datetime_to_string(
            response['sourceImageSetProperties'].get('deletedAt')
        ),
        message=response['sourceImageSetProperties'].get('message'),
    )

    dest_props = ImageSetProperties(
        image_set_id=response['destinationImageSetProperties']['imageSetId'],
        version_id=response['destinationImageSetProperties']['versionId'],
        image_set_state=response['destinationImageSetProperties'].get('imageSetState', 'ACTIVE'),
        image_set_workflow_status=response['destinationImageSetProperties'].get(
            'imageSetWorkflowStatus'
        ),
        created_at=_convert_datetime_to_string(
            response['destinationImageSetProperties'].get('createdAt')
        ),
        updated_at=_convert_datetime_to_string(
            response['destinationImageSetProperties'].get('updatedAt')
        ),
        deleted_at=_convert_datetime_to_string(
            response['destinationImageSetProperties'].get('deletedAt')
        ),
        message=response['destinationImageSetProperties'].get('message'),
    )

    return CopyImageSetResponse(
        datastore_id=response['datastoreId'],
        source_image_set_properties=source_props,
        destination_image_set_properties=dest_props,
    )


def get_image_frame_operation(request: GetImageFrameRequest) -> GetImageFrameResponse:
    """Get a specific image frame."""
    import base64

    client = get_medical_imaging_client()

    response = client.get_image_frame(
        datastoreId=request.datastore_id,
        imageSetId=request.image_set_id,
        imageFrameInformation=request.image_frame_information,
    )

    # Handle the streaming body properly
    image_frame_blob = response.get('imageFrameBlob')
    if image_frame_blob is not None:
        try:
            # Check if it's a StreamingBody object
            if hasattr(image_frame_blob, 'read'):
                # Read all content from the stream
                content = image_frame_blob.read()
                # Ensure it's bytes
                if isinstance(content, str):
                    frame_bytes = content.encode('utf-8')
                else:
                    frame_bytes = content
            elif isinstance(image_frame_blob, bytes):
                # Already bytes, use as-is
                frame_bytes = image_frame_blob
            else:
                # Convert to bytes
                frame_bytes = str(image_frame_blob).encode('utf-8')

            # Base64 encode for JSON serialization
            image_frame_blob = base64.b64encode(frame_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f'Error reading image frame blob: {e}')
            # Fallback to empty base64 string
            image_frame_blob = base64.b64encode(b'').decode('utf-8')
    else:
        # Default to empty base64 string if None
        image_frame_blob = base64.b64encode(b'').decode('utf-8')

    return GetImageFrameResponse(
        image_frame_blob=image_frame_blob, content_type=response.get('contentType')
    )


def list_tags_for_resource_operation(
    request: ListTagsForResourceRequest,
) -> ListTagsForResourceResponse:
    """List tags for a resource."""
    client = get_medical_imaging_client()

    response = client.list_tags_for_resource(resourceArn=request.resource_arn)

    return ListTagsForResourceResponse(tags=response.get('tags', {}))


def tag_resource_operation(request: TagResourceRequest) -> TagResourceResponse:
    """Add tags to a resource."""
    client = get_medical_imaging_client()

    client.tag_resource(resourceArn=request.resource_arn, tags=request.tags)

    return TagResourceResponse(success=True)


def untag_resource_operation(request: UntagResourceRequest) -> UntagResourceResponse:
    """Remove tags from a resource."""
    client = get_medical_imaging_client()

    client.untag_resource(resourceArn=request.resource_arn, tagKeys=request.tag_keys)

    return UntagResourceResponse(success=True)


def start_dicom_export_job_operation(
    request: StartDICOMExportJobRequest,
) -> StartDICOMExportJobResponse:
    """Start a DICOM export job."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {
        'datastoreId': request.datastore_id,
        'dataAccessRoleArn': request.data_access_role_arn,
        'outputS3Uri': request.output_s3_uri,
    }

    if request.client_token:
        kwargs['clientToken'] = request.client_token
    if request.job_name:
        kwargs['jobName'] = request.job_name
    if request.study_instance_uid:
        kwargs['studyInstanceUID'] = request.study_instance_uid
    if request.series_instance_uid:
        kwargs['seriesInstanceUID'] = request.series_instance_uid
    if request.sop_instance_uid:
        kwargs['sopInstanceUID'] = request.sop_instance_uid
    if request.submitted_before:
        kwargs['submittedBefore'] = request.submitted_before
    if request.submitted_after:
        kwargs['submittedAfter'] = request.submitted_after

    response = client.start_dicom_export_job(**kwargs)

    return StartDICOMExportJobResponse(
        datastore_id=response['datastoreId'],
        job_id=response['jobId'],
        job_status=response['jobStatus'],
        submitted_at=_convert_datetime_to_string(response.get('submittedAt')),
    )


def get_dicom_export_job_operation(request: GetDICOMExportJobRequest) -> GetDICOMExportJobResponse:
    """Get information about a DICOM export job."""
    client = get_medical_imaging_client()

    response = client.get_dicom_export_job(datastoreId=request.datastore_id, jobId=request.job_id)

    job_properties = DICOMExportJobProperties(
        job_id=response['jobProperties']['jobId'],
        job_name=response['jobProperties'].get('jobName'),
        job_status=response['jobProperties']['jobStatus'],
        datastore_id=response['jobProperties']['datastoreId'],
        data_access_role_arn=response['jobProperties']['dataAccessRoleArn'],
        ended_at=_convert_datetime_to_string(response['jobProperties'].get('endedAt')),
        submitted_at=_convert_datetime_to_string(response['jobProperties'].get('submittedAt')),
        output_s3_uri=response['jobProperties']['outputS3Uri'],
        message=response['jobProperties'].get('message'),
    )

    return GetDICOMExportJobResponse(job_properties=job_properties)


def list_dicom_export_jobs_operation(
    request: ListDICOMExportJobsRequest,
) -> ListDICOMExportJobsResponse:
    """List DICOM export jobs for a data store."""
    client = get_medical_imaging_client()

    kwargs: Dict[str, Any] = {'datastoreId': request.datastore_id}

    if request.job_status:
        kwargs['jobStatus'] = request.job_status
    if request.next_token:
        kwargs['nextToken'] = request.next_token
    if request.max_results:
        kwargs['maxResults'] = request.max_results  # type: ignore[assignment]

    response = client.list_dicom_export_jobs(**kwargs)

    job_summaries = []
    for job in response.get('jobSummaries', []):
        job_summaries.append(
            DICOMExportJobSummary(
                job_id=job['jobId'],
                job_name=job.get('jobName'),
                job_status=job['jobStatus'],
                datastore_id=job['datastoreId'],
                ended_at=_convert_datetime_to_string(job.get('endedAt')),
                submitted_at=_convert_datetime_to_string(job.get('submittedAt')),
                message=job.get('message'),
            )
        )

    return ListDICOMExportJobsResponse(
        job_summaries=job_summaries, next_token=response.get('nextToken')
    )


# Wrapper functions that match the names called from server.py
def create_datastore(request: CreateDatastoreRequest) -> CreateDatastoreResponse:
    """Create a new data store in AWS HealthImaging."""
    return create_datastore_operation(request)


def delete_datastore(request: DeleteDatastoreRequest) -> DeleteDatastoreResponse:
    """Delete a data store from AWS HealthImaging."""
    return delete_datastore_operation(request)


def get_datastore(request: GetDatastoreRequest) -> GetDatastoreResponse:
    """Get information about a specific data store."""
    return get_datastore_operation(request)


def list_datastores(request: ListDatastoresRequest) -> ListDatastoresResponse:
    """List all data stores in the account."""
    return list_datastores_operation(request)


def start_dicom_import_job(request: StartDICOMImportJobRequest) -> StartDICOMImportJobResponse:
    """Start a DICOM import job."""
    return start_dicom_import_job_operation(request)


def get_dicom_import_job(request: GetDICOMImportJobRequest) -> GetDICOMImportJobResponse:
    """Get information about a DICOM import job."""
    return get_dicom_import_job_operation(request)


def list_dicom_import_jobs(request: ListDICOMImportJobsRequest) -> ListDICOMImportJobsResponse:
    """List DICOM import jobs for a data store."""
    return list_dicom_import_jobs_operation(request)


def search_image_sets(request: SearchImageSetsRequest) -> SearchImageSetsResponse:
    """Search for image sets in a data store."""
    return search_image_sets_operation(request)


def get_image_set(request: GetImageSetRequest) -> GetImageSetResponse:
    """Get information about a specific image set."""
    return get_image_set_operation(request)


def get_image_set_metadata(request: GetImageSetMetadataRequest) -> GetImageSetMetadataResponse:
    """Get metadata for a specific image set."""
    return get_image_set_metadata_operation(request)


def list_image_set_versions(request: ListImageSetVersionsRequest) -> ListImageSetVersionsResponse:
    """List versions of an image set."""
    return list_image_set_versions_operation(request)


def update_image_set_metadata(
    request: UpdateImageSetMetadataRequest,
) -> UpdateImageSetMetadataResponse:
    """Update metadata for an image set."""
    return update_image_set_metadata_operation(request)


def delete_image_set(request: DeleteImageSetRequest) -> DeleteImageSetResponse:
    """Delete an image set."""
    return delete_image_set_operation(request)


def copy_image_set(request: CopyImageSetRequest) -> CopyImageSetResponse:
    """Copy an image set."""
    return copy_image_set_operation(request)


def get_image_frame(request: GetImageFrameRequest) -> GetImageFrameResponse:
    """Get a specific image frame."""
    return get_image_frame_operation(request)


def list_tags_for_resource(request: ListTagsForResourceRequest) -> ListTagsForResourceResponse:
    """List tags for a resource."""
    return list_tags_for_resource_operation(request)


def tag_resource(request: TagResourceRequest) -> TagResourceResponse:
    """Add tags to a resource."""
    return tag_resource_operation(request)


def untag_resource(request: UntagResourceRequest) -> UntagResourceResponse:
    """Remove tags from a resource."""
    return untag_resource_operation(request)


def start_dicom_export_job(request: StartDICOMExportJobRequest) -> StartDICOMExportJobResponse:
    """Start a DICOM export job."""
    return start_dicom_export_job_operation(request)


def get_dicom_export_job(request: GetDICOMExportJobRequest) -> GetDICOMExportJobResponse:
    """Get information about a DICOM export job."""
    return get_dicom_export_job_operation(request)


def list_dicom_export_jobs(request: ListDICOMExportJobsRequest) -> ListDICOMExportJobsResponse:
    """List DICOM export jobs for a data store."""
    return list_dicom_export_jobs_operation(request)


# Advanced DICOM Operations - Restored from original implementation


def delete_patient_studies_operation(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Delete all studies for a specific patient."""
    try:
        client = get_medical_imaging_client()

        # First, search for all image sets for this patient
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        deleted_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    delete_response = client.delete_image_set(
                        datastoreId=datastore_id, imageSetId=image_set['imageSetId']
                    )
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'deleted',
                            'response': delete_response,
                        }
                    )
                except ClientError as e:
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'patientId': patient_id,
            'deletedImageSets': deleted_image_sets,
            'totalDeleted': len([img for img in deleted_image_sets if img['status'] == 'deleted']),
        }

    except ClientError as e:
        logger.warning(f'Error deleting patient studies: {e}')
        raise


def delete_study_operation(datastore_id: str, study_instance_uid: str) -> Dict[str, Any]:
    """Delete all image sets for a specific study."""
    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this study
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        deleted_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    delete_response = client.delete_image_set(
                        datastoreId=datastore_id, imageSetId=image_set['imageSetId']
                    )
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'deleted',
                            'response': delete_response,
                        }
                    )
                except ClientError as e:
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'studyInstanceUID': study_instance_uid,
            'deletedImageSets': deleted_image_sets,
            'totalDeleted': len([img for img in deleted_image_sets if img['status'] == 'deleted']),
        }

    except ClientError as e:
        logger.warning(f'Error deleting study: {e}')
        raise


def search_by_patient_id_operation(
    datastore_id: str, patient_id: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by patient ID."""
    try:
        client = get_medical_imaging_client()

        response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=max_results,
        )

        return response

    except ClientError as e:
        logger.warning(f'Error searching by patient ID {patient_id}: {e}')
        raise


def search_by_study_uid_operation(
    datastore_id: str, study_instance_uid: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by study instance UID."""
    try:
        client = get_medical_imaging_client()

        response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=max_results,
        )

        return response

    except ClientError as e:
        logger.warning(f'Error searching by study UID {study_instance_uid}: {e}')
        raise


def search_by_series_uid_operation(
    datastore_id: str, series_instance_uid: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by series instance UID."""
    try:
        client = get_medical_imaging_client()

        response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMSeriesInstanceUID': series_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=max_results,
        )

        return response

    except ClientError as e:
        logger.warning(f'Error searching by series UID {series_instance_uid}: {e}')
        raise


def get_patient_studies_operation(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Get all studies for a specific patient."""
    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this patient
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        studies = {}

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                # Extract study information from DICOM tags
                dicom_tags = image_set.get('DICOMTags', {})
                study_uid = dicom_tags.get('DICOMStudyInstanceUID')

                if study_uid:
                    if study_uid not in studies:
                        studies[study_uid] = {
                            'studyInstanceUID': study_uid,
                            'studyDescription': dicom_tags.get('DICOMStudyDescription', ''),
                            'studyDate': dicom_tags.get('DICOMStudyDate', ''),
                            'imageSets': [],
                        }

                    studies[study_uid]['imageSets'].append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'version': image_set.get('version', ''),
                            'createdAt': image_set.get('createdAt', ''),
                            'updatedAt': image_set.get('updatedAt', ''),
                        }
                    )

        return {
            'patientId': patient_id,
            'studies': list(studies.values()),
            'totalStudies': len(studies),
        }

    except ClientError as e:
        logger.warning(f'Error getting patient studies: {e}')
        raise


def get_patient_series_operation(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Get all series for a specific patient."""
    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this patient
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        series = {}

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                # Extract series information from DICOM tags
                dicom_tags = image_set.get('DICOMTags', {})
                series_uid = dicom_tags.get('DICOMSeriesInstanceUID')

                if series_uid:
                    if series_uid not in series:
                        series[series_uid] = {
                            'seriesInstanceUID': series_uid,
                            'seriesDescription': dicom_tags.get('DICOMSeriesDescription', ''),
                            'modality': dicom_tags.get('DICOMModality', ''),
                            'studyInstanceUID': dicom_tags.get('DICOMStudyInstanceUID', ''),
                            'imageSets': [],
                        }

                    series[series_uid]['imageSets'].append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'version': image_set.get('version', ''),
                            'createdAt': image_set.get('createdAt', ''),
                            'updatedAt': image_set.get('updatedAt', ''),
                        }
                    )

        return {
            'patientId': patient_id,
            'series': list(series.values()),
            'totalSeries': len(series),
        }

    except ClientError as e:
        logger.warning(f'Error getting patient series: {e}')
        raise


def get_study_primary_image_sets_operation(
    datastore_id: str, study_instance_uid: str
) -> Dict[str, Any]:
    """Get primary image sets for a specific study."""
    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this study
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        primary_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                # Consider the first version as primary
                if image_set.get('version') == '1':
                    primary_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'version': image_set.get('version', ''),
                            'createdAt': image_set.get('createdAt', ''),
                            'updatedAt': image_set.get('updatedAt', ''),
                            'dicomTags': image_set.get('DICOMTags', {}),
                        }
                    )

        return {
            'studyInstanceUID': study_instance_uid,
            'primaryImageSets': primary_image_sets,
            'totalPrimaryImageSets': len(primary_image_sets),
        }

    except ClientError as e:
        logger.warning(f'Error getting study primary image sets: {e}')
        raise


def delete_series_by_uid_operation(datastore_id: str, series_instance_uid: str) -> Dict[str, Any]:
    """Delete a series by SeriesInstanceUID using metadata updates."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for image sets containing this series
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMSeriesInstanceUID': series_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        updated_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    # Create removable attributes for the series
                    updates = {
                        'DICOMUpdates': {
                            'removableAttributes': json.dumps(
                                {'SchemaVersion': '1.1', 'Series': {series_instance_uid: {}}}
                            ).encode()
                        }
                    }

                    update_response = client.update_image_set_metadata(
                        datastoreId=datastore_id,
                        imageSetId=image_set['imageSetId'],
                        latestVersionId=image_set['version'],
                        updateImageSetMetadataUpdates=updates,
                    )

                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'updated',
                            'response': update_response,
                        }
                    )
                except ClientError as e:
                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'seriesInstanceUID': series_instance_uid,
            'updatedImageSets': updated_image_sets,
            'totalUpdated': len([img for img in updated_image_sets if img['status'] == 'updated']),
        }

    except ClientError as e:
        logger.warning(f'Error deleting series {series_instance_uid}: {e}')
        raise


def get_series_primary_image_set_operation(
    datastore_id: str, series_instance_uid: str
) -> Dict[str, Any]:
    """Get the primary image set for a given series."""
    try:
        client = get_medical_imaging_client()

        response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMSeriesInstanceUID': series_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        primary_image_set = None

        if 'imageSetsMetadataSummaries' in response:
            # Filter for primary image sets (version 1)
            for image_set in response['imageSetsMetadataSummaries']:
                if image_set.get('version') == '1':
                    primary_image_set = {
                        'imageSetId': image_set['imageSetId'],
                        'version': image_set.get('version', ''),
                        'createdAt': image_set.get('createdAt', ''),
                        'updatedAt': image_set.get('updatedAt', ''),
                        'dicomTags': image_set.get('DICOMTags', {}),
                    }
                    break

        return {
            'seriesInstanceUID': series_instance_uid,
            'primaryImageSet': primary_image_set,
            'found': primary_image_set is not None,
        }

    except ClientError as e:
        logger.warning(f'Error getting primary image set for series {series_instance_uid}: {e}')
        raise


def get_patient_dicomweb_studies_operation(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Retrieve DICOMweb SearchStudies level information for a given patient ID."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this patient
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        studies = {}

        if 'imageSetsMetadataSummaries' in search_response:
            # Filter for primary image sets only
            primary_image_sets = [
                img
                for img in search_response['imageSetsMetadataSummaries']
                if img.get('version') == '1'
            ]

            # Get unique study UIDs
            study_uids = {
                img['DICOMTags'].get('DICOMStudyInstanceUID')
                for img in primary_image_sets
                if img['DICOMTags'].get('DICOMStudyInstanceUID')
            }

            for study_uid in study_uids:
                # Find a representative image set for this study
                study_image_set = next(
                    img
                    for img in primary_image_sets
                    if img['DICOMTags'].get('DICOMStudyInstanceUID') == study_uid
                )

                try:
                    # Get metadata for this image set
                    metadata_response = client.get_image_set_metadata(
                        datastoreId=datastore_id, imageSetId=study_image_set['imageSetId']
                    )

                    # Handle the streaming body
                    metadata_blob = metadata_response.get('imageSetMetadataBlob')
                    if hasattr(metadata_blob, 'read'):
                        content = metadata_blob.read()
                        if isinstance(content, str):
                            metadata_bytes = content.encode('utf-8')
                        else:
                            metadata_bytes = content
                    else:
                        metadata_bytes = str(metadata_blob).encode('utf-8')

                    # Parse the metadata JSON
                    metadata = json.loads(metadata_bytes.decode('utf-8'))

                    # Extract Patient and Study level DICOM attributes
                    patient_dicom = metadata.get('Patient', {}).get('DICOM', {})
                    study_dicom = {}

                    # Extract study information from the metadata structure
                    if 'Study' in metadata and 'DICOM' in metadata['Study']:
                        study_data = metadata['Study']['DICOM']
                        if 'StudyInstanceUID' in study_data:
                            for uid, study_info in study_data['StudyInstanceUID'].items():
                                if uid == study_uid:
                                    study_dicom = study_info.get('DICOM', {})
                                    break

                    studies[study_uid] = {
                        'studyInstanceUID': study_uid,
                        'patientDICOM': patient_dicom,
                        'studyDICOM': study_dicom,
                        'imageSetId': study_image_set['imageSetId'],
                    }

                except Exception as e:
                    logger.error(
                        f'Error getting metadata for image set {study_image_set["imageSetId"]}: {e}'
                    )
                    studies[study_uid] = {
                        'studyInstanceUID': study_uid,
                        'error': str(e),
                        'imageSetId': study_image_set['imageSetId'],
                    }

        return {
            'patientId': patient_id,
            'studies': list(studies.values()),
            'totalStudies': len(studies),
        }

    except ClientError as e:
        logger.warning(f'Error getting DICOMweb studies for patient {patient_id}: {e}')
        raise


def delete_instance_in_study_operation(
    datastore_id: str, study_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Delete a specific instance in a study."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for image sets containing this study
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        updated_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    # Get current metadata to find the instance
                    metadata_response = client.get_image_set_metadata(
                        datastoreId=datastore_id, imageSetId=image_set['imageSetId']
                    )

                    # Handle the streaming body
                    metadata_blob = metadata_response.get('imageSetMetadataBlob')
                    if hasattr(metadata_blob, 'read'):
                        content = metadata_blob.read()
                        if isinstance(content, str):
                            metadata_bytes = content.encode('utf-8')
                        else:
                            metadata_bytes = content
                    else:
                        metadata_bytes = str(metadata_blob).encode('utf-8')

                    metadata = json.loads(metadata_bytes.decode('utf-8'))

                    # Find the instance in the metadata
                    instance_found = False
                    series_uid = None

                    if 'Study' in metadata and 'DICOM' in metadata['Study']:
                        study_data = metadata['Study']['DICOM']
                        if 'StudyInstanceUID' in study_data:
                            for uid, study_info in study_data['StudyInstanceUID'].items():
                                if uid == study_instance_uid and 'Series' in study_info:
                                    for s_uid, series_info in study_info['Series'].items():
                                        if (
                                            'Instances' in series_info
                                            and sop_instance_uid in series_info['Instances']
                                        ):
                                            instance_found = True
                                            series_uid = s_uid
                                            break
                                if instance_found:
                                    break

                    if instance_found and series_uid:
                        # Create removable attributes for the instance
                        updates = {
                            'DICOMUpdates': {
                                'removableAttributes': json.dumps(
                                    {
                                        'SchemaVersion': '1.1',
                                        'Study': {
                                            study_instance_uid: {
                                                'Series': {
                                                    series_uid: {
                                                        'Instances': {sop_instance_uid: {}}
                                                    }
                                                }
                                            }
                                        },
                                    }
                                ).encode()
                            }
                        }

                        update_response = client.update_image_set_metadata(
                            datastoreId=datastore_id,
                            imageSetId=image_set['imageSetId'],
                            latestVersionId=image_set['version'],
                            updateImageSetMetadataUpdates=updates,
                        )

                        updated_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'updated',
                                'seriesUID': series_uid,
                                'response': update_response,
                            }
                        )
                    else:
                        updated_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'not_found',
                                'message': 'Instance not found in this image set',
                            }
                        )

                except ClientError as e:
                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'studyInstanceUID': study_instance_uid,
            'sopInstanceUID': sop_instance_uid,
            'updatedImageSets': updated_image_sets,
            'totalUpdated': len([img for img in updated_image_sets if img['status'] == 'updated']),
        }

    except ClientError as e:
        logger.warning(
            f'Error deleting instance {sop_instance_uid} in study {study_instance_uid}: {e}'
        )
        raise


def delete_instance_in_series_operation(
    datastore_id: str, series_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Delete a specific instance in a series."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for image sets containing this series
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMSeriesInstanceUID': series_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        updated_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    # Get current metadata to find the instance
                    metadata_response = client.get_image_set_metadata(
                        datastoreId=datastore_id, imageSetId=image_set['imageSetId']
                    )

                    # Handle the streaming body
                    metadata_blob = metadata_response.get('imageSetMetadataBlob')
                    if hasattr(metadata_blob, 'read'):
                        content = metadata_blob.read()
                        if isinstance(content, str):
                            metadata_bytes = content.encode('utf-8')
                        else:
                            metadata_bytes = content
                    else:
                        metadata_bytes = str(metadata_blob).encode('utf-8')

                    metadata = json.loads(metadata_bytes.decode('utf-8'))

                    # Find the instance in the metadata
                    instance_found = False
                    study_uid = None

                    if 'Study' in metadata and 'DICOM' in metadata['Study']:
                        study_data = metadata['Study']['DICOM']
                        if 'StudyInstanceUID' in study_data:
                            for s_uid, study_info in study_data['StudyInstanceUID'].items():
                                if 'Series' in study_info:
                                    for ser_uid, series_info in study_info['Series'].items():
                                        if (
                                            ser_uid == series_instance_uid
                                            and 'Instances' in series_info
                                            and sop_instance_uid in series_info['Instances']
                                        ):
                                            instance_found = True
                                            study_uid = s_uid
                                            break
                                if instance_found:
                                    break

                    if instance_found and study_uid:
                        # Create removable attributes for the instance
                        updates = {
                            'DICOMUpdates': {
                                'removableAttributes': json.dumps(
                                    {
                                        'SchemaVersion': '1.1',
                                        'Study': {
                                            study_uid: {
                                                'Series': {
                                                    series_instance_uid: {
                                                        'Instances': {sop_instance_uid: {}}
                                                    }
                                                }
                                            }
                                        },
                                    }
                                ).encode()
                            }
                        }

                        update_response = client.update_image_set_metadata(
                            datastoreId=datastore_id,
                            imageSetId=image_set['imageSetId'],
                            latestVersionId=image_set['version'],
                            updateImageSetMetadataUpdates=updates,
                        )

                        updated_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'updated',
                                'studyUID': study_uid,
                                'response': update_response,
                            }
                        )
                    else:
                        updated_image_sets.append(
                            {
                                'imageSetId': image_set['imageSetId'],
                                'status': 'not_found',
                                'message': 'Instance not found in this image set',
                            }
                        )

                except ClientError as e:
                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'seriesInstanceUID': series_instance_uid,
            'sopInstanceUID': sop_instance_uid,
            'updatedImageSets': updated_image_sets,
            'totalUpdated': len([img for img in updated_image_sets if img['status'] == 'updated']),
        }

    except ClientError as e:
        logger.warning(
            f'Error deleting instance {sop_instance_uid} in series {series_instance_uid}: {e}'
        )
        raise


def update_patient_study_metadata_operation(
    datastore_id: str,
    study_instance_uid: str,
    patient_updates: Dict[str, Any],
    study_updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update Patient/Study metadata for an entire study."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this study
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': study_instance_uid}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        updated_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    # Create updatable attributes
                    dicom_updates: Dict[str, Any] = {'SchemaVersion': '1.1'}

                    if patient_updates:
                        dicom_updates['Patient'] = {'DICOM': patient_updates}  # type: ignore[assignment]

                    if study_updates:
                        dicom_updates['Study'] = {study_instance_uid: {'DICOM': study_updates}}  # type: ignore[assignment]

                    updates = {
                        'DICOMUpdates': {'updatableAttributes': json.dumps(dicom_updates).encode()}
                    }

                    update_response = client.update_image_set_metadata(
                        datastoreId=datastore_id,
                        imageSetId=image_set['imageSetId'],
                        latestVersionId=image_set['version'],
                        updateImageSetMetadataUpdates=updates,
                    )

                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'updated',
                            'response': update_response,
                        }
                    )

                except ClientError as e:
                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'studyInstanceUID': study_instance_uid,
            'patientUpdates': patient_updates,
            'studyUpdates': study_updates,
            'updatedImageSets': updated_image_sets,
            'totalUpdated': len([img for img in updated_image_sets if img['status'] == 'updated']),
        }

    except ClientError as e:
        logger.warning(f'Error updating metadata for study {study_instance_uid}: {e}')
        raise


# Wrapper functions for advanced operations
def delete_patient_studies(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Delete all studies for a specific patient."""
    return delete_patient_studies_operation(datastore_id, patient_id)


def delete_study(datastore_id: str, study_instance_uid: str) -> Dict[str, Any]:
    """Delete all image sets for a specific study."""
    return delete_study_operation(datastore_id, study_instance_uid)


def search_by_patient_id(
    datastore_id: str, patient_id: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by patient ID."""
    return search_by_patient_id_operation(datastore_id, patient_id, max_results)


def search_by_study_uid(
    datastore_id: str, study_instance_uid: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by study instance UID."""
    return search_by_study_uid_operation(datastore_id, study_instance_uid, max_results)


def search_by_series_uid(
    datastore_id: str, series_instance_uid: str, max_results: int = 50
) -> Dict[str, Any]:
    """Search for image sets by series instance UID."""
    return search_by_series_uid_operation(datastore_id, series_instance_uid, max_results)


def get_patient_studies(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Get all studies for a specific patient."""
    return get_patient_studies_operation(datastore_id, patient_id)


def get_patient_series(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Get all series for a specific patient."""
    return get_patient_series_operation(datastore_id, patient_id)


def get_study_primary_image_sets(datastore_id: str, study_instance_uid: str) -> Dict[str, Any]:
    """Get primary image sets for a specific study."""
    return get_study_primary_image_sets_operation(datastore_id, study_instance_uid)


def delete_series_by_uid(datastore_id: str, series_instance_uid: str) -> Dict[str, Any]:
    """Delete a series by SeriesInstanceUID using metadata updates."""
    return delete_series_by_uid_operation(datastore_id, series_instance_uid)


def get_series_primary_image_set(datastore_id: str, series_instance_uid: str) -> Dict[str, Any]:
    """Get the primary image set for a given series."""
    return get_series_primary_image_set_operation(datastore_id, series_instance_uid)


def get_patient_dicomweb_studies(datastore_id: str, patient_id: str) -> Dict[str, Any]:
    """Retrieve DICOMweb SearchStudies level information for a given patient ID."""
    return get_patient_dicomweb_studies_operation(datastore_id, patient_id)


def delete_instance_in_study(
    datastore_id: str, study_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Delete a specific instance in a study."""
    return delete_instance_in_study_operation(datastore_id, study_instance_uid, sop_instance_uid)


def delete_instance_in_series(
    datastore_id: str, series_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Delete a specific instance in a series."""
    return delete_instance_in_series_operation(datastore_id, series_instance_uid, sop_instance_uid)


def update_patient_study_metadata(
    datastore_id: str,
    study_instance_uid: str,
    patient_updates: Dict[str, Any],
    study_updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update Patient/Study metadata for an entire study."""
    return update_patient_study_metadata_operation(
        datastore_id, study_instance_uid, patient_updates, study_updates
    )


# Bulk Operations - Major Value Add


def bulk_update_patient_metadata_operation(
    datastore_id: str, patient_id: str, metadata_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update patient metadata across all studies for a patient."""
    import json

    try:
        client = get_medical_imaging_client()

        # Search for all image sets for this patient
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': patient_id}], 'operator': 'EQUAL'}]
            },
            maxResults=MAX_SEARCH_COUNT,
        )

        updated_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    # Create updatable attributes for patient metadata
                    dicom_updates = {
                        'SchemaVersion': '1.1',
                        'Patient': {'DICOM': metadata_updates},
                    }

                    updates = {
                        'DICOMUpdates': {'updatableAttributes': json.dumps(dicom_updates).encode()}
                    }

                    update_response = client.update_image_set_metadata(
                        datastoreId=datastore_id,
                        imageSetId=image_set['imageSetId'],
                        latestVersionId=image_set['version'],
                        updateImageSetMetadataUpdates=updates,
                    )

                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'updated',
                            'response': update_response,
                        }
                    )
                except ClientError as e:
                    updated_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'patientId': patient_id,
            'metadataUpdates': metadata_updates,
            'updatedImageSets': updated_image_sets,
            'totalUpdated': len([img for img in updated_image_sets if img['status'] == 'updated']),
        }

    except ClientError as e:
        logger.warning(f'Error bulk updating patient metadata for {patient_id}: {e}')
        raise


def bulk_delete_by_criteria_operation(
    datastore_id: str, criteria: Dict[str, Any], max_deletions: int = 100
) -> Dict[str, Any]:
    """Delete multiple image sets matching specified criteria."""
    try:
        client = get_medical_imaging_client()

        # Build search criteria from the provided criteria
        search_filters = []
        for key, value in criteria.items():
            if key in [
                'DICOMPatientId',
                'DICOMStudyInstanceUID',
                'DICOMSeriesInstanceUID',
                'DICOMModality',
            ]:
                search_filters.append({'values': [{key: value}], 'operator': 'EQUAL'})

        if not search_filters:
            raise ValueError('No valid search criteria provided')

        # Search for image sets matching criteria
        search_response = client.search_image_sets(
            datastoreId=datastore_id,
            searchCriteria={'filters': search_filters},
            maxResults=min(max_deletions, MAX_SEARCH_COUNT),
        )

        deleted_image_sets = []

        if 'imageSetsMetadataSummaries' in search_response:
            for image_set in search_response['imageSetsMetadataSummaries']:
                try:
                    delete_response = client.delete_image_set(
                        datastoreId=datastore_id, imageSetId=image_set['imageSetId']
                    )
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'deleted',
                            'response': delete_response,
                        }
                    )
                except ClientError as e:
                    deleted_image_sets.append(
                        {
                            'imageSetId': image_set['imageSetId'],
                            'status': 'error',
                            'error': str(e),
                        }
                    )

        return {
            'criteria': criteria,
            'maxDeletions': max_deletions,
            'deletedImageSets': deleted_image_sets,
            'totalDeleted': len([img for img in deleted_image_sets if img['status'] == 'deleted']),
            'totalFound': len(search_response.get('imageSetsMetadataSummaries', [])),
        }

    except ClientError as e:
        logger.warning(f'Error bulk deleting by criteria {criteria}: {e}')
        raise


# DICOM Hierarchy Operations - Domain Expertise


def remove_series_from_image_set_operation(
    datastore_id: str, image_set_id: str, series_instance_uid: str
) -> Dict[str, Any]:
    """Remove a specific series from an image set using DICOM hierarchy operations."""
    import json

    try:
        client = get_medical_imaging_client()

        # Get current image set information
        image_set_response = client.get_image_set(
            datastoreId=datastore_id, imageSetId=image_set_id
        )

        # Create removable attributes for the series
        updates = {
            'DICOMUpdates': {
                'removableAttributes': json.dumps(
                    {'SchemaVersion': '1.1', 'Series': {series_instance_uid: {}}}
                ).encode()
            }
        }

        update_response = client.update_image_set_metadata(
            datastoreId=datastore_id,
            imageSetId=image_set_id,
            latestVersionId=image_set_response['versionId'],
            updateImageSetMetadataUpdates=updates,
        )

        return {
            'imageSetId': image_set_id,
            'seriesInstanceUID': series_instance_uid,
            'status': 'removed',
            'response': update_response,
        }

    except ClientError as e:
        logger.warning(
            f'Error removing series {series_instance_uid} from image set {image_set_id}: {e}'
        )
        raise


def remove_instance_from_image_set_operation(
    datastore_id: str, image_set_id: str, series_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Remove a specific instance from an image set using DICOM hierarchy operations."""
    import json

    try:
        client = get_medical_imaging_client()

        # Get current image set information
        image_set_response = client.get_image_set(
            datastoreId=datastore_id, imageSetId=image_set_id
        )

        # Get current metadata to find the study UID
        metadata_response = client.get_image_set_metadata(
            datastoreId=datastore_id, imageSetId=image_set_id
        )

        # Handle the streaming body
        metadata_blob = metadata_response.get('imageSetMetadataBlob')
        if hasattr(metadata_blob, 'read'):
            content = metadata_blob.read()
            if isinstance(content, str):
                metadata_bytes = content.encode('utf-8')
            else:
                metadata_bytes = content
        else:
            metadata_bytes = str(metadata_blob).encode('utf-8')

        metadata = json.loads(metadata_bytes.decode('utf-8'))

        # Find the study UID for this series
        study_uid = None
        if 'Study' in metadata and 'DICOM' in metadata['Study']:
            study_data = metadata['Study']['DICOM']
            if 'StudyInstanceUID' in study_data:
                for s_uid, study_info in study_data['StudyInstanceUID'].items():
                    if 'Series' in study_info and series_instance_uid in study_info['Series']:
                        study_uid = s_uid
                        break

        if not study_uid:
            raise ValueError(f'Could not find study UID for series {series_instance_uid}')

        # Create removable attributes for the instance
        updates = {
            'DICOMUpdates': {
                'removableAttributes': json.dumps(
                    {
                        'SchemaVersion': '1.1',
                        'Study': {
                            study_uid: {
                                'Series': {
                                    series_instance_uid: {'Instances': {sop_instance_uid: {}}}
                                }
                            }
                        },
                    }
                ).encode()
            }
        }

        update_response = client.update_image_set_metadata(
            datastoreId=datastore_id,
            imageSetId=image_set_id,
            latestVersionId=image_set_response['versionId'],
            updateImageSetMetadataUpdates=updates,
        )

        return {
            'imageSetId': image_set_id,
            'studyInstanceUID': study_uid,
            'seriesInstanceUID': series_instance_uid,
            'sopInstanceUID': sop_instance_uid,
            'status': 'removed',
            'response': update_response,
        }

    except ClientError as e:
        logger.warning(
            f'Error removing instance {sop_instance_uid} from image set {image_set_id}: {e}'
        )
        raise


# Wrapper functions for bulk operations
def bulk_update_patient_metadata(
    datastore_id: str, patient_id: str, metadata_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update patient metadata across all studies for a patient."""
    return bulk_update_patient_metadata_operation(datastore_id, patient_id, metadata_updates)


def bulk_delete_by_criteria(
    datastore_id: str, criteria: Dict[str, Any], max_deletions: int = 100
) -> Dict[str, Any]:
    """Delete multiple image sets matching specified criteria."""
    return bulk_delete_by_criteria_operation(datastore_id, criteria, max_deletions)


# Wrapper functions for DICOM hierarchy operations
def remove_series_from_image_set(
    datastore_id: str, image_set_id: str, series_instance_uid: str
) -> Dict[str, Any]:
    """Remove a specific series from an image set using DICOM hierarchy operations."""
    return remove_series_from_image_set_operation(datastore_id, image_set_id, series_instance_uid)


def remove_instance_from_image_set(
    datastore_id: str, image_set_id: str, series_instance_uid: str, sop_instance_uid: str
) -> Dict[str, Any]:
    """Remove a specific instance from an image set using DICOM hierarchy operations."""
    return remove_instance_from_image_set_operation(
        datastore_id, image_set_id, series_instance_uid, sop_instance_uid
    )
