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
import re
import stat
import tempfile


AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DEPLOYMENT_STATUS_DIR = os.path.join(
    tempfile.gettempdir(), 'aws-serverless-mcp-server-deployments'
)

# Project names are used to build filesystem paths for deployment-status files.
# Restrict them to an allowlist so they cannot contain path
# separators or traversal sequences. This eliminates both the relative ('../')
# and absolute ('/etc/...') traversal variants at the input layer.
# 128 is the CloudFormation stack name length limit. CloudFormation is stricter on
# characters (leading letter, no underscores); this pattern only blocks unsafe paths.
PROJECT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,128}$')


class InvalidProjectNameError(ValueError):
    """Raised when a project name fails ``PROJECT_NAME_PATTERN``."""


def check_deployment_status_dir() -> None:
    """Refuse a status directory that another user could have created or can write to.

    The directory has a fixed name under the shared temp directory, so another
    local user could create it first and plant files or symlinks in it. Requiring
    a real directory owned by the current user, with no group or other write
    access, means nobody else can change its contents between a path check and
    the later open(). Group or other write access on a directory we own (e.g.
    created by an earlier version under a 002 umask) is removed rather than
    rejected. The ownership and permission checks apply on POSIX only; they are
    skipped or have no effect where ``os.geteuid`` is unavailable (Windows). A
    missing directory passes; callers create it with mode 0o700.

    Raises:
        ValueError: if the directory is a symlink, not a directory, or owned by
            another user.
    """
    try:
        st = os.lstat(DEPLOYMENT_STATUS_DIR)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(st.st_mode):
        raise ValueError(f'Deployment status directory {DEPLOYMENT_STATUS_DIR!r} is a symlink.')
    if not stat.S_ISDIR(st.st_mode):
        raise ValueError(
            f'Deployment status directory {DEPLOYMENT_STATUS_DIR!r} is not a directory.'
        )
    if hasattr(os, 'geteuid') and st.st_uid != os.geteuid():
        raise ValueError(
            f'Deployment status directory {DEPLOYMENT_STATUS_DIR!r} is owned by another user.'
        )
    if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        os.chmod(DEPLOYMENT_STATUS_DIR, stat.S_IMODE(st.st_mode) & ~(stat.S_IWGRP | stat.S_IWOTH))


def get_deployment_status_file_path(project_name: str) -> str:
    """Return the validated path to a project's deployment-status JSON file.

    Validates ``project_name`` against ``PROJECT_NAME_PATTERN`` and enforces
    that the fully resolved path stays inside ``DEPLOYMENT_STATUS_DIR``. The
    realpath containment check is defense-in-depth: it also rejects a symlink
    that already exists in the status directory and points outside it. Symlinks
    created later are prevented only by ``check_deployment_status_dir`` (POSIX).

    Args:
        project_name: Caller-supplied project identifier.

    Returns:
        Absolute, symlink-resolved path to ``<project_name>.json`` inside
        ``DEPLOYMENT_STATUS_DIR``.

    Raises:
        InvalidProjectNameError: if ``project_name`` fails the allowlist.
        ValueError: if the status
            directory fails ``check_deployment_status_dir``, or the resolved
            path escapes ``DEPLOYMENT_STATUS_DIR``.
    """
    if not isinstance(project_name, str) or not PROJECT_NAME_PATTERN.fullmatch(project_name):
        raise InvalidProjectNameError(
            f'Invalid project name: {project_name!r}. Project names may contain only '
            'letters, digits, hyphens, and underscores, up to 128 characters.'
        )

    check_deployment_status_dir()

    base_dir = os.path.realpath(DEPLOYMENT_STATUS_DIR)
    file_path = os.path.realpath(os.path.join(base_dir, f'{project_name}.json'))

    # commonpath compares whole path components, so '/base-other' is not
    # treated as inside '/base'.
    try:
        contained = os.path.commonpath([base_dir, file_path]) == base_dir
    except ValueError:
        # Raised when paths are on different drives (Windows); treat as escape.
        contained = False
    if not contained:
        raise ValueError(
            f'Resolved path for project {project_name!r} escapes the deployment status directory.'
        )
    return file_path
