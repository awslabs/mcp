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

"""Tests for run timeline visualization tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
    _extract_task_for_timeline,
    _normalize_run_ids,
    generate_run_timeline,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestNormalizeRunIds:
    """Test the _normalize_run_ids function."""

    def test_normalize_run_ids_list(self):
        """Test normalizing a list of run IDs."""
        run_ids = ['run1', 'run2', 'run3']
        result = _normalize_run_ids(run_ids)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_json_string(self):
        """Test normalizing a JSON string of run IDs."""
        run_ids = '["run1", "run2", "run3"]'
        result = _normalize_run_ids(run_ids)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_comma_separated(self):
        """Test normalizing a comma-separated string of run IDs."""
        run_ids = 'run1,run2,run3'
        result = _normalize_run_ids(run_ids)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_run_ids_single_string(self):
        """Test normalizing a single run ID string."""
        run_ids = 'run1'
        result = _normalize_run_ids(run_ids)
        assert result == ['run1']

    def test_normalize_run_ids_with_spaces(self):
        """Test normalizing comma-separated string with spaces."""
        run_ids = 'run1, run2 , run3'
        result = _normalize_run_ids(run_ids)
        assert result == ['run1', 'run2', 'run3']


class TestExtractTaskForTimeline:
    """Test the _extract_task_for_timeline function."""

    def test_extract_task_with_all_fields(self):
        """Test extracting task data with all fields present."""
        task_data = {
            'name': 'TestTask',
            'creationTime': '2024-01-01T10:00:00Z',
            'startTime': '2024-01-01T10:01:00Z',
            'stopTime': '2024-01-01T10:05:00Z',
            'status': 'COMPLETED',
            'cpus': 4,
            'memory': 8,
            'instanceType': 'omics.m.xlarge',
            'metrics': {
                'cpusReserved': 4,
                'memoryReservedGiB': 8,
            },
        }

        result = _extract_task_for_timeline(task_data)

        assert result is not None
        assert result['taskName'] == 'TestTask'
        assert result['creationTime'] == '2024-01-01T10:00:00Z'
        assert result['startTime'] == '2024-01-01T10:01:00Z'
        assert result['stopTime'] == '2024-01-01T10:05:00Z'
        assert result['status'] == 'COMPLETED'
        assert result['allocatedCpus'] == 4
        assert result['allocatedMemoryGiB'] == 8
        assert result['instanceType'] == 'omics.m.xlarge'

    def test_extract_task_missing_creation_time(self):
        """Test extracting task data with missing creationTime."""
        task_data = {
            'name': 'TestTask',
            'stopTime': '2024-01-01T10:05:00Z',
        }

        result = _extract_task_for_timeline(task_data)
        assert result is None

    def test_extract_task_missing_stop_time(self):
        """Test extracting task data with missing stopTime."""
        task_data = {
            'name': 'TestTask',
            'creationTime': '2024-01-01T10:00:00Z',
        }

        result = _extract_task_for_timeline(task_data)
        assert result is None

    def test_extract_task_with_default_values(self):
        """Test extracting task data with default values for optional fields."""
        task_data = {
            'creationTime': '2024-01-01T10:00:00Z',
            'stopTime': '2024-01-01T10:05:00Z',
        }

        result = _extract_task_for_timeline(task_data)

        assert result is not None
        assert result['taskName'] == 'unknown'
        assert result['status'] == 'COMPLETED'
        assert result['allocatedCpus'] == 0
        assert result['allocatedMemoryGiB'] == 0
        assert result['instanceType'] == 'N/A'


class TestGenerateRunTimeline:
    """Test the generate_run_timeline function."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_run_manifest_logs_internal')
    async def test_generate_timeline_success(self, mock_get_logs, mock_get_omics_client):
        """Test successful timeline generation."""
        # Setup mock omics client
        mock_client = MagicMock()
        mock_client.get_run.return_value = {
            'uuid': 'test-uuid',
            'name': 'TestRun',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/test-run',
        }
        mock_get_omics_client.return_value = mock_client

        # Setup mock manifest logs with task data
        mock_get_logs.return_value = {
            'events': [
                {
                    'message': '{"name": "Task1", "cpus": 4, "memory": 8, "instanceType": "omics.m.xlarge", "creationTime": "2024-01-01T10:00:00Z", "startTime": "2024-01-01T10:01:00Z", "stopTime": "2024-01-01T10:05:00Z", "status": "COMPLETED", "metrics": {}}'
                },
                {
                    'message': '{"name": "Task2", "cpus": 2, "memory": 4, "instanceType": "omics.c.large", "creationTime": "2024-01-01T10:02:00Z", "startTime": "2024-01-01T10:03:00Z", "stopTime": "2024-01-01T10:06:00Z", "status": "COMPLETED", "metrics": {}}'
                },
            ]
        }

        # Create mock context
        ctx = MagicMock()
        ctx.error = AsyncMock()

        # Call the function
        result = await generate_run_timeline(ctx, run_ids='test-run', time_unit='hr')

        # Verify result is SVG
        assert '<svg' in result
        assert '</svg>' in result
        assert 'Task1' in result or 'Task2' in result

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    async def test_generate_timeline_invalid_time_unit(self, mock_get_omics_client):
        """Test timeline generation with invalid time unit."""
        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await generate_run_timeline(ctx, run_ids='test-run', time_unit='invalid')

        assert 'Invalid time_unit' in result
        ctx.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_run_manifest_logs_internal')
    async def test_generate_timeline_no_tasks(self, mock_get_logs, mock_get_omics_client):
        """Test timeline generation with no task data."""
        mock_client = MagicMock()
        mock_client.get_run.return_value = {
            'uuid': 'test-uuid',
            'name': 'TestRun',
        }
        mock_get_omics_client.return_value = mock_client

        # Return empty events
        mock_get_logs.return_value = {'events': []}

        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await generate_run_timeline(ctx, run_ids='test-run', time_unit='hr')

        assert 'Unable to retrieve task data' in result
        ctx.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_run_manifest_logs_internal')
    async def test_generate_timeline_multiple_runs(self, mock_get_logs, mock_get_omics_client):
        """Test timeline generation with multiple runs."""
        mock_client = MagicMock()
        mock_client.get_run.return_value = {
            'uuid': 'test-uuid',
            'name': 'TestRun',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/test-run',
        }
        mock_get_omics_client.return_value = mock_client

        mock_get_logs.return_value = {
            'events': [
                {
                    'message': '{"name": "Task1", "cpus": 4, "memory": 8, "instanceType": "omics.m.xlarge", "creationTime": "2024-01-01T10:00:00Z", "startTime": "2024-01-01T10:01:00Z", "stopTime": "2024-01-01T10:05:00Z", "status": "COMPLETED", "metrics": {}}'
                },
            ]
        }

        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await generate_run_timeline(ctx, run_ids=['run1', 'run2'], time_unit='min')

        assert '<svg' in result
        assert '</svg>' in result

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    async def test_generate_timeline_run_without_uuid(self, mock_get_omics_client):
        """Test timeline generation when run has no UUID."""
        mock_client = MagicMock()
        mock_client.get_run.return_value = {
            'name': 'TestRun',
            # No uuid field
        }
        mock_get_omics_client.return_value = mock_client

        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await generate_run_timeline(ctx, run_ids='test-run', time_unit='hr')

        assert 'Unable to retrieve task data' in result

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client')
    async def test_generate_timeline_exception_handling(self, mock_get_omics_client):
        """Test timeline generation handles exceptions gracefully."""
        mock_get_omics_client.side_effect = Exception('Connection error')

        ctx = MagicMock()
        ctx.error = AsyncMock()

        result = await generate_run_timeline(ctx, run_ids='test-run', time_unit='hr')

        assert 'Error generating timeline' in result
        ctx.error.assert_called_once()
