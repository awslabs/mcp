"""Tests for Pydantic models and input validation."""

import pytest
from awslabs.healthlake_mcp_server.fhir_operations import validate_datastore_id
from awslabs.healthlake_mcp_server.models import (
    CreateResourceRequest,
    DatastoreFilter,
    ExportJobConfig,
    ImportJobConfig,
    JobFilter,
    UpdateResourceRequest,
)
from awslabs.healthlake_mcp_server.server import (
    MAX_SEARCH_COUNT,
    InputValidationError,
    validate_count,
)
from pydantic import ValidationError


class TestDatastoreValidation:
    """Test datastore ID and parameter validation."""

    def test_max_search_count_constant(self):
        """Test that MAX_SEARCH_COUNT is properly defined."""
        assert MAX_SEARCH_COUNT == 100

    def test_count_validation_edge_cases(self):
        """Test count validation with edge cases."""
        # Valid cases
        assert validate_count(1) == 1
        assert validate_count(50) == 50
        assert validate_count(100) == 100

        # Invalid cases
        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(0)

        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(101)

        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(-1)

    def test_datastore_id_validation_comprehensive(self):
        """Test comprehensive datastore ID validation."""
        # Valid 32-character alphanumeric ID
        valid_id = '12345678901234567890123456789012'
        assert validate_datastore_id(valid_id) == valid_id

        # Invalid length cases
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('short')

        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('1234567890123456789012345678901234')  # 34 chars

        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('')

        # None case
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id(None)  # type: ignore


class TestResourceModels:
    """Test FHIR resource request models."""

    def test_create_resource_request_valid(self):
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

    def test_create_resource_request_missing_fields(self):
        """Test create request with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            CreateResourceRequest()  # type: ignore

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'datastore_id' in required_fields
        assert 'resource_type' in required_fields
        assert 'resource_data' in required_fields

    def test_create_resource_request_invalid_datastore_id(self):
        """Test create request with invalid datastore ID length."""
        data = {
            'datastore_id': 'short',
            'resource_type': 'Patient',
            'resource_data': {'resourceType': 'Patient'},
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateResourceRequest(**data)

        assert 'datastore_id' in str(exc_info.value)

    def test_update_resource_request_valid(self):
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

    def test_update_resource_request_missing_resource_id(self):
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


class TestJobModels:
    """Test job configuration models."""

    def test_datastore_filter_valid_status(self):
        """Test valid datastore filter with status."""
        filter_obj = DatastoreFilter(status='ACTIVE')
        assert filter_obj.status == 'ACTIVE'

    def test_datastore_filter_invalid_status(self):
        """Test invalid datastore filter status."""
        with pytest.raises(ValidationError) as exc_info:
            DatastoreFilter(status='INVALID_STATUS')

        assert 'status' in str(exc_info.value)

    def test_datastore_filter_optional_status(self):
        """Test datastore filter without status (optional)."""
        filter_obj = DatastoreFilter(status='ACTIVE')
        assert filter_obj.status == 'ACTIVE'

    def test_import_job_config_valid(self):
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

    def test_import_job_config_optional_job_name(self):
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

    def test_export_job_config_valid(self):
        """Test valid export job configuration."""
        data = {
            'datastore_id': '12345678901234567890123456789012',
            'output_data_config': {'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
        }

        config = ExportJobConfig(**data)

        assert config.datastore_id == data['datastore_id']
        assert config.output_data_config['S3Configuration']['S3Uri'] == 's3://bucket/export'

    def test_export_job_config_missing_output_data_config(self):
        """Test export job config with missing output data config."""
        with pytest.raises(ValidationError) as exc_info:
            ExportJobConfig(  # type: ignore
                datastore_id='12345678901234567890123456789012',
                data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
            )

        errors = exc_info.value.errors()
        missing_fields = {error['loc'][0] for error in errors}
        assert 'output_data_config' in missing_fields

    def test_job_filter_valid(self):
        """Test valid job filter."""
        data = {'job_status': 'COMPLETED', 'job_type': 'IMPORT'}

        filter_obj = JobFilter(**data)

        assert filter_obj.job_status == 'COMPLETED'
        assert filter_obj.job_type == 'IMPORT'

    def test_job_filter_invalid_status(self):
        """Test job filter with invalid status."""
        data = {'job_status': 'INVALID_STATUS'}

        with pytest.raises(ValidationError) as exc_info:
            JobFilter(**data)

        assert 'job_status' in str(exc_info.value)

    def test_job_filter_invalid_type(self):
        """Test job filter with invalid type."""
        data = {'job_type': 'INVALID_TYPE'}

        with pytest.raises(ValidationError) as exc_info:
            JobFilter(**data)

        assert 'job_type' in str(exc_info.value)

    def test_job_filter_optional_fields(self):
        """Test job filter with only optional fields."""
        filter_obj = JobFilter(job_status='COMPLETED', job_type='IMPORT')

        assert filter_obj.job_status == 'COMPLETED'
        assert filter_obj.job_type == 'IMPORT'


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
            'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
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
