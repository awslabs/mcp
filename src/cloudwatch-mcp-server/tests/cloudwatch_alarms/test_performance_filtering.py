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

"""Performance tests for CloudWatch active alarms filtering functionality.

This module contains comprehensive performance tests to validate that the filtering
functionality performs efficiently under various load conditions and scenarios.
Tests cover large result sets, memory usage, pagination efficiency, and early
termination optimization.
"""

import asyncio
import gc
import psutil
import pytest
import time
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import ActiveAlarmsResponse
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools
from tests.cloudwatch_alarms.fixtures import (
    SNS_ALERT_ARN,
    AlarmFixtures,
    PaginationFixtures,
)
from unittest.mock import AsyncMock, Mock, patch


@pytest.fixture
def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""

    def __init__(self):
        """Initialize performance metrics tracking."""
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.peak_memory = None
        self.process = psutil.Process()

    def start_measurement(self):
        """Start performance measurement."""
        gc.collect()  # Force garbage collection before measurement
        self.start_time = time.perf_counter()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory

    def update_peak_memory(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory

    def end_measurement(self):
        """End performance measurement."""
        self.end_time = time.perf_counter()
        self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

    @property
    def execution_time(self) -> float:
        """Get execution time in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def memory_delta(self) -> float:
        """Get memory usage delta in MB."""
        if self.start_memory and self.end_memory:
            return self.end_memory - self.start_memory
        return 0.0

    @property
    def peak_memory_delta(self) -> float:
        """Get peak memory usage delta in MB."""
        if self.start_memory and self.peak_memory:
            return self.peak_memory - self.start_memory
        return 0.0


class TestPerformanceFiltering:
    """Performance tests for get_active_alarms filtering functionality."""

    @pytest.mark.asyncio
    async def test_large_result_set_filtering_performance(self, mock_context):
        """Test filtering performance with large result sets (100+ alarms)."""
        # Create large dataset with 150 alarms (120 autoscaling, 30 non-autoscaling)
        large_response = PaginationFixtures.create_large_dataset_response(
            num_autoscaling=120, num_non_autoscaling=30
        )

        metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = large_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with filtering enabled
            metrics.start_measurement()
            result_filtered = await alarms_tools.get_active_alarms(
                mock_context, max_items=25, include_autoscaling_alarms=False
            )
            metrics.update_peak_memory()
            metrics.end_measurement()

            # Verify results
            assert isinstance(result_filtered, ActiveAlarmsResponse)
            assert len(result_filtered.metric_alarms) == 25  # Should get requested amount

            # Performance assertions
            assert metrics.execution_time < 2.0, (
                f'Filtering took too long: {metrics.execution_time:.3f}s'
            )
            assert metrics.peak_memory_delta < 50.0, (
                f'Memory usage too high: {metrics.peak_memory_delta:.1f}MB'
            )

            # Verify all returned alarms are non-autoscaling
            for alarm in result_filtered.metric_alarms:
                assert 'autoscaling-alarm' not in alarm.alarm_name
                assert 'application-alarm' in alarm.alarm_name

    @pytest.mark.asyncio
    async def test_memory_usage_during_filtering_operations(self, mock_context):
        """Test memory usage during filtering operations with various dataset sizes."""
        test_cases = [
            {'autoscaling': 50, 'non_autoscaling': 10, 'max_items': 10},
            {'autoscaling': 100, 'non_autoscaling': 20, 'max_items': 15},
            {'autoscaling': 200, 'non_autoscaling': 50, 'max_items': 30},
        ]

        memory_results = []

        for case in test_cases:
            large_response = PaginationFixtures.create_large_dataset_response(
                num_autoscaling=case['autoscaling'], num_non_autoscaling=case['non_autoscaling']
            )

            metrics = PerformanceMetrics()

            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = large_response
                mock_client.get_paginator.return_value = mock_paginator
                mock_session.return_value.client.return_value = mock_client

                alarms_tools = CloudWatchAlarmsTools()

                metrics.start_measurement()
                result = await alarms_tools.get_active_alarms(
                    mock_context, max_items=case['max_items'], include_autoscaling_alarms=False
                )
                metrics.update_peak_memory()
                metrics.end_measurement()

                memory_results.append(
                    {
                        'total_alarms': case['autoscaling'] + case['non_autoscaling'],
                        'memory_delta': metrics.memory_delta,
                        'peak_memory_delta': metrics.peak_memory_delta,
                        'execution_time': metrics.execution_time,
                    }
                )

                # Verify results
                assert len(result.metric_alarms) == case['max_items']

        # Analyze memory usage patterns
        for i, result in enumerate(memory_results):
            # Memory usage should be reasonable and not grow excessively
            assert result['peak_memory_delta'] < 100.0, (
                f'Case {i}: Peak memory too high: {result["peak_memory_delta"]:.1f}MB'
            )
            assert result['memory_delta'] < 50.0, (
                f'Case {i}: Memory delta too high: {result["memory_delta"]:.1f}MB'
            )

            # Memory usage should not grow linearly with dataset size
            if i > 0:
                prev_result = memory_results[i - 1]
                size_ratio = result['total_alarms'] / prev_result['total_alarms']
                memory_ratio = result['peak_memory_delta'] / max(
                    prev_result['peak_memory_delta'], 1.0
                )

                # Memory growth should be sub-linear (less than size growth)
                assert memory_ratio < size_ratio * 1.5, (
                    f'Memory growth too high: {memory_ratio:.2f} vs size ratio {size_ratio:.2f}'
                )

    @pytest.mark.asyncio
    async def test_pagination_efficiency_high_autoscaling_percentage(self, mock_context):
        """Test pagination efficiency when high percentage of alarms are autoscaling."""
        # Create scenario where 95% of alarms are autoscaling (190 autoscaling, 10 non-autoscaling)
        # This tests the worst-case scenario for filtering efficiency

        # Create multiple pages with high autoscaling ratio
        pages = []
        for page_num in range(20):  # 20 pages with 10 alarms each
            page_alarms = []
            for alarm_num in range(10):
                if (page_num * 10 + alarm_num) < 190:  # First 190 are autoscaling
                    alarm = AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()
                    alarm['AlarmName'] = f'autoscaling-alarm-{page_num:02d}-{alarm_num:02d}'
                else:  # Last 10 are non-autoscaling
                    alarm = AlarmFixtures.create_metric_alarm_without_autoscaling_actions()
                    alarm['AlarmName'] = f'application-alarm-{page_num:02d}-{alarm_num:02d}'
                page_alarms.append(alarm)

            pages.append({'MetricAlarms': page_alarms, 'CompositeAlarms': []})

        metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = pages
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            metrics.start_measurement()
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=8,  # Request 8 non-autoscaling alarms (should find them in later pages)
                include_autoscaling_alarms=False,
            )
            metrics.update_peak_memory()
            metrics.end_measurement()

            # Verify results
            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 8  # Should find 8 non-autoscaling alarms
            assert result.has_more_results  # Should indicate more results available

            # Performance assertions - should still be efficient despite high filtering ratio
            assert metrics.execution_time < 3.0, (
                f'High-ratio filtering took too long: {metrics.execution_time:.3f}s'
            )
            assert metrics.peak_memory_delta < 75.0, (
                f'Memory usage too high: {metrics.peak_memory_delta:.1f}MB'
            )

            # Verify all returned alarms are non-autoscaling
            for alarm in result.metric_alarms:
                assert 'application-alarm' in alarm.alarm_name

    @pytest.mark.asyncio
    async def test_early_termination_optimization(self, mock_context):
        """Test that early termination optimization works correctly."""
        # Create a large dataset where non-autoscaling alarms are found early
        early_termination_pages = []

        # First page: Mix with some non-autoscaling alarms
        first_page_alarms = []
        for i in range(5):
            alarm = AlarmFixtures.create_metric_alarm_without_autoscaling_actions()
            alarm['AlarmName'] = f'early-app-alarm-{i}'
            first_page_alarms.append(alarm)

        for i in range(5):
            alarm = AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()
            alarm['AlarmName'] = f'early-autoscaling-alarm-{i}'
            first_page_alarms.append(alarm)

        early_termination_pages.append({'MetricAlarms': first_page_alarms, 'CompositeAlarms': []})

        # Add many more pages that shouldn't be processed due to early termination
        for page_num in range(1, 10):
            page_alarms = []
            for alarm_num in range(10):
                alarm = AlarmFixtures.create_metric_alarm_without_autoscaling_actions()
                alarm['AlarmName'] = f'unused-app-alarm-{page_num}-{alarm_num}'
                page_alarms.append(alarm)

            early_termination_pages.append({'MetricAlarms': page_alarms, 'CompositeAlarms': []})

        # Track which pages were actually processed
        pages_processed = []

        def track_page_access(pages):
            """Generator that tracks which pages are accessed."""
            for i, page in enumerate(pages):
                pages_processed.append(i)
                yield page

        metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = track_page_access(early_termination_pages)
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            metrics.start_measurement()
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=3,  # Request only 3 alarms (should be satisfied by first page)
                include_autoscaling_alarms=False,
            )
            metrics.update_peak_memory()
            metrics.end_measurement()

            # Verify results
            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 3  # Should get exactly 3 alarms
            assert result.has_more_results  # Should indicate more results available

            # Verify early termination - should only process first page
            assert len(pages_processed) == 1, (
                f'Expected 1 page processed, got {len(pages_processed)}'
            )
            assert pages_processed[0] == 0, 'Should have processed only the first page'

            # Performance should be excellent due to early termination
            assert metrics.execution_time < 0.5, (
                f'Early termination should be fast: {metrics.execution_time:.3f}s'
            )
            assert metrics.peak_memory_delta < 20.0, (
                f'Memory usage should be low: {metrics.peak_memory_delta:.1f}MB'
            )

    @pytest.mark.asyncio
    async def test_filtering_overhead_benchmark(self, mock_context):
        """Benchmark filtering overhead compared to unfiltered operation."""
        # Create identical dataset for both tests
        benchmark_response = PaginationFixtures.create_large_dataset_response(
            num_autoscaling=80, num_non_autoscaling=20
        )

        # Test unfiltered operation (include_autoscaling_alarms=True)
        unfiltered_metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = benchmark_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            unfiltered_metrics.start_measurement()
            unfiltered_result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=50,
                include_autoscaling_alarms=True,  # No filtering
            )
            unfiltered_metrics.update_peak_memory()
            unfiltered_metrics.end_measurement()

        # Test filtered operation (include_autoscaling_alarms=False)
        filtered_metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = benchmark_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            filtered_metrics.start_measurement()
            filtered_result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=20,  # Request only non-autoscaling alarms
                include_autoscaling_alarms=False,  # With filtering
            )
            filtered_metrics.update_peak_memory()
            filtered_metrics.end_measurement()

        # Verify results
        assert len(unfiltered_result.metric_alarms) == 50  # Should include both types
        assert len(filtered_result.metric_alarms) == 20  # Should include only non-autoscaling

        # Calculate overhead
        time_overhead = filtered_metrics.execution_time - unfiltered_metrics.execution_time
        memory_overhead = filtered_metrics.peak_memory_delta - unfiltered_metrics.peak_memory_delta

        # Filtering overhead should be reasonable
        overhead_percentage = (time_overhead / max(unfiltered_metrics.execution_time, 0.001)) * 100

        # Assertions for acceptable overhead
        assert overhead_percentage < 200.0, (
            f'Filtering overhead too high: {overhead_percentage:.1f}%'
        )
        assert time_overhead < 1.0, f'Absolute time overhead too high: {time_overhead:.3f}s'
        assert abs(memory_overhead) < 30.0, f'Memory overhead too high: {memory_overhead:.1f}MB'

        # Log performance comparison for analysis
        print('\nPerformance Benchmark Results:')
        print(
            f'Unfiltered: {unfiltered_metrics.execution_time:.3f}s, {unfiltered_metrics.peak_memory_delta:.1f}MB'
        )
        print(
            f'Filtered:   {filtered_metrics.execution_time:.3f}s, {filtered_metrics.peak_memory_delta:.1f}MB'
        )
        print(
            f'Overhead:   {time_overhead:.3f}s ({overhead_percentage:.1f}%), {memory_overhead:.1f}MB'
        )

    @pytest.mark.asyncio
    async def test_concurrent_filtering_performance(self, mock_context):
        """Test performance under concurrent filtering operations."""
        # Create dataset for concurrent testing
        concurrent_response = PaginationFixtures.create_large_dataset_response(
            num_autoscaling=60, num_non_autoscaling=15
        )

        async def single_filtering_operation():
            """Single filtering operation for concurrent testing."""
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = concurrent_response
                mock_client.get_paginator.return_value = mock_paginator
                mock_session.return_value.client.return_value = mock_client

                alarms_tools = CloudWatchAlarmsTools()
                return await alarms_tools.get_active_alarms(
                    mock_context, max_items=10, include_autoscaling_alarms=False
                )

        metrics = PerformanceMetrics()

        # Run 5 concurrent filtering operations
        metrics.start_measurement()
        concurrent_tasks = [single_filtering_operation() for _ in range(5)]
        results = await asyncio.gather(*concurrent_tasks)
        metrics.update_peak_memory()
        metrics.end_measurement()

        # Verify all operations completed successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 10

        # Performance should still be reasonable under concurrent load
        assert metrics.execution_time < 5.0, (
            f'Concurrent operations took too long: {metrics.execution_time:.3f}s'
        )
        assert metrics.peak_memory_delta < 150.0, (
            f'Concurrent memory usage too high: {metrics.peak_memory_delta:.1f}MB'
        )

    @pytest.mark.asyncio
    async def test_filtering_performance_with_complex_alarm_structures(self, mock_context):
        """Test filtering performance with complex alarm structures and mixed action types."""
        # Create complex alarms with various action combinations
        complex_alarms = []

        for i in range(100):
            if i % 4 == 0:
                # Autoscaling alarm with multiple actions
                alarm = AlarmFixtures.create_metric_alarm_with_autoscaling_alarm_actions()
                alarm['AlarmName'] = f'complex-autoscaling-{i}'
                alarm['AlarmActions'].extend(
                    [SNS_ALERT_ARN, f'arn:aws:lambda:us-east-1:123456789012:function:handler-{i}']
                )
            elif i % 4 == 1:
                # Mixed actions alarm (should be treated as autoscaling)
                alarm = AlarmFixtures.create_metric_alarm_with_mixed_actions()
                alarm['AlarmName'] = f'complex-mixed-{i}'
            elif i % 4 == 2:
                # Non-autoscaling alarm with multiple actions
                alarm = AlarmFixtures.create_metric_alarm_without_autoscaling_actions()
                alarm['AlarmName'] = f'complex-application-{i}'
                alarm['AlarmActions'].extend([f'arn:aws:sns:us-east-1:123456789012:topic-{i}'])
            else:
                # Empty actions alarm
                alarm = AlarmFixtures.create_metric_alarm_with_empty_actions()
                alarm['AlarmName'] = f'complex-empty-{i}'

            complex_alarms.append(alarm)

        # Distribute across pages
        complex_pages = []
        for i in range(0, len(complex_alarms), 10):
            page_alarms = complex_alarms[i : i + 10]
            complex_pages.append({'MetricAlarms': page_alarms, 'CompositeAlarms': []})

        metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = complex_pages
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            metrics.start_measurement()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=30, include_autoscaling_alarms=False
            )
            metrics.update_peak_memory()
            metrics.end_measurement()

            # Verify results - should only include non-autoscaling and empty action alarms
            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 30

            # Verify filtering worked correctly
            for alarm in result.metric_alarms:
                assert (
                    'complex-application-' in alarm.alarm_name
                    or 'complex-empty-' in alarm.alarm_name
                )
                assert 'complex-autoscaling-' not in alarm.alarm_name
                assert 'complex-mixed-' not in alarm.alarm_name

            # Performance should be good even with complex structures
            assert metrics.execution_time < 2.0, (
                f'Complex filtering took too long: {metrics.execution_time:.3f}s'
            )
            assert metrics.peak_memory_delta < 60.0, (
                f'Complex filtering memory usage too high: {metrics.peak_memory_delta:.1f}MB'
            )

    @pytest.mark.asyncio
    async def test_memory_stability_during_long_running_operations(self, mock_context):
        """Test memory stability during long-running filtering operations."""
        # Create a scenario that simulates long-running operations
        memory_measurements = []

        for iteration in range(10):  # 10 iterations to test memory stability
            # Create fresh dataset for each iteration
            iteration_response = PaginationFixtures.create_large_dataset_response(
                num_autoscaling=50 + iteration * 5,  # Gradually increasing size
                num_non_autoscaling=10 + iteration * 2,
            )

            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = iteration_response
                mock_client.get_paginator.return_value = mock_paginator
                mock_session.return_value.client.return_value = mock_client

                alarms_tools = CloudWatchAlarmsTools()

                # Measure memory before operation
                gc.collect()
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024

                # Request number of alarms that we know exist (non-autoscaling count)
                expected_non_autoscaling = 10 + iteration * 2
                max_items_to_request = min(expected_non_autoscaling, 15)

                result = await alarms_tools.get_active_alarms(
                    mock_context, max_items=max_items_to_request, include_autoscaling_alarms=False
                )

                # Measure memory after operation
                memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                memory_delta = memory_after - memory_before

                memory_measurements.append(
                    {
                        'iteration': iteration,
                        'memory_before': memory_before,
                        'memory_after': memory_after,
                        'memory_delta': memory_delta,
                        'alarms_processed': 50 + iteration * 5 + 10 + iteration * 2,
                        'expected_results': max_items_to_request,
                    }
                )

                # Verify operation succeeded
                assert len(result.metric_alarms) == max_items_to_request

                # Force cleanup
                del result
                gc.collect()

        # Analyze memory stability
        memory_deltas = [m['memory_delta'] for m in memory_measurements]
        max_memory_delta = max(memory_deltas)
        avg_memory_delta = sum(memory_deltas) / len(memory_deltas)

        # Memory usage should be stable across iterations
        assert max_memory_delta < 50.0, f'Maximum memory delta too high: {max_memory_delta:.1f}MB'
        assert avg_memory_delta < 25.0, f'Average memory delta too high: {avg_memory_delta:.1f}MB'

        # Memory usage should not grow significantly with iteration
        first_half_avg = sum(memory_deltas[:5]) / 5
        second_half_avg = sum(memory_deltas[5:]) / 5
        growth_ratio = second_half_avg / max(first_half_avg, 1.0)

        assert growth_ratio < 2.0, f'Memory growth too high across iterations: {growth_ratio:.2f}x'

    @pytest.mark.asyncio
    async def test_performance_regression_baseline(self, mock_context):
        """Establish performance baseline for regression testing."""
        # Standard test case for baseline measurement
        baseline_response = PaginationFixtures.create_large_dataset_response(
            num_autoscaling=100, num_non_autoscaling=25
        )

        metrics = PerformanceMetrics()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = baseline_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            metrics.start_measurement()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=20, include_autoscaling_alarms=False
            )
            metrics.update_peak_memory()
            metrics.end_measurement()

            # Verify results
            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 20

            # Establish baseline performance expectations
            baseline_time = metrics.execution_time
            baseline_memory = metrics.peak_memory_delta

            # Document baseline for future regression testing
            print('\nPerformance Baseline (125 alarms, 20 requested):')
            print(f'Execution time: {baseline_time:.3f}s')
            print(f'Peak memory delta: {baseline_memory:.1f}MB')

            # Set reasonable baseline thresholds
            assert baseline_time < 1.5, f'Baseline execution time too slow: {baseline_time:.3f}s'
            assert baseline_memory < 40.0, (
                f'Baseline memory usage too high: {baseline_memory:.1f}MB'
            )

            # These values can be used for future regression testing
            # If future changes cause performance to exceed these thresholds significantly,
            # it may indicate a performance regression
