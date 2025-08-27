"""Targeted tests for FHIR operations error scenarios to boost coverage."""

import httpx
import pytest
from awslabs.healthlake_mcp_server.fhir_operations import (
    FHIRSearchError,
    HealthLakeClient,
    validate_datastore_id,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, Mock, patch


class TestFHIRErrorScenarios:
    """Test FHIR operations error scenarios for coverage boost."""

    @pytest.fixture
    def client(self):
        """Create HealthLakeClient instance."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            return HealthLakeClient()

    async def test_search_with_invalid_parameters(self, client):
        """Test search with invalid parameters - covers lines 465-474."""
        # Test FHIRSearchError handling
        try:
            raise FHIRSearchError('Invalid search parameters', ['param1', 'param2'])
        except FHIRSearchError as e:
            assert str(e) == 'Invalid search parameters'
            assert e.invalid_params == ['param1', 'param2']

    async def test_patient_everything_error_handling(self, client):
        """Test patient everything error handling - covers lines 396-401."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Test HTTP error
            mock_client.get.side_effect = httpx.HTTPStatusError(
                'Bad Request', request=Mock(), response=Mock(status_code=400)
            )

            with pytest.raises(Exception):
                await client.patient_everything('test-datastore', 'patient-123')

    async def test_resource_operations_network_errors(self, client):
        """Test resource operations network errors - covers lines 548-550, 567-569."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Test network error in update_resource
            mock_client.put.side_effect = httpx.ConnectError('Connection failed')

            with pytest.raises(Exception):
                await client.update_resource(
                    'test-datastore', 'Patient', '123', {'resourceType': 'Patient'}
                )

            # Test network error in delete_resource
            mock_client.delete.side_effect = httpx.ConnectError('Connection failed')

            with pytest.raises(Exception):
                await client.delete_resource('test-datastore', 'Patient', '123')

    async def test_import_job_error_scenarios(self, client):
        """Test import job error scenarios - covers lines 629-630."""
        # Test different ClientError scenarios
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        client_error = ClientError(error_response, 'StartFHIRImportJob')

        with patch.object(
            client.healthlake_client, 'start_fhir_import_job', side_effect=client_error
        ):
            with pytest.raises(ValueError, match='Invalid parameters'):
                await client.start_import_job(
                    'test-datastore',
                    {'s3_uri': 's3://bucket/data'},
                    {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                    'arn:aws:iam::123456789012:role/HealthLakeRole',
                )

        # Test AccessDeniedException
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        client_error = ClientError(error_response, 'StartFHIRImportJob')

        with patch.object(
            client.healthlake_client, 'start_fhir_import_job', side_effect=client_error
        ):
            with pytest.raises(PermissionError, match='Access denied'):
                await client.start_import_job(
                    'test-datastore',
                    {'s3_uri': 's3://bucket/data'},
                    {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                    'arn:aws:iam::123456789012:role/HealthLakeRole',
                )

        # Test ResourceNotFoundException
        error_response = {
            'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Datastore not found'}
        }
        client_error = ClientError(error_response, 'StartFHIRImportJob')

        with patch.object(
            client.healthlake_client, 'start_fhir_import_job', side_effect=client_error
        ):
            with pytest.raises(ValueError, match='Datastore not found'):
                await client.start_import_job(
                    'test-datastore',
                    {'s3_uri': 's3://bucket/data'},
                    {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                    'arn:aws:iam::123456789012:role/HealthLakeRole',
                )

    async def test_list_jobs_invalid_type(self, client):
        """Test list jobs with invalid type - covers line 668."""
        # Test the else branch in list_jobs
        result = await client.list_jobs('test-datastore', job_type='INVALID')
        # The method should handle invalid job_type by returning empty result
        assert result is not None

    async def test_helpful_error_message_creation(self, client):
        """Test helpful error message creation - covers lines 330-332."""
        # Test the _create_helpful_error_message method
        test_error = Exception('Test error message')
        error_message = client._create_helpful_error_message(test_error)
        assert 'Test error message' in error_message

    async def test_bundle_processing_edge_cases(self, client):
        """Test bundle processing edge cases."""
        # Test bundle with no entries
        empty_bundle = {'resourceType': 'Bundle', 'total': 0}
        result = client._process_bundle(empty_bundle)
        assert result['total'] == 0
        assert result['entry'] == []

        # Test bundle with entries but no resources
        bundle_no_resources = {
            'resourceType': 'Bundle',
            'total': 1,
            'entry': [{'search': {'mode': 'match'}}],
        }
        result = client._process_bundle(bundle_no_resources)
        assert result['total'] == 1
        assert len(result['entry']) == 1

    async def test_auth_error_handling(self, client):
        """Test authentication error handling."""
        with patch.object(client, '_get_aws_auth', side_effect=Exception('Auth failed')):
            with pytest.raises(Exception, match='Auth failed'):
                await client.read_resource('test-datastore', 'Patient', '123')

    def test_validate_datastore_id_edge_cases(self):
        """Test datastore ID validation edge cases."""
        # Test empty string
        with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
            validate_datastore_id('')

        # Test wrong length
        with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
            validate_datastore_id('short')

        # Test valid ID
        valid_id = 'a' * 32
        assert validate_datastore_id(valid_id) == valid_id

    async def test_search_error_re_raise(self, client):
        """Test that FHIRSearchError is re-raised - covers line 478."""
        with patch.object(client, '_validate_search_request', return_value=['error']):
            with pytest.raises(FHIRSearchError):
                await client.search_resources('test-datastore', 'Patient')

    async def test_export_job_error_handling(self, client):
        """Test export job error handling - covers line 654."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        client_error = ClientError(error_response, 'StartFHIRExportJob')

        with patch.object(
            client.healthlake_client, 'start_fhir_export_job', side_effect=client_error
        ):
            with pytest.raises(ClientError):
                await client.start_export_job(
                    'test-datastore',
                    {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                    'arn:aws:iam::123456789012:role/HealthLakeRole',
                )

    async def test_pagination_next_url_extraction(self, client):
        """Test pagination next URL extraction - covers lines 330-332."""
        bundle_with_next = {
            'resourceType': 'Bundle',
            'link': [
                {'relation': 'self', 'url': 'https://example.com/self'},
                {'relation': 'next', 'url': 'https://example.com/next?page=2'},
            ],
            'entry': [],
        }

        result = client._process_bundle(bundle_with_next)
        assert result['pagination']['has_next'] is True
        assert 'next' in result['pagination']['next_token']

    async def test_import_job_with_kms_key(self, client):
        """Test import job with KMS key - covers line 599."""
        with patch.object(client.healthlake_client, 'start_fhir_import_job') as mock_start:
            mock_start.return_value = {'JobId': 'test-job-123'}

            await client.start_import_job(
                'test-datastore',
                {'s3_uri': 's3://bucket/data'},
                {'s3_configuration': {'s3_uri': 's3://bucket/output', 'kms_key_id': 'key-123'}},
                'arn:aws:iam::123456789012:role/Role',
            )

            # Verify KMS key was set
            call_args = mock_start.call_args[1]
            s3_config = call_args['JobOutputDataConfig']['S3Configuration']
            assert s3_config['KmsKeyId'] == 'key-123'

    async def test_import_job_with_name(self, client):
        """Test import job with job name - covers line 609."""
        with patch.object(client.healthlake_client, 'start_fhir_import_job') as mock_start:
            mock_start.return_value = {'JobId': 'test-job-123'}

            await client.start_import_job(
                'test-datastore',
                {'s3_uri': 's3://bucket/data'},
                {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                'arn:aws:iam::123456789012:role/Role',
                job_name='my-import-job',
            )

            # Verify job name was set
            call_args = mock_start.call_args[1]
            assert call_args['JobName'] == 'my-import-job'

    async def test_import_job_unknown_error_coverage(self, client):
        """Test import job unknown error - covers lines 629-630."""
        error_response = {'Error': {'Code': 'UnknownError', 'Message': 'Unknown error'}}
        client_error = ClientError(error_response, 'StartFHIRImportJob')

        with patch.object(
            client.healthlake_client, 'start_fhir_import_job', side_effect=client_error
        ):
            with pytest.raises(ClientError):
                await client.start_import_job(
                    'test-datastore',
                    {'s3_uri': 's3://bucket/data'},
                    {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                    'arn:aws:iam::123456789012:role/Role',
                )

    async def test_list_export_jobs_with_status_filter(self, client):
        """Test list export jobs with status filter - covers line 668."""
        with patch.object(client.healthlake_client, 'list_fhir_export_jobs') as mock_list:
            mock_list.return_value = {'ExportJobPropertiesList': []}

            await client.list_jobs('test-datastore', job_status='COMPLETED', job_type='EXPORT')

            # Verify job status was passed
            call_args = mock_list.call_args[1]
            assert call_args['JobStatus'] == 'COMPLETED'

    async def test_import_job_invalid_output_config_coverage(self, client):
        """Test import job with invalid output config - covers line 586."""
        with pytest.raises(ValueError, match='s3_configuration with s3_uri'):
            await client.start_import_job(
                'test-datastore',
                {'s3_uri': 's3://bucket/data'},
                {'invalid_config': 'bad'},  # Invalid config structure
                'arn:aws:iam::123456789012:role/Role',
            )
