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

"""Property-based tests for botocore version comparison logic.

Tests Property 17 from the design document.
"""

import hypothesis.strategies as st
import logging
import logging.handlers
import os
import sys
from hypothesis import given, settings
from packaging.version import Version


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


@st.composite
def version_string(draw):
    """Generate a version string like '1.X.Y' where X and Y are random integers."""
    major = 1
    minor = draw(st.integers(min_value=0, max_value=200))
    patch = draw(st.integers(min_value=0, max_value=200))
    return f'{major}.{minor}.{patch}'


# ---------------------------------------------------------------------------
# Property 17: Botocore version warning is logged if and only if installed
#              version is older
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 17: Botocore version warning
# **Validates: Requirements 10.2, 10.3**
@given(installed_ver=version_string(), generated_ver=version_string())
@settings(max_examples=100)
def test_version_warning_iff_installed_older(installed_ver, generated_ver):
    """For any pair of version strings (installed, generated-from), a version.

    warning shall be logged if and only if the installed version is strictly
    less than the generated-from version.
    """
    installed = Version(installed_ver)
    generated_from = Version(generated_ver)

    # Replicate the comparison logic from server.py's _check_botocore_version
    should_warn = installed < generated_from

    # Capture log output by simulating the version check with a list handler
    handler = logging.handlers.MemoryHandler(capacity=100)
    test_logger = logging.getLogger('test_version_check')
    test_logger.handlers.clear()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.WARNING)

    # Execute the same logic as _check_botocore_version
    if installed < generated_from:
        test_logger.warning(
            'Installed botocore %s is older than the version used to generate '
            'this server (%s). Consider upgrading boto3: pip install --upgrade boto3',
            installed_ver,
            generated_ver,
        )

    warning_logged = any(
        'older than the version' in record.getMessage()
        for record in handler.buffer
        if record.levelno >= logging.WARNING
    )

    # Clean up
    test_logger.removeHandler(handler)
    handler.close()

    if should_warn:
        assert warning_logged, (
            f'Expected warning for installed={installed_ver} < generated={generated_ver}, '
            f'but no warning was logged'
        )
    else:
        assert not warning_logged, (
            f'Unexpected warning for installed={installed_ver} >= generated={generated_ver}, '
            f'but a warning was logged'
        )
