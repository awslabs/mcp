"""Tests to boost coverage for error_handler.py."""

import httpx
import pytest
from awslabs.openapi_mcp_server.utils.error_handler import (
    APIError,
)
from unittest.mock import MagicMock, patch


class TestErrorHandlerBoost:
    """Tests to boost coverage for error_handler.py."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = MagicMock()
        logger.error = MagicMock()
        logger.warning = MagicMock()
        logger.info = MagicMock()
        logger.debug = MagicMock()
        return logger

    def test_api_error_class(self):
        """Test APIError class."""
        # Test with minimal parameters
        error = APIError(500, 'Test error')
        assert error.status_code == 500
        assert error.message == 'Test error'
        assert error.details == {}
        assert error.original_error is None
        assert str(error) == '500: Test error'

        # Test with all parameters
        original_error = ValueError('Original error')
        details = {'field': 'username', 'reason': 'too short'}
        error = APIError(
            status_code=400,
            message='Validation error',
            details=details,
            original_error=original_error,
        )
        assert error.status_code == 400
        assert error.message == 'Validation error'
        assert error.details == details
        assert error.original_error == original_error
        assert str(error) == '400: Validation error'

    @patch('awslabs.openapi_mcp_server.utils.error_handler.logger')
    def test_api_error_with_httpx_error(self, mock_logger):
        """Test APIError with httpx error."""
        # Create a mock httpx.HTTPStatusError
        response = MagicMock()
        response.status_code = 404
        response.text = 'Not Found'

        http_error = httpx.HTTPStatusError(
            'Not Found',
            request=MagicMock(),
            response=response,
        )

        # Create APIError from httpx error
        error = APIError(
            status_code=404,
            message='API endpoint not found',
            details={'url': '/api/test'},
            original_error=http_error,
        )

        # Verify error properties
        assert error.status_code == 404
        assert error.message == 'API endpoint not found'
        assert error.details == {'url': '/api/test'}
        assert error.original_error == http_error
        assert str(error) == '404: API endpoint not found'
