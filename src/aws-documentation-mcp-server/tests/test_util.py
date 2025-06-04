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
from awslabs.aws_documentation_mcp_server.util import (
    extract_content_from_html,
    format_documentation_result,
    is_html_content,
    parse_recommendation_results,
)
from unittest.mock import patch


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
