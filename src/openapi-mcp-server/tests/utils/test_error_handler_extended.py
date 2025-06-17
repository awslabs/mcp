# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Extended tests for error handling utilities."""

import httpx
import json
import pytest
import time
from awslabs.openapi_mcp_server.utils.error_handler import (
    APIError,
    AuthenticationError,
    ConnectionError,
    NetworkError,
    extract_error_details,
    format_error_message,
    handle_http_error,
    handle_request_error,
    safe_request,
)
from unittest.mock import AsyncMock, MagicMock, patch


# Original JWT tokens for testing - these are needed for proper JWT decoding
ORIGINAL_JWT_TOKEN_WITH_EXP = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
ORIGINAL_JWT_TOKEN_WITH_IAT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'


class TestAPIError:
    """Tests for APIError class."""

    def test_init(self):
        """Test initialization."""
        error = APIError(400, 'Bad request', {'field': 'value'}, Exception('Original error'))
        assert error.status_code == 400
        assert error.message == 'Bad request'
        assert error.details == {'field': 'value'}
        assert isinstance(error.original_error, Exception)

    def test_str(self):
        """Test string representation."""
        error = APIError(400, 'Bad request', {'field': 'value'})
        assert str(error) == '400: Bad request'

    def test_repr(self):
        """Test representation."""
        error = APIError(400, 'Bad request', {'field': 'value'})
        assert repr(error) == "APIError(400, 'Bad request', {'field': 'value'})"


class TestExtractErrorDetails:
    """Tests for extract_error_details function."""

    def test_extract_json_details(self):
        """Test extraction of JSON error details."""
        # Create a mock response with JSON content
        response = MagicMock()
        response.headers = {'content-type': 'application/json'}
        response.json.return_value = {'error': 'Invalid request', 'code': 400}

        details = extract_error_details(response)
        assert details == {'error': 'Invalid request', 'code': 400}

    def test_extract_text_details(self):
        """Test extraction of text error details."""
        # Create a mock response with text content
        response = MagicMock()
        response.headers = {'content-type': 'text/plain'}
        response.text = 'Error: Invalid request'

        details = extract_error_details(response)
        assert details == {'message': 'Error: Invalid request'}

    def test_extract_json_decode_error(self):
        """Test extraction with JSON decode error."""
        # Create a mock response with invalid JSON content
        response = MagicMock()
        response.headers = {'content-type': 'application/json'}
        response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        response.text = 'Invalid JSON'

        details = extract_error_details(response)
        assert details == {'message': 'Invalid JSON'}

    def test_extract_large_text(self):
        """Test extraction with large text content."""
        # Create a mock response with large text content
        response = MagicMock()
        response.headers = {'content-type': 'text/plain'}
        response.text = 'x' * 2000  # More than 1000 characters

        details = extract_error_details(response)
        assert 'message' in details
        assert len(details['message']) > 0


class TestFormatErrorMessage:
    """Tests for format_error_message function."""

    def test_format_common_error(self):
        """Test formatting of common error message."""
        message = format_error_message(400, 'Bad Request', {})
        assert '400 Bad Request' in message

    def test_format_auth_error(self):
        """Test formatting of authentication error message."""
        message = format_error_message(401, 'Unauthorized', {})
        assert '401 Unauthorized' in message
        assert 'TROUBLESHOOTING: Authentication error' in message

    def test_format_auth_error_with_details(self):
        """Test formatting of authentication error message with details."""
        message = format_error_message(401, 'Unauthorized', {'message': 'Invalid token'})
        assert '401 Unauthorized: Invalid token' in message
        assert 'TROUBLESHOOTING: Authentication error' in message

    def test_format_auth_error_with_nested_details(self):
        """Test formatting of authentication error message with nested details."""
        message = format_error_message(401, 'Unauthorized', {'error': {'message': 'Invalid token'}})
        assert '401 Unauthorized: Invalid token' in message
        assert 'TROUBLESHOOTING: Authentication error' in message

    def test_format_unknown_error(self):
        """Test formatting of unknown error message."""
        message = format_error_message(499, 'Unknown', {})
        assert '499 Unknown' in message


class TestHandleHttpError:
    """Tests for handle_http_error function."""

    def test_handle_auth_error(self):
        """Test handling of authentication error."""
        # Create a mock request with authorization header
        request = MagicMock()
        request.headers = {'Authorization': f'Bearer {ORIGINAL_JWT_TOKEN_WITH_IAT}'}

        # Create a mock response
        response = MagicMock()
        response.status_code = 401
        response.reason_phrase = 'Unauthorized'
        response.headers = {'content-type': 'application/json'}
        response.json.return_value = {'message': 'Invalid token'}

        # Create a mock error
        error = httpx.HTTPStatusError('HTTP error', request=request, response=response)

        # Handle the error
        with patch('awslabs.openapi_mcp_server.utils.error_handler.logger'):
            api_error = handle_http_error(error)

            # Check the result
            assert isinstance(api_error, AuthenticationError)
            assert api_error.status_code == 401
            assert 'Invalid token' in api_error.message
            assert 'TROUBLESHOOTING: Authentication error' in api_error.message

    def test_handle_auth_error_with_jwt_decode(self):
        """Test handling of authentication error with JWT decode."""
        # Create a mock request with authorization header
        request = MagicMock()
        request.headers = {'Authorization': f'Bearer {ORIGINAL_JWT_TOKEN_WITH_EXP}'}

        # Create a mock response
        response = MagicMock()
        response.status_code = 401
        response.reason_phrase = 'Unauthorized'
        response.headers = {'content-type': 'application/json'}
        response.json.return_value = {'message': 'Token expired'}

        # Create a mock error
        error = httpx.HTTPStatusError('HTTP error', request=request, response=response)

        # Handle the error
        with patch('awslabs.openapi_mcp_server.utils.error_handler.logger'):
            # Import base64 directly in the test
            with patch('json.loads') as mock_json_loads:
                # Mock the json.loads to return a payload with exp
                mock_json_loads.return_value = {
                    'exp': int(time.time()) - 3600
                }  # Expired 1 hour ago

                api_error = handle_http_error(error)

                # Check the result
                assert isinstance(api_error, AuthenticationError)
                assert api_error.status_code == 401
                assert 'Token expired' in api_error.message
                assert 'TROUBLESHOOTING: Authentication error' in api_error.message


class TestHandleRequestError:
    """Tests for handle_request_error function."""

    def test_handle_connect_timeout(self):
        """Test handling of connect timeout error."""
        # Create a mock error
        error = httpx.ConnectTimeout('Connection timed out')

        # Handle the error
        api_error = handle_request_error(error)

        # Check the result
        assert isinstance(api_error, ConnectionError)
        assert api_error.status_code == 500
        assert 'Connection timed out' in str(api_error)

    def test_handle_read_timeout(self):
        """Test handling of read timeout error."""
        # Create a mock error
        error = httpx.ReadTimeout('Read timed out')

        # Handle the error
        api_error = handle_request_error(error)

        # Check the result
        assert isinstance(api_error, ConnectionError)
        assert api_error.status_code == 500
        assert 'Read timed out' in str(api_error)

    def test_handle_connect_error(self):
        """Test handling of connect error."""
        # Create a mock error
        error = httpx.ConnectError('Could not connect to the server')

        # Handle the error
        api_error = handle_request_error(error)

        # Check the result
        assert isinstance(api_error, NetworkError)
        assert api_error.status_code == 500
        assert 'Could not connect to the server' in str(api_error)

    def test_handle_generic_error(self):
        """Test handling of generic request error."""
        # Create a mock error
        error = httpx.RequestError('Request error')

        # Handle the error
        api_error = handle_request_error(error)

        # Check the result
        assert isinstance(api_error, NetworkError)
        assert api_error.status_code == 500
        assert 'Request error' in str(api_error)


class TestSafeRequest:
    """Tests for safe_request function."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful request."""
        # Create a mock client
        client = AsyncMock()

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        client.request.return_value = mock_response

        # Make a request
        response = await safe_request(client, 'GET', 'https://example.com')

        # Check the result
        assert response == mock_response
        client.request.assert_called_once_with(method='GET', url='https://example.com')

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test request error."""
        # Create a mock client
        client = AsyncMock()

        # Create a mock request
        mock_request = MagicMock()

        # Create a mock error with request property
        error = httpx.ConnectError('Could not connect to the server')
        type(error).request = mock_request

        # Make the client raise the error
        client.request.side_effect = error

        # Make a request that will raise an error
        with pytest.raises(NetworkError) as excinfo:
            await safe_request(client, 'GET', 'https://example.com')

        # Check the error message
        assert 'Could not connect to the server' in str(excinfo.value)
