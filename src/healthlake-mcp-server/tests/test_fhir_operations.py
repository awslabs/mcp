"""Tests for FHIR operations - critical coverage."""

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
