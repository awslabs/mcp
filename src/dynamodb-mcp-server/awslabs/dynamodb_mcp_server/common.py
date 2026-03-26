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

import logging
import os
import re
from functools import wraps
from typing import Callable


logger = logging.getLogger(__name__)


def validate_source_identifier(source_identifier: str) -> None:
    """Validate source identifier (database name or schema/owner name).

    Args:
        source_identifier: The database name or schema/owner name to validate

    Raises:
        ValueError: If the identifier contains invalid characters or exceeds length limit
    """
    # Max identifier length: SQL Server=128, MySQL=64, PostgreSQL=63
    # Use 128 as upper bound; each database will enforce its own limit
    MAX_DB_NAME_LENGTH = 128

    if len(source_identifier) > MAX_DB_NAME_LENGTH:
        raise ValueError(
            f'Invalid database name: {source_identifier}. '
            f'Database name must not exceed {MAX_DB_NAME_LENGTH} characters.'
        )

    if not re.match(r'^[a-zA-Z0-9_.$-]+$', source_identifier):
        raise ValueError(
            f'Invalid database name: {source_identifier}. '
            'Only alphanumeric characters, underscores, periods, dollar signs, and hyphens are allowed.'
        )


def validate_path_within_directory(
    file_path: str, base_dir: str, path_description: str = 'file path'
) -> str:
    """Validate that a resolved path is within the base directory.

    Args:
        file_path: The file path to validate (can be relative or absolute)
        base_dir: The base directory that the file must be within
        path_description: Description of the path for error messages (e.g., "query output file")

    Returns:
        The canonical absolute path if validation succeeds

    Raises:
        ValueError: If the path resolves outside the base directory
    """
    real_base = os.path.normpath(os.path.realpath(base_dir))
    real_file = os.path.normpath(os.path.realpath(file_path))

    if not (real_file.startswith(real_base + os.sep) or real_file == real_base):
        raise ValueError(
            f'Path traversal detected: {path_description} resolves outside {base_dir}'
        )

    return real_file


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions in DynamoDB operations.

    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that handles exceptions
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception('Error in %s', func.__name__)
            return {'error': str(e)}

    return wrapper
