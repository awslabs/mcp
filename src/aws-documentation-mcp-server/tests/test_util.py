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

import os
import pytest
from awslabs.aws_documentation_mcp_server.util import (
    add_search_intent_to_search_request,
    extract_content_from_html,
    extract_sections_from_html,
    format_documentation_result,
    is_html_content,
    parse_recommendation_results,
)
from unittest.mock import MagicMock, patch


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
        result = extract_content_from_html('')

        # Assertions
        assert result == '<e>Empty HTML content</e>'
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
            result = extract_content_from_html(html)
            assert '<e>' in result
            mock_bs.assert_called_once()


class TestParseRecommendationResults:
    """Tests for parse_recommendation_results function."""

    def test_empty_data(self):
        """Test parsing empty data."""
        data = {}
        results = parse_recommendation_results(data)
        assert results == []

    def test_highly_rated_recommendations(self):
        """Test parsing highly rated recommendations."""
        data = {
            'highlyRated': {
                'items': [
                    {
                        'url': 'https://docs.aws.amazon.com/test1',
                        'assetTitle': 'Test 1',
                        'abstract': 'Abstract 1',
                    },
                    {'url': 'https://docs.aws.amazon.com/test2', 'assetTitle': 'Test 2'},
                ]
            }
        }
        results = parse_recommendation_results(data)
        assert len(results) == 2
        assert results[0].url == 'https://docs.aws.amazon.com/test1'
        assert results[0].title == 'Test 1'
        assert results[0].context == 'Abstract 1'
        assert results[1].url == 'https://docs.aws.amazon.com/test2'
        assert results[1].title == 'Test 2'
        assert results[1].context is None

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
            'highlyRated': {
                'items': [{'url': 'https://docs.aws.amazon.com/hr', 'assetTitle': 'HR'}]
            },
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
        assert len(results) == 4
        # Check that we have one of each type (order doesn't matter for this test)
        urls = [r.url for r in results]
        assert 'https://docs.aws.amazon.com/hr' in urls
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
        assert '<h2>Main Section</h2>' in result
        assert '<p>This is the main content.</p>' in result
        assert '<p>Some more content here.</p>' in result
        assert '<h2>Introduction</h2>' not in result
        assert '<h2>Conclusion</h2>' not in result

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
        assert '<h2>First Section</h2>' in result
        assert 'First content' in result
        assert '<h2>Third Section</h2>' in result
        assert 'Third content' in result
        assert '<h2>Second Section</h2>' not in result
        assert 'Second content' not in result

    def test_case_insensitive_matching(self):
        """Test case-insensitive section matching."""
        html = """<html><body>
            <h2>Main Section</h2>
            <p>Content here.</p>
        </body></html>"""
        result = extract_sections_from_html(html, ['MAIN SECTION'])
        assert '<h2>Main Section</h2>' in result
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
            assert '<h2>Best practices</h2>' in result, f"Failed to match '{repr(test_input)}'"
            assert 'best practices' in result.lower(), f"Content missing for '{repr(test_input)}'"
            assert '<h2>Another Section</h2>' not in result, (
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
        assert '<h2>Main Section</h2>' in result
        assert 'Main content' in result
        assert '<h3>Subsection 1</h3>' in result
        assert 'Sub content 1' in result
        assert '<h4>Sub-subsection</h4>' in result
        assert 'Sub-sub content' in result
        assert '<h3>Subsection 2</h3>' in result
        assert 'Sub content 2' in result
        assert '<h2>Another Section</h2>' not in result
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

        assert '<h2>Found Section</h2>' in result
        assert 'Found content' in result
        assert '<h2>Another Found</h2>' in result
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
        assert '<h2>Last Section</h2>' in result
        assert 'Last content' in result
        assert 'Final line' in result
        assert '<h2>First Section</h2>' not in result

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
        assert '<h2>Empty Section</h2>' in result

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
        assert '<h2>Level 2</h2>' in result
        assert 'Content 2' in result
        assert '<h3>Level 3</h3>' in result  # Should include subsection
        assert 'Content 3' in result
        assert '<h2>Another Level 2</h2>' not in result  # Should stop at same level
        assert '<h1>Another Level 1</h1>' not in result

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
        assert '<h2>Main Section</h2>' in result
        assert 'First main content' in result
        assert 'Second main content' in result  # Should include both matching sections
