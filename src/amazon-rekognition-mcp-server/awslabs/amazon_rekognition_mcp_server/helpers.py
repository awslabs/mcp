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

"""Helper functions for the Amazon Rekognition MCP Server."""

import boto3
import functools
import os
from loguru import logger
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, cast


T = TypeVar('T', bound=Callable[..., Awaitable[Any]])


def get_base_dir() -> Optional[str]:
    """Get the base directory from environment variables.

    Returns:
        The base directory path if set, None otherwise.
    """
    return os.environ.get('BASE_DIR')


def get_aws_session():
    """Create an AWS session using credentials from environment variables."""
    profile_name = os.environ.get('AWS_PROFILE')
    region = os.environ.get('AWS_REGION', 'us-east-1')

    if profile_name:
        logger.debug(f'Using AWS profile: {profile_name}')
        return boto3.Session(profile_name=profile_name, region_name=region)
    else:
        logger.debug('Using default AWS credential chain')
        return boto3.Session(region_name=region)


def get_rekognition_client():
    """Get a Rekognition client."""
    session = get_aws_session()
    return session.client('rekognition')


def handle_exceptions(func: T) -> T:
    """Decorator to handle exceptions in a consistent way."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {e}')
            raise ValueError(f'Error in {func.__name__}: {str(e)}')

    return cast(T, wrapper)


def sanitize_path(file_path: str, base_dir: Optional[str] = None) -> Path:
    """Sanitize and validate a file path to prevent path traversal attacks.

    Args:
        file_path: The input file path to sanitize
        base_dir: Optional base directory to restrict paths to

    Returns:
        Path: A sanitized Path object

    Raises:
        ValueError: If the path is invalid or attempts to traverse outside base_dir
    """
    # Convert to absolute path if base_dir is provided
    if base_dir:
        base_path = Path(base_dir).resolve()
        try:
            # Resolve the path relative to base_dir
            full_path = (base_path / file_path).resolve()
            # Check if the resolved path is still within base_dir
            if not str(full_path).startswith(str(base_path)):
                raise ValueError(f'Path {file_path} attempts to traverse outside base directory')
            return full_path
        except Exception as e:
            raise ValueError(f'Invalid path: {str(e)}')

    # If no base_dir, just sanitize the path
    try:
        return Path(file_path).resolve()
    except Exception as e:
        raise ValueError(f'Invalid path: {str(e)}')


def get_image_bytes(image_path: str) -> Dict[str, bytes]:
    """Get image bytes from a local file.

    Args:
        image_path: Path to the image file.

    Returns:
        Dict with 'Bytes' key containing the image bytes.

    Raises:
        ValueError: If the image file does not exist or cannot be read.
    """
    path = sanitize_path(image_path, get_base_dir())
    if not path.exists():
        raise ValueError(f'Image file not found: {image_path}')

    try:
        with open(path, 'rb') as image_file:
            return {'Bytes': image_file.read()}
    except Exception as e:
        raise ValueError(f'Error reading image file: {str(e)}')
