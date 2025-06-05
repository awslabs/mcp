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
from awslabs.aws_documentation_mcp_server.server_aws import (
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
