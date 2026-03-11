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
"""PDF asset inspection and extraction engine using pdfplumber."""

import asyncio
import io
import os
import pdfplumber
from awslabs.document_loader_mcp_server.extractors import (
    AssetInfo,
    DocumentMetadata,
    ExtractedAsset,
    ExtractionResponse,
    InspectionResponse,
    _get_max_assets,
)
from concurrent.futures import ThreadPoolExecutor
from PIL import Image as PILImage
from typing import List, Optional, Tuple


# PDF filter to output format mapping
FILTER_FORMAT_MAP = {
    'DCTDecode': ('jpeg', '.jpg'),
    'JPXDecode': ('jp2', '.jp2'),
    'CCITTFaxDecode': ('tiff', '.tiff'),
    'JBIG2Decode': ('png', '.png'),
}
DEFAULT_FORMAT = ('png', '.png')


def _resolve_filter_name(filt) -> str:
    """Extract filter name from PSLiteral, bytes, or string.

    Args:
        filt: Filter value from PDF stream attributes (may be PSLiteral, bytes, str, or list).

    Returns:
        Filter name as string (e.g., 'DCTDecode', 'FlateDecode').
    """
    # Handle list of filters (use the last one)
    if isinstance(filt, list):
        filt = filt[-1] if filt else ''

    # Handle PSLiteral objects (have .name attribute)
    if hasattr(filt, 'name'):
        name = getattr(filt, 'name')
        return name.decode('utf-8') if isinstance(name, bytes) else str(name)

    # Handle raw bytes
    if isinstance(filt, bytes):
        return filt.decode('utf-8')

    # Handle string
    return str(filt)


def _get_image_format(image_obj) -> Tuple[str, str]:
    """Map PDF filter to output image format.

    Args:
        image_obj: Image object from pdfplumber with stream attribute.

    Returns:
        Tuple of (format_name, extension) e.g., ('jpeg', '.jpg').
    """
    stream = image_obj.get('stream')
    if not stream:
        return DEFAULT_FORMAT

    # Get filter from stream attributes (no leading slash in dict keys)
    filt = stream.attrs.get('Filter')
    if not filt:
        return DEFAULT_FORMAT

    filter_name = _resolve_filter_name(filt)
    return FILTER_FORMAT_MAP.get(filter_name, DEFAULT_FORMAT)


def _get_stream_dimensions(image_obj) -> Tuple[Optional[int], Optional[int]]:
    """Get width and height from PDF stream attributes.

    Args:
        image_obj: Image object from pdfplumber.

    Returns:
        Tuple of (width, height) or (None, None) if not found.
    """
    stream = image_obj.get('stream')
    if not stream:
        return (None, None)

    width = stream.attrs.get('Width')
    height = stream.attrs.get('Height')
    return (width, height)


def _get_stream_color_mode(image_obj) -> str:
    """Determine Pillow color mode from PDF ColorSpace.

    Args:
        image_obj: Image object from pdfplumber.

    Returns:
        Pillow mode string: 'RGB', 'L', 'CMYK', or 'RGB' as fallback.
    """
    stream = image_obj.get('stream')
    if not stream:
        return 'RGB'

    color_space = stream.attrs.get('ColorSpace')
    if not color_space:
        return 'RGB'

    # Resolve color space name
    if hasattr(color_space, 'name'):
        cs_name = color_space.name
        cs_name = cs_name.decode('utf-8') if isinstance(cs_name, bytes) else str(cs_name)
    elif isinstance(color_space, bytes):
        cs_name = color_space.decode('utf-8')
    elif isinstance(color_space, list) and len(color_space) > 0:
        # Handle array color spaces like [/Indexed /DeviceRGB ...]
        first = color_space[0]
        if hasattr(first, 'name'):
            cs_name = (
                first.name.decode('utf-8') if isinstance(first.name, bytes) else str(first.name)
            )
        else:
            cs_name = str(first)
    else:
        cs_name = str(color_space)

    # Map to Pillow modes
    if 'Gray' in cs_name or 'DeviceGray' in cs_name:
        return 'L'
    elif 'CMYK' in cs_name or 'DeviceCMYK' in cs_name:
        return 'CMYK'
    else:
        return 'RGB'


def _get_image_bytes(image_obj) -> Optional[bytes]:
    """Extract raw bytes from image stream.

    Args:
        image_obj: Image object from pdfplumber.

    Returns:
        Raw image bytes or None if extraction fails.
    """
    stream = image_obj.get('stream')
    if not stream:
        return None

    try:
        return stream.get_data()
    except Exception:
        return None


def _is_raw_pixel_data(image_obj) -> bool:
    """Check if image uses raw pixel data (FlateDecode) vs encoded format.

    Args:
        image_obj: Image object from pdfplumber.

    Returns:
        True if raw pixel data, False if encoded (JPEG, JP2, etc.).
    """
    stream = image_obj.get('stream')
    if not stream:
        return True

    filt = stream.attrs.get('Filter')
    if not filt:
        return True

    filter_name = _resolve_filter_name(filt)
    # DCTDecode and JPXDecode are already-encoded formats
    return filter_name not in ('DCTDecode', 'JPXDecode')


def _introspect_image(
    raw_bytes: bytes, fmt: str, image_obj
) -> Tuple[Optional[int], Optional[int], Optional[Tuple[int, int]], Optional[str]]:
    """Get image dimensions, DPI, and color space using Pillow.

    Args:
        raw_bytes: Raw image bytes.
        fmt: Format name ('jpeg', 'png', etc.).
        image_obj: Original PDF image object for fallback dimensions.

    Returns:
        Tuple of (width, height, dpi, color_space).
    """
    width, height, dpi, color_space = None, None, None, None

    try:
        # Try to open as already-encoded image
        img = PILImage.open(io.BytesIO(raw_bytes))
        width = img.width
        height = img.height
        dpi = img.info.get('dpi')
        color_space = img.mode
        if color_space == 'L':
            color_space = 'Grayscale'
        elif color_space in ('RGB', 'CMYK'):
            color_space = color_space
        else:
            color_space = img.mode
    except Exception:
        # Fall back to frombytes for raw pixel data
        try:
            stream_width, stream_height = _get_stream_dimensions(image_obj)
            if stream_width and stream_height:
                mode = _get_stream_color_mode(image_obj)
                img = PILImage.frombytes(mode, (stream_width, stream_height), raw_bytes)
                width = img.width
                height = img.height
                color_space = img.mode
                if color_space == 'L':
                    color_space = 'Grayscale'
        except Exception:
            # Last resort: use stream dimensions
            stream_width, stream_height = _get_stream_dimensions(image_obj)
            width = stream_width
            height = stream_height

    return (width, height, dpi, color_space)


def _inspect_pdf_sync(file_path: str) -> InspectionResponse:
    """Synchronous PDF inspection implementation.

    Args:
        file_path: Path to PDF file.

    Returns:
        InspectionResponse with discovered assets and metadata.
    """
    # Check file exists
    if not os.path.exists(file_path):
        return InspectionResponse(
            status='error',
            error_message=f'File not found: {file_path}',
            asset_count=0,
            total_assets_found=0,
        )

    max_assets = _get_max_assets()
    assets = []
    warnings = []
    total_assets_found = 0
    global_asset_index = 0

    try:
        # Get file metadata
        file_size = os.path.getsize(file_path)

        # Open PDF with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            # Extract document metadata
            pdf_metadata = pdf.metadata or {}
            title = pdf_metadata.get('Title') or pdf_metadata.get('/Title')
            author = pdf_metadata.get('Author') or pdf_metadata.get('/Author')
            created = pdf_metadata.get('CreationDate') or pdf_metadata.get('/CreationDate')
            modified = pdf_metadata.get('ModDate') or pdf_metadata.get('/ModDate')

            # Convert PDF dates from D:YYYYMMDDHHMMSS format to ISO 8601
            if created and isinstance(created, str) and created.startswith('D:'):
                created = created[2:16]  # Extract YYYYMMDDHHMMSS
                if len(created) >= 8:
                    created = f'{created[:4]}-{created[4:6]}-{created[6:8]}T{created[8:10]}:{created[10:12]}:{created[12:14]}Z'
            if modified and isinstance(modified, str) and modified.startswith('D:'):
                modified = modified[2:16]
                if len(modified) >= 8:
                    modified = f'{modified[:4]}-{modified[4:6]}-{modified[6:8]}T{modified[8:10]}:{modified[10:12]}:{modified[12:14]}Z'

            metadata = DocumentMetadata(
                file_path=file_path,
                file_type='pdf',
                file_size_bytes=file_size,
                title=title,
                author=author,
                created=created if created else None,
                modified=modified if modified else None,
                page_count=len(pdf.pages),
            )

            # Iterate through pages and extract images
            for page_num, page in enumerate(pdf.pages, start=1):
                if global_asset_index >= max_assets:
                    warnings.append(
                        f'Reached MAX_ASSETS limit of {max_assets}. Remaining images not inspected.'
                    )
                    break

                page_images = page.images
                for img_obj in page_images:
                    total_assets_found += 1

                    if global_asset_index >= max_assets:
                        continue

                    try:
                        # Get format and extension
                        fmt, ext = _get_image_format(img_obj)

                        # Get raw bytes
                        raw_bytes = _get_image_bytes(img_obj)
                        if not raw_bytes:
                            warnings.append(
                                f'Page {page_num}: Could not extract bytes for image {global_asset_index}'
                            )
                            continue

                        # Introspect image
                        width, height, dpi, color_space = _introspect_image(
                            raw_bytes, fmt, img_obj
                        )

                        # Get compression filter name
                        stream = img_obj.get('stream')
                        compression = None
                        if stream:
                            filt = stream.attrs.get('Filter')
                            if filt:
                                compression = _resolve_filter_name(filt)

                        # Build asset info
                        asset = AssetInfo(
                            index=global_asset_index,
                            name=f'image_{global_asset_index:03d}{ext}',
                            format=fmt,
                            size_bytes=len(raw_bytes),
                            width_px=width,
                            height_px=height,
                            dpi=dpi,
                            color_space=color_space,
                            compression=compression,
                            location=f'Page {page_num}',
                        )
                        assets.append(asset)
                        global_asset_index += 1

                    except Exception as e:
                        warnings.append(f'Page {page_num}: Failed to inspect image - {str(e)}')

        # Determine status
        status = 'success'
        if total_assets_found > len(assets):
            status = 'partial'

        return InspectionResponse(
            status=status,
            metadata=metadata,
            assets=assets,
            asset_count=len(assets),
            total_assets_found=total_assets_found,
            warnings=warnings,
        )

    except Exception as e:
        return InspectionResponse(
            status='error',
            error_message=f'Failed to inspect PDF: {str(e)}',
            asset_count=0,
            total_assets_found=0,
        )


async def inspect_pdf(file_path: str, timeout_seconds: int = 120) -> InspectionResponse:
    """Inspect PDF file for embedded images.

    Args:
        file_path: Path to PDF file.
        timeout_seconds: Maximum time to wait for inspection (default: 120).

    Returns:
        InspectionResponse with discovered assets and metadata.
    """
    loop = asyncio.get_running_loop()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, _inspect_pdf_sync, file_path),
                timeout=timeout_seconds,
            )
            return result
    except asyncio.TimeoutError:
        return InspectionResponse(
            status='error',
            error_message=f'PDF inspection timed out after {timeout_seconds} seconds',
            asset_count=0,
            total_assets_found=0,
        )
    except Exception as e:
        return InspectionResponse(
            status='error',
            error_message=f'Unexpected error during PDF inspection: {str(e)}',
            asset_count=0,
            total_assets_found=0,
        )


def _save_image_bytes(raw_bytes, fmt, output_path, image_obj):
    """Save image bytes to disk. Handles both encoded and raw pixel data."""
    save_fmt_map = {'jpeg': 'JPEG', 'png': 'PNG', 'tiff': 'TIFF', 'jp2': 'JPEG2000'}

    if not _is_raw_pixel_data(image_obj):
        # Encoded image (JPEG, JP2) -- write directly or via Pillow
        if fmt == 'jpeg':
            with open(output_path, 'wb') as f:
                f.write(raw_bytes)
            return
        try:
            img = PILImage.open(io.BytesIO(raw_bytes))
            img.save(output_path, format=save_fmt_map.get(fmt, 'PNG'))
            return
        except Exception:  # nosec B110 - Intentional fallthrough to try alternative extraction method
            pass  # Fall through to raw pixel reconstruction

    # Raw pixel data -- reconstruct with frombytes
    stream_w, stream_h = _get_stream_dimensions(image_obj)
    if stream_w and stream_h:
        mode = _get_stream_color_mode(image_obj)
        try:
            img = PILImage.frombytes(mode, (stream_w, stream_h), raw_bytes)
            img.save(output_path, format='PNG')
            return
        except Exception:  # nosec B110 - Intentional fallthrough to try last-resort extraction
            pass

    # Last resort
    try:
        img = PILImage.open(io.BytesIO(raw_bytes))
        img.save(output_path, format='PNG')
    except Exception as e:
        raise ValueError(f'Cannot decode image data: {str(e)}') from e


def _extract_pdf_sync(
    file_path: str, output_dir: str, asset_indices: Optional[List[int]]
) -> ExtractionResponse:
    """Synchronous PDF extraction implementation.

    Args:
        file_path: Path to PDF file.
        output_dir: Directory to save extracted assets.
        asset_indices: List of asset indices to extract, or None for all.

    Returns:
        ExtractionResponse with per-asset extraction results.
    """
    # Check file exists
    if not os.path.exists(file_path):
        return ExtractionResponse(
            status='error',
            error_message=f'File not found: {file_path}',
            output_dir=output_dir,
        )

    # Check for empty list (explicit no extraction)
    if asset_indices is not None and len(asset_indices) == 0:
        return ExtractionResponse(
            status='error',
            error_message='No asset indices specified',
            output_dir=output_dir,
        )

    # Discover all images (same iteration as inspect)
    all_images = []
    max_assets = _get_max_assets()

    try:
        with pdfplumber.open(file_path) as pdf:
            global_asset_index = 0
            for page in pdf.pages:
                if global_asset_index >= max_assets:
                    break

                page_images = page.images
                for img_obj in page_images:
                    if global_asset_index >= max_assets:
                        break

                    all_images.append((global_asset_index, img_obj))
                    global_asset_index += 1

        # Determine which indices to extract
        if asset_indices is None:
            # Extract all
            indices_to_extract = list(range(len(all_images)))
            if len(indices_to_extract) > max_assets:
                return ExtractionResponse(
                    status='error',
                    error_message=f'Too many assets. Limit is {max_assets}.',
                    output_dir=output_dir,
                )
        else:
            indices_to_extract = asset_indices

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Extract each requested image
        extracted_assets = []
        success_count = 0
        fail_count = 0

        for idx in indices_to_extract:
            # Check if index is valid
            if idx < 0 or idx >= len(all_images):
                extracted_assets.append(
                    ExtractedAsset(
                        index=idx,
                        output_path='',
                        status='error',
                        error_message=f'Invalid index {idx}. Valid range: 0-{len(all_images) - 1}',
                    )
                )
                fail_count += 1
                continue

            # Get image object
            _, img_obj = all_images[idx]

            try:
                # Get format and extension
                fmt, ext = _get_image_format(img_obj)

                # Get raw bytes
                raw_bytes = _get_image_bytes(img_obj)
                if not raw_bytes:
                    extracted_assets.append(
                        ExtractedAsset(
                            index=idx,
                            output_path='',
                            status='error',
                            error_message='Could not extract image bytes',
                        )
                    )
                    fail_count += 1
                    continue

                # Build output path
                output_path = os.path.join(output_dir, f'image_{idx:03d}{ext}')

                # Save image
                _save_image_bytes(raw_bytes, fmt, output_path, img_obj)

                extracted_assets.append(
                    ExtractedAsset(index=idx, output_path=output_path, status='success')
                )
                success_count += 1

            except Exception as e:
                extracted_assets.append(
                    ExtractedAsset(
                        index=idx,
                        output_path='',
                        status='error',
                        error_message=str(e),
                    )
                )
                fail_count += 1

        # Determine overall status
        if fail_count == 0:
            status = 'success'
        elif success_count == 0:
            status = 'error'
        else:
            status = 'partial'

        return ExtractionResponse(
            status=status,
            extracted=extracted_assets,
            extracted_count=success_count,
            failed_count=fail_count,
            output_dir=output_dir,
        )

    except Exception as e:
        return ExtractionResponse(
            status='error',
            error_message=f'Failed to extract PDF assets: {str(e)}',
            output_dir=output_dir,
        )


async def extract_pdf(
    file_path: str,
    output_dir: str,
    asset_indices: Optional[List[int]] = None,
    timeout_seconds: int = 60,
) -> ExtractionResponse:
    """Extract assets from PDF file.

    Args:
        file_path: Path to PDF file.
        output_dir: Directory to save extracted assets.
        asset_indices: List of asset indices to extract, or None for all.
        timeout_seconds: Maximum time to wait for extraction (default: 60).

    Returns:
        ExtractionResponse with per-asset extraction results.
    """
    loop = asyncio.get_running_loop()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor, _extract_pdf_sync, file_path, output_dir, asset_indices
                ),
                timeout=timeout_seconds,
            )
            return result
    except asyncio.TimeoutError:
        return ExtractionResponse(
            status='error',
            error_message=f'PDF extraction timed out after {timeout_seconds} seconds',
            output_dir=output_dir,
        )
    except Exception as e:
        return ExtractionResponse(
            status='error',
            error_message=f'Unexpected error during PDF extraction: {str(e)}',
            output_dir=output_dir,
        )
