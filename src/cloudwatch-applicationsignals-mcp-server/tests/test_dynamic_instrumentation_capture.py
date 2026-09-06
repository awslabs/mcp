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

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Direct tests for the Capture ADT (capture.py).

The ADT owns the CaptureConfiguration API shape contract — payload
assembly via ``to_api_payload`` and inverse parsing via
``capture_from_response``. These tests pin the contract that:

* ``CaptureArguments`` distinguishes "omitted" (capture all) from
  "present-but-empty" (capture none) across the round-trip.
* The legacy fallback (CodeCapture-shaped dict without the wrapper key)
  still parses to ``CodeCapture``.
* Unknown payloads parse to ``UnknownCapture`` rather than raising.
"""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.capture import (
    CaptureLimits,
    CodeCapture,
    UnknownCapture,
    capture_from_response,
)


class TestCaptureFromResponse:
    """capture_from_response on every shape the API can return."""

    def test_parses_code_capture_with_full_payload(self):
        """Parses code capture with full payload."""
        cap = capture_from_response(
            {
                'CodeCapture': {
                    'CaptureReturn': True,
                    'CaptureStackTrace': False,
                    'CaptureArguments': ['order_id'],
                    'CaptureLocals': ['x', 'y'],
                    'CaptureLimits': {'MaxHits': 3, 'MaxStringLength': 128},
                }
            }
        )
        assert isinstance(cap, CodeCapture)
        assert cap.capture_return is True
        assert cap.capture_stack_trace is False
        assert cap.capture_arguments == ('order_id',)
        assert cap.capture_locals == ('x', 'y')
        assert cap.limits.max_hits == 3
        assert cap.limits.max_string_length == 128
        assert cap.limits.max_collection_width is None

    def test_unknown_payload_returns_unknown_capture(self):
        """Unknown payload returns unknown capture."""
        cap = capture_from_response({'FuturisticCapture': {'Foo': 1}})
        assert isinstance(cap, UnknownCapture)
        assert cap.raw == {'FuturisticCapture': {'Foo': 1}}

    def test_non_dict_input_returns_empty_unknown_capture(self):
        """Non dict input returns empty unknown capture."""
        cap = capture_from_response(None)
        assert isinstance(cap, UnknownCapture)
        assert cap.raw == {}

    def test_legacy_fallback_infers_code_capture_without_wrapper_key(self):
        """Legacy fallback infers code capture without wrapper key."""
        # Some response shapes return CodeCapture-style dicts directly without
        # the CodeCapture wrapper. The legacy extract_capture_variant accepted
        # this; the ADT's ``capture_from_response`` must too.
        cap = capture_from_response(
            {'CaptureReturn': True, 'CaptureStackTrace': True, 'CaptureLimits': {'MaxHits': 5}}
        )
        assert isinstance(cap, CodeCapture)
        assert cap.capture_return is True
        assert cap.limits.max_hits == 5


class TestCaptureArgumentsRoundTrip:
    """Omitted-vs-empty CaptureArguments survives parse → payload → parse."""

    def test_omitted_arguments_round_trip_to_omitted(self):
        """Omitted arguments round trip to omitted."""
        cap = CodeCapture(capture_return=True, capture_stack_trace=True, capture_arguments=None)
        payload = cap.to_api_payload()
        assert 'CaptureArguments' not in payload['CodeCapture']
        round_tripped = capture_from_response(payload)
        assert isinstance(round_tripped, CodeCapture)
        assert round_tripped.capture_arguments is None

    def test_empty_arguments_round_trip_to_empty(self):
        """Empty arguments round trip to empty."""
        cap = CodeCapture(capture_return=True, capture_stack_trace=True, capture_arguments=[])
        # The dataclass stores capture_arguments as a tuple regardless of how
        # the caller spelled the empty sequence; the API payload still emits
        # a JSON list so the wire contract is unchanged.
        assert cap.capture_arguments == ()
        payload = cap.to_api_payload()
        assert payload['CodeCapture']['CaptureArguments'] == []
        round_tripped = capture_from_response(payload)
        assert isinstance(round_tripped, CodeCapture)
        assert round_tripped.capture_arguments == ()


class TestCaptureLimits:
    """CaptureLimits emit only the keys that were set."""

    def test_empty_limits_emit_empty_payload(self):
        """Empty limits emit empty payload."""
        assert CaptureLimits().is_empty()
        assert CaptureLimits().to_api_payload() == {}

    def test_partial_limits_emit_only_set_keys(self):
        """Partial limits emit only set keys."""
        payload = CaptureLimits(max_hits=3, max_object_depth=5).to_api_payload()
        assert payload == {'MaxHits': 3, 'MaxObjectDepth': 5}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
