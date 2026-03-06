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
import sys
from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.utilities.types import Image
from loguru import logger
from markitdown import MarkItDown
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server with a unique name to avoid old tool registry
mcp = FastMCP('Document Loader')


# Security Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit


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

        # Check file size
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f'File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)'

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


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
