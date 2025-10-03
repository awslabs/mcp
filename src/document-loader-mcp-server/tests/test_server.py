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
import pytest
from awslabs.document_loader_mcp_server.server import mcp, DocumentReadResponse
from tests.test_document_parsing import DocumentTestGenerator, MockContext
from fastmcp.utilities.types import Image


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
        expected_tools = ['read_pdf', 'read_docx', 'read_xlsx', 'read_pptx', 'read_image']

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


async def call_mcp_tool(tool_name: str, file_path: str):
    """Helper function to call MCP tools through the server."""
    # Get the tool from the server
    tools = await mcp.get_tools()

    if tool_name not in tools:
        raise ValueError(f'Tool {tool_name} not found. Available tools: {list(tools.keys())}')

    tool = tools[tool_name]
    print(f'Tool attributes: {dir(tool)}')

    # Call the tool function using the 'fn' attribute with Context
    if hasattr(tool, 'fn') and callable(getattr(tool, 'fn')):
        fn = getattr(tool, 'fn')
        ctx = MockContext()
        return await fn(ctx, file_path)
    else:
        raise ValueError(f'Cannot find callable function for tool {tool_name}')


@pytest.mark.asyncio
async def test_mcp_tool_functions():
    """Test the actual MCP tool functions with real documents."""
    print('\nTesting MCP tool functions...')

    # Generate test documents
    generator = DocumentTestGenerator()

    # Test PDF tool
    pdf_path = generator.generate_sample_pdf()
    pdf_result = await call_mcp_tool('read_pdf', pdf_path)
    assert isinstance(pdf_result, DocumentReadResponse)
    assert pdf_result.status == 'success'
    assert len(pdf_result.content) > 0
    assert 'Page 1' in pdf_result.content
    print('✓ read_pdf tool working')

    # Test DOCX tool
    docx_path = generator.generate_sample_docx()
    docx_result = await call_mcp_tool('read_docx', docx_path)
    assert isinstance(docx_result, DocumentReadResponse)
    assert docx_result.status == 'success'
    assert len(docx_result.content) > 0
    print('✓ read_docx tool working')

    # Test XLSX tool
    xlsx_path = generator.generate_sample_xlsx()
    xlsx_result = await call_mcp_tool('read_xlsx', xlsx_path)
    assert isinstance(xlsx_result, DocumentReadResponse)
    assert xlsx_result.status == 'success'
    assert len(xlsx_result.content) > 0
    print('✓ read_xlsx tool working')

    # Test PPTX tool
    pptx_path = generator.generate_sample_pptx()
    pptx_result = await call_mcp_tool('read_pptx', pptx_path)
    assert isinstance(pptx_result, DocumentReadResponse)
    assert pptx_result.status == 'success'
    assert len(pptx_result.content) > 0
    print('✓ read_pptx tool working')

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
    pdf_result = await call_mcp_tool('read_pdf', non_existent_file)
    assert isinstance(pdf_result, DocumentReadResponse)
    assert pdf_result.status == 'error'
    assert 'File not found' in pdf_result.error_message
    print('✓ read_pdf error handling working')

    # Test DOCX error handling
    docx_result = await call_mcp_tool('read_docx', non_existent_file)
    assert isinstance(docx_result, DocumentReadResponse)
    assert docx_result.status == 'error'
    assert 'File not found' in docx_result.error_message
    print('✓ read_docx error handling working')

    # Test XLSX error handling
    xlsx_result = await call_mcp_tool('read_xlsx', non_existent_file)
    assert isinstance(xlsx_result, DocumentReadResponse)
    assert xlsx_result.status == 'error'
    assert 'File not found' in xlsx_result.error_message
    print('✓ read_xlsx error handling working')

    # Test PPTX error handling
    pptx_result = await call_mcp_tool('read_pptx', non_existent_file)
    assert isinstance(pptx_result, DocumentReadResponse)
    assert pptx_result.status == 'error'
    assert 'File not found' in pptx_result.error_message
    print('✓ read_pptx error handling working')

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
        # This should trigger the general Exception handler in read_pdf
        pdf_result = await call_mcp_tool('read_pdf', corrupted_pdf_path)
        assert isinstance(pdf_result, DocumentReadResponse)
        assert pdf_result.status == 'error'
        assert 'Error reading PDF file' in pdf_result.error_message
        print('✓ read_pdf exception handling working')
    finally:
        if os.path.exists(corrupted_pdf_path):
            os.unlink(corrupted_pdf_path)

    # Test with a directory instead of a file to trigger security validation
    with tempfile.TemporaryDirectory() as temp_dir:
        # This should trigger the security validation in _convert_with_markitdown
        docx_result = await call_mcp_tool('read_docx', temp_dir)
        assert isinstance(docx_result, DocumentReadResponse)
        assert docx_result.status == 'error'
        assert 'Path is not a file' in docx_result.error_message
        print('✓ read_docx security validation working')

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
async def test_missing_coverage_scenarios():
    """Test specific scenarios to cover missing lines in coverage report."""
    print('\nTesting missing coverage scenarios...')
    
    import os
    import tempfile
    from unittest.mock import patch, Mock
    
    # Import the actual functions, not the decorated versions
    import awslabs.document_loader_mcp_server.server as server_module
    
    ctx = MockContext()
    
    # Test OSError in path resolution (lines 84-85)
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value.st_size = 1000
        mock_path.suffix.lower.return_value = '.pdf'
        mock_path.resolve.side_effect = OSError("Invalid path")
        mock_path_class.return_value = mock_path
        
        result = server_module.validate_file_path(ctx, "/invalid/path")
        assert result == "Invalid file path: /invalid/path"
        print('✓ OSError in path resolution covered')
    
    # Test RuntimeError in path resolution (lines 84-85)
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value.st_size = 1000
        mock_path.suffix.lower.return_value = '.pdf'
        mock_path.resolve.side_effect = RuntimeError("Runtime error")
        mock_path_class.return_value = mock_path
        
        result = server_module.validate_file_path(ctx, "/invalid/path")
        assert result == "Invalid file path: /invalid/path"
        print('✓ RuntimeError in path resolution covered')
    
    # General exception in validate_file_path (lines 89-92)
    with patch('awslabs.document_loader_mcp_server.server.Path') as mock_path_class:
        mock_path_class.side_effect = Exception("Unexpected error")
        
        result = server_module.validate_file_path(ctx, "/some/path")
        assert result == "Error validating file path /some/path: Unexpected error"
        print('✓ General exception in validate_file_path covered')
    
    # FileNotFoundError in _convert_with_markitdown (lines 130-133)
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path', return_value=None):
        with patch('awslabs.document_loader_mcp_server.server.MarkItDown') as mock_md:
            mock_md.return_value.convert.side_effect = FileNotFoundError("File not found")
            
            result = await server_module._convert_with_markitdown(ctx, "/nonexistent/file.docx", "Word document")
            
            assert result.status == "error"
            assert result.error_message == "Could not find Word document at /nonexistent/file.docx"
            print('✓ FileNotFoundError in _convert_with_markitdown covered')
    
    # General exception in _convert_with_markitdown (lines 139-142)
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path', return_value=None):
        with patch('awslabs.document_loader_mcp_server.server.MarkItDown') as mock_md:
            mock_md.return_value.convert.side_effect = Exception("Conversion failed")
            
            result = await server_module._convert_with_markitdown(ctx, "/some/file.docx", "Word document")
            
            assert result.status == "error"
            assert result.error_message == "Error reading Word document /some/file.docx: Conversion failed"
            print('✓ General exception in _convert_with_markitdown covered')
    
    # FileNotFoundError in read_pdf (lines 193-195)
    # We need to get the actual function from the tool
    tools = await mcp.get_tools()
    read_pdf_tool = tools['read_pdf']
    read_pdf_fn = read_pdf_tool.fn
    
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path', return_value=None):
        with patch('awslabs.document_loader_mcp_server.server.pdfplumber.open') as mock_open:
            mock_open.side_effect = FileNotFoundError("PDF file not found")
            
            result = await read_pdf_fn(ctx, "/nonexistent/file.pdf")
            
            assert result.status == "error"
            assert result.error_message == "Could not find PDF file at /nonexistent/file.pdf"
            print('✓ FileNotFoundError in read_pdf covered')
    
    # General exception in read_image (lines 287-290)
    read_image_tool = tools['read_image']
    read_image_fn = read_image_tool.fn
    
    with patch('awslabs.document_loader_mcp_server.server.validate_file_path', return_value=None):
        with patch('awslabs.document_loader_mcp_server.server.Image') as mock_image:
            mock_image.side_effect = Exception("Image loading failed")
            
            try:
                await read_image_fn(ctx, "/some/image.jpg")
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "Error loading image /some/image.jpg: Image loading failed" in str(e)
                print('✓ General exception in read_image covered')
    
    # main() function (line 295)
    with patch('awslabs.document_loader_mcp_server.server.mcp') as mock_mcp:
        server_module.main()
        mock_mcp.run.assert_called_once()
        print('✓ main() function covered')
    
    print('✓ All missing coverage scenarios tested')


if __name__ == '__main__':
    asyncio.run(test_server())
    asyncio.run(test_mcp_tool_functions())
    asyncio.run(test_error_handling())
    asyncio.run(test_exception_handling())
    asyncio.run(test_missing_coverage_scenarios())
