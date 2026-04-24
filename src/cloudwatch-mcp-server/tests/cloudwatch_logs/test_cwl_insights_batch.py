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

"""Tests for the multi-region Logs Insights query tool."""

import asyncio
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch import (
    _CONCURRENCY_PER_REGION,
    MAX_RECHUNK_DEPTH,
    MultiRegionQueryResult,
    _annotate_rows,
    _chunk_list,
    _convert_time,
    _hit_output_limit,
    _is_splittable_failure,
    _RegionContext,
    execute_cwl_insights_batch,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def ctx():
    """Mock MCP context."""
    mock = AsyncMock()
    mock.info = AsyncMock()
    mock.warning = AsyncMock()
    mock.error = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def _fast_timers():
    """Zero out poll/start intervals so tests don't sleep."""
    with (
        patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch._POLL_INTERVAL',
            0,
        ),
        patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch._START_QUERY_INTERVAL',
            0,
        ),
    ):
        yield


def _make_logs_client(results=None, status='Complete'):
    """Build a mock logs client that returns *results* on get_query_results."""
    client = MagicMock()
    client.start_query.return_value = {'queryId': 'qid-1'}
    client.get_query_results.return_value = {
        'status': status,
        'results': [
            [
                {'field': '@timestamp', 'value': '2025-01-01T00:00:00Z'},
                {'field': '@message', 'value': msg},
            ]
            for msg in (results or ['hello'])
        ],
        'statistics': {'recordsMatched': 1.0, 'recordsScanned': 100.0},
    }
    client.stop_query.return_value = {}
    return client


class TestChunkList:
    """Tests for _chunk_list helper."""

    def test_exact_split(self):
        """Even split produces equal-sized chunks."""
        assert _chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_remainder(self):
        """Uneven split produces a smaller trailing chunk."""
        assert _chunk_list([1, 2, 3], 2) == [[1, 2], [3]]

    def test_single_chunk(self):
        """List smaller than chunk size stays in one chunk."""
        assert _chunk_list([1], 50) == [[1]]

    def test_empty(self):
        """Empty list produces no chunks."""
        assert _chunk_list([], 50) == []


@pytest.mark.asyncio
class TestRegionContext:
    """Tests for _RegionContext rate-limiting."""

    async def test_semaphore_limits_concurrency(self):
        """Semaphore should limit concurrent access."""
        rc = _RegionContext()
        assert rc.semaphore._value == _CONCURRENCY_PER_REGION

    async def test_pace_start_query_enforces_interval(self):
        """Successive pace_start_query calls should be spaced apart."""
        # Use a real (short) interval to verify pacing works.
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch._START_QUERY_INTERVAL',
            0.2,
        ):
            rc = _RegionContext()
            await rc.pace_start_query()
            t0 = asyncio.get_event_loop().time()
            await rc.pace_start_query()
            t1 = asyncio.get_event_loop().time()
            assert t1 - t0 >= 0.1


@pytest.mark.asyncio
class TestMultiRegionQuery:
    """Tests for execute_cwl_insights_batch."""

    async def test_single_region_single_chunk(self, ctx):
        """Basic happy path: 1 region, <50 log groups."""
        client = _make_logs_client(['msg1', 'msg2'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @timestamp, @message | limit 10',
            )

        assert isinstance(result, MultiRegionQueryResult)
        assert result.summary.total_regions == 1
        assert result.summary.total_chunks == 1
        assert result.summary.successful_chunks == 1
        assert result.summary.failed_chunks == 0
        assert len(result.results) == 2
        assert all(r['_region'] == 'us-east-1' for r in result.results)

    async def test_multi_region(self, ctx):
        """Query dispatched to two regions."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1', 'eu-west-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @timestamp, @message | limit 10',
            )

        assert result.summary.total_regions == 2
        assert result.summary.total_chunks == 2
        assert result.summary.successful_chunks == 2
        regions_in_results = {r['_region'] for r in result.results}
        assert regions_in_results == {'us-east-1', 'eu-west-1'}

    async def test_chunking_over_50_log_groups(self, ctx):
        """More than 50 log groups should produce multiple chunks."""
        groups = [f'/aws/test/g{i}' for i in range(75)]
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=groups,
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @timestamp, @message | limit 10',
            )

        assert result.summary.total_log_groups == 75
        assert result.summary.total_chunks == 2
        assert result.summary.successful_chunks == 2

    async def test_account_label_annotation(self, ctx):
        """account_label should appear in _account field."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @timestamp, @message',
                account_label='prod-123456789012',
            )

        assert all(r['_account'] == 'prod-123456789012' for r in result.results)

    async def test_no_account_label_omits_field(self, ctx):
        """When account_label is None, _account should not appear in results."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
            )

        assert all('_account' not in r for r in result.results)

    async def test_retry_on_transient_failure(self, ctx):
        """First call raises, second succeeds → retried_chunks incremented."""
        client = MagicMock()
        call_count = 0

        def start_query_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception('Throttling')
            return {'queryId': 'qid-retry'}

        client.start_query.side_effect = start_query_side_effect
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': '@message', 'value': 'ok'}]],
            'statistics': {},
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert result.summary.retried_chunks == 1
        assert result.summary.successful_chunks == 1
        assert len(result.results) == 1

    async def test_failure_after_retries(self, ctx):
        """All attempts fail → failed_chunks incremented, warning added."""
        client = MagicMock()
        client.start_query.side_effect = Exception('Permanent failure')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert result.summary.failed_chunks == 1
        assert result.summary.successful_chunks == 0
        assert len(result.summary.warnings) > 0
        assert result.results == []

    async def test_rechunk_on_output_limit(self, ctx):
        """When results hit 10k records, the chunk should split the time range."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-big'}
        client.stop_query.return_value = {}

        call_count = 0

        def get_results_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    'status': 'Complete',
                    'results': [
                        [{'field': '@message', 'value': f'row{i}'}] for i in range(10_000)
                    ],
                    'statistics': {},
                }
            return {
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'sub-row'}]],
                'statistics': {},
            }

        client.get_query_results.side_effect = get_results_side_effect

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=10,
            )

        assert result.summary.re_chunked >= 1
        assert len(result.summary.warnings) > 0

    async def test_rechunk_on_timeout(self, ctx):
        """When a chunk times out, it should split the time range."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-timeout'}
        client.stop_query.return_value = {}

        call_count = 0

        def get_results_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'status': 'Timeout', 'results': [], 'statistics': {}}
            return {
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'ok'}]],
                'statistics': {},
            }

        client.get_query_results.side_effect = get_results_side_effect

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=10,
            )

        assert result.summary.re_chunked >= 1

    async def test_failed_status_does_not_rechunk(self, ctx):
        """A 'Failed' query (e.g. bad syntax) should NOT trigger re-chunking."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-fail'}
        client.stop_query.return_value = {}
        client.get_query_results.return_value = {
            'status': 'Failed',
            'results': [],
            'statistics': {},
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await asyncio.wait_for(
                execute_cwl_insights_batch(
                    ctx,
                    log_group_names=['/aws/test/g1'],
                    regions=['us-east-1'],
                    start_time='2025-01-01T00:00:00+00:00',
                    end_time='2025-01-01T01:00:00+00:00',
                    query_string='BAD QUERY SYNTAX',
                    max_timeout=5,
                ),
                timeout=10,
            )

        assert result.summary.re_chunked == 0
        assert result.summary.failed_chunks == 1
        assert any('query error' in w for w in result.summary.warnings)

    async def test_rechunk_depth_cap(self, ctx):
        """Re-chunking should stop at MAX_RECHUNK_DEPTH even if limits keep being hit."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-deep'}
        client.stop_query.return_value = {}
        client.get_query_results.return_value = {
            'status': 'Timeout',
            'results': [],
            'statistics': {},
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await asyncio.wait_for(
                execute_cwl_insights_batch(
                    ctx,
                    log_group_names=['/aws/test/g1'],
                    regions=['us-east-1'],
                    start_time='2025-01-01T00:00:00+00:00',
                    end_time='2025-01-01T01:00:00+00:00',
                    query_string='fields @message',
                    max_timeout=5,
                ),
                timeout=60,
            )

        assert result.summary.re_chunked <= 2**MAX_RECHUNK_DEPTH
        assert any(
            'max re-chunk depth' in w or 'cannot be split' in w.lower()
            for w in result.summary.warnings
        )

    async def test_summary_warnings_on_failure(self, ctx):
        """ctx.warning should be called when there are failed chunks."""
        client = MagicMock()
        client.start_query.side_effect = Exception('boom')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        ctx.warning.assert_called()

    async def test_multiple_log_groups_annotation(self, ctx):
        """When chunk has >1 log group, _logGroups should show count."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=[f'/aws/test/g{i}' for i in range(5)],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
            )

        assert all(r['_logGroups'] == '5 log groups' for r in result.results)

    async def test_empty_log_groups(self, ctx):
        """Empty log_group_names should raise ValueError."""
        with pytest.raises(ValueError, match='log_group_names cannot be empty'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=[],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
            )

    async def test_empty_regions(self, ctx):
        """Empty regions list should raise ValueError."""
        with pytest.raises(ValueError, match='regions cannot be empty'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/aws/test/g1'],
                regions=[],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
            )

    async def test_concurrency_bounded_per_region(self, ctx):
        """Verify that at most _CONCURRENCY_PER_REGION queries run concurrently per region."""
        max_concurrent = 0
        current_concurrent = 0

        original_start_query = MagicMock()
        original_start_query.return_value = {'queryId': 'q1'}

        client = MagicMock()
        client.stop_query.return_value = {}

        call_idx = 0

        def mock_start(**kwargs):
            nonlocal current_concurrent, max_concurrent, call_idx
            call_idx += 1
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            return {'queryId': f'q-{call_idx}'}

        def mock_get_results(**kwargs):
            nonlocal current_concurrent
            current_concurrent -= 1
            return {
                'status': 'Complete',
                'results': [[{'field': '@m', 'value': 'ok'}]],
                'statistics': {},
            }

        client.start_query.side_effect = mock_start
        client.get_query_results.side_effect = mock_get_results

        # 15 log groups = 15 chunks of 1 (we set chunk size to 1 via patching MAX)
        groups = [f'/g{i}' for i in range(15)]

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.MAX_LOG_GROUPS_PER_QUERY',
                1,
            ),
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=groups,
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @m',
                max_timeout=10,
            )

        assert max_concurrent <= _CONCURRENCY_PER_REGION
        assert result.summary.successful_chunks == 15


class TestConvertTime:
    """Tests for _convert_time helper."""

    def test_valid_iso(self):
        """Valid ISO 8601 string converts correctly."""
        assert _convert_time('2025-01-01T00:00:00+00:00') == 1735689600

    def test_invalid_string(self):
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError, match='Invalid ISO 8601'):
            _convert_time('not-a-date')

    def test_none_input(self):
        """None input raises ValueError."""
        with pytest.raises(ValueError):
            _convert_time(None)  # type: ignore[arg-type]


class TestHitOutputLimit:
    """Tests for _hit_output_limit helper."""

    def test_below_limit(self):
        """Below limit returns False."""
        assert _hit_output_limit({'statistics': {'recordsMatched': 100}, 'results': []}) is False

    def test_at_limit_via_stats(self):
        """At limit via stats returns True."""
        assert _hit_output_limit({'statistics': {'recordsMatched': 10_000}, 'results': []}) is True

    def test_at_limit_via_results_fallback(self):
        """At limit via results fallback returns True."""
        rows = [{'m': 'x'}] * 10_000
        assert _hit_output_limit({'statistics': {}, 'results': rows}) is True

    def test_empty(self):
        """Empty results returns False."""
        assert _hit_output_limit({'results': []}) is False


class TestIsSplittableFailure:
    """Tests for _is_splittable_failure helper."""

    def test_timeout(self):
        """Timeout status is splittable."""
        assert _is_splittable_failure({'status': 'Timeout'}) is True

    def test_polling_timeout(self):
        """PollingTimeout status is splittable."""
        assert _is_splittable_failure({'status': 'PollingTimeout'}) is True

    def test_failed_not_splittable(self):
        """Failed status is not splittable."""
        assert _is_splittable_failure({'status': 'Failed'}) is False

    def test_complete_not_splittable(self):
        """Complete status is not splittable."""
        assert _is_splittable_failure({'status': 'Complete'}) is False


class TestAnnotateRows:
    """Tests for _annotate_rows helper."""

    def test_single_log_group(self):
        """Single log group uses name directly."""
        rows = [{'@message': 'hi'}]
        _annotate_rows(rows, 'us-east-1', 'acct-1', ['/aws/lg1'])
        assert rows[0]['_region'] == 'us-east-1'
        assert rows[0]['_account'] == 'acct-1'
        assert rows[0]['_logGroups'] == '/aws/lg1'

    def test_multiple_log_groups(self):
        """Multiple log groups shows count."""
        rows = [{'@message': 'hi'}]
        _annotate_rows(rows, 'eu-west-1', None, ['/lg1', '/lg2', '/lg3'])
        assert rows[0]['_logGroups'] == '3 log groups'
        assert '_account' not in rows[0]


@pytest.mark.asyncio
class TestValidation:
    """Tests for input validation in execute_cwl_insights_batch."""

    async def test_invalid_start_time(self, ctx):
        """Invalid start_time raises ValueError."""
        with pytest.raises(ValueError, match='Invalid time parameter'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='bad',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
            )

    async def test_start_after_end(self, ctx):
        """start_time after end_time raises ValueError."""
        with pytest.raises(ValueError, match='start_time must be before end_time'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-02T00:00:00+00:00',
                end_time='2025-01-01T00:00:00+00:00',
                query_string='fields @message',
            )

    async def test_negative_max_timeout(self, ctx):
        """Negative max_timeout raises ValueError."""
        with pytest.raises(ValueError, match='max_timeout must be positive'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=-1,
            )

    async def test_negative_limit(self, ctx):
        """Negative limit raises ValueError."""
        with pytest.raises(ValueError, match='limit must be positive'):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                limit=-5,
            )

    async def test_non_retryable_client_error(self, ctx):
        """AccessDeniedException should fail fast without retry."""
        client = MagicMock()
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}}
        client.start_query.side_effect = ClientError(error_response, 'StartQuery')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert result.summary.failed_chunks == 1
        assert result.summary.retried_chunks == 0
        assert any('AccessDeniedException' in w for w in result.summary.warnings)
        assert any('not retryable' in w.lower() for w in result.summary.warnings)

    async def test_profile_name_passed(self, ctx):
        """profile_name should be forwarded to get_aws_client."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ) as mock_get:
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                profile_name='my-profile',
            )

        mock_get.assert_called_with('logs', 'us-east-1', 'my-profile')

    async def test_retryable_client_error_exhausted(self, ctx):
        """Retryable ClientError that exhausts all retries."""
        client = MagicMock()
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'slow down'}}
        client.start_query.side_effect = ClientError(error_response, 'StartQuery')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert result.summary.failed_chunks == 1
        assert result.summary.retried_chunks == 1
        assert any('retries' in w for w in result.summary.warnings)

    async def test_polling_timeout_triggers_rechunk(self, ctx):
        """PollingTimeout from _start_and_poll should trigger time-range split."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-pt'}
        client.stop_query.return_value = {}

        call_count = 0

        def get_results(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return {'status': 'Running', 'results': [], 'statistics': {}}
            return {
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'ok'}]],
                'statistics': {},
            }

        client.get_query_results.side_effect = get_results

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch._POLL_INTERVAL',
                0,
            ),
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=1,
            )

        assert result.summary.total_chunks == 1

    async def test_cancelled_status_retries(self, ctx):
        """Cancelled query status should be retried."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-cancel'}
        client.stop_query.return_value = {}

        call_count = 0

        def get_results(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'status': 'Cancelled', 'results': [], 'statistics': {}}
            return {
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'ok'}]],
                'statistics': {},
            }

        client.get_query_results.side_effect = get_results

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert result.summary.retried_chunks >= 1
        assert result.summary.successful_chunks == 1

    async def test_large_result_warning(self, ctx):
        """Results exceeding LARGE_RESULT_WARNING_THRESHOLD should trigger warning."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-big'}
        client.stop_query.return_value = {}
        client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'field': '@message', 'value': f'row{i}'}] for i in range(500)],
            'statistics': {'recordsMatched': 500.0},
        }

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.LARGE_RESULT_WARNING_THRESHOLD',
                100,
            ),
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert any('Large result set' in w for w in result.summary.warnings)

    async def test_limit_param_forwarded(self, ctx):
        """Limit parameter should be passed to start_query."""
        client = _make_logs_client(['msg'])
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            await execute_cwl_insights_batch(
                ctx,
                log_group_names=['/g1'],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                limit=50,
                max_timeout=5,
            )

        call_kwargs = client.start_query.call_args
        assert call_kwargs is not None
        # limit should appear in the kwargs
        assert 50 in (call_kwargs.kwargs.get('limit'), call_kwargs[1].get('limit', None)) or any(
            v == 50 for v in (call_kwargs.kwargs.values() if call_kwargs.kwargs else [])
        )

    async def test_rechunk_with_partial_results(self, ctx):
        """Rechunk at max depth with partial results should count as successful."""
        client = MagicMock()
        client.start_query.return_value = {'queryId': 'qid-partial'}
        client.stop_query.return_value = {}
        client.get_query_results.return_value = {
            'status': 'Timeout',
            'results': [[{'field': '@message', 'value': 'partial'}]],
            'statistics': {},
        }

        with (
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.MAX_RECHUNK_DEPTH',
                0,
            ),
        ):
            result = await asyncio.wait_for(
                execute_cwl_insights_batch(
                    ctx,
                    log_group_names=['/g1'],
                    regions=['us-east-1'],
                    start_time='2025-01-01T00:00:00+00:00',
                    end_time='2025-01-01T01:00:00+00:00',
                    query_string='fields @message',
                    max_timeout=5,
                ),
                timeout=10,
            )

        assert result.summary.successful_chunks == 1
        assert len(result.results) == 1

    async def test_log_group_preview_truncation(self, ctx):
        """Warning messages should truncate log group lists > 3."""
        client = MagicMock()
        client.start_query.side_effect = Exception('boom')

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.cwl_insights_batch.get_aws_client',
            return_value=client,
        ):
            result = await execute_cwl_insights_batch(
                ctx,
                log_group_names=[f'/g{i}' for i in range(5)],
                regions=['us-east-1'],
                start_time='2025-01-01T00:00:00+00:00',
                end_time='2025-01-01T01:00:00+00:00',
                query_string='fields @message',
                max_timeout=5,
            )

        assert any('...' in w for w in result.summary.warnings)
