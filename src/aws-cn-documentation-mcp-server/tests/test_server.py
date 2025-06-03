# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the AWS China Documentation MCP Server."""

import httpx
import pytest
from awslabs.aws_cn_documentation_mcp_server.server import (
    get_available_services,
    read_documentation,
)
from awslabs.aws_cn_documentation_mcp_server.util import extract_content_from_html
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


class TestExtractContentFromHTML:
    """Tests for the extract_content_from_html function."""

    def test_extract_content_from_html(self):
        """Test extracting content from HTML."""
        html = '<html><body><h1>Test</h1><p>This is a test.</p></body></html>'
        with patch('awslabs.aws_cn_documentation_mcp_server.util.BeautifulSoup') as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup
            with patch(
                'awslabs.aws_cn_documentation_mcp_server.util.markdownify.markdownify'
            ) as mock_markdownify:
                mock_markdownify.return_value = '# Test\n\nThis is a test.'
                result = extract_content_from_html(html)
                assert result == '# Test\n\nThis is a test.'
                mock_bs.assert_called_once()
                mock_markdownify.assert_called_once()

    def test_extract_content_from_html_no_content(self):
        """Test extracting content from HTML with no content."""
        html = '<html><body></body></html>'
        with patch('awslabs.aws_cn_documentation_mcp_server.util.BeautifulSoup') as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup
            mock_soup.body = None
            result = extract_content_from_html(html)
            assert '<e>' in result
            mock_bs.assert_called_once()


class TestReadDocumentation:
    """Tests for the read_documentation function."""

    @pytest.mark.asyncio
    async def test_read_documentation(self):
        """Test reading AWS documentation."""
        url = 'https://docs.amazonaws.cn/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Test</h1><p>This is a test.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_cn_documentation_mcp_server.server.extract_content_from_html'
            ) as mock_extract:
                mock_extract.return_value = '# Test\n\nThis is a test.'

                result = await read_documentation(ctx, url=url, max_length=10000, start_index=0)

                assert 'AWS China Documentation from' in result
                assert '# Test\n\nThis is a test.' in result
                mock_get.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_documentation_error(self):
        """Test reading AWS documentation with an error."""
        url = 'https://docs.amazonaws.cn/test.html'
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            result = await read_documentation(ctx, url=url, max_length=10000, start_index=0)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_url_domain(self):
        """Test read_documentation with an invalid URL domain."""
        ctx = MockContext()
        url = 'https://example.com/some-page.html'

        result = await read_documentation(ctx, url)

        assert 'Invalid URL' in result
        assert 'docs.amazonaws.cn domain' in result

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_url_extension(self):
        """Test read_documentation with an invalid URL extension."""
        ctx = MockContext()
        url = 'https://docs.amazonaws.cn/some-page'

        result = await read_documentation(ctx, url)

        assert 'Invalid URL' in result
        assert 'must end with .html' in result

    @pytest.mark.asyncio
    async def test_read_documentation_http_error(self):
        """Test read_documentation with HTTP error."""
        ctx = MockContext()
        url = 'https://docs.amazonaws.cn/some-page.html'

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.side_effect = httpx.HTTPError('Connection error')

            result = await read_documentation(ctx, url)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result

    @pytest.mark.asyncio
    async def test_read_documentation_status_error(self):
        """Test read_documentation with status code error."""
        ctx = MockContext()
        url = 'https://docs.amazonaws.cn/some-page.html'

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_instance.get.return_value = mock_response

            result = await read_documentation(ctx, url)

            assert 'Failed to fetch' in result
            assert 'status code 404' in result

    @pytest.mark.asyncio
    async def test_read_documentation_non_html_content(self):
        """Test read_documentation with non-HTML content."""
        ctx = MockContext()
        url = 'https://docs.amazonaws.cn/some-page.html'
        max_length = 5000
        start_index = 0

        with (
            patch('httpx.AsyncClient') as mock_client,
            patch('awslabs.aws_cn_documentation_mcp_server.util.is_html_content') as mock_is_html,
        ):
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = 'Plain text content'
            mock_response.headers = {'content-type': 'text/plain'}
            mock_instance.get.return_value = mock_response

            # Make is_html_content return False
            mock_is_html.return_value = False

            with patch(
                'awslabs.aws_cn_documentation_mcp_server.server.format_documentation_result'
            ) as mock_format:
                mock_format.return_value = 'Formatted plain text content'
                result = await read_documentation(ctx, url, max_length, start_index)

                # Verify format_documentation_result was called with the right parameters
                mock_format.assert_called_once()
                assert result == 'Formatted plain text content'


class TestGetAvailableServices:
    """Tests for the get_available_services function."""

    @pytest.mark.asyncio
    async def test_get_available_services(self):
        """Test fetching available services from AWS China documentation."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>AWS Services Available in China</h1><p>List of services.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_cn_documentation_mcp_server.server.extract_content_from_html'
            ) as mock_extract:
                mock_extract.return_value = (
                    '# AWS Services Available in China\n\nList of services.'
                )
                with patch(
                    'awslabs.aws_cn_documentation_mcp_server.server.format_documentation_result'
                ) as mock_format:
                    mock_format.return_value = 'AWS China Documentation from https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html\n\n# AWS Services Available in China\n\nList of services.'

                    result = await get_available_services(ctx)

                    assert 'AWS China Documentation from' in result
                    assert '# AWS Services Available in China' in result
                    assert 'List of services.' in result
                    mock_get.assert_called_once_with(
                        'https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html',
                        follow_redirects=True,
                        headers={'User-Agent': mock_get.call_args[1]['headers']['User-Agent']},
                        timeout=30,
                    )
                    mock_extract.assert_called_once()
                    mock_format.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_services_http_error(self):
        """Test fetching available services with HTTP error."""
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            result = await get_available_services(ctx)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_services_status_error(self):
        """Test fetching available services with status code error."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await get_available_services(ctx)

            assert 'Failed to fetch' in result
            assert 'status code 404' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_services_non_html_content(self):
        """Test get_available_services with non-HTML content."""
        ctx = MockContext()

        with (
            patch('httpx.AsyncClient') as mock_client,
            patch('awslabs.aws_cn_documentation_mcp_server.util.is_html_content') as mock_is_html,
        ):
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = 'Plain text services list'
            mock_response.headers = {'content-type': 'text/plain'}
            mock_instance.get.return_value = mock_response

            # Make is_html_content return False
            mock_is_html.return_value = False

            with patch(
                'awslabs.aws_cn_documentation_mcp_server.server.format_documentation_result'
            ) as mock_format:
                mock_format.return_value = 'Formatted services list'
                result = await get_available_services(ctx)

                # Verify format_documentation_result was called with the right parameters
                mock_format.assert_called_once()
                assert result == 'Formatted services list'
