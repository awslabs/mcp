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
"""Tests for utility functions in the AWS Documentation MCP Server."""

import httpx
import os
import pytest
from awslabs.aws_documentation_mcp_server.util import (
    Heading,
    SectionIndex,
    UnreadablePageError,
    add_search_intent_to_search_request,
    anchor_section,
    enforce_redirect_allowlist,
    extract_content_and_anchors,
    extract_content_from_html,
    extract_sections_from_html,
    format_documentation_result,
    has_empty_link_target,
    has_readable_text,
    is_html_content,
    locate_headings,
    markdown_heading_candidates,
    parse_recommendation_results,
    section_markdown,
    url_matches_allowlist,
)
from unittest.mock import MagicMock, patch


ALLOWLIST = (
    r'^https?://docs\.aws\.amazon\.com/',
    r'^https?://awsdocs-neuron\.readthedocs-hosted\.com/',
)


class TestUrlMatchesAllowlist:
    """Tests for url_matches_allowlist (domain-only, no extension check)."""

    def test_docs_host_allowed(self):
        """docs.aws.amazon.com is on the allowlist."""
        assert url_matches_allowlist('https://docs.aws.amazon.com/s3/latest/x.html', ALLOWLIST)

    def test_neuron_host_allowed(self):
        """The third-party Neuron docs host is on the allowlist."""
        assert url_matches_allowlist(
            'https://awsdocs-neuron.readthedocs-hosted.com/x.html', ALLOWLIST
        )

    def test_directory_url_without_html_allowed(self):
        """Redirect targets are often directory URLs (no .html); the domain check must pass them."""
        assert url_matches_allowlist(
            'https://docs.aws.amazon.com/powershell/v4/reference/', ALLOWLIST
        )

    def test_imds_blocked(self):
        """The link-local IMDS endpoint is not on the allowlist."""
        assert not url_matches_allowlist('http://169.254.169.254/latest/meta-data/', ALLOWLIST)

    def test_arbitrary_host_blocked(self):
        """An arbitrary external host is not on the allowlist."""
        assert not url_matches_allowlist('https://evil.example.com/x', ALLOWLIST)

    def test_lookalike_host_blocked(self):
        """A host that merely contains the allowed domain as a substring is not allowed."""
        assert not url_matches_allowlist('https://docs.aws.amazon.com.evil.com/x', ALLOWLIST)


class TestEnforceRedirectAllowlist:
    """Tests for the redirect-revalidation event hook."""

    def _response(self, status, location=None, req_url='https://docs.aws.amazon.com/foo.html'):
        """Build an httpx.Response with an optional Location header for hook testing."""
        headers = {'location': location} if location else {}
        return httpx.Response(status, headers=headers, request=httpx.Request('GET', req_url))

    @pytest.mark.asyncio
    async def test_off_allowlist_redirect_blocked(self):
        """A redirect whose target is off the allowlist (IMDS) is rejected."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        resp = self._response(302, 'http://169.254.169.254/latest/meta-data/')
        with pytest.raises(httpx.RequestError, match='non-allowlisted'):
            await hook(resp)

    @pytest.mark.asyncio
    async def test_on_allowlist_redirect_allowed(self):
        """A same-domain canonicalization redirect is allowed."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        resp = self._response(301, 'https://docs.aws.amazon.com/lambda/latest/dg/')
        await hook(resp)  # must not raise

    @pytest.mark.asyncio
    async def test_relative_redirect_resolved_against_request(self):
        """A relative Location resolves against the request URL and stays on the allowlist."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        resp = self._response(301, '/lambda/latest/dg/')
        await hook(resp)  # must not raise

    @pytest.mark.asyncio
    async def test_relative_redirect_cannot_escape_host(self):
        """A protocol-relative Location to another host is rejected."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        resp = self._response(302, '//169.254.169.254/latest/meta-data/')
        with pytest.raises(httpx.RequestError, match='non-allowlisted'):
            await hook(resp)

    @pytest.mark.asyncio
    async def test_non_redirect_response_is_noop(self):
        """A 200 response is not a redirect and passes through untouched."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        await hook(self._response(200))  # must not raise

    @pytest.mark.asyncio
    async def test_redirect_without_location_is_noop(self):
        """A 3xx with no Location header has nothing to validate and passes through."""
        hook = enforce_redirect_allowlist(ALLOWLIST)
        await hook(self._response(302))  # no Location header -> nothing to validate


class TestIsHtmlContent:
    """Tests for is_html_content function."""

    def test_html_tag_in_content(self):
        """Test detection of HTML content by HTML tag."""
        content = '<html><body>Test content</body></html>'
        assert is_html_content(content, '') is True

    def test_html_content_type(self):
        """Test detection of HTML content by content type."""
        content = 'Some content'
        assert is_html_content(content, 'text/html; charset=utf-8') is True

    def test_empty_content_type(self):
        """Test detection with empty content type."""
        content = 'Some content without HTML tags'
        assert is_html_content(content, '') is True

    def test_non_html_content(self):
        """Test detection of non-HTML content."""
        content = 'Plain text content'
        assert is_html_content(content, 'text/plain') is False


class TestFormatDocumentationResult:
    """Tests for format_documentation_result function."""

    def test_normal_content(self):
        """Test formatting normal content."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'Test content'
        result = format_documentation_result(url, content, 0, 100)
        assert result == f'AWS Documentation from {url}:\n\n{content}'

    def test_start_index_beyond_content(self):
        """Test when start_index is beyond content length."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'Test content'
        result = format_documentation_result(url, content, 100, 100)
        assert '<e>No more content available.</e>' in result

    def test_empty_truncated_content(self):
        """Test when truncated content is empty."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'Test content'
        # This should result in empty truncated content
        result = format_documentation_result(url, content, 12, 100)
        assert '<e>No more content available.</e>' in result

    def test_truncated_content_with_more_available(self):
        """Test when content is truncated with more available."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'A' * 200  # 200 characters
        max_length = 100
        result = format_documentation_result(url, content, 0, max_length)
        assert 'A' * 100 in result
        assert 'start_index=100' in result
        assert 'Content truncated' in result

    def test_truncated_content_exact_fit(self):
        """Test when content fits exactly in max_length."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'A' * 100
        result = format_documentation_result(url, content, 0, 100)
        assert 'Content truncated' not in result

    def test_content_shorter_than_max_length(self):
        """Test when content is shorter than max_length."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'A' * 50  # 50 characters
        max_length = 100
        result = format_documentation_result(url, content, 0, max_length)
        assert 'A' * 50 in result
        assert 'Content truncated' not in result

    def test_partial_content_with_remaining(self):
        """Test when reading partial content with more remaining."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'A' * 300  # 300 characters
        start_index = 100
        max_length = 100
        result = format_documentation_result(url, content, start_index, max_length)
        assert 'A' * 100 in result
        assert 'start_index=200' in result
        assert 'Content truncated' in result

    def test_partial_content_at_end(self):
        """Test when reading partial content at the end."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'A' * 150  # 150 characters
        start_index = 100
        max_length = 100
        result = format_documentation_result(url, content, start_index, max_length)
        assert 'A' * 50 in result
        assert 'Content truncated' not in result


class TestMarkdownifyOptions:
    """The markdownify options this package pins, and what breaks if they move."""

    def test_link_titles_are_not_repeated_from_the_href(self):
        """default_title=True would render [text](url "url"), doubling every href."""
        html = (
            '<html><body><main><p><a href="https://x.example/a">Text</a></p></main></body></html>'
        )
        out = extract_content_from_html(html)
        assert '[Text](https://x.example/a)' in out
        assert '"https://x.example/a")' not in out

    def test_bare_urls_keep_the_bracket_form(self):
        """autolinks=True would emit <url> instead of [url](url), changing every bare link."""
        html = (
            '<html><body><main><p>'
            '<a href="https://x.example/a">https://x.example/a</a>'
            '</p></main></body></html>'
        )
        out = extract_content_from_html(html)
        assert '[https://x.example/a](https://x.example/a)' in out
        assert '<https://x.example/a>' not in out


class TestExtractContentFromHtml:
    """Tests for extract_content_from_html function."""

    @patch('bs4.BeautifulSoup')
    @patch('markdownify.markdownify')
    def test_successful_extraction(self, mock_markdownify, mock_soup):
        """Test successful HTML content extraction."""
        # Setup mocks
        mock_soup_instance = mock_soup.return_value
        mock_soup_instance.body = mock_soup_instance
        mock_soup_instance.select_one.return_value = None  # No main content found
        mock_markdownify.return_value = 'Test content'

        # Call function
        result = extract_content_from_html('<html><body><p>Test content</p></body></html>')

        # Assertions
        assert 'Test content' in result
        mock_soup.assert_called_once()
        mock_markdownify.assert_called_once()

    @patch('bs4.BeautifulSoup')
    def test_empty_content(self, mock_soup):
        """Test extraction with empty content."""
        # Call function with empty content
        with pytest.raises(UnreadablePageError, match='Empty HTML content'):
            extract_content_from_html('')

        mock_soup.assert_not_called()

    def test_extract_content_with_programlisting(self):
        """Test extraction of HTML content with programlisting tags for code examples."""
        # Load the test HTML file
        test_file_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'lambda_sns_raw.html'
        )
        with open(test_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Extract content
        markdown_content = extract_content_from_html(html_content)

        # Verify TypeScript code block is properly extracted
        assert '```typescript' in markdown_content or '```' in markdown_content
        assert "import { Construct } from 'constructs';" in markdown_content
        assert "import { Stack, StackProps } from 'aws-cdk-lib';" in markdown_content
        assert (
            'import { LambdaToSns, LambdaToSnsProps } from "@aws-solutions-constructs/aws-lambda-sns";'
            in markdown_content
        )

        # Verify Python code block is properly extracted
        assert (
            'from aws_solutions_constructs.aws_lambda_sns import LambdaToSns' in markdown_content
        )
        assert 'from aws_cdk import (' in markdown_content
        assert 'aws_lambda as _lambda,' in markdown_content

        # Verify Java code block is properly extracted
        assert 'import software.constructs.Construct;' in markdown_content
        assert 'import software.amazon.awscdk.Stack;' in markdown_content
        assert 'import software.amazon.awscdk.services.lambda.*;' in markdown_content

        # Verify tab structure is preserved in some form
        assert 'Typescript' in markdown_content
        assert 'Python' in markdown_content
        assert 'Java' in markdown_content

        # Verify the position of code blocks relative to the rest of the markdown
        # Check that "Overview" section appears before the code blocks
        overview_pos = markdown_content.find('Overview')
        typescript_code_pos = markdown_content.find("import { Construct } from 'constructs';")
        assert overview_pos > 0, 'Overview section not found'
        assert typescript_code_pos > overview_pos, (
            'TypeScript code block should appear after Overview section'
        )

        # Check that code blocks appear in the correct order (TypeScript, Python, Java)
        python_code_pos = markdown_content.find(
            'from aws_solutions_constructs.aws_lambda_sns import LambdaToSns'
        )
        java_code_pos = markdown_content.find('import software.constructs.Construct;')
        assert python_code_pos > typescript_code_pos, (
            'Python code block should appear after TypeScript code block'
        )
        assert java_code_pos > python_code_pos, (
            'Java code block should appear after Python code block'
        )

        # Check that "Pattern Construct Props" section appears after the code blocks
        props_pos = markdown_content.find('Pattern Construct Props')
        assert props_pos > typescript_code_pos, (
            'Pattern Construct Props section should appear after code blocks'
        )

    def test_extract_content_from_html(self):
        """Test extracting content from HTML."""
        html = '<html><body><h1>Test</h1><p>This is a test.</p></body></html>'
        with patch('bs4.BeautifulSoup') as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup
            with patch('markdownify.markdownify') as mock_markdownify:
                mock_markdownify.return_value = '# Test\n\nThis is a test.'
                result = extract_content_from_html(html)
                assert result == '# Test\n\nThis is a test.'
                mock_bs.assert_called_once()
                mock_markdownify.assert_called_once()

    def test_extract_content_from_html_no_content(self):
        """Test extracting content from HTML with no content."""
        html = '<html><body></body></html>'
        with patch('bs4.BeautifulSoup') as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup
            mock_soup.body = None
            with pytest.raises(UnreadablePageError):
                extract_content_from_html(html)
            mock_bs.assert_called_once()

    def test_extract_content_exception_during_conversion(self):
        """Test that exceptions during markdownify are caught and returned as error."""
        html = '<html><body><p>Test</p></body></html>'
        with patch('markdownify.markdownify', side_effect=Exception('conversion failed')):
            with pytest.raises(
                UnreadablePageError, match='Error converting HTML to Markdown: conversion failed'
            ):
                extract_content_from_html(html)


class TestFormatDocumentationResultEdgeCases:
    """Tests for edge cases in format_documentation_result."""

    def test_zero_max_length_returns_no_content(self):
        """When max_length is 0, truncated_content is empty, returns no-content message."""
        url = 'https://docs.aws.amazon.com/test'
        content = 'Some content here'
        result = format_documentation_result(url, content, 0, 0)
        assert '<e>No more content available.</e>' in result


class TestParseRecommendationResults:
    """Tests for parse_recommendation_results function."""

    def test_empty_data(self):
        """Test parsing empty data."""
        data = {}
        results = parse_recommendation_results(data)
        assert results == []

    def test_journey_recommendations(self):
        """Test parsing journey recommendations."""
        data = {
            'journey': {
                'items': [
                    {
                        'intent': 'Learn',
                        'urls': [
                            {'url': 'https://docs.aws.amazon.com/learn1', 'assetTitle': 'Learn 1'}
                        ],
                    },
                    {
                        'intent': 'Build',
                        'urls': [
                            {'url': 'https://docs.aws.amazon.com/build1', 'assetTitle': 'Build 1'}
                        ],
                    },
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].url == 'https://docs.aws.amazon.com/learn1'
        assert results[0].title == 'Learn 1'
        assert results[0].context == 'Intent: Learn'
        assert results[1].url == 'https://docs.aws.amazon.com/build1'
        assert results[1].title == 'Build 1'
        assert results[1].context == 'Intent: Build'

    def test_new_content_recommendations(self):
        """Test parsing new content recommendations."""
        data = {
            'new': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/new1',
                        'assetTitle': 'New 1',
                        'dateCreated': '2023-01-01',
                    },
                    {'url': 'https://docs.aws.amazon.com/new2', 'assetTitle': 'New 2'},
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].url == 'https://docs.aws.amazon.com/new1'
        assert results[0].title == 'New 1'
        assert results[0].context == 'New content added on 2023-01-01'
        assert results[1].url == 'https://docs.aws.amazon.com/new2'
        assert results[1].title == 'New 2'
        assert results[1].context == 'New content'

    def test_similar_recommendations(self):
        """Test parsing similar recommendations."""
        data = {
            'similar': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/similar1',
                        'assetTitle': 'Similar 1',
                        'abstract': 'Abstract for similar 1',
                    },
                    {'url': 'https://docs.aws.amazon.com/similar2', 'assetTitle': 'Similar 2'},
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].url == 'https://docs.aws.amazon.com/similar1'
        assert results[0].title == 'Similar 1'
        assert results[0].context == 'Abstract for similar 1'
        assert results[1].url == 'https://docs.aws.amazon.com/similar2'
        assert results[1].title == 'Similar 2'
        assert results[1].context == 'Similar content'

    def test_all_recommendation_types(self):
        """Test parsing all recommendation types together."""
        data = {
            'journey': {
                'items': [
                    {
                        'intent': 'Learn',
                        'urls': [
                            {'url': 'https://docs.aws.amazon.com/journey', 'assetTitle': 'Journey'}
                        ],
                    }
                ]
            },
            'new': {'items': [{'url': 'https://docs.aws.amazon.com/new', 'assetTitle': 'New'}]},
            'similar': {
                'items': [{'url': 'https://docs.aws.amazon.com/similar', 'assetTitle': 'Similar'}]
            },
        }
        results = parse_recommendation_results(data)
        assert len(results) == 3
        # Check that we have one of each type (order doesn't matter for this test)
        urls = [r.url for r in results]
        assert 'https://docs.aws.amazon.com/journey' in urls
        assert 'https://docs.aws.amazon.com/new' in urls
        assert 'https://docs.aws.amazon.com/similar' in urls


class TestAddSearchIntentToSearchRequest:
    """Tests for add_search_intent_to_search_request function."""

    def test_valid_search_intent_simple(self):
        """Test adding a simple valid search intent."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'how to deploy'
        result = add_search_intent_to_search_request(search_url, search_intent)
        assert result == 'https://docs.aws.amazon.com/search&search_intent=how+to+deploy'

    def test_valid_search_intent_with_special_chars(self):
        """Test adding search intent with special characters that need URL encoding."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'how to configure S3 bucket & policies?'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # quote_plus should encode spaces as '+' and special chars as '%XX'
        assert (
            result
            == 'https://docs.aws.amazon.com/search&search_intent=how+to+configure+S3+bucket+%26+policies%3F'
        )

    def test_valid_search_intent_with_unicode(self):
        """Test adding search intent with unicode characters."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'déployer une instance'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Verify the URL is properly encoded (unicode characters should be percent-encoded)
        assert (
            result == 'https://docs.aws.amazon.com/search&search_intent=d%C3%A9ployer+une+instance'
        )

    def test_valid_search_intent_with_multiple_words(self):
        """Test adding search intent with multiple words."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'create table with provisioned throughput'
        result = add_search_intent_to_search_request(search_url, search_intent)
        assert (
            result
            == 'https://docs.aws.amazon.com/search&search_intent=create+table+with+provisioned+throughput'
        )

    def test_valid_search_intent_with_slashes(self):
        """Test adding search intent with forward slashes."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'REST/HTTP API configuration'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Forward slashes should be encoded as %2F
        assert (
            result
            == 'https://docs.aws.amazon.com/search&search_intent=REST%2FHTTP+API+configuration'
        )

    def test_empty_search_intent(self):
        """Test with empty string search intent (should not add parameter)."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = ''
        result = add_search_intent_to_search_request(search_url, search_intent)
        assert result == 'https://docs.aws.amazon.com/search'
        assert 'search_intent' not in result

    def test_whitespace_only_search_intent(self):
        """Test with whitespace-only search intent (should add parameter with encoded spaces)."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = '   '
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Whitespace is truthy, so it should be added
        assert result == 'https://docs.aws.amazon.com/search'

    def test_search_intent_with_numbers(self):
        """Test adding search intent with numbers."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'configure RDS with 1000 IOPS'
        result = add_search_intent_to_search_request(search_url, search_intent)
        assert (
            result
            == 'https://docs.aws.amazon.com/search&search_intent=configure+RDS+with+1000+IOPS'
        )

    def test_search_intent_with_punctuation(self):
        """Test adding search intent with various punctuation marks."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'metrics, alarms & dashboards - how-to guide!'
        result = add_search_intent_to_search_request(search_url, search_intent)
        assert (
            result
            == 'https://docs.aws.amazon.com/search&search_intent=metrics%2C+alarms+%26+dashboards+-+how-to+guide%21'
        )

    def test_very_long_search_intent(self):
        """Test adding a very long search intent."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'how to create and configure an AWS Lambda function with VPC access and custom IAM roles for processing S3 events'
        result = add_search_intent_to_search_request(search_url, search_intent)
        expected = 'https://docs.aws.amazon.com/search&search_intent=how+to+create+and+configure+an+AWS+Lambda+function+with+VPC+access+and+custom+IAM+roles+for+processing+S3+events'
        assert result == expected

    def test_search_intent_with_equals_sign(self):
        """Test adding search intent with equals sign."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'set parameter=value'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Equals sign should be encoded as %3D
        assert result == 'https://docs.aws.amazon.com/search&search_intent=set+parameter%3Dvalue'

    def test_search_intent_with_tab_character(self):
        """Test adding search intent with tab character."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'tab\tcharacter'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Tab should be encoded as %09
        assert result == 'https://docs.aws.amazon.com/search&search_intent=tab+character'

    def test_search_intent_with_newline(self):
        """Test adding search intent with newline character."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'line\nbreak'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Newline should be encoded as %0A
        assert result == 'https://docs.aws.amazon.com/search&search_intent=line+break'

    def test_search_intent_with_carriage_return(self):
        """Test adding search intent with carriage return."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'carriage\rreturn'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Carriage return should be encoded as %0D
        assert result == 'https://docs.aws.amazon.com/search&search_intent=carriage+return'

    def test_search_intent_with_hash(self):
        """Test adding search intent with hash/pound sign."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'C# programming'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Hash should be encoded as %23
        assert result == 'https://docs.aws.amazon.com/search&search_intent=C%23+programming'

    def test_search_intent_with_percent_sign(self):
        """Test adding search intent with percent sign."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = '100% CPU usage'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Percent sign should be encoded as %25
        assert result == 'https://docs.aws.amazon.com/search&search_intent=100%25+CPU+usage'

    def test_search_intent_with_plus_sign(self):
        """Test adding search intent with plus sign."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'C++'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Plus sign should be encoded as %2B
        assert result == 'https://docs.aws.amazon.com/search&search_intent=C%2B%2B'

    def test_search_intent_with_ampersand(self):
        """Test adding search intent with ampersand."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'S3 & EC2'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Ampersand should be encoded as %26
        assert result == 'https://docs.aws.amazon.com/search&search_intent=S3+%26+EC2'

    def test_search_intent_with_question_mark(self):
        """Test adding search intent with question mark."""
        search_url = 'https://docs.aws.amazon.com/search'
        search_intent = 'what is lambda?'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # Question mark should be encoded as %3F
        assert result == 'https://docs.aws.amazon.com/search&search_intent=what+is+lambda%3F'

    def test_url_with_existing_parameters(self):
        """Test that the function appends to existing URL structure."""
        search_url = 'https://docs.aws.amazon.com/search?foo=bar'
        search_intent = 'test'
        result = add_search_intent_to_search_request(search_url, search_intent)
        # The function simply appends &search_intent=... to the URL
        assert result == 'https://docs.aws.amazon.com/search?foo=bar&search_intent=test'


class TestExtractSectionsFromHtml:
    """Tests for extract_sections_from_html function."""

    def test_empty_input(self):
        """Test with empty HTML content."""
        result = extract_sections_from_html('', ['section1'])
        assert result == 'No content or section titles provided'

    def test_empty_section_list(self):
        """Test with empty section_titles list."""
        result = extract_sections_from_html('<html><body><h1>Test</h1></body></html>', [])
        assert result == 'No content or section titles provided'

    def test_single_section_extraction(self):
        """Test extracting a single section with content."""
        html = """<html><body>
            <h2>Introduction</h2>
            <p>This is the intro.</p>
            <h2>Main Section</h2>
            <p>This is the main content.</p>
            <p>Some more content here.</p>
            <h2>Conclusion</h2>
            <p>This is the end.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Main Section'])
        assert '## Main Section' in result
        assert 'This is the main content.' in result
        assert 'Some more content here.' in result
        assert '## Introduction' not in result
        assert '## Conclusion' not in result

    def test_multiple_sections_extraction(self):
        """Test extracting multiple sections."""
        html = """<html><body>
            <h2>Introduction</h2>
            <p>This is the intro.</p>
            <h2>First Section</h2>
            <p>First content.</p>
            <h2>Second Section</h2>
            <p>Second content.</p>
            <h2>Third Section</h2>
            <p>Third content.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['First Section', 'Third Section'])
        assert '## First Section' in result
        assert 'First content' in result
        assert '## Third Section' in result
        assert 'Third content' in result
        assert '## Second Section' not in result
        assert 'Second content' not in result

    def test_case_insensitive_matching(self):
        """Test case-insensitive section matching."""
        html = """<html><body>
            <h2>Main Section</h2>
            <p>Content here.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['MAIN SECTION'])
        assert '## Main Section' in result
        assert 'Content here' in result

    def test_whitespace_handling(self):
        """Test section titles with leading/trailing whitespace."""
        html = """<html><body>
            <h2>Best practices</h2>
            <p>This is content for best practices.</p>
            <h2>Another Section</h2>
            <p>More content here.</p>
        </body></html>"""
        test_cases = [
            ' Best practices\n',
            '  Best practices  ',
            'Best  practices',
            '\tBest practices\t',
            'Best\npractices',
        ]

        for test_input in test_cases:
            result = extract_sections_from_html(html, [test_input])
            assert '## Best practices' in result, f"Failed to match '{repr(test_input)}'"
            assert 'best practices' in result.lower(), f"Content missing for '{repr(test_input)}'"
            assert '## Another Section' not in result, (
                f"Should not include other sections for '{repr(test_input)}'"
            )

    def test_nested_sections_included(self):
        """Test that subsections within matching sections are included."""
        html = """<html><body>
            <h2>Main Section</h2>
            <p>Main content.</p>
            <h3>Subsection 1</h3>
            <p>Sub content 1.</p>
            <h4>Sub-subsection</h4>
            <p>Sub-sub content.</p>
            <h3>Subsection 2</h3>
            <p>Sub content 2.</p>
            <h2>Another Section</h2>
            <p>Other content.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Main Section'])
        assert '## Main Section' in result
        assert 'Main content' in result
        assert '### Subsection 1' in result
        assert 'Sub content 1' in result
        assert '#### Sub-subsection' in result
        assert 'Sub-sub content' in result
        assert '### Subsection 2' in result
        assert 'Sub content 2' in result
        assert '## Another Section' not in result
        assert 'Other content' not in result

    def test_no_sections_found_with_h2_headings(self):
        """Test when no sections match but document has h2 headings."""
        html = """<html><body>
            <h1>Introduction</h1>
            <p>Intro content.</p>
            <h2>Subsection A</h2>
            <p>Content A.</p>
            <h2>Subsection B</h2>
            <p>Content B.</p>
        </body></html>"""
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_html(html, ['Nonexistent Section'])
        error_msg = str(exc_info.value)
        assert 'No matching sections were found' in error_msg
        assert 'Available sections:' in error_msg
        assert '"Subsection A"' in error_msg
        assert '"Subsection B"' in error_msg

    def test_no_sections_found_without_h2_headings(self):
        """Test when no sections match and no h2 headings exist."""
        html = """<html><body>
            <h1>Introduction</h1>
            <p>This is the intro.</p>
            <h1>Main Section</h1>
            <p>Content here.</p>
        </body></html>"""
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_html(html, ['Nonexistent Section', 'Another Missing'])
        error_msg = str(exc_info.value)
        assert 'This document does not contain subsections' in error_msg

    def test_partial_success(self):
        """Test when some sections found, others missing (graceful handling)."""
        html = """<html><body>
            <h2>Introduction</h2>
            <p>Intro content.</p>
            <h2>Found Section</h2>
            <p>Found content.</p>
            <h2>Another Found</h2>
            <p>More content.</p>
        </body></html>"""
        result = extract_sections_from_html(
            html, ['Found Section', 'Missing Section', 'Another Found']
        )

        assert '## Found Section' in result
        assert 'Found content' in result
        assert '## Another Found' in result
        assert 'More content' in result
        assert 'The following requested sections were not found: "Missing Section"' in result

    def test_section_at_end_of_document(self):
        """Test extracting the final section."""
        html = """<html><body>
            <h2>First Section</h2>
            <p>First content.</p>
            <h2>Last Section</h2>
            <p>Last content.</p>
            <p>Final line.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Last Section'])
        assert '## Last Section' in result
        assert 'Last content' in result
        assert 'Final line' in result
        assert '## First Section' not in result

    def test_section_with_no_content(self):
        """Test empty sections."""
        html = """<html><body>
            <h2>Section With Content</h2>
            <p>Some content here.</p>
            <h2>Empty Section</h2>
            <h2>Another Section</h2>
            <p>More content.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Empty Section'])
        assert '## Empty Section' in result

    def test_mixed_heading_levels(self):
        """Test mixed heading hierarchy."""
        html = """<html><body>
            <h1>Level 1</h1>
            <p>Content 1.</p>
            <h2>Level 2</h2>
            <p>Content 2.</p>
            <h3>Level 3</h3>
            <p>Content 3.</p>
            <h2>Another Level 2</h2>
            <p>Content 2B.</p>
            <h1>Another Level 1</h1>
            <p>Content 1B.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Level 2'])
        assert '## Level 2' in result
        assert 'Content 2' in result
        assert '### Level 3' in result  # Should include subsection
        assert 'Content 3' in result
        assert '## Another Level 2' not in result  # Should stop at same level
        assert '# Another Level 1' not in result

    def test_duplicate_section_names(self):
        """Test handling of duplicate section titles (should get all matches)."""
        html = """<html><body>
            <h2>Introduction</h2>
            <p>First intro.</p>
            <h2>Main Section</h2>
            <p>First main content.</p>
            <h2>Main Section</h2>
            <p>Second main content.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['Main Section'])
        assert '## Main Section' in result
        assert 'First main content' in result
        assert 'Second main content' in result  # Should include both matching sections


class TestEmptyLinkTargets:
    """An unresolved cross-reference became a link to nowhere."""

    @pytest.mark.parametrize(
        'href',
        [
            './.html#cross-region-ip-apac.amazon.nova-pro-v1:0',
            './.html',
            '.html',
            '/bedrock/latest/userguide/.html',
            '.htm',
            './.HTML',
            './.html?highlight=x',
            '//docs.aws.amazon.com/.html',
            '  ./.html  ',
        ],
    )
    def test_empty_targets_detected(self, href):
        """An href whose filename portion is empty is reported as broken."""
        assert has_empty_link_target(href) is True

    @pytest.mark.parametrize(
        'href',
        [
            './models-region-compatibility.html',
            'https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html',
            '#in-page-anchor',
            '',
            '/bedrock/latest/userguide/',
            'endpoints.html#section',
            'foo/.',  # a directory reference, not a missing filename
            '..',
            './',
            'mailto:someone@example.com',
            'javascript:void(0)',
        ],
    )
    def test_valid_targets_untouched(self, href):
        """Ordinary hrefs, directory links and fragment-only links are left alone."""
        assert has_empty_link_target(href) is False

    def test_broken_link_becomes_plain_text(self):
        """The link is dropped and its text kept, rather than emitting './.html'."""
        html = """<html><body><main>
        <p>Use the <a href="./.html#cross-region-ip-apac">APAC Nova Pro inference profile</a>.</p>
        </main></body></html>"""
        result = extract_content_from_html(html)
        assert 'APAC Nova Pro inference profile' in result
        assert '.html' not in result
        assert '](' not in result

    def test_valid_link_still_rendered(self):
        """A resolvable link in the same paragraph is still emitted as markdown."""
        html = """<html><body><main>
        <p>See <a href="./quotas.html">Quotas</a> and <a href="./.html">Nothing</a>.</p>
        </main></body></html>"""
        result = extract_content_from_html(html)
        assert '](./quotas.html' in result
        assert 'Nothing' in result
        assert './.html' not in result


class TestLinkTitlesNotDuplicated:
    """A link title that merely repeats the href spends the read budget for nothing."""

    def test_href_not_repeated_as_title(self):
        """Links render as [text](url), not [text](url "url")."""
        html = """<html><body><main>
        <p>See <a href="./quotas.html">Quotas</a>.</p>
        </main></body></html>"""
        result = extract_content_from_html(html)
        assert '[Quotas](./quotas.html)' in result

    def test_authored_title_preserved(self):
        """A title the page actually authored is still emitted."""
        html = """<html><body><main>
        <p>See <a href="./quotas.html" title="Service quotas">Quotas</a>.</p>
        </main></body></html>"""
        result = extract_content_from_html(html)
        assert '[Quotas](./quotas.html "Service quotas")' in result


class TestReadableTextPredicate:
    """A page carries prose only if text survives outside markup."""

    def _soup(self, html):
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, 'html.parser')

    def test_prose_nested_inside_noscript_is_not_readable(self):
        """The JS-disabled banner sits several levels down, so the parent alone is not enough."""
        html = (
            '<html><body><noscript><div><div><p><strong>Javascript is disabled'
            '</strong></p></div></div></noscript></body></html>'
        )
        assert has_readable_text(self._soup(html)) is False

    def test_a_comment_is_not_readable_text(self):
        """A comment is markup, not prose."""
        html = '<html><body><!-- generated by the doc build --></body></html>'
        assert has_readable_text(self._soup(html)) is False

    def test_a_script_and_style_shell_is_not_readable(self):
        """A bootstrap shell carries code, not content."""
        html = (
            '<html><body><script>window.awsdocs={guide:"x"};</script>'
            '<style>.awsdocs-body{margin:0}</style></body></html>'
        )
        assert has_readable_text(self._soup(html)) is False

    def test_a_banner_alongside_real_prose_is_readable(self):
        """An ordinary page carries the banner and content, and must stay readable."""
        html = (
            '<html><body><noscript><div><p>Javascript is disabled</p></div></noscript>'
            '<main><p>Real prose.</p></main></body></html>'
        )
        assert has_readable_text(self._soup(html)) is True


class TestShellPagesDoNotSimplify:
    """A page whose body is only markup raises rather than returning the markup as prose."""

    def test_inline_script_is_not_returned_as_documentation(self):
        """A tag stripped by markdownify keeps its text, so script bodies are removed outright."""
        html = (
            '<html><body><script>window.awsdocs={guide:"reference"};boot();</script>'
            '<style>.awsdocs-body{margin:0}</style></body></html>'
        )
        with pytest.raises(UnreadablePageError):
            extract_content_from_html(html)

    def test_nested_noscript_banner_alone_raises(self):
        """A shell carrying only the JS-disabled banner has no content."""
        html = (
            '<html><body><noscript><div><p><strong>Javascript is disabled'
            '</strong></p></div></noscript></body></html>'
        )
        with pytest.raises(UnreadablePageError):
            extract_content_from_html(html)

    def test_comment_only_body_raises(self):
        """A build comment is not content."""
        with pytest.raises(UnreadablePageError):
            extract_content_from_html(
                '<html><body><!-- built by the doc pipeline --></body></html>'
            )

    def test_a_real_page_still_extracts(self):
        """The guard does not fire on a page that has prose."""
        html = '<html><body><main><h1>Title</h1><p>Real prose here.</p></main></body></html>'
        result = extract_content_from_html(html)
        assert 'Real prose here.' in result


class TestSectionTitleMatching:
    """A caller passing a rendered heading finds the section, whatever markup it contains."""

    HTML = (
        '<html><body><main>'
        '<h2>Using the <code>Switch Role</code> API</h2><p>First body.'
        '<h2>Plain Heading</h2><p>Second body.'
        '</main></body></html>'
    )

    def test_a_heading_with_inline_markup_is_matchable(self):
        """The rendered text of the heading is what a caller can see and pass."""
        result = extract_sections_from_html(self.HTML, ['Using the Switch Role API'])
        assert 'First body.' in result
        assert 'Second body.' not in result

    def test_available_sections_are_reported_readably(self):
        """A miss lists titles a caller can actually retry with."""
        with pytest.raises(ValueError) as excinfo:
            extract_sections_from_html(self.HTML, ['No Such Section'])
        message = str(excinfo.value)
        assert 'Using the Switch Role API' in message
        assert 'UsingtheSwitchRoleAPI' not in message

    def test_a_plain_heading_still_matches(self):
        """The normalizer does not disturb headings without markup."""
        result = extract_sections_from_html(self.HTML, ['Plain Heading'])
        assert 'Second body.' in result


class TestWhitespaceOnlyBody:
    """Markup that converts to nothing but whitespace is not a successful read."""

    def test_line_breaks_alone_are_not_content(self):
        """A body of <br> converts to spaces and newlines, which is not prose."""
        with pytest.raises(UnreadablePageError):
            extract_content_from_html('<html><body><br><br></body></html>')

    def test_empty_paragraphs_are_not_content(self):
        """Paragraphs holding only whitespace are not prose either."""
        with pytest.raises(UnreadablePageError):
            extract_content_from_html('<html><body><p> </p><p>  </p></body></html>')


class TestMarkdownHeadingOffsets:
    """Candidate heading lines. Deciding which are real is locate_headings' job, not this one."""

    def test_offsets_point_at_the_hashes(self):
        """Each offset is the index of the heading's own line."""
        markdown = '# One\n\nbody\n\n## Two\n'
        assert markdown_heading_candidates(markdown) == [(1, 0), (2, 13)]
        assert markdown[13:].startswith('## Two')

    def test_candidates_include_lines_inside_code(self):
        """Deliberately unfiltered: this cannot tell code from prose, so it does not try.

        An earlier version tracked fenced blocks here. markdownify indents a fence nested in a
        list or definition list, which desynchronised the open/close pairing and swallowed whole
        regions of the page - 11 real headings on the IAM condition-operators page, including
        "Date condition operators", were read as code comments.
        """
        markdown = '# Real\n\n```\n# just a comment\n```\n\n## Also real\n'
        assert [level for level, _ in markdown_heading_candidates(markdown)] == [1, 1, 2]

    def test_hashes_without_a_space_are_not_a_candidate(self):
        """'#1 priority' is prose, not an h1."""
        assert markdown_heading_candidates('#1 priority\n') == []


class TestAlignHeadings:
    """Matching the page's headings into the markdown, which is what positions depend on."""

    def test_a_code_comment_matches_nothing_and_is_ignored(self):
        """The false candidate is rejected because the page has no such heading."""
        markdown = '# Real\n\n```\n# just a comment\n```\n\n## Also real\n'
        headings = [Heading.of(1, 'Real'), Heading.of(2, 'Also real')]
        located = locate_headings(markdown, headings)
        assert located == [0, markdown.index('## Also real')]

    def test_a_heading_the_conversion_dropped_is_stepped_over(self):
        """One missing heading must not strand every heading after it."""
        markdown = '# One\n\n## Three\n'
        headings = [Heading.of(1, 'One'), Heading.of(2, 'Two'), Heading.of(2, 'Three')]
        located = locate_headings(markdown, headings)
        assert located[0] == 0
        assert located[1] is None
        assert located[2] == markdown.index('## Three')

    def test_a_permalink_suffix_still_matches(self):
        """CLI reference headings carry a permalink anchor that becomes a markdown link."""
        markdown = '## cp[¶](#cp "Permalink to this heading")\n\nbody\n'
        assert locate_headings(markdown, [Heading.of(2, 'cp¶')]) == [0]

    def test_a_code_element_in_a_heading_still_matches(self):
        """<code> inside a heading comes back wrapped in backticks."""
        markdown = '## Avoid `.` in names\n\nbody\n'
        assert locate_headings(markdown, [Heading.of(2, 'Avoid . in names')]) == [0]

    def test_the_same_level_is_required(self):
        """Matching text at the wrong level is not the same heading."""
        assert locate_headings('### Two\n', [Heading.of(2, 'Two')]) == [None]

    def test_hashes_without_a_space_are_not_a_heading(self):
        """'#1 priority' is prose, not an h1."""
        assert markdown_heading_candidates('#1 priority\n') == []


class TestSectionIndex:
    """An anchor is resolved by the heading's position, because markdownify drops its id."""

    HTML = """
    <html><body><main>
      <h1 id="page">Page</h1>
      <h2 id="first">First</h2><p>first body</p>
      <div id="wrapper"><h2 id="second">Second</h2><p>second body</p>
        <h6 id="note">Note</h6><p>a nested callout</p>
      </div>
      <h2 id="third">Third</h2><p>third body</p>
    </main></body></html>
    """

    def test_markdownify_drops_the_heading_id(self):
        """The premise of the whole mechanism: the anchor cannot survive into the markdown."""
        markdown = extract_content_from_html(self.HTML)
        assert '## Second' in markdown
        assert 'id=' not in markdown

    def test_every_anchor_maps_to_a_heading_position(self):
        """Positions are assigned in document order, over section headings only."""
        _, anchors = extract_content_and_anchors(self.HTML)
        assert anchors.position_for_anchor('page') == 0
        assert anchors.position_for_anchor('first') == 1
        assert anchors.position_for_anchor('second') == 2
        assert anchors.position_for_anchor('third') == 3

    def test_an_h6_is_not_a_section_and_its_anchor_stays_in_the_enclosing_one(self):
        """AWS uses h6 for callout titles, so it is chrome rather than a boundary.

        The "Note" here sits inside Second, so #note belongs to Second. Treating the h6 as a
        section would make it a position of its own; sending its anchor forward instead would
        land it on Third, past the content it names.
        """
        _, anchors = extract_content_and_anchors(self.HTML)
        assert [h.text for h in anchors.headings] == ['Page', 'First', 'Second', 'Third']
        assert anchors.position_for_anchor('note') == anchors.position_for_anchor('second')

    def test_an_h6_still_appears_inside_its_section(self):
        """Not a boundary does not mean removed from the content."""
        markdown, anchors = extract_content_and_anchors(self.HTML)
        section = anchor_section(markdown, anchors, 'second')
        assert '###### Note' in section
        assert 'a nested callout' in section
        assert 'third body' not in section

    def test_an_anchor_on_a_wrapper_resolves_to_the_heading_inside_it(self):
        """AWS pages often put the id on a div around the section, not on its heading."""
        _, anchors = extract_content_and_anchors(self.HTML)
        assert anchors.position_for_anchor('wrapper') == anchors.position_for_anchor('second')

    def test_an_unknown_fragment_resolves_to_nothing(self):
        """A miss is reported as a miss rather than guessed at."""
        _, anchors = extract_content_and_anchors(self.HTML)
        assert anchors.position_for_anchor('no-such-anchor') is None

    def test_a_percent_encoded_fragment_is_decoded(self):
        """A fragment arrives percent-encoded in a URL but is plain in the id attribute."""
        _, anchors = extract_content_and_anchors('<main><h2 id="a b">A B</h2></main>')
        assert anchors.position_for_anchor('a%20b') == 0

    def test_an_empty_named_anchor_resolves_to_the_following_heading(self):
        """<a name="..."> carries no content, so the heading after it is the target."""
        _, anchors = extract_content_and_anchors('<main><a name="jump"></a><h2>Target</h2></main>')
        assert anchors.position_for_anchor('jump') == 0

    def test_one_parse_serves_both_results(self):
        """The markdown is identical to what the anchor-free path produces."""
        markdown, _ = extract_content_and_anchors(self.HTML)
        assert markdown == extract_content_from_html(self.HTML)


class TestAnchorSection:
    """Trimming is bounded by heading level, not by the next heading of any level."""

    def _resolve(self, html, fragment):
        markdown, anchors = extract_content_and_anchors(html)
        return anchor_section(markdown, anchors, fragment)

    def test_a_section_stops_at_the_next_sibling(self):
        """The following h2 ends an h2's section."""
        section = self._resolve(TestSectionIndex.HTML, 'first')
        assert section.startswith('## First')
        assert 'first body' in section
        assert 'Second' not in section

    def test_a_deeper_heading_stays_inside_the_section(self):
        """AWS uses h6 for callouts, so stopping at any heading would cut a section short."""
        section = self._resolve(TestSectionIndex.HTML, 'second')
        assert 'second body' in section
        assert '###### Note' in section
        assert 'a nested callout' in section
        assert 'Third' not in section

    def test_the_last_section_runs_to_the_end(self):
        """With no following heading the section ends with the document."""
        section = self._resolve(TestSectionIndex.HTML, 'third')
        assert section.startswith('## Third')
        assert 'third body' in section

    def test_a_top_level_anchor_takes_the_whole_page(self):
        """Nothing outranks the h1, so its section is everything below it."""
        section = self._resolve(TestSectionIndex.HTML, 'page')
        assert 'first body' in section
        assert 'third body' in section

    def test_an_unknown_fragment_returns_none(self):
        """None lets the caller serve the whole page instead of raising."""
        assert self._resolve(TestSectionIndex.HTML, 'no-such-anchor') is None

    def test_a_repeated_heading_is_told_apart_by_its_anchor(self):
        """The case a section title cannot address, which is why anchors are worth honouring.

        "Note" repeating under separate anchors is the common shape: heading text repeated on
        6 of 9 sampled pages, "Note", "Important" and "Warning" being the usual culprits.
        """
        html = """<main>
          <h3 id="note-request">Note</h3><p>about the request</p>
          <h3 id="note-response">Note</h3><p>about the response</p>
        </main>"""
        request = self._resolve(html, 'note-request')
        response = self._resolve(html, 'note-response')
        assert 'about the request' in request and 'about the response' not in request
        assert 'about the response' in response and 'about the request' not in response

    def test_an_anchor_below_h2_resolves(self):
        """Only 63 of 267 sampled anchors sit on an h2, so the deeper levels are the common case."""
        html = """<main>
          <h2 id="syntax">Request Syntax</h2><p>syntax body</p>
          <h3 id="uri-parameters">URI Parameters</h3><p>parameter body</p>
          <h4 id="bucket">bucket</h4><p>bucket body</p>
          <h3 id="response">Response</h3><p>response body</p>
        </main>"""
        section = self._resolve(html, 'uri-parameters')
        assert 'parameter body' in section
        assert 'bucket body' in section  # the h4 belongs to the h3
        assert 'response body' not in section
        assert 'syntax body' not in section

    def test_a_heading_inside_a_wrapper_is_still_bounded(self):
        """The sibling walk the title path uses found no body for 47 of 176 anchored headings.

        Markdown is flat, so nesting the heading inside a div changes nothing here.
        """
        html = """<main>
          <div class="section"><h2 id="first">First</h2><p>first body</p></div>
          <div class="section"><h2 id="second">Second</h2><p>second body</p></div>
        </main>"""
        section = self._resolve(html, 'first')
        assert 'first body' in section
        assert 'second body' not in section

    def test_a_heading_whose_markdown_differs_still_resolves(self):
        """A <code> element inside a heading comes back in backticks; the position does not care."""
        html = '<main><h2 id="periods">Avoid <code>.</code> in names</h2><p>why</p></main>'
        section = self._resolve(html, 'periods')
        assert '`.`' in section
        assert 'why' in section

    def test_a_dropped_heading_only_costs_its_own_section(self):
        """A heading missing from the markdown must not strand the ones around it.

        An earlier version compared heading counts and refused to slice at all when they
        disagreed. Counts disagreed on 5 of 9 sampled real pages, so anchors silently fell back
        to the whole page on the majority of them. Matching each heading by level and text
        instead confines the loss to the heading actually missing.
        """
        index = SectionIndex(
            (
                Heading.of(1, 'one', ('one',)),
                Heading.of(2, 'two', ('two',)),
                Heading.of(2, 'three', ('three',)),
            )
        )
        # The index saw three headings; this markdown is missing "three".
        markdown = '# One\n\nbody\n\n## Two\n\nmore\n'
        assert anchor_section(markdown, index, 'two') == '## Two\n\nmore'
        assert anchor_section(markdown, index, 'three') is None

    def test_a_section_is_not_bounded_by_a_heading_that_went_missing(self):
        """The next *located* sibling ends the section, not the next one in the index."""
        index = SectionIndex(
            (
                Heading.of(2, 'first', ('first',)),
                Heading.of(2, 'missing', ('missing',)),
                Heading.of(2, 'last', ('last',)),
            )
        )
        markdown = '## First\n\nfirst body\n\n## Last\n\nlast body\n'
        assert anchor_section(markdown, index, 'first') == '## First\n\nfirst body'

    def test_a_position_past_the_end_refuses_to_slice(self):
        """Same guard reached directly, without a fragment to look up."""
        index = SectionIndex((Heading.of(1, 'one', ('one',)),))
        assert section_markdown('# One\n\nbody\n', index, 5) is None
        assert section_markdown('# One\n\nbody\n', index, -1) is None

    def test_a_consistent_index_does_slice(self):
        """The guard must not be so strict that the ordinary case trips it."""
        index = SectionIndex((Heading.of(1, 'one', ('one',)), Heading.of(2, 'two', ('two',))))
        assert (
            anchor_section('# One\n\nbody\n\n## Two\n\nmore\n', index, 'two') == '## Two\n\nmore'
        )


class TestSectionIndexTitleLookup:
    """The title lookup exists so a title and an anchor resolve against the same headings."""

    HTML = """<main>
      <h2 id="syntax">Request Syntax</h2><p>syntax body</p>
      <h3 id="note-a">Note</h3><p>first note</p>
      <h2 id="response">Response</h2><p>response body</p>
      <h3 id="note-b">Note</h3><p>second note</p>
    </main>"""

    def _index(self):
        return extract_content_and_anchors(self.HTML)[1]

    def test_a_title_resolves_to_a_position(self):
        """The same currency the anchor lookup returns."""
        assert self._index().positions_for_title('Request Syntax') == [0]

    def test_a_title_is_matched_case_and_whitespace_insensitively(self):
        """Callers do not reproduce the page's exact spacing."""
        assert self._index().positions_for_title('  request   SYNTAX ') == [0]

    def test_a_repeated_title_returns_every_match(self):
        """Heading text is not unique, so the caller is told about all of them."""
        assert self._index().positions_for_title('Note') == [1, 3]

    def test_levels_narrow_the_match(self):
        """Restricting to h2 keeps a title like "Note" from matching a callout."""
        index = self._index()
        assert index.positions_for_title('Note', levels=[2]) == []
        assert index.positions_for_title('Response', levels=[2]) == [2]

    def test_a_title_and_an_anchor_reach_the_same_section(self):
        """The point of holding both on one record."""
        markdown, index = extract_content_and_anchors(self.HTML)
        by_anchor = anchor_section(markdown, index, 'response')
        by_title = section_markdown(markdown, index, index.positions_for_title('Response')[0])
        assert by_anchor == by_title
        assert 'response body' in by_anchor


class TestTitleMatchingIsLevelTwoOnly:
    """Search returns the page's h2 titles, so h2 is what a title is allowed to match."""

    HTML = """<main>
      <h2 id="syntax">Request Syntax</h2><p>syntax body</p>
      <h3 id="note-a">Note</h3><p>a nested note</p>
      <h2 id="response">Response</h2><p>response body</p>
    </main>"""

    def test_a_title_matches_an_h2(self):
        """The level a caller can actually name."""
        result = extract_sections_from_html(self.HTML, ['Request Syntax'])
        assert 'syntax body' in result
        assert 'response body' not in result

    def test_a_title_does_not_match_a_deeper_heading(self):
        """A "Note" names a callout here, not a section, so it must not be selectable by title."""
        with pytest.raises(ValueError, match='No matching sections were found'):
            extract_sections_from_html(self.HTML, ['Note'])

    def test_a_nested_heading_stays_inside_its_section(self):
        """Not selectable on its own, but still returned as part of its parent."""
        result = extract_sections_from_html(self.HTML, ['Request Syntax'])
        assert '### Note' in result
        assert 'a nested note' in result

    def test_available_sections_list_only_h2_as_the_page_writes_them(self):
        """The caller has to retype one of these, so casing is the page's, not normalised."""
        with pytest.raises(ValueError) as excinfo:
            extract_sections_from_html(self.HTML, ['Nonexistent'])
        message = str(excinfo.value)
        assert '"Request Syntax"' in message
        assert '"Response"' in message
        assert 'Note' not in message

    def test_a_title_and_an_anchor_reach_the_same_section(self):
        """Both lookups resolve against one heading table, so they cannot disagree."""
        markdown, index = extract_content_and_anchors(self.HTML)
        by_title = extract_sections_from_html(self.HTML, ['Response'])
        by_anchor = anchor_section(markdown, index, 'response')
        assert by_anchor == by_title

    def test_sections_come_back_in_page_order_without_duplicates(self):
        """Asking out of order, or twice, does not reorder or repeat the page."""
        result = extract_sections_from_html(self.HTML, ['Response', 'Request Syntax', 'Response'])
        assert result.index('syntax body') < result.index('response body')
        assert result.count('response body') == 1


class TestUnseparableSections:
    """Markup that collapses its own headings leaves nothing to cut on."""

    def test_an_unclosed_heading_is_reported_not_returned_empty(self):
        """The h1 never closes, so the parser folds the whole page into it.

        The section cannot be separated from the page. Saying so beats returning a header with
        nothing underneath it, which is what an earlier version of this did.
        """
        html = '<html><body><h1>Page<h1/><h2>Best practices</h2><p>Content.</p></body></html>'
        with pytest.raises(ValueError, match='could not be separated'):
            extract_sections_from_html(html, ['Best practices'])


class TestEmptyHeadings:
    """An empty heading is a marker, not a boundary, and AWS hangs real anchors on them."""

    HTML = """<main>
      <h2 id="return-values">Return values</h2><p>intro</p>
      <h3 id="getatt">Fn::GetAtt</h3><p>getatt body</p>
      <h4 id="getatt-alias"></h4>
      <h2 id="examples">Examples</h2><p>examples body</p>
    </main>"""

    def test_an_empty_heading_is_not_a_section(self):
        """It has no title and the conversion renders nothing for it."""
        _, index = extract_content_and_anchors(self.HTML)
        assert [h.text for h in index.headings] == [
            'Return values',
            'Fn::GetAtt',
            'Examples',
        ]

    def test_its_anchor_attaches_to_the_section_above_it(self):
        """CloudFormation puts a return-value anchor on an empty heading just after the real one.

        Attaching forwards would resolve it to the next section and skip the content it names:
        on the live AWS::S3::Bucket page that returned 62% of the page starting at "Examples",
        against 4.4% starting at "Fn::GetAtt".
        """
        markdown, index = extract_content_and_anchors(self.HTML)
        assert index.position_for_anchor('getatt-alias') == index.position_for_anchor('getatt')
        section = anchor_section(markdown, index, 'getatt-alias')
        assert section.startswith('### Fn::GetAtt')
        assert 'getatt body' in section
        assert 'examples body' not in section

    def test_an_empty_heading_does_not_bound_the_section_above_it(self):
        """Being dropped from the table means it cannot cut the section short either."""
        markdown, index = extract_content_and_anchors(self.HTML)
        section = anchor_section(markdown, index, 'getatt')
        assert 'getatt body' in section

    def test_a_named_anchor_before_a_heading_still_attaches_forwards(self):
        """The empty-heading rule must not invert the ordinary anchor-before-heading case."""
        _, index = extract_content_and_anchors(
            '<main><h2>First</h2><p>a</p><a name="jump"></a><h2>Second</h2><p>b</p></main>'
        )
        assert index.position_for_anchor('jump') == 1
