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

"""Property-based tests for benchmark test threshold assertion logic.

**Feature: init-performance-benchmark, Property 5: Benchmark test threshold assertion**

*For any* median initialization time value above 1500 milliseconds, the benchmark
test SHALL fail. *For any* median value at or below 1500 milliseconds, the benchmark
test SHALL pass.

**Validates: Requirements 5.2**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.conftest import INIT_TIME_THRESHOLD_MS, check_threshold

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Positive floats representing median init times in milliseconds
_positive_ms = st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False)


# ---------------------------------------------------------------------------
# Property 5: Benchmark test threshold assertion
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(median_ms=_positive_ms)
def test_threshold_assertion_property(median_ms: float) -> None:
    """Property 5: For any positive median initialization time, check_threshold
    returns True (pass) when median_ms <= 1500 and False (fail) when
    median_ms > 1500.

    **Validates: Requirements 5.2**
    """
    result = check_threshold(median_ms)
    if median_ms > INIT_TIME_THRESHOLD_MS:
        assert result is False, (
            f"Expected check_threshold({median_ms}) to fail (return False) "
            f"since {median_ms} > {INIT_TIME_THRESHOLD_MS}, but got True"
        )
    else:
        assert result is True, (
            f"Expected check_threshold({median_ms}) to pass (return True) "
            f"since {median_ms} <= {INIT_TIME_THRESHOLD_MS}, but got False"
        )
