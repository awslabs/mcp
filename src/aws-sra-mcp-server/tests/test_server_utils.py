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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.aws_sra_mcp_server.server_utils import (
    _fetch_url,
    _process_code_content,
    _process_html_content,
    _process_markdown_content,
    _read_documentation_base,
    log_truncation,
    read_documentation_html,
    read_documentation_markdown,
    read_other,
)


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
@patch("awslabs.aws_sra_mcp_server.server_utils.is_html_content")
@patch("awslabs.aws_sra_mcp_server.server_utils.extract_content_from_html")
@patch("awslabs.aws_sra_mcp_server.server_utils.format_result")
async def test_read_documentation_html_success(mock_format, mock_extract, mock_is_html, mock_client, mock_context):
    """Test successful read_documentation_html execution."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test content</body></html>"
    mock_response.headers = {"content-type": "text/html"}

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    mock_is_html.return_value = True
    mock_extract.return_value = "Extracted content"
    mock_format.return_value = "Formatted content"

    result = await read_documentation_html(mock_context, "https://docs.aws.amazon.com/test.html", 1000, 0, "test-session")

    assert result == "Formatted content"
    mock_is_html.assert_called_once_with("<html><body>Test content</body></html>", "")
    mock_extract.assert_called_once_with("<html><body>Test content</body></html>")


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
async def test_read_documentation_html_http_error(mock_client, mock_context):
    """Test read_documentation_html with HTTP error."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = Exception("HTTP error")
    mock_client.return_value = mock_client_instance

    result = await read_documentation_html(mock_context, "https://docs.aws.amazon.com/test.html", 1000, 0, "test-session")

    assert "Failed to fetch" in result
    assert "HTTP error" in result
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
async def test_read_documentation_html_status_error(mock_client, mock_context):
    """Test read_documentation_html with HTTP status error."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    result = await read_documentation_html(mock_context, "https://docs.aws.amazon.com/test.html", 1000, 0, "test-session")

    assert "Failed to fetch" in result
    assert "status code 404" in result
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
async def test_fetch_url_success(mock_client, mock_context):
    """Test _fetch_url success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Test content"

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    content, error = await _fetch_url(mock_context, "https://example.com", "session-123")

    assert content == "Test content"
    assert error is None


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
async def test_fetch_url_http_error(mock_client, mock_context):
    """Test _fetch_url with HTTP error status."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    content, error = await _fetch_url(mock_context, "https://example.com", "session-123")

    assert content == ""
    assert "status code 404" in error
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils.httpx.AsyncClient")
async def test_fetch_url_exception(mock_client, mock_context):
    """Test _fetch_url with exception."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value.get.side_effect = Exception("Network error")
    mock_client.return_value = mock_client_instance

    content, error = await _fetch_url(mock_context, "https://example.com", "session-123")

    assert content == ""
    assert "Failed to fetch" in error
    assert "Network error" in error
    assert len(mock_context.errors) == 1


@pytest.mark.asyncio
async def test_log_truncation_no_truncation(mock_context):
    """Test log_truncation when content is not truncated."""
    content = "Short content"
    await log_truncation(mock_context, content, start_index=0, max_length=100)
    
    assert len(mock_context.debug_messages) == 0


@pytest.mark.asyncio
async def test_log_truncation_with_truncation(mock_context):
    """Test log_truncation when content is truncated."""
    content = "This is a very long content that will be truncated"
    await log_truncation(mock_context, content, start_index=0, max_length=10)
    
    assert len(mock_context.debug_messages) == 1
    assert "Content truncated at 10 of 50 characters" in mock_context.debug_messages[0]


@pytest.mark.asyncio
async def test_log_truncation_with_start_index(mock_context):
    """Test log_truncation with non-zero start index."""
    content = "This is a very long content that will be truncated"
    await log_truncation(mock_context, content, start_index=5, max_length=10)
    
    assert len(mock_context.debug_messages) == 1
    assert "Content truncated at 15 of 50 characters" in mock_context.debug_messages[0]


def test_process_html_content_is_html():
    """Test _process_html_content with HTML content."""
    html_content = "<html><body><h1>Title</h1><p>Content</p></body></html>"
    
    with patch("awslabs.aws_sra_mcp_server.server_utils.is_html_content", return_value=True):
        with patch("awslabs.aws_sra_mcp_server.server_utils.extract_content_from_html", return_value="# Title\n\nContent"):
            result = _process_html_content(html_content, "text/html")
            assert result == "# Title\n\nContent"


def test_process_html_content_not_html():
    """Test _process_html_content with non-HTML content."""
    text_content = "Plain text content"
    
    with patch("awslabs.aws_sra_mcp_server.server_utils.is_html_content", return_value=False):
        result = _process_html_content(text_content, "text/plain")
        assert result == "Plain text content"


def test_process_markdown_content():
    """Test _process_markdown_content."""
    markdown_content = "# Title\n\nThis is markdown content"
    result = _process_markdown_content(markdown_content, "text/markdown")
    assert result == "# Title\n\nThis is markdown content"


def test_process_code_content():
    """Test _process_code_content."""
    code_content = "def hello():\n    print('Hello, World!')"
    result = _process_code_content(code_content, "text/plain")
    assert result == "```\ndef hello():\n    print('Hello, World!')\n```"


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils._fetch_url")
@patch("awslabs.aws_sra_mcp_server.server_utils.format_result")
@patch("awslabs.aws_sra_mcp_server.server_utils.log_truncation")
async def test_read_documentation_base_success(mock_log_truncation, mock_format_result, mock_fetch_url, mock_context):
    """Test _read_documentation_base success."""
    mock_fetch_url.return_value = ("Raw content", None)
    mock_format_result.return_value = "Formatted result"
    
    def mock_processor(raw_content, content_type):
        return f"Processed: {raw_content}"

    result = await _read_documentation_base(mock_context, "https://example.com", 1000, 0, "session-123", mock_processor)

    assert result == "Formatted result"
    mock_fetch_url.assert_called_once_with(mock_context, "https://example.com", "session-123")
    mock_format_result.assert_called_once_with("https://example.com", "Processed: Raw content", 0, 1000)
    mock_log_truncation.assert_called_once()


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils._fetch_url")
async def test_read_documentation_base_fetch_error(mock_fetch_url, mock_context):
    """Test _read_documentation_base with fetch error."""
    mock_fetch_url.return_value = ("", "Fetch error message")
    
    def mock_processor(raw_content, content_type):
        return f"Processed: {raw_content}"

    result = await _read_documentation_base(mock_context, "https://example.com", 1000, 0, "session-123", mock_processor)

    assert result == "Fetch error message"


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils._read_documentation_base")
async def test_read_documentation_markdown(mock_read_base, mock_context):
    """Test read_documentation_markdown."""
    mock_read_base.return_value = "Markdown result"

    result = await read_documentation_markdown(mock_context, "https://example.com/test.md", 1000, 0, "session-123")

    assert result == "Markdown result"
    mock_read_base.assert_called_once()
    args, kwargs = mock_read_base.call_args
    assert args[5] == _process_markdown_content


@pytest.mark.asyncio
@patch("awslabs.aws_sra_mcp_server.server_utils._read_documentation_base")
async def test_read_other(mock_read_base, mock_context):
    """Test read_other."""
    mock_read_base.return_value = "Code result"

    result = await read_other(mock_context, "https://example.com/test.py", 1000, 0, "session-123")

    assert result == "Code result"
    mock_read_base.assert_called_once()
    args, kwargs = mock_read_base.call_args
    assert args[5] == _process_code_content
