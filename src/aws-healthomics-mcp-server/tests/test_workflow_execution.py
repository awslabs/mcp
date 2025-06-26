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

"""Unit tests for workflow execution tools."""

import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import (
    get_run,
    list_run_tasks,
    list_runs,
    start_run,
)
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_run_success():
    """Test successful retrieval of run details."""
    # Mock response data
    creation_time = datetime.now(timezone.utc)
    start_time = creation_time
    stop_time = datetime.now(timezone.utc)

    mock_response = {
        'id': 'run-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
        'name': 'test-run',
        'status': 'COMPLETED',
        'workflowId': 'wfl-12345',
        'workflowType': 'WDL',
        'workflowVersionName': 'v1.0',
        'creationTime': creation_time,
        'startTime': start_time,
        'stopTime': stop_time,
        'outputUri': 's3://bucket/output/',
        'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
        'runOutputUri': 's3://bucket/run-output/',
        'parameters': {'param1': 'value1'},
        'uuid': 'abc-123-def-456',
        'statusMessage': 'Run completed successfully',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_run(mock_ctx, run_id='run-12345')

    # Verify client was called correctly
    mock_client.get_run.assert_called_once_with(id='run-12345')

    # Verify result contains all expected fields
    assert result['id'] == 'run-12345'
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:run/run-12345'
    assert result['name'] == 'test-run'
    assert result['status'] == 'COMPLETED'
    assert result['workflowId'] == 'wfl-12345'
    assert result['workflowType'] == 'WDL'
    assert result['workflowVersionName'] == 'v1.0'
    assert result['creationTime'] == creation_time.isoformat()
    assert result['startTime'] == start_time.isoformat()
    assert result['stopTime'] == stop_time.isoformat()
    assert result['outputUri'] == 's3://bucket/output/'
    assert result['roleArn'] == 'arn:aws:iam::123456789012:role/HealthOmicsRole'
    assert result['runOutputUri'] == 's3://bucket/run-output/'
    assert result['parameters'] == {'param1': 'value1'}
    assert result['uuid'] == 'abc-123-def-456'
    assert result['statusMessage'] == 'Run completed successfully'


@pytest.mark.asyncio
async def test_get_run_minimal_response():
    """Test run retrieval with minimal response fields."""
    # Mock response with minimal fields
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'id': 'run-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
        'name': 'test-run',
        'status': 'QUEUED',
        'workflowId': 'wfl-12345',
        'workflowType': 'WDL',
        'creationTime': creation_time,
        'outputUri': 's3://bucket/output/',
        'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
        'runOutputUri': 's3://bucket/run-output/',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_run(mock_ctx, run_id='run-12345')

    # Verify required fields
    assert result['id'] == 'run-12345'
    assert result['status'] == 'QUEUED'
    assert result['creationTime'] == creation_time.isoformat()
    assert result['roleArn'] == 'arn:aws:iam::123456789012:role/HealthOmicsRole'
    assert result['runOutputUri'] == 's3://bucket/run-output/'

    # Verify optional fields are not present
    assert 'startTime' not in result
    assert 'stopTime' not in result
    assert 'parameters' not in result
    assert 'statusMessage' not in result
    assert 'failureReason' not in result


@pytest.mark.asyncio
async def test_get_run_failed_status():
    """Test run retrieval with failed status and failure reason."""
    # Mock response for failed run
    mock_response = {
        'id': 'run-12345',
        'status': 'FAILED',
        'failureReason': 'Resource quota exceeded',
        'statusMessage': 'Run failed due to resource constraints',
        'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
        'runOutputUri': 's3://bucket/run-output/',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_run(mock_ctx, run_id='run-12345')

    # Verify failure information
    assert result['status'] == 'FAILED'
    assert result['failureReason'] == 'Resource quota exceeded'
    assert result['statusMessage'] == 'Run failed due to resource constraints'


@pytest.mark.asyncio
async def test_get_run_boto_error():
    """Test handling of BotoCoreError."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_run(mock_ctx, run_id='run-12345')

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error getting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_run_client_error():
    """Test handling of ClientError."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.side_effect = botocore.exceptions.ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Run not found'}}, 'GetRun'
    )

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.ClientError):
            await get_run(mock_ctx, run_id='run-12345')

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error getting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_run_unexpected_error():
    """Test handling of unexpected errors."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await get_run(mock_ctx, run_id='run-12345')

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error getting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_run_none_timestamps():
    """Test handling of None values for timestamps."""
    # Mock response with None timestamps
    mock_response = {
        'id': 'run-12345',
        'status': 'PENDING',
        'creationTime': None,
        'startTime': None,
        'stopTime': None,
        'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
        'runOutputUri': 's3://bucket/run-output/',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_run(mock_ctx, run_id='run-12345')

    # Verify timestamp handling
    assert result['creationTime'] is None
    assert 'startTime' not in result
    assert 'stopTime' not in result


# Tests for list_runs function


@pytest.mark.asyncio
async def test_list_runs_success():
    """Test successful listing of runs."""
    # Mock response data
    creation_time = datetime.now(timezone.utc)
    start_time = datetime.now(timezone.utc)
    stop_time = datetime.now(timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-12345',
                'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
                'name': 'test-run-1',
                'status': 'COMPLETED',
                'workflowId': 'wfl-12345',
                'workflowType': 'WDL',
                'creationTime': creation_time,
                'startTime': start_time,
                'stopTime': stop_time,
            },
            {
                'id': 'run-67890',
                'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-67890',
                'name': 'test-run-2',
                'status': 'RUNNING',
                'workflowId': 'wfl-67890',
                'workflowType': 'CWL',
                'creationTime': creation_time,
                'startTime': start_time,
            },
        ],
        'nextToken': 'next-page-token',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before=None,
        )

    # Verify client was called correctly
    mock_client.list_runs.assert_called_once_with(maxResults=10)

    # Verify result structure
    assert 'runs' in result
    assert 'nextToken' in result
    assert result['nextToken'] == 'next-page-token'
    assert len(result['runs']) == 2

    # Verify first run
    run1 = result['runs'][0]
    assert run1['id'] == 'run-12345'
    assert run1['name'] == 'test-run-1'
    assert run1['status'] == 'COMPLETED'
    assert run1['workflowId'] == 'wfl-12345'
    assert run1['workflowType'] == 'WDL'
    assert run1['creationTime'] == creation_time.isoformat()
    assert run1['startTime'] == start_time.isoformat()
    assert run1['stopTime'] == stop_time.isoformat()

    # Verify second run (no stopTime)
    run2 = result['runs'][1]
    assert run2['id'] == 'run-67890'
    assert run2['status'] == 'RUNNING'
    assert 'stopTime' not in run2


@pytest.mark.asyncio
async def test_list_runs_with_filters():
    """Test listing runs with status filter (no date filters)."""
    mock_response = {'items': []}

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        await list_runs(
            ctx=mock_ctx,
            max_results=25,
            next_token='previous-token',
            status='COMPLETED',
            created_after=None,
            created_before=None,
        )

    # Verify client was called with status filter only (no date filters)
    mock_client.list_runs.assert_called_once_with(
        maxResults=25,
        startingToken='previous-token',
        status='COMPLETED',
    )


@pytest.mark.asyncio
async def test_list_runs_empty_response():
    """Test listing runs with empty response."""
    mock_response = {'items': []}

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before=None,
        )

    # Verify empty result
    assert result['runs'] == []
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_runs_invalid_status():
    """Test listing runs with invalid status."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Invalid run status'):
        await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status='INVALID_STATUS',
            created_after=None,
            created_before=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Invalid run status' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_runs_boto_error():
    """Test handling of BotoCoreError in list_runs."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error listing runs' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_runs_client_error():
    """Test handling of ClientError in list_runs."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.side_effect = botocore.exceptions.ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListRuns'
    )

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.ClientError):
            await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error listing runs' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_runs_unexpected_error():
    """Test handling of unexpected errors in list_runs."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error listing runs' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_runs_minimal_run_data():
    """Test listing runs with minimal run data."""
    # Mock response with minimal fields
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'items': [
            {
                'id': 'run-12345',
                'status': 'QUEUED',
                'creationTime': creation_time,
            }
        ]
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before=None,
        )

    # Verify minimal run data
    run = result['runs'][0]
    assert run['id'] == 'run-12345'
    assert run['status'] == 'QUEUED'
    assert run['creationTime'] == creation_time.isoformat()

    # Verify optional fields are not present
    assert run.get('arn') is None
    assert run.get('name') is None
    assert run.get('workflowId') is None
    assert run.get('workflowType') is None
    assert 'startTime' not in run
    assert 'stopTime' not in run


@pytest.mark.asyncio
async def test_list_runs_none_timestamps():
    """Test listing runs with None timestamps."""
    # Mock response with None timestamps
    mock_response = {
        'items': [
            {
                'id': 'run-12345',
                'status': 'PENDING',
                'creationTime': None,
                'startTime': None,
                'stopTime': None,
            }
        ]
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before=None,
        )

    # Verify timestamp handling
    run = result['runs'][0]
    assert run['creationTime'] is None
    assert 'startTime' not in run
    assert 'stopTime' not in run


@pytest.mark.asyncio
async def test_list_runs_default_parameters():
    """Test list_runs with default parameters."""
    mock_response = {'items': []}

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before=None,
        )

    # Verify client was called with default parameters only
    mock_client.list_runs.assert_called_once_with(maxResults=10)


@pytest.mark.asyncio
async def test_list_runs_with_date_filters():
    """Test listing runs with client-side date filtering."""
    # Create test data with different creation times
    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-1',
                'name': 'old-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-1',
                'workflowType': 'WDL',
                'creationTime': base_time - timedelta(days=10),  # 2023-06-05
            },
            {
                'id': 'run-2',
                'name': 'middle-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-2',
                'workflowType': 'WDL',
                'creationTime': base_time,  # 2023-06-15
            },
            {
                'id': 'run-3',
                'name': 'new-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-3',
                'workflowType': 'WDL',
                'creationTime': base_time + timedelta(days=10),  # 2023-06-25
            },
        ]
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        # Test filtering with created_after
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after='2023-06-10T00:00:00Z',
            created_before=None,
        )

    # Should return runs created after 2023-06-10 (run-2 and run-3)
    assert len(result['runs']) == 2
    assert result['runs'][0]['id'] == 'run-2'
    assert result['runs'][1]['id'] == 'run-3'

    # Verify client was called with larger batch size for filtering
    mock_client.list_runs.assert_called_once_with(maxResults=100)


@pytest.mark.asyncio
async def test_list_runs_with_created_before_filter():
    """Test listing runs with created_before filter."""
    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-1',
                'name': 'old-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-1',
                'workflowType': 'WDL',
                'creationTime': base_time - timedelta(days=10),  # 2023-06-05
            },
            {
                'id': 'run-2',
                'name': 'middle-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-2',
                'workflowType': 'WDL',
                'creationTime': base_time,  # 2023-06-15
            },
            {
                'id': 'run-3',
                'name': 'new-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-3',
                'workflowType': 'WDL',
                'creationTime': base_time + timedelta(days=10),  # 2023-06-25
            },
        ]
    }

    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        # Test filtering with created_before
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before='2023-06-20T00:00:00Z',
        )

    # Should return runs created before 2023-06-20 (run-1 and run-2)
    assert len(result['runs']) == 2
    assert result['runs'][0]['id'] == 'run-1'
    assert result['runs'][1]['id'] == 'run-2'


@pytest.mark.asyncio
async def test_list_runs_with_both_date_filters():
    """Test listing runs with both created_after and created_before filters."""
    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-1',
                'name': 'old-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-1',
                'workflowType': 'WDL',
                'creationTime': base_time - timedelta(days=10),  # 2023-06-05
            },
            {
                'id': 'run-2',
                'name': 'middle-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-2',
                'workflowType': 'WDL',
                'creationTime': base_time,  # 2023-06-15
            },
            {
                'id': 'run-3',
                'name': 'new-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-3',
                'workflowType': 'WDL',
                'creationTime': base_time + timedelta(days=10),  # 2023-06-25
            },
        ]
    }

    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        # Test filtering with both date filters
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after='2023-06-10T00:00:00Z',
            created_before='2023-06-20T00:00:00Z',
        )

    # Should return only run-2 (created between the two dates)
    assert len(result['runs']) == 1
    assert result['runs'][0]['id'] == 'run-2'


@pytest.mark.asyncio
async def test_list_runs_invalid_created_after():
    """Test list_runs with invalid created_after datetime."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Invalid created_after datetime'):
        await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after='invalid-datetime',
            created_before=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_list_runs_invalid_created_before():
    """Test list_runs with invalid created_before datetime."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Invalid created_before datetime'):
        await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after=None,
            created_before='not-a-datetime',
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_list_runs_date_filter_no_matching_runs():
    """Test date filtering when no runs match the criteria."""
    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-1',
                'name': 'old-run',
                'status': 'COMPLETED',
                'workflowId': 'wfl-1',
                'workflowType': 'WDL',
                'creationTime': base_time - timedelta(days=10),  # 2023-06-05
            },
        ]
    }

    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        # Filter for runs after the only run's creation time
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after='2023-06-10T00:00:00Z',
            created_before=None,
        )

    # Should return empty list
    assert len(result['runs']) == 0
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_runs_date_filter_with_missing_creation_time():
    """Test date filtering when some runs have missing creation times."""
    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    mock_response = {
        'items': [
            {
                'id': 'run-1',
                'name': 'run-with-time',
                'status': 'COMPLETED',
                'workflowId': 'wfl-1',
                'workflowType': 'WDL',
                'creationTime': base_time,
            },
            {
                'id': 'run-2',
                'name': 'run-without-time',
                'status': 'COMPLETED',
                'workflowId': 'wfl-2',
                'workflowType': 'WDL',
                # No creationTime field
            },
        ]
    }

    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_runs(
            ctx=mock_ctx,
            max_results=10,
            next_token=None,
            status=None,
            created_after='2023-06-10T00:00:00Z',
            created_before=None,
        )

    # Should return only the run with a valid creation time
    assert len(result['runs']) == 1
    assert result['runs'][0]['id'] == 'run-1'


@pytest.mark.asyncio
async def test_parse_iso_datetime_various_formats():
    """Test the parse_iso_datetime helper function with various formats."""
    from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import parse_iso_datetime

    # Test various valid formats
    dt1 = parse_iso_datetime('2023-06-15T12:00:00Z')
    assert dt1.year == 2023
    assert dt1.month == 6
    assert dt1.day == 15

    dt2 = parse_iso_datetime('2023-06-15T12:00:00+00:00')
    assert dt2.year == 2023

    dt3 = parse_iso_datetime('2023-06-15T12:00:00')
    assert dt3.year == 2023

    # Test invalid format
    with pytest.raises(ValueError, match='Invalid datetime format'):
        parse_iso_datetime('not-a-date')


@pytest.mark.asyncio
async def test_filter_runs_by_creation_time():
    """Test the filter_runs_by_creation_time helper function."""
    from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import (
        filter_runs_by_creation_time,
    )

    base_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    runs = [
        {
            'id': 'run-1',
            'creationTime': (base_time - timedelta(days=10)).isoformat(),
        },
        {
            'id': 'run-2',
            'creationTime': base_time.isoformat(),
        },
        {
            'id': 'run-3',
            'creationTime': (base_time + timedelta(days=10)).isoformat(),
        },
    ]

    # Test no filters
    result = filter_runs_by_creation_time(runs)
    assert len(result) == 3

    # Test created_after filter
    result = filter_runs_by_creation_time(runs, created_after='2023-06-10T00:00:00Z')
    assert len(result) == 2
    assert result[0]['id'] == 'run-2'
    assert result[1]['id'] == 'run-3'

    # Test created_before filter
    result = filter_runs_by_creation_time(runs, created_before='2023-06-20T00:00:00Z')
    assert len(result) == 2
    assert result[0]['id'] == 'run-1'
    assert result[1]['id'] == 'run-2'

    # Test both filters
    result = filter_runs_by_creation_time(
        runs, created_after='2023-06-10T00:00:00Z', created_before='2023-06-20T00:00:00Z'
    )
    assert len(result) == 1
    assert result[0]['id'] == 'run-2'


@pytest.mark.asyncio
async def test_start_run_success():
    """Test successful workflow run start."""
    # Mock response data
    mock_response = {
        'id': 'run-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
        'status': 'PENDING',
        'name': 'test-run',
        'workflowId': 'wfl-12345',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await start_run(
            mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://my-bucket/outputs/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
            cache_id=None,
            cache_behavior=None,
        )

    # Verify client was called correctly
    mock_client.start_run.assert_called_once_with(
        workflowId='wfl-12345',
        roleArn='arn:aws:iam::123456789012:role/HealthOmicsRole',
        name='test-run',
        outputUri='s3://my-bucket/outputs/',
        parameters={'param1': 'value1'},
        storageType='DYNAMIC',
    )

    # Verify result contains expected fields
    assert result['id'] == 'run-12345'
    assert result['status'] == 'PENDING'
    assert result['name'] == 'test-run'
    assert result['workflowId'] == 'wfl-12345'


@pytest.mark.asyncio
async def test_start_run_with_static_storage():
    """Test workflow run start with static storage."""
    # Mock response data
    mock_response = {
        'id': 'run-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
        'status': 'PENDING',
        'name': 'test-run',
        'workflowId': 'wfl-12345',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        await start_run(
            mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://my-bucket/outputs/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='STATIC',
            storage_capacity=1000,
            cache_id=None,
            cache_behavior=None,
        )

    # Verify client was called with static storage parameters
    mock_client.start_run.assert_called_once_with(
        workflowId='wfl-12345',
        roleArn='arn:aws:iam::123456789012:role/HealthOmicsRole',
        name='test-run',
        outputUri='s3://my-bucket/outputs/',
        parameters={'param1': 'value1'},
        storageType='STATIC',
        storageCapacity=1000,
    )


@pytest.mark.asyncio
async def test_start_run_static_without_capacity():
    """Test workflow run start with static storage but no capacity."""
    # Mock context
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Storage capacity is required'):
        await start_run(
            mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://my-bucket/outputs/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='STATIC',
            storage_capacity=None,
            cache_id=None,
            cache_behavior=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_start_run_with_cache():
    """Test workflow run start with caching enabled."""
    # Mock response data
    mock_response = {
        'id': 'run-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
        'status': 'PENDING',
        'name': 'test-run',
        'workflowId': 'wfl-12345',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        await start_run(
            mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://my-bucket/outputs/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
            cache_id='cache-12345',
            cache_behavior='CACHE_ALWAYS',
        )

    # Verify client was called with cache parameters
    expected_call = mock_client.start_run.call_args[1]
    assert expected_call['cacheId'] == 'cache-12345'
    assert expected_call['cacheBehavior'] == 'CACHE_ALWAYS'


@pytest.mark.asyncio
async def test_start_run_boto_error():
    """Test handling of BotoCoreError in start_run."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.side_effect = botocore.exceptions.BotoCoreError()

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ),
        pytest.raises(botocore.exceptions.BotoCoreError),
    ):
        await start_run(
            mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://my-bucket/outputs/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
            cache_id=None,
            cache_behavior=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error starting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_run_tasks_success():
    """Test successful listing of run tasks."""
    # Mock response data
    creation_time = datetime.now(timezone.utc)
    start_time = creation_time
    stop_time = datetime.now(timezone.utc)

    mock_response = {
        'items': [
            {
                'taskId': 'task-12345',
                'status': 'COMPLETED',
                'name': 'test-task',
                'cpus': 2,
                'memory': 4096,
                'startTime': start_time,
                'stopTime': stop_time,
            },
            {
                'taskId': 'task-67890',
                'status': 'RUNNING',
                'name': 'test-task-2',
                'cpus': 4,
                'memory': 8192,
                'startTime': start_time,
            },
        ],
        'nextToken': 'next-token-123',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_tasks.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_tasks(
            mock_ctx,
            run_id='run-12345',
            max_results=10,
            next_token=None,
            status='COMPLETED',
        )

    # Verify client was called correctly
    mock_client.list_run_tasks.assert_called_once_with(
        id='run-12345',
        maxResults=10,
        status='COMPLETED',
    )

    # Verify result structure
    assert 'tasks' in result
    assert 'nextToken' in result
    assert len(result['tasks']) == 2

    # Verify first task
    task1 = result['tasks'][0]
    assert task1['taskId'] == 'task-12345'
    assert task1['status'] == 'COMPLETED'
    assert task1['name'] == 'test-task'
    assert task1['cpus'] == 2
    assert task1['memory'] == 4096
    assert task1['startTime'] == start_time.isoformat()
    assert task1['stopTime'] == stop_time.isoformat()

    # Verify second task (no stopTime since it's still running)
    task2 = result['tasks'][1]
    assert task2['taskId'] == 'task-67890'
    assert task2['status'] == 'RUNNING'
    assert task2['startTime'] == start_time.isoformat()
    assert 'stopTime' not in task2


@pytest.mark.asyncio
async def test_list_run_tasks_empty_response():
    """Test listing run tasks with empty response."""
    # Mock empty response
    mock_response = {'items': []}

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_tasks.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_tasks(
            mock_ctx,
            run_id='run-12345',
            max_results=10,
            next_token=None,
            status=None,
        )

    # Verify result structure
    assert result['tasks'] == []
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_run_tasks_boto_error():
    """Test handling of BotoCoreError in list_run_tasks."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_tasks.side_effect = botocore.exceptions.BotoCoreError()

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ),
        pytest.raises(botocore.exceptions.BotoCoreError),
    ):
        await list_run_tasks(
            mock_ctx,
            run_id='run-12345',
            max_results=10,
            next_token=None,
            status=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error listing tasks for run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_runs_with_invalid_creation_time():
    """Test list_runs handling of runs with invalid creation times."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()

    # Create a mock datetime object that will fail when isoformat() is called
    class MockInvalidDateTime:
        def isoformat(self):
            raise ValueError('Invalid datetime')

    # Mock response with invalid creation time
    mock_response = {
        'items': [
            {
                'id': 'run-12345',
                'name': 'test-run',
                'status': 'COMPLETED',
                'creationTime': MockInvalidDateTime(),  # Invalid datetime
            },
            {
                'id': 'run-67890',
                'name': 'test-run-2',
                'status': 'COMPLETED',
                'creationTime': datetime.now(timezone.utc),  # Valid datetime
            },
        ],
        'nextToken': None,
    }
    mock_client.list_runs.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        # This should raise an exception due to the invalid datetime
        with pytest.raises(Exception, match='Invalid datetime'):
            await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error listing runs' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_omics_client_failure():
    """Test get_omics_client failure handling."""
    from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import get_omics_client

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_aws_session'
    ) as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.client.side_effect = Exception('Client creation failed')

        with pytest.raises(Exception, match='Client creation failed'):
            get_omics_client()


@pytest.mark.asyncio
async def test_start_run_invalid_storage_type():
    """Test start_run with invalid storage type."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Invalid storage type'):
        await start_run(
            ctx=mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://bucket/output/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='INVALID_TYPE',  # Invalid storage type
            storage_capacity=None,
            cache_id=None,
            cache_behavior=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Invalid storage type' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_start_run_static_storage_without_capacity():
    """Test start_run with STATIC storage but no capacity."""
    mock_ctx = AsyncMock()

    with pytest.raises(
        ValueError, match='Storage capacity is required when using STATIC storage type'
    ):
        await start_run(
            ctx=mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://bucket/output/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='STATIC',
            storage_capacity=None,  # Missing capacity for STATIC storage
            cache_id=None,
            cache_behavior=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert (
        'Storage capacity is required when using STATIC storage type'
        in mock_ctx.error.call_args[0][0]
    )


@pytest.mark.asyncio
async def test_start_run_invalid_cache_behavior():
    """Test start_run with invalid cache behavior."""
    mock_ctx = AsyncMock()

    with pytest.raises(ValueError, match='Invalid cache behavior'):
        await start_run(
            ctx=mock_ctx,
            workflow_id='wfl-12345',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            name='test-run',
            output_uri='s3://bucket/output/',
            parameters={'param1': 'value1'},
            workflow_version_name=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
            cache_id=None,
            cache_behavior='INVALID_BEHAVIOR',  # Invalid cache behavior
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Invalid cache behavior' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_start_run_invalid_s3_uri():
    """Test start_run with invalid S3 URI."""
    mock_ctx = AsyncMock()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.ensure_s3_uri_ends_with_slash'
    ) as mock_ensure_s3_uri:
        mock_ensure_s3_uri.side_effect = ValueError('Invalid S3 URI format')

        with pytest.raises(ValueError, match='Invalid S3 URI'):
            await start_run(
                ctx=mock_ctx,
                workflow_id='wfl-12345',
                role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
                name='test-run',
                output_uri='invalid-uri',  # Invalid S3 URI
                parameters={'param1': 'value1'},
                workflow_version_name=None,
                storage_type='DYNAMIC',
                storage_capacity=None,
                cache_id=None,
                cache_behavior=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Invalid S3 URI' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_start_run_boto_error_new():
    """Test start_run with BotoCoreError."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.ensure_s3_uri_ends_with_slash',
            return_value='s3://bucket/output/',
        ):
            with pytest.raises(botocore.exceptions.BotoCoreError):
                await start_run(
                    ctx=mock_ctx,
                    workflow_id='wfl-12345',
                    role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
                    name='test-run',
                    output_uri='s3://bucket/output/',
                    parameters={'param1': 'value1'},
                    workflow_version_name=None,
                    storage_type='DYNAMIC',
                    storage_capacity=None,
                    cache_id=None,
                    cache_behavior=None,
                )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error starting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_start_run_unexpected_error_new():
    """Test start_run with unexpected error."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.start_run.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.ensure_s3_uri_ends_with_slash',
            return_value='s3://bucket/output/',
        ):
            with pytest.raises(Exception, match='Unexpected error'):
                await start_run(
                    ctx=mock_ctx,
                    workflow_id='wfl-12345',
                    role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
                    name='test-run',
                    output_uri='s3://bucket/output/',
                    parameters={'param1': 'value1'},
                    workflow_version_name=None,
                    storage_type='DYNAMIC',
                    storage_capacity=None,
                    cache_id=None,
                    cache_behavior=None,
                )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error starting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_run_tasks_invalid_status():
    """Test list_run_tasks with invalid status."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()

    # Mock the client to raise a ValidationException for invalid status
    mock_client.list_run_tasks.side_effect = botocore.exceptions.ClientError(
        {'Error': {'Code': 'ValidationException', 'Message': 'Invalid status value'}},
        'ListRunTasks',
    )

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.ClientError):
            await list_run_tasks(
                ctx=mock_ctx,
                run_id='1234567890',  # Use valid run ID format
                max_results=10,
                next_token=None,
                status='INVALID_STATUS',  # Invalid task status
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error listing tasks for run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_run_boto_error_new():
    """Test get_run with BotoCoreError."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_run(ctx=mock_ctx, run_id='run-12345')

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error getting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_run_unexpected_error_new():
    """Test get_run with unexpected error."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await get_run(ctx=mock_ctx, run_id='run-12345')

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error getting run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_run_tasks_boto_error_new():
    """Test list_run_tasks with BotoCoreError."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_tasks.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await list_run_tasks(
                ctx=mock_ctx,
                run_id='1234567890',
                max_results=10,
                next_token=None,
                status=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error listing tasks for run' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_run_tasks_unexpected_error():
    """Test list_run_tasks with unexpected error."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_tasks.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await list_run_tasks(
                ctx=mock_ctx,
                run_id='1234567890',
                max_results=10,
                next_token=None,
                status=None,
            )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error listing tasks for run' in mock_ctx.error.call_args[0][0]
