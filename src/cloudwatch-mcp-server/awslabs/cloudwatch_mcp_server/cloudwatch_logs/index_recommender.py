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
  - recommend_indexes_loggroup: for a specific log group (name or ARN)
  - recommend_indexes_account: for all log groups in the account
"""

import asyncio
import datetime
import json
import math
import re
from awslabs.cloudwatch_mcp_server.aws_common import get_aws_client
from awslabs.cloudwatch_mcp_server.common import remove_null_values
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field
from typing import Annotated, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Query history retention: DescribeQueries API retains approximately 30 days
# Source: https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_DescribeQueries.html
QUERY_HISTORY_DAYS = 30  # DescribeQueries API retains ~30 days of history
TOP_N_FOR_CARDINALITY = 10  # Balance between accuracy and API cost (10 extra queries)
CARDINALITY_SAMPLE_HOURS = 1  # Recent 1-hour sample for cardinality estimation
FIELD_EXISTENCE_SAMPLE_HOURS = 1  # Recent 1-hour sample to verify field exists
QUERY_TIMEOUT = 30  # Max seconds to poll each Insights query before giving up

# System/default-indexed fields to always exclude
# Source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-FilterIndex.html
# CloudWatch Logs provides default indexes for all Standard log class log groups.
# These fields are automatically indexed and don't need custom index policies.
SYSTEM_FIELDS: Set[str] = {
    # Universal default indexes (all Standard log class log groups)
    '@timestamp',
    '@message',
    '@logStream',
    '@log',
    '@ptr',
    '@ingestionTime',
    '@aws.region',
    '@aws.account',
    '@source.log',
    '@data_source_name',
    '@data_source_type',
    '@data_format',
    'traceId',
    'severityText',
    'attributes.session.id',
    # Data-source-specific default indexes
    # VPC Flow Logs (amazon_vpc.flow)
    'action',
    'logStatus',
    'flowDirection',
    'type',
    # Route53 Resolver Query Logs (amazon_route53.resolver_query)
    'query_type',
    'transport',
    'rcode',
    # AWS WAF (aws_waf.access)
    'httpRequest.country',
    # CloudTrail (aws_cloudtrail.data, aws_cloudtrail.management)
    'eventSource',
    'eventName',
    'awsRegion',
    'userAgent',
    'errorCode',
    'eventType',
    'managementEvent',
    'readOnly',
    'eventCategory',
    'requestId',
}

# Scoring weights (must sum to 1.0)
# Rationale: Frequency and equality usage are most predictive of indexing benefit.
# Field indexes only accelerate equality-based queries (field = value, field IN [...]).
# Source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs-Field-Indexing.html
# Recency ensures we prioritize current usage patterns. Scan volume and cardinality
# provide additional signal but are secondary factors.
W_FREQUENCY = 0.30  # How often the field is queried
W_FILTER_EQUALITY = 0.25  # Ratio of equality filter usage (indexes only help equality)
W_RECENCY = 0.15  # Time-decay: recent usage matters more
W_SCAN_VOLUME = 0.15  # Log group size (bigger = more benefit from indexing)
W_CARDINALITY = 0.15  # Field cardinality (higher = more benefit)

if W_FREQUENCY + W_FILTER_EQUALITY + W_RECENCY + W_SCAN_VOLUME + W_CARDINALITY != 1.0:
    raise ValueError('Scoring weights must sum to 1.0')

RECENCY_HALF_LIFE_DAYS = 7  # Exponential decay: queries from 7 days ago have 50% weight


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------
class FieldScoreBreakdown(BaseModel):
    """Score breakdown for a single field."""

    frequency_score: float = Field(..., description='Normalized query frequency score')
    filter_equality_score: float = Field(..., description='Ratio of equality filter usage')
    recency_score: float = Field(..., description='Time-decay weighted recency score')
    scan_volume_score: float = Field(..., description='Normalized log group scan volume score')
    cardinality_score: Optional[float] = Field(
        default=None, description='Normalized cardinality score (only for top candidates)'
    )


class IndexRecommendation(BaseModel):
    """A single field index recommendation."""

    field_name: str = Field(..., description='The field name recommended for indexing')
    score: float = Field(..., description='Overall recommendation score (0-1, higher is better)')
    action: str = Field(..., description='Recommended action: CREATE_INDEX')
    query_count: int = Field(..., description='Number of queries using this field in the period')
    filter_equality_count: int = Field(
        ..., description='Number of queries using this field in equality filters'
    )
    score_breakdown: FieldScoreBreakdown = Field(..., description='Detailed score breakdown')


class AlreadyIndexedField(BaseModel):
    """A field that is already indexed."""

    field_name: str = Field(..., description='The field name')
    query_count: int = Field(..., description='Number of queries using this field')
    source: str = Field(..., description='Index source: ACCOUNT or LOG_GROUP')


class FieldNotFound(BaseModel):
    """A field referenced in queries but not found in log data."""

    field_name: str = Field(..., description='The field name')
    query_count: int = Field(..., description='Number of queries referencing this field')


class IndexRecommenderResult(BaseModel):
    """Result of the index recommender analysis for a single log group."""

    recommendations: List[IndexRecommendation] = Field(
        default_factory=list, description='Fields recommended for indexing, sorted by score'
    )
    already_indexed: List[AlreadyIndexedField] = Field(
        default_factory=list, description='Fields already indexed (no action needed)'
    )
    fields_not_found: List[FieldNotFound] = Field(
        default_factory=list, description='Fields referenced in queries but not in log data'
    )
    queries_analyzed: int = Field(..., description='Total completed queries analyzed')
    unique_queries: int = Field(..., description='Unique query strings analyzed')
    time_range_days: int = Field(..., description='Days of query history covered')
    log_group: str = Field(..., description='Log group name or ARN analyzed')
    warnings: List[str] = Field(default_factory=list, description='Warnings encountered')


class AccountIndexRecommenderResult(BaseModel):
    """Result of the account-level index recommender analysis."""

    log_group_results: List[IndexRecommenderResult] = Field(
        ..., description='Per-log-group recommendations, sorted by highest field score'
    )
    total_log_groups_analyzed: int = Field(
        ..., description='Number of log groups with query history'
    )
    total_queries_analyzed: int = Field(..., description='Total queries analyzed across account')
    time_range_days: int = Field(..., description='Days of query history covered')
    warnings: List[str] = Field(default_factory=list, description='Warnings encountered')


# ---------------------------------------------------------------------------
# Query parsing
# ---------------------------------------------------------------------------
# Parses CWLI, SQL, and PPL query strings to extract field names and classify usage.
# Query language docs:
#   - CWLI: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
#   - SQL: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_SQL.html
#   - PPL: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_PPL.html
#
# Field usage classification:
#   - filter_equality: fields used in equality filters (field = val, field IN [...])
#     These benefit most from indexing since indexes enable exact-match skipping.
#   - filter_non_equality: fields used in non-equality filters (field like, field >, etc.)
#     Indexes don't help these — included for completeness but penalized in scoring.
#   - display: fields used only in SELECT/fields/stats/sort (not filtered)
#     Lower priority for indexing but still tracked.
#
# Preprocessing steps:
#   1. Strip parse...as aliases (query-created variables, not real log fields)
#   2. Strip quoted strings and regex patterns (avoid matching field names inside values)
#   3. Strip 'as <alias>' patterns (stats count() as cnt — cnt is an alias)
#
# Post-extraction filtering:
#   - Exclude system fields (@timestamp, @message, etc.)
#   - Exclude keywords (as, by, limit, count, etc.)
#   - Exclude numeric-prefixed tokens (5m, 1h, 30s — time buckets, not fields)
#
class _FieldUsage:
    """Tracks how a field is used across queries."""

    def __init__(self):
        self.total_count: int = 0
        self.filter_equality_count: int = 0
        self.non_equality_filter_count: int = 0
        self.display_only_count: int = 0
        self.most_recent_use: float = 0.0
        self.unique_query_strings: Set[str] = set()


# CWLI/PPL regex patterns
# Matches: filter field = "val", filterIndex field = "val"
_FILTER_EQUALITY_RE = re.compile(r'(?:filter|filterIndex)\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
# Matches: and field = "val", or field = "val" (compound conditions)
_FILTER_AND_EQUALITY_RE = re.compile(r'(?:and|or)\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
# Matches: filter field IN [...], filterIndex field IN [...]
_FILTER_IN_RE = re.compile(r'(?:filter|filterIndex)\s+(\w[\w.]*)\s+(?:in|IN)\s*\[', re.IGNORECASE)
# Matches: filter field like /regex/, filter field != val, filter field > val
_FILTER_NON_EQUALITY_RE = re.compile(
    r'filter\s+(\w[\w.]*)\s+(?:like|not\s+like|!=|<|>|<=|>=)', re.IGNORECASE
)
# Matches: fields field1, field2, ... | (captures everything until pipe or end)
_FIELDS_RE = re.compile(r'fields\s+(.*?)(?:\||$)', re.IGNORECASE)
# Matches: stats count(*) as alias by field1, field2 | (captures by clause)
_STATS_BY_RE = re.compile(
    r'(?:stats|count|sum|avg|min|max|count_distinct|pct)\s*\(.*?\)\s*(?:as\s+\w+[\s,]*)?\s*by\s+(.*?)(?:\||$)',
    re.IGNORECASE,
)
# Matches: sort field asc/desc
_SORT_RE = re.compile(r'sort\s+(\w[\w.]*)', re.IGNORECASE)

# SQL-specific patterns
# Matches: field = 'val', field = "val", field = 123, `field` = val
_SQL_WHERE_EQUALITY_RE = re.compile(
    r'[`]?(\w[\w.]*)[`]?\s*=\s*(?:\'[^\']*\'|"[^"]*"|\d+)', re.IGNORECASE
)
# Matches: field IN (...), `field` IN (...)
_SQL_WHERE_IN_RE = re.compile(r'[`]?(\w[\w.]*)[`]?\s+IN\s*\(', re.IGNORECASE)
# Matches: field LIKE '%val%', field != val, field <> val
_SQL_WHERE_NON_EQ_RE = re.compile(
    r'[`]?(\w[\w.]*)[`]?\s+(?:LIKE|NOT\s+LIKE|!=|<>)\s', re.IGNORECASE
)
# Matches: SELECT field1, field2, ... FROM (captures select list)
_SQL_SELECT_RE = re.compile(r'SELECT\s+(.*?)\s+FROM\b', re.IGNORECASE | re.DOTALL)
# Matches: GROUP BY field1, field2 (captures until HAVING/ORDER/LIMIT/end)
_SQL_GROUP_BY_RE = re.compile(
    r'GROUP\s+BY\s+(.*?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|$)', re.IGNORECASE
)
# Matches: ORDER BY field1, field2 (captures until LIMIT/end)
_SQL_ORDER_BY_RE = re.compile(r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)', re.IGNORECASE)
# Matches: filterIndex('field' = 'value') — SQL uses quoted field names
_SQL_FILTERINDEX_RE = re.compile(r"filterIndex\s*\(\s*'(\w[\w.]*)'\s*=\s*", re.IGNORECASE)

# PPL-specific patterns (PPL uses 'where' instead of 'filter')
# Matches: where field = val
_PPL_WHERE_EQUALITY_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
# Matches: where field IN [...]
_PPL_WHERE_IN_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s+IN\s*\[', re.IGNORECASE)
# Matches: where field like val, where field != val
_PPL_WHERE_NON_EQ_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s+(?:like|!=|<|>|<=|>=)', re.IGNORECASE)


def _extract_field_names(text: str, language: str = 'cwli') -> List[str]:
    """Extract field names from a comma-separated field list, ignoring functions and keywords.

    Uses function call detection (token followed by '(') to filter out function names,
    plus language-specific reserved keywords.
    """
    # Language-specific reserved keywords
    reserved_by_lang = {
        'cwli': {
            'as',
            'by',
            'asc',
            'desc',
            'limit',
            'like',
            'not',
            'in',
            'and',
            'or',
            'parse',
            'fields',
            'filter',
            'stats',
            'sort',
            'display',
        },
        'sql': {
            'as',
            'by',
            'asc',
            'desc',
            'limit',
            'like',
            'not',
            'in',
            'and',
            'or',
            'from',
            'where',
            'group',
            'having',
            'order',
            'join',
            'inner',
            'left',
            'outer',
            'on',
            'distinct',
            'between',
            'case',
            'when',
            'then',
            'else',
            'end',
            'null',
            'true',
            'false',
            'is',
            'select',
        },
        'ppl': {
            'as',
            'by',
            'asc',
            'desc',
            'limit',
            'like',
            'not',
            'in',
            'and',
            'or',
            'where',
            'source',
            'fields',
            'stats',
            'sort',
            'head',
            'tail',
            'dedup',
            'eval',
            'rename',
        },
    }
    reserved = reserved_by_lang.get(language.lower(), reserved_by_lang['cwli'])

    # Strip "as <alias>" patterns — aliases are not real log fields
    cleaned = re.sub(r'\bas\s+\w[\w.]*', '', text, flags=re.IGNORECASE)
    # Strip backtick-quoted names and extract the inner name
    cleaned = re.sub(r'`(\w[\w.]*)`', r'\1', cleaned)

    # Extract all word tokens
    names = re.findall(r'@[\w.]+|\b(\w[\w.]*)\b', cleaned)

    # Pre-compile regex for function call detection (performance optimization)
    func_pattern = re.compile(r'\b(\w[\w.]*)\s*\(', re.IGNORECASE)
    func_names = {m.group(1).lower() for m in func_pattern.finditer(cleaned)}

    result = []
    for n in names:
        if not n:
            continue
        # Exclude: reserved keywords, numeric-prefixed (5m, 1h), function calls
        if n.lower() in reserved or n[0].isdigit() or n.lower() in func_names:
            continue
        result.append(n)
    return result


def _detect_language(query_string: str) -> str:
    """Detect query language: 'sql', 'ppl', or 'cwli'."""
    if not query_string:
        return 'cwli'
    stripped = query_string.strip()
    if re.match(r'\s*SELECT\b', stripped, re.IGNORECASE):
        return 'sql'
    # PPL starts with SOURCE (when used via API) or uses pipe-delimited 'where' (not 'filter')
    if re.match(r'\s*SOURCE\b', stripped, re.IGNORECASE):
        # Could be CWLI SOURCE or PPL source — check for PPL-specific commands
        if re.search(r'\|\s*where\b', stripped, re.IGNORECASE):
            return 'ppl'
    # If it has 'where' but not 'filter', likely PPL
    if re.search(r'\|\s*where\b', stripped, re.IGNORECASE) and not re.search(
        r'\|\s*filter\b', stripped, re.IGNORECASE
    ):
        return 'ppl'
    return 'cwli'


def _strip_comments(query_string: str) -> str:
    """Strip inline comments from query string.

    CWLI/PPL use # for comments, SQL uses -- and /* */.
    """
    # Strip SQL block comments /* ... */
    cleaned = re.sub(r'/\*.*?\*/', '', query_string, flags=re.DOTALL)
    # Strip SQL line comments --
    cleaned = re.sub(r'--[^\n]*', '', cleaned)
    # Strip CWLI/PPL comments #
    cleaned = re.sub(r'#[^\n]*', '', cleaned)
    return cleaned


def _strip_values(query_string: str) -> str:
    """Strip quoted strings, regex patterns, and comments to avoid matching field names inside values.

    Handles escaped quotes within strings.
    """
    # Strip comments first
    cleaned = _strip_comments(query_string)
    # Strip regex patterns: /.../ (simplified to avoid catastrophic backtracking)
    cleaned = re.sub(r'/[^/]*/', '""', cleaned)
    # Strip double-quoted strings (handles escaped quotes)
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cleaned)
    # Strip single-quoted strings (handles escaped quotes)
    cleaned = re.sub(r"'(?:[^'\\]|\\.)*'", '""', cleaned)
    return cleaned


def _parse_sql_fields(query_string: str) -> Dict[str, str]:
    """Parse a SQL query string and return {field_name: usage_type}."""
    fields: Dict[str, str] = {}

    # filterIndex must be extracted BEFORE stripping values since it uses quoted field names
    for m in _SQL_FILTERINDEX_RE.finditer(query_string):
        fields[m.group(1)] = 'filter_equality'

    cleaned = _strip_values(query_string)

    # Extract WHERE clause to apply condition patterns only there
    where_match = re.search(
        r'\bWHERE\b(.*?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', cleaned, re.IGNORECASE | re.DOTALL
    )
    if where_match:
        where_clause = where_match.group(1)
        for m in _SQL_WHERE_EQUALITY_RE.finditer(where_clause):
            fields[m.group(1)] = 'filter_equality'
        for m in _SQL_WHERE_IN_RE.finditer(where_clause):
            fields[m.group(1)] = 'filter_equality'
        for m in _SQL_WHERE_NON_EQ_RE.finditer(where_clause):
            if m.group(1) not in fields:
                fields[m.group(1)] = 'filter_non_equality'

    # SELECT fields
    for m in _SQL_SELECT_RE.finditer(cleaned):
        select_text = m.group(1)
        if select_text.strip() != '*':
            for name in _extract_field_names(select_text, 'sql'):
                if name not in fields:
                    fields[name] = 'display'

    # GROUP BY
    for m in _SQL_GROUP_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'sql'):
            if name not in fields:
                fields[name] = 'display'

    # ORDER BY
    for m in _SQL_ORDER_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'sql'):
            if name not in fields:
                fields[name] = 'display'

    return fields


def _parse_ppl_fields(query_string: str) -> Dict[str, str]:
    """Parse a PPL query string and return {field_name: usage_type}."""
    fields: Dict[str, str] = {}
    cleaned = _strip_values(query_string)

    # PPL uses 'where' instead of 'filter', but also supports filterIndex
    for m in _FILTER_EQUALITY_RE.finditer(cleaned):
        fields[m.group(1)] = 'filter_equality'
    for m in _PPL_WHERE_EQUALITY_RE.finditer(cleaned):
        fields[m.group(1)] = 'filter_equality'
    for m in _FILTER_AND_EQUALITY_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'filter_equality'
    for m in _PPL_WHERE_IN_RE.finditer(cleaned):
        fields[m.group(1)] = 'filter_equality'

    for m in _PPL_WHERE_NON_EQ_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'filter_non_equality'

    # PPL 'fields' command is same as CWLI
    for m in _FIELDS_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'ppl'):
            if name not in fields:
                fields[name] = 'display'

    # PPL stats ... by
    for m in _STATS_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'ppl'):
            if name not in fields:
                fields[name] = 'display'

    for m in _SORT_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'display'

    return fields


def parse_query_fields(query_string: str, language: Optional[str] = None) -> Dict[str, str]:
    """Parse a CWLI, SQL, or PPL query string and return {field_name: usage_type}.

    Args:
        query_string: The query string to parse
        language: Optional language hint ('CWLI', 'SQL', 'PPL'). If not provided, auto-detects.

    Returns:
        Dict mapping field names to usage_type ('filter_equality', 'filter_non_equality', 'display')
    """
    if not query_string:
        return {}

    lang = language.lower() if language else _detect_language(query_string)

    if lang == 'sql':
        return _parse_sql_fields(query_string)
    if lang == 'ppl':
        return _parse_ppl_fields(query_string)

    # CWLI
    fields: Dict[str, str] = {}

    # Strip parse aliases — "parse ... as var1, var2" creates aliases, not real fields
    cleaned = re.sub(r'\bparse\b.*?\bas\b[^|]*', '', query_string, flags=re.IGNORECASE)
    # Strip quoted strings and regex patterns to avoid matching field names inside values
    cleaned = _strip_values(cleaned)

    for m in _FILTER_EQUALITY_RE.finditer(cleaned):
        fields[m.group(1)] = 'filter_equality'
    for m in _FILTER_AND_EQUALITY_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'filter_equality'
    for m in _FILTER_IN_RE.finditer(cleaned):
        fields[m.group(1)] = 'filter_equality'

    for m in _FILTER_NON_EQUALITY_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'filter_non_equality'

    for m in _FIELDS_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'cwli'):
            if name not in fields:
                fields[name] = 'display'
    for m in _STATS_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'cwli'):
            if name not in fields:
                fields[name] = 'display'
    for m in _SORT_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'display'

    return fields


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_log_group_name(identifier: str) -> str:
    """Extract log group name from an ARN or return as-is if already a name."""
    if identifier.startswith('arn:'):
        parts = identifier.split(':log-group:')
        if len(parts) == 2:
            # Strip trailing :* resource suffix (some APIs append this)
            return parts[1].rstrip(':*').rstrip(':')
    return identifier


def _recency_score(epoch_seconds: float, now: float) -> float:
    """Exponential decay score based on age. Returns 0-1."""
    age_days = max(0, (now - epoch_seconds) / 86400.0)
    return math.exp(-0.693 * age_days / RECENCY_HALF_LIFE_DAYS)


def _normalize(value: float, max_value: float) -> float:
    """Normalize value to 0-1 range."""
    return min(value / max_value, 1.0) if max_value > 0 else 0.0


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
        for _ in range(timeout):
            await asyncio.sleep(1)
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] in ('Complete', 'Failed', 'Cancelled', 'Timeout'):
                return [{f['field']: f['value'] for f in row} for row in result.get('results', [])]
        return []
    except Exception as e:
        logger.warning(f'Quick query failed: {e}')
        return []


def _paginate_describe_queries(
    logs_client,
    max_total: int = 10000,
    **kwargs,
) -> List[Dict]:
    """Paginate DescribeQueries with a cap on total results.

    Args:
        logs_client: boto3 CloudWatch Logs client
        max_total: Maximum total queries to return (default 10000). Prevents
            unbounded pagination on high-volume accounts.
        **kwargs: Passed to describe_queries (logGroupName, status, etc.)
    """
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
) -> tuple[Dict[str, _FieldUsage], Set[str]]:
    """Parse queries and build field usage map. Returns (field_usage, unique_query_strings)."""
    field_usage: Dict[str, _FieldUsage] = {}
    unique_qs: Set[str] = set()

    for q in queries:
        qs = q.get('queryString', '')
        create_time = q.get('createTime', 0) / 1000.0
        unique_qs.add(qs)

        # Use API-provided queryLanguage field from DescribeQueries API
        # (https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_DescribeQueries.html)
        # Fall back to detection only for older query history entries that lack this field
        lang = q.get('queryLanguage', '').upper()
        if lang not in ('CWLI', 'SQL', 'PPL'):
            lang = _detect_language(qs).upper()

        try:
            parsed = parse_query_fields(qs, lang)
        except Exception as e:
            # Log parse errors but don't crash — skip this query and continue
            logger.warning(f'Failed to parse query: {e}. Query: {qs[:100]}...')
            continue

        for field_name, usage_type in parsed.items():
            if field_name in SYSTEM_FIELDS or field_name.startswith('@'):
                continue
            fu = field_usage.setdefault(field_name, _FieldUsage())
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


def _score_fields(
    scorable: Dict[str, _FieldUsage],
    now_epoch: float,
    scan_vol_norm: float,
) -> List[tuple]:
    """Score candidate fields. Returns sorted list of (name, score, breakdown, fu)."""
    max_count = max(fu.total_count for fu in scorable.values())
    scored = []
    for name, fu in scorable.items():
        freq = _normalize(fu.total_count, max_count)
        eq_ratio = fu.filter_equality_count / fu.total_count if fu.total_count > 0 else 0.0
        recency = _recency_score(fu.most_recent_use, now_epoch)
        if fu.filter_equality_count == 0 and fu.non_equality_filter_count > 0:
            eq_ratio *= 0.5
        score = (
            freq * W_FREQUENCY
            + eq_ratio * W_FILTER_EQUALITY
            + recency * W_RECENCY
            + scan_vol_norm * W_SCAN_VOLUME
        )
        breakdown = FieldScoreBreakdown(
            frequency_score=freq,
            filter_equality_score=eq_ratio,
            recency_score=recency,
            scan_volume_score=scan_vol_norm,
        )
        scored.append((name, score, breakdown, fu))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


async def _refine_with_cardinality(
    scored: List[tuple],
    logs_client,
    log_group_name: str,
) -> List[IndexRecommendation]:
    """Run cardinality queries on top candidates and build final recommendations."""
    cardinality_map: Dict[str, float] = {}

    # Build single query for all top candidates
    top_fields = [name for name, _, _, _ in scored[:TOP_N_FOR_CARDINALITY]]
    if top_fields:
        stats_clauses = [
            f'count_distinct({name}) as card_{i}' for i, name in enumerate(top_fields)
        ]
        query = f'stats {", ".join(stats_clauses)} | limit 1'

        card_results = await _run_quick_query(
            logs_client,
            log_group_name,
            query,
            CARDINALITY_SAMPLE_HOURS,
            QUERY_TIMEOUT,
        )

        if card_results:
            row = card_results[0]
            for i, name in enumerate(top_fields):
                try:
                    card_val = float(row.get(f'card_{i}', 0))
                    # Normalize: cardinality of 1000+ gets max score (1.0)
                    cardinality_map[name] = min(card_val / 1000, 1)
                except (ValueError, TypeError):
                    cardinality_map[name] = 0.0

    recommendations = []
    for name, base_score, breakdown, fu in scored:
        card = cardinality_map.get(name)
        if card is not None:
            breakdown.cardinality_score = card
            final = (
                breakdown.frequency_score * W_FREQUENCY
                + breakdown.filter_equality_score * W_FILTER_EQUALITY
                + breakdown.recency_score * W_RECENCY
                + breakdown.scan_volume_score * W_SCAN_VOLUME
                + card * W_CARDINALITY
            )
        else:
            final = base_score
        recommendations.append(
            IndexRecommendation(
                field_name=name,
                score=round(final, 4),
                action='CREATE_INDEX',
                query_count=fu.total_count,
                filter_equality_count=fu.filter_equality_count,
                score_breakdown=breakdown,
            )
        )
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations


# ---------------------------------------------------------------------------
# Shared analysis pipeline
# ---------------------------------------------------------------------------
async def _analyze_log_group(
    ctx: Context,
    logs_client,
    log_group_identifier: str,
    queries: List[Dict],
    now_epoch: float,
) -> IndexRecommenderResult:
    """Run the full analysis pipeline for a single log group given its queries."""
    log_group_name = _extract_log_group_name(log_group_identifier)
    warnings: List[str] = []

    # Parse fields
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
    candidates: Dict[str, _FieldUsage] = {}
    for name, fu in field_usage.items():
        if name in indexed_fields:
            already_indexed.append(
                AlreadyIndexedField(
                    field_name=name,
                    query_count=fu.total_count,
                    source=indexed_fields[name],
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

    # Check field existence (batched, chunked to avoid query length limits)
    existing_fields: Set[str] = set()
    candidate_names = list(candidates.keys())
    # Chunk into batches of 50 to avoid query string length limits
    for i in range(0, len(candidate_names), 50):
        chunk = candidate_names[i : i + 50]
        fields_clause = ', '.join(chunk)
        existence_results = await _run_quick_query(
            logs_client,
            log_group_name,
            f'fields {fields_clause} | limit 1',
            FIELD_EXISTENCE_SAMPLE_HOURS,
            QUERY_TIMEOUT,
        )
        if existence_results:
            row = existence_results[0]
            existing_fields.update(n for n in chunk if row.get(n) is not None)

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

    # Get storedBytes for scan volume score
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

    # Score and refine with cardinality
    scored = _score_fields(scorable, now_epoch, scan_vol_norm)
    await ctx.info(f'Checking cardinality for top candidates in {log_group_name}...')
    recommendations = await _refine_with_cardinality(scored, logs_client, log_group_name)

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
    """Lightweight analysis: parse fields only (no API calls per log group).

    Used by the account-level tool. If indexed_fields is provided, uses it to
    classify already-indexed fields. Otherwise skips index policy check entirely.
    """
    warnings: List[str] = []

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
    candidates: Dict[str, _FieldUsage] = {}
    for name, fu in field_usage.items():
        if indexed_fields and name in indexed_fields:
            already_indexed.append(
                AlreadyIndexedField(
                    field_name=name,
                    query_count=fu.total_count,
                    source=indexed_fields[name],
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

    # Simple scoring without existence/cardinality (frequency + filter ratio + recency)
    max_count = max(fu.total_count for fu in candidates.values())
    recommendations = []
    for name, fu in candidates.items():
        freq = _normalize(fu.total_count, max_count)
        eq_ratio = fu.filter_equality_count / fu.total_count if fu.total_count > 0 else 0.0
        recency = _recency_score(fu.most_recent_use, now_epoch)
        if fu.filter_equality_count == 0 and fu.non_equality_filter_count > 0:
            eq_ratio *= 0.5
        score = freq * 0.40 + eq_ratio * 0.35 + recency * 0.25
        recommendations.append(
            IndexRecommendation(
                field_name=name,
                score=round(score, 4),
                action='CREATE_INDEX',
                query_count=fu.total_count,
                filter_equality_count=fu.filter_equality_count,
                score_breakdown=FieldScoreBreakdown(
                    frequency_score=freq,
                    filter_equality_score=eq_ratio,
                    recency_score=recency,
                    scan_volume_score=0.0,
                ),
            )
        )
    recommendations.sort(key=lambda r: r.score, reverse=True)

    return IndexRecommenderResult(
        recommendations=recommendations,
        already_indexed=already_indexed,
        queries_analyzed=len(queries),
        unique_queries=len(unique_qs),
        time_range_days=QUERY_HISTORY_DAYS,
        log_group=log_group_identifier,
        warnings=warnings,
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
            ),
        ),
    ],
    region: Annotated[
        str | None,
        Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
    ] = None,
    profile_name: Annotated[
        str | None,
        Field(description='AWS CLI profile name. Falls back to AWS_PROFILE or default chain.'),
    ] = None,
) -> IndexRecommenderResult:
    """Recommend field indexes for a specific CloudWatch log group.

    CloudWatch Logs field indexes speed up equality-based queries (filter field = "value" or
    filterIndex) by letting Insights skip log events that don't match. This tool analyzes the
    last 30 days of completed Logs Insights queries (CWLI, SQL, and PPL) for the given log
    group, identifies which fields would benefit most from indexing, and returns prioritized
    recommendations.

    The analysis pipeline:
    1. Fetches query history and parses field usage across all three query languages
    2. Checks which fields are already indexed via DescribeIndexPolicies
    3. Verifies candidate fields exist in the log data (batched Insights query)
    4. Scores candidates: query frequency (30%), equality filter usage (25%),
       recency (15%), scan volume (15%), cardinality of top 10 (15%)

    Use recommend_indexes_account first to identify which log groups to analyze, then use
    this tool for full scored analysis on specific log groups.

    Returns:
        - recommendations: fields to index, sorted by score (higher = more impactful)
        - already_indexed: fields that already have indexes (no action needed)
        - fields_not_found: fields referenced in queries but not present in log data
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
        str | None,
        Field(description='AWS region. Defaults to AWS_REGION or us-east-1.'),
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
                'but take longer. Default 5000 completes in ~5 seconds. Set to 0 for no limit '
                '(may be slow on high-volume accounts).'
            ),
        ),
    ] = 5000,
) -> AccountIndexRecommenderResult:
    """Triage tool: find which log groups across the account would benefit from field indexing.

    CloudWatch Logs field indexes speed up equality-based queries by letting Insights skip
    non-matching log events. This tool scans the last 30 days of completed Logs Insights
    queries (CWLI, SQL, PPL) across the entire account, groups them by log group, and
    identifies fields that are frequently queried but not yet indexed.

    This is a fast, lightweight scan — it parses query history and checks account-level index
    policies (single API call) but does NOT check per-log-group index policies or run Insights
    queries to verify field existence or cardinality. Use this tool first to identify high-value
    log groups, then run recommend_indexes_loggroup on specific log groups for full analysis.

    Returns per-log-group results showing:
        - recommendations: candidate fields to index, scored by frequency and filter usage
        - already_indexed: fields that already have indexes
    Results are sorted so log groups with the highest-scoring candidates appear first.
    """
    logs_client = get_aws_client('logs', region, profile_name)
    now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
    cutoff_epoch = now_epoch - (QUERY_HISTORY_DAYS * 86400)
    warnings: List[str] = []

    await ctx.info('Fetching account-wide query history...')
    try:
        # Cap queries to keep account-wide scan fast on high-volume accounts.
        # DescribeQueries returns most recent first, so we get the latest activity.
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

    # Group by log group
    by_lg: Dict[str, List[Dict]] = {}
    for q in recent:
        lg = q.get('logGroupName', '')
        if lg:
            by_lg.setdefault(lg, []).append(q)

    await ctx.info(f'Found queries across {len(by_lg)} log groups. Analyzing...')

    # Fetch account-level index policies once (not per log group)
    # Source: https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_DescribeAccountPolicies.html
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

    # Sort by highest recommendation score per log group
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
