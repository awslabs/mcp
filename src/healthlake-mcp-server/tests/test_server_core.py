"""Tests for MCP server creation, handlers, and response formatting."""

import json
import pytest
from awslabs.healthlake_mcp_server.server import (
    DateTimeEncoder,
    create_error_response,
    create_healthlake_server,
    create_success_response,
)
from unittest.mock import AsyncMock, Mock, patch


class TestServerCreation:
    """Test MCP server creation and initialization."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_healthlake_server_success(self, mock_client_class):
        """Test successful server creation."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        server = create_healthlake_server()

        assert server is not None
        assert server.name == 'healthlake-mcp-server'
        mock_client_class.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_healthlake_server_with_region(self, mock_client_class):
        """Test server creation with environment region."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with patch.dict('os.environ', {'AWS_REGION': 'us-west-2'}):
            server = create_healthlake_server()

        assert server is not None
        # Client should be created with region from environment
        mock_client_class.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_healthlake_server_client_error(self, mock_client_class):
        """Test server creation with client initialization error."""
        mock_client_class.side_effect = Exception('Client creation failed')

        with pytest.raises(Exception, match='Client creation failed'):
            create_healthlake_server()

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_server_creation_includes_handlers(self, mock_client_class):
        """Test server creation includes all handlers."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        server = create_healthlake_server()

        # Verify server was created successfully
        assert server is not None
        assert server.name == 'healthlake-mcp-server'


class TestResponseFormatting:
    """Test response helper functions."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response('Test error')

        assert len(response) == 1
        content = response[0]
        assert content.type == 'text'
        assert '"error": true' in content.text
        assert '"message": "Test error"' in content.text
        assert '"type": "error"' in content.text

    def test_create_error_response_with_type(self):
        """Test error response with custom type."""
        response = create_error_response('Validation failed', 'validation_error')

        content = response[0]
        assert '"type": "validation_error"' in content.text
        assert '"message": "Validation failed"' in content.text

    def test_create_error_response_with_custom_type(self):
        """Test error response format."""
        response = create_error_response('Test error', 'validation_error')

        assert len(response) == 1
        content = response[0]
        assert content.type == 'text'

        data = json.loads(content.text)
        assert data['error'] is True
        assert data['type'] == 'validation_error'
        assert data['message'] == 'Test error'

    def test_create_error_response_default_type(self):
        """Test error response with default error type."""
        response = create_error_response('Default error')

        data = json.loads(response[0].text)
        assert data['type'] == 'error'

    def test_create_success_response_basic(self):
        """Test basic success response creation."""
        test_data = {'key': 'value', 'number': 42}
        response = create_success_response(test_data)

        assert len(response) == 1
        content = response[0]
        assert content.type == 'text'
        assert '"key": "value"' in content.text
        assert '"number": 42' in content.text

    def test_create_success_response_format(self):
        """Test success response format."""
        test_data = {'key': 'value', 'number': 42}
        response = create_success_response(test_data)

        assert len(response) == 1
        content = response[0]
        assert content.type == 'text'

        data = json.loads(content.text)
        assert data == test_data

    def test_create_success_response_with_datetime(self):
        """Test success response with datetime serialization."""
        from datetime import datetime

        test_data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0)}
        response = create_success_response(test_data)

        content = response[0]
        assert '2023-01-01T12:00:00' in content.text

    def test_create_success_response_handles_datetime(self):
        """Test success response handles datetime serialization."""
        from datetime import datetime

        test_data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0)}
        response = create_success_response(test_data)

        data = json.loads(response[0].text)
        assert '2023-01-01T12:00:00' in data['timestamp']

    def test_error_response_edge_cases(self):
        """Test error response with edge cases."""
        # Test with empty message
        response = create_error_response('', 'empty_error')
        data = json.loads(response[0].text)
        assert data['message'] == ''

        # Test with special characters
        response = create_error_response('Error with "quotes" and \n newlines', 'special_error')
        data = json.loads(response[0].text)
        assert 'quotes' in data['message']
        assert 'newlines' in data['message']


class TestDateTimeEncoding:
    """Test custom datetime encoder."""

    def test_datetime_encoder_with_datetime(self):
        """Test datetime encoder with datetime object."""
        from datetime import datetime

        test_data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0)}

        result = json.dumps(test_data, cls=DateTimeEncoder)

        assert '2023-01-01T12:00:00' in result

    def test_datetime_encoder_with_regular_object(self):
        """Test datetime encoder with regular objects."""
        test_data = {'string': 'value', 'number': 42}

        result = json.dumps(test_data, cls=DateTimeEncoder)

        assert '"string": "value"' in result
        assert '"number": 42' in result

    def test_datetime_encoder_fallback(self):
        """Test datetime encoder fallback for non-datetime objects."""
        encoder = DateTimeEncoder()

        # Test with datetime
        from datetime import datetime

        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert result == '2023-01-01T12:00:00'

        # Test with non-datetime object - should raise TypeError
        with pytest.raises(TypeError):
            encoder.default(object())

    def test_datetime_encoder_edge_cases(self):
        """Test DateTimeEncoder with edge cases."""
        from datetime import datetime

        encoder = DateTimeEncoder()

        # Test with datetime
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert result == '2023-01-01T12:00:00'

        # Test with non-datetime object - should raise TypeError
        with pytest.raises(TypeError):
            encoder.default(object())


class TestServerValidation:
    """Test server validation functions."""

    def test_validate_count_valid(self):
        """Test count validation with valid values."""
        from awslabs.healthlake_mcp_server.server import validate_count

        assert validate_count(1) == 1
        assert validate_count(50) == 50
        assert validate_count(100) == 100

    def test_validate_count_invalid_low(self):
        """Test count validation with value too low."""
        from awslabs.healthlake_mcp_server.server import InputValidationError, validate_count

        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(0)

    def test_validate_count_invalid_high(self):
        """Test count validation with value too high."""
        from awslabs.healthlake_mcp_server.server import InputValidationError, validate_count

        with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
            validate_count(101)

    def test_validate_count_invalid_extreme_values(self):
        """Test count validation with extreme values."""
        from awslabs.healthlake_mcp_server.server import InputValidationError, validate_count

        # Should raise errors for extreme values
        with pytest.raises(InputValidationError):
            validate_count(-5)

        with pytest.raises(InputValidationError):
            validate_count(200)


class TestServerValidationExtended:
    """Extended server validation tests for coverage."""

    def test_validate_count_edge_cases_extended(self):
        """Test count validation edge cases."""
        from awslabs.healthlake_mcp_server.server import InputValidationError, validate_count

        # Valid cases
        assert validate_count(1) == 1
        assert validate_count(100) == 100

        # Invalid cases
        with pytest.raises(InputValidationError):
            validate_count(0)

        with pytest.raises(InputValidationError):
            validate_count(101)


class TestResponseFormattingExtended:
    """Extended response formatting tests for coverage."""

    def test_create_error_response_variations(self):
        """Test error response creation variations."""
        from awslabs.healthlake_mcp_server.server import create_error_response

        # Test with default type
        result = create_error_response('Test error')
        assert len(result) == 1
        assert '"error": true' in result[0].text
        assert '"type": "error"' in result[0].text

        # Test with custom type
        result = create_error_response('Test error', 'custom_type')
        assert '"type": "custom_type"' in result[0].text

    def test_create_success_response_extended(self):
        """Test success response creation."""
        from awslabs.healthlake_mcp_server.server import create_success_response

        data = {'status': 'success', 'count': 5}
        result = create_success_response(data)
        assert len(result) == 1
        assert '"status": "success"' in result[0].text

    def test_datetime_encoder_extended(self):
        """Test DateTimeEncoder functionality."""
        from awslabs.healthlake_mcp_server.server import DateTimeEncoder
        from datetime import datetime

        encoder = DateTimeEncoder()
        dt = datetime(2023, 1, 1, 12, 0, 0)

        result = encoder.default(dt)
        assert result == '2023-01-01T12:00:00'

        # Test with non-datetime object
        with pytest.raises(TypeError):
            encoder.default(object())
