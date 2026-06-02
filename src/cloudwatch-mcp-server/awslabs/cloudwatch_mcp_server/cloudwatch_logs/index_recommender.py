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

"""CloudWatch Logs field index recommender tools.

Analyzes query history to recommend fields that would benefit from indexing.
Two tools:
  - recommend_indexes_loggroup: deep analysis of a specific log group (name or ARN)
  - recommend_indexes_account: fast triage across all log groups in the account
"""

import asyncio
import datetime
import json
from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.query_parser import (
    FieldUsage,
    detect_language,
    parse_query_fields,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.scoring import (
    CARDINALITY_SAMPLE_HOURS,
    FIELD_EXISTENCE_SAMPLE_HOURS,
    QUERY_HISTORY_DAYS,
    QUERY_TIMEOUT,
    SYSTEM_FIELDS,
    TOP_N_FOR_CARDINALITY,
    AccountIndexRecommenderResult,
    AlreadyIndexedField,
    FieldNotFound,
    IndexRecommenderResult,
    build_recommendations,
    score_fields,
    score_fields_lightweight,
)
from awslabs.cloudwatch_mcp_server.common import remove_null_values
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_log_group_name(identifier: str) -> str:
    """Extract log group name from an ARN or return as-is if already a name."""
    if identifier.startswith('arn:'):
        parts = identifier.split(':log-group:')
        if len(parts) == 2:
            return parts[1].rstrip(':*').rstrip(':')
    return identifier


async def _run_quick_query(
    logs_client, log_group: str, query_string: str, hours: int, timeout: int
) -> List[Dict]:
    """Run a quick Insights query and return results."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now - datetime.timedelta(hours=hours)
    try:
        resp = logs_client.start_query(
            logGroupNames=[log_group],
            startTime=int(start.timestamp()),
            endTime=int(now.timestamp()),
            queryString=query_string,
            limit=1,
        )
        query_id = resp['queryId']
        delay = 0.2
        elapsed = 0.0
        while elapsed < timeout:
            await asyncio.sleep(delay)
            elapsed += delay
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] in ('Complete', 'Failed', 'Cancelled', 'Timeout'):
                return [{f['field']: f['value'] for f in row} for row in result.get('results', [])]
            delay = min(delay * 2, 2.0)
        return []
    except Exception as e:
        logger.warning(f'Quick query failed: {e}')
        return []


def _paginate_describe_queries(
    logs_client,
    max_total: int = 10000,
    **kwargs,
) -> List[Dict]:
    """Paginate DescribeQueries with a cap on total results."""
    all_queries: List[Dict] = []
    next_token = None
    first = True
    while first or next_token:
        first = False
        page_size = min(1000, max_total - len(all_queries))
        if page_size <= 0:
            break
        call_kwargs = remove_null_values(
            {**kwargs, 'maxResults': page_size, 'nextToken': next_token}
        )
        resp = logs_client.describe_queries(**call_kwargs)
        all_queries.extend(resp.get('queries', []))
        next_token = resp.get('nextToken')
        if len(all_queries) >= max_total:
            break
    return all_queries


def _build_field_usage(
    queries: List[Dict],
    now_epoch: float,
) -> tuple[Dict[str, FieldUsage], Set[str]]:
    """Parse queries and build field usage map."""
    field_usage: Dict[str, FieldUsage] = {}
    unique_qs: Set[str] = set()
    for q in queries:
        qs = q.get('queryString', '')
        create_time = q.get('createTime', 0) / 1000.0
        unique_qs.add(qs)
        lang = q.get('queryLanguage', '').upper()
        if lang not in ('CWLI', 'SQL', 'PPL'):
            lang = detect_language(qs).upper()
        try:
            parsed = parse_query_fields(qs, lang)
        except Exception as e:
            logger.warning(f'Failed to parse query: {e}. Query: {qs[:100]}...')
            continue
        for field_name, usage_type in parsed.items():
            if field_name in SYSTEM_FIELDS or field_name.startswith('@'):
                continue
            fu = field_usage.setdefault(field_name, FieldUsage())
            fu.total_count += 1
            fu.unique_query_strings.add(qs)
            fu.most_recent_use = max(fu.most_recent_use, create_time)
            if usage_type == 'filter_equality':
                fu.filter_equality_count += 1
            elif usage_type == 'filter_non_equality':
                fu.non_equality_filter_count += 1
            else:
                fu.display_only_count += 1
    return field_usage, unique_qs


# ---------------------------------------------------------------------------
# Analysis pipelines
# ---------------------------------------------------------------------------
async def _analyze_log_group(
    ctx: Context,
    logs_client,
    log_group_identifier: str,
    queries: List[Dict],
    now_epoch: float,
) -> IndexRecommenderResult:
    """Full analysis pipeline for a single log group."""
    log_group_name = _extract_log_group_name(log_group_identifier)
    warnings: List[str] = []

    field_usage, unique_qs = _build_field_usage(queries, now_epoch)
    if not field_usage:
        return IndexRecommenderResult(
            queries_analyzed=len(queries),
            unique_queries=len(unique_qs),
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=['No indexable fields found in query history (only system fields used).'],
        )

    # Check current index policies
    indexed_fields: Dict[str, str] = {}
    try:
        resp = logs_client.describe_index_policies(logGroupIdentifiers=[log_group_identifier])
        for policy in resp.get('indexPolicies', []):
            source = policy.get('source', 'UNKNOWN')
            doc = json.loads(policy.get('policyDocument', '{}'))
            for f in doc.get('Fields', []):
                indexed_fields[f] = source
    except Exception as e:
        logger.warning(f'Could not fetch index policies for {log_group_name}: {e}')
        warnings.append(f'Could not fetch index policies: {e}')

    # Split already-indexed vs candidates
    already_indexed = []
    candidates: Dict[str, FieldUsage] = {}
    for name, fu in field_usage.items():
        if name in indexed_fields:
            already_indexed.append(
                AlreadyIndexedField(
                    field_name=name, query_count=fu.total_count, source=indexed_fields[name]
                )
            )
        else:
            candidates[name] = fu

    if not candidates:
        return IndexRecommenderResult(
            already_indexed=already_indexed,
            queries_analyzed=len(queries),
            unique_queries=len(unique_qs),
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=warnings or ['All queried fields are already indexed.'],
        )

    # Check field existence (batched, concurrent)
    existing_fields: Set[str] = set()
    candidate_names = list(candidates.keys())
    chunks = [candidate_names[i : i + 50] for i in range(0, len(candidate_names), 50)]

    async def _check_chunk(chunk: List[str]) -> None:
        results = await _run_quick_query(
            logs_client,
            log_group_name,
            f'fields {", ".join(chunk)} | limit 1',
            FIELD_EXISTENCE_SAMPLE_HOURS,
            QUERY_TIMEOUT,
        )
        if results:
            existing_fields.update(n for n in chunk if results[0].get(n) is not None)

    await asyncio.gather(*[_check_chunk(c) for c in chunks])

    fields_not_found = [
        FieldNotFound(field_name=n, query_count=fu.total_count)
        for n, fu in candidates.items()
        if n not in existing_fields
    ]
    scorable = {n: fu for n, fu in candidates.items() if n in existing_fields}

    if not scorable:
        return IndexRecommenderResult(
            already_indexed=already_indexed,
            fields_not_found=fields_not_found,
            queries_analyzed=len(queries),
            unique_queries=len(unique_qs),
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=warnings + ['No candidate fields found in log data.'],
        )

    # Scan volume
    stored_bytes = 0
    try:
        lg_resp = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)
        for lg in lg_resp.get('logGroups', []):
            if lg.get('logGroupName') == log_group_name:
                stored_bytes = lg.get('storedBytes', 0)
                break
    except Exception as e:
        logger.warning(f'Could not fetch log group metadata: {e}')
    scan_vol_norm = 1.0 if stored_bytes > 0 else 0.0

    # Score + cardinality refinement
    scored = score_fields(scorable, now_epoch, scan_vol_norm)
    await ctx.info(f'Checking cardinality for top candidates in {log_group_name}...')

    cardinality_map: Dict[str, float] = {}
    top_fields = [name for name, _, _, _ in scored[:TOP_N_FOR_CARDINALITY]]
    if top_fields:
        stats_clauses = [
            f'count_distinct({name}) as card_{i}' for i, name in enumerate(top_fields)
        ]
        card_results = await _run_quick_query(
            logs_client,
            log_group_name,
            f'stats {", ".join(stats_clauses)} | limit 1',
            CARDINALITY_SAMPLE_HOURS,
            QUERY_TIMEOUT,
        )
        if card_results:
            row = card_results[0]
            for i, name in enumerate(top_fields):
                try:
                    cardinality_map[name] = min(float(row.get(f'card_{i}', 0)) / 1000, 1)
                except (ValueError, TypeError):
                    cardinality_map[name] = 0.0

    recommendations = build_recommendations(scored, cardinality_map or None)

    return IndexRecommenderResult(
        recommendations=recommendations,
        already_indexed=already_indexed,
        fields_not_found=fields_not_found,
        queries_analyzed=len(queries),
        unique_queries=len(unique_qs),
        time_range_days=QUERY_HISTORY_DAYS,
        log_group=log_group_identifier,
        warnings=warnings,
    )


async def _analyze_log_group_lightweight(
    ctx: Context,
    logs_client,
    log_group_identifier: str,
    queries: List[Dict],
    now_epoch: float,
    indexed_fields: Optional[Dict[str, str]] = None,
) -> IndexRecommenderResult:
    """Lightweight analysis: parse fields only (no per-log-group API calls)."""
    field_usage, unique_qs = _build_field_usage(queries, now_epoch)
    if not field_usage:
        return IndexRecommenderResult(
            queries_analyzed=len(queries),
            unique_queries=len(unique_qs),
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=['No indexable fields found (only system fields used).'],
        )

    already_indexed = []
    candidates: Dict[str, FieldUsage] = {}
    for name, fu in field_usage.items():
        if indexed_fields and name in indexed_fields:
            already_indexed.append(
                AlreadyIndexedField(
                    field_name=name, query_count=fu.total_count, source=indexed_fields[name]
                )
            )
        else:
            candidates[name] = fu

    if not candidates:
        return IndexRecommenderResult(
            already_indexed=already_indexed,
            queries_analyzed=len(queries),
            unique_queries=len(unique_qs),
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=['All queried fields are already indexed.'],
        )

    recommendations = score_fields_lightweight(candidates, now_epoch)
    return IndexRecommenderResult(
        recommendations=recommendations,
        already_indexed=already_indexed,
        queries_analyzed=len(queries),
        unique_queries=len(unique_qs),
        time_range_days=QUERY_HISTORY_DAYS,
        log_group=log_group_identifier,
    )


# ---------------------------------------------------------------------------
# Tool 1: Single log group
# ---------------------------------------------------------------------------
async def recommend_indexes_loggroup(
    ctx: Context,
    log_group_identifier: Annotated[
        str,
        Field(
            description=(
                'The CloudWatch log group name or ARN to analyze. '
                'Accepts "/aws/lambda/my-func" or the full ARN. '
                'Use ARN when querying from a monitoring account.'
            )
        ),
    ],
    region: Annotated[
        str | None, Field(description='AWS region. Defaults to AWS_REGION or us-east-1.')
    ] = None,
    profile_name: Annotated[
        str | None,
        Field(description='AWS CLI profile name. Falls back to AWS_PROFILE or default chain.'),
    ] = None,
) -> IndexRecommenderResult:
    """Recommend field indexes for a specific CloudWatch log group.

    Analyzes the last 30 days of completed Logs Insights queries (CWLI, SQL, PPL),
    identifies which fields would benefit most from indexing, and returns prioritized
    recommendations scored by: query frequency (30%), equality filter usage (25%),
    recency (15%), scan volume (15%), cardinality of top 10 (15%).

    Use recommend_indexes_account first to identify which log groups to analyze.
    """
    logs_client = get_aws_client('logs', region, profile_name)
    now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
    cutoff_epoch = now_epoch - (QUERY_HISTORY_DAYS * 86400)
    log_group_name = _extract_log_group_name(log_group_identifier)

    await ctx.info(f'Fetching query history for {log_group_name}...')
    try:
        all_queries = _paginate_describe_queries(
            logs_client,
            logGroupName=log_group_name,
            status='Complete',
        )
    except Exception as e:
        logger.exception(f'Error fetching query history: {e}')
        return IndexRecommenderResult(
            queries_analyzed=0,
            unique_queries=0,
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=[f'Error fetching query history: {e}'],
        )

    recent = [q for q in all_queries if q.get('createTime', 0) / 1000.0 >= cutoff_epoch]
    if not recent:
        return IndexRecommenderResult(
            queries_analyzed=0,
            unique_queries=0,
            time_range_days=QUERY_HISTORY_DAYS,
            log_group=log_group_identifier,
            warnings=['No completed queries found in the last 30 days for this log group.'],
        )

    await ctx.info(f'Analyzing {len(recent)} queries...')
    return await _analyze_log_group(ctx, logs_client, log_group_identifier, recent, now_epoch)


# ---------------------------------------------------------------------------
# Tool 2: Account-wide
# ---------------------------------------------------------------------------
async def recommend_indexes_account(
    ctx: Context,
    region: Annotated[
        str | None, Field(description='AWS region. Defaults to AWS_REGION or us-east-1.')
    ] = None,
    profile_name: Annotated[
        str | None,
        Field(description='AWS CLI profile name. Falls back to AWS_PROFILE or default chain.'),
    ] = None,
    max_queries: Annotated[
        int,
        Field(
            description=(
                'Maximum number of queries to analyze. Higher values give more complete results '
                'but take longer. Default 5000 completes in ~5 seconds. Set to 0 for no limit.'
            )
        ),
    ] = 5000,
) -> AccountIndexRecommenderResult:
    """Triage tool: find which log groups would benefit from field indexing.

    Scans the last 30 days of completed Logs Insights queries across the account,
    groups by log group, and identifies frequently queried but unindexed fields.
    Lightweight scan — no per-log-group Insights queries. Use recommend_indexes_loggroup
    for full analysis on specific log groups.
    """
    logs_client = get_aws_client('logs', region, profile_name)
    now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
    cutoff_epoch = now_epoch - (QUERY_HISTORY_DAYS * 86400)
    warnings: List[str] = []

    await ctx.info('Fetching account-wide query history...')
    try:
        effective_max = max_queries if max_queries > 0 else 10_000_000
        all_queries = _paginate_describe_queries(
            logs_client,
            max_total=effective_max,
            status='Complete',
        )
    except Exception as e:
        logger.exception(f'Error fetching query history: {e}')
        return AccountIndexRecommenderResult(
            log_group_results=[],
            total_log_groups_analyzed=0,
            total_queries_analyzed=0,
            time_range_days=QUERY_HISTORY_DAYS,
            warnings=[f'Error fetching query history: {e}'],
        )

    recent = [q for q in all_queries if q.get('createTime', 0) / 1000.0 >= cutoff_epoch]
    if max_queries > 0 and len(all_queries) >= max_queries:
        warnings.append(
            f'Query history was capped at {max_queries} queries. Results may not cover all '
            f'activity. Use recommend_indexes_loggroup for specific log groups or increase '
            f'max_queries for more complete results.'
        )
    if not recent:
        return AccountIndexRecommenderResult(
            log_group_results=[],
            total_log_groups_analyzed=0,
            total_queries_analyzed=0,
            time_range_days=QUERY_HISTORY_DAYS,
            warnings=['No completed queries found in the last 30 days.'],
        )

    by_lg: Dict[str, List[Dict]] = {}
    for q in recent:
        lg = q.get('logGroupName', '')
        if lg:
            by_lg.setdefault(lg, []).append(q)

    await ctx.info(f'Found queries across {len(by_lg)} log groups. Analyzing...')

    # Fetch account-level index policies once
    account_indexed: Dict[str, str] = {}
    try:
        resp = logs_client.describe_account_policies(policyType='FIELD_INDEX_POLICY')
        for policy in resp.get('accountPolicies', []):
            doc = json.loads(policy.get('policyDocument', '{}'))
            for f in doc.get('Fields', []):
                account_indexed[f] = 'ACCOUNT'
    except Exception as e:
        logger.warning(f'Could not fetch account-level index policies: {e}')

    results: List[IndexRecommenderResult] = []
    for lg_name, lg_queries in by_lg.items():
        result = await _analyze_log_group_lightweight(
            ctx,
            logs_client,
            lg_name,
            lg_queries,
            now_epoch,
            indexed_fields=account_indexed or None,
        )
        if result.recommendations or result.already_indexed:
            results.append(result)

    results.sort(
        key=lambda r: r.recommendations[0].score if r.recommendations else 0,
        reverse=True,
    )

    return AccountIndexRecommenderResult(
        log_group_results=results,
        total_log_groups_analyzed=len(by_lg),
        total_queries_analyzed=len(recent),
        time_range_days=QUERY_HISTORY_DAYS,
        warnings=warnings,
    )
