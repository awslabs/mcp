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

"""Unit tests for run batch tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.consts import (
    BATCH_STATUSES,
    ERROR_INVALID_BATCH_RUN_SETTINGS,
    SUBMISSION_STATUSES,
)
from awslabs.aws_healthomics_mcp_server.tools.run_batch import (
    _validate_batch_run_settings,
    cancel_run_batch,
    delete_batch,
    delete_run_batch,
    get_batch,
    list_batches,
    list_runs_in_batch,
    start_run_batch,
)
from awslabs.aws_healthomics_mcp_server.utils.datetime_utils import (
    datetime_to_iso,
)
from datetime import datetime, timezone
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


# --- Test Wrappers ---

start_run_batch_wrapper = MCPToolTestWrapper(start_run_batch)
get_batch_wrapper = MCPToolTestWrapper(get_batch)
list_batches_wrapper = MCPToolTestWrapper(list_batches)
list_runs_in_batch_wrapper = MCPToolTestWrapper(list_runs_in_batch)
cancel_run_batch_wrapper = MCPToolTestWrapper(cancel_run_batch)
delete_run_batch_wrapper = MCPToolTestWrapper(delete_run_batch)
delete_batch_wrapper = MCPToolTestWrapper(delete_batch)


# --- Sample Response Fixtures ---


@pytest.fixture
def sample_start_run_batch_response():
    """Sample StartRunBatch API response."""
    return {
        'id': 'batch-12345678',
        'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-12345678',
        'status': 'PENDING',
        'uuid': 'uuid-12345678-1234-1234-1234-123456789012',
        'tags': {'env': 'test', 'project': 'genomics'},
    }


@pytest.fixture
def sample_get_batch_response():
    """Sample GetBatch API response."""
    return {
        'id': 'batch-12345678',
        'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-12345678',
        'uuid': 'uuid-12345678-1234-1234-1234-123456789012',
        'name': 'test-batch',
        'status': 'INPROGRESS',
        'totalRuns': 50,
        'defaultRunSetting': {
            'workflowId': 'workflow-123',
            'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
            'outputUri': 's3://output-bucket/results/',
        },
        'submissionSummary': {
            'successCount': 45,
            'failedCount': 2,
            'pendingCount': 3,
        },
        'runSummary': {
            'pendingCount': 5,
            'runningCount': 20,
            'completedCount': 20,
            'failedCount': 3,
            'cancelledCount': 2,
        },
        'creationTime': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        'startTime': datetime(2024, 1, 15, 10, 31, 0, tzinfo=timezone.utc),
        'stopTime': None,
        'tags': {'env': 'test'},
    }


@pytest.fixture
def sample_get_batch_failed_response():
    """Sample GetBatch API response for a failed batch."""
    return {
        'id': 'batch-failed-123',
        'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-failed-123',
        'uuid': 'uuid-failed-123',
        'name': 'failed-batch',
        'status': 'FAILED',
        'totalRuns': 10,
        'defaultRunSetting': {
            'workflowId': 'workflow-123',
            'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
            'outputUri': 's3://output-bucket/results/',
        },
        'submissionSummary': {
            'successCount': 0,
            'failedCount': 10,
            'pendingCount': 0,
        },
        'runSummary': {
            'pendingCount': 0,
            'runningCount': 0,
            'completedCount': 0,
            'failedCount': 0,
            'cancelledCount': 0,
        },
        'creationTime': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        'startTime': None,
        'stopTime': datetime(2024, 1, 15, 10, 32, 0, tzinfo=timezone.utc),
        'failureReason': 'Invalid workflow configuration',
        'tags': None,
    }


@pytest.fixture
def sample_list_batches_response():
    """Sample ListBatches API response."""
    return {
        'items': [
            {
                'id': 'batch-001',
                'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-001',
                'name': 'batch-one',
                'status': 'PROCESSED',
                'creationTime': datetime(2024, 1, 10, 8, 0, 0, tzinfo=timezone.utc),
                'startTime': datetime(2024, 1, 10, 8, 5, 0, tzinfo=timezone.utc),
                'stopTime': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
            },
            {
                'id': 'batch-002',
                'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-002',
                'name': 'batch-two',
                'status': 'INPROGRESS',
                'creationTime': datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
                'startTime': datetime(2024, 1, 15, 9, 2, 0, tzinfo=timezone.utc),
                'stopTime': None,
            },
        ],
        'nextToken': 'token-abc123',
    }


@pytest.fixture
def sample_list_runs_in_batch_response():
    """Sample ListRunsInBatch API response."""
    return {
        'items': [
            {
                'runSettingId': 'sample-001',
                'runId': 'run-001',
                'runArn': 'arn:aws:omics:us-east-1:123456789012:run/run-001',
                'submissionStatus': 'SUCCESS',
            },
            {
                'runSettingId': 'sample-002',
                'runId': 'run-002',
                'runArn': 'arn:aws:omics:us-east-1:123456789012:run/run-002',
                'submissionStatus': 'SUCCESS',
            },
            {
                'runSettingId': 'sample-003',
                'submissionStatus': 'FAILED',
                'submissionFailureReason': 'VALIDATION_ERROR',
                'submissionFailureMessage': 'Invalid input parameters',
            },
        ],
        'nextToken': 'runs-token-xyz',
    }


@pytest.fixture
def sample_inline_batch_run_settings():
    """Sample inline batch run settings."""
    return {
        'inlineSettings': [
            {
                'runSettingId': 'sample-001',
                'name': 'Sample 001 Analysis',
                'parameters': {'input_file': 's3://bucket/sample001.bam'},
            },
            {
                'runSettingId': 'sample-002',
                'name': 'Sample 002 Analysis',
                'parameters': {'input_file': 's3://bucket/sample002.bam'},
            },
        ]
    }


@pytest.fixture
def sample_s3_batch_run_settings():
    """Sample S3 URI batch run settings."""
    return {'s3UriSettings': 's3://config-bucket/batch-config.json'}


# --- Helper Function Tests ---


class TestDatetimeToIso:
    """Tests for datetime_to_iso helper function."""

    def test_convertsdatetime_to_iso(self):
        """Test datetime conversion to ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = datetime_to_iso(dt)
        assert result == '2024-01-15T10:30:00+00:00'

    def test_returns_none_for_none_input(self):
        """Test None input returns None."""
        result = datetime_to_iso(None)
        assert result is None

    def test_handles_naive_datetime(self):
        """Test naive datetime conversion."""
        dt = datetime(2024, 6, 20, 14, 45, 30)
        result = datetime_to_iso(dt)
        assert result == '2024-06-20T14:45:30'


class TestValidateBatchRunSettings:
    """Tests for _validate_batch_run_settings helper function."""

    def test_valid_inline_settings(self, sample_inline_batch_run_settings):
        """Test valid inline settings passes validation."""
        result = _validate_batch_run_settings(sample_inline_batch_run_settings)
        assert result is None

    def test_valid_s3_settings(self, sample_s3_batch_run_settings):
        """Test valid S3 settings passes validation."""
        result = _validate_batch_run_settings(sample_s3_batch_run_settings)
        assert result is None

    def test_both_settings_present_fails(self):
        """Test both inline and S3 settings fails validation."""
        settings = {
            'inlineSettings': [{'runSettingId': 'test'}],
            's3UriSettings': 's3://bucket/config.json',
        }
        result = _validate_batch_run_settings(settings)
        assert result == ERROR_INVALID_BATCH_RUN_SETTINGS

    def test_neither_settings_present_fails(self):
        """Test neither inline nor S3 settings fails validation."""
        settings = {}
        result = _validate_batch_run_settings(settings)
        assert result == ERROR_INVALID_BATCH_RUN_SETTINGS

    def test_empty_inline_settings_passes(self):
        """Test empty inline settings list passes validation."""
        settings = {'inlineSettings': []}
        result = _validate_batch_run_settings(settings)
        assert result is None


# --- start_run_batch Tests ---


class TestStartRunBatch:
    """Tests for start_run_batch tool."""

    @pytest.mark.asyncio
    async def test_success_with_minimal_params(
        self, sample_start_run_batch_response, sample_inline_batch_run_settings
    ):
        """Test successful batch creation with minimal parameters."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run_batch.return_value = sample_start_run_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings=sample_inline_batch_run_settings,
            )

        mock_client.start_run_batch.assert_called_once()
        call_kwargs = mock_client.start_run_batch.call_args[1]

        # Verify required params
        assert 'defaultRunSetting' in call_kwargs
        assert call_kwargs['defaultRunSetting']['workflowId'] == 'workflow-123'
        assert (
            call_kwargs['defaultRunSetting']['roleArn']
            == 'arn:aws:iam::123456789012:role/OmicsRole'
        )
        assert call_kwargs['defaultRunSetting']['outputUri'] == 's3://output-bucket/results/'
        assert call_kwargs['batchRunSettings'] == sample_inline_batch_run_settings

        # Verify response
        assert result['id'] == 'batch-12345678'
        assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:batch/batch-12345678'
        assert result['status'] == 'PENDING'
        assert result['uuid'] == 'uuid-12345678-1234-1234-1234-123456789012'
        assert result['tags'] == {'env': 'test', 'project': 'genomics'}

    @pytest.mark.asyncio
    async def test_success_with_all_params(
        self, sample_start_run_batch_response, sample_s3_batch_run_settings
    ):
        """Test successful batch creation with all parameters."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run_batch.return_value = sample_start_run_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings=sample_s3_batch_run_settings,
                batch_name='my-batch',
                workflow_type='WDL',
                workflow_version_name='v1.0',
                parameters={'ref_genome': 's3://bucket/ref.fa'},
                storage_type='DYNAMIC',
                run_group_id='rg-123',
                cache_id='cache-123',
                cache_behavior='CACHE_ALWAYS',
                retention_mode='RETAIN',
                request_id='req-123',
                tags={'env': 'prod'},
            )

        call_kwargs = mock_client.start_run_batch.call_args[1]

        # Verify all optional params in defaultRunSetting
        default_setting = call_kwargs['defaultRunSetting']
        assert default_setting['workflowType'] == 'WDL'
        assert default_setting['workflowVersionName'] == 'v1.0'
        assert default_setting['parameters'] == {'ref_genome': 's3://bucket/ref.fa'}
        assert default_setting['storageType'] == 'DYNAMIC'
        assert default_setting['runGroupId'] == 'rg-123'
        assert default_setting['cacheId'] == 'cache-123'
        assert default_setting['cacheBehavior'] == 'CACHE_ALWAYS'
        assert default_setting['retentionMode'] == 'RETAIN'

        # Verify top-level optional params
        assert call_kwargs['name'] == 'my-batch'
        assert call_kwargs['requestId'] == 'req-123'
        assert call_kwargs['tags'] == {'env': 'prod'}

        assert result['id'] == 'batch-12345678'

    @pytest.mark.asyncio
    async def test_invalid_batch_run_settings_both_present(self):
        """Test error when both inlineSettings and s3UriSettings are present."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        invalid_settings = {
            'inlineSettings': [{'runSettingId': 'test'}],
            's3UriSettings': 's3://bucket/config.json',
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Invalid parameters: ' + ERROR_INVALID_BATCH_RUN_SETTINGS},
            ) as mock_handle_error,
        ):
            result = await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings=invalid_settings,
            )

        mock_handle_error.assert_called_once()
        mock_client.start_run_batch.assert_not_called()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_invalid_batch_run_settings_neither_present(self):
        """Test error when neither inlineSettings nor s3UriSettings are present."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Invalid parameters'},
            ) as mock_handle_error,
        ):
            result = await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings={},
            )

        mock_handle_error.assert_called_once()
        mock_client.start_run_batch.assert_not_called()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_api_error_handling(self, sample_inline_batch_run_settings):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run_batch.side_effect = Exception('API Error')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error starting run batch: API Error'},
            ) as mock_handle_error,
        ):
            result = await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings=sample_inline_batch_run_settings,
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(
        self, sample_start_run_batch_response, sample_inline_batch_run_settings
    ):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run_batch.return_value = sample_start_run_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await start_run_batch_wrapper.call(
                ctx=mock_ctx,
                workflow_id='workflow-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                output_uri='s3://output-bucket/results/',
                batch_run_settings=sample_inline_batch_run_settings,
                aws_profile='my-profile',
                aws_region='eu-west-1',
            )

        mock_get_client.assert_called_once_with(region_name='eu-west-1', profile_name='my-profile')


# --- get_batch Tests ---


class TestGetBatch:
    """Tests for get_batch tool."""

    @pytest.mark.asyncio
    async def test_success_with_all_fields(self, sample_get_batch_response):
        """Test successful batch retrieval with all fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_batch.return_value = sample_get_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await get_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-12345678',
            )

        mock_client.get_batch.assert_called_once_with(id='batch-12345678')

        assert result['id'] == 'batch-12345678'
        assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:batch/batch-12345678'
        assert result['uuid'] == 'uuid-12345678-1234-1234-1234-123456789012'
        assert result['name'] == 'test-batch'
        assert result['status'] == 'INPROGRESS'
        assert result['totalRuns'] == 50
        assert result['defaultRunSetting'] == sample_get_batch_response['defaultRunSetting']
        assert result['submissionSummary'] == sample_get_batch_response['submissionSummary']
        assert result['runSummary'] == sample_get_batch_response['runSummary']
        assert result['tags'] == {'env': 'test'}

        # Verify datetime conversion
        assert result['creationTime'] == '2024-01-15T10:30:00+00:00'
        assert result['startTime'] == '2024-01-15T10:31:00+00:00'
        assert result['stopTime'] is None

    @pytest.mark.asyncio
    async def test_failure_reason_included_for_failed_batch(
        self, sample_get_batch_failed_response
    ):
        """Test failureReason is included when batch status is FAILED."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_batch.return_value = sample_get_batch_failed_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await get_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-failed-123',
            )

        assert result['status'] == 'FAILED'
        assert result['failureReason'] == 'Invalid workflow configuration'

    @pytest.mark.asyncio
    async def test_datetime_conversion_to_iso(self):
        """Test datetime fields are converted to ISO format strings."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        creation_time = datetime(2024, 3, 20, 15, 45, 30, tzinfo=timezone.utc)
        start_time = datetime(2024, 3, 20, 15, 46, 0, tzinfo=timezone.utc)
        stop_time = datetime(2024, 3, 20, 18, 30, 0, tzinfo=timezone.utc)

        mock_client.get_batch.return_value = {
            'id': 'batch-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:batch/batch-123',
            'uuid': 'uuid-123',
            'name': 'test',
            'status': 'PROCESSED',
            'totalRuns': 5,
            'defaultRunSetting': {},
            'submissionSummary': {},
            'runSummary': {},
            'creationTime': creation_time,
            'startTime': start_time,
            'stopTime': stop_time,
            'tags': None,
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await get_batch_wrapper.call(ctx=mock_ctx, batch_id='batch-123')

        assert isinstance(result['creationTime'], str)
        assert isinstance(result['startTime'], str)
        assert isinstance(result['stopTime'], str)
        assert result['creationTime'] == creation_time.isoformat()
        assert result['startTime'] == start_time.isoformat()
        assert result['stopTime'] == stop_time.isoformat()

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_batch.side_effect = Exception('Batch not found')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error getting batch: Batch not found'},
            ) as mock_handle_error,
        ):
            result = await get_batch_wrapper.call(ctx=mock_ctx, batch_id='batch-invalid')

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(self, sample_get_batch_response):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_batch.return_value = sample_get_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await get_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                aws_profile='prod-profile',
                aws_region='us-west-2',
            )

        mock_get_client.assert_called_once_with(
            region_name='us-west-2', profile_name='prod-profile'
        )


# --- list_batches Tests ---


class TestListBatches:
    """Tests for list_batches tool."""

    @pytest.mark.asyncio
    async def test_success_with_filters(self, sample_list_batches_response):
        """Test successful listing with filters."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = sample_list_batches_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_batches_wrapper.call(
                ctx=mock_ctx,
                status='INPROGRESS',
                name='batch',
                run_group_id='rg-123',
                max_results=50,
            )

        call_kwargs = mock_client.list_batch.call_args[1]
        assert call_kwargs['status'] == 'INPROGRESS'
        assert call_kwargs['name'] == 'batch'
        assert call_kwargs['runGroupId'] == 'rg-123'
        assert call_kwargs['maxResults'] == 50

        assert len(result['batches']) == 2
        assert result['nextToken'] == 'token-abc123'

    @pytest.mark.asyncio
    async def test_pagination_with_next_token(self, sample_list_batches_response):
        """Test pagination with nextToken."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = sample_list_batches_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_batches_wrapper.call(
                ctx=mock_ctx,
                next_token='previous-token',
            )

        call_kwargs = mock_client.list_batch.call_args[1]
        assert call_kwargs['startingToken'] == 'previous-token'
        assert 'nextToken' in result

    @pytest.mark.asyncio
    async def test_no_next_token_when_absent(self):
        """Test nextToken is not included when absent from API response."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = {'items': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_batches_wrapper.call(ctx=mock_ctx)

        assert 'nextToken' not in result
        assert result['batches'] == []

    @pytest.mark.asyncio
    async def test_invalid_status_filter(self):
        """Test validation error for invalid status filter."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Invalid parameters'},
            ) as mock_handle_error,
        ):
            result = await list_batches_wrapper.call(
                ctx=mock_ctx,
                status='INVALID_STATUS',
            )

        mock_handle_error.assert_called_once()
        mock_client.list_batch.assert_not_called()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_datetime_conversion_in_list(self, sample_list_batches_response):
        """Test datetime fields are converted to ISO format in list results."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = sample_list_batches_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_batches_wrapper.call(ctx=mock_ctx)

        # Check first batch datetime conversion
        batch_one = result['batches'][0]
        assert isinstance(batch_one['creationTime'], str)
        assert batch_one['creationTime'] == '2024-01-10T08:00:00+00:00'

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.side_effect = Exception('Access denied')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error listing batches: Access denied'},
            ) as mock_handle_error,
        ):
            result = await list_batches_wrapper.call(ctx=mock_ctx)

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(self, sample_list_batches_response):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = sample_list_batches_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await list_batches_wrapper.call(
                ctx=mock_ctx,
                aws_profile='test-profile',
                aws_region='ap-southeast-1',
            )

        mock_get_client.assert_called_once_with(
            region_name='ap-southeast-1', profile_name='test-profile'
        )

    @pytest.mark.asyncio
    async def test_all_valid_status_filters(self):
        """Test all valid batch status values are accepted."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_batch.return_value = {'items': []}

        for status in BATCH_STATUSES:
            with patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ):
                result = await list_batches_wrapper.call(ctx=mock_ctx, status=status)

            assert 'error' not in result
            assert 'batches' in result


# --- list_runs_in_batch Tests ---


class TestListRunsInBatch:
    """Tests for list_runs_in_batch tool."""

    @pytest.mark.asyncio
    async def test_success_with_filters(self, sample_list_runs_in_batch_response):
        """Test successful listing with filters."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.return_value = sample_list_runs_in_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                submission_status='SUCCESS',
                run_setting_id='sample-001',
                run_id='run-001',
                max_results=25,
            )

        call_kwargs = mock_client.list_runs_in_batch.call_args[1]
        assert call_kwargs['id'] == 'batch-123'
        assert call_kwargs['submissionStatus'] == 'SUCCESS'
        assert call_kwargs['runSettingId'] == 'sample-001'
        assert call_kwargs['runId'] == 'run-001'
        assert call_kwargs['maxResults'] == 25

        assert len(result['runs']) == 3
        assert result['nextToken'] == 'runs-token-xyz'

    @pytest.mark.asyncio
    async def test_pagination_with_next_token(self, sample_list_runs_in_batch_response):
        """Test pagination with nextToken."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.return_value = sample_list_runs_in_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                next_token='prev-token',
            )

        call_kwargs = mock_client.list_runs_in_batch.call_args[1]
        assert call_kwargs['startingToken'] == 'prev-token'
        assert 'nextToken' in result

    @pytest.mark.asyncio
    async def test_invalid_submission_status_filter(self):
        """Test validation error for invalid submission status filter."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Invalid parameters'},
            ) as mock_handle_error,
        ):
            result = await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                submission_status='INVALID_STATUS',
            )

        mock_handle_error.assert_called_once()
        mock_client.list_runs_in_batch.assert_not_called()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_optional_fields_included_when_present(self, sample_list_runs_in_batch_response):
        """Test optional fields are included when present in API response."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.return_value = sample_list_runs_in_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
            )

        # First run has runId and runArn
        run_one = result['runs'][0]
        assert run_one['runSettingId'] == 'sample-001'
        assert run_one['runId'] == 'run-001'
        assert run_one['runArn'] == 'arn:aws:omics:us-east-1:123456789012:run/run-001'
        assert run_one['submissionStatus'] == 'SUCCESS'

        # Third run has failure info
        run_three = result['runs'][2]
        assert run_three['runSettingId'] == 'sample-003'
        assert run_three['submissionStatus'] == 'FAILED'
        assert run_three['submissionFailureReason'] == 'VALIDATION_ERROR'
        assert run_three['submissionFailureMessage'] == 'Invalid input parameters'
        assert 'runId' not in run_three
        assert 'runArn' not in run_three

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.side_effect = Exception('Batch not found')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error listing runs in batch batch-123: Batch not found'},
            ) as mock_handle_error,
        ):
            result = await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_all_valid_submission_status_filters(self):
        """Test all valid submission status values are accepted."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.return_value = {'items': []}

        for status in SUBMISSION_STATUSES:
            with patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ):
                result = await list_runs_in_batch_wrapper.call(
                    ctx=mock_ctx,
                    batch_id='batch-123',
                    submission_status=status,
                )

            assert 'error' not in result
            assert 'runs' in result

    @pytest.mark.asyncio
    async def test_credential_override(self, sample_list_runs_in_batch_response):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs_in_batch.return_value = sample_list_runs_in_batch_response

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await list_runs_in_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                aws_profile='dev-profile',
                aws_region='eu-central-1',
            )

        mock_get_client.assert_called_once_with(
            region_name='eu-central-1', profile_name='dev-profile'
        )


# --- cancel_run_batch Tests ---


class TestCancelRunBatch:
    """Tests for cancel_run_batch tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful batch cancellation."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_run_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await cancel_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
            )

        mock_client.cancel_run_batch.assert_called_once_with(id='batch-123')
        assert result['batchId'] == 'batch-123'
        assert result['status'] == 'cancelling'

    @pytest.mark.asyncio
    async def test_state_error_handling(self):
        """Test error handling for state-related errors."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_run_batch.side_effect = Exception(
            'Batch cannot be cancelled in PROCESSED state'
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={
                    'error': 'Error cancelling run batch batch-123: Batch cannot be cancelled in PROCESSED state'
                },
            ) as mock_handle_error,
        ):
            result = await cancel_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_run_batch.side_effect = Exception('Access denied')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error cancelling run batch batch-123: Access denied'},
            ) as mock_handle_error,
        ):
            result = await cancel_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(self):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_run_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await cancel_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-123',
                aws_profile='ops-profile',
                aws_region='us-east-2',
            )

        mock_get_client.assert_called_once_with(
            region_name='us-east-2', profile_name='ops-profile'
        )


# --- delete_run_batch Tests ---


class TestDeleteRunBatch:
    """Tests for delete_run_batch tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful batch runs deletion."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_run_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await delete_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-456',
            )

        mock_client.delete_run_batch.assert_called_once_with(id='batch-456')
        assert result['batchId'] == 'batch-456'
        assert result['status'] == 'deleting'

    @pytest.mark.asyncio
    async def test_state_error_handling(self):
        """Test error handling for state-related errors."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_run_batch.side_effect = Exception(
            'Batch runs cannot be deleted in INPROGRESS state'
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={
                    'error': 'Error deleting runs in batch batch-456: Batch runs cannot be deleted in INPROGRESS state'
                },
            ) as mock_handle_error,
        ):
            result = await delete_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-456',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_run_batch.side_effect = Exception('Batch not found')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error deleting runs in batch batch-456: Batch not found'},
            ) as mock_handle_error,
        ):
            result = await delete_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-456',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(self):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_run_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await delete_run_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-456',
                aws_profile='cleanup-profile',
                aws_region='ap-northeast-1',
            )

        mock_get_client.assert_called_once_with(
            region_name='ap-northeast-1', profile_name='cleanup-profile'
        )


# --- delete_batch Tests ---


class TestDeleteBatch:
    """Tests for delete_batch tool."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful batch metadata deletion."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ):
            result = await delete_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-789',
            )

        mock_client.delete_batch.assert_called_once_with(id='batch-789')
        assert result['batchId'] == 'batch-789'
        assert result['status'] == 'deleted'

    @pytest.mark.asyncio
    async def test_state_error_handling(self):
        """Test error handling for state-related errors."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_batch.side_effect = Exception(
            'Batch cannot be deleted in INPROGRESS state'
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={
                    'error': 'Error deleting batch batch-789: Batch cannot be deleted in INPROGRESS state'
                },
            ) as mock_handle_error,
        ):
            result = await delete_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-789',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test error handling for API failures."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_batch.side_effect = Exception('Access denied')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_batch.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error deleting batch batch-789: Access denied'},
            ) as mock_handle_error,
        ):
            result = await delete_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-789',
            )

        mock_handle_error.assert_called_once()
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_credential_override(self):
        """Test aws_profile and aws_region are passed to get_omics_client."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_batch.return_value = {}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_batch.get_omics_client',
            return_value=mock_client,
        ) as mock_get_client:
            await delete_batch_wrapper.call(
                ctx=mock_ctx,
                batch_id='batch-789',
                aws_profile='admin-profile',
                aws_region='sa-east-1',
            )

        mock_get_client.assert_called_once_with(
            region_name='sa-east-1', profile_name='admin-profile'
        )
