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
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_aws_session')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_run_manifest_logs_internal')
    async def test_get_run_analysis_data_success(self, mock_get_logs, mock_get_session):
        """Test getting run analysis data successfully."""
        # Arrange
        run_ids = ['run-123', 'run-456']

        # Mock AWS session and client
        mock_session = MagicMock()
        mock_omics_client = MagicMock()
        mock_session.client.return_value = mock_omics_client
        mock_get_session.return_value = mock_session

        # Mock get_run responses
        mock_omics_client.get_run.side_effect = [
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
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_aws_session')
    async def test_get_run_analysis_data_no_uuid(self, mock_get_session):
        """Test getting run analysis data when run has no UUID."""
        # Arrange
        run_ids = ['run-123']

        # Mock AWS session and client
        mock_session = MagicMock()
        mock_omics_client = MagicMock()
        mock_session.client.return_value = mock_omics_client
        mock_get_session.return_value = mock_session

        # Mock get_run response without UUID
        mock_omics_client.get_run.return_value = {'name': 'run1', 'status': 'COMPLETED'}

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result is not None
        assert result['summary']['totalRuns'] == 1
        assert len(result['runs']) == 0  # No runs processed due to missing UUID

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis.get_aws_session')
    async def test_get_run_analysis_data_exception_handling(self, mock_get_session):
        """Test getting run analysis data handles exceptions gracefully."""
        # Arrange
        run_ids = ['run-123']

        # Mock AWS session to raise exception
        mock_get_session.side_effect = Exception('AWS connection failed')

        # Act
        result = await _get_run_analysis_data(run_ids)

        # Assert
        assert result == {}


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

        # Act
        result = await analyze_run_performance(mock_ctx, run_ids)

        # Assert
        assert result == 'Generated analysis report'
        mock_get_data.assert_called_once()
        mock_generate_report.assert_called_once_with(mock_analysis_data)

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_analysis._get_run_analysis_data')
    async def test_analyze_run_performance_no_data(self, mock_get_data):
        """Test analyze_run_performance with no analysis data."""
        # Arrange
        mock_ctx = AsyncMock()
        run_ids = ['run-123']

        # Mock empty analysis data
        mock_get_data.return_value = {'runs': []}

        # Act
        result = await analyze_run_performance(mock_ctx, run_ids)

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

        # Act
        result = await analyze_run_performance(mock_ctx, run_ids)

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

            # Test with comma-separated string
            await analyze_run_performance(mock_ctx, 'run1,run2,run3')

            # Verify normalized run IDs were passed
            call_args = mock_get_data.call_args[0][0]
            assert call_args == ['run1', 'run2', 'run3']
