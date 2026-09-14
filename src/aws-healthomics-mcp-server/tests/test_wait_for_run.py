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

"""Tests for waiting on a HealthOmics run to reach a terminal status."""

import pytest
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_RUN_POLL_INTERVAL_SECONDS
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import (
    format_run_response,
    wait_for_run,
)
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


RUN_ID = '4194589'


def _run(status: str, **extra):
    """Build a GetRun API response with the given status."""
    response = {
        'id': RUN_ID,
        'arn': f'arn:aws:omics:us-east-1:123456789012:run/{RUN_ID}',
        'name': 'test-run',
        'status': status,
        'workflowId': '3344054',
        'workflowType': 'PRIVATE',
        'creationTime': datetime(2026, 8, 7, 0, 3, 49, tzinfo=timezone.utc),
        'outputUri': 's3://bucket/outputs/',
        'roleArn': 'arn:aws:iam::123456789012:role/OmicsServiceRole',
        'runOutputUri': f's3://bucket/outputs/{RUN_ID}',
    }
    response.update(extra)
    return response


def _client(*statuses):
    """Build a mock omics client that reports the given statuses in order."""
    client = MagicMock()
    client.get_run.side_effect = [_run(s) for s in statuses]
    return client


class TestFormatRunResponse:
    """Tests for format_run_response, shared by get_run and wait_for_run."""

    def test_renders_datetimes_as_iso_strings(self):
        """Datetime fields are converted to ISO 8601 strings."""
        result = format_run_response(
            _run(
                'COMPLETED',
                startTime=datetime(2026, 8, 7, 0, 4, 19, tzinfo=timezone.utc),
                stopTime=datetime(2026, 8, 7, 0, 10, 51, tzinfo=timezone.utc),
            )
        )
        assert result['creationTime'] == '2026-08-07T00:03:49+00:00'
        assert result['startTime'] == '2026-08-07T00:04:19+00:00'
        assert result['stopTime'] == '2026-08-07T00:10:51+00:00'

    def test_omits_absent_optional_fields(self):
        """Optional fields the API did not return are left out."""
        result = format_run_response(_run('PENDING'))
        assert 'startTime' not in result
        assert 'stopTime' not in result
        assert 'failureReason' not in result

    def test_includes_failure_reason_when_present(self):
        """Failure details are carried through when the API returns them."""
        result = format_run_response(
            _run('FAILED', failureReason='WORKFLOW_RUN_FAILED', statusMessage='see logs')
        )
        assert result['failureReason'] == 'WORKFLOW_RUN_FAILED'
        assert result['statusMessage'] == 'see logs'

    def test_handles_missing_creation_time(self):
        """A response without creationTime does not raise."""
        response = _run('PENDING')
        del response['creationTime']
        assert format_run_response(response)['creationTime'] is None


class TestWaitForRun:
    """Tests for the wait_for_run tool."""

    @pytest.mark.asyncio
    async def test_returns_immediately_when_already_terminal(self):
        """A run that has already completed returns without sleeping."""
        client = _client('COMPLETED')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['status'] == 'COMPLETED'
        assert result['timedOut'] is False
        assert result['pollCount'] == 1
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_polls_through_intermediate_statuses(self):
        """Polling continues until a terminal status is observed."""
        client = _client('PENDING', 'RUNNING', 'COMPLETED')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['status'] == 'COMPLETED'
        assert result['pollCount'] == 3
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_treats_stopping_as_not_terminal(self):
        """STOPPING is an intermediate status, so waiting continues through it.

        The service reports STOPPING while outputs are exported after the last task
        finishes. It is absent from the documented status list, so a terminal check
        based on that list would return a non-final status.
        """
        client = _client('RUNNING', 'STOPPING', 'COMPLETED')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ),
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['status'] == 'COMPLETED'
        assert result['pollCount'] == 3

    @pytest.mark.asyncio
    async def test_failed_status_is_terminal(self):
        """A failed run ends the wait and is not reported as a tool error."""
        client = MagicMock()
        client.get_run.return_value = _run('FAILED', failureReason='WORKFLOW_RUN_FAILED')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=client,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['status'] == 'FAILED'
        assert result['timedOut'] is False
        assert result['run']['failureReason'] == 'WORKFLOW_RUN_FAILED'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_cancelled_status_is_terminal(self):
        """A cancelled run ends the wait."""
        client = MagicMock()
        client.get_run.return_value = _run('CANCELLED')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=client,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['status'] == 'CANCELLED'
        assert result['timedOut'] is False

    @pytest.mark.asyncio
    async def test_timeout_reports_last_status_without_error(self):
        """Reaching the timeout returns the last status rather than raising."""
        client = MagicMock()
        client.get_run.return_value = _run('RUNNING')

        # A monotonic clock that jumps past the timeout on the second reading
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.time.monotonic',
                side_effect=[0.0, 100.0],
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID, timeout_seconds=60)

        assert result['timedOut'] is True
        assert result['status'] == 'RUNNING'
        assert result['pollCount'] == 1
        assert 'error' not in result
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sleep_is_clamped_to_remaining_time(self):
        """The final sleep does not overshoot the timeout."""
        client = MagicMock()
        client.get_run.return_value = _run('RUNNING')

        # 50s elapsed against a 60s timeout leaves 10s, less than the 30s interval
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.time.monotonic',
                side_effect=[0.0, 50.0, 60.0],
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            result = await wait_for_run(
                AsyncMock(), run_id=RUN_ID, timeout_seconds=60, poll_interval_seconds=30
            )

        assert result['timedOut'] is True
        mock_sleep.assert_awaited_once_with(10.0)

    @pytest.mark.asyncio
    async def test_field_defaults_are_resolved_when_omitted(self):
        """Omitted timeout and interval fall back to ints, not FieldInfo objects.

        FastMCP passes unevaluated Field objects through for arguments the caller did
        not supply, so the timeout arithmetic must not assume it received an int.
        """
        client = _client('RUNNING', 'COMPLETED')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
                return_value=client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.asyncio.sleep',
                new_callable=AsyncMock,
            ) as mock_sleep,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert 'error' not in result
        assert result['status'] == 'COMPLETED'
        # The default interval is used rather than a FieldInfo object
        mock_sleep.assert_awaited_once_with(DEFAULT_RUN_POLL_INTERVAL_SECONDS)

    @pytest.mark.asyncio
    async def test_api_error_is_reported_through_handle_tool_error(self):
        """An API failure while polling is surfaced as an error result."""
        client = MagicMock()
        client.get_run.side_effect = RuntimeError('throttled')
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=client,
        ):
            result = await wait_for_run(ctx, run_id=RUN_ID)

        assert 'error' in result
        assert 'throttled' in result['error']
        ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_carries_full_run_details(self):
        """The terminal run details are returned alongside the status summary."""
        client = MagicMock()
        client.get_run.return_value = _run(
            'COMPLETED',
            startTime=datetime(2026, 8, 7, 0, 4, 19, tzinfo=timezone.utc),
            stopTime=datetime(2026, 8, 7, 0, 10, 51, tzinfo=timezone.utc),
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=client,
        ):
            result = await wait_for_run(AsyncMock(), run_id=RUN_ID)

        assert result['id'] == RUN_ID
        assert result['run']['runOutputUri'] == f's3://bucket/outputs/{RUN_ID}'
        assert result['run']['stopTime'] == '2026-08-07T00:10:51+00:00'
        assert isinstance(result['elapsedSeconds'], float)
