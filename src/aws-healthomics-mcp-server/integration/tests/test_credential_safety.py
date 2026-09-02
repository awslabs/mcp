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

"""End-to-end credential-material safety tests for a provisioned run.

These opt-in integration tests take the artifacts a real run left behind - the file
holding the full-duration captured stdout+stderr and every artifact the harness wrote to
disk - and scan them with the ``CredentialMaterialScanner`` registered with the concrete
secret values the harness observed (the STS temporary credentials and the bearer/JWT
tokens minted for callers). They assert no verbatim Credential_Material appears, exercising
the end-to-end safety guarantee rather than the scanner's pure logic (which is covered by
the offline property tests).

Validates: Requirements Credential material safety.

The suite is skipped by default; it only runs when the Opt_In_Signal
(``RUN_REMOTE_INTEGRATION_TESTS``) is set, and each test is skipped (never failed) when its
required inputs are absent. On a detected leak the scanner raises ``AssertionError`` naming
the material type and location WITHOUT the value - that is the desired failure mode, and the
tests pass when nothing leaks.
"""

import pytest
from collections.abc import Mapping
from integration.harness.credential_scan import (
    CredentialMaterialScanner,
    CredentialMaterialType,
)
from pathlib import Path


# Location of a file holding the full-duration captured stdout+stderr from a run.
CAPTURED_OUTPUT_PATH_ENV = 'AHO_ITEST_CAPTURED_OUTPUT_PATH'
# Directory the harness wrote artifacts into (captured-output files, logs, reports, and the
# resource inventory JSON) - every file beneath it is scanned.
ARTIFACT_DIR_ENV = 'AHO_ITEST_ARTIFACT_DIR'

# The concrete secret values the harness observed, grouped by material type. Each maps to
# the environment variable carrying that secret's verbatim value.
SECRET_ENV_BY_TYPE: Mapping[CredentialMaterialType, str] = {
    CredentialMaterialType.SECRET_ACCESS_KEY: 'AHO_ITEST_KNOWN_SECRET_ACCESS_KEY',  # pragma: allowlist secret
    CredentialMaterialType.SESSION_TOKEN: 'AHO_ITEST_KNOWN_SESSION_TOKEN',  # pragma: allowlist secret
    CredentialMaterialType.BEARER_TOKEN: 'AHO_ITEST_BEARER_TOKEN',  # pragma: allowlist secret
}


def _known_secrets(env: Mapping[str, str]) -> dict[CredentialMaterialType, list[str]]:
    """Collect the non-blank known secret values from ``env``, grouped by material type.

    Blank or absent secrets are ignored so an empty registration never matches all text.
    """
    secrets: dict[CredentialMaterialType, list[str]] = {}
    for material_type, env_name in SECRET_ENV_BY_TYPE.items():
        value = env.get(env_name)
        if value and value.strip():
            secrets.setdefault(material_type, []).append(value)
    return secrets


def _scanner_or_skip(env: Mapping[str, str]) -> CredentialMaterialScanner:
    """Build a scanner registered with the known secrets, or skip if none are available.

    Scanning with no registered secrets would pass trivially and prove nothing, so when no
    secret value is present the test is skipped (not failed) naming the secret inputs.
    """
    secrets = _known_secrets(env)
    if not secrets:
        pytest.skip(
            'Missing known Credential_Material value(s); set at least one of: '
            + ', '.join(SECRET_ENV_BY_TYPE.values())
        )
    return CredentialMaterialScanner(secrets)


@pytest.mark.integration
def test_captured_output_contains_no_credential_material(require_inputs, integration_env):
    """Captured stdout+stderr never contains any known secret verbatim.

    The full-duration capture is represented by the provided captured-output file. Reading
    it and asserting the scanner finds nothing verifies that no secret access key, session
    token, or bearer/JWT token leaked into the streams the harness captured.

    Validates: Requirements Credential material safety.
    """
    resolved = require_inputs([CAPTURED_OUTPUT_PATH_ENV])
    scanner = _scanner_or_skip(integration_env)

    captured_path = Path(resolved[CAPTURED_OUTPUT_PATH_ENV])
    if not captured_path.is_file():
        pytest.skip(f'Captured-output file does not exist: {captured_path}')

    text = captured_path.read_text(encoding='utf-8', errors='replace')
    # Raises AssertionError naming type+location (never the value) on any verbatim leak.
    scanner.assert_clean(text, 'captured-output')


@pytest.mark.integration
def test_written_artifacts_contain_no_credential_material(require_inputs, integration_env):
    """Every artifact written to disk is free of any known secret verbatim.

    Walking the artifact directory and scanning each file's content asserts that no
    captured-output file, log file, generated report, or resource inventory the harness
    wrote contains a secret access key, session token, or bearer/JWT token verbatim.

    Validates: Requirements Credential material safety.
    """
    resolved = require_inputs([ARTIFACT_DIR_ENV])
    scanner = _scanner_or_skip(integration_env)

    artifact_dir = Path(resolved[ARTIFACT_DIR_ENV])
    if not artifact_dir.is_dir():
        pytest.skip(f'Artifact directory does not exist: {artifact_dir}')

    files = sorted(path for path in artifact_dir.rglob('*') if path.is_file())
    if not files:
        pytest.skip(f'Artifact directory contains no files to scan: {artifact_dir}')

    for path in files:
        content = path.read_text(encoding='utf-8', errors='replace')
        # Raises AssertionError naming type+location (never the value) on any verbatim leak.
        scanner.assert_clean(content, str(path))
