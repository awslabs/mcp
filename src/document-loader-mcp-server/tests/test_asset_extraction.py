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

import pytest
from awslabs.document_loader_mcp_server.extractors import (
    AssetInfo,
    DocumentMetadata,
    ExtractedAsset,
    ExtractionResponse,
    InspectionResponse,
)
from awslabs.document_loader_mcp_server.extractors.pdf import extract_pdf, inspect_pdf
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


def test_asset_info_optional_fields():
    """Test creating AssetInfo with only required fields."""
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


def test_document_metadata_creation():
    """Test creating DocumentMetadata with all fields."""
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


def test_inspection_response_success():
    """Test InspectionResponse with success status and empty assets."""
    response = InspectionResponse(status='success', asset_count=0, total_assets_found=0)
    assert response.status == 'success'
    assert response.metadata is None
    assert response.assets == []
    assert response.asset_count == 0
    assert response.total_assets_found == 0
    assert response.warnings == []
    assert response.error_message is None


def test_inspection_response_partial():
    """Test InspectionResponse with partial status where total_assets_found > asset_count."""
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


def test_extraction_response():
    """Test ExtractionResponse with one successful ExtractedAsset."""
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


def test_extracted_asset_error():
    """Test ExtractedAsset with error status."""
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


@pytest.mark.asyncio
async def test_inspect_pdf_with_images(pdf_with_images):
    """Test inspecting PDF with embedded images."""
    result = await inspect_pdf(pdf_with_images)
    assert result.status == 'success'
    assert result.metadata is not None
    assert result.metadata.file_type == 'pdf'
    assert result.metadata.page_count >= 2
    assert result.asset_count > 0
    assert result.total_assets_found > 0
    assert len(result.assets) == result.asset_count
    for asset in result.assets:
        assert asset.index >= 0
        assert asset.name
        assert asset.format in ('jpeg', 'png', 'tiff', 'jp2')
        assert asset.size_bytes > 0
        assert asset.location.startswith('Page ')


@pytest.mark.asyncio
async def test_inspect_pdf_without_images(pdf_without_images):
    """Test inspecting PDF without embedded images."""
    result = await inspect_pdf(pdf_without_images)
    assert result.status == 'success'
    assert result.metadata is not None
    assert result.metadata.page_count >= 1
    assert result.asset_count == 0
    assert result.total_assets_found == 0
    assert result.assets == []


@pytest.mark.asyncio
async def test_inspect_pdf_metadata(pdf_with_images):
    """Test that PDF metadata extraction works correctly."""
    result = await inspect_pdf(pdf_with_images)
    assert result.metadata is not None
    assert result.metadata.file_path == pdf_with_images
    assert result.metadata.file_size_bytes > 0
    assert result.metadata.page_count is not None


@pytest.mark.asyncio
async def test_inspect_pdf_nonexistent():
    """Test that nonexistent PDF files return error status."""
    result = await inspect_pdf('/tmp/nonexistent_file.pdf')
    assert result.status == 'error'
    assert result.error_message is not None
    assert result.asset_count == 0


@pytest.mark.asyncio
async def test_extract_pdf_all_assets(pdf_with_images, tmp_path):
    """Test extracting all assets from PDF with images."""
    output_dir = str(tmp_path / 'extracted')
    result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'success'
    assert result.extracted_count > 0
    assert result.failed_count == 0
    assert result.output_dir == output_dir
    for item in result.extracted:
        assert item.status == 'success'
        assert Path(item.output_path).exists()
        assert Path(item.output_path).stat().st_size > 0


@pytest.mark.asyncio
async def test_extract_pdf_selective(pdf_with_images, tmp_path):
    """Test selective extraction of specific asset indices."""
    output_dir = str(tmp_path / 'selective')
    inspection = await inspect_pdf(pdf_with_images)
    assert inspection.asset_count > 0
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[0])
    assert result.status == 'success'
    assert result.extracted_count == 1
    assert len(result.extracted) == 1
    assert result.extracted[0].index == 0


@pytest.mark.asyncio
async def test_extract_pdf_invalid_index(pdf_with_images, tmp_path):
    """Test handling of invalid asset index."""
    output_dir = str(tmp_path / 'invalid')
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[999])
    assert result.status == 'error'
    assert result.failed_count == 1
    assert result.extracted[0].status == 'error'
    assert result.extracted[0].error_message is not None


@pytest.mark.asyncio
async def test_extract_pdf_empty_indices(pdf_with_images, tmp_path):
    """Test that empty asset_indices list returns error."""
    output_dir = str(tmp_path / 'empty')
    result = await extract_pdf(pdf_with_images, output_dir, asset_indices=[])
    assert result.status == 'error'
    assert result.error_message is not None
    assert 'No asset indices' in result.error_message


@pytest.mark.asyncio
async def test_extract_pdf_no_images(pdf_without_images, tmp_path):
    """Test extraction from PDF without images."""
    output_dir = str(tmp_path / 'no_images')
    result = await extract_pdf(pdf_without_images, output_dir)
    assert result.status == 'success'
    assert result.extracted_count == 0


@pytest.mark.asyncio
async def test_extract_pdf_creates_output_dir(pdf_with_images, tmp_path):
    """Test that output directory is created if it doesn't exist."""
    output_dir = str(tmp_path / 'nested' / 'dir' / 'output')
    result = await extract_pdf(pdf_with_images, output_dir)
    assert result.status == 'success'
    assert Path(output_dir).exists()
