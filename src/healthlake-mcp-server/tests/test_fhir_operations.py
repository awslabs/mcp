"""Comprehensive tests for FHIR operations."""

import pytest
from awslabs.healthlake_mcp_server.fhir_operations import AWSAuth, HealthLakeClient
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


class TestHealthLakeClient:
    """Test HealthLakeClient initialization and basic functionality."""

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_client_initialization(self, mock_session):
        """Test client initialization."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        client = HealthLakeClient()
        assert client.session == mock_session_instance
        assert client.healthlake_client is not None

    @patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session')
    def test_get_aws_auth_success(self, mock_session):
        """Test successful AWS auth setup."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = Mock()

        mock_credentials = Mock()
        mock_credentials.access_key = 'test_key'
        mock_credentials.secret_key = 'test_secret'  # pragma: allowlist secret
        mock_credentials.token = None
        mock_session_instance.get_credentials.return_value = mock_credentials

        client = HealthLakeClient()
        auth = client._get_aws_auth()

        assert auth is not None
        assert isinstance(auth, AWSAuth)


class TestDatastoreOperations:
    """Test datastore-related operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_list_datastores_success(self, mock_client):
        """Test successful datastore listing."""
        expected_response = {'DatastorePropertiesList': [{'DatastoreId': 'test-id'}]}
        mock_client.healthlake_client.list_fhir_datastores.return_value = expected_response

        result = await mock_client.list_datastores()

        assert result == expected_response
        mock_client.healthlake_client.list_fhir_datastores.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_datastore_details_success(self, mock_client):
        """Test successful datastore details retrieval."""
        expected_response = {'DatastoreProperties': {'DatastoreId': 'test-id'}}
        mock_client.healthlake_client.describe_fhir_datastore.return_value = expected_response

        result = await mock_client.get_datastore_details('test-id')

        assert result == expected_response
        mock_client.healthlake_client.describe_fhir_datastore.assert_called_once_with(
            DatastoreId='test-id'
        )


class TestResourceOperations:
    """Test FHIR resource CRUD operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_create_resource_success(self, mock_client):
        """Test successful resource creation."""
        expected_response = {'ResponseMetadata': {'HTTPStatusCode': 201}}

        with patch.object(mock_client, '_get_fhir_endpoint', return_value='https://test.endpoint'):
            with patch.object(mock_client, '_get_aws_auth', return_value=Mock()):
                with patch(
                    'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient'
                ) as mock_httpx:
                    mock_response = Mock()
                    mock_response.status_code = 201
                    mock_response.json.return_value = expected_response
                    mock_httpx.return_value.__aenter__.return_value.post.return_value = (
                        mock_response
                    )

                    result = await mock_client.create_resource(
                        'test-datastore', 'Patient', {'resourceType': 'Patient'}
                    )

                    assert result == expected_response

    @pytest.mark.asyncio
    async def test_read_resource_success(self, mock_client):
        """Test successful resource reading."""
        expected_response = {'resourceType': 'Patient', 'id': 'test-id'}

        with patch.object(mock_client, '_get_fhir_endpoint', return_value='https://test.endpoint'):
            with patch.object(mock_client, '_get_aws_auth', return_value=Mock()):
                with patch(
                    'awslabs.healthlake_mcp_server.fhir_operations.httpx.AsyncClient'
                ) as mock_httpx:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = expected_response
                    mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                        mock_response
                    )

                    result = await mock_client.read_resource(
                        'test-datastore', 'Patient', 'test-id'
                    )

                    assert result == expected_response


class TestSearchOperations:
    """Test FHIR search operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_search_validation_empty_resource_type(self, mock_client):
        """Test search validation with empty resource type."""
        validation_errors = mock_client._validate_search_request(
            resource_type='',
            search_params={},
            include_params=None,
            revinclude_params=None,
            chained_params=None,
            count=100,
        )

        assert len(validation_errors) > 0
        assert 'Resource type is required' in validation_errors

    @pytest.mark.asyncio
    async def test_search_validation_invalid_count(self, mock_client):
        """Test search validation with invalid count."""
        # Test count too low
        validation_errors = mock_client._validate_search_request(
            resource_type='Patient',
            search_params={},
            include_params=None,
            revinclude_params=None,
            chained_params=None,
            count=0,
        )

        assert len(validation_errors) > 0
        assert any('Count must be between 1 and 100' in error for error in validation_errors)


class TestJobOperations:
    """Test FHIR import/export job operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_start_import_job_success(self, mock_client):
        """Test successful import job start."""
        expected_response = {'JobId': 'job-123', 'JobStatus': 'SUBMITTED'}
        mock_client.healthlake_client.start_fhir_import_job.return_value = expected_response

        result = await mock_client.start_import_job(
            datastore_id='12345678901234567890123456789012',
            input_data_config={'s3_uri': 's3://bucket/input'},
            job_output_data_config={'s3_configuration': {'s3_uri': 's3://bucket/output'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )

        assert result == expected_response

    @pytest.mark.asyncio
    async def test_start_export_job_success(self, mock_client):
        """Test successful export job start."""
        expected_response = {'JobId': 'export-123', 'JobStatus': 'SUBMITTED'}
        mock_client.healthlake_client.start_fhir_export_job.return_value = expected_response

        result = await mock_client.start_export_job(
            datastore_id='12345678901234567890123456789012',
            output_data_config={'S3Configuration': {'S3Uri': 's3://bucket/export'}},
            data_access_role_arn='arn:aws:iam::123456789012:role/HealthLakeRole',
        )

        assert result == expected_response

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


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HealthLake client for testing."""
        with patch('awslabs.healthlake_mcp_server.fhir_operations.boto3.Session'):
            client = HealthLakeClient()
            client.healthlake_client = Mock()
            return client

    @pytest.mark.asyncio
    async def test_client_error_handling(self, mock_client):
        """Test ClientError handling."""
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_client.healthlake_client.describe_fhir_datastore.side_effect = ClientError(
            error_response, 'DescribeFHIRDatastore'
        )

        with pytest.raises(ClientError):
            await mock_client.get_datastore_details('nonexistent-id')

    @pytest.mark.asyncio
    async def test_list_jobs_error_handling(self, mock_client):
        """Test list_jobs error handling."""
        mock_client.healthlake_client.list_fhir_import_jobs.side_effect = ClientError(
            {}, 'ListFHIRImportJobs'
        )
        mock_client.healthlake_client.list_fhir_export_jobs.side_effect = ClientError(
            {}, 'ListFHIRExportJobs'
        )

        result = await mock_client.list_jobs('test')

        assert result['error'] is True
        assert 'ImportJobs' in result
        assert 'ExportJobs' in result


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
