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
)
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, unquote, urlparse


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
    async def test_read_documentation_with_domain_modification(self):
        """Test reading AWS documentation with domain modification."""
        url = 'https://awsdocs-neuron.readthedocs-hosted.com/test.html'
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

            result = await read_documentation(ctx, url=url, max_length=10000, start_index=0)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
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

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            assert 'Failed to fetch' in result
            assert 'Connection error' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_sections_no_sections_found(self):
        """Test read_sections when no requested sections exist."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Nonexistent Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
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
        mock_response.text = '<html><body><h1>This is a page<h1/><h2>Best practices</h2><p>Content here.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            # Whitespace normalization should match despite extra spaces/newlines
            assert 'Content here' in result

    @pytest.mark.asyncio
    async def test_read_sections_non_html_content(self):
        """Test read_sections with non-HTML content."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Introduction']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'Plain text content without HTML'
        mock_response.headers = {'content-type': 'text/plain'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.is_html_content'
            ) as mock_is_html:
                mock_is_html.return_value = False

                result = await read_sections(ctx, url=url, section_titles=section_titles)

                assert 'Cannot extract sections from non-HTML content' in result
                assert 'read_documentation tool instead' in result
                mock_get.assert_called_once()

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

            result = await read_sections(ctx, url=url, section_titles=section_titles)

            assert 'Failed to fetch' in result
            assert 'status code 500' in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_sections_extract_content_error(self):
        """Test read_sections when extract_content_from_html returns error."""
        url = 'https://docs.aws.amazon.com/test.html'
        section_titles = ['Test Section']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h2>Test Section</h2><p>Content.</p></body></html>'
        mock_response.headers = {'content-type': 'text/html'}

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch(
                'awslabs.aws_documentation_mcp_server.server_utils.extract_content_from_html'
            ) as mock_extract:
                # Simulate extract_content_from_html returning an error
                mock_extract.return_value = '<e>Failed to convert HTML to markdown</e>'

                with pytest.raises(ValueError, match='Failed to convert HTML to markdown'):
                    await read_sections(ctx, url=url, section_titles=section_titles)

    @pytest.mark.asyncio
    async def test_read_sections_end_to_end_workflow(self):
        """Test complete end-to-end workflow and verify only h2 sections extracted."""
        url = 'https://docs.aws.amazon.com/s3/latest/userguide/test.html'
        section_titles = ['Bucket Naming Rules', 'Examples']
        ctx = MockContext()

        mock_response = MagicMock()
        mock_response.status_code = 200
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
                            'seo_abstract': 'Complete guide to configuring S3 buckets',
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
            assert first_result.context == 'Complete guide to configuring S3 buckets'

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
