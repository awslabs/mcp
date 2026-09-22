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


"""Property test for the harness scanner-guarded artifact writer.

This test is pure and offline: it exercises ``safe_write`` from
``integration/harness/credential_scan.py`` using only local filesystem writes to a
temporary directory — no AWS and no network. It lives in ``integration/harness_tests/`` —
separate from the opt-in-gated ``integration/tests/`` suite and from the offline
``tests/`` suite — and is not gated by the Opt_In_Signal.

Validates: Requirements Credential material safety.
"""

import pathlib
import tempfile
from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.credential_scan import (
    CredentialMaterialScanner,
    CredentialMaterialType,
    safe_write,
)


# The three material categories the scanner groups registered secrets under.
_material_types = st.sampled_from(list(CredentialMaterialType))

# Non-blank secret values drawn from digits only. A small digit alphabet keeps the value
# space dense so generated secrets meaningfully overlap (and embed within) the generated
# text, while guaranteeing a secret can never coincidentally appear inside structural
# output (path names, enum values) — so the invariant catches a genuine leak rather than a
# spurious substring collision.
_nonblank_secrets = st.text(alphabet='0123456789', min_size=1, max_size=6)

# Blank registrations (empty and whitespace-only) that the scanner must ignore so an empty
# registration never matches all text.
_blank_secrets = st.sampled_from(['', ' ', '  ', '\t', '\n', ' \t '])

_registered_values = st.one_of(_nonblank_secrets, _blank_secrets)


def _registered_nonblank_values(
    secrets: dict[CredentialMaterialType, list[str]],
) -> list[str]:
    """Independently compute the non-blank registered secret values the scanner honors.

    Mirrors the scanner's own rule: empty or blank registered values are dropped so an
    empty registration can never match.
    """
    return [value for values in secrets.values() for value in values if value and value.strip()]


# Feature: remote-deployment-integration-tests, Property: Artifacts written to disk never contain Credential_Material verbatim
@settings(max_examples=200)
@given(
    secrets=st.dictionaries(
        keys=_material_types,
        values=st.lists(_registered_values, max_size=5),
        max_size=3,
    ),
    text=st.text(alphabet='0123456789 \t', max_size=20),
    filename_seed=st.integers(min_value=0, max_value=2**63 - 1),
)
def test_safe_write_never_persists_credential_material(
    secrets: dict[CredentialMaterialType, list[str]],
    text: str,
    filename_seed: int,
) -> None:
    """Property: Artifacts written to disk never contain Credential_Material verbatim.

    For any text and any set of registered Credential_Material values, ``safe_write``
    either writes content the scanner proves clean or refuses the write (raises), so the
    resulting on-disk artifact never contains any registered Credential_Material value as
    a substring.

    Validates: Requirements Credential material safety.
    """
    scanner = CredentialMaterialScanner(secrets)
    registered = _registered_nonblank_values(secrets)
    text_contains_secret = any(value in text for value in registered)

    # A locally created temp directory (not the function-scoped ``tmp_path`` fixture) keeps
    # each Hypothesis example isolated without tripping the function-scoped-fixture health
    # check; a per-example filename avoids reusing a stale artifact across examples.
    with tempfile.TemporaryDirectory() as temp_dir:
        target = pathlib.Path(temp_dir) / f'artifact-{filename_seed}.txt'

        if text_contains_secret:
            # The writer must refuse: it raises and leaves no leaking artifact behind.
            try:
                safe_write(target, text, scanner)
            except AssertionError:
                pass
            else:
                raise AssertionError('safe_write must refuse text containing a secret')
        else:
            # Clean text is persisted and the returned path is the destination.
            written = safe_write(target, text, scanner)
            assert written == target
            assert target.exists()
            assert target.read_text(encoding='utf-8') == text

        # Invariant (both branches): the on-disk artifact, if it exists at all, never
        # contains any registered Credential_Material value verbatim.
        if target.exists():
            on_disk = target.read_text(encoding='utf-8')
            for value in registered:
                assert value not in on_disk
