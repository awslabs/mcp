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

import os
from .config import (
    ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS,
    ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS_KEY,
    WORKING_DIRECTORY,
)
from awscli.paramfile import get_file
from pathlib import Path


def get_file_validated(prefix, path, mode):
    """Validate that a URI path (i.e. file://<path>) is within the allowed working directory."""
    file_path = os.path.expandvars(os.path.expanduser(path[len(prefix) :]))
    validate_file_path(file_path)

    return get_file(prefix, path, mode)


def validate_file_path(file_path: str) -> str:
    """Validate that a file path is within the allowed working directory.

    Args:
        file_path: The file path to validate

    Returns:
        The validated absolute path

    Raises:
        ValueError: If the path is outside the working directory and unrestricted access is not allowed
    """
    if ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS:
        return file_path

    # Convert to absolute path
    absolute_path = os.path.abspath(file_path)
    working_directory = os.path.abspath(WORKING_DIRECTORY)

    # Check if the path is within the working directory
    try:
        Path(absolute_path).resolve().relative_to(Path(working_directory).resolve())
    except ValueError:
        raise ValueError(
            f"File path '{file_path}' is outside the allowed working directory '{WORKING_DIRECTORY}'. "
            f'Set {ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS_KEY}=true to allow unrestricted file access.'
        )

    return absolute_path
