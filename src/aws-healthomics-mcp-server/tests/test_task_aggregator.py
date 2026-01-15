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

"""Unit and property-based tests for TaskAggregator class."""

import pytest
from awslabs.aws_healthomics_mcp_server.analysis.task_aggregator import TaskAggregator
from hypothesis import given, settings
from hypothesis import strategies as st


class TestTaskAggregatorNormalizeTaskName:
    """Test cases for normalize_task_name method."""

    def test_normalize_wdl_pattern_basic(self):
        """Test WDL pattern: taskName-<shard>-<attempt>."""
        assert TaskAggregator.normalize_task_name('alignReads-0-1') == 'alignReads'

    def test_normalize_wdl_pattern_multi_digit(self):
        """Test WDL pattern with multi-digit shard and attempt."""
        assert TaskAggregator.normalize_task_name('alignReads-10-2') == 'alignReads'
        assert TaskAggregator.normalize_task_name('processData-123-45') == 'processData'

    def test_normalize_wdl_pattern_with_hyphen_in_name(self):
        """Test WDL pattern with hyphen in task name."""
        assert TaskAggregator.normalize_task_name('align-reads-0-1') == 'align-reads'

    def test_normalize_wdl_pattern_with_text_suffix(self):
        """Test WDL pattern with text after scatter index."""
        assert (
            TaskAggregator.normalize_task_name('HaplotypeCallerGATK4-26-2527scattered')
            == 'HaplotypeCallerGATK4'
        )
        assert TaskAggregator.normalize_task_name('alignReads-0-retry') == 'alignReads'
        assert TaskAggregator.normalize_task_name('processData-5-attempt2') == 'processData'

    def test_normalize_nextflow_pattern_basic(self):
        """Test Nextflow pattern: taskName (index)."""
        assert TaskAggregator.normalize_task_name('alignReads (1)') == 'alignReads'

    def test_normalize_nextflow_pattern_string_index(self):
        """Test Nextflow pattern with string index."""
        assert TaskAggregator.normalize_task_name('alignReads (sample1)') == 'alignReads'
        assert TaskAggregator.normalize_task_name('processData (file_001)') == 'processData'

    def test_normalize_cwl_pattern_basic(self):
        """Test CWL pattern: taskName_<index>."""
        assert TaskAggregator.normalize_task_name('alignReads_0') == 'alignReads'

    def test_normalize_cwl_pattern_multi_digit(self):
        """Test CWL pattern with multi-digit index."""
        assert TaskAggregator.normalize_task_name('alignReads_10') == 'alignReads'
        assert TaskAggregator.normalize_task_name('processData_123') == 'processData'

    def test_normalize_no_pattern_match(self):
        """Test task name without scatter suffix."""
        assert TaskAggregator.normalize_task_name('alignReads') == 'alignReads'
        assert TaskAggregator.normalize_task_name('process_data') == 'process_data'

    def test_normalize_empty_string(self):
        """Test empty task name."""
        assert TaskAggregator.normalize_task_name('') == ''

    def test_normalize_none_handling(self):
        """Test None handling (should return None)."""
        assert TaskAggregator.normalize_task_name(None) is None  # type: ignore


class TestTaskAggregatorAggregateTasks:
    """Test cases for aggregate_tasks method."""

    def test_aggregate_empty_list(self):
        """Test aggregation with empty task list."""
        aggregator = TaskAggregator()
        result = aggregator.aggregate_tasks([])
        assert len(result) == 0

    def test_aggregate_single_task(self):
        """Test aggregation with single task."""
        aggregator = TaskAggregator()
        tasks = [
            {
                'taskName': 'alignReads-0-1',
                'runningSeconds': 100.0,
                'cpuEfficiencyRatio': 0.5,
                'memoryEfficiencyRatio': 0.6,
                'maxCpuUtilization': 2.0,
                'maxMemoryUtilizationGiB': 4.0,
                'estimatedUSD': 0.10,
            }
        ]
        result = aggregator.aggregate_tasks(tasks)

        assert len(result) == 1
        row = result.filter(result['baseTaskName'] == 'alignReads')
        assert row['count'][0] == 1
        assert row['meanRunningSeconds'][0] == 100.0
        assert row['totalEstimatedUSD'][0] == 0.10

    def test_aggregate_multiple_scattered_tasks(self):
        """Test aggregation of multiple scattered tasks."""
        aggregator = TaskAggregator()
        tasks = [
            {
                'taskName': 'alignReads-0-1',
                'runningSeconds': 100.0,
                'cpuEfficiencyRatio': 0.5,
                'memoryEfficiencyRatio': 0.6,
                'maxCpuUtilization': 2.0,
                'maxMemoryUtilizationGiB': 4.0,
                'estimatedUSD': 0.10,
            },
            {
                'taskName': 'alignReads-1-1',
                'runningSeconds': 120.0,
                'cpuEfficiencyRatio': 0.6,
                'memoryEfficiencyRatio': 0.7,
                'maxCpuUtilization': 2.5,
                'maxMemoryUtilizationGiB': 5.0,
                'estimatedUSD': 0.12,
            },
        ]
        result = aggregator.aggregate_tasks(tasks)

        assert len(result) == 1
        row = result.filter(result['baseTaskName'] == 'alignReads')
        assert row['count'][0] == 2
        assert row['meanRunningSeconds'][0] == 110.0
        assert row['maximumRunningSeconds'][0] == 120.0
        assert row['totalEstimatedUSD'][0] == pytest.approx(0.22)

    def test_aggregate_multiple_task_types(self):
        """Test aggregation with multiple task types."""
        aggregator = TaskAggregator()
        tasks = [
            {
                'taskName': 'alignReads-0-1',
                'runningSeconds': 100.0,
                'cpuEfficiencyRatio': 0.5,
                'memoryEfficiencyRatio': 0.6,
                'maxCpuUtilization': 2.0,
                'maxMemoryUtilizationGiB': 4.0,
                'estimatedUSD': 0.10,
            },
            {
                'taskName': 'alignReads-1-1',
                'runningSeconds': 120.0,
                'cpuEfficiencyRatio': 0.6,
                'memoryEfficiencyRatio': 0.7,
                'maxCpuUtilization': 2.5,
                'maxMemoryUtilizationGiB': 5.0,
                'estimatedUSD': 0.12,
            },
            {
                'taskName': 'sortBam-0-1',
                'runningSeconds': 50.0,
                'cpuEfficiencyRatio': 0.4,
                'memoryEfficiencyRatio': 0.5,
                'maxCpuUtilization': 1.0,
                'maxMemoryUtilizationGiB': 2.0,
                'estimatedUSD': 0.05,
            },
        ]
        result = aggregator.aggregate_tasks(tasks)

        assert len(result) == 2

        align_row = result.filter(result['baseTaskName'] == 'alignReads')
        assert align_row['count'][0] == 2
        assert align_row['totalEstimatedUSD'][0] == pytest.approx(0.22)

        sort_row = result.filter(result['baseTaskName'] == 'sortBam')
        assert sort_row['count'][0] == 1
        assert sort_row['totalEstimatedUSD'][0] == pytest.approx(0.05)

    def test_aggregate_missing_fields(self):
        """Test aggregation with missing optional fields."""
        aggregator = TaskAggregator()
        tasks = [
            {'taskName': 'alignReads-0-1'},
            {'taskName': 'alignReads-1-1', 'runningSeconds': 100.0},
        ]
        result = aggregator.aggregate_tasks(tasks)

        assert len(result) == 1
        row = result.filter(result['baseTaskName'] == 'alignReads')
        assert row['count'][0] == 2

    def test_aggregate_max_utilization_metrics(self):
        """Test that max utilization metrics are correctly calculated."""
        aggregator = TaskAggregator()
        tasks = [
            {
                'taskName': 'alignReads-0-1',
                'runningSeconds': 100.0,
                'cpuEfficiencyRatio': 0.5,
                'memoryEfficiencyRatio': 0.6,
                'maxCpuUtilization': 2.0,
                'maxMemoryUtilizationGiB': 4.0,
                'estimatedUSD': 0.10,
            },
            {
                'taskName': 'alignReads-1-1',
                'runningSeconds': 120.0,
                'cpuEfficiencyRatio': 0.8,
                'memoryEfficiencyRatio': 0.9,
                'maxCpuUtilization': 3.0,
                'maxMemoryUtilizationGiB': 6.0,
                'estimatedUSD': 0.12,
            },
        ]
        result = aggregator.aggregate_tasks(tasks)

        row = result.filter(result['baseTaskName'] == 'alignReads')
        assert row['maximumCpuUtilizationRatio'][0] == 0.8
        assert row['maximumMemoryUtilizationRatio'][0] == 0.9
        assert row['maxObservedCpus'][0] == 3.0
        assert row['maxObservedMemoryGiB'][0] == 6.0


# Property-Based Tests using Hypothesis


class TestTaskAggregatorPropertyBased:
    """Property-based tests for TaskAggregator using Hypothesis."""

    # Strategy for generating valid task names
    base_task_name_strategy = st.text(
        alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'),
        min_size=1,
        max_size=20,
    )

    @given(base_name=base_task_name_strategy)
    @settings(max_examples=100)
    def test_property_normalization_idempotence(self, base_name: str):
        """Property 8: Task Name Normalization Idempotence.

        For any task name N, normalizing N twice SHALL produce the same result
        as normalizing once: normalize(normalize(N)) == normalize(N).

        **Validates: Requirements 6.1, 6.2**
        **Feature: run-analyzer-enhancement, Property 8: Task Name Normalization Idempotence**
        """
        # Test with base name (no suffix)
        once = TaskAggregator.normalize_task_name(base_name)
        twice = TaskAggregator.normalize_task_name(once)
        assert once == twice, f'Idempotence failed for base name: {base_name}'

    @given(
        base_name=base_task_name_strategy,
        shard=st.integers(min_value=0, max_value=1000),
        attempt=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_property_normalization_idempotence_wdl(
        self, base_name: str, shard: int, attempt: int
    ):
        """Property 8: Task Name Normalization Idempotence (WDL pattern).

        For any WDL-style task name, normalizing twice produces the same result.

        **Validates: Requirements 6.1, 6.2**
        **Feature: run-analyzer-enhancement, Property 8: Task Name Normalization Idempotence**
        """
        task_name = f'{base_name}-{shard}-{attempt}'
        once = TaskAggregator.normalize_task_name(task_name)
        twice = TaskAggregator.normalize_task_name(once)
        assert once == twice, f'Idempotence failed for WDL pattern: {task_name}'

    @given(
        base_name=base_task_name_strategy,
        index=st.text(min_size=1, max_size=10),
    )
    @settings(max_examples=100)
    def test_property_normalization_idempotence_nextflow(self, base_name: str, index: str):
        """Property 8: Task Name Normalization Idempotence (Nextflow pattern).

        For any Nextflow-style task name, normalizing twice produces the same result.

        **Validates: Requirements 6.1, 6.2**
        **Feature: run-analyzer-enhancement, Property 8: Task Name Normalization Idempotence**
        """
        task_name = f'{base_name} ({index})'
        once = TaskAggregator.normalize_task_name(task_name)
        twice = TaskAggregator.normalize_task_name(once)
        assert once == twice, f'Idempotence failed for Nextflow pattern: {task_name}'

    @given(
        base_name=base_task_name_strategy,
        index=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=100)
    def test_property_normalization_idempotence_cwl(self, base_name: str, index: int):
        """Property 8: Task Name Normalization Idempotence (CWL pattern).

        For any CWL-style task name, normalizing twice produces the same result.

        **Validates: Requirements 6.1, 6.2**
        **Feature: run-analyzer-enhancement, Property 8: Task Name Normalization Idempotence**
        """
        task_name = f'{base_name}_{index}'
        once = TaskAggregator.normalize_task_name(task_name)
        twice = TaskAggregator.normalize_task_name(once)
        assert once == twice, f'Idempotence failed for CWL pattern: {task_name}'


# Strategy for generating task dictionaries
def task_strategy():
    """Generate a valid task dictionary for testing."""
    return st.fixed_dictionaries(
        {
            'taskName': st.text(
                alphabet=st.sampled_from(
                    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-() '
                ),
                min_size=1,
                max_size=30,
            ),
            'runningSeconds': st.floats(min_value=0.0, max_value=86400.0, allow_nan=False),
            'cpuEfficiencyRatio': st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
            'memoryEfficiencyRatio': st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
            'maxCpuUtilization': st.floats(min_value=0.0, max_value=192.0, allow_nan=False),
            'maxMemoryUtilizationGiB': st.floats(min_value=0.0, max_value=1536.0, allow_nan=False),
            'estimatedUSD': st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        }
    )


class TestTaskAggregatorAggregationPropertyBased:
    """Property-based tests for aggregate_tasks method."""

    @given(tasks=st.lists(task_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100)
    def test_property_aggregation_count_invariant(self, tasks: list[dict]):
        """Property 9: Aggregation Count Invariant.

        For any set of tasks grouped by base name, the sum of counts across all
        aggregated groups SHALL equal the total number of input tasks.

        **Validates: Requirements 6.3, 6.4, 7.1, 7.2**
        **Feature: run-analyzer-enhancement, Property 9: Aggregation Count Invariant**
        """
        aggregator = TaskAggregator()
        result = aggregator.aggregate_tasks(tasks)

        if len(tasks) == 0:
            assert len(result) == 0
        else:
            # Sum of all counts should equal total input tasks
            total_count = result['count'].sum()
            assert total_count == len(tasks), (
                f'Count invariant violated: sum of counts ({total_count}) '
                f'!= input task count ({len(tasks)})'
            )
