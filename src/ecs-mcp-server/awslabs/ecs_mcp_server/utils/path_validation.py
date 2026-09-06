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

"""
Path validation for user-supplied filesystem paths.

User-supplied paths reach directory creation, file writes, and Docker build
contexts in this server. A path such as ``~/.aws`` contains no traversal
sequences, so pattern matching on the raw string does not stop it; the path has
to be resolved and then compared against the locations it must never touch.

Every path is therefore resolved with ``os.path.realpath`` -- which expands
``..`` components and follows symlinks -- and rejected when the result either
sits inside a sensitive directory or contains one. This mirrors the equivalent
protection in the EKS MCP Server.
"""

import os
import sys
from typing import Optional, Tuple

# Directories inside a user's home that hold credentials or client configuration.
_SENSITIVE_HOME_DIRS: Tuple[str, ...] = (".aws", ".ssh", ".kube", ".gnupg", ".docker")

# System directories that hold host configuration and service state.
_SENSITIVE_SYSTEM_DIRS: Tuple[str, ...] = ("/etc", "/root", "/var/lib")


def _home_dirs() -> Tuple[str, ...]:
    """
    Collects every directory that may be the current user's home.

    ``os.path.expanduser`` trusts ``$HOME``, so a process started with ``$HOME``
    unset or pointing elsewhere would otherwise build the blocklist around the
    wrong directory. The account's home directory from the password database is
    consulted as a second, environment-independent source.

    Returns:
        Tuple[str, ...]: The candidate home directories, without duplicates.
    """
    homes = [os.path.expanduser("~")]

    try:
        import pwd

        homes.append(pwd.getpwuid(os.getuid()).pw_dir)
    except (ImportError, AttributeError, KeyError, OSError):
        # pwd and os.getuid are POSIX-only, and the account may not be listed in
        # the password database. $HOME remains the source in that case.
        pass

    return tuple(dict.fromkeys(home for home in homes if home))


def _resolve_blocked_dirs() -> Tuple[str, ...]:
    """
    Builds the list of directories that user-supplied paths may never touch.

    Each entry is resolved with ``os.path.realpath`` so that platforms which
    expose these locations through symlinks (for example macOS, where ``/var``
    links to ``/private/var``) are compared on their real paths.

    Returns:
        Tuple[str, ...]: The resolved sensitive directories, without duplicates.
    """
    candidates = [
        os.path.join(home, sensitive_dir)
        for home in _home_dirs()
        for sensitive_dir in _SENSITIVE_HOME_DIRS
    ]
    candidates.extend(_SENSITIVE_SYSTEM_DIRS)
    return tuple(dict.fromkeys(os.path.realpath(candidate) for candidate in candidates))


BLOCKED_DIRS: Tuple[str, ...] = _resolve_blocked_dirs()

# macOS and Windows filesystems are case-insensitive by default, so "~/.AWS" and
# "~/.aws" name the same directory there. os.path.normcase only folds case on
# Windows, so fold explicitly on macOS as well to close that bypass.
_CASE_INSENSITIVE_FS: bool = sys.platform in ("darwin", "win32")


def _normalize(path: str) -> str:
    """
    Normalizes a path for comparison against the blocklist.

    Args:
        path: The path to normalize

    Returns:
        str: The path in a form that can be compared on this platform
    """
    normalized = os.path.normcase(path)
    return normalized.casefold() if _CASE_INSENSITIVE_FS else normalized


def _find_blocked_dir(resolved_path: str) -> Optional[str]:
    """
    Finds the sensitive directory that makes a resolved path unusable.

    A path is unusable when it is inside a sensitive directory (``~/.aws`` and
    ``~/.aws/credentials`` both expose credentials) or when it contains one
    (``/`` and ``$HOME`` both pull ``~/.aws`` into a Docker build context).

    Args:
        resolved_path: An already resolved absolute path

    Returns:
        Optional[str]: The offending sensitive directory, or None if the path is
        unrelated to every sensitive directory
    """
    candidate = _normalize(resolved_path)
    for blocked in BLOCKED_DIRS:
        normalized_blocked = _normalize(blocked)
        if candidate == normalized_blocked:
            return blocked
        # Inside a sensitive directory.
        if candidate.startswith(normalized_blocked + os.sep):
            return blocked
        # An ancestor of a sensitive directory, which would pull it along.
        if normalized_blocked.startswith(candidate.rstrip(os.sep) + os.sep):
            return blocked
    return None


def validate_path(path: str, must_exist: bool = False) -> str:
    """
    Validates a user-supplied filesystem path.

    Relative paths are accepted and resolved against the current working
    directory, and a leading ``~`` is expanded. Resolution runs through
    ``os.path.realpath``, so neither ``..`` components nor symlinks can be used
    to reach a sensitive directory.

    Args:
        path: The path to validate. May be absolute or relative.
        must_exist: Whether the resolved path is required to exist already.

    Returns:
        str: The resolved absolute path.

    Raises:
        ValueError: If the path is not a non-empty string, is related to a
            sensitive directory, or does not exist while ``must_exist`` is set.
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path must be a non-empty string")

    resolved_path = os.path.realpath(os.path.expanduser(path))

    # Checked before existence so that a sensitive path which does not exist yet
    # is reported as sensitive rather than as merely missing.
    blocked_dir = _find_blocked_dir(resolved_path)
    if blocked_dir is not None:
        raise ValueError(
            f"Path '{path}' resolves to '{resolved_path}', which is not usable "
            f"because it would expose the sensitive directory '{blocked_dir}'"
        )

    if must_exist and not os.path.exists(resolved_path):
        raise ValueError(f"Path '{path}' does not exist")

    return resolved_path
