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
"""Tests for server utility functions in the AWS Documentation MCP Server."""

import httpx
import pytest
from awslabs.aws_documentation_mcp_server.server_utils import (
    DEFAULT_USER_AGENT,
    read_documentation_impl,
)
from mcp.server.fastmcp.server import Context
from unittest.mock import AsyncMock, MagicMock, patch


class TestReadDocumentationImpl:
    """Tests for the read_documentation_impl function."""

    @pytest.mark.asyncio
    async def test_successful_html_fetch(self):
        """Test successful fetch of HTML content."""
        url = 'https://docs.aws.amazon.com/test.html'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 1000
        start_index = 0

        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Test</h1><p>Content</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                return_value=True,
            ):
                with patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nContent',
                ):
                    with patch(
                        'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                        return_value='AWS Documentation from URL: # Test\n\nContent',
                    ):
                        result = await read_documentation_impl(
                            ctx, url, max_length, start_index, 'test-uuid'
                        )

                        # Verify the result
                        assert result == 'AWS Documentation from URL: # Test\n\nContent'

                        # Verify the mock was called correctly
                        mock_client.get.assert_called_once_with(
                            f'{url}?session=test-uuid',
                            follow_redirects=True,
                            headers={
                                'User-Agent': DEFAULT_USER_AGENT,
                                'X-MCP-Session-Id': 'test-uuid',
                            },
                            timeout=30,
                        )

    @pytest.mark.asyncio
    async def test_successful_non_html_fetch(self):
        """Test successful fetch of non-HTML content."""
        url = 'https://docs.aws.amazon.com/test.txt'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 1000
        start_index = 0

        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'Plain text content'
        mock_response.headers = {'content-type': 'text/plain'}

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                return_value=False,
            ):
                with patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                    return_value='AWS Documentation from URL: Plain text content',
                ):
                    result = await read_documentation_impl(
                        ctx, url, max_length, start_index, 'test-uuid'
                    )

                    # Verify the result
                    assert result == 'AWS Documentation from URL: Plain text content'

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        url = 'https://docs.aws.amazon.com/test.html'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 1000
        start_index = 0

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError('Connection error'))
            mock_client_class.return_value = mock_client

            result = await read_documentation_impl(ctx, url, max_length, start_index, 'test-uuid')

            # Verify the result contains the error message
            assert 'Failed to fetch' in result
            assert 'Connection error' in result

            # Verify the error was logged to the context
            ctx.error.assert_called_once()
            assert 'Failed to fetch' in ctx.error.call_args[0][0]
            assert 'Connection error' in ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        """Test handling of HTTP status errors."""
        url = 'https://docs.aws.amazon.com/test.html'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 1000
        start_index = 0

        # Create a proper mock response with error status code
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await read_documentation_impl(ctx, url, max_length, start_index, 'test-uuid')

            # Verify the result contains the error message
            assert 'Failed to fetch' in result
            assert 'status code 404' in result

            # Verify the error was logged to the context
            ctx.error.assert_called_once()
            assert 'Failed to fetch' in ctx.error.call_args[0][0]
            assert 'status code 404' in ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_content_truncation(self):
        """Test content truncation when content exceeds max_length."""
        url = 'https://docs.aws.amazon.com/test.html'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 5
        start_index = 0

        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '<html><body><h1>Test</h1><p>Long content that exceeds max length</p></body></html>'
        )
        mock_response.headers = {'content-type': 'text/html'}

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                return_value=True,
            ):
                with patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nLong content that exceeds max length',
                ):
                    with patch(
                        'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result'
                    ) as mock_format:
                        # Set up the mock to return a truncated result
                        mock_format.return_value = (
                            'AWS Documentation from URL: # Test\n\nLong... (truncated)'
                        )

                        result = await read_documentation_impl(
                            ctx, url, max_length, start_index, 'test-uuid'
                        )

                        # Verify the result
                        assert (
                            result == 'AWS Documentation from URL: # Test\n\nLong... (truncated)'
                        )

                        # Verify format_documentation_result was called with the correct parameters
                        mock_format.assert_called_once_with(
                            url,
                            '# Test\n\nLong content that exceeds max length',
                            start_index,
                            max_length,
                        )

    @pytest.mark.asyncio
    async def test_start_index_handling(self):
        """Test handling of non-zero start_index."""
        url = 'https://docs.aws.amazon.com/test.html'
        # Create a real Context object with mocked methods
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()
        max_length = 1000
        start_index = 10  # Start from the 10th character

        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Test</h1><p>Content</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        # Use enter_async_context to properly mock the AsyncClient context manager
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_format = MagicMock(return_value='AWS Documentation from URL: Content')

            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                return_value=True,
            ):
                with patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nContent',
                ):
                    with patch(
                        'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                        mock_format,
                    ):
                        result = await read_documentation_impl(
                            ctx, url, max_length, start_index, 'test-uuid'
                        )

                        # Verify the result
                        assert result == 'AWS Documentation from URL: Content'

                        # Verify format_documentation_result was called with the correct start_index
                        mock_format.assert_called_once_with(
                            url, '# Test\n\nContent', start_index, max_length
                        )


class TestVersionImport:
    """Test version import logic with metadata and fallback scenarios."""

    @patch('importlib.metadata.version')
    def test_version_from_metadata_success(self, mock_version):
        """Test successful version retrieval from importlib.metadata."""
        mock_version.return_value = '1.1.0'

        # Re-import the module to trigger the version logic
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        # Verify the version was retrieved from metadata
        mock_version.assert_called_once_with('awslabs.aws-documentation-mcp-server')
        assert '1.1.0' in server_utils.DEFAULT_USER_AGENT
        assert 'ModelContextProtocol/1.1.0' in server_utils.DEFAULT_USER_AGENT

    @patch('importlib.metadata.version')
    def test_version_fallback_to_init(self, mock_version):
        """Test fallback to __init__.py version when metadata fails."""
        # Make metadata version raise an exception
        mock_version.side_effect = Exception('Package not found')

        # Re-import the module to trigger the fallback logic
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        # Verify it fell back to the __init__.py version
        mock_version.assert_called_once_with('awslabs.aws-documentation-mcp-server')
        assert '1.1.0' in server_utils.DEFAULT_USER_AGENT
        assert 'ModelContextProtocol/1.1.0' in server_utils.DEFAULT_USER_AGENT
