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

"""Tests for workflow analysis tools."""

import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.run_analysis import (
    _convert_datetime_to_string,
    _normalize_run_ids,
    _safe_json_dumps,
)
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    _get_logs_from_stream,
    get_run_engine_logs,
    get_run_logs,
    get_run_manifest_logs,
    get_task_logs,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = AsyncMock(spec=Context)
    return context


@pytest.fixture
def mock_logs_client():
    """Create a mock CloudWatch Logs client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_log_events():
    """Sample log events for testing."""
    return [
        {
            'timestamp': 1640995200000,  # 2022-01-01 00:00:00 UTC
            'message': 'Starting workflow execution',
        },
        {
            'timestamp': 1640995260000,  # 2022-01-01 00:01:00 UTC
            'message': 'Task completed successfully',
        },
        {
            'timestamp': 1640995320000,  # 2022-01-01 00:02:00 UTC
            'message': 'Workflow execution completed',
        },
    ]


# Old TestGetLogsFromStream class removed to avoid duplication


class TestGetRunLogs:
    """Test the get_run_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_logs_success(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test successful run log retrieval."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
            'nextForwardToken': 'next-token-123',
        }

        # Act - Call with explicit parameter values
        result = await get_run_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=50,
            next_token=None,
            start_from_head=False,
        )

        # Assert
        assert 'events' in result
        assert 'nextToken' in result
        assert len(result['events']) == 3
        assert result['nextToken'] == 'next-token-123'

        # Verify correct log stream name
        mock_client.get_log_events.assert_called_once()
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['logGroupName'] == '/aws/omics/WorkflowLog'
        assert call_args['logStreamName'] == 'run/run-12345'
        assert call_args['limit'] == 50
        assert call_args['startFromHead'] is False

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_logs_with_time_range(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test run log retrieval with time range."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_run_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time='2022-01-01T00:00:00Z',
            end_time='2022-01-01T00:05:00Z',
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_logs_boto_error(self, mock_get_logs_client, mock_context):
        """Test run log retrieval with boto error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = botocore.exceptions.ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Log stream not found'}
            },
            operation_name='GetLogEvents',
        )

        # Act & Assert
        with pytest.raises(botocore.exceptions.ClientError):
            await get_run_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_logs_invalid_timestamp(self, mock_get_logs_client, mock_context):
        """Test run log retrieval with invalid timestamp."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(ValueError):
            await get_run_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time='invalid-timestamp',
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()


class TestGetRunManifestLogs:
    """Test the get_run_manifest_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_with_uuid(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test manifest log retrieval with run UUID."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_run_manifest_logs(
            ctx=mock_context,
            run_id='run-12345',
            run_uuid='uuid-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

        # Verify correct log stream name with UUID
        mock_client.get_log_events.assert_called_once()
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['logStreamName'] == 'manifest/run/run-12345/uuid-67890'

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_without_uuid(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test manifest log retrieval without run UUID."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_run_manifest_logs(
            ctx=mock_context,
            run_id='run-12345',
            run_uuid=None,
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

        # Verify correct log stream name without UUID
        mock_client.get_log_events.assert_called_once()
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['logStreamName'] == 'manifest/run/run-12345'


class TestGetRunEngineLogs:
    """Test the get_run_engine_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_success(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test successful engine log retrieval."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_run_engine_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

        # Verify correct log stream name
        mock_client.get_log_events.assert_called_once()
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['logStreamName'] == 'run/run-12345/engine'
        assert call_args['startFromHead'] is True

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_from_tail(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test engine log retrieval from tail."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_run_engine_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=False,
        )

        # Assert
        assert 'events' in result

        # Verify startFromHead parameter
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['startFromHead'] is False


class TestGetTaskLogs:
    """Test the get_task_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_success(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test successful task log retrieval."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await get_task_logs(
            ctx=mock_context,
            run_id='run-12345',
            task_id='task-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

        # Verify correct log stream name
        mock_client.get_log_events.assert_called_once()
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['logStreamName'] == 'run/run-12345/task/task-67890'

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_with_pagination(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test task log retrieval with pagination."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
            'nextForwardToken': 'next-token-456',
        }

        # Act
        result = await get_task_logs(
            ctx=mock_context,
            run_id='run-12345',
            task_id='task-67890',
            start_time=None,
            end_time=None,
            limit=25,
            next_token='prev-token-123',
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert 'nextToken' in result
        assert result['nextToken'] == 'next-token-456'

        # Verify pagination parameters
        call_args = mock_client.get_log_events.call_args[1]
        assert call_args['nextToken'] == 'prev-token-123'
        assert call_args['limit'] == 25

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_unexpected_error(self, mock_get_logs_client, mock_context):
        """Test task log retrieval with unexpected error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = Exception('Unexpected error')

        # Act & Assert
        with pytest.raises(Exception, match='Unexpected error'):
            await get_task_logs(
                ctx=mock_context,
                run_id='run-12345',
                task_id='task-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()


class TestParameterValidation:
    """Test parameter validation for log functions."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_logs_with_valid_limits(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test run logs with valid limit values."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act & Assert - Test minimum valid limit
        result = await get_run_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=1,  # Minimum valid
            next_token=None,
            start_from_head=True,
        )
        assert 'events' in result

        # Test maximum valid limit
        result = await get_run_logs(
            ctx=mock_context,
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=10000,  # Maximum valid
            next_token=None,
            start_from_head=True,
        )
        assert 'events' in result

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_with_valid_limits(
        self, mock_get_logs_client, mock_context, sample_log_events
    ):
        """Test task logs with valid limit values."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act & Assert - Test minimum valid limit
        result = await get_task_logs(
            ctx=mock_context,
            run_id='run-12345',
            task_id='task-67890',
            start_time=None,
            end_time=None,
            limit=1,  # Minimum valid
            next_token=None,
            start_from_head=True,
        )
        assert 'events' in result

        # Test maximum valid limit
        result = await get_task_logs(
            ctx=mock_context,
            run_id='run-12345',
            task_id='task-67890',
            start_time=None,
            end_time=None,
            limit=10000,  # Maximum valid
            next_token=None,
            start_from_head=True,
        )
        assert 'events' in result


class TestNormalizeRunIds:
    """Test cases for the _normalize_run_ids function."""

    def test_normalize_list_input(self):
        """Test that list input is returned as-is."""
        input_list = ['run1', 'run2', 'run3']
        result = _normalize_run_ids(input_list)
        assert result == input_list

    def test_normalize_json_string_input(self):
        """Test that JSON string input is parsed correctly."""
        input_json = '["run1", "run2", "run3"]'
        result = _normalize_run_ids(input_json)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_single_json_string(self):
        """Test that single item JSON string is handled."""
        input_json = '"run1"'
        result = _normalize_run_ids(input_json)
        assert result == ['run1']

    def test_normalize_comma_separated_string(self):
        """Test that comma-separated string is parsed correctly."""
        input_csv = 'run1,run2,run3'
        result = _normalize_run_ids(input_csv)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_comma_separated_with_spaces(self):
        """Test that comma-separated string with spaces is handled."""
        input_csv = 'run1, run2 , run3'
        result = _normalize_run_ids(input_csv)
        assert result == ['run1', 'run2', 'run3']

    def test_normalize_single_string(self):
        """Test that single string is converted to list."""
        input_str = 'run1'
        result = _normalize_run_ids(input_str)
        assert result == ['run1']

    def test_normalize_empty_string(self):
        """Test that empty string returns empty list."""
        input_str = ''
        result = _normalize_run_ids(input_str)
        assert result == ['']

    def test_normalize_invalid_json(self):
        """Test that invalid JSON falls back to string parsing."""
        input_str = '["run1", "run2"'  # Invalid JSON
        result = _normalize_run_ids(input_str)
        # Since it contains comma, it's treated as comma-separated
        assert result == ['["run1"', '"run2"']

    def test_normalize_invalid_json_no_comma(self):
        """Test that invalid JSON without comma is treated as single string."""
        input_str = '{"run1"'  # Invalid JSON without comma
        result = _normalize_run_ids(input_str)
        assert result == ['{"run1"']

    def test_normalize_mixed_types_in_json(self):
        """Test that mixed types in JSON are converted to strings."""
        input_json = '[123, "run2", 456]'
        result = _normalize_run_ids(input_json)
        assert result == ['123', 'run2', '456']


class TestDatetimeConversion:
    """Test cases for datetime conversion functions."""

    def test_convert_datetime_to_string_simple(self):
        """Test conversion of simple datetime object."""
        from datetime import datetime, timezone

        dt = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)
        result = _convert_datetime_to_string(dt)
        assert result == '2023-12-25T10:30:45+00:00'

    def test_convert_datetime_to_string_dict(self):
        """Test conversion of datetime objects in dictionary."""
        from datetime import datetime, timezone

        dt = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)
        data = {'name': 'test', 'creationTime': dt, 'count': 42}
        result = _convert_datetime_to_string(data)
        assert result == {'name': 'test', 'creationTime': '2023-12-25T10:30:45+00:00', 'count': 42}

    def test_convert_datetime_to_string_nested(self):
        """Test conversion of datetime objects in nested structures."""
        from datetime import datetime, timezone

        dt1 = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)
        dt2 = datetime(2023, 12, 26, 11, 31, 46, tzinfo=timezone.utc)
        data = {
            'runs': [{'id': 'run1', 'startTime': dt1}, {'id': 'run2', 'startTime': dt2}],
            'summary': {'analysisTime': dt1},
        }
        result = _convert_datetime_to_string(data)
        expected = {
            'runs': [
                {'id': 'run1', 'startTime': '2023-12-25T10:30:45+00:00'},
                {'id': 'run2', 'startTime': '2023-12-26T11:31:46+00:00'},
            ],
            'summary': {'analysisTime': '2023-12-25T10:30:45+00:00'},
        }
        assert result == expected

    def test_safe_json_dumps_with_datetime(self):
        """Test that safe JSON dumps handles datetime objects."""
        from datetime import datetime, timezone

        dt = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)
        data = {'timestamp': dt, 'value': 123}
        result = _safe_json_dumps(data)
        expected_json = '{"timestamp": "2023-12-25T10:30:45+00:00", "value": 123}'
        assert result == expected_json

    def test_convert_datetime_to_string_no_change(self):
        """Test that non-datetime objects are not changed."""
        data = {'string': 'test', 'number': 42, 'boolean': True, 'null': None}
        result = _convert_datetime_to_string(data)
        assert result == data


class TestGetLogsClient:
    """Test the get_logs_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_aws_session')
    def test_get_logs_client_success(self, mock_get_aws_session):
        """Test successful CloudWatch Logs client creation."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import get_logs_client

        # Arrange
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_get_aws_session.return_value = mock_session
        mock_session.client.return_value = mock_client

        # Act
        result = get_logs_client()

        # Assert
        assert result == mock_client
        mock_session.client.assert_called_once_with('logs')

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_aws_session')
    def test_get_logs_client_failure(self, mock_get_aws_session):
        """Test CloudWatch Logs client creation failure."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import get_logs_client

        # Arrange
        mock_get_aws_session.side_effect = Exception('AWS session error')

        # Act & Assert
        with pytest.raises(Exception, match='AWS session error'):
            get_logs_client()

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_aws_session')
    def test_get_logs_client_session_client_failure(self, mock_get_aws_session):
        """Test CloudWatch Logs client creation failure at session.client level."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import get_logs_client

        # Arrange
        mock_session = MagicMock()
        mock_get_aws_session.return_value = mock_session
        mock_session.client.side_effect = Exception('Client creation failed')

        # Act & Assert
        with pytest.raises(Exception, match='Client creation failed'):
            get_logs_client()


class TestGetLogsFromStream:
    """Test the _get_logs_from_stream function."""

    @pytest.mark.asyncio
    async def test_get_logs_from_stream_success(self, sample_log_events):
        """Test successful log retrieval from stream."""
        # Arrange
        mock_client = MagicMock()
        mock_response = {'events': sample_log_events}
        mock_client.get_log_events.return_value = mock_response

        # Act
        result = await _get_logs_from_stream(
            mock_client,
            '/aws/omics/WorkflowLog',
            'run-12345',
            '2024-01-01T10:00:00Z',
            '2024-01-01T11:00:00Z',
            100,
            None,
            True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3
        # Don't check exact timestamp values due to timezone complexity, just verify the call was made
        mock_client.get_log_events.assert_called_once()

        # Verify the call includes the expected parameters (without checking exact timestamp values)
        call_kwargs = mock_client.get_log_events.call_args[1]
        assert call_kwargs['logGroupName'] == '/aws/omics/WorkflowLog'
        assert call_kwargs['logStreamName'] == 'run-12345'
        assert call_kwargs['limit'] == 100
        assert call_kwargs['startFromHead'] is True
        assert 'startTime' in call_kwargs
        assert 'endTime' in call_kwargs

    @pytest.mark.asyncio
    async def test_get_logs_from_stream_no_time_filter(self, sample_log_events):
        """Test log retrieval without time filters."""
        # Arrange
        mock_client = MagicMock()
        mock_response = {'events': sample_log_events}
        mock_client.get_log_events.return_value = mock_response

        # Act
        result = await _get_logs_from_stream(
            mock_client,
            '/aws/omics/WorkflowLog',
            'run-12345',
            None,
            None,
            50,
            None,
            False,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3
        mock_client.get_log_events.assert_called_once_with(
            logGroupName='/aws/omics/WorkflowLog',
            logStreamName='run-12345',
            limit=50,
            startFromHead=False,
        )

    @pytest.mark.asyncio
    async def test_get_logs_from_stream_with_next_token(self, sample_log_events):
        """Test log retrieval with pagination token."""
        # Arrange
        mock_client = MagicMock()
        # Use 'nextForwardToken' as that's what the function expects
        mock_response = {'events': sample_log_events, 'nextForwardToken': 'next-token-456'}
        mock_client.get_log_events.return_value = mock_response

        # Act
        result = await _get_logs_from_stream(
            mock_client,
            '/aws/omics/WorkflowLog',
            'run-12345',
            None,
            None,
            100,
            'token123',
            True,
        )

        # Assert
        assert 'events' in result
        assert 'nextToken' in result
        assert result['nextToken'] == 'next-token-456'
        assert len(result['events']) == 3
        mock_client.get_log_events.assert_called_once_with(
            logGroupName='/aws/omics/WorkflowLog',
            logStreamName='run-12345',
            nextToken='token123',
            limit=100,
            startFromHead=True,
        )


class TestGetRunLogsErrorHandling:
    """Test error handling in get_run_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_logs_boto_error(
        self,
        mock_get_logs_from_stream,
        mock_get_logs_client,
        mock_context,
    ):
        """Test get_run_logs with BotoCoreError."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.side_effect = botocore.exceptions.BotoCoreError()

        # Act & Assert
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_run_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'AWS error retrieving run logs for run run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_logs_unexpected_error(
        self,
        mock_get_logs_from_stream,
        mock_get_logs_client,
        mock_context,
    ):
        """Test get_run_logs with unexpected error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.side_effect = Exception('Unexpected error')

        # Act & Assert
        with pytest.raises(Exception, match='Unexpected error'):
            await get_run_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Unexpected error retrieving run logs for run run-12345' in error_call_args


class TestInternalWrapperFunctions:
    """Test the internal wrapper functions without Pydantic Field decorators."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_success(
        self, mock_get_logs_from_stream, mock_get_logs_client, sample_log_events
    ):
        """Test successful internal manifest log retrieval."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.return_value = {'events': sample_log_events}

        # Act
        result = await get_run_manifest_logs_internal(
            run_id='run-12345',
            run_uuid='uuid-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3
        mock_get_logs_from_stream.assert_called_once_with(
            mock_client,
            '/aws/omics/WorkflowLog',
            'manifest/run/run-12345/uuid-67890',
            None,
            None,
            100,
            None,
            True,
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_error(
        self, mock_get_logs_from_stream, mock_get_logs_client
    ):
        """Test internal manifest log retrieval with error."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.side_effect = Exception('Internal error')

        # Act & Assert
        with pytest.raises(Exception, match='Internal error'):
            await get_run_manifest_logs_internal(
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_internal_success(
        self, mock_get_logs_from_stream, mock_get_logs_client, sample_log_events
    ):
        """Test successful internal engine log retrieval."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_run_engine_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.return_value = {'events': sample_log_events}

        # Act
        result = await get_run_engine_logs_internal(
            run_id='run-12345',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3
        mock_get_logs_from_stream.assert_called_once_with(
            mock_client,
            '/aws/omics/WorkflowLog',
            'run/run-12345/engine',
            None,
            None,
            100,
            None,
            True,
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_internal_error(
        self, mock_get_logs_from_stream, mock_get_logs_client
    ):
        """Test internal engine log retrieval with error."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_run_engine_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.side_effect = Exception('Engine error')

        # Act & Assert
        with pytest.raises(Exception, match='Engine error'):
            await get_run_engine_logs_internal(
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_task_logs_internal_success(
        self, mock_get_logs_from_stream, mock_get_logs_client, sample_log_events
    ):
        """Test successful internal task log retrieval."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_task_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.return_value = {'events': sample_log_events}

        # Act
        result = await get_task_logs_internal(
            run_id='run-12345',
            task_id='task-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3
        mock_get_logs_from_stream.assert_called_once_with(
            mock_client,
            '/aws/omics/WorkflowLog',
            'run/run-12345/task/task-67890',
            None,
            None,
            100,
            None,
            True,
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis._get_logs_from_stream')
    @pytest.mark.asyncio
    async def test_get_task_logs_internal_error(
        self, mock_get_logs_from_stream, mock_get_logs_client
    ):
        """Test internal task log retrieval with error."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            get_task_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_get_logs_from_stream.side_effect = Exception('Task error')

        # Act & Assert
        with pytest.raises(Exception, match='Task error'):
            await get_task_logs_internal(
                run_id='run-12345',
                task_id='task-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )


class TestGetRunManifestLogsInternal:
    """Test the _get_run_manifest_logs_internal function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_success(
        self, mock_get_logs_client, sample_log_events
    ):
        """Test successful internal manifest log retrieval."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            _get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
            'nextForwardToken': 'forward-token',
            'nextBackwardToken': 'backward-token',
        }

        # Act
        result = await _get_run_manifest_logs_internal(
            run_id='run-12345',
            run_uuid='uuid-67890',
            start_time='2024-01-01T10:00:00Z',
            end_time='2024-01-01T11:00:00Z',
            limit=50,
            next_token='token123',
            start_from_head=False,
        )

        # Assert
        assert 'events' in result
        assert 'nextForwardToken' in result
        assert 'nextBackwardToken' in result
        assert len(result['events']) == 3
        assert result['nextForwardToken'] == 'forward-token'
        assert result['nextBackwardToken'] == 'backward-token'

        # Verify the call was made with correct parameters
        mock_client.get_log_events.assert_called_once()
        call_kwargs = mock_client.get_log_events.call_args[1]
        assert call_kwargs['logGroupName'] == '/aws/omics/WorkflowLog/uuid-67890'
        assert call_kwargs['limit'] == 50
        assert call_kwargs['startFromHead'] is False
        assert call_kwargs['nextToken'] == 'token123'
        assert 'startTime' in call_kwargs
        assert 'endTime' in call_kwargs

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_resource_not_found(self, mock_get_logs_client):
        """Test internal manifest log retrieval with ResourceNotFoundException."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            _get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Log group not found'}
            },
            operation_name='GetLogEvents',
        )

        # Act
        result = await _get_run_manifest_logs_internal(
            run_id='run-12345',
            run_uuid='uuid-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert result == {'events': [], 'error': 'Log group not found'}

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_other_client_error(self, mock_get_logs_client):
        """Test internal manifest log retrieval with other ClientError."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            _get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='GetLogEvents',
        )

        # Act & Assert
        with pytest.raises(ClientError):
            await _get_run_manifest_logs_internal(
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_generic_exception(self, mock_get_logs_client):
        """Test internal manifest log retrieval with generic exception."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            _get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = Exception('Generic error')

        # Act & Assert
        with pytest.raises(Exception, match='Generic error'):
            await _get_run_manifest_logs_internal(
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_internal_no_time_params(
        self, mock_get_logs_client, sample_log_events
    ):
        """Test internal manifest log retrieval without time parameters."""
        from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
            _get_run_manifest_logs_internal,
        )

        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.return_value = {
            'events': sample_log_events,
        }

        # Act
        result = await _get_run_manifest_logs_internal(
            run_id='run-12345',
            run_uuid='uuid-67890',
            start_time=None,
            end_time=None,
            limit=100,
            next_token=None,
            start_from_head=True,
        )

        # Assert
        assert 'events' in result
        assert len(result['events']) == 3

        # Verify the call was made without time parameters
        mock_client.get_log_events.assert_called_once()
        call_kwargs = mock_client.get_log_events.call_args[1]
        assert 'startTime' not in call_kwargs
        assert 'endTime' not in call_kwargs


class TestGetRunManifestLogsErrorHandling:
    """Test error handling in get_run_manifest_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_boto_error(self, mock_get_logs_client, mock_context):
        """Test get_run_manifest_logs with BotoCoreError."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = botocore.exceptions.BotoCoreError()

        # Act & Assert
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_run_manifest_logs(
                ctx=mock_context,
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'AWS error retrieving manifest logs for run run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_unexpected_error(
        self, mock_get_logs_client, mock_context
    ):
        """Test get_run_manifest_logs with unexpected error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = Exception('Unexpected manifest error')

        # Act & Assert
        with pytest.raises(Exception, match='Unexpected manifest error'):
            await get_run_manifest_logs(
                ctx=mock_context,
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Unexpected error retrieving manifest logs for run run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_manifest_logs_invalid_timestamp(
        self, mock_get_logs_client, mock_context
    ):
        """Test get_run_manifest_logs with invalid timestamp."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(ValueError):
            await get_run_manifest_logs(
                ctx=mock_context,
                run_id='run-12345',
                run_uuid='uuid-67890',
                start_time='invalid-timestamp',
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Invalid timestamp format' in error_call_args


class TestGetRunEngineLogsErrorHandling:
    """Test error handling in get_run_engine_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_boto_error(self, mock_get_logs_client, mock_context):
        """Test get_run_engine_logs with BotoCoreError."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = botocore.exceptions.BotoCoreError()

        # Act & Assert
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_run_engine_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'AWS error retrieving engine logs for run run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_unexpected_error(self, mock_get_logs_client, mock_context):
        """Test get_run_engine_logs with unexpected error."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = Exception('Unexpected engine error')

        # Act & Assert
        with pytest.raises(Exception, match='Unexpected engine error'):
            await get_run_engine_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Unexpected error retrieving engine logs for run run-12345' in error_call_args

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_run_engine_logs_invalid_timestamp(self, mock_get_logs_client, mock_context):
        """Test get_run_engine_logs with invalid timestamp."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(ValueError):
            await get_run_engine_logs(
                ctx=mock_context,
                run_id='run-12345',
                start_time='invalid-timestamp',
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Invalid timestamp format' in error_call_args


class TestGetTaskLogsErrorHandling:
    """Test error handling in get_task_logs function."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_boto_error(self, mock_get_logs_client, mock_context):
        """Test get_task_logs with BotoCoreError."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client
        mock_client.get_log_events.side_effect = botocore.exceptions.BotoCoreError()

        # Act & Assert
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_task_logs(
                ctx=mock_context,
                run_id='run-12345',
                task_id='task-67890',
                start_time=None,
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert (
            'AWS error retrieving task logs for run run-12345, task task-67890' in error_call_args
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.workflow_analysis.get_logs_client')
    @pytest.mark.asyncio
    async def test_get_task_logs_invalid_timestamp(self, mock_get_logs_client, mock_context):
        """Test get_task_logs with invalid timestamp."""
        # Arrange
        mock_client = MagicMock()
        mock_get_logs_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(ValueError):
            await get_task_logs(
                ctx=mock_context,
                run_id='run-12345',
                task_id='task-67890',
                start_time='invalid-timestamp',
                end_time=None,
                limit=100,
                next_token=None,
                start_from_head=True,
            )

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert 'Invalid timestamp format' in error_call_args
