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

"""Smoke tests for AWS SDK output URI prefix mode support.

These are low-iteration smoke tests (not property tests) that verify the
external AWS SDK behavior required by this feature:

- The installed boto3 / botocore versions meet the minimum that introduced the
  ``outputUriPrefixMode`` field, and pyproject.toml declares that minimum.
- A real ``omics`` boto3 client's StartRun input shape accepts
  ``outputUriPrefixMode`` with the values the tool validates against, and the
  GetRun output shape returns it (no network calls are made; the fields are
  verified against the client's service model).
"""

import boto3
import botocore
import pathlib
import re
from awslabs.aws_healthomics_mcp_server.consts import OUTPUT_URI_PREFIX_MODES
from packaging.version import Version


# Minimum SDK version whose omics model includes outputUriPrefixMode on StartRun and GetRun.
MINIMUM_SDK_VERSION = Version('1.43.123')

# Repo root is the parent of the tests/ directory.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / 'pyproject.toml'


def test_installed_boto3_version_meets_minimum():
    """The installed boto3 version is >= 1.43.123."""
    assert Version(boto3.__version__) >= MINIMUM_SDK_VERSION, (
        f'Installed boto3 {boto3.__version__} is below the required minimum {MINIMUM_SDK_VERSION}'
    )


def test_installed_botocore_version_meets_minimum():
    """The installed botocore version is >= 1.43.123."""
    assert Version(botocore.__version__) >= MINIMUM_SDK_VERSION, (
        f'Installed botocore {botocore.__version__} is below the required '
        f'minimum {MINIMUM_SDK_VERSION}'
    )


def _declared_minimum(package):
    """Return the declared minimum Version for a package from pyproject.toml."""
    text = PYPROJECT_PATH.read_text(encoding='utf-8')
    match = re.search(rf'["\']{package}\s*>=\s*([0-9][0-9A-Za-z.\-]*)["\']', text)
    if match:
        return Version(match.group(1))
    return None


def test_pyproject_declares_boto3_minimum():
    """pyproject.toml declares a boto3 minimum of at least 1.43.123."""
    declared = _declared_minimum('boto3')

    assert declared is not None, 'boto3 dependency constraint not found in pyproject.toml'
    assert declared >= MINIMUM_SDK_VERSION, (
        f'pyproject.toml declares boto3>={declared}, below required {MINIMUM_SDK_VERSION}'
    )


def test_pyproject_declares_botocore_minimum():
    """pyproject.toml declares an explicit botocore minimum of at least 1.43.123."""
    declared = _declared_minimum('botocore')

    assert declared is not None, 'botocore dependency constraint not found in pyproject.toml'
    assert declared >= MINIMUM_SDK_VERSION, (
        f'pyproject.toml declares botocore>={declared}, below required {MINIMUM_SDK_VERSION}'
    )


def _omics_operation_model(operation_name):
    """Return the omics operation model (no network calls)."""
    client = boto3.client('omics', region_name='us-east-1')
    return client.meta.service_model.operation_model(operation_name)


def test_start_run_accepts_output_uri_prefix_mode():
    """StartRun accepts outputUriPrefixMode, and its enum matches the tool's allowed values."""
    members = _omics_operation_model('StartRun').input_shape.members
    assert 'outputUriPrefixMode' in members, (
        'StartRun input shape does not declare outputUriPrefixMode; '
        'the installed SDK does not support output URI prefix mode'
    )
    assert sorted(members['outputUriPrefixMode'].enum) == sorted(OUTPUT_URI_PREFIX_MODES)


def test_get_run_returns_output_uri_prefix_mode():
    """The GetRun output shape declares outputUriPrefixMode."""
    members = _omics_operation_model('GetRun').output_shape.members
    assert 'outputUriPrefixMode' in members, (
        'GetRun output shape does not declare outputUriPrefixMode; '
        'the installed SDK does not support output URI prefix mode'
    )
