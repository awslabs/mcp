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

"""Tests for the doc_fetcher utility module."""

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import doc_fetcher
from unittest.mock import Mock, patch


class TestDocFetcher:
    """Test cases for document fetching utilities."""

    @patch('urllib.request.urlopen')
    def test_get_success(self, mock_urlopen):
        """Test _get successfully fetches content."""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = b'Test content'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Act
        result = doc_fetcher._get('https://example.com/doc')

        # Assert
        assert result == 'Test content'

    @patch('urllib.request.urlopen')
    def test_get_handles_encoding_errors(self, mock_urlopen):
        """Test _get handles encoding errors gracefully."""
        # Arrange
        mock_response = Mock()
        mock_response.read.return_value = b'\xff\xfe invalid utf-8'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Act
        result = doc_fetcher._get('https://example.com/doc')

        # Assert
        # Should not raise exception, should handle with errors='ignore'
        assert isinstance(result, str)

    def test_parse_llms_txt_extracts_links(self):
        """Test parse_llms_txt extracts markdown links correctly."""
        # Arrange
        llms_content = """
        # Documentation Links

        [Getting Started](https://strandsagents.com/doc1)
        [API Reference](https://strandsagents.com/doc2)

        Some other text without links.
        """

        with patch.object(doc_fetcher, '_get', return_value=llms_content):
            # Act
            result = doc_fetcher.parse_llms_txt('https://strandsagents.com/llm.txt')

            # Assert
            assert len(result) == 2
            assert ('Getting Started', 'https://strandsagents.com/doc1') in result
            assert ('API Reference', 'https://strandsagents.com/doc2') in result

    def test_parse_llms_txt_handles_empty_titles(self):
        """Test parse_llms_txt handles links with empty titles."""
        # Arrange
        llms_content = '[](https://strandsagents.com/doc1) [Title](https://strandsagents.com/doc2)'

        with patch.object(doc_fetcher, '_get', return_value=llms_content):
            # Act
            result = doc_fetcher.parse_llms_txt('https://strandsagents.com/llms.txt')

            # Assert
            assert len(result) == 1  # Empty title links are filtered out
            assert ('Title', 'https://strandsagents.com/doc2') in result

    def test_html_to_text_removes_script_style(self):
        """Test _html_to_text removes script and style blocks."""
        # Arrange
        html = """
        <html>
        <head>
            <style>body { color: red; }</style>
            <script>alert('test');</script>
        </head>
        <body>
            <p>This is visible content.</p>
            <noscript>No script content</noscript>
        </body>
        </html>
        """

        # Act
        result = doc_fetcher._html_to_text(html)

        # Assert
        assert 'color: red' not in result
        assert "alert('test')" not in result
        assert 'No script content' not in result
        assert 'This is visible content.' in result

    def test_html_to_text_removes_tags(self):
        """Test _html_to_text removes HTML tags."""
        # Arrange
        html = '<p>Hello <strong>world</strong>!</p><br><div>More content</div>'

        # Act
        result = doc_fetcher._html_to_text(html)

        # Assert
        assert '<p>' not in result
        assert '<strong>' not in result
        assert '<br>' not in result
        assert 'Hello' in result
        assert 'world' in result
        assert 'More content' in result

    def test_html_to_text_unescapes_entities(self):
        """Test _html_to_text unescapes HTML entities."""
        # Arrange
        html = '<p>Hello &amp; goodbye &lt;world&gt; &quot;test&quot;</p>'

        # Act
        result = doc_fetcher._html_to_text(html)

        # Assert
        assert 'Hello & goodbye <world> "test"' in result

    def test_extract_html_title_from_title_tag(self):
        """Test _extract_html_title extracts from title tag."""
        # Arrange
        html = '<html><head><title>Page Title</title></head><body>Content</body></html>'

        # Act
        result = doc_fetcher._extract_html_title(html)

        # Assert
        assert result == 'Page Title'

    def test_extract_html_title_from_og_meta(self):
        """Test _extract_html_title extracts from Open Graph meta tag."""
        # Arrange
        html = '<html><head><meta property="og:title" content="OG Title"></head><body>Content</body></html>'

        # Act
        result = doc_fetcher._extract_html_title(html)

        # Assert
        assert result == 'OG Title'

    def test_extract_html_title_from_h1(self):
        """Test _extract_html_title extracts from h1 tag as fallback."""
        # Arrange
        html = '<html><body><h1>Header <span>Title</span></h1><p>Content</p></body></html>'

        # Act
        result = doc_fetcher._extract_html_title(html)

        # Assert
        assert result == 'Header  Title'  # Extra space from tag removal

    def test_extract_html_title_returns_none_when_not_found(self):
        """Test _extract_html_title returns None when no title found."""
        # Arrange
        html = '<html><body><p>Just content, no title</p></body></html>'

        # Act
        result = doc_fetcher._extract_html_title(html)

        # Assert
        assert result is None

    def test_extract_html_title_unescapes_entities(self):
        """Test _extract_html_title unescapes HTML entities in titles."""
        # Arrange
        html = '<html><head><title>Title &amp; Subtitle</title></head></html>'

        # Act
        result = doc_fetcher._extract_html_title(html)

        # Assert
        assert result == 'Title & Subtitle'

    @patch.object(doc_fetcher, '_get')
    def test_fetch_and_clean_html_content(self, mock_get):
        """Test fetch_and_clean processes HTML content correctly."""
        # Arrange
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Heading</h1>
            <p>This is test content.</p>
        </body>
        </html>
        """
        mock_get.return_value = html_content

        # Act
        result = doc_fetcher.fetch_and_clean('https://strandsagents.com/page')

        # Assert
        assert result.url == 'https://strandsagents.com/page'
        assert result.title == 'Test Page'
        assert 'Main Heading' in result.content
        assert 'This is test content.' in result.content
        assert '<html>' not in result.content

    @patch.object(doc_fetcher, '_get')
    def test_fetch_and_clean_plain_text_content(self, mock_get):
        """Test fetch_and_clean processes plain text content."""
        # Arrange
        text_content = 'This is plain text content without HTML tags.'
        mock_get.return_value = text_content

        # Act
        result = doc_fetcher.fetch_and_clean('https://strandsagents.com/doc.txt')

        # Assert
        assert result.url == 'https://strandsagents.com/doc.txt'
        assert result.title == 'doc.txt'
        assert result.content == text_content

    @patch.object(doc_fetcher, '_get')
    def test_fetch_and_clean_markdown_content(self, mock_get):
        """Test fetch_and_clean processes markdown content as plain text."""
        # Arrange
        markdown_content = """
        # Main Title

        This is markdown content with **bold** text and [links](https://example.com).

        ## Subsection

        More content here.
        """
        mock_get.return_value = markdown_content

        # Act
        result = doc_fetcher.fetch_and_clean('https://strandsagents.com/doc.md')

        # Assert
        assert result.url == 'https://strandsagents.com/doc.md'
        assert result.title == 'doc.md'
        assert result.content == markdown_content

    @patch.object(doc_fetcher, '_get')
    def test_fetch_and_clean_html_without_title(self, mock_get):
        """Test fetch_and_clean handles HTML without extractable title."""
        # Arrange
        html_content = '<html><body><p>Content without title</p></body></html>'
        mock_get.return_value = html_content

        # Act
        result = doc_fetcher.fetch_and_clean('https://strandsagents.com/page.html')

        # Assert
        assert result.url == 'https://strandsagents.com/page.html'
        assert result.title == 'page.html'  # Falls back to filename
        assert 'Content without title' in result.content
