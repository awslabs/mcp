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

"""Multi-region, multi-log-group CloudWatch Logs Insights query tool."""

import asyncio
import datetime
from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client
from awslabs.cloudwatch_mcp_server.common import remove_null_values
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field
from timeit import default_timer as timer
from typing import Annotated, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants – CloudWatch Logs Insights service limits
# ---------------------------------------------------------------------------
MAX_LOG_GROUPS_PER_QUERY = 50
MAX_OUTPUT_RECORDS = 10_000
MAX_RETRIES = 2
MAX_RECHUNK_DEPTH = 4  # cap recursive time-range splits
RETRY_BACKOFF_BASE = 2  # exponential backoff: 2s, 4s for attempts 1, 2
LARGE_RESULT_WARNING_THRESHOLD = 100_000  # warn when result set exceeds this

# ---------------------------------------------------------------------------
# Throttle defaults – consume ≤ 25 % of the account/region hard limits so
# the customer's other workloads are not starved.
#
# Account/region hard limits (most regions):
#   - 30 concurrent Insights queries
#   - 6 TPS for StartQuery
#   - 6 TPS for GetQueryResults
#
# 25 % targets:
#   concurrent queries : 30 × 0.25 = 7.5  → 7
#   StartQuery TPS     :  6 × 0.25 = 1.5  → pace ≥ 0.67 s  (we use 0.7 s → 1.4/s)
#   GetQueryResults TPS:  6 × 0.25 = 1.5  → 7 queries / 5 s poll = 1.4/s
# ---------------------------------------------------------------------------
_CONCURRENCY_PER_REGION = 7
_POLL_INTERVAL = 5  # seconds between GetQueryResults calls per query
_START_QUERY_INTERVAL = 0.7  # seconds between StartQuery calls per region


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------
class MultiRegionQuerySummary(BaseModel):
    """Summary of actions taken during a multi-region Logs Insights query."""

    total_log_groups: int = Field(..., description='Total log groups requested')
    total_regions: int = Field(..., description='Total regions queried')
    total_chunks: int = Field(..., description='Total query chunks dispatched')
    successful_chunks: int = Field(default=0, description='Chunks that completed successfully')
    retried_chunks: int = Field(default=0, description='Chunks that required retry')
    re_chunked: int = Field(default=0, description='Chunks that were split further due to limits')
    failed_chunks: int = Field(default=0, description='Chunks that failed after retries')
    total_records_returned: int = Field(default=0, description='Total merged result records')
    warnings: List[str] = Field(default_factory=list, description='Warnings encountered')


class MultiRegionQueryResult(BaseModel):
    """Result of a multi-region Logs Insights query."""

    summary: MultiRegionQuerySummary = Field(..., description='Execution summary')
    results: List[Dict] = Field(default_factory=list, description='Merged result records')


# ---------------------------------------------------------------------------
# Per-region rate-limiting context
# ---------------------------------------------------------------------------
class _RegionContext:
    """Holds the semaphore and rate-limit state for one region."""

    def __init__(self):
        self.semaphore = asyncio.Semaphore(_CONCURRENCY_PER_REGION)
        self._last_start = 0.0
        self._lock = asyncio.Lock()

    async def pace_start_query(self) -> None:
        """Ensure at least _START_QUERY_INTERVAL between StartQuery calls."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self._last_start + _START_QUERY_INTERVAL - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_start = asyncio.get_event_loop().time()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _chunk_list(lst: List, size: int) -> List[List]:
    """Split *lst* into sub-lists of at most *size* elements."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def _convert_time(time_str: str) -> int:
    """ISO 8601 string → Unix epoch seconds.
    
    Note: This is a standalone function separate from CloudWatchLogsTools._convert_time_to_timestamp
    because it includes enhanced error handling with actionable error messages for the batch tool.

    Raises:
        ValueError: If time_str is not a valid ISO 8601 timestamp.
    """
    try:
        return int(datetime.datetime.fromisoformat(time_str).timestamp())
    except (ValueError, AttributeError, TypeError) as e:
        raise ValueError(
            f"Invalid ISO 8601 timestamp '{time_str}'. "
            f"Expected format: '2025-04-19T20:00:00+00:00'. Error: {e}"
        ) from e


async def _start_and_poll(
    region_ctx: _RegionContext,
    logs_client,
    log_groups: List[str],
    start_ts: int,
    end_ts: int,
    query_string: str,
    limit: Optional[int],
    max_timeout: int,
) -> Dict:
    """Start a single Insights query and poll until terminal state.

    Acquires the region semaphore for the full lifetime of the query
    (start → poll → complete) so that at most _CONCURRENCY_PER_REGION
    queries are in-flight per region at any time.  This keeps both
    concurrent-query count and GetQueryResults TPS within limits.

    Returns a dict with keys: status, results, statistics, query_id.
    """
    async with region_ctx.semaphore:
        await region_ctx.pace_start_query()

        kwargs = remove_null_values(
            {
                'logGroupNames': log_groups,
                'startTime': start_ts,
                'endTime': end_ts,
                'queryString': query_string,
                'limit': limit,
            }
        )
        resp = logs_client.start_query(**kwargs)
        query_id = resp['queryId']
        logger.debug(f'Started query {query_id} for {len(log_groups)} log groups')

        poll_start = timer()
        while timer() - poll_start < max_timeout:
            await asyncio.sleep(_POLL_INTERVAL)
            resp = logs_client.get_query_results(queryId=query_id)
            status = resp['status']
            if status in ('Complete', 'Failed', 'Cancelled', 'Timeout'):
                return {
                    'query_id': query_id,
                    'status': status,
                    'results': [
                        {f['field']: f['value'] for f in row} for row in resp.get('results', [])
                    ],
                    'statistics': resp.get('statistics', {}),
                }

        # Polling timed out on our side – cancel to avoid cost
        try:
            logs_client.stop_query(queryId=query_id)
        except Exception as e:
            logger.warning(f"Failed to stop query {query_id} after polling timeout: {e}")
        return {
            'query_id': query_id,
            'status': 'PollingTimeout',
            'results': [],
            'statistics': {},
        }


def _hit_output_limit(result: Dict) -> bool:
    """Return True if the query likely hit the 10 000-record output cap.
    
    Uses recordsMatched from statistics when available, falls back to result count.
    """
    stats = result.get('statistics', {})
    records_matched = stats.get('recordsMatched', 0)
    
    # If statistics available, use recordsMatched
    if records_matched > 0:
        return records_matched >= MAX_OUTPUT_RECORDS
    
    # Fallback to result count
    return len(result.get('results', [])) >= MAX_OUTPUT_RECORDS


def _is_splittable_failure(result: Dict) -> bool:
    """Return True if the failure is likely due to time/volume and splitting may help.

    Only Timeout and PollingTimeout are candidates for time-range splitting.
    A generic 'Failed' status usually indicates a query-syntax or permissions error
    that would just fail again in both halves, so we do NOT split on it.
    """
    return result.get('status') in ('Timeout', 'PollingTimeout')


def _annotate_rows(
    rows: List[Dict], region: str, account: Optional[str], log_groups: List[str]
) -> None:
    """Add _region, _account, _logGroups metadata to each row in-place."""
    log_group_label = log_groups[0] if len(log_groups) == 1 else f'{len(log_groups)} log groups'
    for row in rows:
        row['_region'] = region
        if account:
            row['_account'] = account
        row['_logGroups'] = log_group_label


# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------
async def _run_chunk(
    region_ctx: _RegionContext,
    logs_client,
    log_groups: List[str],
    start_ts: int,
    end_ts: int,
    query_string: str,
    limit: Optional[int],
    max_timeout: int,
    summary: MultiRegionQuerySummary,
    region: str,
    account: Optional[str],
    rechunk_depth: int = 0,
) -> List[Dict]:
    """Execute one chunk with retry and adaptive re-chunking.

    Returns annotated result rows.
    """
    result: Dict = {'status': 'NotStarted', 'results': []}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await _start_and_poll(
                region_ctx,
                logs_client,
                log_groups,
                start_ts,
                end_ts,
                query_string,
                limit,
                max_timeout,
            )
        except ClientError as exc:
            error_code = exc.response.get('Error', {}).get('Code', 'Unknown')
            # Non-retryable errors: fail fast without retry
            if error_code in ('AccessDeniedException', 'InvalidParameterException', 'ResourceNotFoundException'):
                logger.exception(f'Non-retryable error in {region}: {error_code}')
                summary.failed_chunks += 1
                log_group_preview = log_groups[:3] + (['...'] if len(log_groups) > 3 else [])
                time_range = f"{datetime.datetime.fromtimestamp(start_ts).isoformat()} to {datetime.datetime.fromtimestamp(end_ts).isoformat()}"
                summary.warnings.append(
                    f'Query failed in {region} with {error_code}. '
                    f'Log groups: {log_group_preview}. Time range: {time_range}. '
                    f'Error: {exc}. This error is not retryable.'
                )
                return []
            # Retryable errors: continue with retry logic
            logger.exception(f'Chunk attempt {attempt} error in {region}: {exc}')
            if attempt < MAX_RETRIES:
                summary.retried_chunks += 1
                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)
                continue
            summary.failed_chunks += 1
            log_group_preview = log_groups[:3] + (['...'] if len(log_groups) > 3 else [])
            time_range = f"{datetime.datetime.fromtimestamp(start_ts).isoformat()} to {datetime.datetime.fromtimestamp(end_ts).isoformat()}"
            summary.warnings.append(
                f'Query failed in {region} after {MAX_RETRIES} retries. '
                f'Log groups: {log_group_preview}. Time range: {time_range}. '
                f'Error: {exc}. Suggestion: Try reducing time range or number of log groups.'
            )
            return []
        except Exception as exc:
            logger.exception(f'Chunk attempt {attempt} error in {region}: {exc}')
            if attempt < MAX_RETRIES:
                summary.retried_chunks += 1
                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)
                continue
            summary.failed_chunks += 1
            # Provide actionable error context
            log_group_preview = log_groups[:3] + (['...'] if len(log_groups) > 3 else [])
            time_range = f"{datetime.datetime.fromtimestamp(start_ts).isoformat()} to {datetime.datetime.fromtimestamp(end_ts).isoformat()}"
            summary.warnings.append(
                f'Query failed in {region} after {MAX_RETRIES} retries. '
                f'Log groups: {log_group_preview}. Time range: {time_range}. '
                f'Error: {exc}. Suggestion: Try reducing time range or number of log groups.'
            )
            return []

        # ---- adaptive re-chunking on splittable limit hits ----
        needs_split = _hit_output_limit(result) or _is_splittable_failure(result)
        if needs_split:
            reason = 'output record limit' if _hit_output_limit(result) else 'timeout'
            mid_ts = (start_ts + end_ts) // 2

            if mid_ts == start_ts or rechunk_depth >= MAX_RECHUNK_DEPTH:
                cap_reason = (
                    'time range cannot be split further'
                    if mid_ts == start_ts
                    else f'max re-chunk depth ({MAX_RECHUNK_DEPTH}) reached'
                )
                summary.warnings.append(
                    f'Chunk in {region} hit {reason} but {cap_reason}; returning partial results'
                )
                if result.get('results'):
                    summary.successful_chunks += 1
                else:
                    summary.failed_chunks += 1
                break

            logger.info(f'Chunk hit {reason} – splitting time range (depth {rechunk_depth + 1})')
            summary.re_chunked += 1
            summary.warnings.append(
                f'Chunk in {region} hit {reason}; splitting time range into halves'
            )
            # Run halves sequentially within this chunk's "slot" to avoid
            # exponential fan-out that would blow past the concurrent query limit.
            first_half = await _run_chunk(
                region_ctx,
                logs_client,
                log_groups,
                start_ts,
                mid_ts,
                query_string,
                limit,
                max_timeout,
                summary,
                region,
                account,
                rechunk_depth + 1,
            )
            second_half = await _run_chunk(
                region_ctx,
                logs_client,
                log_groups,
                mid_ts,
                end_ts,
                query_string,
                limit,
                max_timeout,
                summary,
                region,
                account,
                rechunk_depth + 1,
            )
            return first_half + second_half

        # ---- non-splittable failure (e.g. bad query syntax, permissions) ----
        if result['status'] == 'Failed':
            summary.failed_chunks += 1
            summary.warnings.append(
                f'Query failed in {region} (likely query error, not timeout): '
                f'status={result["status"]}'
            )
            return []

        if result['status'] == 'Complete':
            summary.successful_chunks += 1
            break

        # Retryable non-complete status (Cancelled, etc.)
        if attempt < MAX_RETRIES:
            summary.retried_chunks += 1
            await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)
        else:
            summary.failed_chunks += 1
            summary.warnings.append(f'Chunk ended with status {result["status"]} in {region}')

    # Annotate rows
    rows = result.get('results', [])
    _annotate_rows(rows, region, account, log_groups)
    return rows


async def execute_cwl_insights_batch(
    ctx: Context,
    log_group_names: Annotated[
        List[str],
        Field(
            description=(
                'List of CloudWatch log group names or ARNs to query. '
                'Use ARN format (arn:aws:logs:region:account-id:log-group:name) for cross-account/cross-region queries. '
                'These will be automatically chunked into batches of 50 per StartQuery call.'
            ),
        ),
    ],
    regions: Annotated[
        List[str],
        Field(
            description=(
                'List of AWS regions to query (e.g. ["us-east-1", "eu-west-1"]). '
                'The same query and log group names are executed in every region.'
            ),
        ),
    ],
    start_time: str = Field(
        ...,
        description='ISO 8601 start time (e.g. "2025-04-19T20:00:00+00:00").',
    ),
    end_time: str = Field(
        ...,
        description='ISO 8601 end time (e.g. "2025-04-19T21:00:00+00:00").',
    ),
    query_string: str = Field(
        ...,
        description=(
            'CloudWatch Logs Insights query string. '
            'See https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html'
        ),
    ),
    limit: Annotated[
        int | None,
        Field(
            description=(
                'Max log events per chunk. Use this or a `| limit N` clause in the query '
                'to avoid overwhelming the agent context window.'
            ),
        ),
    ] = None,
    max_timeout: Annotated[
        int,
        Field(
            description='Max seconds to poll each chunk before giving up (default 120).',
        ),
    ] = 120,
    account_label: Annotated[
        str | None,
        Field(
            description=(
                'Optional account identifier to annotate results with '
                '(e.g., "prod-123456789012"). Useful for cross-account queries '
                'from a monitoring account to label which source account the data came from.'
            ),
        ),
    ] = None,
    profile_name: Annotated[
        str | None,
        Field(
            description=(
                'AWS CLI profile name (e.g., "prod-readonly", "default"). '
                'Falls back to AWS_PROFILE env var or default credential chain.'
            ),
        ),
    ] = None,
) -> MultiRegionQueryResult:
    """Run a CloudWatch Logs Insights query across multiple log groups, accounts, and regions.

    Automatically chunks log groups (max 50 per StartQuery), throttles concurrency
    to 25% of account limits, retries transient failures, and splits time ranges
    on 10k-record or timeout hits (up to 4 levels). Results are annotated with
    _region, _logGroups, and optionally _account metadata.

    For simple single-region queries on a few log groups, use execute_log_insights_query instead.

    Raises:
        ValueError: If input parameters are invalid (e.g. start_time >= end_time).
    """
    # Validate inputs
    if not log_group_names:
        raise ValueError("log_group_names cannot be empty")

    if not regions:
        raise ValueError("regions cannot be empty")

    if max_timeout <= 0:
        raise ValueError(f"max_timeout must be positive, got {max_timeout}")

    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")

    # Convert and validate time range
    try:
        start_ts = _convert_time(start_time)
        end_ts = _convert_time(end_time)
    except ValueError as e:
        raise ValueError(f"Invalid time parameter: {e}") from e

    if start_ts >= end_ts:
        raise ValueError(
            f"start_time must be before end_time. "
            f"Got start_time={start_time}, end_time={end_time}"
        )

    chunks_per_region = _chunk_list(log_group_names, MAX_LOG_GROUPS_PER_QUERY)
    total_chunks = len(chunks_per_region) * len(regions)

    summary = MultiRegionQuerySummary(
        total_log_groups=len(log_group_names),
        total_regions=len(regions),
        total_chunks=total_chunks,
    )

    await ctx.info(
        f'Dispatching {total_chunks} query chunks across {len(regions)} region(s) '
        f'for {len(log_group_names)} log group(s)…'
    )

    tasks = []
    for region in regions:
        region_ctx = _RegionContext()
        logs_client = get_aws_client('logs', region, profile_name)
        for chunk in chunks_per_region:
            tasks.append(
                _run_chunk(
                    region_ctx,
                    logs_client,
                    chunk,
                    start_ts,
                    end_ts,
                    query_string,
                    limit,
                    max_timeout,
                    summary,
                    region,
                    account_label,
                )
            )

    all_rows_nested = await asyncio.gather(*tasks)
    merged = [row for rows in all_rows_nested for row in rows]
    summary.total_records_returned = len(merged)

    # Warn about large result sets
    if len(merged) >= LARGE_RESULT_WARNING_THRESHOLD:
        warning_msg = (
            f'Large result set: {len(merged)} records returned. '
            f'This may consume significant memory. Consider using the limit parameter '
            f'or adding "| limit N" to your query to reduce result size.'
        )
        summary.warnings.append(warning_msg)
        await ctx.warning(warning_msg)

    if summary.failed_chunks:
        await ctx.warning(
            f'{summary.failed_chunks} chunk(s) failed. See summary.warnings for details.'
        )

    return MultiRegionQueryResult(summary=summary, results=merged)
