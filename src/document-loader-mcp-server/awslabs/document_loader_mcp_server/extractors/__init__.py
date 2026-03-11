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
"""Data models for asset extraction functionality."""

import os
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple


DEFAULT_MAX_ASSETS = 200


def _get_max_assets() -> int:
    """Get max assets from environment or use default.

    Returns:
        Maximum number of assets to process (default: 200).
    """
    env_val = os.getenv('MAX_ASSETS')
    if env_val:
        try:
            val = int(env_val)
            if val > 0:
                return val
        except ValueError:
            pass
    return DEFAULT_MAX_ASSETS


class AssetInfo(BaseModel):
    """Information about an embedded asset in a document."""

    index: int = Field(..., description='Position in asset list (for selective extraction)')
    name: str = Field(..., description='Generated filename (e.g., image_001.jpg)')
    format: str = Field(..., description='Output image format (png, jpeg, tiff, jp2)')
    size_bytes: int = Field(..., description='Raw byte size of the embedded image data')
    width_px: Optional[int] = Field(None, description='Pixel width')
    height_px: Optional[int] = Field(None, description='Pixel height')
    dpi: Optional[Tuple[int, int]] = Field(None, description='(x_dpi, y_dpi)')
    color_space: Optional[str] = Field(None, description='RGB, CMYK, or Grayscale')
    compression: Optional[str] = Field(
        None, description='PDF filter name: DCTDecode, FlateDecode, etc.'
    )
    location: str = Field(..., description='Location in document, e.g. Page 3')


class DocumentMetadata(BaseModel):
    """Document-level metadata."""

    file_path: str = Field(..., description='Path to the document file')
    file_type: str = Field(..., description='File type: pdf, docx, pptx, xlsx, etc.')
    file_size_bytes: int = Field(..., description='File size in bytes')
    title: Optional[str] = Field(None, description='Document title')
    author: Optional[str] = Field(None, description='Document author')
    created: Optional[str] = Field(None, description='Creation date (ISO 8601)')
    modified: Optional[str] = Field(None, description='Last modified date (ISO 8601)')
    page_count: Optional[int] = Field(None, description='Number of pages/slides/sheets')


class InspectionResponse(BaseModel):
    """Response from asset inspection operations."""

    status: str = Field(..., description='success, partial, or error')
    metadata: Optional[DocumentMetadata] = Field(None, description='Document-level metadata')
    assets: List[AssetInfo] = Field(
        default_factory=list, description='Successfully inspected assets'
    )
    asset_count: int = Field(0, description='Number of successfully inspected assets')
    total_assets_found: int = Field(
        0, description='Total assets discovered, including failed inspections'
    )
    warnings: List[str] = Field(default_factory=list, description='Non-fatal warnings')
    error_message: Optional[str] = Field(None, description='Error message if status is error')


class ExtractedAsset(BaseModel):
    """Result of extracting a single asset."""

    index: int = Field(..., description='Asset index from inspection')
    output_path: str = Field(..., description='Path where the asset was saved')
    status: str = Field(..., description='success or error')
    error_message: Optional[str] = Field(None, description='Why this asset failed')


class ExtractionResponse(BaseModel):
    """Response from asset extraction operations."""

    status: str = Field(..., description='success, partial, or error')
    extracted: List[ExtractedAsset] = Field(
        default_factory=list, description='Per-asset extraction results'
    )
    extracted_count: int = Field(0, description='Number of successfully extracted assets')
    failed_count: int = Field(0, description='Number of failed extractions')
    output_dir: str = Field('', description='Directory containing extracted assets')
    warnings: List[str] = Field(default_factory=list, description='Non-fatal warnings')
    error_message: Optional[str] = Field(None, description='Error message if status is error')
