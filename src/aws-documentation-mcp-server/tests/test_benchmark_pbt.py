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

"""Property-based tests for benchmark report helpers in scripts/benchmark_init.py."""

import importlib.util
import os
import statistics
from hypothesis import given, settings
from hypothesis import strategies as st


_scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
_spec = importlib.util.spec_from_file_location(
    'benchmark_init', os.path.join(_scripts_dir, 'benchmark_init.py')
)
assert _spec is not None and _spec.loader is not None, 'failed to load benchmark_init'
_benchmark_init = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_benchmark_init)

compute_median = _benchmark_init.compute_median
identify_threshold_violations = _benchmark_init.identify_threshold_violations
sort_bottleneck_report = _benchmark_init.sort_bottleneck_report


_phase_name = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz_'),
    min_size=1,
    max_size=20,
)

_time_ms = st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False)

_phase_list = st.lists(
    st.tuples(_phase_name, _time_ms),
    min_size=0,
    max_size=50,
)

_positive_float = st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False)

_positive_float_list = st.lists(_positive_float, min_size=1, max_size=100)


@settings(max_examples=100)
@given(phases=_phase_list)
def test_bottleneck_report_sorted_descending(phases: list[tuple[str, float]]) -> None:
    """Bottleneck report must be sorted in descending order of elapsed time."""
    sorted_phases = sort_bottleneck_report(phases)
    times = [t for _, t in sorted_phases]
    for i in range(len(times) - 1):
        assert times[i] >= times[i + 1], (
            f'Report not sorted descending at index {i}: {times[i]} < {times[i + 1]}'
        )


@settings(max_examples=100)
@given(values=_positive_float_list)
def test_median_matches_statistics_median(values: list[float]) -> None:
    """compute_median must equal statistics.median for any non-empty list."""
    result = compute_median(values)
    expected = statistics.median(values)
    assert result == expected, f'compute_median returned {result}, expected {expected}'


@settings(max_examples=100)
@given(phases=_phase_list)
def test_threshold_violations_match_filter(phases: list[tuple[str, float]]) -> None:
    """Violations list contains exactly phases whose elapsed time exceeds the threshold."""
    threshold = 200.0
    violations = identify_threshold_violations(phases, threshold_ms=threshold)

    expected_names = [name for name, t in phases if t > threshold]
    actual_names = [v.split(':')[0] for v in violations]

    assert len(actual_names) == len(expected_names), (
        f'Expected {len(expected_names)} violations, got {len(actual_names)}. Phases: {phases}'
    )
    assert actual_names == expected_names, (
        f'Violation names mismatch.\nExpected: {expected_names}\nActual:   {actual_names}'
    )
