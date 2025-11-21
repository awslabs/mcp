"""Tests for AWS HealthLake FHIR client operations."""

import pytest
from awslabs.healthlake_mcp_server.fhir_operations import (
    AWSAuth,
    FHIRSearchError,
    HealthLakeClient,
    validate_datastore_id,
)
from botocore.exceptions import ClientError, NoCredentialsError
from unittest.mock import AsyncMock, Mock, patch


class TestValidateDatastoreId:
    """Test datastore ID validation."""

    def test_valid_datastore_id(self):
        """Test valid 32-character datastore ID."""
        valid_id = '12345678901234567890123456789012'
        result = validate_datastore_id(valid_id)
        assert result == valid_id

    def test_invalid_length_short(self):
        """Test datastore ID too short."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('short')

    def test_invalid_length_long(self):
        """Test datastore ID too long."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('1234567890123456789012345678901234')

    def test_empty_datastore_id(self):
        """Test empty datastore ID."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('')


class TestHealthLakeClientInit:
    """Test HealthLake client initialization."""

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_init_with_region(self, mock_session):
        """Test client initialization with specific region."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient(region_name='us-west-2')

        assert client.region == 'us-west-2'
        mock_session_instance.client.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_init_no_credentials(self, mock_session):
        """Test client initialization with no credentials."""
        mock_session.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            HealthLakeClient()


class TestAsyncDatastoreOperations:
    """Test async datastore operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_list_datastores_success(self, mock_client):
        """Test successful datastore listing."""
        expected_response = {
            'DatastorePropertiesList': [
                {'DatastoreId': '12345678901234567890123456789012', 'DatastoreStatus': 'ACTIVE'}
            ]
        }
        mock_client.healthlake_client.list_fhir_datastores.return_value = expected_response

        result = await mock_client.list_datastores()

        assert result == expected_response
        mock_client.healthlake_client.list_fhir_datastores.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_list_datastores_with_filter(self, mock_client):
        """Test datastore listing with status filter."""
        expected_response = {'DatastorePropertiesList': []}
        mock_client.healthlake_client.list_fhir_datastores.return_value = expected_response

        result = await mock_client.list_datastores(filter_status='ACTIVE')

        assert result == expected_response

        mock_client.healthlake_client.list_fhir_datastores.assert_called_once_with(
            Filter={'DatastoreStatus': 'ACTIVE'}
        )

    @pytest.mark.asyncio
    async def test_list_datastores_client_error(self, mock_client):
        """Test datastore listing with client error."""
        mock_client.healthlake_client.list_fhir_datastores.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListFHIRDatastores'
        )

        with pytest.raises(ClientError):
            await mock_client.list_datastores()

    @pytest.mark.asyncio
    async def test_get_datastore_details_success(self, mock_client):
        """Test successful datastore details retrieval."""
        datastore_id = '12345678901234567890123456789012'
        expected_response = {
            'DatastoreProperties': {'DatastoreId': datastore_id, 'DatastoreStatus': 'ACTIVE'}
        }
        mock_client.healthlake_client.describe_fhir_datastore.return_value = expected_response

        result = await mock_client.get_datastore_details(datastore_id)

        assert result == expected_response
        mock_client.healthlake_client.describe_fhir_datastore.assert_called_once_with(
            DatastoreId=datastore_id
        )

    @pytest.mark.asyncio
    async def test_get_datastore_details_client_error(self, mock_client):
        """Test datastore details with client error."""
        datastore_id = '12345678901234567890123456789012'
        mock_client.healthlake_client.describe_fhir_datastore.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFound', 'Message': 'Datastore not found'}},
            'DescribeFHIRDatastore',
        )

        with pytest.raises(ClientError):
            await mock_client.get_datastore_details(datastore_id)


class TestAsyncCRUDOperations:
    """Test async CRUD operations."""

    @pytest.fixture
    def mock_client_with_auth(self):
        """Create a mock client with auth setup."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            client.session = Mock()
            client.region = 'us-east-1'

            # Mock credentials
            mock_credentials = Mock()
            client.session.get_credentials.return_value = mock_credentials
            return client

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_read_resource_success(self, mock_httpx, mock_client_with_auth):
        """Test successful resource read."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {'resourceType': 'Patient', 'id': 'patient-123'}
        mock_response.raise_for_status = Mock()

        # Create async context manager mock
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        result = await mock_client_with_auth.read_resource(
            '12345678901234567890123456789012', 'Patient', 'patient-123'
        )

        assert result == {'resourceType': 'Patient', 'id': 'patient-123'}
        mock_client_instance.get.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_create_resource_success(self, mock_httpx, mock_client_with_auth):
        """Test successful resource creation."""
        mock_response = Mock()
        mock_response.json.return_value = {'resourceType': 'Patient', 'id': 'new-patient'}
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        resource_data = {'resourceType': 'Patient', 'name': [{'family': 'Smith'}]}

        result = await mock_client_with_auth.create_resource(
            '12345678901234567890123456789012', 'Patient', resource_data
        )

        assert result == {'resourceType': 'Patient', 'id': 'new-patient'}
        mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_update_resource_success(self, mock_httpx, mock_client_with_auth):
        """Test successful resource update."""
        mock_response = Mock()
        mock_response.json.return_value = {'resourceType': 'Patient', 'id': 'patient-123'}
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.put.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        resource_data = {'resourceType': 'Patient', 'id': 'patient-123'}

        result = await mock_client_with_auth.update_resource(
            '12345678901234567890123456789012', 'Patient', 'patient-123', resource_data
        )

        assert result == {'resourceType': 'Patient', 'id': 'patient-123'}
        mock_client_instance.put.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_delete_resource_success(self, mock_httpx, mock_client_with_auth):
        """Test successful resource deletion."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.delete.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        result = await mock_client_with_auth.delete_resource(
            '12345678901234567890123456789012', 'Patient', 'patient-123'
        )

        expected = {'status': 'deleted', 'resourceType': 'Patient', 'id': 'patient-123'}
        assert result == expected
        mock_client_instance.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_crud_operation_http_error(self, mock_httpx, mock_client_with_auth):
        """Test CRUD operation with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('HTTP 404 Not Found')

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(Exception, match='HTTP 404 Not Found'):
            await mock_client_with_auth.read_resource(
                '12345678901234567890123456789012', 'Patient', 'nonexistent'
            )

    """Test search request validation."""

    def test_validate_search_request_valid(self):
        """Test valid search request."""
        client = HealthLakeClient.__new__(HealthLakeClient)  # Skip __init__

        errors = client._validate_search_request(resource_type='Patient', count=50)

        assert errors == []

    def test_validate_search_request_empty_resource_type(self):
        """Test validation with empty resource type."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        errors = client._validate_search_request(resource_type='', count=50)

        assert 'Resource type is required' in errors

    def test_validate_search_request_invalid_count_low(self):
        """Test validation with count too low."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        errors = client._validate_search_request(resource_type='Patient', count=0)

        assert 'Count must be between 1 and 100' in errors

    def test_validate_search_request_invalid_count_high(self):
        """Test validation with count too high."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        errors = client._validate_search_request(resource_type='Patient', count=101)

        assert 'Count must be between 1 and 100' in errors

    def test_validate_search_request_invalid_include_format(self):
        """Test validation with invalid include format."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        errors = client._validate_search_request(
            resource_type='Patient', include_params=['invalid_format'], count=50
        )

        assert 'Invalid include format' in errors[0]

    def test_validate_search_request_invalid_revinclude_format(self):
        """Test validation with invalid revinclude format."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        errors = client._validate_search_request(
            resource_type='Patient', revinclude_params=['invalid_format'], count=50
        )

        assert 'Invalid revinclude format' in errors[0]


class TestBundleProcessing:
    """Test FHIR Bundle processing."""

    def test_process_bundle_basic(self):
        """Test basic bundle processing."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        bundle = {
            'resourceType': 'Bundle',
            'id': 'test-bundle',
            'type': 'searchset',
            'total': 2,
            'entry': [
                {'resource': {'resourceType': 'Patient', 'id': '1'}},
                {'resource': {'resourceType': 'Patient', 'id': '2'}},
            ],
            'link': [],
        }

        result = client._process_bundle(bundle)

        assert result['resourceType'] == 'Bundle'
        assert result['total'] == 2
        assert len(result['entry']) == 2
        assert result['pagination']['has_next'] is False

    def test_process_bundle_with_next_link(self):
        """Test bundle processing with pagination."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        bundle = {
            'resourceType': 'Bundle',
            'entry': [],
            'link': [
                {
                    'relation': 'next',
                    'url': 'https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/Patient/_search?_count=100&page=next_token',
                }
            ],
        }

        result = client._process_bundle(bundle)

        assert result['pagination']['has_next'] is True
        assert result['pagination']['next_token'] is not None

    def test_process_bundle_missing_total(self):
        """Test bundle processing when total is missing."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        bundle = {'resourceType': 'Bundle', 'entry': [{'resource': {'resourceType': 'Patient'}}]}

        result = client._process_bundle(bundle)

        assert result['total'] == 1  # Should use entry count as fallback


class TestSearchRequestBuilding:
    """Test search request building."""

    def test_build_search_request_basic(self):
        """Test basic search request building."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            count=50,
        )

        assert url.endswith('Patient/_search')
        assert form_data['_count'] == '50'

    def test_build_search_request_with_params(self):
        """Test search request with parameters."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            search_params={'name': 'Smith', 'gender': 'male'},
            count=50,
        )

        assert form_data['name'] == 'Smith'
        assert form_data['gender'] == 'male'

    def test_build_search_request_with_modifiers(self):
        """Test search request with FHIR modifiers."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            search_params={'name:contains': 'Smith'},
            count=50,
        )

        # Should URL-encode the colon in parameter names
        assert 'name%3Acontains' in form_data

    def test_build_search_request_with_includes(self):
        """Test search request with include parameters."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            include_params=['Patient:general-practitioner'],
            revinclude_params=['Observation:subject'],
            count=50,
        )

        assert form_data['_include'] == 'Patient:general-practitioner'
        assert form_data['_revinclude'] == 'Observation:subject'

    def test_build_search_request_with_next_token(self):
        """Test search request with pagination token."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        next_token = 'https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/Patient/_search?page=token'

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            next_token=next_token,
            count=50,
        )

        assert url == next_token
        assert form_data == {}


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_fhir_search_error_creation(self):
        """Test FHIRSearchError creation."""
        error = FHIRSearchError('Test error', ['param1', 'param2'])

        assert str(error) == 'Test error'
        assert error.invalid_params == ['param1', 'param2']

    def test_create_helpful_error_message_400(self):
        """Test helpful error message for 400 errors."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        error = Exception('400 Bad Request: Invalid parameter')
        message = client._create_helpful_error_message(error)

        assert 'HealthLake rejected the search request' in message
        assert 'Common solutions:' in message

    def test_create_helpful_error_message_validation(self):
        """Test helpful error message for validation errors."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        error = Exception('Validation failed: Invalid format')
        message = client._create_helpful_error_message(error)

        assert 'Search validation failed' in message
        assert 'Check your search parameters' in message

    def test_create_helpful_error_message_generic(self):
        """Test helpful error message for generic errors."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        error = Exception('Network timeout')
        message = client._create_helpful_error_message(error)

        assert 'Search error: Network timeout' in message


class TestExportJobOperations:
    """Test export job operations for coverage."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_start_export_job_success(self, mock_client):
        """Test successful export job start (coverage: lines 640-653)."""
        expected_response = {'JobId': 'export-123', 'JobStatus': 'SUBMITTED'}
        mock_client.healthlake_client.start_fhir_export_job.return_value = expected_response

        result = await mock_client.start_export_job(
            datastore_id='12345678901234567890123456789012',
            output_data_config={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )

        assert result == expected_response
        mock_client.healthlake_client.start_fhir_export_job.assert_called_once_with(
            DatastoreId='12345678901234567890123456789012',
            OutputDataConfig={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            DataAccessRoleArn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )

    @pytest.mark.asyncio
    async def test_start_export_job_with_job_name(self, mock_client):
        """Test export job start with optional job name."""
        expected_response = {'JobId': 'export-456', 'JobStatus': 'SUBMITTED'}
        mock_client.healthlake_client.start_fhir_export_job.return_value = expected_response

        result = await mock_client.start_export_job(
            datastore_id='12345678901234567890123456789012',
            output_data_config={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
            job_name='MyExportJob',
        )

        assert result == expected_response
        mock_client.healthlake_client.start_fhir_export_job.assert_called_once_with(
            DatastoreId='12345678901234567890123456789012',
            OutputDataConfig={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            DataAccessRoleArn='arn:aws:iam::123456789012:role/HealthLakeRole',
            JobName='MyExportJob',
        )

    @pytest.mark.asyncio
    async def test_start_export_job_client_error(self, mock_client):
        """Test export job start with ClientError."""
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid S3 URI'}}
        mock_client.healthlake_client.start_fhir_export_job.side_effect = ClientError(
            error_response, 'StartFHIRExportJob'
        )

        with pytest.raises(ClientError):
            await mock_client.start_export_job(
                datastore_id='12345678901234567890123456789012',
                output_data_config={'S3Configuration': {'S3Uri': 'invalid-uri'}},
                data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
            )


class TestAWSAuth:
    """Test AWS authentication."""

    def test_aws_auth_initialization(self):
        """Test AWSAuth initialization."""
        mock_credentials = Mock()
        auth = AWSAuth(credentials=mock_credentials, region='us-east-1')

        assert auth.credentials == mock_credentials
        assert auth.region == 'us-east-1'
        assert auth.service == 'healthlake'

    def test_aws_auth_custom_service(self):
        """Test AWSAuth with custom service."""
        mock_credentials = Mock()
        auth = AWSAuth(credentials=mock_credentials, region='us-east-1', service='custom')

        assert auth.service == 'custom'


class TestAsyncJobOperations:
    """Test async job operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_start_import_job_success(self, mock_client):
        """Test successful import job start."""
        expected_response = {'JobId': 'import-job-123', 'JobStatus': 'SUBMITTED'}
        mock_client.healthlake_client.start_fhir_import_job.return_value = expected_response

        result = await mock_client.start_import_job(
            '12345678901234567890123456789012',
            {'s3_uri': 's3://bucket/input'},
            {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            'arn:aws:iam::123456789012:role/HealthLakeRole',
        )

        assert result == expected_response
        mock_client.healthlake_client.start_fhir_import_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_import_job_validation_error(self, mock_client):
        """Test import job with validation error."""
        with pytest.raises(ValueError, match="input_data_config must contain 's3_uri'"):
            await mock_client.start_import_job(
                '12345678901234567890123456789012',
                {},  # Missing s3_uri
                {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                'arn:aws:iam::123456789012:role/HealthLakeRole',
            )

    @pytest.mark.asyncio
    async def test_list_jobs_both_types(self, mock_client):
        """Test listing both import and export jobs."""
        import_response = {'ImportJobPropertiesList': [{'JobId': 'import-1'}]}
        export_response = {'ExportJobPropertiesList': [{'JobId': 'export-1'}]}

        mock_client.healthlake_client.list_fhir_import_jobs.return_value = import_response
        mock_client.healthlake_client.list_fhir_export_jobs.return_value = export_response

        result = await mock_client.list_jobs('12345678901234567890123456789012')

        expected = {'ImportJobs': [{'JobId': 'import-1'}], 'ExportJobs': [{'JobId': 'export-1'}]}
        assert result == expected

    @pytest.mark.asyncio
    async def test_list_jobs_import_only(self, mock_client):
        """Test listing import jobs only (coverage: lines 661-664)."""
        import_response = {'ImportJobPropertiesList': [{'JobId': 'import-1'}]}
        mock_client.healthlake_client.list_fhir_import_jobs.return_value = import_response

        result = await mock_client.list_jobs('12345678901234567890123456789012', job_type='IMPORT')

        assert result == import_response
        mock_client.healthlake_client.list_fhir_import_jobs.assert_called_once_with(
            DatastoreId='12345678901234567890123456789012'
        )

    @pytest.mark.asyncio
    async def test_list_jobs_export_only(self, mock_client):
        """Test listing export jobs only (coverage: lines 666-669)."""
        export_response = {'ExportJobPropertiesList': [{'JobId': 'export-1'}]}
        mock_client.healthlake_client.list_fhir_export_jobs.return_value = export_response

        result = await mock_client.list_jobs('12345678901234567890123456789012', job_type='EXPORT')

        assert result == export_response
        mock_client.healthlake_client.list_fhir_export_jobs.assert_called_once_with(
            DatastoreId='12345678901234567890123456789012'
        )

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(self, mock_client):
        """Test listing jobs with status filter."""
        import_response = {'ImportJobPropertiesList': [{'JobId': 'import-1'}]}
        mock_client.healthlake_client.list_fhir_import_jobs.return_value = import_response

        result = await mock_client.list_jobs(
            '12345678901234567890123456789012', job_status='COMPLETED', job_type='IMPORT'
        )

        assert result == import_response
        mock_client.healthlake_client.list_fhir_import_jobs.assert_called_once_with(
            DatastoreId='12345678901234567890123456789012', JobStatus='COMPLETED'
        )


class TestAWSAuthFlow:
    """Test AWS SigV4 authentication flow."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock HTTP request."""
        request = Mock()
        request.method = 'POST'
        request.url = Mock()
        request.url.host = 'healthlake.us-east-1.amazonaws.com'
        request.content = b'{"resourceType": "Patient"}'
        request.headers = {'content-length': '25'}
        return request

    @pytest.fixture
    def mock_credentials(self):
        """Create mock AWS credentials."""
        credentials = Mock()
        credentials.access_key = 'AKIATEST'
        credentials.secret_key = 'secret'  # pragma: allowlist secret
        credentials.token = None
        return credentials

    def test_aws_auth_flow_post_request(self, mock_request, mock_credentials):
        """Test auth flow for POST request with body."""
        auth = AWSAuth(credentials=mock_credentials, region='us-east-1')

        with (
            patch('awslabs.healthlake_mcp_server.fhir_operations.AWSRequest') as mock_aws_request,
            patch('awslabs.healthlake_mcp_server.fhir_operations.SigV4Auth') as mock_signer,
        ):
            mock_aws_request_instance = Mock()
            mock_aws_request.return_value = mock_aws_request_instance
            mock_aws_request_instance.headers = {
                'Authorization': 'AWS4-HMAC-SHA256 ...',
                'X-Amz-Date': '20220101T120000Z',
                'Host': 'healthlake.us-east-1.amazonaws.com',
            }

            mock_signer_instance = Mock()
            mock_signer.return_value = mock_signer_instance

            # Execute auth flow
            auth_generator = auth.auth_flow(mock_request)
            result_request = next(auth_generator)

            # Verify AWS request was created correctly
            mock_aws_request.assert_called_once()
            call_args = mock_aws_request.call_args
            assert call_args[1]['method'] == 'POST'
            assert call_args[1]['data'] == b'{"resourceType": "Patient"}'

            # Verify signer was called
            mock_signer.assert_called_once_with(mock_credentials, 'healthlake', 'us-east-1')
            mock_signer_instance.add_auth.assert_called_once_with(mock_aws_request_instance)

            # Verify headers were set
            assert result_request == mock_request

    def test_aws_auth_flow_get_request(self, mock_credentials):
        """Test auth flow for GET request without body."""
        request = Mock()
        request.method = 'GET'
        request.url = Mock()
        request.url.host = 'healthlake.us-east-1.amazonaws.com'
        request.content = None
        request.headers = {}

        auth = AWSAuth(credentials=mock_credentials, region='us-east-1')

        with (
            patch('awslabs.healthlake_mcp_server.fhir_operations.AWSRequest') as mock_aws_request,
            patch('awslabs.healthlake_mcp_server.fhir_operations.SigV4Auth') as mock_signer,
        ):
            mock_aws_request_instance = Mock()
            mock_aws_request.return_value = mock_aws_request_instance
            mock_aws_request_instance.headers = {'Authorization': 'AWS4-HMAC-SHA256 ...'}

            mock_signer_instance = Mock()
            mock_signer.return_value = mock_signer_instance

            # Execute auth flow
            auth_generator = auth.auth_flow(request)
            result_request = next(auth_generator)

            # Verify no body for GET request
            call_args = mock_aws_request.call_args
            assert call_args[1]['data'] is None
            assert result_request == request

    def test_aws_auth_flow_with_content_length(self, mock_request, mock_credentials):
        """Test auth flow preserves Content-Length header."""
        auth = AWSAuth(credentials=mock_credentials, region='us-east-1')

        with (
            patch('awslabs.healthlake_mcp_server.fhir_operations.AWSRequest') as mock_aws_request,
            patch('awslabs.healthlake_mcp_server.fhir_operations.SigV4Auth'),
        ):
            mock_aws_request_instance = Mock()
            mock_aws_request.return_value = mock_aws_request_instance
            mock_aws_request_instance.headers = {}

            # Execute auth flow
            auth_generator = auth.auth_flow(mock_request)
            next(auth_generator)

            # Verify Content-Length was included in headers for signing
            call_args = mock_aws_request.call_args
            headers = call_args[1]['headers']
            assert headers['Content-Length'] == '25'

    def test_aws_auth_flow_custom_service(self, mock_request, mock_credentials):
        """Test auth flow with custom service name."""
        auth = AWSAuth(credentials=mock_credentials, region='us-west-2', service='custom-service')

        with patch('awslabs.healthlake_mcp_server.fhir_operations.SigV4Auth') as mock_signer:
            # Execute auth flow
            auth_generator = auth.auth_flow(mock_request)
            next(auth_generator)

            # Verify custom service was used
            mock_signer.assert_called_once_with(mock_credentials, 'custom-service', 'us-west-2')


class TestAWSAuthMethod:
    """Test AWS authentication method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.session = Mock()
            client.region = 'us-east-1'
            return client

    def test_get_aws_auth_success(self, mock_client):
        """Test successful AWS auth creation."""
        mock_credentials = Mock()
        mock_client.session.get_credentials.return_value = mock_credentials

        auth = mock_client._get_aws_auth()

        assert isinstance(auth, AWSAuth)
        assert auth.credentials == mock_credentials
        assert auth.region == 'us-east-1'

    def test_get_aws_auth_no_credentials(self, mock_client):
        """Test AWS auth with no credentials."""
        mock_client.session.get_credentials.return_value = None

        with pytest.raises(NoCredentialsError):
            mock_client._get_aws_auth()


class TestHTTPErrorScenarios:
    """Test HTTP error handling scenarios."""

    @pytest.fixture
    def mock_client_with_auth(self):
        """Create a mock client with auth setup."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            client.session = Mock()
            client.region = 'us-east-1'

            # Mock credentials
            mock_credentials = Mock()
            client.session.get_credentials.return_value = mock_credentials
            return client

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_search_resources_http_timeout(self, mock_httpx, mock_client_with_auth):
        """Test search resources with HTTP timeout."""
        import httpx

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException('Request timeout')
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(Exception, match='Request timeout'):
            await mock_client_with_auth.search_resources(
                '12345678901234567890123456789012', 'Patient', {'name': 'Smith'}
            )

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_search_resources_http_400_error(self, mock_httpx, mock_client_with_auth):
        """Test search resources with HTTP 400 error."""
        import httpx

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            '400 Bad Request', request=Mock(), response=Mock()
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(Exception) as exc_info:
            await mock_client_with_auth.search_resources(
                '12345678901234567890123456789012', 'Patient', {'name': 'Smith'}
            )

        # Should create helpful error message
        error_message = str(exc_info.value)
        assert 'HealthLake rejected the search request' in error_message or '400' in error_message

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_patient_everything_connection_error(self, mock_httpx, mock_client_with_auth):
        """Test patient everything with connection error."""
        import httpx

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.ConnectError('Connection failed')
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(Exception, match='Connection failed'):
            await mock_client_with_auth.patient_everything(
                '12345678901234567890123456789012', 'patient-123'
            )

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient')
    async def test_create_resource_json_decode_error(self, mock_httpx, mock_client_with_auth):
        """Test create resource with JSON decode error."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError('Invalid JSON')

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(Exception, match='Invalid JSON'):
            await mock_client_with_auth.create_resource(
                '12345678901234567890123456789012', 'Patient', {'resourceType': 'Patient'}
            )


class TestBundleProcessingEdgeCases:
    """Test bundle processing edge cases."""

    def test_process_bundle_with_includes_complex(self):
        """Test bundle processing with complex includes structure."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        bundle = {
            'resourceType': 'Bundle',
            'entry': [
                {
                    'resource': {'resourceType': 'Patient', 'id': 'patient-1'},
                    'search': {'mode': 'match'},
                },
                {
                    'resource': {'resourceType': 'Practitioner', 'id': 'practitioner-1'},
                    'search': {'mode': 'include'},
                },
                {
                    'resource': {'resourceType': 'Observation', 'id': 'obs-1'},
                    'search': {'mode': 'include'},
                },
            ],
            'link': [],
        }

        result = client._process_bundle_with_includes(bundle)

        assert len(result['entry']) == 1  # Only match entries
        assert result['entry'][0]['resource']['id'] == 'patient-1'

        # Check included resources are organized by type
        assert 'included' in result
        assert 'Practitioner' in result['included']
        assert 'Observation' in result['included']
        assert 'practitioner-1' in result['included']['Practitioner']
        assert 'obs-1' in result['included']['Observation']

    def test_process_bundle_malformed_pagination_url(self):
        """Test bundle processing with malformed pagination URL."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        bundle = {
            'resourceType': 'Bundle',
            'entry': [],
            'link': [{'relation': 'next', 'url': 'malformed-url-without-proper-encoding'}],
        }

        result = client._process_bundle(bundle)

        # Should handle malformed URL gracefully
        assert result['pagination']['has_next'] is True
        assert result['pagination']['next_token'] == 'malformed-url-without-proper-encoding'

    def test_build_search_request_list_values(self):
        """Test search request building with list values."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Patient',
            search_params={'name': ['Smith', 'Johnson'], 'gender': 'male'},
            count=50,
        )

        assert form_data['name'] == 'Smith,Johnson'
        assert form_data['gender'] == 'male'


class TestFHIRSearchAdvanced:
    """Test advanced FHIR search functionality for missing coverage."""

    def test_search_with_chained_params(self):
        """Test search with chained parameters."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        url, form_data = client._build_search_request(
            base_url='https://healthlake.us-east-1.amazonaws.com/datastore/test/r4/',
            resource_type='Observation',
            chained_params={
                'subject:Patient.name': 'Smith',
                'performer:Practitioner.name': 'Johnson',
            },
            count=50,
        )

        # Should encode colons in parameter names
        assert 'subject%3APatient.name' in form_data
        assert 'performer%3APractitioner.name' in form_data
        assert form_data['subject%3APatient.name'] == 'Smith'
        assert form_data['performer%3APractitioner.name'] == 'Johnson'


class TestFHIRErrorHandling:
    """Test FHIR error handling for missing coverage."""

    def test_pagination_error_handling(self):
        """Test pagination error handling."""
        client = HealthLakeClient.__new__(HealthLakeClient)

        # Test with malformed next URL that causes exception during processing
        bundle = {
            'resourceType': 'Bundle',
            'entry': [{'resource': {'resourceType': 'Patient', 'id': '1'}}],
            'link': [{'relation': 'next', 'url': 'https://example.com/next?param=value'}],
        }

        # This should process without error and extract the next token
        result = client._process_bundle(bundle)
        assert result['pagination']['has_next'] is True
        assert 'next' in result['pagination']['next_token']


class TestAWSAuthErrors:
    """Test AWS authentication error handling for missing coverage."""

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_client_initialization_with_no_credentials(self, mock_session):
        """Test client initialization when no credentials are available."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        # This should succeed - credentials are checked later during auth
        client = HealthLakeClient()
        assert client is not None


class TestBundleProcessingExtended:
    """Extended bundle processing tests for coverage."""

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_process_bundle_url_parsing_error(self, mock_session):
        """Test URL parsing exception handling (coverage: lines 281-283)."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        # Bundle with malformed URL that causes parsing error
        bundle = {
            'resourceType': 'Bundle',
            'entry': [],
            'link': [{'relation': 'next', 'url': 'malformed://url[{invalid}'}],
        }

        result = client._process_bundle(bundle)

        # Should handle error gracefully and still return pagination
        assert 'pagination' in result
        assert result['pagination']['has_next'] is True


class TestJobOperationErrorHandling:
    """Test job operation error scenarios for coverage."""

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    async def test_start_import_job_validation_exception(self, mock_session):
        """Test import job ValidationException handling (coverage: lines 615-630)."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid S3 URI'}}

        with patch.object(client, 'healthlake_client') as mock_client:
            mock_client.start_fhir_import_job.side_effect = ClientError(
                error_response, 'StartFHIRImportJob'
            )

            with pytest.raises(ValueError, match='Invalid parameters'):
                await client.start_import_job(
                    datastore_id='test',
                    input_data_config={'s3_uri': 's3://test'},
                    job_output_data_config={'s3_configuration': {'s3_uri': 's3://test'}},
                    data_access_role_arn='arn:test',
                )

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    async def test_start_import_job_access_denied(self, mock_session):
        """Test import job AccessDeniedException handling."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}

        with patch.object(client, 'healthlake_client') as mock_client:
            mock_client.start_fhir_import_job.side_effect = ClientError(
                error_response, 'StartFHIRImportJob'
            )

            with pytest.raises(PermissionError, match='Access denied'):
                await client.start_import_job(
                    datastore_id='test',
                    input_data_config={'s3_uri': 's3://test'},
                    job_output_data_config={'s3_configuration': {'s3_uri': 's3://test'}},
                    data_access_role_arn='arn:test',
                )

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    async def test_start_import_job_resource_not_found(self, mock_session):
        """Test import job ResourceNotFoundException handling."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}}

        with patch.object(client, 'healthlake_client') as mock_client:
            mock_client.start_fhir_import_job.side_effect = ClientError(
                error_response, 'StartFHIRImportJob'
            )

            with pytest.raises(ValueError, match='Datastore not found'):
                await client.start_import_job(
                    datastore_id='test',
                    input_data_config={'s3_uri': 's3://test'},
                    job_output_data_config={'s3_configuration': {'s3_uri': 's3://test'}},
                    data_access_role_arn='arn:test',
                )

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    async def test_list_jobs_client_error(self, mock_session):
        """Test list_jobs error handling (coverage: lines 661-669, 683-686)."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        with patch.object(client, 'healthlake_client') as mock_client:
            mock_client.list_fhir_import_jobs.side_effect = ClientError({}, 'ListFHIRImportJobs')
            mock_client.list_fhir_export_jobs.side_effect = ClientError({}, 'ListFHIRExportJobs')

            result = await client.list_jobs('test')

            assert result['error'] is True
            assert 'ImportJobs' in result
            assert 'ExportJobs' in result


class TestFHIRSearchValidationExtended:
    """Extended FHIR search validation tests."""

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_validate_search_request_empty_resource_type(self, mock_session):
        """Test validation with empty resource type."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        errors = client._validate_search_request(resource_type='', count=50)

        assert 'Resource type is required' in errors

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_validate_search_request_invalid_include_format(self, mock_session):
        """Test validation with invalid include format."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        errors = client._validate_search_request(
            resource_type='Patient', include_params=['invalid_format'], count=50
        )

        assert any('Invalid include format' in error for error in errors)

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_validate_search_request_invalid_revinclude_format(self, mock_session):
        """Test validation with invalid revinclude format."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()

        errors = client._validate_search_request(
            resource_type='Patient', revinclude_params=['invalid_format'], count=50
        )

        assert any('Invalid revinclude format' in error for error in errors)


class TestAWSAuthExtended:
    """Extended AWS auth tests for coverage."""

    def test_get_aws_auth_no_credentials_error(self):
        """Test auth setup with no credentials (coverage: lines 330-332)."""
        with patch('boto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get_credentials.return_value = None
            mock_session_class.return_value = mock_session

            client = HealthLakeClient()

            with pytest.raises(NoCredentialsError):
                client._get_aws_auth()
