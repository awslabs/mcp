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
    UnreadablePageError,
    add_search_intent_to_search_request,
    enforce_redirect_allowlist,
    extract_content_from_html,
    format_documentation_result,
    has_empty_link_target,
    has_readable_text,
    is_html_content,
    parse_recommendation_results,
    select_sections,
    to_html_page_url,
    url_matches_allowlist,
)
from unittest.mock import MagicMock, patch


def extract_sections_from_markdown(markdown, section_titles):
    """Return the selection as read_sections renders it, without the server's paging."""
    selection = select_sections(markdown, section_titles)
    if selection.whole_page:
        return f'{selection.notes.lstrip()}\n\n{markdown}' if selection.notes else markdown
    return selection.markdown + selection.notes


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


class TestExtractSectionsFromMarkdown:
    """Tests for extract_sections_from_markdown function."""

    def test_empty_input_is_unreadable(self):
        """Empty content is unreadable, like whitespace-only content."""
        with pytest.raises(UnreadablePageError):
            extract_sections_from_markdown('', ['section1'])

    def test_empty_section_list(self):
        """Test with empty section_titles list."""
        result = extract_sections_from_markdown('# Test', [])
        assert result == 'No content or section titles provided'

    def test_whitespace_only_content_is_unreadable(self):
        """Content with no text at all cannot hold a section."""
        with pytest.raises(UnreadablePageError):
            extract_sections_from_markdown('  \n\n ', ['Main Section'])

    def test_single_section_extraction(self):
        """Test extracting a single section with content."""
        markdown = (
            '## Introduction\n\nThis is the intro.\n\n'
            '## Main Section\n\nThis is the main content.\n\nSome more content here.\n\n'
            '## Conclusion\n\nThis is the end.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Main Section'])
        assert result == (
            '## Main Section\n\nThis is the main content.\n\nSome more content here.'
        )

    def test_multiple_sections_extraction(self):
        """Test extracting multiple sections."""
        markdown = (
            '## Introduction\n\nThis is the intro.\n\n'
            '## First Section\n\nFirst content.\n\n'
            '## Second Section\n\nSecond content.\n\n'
            '## Third Section\n\nThird content.\n'
        )
        result = extract_sections_from_markdown(markdown, ['First Section', 'Third Section'])
        assert result == (
            '## First Section\n\nFirst content.\n\n## Third Section\n\nThird content.'
        )

    def test_case_insensitive_matching(self):
        """Test case-insensitive section matching."""
        result = extract_sections_from_markdown(
            '## Main Section\n\nContent here.', ['MAIN SECTION']
        )
        assert '## Main Section' in result
        assert 'Content here' in result

    def test_whitespace_handling(self):
        """Test section titles with leading/trailing whitespace."""
        markdown = (
            '## Best practices\n\nThis is content for best practices.\n\n'
            '## Another Section\n\nMore content here.\n'
        )
        test_cases = [
            ' Best practices\n',
            '  Best practices  ',
            'Best  practices',
            '\tBest practices\t',
            'Best\npractices',
        ]

        for test_input in test_cases:
            result = extract_sections_from_markdown(markdown, [test_input])
            assert '## Best practices' in result, f"Failed to match '{repr(test_input)}'"
            assert 'content for best practices' in result, (
                f"Content missing for '{repr(test_input)}'"
            )
            assert '## Another Section' not in result, (
                f"Should not include other sections for '{repr(test_input)}'"
            )

    def test_nested_sections_included(self):
        """Test that subsections within matching sections are included."""
        markdown = (
            '## Main Section\n\nMain content.\n\n'
            '### Subsection 1\n\nSub content 1.\n\n'
            '#### Sub-subsection\n\nSub-sub content.\n\n'
            '### Subsection 2\n\nSub content 2.\n\n'
            '## Another Section\n\nOther content.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Main Section'])
        for expected in (
            '## Main Section',
            'Main content',
            '### Subsection 1',
            'Sub content 1',
            '#### Sub-subsection',
            'Sub-sub content',
            '### Subsection 2',
            'Sub content 2',
        ):
            assert expected in result
        assert '## Another Section' not in result
        assert 'Other content' not in result

    def test_no_sections_found_with_h2_headings(self):
        """Test when no sections match but document has level-2 headings."""
        markdown = (
            '# Introduction\n\nIntro content.\n\n'
            '## Subsection A\n\nContent A.\n\n'
            '## Subsection B\n\nContent B.\n'
        )
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_markdown(markdown, ['Nonexistent Section'])
        error_msg = str(exc_info.value)
        assert 'No matching sections were found' in error_msg
        assert 'Available sections: "Subsection A", "Subsection B".' in error_msg

    def test_no_sections_found_without_h2_headings(self):
        """Test when no sections match and no level-2 headings exist."""
        markdown = '# Introduction\n\nThis is the intro.\n\n# Main Section\n\nContent here.'
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_markdown(markdown, ['Nonexistent Section', 'Another Missing'])
        assert 'This document does not contain subsections' in str(exc_info.value)

    def test_partial_success(self):
        """Test when some sections found, others missing (graceful handling)."""
        markdown = (
            '## Introduction\n\nIntro content.\n\n'
            '## Found Section\n\nFound content.\n\n'
            '## Another Found\n\nMore content.\n'
        )
        result = extract_sections_from_markdown(
            markdown, ['Found Section', 'Missing Section', 'Another Found']
        )
        assert result == (
            '## Found Section\n\nFound content.\n\n## Another Found\n\nMore content.'
            '\n\n> **Note**: The following requested sections were not found: "Missing Section"'
        )

    def test_section_at_end_of_document(self):
        """Test extracting the final section."""
        markdown = (
            '## First Section\n\nFirst content.\n\n'
            '## Last Section\n\nLast content.\n\nFinal line.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Last Section'])
        assert result == '## Last Section\n\nLast content.\n\nFinal line.'

    def test_section_with_no_content(self):
        """Test empty sections."""
        markdown = (
            '## Section With Content\n\nSome content here.\n\n'
            '## Empty Section\n\n'
            '## Another Section\n\nMore content.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Empty Section'])
        assert result == '## Empty Section'

    def test_mixed_heading_levels(self):
        """Test mixed heading hierarchy."""
        markdown = (
            '# Level 1\n\nContent 1.\n\n'
            '## Level 2\n\nContent 2.\n\n'
            '### Level 3\n\nContent 3.\n\n'
            '## Another Level 2\n\nContent 2B.\n\n'
            '# Another Level 1\n\nContent 1B.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Level 2'])
        assert result == '## Level 2\n\nContent 2.\n\n### Level 3\n\nContent 3.'

    def test_level_one_line_does_not_end_a_section(self):
        """Converted HTML leaves a paragraph starting with '#' unescaped; it is section text."""
        markdown = '## Hosts\n\nIntro.\n\n# of hosts is 3\n\nMore detail.\n\n## Next\n\nOther.\n'
        result = extract_sections_from_markdown(markdown, ['Hosts'])
        assert result == '## Hosts\n\nIntro.\n\n# of hosts is 3\n\nMore detail.'

    def test_duplicate_section_names(self):
        """Test handling of duplicate section titles (should get all matches)."""
        markdown = (
            '## Introduction\n\nFirst intro.\n\n'
            '## Main Section\n\nFirst main content.\n\n'
            '## Main Section\n\nSecond main content.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Main Section'])
        assert 'First main content' in result
        assert 'Second main content' in result  # Should include both matching sections

    def test_headings_inside_code_blocks_are_ignored(self):
        """A '#' line inside a fenced code block neither starts nor ends a section."""
        markdown = (
            '## Example\n\n```bash\n## not a heading\necho hi\n```\n\n## Next\n\nNext content.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Example'])
        assert result == '## Example\n\n```bash\n## not a heading\necho hi\n```'
        with pytest.raises(ValueError, match='Available sections: "Example", "Next".'):
            extract_sections_from_markdown(markdown, ['not a heading'])


class TestSectionsAtAnyHeadingLevel:
    """Search lists headings at every level, so read_sections must accept any of them."""

    # Shaped on amazondynamodb/latest/developerguide/ServiceQuotas.html
    QUOTAS = (
        '\n\n# Quotas in Amazon DynamoDB\n<a name="ServiceQuotas"></a>\n\nIntro.\n\n'
        '## Read/write throughput\n\nThroughput intro.\n\n'
        '### Throughput default quotas\n\nDefault quotas body.\n\n'
        '### Increasing or decreasing throughput (for provisioned tables)\n\nChange intro.\n\n'
        '#### Increasing provisioned throughput\n\nIncrease body.\n\n'
        '#### Decreasing provisioned throughput\n\nDecrease body.\n\n'
        '## Reserved Capacity\n\nReserved body.\n\n'
        '## Tables\n\nTables body.\n\n'
        '### Table size\n\nTable size body.\n'
    )

    def test_level_one_title_selects_the_whole_page(self):
        """Search recommends the page title, which is an h1."""
        selection = select_sections(self.QUOTAS, ['Quotas in Amazon DynamoDB'])
        assert selection.whole_page
        assert selection.markdown == self.QUOTAS
        assert selection.missing == []

    def test_whole_page_still_reports_missing_titles(self):
        """The page title plus a title the page lacks still notes the missing one."""
        selection = select_sections(self.QUOTAS, ['Quotas in Amazon DynamoDB', 'Service quotas'])
        assert selection.whole_page
        assert selection.missing == ['Service quotas']

    def test_level_three_section_ends_at_the_next_level_three(self):
        """An h3 section stops at its sibling, not at the end of its h2."""
        result = extract_sections_from_markdown(self.QUOTAS, ['Throughput default quotas'])
        assert result == '### Throughput default quotas\n\nDefault quotas body.'

    def test_level_three_section_keeps_its_subsections(self):
        """Deeper headings belong to the section, so the h3 runs to the next h2."""
        result = extract_sections_from_markdown(
            self.QUOTAS, ['Increasing or decreasing throughput (for provisioned tables)']
        )
        assert result.startswith('### Increasing or decreasing throughput')
        assert '#### Increasing provisioned throughput' in result
        assert result.endswith('Decrease body.')
        assert 'Reserved' not in result

    def test_level_four_section(self):
        """Shaped on the DevOps Agent authentication page, which lists an h4 title."""
        markdown = (
            '# Authentication and security\n\n## Security considerations\n\n'
            '### Traceability\n\nCloudTrail intro.\n\n'
            '#### Access token authentication events\n\nAuthenticateAccessToken body.\n\n'
            '| Field | Description |\n| --- | --- |\n| userName | The token name. |\n\n'
            '#### Downstream action events\n\nDownstream body.\n\n'
            '### VPC endpoint policy limitation\n\nVPC body.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Access token authentication events'])
        assert result == (
            '#### Access token authentication events\n\nAuthenticateAccessToken body.\n\n'
            '| Field | Description |\n| --- | --- |\n| userName | The token name. |'
        )

    def test_level_three_section_at_end_of_document(self):
        """Shaped on the AppSync resolvers tutorial, which ends on an h3."""
        markdown = (
            '# Creating a simple post application using DynamoDB resolvers\n\n'
            '## Create an updatePost Mutation (DynamoDB UpdateItem)\n\nMutation body.\n\n'
            '#### [ JSON ]\n\n```json\n{}\n```\n\n'
            '### Call the API to Update a Post\n\nUpdate body.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Call the API to Update a Post'])
        assert result == '### Call the API to Update a Post\n\nUpdate body.'

    def test_title_at_two_levels_returns_both_sections(self):
        """Shaped on the Lambda quotas page, where "Compute and storage" is an h2 and an h3."""
        markdown = (
            '## Compute and storage\n\nFunction quotas.\n\n'
            '## Lambda MicroVMs\n\n### Compute and storage\n\nPer-MicroVM quotas.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Compute and storage'])
        assert result == (
            '## Compute and storage\n\nFunction quotas.'
            '\n\n### Compute and storage\n\nPer-MicroVM quotas.'
        )

    def test_page_title_that_also_names_a_section_returns_the_section(self):
        """Shaped on the API Gateway VPCLinks page, which has an h3 property named VpcLinks."""
        markdown = (
            '# VPCLinks\n\n## Properties\n\n### VpcLinks\n\nProperty body.\n\n## Other\n\nx\n'
        )
        note = (
            '\n\n> **Note**: "VPCLinks" also names the whole page. Use the read_documentation'
            ' tool to read all of it.'
        )
        alone = extract_sections_from_markdown(markdown, ['VPCLinks'])
        assert alone == '### VpcLinks\n\nProperty body.' + note
        mixed = extract_sections_from_markdown(markdown, ['VPCLinks', 'Other'])
        assert mixed == '### VpcLinks\n\nProperty body.\n\n## Other\n\nx' + note

    def test_nested_titles_are_returned_once(self):
        """Asking for a section and one of its subsections does not repeat the subsection."""
        result = extract_sections_from_markdown(
            self.QUOTAS, ['Read/write throughput', 'Throughput default quotas']
        )
        assert result.count('Default quotas body.') == 1
        assert result.startswith('## Read/write throughput')
        assert '> **Note**' not in result

    def test_repeated_deeper_titles_return_every_match(self):
        """Like repeated h2 titles, every heading carrying the title is returned."""
        markdown = (
            '## Create\n\n### Prerequisites\n\nCreate prereqs.\n\n### Steps\n\nSteps.\n\n'
            '## Delete\n\n### Prerequisites\n\nDelete prereqs.\n'
        )
        result = extract_sections_from_markdown(markdown, ['Prerequisites'])
        assert result == (
            '### Prerequisites\n\nCreate prereqs.\n\n### Prerequisites\n\nDelete prereqs.'
        )

    def test_level_one_line_does_not_end_a_deeper_section(self):
        """The unescaped '# of hosts' paragraph is text inside an h3 section too."""
        markdown = '### Hosts\n\nIntro.\n\n# of hosts is 3\n\nMore.\n\n### Next\n\nOther.\n'
        result = extract_sections_from_markdown(markdown, ['Hosts'])
        assert result == '### Hosts\n\nIntro.\n\n# of hosts is 3\n\nMore.'

    def test_deeper_headings_inside_code_blocks_are_ignored(self):
        """A '###' line in a fenced block neither matches nor ends a section."""
        markdown = '### Example\n\n```\n### not a heading\n```\n\n### Next\n\nNext.\n'
        result = extract_sections_from_markdown(markdown, ['Example'])
        assert result == '### Example\n\n```\n### not a heading\n```'
        with pytest.raises(ValueError, match='Available sections: "Example", "Next".'):
            extract_sections_from_markdown(markdown, ['not a heading'])

    def test_page_without_level_two_lists_its_top_subsections(self):
        """A miss on a page whose subsections start at h3 lists those, not 'no subsections'."""
        markdown = '# Page\n\n### First\n\n#### Inner\n\nBody.\n\n### Second\n\nBody.\n'
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_markdown(markdown, ['Missing'])
        assert 'Available sections: "First", "Second".' in str(exc_info.value)

    def test_page_title_with_a_section_returns_the_section(self):
        """A section named alongside the page title is returned, not lost past the first page."""
        result = extract_sections_from_markdown(
            self.QUOTAS, ['Quotas in Amazon DynamoDB', 'Table size']
        )
        assert result == (
            '### Table size\n\nTable size body.'
            '\n\n> **Note**: "Quotas in Amazon DynamoDB" also names the whole page. Use the'
            ' read_documentation tool to read all of it.'
        )

    def test_page_title_equal_to_a_level_two_title_returns_the_section(self):
        """An h2 that shares the page title returns the h2, not the whole page."""
        selection = select_sections('# Limits\n\n## Limits\n\nBody.\n', ['Limits'])
        assert not selection.whole_page
        assert selection.markdown == '## Limits\n\nBody.'
        assert selection.page_titles == ['Limits']

    def test_later_level_one_line_is_not_the_page_title(self):
        """Only the first h1 names the page; an unescaped '# of hosts' paragraph names nothing."""
        markdown = '# Cluster sizing\n\nIntro.\n\n# of hosts\n\n3\n\n## Details\n\nd\n'
        with pytest.raises(ValueError, match='Available sections: "Details".'):
            select_sections(markdown, ['of hosts'])

    def test_empty_title_matches_nothing(self):
        """A title with no text does not select an empty heading or the page."""
        markdown = '# \n\n### \n\nEmpty heading body.\n\n## A\n\nb\n'
        result = extract_sections_from_markdown(markdown, ['', 'A'])
        assert result == (
            '## A\n\nb\n\n> **Note**: The following requested sections were not found: ""'
        )

    def test_callouts_and_empty_headings_are_not_offered(self):
        """h6 callout titles and empty headings are not listed as sections to retry with."""
        markdown = '# Page\n\n### \n\nx\n\n### Setup\n\n###### Note\n\nn\n\n### Usage\n\nu\n'
        with pytest.raises(ValueError) as exc_info:
            select_sections(markdown, ['Missing'])
        assert 'Available sections: "Setup", "Usage".' in str(exc_info.value)

    def test_repeated_level_two_titles_are_all_offered(self):
        """The h2 list in a miss keeps repeated titles, as it always has."""
        markdown = '## Example\n\na\n\n## Example\n\nb\n'
        with pytest.raises(ValueError, match='Available sections: "Example", "Example".'):
            select_sections(markdown, ['Missing'])

    def test_missing_titles_are_reported_stripped(self):
        """A padded title that matches nothing is named without its padding."""
        result = extract_sections_from_markdown(self.QUOTAS, ['Tables', '  Service quotas  '])
        assert result.endswith('were not found: "Service quotas"')

    def test_page_title_spellings_are_noted_once(self):
        """Two spellings of the page title alongside a section are noted once."""
        result = extract_sections_from_markdown(
            self.QUOTAS, ['Quotas in Amazon DynamoDB', 'QUOTAS IN AMAZON DYNAMODB', 'Table size']
        )
        assert result.endswith(
            '"Quotas in Amazon DynamoDB" also names the whole page.'
            ' Use the read_documentation tool to read all of it.'
        )

    def test_available_subsections_are_listed_once(self):
        """Repeated headings, such as tab labels, are offered once when a title misses."""
        markdown = '# Page\n\n### [ JSON ]\n\nA.\n\n### [ YAML ]\n\nB.\n\n### [ JSON ]\n\nC.\n'
        with pytest.raises(ValueError) as exc_info:
            extract_sections_from_markdown(markdown, ['Missing'])
        assert 'Available sections: "[ JSON ]", "[ YAML ]".' in str(exc_info.value)

    def test_level_six_titles_match_but_are_not_offered(self):
        """An h6 callout title can be read by name, but a miss never suggests one."""
        markdown = '# Page\n\n## Setup\n\n###### Note\n\nCallout.\n\n## Usage\n\nu\n'
        assert extract_sections_from_markdown(markdown, ['Note']) == '###### Note\n\nCallout.'
        with pytest.raises(ValueError, match='Available sections: "Setup", "Usage".'):
            select_sections(markdown, ['Missing'])

    def test_missing_title_spellings_are_noted_once(self):
        """Two spellings of a title that matches nothing are listed once, as first written."""
        result = extract_sections_from_markdown(self.QUOTAS, ['Tables', 'Foo', 'foo', 'Bar'])
        assert result.endswith('were not found: "Foo", "Bar"')

    def test_title_repeated_in_another_case_is_not_reported_missing(self):
        """Two spellings of one title resolve together, so neither is listed as not found."""
        result = extract_sections_from_markdown(self.QUOTAS, ['Tables', 'tables'])
        assert '> **Note**' not in result
        assert result.startswith('## Tables')


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

    MARKDOWN = (
        '## Using the `Switch Role` API\n\nFirst body.\n\n## Plain Heading\n\nSecond body.\n'
    )

    def test_a_heading_with_inline_markup_is_matchable(self):
        """The rendered text of the heading is what a caller can see and pass."""
        result = extract_sections_from_markdown(self.MARKDOWN, ['Using the Switch Role API'])
        assert 'First body.' in result
        assert 'Second body.' not in result

    def test_available_sections_are_reported_readably(self):
        """A miss lists titles a caller can actually retry with."""
        with pytest.raises(ValueError) as excinfo:
            extract_sections_from_markdown(self.MARKDOWN, ['No Such Section'])
        message = str(excinfo.value)
        assert '"Using the Switch Role API"' in message
        assert '`' not in message

    def test_a_title_copied_with_markup_matches(self):
        """Requested titles get the same normalization as the page's headings."""
        result = extract_sections_from_markdown(self.MARKDOWN, ['Using the `Switch Role` API'])
        assert 'First body.' in result

    def test_indented_code_is_not_a_heading(self):
        """Four leading spaces make an indented code block, so '## x' there is code."""
        markdown = '## Example\n\n    ## a shell comment\n    echo hi\n\n## Next\n\nNext.\n'
        result = extract_sections_from_markdown(markdown, ['Example'])
        assert result == '## Example\n\n    ## a shell comment\n    echo hi'

    def test_a_plain_heading_still_matches(self):
        """The normalizer does not disturb headings without markup."""
        result = extract_sections_from_markdown(self.MARKDOWN, ['Plain Heading'])
        assert 'Second body.' in result

    @pytest.mark.parametrize(
        'heading, title',
        [
            ('## **CloudWatch**', 'CloudWatch'),  # bold-wrapped in published Markdown
            ('## Using [roles](roles.md)', 'Using roles'),  # link keeps its text
            ('## x86\\_64 instances', 'x86_64 instances'),  # escaped underscore
            ('## Options \u00b6', 'Options'),  # pilcrow permalink
            ('## Using C #', 'Using C #'),  # a trailing '#' is part of the title
            ('   ## Indented', 'Indented'),  # up to three leading spaces is still a heading
        ],
    )
    def test_published_markdown_heading_forms_match(self, heading, title):
        """Heading markup seen in published and converted Markdown reduces to its text."""
        result = extract_sections_from_markdown(f'{heading}\n\nBody.\n', [title])
        assert result == f'{heading.strip()}\n\nBody.'


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


class TestToHtmlPageUrl:
    """Tests for mapping a documentation URL to the .html page the tools fetch."""

    @pytest.mark.parametrize(
        'url, expected',
        [
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html',
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html',
            ),
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.md',
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html',
            ),
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.md#destinations',
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html',
            ),
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html#section',
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html',
            ),
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.md?x=1',
                'https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html',
            ),
            (
                'https://docs.aws.amazon.com/lambda/latest/dg/README.MD',
                'https://docs.aws.amazon.com/lambda/latest/dg/README.html',
            ),
        ],
    )
    def test_html_and_md_urls_map_to_html_page(self, url, expected):
        """A .md URL names the .html page at its path; query and fragment are dropped."""
        assert to_html_page_url(url) == expected

    @pytest.mark.parametrize(
        'url',
        [
            'https://docs.aws.amazon.com/test.pdf',
            'https://docs.aws.amazon.com/lambda/latest/dg/',
            'https://docs.aws.amazon.com/test.md.bak#x',
            'https://docs.aws.amazon.com/README.markdown',
        ],
    )
    def test_other_urls_are_rejected(self, url):
        """Anything not ending in .html or .md has no page URL."""
        assert to_html_page_url(url) is None
