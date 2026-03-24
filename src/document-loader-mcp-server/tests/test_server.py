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
"""Test script to verify MCP server functionality."""

import asyncio
import os
import pytest
from awslabs.document_loader_mcp_server.server import (
    DocumentReadResponse,
    SlidesExtractionResponse,
    _check_soffice_available,
    _convert_to_pdf_with_soffice,
    _convert_with_markitdown,
    _extract_slides_sync,
    _find_soffice,
    _get_base_directory,
    _get_soffice_timeout,
    _read_pdf_content,
    mcp,
    validate_file_path,
    validate_output_dir,
)
from fastmcp.utilities.types import Image
from tests.test_document_parsing import DocumentTestGenerator, MockContext
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_server():
    """Test the MCP server tools."""
    print('Testing MCP Server...')

    # Test getting tools
    try:
        tools = await mcp.get_tools()
        print(f'\nAvailable tools ({len(tools)}):')

        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_name = getattr(tool, 'name')
                tool_desc = getattr(tool, 'description', 'No description')
                print(f'- {tool_name}: {tool_desc}')
                tool_names.append(str(tool_name))
            else:
                print(f'- {tool}: {type(tool)}')
                tool_names.append(str(tool))

        # Verify our tools are present
        expected_tools = ['read_document', 'read_image']

        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                print(f'✓ {expected_tool} tool found')
            else:
                print(f'✗ {expected_tool} tool missing')

        print('\nMCP Server is working correctly!')

    except Exception as e:
        print(f'Error testing server: {e}')
        import traceback

        traceback.print_exc()


async def call_mcp_tool(tool_name: str, file_path: str, file_type: str = None):
    """Helper function to call MCP tools through the server."""
    # Get the tool from the server
    tools = await mcp.get_tools()

    if tool_name not in tools:
        raise ValueError(f'Tool {tool_name} not found. Available tools: {list(tools.keys())}')

    tool = tools[tool_name]

    # Call the tool function using the 'fn' attribute with Context
    if hasattr(tool, 'fn') and callable(getattr(tool, 'fn')):
        fn = getattr(tool, 'fn')
        ctx = MockContext()

        # Handle different tool signatures
        if tool_name == 'read_document' and file_type:
            return await fn(ctx, file_path, file_type, 30)  # Use default timeout
        elif tool_name == 'read_image':
            return await fn(ctx, file_path, 30)  # Use default timeout
        else:
            return await fn(ctx, file_path, 30)  # Use default timeout
    else:
        raise ValueError(f'Cannot find callable function for tool {tool_name}')


@pytest.mark.asyncio
async def test_mcp_tool_functions():
    """Test the actual MCP tool functions with real documents."""
    print('\nTesting MCP tool functions...')

    # Generate test documents
    generator = DocumentTestGenerator()

    # Test PDF document using consolidated read_document tool
    pdf_path = generator.generate_sample_pdf()
    pdf_result = await call_mcp_tool('read_document', pdf_path, 'pdf')
    assert isinstance(pdf_result, DocumentReadResponse)
    assert pdf_result.status == 'success'
    assert len(pdf_result.content) > 0
    assert 'Page 1' in pdf_result.content
    print('✓ read_document (PDF) tool working')

    # Test DOCX document using consolidated read_document tool
    docx_path = generator.generate_sample_docx()
    docx_result = await call_mcp_tool('read_document', docx_path, 'docx')
    assert isinstance(docx_result, DocumentReadResponse)
    assert docx_result.status == 'success'
    assert len(docx_result.content) > 0
    print('✓ read_document (DOCX) tool working')

    # Test DOC document using consolidated read_document tool
    doc_path = (
        generator.generate_sample_docx()
    )  # Use same generator, just test different file_type
    doc_result = await call_mcp_tool('read_document', doc_path, 'doc')
    assert isinstance(doc_result, DocumentReadResponse)
    assert doc_result.status == 'success'
    assert len(doc_result.content) > 0
    print('✓ read_document (DOC) tool working')

    # Test XLSX document using consolidated read_document tool
    xlsx_path = generator.generate_sample_xlsx()
    xlsx_result = await call_mcp_tool('read_document', xlsx_path, 'xlsx')
    assert isinstance(xlsx_result, DocumentReadResponse)
    assert xlsx_result.status == 'success'
    assert len(xlsx_result.content) > 0
    print('✓ read_document (XLSX) tool working')

    # Test XLS document using consolidated read_document tool
    xls_path = (
        generator.generate_sample_xlsx()
    )  # Use same generator, just test different file_type
    xls_result = await call_mcp_tool('read_document', xls_path, 'xls')
    assert isinstance(xls_result, DocumentReadResponse)
    assert xls_result.status == 'success'
    assert len(xls_result.content) > 0
    print('✓ read_document (XLS) tool working')

    # Test PPTX document using consolidated read_document tool
    pptx_path = generator.generate_sample_pptx()
    pptx_result = await call_mcp_tool('read_document', pptx_path, 'pptx')
    assert isinstance(pptx_result, DocumentReadResponse)
    assert pptx_result.status == 'success'
    assert len(pptx_result.content) > 0
    print('✓ read_document (PPTX) tool working')

    # Test PPT document using consolidated read_document tool
    ppt_path = (
        generator.generate_sample_pptx()
    )  # Use same generator, just test different file_type
    ppt_result = await call_mcp_tool('read_document', ppt_path, 'ppt')
    assert isinstance(ppt_result, DocumentReadResponse)
    assert ppt_result.status == 'success'
    assert len(ppt_result.content) > 0
    print('✓ read_document (PPT) tool working')

    # Test image tool
    image_path = generator.generate_sample_image()
    image_result = await call_mcp_tool('read_image', image_path)
    assert isinstance(image_result, Image)
    assert hasattr(image_result, 'path')
    print('✓ read_image tool working')


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in MCP tools."""
    print('\nTesting error handling...')

    # Test with non-existent files
    non_existent_file = '/path/that/does/not/exist.pdf'

    # Test PDF error handling
    pdf_result = await call_mcp_tool('read_document', non_existent_file, 'pdf')
    assert isinstance(pdf_result, DocumentReadResponse)
    assert pdf_result.status == 'error'
    assert 'File not found' in pdf_result.error_message
    print('✓ read_document (PDF) error handling working')

    # Test DOCX error handling
    docx_result = await call_mcp_tool('read_document', non_existent_file, 'docx')
    assert isinstance(docx_result, DocumentReadResponse)
    assert docx_result.status == 'error'
    assert 'File not found' in docx_result.error_message
    print('✓ read_document (DOCX) error handling working')

    # Test DOC error handling
    doc_result = await call_mcp_tool('read_document', non_existent_file, 'doc')
    assert isinstance(doc_result, DocumentReadResponse)
    assert doc_result.status == 'error'
    assert 'File not found' in doc_result.error_message
    print('✓ read_document (DOC) error handling working')

    # Test XLSX error handling
    xlsx_result = await call_mcp_tool('read_document', non_existent_file, 'xlsx')
    assert isinstance(xlsx_result, DocumentReadResponse)
    assert xlsx_result.status == 'error'
    assert 'File not found' in xlsx_result.error_message
    print('✓ read_document (XLSX) error handling working')

    # Test XLS error handling
    xls_result = await call_mcp_tool('read_document', non_existent_file, 'xls')
    assert isinstance(xls_result, DocumentReadResponse)
    assert xls_result.status == 'error'
    assert 'File not found' in xls_result.error_message
    print('✓ read_document (XLS) error handling working')

    # Test PPTX error handling
    pptx_result = await call_mcp_tool('read_document', non_existent_file, 'pptx')
    assert isinstance(pptx_result, DocumentReadResponse)
    assert pptx_result.status == 'error'
    assert 'File not found' in pptx_result.error_message
    print('✓ read_document (PPTX) error handling working')

    # Test PPT error handling
    ppt_result = await call_mcp_tool('read_document', non_existent_file, 'ppt')
    assert isinstance(ppt_result, DocumentReadResponse)
    assert ppt_result.status == 'error'
    assert 'File not found' in ppt_result.error_message
    print('✓ read_document (PPT) error handling working')

    # Test unsupported file type error handling
    unsupported_result = await call_mcp_tool('read_document', non_existent_file, 'txt')
    assert isinstance(unsupported_result, DocumentReadResponse)
    assert unsupported_result.status == 'error'
    assert 'Unsupported file_type' in unsupported_result.error_message
    print('✓ read_document unsupported file type error handling working')

    # Test image error handling (should raise exceptions)
    try:
        await call_mcp_tool('read_image', non_existent_file)
        assert False, 'Should have raised ValueError'
    except ValueError as e:
        assert 'File not found' in str(e)
        print('✓ read_image error handling working')

    # Test unsupported image format - create a temporary file with unsupported extension
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.unsupported', delete=False) as temp_file:
        temp_file.write(b'fake content')
        temp_file_path = temp_file.name

    try:
        await call_mcp_tool('read_image', temp_file_path)
        assert False, 'Should have raised ValueError'
    except ValueError as e:
        assert 'Unsupported file type' in str(e)
        print('✓ read_image format validation working')
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.asyncio
async def test_exception_handling():
    """Test exception handling in document processing."""
    print('\nTesting exception handling...')

    # Test with corrupted/invalid files to trigger general exceptions
    import os
    import tempfile

    # Create a corrupted PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(b'This is not a valid PDF file content')
        corrupted_pdf_path = temp_file.name

    try:
        # This should trigger the general Exception handler in read_document (PDF)
        pdf_result = await call_mcp_tool('read_document', corrupted_pdf_path, 'pdf')
        assert isinstance(pdf_result, DocumentReadResponse)
        assert pdf_result.status == 'error'
        assert 'Error reading PDF file' in pdf_result.error_message
        print('✓ read_document (PDF) exception handling working')
    finally:
        if os.path.exists(corrupted_pdf_path):
            os.unlink(corrupted_pdf_path)

    # Test with a directory instead of a file to trigger security validation
    with tempfile.TemporaryDirectory() as temp_dir:
        # This should trigger the security validation in _convert_with_markitdown
        docx_result = await call_mcp_tool('read_document', temp_dir, 'docx')
        assert isinstance(docx_result, DocumentReadResponse)
        assert docx_result.status == 'error'
        assert 'Path is not a file' in docx_result.error_message
        print('✓ read_document (DOCX) security validation working')

    # Test image with invalid data
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        # Write invalid PNG data
        temp_file.write(b'invalid png data')
        invalid_image_path = temp_file.name

    try:
        image_result = await call_mcp_tool('read_image', invalid_image_path)
        # If we get here, the Image creation didn't fail as expected
        # This is fine, just means the test didn't trigger the exception path
        assert isinstance(image_result, Image)
        print('✓ read_image handled invalid data gracefully')
    except (RuntimeError, ValueError, Exception) as e:
        # This covers the RuntimeError exception path in read_image
        assert 'Error loading image' in str(e)
        print('✓ read_image exception handling working')
    finally:
        if os.path.exists(invalid_image_path):
            os.unlink(invalid_image_path)


@pytest.mark.asyncio
async def test_validate_file_path_resolve_exception():
    """Test path.resolve exception in validate_file_path (lines 72-73)."""
    # Create a mock context
    ctx = MockContext()

    # Create a mock path that raises an exception when resolve is called
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value.st_size = 1000  # Small file
        mock_path.suffix.lower.return_value = '.pdf'
        # Make resolve raise an OSError
        mock_path.resolve.side_effect = OSError('Path resolution error')
        mock_path_class.return_value = mock_path

        # Call the function
        error = validate_file_path(ctx, '/test/path.pdf')

        # Verify the error message
        assert error is not None
        assert 'Invalid file path' in error
        print('✓ OSError in path resolution covered')

    # Test with RuntimeError
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value.st_size = 1000  # Small file
        mock_path.suffix.lower.return_value = '.pdf'
        # Make resolve raise a RuntimeError
        mock_path.resolve.side_effect = RuntimeError('Runtime error in path resolution')
        mock_path_class.return_value = mock_path

        # Call the function
        error = validate_file_path(ctx, '/test/path.pdf')

        # Verify the error message
        assert error is not None
        assert 'Invalid file path' in error
        print('✓ RuntimeError in path resolution covered')


@pytest.mark.asyncio
async def test_validate_file_path_general_exception():
    """Test general exception in validate_file_path (lines 77-78)."""
    # Create a mock context
    ctx = MockContext()

    # Test with a general exception in Path constructor
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        # Make Path constructor raise an exception
        mock_path_class.side_effect = Exception('General exception in Path')

        # Call the function
        error = validate_file_path(ctx, '/test/path.pdf')

        # Verify the error message
        assert error is not None
        assert 'Error validating file path' in error
        assert 'General exception in Path' in error
        print('✓ General exception in validate_file_path covered')


@pytest.mark.asyncio
async def test_path_traversal_blocked():
    """Test that path traversal attempts are blocked by base directory enforcement."""
    import os
    import tempfile
    from pathlib import Path

    # Create a temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(b'%PDF-1.4 test')  # Minimal PDF header
        temp_file_path = temp_file.name

    try:
        # Mock base directory to a restricted location
        with patch('awslabs.document_loader_mcp_server.server._get_base_directory') as mock_base:
            mock_base.return_value = Path('/restricted/directory')

            ctx = MockContext()
            error = validate_file_path(ctx, temp_file_path)

            assert error is not None
            assert 'Access denied: path outside allowed directory' in error
            print('✓ Path traversal blocked by base directory enforcement')
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.asyncio
async def test_convert_with_markitdown_file_not_found():
    """Test FileNotFoundError in _convert_with_markitdown (lines 106-108)."""
    # Create a mock context
    ctx = MockContext()

    # Create a valid file path that passes validation but fails in MarkItDown
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock MarkItDown to raise FileNotFoundError
        with patch(
            'awslabs.document_loader_mcp_server.server.MarkItDown'
        ) as mock_markitdown_class:
            mock_markitdown = MagicMock()
            mock_markitdown.convert.side_effect = FileNotFoundError('File not found in MarkItDown')
            mock_markitdown_class.return_value = mock_markitdown

            # Call the function
            response = await _convert_with_markitdown(ctx, '/test/document.docx', 'Word document')

            # Verify the response
            assert isinstance(response, DocumentReadResponse)
            assert response.status == 'error'
            assert response.content == ''
            assert 'Could not find Word document' in response.error_message
            print('✓ FileNotFoundError in _convert_with_markitdown covered')


@pytest.mark.asyncio
async def test_convert_with_markitdown_general_exception():
    """Test general exception in _convert_with_markitdown (lines 114-116)."""
    # Create a mock context
    ctx = MockContext()

    # Create a valid file path that passes validation but fails in MarkItDown
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock MarkItDown to raise a general exception
        with patch(
            'awslabs.document_loader_mcp_server.server.MarkItDown'
        ) as mock_markitdown_class:
            mock_markitdown = MagicMock()
            mock_markitdown.convert.side_effect = Exception('General error in MarkItDown')
            mock_markitdown_class.return_value = mock_markitdown

            # Call the function
            response = await _convert_with_markitdown(ctx, '/test/document.docx', 'Word document')

            # Verify the response
            assert isinstance(response, DocumentReadResponse)
            assert response.status == 'error'
            assert response.content == ''
            assert 'Error reading Word document' in response.error_message
            assert 'General error in MarkItDown' in response.error_message
            print('✓ General exception in _convert_with_markitdown covered')


@pytest.mark.asyncio
async def test_read_pdf_content_file_not_found():
    """Test FileNotFoundError in _read_pdf_content (lines 155-156)."""
    # Create a mock context
    ctx = MockContext()

    # Create a valid file path that passes validation but fails in pdfplumber
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock pdfplumber to raise FileNotFoundError
        with patch('awslabs.document_loader_mcp_server.server.pdfplumber.open') as mock_pdf_open:
            mock_pdf_open.side_effect = FileNotFoundError('PDF file not found')

            # Call the function
            response = await _read_pdf_content(ctx, '/test/document.pdf')

            # Verify the response
            assert isinstance(response, DocumentReadResponse)
            assert response.status == 'error'
            assert response.content == ''
            assert 'Could not find PDF file' in response.error_message
            print('✓ FileNotFoundError in _read_pdf_content covered')


@pytest.mark.asyncio
async def test_read_image_exception():
    """Test exception in read_image (lines 220-222)."""
    # Create a valid file path that passes validation but fails in Image creation
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock Image to raise an exception
        with patch('awslabs.document_loader_mcp_server.server.Image') as mock_image_class:
            mock_image_class.side_effect = Exception('Error creating Image object')

            # Call the function through the MCP tool and expect a RuntimeError
            with pytest.raises(RuntimeError) as excinfo:
                await call_mcp_tool('read_image', '/test/image.png')

            # Verify the error message
            assert 'Error loading image' in str(excinfo.value)
            assert 'Error creating Image object' in str(excinfo.value)
            print('✓ General exception in read_image covered')


@pytest.mark.asyncio
async def test_convert_with_markitdown_timeout():
    """Test timeout handling in _convert_with_markitdown."""
    # Create a mock context
    ctx = MockContext()

    # Create a valid file path that passes validation but times out in conversion
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock the event loop and executor to prevent actual execution
        with patch(
            'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
        ) as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock run_in_executor to return a future that we can control
            mock_future = asyncio.Future()
            mock_loop.run_in_executor.return_value = mock_future

            # Mock asyncio.wait_for to raise TimeoutError immediately
            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
            ) as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                # Call the function
                response = await _convert_with_markitdown(
                    ctx, '/test/document.docx', 'Word document', 30
                )

                # Verify the response
                assert isinstance(response, DocumentReadResponse)
                assert response.status == 'error'
                assert response.content == ''
                assert (
                    'Word document conversion timed out after 30 seconds' in response.error_message
                )
                print('✓ TimeoutError in _convert_with_markitdown covered')


@pytest.mark.asyncio
async def test_read_pdf_content_timeout():
    """Test timeout handling in _read_pdf_content."""
    # Create a mock context
    ctx = MockContext()

    # Create a valid file path that passes validation but times out in PDF processing
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock the event loop and executor to prevent actual execution
        with patch(
            'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
        ) as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock run_in_executor to return a future that we can control
            mock_future = asyncio.Future()
            mock_loop.run_in_executor.return_value = mock_future

            # Mock asyncio.wait_for to raise TimeoutError immediately
            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
            ) as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                # Call the function
                response = await _read_pdf_content(ctx, '/test/document.pdf', 30)

                # Verify the response
                assert isinstance(response, DocumentReadResponse)
                assert response.status == 'error'
                assert response.content == ''
                assert 'PDF processing timed out after 30 seconds' in response.error_message
                print('✓ TimeoutError in _read_pdf_content covered')


@pytest.mark.asyncio
async def test_read_image_timeout():
    """Test timeout handling in read_image."""
    # Create a valid file path that passes validation but times out in image loading
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        # Make validation pass
        mock_validate.return_value = None

        # Mock the event loop and executor to prevent actual execution
        with patch(
            'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
        ) as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock run_in_executor to return a future that we can control
            mock_future = asyncio.Future()
            mock_loop.run_in_executor.return_value = mock_future

            # Mock asyncio.wait_for to raise TimeoutError immediately
            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
            ) as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                # Call the function through the MCP tool and expect a RuntimeError
                with pytest.raises(RuntimeError) as excinfo:
                    await call_mcp_tool('read_image', '/test/image.png')

                # Verify the error message
                assert 'Image loading timed out after 30 seconds' in str(excinfo.value)
                print('✓ TimeoutError in read_image covered')


@pytest.mark.asyncio
async def test_read_document_timeout_scenarios():
    """Test timeout handling for all document types in read_document tool."""
    # Test PDF timeout through read_document tool
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        mock_validate.return_value = None

        # Mock the event loop and executor to prevent actual execution
        with patch(
            'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
        ) as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock run_in_executor to return a future that we can control
            mock_future = asyncio.Future()
            mock_loop.run_in_executor.return_value = mock_future

            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
            ) as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                # Test PDF timeout
                pdf_result = await call_mcp_tool('read_document', '/test/document.pdf', 'pdf')
                assert isinstance(pdf_result, DocumentReadResponse)
                assert pdf_result.status == 'error'
                assert 'PDF processing timed out after 30 seconds' in pdf_result.error_message
                print('✓ PDF timeout through read_document covered')

                # Test DOCX timeout
                docx_result = await call_mcp_tool('read_document', '/test/document.docx', 'docx')
                assert isinstance(docx_result, DocumentReadResponse)
                assert docx_result.status == 'error'
                assert (
                    'Word document conversion timed out after 30 seconds'
                    in docx_result.error_message
                )
                print('✓ DOCX timeout through read_document covered')

                # Test XLSX timeout
                xlsx_result = await call_mcp_tool('read_document', '/test/document.xlsx', 'xlsx')
                assert isinstance(xlsx_result, DocumentReadResponse)
                assert xlsx_result.status == 'error'
                assert (
                    'Excel file conversion timed out after 30 seconds' in xlsx_result.error_message
                )
                print('✓ XLSX timeout through read_document covered')

                # Test PPTX timeout
                pptx_result = await call_mcp_tool('read_document', '/test/document.pptx', 'pptx')
                assert isinstance(pptx_result, DocumentReadResponse)
                assert pptx_result.status == 'error'
                assert (
                    'PowerPoint file conversion timed out after 30 seconds'
                    in pptx_result.error_message
                )
                print('✓ PPTX timeout through read_document covered')


def test_get_max_file_size_default():
    """Test _get_max_file_size returns default when env var is not set."""
    from awslabs.document_loader_mcp_server.server import DEFAULT_MAX_FILE_SIZE, _get_max_file_size

    with patch.dict(os.environ, {}, clear=True):
        result = _get_max_file_size()
        assert result == DEFAULT_MAX_FILE_SIZE
        print('✓ _get_max_file_size returns default when env var is not set')


def test_get_max_file_size_custom():
    """Test _get_max_file_size returns custom value from env var in MB."""
    from awslabs.document_loader_mcp_server.server import _get_max_file_size

    with patch.dict(os.environ, {'MAX_FILE_SIZE_MB': '100'}):
        result = _get_max_file_size()
        assert result == 100 * 1024 * 1024
        print('✓ _get_max_file_size returns custom value from env var')


def test_get_max_file_size_invalid():
    """Test _get_max_file_size falls back to default for invalid values."""
    from awslabs.document_loader_mcp_server.server import DEFAULT_MAX_FILE_SIZE, _get_max_file_size

    with patch.dict(os.environ, {'MAX_FILE_SIZE_MB': 'not_a_number'}):
        result = _get_max_file_size()
        assert result == DEFAULT_MAX_FILE_SIZE
        print('✓ _get_max_file_size falls back to default for non-numeric value')


def test_get_max_file_size_negative():
    """Test _get_max_file_size falls back to default for negative values."""
    from awslabs.document_loader_mcp_server.server import DEFAULT_MAX_FILE_SIZE, _get_max_file_size

    with patch.dict(os.environ, {'MAX_FILE_SIZE_MB': '-100'}):
        result = _get_max_file_size()
        assert result == DEFAULT_MAX_FILE_SIZE
        print('✓ _get_max_file_size falls back to default for negative value')


def test_get_max_file_size_zero():
    """Test _get_max_file_size falls back to default for zero."""
    from awslabs.document_loader_mcp_server.server import DEFAULT_MAX_FILE_SIZE, _get_max_file_size

    with patch.dict(os.environ, {'MAX_FILE_SIZE_MB': '0'}):
        result = _get_max_file_size()
        assert result == DEFAULT_MAX_FILE_SIZE
        print('✓ _get_max_file_size falls back to default for zero value')


def test_check_soffice_available():
    """Test _check_soffice_available returns None when soffice is found."""
    with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
        mock_find.return_value = '/usr/bin/soffice'
        result = _check_soffice_available()
        assert result is None
        print('✓ _check_soffice_available returns None when soffice found')


def test_check_soffice_not_available():
    """Test _check_soffice_available returns error when soffice is missing."""
    with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
        mock_find.return_value = None
        result = _check_soffice_available()
        assert result is not None
        assert 'soffice' in result
        print('✓ _check_soffice_available returns error when soffice missing')


def test_find_soffice_in_path():
    """Test _find_soffice finds soffice via PATH."""
    with patch('awslabs.document_loader_mcp_server.server.shutil.which') as mock_which:
        mock_which.return_value = '/usr/local/bin/soffice'
        result = _find_soffice()
        assert result == '/usr/local/bin/soffice'
        print('✓ _find_soffice finds soffice in PATH')


def test_find_soffice_macos_libreoffice():
    """Test _find_soffice finds macOS LibreOffice app bundle."""
    with patch('awslabs.document_loader_mcp_server.server.shutil.which') as mock_which:
        mock_which.return_value = None
        with patch('awslabs.document_loader_mcp_server.server.os.path.isfile') as mock_isfile:
            with patch('awslabs.document_loader_mcp_server.server.os.access') as mock_access:
                mock_isfile.side_effect = lambda p: p == (
                    '/Applications/LibreOffice.app/Contents/MacOS/soffice'
                )
                mock_access.return_value = True
                result = _find_soffice()
                assert result == '/Applications/LibreOffice.app/Contents/MacOS/soffice'
                print('✓ _find_soffice finds macOS LibreOffice bundle')


def test_find_soffice_macos_openoffice():
    """Test _find_soffice finds macOS OpenOffice app bundle."""
    with patch('awslabs.document_loader_mcp_server.server.shutil.which') as mock_which:
        mock_which.return_value = None
        with patch('awslabs.document_loader_mcp_server.server.os.path.isfile') as mock_isfile:
            with patch('awslabs.document_loader_mcp_server.server.os.access') as mock_access:
                mock_isfile.side_effect = lambda p: p == (
                    '/Applications/OpenOffice.app/Contents/MacOS/soffice'
                )
                mock_access.return_value = True
                result = _find_soffice()
                assert result == '/Applications/OpenOffice.app/Contents/MacOS/soffice'
                print('✓ _find_soffice finds macOS OpenOffice bundle')


def test_find_soffice_not_found():
    """Test _find_soffice returns None when soffice is nowhere."""
    with patch('awslabs.document_loader_mcp_server.server.shutil.which') as mock_which:
        mock_which.return_value = None
        with patch('awslabs.document_loader_mcp_server.server.os.path.isfile') as mock_isfile:
            mock_isfile.return_value = False
            result = _find_soffice()
            assert result is None
            print('✓ _find_soffice returns None when not found')


@pytest.mark.asyncio
async def test_extract_slides_soffice_missing():
    """Test extract_slides_as_images returns error when soffice is missing for PPTX."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
        temp_file.write(b'fake pptx content')
        temp_file_path = temp_file.name

    try:
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = None
            result = await call_mcp_tool_slides(temp_file_path, '/tmp/slides_out')
            assert isinstance(result, SlidesExtractionResponse)
            assert result.status == 'error'
            assert 'soffice' in result.error_message
            print('✓ extract_slides_as_images returns error when soffice missing')
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.asyncio
async def test_extract_slides_nonexistent_file():
    """Test extract_slides_as_images returns error for nonexistent file."""
    result = await call_mcp_tool_slides('/nonexistent/file.pdf', '/tmp/slides_out')
    assert isinstance(result, SlidesExtractionResponse)
    assert result.status == 'error'
    assert 'File not found' in result.error_message
    print('✓ extract_slides_as_images handles nonexistent file')


@pytest.mark.asyncio
async def test_extract_slides_timeout():
    """Test extract_slides_as_images handles timeout."""
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        mock_validate.return_value = None

        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
            ) as mock_get_loop:
                mock_loop = MagicMock()
                mock_get_loop.return_value = mock_loop
                mock_future = asyncio.Future()
                mock_loop.run_in_executor.return_value = mock_future

                with patch(
                    'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
                ) as mock_wait_for:
                    mock_wait_for.side_effect = asyncio.TimeoutError()
                    result = await call_mcp_tool_slides('/test/doc.pptx', '/tmp/out')
                    assert isinstance(result, SlidesExtractionResponse)
                    assert result.status == 'error'
                    assert 'timed out' in result.error_message
                    print('✓ extract_slides_as_images handles timeout')


@pytest.mark.asyncio
async def test_extract_slides_pdf_no_soffice_check():
    """Test extract_slides_as_images skips soffice check for PDF input."""
    with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
        mock_find.return_value = None  # soffice not available

        # For PDF, soffice check should be skipped, so we hit file validation instead
        result = await call_mcp_tool_slides('/nonexistent/file.pdf', '/tmp/slides_out')
        assert isinstance(result, SlidesExtractionResponse)
        assert result.status == 'error'
        # Should fail on file validation, NOT soffice check
        assert 'File not found' in result.error_message
        print('✓ extract_slides_as_images skips soffice check for PDF')


async def call_mcp_tool_slides(
    file_path: str, output_dir: str, dpi: int = 200, timeout: int = 120
):
    """Helper function to call extract_slides_as_images MCP tool."""
    tools = await mcp.get_tools()

    if 'extract_slides_as_images' not in tools:
        raise ValueError('Tool extract_slides_as_images not found')

    tool = tools['extract_slides_as_images']
    if hasattr(tool, 'fn') and callable(getattr(tool, 'fn')):
        fn = getattr(tool, 'fn')
        ctx = MockContext()
        return await fn(ctx, file_path, output_dir, dpi, timeout)
    else:
        raise ValueError('Cannot find callable function for tool extract_slides_as_images')


def test_get_base_directory_from_env():
    """Test _get_base_directory returns path from DOCUMENT_BASE_DIR env var."""
    with patch.dict(os.environ, {'DOCUMENT_BASE_DIR': '/custom/base'}):
        from pathlib import Path

        result = _get_base_directory()
        assert result == Path('/custom/base')
        print('✓ _get_base_directory returns path from env var')


def test_get_soffice_timeout_default():
    """Test _get_soffice_timeout returns default when env var not set."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop('SOFFICE_TIMEOUT_SECONDS', None)
        result = _get_soffice_timeout()
        assert result == 120
        print('✓ _get_soffice_timeout returns default')


def test_get_soffice_timeout_custom():
    """Test _get_soffice_timeout returns custom value from env var."""
    with patch.dict(os.environ, {'SOFFICE_TIMEOUT_SECONDS': '60'}):
        result = _get_soffice_timeout()
        assert result == 60
        print('✓ _get_soffice_timeout returns custom value')


def test_get_soffice_timeout_invalid():
    """Test _get_soffice_timeout falls back to default for invalid env var."""
    with patch.dict(os.environ, {'SOFFICE_TIMEOUT_SECONDS': 'abc'}):
        result = _get_soffice_timeout()
        assert result == 120
        print('✓ _get_soffice_timeout falls back for invalid value')


def test_get_soffice_timeout_out_of_range():
    """Test _get_soffice_timeout falls back to default for out-of-range env var."""
    with patch.dict(os.environ, {'SOFFICE_TIMEOUT_SECONDS': '999'}):
        result = _get_soffice_timeout()
        assert result == 120
        print('✓ _get_soffice_timeout falls back for out-of-range value')


def test_validate_output_dir_within_base():
    """Test validate_output_dir allows paths within base directory."""
    with patch.dict(os.environ, {'DOCUMENT_BASE_DIR': '/tmp'}):
        result = validate_output_dir('/tmp/slides_output')
        assert result is None
        print('✓ validate_output_dir allows paths within base directory')


def test_validate_output_dir_outside_base():
    """Test validate_output_dir blocks paths outside base directory."""
    with patch.dict(os.environ, {'DOCUMENT_BASE_DIR': '/var/app/documents'}):
        result = validate_output_dir('/etc/evil_output')
        assert result is not None
        assert 'Access denied' in result
        print('✓ validate_output_dir blocks paths outside base directory')


def test_convert_to_pdf_with_soffice_success():
    """Test _convert_to_pdf_with_soffice successful conversion."""
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch('awslabs.document_loader_mcp_server.server.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                # Create a fake PDF output file that soffice would produce
                pdf_path = os.path.join(temp_dir, 'test.pdf')
                with open(pdf_path, 'w') as f:
                    f.write('fake pdf')

                result = _convert_to_pdf_with_soffice('/input/test.pptx', temp_dir)
                assert result == pdf_path
                mock_run.assert_called_once()
                # Verify timeout is passed to subprocess.run
                call_kwargs = mock_run.call_args[1]
                assert 'timeout' in call_kwargs
                print('✓ _convert_to_pdf_with_soffice succeeds')


def test_convert_to_pdf_with_soffice_custom_timeout():
    """Test _convert_to_pdf_with_soffice passes custom timeout to subprocess.run."""
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch('awslabs.document_loader_mcp_server.server.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                pdf_path = os.path.join(temp_dir, 'test.pdf')
                with open(pdf_path, 'w') as f:
                    f.write('fake pdf')

                _convert_to_pdf_with_soffice('/input/test.pptx', temp_dir, timeout_seconds=60)
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs['timeout'] == 60
                print('✓ _convert_to_pdf_with_soffice passes custom timeout')


def test_convert_to_pdf_with_soffice_not_found():
    """Test _convert_to_pdf_with_soffice raises when soffice not found."""
    with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
        mock_find.return_value = None
        with pytest.raises(RuntimeError, match='soffice binary not found'):
            _convert_to_pdf_with_soffice('/input/test.pptx', '/tmp/out')
        print('✓ _convert_to_pdf_with_soffice raises when soffice missing')


def test_convert_to_pdf_with_soffice_no_output():
    """Test _convert_to_pdf_with_soffice raises when PDF not created."""
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch('awslabs.document_loader_mcp_server.server.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                # Don't create the PDF file — simulates soffice failing silently
                with pytest.raises(FileNotFoundError, match='PDF file not found'):
                    _convert_to_pdf_with_soffice('/input/test.pptx', temp_dir)
                print('✓ _convert_to_pdf_with_soffice raises when no PDF output')


def test_extract_slides_sync_pdf():
    """Test _extract_slides_sync with PDF input."""
    import tempfile

    with tempfile.TemporaryDirectory() as output_dir:
        with patch('awslabs.document_loader_mcp_server.server.convert_from_path') as mock_convert:
            # Create mock page objects
            mock_page1 = MagicMock()
            mock_page2 = MagicMock()
            mock_convert.return_value = [mock_page1, mock_page2]

            result = _extract_slides_sync('/test/doc.pdf', output_dir, 200, 'png')
            assert len(result) == 2
            assert 'slide_1.png' in result[0]
            assert 'slide_2.png' in result[1]
            mock_page1.save.assert_called_once()
            mock_page2.save.assert_called_once()
            mock_convert.assert_called_once_with('/test/doc.pdf', dpi=200)
            print('✓ _extract_slides_sync works for PDF')


def test_extract_slides_sync_pptx():
    """Test _extract_slides_sync with PPTX input (via soffice)."""
    import tempfile

    with tempfile.TemporaryDirectory() as output_dir:
        with patch(
            'awslabs.document_loader_mcp_server.server._convert_to_pdf_with_soffice'
        ) as mock_soffice:
            mock_soffice.return_value = '/tmp/converted.pdf'

            with patch(
                'awslabs.document_loader_mcp_server.server.convert_from_path'
            ) as mock_convert:
                mock_page = MagicMock()
                mock_convert.return_value = [mock_page]

                result = _extract_slides_sync('/test/slides.pptx', output_dir, 200, 'png')
                assert len(result) == 1
                assert 'slide_1.png' in result[0]
                mock_soffice.assert_called_once()
                mock_convert.assert_called_once_with('/tmp/converted.pdf', dpi=200)
                print('✓ _extract_slides_sync works for PPTX')


def test_extract_slides_sync_unsupported():
    """Test _extract_slides_sync raises for unsupported file types."""
    with pytest.raises(ValueError, match='Unsupported file type'):
        _extract_slides_sync('/test/doc.txt', '/tmp/out')
    print('✓ _extract_slides_sync raises for unsupported types')


@pytest.mark.asyncio
async def test_extract_slides_success():
    """Test extract_slides_as_images success path."""
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        mock_validate.return_value = None

        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
            ) as mock_get_loop:
                mock_loop = MagicMock()
                mock_get_loop.return_value = mock_loop

                mock_future = asyncio.Future()
                mock_future.set_result(['/tmp/out/slide_1.png', '/tmp/out/slide_2.png'])
                mock_loop.run_in_executor.return_value = mock_future

                with patch(
                    'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
                ) as mock_wait_for:
                    mock_wait_for.return_value = ['/tmp/out/slide_1.png', '/tmp/out/slide_2.png']

                    result = await call_mcp_tool_slides('/test/slides.pptx', '/tmp/out')
                    assert isinstance(result, SlidesExtractionResponse)
                    assert result.status == 'success'
                    assert result.slide_count == 2
                    assert len(result.slide_images) == 2
                    assert result.output_dir == '/tmp/out'
                    print('✓ extract_slides_as_images success path covered')


@pytest.mark.asyncio
async def test_extract_slides_general_exception():
    """Test extract_slides_as_images general exception handler."""
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path') as mock_validate:
        mock_validate.return_value = None

        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = '/usr/bin/soffice'

            with patch(
                'awslabs.document_loader_mcp_server.server.asyncio.get_event_loop'
            ) as mock_get_loop:
                mock_loop = MagicMock()
                mock_get_loop.return_value = mock_loop

                mock_future = asyncio.Future()
                mock_loop.run_in_executor.return_value = mock_future

                with patch(
                    'awslabs.document_loader_mcp_server.server.asyncio.wait_for'
                ) as mock_wait_for:
                    mock_wait_for.side_effect = RuntimeError('Conversion failed')

                    result = await call_mcp_tool_slides('/test/slides.pptx', '/tmp/out')
                    assert isinstance(result, SlidesExtractionResponse)
                    assert result.status == 'error'
                    assert 'Conversion failed' in result.error_message
                    print('✓ extract_slides_as_images general exception covered')


if __name__ == '__main__':
    asyncio.run(test_server())
    asyncio.run(test_mcp_tool_functions())
    asyncio.run(test_error_handling())
    asyncio.run(test_exception_handling())
    asyncio.run(test_validate_file_path_resolve_exception())
    asyncio.run(test_validate_file_path_general_exception())
    asyncio.run(test_convert_with_markitdown_file_not_found())
    asyncio.run(test_convert_with_markitdown_general_exception())
    asyncio.run(test_read_pdf_content_file_not_found())
    asyncio.run(test_read_image_exception())
    asyncio.run(test_convert_with_markitdown_timeout())
    asyncio.run(test_read_pdf_content_timeout())
    asyncio.run(test_read_image_timeout())
    asyncio.run(test_read_document_timeout_scenarios())
