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


"""Property tests for the harness Credential_Material scanner.

These tests are pure and offline: they exercise ``CredentialMaterialScanner`` from
``integration/harness/credential_scan.py`` without touching AWS or the network. They
live in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite and from the offline ``tests/`` suite — and are not gated
by the Opt_In_Signal.

Validates: Requirements Credential material safety.
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.credential_scan import (
    CredentialMaterialScanner,
    CredentialMaterialType,
)


# The three material categories the scanner groups registered secrets under.
_material_types = st.sampled_from(list(CredentialMaterialType))

# Non-blank secret values drawn from digits only. A small digit alphabet keeps the value
# space dense so generated secrets meaningfully overlap (and embed within) the generated
# text, while guaranteeing a secret can never coincidentally appear inside the scanner's
# structural output (class names, enum values, and the location contain no digits) — so a
# redaction assertion catches a genuine leak rather than a spurious substring collision.
_nonblank_secrets = st.text(alphabet='0123456789', min_size=1, max_size=6)

# Blank registrations (empty and whitespace-only) that the scanner must ignore so an
# empty registration never matches all text.
_blank_secrets = st.sampled_from(['', ' ', '  ', '\t', '\n', ' \t '])

_registered_values = st.one_of(_nonblank_secrets, _blank_secrets)


def _registered_pairs(
    secrets: dict[CredentialMaterialType, list[str]],
) -> list[tuple[CredentialMaterialType, str]]:
    """Independently compute the (type, value) pairs the scanner should honor.

    Mirrors the scanner's own rule: empty or blank registered values are dropped so an
    empty registration can never match, and order follows the mapping then each list.
    """
    return [
        (material_type, value)
        for material_type, values in secrets.items()
        for value in values
        if value and value.strip()
    ]


# Feature: remote-deployment-integration-tests, Property: Credential-material detection is sound, complete, and redacted
@settings(max_examples=200)
@given(
    secrets=st.dictionaries(
        keys=_material_types,
        values=st.lists(_registered_values, max_size=5),
        max_size=3,
    ),
    text=st.text(alphabet='0123456789 \t', max_size=20),
)
def test_credential_detection_is_sound_complete_and_redacted(
    secrets: dict[CredentialMaterialType, list[str]], text: str
) -> None:
    """Property: Credential-material detection is sound, complete, and redacted.

    For any set of registered Credential_Material values and any text, the scanner
    reports a finding for a registered value if and only if that value appears verbatim
    as a substring of the text; every finding carries the correct material type and
    location; and no finding, and no message the scanner raises, ever contains the
    Credential_Material value itself.

    Validates: Requirements Credential material safety.
    """
    location = 'captured-output'
    scanner = CredentialMaterialScanner(secrets)
    findings = scanner.scan(text, location)

    registered = _registered_pairs(secrets)

    # Soundness + completeness: findings correspond exactly (type + membership) to the
    # registered non-blank values that appear verbatim as a substring of the text.
    expected_findings = [
        (material_type, value) for material_type, value in registered if value in text
    ]
    assert len(findings) == len(expected_findings)
    for finding, (expected_type, _expected_value) in zip(findings, expected_findings):
        # Each finding carries the correct material type and location.
        assert finding.material_type == expected_type
        assert finding.location == location

    # Per-type completeness: a type appears among the findings iff at least one of its
    # registered non-blank values is a substring of the text (finding iff substring).
    for material_type in CredentialMaterialType:
        type_values = [value for mt, value in registered if mt == material_type]
        type_present = any(finding.material_type == material_type for finding in findings)
        assert type_present == any(value in text for value in type_values)

    # Redaction: no finding's repr/str ever contains a registered value verbatim.
    for _material_type, value in registered:
        assert value not in repr(findings)
        for finding in findings:
            assert value not in repr(finding)
            assert value not in str(finding)

    # Redaction of the raised message: assert_clean names only types + location and
    # never the offending value itself.
    if findings:
        try:
            scanner.assert_clean(text, location)
        except AssertionError as error:
            message = str(error)
            assert location in message
            for _material_type, value in registered:
                if value in text:
                    assert value not in message
        else:
            raise AssertionError('assert_clean should raise when findings exist')
    else:
        # No findings means assert_clean is silent.
        scanner.assert_clean(text, location)
