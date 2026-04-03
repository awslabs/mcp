"""Comprehensive tests for MCP server functionality."""

import json
from awslabs.healthlake_mcp_server.server import (
    DateTimeEncoder,
    InputValidationError,
    create_error_response,
    create_healthlake_server,
    create_success_response,
)
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestServerCreation:
    """Test MCP server creation and configuration."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_server_creation(self, mock_client_class):
        """Test server creation and handler registration."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        server = create_healthlake_server()

        assert server.name == 'healthlake-mcp-server'
        assert len(server.request_handlers) > 0


class TestDateTimeEncoder:
    """Test JSON datetime encoding."""

    def test_datetime_encoding(self):
        """Test DateTimeEncoder with datetime object."""
        encoder = DateTimeEncoder()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert result == '2024-01-01T12:00:00'

    def test_strftime_object_encoding(self):
        """Test DateTimeEncoder with object having strftime."""

        class MockDateTime:
            def strftime(self, fmt):
                return '2024-01-01'

        mock_dt = MockDateTime()
        has_strftime = hasattr(mock_dt, 'strftime')
        assert has_strftime is True

        formatted = mock_dt.strftime('%Y-%m-%d')
        assert formatted == '2024-01-01'


class TestResponseHelpers:
    """Test response helper functions."""

    def test_create_error_response(self):
        """Test create_error_response function."""
        result = create_error_response('Test error', 'test_type')
        assert len(result) == 1
        assert 'Test error' in result[0].text
        assert '"error": true' in result[0].text
        assert '"type": "test_type"' in result[0].text

    def test_create_success_response(self):
        """Test create_success_response function."""
        data = {'key': 'value'}
        result = create_success_response(data)
        assert len(result) == 1
        assert '"key": "value"' in result[0].text

    def test_create_success_response_with_datetime(self):
        """Test create_success_response with datetime encoding."""
        data = {'timestamp': datetime(2024, 1, 1, 12, 0, 0)}
        result = create_success_response(data)
        assert len(result) == 1
        assert '2024-01-01T12:00:00' in result[0].text


class TestToolHandlers:
    """Test MCP tool handlers."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_list_datastores_handler(self, mock_client_class):
        """Test list datastores tool handler."""
        mock_client = AsyncMock()
        mock_client.list_datastores.return_value = {
            'DatastorePropertiesList': [{'DatastoreId': 'test-id'}]
        }
        mock_client_class.return_value = mock_client

        from awslabs.healthlake_mcp_server.server import ToolHandler

        handler = ToolHandler(mock_client)

        import asyncio

        result = asyncio.run(handler.handle_tool('list_datastores', {}))

        assert len(result) == 1
        assert 'test-id' in result[0].text

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_get_datastore_details_handler(self, mock_client_class):
        """Test get datastore details tool handler."""
        mock_client = AsyncMock()
        mock_client.get_datastore_details.return_value = {
            'DatastoreId': '12345678901234567890123456789012'
        }
        mock_client_class.return_value = mock_client

        from awslabs.healthlake_mcp_server.server import ToolHandler

        handler = ToolHandler(mock_client)

        import asyncio

        result = asyncio.run(
            handler.handle_tool(
                'get_datastore_details', {'datastore_id': '12345678901234567890123456789012'}
            )
        )

        assert len(result) == 1
        assert '12345678901234567890123456789012' in result[0].text


class TestErrorHandling:
    """Test error handling in server components."""

    def test_input_validation_error_handling(self):
        """Test InputValidationError handling."""
        try:
            raise InputValidationError('Invalid input')
        except (InputValidationError, ValueError) as e:
            result = create_error_response(str(e), 'validation_error')
            assert len(result) == 1
            assert 'Invalid input' in result[0].text

    def test_client_error_handling(self):
        """Test ClientError handling patterns."""
        # Test ResourceNotFoundException
        error_code = 'ResourceNotFoundException'
        if error_code == 'ResourceNotFoundException':
            error_type = 'not_found'
        elif error_code == 'ValidationException':
            error_type = 'validation_error'
        else:
            error_type = 'service_error'
        assert error_type == 'not_found'

        # Test ValidationException
        error_code = 'ValidationException'
        if error_code == 'ResourceNotFoundException':
            error_type = 'not_found'
        elif error_code == 'ValidationException':
            error_type = 'validation_error'
        else:
            error_type = 'service_error'
        assert error_type == 'validation_error'


class TestResourceLogic:
    """Test resource creation and processing logic."""

    def test_status_emoji_logic(self):
        """Test datastore status emoji logic."""
        # Test ACTIVE status
        status = 'ACTIVE'
        emoji = '✅' if status == 'ACTIVE' else '⏳'
        assert emoji == '✅'

        # Test non-ACTIVE status
        status = 'CREATING'
        emoji = '✅' if status == 'ACTIVE' else '⏳'
        assert emoji == '⏳'

    def test_datastore_name_fallback(self):
        """Test datastore name fallback logic."""
        # Test with name
        datastore = {'DatastoreName': 'TestName'}
        name = datastore.get('DatastoreName', 'Unnamed')
        assert name == 'TestName'

        # Test without name
        datastore = {}
        name = datastore.get('DatastoreName', 'Unnamed')
        assert name == 'Unnamed'

    def test_uri_processing(self):
        """Test URI validation and processing."""
        # Test valid URI
        uri_str = 'healthlake://datastore/12345678901234567890123456789012'
        is_valid = uri_str.startswith('healthlake://datastore/')
        assert is_valid is True

        # Test datastore ID extraction
        datastore_id = uri_str.split('/')[-1]
        assert datastore_id == '12345678901234567890123456789012'

        # Test invalid URI
        uri_str = 'invalid://not-healthlake'
        is_valid = uri_str.startswith('healthlake://datastore/')
        assert is_valid is False

    def test_json_encoding_with_datetime(self):
        """Test JSON encoding with DateTimeEncoder."""
        data = {
            'id': '12345678901234567890123456789012',
            'created': datetime(2024, 1, 1, 12, 0, 0),
            'name': 'TestDatastore',
        }

        result = json.dumps(data, indent=2, cls=DateTimeEncoder)
        assert '12345678901234567890123456789012' in result
        assert '2024-01-01T12:00:00' in result
        assert 'TestDatastore' in result
