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
"""Tests for inspect_document_assets and extract_document_assets MCP tools."""

import os
import pytest
import tempfile

# Import extractors and server validation functions at module level
from awslabs.document_loader_mcp_server.extractors import (
    ExtractionResponse,
    InspectionResponse,
    dispatch_extract,
    dispatch_inspect,
)
from awslabs.document_loader_mcp_server.server import (
    _check_soffice_available,
    _convert_to_pdf_with_soffice,
    validate_file_path,
    validate_output_dir,
)
from pathlib import Path
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from tests.test_document_parsing import MockContext
from unittest.mock import patch


# Helper functions that mimic the tool logic
async def _inspect_assets_helper(file_path: str, timeout_seconds: int = 30):
    """Helper to test inspect tool logic."""
    ctx = MockContext()
    suffix = Path(file_path).suffix.lower()

    # Check soffice for Office formats before file validation
    if suffix in {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'}:
        soffice_error = _check_soffice_available()
        if soffice_error:
            return InspectionResponse(
                status='error',
                asset_count=0,
                total_assets_found=0,
                error_message=soffice_error,
            )

    # Validate file path
    validation_error = validate_file_path(ctx, file_path)  # type: ignore[arg-type]
    if validation_error:
        return InspectionResponse(
            status='error',
            asset_count=0,
            total_assets_found=0,
            error_message=validation_error,
        )

    return await dispatch_inspect(
        file_path=file_path,
        timeout_seconds=timeout_seconds,
        convert_to_pdf_fn=_convert_to_pdf_with_soffice,
        check_soffice_fn=_check_soffice_available,
    )


async def _extract_assets_helper(
    file_path: str, output_dir: str, asset_indices=None, timeout_seconds: int = 60
):
    """Helper to test extract tool logic."""
    ctx = MockContext()
    suffix = Path(file_path).suffix.lower()

    if suffix in {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'}:
        soffice_error = _check_soffice_available()
        if soffice_error:
            return ExtractionResponse(
                status='error',
                output_dir='',
                error_message=soffice_error,
            )

    validation_error = validate_file_path(ctx, file_path)  # type: ignore[arg-type]
    if validation_error:
        return ExtractionResponse(
            status='error',
            output_dir='',
            error_message=validation_error,
        )

    output_dir_error = validate_output_dir(output_dir)
    if output_dir_error:
        return ExtractionResponse(
            status='error',
            output_dir='',
            error_message=output_dir_error,
        )

    return await dispatch_extract(
        file_path=file_path,
        output_dir=output_dir,
        asset_indices=asset_indices,
        timeout_seconds=timeout_seconds,
        convert_to_pdf_fn=_convert_to_pdf_with_soffice,
        check_soffice_fn=_check_soffice_available,
    )


@pytest.fixture
def pdf_with_images(tmp_path):
    """Generate a PDF with embedded images for tool testing."""
    pdf_path = tmp_path / 'tool_test.pdf'
    images = []
    for i, (size, color) in enumerate([(200, 150), (300, 200)]):
        img = PILImage.new('RGB', (size, color), color='red')
        img_path = tmp_path / f'img_{i}.png'
        img.save(str(img_path), format='PNG')
        images.append(str(img_path))
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph('Tool Test', styles['Title']), Spacer(1, 12)]
    for img_path in images:
        story.append(RLImage(img_path, width=100, height=80))
        story.append(Spacer(1, 6))
    doc.build(story)
    return str(pdf_path)


@pytest.mark.asyncio
async def test_server_registers_new_tools():
    """Test that new asset tools are registered in the MCP server."""
    print('Testing MCP server tool registration...')
    from awslabs.document_loader_mcp_server.server import mcp

    tools = await mcp.get_tools()
    # tools is a dict with tool names as keys or a list
    if isinstance(tools, dict):
        tool_names = list(tools.keys())
    else:
        tool_names = [t.name for t in tools]  # type: ignore[union-attr]
    assert 'inspect_document_assets' in tool_names
    assert 'extract_document_assets' in tool_names
    print(f'Found {len(tool_names)} tools, including asset tools')
    print('✓ Asset tool registration passed')


@pytest.mark.asyncio
async def test_inspect_tool_pdf(pdf_with_images):
    """Test inspecting assets from a PDF file."""
    print('Testing inspect_document_assets tool with PDF...')
    print(f'PDF path: {pdf_with_images}')
    result = await _inspect_assets_helper(pdf_with_images, timeout_seconds=30)
    assert result.status == 'success'
    assert result.asset_count > 0
    assert result.metadata is not None
    print(f'Found {result.asset_count} assets')
    print('✓ Inspect tool PDF test passed')


@pytest.mark.asyncio
async def test_extract_tool_pdf(pdf_with_images, tmp_path):
    """Test extracting assets from a PDF file."""
    print('Testing extract_document_assets tool with PDF...')
    output_dir = str(tmp_path / 'tool_output')
    print(f'Output directory: {output_dir}')
    result = await _extract_assets_helper(pdf_with_images, output_dir, timeout_seconds=30)
    assert result.status == 'success'
    assert result.extracted_count > 0
    print(f'Extracted {result.extracted_count} assets')
    for item in result.extracted:
        assert Path(item.output_path).exists()
        print(f'  Asset {item.index}: {item.output_path}')
    print('✓ Extract tool PDF test passed')


@pytest.mark.asyncio
async def test_inspect_tool_security_path_traversal(tmp_path):
    """Test that inspect tool blocks path traversal attempts."""
    print('Testing inspect tool security (path traversal)...')
    result = await _inspect_assets_helper('../../etc/passwd', timeout_seconds=10)
    assert result.status == 'error'
    assert result.error_message is not None
    print(f'Blocked with error: {result.error_message}')
    print('✓ Inspect tool path traversal security passed')


@pytest.mark.asyncio
async def test_extract_tool_security_output_dir(pdf_with_images):
    """Test that extract tool blocks invalid output directory."""
    print('Testing extract tool security (output directory)...')
    result = await _extract_assets_helper(
        pdf_with_images, output_dir='/etc/evil_output', timeout_seconds=10
    )
    assert result.status == 'error'
    assert result.error_message is not None
    print(f'Blocked with error: {result.error_message}')
    print('✓ Extract tool output directory security passed')


@pytest.mark.asyncio
async def test_inspect_tool_office_no_soffice():
    """Test that inspect tool returns error when soffice is not available for Office files."""
    print('Testing inspect tool with Office file when soffice unavailable...')
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        f.write(b'fake')
        fake_docx = f.name
    try:
        # Patch _find_soffice to return None, which will make _check_soffice_available return an error
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = None
            result = await _inspect_assets_helper(fake_docx, timeout_seconds=10)
            assert result.status == 'error'
            assert result.error_message is not None
            assert (
                'soffice' in result.error_message.lower() or 'LibreOffice' in result.error_message
            )
            print(f'Error message: {result.error_message}')
            print('✓ Inspect tool Office file without soffice passed')
    finally:
        os.unlink(fake_docx)


# ============================================================================
# NEW COVERAGE TESTS - Increasing extractors/__init__.py and server.py coverage
# ============================================================================


# Test 1: _get_max_assets() environment variable scenarios
@pytest.mark.asyncio
async def test_get_max_assets_custom_valid():
    """Test _get_max_assets with valid custom MAX_ASSETS environment variable."""
    from awslabs.document_loader_mcp_server.extractors import _get_max_assets

    print('Testing _get_max_assets with custom valid value (MAX_ASSETS=5)...')
    with patch.dict(os.environ, {'MAX_ASSETS': '5'}):
        result = _get_max_assets()
        assert result == 5
        print(f'✓ Returned custom value: {result}')


@pytest.mark.asyncio
async def test_get_max_assets_invalid_string():
    """Test _get_max_assets with invalid string (non-integer)."""
    from awslabs.document_loader_mcp_server.extractors import (
        DEFAULT_MAX_ASSETS,
        _get_max_assets,
    )

    print('Testing _get_max_assets with invalid string (MAX_ASSETS=abc)...')
    with patch.dict(os.environ, {'MAX_ASSETS': 'abc'}):
        result = _get_max_assets()
        assert result == DEFAULT_MAX_ASSETS
        print(f'✓ Returned default value: {result}')


@pytest.mark.asyncio
async def test_get_max_assets_zero():
    """Test _get_max_assets with zero value."""
    from awslabs.document_loader_mcp_server.extractors import (
        DEFAULT_MAX_ASSETS,
        _get_max_assets,
    )

    print('Testing _get_max_assets with zero (MAX_ASSETS=0)...')
    with patch.dict(os.environ, {'MAX_ASSETS': '0'}):
        result = _get_max_assets()
        assert result == DEFAULT_MAX_ASSETS
        print(f'✓ Returned default value: {result}')


@pytest.mark.asyncio
async def test_get_max_assets_negative():
    """Test _get_max_assets with negative value."""
    from awslabs.document_loader_mcp_server.extractors import (
        DEFAULT_MAX_ASSETS,
        _get_max_assets,
    )

    print('Testing _get_max_assets with negative (MAX_ASSETS=-1)...')
    with patch.dict(os.environ, {'MAX_ASSETS': '-1'}):
        result = _get_max_assets()
        assert result == DEFAULT_MAX_ASSETS
        print(f'✓ Returned default value: {result}')


# Test 2: dispatch_inspect with Office formats - error paths
@pytest.mark.asyncio
async def test_dispatch_inspect_office_soffice_error():
    """Test dispatch_inspect with Office file when soffice check returns error."""
    print('Testing dispatch_inspect with Office file when soffice check fails...')
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        f.write(b'PK\x03\x04')  # Minimal ZIP header for .docx
        fake_docx = f.name

    try:
        # Mock check_soffice_fn to return an error message
        def mock_check_soffice():
            return 'soffice not found in PATH'

        result = await dispatch_inspect(
            file_path=fake_docx,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=None,
        )
        assert result.status == 'error'
        assert 'soffice not found' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_docx)


@pytest.mark.asyncio
async def test_dispatch_inspect_office_no_converter():
    """Test dispatch_inspect with Office file when converter is None."""
    print('Testing dispatch_inspect with Office file when no converter provided...')
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
        f.write(b'PK\x03\x04')
        fake_pptx = f.name

    try:
        # Mock check_soffice_fn to return None (success), but pass no converter
        def mock_check_soffice():
            return None

        result = await dispatch_inspect(
            file_path=fake_pptx,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=None,
        )
        assert result.status == 'error'
        assert 'not available' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_pptx)


@pytest.mark.asyncio
async def test_dispatch_inspect_office_conversion_success(pdf_with_images):
    """Test dispatch_inspect with Office file and successful conversion."""
    print('Testing dispatch_inspect with Office file and successful conversion...')
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        f.write(b'PK\x03\x04')
        fake_xlsx = f.name

    try:

        def mock_check_soffice():
            return None

        # Mock converter returns a real PDF path
        def mock_convert(file_path, temp_dir, timeout):
            return pdf_with_images

        result = await dispatch_inspect(
            file_path=fake_xlsx,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=mock_convert,
        )
        assert result.status == 'success'
        assert result.asset_count > 0
        # Verify metadata reflects original file
        assert result.metadata.file_path == fake_xlsx
        assert result.metadata.file_type == 'xlsx'
        print(f'✓ Successfully inspected with {result.asset_count} assets')
    finally:
        os.unlink(fake_xlsx)


@pytest.mark.asyncio
async def test_dispatch_inspect_office_conversion_exception():
    """Test dispatch_inspect with Office file when conversion raises exception."""
    print('Testing dispatch_inspect with Office file when conversion raises exception...')
    with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as f:
        f.write(b'\xd0\xcf\x11\xe0')  # Minimal OLE header
        fake_doc = f.name

    try:

        def mock_check_soffice():
            return None

        def mock_convert(file_path, temp_dir, timeout):
            raise RuntimeError('Conversion failed: LibreOffice crashed')

        result = await dispatch_inspect(
            file_path=fake_doc,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=mock_convert,
        )
        assert result.status == 'error'
        assert 'Error converting' in result.error_message
        assert 'LibreOffice crashed' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_doc)


# Test 3: dispatch_extract with Office formats - error paths
@pytest.mark.asyncio
async def test_dispatch_extract_office_soffice_error(tmp_path):
    """Test dispatch_extract with Office file when soffice check returns error."""
    print('Testing dispatch_extract with Office file when soffice check fails...')
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        f.write(b'PK\x03\x04')
        fake_docx = f.name

    output_dir = str(tmp_path / 'output')

    try:

        def mock_check_soffice():
            return 'LibreOffice not available'

        result = await dispatch_extract(
            file_path=fake_docx,
            output_dir=output_dir,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=None,
        )
        assert result.status == 'error'
        assert 'LibreOffice not available' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_docx)


@pytest.mark.asyncio
async def test_dispatch_extract_office_no_converter(tmp_path):
    """Test dispatch_extract with Office file when converter is None."""
    print('Testing dispatch_extract with Office file when no converter provided...')
    with tempfile.NamedTemporaryFile(suffix='.ppt', delete=False) as f:
        f.write(b'\xd0\xcf\x11\xe0')
        fake_ppt = f.name

    output_dir = str(tmp_path / 'output')

    try:

        def mock_check_soffice():
            return None

        result = await dispatch_extract(
            file_path=fake_ppt,
            output_dir=output_dir,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=None,
        )
        assert result.status == 'error'
        assert 'not available' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_ppt)


@pytest.mark.asyncio
async def test_dispatch_extract_office_conversion_success(pdf_with_images, tmp_path):
    """Test dispatch_extract with Office file and successful conversion."""
    print('Testing dispatch_extract with Office file and successful conversion...')
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
        f.write(b'PK\x03\x04')
        fake_docx = f.name

    output_dir = str(tmp_path / 'extract_output')

    try:

        def mock_check_soffice():
            return None

        def mock_convert(file_path, temp_dir, timeout):
            return pdf_with_images

        result = await dispatch_extract(
            file_path=fake_docx,
            output_dir=output_dir,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=mock_convert,
        )
        assert result.status == 'success'
        assert result.extracted_count > 0
        print(f'✓ Successfully extracted {result.extracted_count} assets')
    finally:
        os.unlink(fake_docx)


@pytest.mark.asyncio
async def test_dispatch_extract_office_conversion_exception(tmp_path):
    """Test dispatch_extract with Office file when conversion raises exception."""
    print('Testing dispatch_extract with Office file when conversion raises exception...')
    with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as f:
        f.write(b'\xd0\xcf\x11\xe0')
        fake_xls = f.name

    output_dir = str(tmp_path / 'output')

    try:

        def mock_check_soffice():
            return None

        def mock_convert(file_path, temp_dir, timeout):
            raise RuntimeError('soffice process timeout')

        result = await dispatch_extract(
            file_path=fake_xls,
            output_dir=output_dir,
            timeout_seconds=10,
            check_soffice_fn=mock_check_soffice,
            convert_to_pdf_fn=mock_convert,
        )
        assert result.status == 'error'
        assert 'Error converting' in result.error_message
        assert 'timeout' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_xls)


@pytest.mark.asyncio
async def test_dispatch_extract_unsupported_file_type(tmp_path):
    """Test dispatch_extract with unsupported file type (.txt)."""
    print('Testing dispatch_extract with unsupported file type (.txt)...')
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'Hello world')
        fake_txt = f.name

    output_dir = str(tmp_path / 'output')

    try:
        result = await dispatch_extract(
            file_path=fake_txt, output_dir=output_dir, timeout_seconds=10
        )
        assert result.status == 'error'
        assert 'Unsupported' in result.error_message
        print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_txt)


# Test 4: extract_tool handler with Office file and invalid paths
@pytest.mark.asyncio
async def test_extract_tool_office_no_soffice():
    """Test extract tool with Office file when soffice is unavailable."""
    print('Testing extract tool with Office file when soffice unavailable...')
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as f:
        f.write(b'PK\x03\x04')
        fake_pptx = f.name

    try:
        with patch('awslabs.document_loader_mcp_server.server._find_soffice') as mock_find:
            mock_find.return_value = None
            result = await _extract_assets_helper(
                fake_pptx, output_dir='/tmp/test_output', timeout_seconds=10
            )
            assert result.status == 'error'
            assert result.error_message is not None
            assert (
                'soffice' in result.error_message.lower() or 'LibreOffice' in result.error_message
            )
            print(f'✓ Error message: {result.error_message}')
    finally:
        os.unlink(fake_pptx)


@pytest.mark.asyncio
async def test_extract_tool_invalid_file_path():
    """Test extract tool with invalid file path."""
    print('Testing extract tool with invalid file path...')
    result = await _extract_assets_helper(
        file_path='/nonexistent/path/file.pdf', output_dir='/tmp/output', timeout_seconds=10
    )
    assert result.status == 'error'
    assert result.error_message is not None
    print(f'✓ Error message: {result.error_message}')


@pytest.mark.asyncio
async def test_inspect_tool_invalid_file_path():
    """Test inspect tool with invalid file path (non-existent)."""
    print('Testing inspect tool with non-existent file path...')
    result = await _inspect_assets_helper(
        file_path='/tmp/does_not_exist_12345.pdf', timeout_seconds=10
    )
    assert result.status == 'error'
    assert result.error_message is not None
    print(f'✓ Error message: {result.error_message}')


print('\n✓ All new coverage tests added successfully')
