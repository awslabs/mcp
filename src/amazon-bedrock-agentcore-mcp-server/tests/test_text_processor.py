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

"""Tests for the text_processor utility module."""

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import doc_fetcher, text_processor


class TestTextProcessor:
    """Test cases for text processing utilities."""

    def test_normalize_collapses_whitespace(self):
        """Test normalize collapses multiple whitespace characters."""
        # Test multiple spaces
        assert text_processor.normalize('hello    world') == 'hello world'

        # Test mixed whitespace
        assert text_processor.normalize('hello\t\n  world') == 'hello world'

        # Test leading/trailing whitespace
        assert text_processor.normalize('  hello world  ') == 'hello world'

        # Test empty string
        assert text_processor.normalize('') == ''

    def test_title_from_url_extracts_slug(self):
        """Test title_from_url extracts and formats URL slug."""
        # Basic URL
        assert (
            text_processor.title_from_url('https://example.com/getting-started')
            == 'Getting Started'
        )

        # URL with multiple path segments
        assert (
            text_processor.title_from_url('https://example.com/docs/api/reference') == 'Reference'
        )

        # URL with underscores
        assert (
            text_processor.title_from_url('https://example.com/agent_core_overview')
            == 'Agent Core Overview'
        )

        # URL ending with index file
        assert text_processor.title_from_url('https://example.com/docs/index.html') == 'Docs'

        # URL with no path - uses domain as fallback
        assert text_processor.title_from_url('https://example.com') == 'Example.Com'

    def test_format_display_title_prioritizes_curated(self):
        """Test format_display_title prioritizes curated titles."""
        url = 'https://example.com/doc'
        extracted = 'Extracted Title'
        url_titles = {url: 'Curated Title'}

        result = text_processor.format_display_title(url, extracted, url_titles)
        assert result == 'Curated Title'

    def test_format_display_title_uses_extracted_when_available(self):
        """Test format_display_title uses extracted title when no curated title."""
        url = 'https://example.com/doc'
        extracted = 'Extracted Title'
        url_titles = {}

        result = text_processor.format_display_title(url, extracted, url_titles)
        assert result == 'Extracted Title'

    def test_format_display_title_falls_back_to_url(self):
        """Test format_display_title falls back to URL-derived title."""
        url = 'https://example.com/getting-started'
        extracted = None
        url_titles = {}

        result = text_processor.format_display_title(url, extracted, url_titles)
        assert result == 'Getting Started'

    def test_format_display_title_handles_generic_titles(self):
        """Test format_display_title handles generic extracted titles."""
        url = 'https://example.com/getting-started'
        url_titles = {}

        # Test generic titles that should fall back to URL
        generic_titles = ['index', 'Index', 'index.md', 'INDEX.MD']
        for title in generic_titles:
            result = text_processor.format_display_title(url, title, url_titles)
            assert result == 'Getting Started'

    def test_index_title_variants_generates_variants(self):
        """Test index_title_variants generates searchable variants."""
        display_title = 'Agent Core Overview'
        url = 'https://example.com/agent-core-overview'

        result = text_processor.index_title_variants(display_title, url)

        # Should contain the display title
        assert 'Agent Core Overview' in result
        # Should contain URL-derived variant
        assert 'Agent Core Overview' in result

    def test_index_title_variants_handles_numeric_substitution(self):
        """Test index_title_variants handles numeric-to-word substitution."""
        display_title = 'Agent2Agent Communication'
        url = 'https://example.com/agent2agent'

        result = text_processor.index_title_variants(display_title, url)

        # Should contain variant with 'to' substitution
        assert 'Agent to Agent Communication' in result

    def test_normalize_for_comparison_removes_punctuation(self):
        """Test normalize_for_comparison removes punctuation and normalizes case."""
        assert text_processor.normalize_for_comparison('Hello, World!') == 'hello world'
        assert (
            text_processor.normalize_for_comparison('Agent-Core_Overview') == 'agent core overview'
        )
        assert text_processor.normalize_for_comparison('API v2.0') == 'api v2 0'

    def test_make_snippet_returns_title_for_empty_page(self):
        """Test make_snippet returns title when page is empty or None."""
        display_title = 'Test Document'

        # Test with None page
        result = text_processor.make_snippet(None, display_title)
        assert result == display_title

        # Test with empty content
        empty_page = doc_fetcher.Page(url='test', title='Test', content='')
        result = text_processor.make_snippet(empty_page, display_title)
        assert result == display_title

    def test_make_snippet_removes_code_blocks(self):
        """Test make_snippet removes code blocks from content."""
        content = """
        This is some text.

        ```python
        def example():
            return "code"
        ```

        This is more text after the code block.
        """
        page = doc_fetcher.Page(url='test', title='Test', content=content)

        result = text_processor.make_snippet(page, 'Test Document')

        # Should not contain code block content
        assert 'def example' not in result
        assert 'This is some text' in result
        # The snippet stops at the first meaningful paragraph
        # so it may not include text after code blocks

    def test_make_snippet_skips_title_line(self):
        """Test make_snippet skips first line if it matches the title."""
        display_title = 'Test Document'
        content = f"""
        # {display_title}

        This is the actual content that should be in the snippet.
        """
        page = doc_fetcher.Page(url='test', title='Test', content=content)

        result = text_processor.make_snippet(page, display_title)

        # Should not contain the title line
        assert '# Test Document' not in result
        assert 'This is the actual content' in result

    def test_make_snippet_skips_headings_and_toc(self):
        """Test make_snippet skips headings and table of contents entries."""
        content = """
        # Main Title

        ## Subsection

        - Table of contents item
        - Another TOC item
        1. Numbered list item

        This is the actual paragraph content that should be included in the snippet.
        """
        page = doc_fetcher.Page(url='test', title='Test', content=content)

        result = text_processor.make_snippet(page, 'Test Document')

        # Should skip headings and TOC
        assert 'Main Title' not in result
        assert 'Subsection' not in result
        assert 'Table of contents' not in result
        assert 'This is the actual paragraph' in result

    def test_make_snippet_truncates_long_content(self):
        """Test make_snippet truncates content that exceeds max_chars."""
        long_content = 'This is a very long piece of content. ' * 20
        page = doc_fetcher.Page(url='test', title='Test', content=long_content)

        result = text_processor.make_snippet(page, 'Test Document', max_chars=100)

        # Should be truncated with ellipsis
        assert len(result) <= 100
        assert result.endswith('…')

    def test_make_snippet_stops_at_sentence_end(self):
        """Test make_snippet stops at sentence boundaries when possible."""
        content = """
        This is the first sentence. This is the second sentence that continues for a while.
        This is another sentence.
        """
        page = doc_fetcher.Page(url='test', title='Test', content=content)

        result = text_processor.make_snippet(page, 'Test Document')

        # Should include complete sentences
        assert 'This is the first sentence.' in result
