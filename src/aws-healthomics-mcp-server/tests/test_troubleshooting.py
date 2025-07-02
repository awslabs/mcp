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

"""Tests for troubleshooting tools."""

import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
    diagnose_run_failure,
    get_omics_client,
)
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = AsyncMock(spec=Context)
    return context


@pytest.fixture
def mock_omics_client():
    """Create a mock HealthOmics client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_failed_run_response():
    """Sample failed run response."""
    return {
        'id': 'run-12345',
        'status': 'FAILED',
        'failureReason': 'Task execution failed due to insufficient memory',
        'name': 'test-workflow-run',
        'workflowId': 'workflow-67890',
        'uuid': 'uuid-abcd-1234',
        'creationTime': '2024-01-01T10:00:00Z',
        'startTime': '2024-01-01T10:05:00Z',
        'stopTime': '2024-01-01T10:30:00Z',
        'workflowType': 'WDL',
    }


@pytest.fixture
def sample_running_run_response():
    """Sample running run response."""
    return {
        'id': 'run-12345',
        'status': 'RUNNING',
        'name': 'test-workflow-run',
        'workflowId': 'workflow-67890',
    }


@pytest.fixture
def sample_failed_tasks():
    """Sample failed tasks response."""
    return {
        'items': [
            {
                'taskId': 'task-111',
                'name': 'preprocessing',
                'status': 'FAILED',
                'statusMessage': 'Container exited with code 1',
            },
            {
                'taskId': 'task-222',
                'name': 'analysis',
                'status': 'FAILED',
                'statusMessage': 'Out of memory error',
            },
        ],
        'nextToken': None,
    }


@pytest.fixture
def sample_log_events():
    """Sample log events."""
    return {
        'events': [
            {'message': 'Starting task execution'},
            {'message': 'Error: insufficient memory'},
            {'message': 'Task failed with exit code 1'},
        ]
    }


class TestGetOmicsClient:
    """Test the get_omics_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_aws_session')
    def test_get_omics_client_success(self, mock_get_aws_session):
        """Test successful HealthOmics client creation."""
        # Arrange
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_get_aws_session.return_value = mock_session
        mock_session.client.return_value = mock_client

        # Act
        result = get_omics_client()

        # Assert
        assert result == mock_client
        mock_session.client.assert_called_once_with('omics')

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_aws_session')
    def test_get_omics_client_failure(self, mock_get_aws_session):
        """Test HealthOmics client creation failure."""
        # Arrange
        mock_get_aws_session.side_effect = Exception('AWS session error')

        # Act & Assert
        with pytest.raises(Exception, match='AWS session error'):
            get_omics_client()


class TestDiagnoseRunFailure:
    """Test the diagnose_run_failure function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @patch(
        'awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_manifest_logs_internal'
    )
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_task_logs_internal')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_success(
        self,
        mock_get_task_logs_internal,
        mock_get_run_manifest_logs_internal,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_failed_tasks,
        sample_log_events,
    ):
        """Test successful run failure diagnosis."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response
        mock_client.list_run_tasks.return_value = sample_failed_tasks

        # Mock get_run_task calls for task-specific timing
        mock_client.get_run_task.return_value = {
            'creationTime': datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
            'stopTime': datetime(2024, 1, 1, 10, 25, 0, tzinfo=timezone.utc),
        }

        # Mock log responses
        mock_get_run_engine_logs_internal.return_value = sample_log_events
        mock_get_run_manifest_logs_internal.return_value = sample_log_events
        mock_get_task_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert result['runUuid'] == 'uuid-abcd-1234'
        assert result['status'] == 'FAILED'
        assert result['failureReason'] == 'Task execution failed due to insufficient memory'
        assert result['workflowId'] == 'workflow-67890'
        assert result['workflowType'] == 'WDL'
        assert len(result['engineLogs']) == 3
        assert result['engineLogCount'] == 3
        assert len(result['manifestLogs']) == 3
        assert result['manifestLogCount'] == 3
        assert len(result['failedTasks']) == 2
        assert result['failedTaskCount'] == 2
        assert len(result['recommendations']) > 5  # Enhanced recommendations

        # Verify summary information
        summary = result['summary']
        assert summary['totalFailedTasks'] == 2
        assert summary['hasManifestLogs'] is True
        assert summary['hasEngineLogs'] is True

        # Verify failed task details
        first_task = result['failedTasks'][0]
        assert first_task['taskId'] == 'task-111'
        assert first_task['name'] == 'preprocessing'
        assert first_task['statusMessage'] == 'Container exited with code 1'
        assert len(first_task['logs']) == 3
        assert first_task['logCount'] == 3

        # Verify API calls
        mock_client.get_run.assert_called_once_with(id='run-12345')
        mock_client.list_run_tasks.assert_called_once_with(
            id='run-12345',
            status='FAILED',
            maxResults=100,  # Updated to 100
        )

        # Verify log function calls with correct parameters (now include time windows)
        mock_get_run_engine_logs_internal.assert_called_once_with(
            run_id='run-12345',
            start_time='2024-01-01T09:55:00+00:00',  # 5 minutes before creation time
            end_time='2024-01-01T10:35:00+00:00',  # 5 minutes after stop time
            limit=100,
            start_from_head=False,
        )

        # Verify manifest log call
        mock_get_run_manifest_logs_internal.assert_called_once_with(
            run_id='run-12345',
            run_uuid='uuid-abcd-1234',
            start_time='2024-01-01T09:55:00+00:00',  # 5 minutes before creation time
            end_time='2024-01-01T10:35:00+00:00',  # 5 minutes after stop time
            limit=100,
            start_from_head=False,
        )

        # Verify task log calls (should use task-specific timing)
        assert mock_get_task_logs_internal.call_count == 2
        mock_get_task_logs_internal.assert_any_call(
            run_id='run-12345',
            task_id='task-111',
            start_time='2024-01-01T10:00:00+00:00',  # 5 minutes before task creation
            end_time='2024-01-01T10:30:00+00:00',  # 5 minutes after task stop
            limit=100,  # Updated to 100
            start_from_head=False,
        )
        mock_get_task_logs_internal.assert_any_call(
            run_id='run-12345',
            task_id='task-222',
            start_time='2024-01-01T10:00:00+00:00',  # 5 minutes before task creation
            end_time='2024-01-01T10:30:00+00:00',  # 5 minutes after task stop
            limit=100,  # Updated to 100
            start_from_head=False,
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_not_failed(
        self,
        mock_get_omics_client,
        mock_context,
        sample_running_run_response,
    ):
        """Test diagnosis of a run that is not in FAILED state."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_running_run_response

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['status'] == 'RUNNING'
        assert 'Run is not in FAILED state' in result['message']
        assert 'Current status: RUNNING' in result['message']

        # Verify no further API calls were made
        mock_client.list_run_tasks.assert_not_called()

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_no_uuid(
        self,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_log_events,
    ):
        """Test diagnosis when run has no UUID (no manifest logs available)."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client

        # Run response without UUID
        run_response = {
            'id': 'run-12345',
            'status': 'FAILED',
            'failureReason': 'Task execution failed',
            'name': 'test-workflow-run',
            'workflowId': 'workflow-67890',
        }
        mock_client.get_run.return_value = run_response
        mock_client.list_run_tasks.return_value = {'items': [], 'nextToken': None}
        mock_get_run_engine_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert result['runUuid'] is None
        assert len(result['manifestLogs']) == 1
        assert 'No run UUID available' in result['manifestLogs'][0]
        assert result['manifestLogCount'] == 1
        assert result['summary']['hasManifestLogs'] is False

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @patch(
        'awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_manifest_logs_internal'
    )
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_engine_logs_error(
        self,
        mock_get_run_manifest_logs_internal,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_failed_tasks,
        sample_log_events,
    ):
        """Test diagnosis when engine log retrieval fails."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response
        mock_client.list_run_tasks.return_value = {
            'items': [],
            'nextToken': None,
        }  # No failed tasks

        # Mock engine logs to raise an exception, but manifest logs succeed
        mock_get_run_engine_logs_internal.side_effect = Exception('Log retrieval failed')
        mock_get_run_manifest_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert result['status'] == 'FAILED'
        assert len(result['engineLogs']) == 1
        assert 'Error retrieving engine logs' in result['engineLogs'][0]
        assert len(result['manifestLogs']) == 3  # Manifest logs succeeded
        assert len(result['failedTasks']) == 0

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_task_logs_internal')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_task_logs_error(
        self,
        mock_get_task_logs_internal,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_failed_tasks,
        sample_log_events,
    ):
        """Test diagnosis when task log retrieval fails."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response
        mock_client.list_run_tasks.return_value = sample_failed_tasks

        # Mock successful engine logs but failed task logs
        mock_get_run_engine_logs_internal.return_value = sample_log_events
        mock_get_task_logs_internal.side_effect = Exception('Task log retrieval failed')

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert len(result['engineLogs']) == 3  # Engine logs succeeded
        assert len(result['failedTasks']) == 2  # Tasks are still included

        # Check that task logs contain error messages
        for task in result['failedTasks']:
            assert len(task['logs']) == 1
            assert 'Error retrieving task logs' in task['logs'][0]

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_boto_error(
        self,
        mock_get_omics_client,
        mock_context,
    ):
        """Test diagnosis with boto client error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.side_effect = botocore.exceptions.ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Run not found'}
            },
            operation_name='GetRun',
        )

        # Act & Assert
        with pytest.raises(botocore.exceptions.ClientError):
            await diagnose_run_failure(
                ctx=mock_context,
                run_id='run-12345',
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'AWS error diagnosing run failure' in error_call_args
        assert 'run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_unexpected_error(
        self,
        mock_get_omics_client,
        mock_context,
    ):
        """Test diagnosis with unexpected error."""
        # Arrange
        mock_get_omics_client.side_effect = Exception('Unexpected error')

        # Act & Assert
        with pytest.raises(Exception, match='Unexpected error'):
            await diagnose_run_failure(
                ctx=mock_context,
                run_id='run-12345',
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Unexpected error diagnosing run failure' in error_call_args
        assert 'run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_no_failure_reason(
        self,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_log_events,
    ):
        """Test diagnosis when run has no failure reason."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client

        # Run response without failureReason
        run_response = {
            'id': 'run-12345',
            'status': 'FAILED',
            'name': 'test-workflow-run',
            'workflowId': 'workflow-67890',
        }
        mock_client.get_run.return_value = run_response
        mock_client.list_run_tasks.return_value = {'items': []}
        mock_get_run_engine_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['failureReason'] == 'No failure reason provided'

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_recommendations_included(
        self,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_log_events,
    ):
        """Test that diagnosis includes helpful recommendations."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response
        mock_client.list_run_tasks.return_value = {'items': []}
        mock_get_run_engine_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        recommendations = result['recommendations']
        assert len(recommendations) > 0

        # Check for specific recommendations
        recommendation_text = ' '.join(recommendations)
        assert 'IAM role permissions' in recommendation_text
        assert 'container images' in recommendation_text
        assert 'input files' in recommendation_text
        assert 'syntax errors' in recommendation_text
        assert 'parameter values' in recommendation_text
        assert 'manifest logs' in recommendation_text  # New enhanced recommendation
        assert 'resource allocation' in recommendation_text  # New enhanced recommendation

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @patch(
        'awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_manifest_logs_internal'
    )
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_manifest_logs_error(
        self,
        mock_get_run_manifest_logs_internal,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_log_events,
    ):
        """Test diagnosis when manifest log retrieval fails."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response
        mock_client.list_run_tasks.return_value = {'items': [], 'nextToken': None}

        # Mock successful engine logs but failed manifest logs
        mock_get_run_engine_logs_internal.return_value = sample_log_events
        mock_get_run_manifest_logs_internal.side_effect = Exception(
            'Manifest log retrieval failed'
        )

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert len(result['engineLogs']) == 3  # Engine logs succeeded
        assert len(result['manifestLogs']) == 1
        assert 'Error retrieving manifest logs' in result['manifestLogs'][0]
        assert result['summary']['hasManifestLogs'] is False

    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_omics_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_engine_logs_internal')
    @patch(
        'awslabs.aws_healthomics_mcp_server.tools.troubleshooting.get_run_manifest_logs_internal'
    )
    @pytest.mark.asyncio
    async def test_diagnose_run_failure_pagination_multiple_tasks(
        self,
        mock_get_run_manifest_logs_internal,
        mock_get_run_engine_logs_internal,
        mock_get_omics_client,
        mock_context,
        sample_failed_run_response,
        sample_log_events,
    ):
        """Test diagnosis with pagination for multiple failed tasks."""
        # Arrange
        mock_client = MagicMock()
        mock_get_omics_client.return_value = mock_client
        mock_client.get_run.return_value = sample_failed_run_response

        # Mock paginated task responses
        first_page = {
            'items': [
                {
                    'taskId': 'task-001',
                    'name': 'task1',
                    'status': 'FAILED',
                    'statusMessage': 'Failed task 1',
                }
            ],
            'nextToken': 'token123',
        }
        second_page = {
            'items': [
                {
                    'taskId': 'task-002',
                    'name': 'task2',
                    'status': 'FAILED',
                    'statusMessage': 'Failed task 2',
                }
            ],
            'nextToken': None,
        }
        mock_client.list_run_tasks.side_effect = [first_page, second_page]

        # Mock log responses
        mock_get_run_engine_logs_internal.return_value = sample_log_events
        mock_get_run_manifest_logs_internal.return_value = sample_log_events

        # Act
        result = await diagnose_run_failure(
            ctx=mock_context,
            run_id='run-12345',
        )

        # Assert
        assert result['runId'] == 'run-12345'
        assert len(result['failedTasks']) == 2
        assert result['failedTaskCount'] == 2
        assert result['summary']['totalFailedTasks'] == 2

        # Verify both API calls were made for pagination
        assert mock_client.list_run_tasks.call_count == 2
        mock_client.list_run_tasks.assert_any_call(
            id='run-12345',
            status='FAILED',
            maxResults=100,
        )
        mock_client.list_run_tasks.assert_any_call(
            id='run-12345',
            status='FAILED',
            maxResults=100,
            startingToken='token123',
        )


class TestTimeWindowCalculation:
    """Test time window calculation functionality."""

    def test_calculate_log_time_window_with_datetime_objects(self):
        """Test calculate_log_time_window with datetime objects."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
            calculate_log_time_window,
        )

        # Test with datetime objects
        start_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)

        log_start, log_end = calculate_log_time_window(start_time, end_time, buffer_minutes=5)

        assert log_start == '2024-01-01T09:55:00+00:00'
        assert log_end == '2024-01-01T10:35:00+00:00'

    def test_calculate_log_time_window_with_strings(self):
        """Test calculate_log_time_window with string inputs."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
            calculate_log_time_window,
        )

        # Test with string inputs
        start_str = '2024-01-01T10:00:00Z'
        end_str = '2024-01-01T10:30:00Z'

        log_start, log_end = calculate_log_time_window(start_str, end_str, buffer_minutes=10)

        assert log_start == '2024-01-01T09:50:00+00:00'
        assert log_end == '2024-01-01T10:40:00+00:00'

    def test_calculate_log_time_window_with_invalid_inputs(self):
        """Test calculate_log_time_window with invalid inputs."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
            calculate_log_time_window,
        )

        # Test with invalid inputs
        log_start, log_end = calculate_log_time_window(None, None)
        assert log_start is None
        assert log_end is None

        # Test with mixed invalid inputs
        log_start, log_end = calculate_log_time_window('invalid', None)
        assert log_start is None
        assert log_end is None

    def test_calculate_log_time_window_with_invalid_datetime_string(self):
        """Test calculate_log_time_window with invalid datetime string."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
            calculate_log_time_window,
        )

        # Test with invalid datetime string
        log_start, log_end = calculate_log_time_window('invalid-date', '2024-01-01T10:30:00Z')
        assert log_start is None
        assert log_end is None

    def test_calculate_log_time_window_with_non_datetime_objects(self):
        """Test calculate_log_time_window with non-datetime objects."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import (
            calculate_log_time_window,
        )

        # Test with non-datetime objects
        log_start, log_end = calculate_log_time_window(123, 456)
        assert log_start is None
        assert log_end is None


class TestSafeDatetimeToIso:
    """Test the safe_datetime_to_iso function."""

    def test_safe_datetime_to_iso_with_none(self):
        """Test safe_datetime_to_iso with None input."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import safe_datetime_to_iso

        result = safe_datetime_to_iso(None)
        assert result is None

    def test_safe_datetime_to_iso_with_datetime(self):
        """Test safe_datetime_to_iso with datetime object."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import safe_datetime_to_iso

        dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = safe_datetime_to_iso(dt)
        assert result == '2024-01-01T10:00:00+00:00'

    def test_safe_datetime_to_iso_with_string(self):
        """Test safe_datetime_to_iso with string input."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import safe_datetime_to_iso

        result = safe_datetime_to_iso('2024-01-01T10:00:00Z')
        assert result == '2024-01-01T10:00:00Z'

    def test_safe_datetime_to_iso_with_other_type(self):
        """Test safe_datetime_to_iso with other type."""
        from awslabs.aws_healthomics_mcp_server.tools.troubleshooting import safe_datetime_to_iso

        result = safe_datetime_to_iso(123)
        assert result == '123'

        result = safe_datetime_to_iso(['list'])
        assert result == "['list']"
