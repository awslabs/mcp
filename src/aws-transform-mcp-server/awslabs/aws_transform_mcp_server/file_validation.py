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

"""Path validation to prevent credential exfiltration via file uploads."""

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
        '.docker/config.json',
    }
)

# Directory prefixes (resolved) that must never be read from.
_HOME = os.path.realpath(os.path.expanduser('~'))
BLOCKED_READ_DIRS: tuple[str, ...] = (
    os.path.join(_HOME, '.aws'),
    os.path.join(_HOME, '.ssh'),
    os.path.join(_HOME, '.gnupg'),
    os.path.join(_HOME, '.docker'),
    os.path.join(_HOME, '.aws-transform-mcp'),
    '/etc/shadow',
    '/etc/passwd',
)


def _is_blocked_name(path: str) -> bool:
    return os.path.basename(path).lower() in BLOCKED_FILENAMES


def _in_blocked_dir(resolved: str) -> bool:
    for d in BLOCKED_READ_DIRS:
        if resolved == d or resolved.startswith(d + os.sep):
            return True
    return False


def validate_read_path(file_path: str) -> str:
    """Validate a file path before reading for upload.

    Returns the resolved absolute path.
    Raises ValueError on any policy violation.
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))

    if _in_blocked_dir(resolved):
        logger.warning('[security] Blocked read from sensitive directory: {}', file_path)
        raise ValueError(f'Reading from sensitive directory is not allowed: {file_path}')

    if _is_blocked_name(resolved):
        logger.warning('[security] Blocked read of sensitive file: {}', os.path.basename(resolved))
        raise ValueError(f'Blocked filename: {os.path.basename(resolved)} cannot be uploaded.')

    return resolved
