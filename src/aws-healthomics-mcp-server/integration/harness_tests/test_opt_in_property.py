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


"""Property tests for the harness opt-in dependency gate.

These tests are pure and offline: they exercise ``missing_required_inputs`` from
``integration/harness/opt_in.py`` without touching AWS or the network. They live
in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite and from the offline ``tests/`` suite — and are not
gated by the Opt_In_Signal.

Validates: Requirements Harness location and offline isolation.
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.opt_in import missing_required_inputs


# Names of configuration inputs a test may depend on. A small alphabet keeps the
# key space dense enough that generated ``provided`` mappings meaningfully
# overlap the ``required`` names.
_input_names = st.text(alphabet='abcxyz_', min_size=1, max_size=4)

# Values a provided mapping may hold. Includes present-with-value strings and
# blank values (empty and whitespace-only) so both the "absent" and "blank"
# branches of the missing-input definition are exercised.
_blank_values = st.sampled_from(['', ' ', '  ', '\t', '\n', ' \t\n '])
_nonblank_values = st.text(min_size=1).filter(lambda value: value.strip() != '')
_provided_values = st.one_of(_blank_values, _nonblank_values)


def _expected_missing(required: list[str], provided: dict[str, str]) -> list[str]:
    """Independently compute the required names that are absent or blank.

    A required name is missing when it is not a key of ``provided`` or when its
    value is blank (empty or whitespace-only). Order follows ``required`` and a
    name repeated in ``required`` is reported once per occurrence.
    """
    expected: list[str] = []
    for name in required:
        if name not in provided:
            expected.append(name)
        elif provided[name].strip() == '':
            expected.append(name)
    return expected


# Feature: remote-deployment-integration-tests, Property: Missing-input detection is exact
@settings(max_examples=200)
@given(
    required=st.lists(_input_names, max_size=8),
    provided=st.dictionaries(keys=_input_names, values=_provided_values, max_size=8),
)
def test_missing_input_detection_is_exact(required: list[str], provided: dict[str, str]) -> None:
    """Property: Missing-input detection is exact.

    For any set of required input names and any mapping of provided inputs,
    ``missing_required_inputs`` returns exactly those required names that are
    absent from the mapping or map to a blank value — no more and no fewer,
    preserving the order of ``required``.

    Validates: Requirements Harness location and offline isolation.
    """
    result = missing_required_inputs(required, provided)

    # Exactness: the result equals the independently computed expectation,
    # including order and per-occurrence multiplicity.
    assert result == _expected_missing(required, provided)

    # No more: every reported name is genuinely absent or blank in ``provided``.
    for name in result:
        assert name not in provided or provided[name].strip() == ''

    # No fewer: every required name that is present with a non-blank value is
    # never reported as missing.
    for name in required:
        if name in provided and provided[name].strip() != '':
            assert name not in result
