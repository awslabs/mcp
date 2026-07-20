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

"""Integration / smoke tests for AWS SDK scratch storage mode support.

These are low-iteration smoke tests (not property tests) that verify the
external AWS SDK behavior required by this feature:

- The installed boto3 / botocore versions meet the minimum that introduced the
  ``scratchStorageMode`` parameter, and pyproject.toml declares that minimum.
- A real ``omics`` boto3 client's StartRun and StartRunBatch operation models
  accept ``scratchStorageMode`` (no network calls are made; the parameter is
  verified against the client's input shape model).

Validates: Requirements Minimum AWS SDK version
"""

import boto3
import botocore
import pathlib
import re
from packaging.version import Version


# Minimum SDK version that introduced the scratchStorageMode parameter on the
# HealthOmics StartRun / StartRunBatch request shapes.
MINIMUM_SDK_VERSION = Version('1.43.36')

# Repo root is the parent of the tests/ directory.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / 'pyproject.toml'


def test_installed_boto3_version_meets_minimum():
    """The installed boto3 version is >= 1.43.36."""
    assert Version(boto3.__version__) >= MINIMUM_SDK_VERSION, (
        f'Installed boto3 {boto3.__version__} is below the required minimum {MINIMUM_SDK_VERSION}'
    )


def test_installed_botocore_version_meets_minimum():
    """The installed botocore version is >= 1.43.36."""
    assert Version(botocore.__version__) >= MINIMUM_SDK_VERSION, (
        f'Installed botocore {botocore.__version__} is below the required '
        f'minimum {MINIMUM_SDK_VERSION}'
    )


def _declared_minimum(package):
    """Return the declared minimum Version for a package from pyproject.toml."""
    text = PYPROJECT_PATH.read_text(encoding='utf-8')
    # Match a quoted dependency entry such as "boto3>=1.43.36".
    match = re.search(rf'["\']{package}\s*>=\s*([0-9][0-9A-Za-z.\-]*)["\']', text)
    if match:
        return Version(match.group(1))
    return None


def test_pyproject_declares_boto3_minimum():
    """pyproject.toml declares a boto3 minimum of at least 1.43.36."""
    declared = _declared_minimum('boto3')

    assert declared is not None, 'boto3 dependency constraint not found in pyproject.toml'
    assert declared >= MINIMUM_SDK_VERSION, (
        f'pyproject.toml declares boto3>={declared}, below required {MINIMUM_SDK_VERSION}'
    )


def test_pyproject_declares_botocore_minimum():
    """pyproject.toml declares an explicit botocore minimum of at least 1.43.36."""
    declared = _declared_minimum('botocore')

    assert declared is not None, 'botocore dependency constraint not found in pyproject.toml'
    assert declared >= MINIMUM_SDK_VERSION, (
        f'pyproject.toml declares botocore>={declared}, below required {MINIMUM_SDK_VERSION}'
    )


def _omics_input_members(operation_name):
    """Return the input shape members for an omics operation (no network calls)."""
    client = boto3.client('omics', region_name='us-east-1')
    operation_model = client.meta.service_model.operation_model(operation_name)
    return operation_model.input_shape.members


def test_start_run_accepts_scratch_storage_mode():
    """The StartRun operation model accepts the scratchStorageMode parameter."""
    members = _omics_input_members('StartRun')
    assert 'scratchStorageMode' in members, (
        'StartRun input shape does not declare scratchStorageMode; '
        'the installed SDK does not support scratch storage mode'
    )


def test_start_run_batch_accepts_scratch_storage_mode():
    """The StartRunBatch defaultRunSetting accepts the scratchStorageMode parameter."""
    # For StartRunBatch the scratchStorageMode lives inside the defaultRunSetting
    # structure (the per-batch default applied to every run), matching where the
    # batch tool injects it.
    members = _omics_input_members('StartRunBatch')
    assert 'defaultRunSetting' in members, (
        'StartRunBatch input shape does not declare defaultRunSetting'
    )
    default_run_setting_members = members['defaultRunSetting'].members
    assert 'scratchStorageMode' in default_run_setting_members, (
        'StartRunBatch defaultRunSetting does not declare scratchStorageMode; '
        'the installed SDK does not support scratch storage mode'
    )
