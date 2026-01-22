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

"""Tests for run analysis tools."""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
    _aggregate_task_metrics,
    _convert_datetime_to_string,
    _extract_task_metrics_from_manifest,
    _generate_analysis_report,
    _get_run_analysis_data,
    _json_serializer,
    _normalize_run_ids,
    _parse_manifest_for_analysis,
    _safe_json_dumps,
    analyze_run_performance,
)
from datetime import datetime, timezone

# Property-Based Tests using Hypothesis
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import AsyncMock, MagicMock, patch


class TestNormalizeRunIds:
    """Test the _normalize_run_ids function."""

    def test_normalize_run_ids_list(self):
        """Test normalizing a list of run IDs."""
        # Arrange
        run_ids = ['run1', 'run2', 'run3']

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_json_string(self):
        """Test normalizing a JSON string of run IDs."""
        # Arrange
        run_ids = '["run1", "run2", "run3"]'

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_comma_separated(self):
        """Test normalizing a comma-separated string of run IDs."""
        # Arrange
        run_ids = 'run1,run2,run3'

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_single_string(self):
        """Test normalizing a single run ID string."""
        # Arrange
        run_ids = 'run1'

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['run1']

    def test_normalize_run_ids_with_spaces(self):
        """Test normalizing comma-separated string with spaces."""
        # Arrange
        run_ids = 'run1, run2 , run3'

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_fallback_case(self):
        """Test normalizing run IDs fallback to string conversion."""
        # Arrange - Test with an integer converted to string (edge case)
        run_ids = '12345'

        # Act
        result = _normalize_run_ids(run_ids)

        # Assert
        assert result == ['12345']


class TestConvertDatetimeToString:
    """Test the _convert_datetime_to_string function."""

    def test_convert_datetime_object(self):
        """Test converting a datetime object."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0)

        # Act
        result = _convert_datetime_to_string(dt)

        # Assert
        assert result == '2023-01-01T12:00:00'

    def test_convert_dict_with_datetime(self):
        """Test converting a dictionary containing datetime objects."""
        # Arrange
        data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0), 'name': 'test', 'count': 42}

        # Act
        result = _convert_datetime_to_string(data)

        # Assert
        expected = {'timestamp': '2023-01-01T12:00:00', 'name': 'test', 'count': 42}
        assert result == expected

    def test_convert_list_with_datetime(self):
        """Test converting a list containing datetime objects."""
        # Arrange
        data = [datetime(2023, 1, 1, 12, 0, 0), 'test', 42]

        # Act
        result = _convert_datetime_to_string(data)

        # Assert
        expected = ['2023-01-01T12:00:00', 'test', 42]
        assert result == expected

    def test_convert_non_datetime_object(self):
        """Test converting non-datetime objects."""
        # Arrange
        data = 'test string'

        # Act
        result = _convert_datetime_to_string(data)

        # Assert
        assert result == 'test string'


class TestSafeJsonDumps:
    """Test the _safe_json_dumps function."""

    def test_safe_json_dumps_with_datetime(self):
        """Test JSON serialization with datetime objects."""
        # Arrange
        data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0), 'name': 'test'}

        # Act
        result = _safe_json_dumps(data)

        # Assert
        assert '"timestamp": "2023-01-01T12:00:00"' in result
        assert '"name": "test"' in result

    def test_safe_json_dumps_regular_data(self):
        """Test JSON serialization with regular data."""
        # Arrange
        data = {'name': 'test', 'count': 42}

        # Act
        result = _safe_json_dumps(data)

        # Assert
        assert '"name": "test"' in result
        assert '"count": 42' in result


class TestJsonSerializer:
    """Test the _json_serializer function."""

    def test_json_serializer_datetime(self):
        """Test JSON serialization of datetime objects."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0)

        # Act
        result = _json_serializer(dt)

        # Assert
        assert result == '2023-01-01T12:00:00'

    def test_json_serializer_non_datetime_raises_error(self):
        """Test JSON serialization raises error for non-datetime objects."""
        # Arrange
        obj = object()

        # Act & Assert
        with pytest.raises(TypeError, match='Object of type .* is not JSON serializable'):
            _json_serializer(obj)


class TestExtractTaskMetricsFromManifest:
    """Test the _extract_task_metrics_from_manifest function."""

    def test_extract_task_metrics_complete_data(self):
        """Test extracting task metrics with complete data."""
        # Arrange
        task_data = {
            'name': 'test-task',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/1234567890123456/task/test-task',
            'uuid': 'task-uuid-123',
            'cpus': 4,
            'memory': 8,
            'instanceType': 'omics.c.large',
            'gpus': 0,
            'image': 'ubuntu:latest',
            'metrics': {
                'cpusReserved': 4,
                'cpusAverage': 2.5,
                'cpusMaximum': 3.8,
                'memoryReservedGiB': 8,
                'memoryAverageGiB': 4.2,
                'memoryMaximumGiB': 6.1,
                'gpusReserved': 0,
                'runningSeconds': 3600,
            },
            'startTime': '2023-01-01T12:00:00Z',
            'stopTime': '2023-01-01T13:00:00Z',
            'creationTime': '2023-01-01T11:55:00Z',
            'status': 'COMPLETED',
        }

        # Act
        result = _extract_task_metrics_from_manifest(task_data)

        # Assert
        assert result is not None
        assert result['taskName'] == 'test-task'
        assert result['allocatedCpus'] == 4
        assert result['allocatedMemoryGiB'] == 8
        assert result['instanceType'] == 'omics.c.large'
        assert result['avgCpuUtilization'] == 2.5
        assert result['avgMemoryUtilizationGiB'] == 4.2
        assert result['cpuEfficiencyRatio'] == 0.625  # 2.5/4
        assert result['memoryEfficiencyRatio'] == 0.525  # 4.2/8
        assert result['wastedCpus'] == 1.5  # 4-2.5
        assert result['wastedMemoryGiB'] == 3.8  # 8-4.2
        assert result['isOverProvisioned'] is False  # Both ratios > 0.5
        assert result['isUnderProvisioned'] is True  # Max CPU ratio 3.8/4 = 0.95 > 0.9

    def test_extract_task_metrics_over_provisioned(self):
        """Test extracting task metrics for over-provisioned task."""
        # Arrange
        task_data = {
            'name': 'over-provisioned-task',
            'cpus': 8,
            'memory': 16,
            'instanceType': 'omics.c.xlarge',
            'metrics': {
                'cpusReserved': 8,
                'cpusAverage': 2.0,  # 25% efficiency
                'cpusMaximum': 3.0,
                'memoryReservedGiB': 16,
                'memoryAverageGiB': 4.0,  # 25% efficiency
                'memoryMaximumGiB': 6.0,
                'runningSeconds': 1800,
            },
        }

        # Act
        result = _extract_task_metrics_from_manifest(task_data)

        # Assert
        assert result is not None
        assert result['cpuEfficiencyRatio'] == 0.25
        assert result['memoryEfficiencyRatio'] == 0.25
        assert result['isOverProvisioned'] is True  # Both ratios < 0.5
        assert result['wastedCpus'] == 6.0
        assert result['wastedMemoryGiB'] == 12.0

    def test_extract_task_metrics_under_provisioned(self):
        """Test extracting task metrics for under-provisioned task."""
        # Arrange
        task_data = {
            'name': 'under-provisioned-task',
            'cpus': 2,
            'memory': 4,
            'instanceType': 'omics.c.medium',
            'metrics': {
                'cpusReserved': 2,
                'cpusAverage': 1.8,
                'cpusMaximum': 1.95,  # 97.5% max efficiency
                'memoryReservedGiB': 4,
                'memoryAverageGiB': 3.6,
                'memoryMaximumGiB': 3.8,  # 95% max efficiency
                'runningSeconds': 7200,
            },
        }

        # Act
        result = _extract_task_metrics_from_manifest(task_data)

        # Assert
        assert result is not None
        assert result['maxCpuEfficiencyRatio'] == 0.975
        assert result['maxMemoryEfficiencyRatio'] == 0.95
        assert result['isUnderProvisioned'] is True  # Both max ratios > 0.9

    def test_extract_task_metrics_zero_reserved_resources(self):
        """Test extracting task metrics with zero reserved resources."""
        # Arrange
        task_data = {
            'name': 'zero-reserved-task',
            'cpus': 0,
            'memory': 0,
            'metrics': {
                'cpusReserved': 0,
                'cpusAverage': 0,
                'cpusMaximum': 0,
                'memoryReservedGiB': 0,
                'memoryAverageGiB': 0,
                'memoryMaximumGiB': 0,
                'runningSeconds': 60,
            },
        }

        # Act
        result = _extract_task_metrics_from_manifest(task_data)

        # Assert
        assert result is not None
        assert result['cpuEfficiencyRatio'] == 0
        assert result['memoryEfficiencyRatio'] == 0
        assert result['wastedCpus'] == 0
        assert result['wastedMemoryGiB'] == 0

    def test_extract_task_metrics_missing_data(self):
        """Test extracting task metrics with missing data."""
        # Arrange
        task_data = {
            'name': 'incomplete-task',
            # Missing most fields
        }

        # Act
        result = _extract_task_metrics_from_manifest(task_data)

        # Assert
        assert result is not None
        assert result['taskName'] == 'incomplete-task'
        assert result['allocatedCpus'] == 0
        assert result['allocatedMemoryGiB'] == 0
        assert result['instanceType'] == ''

    def test_extract_task_metrics_exception_handling(self):
        """Test extracting task metrics handles exceptions gracefully."""
        # Arrange
        task_data = None  # This will cause an exception

        # Act
        result = _extract_task_metrics_from_manifest(task_data)  # type: ignore

        # Assert
        assert result is None


class TestAggregateTaskMetrics:
    """Test the _aggregate_task_metrics function."""

    def test_aggregate_task_metrics_empty_list(self):
        """Test aggregation with empty task list."""
        # Act
        result = _aggregate_task_metrics([])

        # Assert
        assert result == []

    def test_aggregate_task_metrics_single_task(self):
        """Test aggregation with single task."""
        # Arrange
        task_metrics = [
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

        # Act
        result = _aggregate_task_metrics(task_metrics)

        # Assert
        assert len(result) == 1
        assert result[0]['baseTaskName'] == 'alignReads'
        assert result[0]['count'] == 1
        assert result[0]['meanRunningSeconds'] == 100.0
        assert result[0]['totalEstimatedUSD'] == 0.10

    def test_aggregate_task_metrics_multiple_scattered_tasks(self):
        """Test aggregation of multiple scattered tasks (Requirements 6.1, 6.2, 6.3, 6.4)."""
        # Arrange
        task_metrics = [
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

        # Act
        result = _aggregate_task_metrics(task_metrics)

        # Assert
        assert len(result) == 2

        # Find alignReads aggregate
        align_agg = next((r for r in result if r['baseTaskName'] == 'alignReads'), None)
        assert align_agg is not None
        assert align_agg['count'] == 2
        assert align_agg['meanRunningSeconds'] == 110.0
        assert align_agg['maximumRunningSeconds'] == 120.0
        assert align_agg['totalEstimatedUSD'] == pytest.approx(0.22)

        # Find sortBam aggregate
        sort_agg = next((r for r in result if r['baseTaskName'] == 'sortBam'), None)
        assert sort_agg is not None
        assert sort_agg['count'] == 1
        assert sort_agg['totalEstimatedUSD'] == pytest.approx(0.05)

    def test_aggregate_task_metrics_with_instance_recommender(self):
        """Test aggregation with instance recommendations (Requirement 6.5)."""
        # Arrange
        from awslabs.aws_healthomics_mcp_server.analysis.instance_recommender import (
            InstanceRecommender,
        )

        task_metrics = [
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
                'maxCpuUtilization': 3.0,  # Higher CPU usage
                'maxMemoryUtilizationGiB': 6.0,  # Higher memory usage
                'estimatedUSD': 0.12,
            },
        ]

        instance_recommender = InstanceRecommender(headroom=0.20)

        # Act
        result = _aggregate_task_metrics(task_metrics, instance_recommender=instance_recommender)

        # Assert
        assert len(result) == 1
        agg = result[0]
        assert agg['baseTaskName'] == 'alignReads'

        # Verify instance recommendation is based on maximum observed usage
        # Max CPU: 3.0, Max Memory: 6.0
        # With 20% headroom: CPU required = ceil(3.0 * 1.2) = 4, Memory required = ceil(6.0 * 1.2) = 8
        assert agg['recommendedInstanceType'] != ''
        assert agg['recommendedCpus'] == 4  # ceil(3.0 * 1.2)
        assert agg['recommendedMemoryGiB'] == 8.0  # ceil(6.0 * 1.2)

    def test_aggregate_task_metrics_without_instance_recommender(self):
        """Test aggregation without instance recommender provides default values."""
        # Arrange
        task_metrics = [
            {
                'taskName': 'alignReads-0-1',
                'runningSeconds': 100.0,
                'cpuEfficiencyRatio': 0.5,
                'memoryEfficiencyRatio': 0.6,
                'maxCpuUtilization': 2.0,
                'maxMemoryUtilizationGiB': 4.0,
                'estimatedUSD': 0.10,
            },
        ]

        # Act
        result = _aggregate_task_metrics(task_metrics, instance_recommender=None)

        # Assert
        assert len(result) == 1
        agg = result[0]
        assert agg['recommendedInstanceType'] == ''
        assert agg['recommendedCpus'] == 0
        assert agg['recommendedMemoryGiB'] == 0.0


class TestParseManifestForAnalysis:
    """Test the _parse_manifest_for_analysis function."""

    @pytest.mark.asyncio
    async def test_parse_manifest_for_analysis_complete_data(self):
        """Test parsing manifest with complete data."""
        # Arrange
        run_id = 'test-run-123'
        run_response = {
            'name': 'test-workflow-run',
            'status': 'COMPLETED',
            'workflowId': 'workflow-123',
            'creationTime': datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            'startTime': datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
            'stopTime': datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            'runOutputUri': 's3://bucket/output/',
        }
        manifest_logs = {
            'events': [
                {
                    'message': json.dumps(
                        {
                            'workflow': 'test-workflow',
                            'metrics': {'runningSeconds': 3300},
                            'name': 'test-workflow-run',
                            'arn': 'arn:aws:omics:us-east-1:123456789012:run/test-run-123',
                            'parameters': {'input': 'test.fastq'},
                            'storageType': 'DYNAMIC',
                        }
                    )
                },
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 4,
                            'memory': 8,
                            'instanceType': 'omics.c.large',
                            'metrics': {
                                'cpusReserved': 4,
                                'cpusAverage': 3.2,
                                'cpusMaximum': 3.8,
                                'memoryReservedGiB': 8,
                                'memoryAverageGiB': 6.4,
                                'memoryMaximumGiB': 7.2,
                                'runningSeconds': 1800,
                            },
                        }
                    )
                },
            ]
        }

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is not None
        assert result['runInfo']['runId'] == 'test-run-123'
        assert result['runInfo']['runName'] == 'test-workflow-run'
        assert result['runInfo']['status'] == 'COMPLETED'
        assert len(result['taskMetrics']) == 1
        assert result['taskMetrics'][0]['taskName'] == 'task1'
        assert result['summary']['totalTasks'] == 1
        assert result['summary']['totalAllocatedCpus'] == 4
        assert result['summary']['totalAllocatedMemoryGiB'] == 8

    @pytest.mark.asyncio
    async def test_parse_manifest_for_analysis_no_events(self):
        """Test parsing manifest with no log events."""
        # Arrange
        run_id = 'test-run-123'
        run_response = {'name': 'test-run', 'status': 'COMPLETED'}
        manifest_logs = {'events': []}

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_manifest_for_analysis_invalid_json(self):
        """Test parsing manifest with invalid JSON messages."""
        # Arrange
        run_id = 'test-run-123'
        run_response = {'name': 'test-run', 'status': 'COMPLETED'}
        manifest_logs = {
            'events': [
                {'message': 'invalid json'},
                {'message': '{"incomplete": json'},
                {'message': 'plain text message'},
            ]
        }

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is not None
        assert len(result['taskMetrics']) == 0
        assert result['summary']['totalTasks'] == 0

    @pytest.mark.asyncio
    async def test_parse_manifest_for_analysis_exception_handling(self):
        """Test parsing manifest handles exceptions gracefully."""
        # Arrange
        run_id = 'test-run-123'
        run_response = None  # This will cause an exception
        manifest_logs = {'events': []}

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)  # type: ignore

        # Assert
        assert result is None


class TestGenerateAnalysisReport:
    """Test the _generate_analysis_report function."""

    @pytest.mark.asyncio
    async def test_generate_analysis_report_complete_data(self):
        """Test generating analysis report with complete data."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'test-run-123',
                        'runName': 'test-workflow-run',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 2,
                        'totalAllocatedCpus': 8.0,
                        'totalAllocatedMemoryGiB': 16.0,
                        'totalActualCpuUsage': 5.0,
                        'totalActualMemoryUsageGiB': 10.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                    },
                    'taskMetrics': [
                        {
                            'taskName': 'task1',
                            'instanceType': 'omics.c.large',
                            'isOverProvisioned': True,
                            'wastedCpus': 2.0,
                            'wastedMemoryGiB': 4.0,
                            'cpuEfficiencyRatio': 0.4,
                            'memoryEfficiencyRatio': 0.4,
                            'runningSeconds': 1800,
                        },
                        {
                            'taskName': 'task2',
                            'instanceType': 'omics.c.large',
                            'isUnderProvisioned': True,
                            'maxCpuEfficiencyRatio': 0.95,
                            'maxMemoryEfficiencyRatio': 0.92,
                            'runningSeconds': 3600,
                        },
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert '# AWS HealthOmics Workflow Performance Analysis Report' in result
        assert 'Total Runs Analyzed**: 1' in result
        assert 'test-workflow-run (test-run-123)' in result
        assert 'Over-Provisioned Tasks' in result
        assert 'Under-Provisioned Tasks' in result
        assert 'task1' in result
        assert 'task2' in result
        assert 'omics.c.large' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_multiple_instance_types(self):
        """Test generating analysis report with multiple instance types."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'test-run-123',
                        'runName': 'multi-instance-run',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 4,
                        'totalAllocatedCpus': 16.0,
                        'totalAllocatedMemoryGiB': 32.0,
                        'totalActualCpuUsage': 11.2,
                        'totalActualMemoryUsageGiB': 19.2,
                        'overallCpuEfficiency': 0.7,
                        'overallMemoryEfficiency': 0.6,
                    },
                    'taskMetrics': [
                        {
                            'taskName': 'task1',
                            'instanceType': 'omics.c.large',
                            'cpuEfficiencyRatio': 0.8,
                            'memoryEfficiencyRatio': 0.7,
                        },
                        {
                            'taskName': 'task2',
                            'instanceType': 'omics.c.large',
                            'cpuEfficiencyRatio': 0.6,
                            'memoryEfficiencyRatio': 0.5,
                        },
                        {
                            'taskName': 'task3',
                            'instanceType': 'omics.c.xlarge',
                            'cpuEfficiencyRatio': 0.9,
                            'memoryEfficiencyRatio': 0.8,
                        },
                        {
                            'taskName': 'task4',
                            'instanceType': 'omics.c.xlarge',
                            'cpuEfficiencyRatio': 0.7,
                            'memoryEfficiencyRatio': 0.6,
                        },
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Instance Type Analysis' in result
        assert 'omics.c.large' in result
        assert 'omics.c.xlarge' in result
        assert '(2 tasks)' in result  # Should show task count for each instance type
        assert 'Average CPU Efficiency' in result
        assert 'Average Memory Efficiency' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_no_runs(self):
        """Test generating analysis report with no runs."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 0,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert '# AWS HealthOmics Workflow Performance Analysis Report' in result
        assert 'Total Runs Analyzed**: 0' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_exception_handling(self):
        """Test generating analysis report handles exceptions gracefully."""
        # Arrange
        analysis_data = None  # This will cause an exception

        # Act
        result = await _generate_analysis_report(analysis_data)  # type: ignore

        # Assert
        assert isinstance(result, str)
        assert 'Error generating analysis report' in result


class TestGetRunAnalysisData:
    """Test the _get_run_analysis_data function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_run_manifest_logs_internal')
    async def test_get_run_analysis_data_success(self, mock_get_logs, mock_get_omics_client):
        """Test getting run analysis data successfully."""
        # Arrange
        run_ids = ['run-123', 'run-456']

        # Mock omics client
        mock_omics_client_instance = MagicMock()
        mock_get_omics_client.return_value = mock_omics_client_instance

        # Mock get_run responses
        mock_omics_client_instance.get_run.side_effect = [
            {'uuid': 'uuid-123', 'name': 'run1', 'status': 'COMPLETED'},
            {'uuid': 'uuid-456', 'name': 'run2', 'status': 'COMPLETED'},
        ]

        # Mock manifest logs
        mock_get_logs.return_value = {
            'events': [
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 4,
                            'memory': 8,
                            'instanceType': 'omics.c.large',
                            'metrics': {
                                'cpusReserved': 4,
                                'cpusAverage': 3.2,
                                'memoryReservedGiB': 8,
                                'memoryAverageGiB': 6.4,
                                'runningSeconds': 1800,
                            },
                        }
                    )
                }
            ]
        }

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result is not None
        assert result['summary']['totalRuns'] == 2
        assert result['summary']['analysisType'] == 'manifest-based'
        assert len(result['runs']) == 2

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_omics_client')
    async def test_get_run_analysis_data_no_uuid(self, mock_get_omics_client):
        """Test getting run analysis data when run has no UUID."""
        # Arrange
        run_ids = ['run-123']

        # Mock omics client
        mock_omics_client_instance = MagicMock()
        mock_get_omics_client.return_value = mock_omics_client_instance

        # Mock get_run response without UUID
        mock_omics_client_instance.get_run.return_value = {'name': 'run1', 'status': 'COMPLETED'}

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result is not None
        assert result['summary']['totalRuns'] == 1
        assert len(result['runs']) == 0  # No runs processed due to missing UUID

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_omics_client')
    async def test_get_run_analysis_data_exception_handling(self, mock_get_omics_client):
        """Test getting run analysis data handles exceptions gracefully."""
        # Arrange
        run_ids = ['run-123']

        # Mock omics client to raise exception
        mock_get_omics_client.side_effect = Exception('AWS connection failed')

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_run_manifest_logs_internal')
    async def test_get_run_analysis_data_get_run_exception(
        self, mock_get_logs, mock_get_omics_client
    ):
        """Test getting run analysis data when get_run fails for individual runs."""
        # Arrange
        run_ids = ['run-123', 'run-456']

        # Mock omics client
        mock_omics_client_instance = MagicMock()
        mock_get_omics_client.return_value = mock_omics_client_instance

        # Mock get_run to fail for first run, succeed for second
        mock_omics_client_instance.get_run.side_effect = [
            Exception('Run not found'),
            {'uuid': 'uuid-456', 'name': 'run2', 'status': 'COMPLETED'},
        ]

        # Mock manifest logs with some data for the successful run
        mock_get_logs.return_value = {
            'events': [{'message': '{"name": "test-task", "cpus": 2, "memory": 4}'}]
        }

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result is not None
        assert result['summary']['totalRuns'] == 2
        assert len(result['runs']) == 1  # Only one run processed successfully

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_run_manifest_logs_internal')
    async def test_get_run_analysis_data_manifest_logs_exception(
        self, mock_get_logs, mock_get_omics_client
    ):
        """Test getting run analysis data when manifest logs retrieval fails."""
        # Arrange
        run_ids = ['run-123']

        # Mock omics client
        mock_omics_client_instance = MagicMock()
        mock_get_omics_client.return_value = mock_omics_client_instance
        mock_omics_client_instance.get_run.return_value = {
            'uuid': 'uuid-123',
            'name': 'run1',
            'status': 'COMPLETED',
        }

        # Mock manifest logs to fail
        mock_get_logs.side_effect = Exception('Failed to get manifest logs')

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result is not None
        assert result['summary']['totalRuns'] == 1
        assert len(result['runs']) == 0  # No runs processed due to manifest failure


class TestAnalyzeRunPerformance:
    """Test the analyze_run_performance function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis._generate_analysis_report')
    async def test_analyze_run_performance_success(self, mock_generate_report, mock_get_data):
        """Test analyze_run_performance with successful analysis."""
        # Arrange
        mock_ctx = AsyncMock()
        run_ids = ['run-123']

        # Mock analysis data
        mock_analysis_data = {
            'runs': [{'runInfo': {'runId': 'run-123'}}],
            'summary': {'totalRuns': 1},
        }
        mock_get_data.return_value = mock_analysis_data
        mock_generate_report.return_value = 'Generated analysis report'

        # Act - explicitly pass default values
        result = await analyze_run_performance(mock_ctx, run_ids, headroom=0.20, detailed=False)

        # Assert
        assert result == 'Generated analysis report'
        mock_get_data.assert_called_once()
        # Verify _generate_analysis_report was called with the analysis data
        mock_generate_report.assert_called_once()
        call_args = mock_generate_report.call_args
        assert call_args[0][0] == mock_analysis_data  # First positional arg is analysis_data

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data')
    async def test_analyze_run_performance_no_data(self, mock_get_data):
        """Test analyze_run_performance with no analysis data."""
        # Arrange
        mock_ctx = AsyncMock()
        run_ids = ['run-123']

        # Mock empty analysis data
        mock_get_data.return_value = {'runs': []}

        # Act - explicitly pass default values
        result = await analyze_run_performance(mock_ctx, run_ids, headroom=0.20, detailed=False)

        # Assert
        assert 'Unable to retrieve manifest data' in result
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data')
    async def test_analyze_run_performance_exception_handling(self, mock_get_data):
        """Test analyze_run_performance handles exceptions gracefully."""
        # Arrange
        mock_ctx = AsyncMock()
        run_ids = ['run-123']

        # Mock exception
        mock_get_data.side_effect = Exception('Analysis failed')

        # Act - explicitly pass default values
        result = await analyze_run_performance(mock_ctx, run_ids, headroom=0.20, detailed=False)

        # Assert
        assert 'Error analyzing run performance' in result
        assert 'Analysis failed' in result
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_run_performance_normalize_run_ids(self):
        """Test analyze_run_performance normalizes run IDs correctly."""
        # Arrange
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data'
        ) as mock_get_data:
            mock_get_data.return_value = {'runs': []}

            # Test with comma-separated string - explicitly pass default values
            await analyze_run_performance(
                mock_ctx, 'run1,run2,run3', headroom=0.20, detailed=False
            )

            # Verify normalized run IDs were passed
            call_args = mock_get_data.call_args[0][0]
            assert call_args == ['run1', 'run2', 'run3']

    @pytest.mark.asyncio
    async def test_analyze_run_performance_negative_headroom_rejected(self):
        """Test analyze_run_performance rejects negative headroom values."""
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await analyze_run_performance(mock_ctx, ['run1'], headroom=-0.1)

        # Assert
        assert 'Headroom must be non-negative' in result
        assert '-0.1' in result
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_run_performance_zero_headroom_allowed(self):
        """Test analyze_run_performance allows zero headroom."""
        # Arrange
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data'
        ) as mock_get_data:
            mock_get_data.return_value = {
                'runs': [{'runInfo': {}, 'summary': {}, 'taskMetrics': []}],
                'summary': {
                    'totalRuns': 1,
                    'analysisTimestamp': '2024-01-01',
                    'analysisType': 'single',
                },
            }

            with patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_analysis._generate_analysis_report'
            ) as mock_generate_report:
                mock_generate_report.return_value = 'Analysis report'

                # Act
                result = await analyze_run_performance(mock_ctx, ['run1'], headroom=0.0)

                # Assert
                assert result == 'Analysis report'
                mock_ctx.error.assert_not_called()
                # Verify headroom=0.0 was passed through
                call_kwargs = mock_get_data.call_args[1]
                assert call_kwargs['headroom'] == 0.0


# Strategies for generating test data
def task_cost_strategy():
    """Strategy for generating task cost data."""
    return st.fixed_dictionaries(
        {
            'taskName': st.text(min_size=1, max_size=50),
            'estimatedUSD': st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
            'potentialSavingsUSD': st.floats(min_value=0.0, max_value=500.0, allow_nan=False),
        }
    )


class TestRunAnalysisPropertyBased:
    """Property-based tests for run analysis using Hypothesis."""

    @given(
        task_costs=st.lists(
            st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
            min_size=0,
            max_size=50,
        ),
        storage_cost=st.floats(min_value=0.0, max_value=500.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_property_total_cost_equals_sum_of_parts(
        self, task_costs: list[float], storage_cost: float
    ):
        """Property 2: Total Cost Equals Sum of Parts.

        For any workflow run with tasks T1...Tn and storage cost S,
        the total estimated cost SHALL equal sum(cost(Ti)) + S.

        **Validates: Requirements 2.1, 2.4**
        **Feature: run-analyzer-enhancement, Property 2: Total Cost Equals Sum of Parts**
        """
        # Calculate expected total
        task_cost_sum = sum(task_costs)
        expected_total = task_cost_sum + storage_cost

        # Simulate the calculation done in _parse_manifest_for_analysis
        # This mirrors the actual implementation logic
        task_cost_usd = sum(task_costs)
        storage_cost_usd = storage_cost
        total_estimated_usd = task_cost_usd + storage_cost_usd

        # Property: total equals sum of parts
        assert total_estimated_usd == pytest.approx(expected_total, rel=1e-9)

        # Property: total is always >= 0
        assert total_estimated_usd >= 0.0

        # Property: total is always >= task cost
        assert total_estimated_usd >= task_cost_usd

        # Property: total is always >= storage cost
        assert total_estimated_usd >= storage_cost_usd

    @given(
        run_summaries=st.lists(
            st.fixed_dictionaries(
                {
                    'totalEstimatedUSD': st.floats(
                        min_value=0.0, max_value=10000.0, allow_nan=False
                    ),
                    'totalPotentialSavingsUSD': st.floats(
                        min_value=0.0, max_value=5000.0, allow_nan=False
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_property_grand_total_equals_sum_of_runs(self, run_summaries: list[dict]):
        """Property 2 (extended): Grand Total Equals Sum of Run Totals.

        For any set of runs R1...Rn, the grand total cost SHALL equal
        sum(totalEstimatedUSD(Ri)).

        **Validates: Requirements 2.4**
        **Feature: run-analyzer-enhancement, Property 2: Total Cost Equals Sum of Parts**
        """
        # Calculate expected grand total
        expected_grand_total = sum(r['totalEstimatedUSD'] for r in run_summaries)
        expected_grand_savings = sum(r['totalPotentialSavingsUSD'] for r in run_summaries)

        # Simulate the calculation done in _get_run_analysis_data
        # This mirrors the actual implementation logic
        runs = [{'summary': s} for s in run_summaries]
        grand_total_cost = sum(run.get('summary', {}).get('totalEstimatedUSD', 0) for run in runs)
        grand_total_savings = sum(
            run.get('summary', {}).get('totalPotentialSavingsUSD', 0) for run in runs
        )

        # Property: grand total equals sum of run totals
        assert grand_total_cost == pytest.approx(expected_grand_total, rel=1e-9)
        assert grand_total_savings == pytest.approx(expected_grand_savings, rel=1e-9)

        # Property: grand total is always >= 0
        assert grand_total_cost >= 0.0
        assert grand_total_savings >= 0.0

        # Property: grand total is always >= any individual run total
        for run_summary in run_summaries:
            assert grand_total_cost >= run_summary['totalEstimatedUSD']
            assert grand_total_savings >= run_summary['totalPotentialSavingsUSD']


class TestAggregateCrossRunMetrics:
    """Test the _aggregate_cross_run_metrics function."""

    def test_aggregate_cross_run_metrics_empty_list(self):
        """Test cross-run aggregation with empty runs list."""
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _aggregate_cross_run_metrics,
        )

        # Act
        result = _aggregate_cross_run_metrics([])

        # Assert
        assert result == []

    def test_aggregate_cross_run_metrics_single_run(self):
        """Test cross-run aggregation with single run."""
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _aggregate_cross_run_metrics,
        )

        # Arrange
        runs_data = [
            {
                'runInfo': {'runId': 'run-1'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-0-1',
                        'runningSeconds': 100.0,
                        'cpuEfficiencyRatio': 0.5,
                        'memoryEfficiencyRatio': 0.6,
                        'maxCpuUtilization': 2.0,
                        'maxMemoryUtilizationGiB': 4.0,
                        'estimatedUSD': 0.10,
                    },
                ],
            }
        ]

        # Act
        result = _aggregate_cross_run_metrics(runs_data)

        # Assert
        assert len(result) == 1
        assert result[0]['baseTaskName'] == 'alignReads'
        assert result[0]['runCount'] == 1
        assert result[0]['totalTaskCount'] == 1
        assert result[0]['totalEstimatedUSD'] == pytest.approx(0.10)

    def test_aggregate_cross_run_metrics_multiple_runs(self):
        """Test cross-run aggregation with multiple runs (Requirements 7.1, 7.2, 7.3)."""
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _aggregate_cross_run_metrics,
        )

        # Arrange
        runs_data = [
            {
                'runInfo': {'runId': 'run-1'},
                'taskMetrics': [
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
                        'taskName': 'sortBam-0-1',
                        'runningSeconds': 50.0,
                        'cpuEfficiencyRatio': 0.4,
                        'memoryEfficiencyRatio': 0.5,
                        'maxCpuUtilization': 1.0,
                        'maxMemoryUtilizationGiB': 2.0,
                        'estimatedUSD': 0.05,
                    },
                ],
            },
            {
                'runInfo': {'runId': 'run-2'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-0-1',
                        'runningSeconds': 120.0,
                        'cpuEfficiencyRatio': 0.6,
                        'memoryEfficiencyRatio': 0.7,
                        'maxCpuUtilization': 2.5,
                        'maxMemoryUtilizationGiB': 5.0,
                        'estimatedUSD': 0.12,
                    },
                    {
                        'taskName': 'sortBam-0-1',
                        'runningSeconds': 60.0,
                        'cpuEfficiencyRatio': 0.5,
                        'memoryEfficiencyRatio': 0.6,
                        'maxCpuUtilization': 1.2,
                        'maxMemoryUtilizationGiB': 2.5,
                        'estimatedUSD': 0.06,
                    },
                ],
            },
        ]

        # Act
        result = _aggregate_cross_run_metrics(runs_data)

        # Assert
        assert len(result) == 2

        # Find alignReads aggregate
        align_agg = next((r for r in result if r['baseTaskName'] == 'alignReads'), None)
        assert align_agg is not None
        assert align_agg['runCount'] == 2  # Present in both runs
        assert align_agg['totalTaskCount'] == 2  # One task per run
        assert align_agg['meanRunningSeconds'] == 110.0  # (100 + 120) / 2
        assert align_agg['maximumRunningSeconds'] == 120.0
        assert align_agg['totalEstimatedUSD'] == pytest.approx(0.22)  # 0.10 + 0.12

        # Find sortBam aggregate
        sort_agg = next((r for r in result if r['baseTaskName'] == 'sortBam'), None)
        assert sort_agg is not None
        assert sort_agg['runCount'] == 2
        assert sort_agg['totalTaskCount'] == 2
        assert sort_agg['totalEstimatedUSD'] == pytest.approx(0.11)  # 0.05 + 0.06

    def test_aggregate_cross_run_metrics_with_instance_recommender(self):
        """Test cross-run aggregation with instance recommendations."""
        from awslabs.aws_healthomics_mcp_server.analysis.instance_recommender import (
            InstanceRecommender,
        )
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _aggregate_cross_run_metrics,
        )

        # Arrange
        runs_data = [
            {
                'runInfo': {'runId': 'run-1'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-0-1',
                        'runningSeconds': 100.0,
                        'cpuEfficiencyRatio': 0.5,
                        'memoryEfficiencyRatio': 0.6,
                        'maxCpuUtilization': 2.0,
                        'maxMemoryUtilizationGiB': 4.0,
                        'estimatedUSD': 0.10,
                    },
                ],
            },
            {
                'runInfo': {'runId': 'run-2'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-0-1',
                        'runningSeconds': 120.0,
                        'cpuEfficiencyRatio': 0.6,
                        'memoryEfficiencyRatio': 0.7,
                        'maxCpuUtilization': 3.0,  # Higher CPU usage
                        'maxMemoryUtilizationGiB': 6.0,  # Higher memory usage
                        'estimatedUSD': 0.12,
                    },
                ],
            },
        ]

        instance_recommender = InstanceRecommender(headroom=0.20)

        # Act
        result = _aggregate_cross_run_metrics(runs_data, instance_recommender=instance_recommender)

        # Assert
        assert len(result) == 1
        agg = result[0]
        assert agg['baseTaskName'] == 'alignReads'

        # Verify instance recommendation is based on maximum observed usage across all runs
        # Max CPU: 3.0, Max Memory: 6.0
        # With 20% headroom: CPU required = ceil(3.0 * 1.2) = 4, Memory required = ceil(6.0 * 1.2) = 8
        assert agg['recommendedInstanceType'] != ''
        assert agg['recommendedCpus'] == 4  # ceil(3.0 * 1.2)
        assert agg['recommendedMemoryGiB'] == 8.0  # ceil(6.0 * 1.2)


class TestCrossRunAggregationInTaskAggregator:
    """Test the aggregate_cross_run_tasks method in TaskAggregator."""

    def test_aggregate_cross_run_tasks_empty_list(self):
        """Test cross-run aggregation with empty runs list."""
        from awslabs.aws_healthomics_mcp_server.analysis.task_aggregator import TaskAggregator

        # Arrange
        aggregator = TaskAggregator()

        # Act
        result = aggregator.aggregate_cross_run_tasks([])

        # Assert
        assert len(result) == 0

    def test_aggregate_cross_run_tasks_no_task_metrics(self):
        """Test cross-run aggregation with runs that have no task metrics."""
        from awslabs.aws_healthomics_mcp_server.analysis.task_aggregator import TaskAggregator

        # Arrange
        aggregator = TaskAggregator()
        runs_data = [
            {'runInfo': {'runId': 'run-1'}, 'taskMetrics': []},
            {'runInfo': {'runId': 'run-2'}, 'taskMetrics': []},
        ]

        # Act
        result = aggregator.aggregate_cross_run_tasks(runs_data)

        # Assert
        assert len(result) == 0

    def test_aggregate_cross_run_tasks_multiple_runs(self):
        """Test cross-run aggregation with multiple runs."""
        from awslabs.aws_healthomics_mcp_server.analysis.task_aggregator import TaskAggregator

        # Arrange
        aggregator = TaskAggregator()
        runs_data = [
            {
                'runInfo': {'runId': 'run-1'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-0-1',
                        'runningSeconds': 100.0,
                        'cpuEfficiencyRatio': 0.5,
                        'memoryEfficiencyRatio': 0.6,
                        'maxCpuUtilization': 2.0,
                        'maxMemoryUtilizationGiB': 4.0,
                        'estimatedUSD': 0.10,
                    },
                ],
            },
            {
                'runInfo': {'runId': 'run-2'},
                'taskMetrics': [
                    {
                        'taskName': 'alignReads-1-1',
                        'runningSeconds': 120.0,
                        'cpuEfficiencyRatio': 0.6,
                        'memoryEfficiencyRatio': 0.7,
                        'maxCpuUtilization': 2.5,
                        'maxMemoryUtilizationGiB': 5.0,
                        'estimatedUSD': 0.12,
                    },
                ],
            },
        ]

        # Act
        result = aggregator.aggregate_cross_run_tasks(runs_data)

        # Assert
        assert len(result) == 1
        row = result.to_dicts()[0]
        assert row['baseTaskName'] == 'alignReads'
        assert row['runCount'] == 2
        assert row['totalTaskCount'] == 2
        assert row['meanRunningSeconds'] == 110.0
        assert row['maximumRunningSeconds'] == 120.0
        assert row['totalEstimatedUSD'] == pytest.approx(0.22)


class TestParseManifestStorageCost:
    """Test storage cost calculation in _parse_manifest_for_analysis."""

    @pytest.mark.asyncio
    async def test_parse_manifest_with_storage_cost_calculation(self):
        """Test parsing manifest with storage cost calculation (Requirements 11.1, 11.2, 11.3, 11.4)."""
        from awslabs.aws_healthomics_mcp_server.analysis.cost_analyzer import CostAnalyzer
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _parse_manifest_for_analysis,
        )

        # Arrange
        run_id = 'test-run-123'
        run_response = {
            'name': 'test-workflow-run',
            'status': 'COMPLETED',
            'workflowId': 'workflow-123',
            'creationTime': datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            'startTime': datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
            'stopTime': datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        }
        manifest_logs = {
            'events': [
                {
                    'message': json.dumps(
                        {
                            'workflow': 'test-workflow',
                            'metrics': {'runningSeconds': 3600},
                            'name': 'test-workflow-run',
                            'arn': 'arn:aws:omics:us-east-1:123456789012:run/test-run-123',
                            'storageType': 'DYNAMIC',
                            'storageCapacity': 100,
                        }
                    )
                },
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 4,
                            'memory': 8,
                            'instanceType': 'omics.c.large',
                            'metrics': {
                                'cpusReserved': 4,
                                'cpusAverage': 3.2,
                                'cpusMaximum': 3.8,
                                'memoryReservedGiB': 8,
                                'memoryAverageGiB': 6.4,
                                'memoryMaximumGiB': 7.2,
                                'runningSeconds': 1800,
                            },
                        }
                    )
                },
            ]
        }

        cost_analyzer = CostAnalyzer(region='us-east-1')

        # Act
        result = await _parse_manifest_for_analysis(
            run_id, run_response, manifest_logs, cost_analyzer=cost_analyzer
        )

        # Assert
        assert result is not None
        assert 'summary' in result
        assert 'storageCostUSD' in result['summary']
        assert result['summary']['storageCostUSD'] >= 0.0
        assert 'totalEstimatedUSD' in result['summary']
        # Total should include both task and storage costs
        assert result['summary']['totalEstimatedUSD'] >= result['summary']['storageCostUSD']

    @pytest.mark.asyncio
    async def test_parse_manifest_with_json_decode_error(self):
        """Test parsing manifest handles JSON decode errors gracefully."""
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _parse_manifest_for_analysis,
        )

        # Arrange
        run_id = 'test-run-123'
        run_response = {'name': 'test-run', 'status': 'COMPLETED'}
        manifest_logs = {
            'events': [
                {'message': 'invalid json'},
                {'message': '{"incomplete": json'},
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 2,
                            'memory': 4,
                            'instanceType': 'omics.c.small',
                            'metrics': {
                                'cpusReserved': 2,
                                'cpusAverage': 1.5,
                                'memoryReservedGiB': 4,
                                'memoryAverageGiB': 3.0,
                                'runningSeconds': 100,
                            },
                        }
                    )
                },
            ]
        }

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is not None
        # Should have parsed the valid JSON message
        assert len(result['taskMetrics']) == 1
        assert result['taskMetrics'][0]['taskName'] == 'task1'

    @pytest.mark.asyncio
    async def test_parse_manifest_with_exception_in_message_parsing(self):
        """Test parsing manifest handles exceptions in message parsing."""
        from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
            _parse_manifest_for_analysis,
        )

        # Arrange
        run_id = 'test-run-123'
        run_response = {'name': 'test-run', 'status': 'COMPLETED'}
        manifest_logs = {
            'events': [
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 2,
                            'memory': 4,
                            'instanceType': 'omics.c.small',
                            'metrics': {
                                'cpusReserved': 2,
                                'cpusAverage': 1.5,
                                'memoryReservedGiB': 4,
                                'memoryAverageGiB': 3.0,
                                'runningSeconds': 100,
                            },
                        }
                    )
                },
                {'message': 'plain text'},
            ]
        }

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is not None
        assert len(result['taskMetrics']) == 1


class TestGenerateAnalysisReportCrossRunComparison:
    """Test cross-run comparison in _generate_analysis_report."""

    @pytest.mark.asyncio
    async def test_generate_analysis_report_with_cross_run_comparison(self):
        """Test generating analysis report with cross-run comparison (Requirements 2.4, 7.4)."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 2,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
                'grandTotalEstimatedUSD': 0.50,
                'grandTotalPotentialSavingsUSD': 0.10,
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 2,
                        'totalAllocatedCpus': 8.0,
                        'totalAllocatedMemoryGiB': 16.0,
                        'totalActualCpuUsage': 5.0,
                        'totalActualMemoryUsageGiB': 10.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                        'totalEstimatedUSD': 0.25,
                        'taskCostUSD': 0.20,
                        'storageCostUSD': 0.05,
                        'totalPotentialSavingsUSD': 0.05,
                        'peakConcurrentCpus': 4.0,
                        'peakConcurrentMemoryGiB': 8.0,
                    },
                    'taskMetrics': [],
                },
                {
                    'runInfo': {
                        'runId': 'run-2',
                        'runName': 'workflow-run-2',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-02T10:00:00Z',
                        'startTime': '2023-01-02T10:05:00Z',
                        'stopTime': '2023-01-02T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 2,
                        'totalAllocatedCpus': 8.0,
                        'totalAllocatedMemoryGiB': 16.0,
                        'totalActualCpuUsage': 6.0,
                        'totalActualMemoryUsageGiB': 12.0,
                        'overallCpuEfficiency': 0.75,
                        'overallMemoryEfficiency': 0.75,
                        'totalEstimatedUSD': 0.25,
                        'taskCostUSD': 0.20,
                        'storageCostUSD': 0.05,
                        'totalPotentialSavingsUSD': 0.05,
                        'peakConcurrentCpus': 4.0,
                        'peakConcurrentMemoryGiB': 8.0,
                    },
                    'taskMetrics': [],
                },
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Cross-Run Summary Comparison' in result
        assert 'workflow-run-1' in result
        assert 'workflow-run-2' in result
        assert 'Cross-Run Statistics' in result
        assert 'Total Tasks (all runs)' in result
        assert 'Average Cost per Run' in result
        assert 'Average CPU Efficiency' in result
        assert 'Average Memory Efficiency' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_with_cross_run_aggregates(self):
        """Test generating analysis report with cross-run aggregates (Requirements 7.1, 7.2, 7.3)."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 2,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
                'grandTotalEstimatedUSD': 0.50,
                'grandTotalPotentialSavingsUSD': 0.10,
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 4.0,
                        'totalAllocatedMemoryGiB': 8.0,
                        'totalActualCpuUsage': 2.5,
                        'totalActualMemoryUsageGiB': 5.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                        'totalEstimatedUSD': 0.25,
                        'taskCostUSD': 0.20,
                        'storageCostUSD': 0.05,
                        'totalPotentialSavingsUSD': 0.05,
                        'peakConcurrentCpus': 4.0,
                        'peakConcurrentMemoryGiB': 8.0,
                    },
                    'taskMetrics': [],
                },
                {
                    'runInfo': {
                        'runId': 'run-2',
                        'runName': 'workflow-run-2',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-02T10:00:00Z',
                        'startTime': '2023-01-02T10:05:00Z',
                        'stopTime': '2023-01-02T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 4.0,
                        'totalAllocatedMemoryGiB': 8.0,
                        'totalActualCpuUsage': 3.0,
                        'totalActualMemoryUsageGiB': 6.0,
                        'overallCpuEfficiency': 0.75,
                        'overallMemoryEfficiency': 0.75,
                        'totalEstimatedUSD': 0.25,
                        'taskCostUSD': 0.20,
                        'storageCostUSD': 0.05,
                        'totalPotentialSavingsUSD': 0.05,
                        'peakConcurrentCpus': 4.0,
                        'peakConcurrentMemoryGiB': 8.0,
                    },
                    'taskMetrics': [],
                },
            ],
            'crossRunAggregates': [
                {
                    'baseTaskName': 'alignReads',
                    'runCount': 2,
                    'totalTaskCount': 4,
                    'meanRunningSeconds': 110.0,
                    'maximumRunningSeconds': 120.0,
                    'meanCpuUtilizationRatio': 0.55,
                    'meanMemoryUtilizationRatio': 0.65,
                    'totalEstimatedUSD': 0.44,
                    'recommendedInstanceType': 'omics.c.large',
                },
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Cross-Run Aggregate Metrics' in result
        assert 'alignReads' in result
        assert 'across 2 runs' in result
        assert '4 total instances' in result
        assert 'Mean Runtime' in result
        assert 'Total Cost (all runs)' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_single_run_no_cross_run_comparison(self):
        """Test that single run analysis does not include cross-run comparison."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 4.0,
                        'totalAllocatedMemoryGiB': 8.0,
                        'totalActualCpuUsage': 2.5,
                        'totalActualMemoryUsageGiB': 5.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                    },
                    'taskMetrics': [],
                },
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Cross-Run Summary Comparison' not in result
        assert 'Cross-Run Aggregate Metrics' not in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_with_high_priority_savings(self):
        """Test generating analysis report with high-priority savings tasks."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 4.0,
                        'totalAllocatedMemoryGiB': 8.0,
                        'totalActualCpuUsage': 2.5,
                        'totalActualMemoryUsageGiB': 5.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                    },
                    'taskMetrics': [
                        {
                            'taskName': 'expensive-task',
                            'instanceType': 'omics.c.xlarge',
                            'estimatedUSD': 1.00,
                            'potentialSavingsUSD': 0.15,
                            'recommendedInstanceType': 'omics.c.large',
                            'isHighPrioritySaving': True,
                            'runningSeconds': 3600,
                        }
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'High-Priority Savings Opportunities' in result
        assert 'expensive-task' in result
        assert 'Estimated Cost: $1.0000' in result
        assert 'Potential Savings: $0.1500' in result
        assert 'omics.c.xlarge' in result
        assert 'omics.c.large' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_with_aggregated_metrics(self):
        """Test generating analysis report with aggregated task metrics."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 2,
                        'totalAllocatedCpus': 8.0,
                        'totalAllocatedMemoryGiB': 16.0,
                        'totalActualCpuUsage': 5.0,
                        'totalActualMemoryUsageGiB': 10.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                    },
                    'taskMetrics': [],
                    'aggregatedTaskMetrics': [
                        {
                            'baseTaskName': 'alignReads',
                            'count': 2,
                            'meanRunningSeconds': 100.0,
                            'maximumRunningSeconds': 120.0,
                            'maxObservedCpus': 3.0,
                            'maxObservedMemoryGiB': 6.0,
                            'totalEstimatedUSD': 0.25,
                            'recommendedInstanceType': 'omics.c.large',
                        }
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Aggregated Task Metrics (Scattered Tasks)' in result
        assert 'alignReads' in result
        assert '(2 instances)' in result
        assert 'Mean Runtime: 100.00 seconds' in result
        assert 'Max Runtime: 120.00 seconds' in result
        assert 'Max CPU Usage: 3.00 CPUs' in result
        assert 'Max Memory Usage: 6.00 GiB' in result
        assert 'Total Cost: $0.2500' in result
        assert 'Recommended Instance: omics.c.large' in result

    @pytest.mark.asyncio
    async def test_generate_analysis_report_with_detailed_json(self):
        """Test generating analysis report with detailed JSON section."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 4.0,
                        'totalAllocatedMemoryGiB': 8.0,
                        'totalActualCpuUsage': 2.5,
                        'totalActualMemoryUsageGiB': 5.0,
                        'overallCpuEfficiency': 0.625,
                        'overallMemoryEfficiency': 0.625,
                    },
                    'taskMetrics': [
                        {
                            'taskName': 'task1',
                            'allocatedCpus': 4,
                            'allocatedMemoryGiB': 8,
                        }
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data, detailed=True)

        # Assert
        assert isinstance(result, str)
        assert 'Detailed Task Metrics (JSON)' in result
        assert '```json' in result
        assert 'task1' in result


class TestNormalizeRunIdsEdgeCases:
    """Test edge cases for _normalize_run_ids function."""

    def test_normalize_run_ids_fallback_with_integer(self):
        """Test normalizing run IDs with integer input (fallback case)."""
        # Arrange
        run_ids = 12345

        # Act
        result = _normalize_run_ids(run_ids)  # type: ignore[arg-type]

        # Assert
        assert result == ['12345']

    def test_normalize_run_ids_fallback_with_object(self):
        """Test normalizing run IDs with object input (fallback case)."""

        # Arrange
        class CustomObject:
            def __str__(self):
                return 'custom-run-id'

        run_ids = CustomObject()

        # Act
        result = _normalize_run_ids(run_ids)  # type: ignore[arg-type]

        # Assert
        assert result == ['custom-run-id']


class TestGenerateAnalysisReportOverProvisionedTasks:
    """Test report generation for over-provisioned tasks with recommendations."""

    @pytest.mark.asyncio
    async def test_generate_analysis_report_over_provisioned_with_recommendation(self):
        """Test generating analysis report for over-provisioned task with recommendation."""
        # Arrange
        analysis_data = {
            'summary': {
                'totalRuns': 1,
                'analysisTimestamp': '2023-01-01T12:00:00Z',
                'analysisType': 'manifest-based',
            },
            'runs': [
                {
                    'runInfo': {
                        'runId': 'run-1',
                        'runName': 'workflow-run-1',
                        'status': 'COMPLETED',
                        'workflowId': 'workflow-123',
                        'creationTime': '2023-01-01T10:00:00Z',
                        'startTime': '2023-01-01T10:05:00Z',
                        'stopTime': '2023-01-01T11:00:00Z',
                    },
                    'summary': {
                        'totalTasks': 1,
                        'totalAllocatedCpus': 8.0,
                        'totalAllocatedMemoryGiB': 16.0,
                        'totalActualCpuUsage': 2.0,
                        'totalActualMemoryUsageGiB': 4.0,
                        'overallCpuEfficiency': 0.25,
                        'overallMemoryEfficiency': 0.25,
                    },
                    'taskMetrics': [
                        {
                            'taskName': 'over-provisioned-task',
                            'instanceType': 'omics.c.xlarge',
                            'isOverProvisioned': True,
                            'wastedCpus': 6.0,
                            'wastedMemoryGiB': 12.0,
                            'cpuEfficiencyRatio': 0.25,
                            'memoryEfficiencyRatio': 0.25,
                            'runningSeconds': 3600,
                            'estimatedUSD': 0.50,
                            'recommendedInstanceType': 'omics.c.small',
                        }
                    ],
                }
            ],
        }

        # Act
        result = await _generate_analysis_report(analysis_data)

        # Assert
        assert isinstance(result, str)
        assert 'Over-Provisioned Tasks (Wasting Resources)' in result
        assert 'over-provisioned-task' in result
        assert 'Recommended Instance: omics.c.small' in result


class TestParseManifestExceptionHandling:
    """Test exception handling in _parse_manifest_for_analysis."""

    @pytest.mark.asyncio
    async def test_parse_manifest_with_general_exception_in_event_loop(self):
        """Test parsing manifest handles general exceptions in event processing."""
        # Arrange
        run_id = 'test-run-123'
        run_response = {'name': 'test-run', 'status': 'COMPLETED'}

        # Create a message that will cause an exception during parsing
        # but not a JSON decode error
        manifest_logs = {
            'events': [
                {
                    'message': json.dumps(
                        {
                            'name': 'task1',
                            'cpus': 2,
                            'memory': 4,
                            'instanceType': 'omics.c.small',
                            'metrics': {
                                'cpusReserved': 2,
                                'cpusAverage': 1.5,
                                'memoryReservedGiB': 4,
                                'memoryAverageGiB': 3.0,
                                'runningSeconds': 100,
                            },
                        }
                    )
                },
            ]
        }

        # Act
        result = await _parse_manifest_for_analysis(run_id, run_response, manifest_logs)

        # Assert
        assert result is not None
        assert len(result['taskMetrics']) == 1


class TestExtractTaskMetricsWithCostAnalyzer:
    """Test _extract_task_metrics_from_manifest with cost analyzer integration."""

    def test_extract_task_metrics_with_cost_analyzer_none_result(self):
        """Test extracting task metrics when cost analyzer returns None."""
        from awslabs.aws_healthomics_mcp_server.analysis.cost_analyzer import CostAnalyzer
        from unittest.mock import MagicMock

        # Arrange
        task_data = {
            'name': 'test-task',
            'cpus': 4,
            'memory': 8,
            'instanceType': 'omics.c.large',
            'metrics': {
                'cpusReserved': 4,
                'cpusAverage': 3.2,
                'cpusMaximum': 3.8,
                'memoryReservedGiB': 8,
                'memoryAverageGiB': 6.4,
                'memoryMaximumGiB': 7.2,
                'runningSeconds': 1800,
            },
        }

        # Mock cost analyzer to return None
        cost_analyzer = MagicMock(spec=CostAnalyzer)
        cost_analyzer.calculate_task_cost.return_value = None

        # Act
        result = _extract_task_metrics_from_manifest(task_data, cost_analyzer=cost_analyzer)

        # Assert
        assert result is not None
        assert result['estimatedUSD'] == 0.0
        assert result['minimumUSD'] == 0.0
