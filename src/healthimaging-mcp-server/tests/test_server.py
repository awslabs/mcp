"""Tests for the HealthImaging MCP server."""

import pytest
from awslabs.healthimaging_mcp_server.server import app
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from mcp.server.fastmcp import FastMCP
from unittest.mock import MagicMock, patch


class TestHealthImagingServer:
    """Test the HealthImaging MCP server tools."""

    def test_app_is_fastmcp_instance(self):
        """Test that app is a FastMCP instance."""
        assert isinstance(app, FastMCP)

    def test_create_datastore_success(self):
        """Test successful datastore creation."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.create_datastore.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'datastoreStatus': 'CREATING',
            }

            from awslabs.healthimaging_mcp_server.server import create_datastore

            result = create_datastore(
                datastore_name='test-datastore',
                kms_key_arn='arn:aws:kms:us-east-1:000000000000:key/test-key-1234-5678-9abc-def012345678',
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.datastore_status == 'CREATING'
            mock_boto_client.assert_called_once()

    def test_get_datastore_success(self):
        """Test successful datastore retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_datastore.return_value = {
                'datastoreProperties': {
                    'datastoreId': '00000000000034567890000000000000',
                    'datastoreName': 'test-datastore',
                    'datastoreStatus': 'ACTIVE',
                }
            }

            from awslabs.healthimaging_mcp_server.server import get_datastore

            result = get_datastore(datastore_id='00000000000034567890000000000000')

            assert result.datastore_properties.datastore_id == '00000000000034567890000000000000'
            assert result.datastore_properties.datastore_name == 'test-datastore'
            mock_boto_client.assert_called_once()

    def test_list_datastores_success(self):
        """Test successful datastore listing."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.list_datastores.return_value = {
                'datastoreSummaries': [
                    {
                        'datastoreId': '00000000000034567890000000000000',
                        'datastoreName': 'test-datastore-1',
                        'datastoreStatus': 'ACTIVE',
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import list_datastores

            result = list_datastores()

            assert len(result.datastore_summaries) == 1
            assert result.datastore_summaries[0].datastore_id == '00000000000034567890000000000000'
            mock_boto_client.assert_called_once()

    def test_search_image_sets_success(self):
        """Test successful image set search."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'test-image-set-id',
                        'version': 1,
                        'createdAt': '2023-01-01T00:00:00Z',
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import search_image_sets

            result = search_image_sets(
                datastore_id='00000000000034567890000000000000',
                search_criteria={
                    'filters': [{'values': [{'DICOMPatientId': '123'}], 'operator': 'EQUAL'}]
                },
            )

            assert len(result.image_sets_metadata_summaries) == 1
            assert result.image_sets_metadata_summaries[0].image_set_id == 'test-image-set-id'
            mock_boto_client.assert_called_once()

    def test_delete_datastore_success(self):
        """Test successful datastore deletion."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.delete_datastore.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'datastoreStatus': 'DELETING',
            }

            from awslabs.healthimaging_mcp_server.server import delete_datastore

            result = delete_datastore(datastore_id='00000000000034567890000000000000')

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.datastore_status == 'DELETING'
            mock_boto_client.assert_called_once()

    def test_error_handling(self):
        """Test error handling in server functions."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_datastore.side_effect = Exception('Test error')

            from awslabs.healthimaging_mcp_server.server import get_datastore

            with pytest.raises(Exception) as exc_info:
                get_datastore(datastore_id='00000000000034567890000000000000')

            assert 'Test error' in str(exc_info.value)
            mock_boto_client.assert_called_once()

    def test_get_image_set_success(self):
        """Test successful image set retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_image_set.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'imageSetId': 'test-image-set-id',
                'versionId': '1',
                'imageSetState': 'ACTIVE',
            }

            from awslabs.healthimaging_mcp_server.server import get_image_set

            result = get_image_set(
                datastore_id='00000000000034567890000000000000', image_set_id='test-image-set-id'
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.image_set_id == 'test-image-set-id'
            mock_boto_client.assert_called_once()

    def test_delete_image_set_success(self):
        """Test successful image set deletion."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.delete_image_set.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'imageSetId': 'test-image-set-id',
                'imageSetState': 'DELETED',
            }

            from awslabs.healthimaging_mcp_server.server import delete_image_set

            result = delete_image_set(
                datastore_id='00000000000034567890000000000000', image_set_id='test-image-set-id'
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.image_set_id == 'test-image-set-id'
            mock_boto_client.assert_called_once()

    def test_get_image_set_metadata_success(self):
        """Test successful image set metadata retrieval."""
        import base64

        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_image_set_metadata.return_value = {
                'imageSetMetadataBlob': b'{"metadata": "test"}'
            }

            from awslabs.healthimaging_mcp_server.server import get_image_set_metadata

            result = get_image_set_metadata(
                datastore_id='00000000000034567890000000000000', image_set_id='test-image-set-id'
            )

            # Should return base64-encoded string
            expected_base64 = base64.b64encode(b'{"metadata": "test"}').decode('utf-8')
            assert result.image_set_metadata_blob == expected_base64
            mock_boto_client.assert_called_once()

    def test_get_image_frame_success(self):
        """Test successful image frame retrieval."""
        import base64

        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_image_frame.return_value = {'imageFrameBlob': b'image_data'}

            from awslabs.healthimaging_mcp_server.server import get_image_frame

            result = get_image_frame(
                datastore_id='00000000000034567890000000000000',
                image_set_id='test-image-set-id',
                image_frame_information={'imageFrameId': 'frame-1'},
            )

            # Should return base64-encoded string
            expected_base64 = base64.b64encode(b'image_data').decode('utf-8')
            assert result.image_frame_blob == expected_base64
            mock_boto_client.assert_called_once()

    def test_copy_image_set_success(self):
        """Test successful image set copying."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.copy_image_set.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'sourceImageSetProperties': {
                    'imageSetId': 'source-image-set-id',
                    'versionId': '1',
                },
                'destinationImageSetProperties': {
                    'imageSetId': 'dest-image-set-id',
                    'versionId': '1',
                },
            }

            from awslabs.healthimaging_mcp_server.server import copy_image_set

            result = copy_image_set(
                datastore_id='00000000000034567890000000000000',
                source_image_set_id='source-image-set-id',
                copy_image_set_information={'sourceImageSet': {'latestVersionId': '1'}},
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.source_image_set_properties.image_set_id == 'source-image-set-id'
            mock_boto_client.assert_called_once()

    def test_update_image_set_metadata_success(self):
        """Test successful image set metadata update."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.update_image_set_metadata.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'imageSetId': 'test-image-set-id',
                'latestVersionId': '2',
                'imageSetState': 'ACTIVE',
            }

            from awslabs.healthimaging_mcp_server.server import update_image_set_metadata

            result = update_image_set_metadata(
                datastore_id='00000000000034567890000000000000',
                image_set_id='test-image-set-id',
                latest_version_id='1',
                update_image_set_metadata_updates={'DICOMUpdates': {'updatableAttributes': {}}},
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.image_set_id == 'test-image-set-id'
            mock_boto_client.assert_called_once()

    def test_start_dicom_import_job_success(self):
        """Test successful DICOM import job start."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.start_dicom_import_job.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'jobId': 'test-job-id',
                'jobStatus': 'SUBMITTED',
            }

            from awslabs.healthimaging_mcp_server.server import start_dicom_import_job

            result = start_dicom_import_job(
                datastore_id='00000000000034567890000000000000',
                data_access_role_arn='arn:aws:iam::000000000000:role/test-role',
                input_s3_uri='s3://test-bucket/input/',
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.job_id == 'test-job-id'
            mock_boto_client.assert_called_once()

    def test_get_dicom_import_job_success(self):
        """Test successful DICOM import job retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_dicom_import_job.return_value = {
                'jobProperties': {
                    'jobId': 'test-job-id',
                    'jobName': 'test-job',
                    'jobStatus': 'COMPLETED',
                    'datastoreId': '00000000000034567890000000000000',
                }
            }

            from awslabs.healthimaging_mcp_server.server import get_dicom_import_job

            result = get_dicom_import_job(
                datastore_id='00000000000034567890000000000000', job_id='test-job-id'
            )

            assert result.job_properties.job_id == 'test-job-id'
            assert result.job_properties.datastore_id == '00000000000034567890000000000000'
            mock_boto_client.assert_called_once()

    def test_list_dicom_import_jobs_success(self):
        """Test successful DICOM import jobs listing."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.list_dicom_import_jobs.return_value = {
                'jobSummaries': [
                    {
                        'jobId': 'test-job-id',
                        'jobName': 'test-job',
                        'jobStatus': 'COMPLETED',
                        'datastoreId': '00000000000034567890000000000000',
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import list_dicom_import_jobs

            result = list_dicom_import_jobs(datastore_id='00000000000034567890000000000000')

            assert len(result.job_summaries) == 1
            assert result.job_summaries[0].job_id == 'test-job-id'
            mock_boto_client.assert_called_once()

    def test_list_tags_for_resource_success(self):
        """Test successful resource tags listing."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.list_tags_for_resource.return_value = {
                'tags': {'Environment': 'test', 'Project': 'healthimaging'}
            }

            from awslabs.healthimaging_mcp_server.server import list_tags_for_resource

            result = list_tags_for_resource(
                resource_arn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000'
            )

            assert result.tags == {'Environment': 'test', 'Project': 'healthimaging'}
            mock_boto_client.assert_called_once()

    def test_tag_resource_success(self):
        """Test successful resource tagging."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.tag_resource.return_value = {}

            from awslabs.healthimaging_mcp_server.server import tag_resource

            result = tag_resource(
                resource_arn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
                tags={'Environment': 'test'},
            )

            assert result.success is True
            mock_boto_client.assert_called_once()

    def test_untag_resource_success(self):
        """Test successful resource untagging."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.untag_resource.return_value = {}

            from awslabs.healthimaging_mcp_server.server import untag_resource

            result = untag_resource(
                resource_arn='arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
                tag_keys=['Environment'],
            )

            assert result.success is True
            mock_boto_client.assert_called_once()

    def test_main_function_exists(self):
        """Test that main function exists and can be imported."""
        from awslabs.healthimaging_mcp_server.server import main

        assert callable(main)

    def test_main_module_execution(self):
        """Test that main module can be executed."""
        from unittest.mock import patch

        with patch('awslabs.healthimaging_mcp_server.server.main') as mock_main:
            # Import the main module to trigger the if __name__ == '__main__' block
            # The main function should not be called during import
            mock_main.assert_not_called()

    def test_main_module_import(self):
        """Test that main module imports correctly."""
        # This test covers the import line in main.py
        import awslabs.healthimaging_mcp_server.main as main_module

        assert hasattr(main_module, 'main')
        assert callable(main_module.main)

    def test_list_image_set_versions_success(self):
        """Test successful image set versions listing."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.list_image_set_versions.return_value = {
                'imageSetPropertiesList': [
                    {
                        'imageSetId': 'test-image-set-id',
                        'versionId': '1',
                        'imageSetState': 'ACTIVE',
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import list_image_set_versions

            result = list_image_set_versions(
                datastore_id='00000000000034567890000000000000', image_set_id='test-image-set-id'
            )

            assert len(result.image_set_properties_list) == 1
            assert result.image_set_properties_list[0].image_set_id == 'test-image-set-id'
            mock_boto_client.assert_called_once()

    def test_start_dicom_export_job_success(self):
        """Test successful DICOM export job start."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.start_dicom_export_job.return_value = {
                'datastoreId': '00000000000034567890000000000000',
                'jobId': 'export-job-123',
                'jobStatus': 'SUBMITTED',
            }

            from awslabs.healthimaging_mcp_server.server import start_dicom_export_job

            result = start_dicom_export_job(
                datastore_id='00000000000034567890000000000000',
                data_access_role_arn='arn:aws:iam::000000000000:role/test-role',
                output_s3_uri='s3://test-bucket/output/',
            )

            assert result.datastore_id == '00000000000034567890000000000000'
            assert result.job_id == 'export-job-123'
            assert result.job_status == 'SUBMITTED'
            mock_boto_client.assert_called_once()

    def test_get_dicom_export_job_success(self):
        """Test successful DICOM export job retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.get_dicom_export_job.return_value = {
                'jobProperties': {
                    'jobId': 'export-job-123',
                    'jobName': 'export-job',
                    'jobStatus': 'COMPLETED',
                    'datastoreId': '00000000000034567890000000000000',
                    'dataAccessRoleArn': 'arn:aws:iam::000000000000:role/Role',
                    'outputS3Uri': 's3://bucket/output/',
                }
            }

            from awslabs.healthimaging_mcp_server.server import get_dicom_export_job

            result = get_dicom_export_job(
                datastore_id='00000000000034567890000000000000', job_id='export-job-123'
            )

            assert result.job_properties.job_id == 'export-job-123'
            assert result.job_properties.datastore_id == '00000000000034567890000000000000'
            mock_boto_client.assert_called_once()

    def test_list_dicom_export_jobs_success(self):
        """Test successful DICOM export jobs listing."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.list_dicom_export_jobs.return_value = {
                'jobSummaries': [
                    {
                        'jobId': 'export-job-123',
                        'jobName': 'export-job',
                        'jobStatus': 'COMPLETED',
                        'datastoreId': '00000000000034567890000000000000',
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import list_dicom_export_jobs

            result = list_dicom_export_jobs(datastore_id='00000000000034567890000000000000')

            assert len(result.job_summaries) == 1
            assert result.job_summaries[0].job_id == 'export-job-123'
            mock_boto_client.assert_called_once()

    def test_multiple_error_scenarios(self):
        """Test error handling across multiple functions."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Test different error scenarios
            from awslabs.healthimaging_mcp_server.server import (
                create_datastore,
                delete_datastore,
                list_datastores,
            )

            # Test create_datastore error
            mock_hi_client.create_datastore.side_effect = Exception('Create error')
            with pytest.raises(Exception) as exc_info:
                create_datastore(datastore_name='test')
            assert 'Create error' in str(exc_info.value)

            # Test delete_datastore error
            mock_hi_client.delete_datastore.side_effect = Exception('Delete error')
            with pytest.raises(Exception) as exc_info:
                delete_datastore(datastore_id='00000000000034567890000000000000')
            assert 'Delete error' in str(exc_info.value)

            # Test list_datastores error
            mock_hi_client.list_datastores.side_effect = Exception('List error')
            with pytest.raises(Exception) as exc_info:
                list_datastores()
            assert 'List error' in str(exc_info.value)


# Error handling tests to improve coverage


@pytest.mark.asyncio
async def test_create_datastore_no_credentials_error():
    """Test create_datastore with no credentials error."""
    with patch('boto3.client') as mock_client:
        mock_client.side_effect = NoCredentialsError()

        with pytest.raises(Exception):
            await app.call_tool('create_datastore', {'datastore_name': 'test-datastore'})


@pytest.mark.asyncio
async def test_create_datastore_boto_core_error():
    """Test create_datastore with BotoCoreError."""
    with patch('boto3.client') as mock_client:
        mock_client.side_effect = BotoCoreError()

        with pytest.raises(Exception):
            await app.call_tool('create_datastore', {'datastore_name': 'test-datastore'})


@pytest.mark.asyncio
async def test_delete_datastore_client_error():
    """Test delete_datastore with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.delete_datastore.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Datastore not found'}
            },
            operation_name='DeleteDatastore',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'delete_datastore', {'datastore_id': '00000000000034567890000000000000'}
            )


@pytest.mark.asyncio
async def test_get_datastore_client_error():
    """Test get_datastore with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_datastore.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Datastore not found'}
            },
            operation_name='GetDatastore',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_datastore', {'datastore_id': '00000000000034567890000000000000'}
            )


@pytest.mark.asyncio
async def test_list_datastores_client_error():
    """Test list_datastores with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.list_datastores.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListDatastores',
        )

        with pytest.raises(Exception):
            await app.call_tool('list_datastores', {})


@pytest.mark.asyncio
async def test_search_image_sets_client_error():
    """Test search_image_sets with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.search_image_sets.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid search criteria'}
            },
            operation_name='SearchImageSets',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'search_image_sets',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'search_criteria': {
                        'filters': [{'values': [{'DICOMPatientId': '123'}], 'operator': 'EQUAL'}]
                    },
                },
            )


@pytest.mark.asyncio
async def test_get_image_set_client_error():
    """Test get_image_set with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_image_set.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Image set not found'}
            },
            operation_name='GetImageSet',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_image_set',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'image_set_id': '00000000000034567890000000000000',
                },
            )


@pytest.mark.asyncio
async def test_delete_image_set_client_error():
    """Test delete_image_set with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.delete_image_set.side_effect = ClientError(
            error_response={'Error': {'Code': 'ConflictException', 'Message': 'Image set in use'}},
            operation_name='DeleteImageSet',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'delete_image_set',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'image_set_id': '00000000000034567890000000000000',
                },
            )


@pytest.mark.asyncio
async def test_get_image_set_metadata_client_error():
    """Test get_image_set_metadata with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_image_set_metadata.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Metadata not found'}
            },
            operation_name='GetImageSetMetadata',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_image_set_metadata',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'image_set_id': '00000000000034567890000000000000',
                },
            )


@pytest.mark.asyncio
async def test_get_image_frame_client_error():
    """Test get_image_frame with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_image_frame.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFound', 'Message': 'Frame not found'}},
            operation_name='GetImageFrame',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_image_frame',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'image_set_id': '00000000000034567890000000000000',
                    'image_frame_information': {'imageFrameId': 'frame123'},
                },
            )


@pytest.mark.asyncio
async def test_copy_image_set_client_error():
    """Test copy_image_set with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.copy_image_set.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid copy request'}
            },
            operation_name='CopyImageSet',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'copy_image_set',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'source_image_set_id': '00000000000034567890000000000000',
                    'copy_image_set_information': {'sourceImageSet': {'latestVersionId': '1'}},
                },
            )


@pytest.mark.asyncio
async def test_update_image_set_metadata_client_error():
    """Test update_image_set_metadata with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.update_image_set_metadata.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ConflictException', 'Message': 'Metadata conflict'}
            },
            operation_name='UpdateImageSetMetadata',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'update_image_set_metadata',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'image_set_id': '00000000000034567890000000000000',
                    'latest_version_id': '1',
                    'update_image_set_metadata_updates': {
                        'DICOMUpdates': {'updatableAttributes': '{}'}
                    },
                },
            )


@pytest.mark.asyncio
async def test_start_dicom_import_job_client_error():
    """Test start_dicom_import_job with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.start_dicom_import_job.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid import job'}
            },
            operation_name='StartDICOMImportJob',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'start_dicom_import_job',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'data_access_role_arn': 'arn:aws:iam::000000000000:role/test-role',
                    'input_s3_uri': 's3://test-bucket/input/',
                    'job_name': 'test-import',
                    'client_token': 'test-token',
                },
            )


@pytest.mark.asyncio
async def test_get_dicom_import_job_client_error():
    """Test get_dicom_import_job with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_dicom_import_job.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Import job not found'}
            },
            operation_name='GetDICOMImportJob',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_dicom_import_job',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'job_id': '00000000000034567890000000000000',
                },
            )


@pytest.mark.asyncio
async def test_list_dicom_import_jobs_client_error():
    """Test list_dicom_import_jobs with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.list_dicom_import_jobs.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListDICOMImportJobs',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'list_dicom_import_jobs', {'datastore_id': '00000000000034567890000000000000'}
            )


@pytest.mark.asyncio
async def test_start_dicom_export_job_client_error():
    """Test start_dicom_export_job with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.start_dicom_export_job.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid export job'}
            },
            operation_name='StartDICOMExportJob',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'start_dicom_export_job',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'data_access_role_arn': 'arn:aws:iam::000000000000:role/test-role',
                    'output_s3_uri': 's3://test-bucket/output/',
                    'job_name': 'test-export',
                    'client_token': 'test-token',
                },
            )


@pytest.mark.asyncio
async def test_get_dicom_export_job_client_error():
    """Test get_dicom_export_job with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.get_dicom_export_job.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Export job not found'}
            },
            operation_name='GetDICOMExportJob',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'get_dicom_export_job',
                {
                    'datastore_id': '00000000000034567890000000000000',
                    'job_id': '00000000000034567890000000000000',
                },
            )


@pytest.mark.asyncio
async def test_list_dicom_export_jobs_client_error():
    """Test list_dicom_export_jobs with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.list_dicom_export_jobs.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListDICOMExportJobs',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'list_dicom_export_jobs', {'datastore_id': '00000000000034567890000000000000'}
            )


@pytest.mark.asyncio
async def test_list_tags_for_resource_client_error():
    """Test list_tags_for_resource with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.list_tags_for_resource.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFound', 'Message': 'Resource not found'}
            },
            operation_name='ListTagsForResource',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'list_tags_for_resource',
                {
                    'resource_arn': 'arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000'
                },
            )


@pytest.mark.asyncio
async def test_tag_resource_client_error():
    """Test tag_resource with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.tag_resource.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Invalid tags'}},
            operation_name='TagResource',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'tag_resource',
                {
                    'resource_arn': 'arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
                    'tags': {'Environment': 'Test'},
                },
            )


@pytest.mark.asyncio
async def test_untag_resource_client_error():
    """Test untag_resource with ClientError."""
    with patch('boto3.client') as mock_client:
        mock_medical_imaging = MagicMock()
        mock_client.return_value = mock_medical_imaging
        mock_medical_imaging.untag_resource.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid tag keys'}
            },
            operation_name='UntagResource',
        )

        with pytest.raises(Exception):
            await app.call_tool(
                'untag_resource',
                {
                    'resource_arn': 'arn:aws:medical-imaging:us-east-1:000000000000:datastore/00000000000034567890000000000000',
                    'tag_keys': ['Environment'],
                },
            )


class TestAdvancedDICOMServerOperations:
    """Test advanced DICOM operations through the MCP server."""

    def test_delete_patient_studies_success(self):
        """Test successful patient studies deletion."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMPatientId': 'patient123'},
                    }
                ]
            }

            # Mock delete response
            mock_hi_client.delete_image_set.return_value = {
                'datastoreId': 'ds123',
                'imageSetId': 'img123',
                'imageSetState': 'DELETED',
            }

            from awslabs.healthimaging_mcp_server.server import delete_patient_studies

            result = delete_patient_studies(
                datastore_id='00000000000034567890000000000000', patient_id='patient123'
            )

            assert result['patientId'] == 'patient123'
            assert result['totalDeleted'] == 1
            mock_boto_client.assert_called_once()

    def test_delete_study_success(self):
        """Test successful study deletion."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                    }
                ]
            }

            # Mock delete response
            mock_hi_client.delete_image_set.return_value = {
                'datastoreId': 'ds123',
                'imageSetId': 'img123',
                'imageSetState': 'DELETED',
            }

            from awslabs.healthimaging_mcp_server.server import delete_study

            result = delete_study(
                datastore_id='00000000000034567890000000000000', study_instance_uid='study123'
            )

            assert result['studyInstanceUID'] == 'study123'
            assert result['totalDeleted'] == 1
            mock_boto_client.assert_called_once()

    def test_search_by_patient_id_success(self):
        """Test successful patient ID search."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMPatientId': 'patient123'},
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import search_by_patient_id

            result = search_by_patient_id(
                datastore_id='00000000000034567890000000000000',
                patient_id='patient123',
                max_results=50,
            )

            assert 'imageSetsMetadataSummaries' in result
            assert len(result['imageSetsMetadataSummaries']) == 1
            mock_boto_client.assert_called_once()

    def test_search_by_study_uid_success(self):
        """Test successful study UID search."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import search_by_study_uid

            result = search_by_study_uid(
                datastore_id='00000000000034567890000000000000',
                study_instance_uid='study123',
                max_results=50,
            )

            assert 'imageSetsMetadataSummaries' in result
            assert len(result['imageSetsMetadataSummaries']) == 1
            mock_boto_client.assert_called_once()

    def test_search_by_series_uid_success(self):
        """Test successful series UID search."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import search_by_series_uid

            result = search_by_series_uid(
                datastore_id='00000000000034567890000000000000',
                series_instance_uid='series123',
                max_results=50,
            )

            assert 'imageSetsMetadataSummaries' in result
            assert len(result['imageSetsMetadataSummaries']) == 1
            mock_boto_client.assert_called_once()

    def test_get_patient_studies_success(self):
        """Test successful patient studies retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
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
                        },
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import get_patient_studies

            result = get_patient_studies(
                datastore_id='00000000000034567890000000000000', patient_id='patient123'
            )

            assert result['patientId'] == 'patient123'
            assert result['totalStudies'] == 1
            assert len(result['studies']) == 1
            mock_boto_client.assert_called_once()

    def test_get_patient_series_success(self):
        """Test successful patient series retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'createdAt': '2023-01-01T00:00:00Z',
                        'updatedAt': '2023-01-01T00:00:00Z',
                        'DICOMTags': {
                            'DICOMPatientId': 'patient123',
                            'DICOMSeriesInstanceUID': 'series123',
                            'DICOMModality': 'CT',
                        },
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import get_patient_series

            result = get_patient_series(
                datastore_id='00000000000034567890000000000000', patient_id='patient123'
            )

            assert result['patientId'] == 'patient123'
            assert result['totalSeries'] == 1
            assert len(result['series']) == 1
            mock_boto_client.assert_called_once()

    def test_get_study_primary_image_sets_success(self):
        """Test successful study primary image sets retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',  # Primary version
                        'createdAt': '2023-01-01T00:00:00Z',
                        'updatedAt': '2023-01-01T00:00:00Z',
                        'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                    }
                ]
            }

            from awslabs.healthimaging_mcp_server.server import get_study_primary_image_sets

            result = get_study_primary_image_sets(
                datastore_id='00000000000034567890000000000000', study_instance_uid='study123'
            )

            assert result['studyInstanceUID'] == 'study123'
            assert result['totalPrimaryImageSets'] == 1
            assert len(result['primaryImageSets']) == 1
            mock_boto_client.assert_called_once()

    def test_advanced_dicom_error_handling(self):
        """Test error handling in advanced DICOM operations."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.side_effect = Exception('Search error')

            from awslabs.healthimaging_mcp_server.server import search_by_patient_id

            with pytest.raises(Exception) as exc_info:
                search_by_patient_id(
                    datastore_id='00000000000034567890000000000000', patient_id='patient123'
                )

            assert 'Search error' in str(exc_info.value)
            mock_boto_client.assert_called_once()

    # Tests for the 6 new advanced DICOM operations

    def test_delete_series_by_uid_success(self):
        """Test successful series deletion by UID."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                    }
                ]
            }

            # Mock update response
            mock_hi_client.update_image_set_metadata.return_value = {
                'imageSetId': 'img123',
                'latestVersionId': '2',
                'imageSetState': 'ACTIVE',
            }

            from awslabs.healthimaging_mcp_server.server import delete_series_by_uid

            result = delete_series_by_uid(
                datastore_id='00000000000034567890000000000000', series_instance_uid='series123'
            )

            assert result['seriesInstanceUID'] == 'series123'
            assert result['totalUpdated'] == 1
            mock_boto_client.assert_called_once()

    def test_get_series_primary_image_set_success(self):
        """Test successful series primary image set retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response with primary image set
            mock_hi_client.search_image_sets.return_value = {
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

            from awslabs.healthimaging_mcp_server.server import get_series_primary_image_set

            result = get_series_primary_image_set(
                datastore_id='00000000000034567890000000000000', series_instance_uid='series123'
            )

            assert result['seriesInstanceUID'] == 'series123'
            assert result['found'] is True
            assert result['primaryImageSet']['imageSetId'] == 'img123'
            mock_boto_client.assert_called_once()

    def test_get_patient_dicomweb_studies_success(self):
        """Test successful patient DICOMweb studies retrieval."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
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
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = b'{"Patient": {"DICOM": {"PatientName": "Test"}}, "Study": {"DICOM": {"StudyInstanceUID": {"study123": {"DICOM": {"StudyDescription": "Test Study"}}}}}}'

            mock_hi_client.get_image_set_metadata.return_value = {
                'imageSetMetadataBlob': mock_streaming_body
            }

            from awslabs.healthimaging_mcp_server.server import get_patient_dicomweb_studies

            result = get_patient_dicomweb_studies(
                datastore_id='00000000000034567890000000000000', patient_id='patient123'
            )

            assert result['patientId'] == 'patient123'
            assert result['totalStudies'] == 1
            mock_boto_client.assert_called_once()

    def test_delete_instance_in_study_success(self):
        """Test successful instance deletion in study."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                    }
                ]
            }

            # Mock metadata response with instance
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {"study123": {"Series": {"series123": {"Instances": {"instance123": {}}}}}}}}}'

            mock_hi_client.get_image_set_metadata.return_value = {
                'imageSetMetadataBlob': mock_streaming_body
            }

            # Mock update response
            mock_hi_client.update_image_set_metadata.return_value = {
                'imageSetId': 'img123',
                'latestVersionId': '2',
            }

            from awslabs.healthimaging_mcp_server.server import delete_instance_in_study

            result = delete_instance_in_study(
                datastore_id='00000000000034567890000000000000',
                study_instance_uid='study123',
                sop_instance_uid='instance123',
            )

            assert result['studyInstanceUID'] == 'study123'
            assert result['sopInstanceUID'] == 'instance123'
            assert result['totalUpdated'] == 1
            mock_boto_client.assert_called_once()

    def test_delete_instance_in_series_success(self):
        """Test successful instance deletion in series."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMSeriesInstanceUID': 'series123'},
                    }
                ]
            }

            # Mock metadata response with instance
            mock_streaming_body = MagicMock()
            mock_streaming_body.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {"study123": {"Series": {"series123": {"Instances": {"instance123": {}}}}}}}}}'

            mock_hi_client.get_image_set_metadata.return_value = {
                'imageSetMetadataBlob': mock_streaming_body
            }

            # Mock update response
            mock_hi_client.update_image_set_metadata.return_value = {
                'imageSetId': 'img123',
                'latestVersionId': '2',
            }

            from awslabs.healthimaging_mcp_server.server import delete_instance_in_series

            result = delete_instance_in_series(
                datastore_id='00000000000034567890000000000000',
                series_instance_uid='series123',
                sop_instance_uid='instance123',
            )

            assert result['seriesInstanceUID'] == 'series123'
            assert result['sopInstanceUID'] == 'instance123'
            assert result['totalUpdated'] == 1
            mock_boto_client.assert_called_once()

    def test_update_patient_study_metadata_success(self):
        """Test successful patient/study metadata update."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client

            # Mock search response
            mock_hi_client.search_image_sets.return_value = {
                'imageSetsMetadataSummaries': [
                    {
                        'imageSetId': 'img123',
                        'version': '1',
                        'DICOMTags': {'DICOMStudyInstanceUID': 'study123'},
                    }
                ]
            }

            # Mock update response
            mock_hi_client.update_image_set_metadata.return_value = {
                'imageSetId': 'img123',
                'latestVersionId': '2',
            }

            from awslabs.healthimaging_mcp_server.server import update_patient_study_metadata

            patient_updates = {'PatientName': 'Updated Name'}
            study_updates = {'StudyDescription': 'Updated Description'}

            result = update_patient_study_metadata(
                datastore_id='00000000000034567890000000000000',
                study_instance_uid='study123',
                patient_updates=patient_updates,
                study_updates=study_updates,
            )

            assert result['studyInstanceUID'] == 'study123'
            assert result['patientUpdates'] == patient_updates
            assert result['studyUpdates'] == study_updates
            assert result['totalUpdated'] == 1
            mock_boto_client.assert_called_once()

    def test_new_operations_error_handling(self):
        """Test error handling in new operations."""
        with patch('boto3.client') as mock_boto_client:
            mock_hi_client = MagicMock()
            mock_boto_client.return_value = mock_hi_client
            mock_hi_client.search_image_sets.side_effect = Exception('Search error')

            from awslabs.healthimaging_mcp_server.server import delete_series_by_uid

            with pytest.raises(Exception) as exc_info:
                delete_series_by_uid(
                    datastore_id='00000000000034567890000000000000',
                    series_instance_uid='series123',
                )

            assert 'Search error' in str(exc_info.value)
            mock_boto_client.assert_called_once()


@pytest.mark.asyncio
async def test_main_function_coverage():
    """Test main function for coverage."""
    with patch('awslabs.healthimaging_mcp_server.server.app') as mock_app:
        from awslabs.healthimaging_mcp_server.server import main

        main()
        mock_app.run.assert_called_once()


class TestBulkOperationsServer:
    """Test bulk operations server functions."""

    @patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.bulk_update_patient_metadata'
    )
    def test_bulk_update_patient_metadata_success(self, mock_operation):
        """Test bulk_update_patient_metadata server function success."""
        mock_operation.return_value = {
            'patientId': 'patient123',
            'totalUpdated': 2,
            'updatedImageSets': [],
        }

        from awslabs.healthimaging_mcp_server.server import bulk_update_patient_metadata

        result = bulk_update_patient_metadata(
            datastore_id='ds123',
            patient_id='patient123',
            metadata_updates={'PatientName': 'Updated'},
        )

        assert result['patientId'] == 'patient123'
        assert result['totalUpdated'] == 2
        mock_operation.assert_called_once_with('ds123', 'patient123', {'PatientName': 'Updated'})

    @patch('awslabs.healthimaging_mcp_server.healthimaging_operations.bulk_delete_by_criteria')
    def test_bulk_delete_by_criteria_success(self, mock_operation):
        """Test bulk_delete_by_criteria server function success."""
        mock_operation.return_value = {
            'criteria': {'DICOMPatientId': 'patient123'},
            'totalDeleted': 2,
            'deletedImageSets': [],
        }

        from awslabs.healthimaging_mcp_server.server import bulk_delete_by_criteria

        result = bulk_delete_by_criteria(
            datastore_id='ds123', criteria={'DICOMPatientId': 'patient123'}, max_deletions=10
        )

        assert result['criteria'] == {'DICOMPatientId': 'patient123'}
        assert result['totalDeleted'] == 2
        mock_operation.assert_called_once_with('ds123', {'DICOMPatientId': 'patient123'}, 10)

    @patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.bulk_update_patient_metadata'
    )
    def test_bulk_operations_error_handling(self, mock_operation):
        """Test bulk operations error handling."""
        mock_operation.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'UpdateImageSetMetadata',
        )

        from awslabs.healthimaging_mcp_server.server import bulk_update_patient_metadata

        with pytest.raises(ClientError):
            bulk_update_patient_metadata(
                datastore_id='ds123',
                patient_id='patient123',
                metadata_updates={'PatientName': 'Updated'},
            )


class TestDICOMHierarchyOperationsServer:
    """Test DICOM hierarchy operations server functions."""

    @patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.remove_series_from_image_set'
    )
    def test_remove_series_from_image_set_success(self, mock_operation):
        """Test remove_series_from_image_set server function success."""
        mock_operation.return_value = {
            'imageSetId': 'img123',
            'seriesInstanceUID': 'series123',
            'status': 'removed',
        }

        from awslabs.healthimaging_mcp_server.server import remove_series_from_image_set

        result = remove_series_from_image_set(
            datastore_id='ds123', image_set_id='img123', series_instance_uid='series123'
        )

        assert result['imageSetId'] == 'img123'
        assert result['seriesInstanceUID'] == 'series123'
        assert result['status'] == 'removed'
        mock_operation.assert_called_once_with('ds123', 'img123', 'series123')

    @patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.remove_instance_from_image_set'
    )
    def test_remove_instance_from_image_set_success(self, mock_operation):
        """Test remove_instance_from_image_set server function success."""
        mock_operation.return_value = {
            'imageSetId': 'img123',
            'studyInstanceUID': 'study123',
            'seriesInstanceUID': 'series123',
            'sopInstanceUID': 'instance123',
            'status': 'removed',
        }

        from awslabs.healthimaging_mcp_server.server import remove_instance_from_image_set

        result = remove_instance_from_image_set(
            datastore_id='ds123',
            image_set_id='img123',
            series_instance_uid='series123',
            sop_instance_uid='instance123',
        )

        assert result['imageSetId'] == 'img123'
        assert result['studyInstanceUID'] == 'study123'
        assert result['seriesInstanceUID'] == 'series123'
        assert result['sopInstanceUID'] == 'instance123'
        assert result['status'] == 'removed'
        mock_operation.assert_called_once_with('ds123', 'img123', 'series123', 'instance123')

    @patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.remove_series_from_image_set'
    )
    def test_hierarchy_operations_error_handling(self, mock_operation):
        """Test DICOM hierarchy operations error handling."""
        mock_operation.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Image set not found'}},
            'GetImageSet',
        )

        from awslabs.healthimaging_mcp_server.server import remove_series_from_image_set

        with pytest.raises(ClientError):
            remove_series_from_image_set(
                datastore_id='ds123', image_set_id='img123', series_instance_uid='series123'
            )


class TestEnumConversionFunctions:
    """Test enum conversion helper functions."""

    def test_convert_to_datastore_status_valid_values(self):
        """Test _convert_to_datastore_status with valid enum values."""
        from awslabs.healthimaging_mcp_server.models import DatastoreStatus
        from awslabs.healthimaging_mcp_server.server import _convert_to_datastore_status

        # Test all valid enum values
        assert _convert_to_datastore_status('CREATING') == DatastoreStatus.CREATING
        assert _convert_to_datastore_status('ACTIVE') == DatastoreStatus.ACTIVE
        assert _convert_to_datastore_status('DELETING') == DatastoreStatus.DELETING
        assert _convert_to_datastore_status('DELETED') == DatastoreStatus.DELETED

    def test_convert_to_datastore_status_none_value(self):
        """Test _convert_to_datastore_status with None value."""
        from awslabs.healthimaging_mcp_server.server import _convert_to_datastore_status

        assert _convert_to_datastore_status(None) is None

    def test_convert_to_datastore_status_invalid_value(self):
        """Test _convert_to_datastore_status with invalid value."""
        from awslabs.healthimaging_mcp_server.server import _convert_to_datastore_status

        assert _convert_to_datastore_status('INVALID_STATUS') is None

    def test_convert_to_job_status_valid_values(self):
        """Test _convert_to_job_status with valid enum values."""
        from awslabs.healthimaging_mcp_server.models import JobStatus
        from awslabs.healthimaging_mcp_server.server import _convert_to_job_status

        # Test all valid enum values
        assert _convert_to_job_status('SUBMITTED') == JobStatus.SUBMITTED
        assert _convert_to_job_status('IN_PROGRESS') == JobStatus.IN_PROGRESS
        assert _convert_to_job_status('COMPLETED') == JobStatus.COMPLETED
        assert _convert_to_job_status('FAILED') == JobStatus.FAILED

    def test_convert_to_job_status_none_value(self):
        """Test _convert_to_job_status with None value."""
        from awslabs.healthimaging_mcp_server.server import _convert_to_job_status

        assert _convert_to_job_status(None) is None

    def test_convert_to_job_status_invalid_value(self):
        """Test _convert_to_job_status with invalid value."""
        from awslabs.healthimaging_mcp_server.server import _convert_to_job_status

        assert _convert_to_job_status('INVALID_STATUS') is None
