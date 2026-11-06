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

"""Process-wide switch for server-local file paths named in tool arguments.

Some tools accept a path on the server host for input (workflow files, ZIP
bundles, README files) or output (``output_path``). That is only safe when the
caller is the local user who launched the server, which is the ``stdio``
transport. Over a network transport the caller is remote, so tool arguments
must never select a server-local path to read or write.

Local file access is disabled until :func:`configure_local_file_access` enables
it at startup for ``stdio``. Code that imports and calls the tools directly
therefore cannot reach the local filesystem by accident.
"""

import os
import re
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_TRANSPORT,
    ERROR_LOCAL_FILE_ACCESS_DISABLED,
)
from loguru import logger
from typing import Optional


# File suffixes that make a whitespace-free relative string a path attempt
# (for example ``main.wdl`` or ``docs/README.md``) when local access is disabled.
_LOCAL_PATH_SUFFIXES = ('.md', '.wdl', '.nf', '.cwl', '.zip', '.json', '.yml', '.yaml')

# Characters allowed in such a relative path attempt. Whitespace, newlines, ``:``
# and other punctuation keep the value inline content.
_RELATIVE_PATH_PATTERN = re.compile(r'[A-Za-z0-9._~/\\-]+')

# Fail closed: disabled until server startup enables it for stdio.
_local_file_access_allowed = False


class LocalFileAccessDisabledError(ValueError):
    """Raised when a tool argument names a local path and local access is disabled.

    Subclasses ``ValueError`` so the existing tool error handling reports it as a
    normal tool failure.
    """

    def __init__(self) -> None:
        """Create the error with a fixed message that does not echo the path."""
        super().__init__(ERROR_LOCAL_FILE_ACCESS_DISABLED)


def configure_local_file_access(transport: str) -> None:
    """Allow local file paths in tool arguments only for the ``stdio`` transport.

    Must be called at startup before any transport serves a request.

    Args:
        transport: The resolved transport mode.
    """
    global _local_file_access_allowed
    _local_file_access_allowed = transport == DEFAULT_TRANSPORT
    state = 'enabled' if _local_file_access_allowed else 'disabled'
    logger.info(f'Local file paths in tool arguments: {state} (transport={transport})')


def is_local_file_access_allowed() -> bool:
    """Return whether tool arguments may name server-local file paths."""
    return _local_file_access_allowed


def require_local_file_access() -> None:
    """Raise unless tool arguments may name server-local file paths.

    Raises:
        LocalFileAccessDisabledError: If local file access is disabled.
    """
    if not _local_file_access_allowed:
        raise LocalFileAccessDisabledError()


def require_local_output_access(output_path: Optional[str]) -> None:
    """Raise if ``output_path`` names a local destination and local access is disabled.

    Tools call this before any other work so a network caller's local
    ``output_path`` fails without reading inputs or calling AWS. ``None``,
    non-string defaults, and ``s3://`` destinations are always allowed.

    Args:
        output_path: The caller-supplied output destination, or ``None``.

    Raises:
        LocalFileAccessDisabledError: If ``output_path`` is local and local file
            access is disabled.
    """
    if isinstance(output_path, str) and not output_path.startswith('s3://'):
        require_local_file_access()


def looks_like_local_path(value: str) -> bool:
    """Return whether a string is plainly a local path attempt.

    A pure string check that never touches the filesystem. Used when local access
    is disabled so a path attempt is rejected with a clear error instead of being
    treated as inline content. Only single-line values qualify:

    - an absolute path, such as ``/etc/passwd``; or
    - a relative path with no whitespace that ends in a known workflow file
      suffix, such as ``main.wdl`` or ``docs/README.md``.

    Multi-line workflow text and base64 content (which never contains ``.``)
    stay inline.

    Args:
        value: The caller-supplied string (already known not to be ``s3://``).

    Returns:
        ``True`` if the value should be rejected as a local path.
    """
    if not value or '\n' in value or '\r' in value:
        return False
    if os.path.isabs(value):
        return True
    if not _RELATIVE_PATH_PATTERN.fullmatch(value):
        return False
    name = value.replace('\\', '/').rsplit('/', 1)[-1].lower()
    return any(
        name.endswith(suffix) and len(name) > len(suffix) for suffix in _LOCAL_PATH_SUFFIXES
    )
