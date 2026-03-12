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

"""Shared path validation and local file write utilities.

Consolidates path validation logic extracted from content_resolver.py
so it can be reused by both content resolution and timeline output features.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple


def validate_local_path(path: str) -> None:
    """Validate that a local file path does not contain path traversal sequences.

    Extracted from content_resolver._validate_local_path to be shared across modules.
    Checks for '..' as a path component using both forward-slash and OS-native separators.

    Args:
        path: The file path to validate.

    Raises:
        ValueError: If the path contains traversal sequences.
    """
    if path.startswith('../') or '/../' in path or path == '..' or path.endswith('/..'):
        raise ValueError(f'Path contains traversal sequences: {path}')
    # Also check OS-native separators for cross-platform safety
    parts = os.path.normpath(path).split(os.sep)
    if '..' in parts:
        raise ValueError(f'Path contains traversal sequences: {path}')


def validate_s3_uri_format(uri: str) -> Tuple[str, str]:
    """Validate S3 URI format and return parsed bucket and key.

    Extracted from content_resolver._validate_s3_uri_format to be shared across modules.
    Uses parse_s3_path and is_valid_bucket_name from s3_utils.py.

    Args:
        uri: The S3 URI to validate (e.g. 's3://bucket/key').

    Returns:
        Tuple of (bucket_name, key).

    Raises:
        ValueError: If the URI format is invalid or bucket name is invalid.
    """
    from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
        is_valid_bucket_name,
        parse_s3_path,
    )

    try:
        bucket, key = parse_s3_path(uri)
    except ValueError:
        raise ValueError(f'Invalid S3 URI format: {uri}')

    if not is_valid_bucket_name(bucket):
        raise ValueError(f'Invalid S3 URI format: {uri}')

    return bucket, key


def sanitize_local_path(path: str) -> str:
    """Validate and resolve a local file path for safe writing.

    Builds on validate_local_path and adds:
    - Null byte detection
    - Resolution to absolute canonical form via Path.resolve()
    - Post-resolution traversal check

    Args:
        path: The user-supplied file path.

    Returns:
        The resolved absolute path as a string.

    Raises:
        ValueError: If the path fails any security check.
    """
    if '\x00' in path:
        raise ValueError('Path contains null bytes')

    validate_local_path(path)

    resolved = str(Path(path).resolve())

    return resolved


def write_svg_to_local(svg_content: str, path: str) -> str:
    """Sanitize path, ensure no overwrite, create parents, and write SVG.

    Args:
        svg_content: The SVG string to write.
        path: The user-supplied local file path.

    Returns:
        The resolved absolute path where the file was written.

    Raises:
        ValueError: If path sanitization fails.
        FileExistsError: If a file already exists at the path.
        OSError: If the write fails (permissions, disk full, etc.).
    """
    resolved = sanitize_local_path(path)
    resolved_path = Path(resolved)

    if resolved_path.exists():
        raise FileExistsError(f'File already exists: {resolved}')

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(svg_content, encoding='utf-8')

    return resolved


def write_zip_to_local(zip_data: bytes, path: str) -> str:
    """Sanitize path, ensure no overwrite, create parents, and write ZIP.

    Args:
        zip_data: The raw ZIP bytes to write.
        path: The user-supplied local file path.

    Returns:
        The resolved absolute path where the file was written.

    Raises:
        ValueError: If path sanitization fails.
        FileExistsError: If a file already exists at the path.
        OSError: If the write fails (permissions, disk full, etc.).
    """
    resolved = sanitize_local_path(path)
    resolved_path = Path(resolved)

    if resolved_path.exists():
        raise FileExistsError(f'File already exists: {resolved}')

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_bytes(zip_data)

    return resolved
