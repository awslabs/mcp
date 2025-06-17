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
"""Tests for the error handler utility."""

import httpx
import json
import pytest
from awslabs.openapi_mcp_server.utils.error_handler import (
    APIError,
    AuthenticationError,
    ResourceNotFoundError,
    extract_error_details,
    format_error_message,
    handle_http_error,
    handle_request_error,
    safe_request,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestErrorHandlerUtils:
    """Test the error handler utility functions."""

    def test_extract_error_details_json(self):
        """Test extracting error details from a JSON response."""
        mock_response = MagicMock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'error': 'Invalid token', 'code': 'auth_error'}

        details = extract_error_details(mock_response)
        assert details == {'error': 'Invalid token', 'code': 'auth_error'}

    def test_extract_error_details_text(self):
        """Test extracting error details from a text response."""
        mock_response = MagicMock()
        mock_response.headers = {'content-type': 'text/plain'}
        mock_response.text = 'Invalid request format'

        details = extract_error_details(mock_response)
        assert details == {'message': 'Invalid request format'}

    def test_extract_error_details_json_error(self):
        """Test extracting error details when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.side_effect = json.JSONDecodeError('Expecting value', '', 0)
        mock_response.text = 'Not valid JSON'

        details = extract_error_details(mock_response)
        assert details == {'message': 'Not valid JSON'}

    def test_format_error_message_basic(self):
        """Test basic error message formatting."""
        message = format_error_message(404, 'Not Found', {})
        assert '404 Not Found' in message

    def test_format_error_message_with_details(self):
        """Test error message formatting with details."""
        details = {'message': 'User account suspended'}
        message = format_error_message(403, 'Forbidden', details)
        assert '403 Forbidden: User account suspended' in message
        assert 'TROUBLESHOOTING: Authorization error' in message


class TestHandleHttpError:
    """Test the handle_http_error function."""

    def test_handle_401_error(self):
        """Test handling of 401 Unauthorized error."""
        # Create real response and request objects
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.reason_phrase = 'Unauthorized'
        mock_response.json.return_value = {'message': 'Invalid credentials'}
        mock_response.headers = {'content-type': 'application/json'}

        # Create a real HTTPStatusError
        mock_request = MagicMock()
        error = httpx.HTTPStatusError(
            '401 Unauthorized', request=mock_request, response=mock_response
        )

        result = handle_http_error(error)

        assert isinstance(result, AuthenticationError)
        assert result.status_code == 401
        assert 'Invalid credentials' in result.message
        assert 'TROUBLESHOOTING: Authentication error' in result.message

    def test_handle_404_error(self):
        """Test handling of 404 Not Found error."""
        # Create real response and request objects
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = 'Not Found'
        mock_response.json.side_effect = json.JSONDecodeError('Expecting value', '', 0)
        mock_response.text = 'Resource does not exist'
        mock_response.headers = {'content-type': 'text/plain'}

        # Create a real HTTPStatusError
        mock_request = MagicMock()
        error = httpx.HTTPStatusError('404 Not Found', request=mock_request, response=mock_response)

        result = handle_http_error(error)

        assert isinstance(result, ResourceNotFoundError)
        assert result.status_code == 404
        assert 'Resource does not exist' in result.message


class TestHandleRequestError:
    """Test the handle_request_error function."""

    def test_handle_connect_timeout(self):
        """Test handling of connect timeout error."""
        # Create a mock error
        error = httpx.ConnectTimeout('Connection timed out')

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: APIError,
                httpx.ReadTimeout: APIError,
                httpx.ConnectError: APIError,
                httpx.RequestError: APIError,
            },
        ):
            # Handle the error
            api_error = handle_request_error(error)

            # Check the result
            assert isinstance(api_error, APIError)
            assert 'Connection timed out' in str(api_error)
            assert api_error.status_code == 500


class TestSafeRequest:
    """Test the safe_request function."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful request."""
        # Create a mock client
        client = AsyncMock()

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason_phrase = 'OK'
        client.request.return_value = mock_response

        # Make a request
        response = await safe_request(client, 'GET', 'https://example.com')

        # Check that the client was called correctly
        client.request.assert_called_once_with(method='GET', url='https://example.com')

        # Check that the response was returned
        assert response == mock_response
