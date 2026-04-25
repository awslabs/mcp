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
"""Tests for asset extraction data models and functionality."""

import asyncio
import io
import os
import pytest
from awslabs.document_loader_mcp_server.extractors import (
    ASSET_EXTRACTION_EXTENSIONS,
    AssetInfo,
    DocumentMetadata,
    ExtractedAsset,
    ExtractionResponse,
    InspectionResponse,
    dispatch_extract,
    dispatch_inspect,
)
from awslabs.document_loader_mcp_server.extractors.pdf import (
    _get_image_bytes,
    _get_image_format,
    _get_stream_color_mode,
    _get_stream_dimensions,
    _introspect_image,
    _is_raw_pixel_data,
    _resolve_filter_name,
    _save_image_bytes,
    extract_pdf,
    inspect_pdf,
)
from pathlib import Path
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from unittest.mock import MagicMock, patch


@pytest.fixture
def pdf_with_images(tmp_path):
    """Generate a PDF with 3 embedded images for testing."""
    pdf_path = tmp_path / 'test_with_images.pdf'
    images = []
    for i, (size, color, fmt) in enumerate(
        [
            ((200, 150), 'red', 'PNG'),
            ((300, 200), 'blue', 'JPEG'),
            ((100, 100), 'green', 'PNG'),
        ]
    ):
        img = PILImage.new('RGB', size, color=color)
        img_path = tmp_path / f'test_img_{i}.{"jpg" if fmt == "JPEG" else "png"}'
        img.save(str(img_path), format=fmt)
        images.append(str(img_path))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph('Test PDF with Embedded Images', styles['Title']))
    story.append(Spacer(1, 12))
    for img_path in images:
        story.append(RLImage(img_path, width=150, height=100))
        story.append(Spacer(1, 12))
    story.append(PageBreak())
    story.append(Paragraph('Page 2', styles['Heading1']))
    story.append(RLImage(images[0], width=150, height=100))
    doc.build(story)
    return str(pdf_path)


@pytest.fixture
def pdf_without_images(tmp_path):
    """Generate a text-only PDF with no embedded images."""
    pdf_path = tmp_path / 'text_only.pdf'
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph('Text Only Document', styles['Title']),
        Spacer(1, 12),
        Paragraph('This document has no images.', styles['Normal']),
    ]
    doc.build(story)
    return str(pdf_path)


def test_asset_info_creation():
    """Test creating AssetInfo with all fields."""
    print('Testing AssetInfo creation with all fields...')
    asset = AssetInfo(
        index=0,
        name='image_001.jpg',
        format='jpeg',
        size_bytes=12345,
        width_px=800,
        height_px=600,
        dpi=(72, 72),
        color_space='RGB',
        compression='DCTDecode',
        location='Page 3',
    )
    assert asset.index == 0
    assert asset.name == 'image_001.jpg'
    assert asset.format == 'jpeg'
    assert asset.size_bytes == 12345
    assert asset.width_px == 800
    assert asset.height_px == 600
    assert asset.dpi == (72, 72)
    assert asset.color_space == 'RGB'
    assert asset.compression == 'DCTDecode'
    assert asset.location == 'Page 3'
    print('✓ AssetInfo creation with all fields passed')


def test_asset_info_optional_fields():
    """Test creating AssetInfo with only required fields."""
    print('Testing AssetInfo creation with only required fields...')
    asset = AssetInfo(
        index=1, name='image_002.png', format='png', size_bytes=54321, location='Page 1'
    )
    assert asset.index == 1
    assert asset.name == 'image_002.png'
    assert asset.format == 'png'
    assert asset.size_bytes == 54321
    assert asset.location == 'Page 1'
    assert asset.width_px is None
    assert asset.height_px is None
    assert asset.dpi is None
    assert asset.color_space is None
    assert asset.compression is None
    print('✓ AssetInfo creation with optional fields passed')


def test_document_metadata_creation():
    """Test creating DocumentMetadata with all fields."""
    print('Testing DocumentMetadata creation...')
    metadata = DocumentMetadata(
        file_path='/path/to/doc.pdf',
        file_type='pdf',
        file_size_bytes=1024000,
        title='Test Document',
        author='John Doe',
        created='2024-01-01T00:00:00Z',
        modified='2024-01-02T00:00:00Z',
        page_count=10,
    )
    assert metadata.file_path == '/path/to/doc.pdf'
    assert metadata.file_type == 'pdf'
    assert metadata.file_size_bytes == 1024000
    assert metadata.title == 'Test Document'
    assert metadata.author == 'John Doe'
    assert metadata.created == '2024-01-01T00:00:00Z'
    assert metadata.modified == '2024-01-02T00:00:00Z'
    assert metadata.page_count == 10
    print('✓ DocumentMetadata creation passed')


def test_inspection_response_success():
    """Test InspectionResponse with success status and empty assets."""
    print('Testing InspectionResponse with success status...')
    response = InspectionResponse(status='success', asset_count=0, total_assets_found=0)
    assert response.status == 'success'
    assert response.metadata is None
    assert response.assets == []
    assert response.asset_count == 0
    assert response.total_assets_found == 0
    assert response.warnings == []
    assert response.error_message is None
    print('✓ InspectionResponse success status passed')


def test_inspection_response_partial():
    """Test InspectionResponse with partial status where total_assets_found > asset_count."""
    print('Testing InspectionResponse with partial status...')
    response = InspectionResponse(
        status='partial',
        asset_count=2,
        total_assets_found=5,
        warnings=['3 assets failed inspection'],
    )
    assert response.status == 'partial'
    assert response.asset_count == 2
    assert response.total_assets_found == 5
    assert len(response.warnings) == 1
    assert response.warnings[0] == '3 assets failed inspection'
    print('✓ InspectionResponse partial status passed')


def test_extraction_response():
    """Test ExtractionResponse with one successful ExtractedAsset."""
    print('Testing ExtractionResponse with successful extraction...')
    extracted = ExtractedAsset(index=0, output_path='/out/image_001.png', status='success')
    response = ExtractionResponse(
        status='success',
        extracted=[extracted],
        extracted_count=1,
        failed_count=0,
        output_dir='/out',
    )
    assert response.status == 'success'
    assert len(response.extracted) == 1
    assert response.extracted[0].index == 0
    assert response.extracted[0].output_path == '/out/image_001.png'
    assert response.extracted[0].status == 'success'
    assert response.extracted_count == 1
    assert response.failed_count == 0
    assert response.output_dir == '/out'
    assert response.warnings == []
    assert response.error_message is None
    print('✓ ExtractionResponse success passed')


def test_extracted_asset_error():
    """Test ExtractedAsset with error status."""
    print('Testing ExtractedAsset with error status...')
    asset = ExtractedAsset(
        index=2,
        output_path='',
        status='error',
        error_message='Failed to decode image data',
    )
    assert asset.index == 2
    assert asset.output_path == ''
    assert asset.status == 'error'
    assert asset.error_message == 'Failed to decode image data'
    print('✓ ExtractedAsset error status passed')


@pytest.mark.asyncio
async def test_inspect_pdf_with_images(pdf_with_images):
    """Test inspecting PDF with embedded images."""
    print('Testing PDF inspection with embedded images...')
    print(f'PDF path: {pdf_with_images}')
    result = await inspect_pdf(pdf_with_images)
    assert result.status == 'success'
    assert result.metadata is not None
    assert result.metadata.file_type == 'pdf'
    assert result.metadata.page_count is not None
    assert result.metadata.page_count >= 2
    assert result.asset_count > 0
    assert result.total_assets_found > 0
    assert len(result.assets) == result.asset_count
    print(f'Found {result.asset_count} assets')
    for asset in result.assets:
        assert asset.index >= 0
        assert asset.name
        assert asset.format in ('jpeg', 'png', 'tiff', 'jp2')
        assert asset.size_bytes > 0
        assert asset.location.startswith('Page ')
        print(f'  Asset {asset.index}: {asset.name} ({asset.format}, {asset.size_bytes} bytes)')
    print('✓ PDF inspection with images passed')


@pytest.mark.asyncio
async def test_inspect_pdf_without_images(pdf_without_images):
    """Test inspecting PDF without embedded images."""
    print('Testing PDF inspection without images...')
    print(f'PDF path: {pdf_without_images}')
    result = await inspect_pdf(pdf_without_images)
    assert result.status == 'success'
    assert result.metadata is not None
    assert result.metadata.page_count is not None
    assert result.metadata.page_count >= 1
    assert result.asset_count == 0
    assert result.total_assets_found == 0
    assert result.assets == []
    print('No assets found (as expected)')
    print('✓ PDF inspection without images passed')


@pytest.mark.asyncio
async def test_inspect_pdf_metadata(pdf_with_images):
    """Test that PDF metadata extraction works correctly."""
    print('Testing PDF metadata extraction...')
    result = await inspect_pdf(pdf_with_images)
    assert result.metadata is not None
    assert result.metadata.file_path == pdf_with_images
    assert result.metadata.file_size_bytes > 0
    assert result.metadata.page_count is not None
    print(f'Metadata: {result.metadata.file_size_bytes} bytes, {result.metadata.page_count} pages')
    print('✓ PDF metadata extraction passed')


@pytest.mark.asyncio
async def test_inspect_pdf_nonexistent():
    """Test that nonexistent PDF files return error status."""
    print('Testing PDF inspection with nonexistent file...')
    result = await inspect_pdf('/tmp/nonexistent_file.pdf')
    assert result.status == 'error'
    assert result.error_message is not None
    assert result.asset_count == 0
    print(f'Error message: {result.error_message}')
    print('✓ Nonexistent file handling passed')


@pytest.mark.asyncio
async def test_extract_pdf_all_assets(pdf_with_images, tmp_path):
    """Test extracting all assets from PDF with images."""
    print('Testing PDF asset extraction (all assets)...')
    output_dir = str(tmp_path / 'extracted')
    print(f'Output directory: {output_dir}')
    result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'success'
    assert result.extracted_count > 0
    assert result.failed_count == 0
    assert result.output_dir == output_dir
    print(f'Extracted {result.extracted_count} assets')
    for item in result.extracted:
        assert item.status == 'success'
        assert Path(item.output_path).exists()
        assert Path(item.output_path).stat().st_size > 0
        print(f'  Extracted asset {item.index}: {item.output_path}')
    print('✓ PDF asset extraction (all) passed')


@pytest.mark.asyncio
async def test_extract_pdf_selective(pdf_with_images, tmp_path):
    """Test selective extraction of specific asset indices."""
    print('Testing PDF asset extraction (selective)...')
    output_dir = str(tmp_path / 'selective')
    inspection = await inspect_pdf(pdf_with_images)
    assert inspection.asset_count > 0
    print(f'Extracting asset 0 only (out of {inspection.asset_count} total)')
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[0])
    assert result.status == 'success'
    assert result.extracted_count == 1
    assert len(result.extracted) == 1
    assert result.extracted[0].index == 0
    print(f'Extracted asset 0: {result.extracted[0].output_path}')
    print('✓ PDF asset extraction (selective) passed')


@pytest.mark.asyncio
async def test_extract_pdf_invalid_index(pdf_with_images, tmp_path):
    """Test handling of invalid asset index."""
    print('Testing PDF asset extraction with invalid index...')
    output_dir = str(tmp_path / 'invalid')
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[999])
    assert result.status == 'error'
    assert result.failed_count == 1
    assert result.extracted[0].status == 'error'
    assert result.extracted[0].error_message is not None
    print(f'Error message: {result.extracted[0].error_message}')
    print('✓ Invalid index handling passed')


@pytest.mark.asyncio
async def test_extract_pdf_empty_indices(pdf_with_images, tmp_path):
    """Test that empty asset_indices list returns error."""
    print('Testing PDF asset extraction with empty indices list...')
    output_dir = str(tmp_path / 'empty')
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[])
    assert result.status == 'error'
    assert result.error_message is not None
    assert 'No asset indices' in result.error_message
    print(f'Error message: {result.error_message}')
    print('✓ Empty indices handling passed')


@pytest.mark.asyncio
async def test_extract_pdf_no_images(pdf_without_images, tmp_path):
    """Test extraction from PDF without images."""
    print('Testing PDF asset extraction from text-only PDF...')
    output_dir = str(tmp_path / 'no_images')
    result = await extract_pdf(pdf_without_images, output_dir)
    assert result.status == 'success'
    assert result.extracted_count == 0
    print('No assets extracted (as expected)')
    print('✓ Text-only PDF extraction passed')


@pytest.mark.asyncio
async def test_extract_pdf_creates_output_dir(pdf_with_images, tmp_path):
    """Test that output directory is created if it doesn't exist."""
    print('Testing PDF asset extraction with nested output directory...')
    output_dir = str(tmp_path / 'nested' / 'dir' / 'output')
    print(f'Output directory: {output_dir}')
    result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'success'
    assert Path(output_dir).exists()
    print('Output directory created successfully')
    print('✓ Nested directory creation passed')


# Dispatch logic tests


def test_asset_extraction_extensions():
    """Test that ASSET_EXTRACTION_EXTENSIONS contains expected formats."""
    print('Testing ASSET_EXTRACTION_EXTENSIONS...')
    assert '.pdf' in ASSET_EXTRACTION_EXTENSIONS
    assert '.docx' in ASSET_EXTRACTION_EXTENSIONS
    assert '.doc' in ASSET_EXTRACTION_EXTENSIONS
    assert '.pptx' in ASSET_EXTRACTION_EXTENSIONS
    assert '.ppt' in ASSET_EXTRACTION_EXTENSIONS
    assert '.xlsx' in ASSET_EXTRACTION_EXTENSIONS
    assert '.xls' in ASSET_EXTRACTION_EXTENSIONS
    print(f'Supported extensions: {sorted(ASSET_EXTRACTION_EXTENSIONS)}')
    print('✓ Asset extraction extensions passed')


@pytest.mark.asyncio
async def test_dispatch_inspect_pdf(pdf_with_images):
    """Test dispatch_inspect with PDF file."""
    print('Testing dispatch_inspect with PDF...')
    result = await dispatch_inspect(pdf_with_images)
    assert result.status == 'success'
    assert result.asset_count > 0
    print(f'Dispatch found {result.asset_count} assets')
    print('✓ Dispatch inspect PDF passed')


@pytest.mark.asyncio
async def test_dispatch_inspect_unsupported():
    """Test dispatch_inspect with unsupported file type."""
    print('Testing dispatch_inspect with unsupported file type...')
    result = await dispatch_inspect('/tmp/test.txt')
    assert result.status == 'error'
    assert result.error_message is not None
    assert 'Unsupported' in result.error_message
    print(f'Error message: {result.error_message}')
    print('✓ Dispatch inspect unsupported file passed')


@pytest.mark.asyncio
async def test_dispatch_extract_pdf(pdf_with_images, tmp_path):
    """Test dispatch_extract with PDF file."""
    print('Testing dispatch_extract with PDF...')
    output_dir = str(tmp_path / 'dispatch_extract')
    result = await dispatch_extract(pdf_with_images, output_dir)
    assert result.status == 'success'
    assert result.extracted_count > 0
    print(f'Dispatch extracted {result.extracted_count} assets')
    print('✓ Dispatch extract PDF passed')


# ===============================================================================
# UNIT TESTS FOR INTERNAL PDF EXTRACTOR FUNCTIONS (Coverage Enhancement)
# ===============================================================================


# Tests for _resolve_filter_name
def test_resolve_filter_name_list_with_elements():
    """Test _resolve_filter_name with non-empty list returns last element."""
    print('Testing _resolve_filter_name with non-empty list...')

    # Mock PSLiteral-like object
    mock_literal = MagicMock()
    mock_literal.name = b'FlateDecode'

    result = _resolve_filter_name(['DCTDecode', mock_literal])
    assert result == 'FlateDecode'
    print('✓ _resolve_filter_name with non-empty list passed')


def test_resolve_filter_name_empty_list():
    """Test _resolve_filter_name with empty list returns empty string."""
    print('Testing _resolve_filter_name with empty list...')
    result = _resolve_filter_name([])
    assert result == ''
    print('✓ _resolve_filter_name with empty list passed')


def test_resolve_filter_name_psliteral_bytes_name():
    """Test _resolve_filter_name with PSLiteral having bytes name."""
    print('Testing _resolve_filter_name with PSLiteral (bytes name)...')
    mock_literal = MagicMock()
    mock_literal.name = b'DCTDecode'

    result = _resolve_filter_name(mock_literal)
    assert result == 'DCTDecode'
    print('✓ _resolve_filter_name with PSLiteral bytes name passed')


def test_resolve_filter_name_psliteral_string_name():
    """Test _resolve_filter_name with PSLiteral having string name."""
    print('Testing _resolve_filter_name with PSLiteral (string name)...')
    mock_literal = MagicMock()
    mock_literal.name = 'JPXDecode'

    result = _resolve_filter_name(mock_literal)
    assert result == 'JPXDecode'
    print('✓ _resolve_filter_name with PSLiteral string name passed')


def test_resolve_filter_name_bytes():
    """Test _resolve_filter_name with bytes input."""
    print('Testing _resolve_filter_name with bytes...')
    result = _resolve_filter_name(b'FlateDecode')
    assert result == 'FlateDecode'
    print('✓ _resolve_filter_name with bytes passed')


def test_resolve_filter_name_string():
    """Test _resolve_filter_name with plain string input."""
    print('Testing _resolve_filter_name with plain string...')
    result = _resolve_filter_name('CCITTFaxDecode')
    assert result == 'CCITTFaxDecode'
    print('✓ _resolve_filter_name with string passed')


# Tests for _get_image_format
def test_get_image_format_no_stream():
    """Test _get_image_format when image_obj has no stream."""
    print('Testing _get_image_format with no stream...')
    image_obj = {}
    fmt, ext = _get_image_format(image_obj)
    assert fmt == 'png'
    assert ext == '.png'
    print('✓ _get_image_format with no stream passed')


def test_get_image_format_no_filter():
    """Test _get_image_format when stream has no Filter attribute."""
    print('Testing _get_image_format with stream but no Filter...')
    mock_stream = MagicMock()
    mock_stream.attrs = {}
    image_obj = {'stream': mock_stream}

    fmt, ext = _get_image_format(image_obj)
    assert fmt == 'png'
    assert ext == '.png'
    print('✓ _get_image_format with no filter passed')


def test_get_image_format_dctdecode():
    """Test _get_image_format with DCTDecode filter returns JPEG."""
    print('Testing _get_image_format with DCTDecode filter...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'DCTDecode'}
    image_obj = {'stream': mock_stream}

    fmt, ext = _get_image_format(image_obj)
    assert fmt == 'jpeg'
    assert ext == '.jpg'
    print('✓ _get_image_format with DCTDecode passed')


def test_get_image_format_jpxdecode():
    """Test _get_image_format with JPXDecode filter returns JP2."""
    print('Testing _get_image_format with JPXDecode filter...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'JPXDecode'}
    image_obj = {'stream': mock_stream}

    fmt, ext = _get_image_format(image_obj)
    assert fmt == 'jp2'
    assert ext == '.jp2'
    print('✓ _get_image_format with JPXDecode passed')


def test_get_image_format_unknown_filter():
    """Test _get_image_format with unknown filter returns default format."""
    print('Testing _get_image_format with unknown filter...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'UnknownFilter'}
    image_obj = {'stream': mock_stream}

    fmt, ext = _get_image_format(image_obj)
    assert fmt == 'png'
    assert ext == '.png'
    print('✓ _get_image_format with unknown filter passed')


# Tests for _get_stream_dimensions
def test_get_stream_dimensions_no_stream():
    """Test _get_stream_dimensions when image_obj has no stream."""
    print('Testing _get_stream_dimensions with no stream...')
    image_obj = {}
    width, height = _get_stream_dimensions(image_obj)
    assert width is None
    assert height is None
    print('✓ _get_stream_dimensions with no stream passed')


def test_get_stream_dimensions_with_dimensions():
    """Test _get_stream_dimensions returns Width and Height from stream."""
    print('Testing _get_stream_dimensions with Width and Height...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Width': 800, 'Height': 600}
    image_obj = {'stream': mock_stream}

    width, height = _get_stream_dimensions(image_obj)
    assert width == 800
    assert height == 600
    print('✓ _get_stream_dimensions with dimensions passed')


# Tests for _get_stream_color_mode
def test_get_stream_color_mode_no_stream():
    """Test _get_stream_color_mode with no stream returns RGB."""
    print('Testing _get_stream_color_mode with no stream...')
    image_obj = {}
    mode = _get_stream_color_mode(image_obj)
    assert mode == 'RGB'
    print('✓ _get_stream_color_mode with no stream passed')


def test_get_stream_color_mode_no_colorspace():
    """Test _get_stream_color_mode with stream but no ColorSpace returns RGB."""
    print('Testing _get_stream_color_mode with no ColorSpace...')
    mock_stream = MagicMock()
    mock_stream.attrs = {}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'RGB'
    print('✓ _get_stream_color_mode with no ColorSpace passed')


def test_get_stream_color_mode_device_gray_psliteral():
    """Test _get_stream_color_mode with DeviceGray PSLiteral returns L."""
    print('Testing _get_stream_color_mode with DeviceGray PSLiteral...')
    mock_cs = MagicMock()
    mock_cs.name = b'DeviceGray'
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': mock_cs}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'L'
    print('✓ _get_stream_color_mode with DeviceGray PSLiteral passed')


def test_get_stream_color_mode_device_cmyk():
    """Test _get_stream_color_mode with DeviceCMYK returns CMYK."""
    print('Testing _get_stream_color_mode with DeviceCMYK...')
    mock_cs = MagicMock()
    mock_cs.name = 'DeviceCMYK'
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': mock_cs}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'CMYK'
    print('✓ _get_stream_color_mode with DeviceCMYK passed')


def test_get_stream_color_mode_bytes_colorspace():
    """Test _get_stream_color_mode with bytes ColorSpace."""
    print('Testing _get_stream_color_mode with bytes ColorSpace...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': b'DeviceGray'}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'L'
    print('✓ _get_stream_color_mode with bytes ColorSpace passed')


def test_get_stream_color_mode_array_colorspace():
    """Test _get_stream_color_mode with array ColorSpace [/Indexed /DeviceRGB ...]."""
    print('Testing _get_stream_color_mode with array ColorSpace...')
    mock_first = MagicMock()
    mock_first.name = b'Indexed'
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': [mock_first, 'DeviceRGB', 255]}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'RGB'  # 'Indexed' doesn't match Gray or CMYK
    print('✓ _get_stream_color_mode with array ColorSpace passed')


def test_get_stream_color_mode_plain_string():
    """Test _get_stream_color_mode with plain string ColorSpace."""
    print('Testing _get_stream_color_mode with plain string ColorSpace...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': 'DeviceRGB'}
    image_obj = {'stream': mock_stream}

    mode = _get_stream_color_mode(image_obj)
    assert mode == 'RGB'
    print('✓ _get_stream_color_mode with plain string passed')


# Tests for _get_image_bytes
def test_get_image_bytes_no_stream():
    """Test _get_image_bytes with no stream returns None."""
    print('Testing _get_image_bytes with no stream...')
    image_obj = {}
    result = _get_image_bytes(image_obj)
    assert result is None
    print('✓ _get_image_bytes with no stream passed')


def test_get_image_bytes_get_data_raises():
    """Test _get_image_bytes when get_data() raises exception returns None."""
    print('Testing _get_image_bytes when get_data() raises...')
    mock_stream = MagicMock()
    mock_stream.get_data.side_effect = Exception('Stream error')
    image_obj = {'stream': mock_stream}

    result = _get_image_bytes(image_obj)
    assert result is None
    print('✓ _get_image_bytes with exception passed')


def test_get_image_bytes_success():
    """Test _get_image_bytes successfully returns bytes."""
    print('Testing _get_image_bytes with successful get_data()...')
    mock_stream = MagicMock()
    mock_stream.get_data.return_value = b'\x89PNG\r\n\x1a\n...'
    image_obj = {'stream': mock_stream}

    result = _get_image_bytes(image_obj)
    assert result == b'\x89PNG\r\n\x1a\n...'
    print('✓ _get_image_bytes success passed')


# Tests for _is_raw_pixel_data
def test_is_raw_pixel_data_no_stream():
    """Test _is_raw_pixel_data with no stream returns True."""
    print('Testing _is_raw_pixel_data with no stream...')
    image_obj = {}
    result = _is_raw_pixel_data(image_obj)
    assert result is True
    print('✓ _is_raw_pixel_data with no stream passed')


def test_is_raw_pixel_data_no_filter():
    """Test _is_raw_pixel_data with no filter returns True."""
    print('Testing _is_raw_pixel_data with no filter...')
    mock_stream = MagicMock()
    mock_stream.attrs = {}
    image_obj = {'stream': mock_stream}

    result = _is_raw_pixel_data(image_obj)
    assert result is True
    print('✓ _is_raw_pixel_data with no filter passed')


def test_is_raw_pixel_data_dctdecode():
    """Test _is_raw_pixel_data with DCTDecode returns False."""
    print('Testing _is_raw_pixel_data with DCTDecode...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'DCTDecode'}
    image_obj = {'stream': mock_stream}

    result = _is_raw_pixel_data(image_obj)
    assert result is False
    print('✓ _is_raw_pixel_data with DCTDecode passed')


def test_is_raw_pixel_data_jpxdecode():
    """Test _is_raw_pixel_data with JPXDecode returns False."""
    print('Testing _is_raw_pixel_data with JPXDecode...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'JPXDecode'}
    image_obj = {'stream': mock_stream}

    result = _is_raw_pixel_data(image_obj)
    assert result is False
    print('✓ _is_raw_pixel_data with JPXDecode passed')


def test_is_raw_pixel_data_flatedecode():
    """Test _is_raw_pixel_data with FlateDecode returns True."""
    print('Testing _is_raw_pixel_data with FlateDecode...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'FlateDecode'}
    image_obj = {'stream': mock_stream}

    result = _is_raw_pixel_data(image_obj)
    assert result is True
    print('✓ _is_raw_pixel_data with FlateDecode passed')


# Tests for _introspect_image
def test_introspect_image_valid_jpeg():
    """Test _introspect_image with valid JPEG bytes."""
    print('Testing _introspect_image with valid JPEG...')
    # Create a small JPEG image
    img = PILImage.new('RGB', (100, 80), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', dpi=(96, 96))
    jpeg_bytes = buffer.getvalue()

    mock_image_obj = {'stream': None}
    width, height, dpi, color_space = _introspect_image(jpeg_bytes, 'jpeg', mock_image_obj)

    assert width == 100
    assert height == 80
    assert dpi == (96, 96)
    assert color_space == 'RGB'
    print('✓ _introspect_image with valid JPEG passed')


def test_introspect_image_grayscale():
    """Test _introspect_image with grayscale image returns 'Grayscale'."""
    print('Testing _introspect_image with grayscale image...')
    img = PILImage.new('L', (50, 40), color=128)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    mock_image_obj = {'stream': None}
    width, height, dpi, color_space = _introspect_image(png_bytes, 'png', mock_image_obj)

    assert width == 50
    assert height == 40
    assert color_space == 'Grayscale'
    print('✓ _introspect_image with grayscale passed')


def test_introspect_image_fallback_frombytes():
    """Test _introspect_image fallback to frombytes with stream dimensions."""
    print('Testing _introspect_image fallback to frombytes...')
    # Create raw RGB pixel data
    width, height = 10, 8
    raw_bytes = b'\xff\x00\x00' * (width * height)  # Red pixels

    mock_stream = MagicMock()
    mock_stream.attrs = {'Width': width, 'Height': height, 'ColorSpace': 'DeviceRGB'}
    mock_image_obj = {'stream': mock_stream}

    w, h, dpi, color_space = _introspect_image(raw_bytes, 'png', mock_image_obj)

    assert w == width
    assert h == height
    assert color_space in ('RGB', 'L', 'CMYK')  # Depends on mode detection
    print('✓ _introspect_image frombytes fallback passed')


def test_introspect_image_last_resort_dimensions():
    """Test _introspect_image last resort uses stream dimensions when all else fails."""
    print('Testing _introspect_image last resort with stream dimensions...')
    # Invalid bytes that can't be decoded
    invalid_bytes = b'\x00\x01\x02\x03\x04'

    mock_stream = MagicMock()
    mock_stream.attrs = {'Width': 200, 'Height': 150}
    mock_image_obj = {'stream': mock_stream}

    width, height, dpi, color_space = _introspect_image(invalid_bytes, 'png', mock_image_obj)

    # Should fall back to stream dimensions
    assert width == 200
    assert height == 150
    print('✓ _introspect_image last resort dimensions passed')


# Tests for _save_image_bytes
def test_save_image_bytes_jpeg_direct_write(tmp_path):
    """Test _save_image_bytes with JPEG format writes directly."""
    print('Testing _save_image_bytes with JPEG direct write...')
    # Create JPEG bytes
    img = PILImage.new('RGB', (50, 40), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    jpeg_bytes = buffer.getvalue()

    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'DCTDecode'}
    mock_image_obj = {'stream': mock_stream}

    output_path = str(tmp_path / 'test_direct.jpg')
    _save_image_bytes(jpeg_bytes, 'jpeg', output_path, mock_image_obj)

    assert Path(output_path).exists()
    assert Path(output_path).stat().st_size > 0
    print('✓ _save_image_bytes JPEG direct write passed')


def test_save_image_bytes_jp2_pillow_save(tmp_path):
    """Test _save_image_bytes with non-JPEG encoded uses Pillow open+save."""
    print('Testing _save_image_bytes with JP2 via Pillow...')
    # Use PNG as a proxy for non-JPEG encoded format
    img = PILImage.new('RGB', (30, 20), color='green')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'JPXDecode'}
    mock_image_obj = {'stream': mock_stream}

    output_path = str(tmp_path / 'test_jp2.png')
    _save_image_bytes(png_bytes, 'jp2', output_path, mock_image_obj)

    assert Path(output_path).exists()
    print('✓ _save_image_bytes JP2 Pillow save passed')


def test_save_image_bytes_raw_pixel_frombytes(tmp_path):
    """Test _save_image_bytes with raw pixel data uses frombytes."""
    print('Testing _save_image_bytes with raw pixel data...')
    width, height = 10, 8
    raw_bytes = b'\xff\x00\x00' * (width * height)  # Red pixels

    mock_stream = MagicMock()
    mock_stream.attrs = {
        'Width': width,
        'Height': height,
        'ColorSpace': 'DeviceRGB',
        'Filter': 'FlateDecode',
    }
    mock_image_obj = {'stream': mock_stream}

    output_path = str(tmp_path / 'test_raw.png')
    _save_image_bytes(raw_bytes, 'png', output_path, mock_image_obj)

    assert Path(output_path).exists()
    print('✓ _save_image_bytes raw pixel frombytes passed')


def test_save_image_bytes_last_resort_pillow_open(tmp_path):
    """Test _save_image_bytes last resort uses Pillow.open."""
    print('Testing _save_image_bytes last resort Pillow.open...')
    # Create valid PNG that will be used in last resort
    img = PILImage.new('RGB', (15, 12), color='yellow')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    # Mock image_obj with no stream dimensions to force last resort
    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'FlateDecode'}  # Raw pixel format
    mock_image_obj = {'stream': mock_stream}

    output_path = str(tmp_path / 'test_lastresort.png')
    _save_image_bytes(png_bytes, 'png', output_path, mock_image_obj)

    assert Path(output_path).exists()
    print('✓ _save_image_bytes last resort Pillow.open passed')


def test_save_image_bytes_all_paths_fail(tmp_path):
    """Test _save_image_bytes raises ValueError when all paths fail."""
    print('Testing _save_image_bytes with all paths failing...')
    # Completely invalid bytes
    invalid_bytes = b'\x00\x01\x02'

    mock_stream = MagicMock()
    mock_stream.attrs = {'Filter': 'FlateDecode'}
    mock_image_obj = {'stream': mock_stream}

    output_path = str(tmp_path / 'test_fail.png')

    with pytest.raises(ValueError, match='Cannot decode image data'):
        _save_image_bytes(invalid_bytes, 'png', output_path, mock_image_obj)

    print('✓ _save_image_bytes all paths fail passed')


# Tests for async wrapper timeout and error handling
@pytest.mark.asyncio
async def test_inspect_pdf_timeout():
    """Test inspect_pdf timeout returns error with timeout message."""
    print('Testing inspect_pdf timeout...')

    # Patch wait_for in the pdf module namespace
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf.asyncio.wait_for',
        side_effect=asyncio.TimeoutError(),
    ):
        result = await inspect_pdf('/tmp/test.pdf', timeout_seconds=1)

    assert result.status == 'error'
    assert 'timed out' in result.error_message
    assert '1 seconds' in result.error_message
    print('✓ inspect_pdf timeout passed')


@pytest.mark.asyncio
async def test_inspect_pdf_unexpected_exception():
    """Test inspect_pdf handles unexpected exception."""
    print('Testing inspect_pdf unexpected exception...')

    # Patch wait_for in the pdf module namespace to raise unexpected error
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf.asyncio.wait_for',
        side_effect=RuntimeError('Unexpected error'),
    ):
        result = await inspect_pdf('/tmp/test.pdf')

    assert result.status == 'error'
    assert 'Unexpected error' in result.error_message
    print('✓ inspect_pdf unexpected exception passed')


@pytest.mark.asyncio
async def test_extract_pdf_timeout():
    """Test extract_pdf timeout returns error with timeout message."""
    print('Testing extract_pdf timeout...')

    # Patch wait_for in the pdf module namespace
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf.asyncio.wait_for',
        side_effect=asyncio.TimeoutError(),
    ):
        result = await extract_pdf('/tmp/test.pdf', '/tmp/output', timeout_seconds=1)

    assert result.status == 'error'
    assert 'timed out' in result.error_message
    assert '1 seconds' in result.error_message
    print('✓ extract_pdf timeout passed')


@pytest.mark.asyncio
async def test_extract_pdf_unexpected_exception():
    """Test extract_pdf handles unexpected exception."""
    print('Testing extract_pdf unexpected exception...')

    # Patch wait_for in the pdf module namespace to raise unexpected error
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf.asyncio.wait_for',
        side_effect=ValueError('Unexpected extraction error'),
    ):
        result = await extract_pdf('/tmp/test.pdf', '/tmp/output')

    assert result.status == 'error'
    assert 'Unexpected' in result.error_message
    print('✓ extract_pdf unexpected exception passed')


# Tests for MAX_ASSETS limit in inspect
@pytest.mark.asyncio
async def test_inspect_pdf_max_assets_limit(pdf_with_images):
    """Test inspect_pdf hits MAX_ASSETS limit and returns partial status."""
    print('Testing inspect_pdf with MAX_ASSETS=1...')

    with patch.dict(os.environ, {'MAX_ASSETS': '1'}):
        result = await inspect_pdf(pdf_with_images)

    # With limit of 1, should only inspect 1 asset but find more
    assert result.asset_count <= 1
    if result.total_assets_found > 1:
        assert result.status == 'partial'
        assert any('MAX_ASSETS' in warning for warning in result.warnings)
        print(f'Correctly limited to 1 asset (found {result.total_assets_found} total)')

    print('✓ inspect_pdf MAX_ASSETS limit passed')


# Tests for extract_pdf edge cases
@pytest.mark.asyncio
async def test_extract_pdf_file_not_found(tmp_path):
    """Test extract_pdf with non-existent file returns error."""
    print('Testing extract_pdf with non-existent file...')
    output_dir = str(tmp_path / 'output')
    result = await extract_pdf('/nonexistent/file.pdf', output_dir)

    assert result.status == 'error'
    assert 'not found' in result.error_message.lower()
    print('✓ extract_pdf file not found passed')


@pytest.mark.asyncio
async def test_extract_pdf_max_assets_limit_during_discovery(pdf_with_images, tmp_path):
    """Test extract_pdf respects MAX_ASSETS limit during discovery phase."""
    print('Testing extract_pdf with MAX_ASSETS=1...')
    output_dir = str(tmp_path / 'output')

    # Patch _get_max_assets to return 1
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._get_max_assets', return_value=1
    ):
        result = await extract_pdf(pdf_with_images, output_dir)

    # With limit of 1, discovery will only find 1 image regardless of how many exist
    # Extraction should succeed with at most 1 asset
    assert result.status == 'success'
    assert result.extracted_count <= 1

    print('✓ extract_pdf MAX_ASSETS discovery limit passed')


# ===============================================================================
# CORRUPTED PDF / EDGE CASE TESTS (Remaining coverage gaps)
# ===============================================================================


def test_get_stream_color_mode_array_no_name_attr():
    """Test array color space where first element has no .name attribute (line 140)."""
    print('Testing _get_stream_color_mode with array color space, no .name on first element...')
    mock_stream = MagicMock()
    mock_stream.attrs = {'ColorSpace': ['DeviceRGB', 256, 'some_table']}
    image_obj = {'stream': mock_stream}
    result = _get_stream_color_mode(image_obj)
    assert result == 'RGB'
    print('✓ Array color space without .name attribute returns RGB')


def test_introspect_image_unusual_mode():
    """Test _introspect_image with image having unusual mode like RGBA (line 221)."""
    print('Testing _introspect_image with RGBA mode image...')
    img = PILImage.new('RGBA', (50, 50), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    raw_bytes = buf.getvalue()
    image_obj = {'stream': None}
    width, height, dpi, color_space = _introspect_image(raw_bytes, 'png', image_obj)
    assert width == 50
    assert height == 50
    assert color_space == 'RGBA'
    print('✓ Unusual mode RGBA preserved as-is')


def test_introspect_image_frombytes_grayscale():
    """Test _introspect_image frombytes fallback with Grayscale raw data (line 233)."""
    print('Testing _introspect_image frombytes fallback with grayscale raw data...')
    raw_bytes = bytes([128] * (10 * 10))  # 10x10 grayscale raw pixels
    mock_stream = MagicMock()
    mock_stream.attrs = {'Width': 10, 'Height': 10, 'ColorSpace': None}
    image_obj = {'stream': mock_stream}

    # Patch _get_stream_color_mode to return 'L' for grayscale
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._get_stream_color_mode',
        return_value='L',
    ):
        width, height, dpi, color_space = _introspect_image(raw_bytes, 'png', image_obj)
    assert width == 10
    assert height == 10
    assert color_space == 'Grayscale'
    print('✓ frombytes fallback with Grayscale raw data works')


def test_introspect_image_frombytes_fails_last_resort():
    """Test _introspect_image when frombytes raises, falls to last resort (lines 234-238)."""
    print('Testing _introspect_image when frombytes fails...')
    raw_bytes = b'not valid image data at all'
    mock_stream = MagicMock()
    mock_stream.attrs = {'Width': 5, 'Height': 5, 'ColorSpace': None}
    image_obj = {'stream': mock_stream}
    width, height, dpi, color_space = _introspect_image(raw_bytes, 'png', image_obj)
    # Last resort: uses stream dimensions directly
    assert width == 5
    assert height == 5
    print('✓ Last resort stream dimensions used when frombytes fails')


@pytest.mark.asyncio
async def test_inspect_pdf_image_no_bytes(pdf_with_images):
    """Test inspection when _get_image_bytes returns None for an image (lines 322-326)."""
    print('Testing inspection when image bytes extraction fails...')
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._get_image_bytes', return_value=None
    ):
        result = await inspect_pdf(pdf_with_images)
    # Images exist but bytes can't be extracted → warnings, partial status
    assert result.status in ('partial', 'success')
    has_warning = any('Could not extract bytes' in w for w in result.warnings)
    assert has_warning
    print(f'Warnings: {result.warnings}')
    print('✓ Image with no extractable bytes produces warning')


@pytest.mark.asyncio
async def test_inspect_pdf_per_image_exception(pdf_with_images):
    """Test inspection when processing a single image raises exception (lines 357-358)."""
    print('Testing inspection when image processing raises exception...')
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._get_image_format',
        side_effect=RuntimeError('Corrupted image stream'),
    ):
        result = await inspect_pdf(pdf_with_images)
    # All images fail → total_assets_found > 0 but assets empty
    has_warning = any('Failed to inspect image' in w for w in result.warnings)
    assert has_warning
    print(f'Warnings: {result.warnings}')
    print('✓ Per-image exception produces warning')


@pytest.mark.asyncio
async def test_inspect_pdf_corrupted_file():
    """Test inspection of a corrupted/invalid PDF file (lines 374-375)."""
    print('Testing inspection of corrupted PDF...')
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.4 this is not a valid pdf at all garbage data')
        corrupted_path = f.name
    try:
        result = await inspect_pdf(corrupted_path)
        assert result.status == 'error'
        assert 'Failed to inspect PDF' in result.error_message
        print(f'Error: {result.error_message}')
        print('✓ Corrupted PDF returns error status')
    finally:
        os.unlink(corrupted_path)


def test_save_image_bytes_encoded_non_jpeg_pillow_fails_fallthrough(tmp_path):
    """Test _save_image_bytes when non-JPEG encoded image Pillow open fails (lines 431-432)."""
    print('Testing _save_image_bytes fallthrough when Pillow open fails for encoded image...')
    output_path = str(tmp_path / 'test_fallthrough.png')
    # Create raw pixel data that _is_raw_pixel_data returns False for (encoded)
    # but PILImage.open will fail on, then frombytes will succeed
    raw_bytes = bytes([255, 0, 0] * (10 * 10))  # 10x10 RGB raw
    mock_stream = MagicMock()
    mock_stream.attrs = {
        'Filter': 'JPXDecode',  # encoded, so _is_raw_pixel_data=False
        'Width': 10,
        'Height': 10,
        'ColorSpace': None,
    }
    image_obj = {'stream': mock_stream}
    _save_image_bytes(raw_bytes, 'jp2', output_path, image_obj)
    assert Path(output_path).exists()
    assert Path(output_path).stat().st_size > 0
    print('✓ Fallthrough from Pillow.open to frombytes works')


def test_save_image_bytes_frombytes_also_fails(tmp_path):
    """Test _save_image_bytes when frombytes fails too, tries last resort (lines 442-443)."""
    print('Testing _save_image_bytes when frombytes fails, tries last resort Pillow open...')
    output_path = str(tmp_path / 'test_last_resort.png')
    # Create a valid PNG that PILImage.open can handle at last resort
    img = PILImage.new('RGB', (5, 5), color='blue')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()

    mock_stream = MagicMock()
    mock_stream.attrs = {
        'Filter': 'SomeUnknownFilter',  # raw pixel path
        'Width': 999,  # Wrong dimensions → frombytes will fail
        'Height': 999,
        'ColorSpace': None,
    }
    image_obj = {'stream': mock_stream}
    _save_image_bytes(png_bytes, 'png', output_path, image_obj)
    assert Path(output_path).exists()
    print('✓ Last resort Pillow.open succeeds after frombytes fails')


@pytest.mark.asyncio
async def test_extract_pdf_image_no_bytes(pdf_with_images, tmp_path):
    """Test extraction when _get_image_bytes returns None (lines 545-555)."""
    print('Testing extraction when image bytes extraction fails...')
    output_dir = str(tmp_path / 'no_bytes_extract')
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._get_image_bytes', return_value=None
    ):
        result = await extract_pdf(pdf_with_images, output_dir)
    # All images have no bytes → all fail
    assert result.status == 'error'
    assert result.failed_count > 0
    for item in result.extracted:
        assert item.status == 'error'
        assert 'Could not extract image bytes' in item.error_message
    print(f'Failed count: {result.failed_count}')
    print('✓ Extraction with no bytes produces per-asset errors')


@pytest.mark.asyncio
async def test_extract_pdf_save_raises_exception(pdf_with_images, tmp_path):
    """Test extraction when _save_image_bytes raises (lines 568-577)."""
    print('Testing extraction when save raises exception...')
    output_dir = str(tmp_path / 'save_fails')
    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._save_image_bytes',
        side_effect=ValueError('Cannot decode image data: corrupt'),
    ):
        result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'error'
    assert result.failed_count > 0
    for item in result.extracted:
        assert item.status == 'error'
    print(f'Failed count: {result.failed_count}')
    print('✓ Per-asset save exception handled correctly')


@pytest.mark.asyncio
async def test_extract_pdf_partial_status(pdf_with_images, tmp_path):
    """Test extraction returns 'partial' when some succeed and some fail (line 585)."""
    print('Testing partial extraction status...')
    output_dir = str(tmp_path / 'partial')
    call_count = [0]
    original_save = _save_image_bytes

    def flaky_save(raw_bytes, fmt, output_path, image_obj):
        call_count[0] += 1
        if call_count[0] == 1:
            return original_save(raw_bytes, fmt, output_path, image_obj)
        raise ValueError('Simulated failure on 2nd+ image')

    with patch(
        'awslabs.document_loader_mcp_server.extractors.pdf._save_image_bytes',
        side_effect=flaky_save,
    ):
        result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'partial'
    assert result.extracted_count >= 1
    assert result.failed_count >= 1
    print(f'Extracted: {result.extracted_count}, Failed: {result.failed_count}')
    print('✓ Partial status when mixed success/failure')


@pytest.mark.asyncio
async def test_extract_pdf_corrupted_file(tmp_path):
    """Test extraction of a corrupted PDF file (outer exception in _extract_pdf_sync)."""
    print('Testing extraction of corrupted PDF...')
    corrupted_path = str(tmp_path / 'corrupted.pdf')
    with open(corrupted_path, 'wb') as f:
        f.write(b'%PDF-1.4 total garbage not a real pdf')
    output_dir = str(tmp_path / 'corrupted_out')
    result = await extract_pdf(corrupted_path, output_dir)
    assert result.status == 'error'
    assert 'Failed to extract PDF assets' in result.error_message
    print(f'Error: {result.error_message}')
    print('✓ Corrupted PDF extraction returns error')
