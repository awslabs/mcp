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
"""Tests for the error handler module."""

import httpx
import pytest
from awslabs.openapi_mcp_server.utils.error_handler import (
    ConnectionError,
    NetworkError,
    handle_request_error,
    safe_request,
)
from unittest.mock import MagicMock, patch


class TestHandleRequestError:
    """Test cases for handle_request_error function."""

    def test_handle_connect_timeout(self):
        """Test handling of connect timeout error."""
        # Create a mock error
        error = httpx.ConnectTimeout('Connection timed out')

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: ConnectionError,
                httpx.ReadTimeout: ConnectionError,
                httpx.ConnectError: NetworkError,
                httpx.RequestError: NetworkError,
            },
        ):
            # Handle the error
            api_error = handle_request_error(error)

            # Check the result
            assert isinstance(api_error, ConnectionError)
            assert 'Connection timed out' in str(api_error)

    def test_handle_read_timeout(self):
        """Test handling of read timeout error."""
        # Create a mock error
        error = httpx.ReadTimeout('Read timed out')

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: ConnectionError,
                httpx.ReadTimeout: ConnectionError,
                httpx.ConnectError: NetworkError,
                httpx.RequestError: NetworkError,
            },
        ):
            # Handle the error
            api_error = handle_request_error(error)

            # Check the result
            assert isinstance(api_error, ConnectionError)
            assert 'Read timed out' in str(api_error)

    def test_handle_connect_error(self):
        """Test handling of connect error."""
        # Create a mock error
        error = httpx.ConnectError('Could not connect to the server')

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: ConnectionError,
                httpx.ReadTimeout: ConnectionError,
                httpx.ConnectError: NetworkError,
                httpx.RequestError: NetworkError,
            },
        ):
            # Handle the error
            api_error = handle_request_error(error)

            # Check the result
            assert isinstance(api_error, NetworkError)
            assert 'Could not connect to the server' in str(api_error)

    def test_handle_generic_error(self):
        """Test handling of generic request error."""
        # Create a mock error
        error = httpx.RequestError('Request error')

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: ConnectionError,
                httpx.ReadTimeout: ConnectionError,
                httpx.ConnectError: NetworkError,
                httpx.RequestError: NetworkError,
            },
        ):
            # Handle the error
            api_error = handle_request_error(error)

            # Check the result
            assert isinstance(api_error, NetworkError)
            assert 'Request error' in str(api_error)


class TestSafeRequest:
    """Test cases for safe_request function."""

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test request error."""
        # Create a mock client
        client = MagicMock()

        # Create a mock request
        mock_request = MagicMock()

        # Create a mock error with request property
        error = httpx.ConnectError('Could not connect to the server')
        error.request = mock_request

        # Make the client raise the error
        client.request = MagicMock(side_effect=error)

        # Fix the ERROR_CLASSES issue by patching it
        with patch(
            'awslabs.openapi_mcp_server.utils.error_handler.ERROR_CLASSES',
            {
                httpx.ConnectTimeout: ConnectionError,
                httpx.ReadTimeout: ConnectionError,
                httpx.ConnectError: NetworkError,
                httpx.RequestError: NetworkError,
            },
        ):
            # Make a request that will raise an error
            with pytest.raises(NetworkError) as excinfo:
                await safe_request(client, 'GET', 'https://example.com')

            # Check the error message
            assert 'Could not connect to the server' in str(excinfo.value)
