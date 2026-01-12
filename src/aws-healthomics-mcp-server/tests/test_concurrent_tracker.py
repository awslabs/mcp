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

"""Unit and property-based tests for ConcurrentResourceTracker class."""

from awslabs.aws_healthomics_mcp_server.analysis.concurrent_tracker import (
    ConcurrentResourceTracker,
)
from datetime import datetime, timedelta
from hypothesis import given, settings
from hypothesis import strategies as st


class TestConcurrentResourceTrackerBasic:
    """Basic unit tests for ConcurrentResourceTracker."""

    def test_empty_task_list(self):
        """Test with empty task list returns zeros."""
        tracker = ConcurrentResourceTracker()
        result = tracker.calculate_concurrent_metrics([])

        assert result['peakConcurrentCpus'] == 0.0
        assert result['peakConcurrentMemoryGiB'] == 0.0
        assert result['averageConcurrentCpus'] == 0.0
        assert result['averageConcurrentMemoryGiB'] == 0.0

    def test_single_task(self):
        """Test with single task."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': '2023-01-01T00:00:00Z',
                'stopTime': '2023-01-01T01:00:00Z',
                'reservedCpus': 4,
                'reservedMemoryGiB': 8.0,
            }
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        assert result['peakConcurrentCpus'] == 4.0
        assert result['peakConcurrentMemoryGiB'] == 8.0
        assert result['averageConcurrentCpus'] == 4.0
        assert result['averageConcurrentMemoryGiB'] == 8.0

    def test_overlapping_tasks(self):
        """Test with overlapping tasks."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': '2023-01-01T00:00:00Z',
                'stopTime': '2023-01-01T01:00:00Z',
                'reservedCpus': 4,
                'reservedMemoryGiB': 8.0,
            },
            {
                'startTime': '2023-01-01T00:30:00Z',
                'stopTime': '2023-01-01T01:30:00Z',
                'reservedCpus': 2,
                'reservedMemoryGiB': 4.0,
            },
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        # Peak should be sum during overlap (4+2=6 CPUs, 8+4=12 GiB)
        assert result['peakConcurrentCpus'] == 6.0
        assert result['peakConcurrentMemoryGiB'] == 12.0

    def test_sequential_tasks(self):
        """Test with sequential non-overlapping tasks."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': '2023-01-01T00:00:00Z',
                'stopTime': '2023-01-01T01:00:00Z',
                'reservedCpus': 4,
                'reservedMemoryGiB': 8.0,
            },
            {
                'startTime': '2023-01-01T01:00:00Z',
                'stopTime': '2023-01-01T02:00:00Z',
                'reservedCpus': 2,
                'reservedMemoryGiB': 4.0,
            },
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        # Peak should be max of individual tasks (4 CPUs, 8 GiB)
        assert result['peakConcurrentCpus'] == 4.0
        assert result['peakConcurrentMemoryGiB'] == 8.0

    def test_missing_timing_data(self):
        """Test tasks with missing timing data are skipped."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': '2023-01-01T00:00:00Z',
                'stopTime': '2023-01-01T01:00:00Z',
                'reservedCpus': 4,
                'reservedMemoryGiB': 8.0,
            },
            {
                'startTime': '2023-01-01T00:30:00Z',
                # Missing stopTime
                'reservedCpus': 2,
                'reservedMemoryGiB': 4.0,
            },
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        # Only first task should be counted
        assert result['peakConcurrentCpus'] == 4.0
        assert result['peakConcurrentMemoryGiB'] == 8.0

    def test_datetime_objects(self):
        """Test with datetime objects instead of strings."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': datetime(2023, 1, 1, 0, 0, 0),
                'stopTime': datetime(2023, 1, 1, 1, 0, 0),
                'reservedCpus': 4,
                'reservedMemoryGiB': 8.0,
            }
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        assert result['peakConcurrentCpus'] == 4.0
        assert result['peakConcurrentMemoryGiB'] == 8.0

    def test_missing_resource_data(self):
        """Test tasks with missing resource data use defaults."""
        tracker = ConcurrentResourceTracker()
        tasks = [
            {
                'startTime': '2023-01-01T00:00:00Z',
                'stopTime': '2023-01-01T01:00:00Z',
                # Missing reservedCpus and reservedMemoryGiB
            }
        ]
        result = tracker.calculate_concurrent_metrics(tasks)

        # Should use default of 0
        assert result['peakConcurrentCpus'] == 0.0
        assert result['peakConcurrentMemoryGiB'] == 0.0


# Property-Based Tests using Hypothesis


# Strategy for generating task timestamps
def task_with_timing_strategy():
    """Generate a valid task dictionary with timing data."""
    return st.fixed_dictionaries(
        {
            'reservedCpus': st.floats(min_value=0.0, max_value=192.0, allow_nan=False),
            'reservedMemoryGiB': st.floats(min_value=0.0, max_value=1536.0, allow_nan=False),
            'duration_seconds': st.integers(min_value=1, max_value=86400),  # 1 sec to 1 day
            'start_offset_seconds': st.integers(min_value=0, max_value=86400),  # offset from base
        }
    )


class TestConcurrentResourceTrackerPropertyBased:
    """Property-based tests for ConcurrentResourceTracker using Hypothesis."""

    @given(tasks_data=st.lists(task_with_timing_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100)
    def test_property_concurrent_metrics_invariants(self, tasks_data: list[dict]):
        """Property 10: Concurrent Metrics Invariants.

        For any set of tasks with timing data:
        - peakConcurrentCpus >= averageConcurrentCpus >= 0
        - peakConcurrentMemoryGiB >= averageConcurrentMemoryGiB >= 0
        - peakConcurrentCpus >= max individual task CPU reservation

        **Validates: Requirements 9.1, 9.2, 9.3**
        **Feature: run-analyzer-enhancement, Property 10: Concurrent Metrics Invariants**
        """
        # Convert generated data to task format with actual timestamps
        base_time = datetime(2023, 1, 1, 0, 0, 0)
        tasks = []
        max_individual_cpus = 0.0
        max_individual_memory = 0.0

        for task_data in tasks_data:
            start_time = base_time + timedelta(seconds=task_data['start_offset_seconds'])
            stop_time = start_time + timedelta(seconds=task_data['duration_seconds'])

            tasks.append(
                {
                    'startTime': start_time,
                    'stopTime': stop_time,
                    'reservedCpus': task_data['reservedCpus'],
                    'reservedMemoryGiB': task_data['reservedMemoryGiB'],
                }
            )

            max_individual_cpus = max(max_individual_cpus, task_data['reservedCpus'])
            max_individual_memory = max(max_individual_memory, task_data['reservedMemoryGiB'])

        tracker = ConcurrentResourceTracker()
        result = tracker.calculate_concurrent_metrics(tasks)

        # Property 1: All metrics are non-negative
        assert result['peakConcurrentCpus'] >= 0.0, (
            f'peakConcurrentCpus should be >= 0, got {result["peakConcurrentCpus"]}'
        )
        assert result['peakConcurrentMemoryGiB'] >= 0.0, (
            f'peakConcurrentMemoryGiB should be >= 0, got {result["peakConcurrentMemoryGiB"]}'
        )
        assert result['averageConcurrentCpus'] >= 0.0, (
            f'averageConcurrentCpus should be >= 0, got {result["averageConcurrentCpus"]}'
        )
        assert result['averageConcurrentMemoryGiB'] >= 0.0, (
            f'averageConcurrentMemoryGiB should be >= 0, got {result["averageConcurrentMemoryGiB"]}'
        )

        # Property 2: Peak >= Average (with floating-point tolerance)
        # Use a small epsilon for floating-point comparison
        epsilon = 1e-9
        assert result['peakConcurrentCpus'] >= result['averageConcurrentCpus'] - epsilon, (
            f'peakConcurrentCpus ({result["peakConcurrentCpus"]}) should be >= '
            f'averageConcurrentCpus ({result["averageConcurrentCpus"]})'
        )
        assert (
            result['peakConcurrentMemoryGiB'] >= result['averageConcurrentMemoryGiB'] - epsilon
        ), (
            f'peakConcurrentMemoryGiB ({result["peakConcurrentMemoryGiB"]}) should be >= '
            f'averageConcurrentMemoryGiB ({result["averageConcurrentMemoryGiB"]})'
        )

        # Property 3: Peak >= max individual task reservation
        if tasks:
            assert result['peakConcurrentCpus'] >= max_individual_cpus, (
                f'peakConcurrentCpus ({result["peakConcurrentCpus"]}) should be >= '
                f'max individual CPU reservation ({max_individual_cpus})'
            )
            assert result['peakConcurrentMemoryGiB'] >= max_individual_memory, (
                f'peakConcurrentMemoryGiB ({result["peakConcurrentMemoryGiB"]}) should be >= '
                f'max individual memory reservation ({max_individual_memory})'
            )
