"""Targeted tests for models edge cases to boost coverage."""

import pytest
from awslabs.healthlake_mcp_server.models import (
    CreateResourceRequest,
    ExportJobConfig,
    ImportJobConfig,
    UpdateResourceRequest,
)
from pydantic import ValidationError


class TestModelsEdgeCases:
    """Test models validation edge cases for coverage boost."""

    def test_create_resource_request_invalid_datastore_id(self):
        """Test CreateResourceRequest with non-alphanumeric datastore ID - covers line 53."""
        with pytest.raises(ValidationError):
            CreateResourceRequest(
                datastore_id='invalid-datastore-id-with-dashes!',
                resource_type='Patient',
                resource_data={'resourceType': 'Patient'},
            )

    def test_update_resource_request_invalid_datastore_id(self):
        """Test UpdateResourceRequest with non-alphanumeric datastore ID - covers line 70."""
        with pytest.raises(ValidationError):
            UpdateResourceRequest(
                datastore_id='invalid-datastore-id-with-dashes!',
                resource_type='Patient',
                resource_id='123',
                resource_data={'resourceType': 'Patient'},
            )

    def test_import_job_config_invalid_datastore_id(self):
        """Test ImportJobConfig with non-alphanumeric datastore ID - covers line 93."""
        with pytest.raises(ValidationError):
            ImportJobConfig(
                datastore_id='invalid-datastore-id-with-dashes!',
                input_data_config={'s3_uri': 's3://bucket/data'},
                data_access_role_arn='arn:aws:iam::123456789012:role/Role',
            )

    def test_export_job_config_invalid_datastore_id(self):
        """Test ExportJobConfig with non-alphanumeric datastore ID - covers line 110."""
        with pytest.raises(ValidationError):
            ExportJobConfig(
                datastore_id='invalid-datastore-id-with-dashes!',
                output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                data_access_role_arn='arn:aws:iam::123456789012:role/Role',
            )

    def test_valid_alphanumeric_datastore_ids(self):
        """Test that valid alphanumeric datastore IDs work correctly."""
        valid_id = 'a' * 32  # 32 character alphanumeric string

        # Test all models with valid ID
        create_req = CreateResourceRequest(
            datastore_id=valid_id,
            resource_type='Patient',
            resource_data={'resourceType': 'Patient'},
        )
        assert create_req.datastore_id == valid_id

        update_req = UpdateResourceRequest(
            datastore_id=valid_id,
            resource_type='Patient',
            resource_id='123',
            resource_data={'resourceType': 'Patient'},
        )
        assert update_req.datastore_id == valid_id

        import_config = ImportJobConfig(
            datastore_id=valid_id,
            input_data_config={'s3_uri': 's3://bucket/data'},
            data_access_role_arn='arn:aws:iam::123456789012:role/Role',
        )
        assert import_config.datastore_id == valid_id

        export_config = ExportJobConfig(
            datastore_id=valid_id,
            output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/Role',
        )
        assert export_config.datastore_id == valid_id
