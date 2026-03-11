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
    ExtractionResponse,
    ExtractedAsset,
    InspectionResponse,
)


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
