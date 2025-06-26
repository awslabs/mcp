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
import json
import pytest
from awslabs.aws_documentation_mcp_server.server_aws import (
    main,
    read_documentation,
    recommend,
    search_documentation,
)
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


class TestReadDocumentation:
    """Tests for the read_documentation function."""

    @pytest.mark.asyncio
    async def test_read_documentation(self):
        """Test reading AWS documentation."""
        url = 'https://docs.aws.amazon.com/test.html'
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

                result = await read_documentation(ctx, url=url, max_length=10000, start_index=0)

                assert 'AWS Documentation from' in result
                assert '# Test\n\nThis is a test.' in result
                mock_get.assert_called_once()
                mock_extract.assert_called_once()
                called_url = mock_get.call_args[0][0]
                assert '?session=' in called_url
                assert called_url.startswith('https://docs.aws.amazon.com/test.html?session=')

    @pytest.mark.asyncio
    async def test_read_documentation_error(self):
        """Test reading AWS documentation with an error."""
        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            result = await read_documentation(ctx, url=url, max_length=10000, start_index=0)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_domain(self):
        """Test reading AWS documentation with invalid domain."""
        url = 'https://invalid-domain.com/test.html'
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must be from the docs.aws.amazon.com domain'):
            await read_documentation(ctx, url=url, max_length=10000, start_index=0)

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_extension(self):
        """Test reading AWS documentation with invalid file extension."""
        url = 'https://docs.aws.amazon.com/test.pdf'
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must end with .html'):
            await read_documentation(ctx, url=url, max_length=10000, start_index=0)


class TestSearchDocumentation:
    """Tests for the search_documentation function."""

    @pytest.mark.asyncio
    async def test_search_documentation(self):
        """Test searching AWS documentation."""
        search_phrase = 'test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test1',
                        'title': 'Test 1',
                        'summary': 'This is test 1.',
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/test2',
                        'title': 'Test 2',
                        'suggestionBody': 'This is test 2.',
                    }
                },
            ]
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

            assert len(results) == 2
            assert results[0].rank_order == 1
            assert results[0].url == 'https://docs.aws.amazon.com/test1'
            assert results[0].title == 'Test 1'
            assert results[0].context == 'This is test 1.'
            assert results[1].rank_order == 2
            assert results[1].url == 'https://docs.aws.amazon.com/test2'
            assert results[1].title == 'Test 2'
            assert results[1].context == 'This is test 2.'
            mock_post.assert_called_once()

            called_url = mock_post.call_args[0][0]
            assert '?session=' in called_url
            assert called_url.startswith(
                'https://proxy.search.docs.aws.amazon.com/search?session='
            )

    @pytest.mark.asyncio
    async def test_search_documentation_http_error(self):
        """Test searching AWS documentation with HTTP error."""
        search_phrase = 'test'
        ctx = MockContext()

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError('Connection error')

            results = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

            assert len(results) == 1
            assert results[0].rank_order == 1
            assert results[0].url == ''
            assert 'Error searching AWS docs: Connection error' in results[0].title
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_search_documentation_status_error(self):
        """Test searching AWS documentation with status code error."""
        search_phrase = 'test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

            assert len(results) == 1
            assert results[0].rank_order == 1
            assert results[0].url == ''
            assert 'Error searching AWS docs - status code 500' in results[0].title
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_search_documentation_json_error(self):
        """Test searching AWS documentation with JSON decode error."""
        search_phrase = 'test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

            assert len(results) == 1
            assert results[0].rank_order == 1
            assert results[0].url == ''
            assert 'Error parsing search results:' in results[0].title
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_search_documentation_empty_results(self):
        """Test searching AWS documentation with empty results."""
        search_phrase = 'test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No suggestions key

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

            assert len(results) == 0
            mock_post.assert_called_once()


class TestRecommend:
    """Tests for the recommend function."""

    @pytest.mark.asyncio
    async def test_recommend(self):
        """Test getting content recommendations."""
        url = 'https://docs.aws.amazon.com/test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'highlyRated': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/rec1',
                        'assetTitle': 'Recommendation 1',
                        'abstract': 'This is recommendation 1.',
                    }
                ]
            },
            'similar': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/rec2',
                        'assetTitle': 'Recommendation 2',
                        'abstract': 'This is recommendation 2.',
                    }
                ]
            },
        }

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await recommend(ctx, url=url)

            assert len(results) == 2
            assert results[0].url == 'https://docs.aws.amazon.com/rec1'
            assert results[0].title == 'Recommendation 1'
            assert results[0].context == 'This is recommendation 1.'
            assert results[1].url == 'https://docs.aws.amazon.com/rec2'
            assert results[1].title == 'Recommendation 2'
            assert results[1].context == 'This is recommendation 2.'
            mock_get.assert_called_once()

            called_url = mock_get.call_args[0][0]
            assert '?path=' in called_url
            assert '&session=' in called_url
            assert called_url.startswith(
                'https://contentrecs-api.docs.aws.amazon.com/v1/recommendations?path=https://docs.aws.amazon.com/test&session='
            )

    @pytest.mark.asyncio
    async def test_recommend_http_error(self):
        """Test getting content recommendations with HTTP error."""
        url = 'https://docs.aws.amazon.com/test'
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            results = await recommend(ctx, url=url)

            assert len(results) == 1
            assert results[0].url == ''
            assert 'Error getting recommendations: Connection error' in results[0].title
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_recommend_status_error(self):
        """Test getting content recommendations with status code error."""
        url = 'https://docs.aws.amazon.com/test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await recommend(ctx, url=url)

            assert len(results) == 1
            assert results[0].url == ''
            assert 'Error getting recommendations - status code 500' in results[0].title
            assert results[0].context is None

    @pytest.mark.asyncio
    async def test_recommend_json_error(self):
        """Test getting content recommendations with JSON decode error."""
        url = 'https://docs.aws.amazon.com/test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await recommend(ctx, url=url)

            assert len(results) == 1
            assert results[0].url == ''
            assert 'Error parsing recommendations:' in results[0].title
            assert results[0].context is None


class TestMain:
    """Tests for the main function."""

    def test_main(self):
        """Test the main function."""
        with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp.run') as mock_run:
            with patch(
                'awslabs.aws_documentation_mcp_server.server_aws.logger.info'
            ) as mock_logger:
                main()
                mock_logger.assert_called_once_with('Starting AWS Documentation MCP Server')
                mock_run.assert_called_once()
