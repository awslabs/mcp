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

"""Property-based tests for benchmark report helper functions.

Tests the pure functions in scripts/benchmark_init.py:
- sort_bottleneck_report
- compute_median
- identify_threshold_violations

**Feature: init-performance-benchmark**

**Validates: Requirements 1.2, 1.4, 2.3, 5.3**
"""

import importlib.util
import os
import statistics

from hypothesis import given, settings
from hypothesis import strategies as st

# Load benchmark_init from scripts/ without modifying sys.path
_scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
_spec = importlib.util.spec_from_file_location('benchmark_init', os.path.join(_scripts_dir, 'benchmark_init.py'))
_benchmark_init = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_benchmark_init)

compute_median = _benchmark_init.compute_median
identify_threshold_violations = _benchmark_init.identify_threshold_violations
sort_bottleneck_report = _benchmark_init.sort_bottleneck_report

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Phase names: short non-empty ASCII strings
_phase_name = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz_'),
    min_size=1,
    max_size=20,
)

# Timing values in the 0–2000ms range (floats)
_time_ms = st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False)

# A list of (phase_name, time_ms) tuples
_phase_list = st.lists(
    st.tuples(_phase_name, _time_ms),
    min_size=0,
    max_size=50,
)

# Positive floats for median calculation
_positive_float = st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False)

_positive_float_list = st.lists(_positive_float, min_size=1, max_size=100)


# ---------------------------------------------------------------------------
# Property 1: Bottleneck report is sorted slowest-to-fastest
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(phases=_phase_list)
def test_bottleneck_report_sorted_descending(phases: list[tuple[str, float]]) -> None:
    """Property 1: For any list of phase timings, the bottleneck report
    output is sorted in descending order of elapsed time (slowest first).

    **Validates: Requirements 1.2**
    """
    sorted_phases = sort_bottleneck_report(phases)
    times = [t for _, t in sorted_phases]
    for i in range(len(times) - 1):
        assert times[i] >= times[i + 1], (
            f"Report not sorted descending at index {i}: "
            f"{times[i]} < {times[i + 1]}"
        )


# ---------------------------------------------------------------------------
# Property 2: Median calculation correctness
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(values=_positive_float_list)
def test_median_matches_statistics_median(values: list[float]) -> None:
    """Property 2: For any non-empty list of positive timing measurements,
    the reported median equals statistics.median of those measurements.

    **Validates: Requirements 1.4, 5.3**
    """
    result = compute_median(values)
    expected = statistics.median(values)
    assert result == expected, (
        f"compute_median returned {result}, expected {expected}"
    )


# ---------------------------------------------------------------------------
# Property 3: Threshold violation identification
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(phases=_phase_list)
def test_threshold_violations_match_filter(phases: list[tuple[str, float]]) -> None:
    """Property 3: For any set of phase timings (0–2000ms), the violations
    list contains exactly those phases whose elapsed time exceeds 200ms,
    and no others.

    **Validates: Requirements 2.3**
    """
    threshold = 200.0
    violations = identify_threshold_violations(phases, threshold_ms=threshold)

    # Compute expected violating phase names
    expected_names = [name for name, t in phases if t > threshold]

    # Extract names from violation strings (format: "<name>: <time>ms > <threshold>ms")
    actual_names = [v.split(':')[0] for v in violations]

    assert len(actual_names) == len(expected_names), (
        f"Expected {len(expected_names)} violations, got {len(actual_names)}. "
        f"Phases: {phases}"
    )
    assert actual_names == expected_names, (
        f"Violation names mismatch.\n"
        f"Expected: {expected_names}\n"
        f"Actual:   {actual_names}"
    )
