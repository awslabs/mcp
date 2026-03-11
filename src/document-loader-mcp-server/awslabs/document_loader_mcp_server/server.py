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
"""Document Loader MCP Server."""

import asyncio
import os
import pdfplumber
import shutil
import subprocess  # nosec B404 - subprocess used with fixed command, no shell=True
import sys
import tempfile
from awslabs.document_loader_mcp_server.extractors import (
    ExtractionResponse,
    InspectionResponse,
    dispatch_extract,
    dispatch_inspect,
)
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.utilities.types import Image
from loguru import logger
from markitdown import MarkItDown
from pathlib import Path
from pdf2image import convert_from_path
from pydantic import BaseModel, Field
from typing import List, Optional


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server with a unique name to avoid old tool registry
mcp = FastMCP('Document Loader')


# Security Constants
DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit


def _get_max_file_size() -> int:
    """Get max file size from environment or use default.

    The MAX_FILE_SIZE_MB env var is specified in megabytes for ergonomics.
    """
    env_val = os.getenv('MAX_FILE_SIZE_MB')
    if env_val:
        try:
            size_mb = int(env_val)
            if size_mb > 0:
                return size_mb * 1024 * 1024
            logger.warning(
                f'MAX_FILE_SIZE_MB must be positive, using default: '
                f'{DEFAULT_MAX_FILE_SIZE // (1024 * 1024)}MB'
            )
        except ValueError:
            logger.warning(
                f'Invalid MAX_FILE_SIZE_MB value: {env_val}, using default: '
                f'{DEFAULT_MAX_FILE_SIZE // (1024 * 1024)}MB'
            )
    return DEFAULT_MAX_FILE_SIZE


# Base directory for file access security - configurable via environment
# Secure by default: restricts to current working directory
# For production: set DOCUMENT_BASE_DIR="/var/app/documents"
# For testing: set DOCUMENT_BASE_DIR="/" to allow temp files
def _get_base_directory() -> Path:
    """Get base directory with secure defaults."""
    env_base = os.getenv('DOCUMENT_BASE_DIR')
    if env_base:
        return Path(env_base)

    # Check if we're in a testing environment
    if any(
        test_indicator in os.environ
        for test_indicator in ['PYTEST_CURRENT_TEST', 'CI', 'GITHUB_ACTIONS']
    ):
        # In testing: allow broader access for temp files
        return Path('/')

    # Production default: restrict to current working directory
    return Path.cwd()


BASE_DIRECTORY = _get_base_directory()

# Timeout Constants
DEFAULT_TIMEOUT_SECONDS = 30  # 30 second default timeout
MAX_TIMEOUT_SECONDS = 300  # 5 minute maximum timeout
MIN_TIMEOUT_SECONDS = 5  # 5 second minimum timeout
DEFAULT_SOFFICE_TIMEOUT_SECONDS = 120  # 2 minute default for soffice subprocess


def _get_soffice_timeout() -> int:
    """Get soffice subprocess timeout from environment or use default.

    The SOFFICE_TIMEOUT_SECONDS env var controls how long the soffice
    subprocess is allowed to run before being killed.
    """
    env_val = os.getenv('SOFFICE_TIMEOUT_SECONDS')
    if env_val:
        try:
            timeout = int(env_val)
            if MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
                return timeout
            logger.warning(
                f'SOFFICE_TIMEOUT_SECONDS must be between {MIN_TIMEOUT_SECONDS} and '
                f'{MAX_TIMEOUT_SECONDS}, using default: {DEFAULT_SOFFICE_TIMEOUT_SECONDS}s'
            )
        except ValueError:
            logger.warning(
                f'Invalid SOFFICE_TIMEOUT_SECONDS value: {env_val}, using default: '
                f'{DEFAULT_SOFFICE_TIMEOUT_SECONDS}s'
            )
    return DEFAULT_SOFFICE_TIMEOUT_SECONDS


ALLOWED_EXTENSIONS = {
    '.pdf',
    '.docx',
    '.doc',
    '.xlsx',
    '.xls',
    '.pptx',
    '.ppt',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.bmp',
    '.tiff',
    '.tif',
    '.webp',
}


# Pydantic Models for Request/Response Validation
class DocumentReadResponse(BaseModel):
    """Response from document reading operations."""

    status: str = Field(..., description='Status of the operation (success/error)')
    content: str = Field(..., description='Extracted content from the document')
    file_path: str = Field(..., description='Path to the processed file')
    error_message: Optional[str] = Field(None, description='Error message if operation failed')


class SlidesExtractionResponse(BaseModel):
    """Response from slide image extraction operations."""

    status: str = Field(..., description='Status of the operation (success/error)')
    slide_images: List[str] = Field(
        default_factory=list, description='List of file paths to extracted slide images'
    )
    slide_count: int = Field(0, description='Number of slides extracted')
    file_path: str = Field(..., description='Path to the source file')
    output_dir: str = Field('', description='Directory containing the extracted slide images')
    error_message: Optional[str] = Field(None, description='Error message if operation failed')


def _extract_pdf_text_sync(file_path: str) -> str:
    """Synchronous PDF text extraction for thread pool execution."""
    text_content = ''
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text_content += f'\n--- Page {page_num} ---\n'
            page_text = page.extract_text()
            if page_text:
                text_content += page_text
    return text_content.strip()


def _convert_document_sync(file_path: str) -> str:
    """Synchronous document conversion for thread pool execution."""
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content


def _load_image_sync(file_path: str) -> Image:
    """Synchronous image loading for thread pool execution."""
    return Image(path=file_path)


def _is_within_base_directory(resolved_path: Path) -> bool:
    """Check if resolved path is within the allowed base directory."""
    # Get base directory dynamically to support testing
    base_dir = _get_base_directory()
    try:
        resolved_path.relative_to(base_dir)
        return True
    except ValueError:
        return False


def validate_output_dir(output_dir: str) -> Optional[str]:
    """Validate output directory is within the allowed base directory."""
    try:
        resolved = Path(output_dir).resolve()
        if not _is_within_base_directory(resolved):
            base_dir = _get_base_directory()
            logger.warning(
                f'Output dir traversal attempt blocked: {output_dir} -> {resolved}, '
                f'outside base directory {base_dir}'
            )
            return 'Access denied: output directory outside allowed directory'
        return None
    except Exception as e:
        error_msg = f'Error validating output directory {output_dir}: {str(e)}'
        logger.error(error_msg)
        return error_msg


def validate_file_path(ctx: Context, file_path: str) -> Optional[str]:
    """Validate file path for security constraints."""
    try:
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return f'File not found at {file_path}'

        # Check if it's actually a file (not a directory)
        if not path.is_file():
            return f'Path is not a file: {file_path}'

        # Check file size — read dynamically so env var changes take effect
        max_file_size = _get_max_file_size()
        file_size = path.stat().st_size
        if file_size > max_file_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = max_file_size / (1024 * 1024)
            return (
                f'File too large: {size_mb:.1f}MB (max: {max_mb:.0f}MB). '
                f'To increase the limit, set the MAX_FILE_SIZE_MB environment variable '
                f'(e.g., MAX_FILE_SIZE_MB=200).'
            )

        # Check file extension
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return f'Unsupported file type: {path.suffix}. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}'

        # Enhanced security checks - Prevent path traversal attacks
        try:
            resolved_path = path.resolve(strict=True)

            # NEW: Check if resolved path is within base directory
            if not _is_within_base_directory(resolved_path):
                base_dir = _get_base_directory()
                logger.warning(
                    f'Path traversal attempt blocked: {file_path} -> {resolved_path}, outside base directory {base_dir}'
                )
                return 'Access denied: path outside allowed directory'

        except (OSError, RuntimeError):
            return f'Invalid file path: {file_path}'

        return None  # Validation passed

    except Exception as e:
        error_msg = f'Error validating file path {file_path}: {str(e)}'
        logger.error(error_msg)
        return error_msg


async def _convert_with_markitdown(
    ctx: Context, file_path: str, file_type: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> DocumentReadResponse:
    """Helper function to convert documents to markdown using MarkItDown."""
    # Validate file path for security
    validation_error = validate_file_path(ctx, file_path)
    if validation_error:
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=validation_error
        )

    try:
        # Run conversion in thread pool with timeout
        loop = asyncio.get_event_loop()
        content = await asyncio.wait_for(
            loop.run_in_executor(None, _convert_document_sync, file_path), timeout=timeout_seconds
        )

        return DocumentReadResponse(
            status='success', content=content, file_path=file_path, error_message=None
        )

    except asyncio.TimeoutError:
        error_msg = (
            f'{file_type} conversion timed out after {timeout_seconds} seconds for {file_path}'
        )
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )
    except FileNotFoundError:
        error_msg = f'Could not find {file_type} at {file_path}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )
    except Exception as e:
        error_msg = f'Error reading {file_type} {file_path}: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )


async def _read_pdf_content(
    ctx: Context, file_path: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
) -> DocumentReadResponse:
    """Helper function to read PDF content using pdfplumber."""
    # Validate file path for security
    validation_error = validate_file_path(ctx, file_path)
    if validation_error:
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=validation_error
        )

    try:
        # Run PDF extraction in thread pool with timeout
        loop = asyncio.get_event_loop()
        text_content = await asyncio.wait_for(
            loop.run_in_executor(None, _extract_pdf_text_sync, file_path), timeout=timeout_seconds
        )

        return DocumentReadResponse(
            status='success', content=text_content, file_path=file_path, error_message=None
        )

    except asyncio.TimeoutError:
        error_msg = f'PDF processing timed out after {timeout_seconds} seconds for {file_path}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )
    except FileNotFoundError:
        error_msg = f'Could not find PDF file at {file_path}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )
    except Exception as e:
        error_msg = f'Error reading PDF file {file_path}: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return DocumentReadResponse(
            status='error', content='', file_path=file_path, error_message=error_msg
        )


@mcp.tool()
async def read_document(
    ctx: Context,
    file_path: str = Field(..., description='Path to the document file to read'),
    file_type: str = Field(
        ..., description="Type of document: 'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', or 'ppt'"
    ),
    timeout_seconds: int = Field(
        DEFAULT_TIMEOUT_SECONDS, description='Timeout in seconds (min: 5, max: 300)', ge=5, le=300
    ),
) -> DocumentReadResponse:
    """Extract content from various document formats (PDF, Word, Excel, PowerPoint)."""
    # Normalize file_type to lowercase
    file_type = file_type.lower()

    # Validate file_type parameter
    supported_types = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt'}
    if file_type not in supported_types:
        return DocumentReadResponse(
            status='error',
            content='',
            file_path=file_path,
            error_message=f'Unsupported file_type: {file_type}. Supported types: {", ".join(sorted(supported_types))}',
        )

    # Handle PDF files with pdfplumber
    if file_type == 'pdf':
        return await _read_pdf_content(ctx, file_path, timeout_seconds)

    # Handle Office documents with markitdown
    elif file_type in {'docx', 'doc'}:
        return await _convert_with_markitdown(ctx, file_path, 'Word document', timeout_seconds)
    elif file_type in {'xlsx', 'xls'}:
        return await _convert_with_markitdown(ctx, file_path, 'Excel file', timeout_seconds)
    elif file_type in {'pptx', 'ppt'}:
        return await _convert_with_markitdown(ctx, file_path, 'PowerPoint file', timeout_seconds)

    # This should never be reached due to validation above, but pyright needs explicit return
    return DocumentReadResponse(
        status='error',
        content='',
        file_path=file_path,
        error_message=f'Unsupported file_type: {file_type}. This should not happen.',
    )


@mcp.tool()
async def read_image(
    ctx: Context,
    file_path: str = Field(
        ...,
        description='Absolute path to the image file (supports PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)',
    ),
    timeout_seconds: int = Field(
        DEFAULT_TIMEOUT_SECONDS, description='Timeout in seconds (min: 5, max: 300)', ge=5, le=300
    ),
) -> Image:
    """Load an image file and return it to the LLM for viewing and analysis."""
    # Validate file path for security
    validation_error = validate_file_path(ctx, file_path)
    if validation_error:
        raise ValueError(validation_error)

    try:
        # Run image loading in thread pool with timeout
        loop = asyncio.get_event_loop()
        image = await asyncio.wait_for(
            loop.run_in_executor(None, _load_image_sync, file_path), timeout=timeout_seconds
        )
        return image

    except asyncio.TimeoutError:
        error_msg = f'Image loading timed out after {timeout_seconds} seconds for {file_path}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f'Error loading image {file_path}: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


# Known soffice paths for macOS app bundles (not on $PATH by default)
_SOFFICE_KNOWN_PATHS = [
    '/Applications/LibreOffice.app/Contents/MacOS/soffice',
    '/Applications/OpenOffice.app/Contents/MacOS/soffice',
    os.path.expanduser('~/Applications/LibreOffice.app/Contents/MacOS/soffice'),
    os.path.expanduser('~/Applications/OpenOffice.app/Contents/MacOS/soffice'),
]


def _find_soffice() -> Optional[str]:
    """Find the soffice binary.

    Checks $PATH first, then known macOS app bundle locations.
    Returns the full path to soffice, or None if not found.
    """
    path = shutil.which('soffice')
    if path:
        return path
    for known_path in _SOFFICE_KNOWN_PATHS:
        if os.path.isfile(known_path) and os.access(known_path, os.X_OK):
            return known_path
    return None


def _check_soffice_available() -> Optional[str]:
    """Check if LibreOffice/OpenOffice soffice binary is available.

    Returns None if available, or an error message string if not.
    """
    if _find_soffice() is None:
        return (
            'LibreOffice/OpenOffice (soffice) is not installed or not found. '
            'Install it to use slide image extraction:\n'
            '- Ubuntu/Debian: sudo apt install libreoffice\n'
            '- macOS: brew install --cask libreoffice\n'
            '- Windows: https://www.libreoffice.org/download/'
        )
    return None


def _convert_to_pdf_with_soffice(
    file_path: str, temp_dir: str, timeout_seconds: Optional[int] = None
) -> str:
    """Convert a PPTX file to PDF using LibreOffice/OpenOffice headless mode."""
    if timeout_seconds is None:
        timeout_seconds = _get_soffice_timeout()
    soffice_path = _find_soffice()
    if not soffice_path:
        raise RuntimeError('soffice binary not found')
    cmd = [
        soffice_path,
        '--headless',
        '--convert-to',
        'pdf',
        file_path,
        '--outdir',
        temp_dir,
    ]
    subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds
    )  # nosec B603 - fixed command with no shell=True, args are not user-controlled
    pdf_filename = Path(file_path).stem + '.pdf'
    pdf_path = os.path.join(temp_dir, pdf_filename)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f'PDF file not found after soffice conversion: {pdf_path}')
    return pdf_path


def _extract_slides_sync(
    file_path: str,
    output_dir: str,
    dpi: int = 200,
    output_format: str = 'png',
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> List[str]:
    """Synchronous slide extraction for thread pool execution.

    Converts PPTX to PDF via soffice, then PDF pages to images via pdf2image.
    For PDF input, converts pages to images directly.
    """
    suffix = Path(file_path).suffix.lower()
    temp_dir = None
    try:
        if suffix in {'.pptx', '.ppt'}:
            temp_dir = tempfile.mkdtemp(prefix='docloader_soffice_')
            pdf_path = _convert_to_pdf_with_soffice(file_path, temp_dir, timeout_seconds)
        elif suffix == '.pdf':
            pdf_path = file_path
        else:
            raise ValueError(f'Unsupported file type for slide extraction: {suffix}')

        os.makedirs(output_dir, exist_ok=True)
        pages = convert_from_path(pdf_path, dpi=dpi)
        output_files = []
        for i, page in enumerate(pages):
            output_file = os.path.join(output_dir, f'slide_{i + 1}.{output_format}')
            page.save(output_file, output_format.upper())
            output_files.append(output_file)
        return output_files
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@mcp.tool()
async def extract_slides_as_images(
    ctx: Context,
    file_path: str = Field(..., description='Path to a PPTX, PPT, or PDF file'),
    output_dir: str = Field(..., description='Directory to save extracted slide images'),
    dpi: int = Field(200, description='Image resolution in DPI (default: 200)', ge=72, le=600),
    timeout_seconds: int = Field(
        120, description='Timeout in seconds (min: 5, max: 300)', ge=5, le=300
    ),
) -> SlidesExtractionResponse:
    """Extract slides/pages as individual PNG images from PPTX, PPT, or PDF files.

    Requires LibreOffice (soffice) for PPTX/PPT conversion and poppler-utils
    (pdftoppm) for PDF-to-image rendering. Use read_image to view individual
    slide images from the output.
    """
    # Check soffice availability for presentation files
    suffix = Path(file_path).suffix.lower()
    if suffix in {'.pptx', '.ppt'}:
        soffice_error = _check_soffice_available()
        if soffice_error:
            return SlidesExtractionResponse(
                status='error',
                slide_count=0,
                file_path=file_path,
                output_dir='',
                error_message=soffice_error,
            )

    # Validate file path
    validation_error = validate_file_path(ctx, file_path)
    if validation_error:
        return SlidesExtractionResponse(
            status='error',
            slide_count=0,
            file_path=file_path,
            output_dir='',
            error_message=validation_error,
        )

    # Validate output directory against base directory
    output_dir_error = validate_output_dir(output_dir)
    if output_dir_error:
        return SlidesExtractionResponse(
            status='error',
            slide_count=0,
            file_path=file_path,
            output_dir='',
            error_message=output_dir_error,
        )

    try:
        loop = asyncio.get_event_loop()
        slide_files = await asyncio.wait_for(
            loop.run_in_executor(
                None, _extract_slides_sync, file_path, output_dir, dpi, 'png', timeout_seconds
            ),
            timeout=timeout_seconds,
        )
        return SlidesExtractionResponse(
            status='success',
            slide_images=slide_files,
            slide_count=len(slide_files),
            file_path=file_path,
            output_dir=output_dir,
            error_message=None,
        )
    except asyncio.TimeoutError:
        error_msg = f'Slide extraction timed out after {timeout_seconds} seconds for {file_path}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return SlidesExtractionResponse(
            status='error',
            slide_count=0,
            file_path=file_path,
            output_dir='',
            error_message=error_msg,
        )
    except Exception as e:
        error_msg = f'Error extracting slides from {file_path}: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return SlidesExtractionResponse(
            status='error',
            slide_count=0,
            file_path=file_path,
            output_dir='',
            error_message=error_msg,
        )


@mcp.tool()
async def inspect_document_assets(
    ctx: Context,
    file_path: str = Field(
        ..., description='Path to document file (PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS)'
    ),
    timeout_seconds: int = Field(
        30, description='Timeout in seconds (min: 5, max: 300)', ge=5, le=300
    ),
) -> InspectionResponse:
    """Inspect a document to discover embedded images and document metadata.

    Returns document-level metadata and a detailed inventory of all embedded
    images with properties like dimensions, format, DPI, and color space.
    Use asset indices from the response with extract_document_assets to
    pull specific assets out of the document.

    For Office formats (DOCX, DOC, PPTX, PPT, XLSX, XLS), requires LibreOffice
    (soffice). PDF files are processed directly with pdfplumber.
    """
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
    validation_error = validate_file_path(ctx, file_path)
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


@mcp.tool()
async def extract_document_assets(
    ctx: Context,
    file_path: str = Field(
        ..., description='Path to document file (PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS)'
    ),
    output_dir: str = Field(..., description='Directory to save extracted assets'),
    asset_indices: Optional[List[int]] = Field(
        None,
        description='Specific asset indices to extract (from inspect_document_assets). None = all.',
    ),
    timeout_seconds: int = Field(
        60, description='Timeout in seconds (min: 5, max: 300)', ge=5, le=300
    ),
) -> ExtractionResponse:
    """Extract embedded images from a document to disk.

    Use inspect_document_assets first to discover available assets and their
    indices. Pass specific indices to extract selectively, or omit to extract all.

    For Office formats, requires LibreOffice (soffice). PDF files are processed
    directly with pdfplumber.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix in {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'}:
        soffice_error = _check_soffice_available()
        if soffice_error:
            return ExtractionResponse(
                status='error',
                output_dir='',
                error_message=soffice_error,
            )

    validation_error = validate_file_path(ctx, file_path)
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


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
