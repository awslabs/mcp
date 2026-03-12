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

"""Content resolution utility for detecting and resolving file paths, S3 URIs, and inline content."""

from __future__ import annotations

import base64
import io
import os
import zipfile
from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
    validate_local_path,
    validate_s3_uri_format,
)
from botocore.exceptions import ClientError
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from typing import Dict, Optional, Union


class ContentInputType(str, Enum):
    """Enumeration of content input types for content resolution."""

    S3_URI = 's3_uri'
    LOCAL_FILE = 'local_file'
    INLINE_CONTENT = 'inline_content'


@dataclass
class ResolvedContent:
    """Result of resolving a single content input.

    Holds the resolved content along with metadata about how the input
    was classified and the original source string for logging and error messages.
    """

    content: Union[str, bytes]
    input_type: ContentInputType
    source: str


@dataclass
class ResolvedBundle:
    """Result of resolving a bundle input (directory, ZIP, or S3 prefix).

    Holds a mapping of relative file paths to their text content, along with
    metadata about how the input was classified and the original source string.
    """

    files: Dict[str, str]
    input_type: ContentInputType
    source: str


def _check_size_limit(size: int, max_size_bytes: int, source: str) -> None:
    """Check that content size does not exceed the configured maximum.

    Args:
        size: The actual content size in bytes.
        max_size_bytes: The maximum allowed size in bytes.
        source: The original source string for error messages.

    Raises:
        ValueError: If size exceeds max_size_bytes.
    """
    if size > max_size_bytes:
        size_mb = size / (1024 * 1024)
        limit_mb = max_size_bytes / (1024 * 1024)
        raise ValueError(
            f'Content exceeds maximum size limit ({size_mb:.1f}MB > {limit_mb:.1f}MB): {source}'
        )


def detect_content_input_type(value: str) -> ContentInputType:
    """Detect the type of content input.

    Detection order:
    1. If starts with 's3://' -> S3_URI
    2. If path passes security checks and exists on filesystem -> LOCAL_FILE
    3. Otherwise -> INLINE_CONTENT

    Args:
        value: The input string to classify.

    Returns:
        The detected ContentInputType.
    """
    # 1. S3 URI check
    if value.startswith('s3://'):
        return ContentInputType.S3_URI

    # 2. Local file/directory check (with path traversal guard)
    try:
        validate_local_path(value)
        if os.path.isfile(value) or os.path.isdir(value):
            return ContentInputType.LOCAL_FILE
    except ValueError:
        logger.debug(f'Path traversal detected, treating as inline content: {value}')

    # 3. Inline content fallback
    return ContentInputType.INLINE_CONTENT


def _read_local_file(path: str, mode: str, max_size_bytes: Optional[int]) -> Union[str, bytes]:
    """Read content from a local file with security and size checks.

    Args:
        path: The local file path to read.
        mode: 'text' for UTF-8 string or 'binary' for raw bytes.
        max_size_bytes: Maximum allowed file size in bytes, or None to skip.

    Returns:
        File content as str (text mode) or bytes (binary mode).

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permissions.
        ValueError: If path traversal is detected or size limit exceeded.
    """
    validate_local_path(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f'File not found: {path}')

    if not os.path.isfile(path):
        raise ValueError(f'Path is not a regular file: {path}')

    if not os.access(path, os.R_OK):
        raise PermissionError(f'Permission denied reading file: {path}')

    file_size = os.path.getsize(path)
    if max_size_bytes is not None:
        _check_size_limit(file_size, max_size_bytes, path)

    if mode == 'text':
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        with open(path, 'rb') as f:
            return f.read()


def _read_s3_object(uri: str, mode: str, max_size_bytes: Optional[int]) -> Union[str, bytes]:
    """Read content from an S3 object with validation and size checks.

    Args:
        uri: The S3 URI to read (e.g. 's3://bucket/key').
        mode: 'text' for UTF-8 string or 'binary' for raw bytes.
        max_size_bytes: Maximum allowed content size in bytes, or None to skip.

    Returns:
        Object content as str (text mode) or bytes (binary mode).

    Raises:
        ValueError: If URI format is invalid, object not found, or access denied.
    """
    bucket, key = validate_s3_uri_format(uri)

    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session

    session = get_aws_session()
    s3_client = session.client('s3')

    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        content_length = response['ContentLength']
        if max_size_bytes is not None:
            _check_size_limit(content_length, max_size_bytes, uri)

        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read()

        if mode == 'text':
            return data.decode('utf-8')
        return data
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchKey':
            raise ValueError(f'S3 object not found: {uri}')
        elif error_code == '403' or error_code == 'AccessDenied':
            raise ValueError(f'Access denied to S3 object: {uri}')
        raise


async def resolve_single_content(
    value: str,
    mode: str = 'text',
    max_size_bytes: Optional[int] = None,
) -> ResolvedContent:
    """Resolve a single content input to its content.

    Detects the input type and dispatches to the appropriate reader.
    For inline content in text mode, returns the value as-is.
    For inline content in binary mode, base64-decodes the value.

    Args:
        value: The input string (local path, S3 URI, or inline content).
        mode: 'text' for UTF-8 string or 'binary' for raw bytes.
        max_size_bytes: Maximum allowed size in bytes, or None for default.

    Returns:
        ResolvedContent with the resolved content and metadata.
    """
    from awslabs.aws_healthomics_mcp_server.consts import (
        DEFAULT_CONTENT_RESOLVER_MAX_FILE_SIZE_MB,
    )

    if max_size_bytes is None:
        max_size_bytes = DEFAULT_CONTENT_RESOLVER_MAX_FILE_SIZE_MB * 1024 * 1024

    input_type = detect_content_input_type(value)
    source = value[:100] if input_type == ContentInputType.INLINE_CONTENT else value
    logger.info(f'Resolving content: type={input_type.value}, source={source}')

    if input_type == ContentInputType.LOCAL_FILE:
        content = _read_local_file(value, mode, max_size_bytes)
    elif input_type == ContentInputType.S3_URI:
        content = _read_s3_object(value, mode, max_size_bytes)
    else:
        # Inline content
        if mode == 'binary':
            content = base64.b64decode(value)
        else:
            content = value

    return ResolvedContent(
        content=content,
        input_type=input_type,
        source=value,
    )


def _read_local_directory(path: str, max_size_bytes: Optional[int]) -> Dict[str, str]:
    """Read all files from a local directory recursively as UTF-8 text.

    Args:
        path: The local directory path to read.
        max_size_bytes: Maximum allowed total size in bytes, or None to skip.

    Returns:
        Dictionary of {relative_path: text_content}.

    Raises:
        FileNotFoundError: If the directory does not exist.
        ValueError: If path traversal is detected or size limit exceeded.
    """
    validate_local_path(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f'File not found: {path}')

    if not os.path.isdir(path):
        raise ValueError(f'Path is not a directory: {path}')

    files: Dict[str, str] = {}
    total_size = 0

    for root, _dirs, filenames in os.walk(path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, path)

            file_size = os.path.getsize(full_path)
            total_size += file_size
            if max_size_bytes is not None:
                _check_size_limit(total_size, max_size_bytes, path)

            with open(full_path, 'r', encoding='utf-8') as f:
                files[rel_path] = f.read()

    return files


def _read_s3_prefix(uri: str, max_size_bytes: Optional[int]) -> Dict[str, str]:
    """List and download all objects under an S3 prefix as UTF-8 text.

    Args:
        uri: The S3 URI prefix (e.g. 's3://bucket/prefix/').
        max_size_bytes: Maximum allowed total size in bytes, or None to skip.

    Returns:
        Dictionary of {relative_key: text_content}.

    Raises:
        ValueError: If URI format is invalid or access denied.
    """
    bucket, prefix = validate_s3_uri_format(uri)

    from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session

    session = get_aws_session()
    s3_client = session.client('s3')

    files: Dict[str, str] = {}
    total_size = 0

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Skip the prefix itself (directory marker)
                if key == prefix:
                    continue

                obj_size = obj.get('Size', 0)
                total_size += obj_size
                if max_size_bytes is not None:
                    _check_size_limit(total_size, max_size_bytes, uri)

                response = s3_client.get_object(Bucket=bucket, Key=key)
                data = response['Body'].read()
                rel_key = key[len(prefix) :] if key.startswith(prefix) else key
                files[rel_key] = data.decode('utf-8')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '403' or error_code == 'AccessDenied':
            raise ValueError(f'Access denied to S3 prefix: {uri}')
        raise

    return files


def _extract_zip_contents(data: bytes) -> Dict[str, str]:
    """Extract ZIP bytes into a dictionary of {filename: text_content}.

    Args:
        data: The raw ZIP file bytes.

    Returns:
        Dictionary of {filename: text_content}.

    Raises:
        ValueError: If ZIP extraction fails or content cannot be decoded as UTF-8.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files: Dict[str, str] = {}
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue
                try:
                    files[info.filename] = zf.read(info.filename).decode('utf-8')
                except UnicodeDecodeError:
                    raise ValueError(f'Failed to decode content as UTF-8: {info.filename}')
            return files
    except zipfile.BadZipFile as e:
        raise ValueError(f'Failed to extract ZIP content: {e}')


async def resolve_bundle_content(
    value: Union[str, Dict[str, str]],
    max_size_bytes: Optional[int] = None,
) -> ResolvedBundle:
    """Resolve a bundle input to a dictionary of {relative_path: text_content}.

    Handles dict passthrough (backward compatible), local directories,
    local ZIP files, S3 prefixes, and S3 ZIP objects.

    Args:
        value: The input (local path, S3 URI, or dict of file contents).
        max_size_bytes: Maximum allowed total size in bytes, or None for default.

    Returns:
        ResolvedBundle with the resolved files and metadata.
    """
    from awslabs.aws_healthomics_mcp_server.consts import (
        DEFAULT_CONTENT_RESOLVER_MAX_FILE_SIZE_MB,
    )

    if max_size_bytes is None:
        max_size_bytes = DEFAULT_CONTENT_RESOLVER_MAX_FILE_SIZE_MB * 1024 * 1024

    # Dict passthrough (backward compatible)
    if isinstance(value, dict):
        logger.info('Resolving bundle: type=dict_passthrough')
        return ResolvedBundle(
            files=value,
            input_type=ContentInputType.INLINE_CONTENT,
            source='<dict>',
        )

    input_type = detect_content_input_type(value)
    logger.info(f'Resolving bundle: type={input_type.value}, source={value}')

    if input_type == ContentInputType.LOCAL_FILE:
        if value.lower().endswith('.zip'):
            # Local ZIP file
            data = _read_local_file(value, 'binary', max_size_bytes)
            files = _extract_zip_contents(data)  # type: ignore[arg-type]
        else:
            # Local directory
            files = _read_local_directory(value, max_size_bytes)
    elif input_type == ContentInputType.S3_URI:
        if value.lower().endswith('.zip'):
            # S3 ZIP object
            data = _read_s3_object(value, 'binary', max_size_bytes)
            files = _extract_zip_contents(data)  # type: ignore[arg-type]
        elif value.endswith('/'):
            # S3 prefix
            files = _read_s3_prefix(value, max_size_bytes)
        else:
            # Treat as S3 prefix by appending /
            files = _read_s3_prefix(value + '/', max_size_bytes)
    else:
        # Inline content — not meaningful for bundles, but handle gracefully
        raise ValueError(
            'Cannot resolve bundle from inline content. '
            'Provide a directory path, ZIP file path, S3 prefix, or dict.'
        )

    return ResolvedBundle(
        files=files,
        input_type=input_type,
        source=value,
    )
