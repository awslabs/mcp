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

"""Tests for the PDF utilities module."""

import pytest
from awslabs.aws_msk_mcp_server.resources.documentation.pdf_utils import (
    PDF_RESOURCES,
    extract_pdf_content,
    extract_pdf_toc,
    get_pdf_content,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestPDFUtils:
    """Tests for the PDF utilities module."""

    def test_pdf_resources_structure(self):
        """Test the PDF_RESOURCES dictionary structure."""
        # Assert
        assert 'developer-guide' in PDF_RESOURCES
        assert 'title' in PDF_RESOURCES['developer-guide']
        assert 'url' in PDF_RESOURCES['developer-guide']
        assert PDF_RESOURCES['developer-guide']['title'] == 'Amazon MSK Developer Guide'
        assert 'docs.aws.amazon.com' in PDF_RESOURCES['developer-guide']['url']

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_pdf_content_success(self, mock_async_client):
        """Test the get_pdf_content function with successful HTTP response."""
        # Arrange
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = b'mock pdf content'
        mock_response.raise_for_status = AsyncMock()

        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_async_client.return_value = mock_client

        # Act
        result = await get_pdf_content('developer-guide')

        # Assert
        assert result == b'mock pdf content'
        mock_client.get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_pdf_content_invalid_id(self, mock_async_client):
        """Test the get_pdf_content function with an invalid PDF ID."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            await get_pdf_content('invalid-id')

        assert 'Unknown PDF resource' in str(excinfo.value)
        mock_async_client.assert_not_called()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_pdf_content_http_error(self, mock_async_client):
        """Test the get_pdf_content function when the HTTP request fails."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception('HTTP request failed')
        mock_async_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await get_pdf_content('developer-guide')

        assert 'HTTP request failed' in str(excinfo.value)

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_content_success(self, mock_pdf_reader):
        """Test the extract_pdf_content function with successful PDF extraction."""
        # Arrange
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        mock_page1.extract_text.return_value = 'Page 1 content'
        mock_page2.extract_text.return_value = 'Page 2 content'

        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        # Act
        result = extract_pdf_content(b'mock pdf content', 1, 2)

        # Assert
        assert 'content' in result
        assert 'pagination' in result
        assert 'Page 1 content' in result['content']
        assert 'Page 2 content' in result['content']
        assert result['pagination']['start_page'] == 1
        assert result['pagination']['end_page'] == 2
        assert result['pagination']['total_pages'] == 2
        assert result['pagination']['has_more'] is False

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_content_partial_pages(self, mock_pdf_reader):
        """Test the extract_pdf_content function with partial page range."""
        # Arrange
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_page3 = MagicMock()

        mock_page1.extract_text.return_value = 'Page 1 content'
        mock_page2.extract_text.return_value = 'Page 2 content'
        mock_page3.extract_text.return_value = 'Page 3 content'

        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf_reader.return_value = mock_reader

        # Act
        result = extract_pdf_content(b'mock pdf content', 2, 2)

        # Assert
        assert 'content' in result
        assert 'pagination' in result
        assert 'Page 1 content' not in result['content']
        assert 'Page 2 content' in result['content']
        assert 'Page 3 content' not in result['content']
        assert result['pagination']['start_page'] == 2
        assert result['pagination']['end_page'] == 2
        assert result['pagination']['total_pages'] == 3
        assert result['pagination']['has_more'] is True

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_content_invalid_range(self, mock_pdf_reader):
        """Test the extract_pdf_content function with invalid page range."""
        # Arrange
        mock_reader = MagicMock()
        mock_page1 = MagicMock()

        mock_page1.extract_text.return_value = 'Page 1 content'

        mock_reader.pages = [mock_page1]
        mock_pdf_reader.return_value = mock_reader

        # Act
        result = extract_pdf_content(b'mock pdf content', 0, 5)

        # Assert
        assert 'content' in result
        assert 'pagination' in result
        assert 'Page 1 content' in result['content']
        assert result['pagination']['start_page'] == 1
        assert result['pagination']['end_page'] == 1
        assert result['pagination']['total_pages'] == 1
        assert result['pagination']['has_more'] is False

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_content_error(self, mock_pdf_reader):
        """Test the extract_pdf_content function when PDF extraction fails."""
        # Arrange
        mock_pdf_reader.side_effect = Exception('PDF extraction failed')

        # Act
        result = extract_pdf_content(b'mock pdf content')

        # Assert
        assert 'error' in result
        assert 'Failed to extract PDF content' in result['error']
        assert result['content'] is None

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_toc_success(self, mock_pdf_reader):
        """Test the extract_pdf_toc function with successful TOC extraction."""
        # Arrange
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        mock_page1.extract_text.return_value = 'Introduction\nThis is the introduction'
        mock_page2.extract_text.return_value = (
            'Getting Started\nThis is the getting started section'
        )

        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        # Act
        result = extract_pdf_toc(b'mock pdf content')

        # Assert
        assert len(result) == 2
        assert result[0]['title'] == 'Introduction'
        assert result[0]['page'] == 1
        assert result[1]['title'] == 'Getting Started'
        assert result[1]['page'] == 2

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_toc_empty_pages(self, mock_pdf_reader):
        """Test the extract_pdf_toc function with empty pages."""
        # Arrange
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        mock_page1.extract_text.return_value = ''
        mock_page2.extract_text.return_value = ''

        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        # Act
        result = extract_pdf_toc(b'mock pdf content')

        # Assert
        assert len(result) == 0

    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_toc_error(self, mock_pdf_reader):
        """Test the extract_pdf_toc function when TOC extraction fails."""
        # Arrange
        mock_pdf_reader.side_effect = Exception('TOC extraction failed')

        # Act
        result = extract_pdf_toc(b'mock pdf content')

        # Assert
        assert len(result) == 0
