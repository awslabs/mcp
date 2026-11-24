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

"""Path validation to prevent path traversal and writes to sensitive directories.

This is a best-effort guard against accidental misuse, such as a model
mistakenly targeting ``~/.aws``. It is not an access control: every path comes
from the tool call, so it cannot stop a model that has been steered. Restrict
what the server can reach by how it is run (omit ``--allow-write``, scope its
credentials, keep tool approval on in the MCP host, or run it in a sandbox).
"""

import os
import sys


_HOME = os.path.realpath(os.path.expanduser('~'))

# Every entry is resolved with os.path.realpath so it compares equal to the
# resolved path under test. On macOS, /etc is a symlink to /private/etc.
BLOCKED_DIRS: tuple[str, ...] = tuple(
    dict.fromkeys(
        os.path.realpath(d)
        for d in (
            os.path.join(_HOME, '.aws'),
            os.path.join(_HOME, '.ssh'),
            os.path.join(_HOME, '.kube'),
            os.path.join(_HOME, '.gnupg'),
            os.path.join(_HOME, '.docker'),
            '/etc',
            '/root',
        )
    )
)

# macOS and Windows file systems are case-insensitive by default, so "~/.AWS"
# and "~/.aws" name the same directory there. os.path.normcase only folds case
# on Windows, so fold explicitly on macOS as well.
_CASE_INSENSITIVE_FS: bool = sys.platform in ('darwin', 'win32')


def _normalize(path: str) -> str:
    normalized = os.path.normcase(path)
    return normalized.casefold() if _CASE_INSENSITIVE_FS else normalized


def _in_blocked_dir(resolved: str) -> bool:
    candidate = _normalize(resolved)
    for d in BLOCKED_DIRS:
        blocked = _normalize(d)
        if candidate == blocked or candidate.startswith(blocked + os.sep):
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
