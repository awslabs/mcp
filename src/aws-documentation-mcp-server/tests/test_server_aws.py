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
    read_sections,
    recommend,
    search_documentation,
    search_table,
)
from awslabs.aws_documentation_mcp_server.util import UnreadablePageError
from mcp.server.mcpserver import Context
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, unquote, urlparse


class MockContext(Context):
    """Mock context for testing."""

    def __init__(self) -> None:
        """Initialize with no request context; nothing here needs one."""
        super().__init__()

    async def error(self, data: Any, *, logger_name: Optional[str] = None):
        """Mock error method."""
        print(f'Error: {data}')


class TestReadDocumentation:
    """Tests for the read_documentation function."""

    @pytest.mark.asyncio
    async def test_read_documentation(self):
        """Test reading AWS documentation."""
        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
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
    async def test_read_documentation_with_domain_modification(self):
        """Test reading AWS documentation with domain modification."""
        url = 'https://awsdocs-neuron.readthedocs-hosted.com/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
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
                assert called_url.startswith(
                    'https://awsdocs-neuron.readthedocs-hosted.com/test.html?session='
                )

    @pytest.mark.asyncio
    async def test_read_documentation_error(self):
        """Test reading AWS documentation with an error."""
        url = 'https://docs.aws.amazon.com/test.html'
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            with pytest.raises(ValueError, match='Connection error'):
                await read_documentation(ctx, url=url, max_length=10000, start_index=0)
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_domain(self):
        """Test reading AWS documentation with invalid domain."""
        url = 'https://invalid-domain.com/test.html'
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_documentation(ctx, url=url, max_length=10000, start_index=0)

    @pytest.mark.asyncio
    async def test_read_documentation_invalid_extension(self):
        """Test reading AWS documentation with invalid file extension."""
        url = 'https://docs.aws.amazon.com/test.pdf'
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must end with .html'):
            await read_documentation(ctx, url=url, max_length=10000, start_index=0)


class TestReadSections:
    """Tests for the read_sections function."""

    @pytest.mark.asyncio
    async def test_read_sections_success(self):
        """Test successful section extraction from AWS documentation."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Introduction', 'Main Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>Introduction</h2>
            <p>This is the introduction.</p>
            <h2>Main Section</h2>
            <p>This is the main content.</p>
            <h2>Other Section</h2>
            <p>This should not be included.</p>
        </body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            # Verify requested sections are extracted
            assert 'This is the introduction' in result
            assert 'This is the main content' in result

            # Verify unmatched section is not included
            assert 'This should not be included' not in result

            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]

            # Verify sections parameter by parsing and decoding
            parsed_url = urlparse(called_url)
            query_params = parse_qs(parsed_url.query)
            assert 'sections' in query_params

            # Decode and verify section titles
            encoded_sections = query_params['sections'][0]
            decoded_sections = [unquote(s.strip()) for s in encoded_sections.split(',')]
            assert 'Introduction' in decoded_sections
            assert 'Main Section' in decoded_sections

    @pytest.mark.asyncio
    async def test_read_sections_with_domain_modification(self):
        """Test section extraction with domain modification."""
        url = 'https://awsdocs-neuron.readthedocs-hosted.com/test.html'
        section_titles = ['Getting Started']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = (
            '<html><body><h2>Getting Started</h2><p>Neuron content.</p></body></html>'
        )
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            assert 'Neuron content' in result
            called_url = mock_get.call_args[0][0]
            assert '?session=' in called_url

    @pytest.mark.asyncio
    async def test_read_sections_http_error(self):
        """Test read_sections with HTTP error."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Introduction']
        ctx = MockContext()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError('Connection error')

            with pytest.raises(ValueError, match='Connection error'):
                await read_sections(ctx, url=url, section_titles=section_titles)
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_sections_no_sections_found(self):
        """Test read_sections when no requested sections exist."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Nonexistent Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        # Only h1, no h2 sections
        mock_response.text = (
            '<html><body><h1>Other Section</h1><p>Different content.</p></body></html>'
        )
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(ValueError, match='This document does not contain subsections'):
                await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_partial_success(self):
        """Test read_sections with partial success (some sections found, others missing)."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Found Section', 'Missing Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        # One h2 section exists, one doesn't
        mock_response.text = '<html><body><h2>Found Section</h2><p>Content here.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            assert 'Content here' in result
            assert 'The following requested sections were not found: "Missing Section"' in result

    @pytest.mark.asyncio
    async def test_read_sections_invalid_domain(self):
        """Test read_sections with invalid domain."""
        url = 'https://invalid-domain.com/test.html'
        section_titles = ['Introduction']
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_invalid_extension(self):
        """Test read_sections with invalid file extension."""
        url = 'https://docs.aws.amazon.com/test.pdf'
        section_titles = ['Introduction']
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must end with .html'):
            await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_empty_section_titles(self):
        """Test read_sections with empty section_titles parameter."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = []
        ctx = MockContext()

        with pytest.raises(ValueError, match='section_titles parameter cannot be empty'):
            await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_special_characters_url_encoding(self):
        """Test that section titles with special characters are properly URL-encoded."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = [
            'C++ & C# Programming',
            'REST/HTTP APIs',
            'Parameters (optional)',
            'Key=Value Pairs',
        ]
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>C++ & C# Programming</h2>
            <p>Programming content.</p>
            <h2>REST/HTTP APIs</h2>
            <p>API content.</p>
            <h2>Parameters (optional)</h2>
            <p>Parameter details.</p>
            <h2>Key=Value Pairs</h2>
            <p>Key-value content.</p>
        </body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            assert 'Programming content' in result
            assert 'API content' in result

            called_url = mock_get.call_args[0][0]
            parsed_url = urlparse(called_url)
            query_params = parse_qs(parsed_url.query)

            assert 'sections' in query_params, 'sections parameter missing from URL'

            # Decode comma-separated sections (use unquote since we use quote, not quote_plus)
            encoded_sections = query_params['sections'][0]
            decoded_sections = [unquote(s.strip()) for s in encoded_sections.split(',')]

            for original_title in section_titles:
                assert original_title.strip() in decoded_sections, (
                    f'Title "{original_title}" not in decoded sections: {decoded_sections}'
                )

    @pytest.mark.asyncio
    async def test_read_sections_whitespace_normalization(self):
        """Test whitespace normalization fix for BUG-001."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = [' Best  practices \n']  # Extra spaces and newline
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = '<html><body><h1>This is a page</h1><h2>Best practices</h2><p>Content here.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            # Whitespace normalization should match despite extra spaces/newlines
            assert 'Content here' in result

    @pytest.mark.asyncio
    async def test_read_sections_markdown_content(self):
        """Test read_sections extracts sections from a negotiated Markdown response."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Introduction']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = '# Page\n\n## Introduction\n\nIntro.\n\n## Other\n\nOther.\n'
        mock_response.headers = {'content-type': 'text/markdown'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html'
            ) as mock_extract:
                result = await read_sections(ctx, url=url, section_titles=section_titles)

            mock_extract.assert_not_called()
            mock_get.assert_called_once()
            assert result == f'AWS Documentation from {url}:\n\n## Introduction\n\nIntro.'

    @pytest.mark.asyncio
    async def test_read_sections_non_404_error(self):
        """Test read_sections with non-404 HTTP error."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Introduction']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(ValueError, match='status code 500'):
                await read_sections(ctx, url=url, section_titles=section_titles)
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_sections_extract_content_error(self):
        """Test read_sections when extract_content_from_html returns error."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Test Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = '<html><body><h2>Test Section</h2><p>Content.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html'
            ) as mock_extract:
                # Simulate extraction refusing the page
                mock_extract.side_effect = UnreadablePageError('Page failed to be simplified')

                with pytest.raises(ValueError, match='could not be read'):
                    await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_end_to_end_workflow(self):
        """Test complete end-to-end workflow and verify only h2 sections extracted."""
        url = 'https://docs.aws.amazon.com/s3/latest/userguide/test.html'
        section_titles = ['Bucket Naming Rules', 'Examples']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <div class="main-content">
                <h1>S3 Bucket Guide</h1>
                <p>Introduction to S3 buckets.</p>
                <h2>Bucket Naming Rules</h2>
                <ul>
                    <li>Names must be unique</li>
                    <li>Use lowercase letters</li>
                </ul>
                <h2>Examples</h2>
                <p>Here are some examples:</p>
                <code>my-bucket-name</code>
                <h2>Other Information</h2>
                <p>This section should not be included.</p>
            </div>
        </body></html>"""
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            # Verify h2 sections ARE extracted
            assert 'Bucket Naming Rules' in result
            assert 'Names must be unique' in result
            assert 'Examples' in result
            assert 'my-bucket-name' in result

            # Verify h1 content is NOT extracted
            assert 'Introduction to S3 buckets' not in result

            # Verify unmatched h2 section is NOT extracted
            assert 'Other Information' not in result
            assert 'This section should not be included' not in result

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
            'queryId': 'test-query-id',
            'facets': {
                'aws-docs-search-product': ['Amazon S3', 'AWS Lambda'],
                'aws-docs-search-guide': ['User Guide', 'API Reference'],
            },
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
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            results = response.search_results
            assert len(results) == 2
            assert results[0].rank_order == 1
            assert results[0].url == 'https://docs.aws.amazon.com/test1'
            assert results[0].title == 'Test 1'
            assert results[0].context == 'This is test 1.'
            assert results[1].rank_order == 2
            assert results[1].url == 'https://docs.aws.amazon.com/test2'
            assert results[1].title == 'Test 2'
            assert results[1].context == 'This is test 2.'
            assert response.query_id == 'test-query-id'
            assert response.facets == {
                'product_types': ['Amazon S3', 'AWS Lambda'],
                'guide_types': ['User Guide', 'API Reference'],
            }
            assert response.query_id == 'test-query-id'
            assert response.facets == {
                'product_types': ['Amazon S3', 'AWS Lambda'],
                'guide_types': ['User Guide', 'API Reference'],
            }
            mock_post.assert_called_once()

            for call in mock_post.call_args_list:
                args, kwargs = call
                called_url = args[0]  # args is a tuple, first element is request URL

                assert '?session=' in called_url
                assert called_url.startswith('https://proxy.search.docs.aws.com/search?session=')

                request_body = kwargs['json']
                assert not any(
                    context_attr['key'] == 'domain'
                    and context_attr['value'] == 'awsdocs-neuron.readthedocs-hosted.com'
                    for context_attr in request_body['contextAttributes']
                )

    @pytest.mark.asyncio
    async def test_search_documentation_with_domain_modification(self):
        """Test searching AWS documentation."""
        search_phrase = 'test neuron'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-id',
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
                        'link': 'https://awsdocs-neuron.readthedocs-hosted.com/test2',
                        'title': 'Modified Domain Test',
                        'suggestionBody': 'This is modified domain test.',
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            search_results = results.search_results
            assert len(search_results) == 2
            mock_post.assert_called_once()

            for call in mock_post.call_args_list:
                args, kwargs = call
                called_url = args[0]  # args is a tuple, first element is request URL

                assert '?session=' in called_url
                assert called_url.startswith('https://proxy.search.docs.aws.com/search?session=')

                request_body = kwargs['json']
                assert any(
                    context_attr['key'] == 'domain'
                    and context_attr['value'] == 'awsdocs-neuron.readthedocs-hosted.com'
                    for context_attr in request_body['contextAttributes']
                )

    @pytest.mark.asyncio
    async def test_search_documentation_http_error(self):
        """Test searching AWS documentation with HTTP error."""
        search_phrase = 'test'
        ctx = MockContext()

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError('Connection error')

            response = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            results = response.search_results
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

            response = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            results = response.search_results

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

            response = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            results = response.search_results

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

            response = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )
            results = response.search_results
            assert len(results) == 0
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documentation_with_filters(self):
        """Test searching AWS documentation with product and guide filters."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'facets': {
                'aws-docs-search-product': ['Amazon S3'],
                'aws-docs-search-guide': ['User Guide'],
            },
            'suggestions': [],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # Test both filters
            response = await search_documentation(
                ctx,
                search_phrase='test',
                limit=10,
                product_types=['Amazon S3', 'AWS Lambda'],
                guide_types=['User Guide', 'API Reference'],
            )
            args, kwargs = mock_post.call_args
            context_attrs = kwargs['json']['contextAttributes']
            assert {'key': 'aws-docs-search-product', 'value': 'Amazon S3'} in context_attrs
            assert {'key': 'aws-docs-search-product', 'value': 'AWS Lambda'} in context_attrs
            assert {'key': 'aws-docs-search-guide', 'value': 'User Guide'} in context_attrs
            assert {'key': 'aws-docs-search-guide', 'value': 'API Reference'} in context_attrs
            assert response.facets == {
                'product_types': ['Amazon S3'],
                'guide_types': ['User Guide'],
            }

            # Test only product filter
            await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=['Amazon S3'], guide_types=None
            )
            args, kwargs = mock_post.call_args
            context_attrs = kwargs['json']['contextAttributes']
            assert {'key': 'aws-docs-search-product', 'value': 'Amazon S3'} in context_attrs

            # Test only guide filter
            await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=['User Guide']
            )
            args, kwargs = mock_post.call_args
            context_attrs = kwargs['json']['contextAttributes']
            assert {'key': 'aws-docs-search-guide', 'value': 'User Guide'} in context_attrs

    @pytest.mark.asyncio
    async def test_search_documentation_with_sections(self):
        """Test searching AWS documentation with section summaries included in results."""
        search_phrase = 'S3 bucket configuration'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-sections',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/bucket-configuration.html',
                        'title': 'S3 Bucket Configuration Guide',
                        'metadata': {
                            'sections': [
                                'Bucket Naming Rules',
                                'Access Control Settings',
                                'Versioning Configuration',
                            ],
                        },
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/basic-setup.html',
                        'title': 'S3 Basic Setup',
                        'summary': 'Basic S3 setup instructions',
                        'metadata': {
                            # No sections for this result
                        },
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )

            assert len(results.search_results) == 2
            assert results.query_id == 'test-query-sections'

            first_result = results.search_results[0]
            assert first_result.rank_order == 1
            assert (
                first_result.url
                == 'https://docs.aws.amazon.com/s3/latest/userguide/bucket-configuration.html'
            )
            assert first_result.title == 'S3 Bucket Configuration Guide'
            # seo_abstract is no longer used for context; with no summary/suggestionBody it is None.
            assert first_result.context is None

            assert first_result.sections is not None
            assert len(first_result.sections) == 3
            assert first_result.sections == [
                'Bucket Naming Rules',
                'Access Control Settings',
                'Versioning Configuration',
            ]

            second_result = results.search_results[1]
            assert second_result.rank_order == 2
            assert (
                second_result.url
                == 'https://docs.aws.amazon.com/s3/latest/userguide/basic-setup.html'
            )
            assert second_result.title == 'S3 Basic Setup'
            assert second_result.context == 'Basic S3 setup instructions'

            assert second_result.sections is None

            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documentation_with_recommended_sections(self):
        """recommended_sections is lifted to a top-level field, parallel to sections."""
        search_phrase = 'S3 object lock'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-recommended',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/object-lock-managing.html',
                        'title': 'S3 Object Lock',
                        'metadata': {
                            'seo_abstract': 'Managing S3 Object Lock',
                            'sections': ['Permissions', 'Bypassing governance mode'],
                            'recommended_sections': [
                                'Managing S3 Lifecycle policies with Object Lock',
                                'Uploading objects to an Object Lock enabled bucket',
                            ],
                        },
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/basic.html',
                        'title': 'Basic',
                        'summary': 'No recommended sections here',
                        'metadata': {},
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(
                ctx, search_phrase=search_phrase, limit=10, product_types=None, guide_types=None
            )

            first_result = results.search_results[0]
            # Both fields surface independently at the top level
            assert first_result.sections == ['Permissions', 'Bypassing governance mode']
            assert first_result.recommended_sections == [
                'Managing S3 Lifecycle policies with Object Lock',
                'Uploading objects to an Object Lock enabled bucket',
            ]

            # No error on absent recommended_sections
            second_result = results.search_results[1]
            assert second_result.recommended_sections is None

            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documentation_recommended_sections_filters_and_ignores_non_list(self):
        """Empty/non-string entries are dropped; a non-list value yields None."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'test-query-rec-edge',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/a.html',
                        'title': 'A',
                        'metadata': {
                            # falsy and non-string entries are filtered out
                            'recommended_sections': ['Keep me', '', None, 42, 'Also keep'],
                        },
                    }
                },
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/s3/latest/userguide/b.html',
                        'title': 'B',
                        'metadata': {
                            # non-list value is ignored entirely
                            'recommended_sections': 'not-a-list',
                        },
                    }
                },
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=None
            )

            assert results.search_results[0].recommended_sections == ['Keep me', 'Also keep']
            assert results.search_results[1].recommended_sections is None

            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documentation_surfaces_known_response_metadata_fields(self):
        """Known response-level metadata fields are surfaced; unknown fields are dropped."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'qid',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/x',
                        'title': 'X',
                        'suggestionBody': 'desc',
                    }
                }
            ],
            'metadata': {
                'discovered_services': [{'name': 'Amazon S3'}],
                'related_tasks': [
                    {
                        'name': 'enable Object Lock',
                        'description': '...',
                        'urls': [
                            {
                                'url_name': '/AmazonS3/latest/userguide/lock.html',
                                'url_description': 'Object Lock overview',
                            }
                        ],
                    }
                ],
                'unknown_field_a': 'should-not-appear',
                'unknown_field_b': {'foo': 'bar'},
            },
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=None
            )

            assert response.metadata is not None
            assert response.metadata.discovered_services is not None
            assert response.metadata.discovered_services[0].name == 'Amazon S3'
            assert response.metadata.related_tasks is not None
            assert response.metadata.related_tasks[0].name == 'enable Object Lock'
            metadata_dump = response.metadata.model_dump(exclude_none=True)
            assert 'unknown_field_a' not in metadata_dump
            assert 'unknown_field_b' not in metadata_dump

    @pytest.mark.asyncio
    async def test_search_documentation_no_metadata_when_proxy_omits_it(self):
        """Responses without a metadata block leave SearchResponse.metadata as None."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'qid',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/x',
                        'title': 'X',
                        'suggestionBody': 'desc',
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=None
            )

            assert response.metadata is None

    @pytest.mark.asyncio
    async def test_search_documentation_drops_malformed_response_metadata(self):
        """A malformed response-level metadata block is dropped, not raised."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'qid',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/x',
                        'title': 'X',
                        'suggestionBody': 'desc',
                    }
                }
            ],
            # discovered_services items require a string `name`; a non-dict entry
            # makes model_validate raise (ValidationError) unless guarded.
            'metadata': {'discovered_services': ['not-a-dict']},
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=None
            )

            # Search succeeded; bad metadata was dropped rather than raised.
            assert len(response.search_results) == 1
            assert response.search_results[0].url == 'https://docs.aws.amazon.com/x'
            assert response.metadata is None

    @pytest.mark.asyncio
    async def test_search_documentation_drops_malformed_result_metadata(self):
        """A malformed per-result metadata block is dropped, not raised."""
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'queryId': 'qid',
            'suggestions': [
                {
                    'textExcerptSuggestion': {
                        'link': 'https://docs.aws.amazon.com/x',
                        'title': 'X',
                        'suggestionBody': 'desc',
                        'metadata': {
                            'sections': ['Overview'],
                            # additional_urls entries require a string `url`; a bare
                            # string entry makes model_validate raise unless guarded.
                            'additional_urls': ['not-a-dict'],
                        },
                    }
                }
            ],
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = await search_documentation(
                ctx, search_phrase='test', limit=10, product_types=None, guide_types=None
            )

            result = response.search_results[0]
            assert result.url == 'https://docs.aws.amazon.com/x'
            assert result.sections == ['Overview']
            assert result.metadata is None


class TestRecommend:
    """Tests for the recommend function."""

    @pytest.mark.asyncio
    async def test_recommend(self):
        """Test getting content recommendations."""
        url = 'https://docs.aws.amazon.com/test'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.json.return_value = {
            'new': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/rec1',
                        'assetTitle': 'Recommendation 1',
                        'dateCreated': '2026-01-01',
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
            assert results[0].context == 'New content added on 2026-01-01'
            assert results[1].url == 'https://docs.aws.amazon.com/rec2'
            assert results[1].title == 'Recommendation 2'
            assert results[1].context == 'This is recommendation 2.'
            mock_get.assert_called_once()

            assert mock_get.call_args.args[0] == (
                'https://api.contentrecs.docs.aws.com/v1/recommendations'
            )
            params = mock_get.call_args.kwargs['params']
            assert params['path'] == 'https://docs.aws.amazon.com/test'
            assert params['session']

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
        mock_response.url = url
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            results = await recommend(ctx, url=url)

            assert len(results) == 1
            assert results[0].url == ''
            assert 'Error parsing recommendations:' in results[0].title
            assert results[0].context is None

    @staticmethod
    async def _requested_path(url: str) -> str:
        """Call recommend with an empty API response and return the path it asked about."""
        response = MagicMock(status_code=200)
        response.json.return_value = {}
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock, return_value=response) as get:
            await recommend(MockContext(), url=url)
        return get.call_args.kwargs['params']['path']

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'url',
        [
            'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.md',
            'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.md#overview',
            'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html?x=1',
        ],
    )
    async def test_recommend_asks_about_the_html_page(self, url):
        """Recommendations are indexed by .html page, so a followed .md link maps to one."""
        assert await self._requested_path(url) == (
            'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html'
        )

    @pytest.mark.asyncio
    async def test_recommend_encodes_the_path(self):
        """A path with query-significant characters cannot add parameters to the API call."""
        url = 'https://docs.aws.amazon.com/lambda/latest/dg/a&session=forged'
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={})

        real_client = httpx.AsyncClient
        with patch(
            'httpx.AsyncClient',
            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
        ):
            await recommend(MockContext(), url=url)

        query = parse_qs(requests[0].url.query.decode())
        assert query['path'] == [url]
        assert query['session'] != ['forged']

    @pytest.mark.asyncio
    async def test_recommend_rejects_unsupported_domain(self):
        """A URL outside the documentation domains is rejected before any request."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as get:
            with pytest.raises(ValueError, match='URL must be from list of supported domains'):
                await recommend(MockContext(), url='not a url')
        get.assert_not_called()


class TestSearchTable:
    """Tests for the search_table function."""

    @pytest.mark.asyncio
    async def test_search_table_success(self):
        """Test successful table search."""
        url = 'https://docs.aws.amazon.com/general/latest/gr/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>Service quotas</h2>
            <table><thead><tr><th>Name</th><th>Value</th></tr></thead>
            <tbody><tr><td>Foo quota</td><td>100</td></tr>
            <tr><td>Bar quota</td><td>200</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await search_table(
                ctx, url=url, section_title='Service quotas', query='Foo', max_rows=20
            )

            assert result.tables_with_matches == 1
            assert result.results[0].matched_rows == 1
            assert result.results[0].rows[0]['Name'] == 'Foo quota'

    @pytest.mark.asyncio
    async def test_search_table_invalid_url(self):
        """Test that invalid URLs are rejected."""
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must be from list of supported domains'):
            await search_table(
                ctx,
                url='https://example.com/page.html',
                section_title='Test',
                query='foo',
                max_rows=20,
            )

    @pytest.mark.asyncio
    async def test_search_table_url_must_end_with_html(self):
        """Test that URLs must end with .html."""
        ctx = MockContext()

        with pytest.raises(ValueError, match='URL must end with .html'):
            await search_table(
                ctx,
                url='https://docs.aws.amazon.com/test.json',
                section_title='Test',
                query='foo',
                max_rows=20,
            )

    @pytest.mark.asyncio
    async def test_search_table_empty_query(self):
        """Test that empty query is rejected."""
        ctx = MockContext()

        with pytest.raises(ValueError, match='query parameter cannot be empty'):
            await search_table(
                ctx,
                url='https://docs.aws.amazon.com/test.html',
                section_title='Test',
                query='',
                max_rows=20,
            )

    @pytest.mark.asyncio
    async def test_search_table_no_matches_returns_hint(self):
        """Test that zero matches includes a hint."""
        url = 'https://docs.aws.amazon.com/general/latest/gr/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>Quotas</h2>
            <table><thead><tr><th>Name</th></tr></thead>
            <tbody><tr><td>Something</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await search_table(
                ctx, url=url, section_title='Quotas', query='nonexistent', max_rows=20
            )

            assert result.tables_with_matches == 0
            assert result.results == []
            assert result.hint is not None

    @pytest.mark.asyncio
    async def test_search_table_section_not_found_returns_available(self):
        """Test that wrong section title returns available sections."""
        url = 'https://docs.aws.amazon.com/general/latest/gr/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>Real Section</h2>
            <table><thead><tr><th>A</th></tr></thead>
            <tbody><tr><td>1</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await search_table(
                ctx, url=url, section_title='Wrong Section', query='foo', max_rows=20
            )

            assert result.hint is not None
            assert 'Real Section' in result.hint

    @pytest.mark.asyncio
    async def test_search_table_optional_section_title(self):
        """Test that section_title can be omitted to search all tables."""
        url = 'https://docs.aws.amazon.com/general/latest/gr/test.html'
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url
        mock_response.text = """<html><body>
            <h2>Section A</h2>
            <table><thead><tr><th>Name</th></tr></thead>
            <tbody><tr><td>Alpha</td></tr></tbody></table>
            <h2>Section B</h2>
            <table><thead><tr><th>Name</th></tr></thead>
            <tbody><tr><td>Beta</td></tr></tbody></table>
        </body></html>"""

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await search_table(
                ctx, url=url, section_title=None, query='Beta', max_rows=20
            )

            assert result.tables_with_matches == 1
            assert 'Beta' in str(result.results[0].rows)


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


class TestMarkdownPageUrls:
    """The read tools accept the relative .md links published Markdown carries."""

    MD_URL = 'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.md'
    HTML_URL = 'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html'
    MODULE = 'awslabs.aws_documentation_mcp_server.server_aws'

    @pytest.mark.asyncio
    async def test_read_documentation_fetches_html_page_for_md_url(self):
        """read_documentation reads the .html page at the .md URL's path."""
        with patch(f'{self.MODULE}.read_documentation_impl', new_callable=AsyncMock) as impl:
            await read_documentation(
                MockContext(), url=self.MD_URL, max_length=1000, start_index=0
            )
        assert impl.call_args.args[1] == self.HTML_URL

    @pytest.mark.asyncio
    async def test_read_sections_fetches_html_page_for_md_url(self):
        """read_sections reads the .html page at the .md URL's path."""
        with patch(f'{self.MODULE}.read_sections_impl', new_callable=AsyncMock) as impl:
            await read_sections(MockContext(), url=self.MD_URL, section_titles=['Overview'])
        assert impl.call_args.args[1] == self.HTML_URL

    @pytest.mark.asyncio
    async def test_search_table_fetches_html_page_for_md_url(self):
        """search_table parses HTML, so a .md URL must still reach the .html page."""
        with patch(f'{self.MODULE}.search_table_impl', new_callable=AsyncMock) as impl:
            await search_table(
                MockContext(), url=self.MD_URL, section_title=None, query='foo', max_rows=20
            )
        assert impl.call_args.args[1] == self.HTML_URL

    @staticmethod
    def _mock_client(text: str, content_type: str, url: str) -> MagicMock:
        response = MagicMock(status_code=200, url=url, text=text)
        response.headers = {'content-type': content_type}
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.get = AsyncMock(return_value=response)
        return client

    @pytest.mark.asyncio
    async def test_md_url_fetches_html_page_with_cached_query_id(self):
        """A .md link from a search result's page still finds that result's query_id."""
        from awslabs.aws_documentation_mcp_server.models import SearchResponse, SearchResult
        from awslabs.aws_documentation_mcp_server.server_utils import (
            SEARCH_RESULT_CACHE,
            add_search_result_cache_item,
        )

        SEARCH_RESULT_CACHE.clear()
        add_search_result_cache_item(
            SearchResponse(
                search_results=[SearchResult(rank_order=1, title='t', url=self.HTML_URL)],
                facets=None,
                query_id='qid-1',
            )
        )
        client = self._mock_client('# Sync\n\nSee [a](other.md).', 'text/markdown', self.HTML_URL)
        try:
            with patch('httpx.AsyncClient', return_value=client):
                result = await read_documentation(
                    MockContext(), url=f'{self.MD_URL}#overview', max_length=1000, start_index=0
                )
        finally:
            SEARCH_RESULT_CACHE.clear()

        requested = urlparse(client.get.call_args.args[0])
        assert f'{requested.scheme}://{requested.netloc}{requested.path}' == self.HTML_URL
        assert parse_qs(requested.query)['query_id'] == ['qid-1']
        assert '[a](other.md)' in result

    @pytest.mark.asyncio
    async def test_search_table_md_url_requests_html(self):
        """search_table parses HTML, so a .md URL requests the .html page as HTML."""
        html = '<html><body><h2>T</h2><table><tr><th>A</th></tr><tr><td>foo</td></tr></table></body></html>'
        client = self._mock_client(html, 'text/html', self.HTML_URL)
        with patch('httpx.AsyncClient', return_value=client):
            await search_table(
                MockContext(), url=self.MD_URL, section_title=None, query='foo', max_rows=20
            )

        assert urlparse(client.get.call_args.args[0]).path.endswith('/invocation-sync.html')
        assert client.get.call_args.kwargs['headers']['Accept'].startswith('text/html')
