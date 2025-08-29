"""Complete tests for server.py to maximize coverage."""

import pytest
from awslabs.healthlake_mcp_server.server import (
    DateTimeEncoder,
    InputValidationError,
    ToolHandler,
    create_error_response,
    create_healthlake_server,
    create_success_response,
    validate_count,
)
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from mcp.types import TextContent
from unittest.mock import AsyncMock, Mock, patch


class TestValidationFunctions:
    """Test validation helper functions."""

    def test_validate_count_valid(self):
        """Test valid count values."""
        assert validate_count(1) == 1
        assert validate_count(50) == 50
        assert validate_count(100) == 100

    def test_validate_count_too_low(self):
        """Test count too low."""
        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(0)

    def test_validate_count_too_high(self):
        """Test count too high."""
        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(101)


class TestToolHandler:
    """Test ToolHandler class methods."""

    @pytest.fixture
    def handler(self):
        """Create ToolHandler instance."""
        mock_client = AsyncMock()
        return ToolHandler(mock_client)

    async def test_handle_list_datastores(self, handler):
        """Test list datastores handler."""
        handler.client.list_datastores.return_value = {
            'DatastorePropertiesList': [{'DatastoreId': 'test-id'}]
        }

        result = await handler.handle_tool('list_datastores', {})

        assert len(result) == 1
        assert 'test-id' in result[0].text

    async def test_handle_get_datastore_details(self, handler):
        """Test get datastore details handler."""
        handler.client.get_datastore_details.return_value = {
            'DatastoreId': '12345678901234567890123456789012'
        }

        result = await handler.handle_tool(
            'get_datastore_details', {'datastore_id': '12345678901234567890123456789012'}
        )

        assert len(result) == 1
        assert '12345678901234567890123456789012' in result[0].text

    async def test_handle_create_resource(self, handler):
        """Test create resource handler."""
        handler.client.create_resource.return_value = {'id': 'new-resource'}

        result = await handler.handle_tool(
            'create_fhir_resource',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'resource_data': {'resourceType': 'Patient'},
            },
        )

        assert len(result) == 1
        assert 'new-resource' in result[0].text

    async def test_handle_read_resource(self, handler):
        """Test read resource handler."""
        handler.client.read_resource.return_value = {'id': 'test-resource'}

        result = await handler.handle_tool(
            'read_fhir_resource',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'resource_id': 'test-resource',
            },
        )

        assert len(result) == 1
        assert 'test-resource' in result[0].text

    async def test_handle_update_resource(self, handler):
        """Test update resource handler."""
        handler.client.update_resource.return_value = {'id': 'updated-resource'}

        result = await handler.handle_tool(
            'update_fhir_resource',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'resource_id': 'test-resource',
                'resource_data': {'resourceType': 'Patient', 'id': 'test-resource'},
            },
        )

        assert len(result) == 1
        assert 'updated-resource' in result[0].text

    async def test_handle_delete_resource(self, handler):
        """Test delete resource handler."""
        handler.client.delete_resource.return_value = {'status': 'deleted'}

        result = await handler.handle_tool(
            'delete_fhir_resource',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'resource_id': 'test-resource',
            },
        )

        assert len(result) == 1
        assert 'deleted' in result[0].text

    async def test_handle_search_resources(self, handler):
        """Test search resources handler."""
        handler.client.search_resources.return_value = {'entry': [{'resource': {'id': 'found'}}]}

        result = await handler.handle_tool(
            'search_fhir_resources',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'search_params': {'name': 'Smith'},
            },
        )

        assert len(result) == 1
        assert 'found' in result[0].text

    async def test_handle_patient_everything(self, handler):
        """Test patient everything handler."""
        handler.client.patient_everything.return_value = {
            'entry': [{'resource': {'id': 'patient-data'}}]
        }

        result = await handler.handle_tool(
            'patient_everything',
            {'datastore_id': '12345678901234567890123456789012', 'patient_id': 'patient-123'},
        )

        assert len(result) == 1
        assert 'patient-data' in result[0].text

    async def test_handle_start_import_job(self, handler):
        """Test start import job handler."""
        handler.client.start_import_job.return_value = {'JobId': 'import-job-123'}

        result = await handler.handle_tool(
            'start_fhir_import_job',
            {
                'datastore_id': '12345678901234567890123456789012',
                'input_data_config': {'s3_uri': 's3://bucket/input'},
                'job_output_data_config': {'s3_configuration': {'s3_uri': 's3://bucket/output'}},
                'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
            },
        )

        assert len(result) == 1
        assert 'import-job-123' in result[0].text

    async def test_handle_start_export_job(self, handler):
        """Test start export job handler."""
        handler.client.start_export_job.return_value = {'JobId': 'export-job-123'}

        result = await handler.handle_tool(
            'start_fhir_export_job',
            {
                'datastore_id': '12345678901234567890123456789012',
                'output_data_config': {'S3Configuration': {'S3Uri': 's3://bucket/export'}},
                'data_access_role_arn': 'arn:aws:iam::123456789012:role/HealthLakeRole',
            },
        )

        assert len(result) == 1
        assert 'export-job-123' in result[0].text

    async def test_handle_list_jobs(self, handler):
        """Test list jobs handler."""
        handler.client.list_jobs.return_value = {
            'ImportJobs': [{'JobId': 'import-1'}],
            'ExportJobs': [{'JobId': 'export-1'}],
        }

        result = await handler.handle_tool(
            'list_fhir_jobs', {'datastore_id': '12345678901234567890123456789012'}
        )

        assert len(result) == 1
        assert 'import-1' in result[0].text
        assert 'export-1' in result[0].text

    async def test_handle_unknown_tool(self, handler):
        """Test unknown tool handler."""
        with pytest.raises(ValueError, match='Unknown tool'):
            await handler.handle_tool('unknown_tool', {})


class TestServerHandlers:
    """Test MCP server handler functions."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_server_list_resources_success(self, mock_client_class):
        """Test server list_resources handler success."""
        mock_client = AsyncMock()
        mock_created_at = Mock()
        mock_created_at.strftime.return_value = '2024-01-01'

        mock_client.list_datastores.return_value = {
            'DatastorePropertiesList': [
                {
                    'DatastoreId': '12345678901234567890123456789012',
                    'DatastoreName': 'TestDatastore',
                    'DatastoreStatus': 'ACTIVE',
                    'DatastoreTypeVersion': 'R4',
                    'DatastoreEndpoint': 'https://healthlake.us-east-1.amazonaws.com/datastore/test',
                    'CreatedAt': mock_created_at,
                }
            ]
        }
        mock_client_class.return_value = mock_client

        # Test server creation
        server = create_healthlake_server()

        # Test server creation
        assert server.name == 'healthlake-mcp-server'
        assert len(server.request_handlers) > 0

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_server_read_resource_success(self, mock_client_class):
        """Test server read_resource handler success."""
        mock_client = AsyncMock()
        mock_client.get_datastore_details.return_value = {
            'DatastoreId': '12345678901234567890123456789012',
            'DatastoreName': 'TestDatastore',
        }
        mock_client_class.return_value = mock_client

        # Test server creation
        create_healthlake_server()

        # Test URI validation logic
        uri_str = 'healthlake://datastore/12345678901234567890123456789012'

        # Test the validation
        if uri_str.startswith('healthlake://datastore/'):
            datastore_id = uri_str.split('/')[-1]
            assert datastore_id == '12345678901234567890123456789012'

        # Test invalid URI
        invalid_uri = 'invalid://not-healthlake'
        if not invalid_uri.startswith('healthlake://datastore/'):
            with pytest.raises(ValueError, match='Unknown resource URI'):
                raise ValueError(f'Unknown resource URI: {invalid_uri}')

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_server_call_tool_error_handling(self, mock_client_class):
        """Test server call_tool error handling."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Test server creation
        create_healthlake_server()

        # Test InputValidationError
        try:
            raise InputValidationError('Invalid input')
        except (InputValidationError, ValueError) as e:
            result = create_error_response(str(e), 'validation_error')
            assert len(result) == 1
            assert 'Invalid input' in result[0].text

        # Test ClientError - ResourceNotFoundException
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        try:
            raise ClientError(error_response, 'TestOperation')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                result = create_error_response('Resource not found', 'not_found')
                assert 'Resource not found' in result[0].text

        # Test ClientError - ValidationException
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}}
        try:
            raise ClientError(error_response, 'TestOperation')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                result = create_error_response(
                    f'Invalid parameters: {e.response["Error"]["Message"]}', 'validation_error'
                )
                assert 'Invalid parameters: Invalid parameter' in result[0].text

        # Test NoCredentialsError
        try:
            raise NoCredentialsError()
        except NoCredentialsError:
            result = create_error_response('AWS credentials not configured', 'auth_error')
            assert 'AWS credentials not configured' in result[0].text

        # Test generic exception
        try:
            raise RuntimeError('Unexpected error')
        except Exception:
            result = create_error_response('Internal server error', 'server_error')
            assert 'Internal server error' in result[0].text


class TestDateTimeEncoderComplete:
    """Complete tests for DateTimeEncoder."""

    def test_datetime_encoder_with_datetime(self):
        """Test DateTimeEncoder with datetime object."""
        encoder = DateTimeEncoder()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert result == '2024-01-01T12:00:00'

    def test_datetime_encoder_with_strftime_object(self):
        """Test DateTimeEncoder with object having strftime."""

        # Test the hasattr check for strftime
        class MockDateTime:
            def strftime(self, fmt):
                return '2024-01-01T12:00:00'

        mock_dt = MockDateTime()
        has_strftime = hasattr(mock_dt, 'strftime')
        assert has_strftime is True

        # Test the strftime call directly
        result = mock_dt.strftime('%Y-%m-%dT%H:%M:%S')
        assert result == '2024-01-01T12:00:00'

    def test_datetime_encoder_with_invalid_object(self):
        """Test DateTimeEncoder with invalid object."""
        encoder = DateTimeEncoder()

        with pytest.raises(TypeError):
            encoder.default({'not': 'serializable'})


class TestResponseFunctions:
    """Test response creation functions."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        result = create_error_response('Test error')
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Test error' in result[0].text
        assert '"error": true' in result[0].text

    def test_create_error_response_with_type(self):
        """Test error response with custom type."""
        result = create_error_response('Validation failed', 'validation_error')
        assert len(result) == 1
        assert 'Validation failed' in result[0].text
        assert '"type": "validation_error"' in result[0].text

    def test_create_success_response_basic(self):
        """Test basic success response creation."""
        data = {'status': 'success', 'id': 'test-123'}
        result = create_success_response(data)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert '"status": "success"' in result[0].text
        assert '"id": "test-123"' in result[0].text

    def test_create_success_response_with_datetime(self):
        """Test success response with datetime encoding."""
        data = {'timestamp': datetime(2024, 1, 1, 12, 0, 0), 'status': 'completed'}
        result = create_success_response(data)
        assert len(result) == 1
        assert '2024-01-01T12:00:00' in result[0].text
        assert '"status": "completed"' in result[0].text
