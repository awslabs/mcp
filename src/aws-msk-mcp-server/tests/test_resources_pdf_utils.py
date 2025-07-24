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

"""Unit tests for the resources/pdf_utils.py module."""

import pytest
from awslabs.aws_msk_mcp_server.resources.pdf_utils import (
    DEFAULT_USER_AGENT,
    PDF_RESOURCES,
    extract_pdf_content,
    extract_pdf_toc,
    get_pdf_content,
)
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch


# Use pytest style tests instead of unittest.TestCase
class TestPdfUtils:
    """Tests for the pdf_utils.py module."""

    @pytest.mark.asyncio
    async def test_get_pdf_content_success(self):
        """Test get_pdf_content with successful HTTP response."""
        # Mock response content
        mock_content = b'mock pdf content'

        # Create a mock response
        mock_response = MagicMock()
        mock_response.content = mock_content
        mock_response.raise_for_status = MagicMock()

        # Create a mock AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response

        # Patch httpx.AsyncClient to return our mock
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Call the function under test
            result = await get_pdf_content('developer-guide')

            # Verify the result
            assert result == mock_content

            # Verify the client was called with the correct arguments
            mock_client.__aenter__.return_value.get.assert_called_once_with(
                PDF_RESOURCES['developer-guide']['url'],
                follow_redirects=True,
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=30,
            )
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pdf_content_invalid_id(self):
        """Test get_pdf_content with an invalid PDF ID."""
        # Call the function under test with an invalid ID
        with pytest.raises(ValueError) as excinfo:
            await get_pdf_content('invalid-id')

        # Verify the error message
        assert 'Unknown PDF resource: invalid-id' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_pdf_content_http_error(self):
        """Test get_pdf_content with an HTTP error."""
        # Create a mock response that raises an exception
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('HTTP Error')

        # Create a mock AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response

        # Patch httpx.AsyncClient to return our mock
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Call the function under test and expect an exception
            with pytest.raises(Exception) as excinfo:
                await get_pdf_content('developer-guide')

            # Verify the error message
            assert 'HTTP Error' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_pdf_content_connection_error(self):
        """Test get_pdf_content with a connection error."""
        # Create a mock AsyncClient that raises an exception
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.side_effect = Exception('Connection Error')

        # Patch httpx.AsyncClient to return our mock
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Call the function under test and expect an exception
            with pytest.raises(Exception) as excinfo:
                await get_pdf_content('developer-guide')

            # Verify the error message
            assert 'Connection Error' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_pdf_content_general_exception(self):
        """Test get_pdf_content with a general exception in the try-except block."""
        # Create a mock AsyncClient
        mock_client = AsyncMock()

        # Patch httpx.AsyncClient to return our mock and raise a specific exception
        # that will be caught by the general exception handler
        with patch('httpx.AsyncClient', return_value=mock_client):
            with patch.object(
                mock_client.__aenter__.return_value, 'get', side_effect=Exception('General Error')
            ):
                # Call the function under test and expect an exception
                with pytest.raises(Exception) as excinfo:
                    await get_pdf_content('developer-guide')

                # Verify the error message
                assert 'General Error' in str(excinfo.value)

    def test_extract_pdf_content_success(self):
        """Test extract_pdf_content with valid PDF content."""
        # Create a mock PDF reader
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = 'Page 1 content'

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = 'Page 2 content'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test
            result = extract_pdf_content(b'mock pdf content', 1, 2)

            # Verify the result
            assert result['content'] == 'Page 1 content\n\n--- Page Break ---\n\nPage 2 content'
            assert result['pagination'] == {
                'start_page': 1,
                'end_page': 2,
                'total_pages': 2,
                'has_more': False,
            }

    def test_extract_pdf_content_default_end_page(self):
        """Test extract_pdf_content with default end_page (None)."""
        # Create a mock PDF reader
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = 'Page 1 content'

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = 'Page 2 content'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test with default end_page
            result = extract_pdf_content(b'mock pdf content', 1)

            # Verify the result
            assert result['content'] == 'Page 1 content\n\n--- Page Break ---\n\nPage 2 content'
            assert result['pagination'] == {
                'start_page': 1,
                'end_page': 2,
                'total_pages': 2,
                'has_more': False,
            }

    def test_extract_pdf_content_invalid_start_page(self):
        """Test extract_pdf_content with an invalid start_page."""
        # Create a mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = 'Page content'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test with an invalid start_page
            result = extract_pdf_content(b'mock pdf content', 0)

            # Verify the result (should adjust start_page to 1)
            assert result['content'] == 'Page content'
            assert result['pagination'] == {
                'start_page': 1,
                'end_page': 1,
                'total_pages': 1,
                'has_more': False,
            }

    def test_extract_pdf_content_end_page_exceeds_total(self):
        """Test extract_pdf_content with end_page exceeding total pages."""
        # Create a mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = 'Page content'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test with end_page > total pages
            result = extract_pdf_content(b'mock pdf content', 1, 5)

            # Verify the result (should adjust end_page to total pages)
            assert result['content'] == 'Page content'
            assert result['pagination'] == {
                'start_page': 1,
                'end_page': 1,
                'total_pages': 1,
                'has_more': False,
            }

    def test_extract_pdf_content_bytesio_error(self):
        """Test extract_pdf_content with an error creating BytesIO."""
        # Patch io.BytesIO to raise an exception
        with patch('io.BytesIO', side_effect=Exception('BytesIO Error')):
            # Call the function under test
            result = extract_pdf_content(b'mock pdf content')

            # Verify the result contains an error message
            assert 'error' in result
            assert result['content'] is None
            assert 'BytesIO Error' in result['error']

    def test_extract_pdf_content_pdfreader_error(self):
        """Test extract_pdf_content with an error creating PdfReader."""
        # Patch PyPDF2.PdfReader to raise an exception
        with patch('PyPDF2.PdfReader', side_effect=Exception('PdfReader Error')):
            # Call the function under test
            result = extract_pdf_content(b'mock pdf content')

            # Verify the result contains an error message
            assert 'error' in result
            assert result['content'] is None
            assert 'PdfReader Error' in result['error']

    def test_extract_pdf_content_page_extraction_error(self):
        """Test extract_pdf_content with an error extracting page text."""
        # Create a mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.side_effect = Exception('Page Extraction Error')

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test
            result = extract_pdf_content(b'mock pdf content')

            # Verify the result contains an error message
            assert 'error' in result
            assert result['content'] is None
            assert 'Page Extraction Error' in result['error']

    def test_extract_pdf_content_general_exception(self):
        """Test extract_pdf_content with a general exception in the outer try-except block."""
        # Create a mock PDF reader that passes the initial creation but fails when accessing pages
        mock_reader = MagicMock()
        # Use PropertyMock to raise an exception when the 'pages' property is accessed
        type(mock_reader).pages = PropertyMock(side_effect=Exception('General Error'))

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test
            result = extract_pdf_content(b'mock pdf content')

            # Verify the result contains an error message
            assert 'error' in result
            assert result['content'] is None
            assert 'General Error' in result['error']

    def test_extract_pdf_toc_success(self):
        """Test extract_pdf_toc with valid PDF content."""
        # Create mock pages with text content
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = 'Chapter 1\nSome content'

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = 'Chapter 2\nMore content'

        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = '123\n'  # Should be skipped (isdigit)

        mock_page4 = MagicMock()
        mock_page4.extract_text.return_value = 'A\n'  # Should be skipped (too short)

        mock_page5 = MagicMock()
        mock_page5.extract_text.return_value = ''  # Should be skipped (empty)

        # Create a mock PDF reader
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3, mock_page4, mock_page5]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test
            result = extract_pdf_toc(b'mock pdf content')

            # Verify the result
            assert len(result) == 2
            assert result[0] == {'title': 'Chapter 1', 'page': 1}
            assert result[1] == {'title': 'Chapter 2', 'page': 2}

    def test_extract_pdf_toc_page_extraction_error(self):
        """Test extract_pdf_toc with an error extracting page text."""
        # Create a mock page that raises an exception
        mock_page = MagicMock()
        mock_page.extract_text.side_effect = Exception('Page Extraction Error')

        # Create a mock PDF reader
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        # Patch PyPDF2.PdfReader to return our mock
        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            # Call the function under test
            result = extract_pdf_toc(b'mock pdf content')

            # Verify the result is an empty list (errors are skipped)
            assert result == []

    def test_extract_pdf_toc_pdfreader_error(self):
        """Test extract_pdf_toc with an error creating PdfReader."""
        # Patch PyPDF2.PdfReader to raise an exception
        with patch('PyPDF2.PdfReader', side_effect=Exception('PdfReader Error')):
            # Call the function under test
            result = extract_pdf_toc(b'mock pdf content')

            # Verify the result is an empty list
            assert result == []

    def test_extract_pdf_toc_bytesio_error(self):
        """Test extract_pdf_toc with an error creating BytesIO."""
        # Patch io.BytesIO to raise an exception
        with patch('io.BytesIO', side_effect=Exception('BytesIO Error')):
            # Call the function under test
            result = extract_pdf_toc(b'mock pdf content')

            # Verify the result is an empty list
            assert result == []


# No need for unittest.main() with pytest
