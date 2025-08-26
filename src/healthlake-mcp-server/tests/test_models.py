"""Tests for Pydantic models - critical validation coverage."""

import pytest
from awslabs.healthlake_mcp_server.models import (
    CreateResourceRequest,
    DatastoreFilter,
    ExportJobConfig,
    ImportJobConfig,
    JobFilter,
    UpdateResourceRequest,
)
from pydantic import ValidationError


class TestCreateResourceRequest:
    """Test CreateResourceRequest model validation."""

    def test_valid_create_request(self):
        """Test valid create resource request."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'resource_type': 'Patient',
            'resource_data': {'resourceType': 'Patient', 'name': [{'family': 'Smith'}]},
        }

        request = CreateResourceRequest(**data)

        assert request.datastore_id == data['datastore_id']
        assert request.resource_type == 'Patient'
        assert request.resource_data['resourceType'] == 'Patient'

    def test_missing_required_fields(self):
        """Test create request with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            CreateResourceRequest()

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'datastore_id' in required_fields
        assert 'resource_type' in required_fields
        assert 'resource_data' in required_fields

    def test_invalid_datastore_id_length(self):
        """Test create request with invalid datastore ID length."""
        data = {
            'datastore_id': 'short',
            'resource_type': 'Patient',
            'resource_data': {'resourceType': 'Patient'},
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateResourceRequest(**data)

        assert 'datastore_id' in str(exc_info.value)


class TestUpdateResourceRequest:
    """Test UpdateResourceRequest model validation."""

    def test_valid_update_request(self):
        """Test valid update resource request."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'resource_type': 'Patient',
            'resource_id': 'patient-123',
            'resource_data': {'resourceType': 'Patient', 'id': 'patient-123'},
        }

        request = UpdateResourceRequest(**data)

        assert request.datastore_id == data['datastore_id']
        assert request.resource_type == 'Patient'
        assert request.resource_id == 'patient-123'

    def test_missing_resource_id(self):
        """Test update request with missing resource ID."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'resource_type': 'Patient',
            'resource_data': {'resourceType': 'Patient'},
        }

        with pytest.raises(ValidationError) as exc_info:
            UpdateResourceRequest(**data)

        errors = exc_info.value.errors()
        missing_fields = {error['loc'][0] for error in errors}
        assert 'resource_id' in missing_fields


class TestDatastoreFilter:
    """Test DatastoreFilter model validation."""

    def test_valid_filter_status(self):
        """Test valid datastore filter with status."""
        filter_obj = DatastoreFilter(status='ACTIVE')

        assert filter_obj.status == 'ACTIVE'

    def test_invalid_filter_status(self):
        """Test invalid datastore filter status."""
        with pytest.raises(ValidationError) as exc_info:
            DatastoreFilter(status='INVALID_STATUS')

        assert 'status' in str(exc_info.value)

    def test_optional_filter_status(self):
        """Test datastore filter without status (optional)."""
        filter_obj = DatastoreFilter()

        assert filter_obj.status is None


class TestImportJobConfig:
    """Test ImportJobConfig model validation."""

    def test_valid_import_job_config(self):
        """Test valid import job configuration."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'input_data_config': {'s3_uri': 's3://bucket/input'},
            'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        config = ImportJobConfig(**data)

        assert config.datastore_id == data['datastore_id']
        assert config.input_data_config['s3_uri'] == 's3://bucket/input'
        assert config.data_access_role_arn.startswith('arn:aws:iam::')

    def test_missing_s3_uri_in_input_config(self):
        """Test import job config with missing S3 URI in input config."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'input_data_config': {},  # Missing s3_uri - but this is not validated at model level
            'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        # This should pass at model level - validation happens in business logic
        config = ImportJobConfig(**data)
        assert config.input_data_config == {}

    def test_optional_job_name(self):
        """Test import job config with optional job name."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'input_data_config': {'s3_uri': 's3://bucket/input'},
            'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
            'job_name': 'test-import-job',
        }

        config = ImportJobConfig(**data)

        assert config.job_name == 'test-import-job'


class TestExportJobConfig:
    """Test ExportJobConfig model validation."""

    def test_valid_export_job_config(self):
        """Test valid export job configuration."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'output_data_config': {'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        config = ExportJobConfig(**data)

        assert config.datastore_id == data['datastore_id']
        assert config.output_data_config['S3Configuration']['S3Uri'] == 's3://bucket/export'

    def test_missing_output_data_config(self):
        """Test export job config with missing output data config."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        with pytest.raises(ValidationError) as exc_info:
            ExportJobConfig(**data)

        errors = exc_info.value.errors()
        missing_fields = {error['loc'][0] for error in errors}
        assert 'output_data_config' in missing_fields


class TestJobFilter:
    """Test JobFilter model validation."""

    def test_valid_job_filter(self):
        """Test valid job filter."""
        data = {'job_status': 'COMPLETED', 'job_type': 'IMPORT'}

        filter_obj = JobFilter(**data)

        assert filter_obj.job_status == 'COMPLETED'
        assert filter_obj.job_type == 'IMPORT'

    def test_invalid_job_status(self):
        """Test job filter with invalid status."""
        data = {'job_status': 'INVALID_STATUS'}

        with pytest.raises(ValidationError) as exc_info:
            JobFilter(**data)

        assert 'job_status' in str(exc_info.value)

    def test_invalid_job_type(self):
        """Test job filter with invalid type."""
        data = {'job_type': 'INVALID_TYPE'}

        with pytest.raises(ValidationError) as exc_info:
            JobFilter(**data)

        assert 'job_type' in str(exc_info.value)

    def test_optional_fields(self):
        """Test job filter with only optional fields."""
        filter_obj = JobFilter()

        assert filter_obj.job_status is None
        assert filter_obj.job_type is None


class TestModelValidators:
    """Test Pydantic model validators."""

    def test_create_request_validator_non_alphanumeric(self):
        """Test create request validator with non-alphanumeric datastore ID."""
        data = {
            'datastore_id': '1234567890123456789012345678901!',  # Contains special character
            'resource_type': 'Patient',
            'resource_data': {'resourceType': 'Patient'},
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateResourceRequest(**data)

        assert 'alphanumeric' in str(exc_info.value)

    def test_update_request_validator_non_alphanumeric(self):
        """Test update request validator with non-alphanumeric datastore ID."""
        data = {
            'datastore_id': '1234567890123456789012345678901@',  # Contains special character
            'resource_type': 'Patient',
            'resource_id': 'patient-123',
            'resource_data': {'resourceType': 'Patient'},
        }

        with pytest.raises(ValidationError) as exc_info:
            UpdateResourceRequest(**data)

        assert 'alphanumeric' in str(exc_info.value)

    def test_import_job_config_validator_non_alphanumeric(self):
        """Test import job config validator with non-alphanumeric datastore ID."""
        data = {
            'datastore_id': '1234567890123456789012345678901#',  # Contains special character
            'input_data_config': {'s3_uri': 's3://bucket/input'},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        with pytest.raises(ValidationError) as exc_info:
            ImportJobConfig(**data)

        assert 'alphanumeric' in str(exc_info.value)

    def test_export_job_config_validator_non_alphanumeric(self):
        """Test export job config validator with non-alphanumeric datastore ID."""
        data = {
            'datastore_id': '1234567890123456789012345678901$',  # Contains special character
            'output_data_config': {'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        with pytest.raises(ValidationError) as exc_info:
            ExportJobConfig(**data)

        assert 'alphanumeric' in str(exc_info.value)
