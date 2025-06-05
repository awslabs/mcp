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
"""Tests for the AWS Documentation MCP Server."""

import httpx
import pytest
from awslabs.aws_documentation_mcp_server.server_aws_cn import (
    get_available_services,
)
from awslabs.aws_documentation_mcp_server.server_aws_cn import (
    read_documentation as read_documentation_china,
)
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


class TestReadDocumentationChina:
    """Tests for the read_documentation function in server_aws_cn."""

    @pytest.mark.asyncio
    async def test_read_documentation_china(self):
        """Test reading AWS China documentation."""
        url = 'https://docs.amazonaws.cn/en_us/AmazonS3/latest/userguide/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>Test</h1><p>This is a test.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html'
            ) as mock_extract:
                mock_extract.return_value = '# Test\n\nThis is a test.'

                result = await read_documentation_china(
                    ctx, url=url, max_length=10000, start_index=0
                )

                assert 'AWS Documentation from' in result
                assert (
                    'https://docs.amazonaws.cn/en_us/AmazonS3/latest/userguide/test.html' in result
                )
                assert '# Test\n\nThis is a test.' in result
                mock_get.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_documentation_china_invalid_domain(self):
        """Test reading AWS China documentation with invalid domain."""
        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MockContext()

        result = await read_documentation_china(ctx, url=url, max_length=10000, start_index=0)

        assert 'Invalid URL' in result
        assert 'must be from the docs.amazonaws.cn domain' in result

    @pytest.mark.asyncio
    async def test_read_documentation_china_invalid_extension(self):
        """Test reading AWS China documentation with invalid file extension."""
        url = 'https://docs.amazonaws.cn/en_us/test'
        ctx = MockContext()

        result = await read_documentation_china(ctx, url=url, max_length=10000, start_index=0)

        assert 'Invalid URL' in result
        assert 'must end with .html' in result

    @pytest.mark.asyncio
    async def test_read_documentation_china_error(self):
        """Test reading AWS China documentation with an error."""
        url = 'https://docs.amazonaws.cn/en_us/test.html'
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            result = await read_documentation_china(ctx, url=url, max_length=10000, start_index=0)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()


class TestGetAvailableServices:
    """Tests for the get_available_services function."""

    @pytest.mark.asyncio
    async def test_get_available_services(self):
        """Test getting available services in AWS China."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>AWS Services in China</h1><p>Available services list.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_aws_cn.extract_content_from_html'
            ) as mock_extract:
                mock_extract.return_value = '# AWS Services in China\n\nAvailable services list.'

                result = await get_available_services(ctx)

                assert 'AWS Documentation from' in result
                assert (
                    'https://docs.amazonaws.cn/en_us/aws/latest/userguide/services.html' in result
                )
                assert '# AWS Services in China\n\nAvailable services list.' in result
                mock_get.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_services_error(self):
        """Test getting available services with an error."""
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            result = await get_available_services(ctx)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()
