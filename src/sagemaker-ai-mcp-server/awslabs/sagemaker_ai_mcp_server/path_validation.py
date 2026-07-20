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

"""Path validation to prevent reading sensitive files."""

import os
from loguru import logger


# File basenames that must never be read.
BLOCKED_FILENAMES: frozenset[str] = frozenset(
    {
        '.env',
        '.netrc',
        '.pgpass',
        '.bashrc',
        '.bash_profile',
        '.zshrc',
        '.profile',
        '.npmrc',
        '.pypirc',
        '.gitconfig',
        '.git-credentials',
        'authorized_keys',
        'known_hosts',
        'id_rsa',
        'id_rsa.pub',
        'id_ed25519',
        'id_ed25519.pub',
        'id_ecdsa',
        'id_ecdsa.pub',
        'credentials',
        'config.json',
    }
)

# Directory prefixes (resolved) that must never be read from.
_HOME = os.path.realpath(os.path.expanduser('~'))
BLOCKED_READ_DIRS: tuple[str, ...] = (
    os.path.join(_HOME, '.aws'),
    os.path.join(_HOME, '.ssh'),
    os.path.join(_HOME, '.gnupg'),
    os.path.join(_HOME, '.docker'),
    '/proc',
)

# Exact file paths that must never be read.
BLOCKED_READ_FILES: tuple[str, ...] = (
    os.path.realpath('/etc/shadow'),
    os.path.realpath('/etc/passwd'),
)


def validate_file_read_path(file_path: str) -> str:
    """Validate a file path before reading.

    Ensures the path is absolute, resolves symlinks and traversals,
    and blocks access to sensitive directories and filenames.

    Args:
        file_path: The path to validate.

    Returns:
        The resolved absolute path.

    Raises:
        ValueError: If the path violates any security policy.
    """
    if not os.path.isabs(file_path):
        raise ValueError(f'Path must be absolute, got relative path: {file_path}')

    resolved = os.path.realpath(os.path.expanduser(file_path))

    # Check blocked directories
    for blocked_dir in BLOCKED_READ_DIRS:
        if resolved == blocked_dir or resolved.startswith(blocked_dir + os.sep):
            logger.warning('[security] Blocked read from sensitive directory: {}', file_path)
            raise ValueError(f'Reading from sensitive directory is not allowed: {file_path}')

    # Check blocked exact file paths
    for blocked_file in BLOCKED_READ_FILES:
        if resolved == blocked_file:
            logger.warning('[security] Blocked read of sensitive system file: {}', file_path)
            raise ValueError(f'Reading sensitive system file is not allowed: {file_path}')

    # Check blocked filenames
    basename = os.path.basename(resolved).lower()
    if basename in BLOCKED_FILENAMES:
        logger.warning('[security] Blocked read of sensitive file: {}', basename)
        raise ValueError(f'Reading sensitive file is not allowed: {basename}')

    return resolved
