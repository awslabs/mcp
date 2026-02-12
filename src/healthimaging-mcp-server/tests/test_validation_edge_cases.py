"""Additional validation tests to improve coverage."""

import pytest
from awslabs.healthimaging_mcp_server.models import (
    CopyImageSetRequest,
    DeleteDatastoreRequest,
    DeleteImageSetRequest,
    GetDatastoreRequest,
    GetDICOMExportJobRequest,
    GetDICOMImportJobRequest,
    GetImageFrameRequest,
    GetImageSetMetadataRequest,
    GetImageSetRequest,
    ListDatastoresRequest,
    ListDICOMExportJobsRequest,
    ListDICOMImportJobsRequest,
    ListImageSetVersionsRequest,
    SearchImageSetsRequest,
    StartDICOMExportJobRequest,
    StartDICOMImportJobRequest,
    UpdateImageSetMetadataRequest,
)
from pydantic import ValidationError


class TestValidationEdgeCases:
    """Test validation edge cases to improve coverage."""

    def test_empty_string_datastore_id_validation(self):
        """Test empty string datastore_id validation."""
        with pytest.raises(ValidationError, match='datastore_id cannot be empty'):
            DeleteDatastoreRequest(datastore_id='')

        with pytest.raises(ValidationError, match='datastore_id cannot be empty'):
            GetDatastoreRequest(datastore_id='   ')  # whitespace only

    def test_wrong_length_datastore_id_validation(self):
        """Test wrong length datastore_id validation."""
        with pytest.raises(
            ValidationError, match='datastore_id must be exactly 32 characters long'
        ):
            DeleteDatastoreRequest(datastore_id='short')

        with pytest.raises(
            ValidationError, match='datastore_id must be exactly 32 characters long'
        ):
            GetDatastoreRequest(datastore_id='toolong' * 10)

    def test_max_results_boundary_validation(self):
        """Test max_results boundary validation."""
        # Test 0 (too small)
        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListDatastoresRequest(max_results=0)

        # Test negative (too small)
        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListDatastoresRequest(max_results=-1)

        # Test too large for different models
        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListDatastoresRequest(max_results=51)

        valid_datastore_id = '12345678901234567890123456789012'

        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListDICOMImportJobsRequest(datastore_id=valid_datastore_id, max_results=51)

        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListDICOMExportJobsRequest(datastore_id=valid_datastore_id, max_results=51)

        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            SearchImageSetsRequest(datastore_id=valid_datastore_id, max_results=51)

        with pytest.raises(ValidationError, match='max_results must be between 1 and'):
            ListImageSetVersionsRequest(
                datastore_id=valid_datastore_id, image_set_id='img', max_results=51
            )

    def test_all_datastore_id_models_empty_validation(self):
        """Test empty datastore_id validation across all models."""
        empty_id = ''

        with pytest.raises(ValidationError):
            StartDICOMImportJobRequest(
                job_name='test',
                datastore_id=empty_id,
                data_access_role_arn='arn',
                input_s3_uri='s3://bucket',
            )

        with pytest.raises(ValidationError):
            GetDICOMImportJobRequest(datastore_id=empty_id, job_id='job')

        with pytest.raises(ValidationError):
            ListDICOMImportJobsRequest(datastore_id=empty_id)

        with pytest.raises(ValidationError):
            StartDICOMExportJobRequest(
                job_name='test',
                datastore_id=empty_id,
                data_access_role_arn='arn',
                output_s3_uri='s3://bucket',
            )

        with pytest.raises(ValidationError):
            GetDICOMExportJobRequest(datastore_id=empty_id, job_id='job')

        with pytest.raises(ValidationError):
            ListDICOMExportJobsRequest(datastore_id=empty_id)

        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id=empty_id)

        with pytest.raises(ValidationError):
            GetImageSetRequest(datastore_id=empty_id, image_set_id='img')

        with pytest.raises(ValidationError):
            GetImageSetMetadataRequest(datastore_id=empty_id, image_set_id='img')

        with pytest.raises(ValidationError):
            ListImageSetVersionsRequest(datastore_id=empty_id, image_set_id='img')

        with pytest.raises(ValidationError):
            UpdateImageSetMetadataRequest(
                datastore_id=empty_id,
                image_set_id='img',
                latest_version_id='1',
                update_image_set_metadata_updates={},
            )

        with pytest.raises(ValidationError):
            CopyImageSetRequest(
                datastore_id=empty_id, source_image_set_id='src', copy_image_set_information={}
            )

        with pytest.raises(ValidationError):
            DeleteImageSetRequest(datastore_id=empty_id, image_set_id='img')

        with pytest.raises(ValidationError):
            GetImageFrameRequest(
                datastore_id=empty_id, image_set_id='img', image_frame_information={}
            )

    def test_all_datastore_id_models_wrong_length_validation(self):
        """Test wrong length datastore_id validation across all models."""
        wrong_length_id = 'short'

        with pytest.raises(ValidationError):
            StartDICOMImportJobRequest(
                job_name='test',
                datastore_id=wrong_length_id,
                data_access_role_arn='arn',
                input_s3_uri='s3://bucket',
            )

        with pytest.raises(ValidationError):
            GetDICOMImportJobRequest(datastore_id=wrong_length_id, job_id='job')

        with pytest.raises(ValidationError):
            ListDICOMImportJobsRequest(datastore_id=wrong_length_id)

        with pytest.raises(ValidationError):
            StartDICOMExportJobRequest(
                job_name='test',
                datastore_id=wrong_length_id,
                data_access_role_arn='arn',
                output_s3_uri='s3://bucket',
            )

        with pytest.raises(ValidationError):
            GetDICOMExportJobRequest(datastore_id=wrong_length_id, job_id='job')

        with pytest.raises(ValidationError):
            ListDICOMExportJobsRequest(datastore_id=wrong_length_id)

        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id=wrong_length_id)

        with pytest.raises(ValidationError):
            GetImageSetRequest(datastore_id=wrong_length_id, image_set_id='img')

        with pytest.raises(ValidationError):
            GetImageSetMetadataRequest(datastore_id=wrong_length_id, image_set_id='img')

        with pytest.raises(ValidationError):
            ListImageSetVersionsRequest(datastore_id=wrong_length_id, image_set_id='img')

        with pytest.raises(ValidationError):
            UpdateImageSetMetadataRequest(
                datastore_id=wrong_length_id,
                image_set_id='img',
                latest_version_id='1',
                update_image_set_metadata_updates={},
            )

        with pytest.raises(ValidationError):
            CopyImageSetRequest(
                datastore_id=wrong_length_id,
                source_image_set_id='src',
                copy_image_set_information={},
            )

        with pytest.raises(ValidationError):
            DeleteImageSetRequest(datastore_id=wrong_length_id, image_set_id='img')

        with pytest.raises(ValidationError):
            GetImageFrameRequest(
                datastore_id=wrong_length_id, image_set_id='img', image_frame_information={}
            )
