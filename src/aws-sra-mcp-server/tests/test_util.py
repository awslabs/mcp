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

from unittest.mock import MagicMock, patch

from awslabs.aws_sra_mcp_server.util import (
    extract_content_from_html,
    format_result,
    is_html_content,
    parse_recommendation_results,
)


def test_extract_content_from_html_empty():
    """Test extract_content_from_html with empty HTML."""
    result = extract_content_from_html("")
    assert result == "<e>Empty HTML content</e>"


def test_extract_content_from_html_none():
    """Test extract_content_from_html with None HTML."""
    result = extract_content_from_html(None)
    assert result == "<e>Empty HTML content</e>"


@patch("bs4.BeautifulSoup")
@patch("markdownify.markdownify")
def test_extract_content_from_html_success(mock_markdownify, mock_bs):
    """Test successful extract_content_from_html."""
    mock_soup = MagicMock()
    mock_main_content = MagicMock()
    mock_soup.select_one.return_value = mock_main_content
    mock_soup.body = None
    mock_bs.return_value = mock_soup
    mock_markdownify.return_value = "# Test Content\n\nThis is test content."
    
    html = "<html><body><main><h1>Test</h1><p>Content</p></main></body></html>"
    result = extract_content_from_html(html)


def test_format_result_no_content_available():
    """Test format_result when start_index is beyond content length."""
    content = "Short content"
    url = "https://example.com"
    content_type = "Documentation"
    max_length = 1000
    start_index = 100  # Beyond content length
    
    result = format_result(url, content, start_index, max_length, content_type)
    
    assert "No more content available" in result
    assert url in result
    assert content_type in result


@patch("bs4.BeautifulSoup")
@patch("markdownify.markdownify")
def test_extract_content_from_html_no_main_uses_body(mock_markdownify, mock_bs):
    """Test extract_content_from_html uses body when no main content."""
    mock_soup = MagicMock()
    mock_body = MagicMock()
    mock_soup.select_one.return_value = None
    mock_soup.body = mock_body
    mock_bs.return_value = mock_soup
    mock_markdownify.return_value = "Body content"
    
    html = "<html><body><p>Content</p></body></html>"
    result = extract_content_from_html(html)
    
    assert result == "Body content"


@patch("bs4.BeautifulSoup")
@patch("markdownify.markdownify")
def test_extract_content_from_html_no_body_uses_soup(mock_markdownify, mock_bs):
    """Test extract_content_from_html uses soup when no body."""
    mock_soup = MagicMock()
    mock_soup.select_one.return_value = None
    mock_soup.body = None
    mock_bs.return_value = mock_soup
    mock_markdownify.return_value = "Full document content"
    
    html = "<html><p>Content</p></html>"
    result = extract_content_from_html(html)
    
    assert result == "Full document content"


@patch("bs4.BeautifulSoup")
@patch("markdownify.markdownify")
def test_extract_content_from_html_removes_nav(mock_markdownify, mock_bs):
    """Test extract_content_from_html removes navigation elements."""
    mock_soup = MagicMock()
    mock_main_content = MagicMock()
    mock_nav_element = MagicMock()
    
    mock_soup.select_one.return_value = mock_main_content
    mock_main_content.select.return_value = [mock_nav_element]
    mock_bs.return_value = mock_soup
    mock_markdownify.return_value = "Clean content"
    
    html = "<html><body><main><nav>Navigation</nav><p>Content</p></main></body></html>"
    result = extract_content_from_html(html)
    
    mock_nav_element.decompose.assert_called()
    assert result == "Clean content"


@patch("bs4.BeautifulSoup")
@patch("markdownify.markdownify")
def test_extract_content_from_html_empty_result(mock_markdownify, mock_bs):
    """Test extract_content_from_html when markdownify returns empty."""
    mock_soup = MagicMock()
    mock_main_content = MagicMock()
    mock_soup.select_one.return_value = mock_main_content
    mock_bs.return_value = mock_soup
    mock_markdownify.return_value = ""
    
    html = "<html><body><main></main></body></html>"
    result = extract_content_from_html(html)
    
    assert result == "<e>Page failed to be simplified from HTML</e>"


@patch("bs4.BeautifulSoup")
def test_extract_content_from_html_exception(mock_bs):
    """Test extract_content_from_html with exception."""
    mock_bs.side_effect = Exception("Parsing error")
    
    html = "<html><body><p>Content</p></body></html>"
    result = extract_content_from_html(html)
    
    assert result.startswith("<e>Error converting HTML to Markdown:")
    assert "Parsing error" in result


def test_is_html_content_with_html_tag():
    """Test is_html_content with HTML tag."""
    page_raw = "<html><head><title>Test</title></head><body>Content</body></html>"
    result = is_html_content(page_raw, "")
    assert result is True


def test_is_html_content_with_content_type():
    """Test is_html_content with HTML content type."""
    page_raw = "Some content without HTML tags"
    result = is_html_content(page_raw, "text/html; charset=utf-8")
    assert result is True


def test_is_html_content_no_content_type():
    """Test is_html_content with no content type."""
    page_raw = "Some content without HTML tags"
    result = is_html_content(page_raw, "")
    assert result is True


def test_is_html_content_false():
    """Test is_html_content returning false."""
    page_raw = "Plain text content without any HTML indicators"
    result = is_html_content(page_raw, "text/plain")
    assert result is False


def test_is_html_content_html_tag_not_at_start():
    """Test is_html_content when HTML tag is not at start."""
    page_raw = "Some prefix content <html><body>Content</body></html>"
    result = is_html_content(page_raw, "text/plain")
    assert result is True


def test_format_result_no_truncation():
    """Test format_result without truncation."""
    content = "Short content"
    result = format_result(url="https://example.com/test", content=content, start_index=0, max_length=100, content_type="Test")
    
    expected = "AWS Security Reference Architecture Test from https://example.com/test:\n\nShort content"
    assert result == expected


def test_format_result_with_truncation():
    """Test format_result with truncation."""
    content = "This is a very long content that will be truncated for testing purposes"
    result = format_result(url="https://example.com/test", content=content, start_index=0, max_length=20, content_type="Test")
    
    assert "This is a very long" in result
    assert "start_index=20" in result
    assert "Content truncated" in result


def test_format_result_start_index_beyond_content():
    """Test format_result when start index is beyond content length."""
    content = "Short content"
    result = format_result(url="https://example.com/test", content=content, start_index=100, max_length=50, content_type="Test")
    
    assert "No more content available" in result


def test_format_result_empty_truncated_content():
    """Test format_result when truncated content is empty."""
    content = "Content"
    result = format_result(url="https://example.com/test", content=content, start_index=7, max_length=50, content_type="Test")
    
    assert "No more content available" in result


def test_format_result_with_start_index():
    """Test format_result with non-zero start index."""
    content = "This is a long content that spans multiple pages for testing"
    result = format_result(url="https://example.com/test", content=content, start_index=10, max_length=20, content_type="Test")
    
    assert "long content that sp" in result
    assert "start_index=30" in result


def test_format_result_default_content_type():
    """Test format_result with default content type."""
    content = "Test content"
    result = format_result(url="https://example.com/test", content=content, start_index=0, max_length=100)
    
    assert "AWS Security Reference Architecture Documentation from" in result


def test_parse_recommendation_results_empty():
    """Test parse_recommendation_results with empty data."""
    result = parse_recommendation_results({})
    assert result == []


def test_parse_recommendation_results_highly_rated():
    """Test parse_recommendation_results with highly rated items."""
    data = {
        "highlyRated": {
            "items": [
                {"url": "https://example.com/1", "assetTitle": "Test Title 1", "abstract": "Test abstract 1"},
                {"url": "https://example.com/2", "assetTitle": "Test Title 2"},
            ]
        }
    }
    results = parse_recommendation_results(data)
    assert len(results) == 2
    assert results[0].context == "Test abstract 1"
    assert results[1].context is None


def test_parse_recommendation_results_journey():
    """Test parse_recommendation_results with journey items."""
    data = {
        "journey": {
            "items": [
                {
                    "intent": "Security Setup",
                    "urls": [{"url": "https://example.com/journey1", "assetTitle": "Journey Title 1"}],
                }
            ]
        }
    }
    results = parse_recommendation_results(data)
    assert len(results) == 1
    assert results[0].context == "Intent: Security Setup"


def test_parse_recommendation_results_new():
    """Test parse_recommendation_results with new content items."""
    data = {
        "new": {
            "items": [
                {"url": "https://example.com/new1", "assetTitle": "New Title 1", "dateCreated": "2024-01-01"},
                {"url": "https://example.com/new2", "assetTitle": "New Title 2"},
            ]
        }
    }
    results = parse_recommendation_results(data)
    assert len(results) == 2
    assert results[0].context == "New content added on 2024-01-01"
    assert results[1].context == "New content"


def test_parse_recommendation_results_similar():
    """Test parse_recommendation_results with similar items."""
    data = {
        "similar": {
            "items": [
                {"url": "https://example.com/similar1", "assetTitle": "Similar Title 1", "abstract": "Similar abstract 1"},
                {"url": "https://example.com/similar2", "assetTitle": "Similar Title 2"},
            ]
        }
    }
    results = parse_recommendation_results(data)
    assert len(results) == 2
    assert results[0].context == "Similar abstract 1"
    assert results[1].context == "Similar content"


def test_parse_recommendation_results_missing_fields():
    """Test parse_recommendation_results with missing fields."""
    data = {
        "highlyRated": {
            "items": [{"abstract": "Test abstract"}]
        }
    }
    results = parse_recommendation_results(data)
    assert len(results) == 1
    assert results[0].url == ""
    assert results[0].title == ""
    assert results[0].context == "Test abstract"
