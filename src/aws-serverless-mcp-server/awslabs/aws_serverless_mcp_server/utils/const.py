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
import tempfile


AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
DEPLOYMENT_STATUS_DIR = os.path.join(
    tempfile.gettempdir(), 'aws-serverless-mcp-server-deployments'
)

# Project names are used to build filesystem paths for deployment-status files.
# Restrict them to an allowlist so they cannot contain path
# separators or traversal sequences. This eliminates both the relative ('../')
# and absolute ('/etc/...') traversal variants at the input layer.
PROJECT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')


def get_deployment_status_file_path(project_name: str) -> str:
    """Return the validated path to a project's deployment-status JSON file.

    Validates ``project_name`` against ``PROJECT_NAME_PATTERN`` and enforces
    that the fully resolved path stays inside ``DEPLOYMENT_STATUS_DIR``. The
    realpath containment check is defense-in-depth: it also blocks escapes via
    symlinks placed inside the status directory, which the allowlist alone
    cannot catch.

    Args:
        project_name: Caller-supplied project identifier.

    Returns:
        Absolute, symlink-resolved path to ``<project_name>.json`` inside
        ``DEPLOYMENT_STATUS_DIR``.

    Raises:
        ValueError: if ``project_name`` fails the allowlist or the resolved
            path escapes ``DEPLOYMENT_STATUS_DIR``.
    """
    if not isinstance(project_name, str) or not PROJECT_NAME_PATTERN.match(project_name):
        raise ValueError(
            f'Invalid project name: {project_name!r}. Project names may contain only '
            'letters, digits, hyphens, and underscores.'
        )

    base_dir = os.path.realpath(DEPLOYMENT_STATUS_DIR)
    file_path = os.path.realpath(os.path.join(base_dir, f'{project_name}.json'))

    # commonpath is drive/separator aware and avoids the prefix-collision bug of
    # a naive startswith check (e.g. '/base' vs '/base-evil').
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
