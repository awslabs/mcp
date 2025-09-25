"""Tests for Pydantic models and validation."""

import pytest
from awslabs.healthlake_mcp_server.fhir_operations import validate_datastore_id
from awslabs.healthlake_mcp_server.models import (
    CreateResourceRequest,
    DatastoreFilter,
    ExportJobConfig,
    FHIRResource,
    ImportJobConfig,
    JobFilter,
    SearchParameters,
    UpdateResourceRequest,
)
from pydantic import ValidationError


class TestFHIRResource:
    """Test FHIR resource model."""

    def test_valid_fhir_resource(self):
        """Test valid FHIR resource creation."""
        resource = FHIRResource(resourceType='Patient', id='test-123')
        assert resource.resourceType == 'Patient'
        assert resource.id == 'test-123'

    def test_fhir_resource_without_id(self):
        """Test FHIR resource without ID."""
        resource = FHIRResource(resourceType='Patient')
        assert resource.resourceType == 'Patient'
        assert resource.id is None


class TestSearchParameters:
    """Test SearchParameters model."""

    def test_valid_search_parameters(self):
        """Test valid search parameters."""
        params = SearchParameters(parameters={'name': 'Smith'}, count=50)
        assert params.parameters == {'name': 'Smith'}
        assert params.count == 50

    def test_default_count(self):
        """Test default count value."""
        params = SearchParameters(parameters={})
        assert params.count == 100  # default value


class TestCreateResourceRequest:
    """Test CreateResourceRequest model."""

    def test_valid_create_request(self):
        """Test valid create resource request."""
        request = CreateResourceRequest(
            datastore_id='12345678901234567890123456789012',
            resource_type='Patient',
            resource_data={'resourceType': 'Patient', 'name': [{'family': 'Smith'}]},
        )
        assert request.datastore_id == '12345678901234567890123456789012'
        assert request.resource_type == 'Patient'
        assert 'resourceType' in request.resource_data

    def test_invalid_datastore_id(self):
        """Test invalid datastore ID."""
        with pytest.raises(ValidationError):
            CreateResourceRequest(
                datastore_id='short',
                resource_type='Patient',
                resource_data={'resourceType': 'Patient'},
            )


class TestUpdateResourceRequest:
    """Test UpdateResourceRequest model."""

    def test_valid_update_request(self):
        """Test valid update resource request."""
        request = UpdateResourceRequest(
            datastore_id='12345678901234567890123456789012',
            resource_type='Patient',
            resource_id='patient-123',
            resource_data={'resourceType': 'Patient', 'id': 'patient-123'},
        )
        assert request.datastore_id == '12345678901234567890123456789012'
        assert request.resource_type == 'Patient'
        assert request.resource_id == 'patient-123'


class TestDatastoreFilter:
    """Test DatastoreFilter model."""

    def test_valid_active_filter(self):
        """Test valid ACTIVE filter."""
        filter_obj = DatastoreFilter(status='ACTIVE')
        assert filter_obj.status == 'ACTIVE'

    def test_valid_creating_filter(self):
        """Test valid CREATING filter."""
        filter_obj = DatastoreFilter(status='CREATING')
        assert filter_obj.status == 'CREATING'

    def test_none_status(self):
        """Test None status (optional field)."""
        filter_obj = DatastoreFilter(status=None)
        assert filter_obj.status is None

    def test_invalid_status_value(self):
        """Test invalid status value."""
        with pytest.raises(ValidationError):
            DatastoreFilter(status='INVALID_STATUS')


class TestImportJobConfig:
    """Test ImportJobConfig model."""

    def test_valid_import_config(self):
        """Test valid import job config."""
        config = ImportJobConfig(
            datastore_id='12345678901234567890123456789012',
            input_data_config={'s3_uri': 's3://bucket/input'},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )
        assert config.datastore_id == '12345678901234567890123456789012'
        assert config.input_data_config['s3_uri'] == 's3://bucket/input'

    def test_import_config_with_job_name(self):
        """Test import config with job name."""
        config = ImportJobConfig(
            datastore_id='12345678901234567890123456789012',
            input_data_config={'s3_uri': 's3://bucket/input'},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
            job_name='MyImportJob',
        )
        assert config.job_name == 'MyImportJob'


class TestExportJobConfig:
    """Test ExportJobConfig model."""

    def test_valid_export_config(self):
        """Test valid export job config."""
        config = ExportJobConfig(
            datastore_id='12345678901234567890123456789012',
            output_data_config={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )
        assert config.datastore_id == '12345678901234567890123456789012'
        assert 'S3Configuration' in config.output_data_config

    def test_export_config_with_job_name(self):
        """Test export config with job name."""
        config = ExportJobConfig(
            datastore_id='12345678901234567890123456789012',
            output_data_config={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
            job_name='MyExportJob',
        )
        assert config.job_name == 'MyExportJob'


class TestJobFilter:
    """Test JobFilter model."""

    def test_valid_import_job_filter(self):
        """Test valid import job filter."""
        filter_obj = JobFilter(job_status='COMPLETED', job_type='IMPORT')
        assert filter_obj.job_status == 'COMPLETED'
        assert filter_obj.job_type == 'IMPORT'

    def test_valid_export_job_filter(self):
        """Test valid export job filter."""
        filter_obj = JobFilter(job_status='IN_PROGRESS', job_type='EXPORT')
        assert filter_obj.job_status == 'IN_PROGRESS'
        assert filter_obj.job_type == 'EXPORT'

    def test_invalid_job_status(self):
        """Test invalid job status."""
        with pytest.raises(ValidationError):
            JobFilter(job_status='INVALID_STATUS', job_type='IMPORT')

    def test_invalid_job_type(self):
        """Test invalid job type."""
        with pytest.raises(ValidationError):
            JobFilter(job_status='COMPLETED', job_type='INVALID_TYPE')


class TestValidationFunctions:
    """Test validation helper functions."""

    def test_validate_datastore_id_valid(self):
        """Test valid datastore ID."""
        valid_id = '12345678901234567890123456789012'
        result = validate_datastore_id(valid_id)
        assert result == valid_id

    def test_validate_datastore_id_invalid_length(self):
        """Test invalid datastore ID length."""
        with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
            validate_datastore_id('short-id')

    def test_validate_datastore_id_empty(self):
        """Test empty datastore ID."""
        with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
            validate_datastore_id('')
