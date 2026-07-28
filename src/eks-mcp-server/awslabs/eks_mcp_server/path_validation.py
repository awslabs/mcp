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

"""Path validation to prevent path traversal and writes to sensitive directories."""

import os


_HOME = os.path.realpath(os.path.expanduser('~'))

BLOCKED_DIRS: tuple[str, ...] = (
    os.path.join(_HOME, '.aws'),
    os.path.join(_HOME, '.ssh'),
    os.path.join(_HOME, '.kube'),
    os.path.join(_HOME, '.gnupg'),
    os.path.join(_HOME, '.docker'),
    '/etc',
    '/root',
)


def _in_blocked_dir(resolved: str) -> bool:
    for d in BLOCKED_DIRS:
        if resolved == d or resolved.startswith(d + os.sep):
            return True
    return False


def validate_file_path(path: str) -> str:
    """Validate a user-supplied file path for read or write operations.

    Checks:
    - Path must be absolute.
    - Resolved path must not fall within a sensitive directory.

    Returns the resolved absolute path.
    Raises ValueError on any policy violation.
    """
    if not os.path.isabs(path):
        raise ValueError(f'Path must be absolute: {path}')

    resolved = os.path.realpath(path)

    if _in_blocked_dir(resolved):
        raise ValueError(f'Path points to a sensitive directory: {path}')

    return resolved


def validate_directory_path(path: str) -> str:
    """Validate a user-supplied directory path for write operations.

    Checks:
    - Path must be absolute.
    - Resolved path must not fall within a sensitive directory.

    Returns the resolved absolute path.
    Raises ValueError on any policy violation.
    """
    if not os.path.isabs(path):
        raise ValueError(f'Path must be absolute: {path}')

    resolved = os.path.realpath(path)

    if _in_blocked_dir(resolved):
        raise ValueError(f'Path points to a sensitive directory: {path}')

    return resolved
