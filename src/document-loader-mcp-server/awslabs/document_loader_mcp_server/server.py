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
import contextlib
import os
import pdfplumber
import secrets
import shutil
import stat
import subprocess  # nosec B404 - subprocess used with fixed command, no shell=True
import sys
import tempfile
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


# Base directory for file access security - configurable via environment.
# Secure by default: restricts file access to the current working directory.
# Set DOCUMENT_BASE_DIR to define the sandbox explicitly, e.g.
#   production: DOCUMENT_BASE_DIR="/var/app/documents"
#
# The sandbox is ALWAYS enforced. There is intentionally no implicit bypass
# based on ambient environment signals (e.g. CI, GITHUB_ACTIONS,
# PYTEST_CURRENT_TEST): those are set unconditionally by CI platforms and
# would silently disable path containment in exactly the automated,
# unattended environments where it matters most. Tests that require broader
# access set DOCUMENT_BASE_DIR explicitly (see tests/conftest.py).
def _get_base_directory() -> Path:
    """Get base directory with secure defaults.

    Honors the DOCUMENT_BASE_DIR environment variable when set; otherwise
    restricts access to the current working directory. The returned path is
    resolved so that containment checks compare canonical (symlink-free)
    paths.
    """
    env_base = os.getenv('DOCUMENT_BASE_DIR')
    if env_base:
        return Path(env_base).resolve()

    # Production default: restrict to current working directory.
    return Path.cwd().resolve()


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


class UnsafeOutputPathError(PermissionError):
    """Raised when a slide output path is not safe to write to."""


# Prefix for the temporary files slides are written to before being moved
# into place. Hidden, and distinct from the final slide_N names.
_SLIDE_TEMP_PREFIX = '.docloader_slide_'

# Windows reparse tags with this bit set are "name surrogates" (symbolic
# links, junctions/mount points): they redirect to another location. Other
# reparse points (for example cloud file placeholders) do not, and are allowed.
_REPARSE_TAG_NAME_SURROGATE = 0x20000000


def _is_link_or_reparse_point(st: os.stat_result) -> bool:
    """Return True if an lstat result is a symlink or a redirecting reparse point."""
    if stat.S_ISLNK(st.st_mode):
        return True
    attributes = getattr(st, 'st_file_attributes', 0)
    reparse_flag = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
    if attributes & reparse_flag:
        return bool(getattr(st, 'st_reparse_tag', 0) & _REPARSE_TAG_NAME_SURROGATE)
    return False


def _supports_fd_relative_writes() -> bool:
    """Return True if the OS supports no-follow, directory-relative file operations."""
    # os.replace shares its implementation with os.rename, but CPython lists only
    # os.rename in os.supports_dir_fd. Checking os.replace here would always fail.
    return (
        hasattr(os, 'O_NOFOLLOW')
        and hasattr(os, 'O_DIRECTORY')
        and {os.open, os.mkdir, os.stat, os.unlink, os.rename} <= os.supports_dir_fd
    )


def _resolve_output_dir(output_dir: str) -> tuple[Path, Path]:
    """Resolve the output directory once and re-check it is inside the base directory.

    Returns:
        A ``(base_dir, resolved_output_dir)`` tuple of resolved paths.
    """
    base_dir = _get_base_directory()
    resolved = Path(output_dir).resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        logger.warning(
            f'Output dir outside base directory blocked: {output_dir} -> {resolved}, '
            f'base directory {base_dir}'
        )
        raise UnsafeOutputPathError(
            'Access denied: output directory outside allowed directory'
        ) from None
    return base_dir, resolved


# Mode for output directories this tool creates (the umask still applies).
_OUTPUT_DIR_MODE = 0o755


def _open_output_dir_fd(base_dir: Path, resolved_dir: Path) -> int:
    """Create (if needed) and open the output directory without following links.

    Walks from the base directory one component at a time, opening each with
    O_NOFOLLOW relative to its parent's descriptor, so a component replaced by
    a symlink after validation is refused rather than followed.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_CLOEXEC', 0)
    fd = os.open(base_dir, flags)
    try:
        for part in resolved_dir.relative_to(base_dir).parts:
            with contextlib.suppress(FileExistsError):
                os.mkdir(part, _OUTPUT_DIR_MODE, dir_fd=fd)
            try:
                next_fd = os.open(part, flags | os.O_NOFOLLOW, dir_fd=fd)
            except OSError:
                st = os.stat(part, dir_fd=fd, follow_symlinks=False)
                if _is_link_or_reparse_point(st):
                    raise UnsafeOutputPathError(
                        'Access denied: output directory path contains a symbolic link'
                    ) from None
                raise
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _prepare_output_dir_path(base_dir: Path, resolved_dir: Path) -> None:
    """Portable fallback: create the output directory and verify it has no links.

    Used where directory-relative, no-follow operations are not available
    (for example Windows).
    """
    # os.makedirs applies `mode` only to the last directory, so create each one.
    current = base_dir
    for part in resolved_dir.relative_to(base_dir).parts:
        current = current / part
        with contextlib.suppress(FileExistsError):
            os.mkdir(current, _OUTPUT_DIR_MODE)
    _verify_output_dir_path(base_dir, resolved_dir)


def _verify_output_dir_path(base_dir: Path, resolved_dir: Path) -> None:
    """Portable fallback: check that no component of the output directory is a link.

    Run when the directory is prepared and again before each slide write, to
    narrow the window in which a component could be swapped. Path-based APIs
    cannot close that window fully.
    """
    current = base_dir
    for part in resolved_dir.relative_to(base_dir).parts:
        current = current / part
        if _is_link_or_reparse_point(os.lstat(current)):
            raise UnsafeOutputPathError(
                'Access denied: output directory path contains a symbolic link'
            )
    if resolved_dir.resolve(strict=True) != resolved_dir:
        raise UnsafeOutputPathError('Access denied: output directory changed during extraction')


def _check_slide_target(name: str, dir_fd: Optional[int], dir_path: Path) -> None:
    """Refuse to write a slide whose final path already exists as a link."""
    try:
        if dir_fd is not None:
            st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        else:
            st = os.lstat(dir_path / name)
    except FileNotFoundError:
        return
    if _is_link_or_reparse_point(st):
        raise UnsafeOutputPathError(
            f'Access denied: {name} in output directory is a symbolic link'
        )


def _write_slide(
    page,
    name: str,
    image_format: str,
    dir_fd: Optional[int],
    dir_path: Path,
    base_dir: Optional[Path] = None,
):
    """Write one slide image safely.

    The image is saved to a new, exclusively created temporary file in the
    output directory and then atomically moved onto the final name. A link
    placed at the final name after the check is replaced, not followed.
    """
    if dir_fd is None and base_dir is not None:
        _verify_output_dir_path(base_dir, dir_path)
    _check_slide_target(name, dir_fd, dir_path)
    temp_name = f'{_SLIDE_TEMP_PREFIX}{secrets.token_hex(8)}.tmp'
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, 'O_NOFOLLOW', 0)
        | getattr(os, 'O_CLOEXEC', 0)
        | getattr(os, 'O_BINARY', 0)
    )
    if dir_fd is not None:
        fd = os.open(temp_name, flags, 0o666, dir_fd=dir_fd)
    else:
        fd = os.open(dir_path / temp_name, flags, 0o666)
    try:
        with os.fdopen(fd, 'wb') as temp_file:
            page.save(temp_file, image_format)
        if dir_fd is not None:
            os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        else:
            if base_dir is not None:
                _verify_output_dir_path(base_dir, dir_path)
            os.replace(dir_path / temp_name, dir_path / name)
    except BaseException:
        with contextlib.suppress(OSError):
            if dir_fd is not None:
                os.unlink(temp_name, dir_fd=dir_fd)
            else:
                os.unlink(dir_path / temp_name)
        raise


def _remove_slides(
    names: List[str], dir_fd: Optional[int], dir_path: Path, base_dir: Path
) -> None:
    """Best-effort removal of slides written by a failed extraction."""
    if dir_fd is None:
        try:
            _verify_output_dir_path(base_dir, dir_path)
        except OSError:
            return
    for name in names:
        with contextlib.suppress(OSError):
            if dir_fd is not None:
                os.unlink(name, dir_fd=dir_fd)
            else:
                os.unlink(dir_path / name)


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

    Slides are written only inside the resolved output directory, which must
    be inside the base directory. Existing symlinks at slide paths are refused.
    """
    suffix = Path(file_path).suffix.lower()
    temp_dir = None
    dir_fd = None
    try:
        if suffix in {'.pptx', '.ppt'}:
            temp_dir = tempfile.mkdtemp(prefix='docloader_soffice_')
            pdf_path = _convert_to_pdf_with_soffice(file_path, temp_dir, timeout_seconds)
        elif suffix == '.pdf':
            pdf_path = file_path
        else:
            raise ValueError(f'Unsupported file type for slide extraction: {suffix}')

        base_dir, resolved_dir = _resolve_output_dir(output_dir)
        if _supports_fd_relative_writes():
            dir_fd = _open_output_dir_fd(base_dir, resolved_dir)
        else:
            _prepare_output_dir_path(base_dir, resolved_dir)

        pages = convert_from_path(pdf_path, dpi=dpi)
        names = [f'slide_{i + 1}.{output_format}' for i in range(len(pages))]
        # Check every target before writing any, so a refused link does not
        # leave a partial set of slides behind.
        for name in names:
            _check_slide_target(name, dir_fd, resolved_dir)

        written = []
        try:
            for page, name in zip(pages, names):
                _write_slide(page, name, output_format.upper(), dir_fd, resolved_dir, base_dir)
                written.append(name)
        except BaseException:
            # An error response reports no slides, so remove the ones this call wrote.
            _remove_slides(written, dir_fd, resolved_dir, base_dir)
            raise
        return [os.path.join(output_dir, name) for name in written]
    finally:
        if dir_fd is not None:
            os.close(dir_fd)
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
    except UnsafeOutputPathError as e:
        error_msg = str(e)
        logger.warning(f'Slide extraction refused for {output_dir}: {error_msg}')
        await ctx.error(error_msg)
        return SlidesExtractionResponse(
            status='error',
            slide_count=0,
            file_path=file_path,
            output_dir='',
            error_message=error_msg,
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


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
