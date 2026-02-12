"""Tests for HealthImaging operations functions."""

import json
import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import (
    bulk_delete_by_criteria_operation,
    # Bulk operations
    bulk_update_patient_metadata_operation,
    create_datastore_operation,
    delete_instance_in_series_operation,
    delete_instance_in_study_operation,
    # Advanced DICOM operations
    delete_patient_studies_operation,
    # New advanced DICOM operations
    delete_series_by_uid_operation,
    delete_study_operation,
    get_dicom_export_job_operation,
    get_image_frame_operation,
    get_image_set_metadata_operation,
    get_image_set_operation,
    get_patient_dicomweb_studies_operation,
    get_patient_series_operation,
    get_patient_studies_operation,
    get_series_primary_image_set_operation,
    get_study_primary_image_sets_operation,
    list_datastores_operation,
    list_dicom_export_jobs_operation,
    list_dicom_import_jobs_operation,
    list_image_set_versions_operation,
    remove_instance_from_image_set_operation,
    # DICOM hierarchy operations
    remove_series_from_image_set_operation,
    search_by_patient_id_operation,
    search_by_series_uid_operation,
    search_by_study_uid_operation,
    search_image_sets_operation,
    start_dicom_export_job_operation,
    start_dicom_import_job_operation,
    tag_resource_operation,
    untag_resource_operation,
    update_patient_study_metadata_operation,
)
from awslabs.healthimaging_mcp_server.models import (
    CreateDatastoreRequest,
    DatastoreStatus,
    GetDICOMExportJobRequest,
    GetImageFrameRequest,
    GetImageSetMetadataRequest,
    GetImageSetRequest,
    JobStatus,
    ListDatastoresRequest,
    ListDICOMExportJobsRequest,
    ListDICOMImportJobsRequest,
    ListImageSetVersionsRequest,
    SearchImageSetsRequest,
    StartDICOMExportJobRequest,
    StartDICOMExportJobResponse,
    StartDICOMImportJobRequest,
    TagResourceRequest,
    UntagResourceRequest,
)
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import Mock, patch


class TestDatastoreOperations:
    """Test datastore operations with conditional branches."""

    @patch('boto3.client')
    def test_create_datastore_with_all_optional_params(self, mock_boto_client):
        """Test create_datastore_operation with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.create_datastore.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'datastoreStatus': 'CREATING',
        }

        request = CreateDatastoreRequest(
            datastore_name='test-datastore',
            tags={'Environment': 'test', 'Project': 'healthimaging'},
            kms_key_arn='arn:aws:kms:us-east-1:000000000000:key/test-key-1234-5678-9abc-def012345678',
        )

        response = create_datastore_operation(request)

        # Verify all optional parameters were passed
        mock_client.create_datastore.assert_called_once_with(
            datastoreName='test-datastore',
            tags={'Environment': 'test', 'Project': 'healthimaging'},
            kmsKeyArn='arn:aws:kms:us-east-1:000000000000:key/test-key-1234-5678-9abc-def012345678',
        )
        assert response.datastore_id == '00000000000034567890000000000000'

    @patch('boto3.client')
    def test_create_datastore_without_optional_params(self, mock_boto_client):
        """Test create_datastore_operation without optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.create_datastore.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'datastoreStatus': 'CREATING',
        }

        request = CreateDatastoreRequest(datastore_name='test-datastore')

        response = create_datastore_operation(request)

        # Verify only required parameter was passed
        mock_client.create_datastore.assert_called_once_with(datastoreName='test-datastore')
        assert response.datastore_id == '00000000000034567890000000000000'

    @patch('boto3.client')
    def test_list_datastores_with_all_optional_params(self, mock_boto_client):
        """Test list_datastores_operation with all optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.list_datastores.return_value = {
            'datastoreSummaries': [
                {
                    'datastoreId': '00000000000034567890000000000000',
                    'datastoreName': 'test-datastore',
                    'datastoreStatus': 'ACTIVE',
                    'datastoreArn': 'arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'test_token_123',
        }

        request = ListDatastoresRequest(
            datastore_status=DatastoreStatus.ACTIVE, next_token='prev_token', max_results=50
        )

        response = list_datastores_operation(request)

        # Verify all optional parameters were passed
        mock_client.list_datastores.assert_called_once_with(
            datastoreStatus=DatastoreStatus.ACTIVE, nextToken='prev_token', maxResults=50
        )
        assert len(response.datastore_summaries) == 1
        assert response.next_token == 'test_token_123'

    @patch('boto3.client')
    def test_list_datastores_without_optional_params(self, mock_boto_client):
        """Test list_datastores_operation without optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.list_datastores.return_value = {'datastoreSummaries': []}

        request = ListDatastoresRequest()

        response = list_datastores_operation(request)

        # Verify no optional parameters were passed
        mock_client.list_datastores.assert_called_once_with()
        assert len(response.datastore_summaries) == 0


class TestDICOMJobOperations:
    """Test DICOM job operations with conditional branches."""

    @patch('boto3.client')
    def test_start_dicom_import_job_with_optional_params(self, mock_boto_client):
        """Test start_dicom_import_job_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.start_dicom_import_job.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'jobId': 'job123',
            'jobStatus': 'SUBMITTED',
        }

        request = StartDICOMImportJobRequest(
            job_name='test-import-job',
            datastore_id='00000000000034567890000000000000',
            data_access_role_arn='arn:aws:iam::000000000000:role/Role',
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            client_token='test_client_123',
        )

        start_dicom_import_job_operation(request)

        # Verify optional parameter was passed
        expected_kwargs = {
            'jobName': 'test-import-job',
            'datastoreId': '00000000000034567890000000000000',
            'dataAccessRoleArn': 'arn:aws:iam::000000000000:role/Role',
            'inputS3Uri': 's3://bucket/input/',
            'outputS3Uri': 's3://bucket/output/',
            'clientToken': 'test_client_123',
        }
        mock_client.start_dicom_import_job.assert_called_once_with(**expected_kwargs)

    @patch('boto3.client')
    def test_start_dicom_export_job_with_optional_params(self, mock_boto_client):
        """Test start_dicom_export_job_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.start_dicom_export_job.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'jobId': 'export-job-123',
            'jobStatus': 'SUBMITTED',
            'submittedAt': datetime.now(),
        }

        request = StartDICOMExportJobRequest(
            job_name='test-export-job',
            datastore_id='00000000000034567890000000000000',
            data_access_role_arn='arn:aws:iam::000000000000:role/Role',
            output_s3_uri='s3://bucket/output/',
            client_token='client456',
            study_instance_uid='1.2.3.4.5.6.7.8.9',
            series_instance_uid='1.2.3.4.5.6.7.8.9.10',
            sop_instance_uid='1.2.3.4.5.6.7.8.9.10.11',
            submitted_before='2023-01-01T00:00:00Z',
            submitted_after='2022-01-01T00:00:00Z',
        )

        result = start_dicom_export_job_operation(request)

        assert isinstance(result, StartDICOMExportJobResponse)
        assert result.datastore_id == '00000000000034567890000000000000'
        assert result.job_id == 'export-job-123'
        assert result.job_status == 'SUBMITTED'

        expected_kwargs = {
            'datastoreId': '00000000000034567890000000000000',
            'dataAccessRoleArn': 'arn:aws:iam::000000000000:role/Role',
            'outputS3Uri': 's3://bucket/output/',
            'jobName': 'test-export-job',
            'clientToken': 'client456',
            'studyInstanceUID': '1.2.3.4.5.6.7.8.9',
            'seriesInstanceUID': '1.2.3.4.5.6.7.8.9.10',
            'sopInstanceUID': '1.2.3.4.5.6.7.8.9.10.11',
            'submittedBefore': '2023-01-01T00:00:00Z',
            'submittedAfter': '2022-01-01T00:00:00Z',
        }
        mock_client.start_dicom_export_job.assert_called_once_with(**expected_kwargs)

    @patch('boto3.client')
    def test_list_dicom_import_jobs_with_optional_params(self, mock_boto_client):
        """Test list_dicom_import_jobs_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.list_dicom_import_jobs.return_value = {
            'jobSummaries': [
                {
                    'jobId': 'job123',
                    'jobName': 'import-job',
                    'jobStatus': 'COMPLETED',
                    'datastoreId': '00000000000034567890000000000000',
                    'submittedAt': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'test_import_token_123',
        }

        request = ListDICOMImportJobsRequest(
            datastore_id='00000000000034567890000000000000',
            job_status=JobStatus.COMPLETED,
            next_token='prev_token',
            max_results=25,
        )

        response = list_dicom_import_jobs_operation(request)

        # Verify all optional parameters were passed
        mock_client.list_dicom_import_jobs.assert_called_once_with(
            datastoreId='00000000000034567890000000000000',
            jobStatus=JobStatus.COMPLETED,
            nextToken='prev_token',
            maxResults=25,
        )
        assert len(response.job_summaries) == 1

    @patch('boto3.client')
    def test_list_dicom_export_jobs_with_optional_params(self, mock_boto_client):
        """Test list_dicom_export_jobs_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.list_dicom_export_jobs.return_value = {
            'jobSummaries': [
                {
                    'jobId': 'export-job-123',
                    'jobName': 'export-job',
                    'jobStatus': 'COMPLETED',
                    'datastoreId': '00000000000034567890000000000000',
                    'submittedAt': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'test_export_token_123',
        }

        request = ListDICOMExportJobsRequest(
            datastore_id='00000000000034567890000000000000',
            job_status=JobStatus.FAILED,
            next_token='prev_token',
            max_results=25,
        )

        response = list_dicom_export_jobs_operation(request)

        # Verify all optional parameters were passed
        mock_client.list_dicom_export_jobs.assert_called_once_with(
            datastoreId='00000000000034567890000000000000',
            jobStatus=JobStatus.FAILED,
            nextToken='prev_token',
            maxResults=25,
        )
        assert len(response.job_summaries) == 1
        assert response.next_token == 'test_export_token_123'

    @patch('boto3.client')
    def test_get_dicom_export_job_operation(self, mock_boto_client):
        """Test get_dicom_export_job_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.get_dicom_export_job.return_value = {
            'jobProperties': {
                'jobId': 'export-job-123',
                'jobName': 'export-job',
                'jobStatus': 'COMPLETED',
                'datastoreId': '00000000000034567890000000000000',
                'dataAccessRoleArn': 'arn:aws:iam::000000000000:role/Role',
                'outputS3Uri': 's3://bucket/output/',
                'submittedAt': '2023-01-01T00:00:00Z',
            }
        }

        request = GetDICOMExportJobRequest(
            datastore_id='00000000000034567890000000000000', job_id='export-job-123'
        )

        response = get_dicom_export_job_operation(request)

        mock_client.get_dicom_export_job.assert_called_once_with(
            datastoreId='00000000000034567890000000000000', jobId='export-job-123'
        )
        assert response.job_properties.job_id == 'export-job-123'
        assert response.job_properties.datastore_id == '00000000000034567890000000000000'


class TestImageSetOperations:
    """Test image set operations with conditional branches."""

    @patch('boto3.client')
    def test_search_image_sets_with_optional_params(self, mock_boto_client):
        """Test search_image_sets_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {'PatientID': '12345'},
                }
            ],
            'nextToken': 'search_token',
        }

        request = SearchImageSetsRequest(
            datastore_id='00000000000034567890000000000000',
            search_criteria={
                'filters': [{'values': [{'DICOMPatientId': '12345'}], 'operator': 'EQUAL'}]
            },
            max_results=50,
            next_token='prev_token',
        )

        response = search_image_sets_operation(request)

        # Verify all optional parameters were passed
        mock_client.search_image_sets.assert_called_once_with(
            datastoreId='00000000000034567890000000000000',
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': '12345'}], 'operator': 'EQUAL'}]
            },
            maxResults=50,
            nextToken='prev_token',
        )
        assert len(response.image_sets_metadata_summaries) == 1

    @patch('boto3.client')
    def test_get_image_set_with_optional_params(self, mock_boto_client):
        """Test get_image_set_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.get_image_set.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'imageSetId': 'img123',
            'versionId': '2',
            'imageSetState': 'ACTIVE',
            'imageSetWorkflowStatus': 'UPDATED',
            'createdAt': '2023-01-01T00:00:00Z',
            'updatedAt': '2023-01-01T01:00:00Z',
        }

        request = GetImageSetRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123', version_id='2'
        )

        response = get_image_set_operation(request)

        # Verify optional parameter was passed
        mock_client.get_image_set.assert_called_once_with(
            datastoreId='00000000000034567890000000000000', imageSetId='img123', versionId='2'
        )
        assert response.version_id == '2'

    @patch('boto3.client')
    def test_get_image_set_metadata_with_optional_params(self, mock_boto_client):
        """Test get_image_set_metadata_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': b'metadata_content',
            'contentType': 'application/json',
            'contentEncoding': 'gzip',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123', version_id='2'
        )

        response = get_image_set_metadata_operation(request)

        # Verify optional parameter was passed
        mock_client.get_image_set_metadata.assert_called_once_with(
            datastoreId='00000000000034567890000000000000', imageSetId='img123', versionId='2'
        )
        assert response.content_encoding == 'gzip'

    @patch('boto3.client')
    def test_list_image_set_versions_with_optional_params(self, mock_boto_client):
        """Test list_image_set_versions_operation with optional parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.list_image_set_versions.return_value = {
            'datastoreId': '00000000000034567890000000000000',
            'imageSetId': 'img123',
            'imageSetPropertiesList': [
                {
                    'imageSetId': 'img123',
                    'versionId': '1',
                    'imageSetState': 'ACTIVE',
                    'imageSetWorkflowStatus': 'CREATED',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'versions_token',
        }

        request = ListImageSetVersionsRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            next_token='prev_token',
            max_results=25,
        )

        response = list_image_set_versions_operation(request)

        # Verify all optional parameters were passed
        mock_client.list_image_set_versions.assert_called_once_with(
            datastoreId='00000000000034567890000000000000',
            imageSetId='img123',
            nextToken='prev_token',
            maxResults=25,
        )
        assert response.next_token == 'versions_token'


class TestTaggingOperations:
    """Test tagging operations with conditional branches."""

    @patch('boto3.client')
    def test_tag_resource_operation(self, mock_boto_client):
        """Test tag_resource_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.tag_resource.return_value = {}

        request = TagResourceRequest(
            resource_arn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
            tags={'Environment': 'test', 'Project': 'healthimaging'},
        )

        response = tag_resource_operation(request)

        mock_client.tag_resource.assert_called_once_with(
            resourceArn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
            tags={'Environment': 'test', 'Project': 'healthimaging'},
        )
        assert response is not None

    @patch('boto3.client')
    def test_untag_resource_operation(self, mock_boto_client):
        """Test untag_resource_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.untag_resource.return_value = {}

        request = UntagResourceRequest(
            resource_arn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
            tag_keys=['Environment', 'Project'],
        )

        response = untag_resource_operation(request)

        mock_client.untag_resource.assert_called_once_with(
            resourceArn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
            tagKeys=['Environment', 'Project'],
        )
        assert response is not None


class TestAdvancedDICOMOperations:
    """Test advanced DICOM operations with complex business logic."""

    @patch('boto3.client')
    def test_delete_patient_studies_operation(self, mock_boto_client):
        """Test delete_patient_studies_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMPatientId': 'patient123'},
                },
                {
                    'imageSetId': 'img456',
                    'version': '1',
                    'DICOMTags': {'DICOMPatientId': 'patient123'},
                },
            ]
        }

        # Mock delete responses
        mock_client.delete_image_set.side_effect = [
            {'datastoreId': 'ds123', 'imageSetId': 'img123', 'imageSetState': 'DELETED'},
            {'datastoreId': 'ds123', 'imageSetId': 'img456', 'imageSetState': 'DELETED'},
        ]

        result = delete_patient_studies_operation('ds123', 'patient123')

        assert result['patientId'] == 'patient123'
        assert result['totalDeleted'] == 2
        assert len(result['deletedImageSets']) == 2
        assert all(img['status'] == 'deleted' for img in result['deletedImageSets'])

    @patch('boto3.client')
    def test_delete_study_operation(self, mock_boto_client):
        """Test delete_study_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                }
            ]
        }

        # Mock delete response
        mock_client.delete_image_set.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img123',
            'imageSetState': 'DELETED',
        }

        result = delete_study_operation('ds123', 'study123')

        assert result['studyInstanceUID'] == 'study123'
        assert result['totalDeleted'] == 1
        assert len(result['deletedImageSets']) == 1

    @patch('boto3.client')
    def test_search_by_patient_id_operation(self, mock_boto_client):
        """Test search_by_patient_id_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMPatientId': 'patient123'},
                }
            ]
        }

        result = search_by_patient_id_operation('ds123', 'patient123', 50)

        mock_client.search_image_sets.assert_called_once_with(
            datastoreId='ds123',
            searchCriteria={
                'filters': [{'values': [{'DICOMPatientId': 'patient123'}], 'operator': 'EQUAL'}]
            },
            maxResults=50,
        )
        assert 'imageSetsMetadataSummaries' in result

    @patch('boto3.client')
    def test_search_by_study_uid_operation(self, mock_boto_client):
        """Test search_by_study_uid_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                }
            ]
        }

        result = search_by_study_uid_operation('ds123', 'study123', 50)

        mock_client.search_image_sets.assert_called_once_with(
            datastoreId='ds123',
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMStudyInstanceUID': 'study123'}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=50,
        )
        assert 'imageSetsMetadataSummaries' in result

    @patch('boto3.client')
    def test_search_by_series_uid_operation(self, mock_boto_client):
        """Test search_by_series_uid_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                }
            ]
        }

        result = search_by_series_uid_operation('ds123', 'series123', 50)

        mock_client.search_image_sets.assert_called_once_with(
            datastoreId='ds123',
            searchCriteria={
                'filters': [
                    {
                        'values': [{'DICOMSeriesInstanceUID': 'series123'}],
                        'operator': 'EQUAL',
                    }
                ]
            },
            maxResults=50,
        )
        assert 'imageSetsMetadataSummaries' in result

    @patch('boto3.client')
    def test_get_patient_studies_operation(self, mock_boto_client):
        """Test get_patient_studies_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {
                        'DICOMPatientId': 'patient123',
                        'DICOMStudyInstanceUID': 'study123',
                        'DICOMStudyDescription': 'Test Study',
                        'DICOMStudyDate': '20230101',
                    },
                }
            ]
        }

        result = get_patient_studies_operation('ds123', 'patient123')

        assert result['patientId'] == 'patient123'
        assert result['totalStudies'] == 1
        assert len(result['studies']) == 1
        assert result['studies'][0]['studyInstanceUID'] == 'study123'
        assert result['studies'][0]['studyDescription'] == 'Test Study'

    @patch('boto3.client')
    def test_get_patient_series_operation(self, mock_boto_client):
        """Test get_patient_series_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {
                        'DICOMPatientId': 'patient123',
                        'DICOMSeriesInstanceUID': 'series123',
                        'DICOMSeriesDescription': 'Test Series',
                        'DICOMModality': 'CT',
                        'DICOMStudyInstanceUID': 'study123',
                    },
                }
            ]
        }

        result = get_patient_series_operation('ds123', 'patient123')

        assert result['patientId'] == 'patient123'
        assert result['totalSeries'] == 1
        assert len(result['series']) == 1
        assert result['series'][0]['seriesInstanceUID'] == 'series123'
        assert result['series'][0]['modality'] == 'CT'

    @patch('boto3.client')
    def test_get_study_primary_image_sets_operation(self, mock_boto_client):
        """Test get_study_primary_image_sets_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',  # Primary version
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                },
                {
                    'imageSetId': 'img456',
                    'version': '2',  # Not primary
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                },
            ]
        }

        result = get_study_primary_image_sets_operation('ds123', 'study123')

        assert result['studyInstanceUID'] == 'study123'
        assert result['totalPrimaryImageSets'] == 1
        assert len(result['primaryImageSets']) == 1
        assert result['primaryImageSets'][0]['imageSetId'] == 'img123'
        assert result['primaryImageSets'][0]['version'] == '1'


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases to improve coverage."""

    @patch('boto3.client')
    def test_get_image_set_metadata_streaming_body_error(self, mock_boto_client):
        """Test get_image_set_metadata_operation with streaming body error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a streaming body that raises an exception when read
        mock_streaming_body = Mock()
        mock_streaming_body.read.side_effect = Exception('Stream read error')

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body,
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should return empty base64 string on error
        import base64

        expected_empty = base64.b64encode(b'').decode('utf-8')
        assert response.image_set_metadata_blob == expected_empty

    @patch('boto3.client')
    def test_get_image_set_metadata_string_content(self, mock_boto_client):
        """Test get_image_set_metadata_operation with string content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a streaming body that returns string content
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = '{"test": "data"}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body,
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should handle string content correctly
        import base64

        expected_base64 = base64.b64encode('{"test": "data"}'.encode('utf-8')).decode('utf-8')
        assert response.image_set_metadata_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_set_metadata_none_blob(self, mock_boto_client):
        """Test get_image_set_metadata_operation with None blob."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': None,
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should return empty base64 string for None
        import base64

        expected_empty = base64.b64encode(b'').decode('utf-8')
        assert response.image_set_metadata_blob == expected_empty

    @patch('boto3.client')
    def test_get_image_frame_streaming_body_error(self, mock_boto_client):
        """Test get_image_frame_operation with streaming body error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a streaming body that raises an exception when read
        mock_streaming_body = Mock()
        mock_streaming_body.read.side_effect = Exception('Stream read error')

        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': mock_streaming_body,
            'contentType': 'image/jpeg',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should return empty base64 string on error
        import base64

        expected_empty = base64.b64encode(b'').decode('utf-8')
        assert response.image_frame_blob == expected_empty

    @patch('boto3.client')
    def test_delete_patient_studies_with_delete_error(self, mock_boto_client):
        """Test delete_patient_studies_operation with delete error."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMPatientId': 'patient123'},
                }
            ]
        }

        # Mock delete to raise ClientError
        mock_client.delete_image_set.side_effect = ClientError(
            error_response={'Error': {'Code': 'ConflictException', 'Message': 'Cannot delete'}},
            operation_name='DeleteImageSet',
        )

        result = delete_patient_studies_operation('ds123', 'patient123')

        assert result['patientId'] == 'patient123'
        assert result['totalDeleted'] == 0
        assert len(result['deletedImageSets']) == 1
        assert result['deletedImageSets'][0]['status'] == 'error'
        assert 'Cannot delete' in result['deletedImageSets'][0]['error']

    @patch('boto3.client')
    def test_advanced_operations_client_errors(self, mock_boto_client):
        """Test advanced operations with ClientError exceptions."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test search_by_patient_id_operation with ClientError
        mock_client.search_image_sets.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid patient ID'}
            },
            operation_name='SearchImageSets',
        )

        with pytest.raises(ClientError):
            search_by_patient_id_operation('ds123', 'invalid_patient', 50)

        # Test get_patient_studies_operation with ClientError
        with pytest.raises(ClientError):
            get_patient_studies_operation('ds123', 'invalid_patient')

        # Test delete_patient_studies_operation with search error
        with pytest.raises(ClientError):
            delete_patient_studies_operation('ds123', 'invalid_patient')

    # Tests for the 6 new advanced DICOM operations

    @patch('boto3.client')
    def test_delete_series_by_uid_operation(self, mock_boto_client):
        """Test delete_series_by_uid_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                }
            ]
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'imageSetId': 'img123',
            'latestVersionId': '2',
            'imageSetState': 'ACTIVE',
        }

        result = delete_series_by_uid_operation('ds123', 'series123')

        assert result['seriesInstanceUID'] == 'series123'
        assert result['totalUpdated'] == 1
        assert len(result['updatedImageSets']) == 1
        assert result['updatedImageSets'][0]['status'] == 'updated'

    @patch('boto3.client')
    def test_get_series_primary_image_set_operation(self, mock_boto_client):
        """Test get_series_primary_image_set_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response with primary image set
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'createdAt': '2023-01-01T00:00:00Z',
                    'updatedAt': '2023-01-01T00:00:00Z',
                    'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                }
            ]
        }

        result = get_series_primary_image_set_operation('ds123', 'series123')

        assert result['seriesInstanceUID'] == 'series123'
        assert result['found'] is True
        assert result['primaryImageSet']['imageSetId'] == 'img123'
        assert result['primaryImageSet']['version'] == '1'

    @patch('boto3.client')
    def test_get_patient_dicomweb_studies_operation(self, mock_boto_client):
        """Test get_patient_dicomweb_studies_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {
                        'DICOMPatientId': 'patient123',
                        'DICOMStudyInstanceUID': 'study123',
                    },
                }
            ]
        }

        # Mock metadata response
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'{"Patient": {"DICOM": {"PatientName": "Test"}}, "Study": {"DICOM": {"StudyInstanceUID": {"study123": {"DICOM": {"StudyDescription": "Test Study"}}}}}}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body
        }

        result = get_patient_dicomweb_studies_operation('ds123', 'patient123')

        assert result['patientId'] == 'patient123'
        assert result['totalStudies'] == 1
        assert len(result['studies']) == 1
        assert result['studies'][0]['studyInstanceUID'] == 'study123'

    @patch('boto3.client')
    def test_delete_instance_in_study_operation(self, mock_boto_client):
        """Test delete_instance_in_study_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                }
            ]
        }

        # Mock metadata response with instance
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {"study123": {"Series": {"series123": {"Instances": {"instance123": {}}}}}}}}}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'imageSetId': 'img123',
            'latestVersionId': '2',
        }

        result = delete_instance_in_study_operation('ds123', 'study123', 'instance123')

        assert result['studyInstanceUID'] == 'study123'
        assert result['sopInstanceUID'] == 'instance123'
        assert result['totalUpdated'] == 1

    @patch('boto3.client')
    def test_delete_instance_in_series_operation(self, mock_boto_client):
        """Test delete_instance_in_series_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                }
            ]
        }

        # Mock metadata response with instance
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {"study123": {"Series": {"series123": {"Instances": {"instance123": {}}}}}}}}}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'imageSetId': 'img123',
            'latestVersionId': '2',
        }

        result = delete_instance_in_series_operation('ds123', 'series123', 'instance123')

        assert result['seriesInstanceUID'] == 'series123'
        assert result['sopInstanceUID'] == 'instance123'
        assert result['totalUpdated'] == 1

    @patch('boto3.client')
    def test_update_patient_study_metadata_operation(self, mock_boto_client):
        """Test update_patient_study_metadata_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                }
            ]
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'imageSetId': 'img123',
            'latestVersionId': '2',
        }

        patient_updates = {'PatientName': 'Updated Name'}
        study_updates = {'StudyDescription': 'Updated Description'}

        result = update_patient_study_metadata_operation(
            'ds123', 'study123', patient_updates, study_updates
        )

        assert result['studyInstanceUID'] == 'study123'
        assert result['patientUpdates'] == patient_updates
        assert result['studyUpdates'] == study_updates
        assert result['totalUpdated'] == 1

    @patch('boto3.client')
    def test_new_operations_with_errors(self, mock_boto_client):
        """Test new operations with various error conditions."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Test delete_series_by_uid with update error
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img123', 'version': '1'}]
        }

        mock_client.update_image_set_metadata.side_effect = ClientError(
            error_response={'Error': {'Code': 'ConflictException', 'Message': 'Update failed'}},
            operation_name='UpdateImageSetMetadata',
        )

        result = delete_series_by_uid_operation('ds123', 'series123')

        assert result['totalUpdated'] == 0
        assert result['updatedImageSets'][0]['status'] == 'error'
        assert 'Update failed' in result['updatedImageSets'][0]['error']

    @patch('boto3.client')
    def test_get_series_primary_image_set_not_found(self, mock_boto_client):
        """Test get_series_primary_image_set_operation when no primary image set found."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response with no primary image sets (version != '1')
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '2',  # Not primary
                    'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                }
            ]
        }

        result = get_series_primary_image_set_operation('ds123', 'series123')

        assert result['seriesInstanceUID'] == 'series123'
        assert result['found'] is False
        assert result['primaryImageSet'] is None

    @patch('boto3.client')
    def test_delete_instance_not_found(self, mock_boto_client):
        """Test delete instance operations when instance not found."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img123',
                    'version': '1',
                    'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                }
            ]
        }

        # Mock metadata response without the target instance
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {"study123": {"Series": {"series123": {"Instances": {"other_instance": {}}}}}}}}}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body
        }

        result = delete_instance_in_study_operation('ds123', 'study123', 'missing_instance')

        assert result['totalUpdated'] == 0
        assert result['updatedImageSets'][0]['status'] == 'not_found'
        assert 'Instance not found' in result['updatedImageSets'][0]['message']

    @patch('boto3.client')
    def test_get_image_set_metadata_bytes_content(self, mock_boto_client):
        """Test get_image_set_metadata_operation with bytes content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock response with bytes content directly
        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': b'{"test": "data"}',
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should handle bytes content correctly
        import base64

        expected_base64 = base64.b64encode(b'{"test": "data"}').decode('utf-8')
        assert response.image_set_metadata_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_set_metadata_other_content(self, mock_boto_client):
        """Test get_image_set_metadata_operation with other content type."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock response with integer content (other type)
        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': 12345,
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should handle other content types by converting to string then bytes
        import base64

        expected_base64 = base64.b64encode('12345'.encode('utf-8')).decode('utf-8')
        assert response.image_set_metadata_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_frame_bytes_content(self, mock_boto_client):
        """Test get_image_frame_operation with bytes content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock response with bytes content directly
        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': b'image_data',
            'contentType': 'image/jpeg',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should handle bytes content correctly
        import base64

        expected_base64 = base64.b64encode(b'image_data').decode('utf-8')
        assert response.image_frame_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_frame_other_content(self, mock_boto_client):
        """Test get_image_frame_operation with other content type."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock response with integer content (other type)
        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': 12345,
            'contentType': 'image/jpeg',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should handle other content types by converting to string then bytes
        import base64

        expected_base64 = base64.b64encode('12345'.encode('utf-8')).decode('utf-8')
        assert response.image_frame_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_set_metadata_streaming_non_string(self, mock_boto_client):
        """Test get_image_set_metadata_operation with streaming body returning non-string."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a streaming body that returns bytes content
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'{"test": "data"}'

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body,
            'contentType': 'application/json',
        }

        request = GetImageSetMetadataRequest(
            datastore_id='00000000000034567890000000000000', image_set_id='img123'
        )

        response = get_image_set_metadata_operation(request)

        # Should handle bytes content from streaming body correctly
        import base64

        expected_base64 = base64.b64encode(b'{"test": "data"}').decode('utf-8')
        assert response.image_set_metadata_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_frame_streaming_non_string(self, mock_boto_client):
        """Test get_image_frame_operation with streaming body returning non-string."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock a streaming body that returns bytes content
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = b'image_data'

        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': mock_streaming_body,
            'contentType': 'image/jpeg',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should handle bytes content from streaming body correctly
        import base64

        expected_base64 = base64.b64encode(b'image_data').decode('utf-8')
        assert response.image_frame_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_frame_none_blob(self, mock_boto_client):
        """Test get_image_frame_operation with None blob."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': None,
            'contentType': 'application/octet-stream',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should return empty base64 string for None
        import base64

        expected_base64 = base64.b64encode(b'').decode('utf-8')
        assert response.image_frame_blob == expected_base64

    @patch('boto3.client')
    def test_get_image_frame_streaming_string_content(self, mock_boto_client):
        """Test get_image_frame_operation with streaming body returning string."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock streaming body that returns string content
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = 'string_image_data'

        mock_client.get_image_frame.return_value = {
            'imageFrameBlob': mock_streaming_body,
            'contentType': 'application/octet-stream',
        }

        request = GetImageFrameRequest(
            datastore_id='00000000000034567890000000000000',
            image_set_id='img123',
            image_frame_information={'imageFrameId': 'frame123'},
        )

        response = get_image_frame_operation(request)

        # Should encode string to bytes then to base64
        import base64

        expected_base64 = base64.b64encode(b'string_image_data').decode('utf-8')
        assert response.image_frame_blob == expected_base64


class TestBulkOperations:
    """Test bulk operations."""

    @patch('boto3.client')
    def test_bulk_update_patient_metadata_operation(self, mock_boto_client):
        """Test bulk_update_patient_metadata_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'version': '1'},
                {'imageSetId': 'img2', 'version': '1'},
            ]
        }

        # Mock update responses
        mock_client.update_image_set_metadata.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img1',
            'latestVersionId': '2',
            'imageSetState': 'ACTIVE',
        }

        result = bulk_update_patient_metadata_operation(
            'ds123', 'patient123', {'PatientName': 'Updated'}
        )

        assert result['patientId'] == 'patient123'
        assert result['totalUpdated'] == 2
        assert len(result['updatedImageSets']) == 2

    @patch('boto3.client')
    def test_bulk_delete_by_criteria_operation(self, mock_boto_client):
        """Test bulk_delete_by_criteria_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock search response
        mock_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}, {'imageSetId': 'img2'}]
        }

        # Mock delete responses
        mock_client.delete_image_set.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img1',
            'imageSetState': 'DELETED',
        }

        result = bulk_delete_by_criteria_operation('ds123', {'DICOMPatientId': 'patient123'}, 10)

        assert result['criteria'] == {'DICOMPatientId': 'patient123'}
        assert result['totalDeleted'] == 2
        assert result['totalFound'] == 2

    @patch('boto3.client')
    def test_bulk_operations_with_errors(self, mock_boto_client):
        """Test bulk operations with client errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'SearchImageSets',
        )

        # Test bulk_update_patient_metadata_operation
        with pytest.raises(ClientError):
            bulk_update_patient_metadata_operation(
                'ds123', 'patient123', {'PatientName': 'Updated'}
            )

        # Test bulk_delete_by_criteria_operation
        with pytest.raises(ClientError):
            bulk_delete_by_criteria_operation('ds123', {'DICOMPatientId': 'patient123'}, 10)


class TestDICOMHierarchyOperations:
    """Test DICOM hierarchy operations."""

    @patch('boto3.client')
    def test_remove_series_from_image_set_operation(self, mock_boto_client):
        """Test remove_series_from_image_set_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock get image set response
        mock_client.get_image_set.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img123',
            'versionId': '1',
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img123',
            'latestVersionId': '2',
            'imageSetState': 'ACTIVE',
        }

        result = remove_series_from_image_set_operation('ds123', 'img123', 'series123')

        assert result['imageSetId'] == 'img123'
        assert result['seriesInstanceUID'] == 'series123'
        assert result['status'] == 'removed'

    @patch('boto3.client')
    def test_remove_instance_from_image_set_operation(self, mock_boto_client):
        """Test remove_instance_from_image_set_operation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock get image set response
        mock_client.get_image_set.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img123',
            'versionId': '1',
        }

        # Mock metadata response with streaming body
        mock_streaming_body = Mock()
        mock_streaming_body.read.return_value = json.dumps(
            {
                'Study': {
                    'DICOM': {
                        'StudyInstanceUID': {
                            'study123': {
                                'Series': {'series123': {'Instances': {'instance123': {}}}}
                            }
                        }
                    }
                }
            }
        ).encode('utf-8')

        mock_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_streaming_body
        }

        # Mock update response
        mock_client.update_image_set_metadata.return_value = {
            'datastoreId': 'ds123',
            'imageSetId': 'img123',
            'latestVersionId': '2',
            'imageSetState': 'ACTIVE',
        }

        result = remove_instance_from_image_set_operation(
            'ds123', 'img123', 'series123', 'instance123'
        )

        assert result['imageSetId'] == 'img123'
        assert result['studyInstanceUID'] == 'study123'
        assert result['seriesInstanceUID'] == 'series123'
        assert result['sopInstanceUID'] == 'instance123'
        assert result['status'] == 'removed'

    @patch('boto3.client')
    def test_hierarchy_operations_with_errors(self, mock_boto_client):
        """Test DICOM hierarchy operations with client errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Image set not found'}},
            'GetImageSet',
        )

        # Test remove_series_from_image_set_operation
        with pytest.raises(ClientError):
            remove_series_from_image_set_operation('ds123', 'img123', 'series123')

        # Test remove_instance_from_image_set_operation
        with pytest.raises(ClientError):
            remove_instance_from_image_set_operation('ds123', 'img123', 'series123', 'instance123')
