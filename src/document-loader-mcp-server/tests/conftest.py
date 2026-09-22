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
"""Shared pytest fixtures for document-loader-mcp-server tests."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def broad_base_directory():
    """Grant tests broad filesystem access explicitly.

    Production code restricts file access to ``DOCUMENT_BASE_DIR`` (default:
    the current working directory) and has no implicit CI/test bypass. Many
    tests read fixtures from temporary directories outside the working
    directory, so they opt into broad access here — explicitly, in test code
    only — by setting ``DOCUMENT_BASE_DIR`` to the filesystem root.

    This replaces the previous behavior where the server itself widened the
    sandbox to ``/`` whenever ambient ``CI`` / ``GITHUB_ACTIONS`` /
    ``PYTEST_CURRENT_TEST`` variables were present (a path-containment bypass).

    Individual tests may override ``DOCUMENT_BASE_DIR`` (via ``patch.dict``)
    or mock ``_get_base_directory`` to assert containment behavior; those
    overrides take precedence within the test.
    """
    with patch.dict(os.environ, {'DOCUMENT_BASE_DIR': '/'}):
        yield
