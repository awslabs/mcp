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
from awslabs.aws_documentation_mcp_server.models import SearchResponse, SearchResult
from awslabs.aws_documentation_mcp_server.server_utils import (
    DEFAULT_USER_AGENT,
    SEARCH_RESULT_CACHE,
    add_search_result_cache_item,
    get_query_id_from_cache,
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

            with (
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                    return_value=True,
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nContent',
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                    return_value='AWS Documentation from URL: # Test\n\nContent',
                ),
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

            with (
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                    return_value=False,
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                    return_value='AWS Documentation from URL: Plain text content',
                ),
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

            with (
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                    return_value=True,
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nLong content that exceeds max length',
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result'
                ) as mock_format,
            ):
                # Set up the mock to return a truncated result
                mock_format.return_value = (
                    'AWS Documentation from URL: # Test\n\nLong... (truncated)'
                )

                result = await read_documentation_impl(
                    ctx, url, max_length, start_index, 'test-uuid'
                )

                # Verify the result
                assert result == 'AWS Documentation from URL: # Test\n\nLong... (truncated)'

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

            with (
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                    return_value=True,
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nContent',
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                    mock_format,
                ),
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

    @pytest.mark.asyncio
    async def test_query_id_from_cache(self):
        """Test successful fetch of HTML content that has query ID in cache."""
        url = 'https://docs.aws.amazon.com/test.html'

        SEARCH_RESULT_CACHE.clear()

        add_search_result_cache_item(
            SearchResponse(
                search_results=[
                    SearchResult(
                        rank_order=1,
                        title='testtitle1',
                        url='https://docs.aws.amazon.com/test.html',
                    )
                ],
                facets={
                    'product_types': ['Amazon S3', 'AWS Lambda'],
                    'guide_types': ['User Guide', 'API Reference'],
                },
                query_id='test-query-id',
            )
        )

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

            with (
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.is_html_content',
                    return_value=True,
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html',
                    return_value='# Test\n\nContent',
                ),
                patch(
                    'awslabs.aws_documentation_mcp_server.server_utils.format_documentation_result',
                    return_value='AWS Documentation from URL: # Test\n\nContent',
                ),
            ):
                result = await read_documentation_impl(
                    ctx, url, max_length, start_index, 'test-uuid'
                )

                # Verify the result
                assert result == 'AWS Documentation from URL: # Test\n\nContent'

                # Verify the mock was called correctly
                mock_client.get.assert_called_once_with(
                    f'{url}?session=test-uuid&query_id=test-query-id',
                    follow_redirects=True,
                    headers={
                        'User-Agent': DEFAULT_USER_AGENT,
                        'X-MCP-Session-Id': 'test-uuid',
                    },
                    timeout=30,
                )

    @pytest.mark.asyncio
    async def test_truncation_applied_to_read_documentation(self):
        """Test that truncate_large_tables is actually invoked by read_documentation_impl."""
        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        # Build a response with a large table (>20 rows)
        rows_html = ''.join(f'<tr><td>row{i}</td><td>val{i}</td></tr>' for i in range(30))
        html = f"""<html><body>
        <h2>Section</h2>
        <table><thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody>{rows_html}</tbody></table>
        </body></html>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await read_documentation_impl(ctx, url, 50000, 0, 'test-uuid')

            # The large table should have been truncated
            assert 'Table truncated' in result
            assert 'search_table' in result


class TestUserAgentCustomization:
    """Test custom User-Agent functionality."""

    @patch.dict('os.environ', {'MCP_USER_AGENT': 'Custom/1.0 Browser'}, clear=False)
    def test_custom_user_agent_from_env(self):
        """Test that custom User-Agent is used when MCP_USER_AGENT is set."""
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        assert 'Custom/1.0 Browser' in server_utils.DEFAULT_USER_AGENT
        assert 'ModelContextProtocol' in server_utils.DEFAULT_USER_AGENT

    @patch.dict('os.environ', {}, clear=True)
    def test_default_user_agent_when_no_env(self):
        """Test that default User-Agent is used when MCP_USER_AGENT is not set."""
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        assert 'Chrome' in server_utils.DEFAULT_USER_AGENT
        assert 'ModelContextProtocol' in server_utils.DEFAULT_USER_AGENT


class TestVersionImport:
    """Test version import logic with metadata and fallback scenarios."""

    @patch('importlib.metadata.version')
    def test_version_from_metadata_success(self, mock_version):
        """Test successful version retrieval from importlib.metadata."""
        mock_version.return_value = '1.1.3'

        # Re-import the module to trigger the version logic
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        # Verify the version was retrieved from metadata
        mock_version.assert_called_once_with('awslabs.aws-documentation-mcp-server')
        assert '1.1.3' in server_utils.DEFAULT_USER_AGENT
        assert 'ModelContextProtocol/1.1.3' in server_utils.DEFAULT_USER_AGENT

    @patch('importlib.metadata.version')
    def test_version_fallback_to_init(self, mock_version):
        """Test fallback to __init__.py version when metadata fails. `__version__` patched in to avoid having to update with every version bump."""
        # Make metadata version raise an exception
        mock_version.side_effect = Exception('Package not found')

        import awslabs.aws_documentation_mcp_server as mcp_server

        version = mcp_server.__version__

        # Re-import the module to trigger the fallback logic
        import awslabs.aws_documentation_mcp_server.server_utils as server_utils
        import importlib

        importlib.reload(server_utils)

        # Verify it fell back to the __init__.py version
        mock_version.assert_called_once_with('awslabs.aws-documentation-mcp-server')
        assert version in server_utils.DEFAULT_USER_AGENT
        assert f'ModelContextProtocol/{version}' in server_utils.DEFAULT_USER_AGENT


class TestSearchResultCache:
    """Test expected functionality of SEARCH_RESULT_CACHE."""

    def test_add_search_result_cache_item(self):
        """Tests that adding items to search result cache is correct."""
        SEARCH_RESULT_CACHE.clear()

        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='testtitle1', url='testurl1')],
                facets={},
                query_id='query1',
            )
        )
        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='testtitle2', url='testurl2')],
                facets={},
                query_id='query2',
            )
        )
        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='testtitle3', url='testurl3')],
                facets={},
                query_id='query3',
            )
        )

        test_query_id = get_query_id_from_cache('testurl1')
        assert test_query_id is not None
        assert test_query_id == 'query1'

        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='testtitle4', url='testurl4')],
                facets={},
                query_id='query4',
            )
        )

        test_query_id = get_query_id_from_cache('testurl1')
        assert test_query_id is None
        test_query_id = get_query_id_from_cache('testurl3')
        assert test_query_id is not None
        assert test_query_id == 'query3'

    def test_get_query_id_from_cache(self):
        """Test that get_query_id_from_cache returns the correct search_results."""
        SEARCH_RESULT_CACHE.clear()

        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='testtitle1', url='testurl1')],
                facets={},
                query_id='query1',
            )
        )
        add_search_result_cache_item(
            SearchResponse(
                search_results=[
                    SearchResult(rank_order=1, title='testtitle1', url='testurl1'),
                    SearchResult(rank_order=2, title='testtitle2', url='testurl2'),
                ],
                facets={},
                query_id='query2',
            )
        )
        add_search_result_cache_item(
            SearchResponse(
                search_results=[
                    SearchResult(rank_order=1, title='testtitle3', url='testurl3'),
                    SearchResult(rank_order=2, title='testtitle5', url='testurl5'),
                ],
                facets={},
                query_id='test-query-id-5',
            )
        )

        # Should get most recent query ID even with duplicate URLs
        test_query_id = get_query_id_from_cache('testurl1')
        assert test_query_id is not None
        assert test_query_id == 'query2'

        test_query_id = get_query_id_from_cache('testurl2')
        assert test_query_id is not None
        assert test_query_id == 'query2'

        test_query_id = get_query_id_from_cache('testurl3')
        assert test_query_id is not None
        assert test_query_id == 'test-query-id-5'

        test_query_id = get_query_id_from_cache('testurl4')
        assert test_query_id is None


class TestSearchTableImpl:
    """Tests for search_table_impl URL construction and tracking params."""

    @pytest.mark.asyncio
    async def test_url_includes_tracking_params(self):
        """Test that search_table_impl appends tool, query, and section params to URL."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/general/latest/gr/bedrock.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h2>Test Section</h2><table><thead><tr><th>Name</th><th>Value</th></tr></thead><tbody><tr><td>foo</td><td>bar</td></tr></tbody></table></body></html>'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_table_impl(ctx, url, 'Test Section', 'foo', 20, 'test-uuid')

            called_url = mock_client.get.call_args[0][0]
            assert 'session=test-uuid' in called_url
            assert 'tool=search_table' in called_url
            assert 'query=foo' in called_url
            assert 'section=Test%20Section' in called_url

    @pytest.mark.asyncio
    async def test_url_without_section_title(self):
        """Test that section param is omitted when section_title is empty."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/general/latest/gr/bedrock.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>foo</td></tr></tbody></table></body></html>'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_table_impl(ctx, url, '', 'foo', 20, 'test-uuid')

            called_url = mock_client.get.call_args[0][0]
            assert 'tool=search_table' in called_url
            assert 'query=foo' in called_url
            assert 'section=' not in called_url

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test search_table_impl handles HTTP errors."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError('Connection error'))
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Sec', 'query', 20, 'test-uuid')

            assert result.error is not None
            assert 'Failed to fetch' in result.error
            assert 'Connection error' in result.error
            assert result.results == []
            ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        """Test search_table_impl handles 404 status codes."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Sec', 'query', 20, 'test-uuid')

            assert result.error is not None
            assert 'Failed to fetch' in result.error
            assert 'status code 404' in result.error
            assert result.results == []

    @pytest.mark.asyncio
    async def test_no_tables_on_page(self):
        """Test search_table_impl when page has no tables."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h2>Section</h2><p>No tables here</p></body></html>'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, '', 'query', 20, 'test-uuid')

            assert result.tables_searched == 0
            assert result.hint is not None
            assert 'No tables found' in result.hint

    @pytest.mark.asyncio
    async def test_section_not_found(self):
        """Test search_table_impl when section doesn't exist."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h2>Real Section</h2><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></body></html>'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(
                ctx, url, 'Nonexistent Section', 'query', 20, 'test-uuid'
            )

            assert result.tables_searched == 0
            assert result.hint is not None
            assert 'not found' in result.hint
            assert 'Real Section' in result.hint

    @pytest.mark.asyncio
    async def test_successful_match(self):
        """Test search_table_impl returns matching rows."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body><h2>Quotas</h2><table>
        <thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody>
            <tr><td>Titan requests</td><td>6000</td></tr>
            <tr><td>Claude requests</td><td>500</td></tr>
            <tr><td>Titan tokens</td><td>300000</td></tr>
        </tbody></table></body></html>"""

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Quotas', 'Titan', 20, 'test-uuid')

            assert result.tables_searched == 1
            assert result.tables_with_matches == 1
            assert len(result.results) == 1
            assert result.results[0].matched_rows == 2
            assert result.hint is None

    @pytest.mark.asyncio
    async def test_no_matches_returns_hint(self):
        """Test search_table_impl returns hint when no rows match."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body><h2>Quotas</h2><table>
        <thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody><tr><td>foo</td><td>bar</td></tr></tbody></table></body></html>"""

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Quotas', 'nonexistent', 20, 'test-uuid')

            assert result.tables_with_matches == 0
            assert result.results == []
            assert result.hint is not None
            assert 'No rows matched' in result.hint

    @pytest.mark.asyncio
    async def test_multi_table_response(self):
        """Test search_table_impl with multiple tables in a section."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body>
        <h2>Service quotas</h2>
        <h3>EC2</h3>
        <table><thead><tr><th>Name</th><th>Default</th></tr></thead>
        <tbody><tr><td>Instances</td><td>100</td></tr></tbody></table>
        <h3>Lambda</h3>
        <table><thead><tr><th>Name</th><th>Default</th></tr></thead>
        <tbody><tr><td>Functions</td><td>1000</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(
                ctx, url, 'Service quotas', 'Instances', 20, 'test-uuid'
            )

            assert result.tables_searched == 2
            assert result.tables_with_matches == 1
            assert result.results[0].matched_rows == 1

    @pytest.mark.asyncio
    async def test_query_id_from_cache(self):
        """Test search_table_impl appends query_id when URL is in cache."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        SEARCH_RESULT_CACHE.clear()
        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='test', url=url)],
                facets={},
                query_id='cached-query-id',
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h2>Sec</h2><table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></body></html>'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_table_impl(ctx, url, 'Sec', 'query', 20, 'test-uuid')

            called_url = mock_client.get.call_args[0][0]
            assert 'query_id=cached-query-id' in called_url

    @pytest.mark.asyncio
    async def test_empty_section_title_treated_as_none(self):
        """Test that empty string section_title searches all tables."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body>
        <h2>Sec</h2>
        <table><thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>foo</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, '', 'foo', 20, 'test-uuid')

            assert result.tables_searched == 1
            assert result.tables_with_matches == 1

    @pytest.mark.asyncio
    async def test_non_html_content_returns_hint(self):
        """Test search_table_impl returns hint when content is not HTML."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.headers = {'content-type': 'application/json'}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, '', 'query', 20, 'test-uuid')

            assert result.tables_searched == 0
            assert result.hint is not None
            assert 'not HTML' in result.hint

    @pytest.mark.asyncio
    async def test_max_rows_caps_results(self):
        """Test search_table_impl caps returned rows at max_rows."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        # Build a table with 25 matching rows
        rows_html = ''.join(f'<tr><td>Quota {i}</td><td>active</td></tr>' for i in range(25))
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = f"""<html><body><h2>Quotas</h2><table>
        <thead><tr><th>Name</th><th>Status</th></tr></thead>
        <tbody>{rows_html}</tbody></table></body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Quotas', 'active', 10, 'test-uuid')

            assert result.results[0].total_rows == 25
            assert result.results[0].matched_rows == 25
            assert result.results[0].showing == 10
            assert len(result.results[0].rows) == 10

    @pytest.mark.asyncio
    async def test_rowspan_table_returns_nested_structure(self):
        """Test search_table_impl returns parent/child columns for rowspan tables."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body><h2>Actions</h2><table>
        <thead><tr><th>Action</th><th>Level</th><th>Resource</th></tr></thead>
        <tbody>
            <tr><td rowspan="2">RunInstances</td><td rowspan="2">Write</td><td>image*</td></tr>
            <tr><td>instance*</td></tr>
            <tr><td>StopInstances</td><td>Write</td><td>instance*</td></tr>
        </tbody></table></body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, 'Actions', 'RunInstances', 20, 'test-uuid')

            assert result.tables_with_matches == 1
            table_result = result.results[0]
            assert table_result.parent_columns == ['Action', 'Level']
            assert table_result.child_columns == ['Resource']
            assert table_result.matched_rows == 1
            assert table_result.rows[0]['Action'] == 'RunInstances'
            assert len(table_result.rows[0]['rows']) == 2

    @pytest.mark.asyncio
    async def test_section_title_none_searches_all_tables(self):
        """Test that section_title=None (not '') searches all tables on the page."""
        from awslabs.aws_documentation_mcp_server.server_utils import search_table_impl

        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MagicMock(spec=Context)
        ctx.error = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<html><body>
        <h2>Section A</h2>
        <table><thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>alpha</td></tr></tbody></table>
        <h2>Section B</h2>
        <table><thead><tr><th>Name</th></tr></thead>
        <tbody><tr><td>beta</td></tr></tbody></table>
        </body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_table_impl(ctx, url, None, 'alpha', 20, 'test-uuid')

            assert result.tables_searched == 2
            assert result.tables_with_matches == 1
            assert result.results[0].matched_rows == 1
            assert result.section_title != ''
