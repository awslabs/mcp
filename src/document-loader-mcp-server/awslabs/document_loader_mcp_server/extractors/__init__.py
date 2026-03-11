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
import shutil
import tempfile
from loguru import logger
from pathlib import Path
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
    width_px: Optional[int] = Field(default=None, description='Pixel width')
    height_px: Optional[int] = Field(default=None, description='Pixel height')
    dpi: Optional[Tuple[int, int]] = Field(default=None, description='(x_dpi, y_dpi)')
    color_space: Optional[str] = Field(default=None, description='RGB, CMYK, or Grayscale')
    compression: Optional[str] = Field(
        default=None, description='PDF filter name: DCTDecode, FlateDecode, etc.'
    )
    location: str = Field(..., description='Location in document, e.g. Page 3')


class DocumentMetadata(BaseModel):
    """Document-level metadata."""

    file_path: str = Field(..., description='Path to the document file')
    file_type: str = Field(..., description='File type: pdf, docx, pptx, xlsx, etc.')
    file_size_bytes: int = Field(..., description='File size in bytes')
    title: Optional[str] = Field(default=None, description='Document title')
    author: Optional[str] = Field(default=None, description='Document author')
    created: Optional[str] = Field(default=None, description='Creation date (ISO 8601)')
    modified: Optional[str] = Field(default=None, description='Last modified date (ISO 8601)')
    page_count: Optional[int] = Field(default=None, description='Number of pages/slides/sheets')


class InspectionResponse(BaseModel):
    """Response from asset inspection operations."""

    status: str = Field(..., description='success, partial, or error')
    metadata: Optional[DocumentMetadata] = Field(
        default=None, description='Document-level metadata'
    )
    assets: List[AssetInfo] = Field(
        default_factory=list, description='Successfully inspected assets'
    )
    asset_count: int = Field(default=0, description='Number of successfully inspected assets')
    total_assets_found: int = Field(
        default=0, description='Total assets discovered, including failed inspections'
    )
    warnings: List[str] = Field(default_factory=list, description='Non-fatal warnings')
    error_message: Optional[str] = Field(
        default=None, description='Error message if status is error'
    )


class ExtractedAsset(BaseModel):
    """Result of extracting a single asset."""

    index: int = Field(..., description='Asset index from inspection')
    output_path: str = Field(..., description='Path where the asset was saved')
    status: str = Field(..., description='success or error')
    error_message: Optional[str] = Field(default=None, description='Why this asset failed')


class ExtractionResponse(BaseModel):
    """Response from asset extraction operations."""

    status: str = Field(..., description='success, partial, or error')
    extracted: List[ExtractedAsset] = Field(
        default_factory=list, description='Per-asset extraction results'
    )
    extracted_count: int = Field(default=0, description='Number of successfully extracted assets')
    failed_count: int = Field(default=0, description='Number of failed extractions')
    output_dir: str = Field(default='', description='Directory containing extracted assets')
    warnings: List[str] = Field(default_factory=list, description='Non-fatal warnings')
    error_message: Optional[str] = Field(
        default=None, description='Error message if status is error'
    )


# Dispatch logic for multi-format support
ASSET_EXTRACTION_EXTENSIONS = {
    '.pdf',
    '.docx',
    '.doc',
    '.pptx',
    '.ppt',
    '.xlsx',
    '.xls',
}

OFFICE_EXTENSIONS = {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'}


async def dispatch_inspect(
    file_path: str,
    timeout_seconds: int = 30,
    convert_to_pdf_fn=None,
    check_soffice_fn=None,
) -> InspectionResponse:
    """Dispatch inspection based on file type.

    PDF -> pdfplumber directly.
    Office formats -> soffice convert to PDF -> pdfplumber.
    """
    from awslabs.document_loader_mcp_server.extractors.pdf import inspect_pdf

    suffix = Path(file_path).suffix.lower()

    if suffix not in ASSET_EXTRACTION_EXTENSIONS:
        return InspectionResponse(
            status='error',
            asset_count=0,
            total_assets_found=0,
            error_message=f'Unsupported file type: {suffix}. Supported: {", ".join(sorted(ASSET_EXTRACTION_EXTENSIONS))}',
        )

    if suffix == '.pdf':
        return await inspect_pdf(file_path, timeout_seconds)

    # Office format: check soffice, convert to PDF, then inspect
    if check_soffice_fn:
        soffice_error = check_soffice_fn()
        if soffice_error:
            return InspectionResponse(
                status='error',
                asset_count=0,
                total_assets_found=0,
                error_message=soffice_error,
            )

    if convert_to_pdf_fn is None:
        return InspectionResponse(
            status='error',
            asset_count=0,
            total_assets_found=0,
            error_message='soffice conversion not available (no converter provided)',
        )

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix='docloader_assets_')
        pdf_path = convert_to_pdf_fn(file_path, temp_dir, timeout_seconds)
        result = await inspect_pdf(pdf_path, timeout_seconds)
        # Override metadata to reflect original file
        if result.metadata:
            result.metadata.file_path = file_path
            result.metadata.file_type = suffix.lstrip('.')
            result.metadata.file_size_bytes = Path(file_path).stat().st_size
        return result
    except Exception as e:
        logger.error(f'Error during soffice inspection of {file_path}: {str(e)}')
        return InspectionResponse(
            status='error',
            asset_count=0,
            total_assets_found=0,
            error_message=f'Error converting {suffix} to PDF: {str(e)}',
        )
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def dispatch_extract(
    file_path: str,
    output_dir: str,
    asset_indices: Optional[List[int]] = None,
    timeout_seconds: int = 60,
    convert_to_pdf_fn=None,
    check_soffice_fn=None,
) -> ExtractionResponse:
    """Dispatch extraction based on file type.

    PDF -> pdfplumber directly.
    Office formats -> soffice convert to PDF -> pdfplumber.
    """
    from awslabs.document_loader_mcp_server.extractors.pdf import extract_pdf

    suffix = Path(file_path).suffix.lower()

    if suffix not in ASSET_EXTRACTION_EXTENSIONS:
        return ExtractionResponse(
            status='error',
            output_dir=output_dir,
            error_message=f'Unsupported file type: {suffix}. Supported: {", ".join(sorted(ASSET_EXTRACTION_EXTENSIONS))}',
        )

    if suffix == '.pdf':
        return await extract_pdf(file_path, output_dir, asset_indices, timeout_seconds)

    # Office format: check soffice, convert to PDF, then extract
    if check_soffice_fn:
        soffice_error = check_soffice_fn()
        if soffice_error:
            return ExtractionResponse(
                status='error',
                output_dir=output_dir,
                error_message=soffice_error,
            )

    if convert_to_pdf_fn is None:
        return ExtractionResponse(
            status='error',
            output_dir=output_dir,
            error_message='soffice conversion not available (no converter provided)',
        )

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix='docloader_assets_')
        pdf_path = convert_to_pdf_fn(file_path, temp_dir, timeout_seconds)
        return await extract_pdf(pdf_path, output_dir, asset_indices, timeout_seconds)
    except Exception as e:
        logger.error(f'Error during soffice extraction of {file_path}: {str(e)}')
        return ExtractionResponse(
            status='error',
            output_dir=output_dir,
            error_message=f'Error converting {suffix} to PDF: {str(e)}',
        )
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
