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

"""CloudWatch Logs Insights query parser.

Parses CWLI, SQL, and PPL query strings to extract field names and classify usage.
Query language docs:
  - CWLI: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
  - SQL: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_SQL.html
  - PPL: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_PPL.html

Field usage classification:
  - filter_equality: fields in equality filters (field = val, field IN [...])
  - filter_non_equality: fields in non-equality filters (field like, field >, etc.)
  - display: fields in SELECT/fields/stats/sort (not filtered)
"""

import re
from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Field usage tracker
# ---------------------------------------------------------------------------
class FieldUsage:
    """Tracks how a field is used across queries."""

    def __init__(self):
        """Initialize field usage counters."""
        self.total_count: int = 0
        self.filter_equality_count: int = 0
        self.non_equality_filter_count: int = 0
        self.display_only_count: int = 0
        self.most_recent_use: float = 0.0
        self.unique_query_strings: Set[str] = set()


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
# CWLI/PPL patterns
_FILTER_EQUALITY_RE = re.compile(r'(?:filter|filterIndex)\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
_FILTER_AND_EQUALITY_RE = re.compile(r'(?:and|or)\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
_FILTER_IN_RE = re.compile(r'(?:filter|filterIndex)\s+(\w[\w.]*)\s+(?:in|IN)\s*\[', re.IGNORECASE)
_FILTER_NON_EQUALITY_RE = re.compile(
    r'filter\s+(\w[\w.]*)\s+(?:like|not\s+like|!=|<|>|<=|>=)', re.IGNORECASE
)
_FIELDS_RE = re.compile(r'fields\s+(.*?)(?:\||$)', re.IGNORECASE)
_STATS_BY_RE = re.compile(
    r'(?:stats|count|sum|avg|min|max|count_distinct|pct)\s*\(.*?\)\s*(?:as\s+\w+[\s,]*)?\s*by\s+(.*?)(?:\||$)',
    re.IGNORECASE,
)
_SORT_RE = re.compile(r'sort\s+(\w[\w.]*)', re.IGNORECASE)

# SQL patterns
_SQL_WHERE_EQUALITY_RE = re.compile(
    r'[`]?(\w[\w.]*)[`]?\s*=\s*(?:\'[^\']*\'|"[^"]*"|\d+)', re.IGNORECASE
)
_SQL_WHERE_IN_RE = re.compile(r'[`]?(\w[\w.]*)[`]?\s+IN\s*\(', re.IGNORECASE)
_SQL_WHERE_NON_EQ_RE = re.compile(
    r'[`]?(\w[\w.]*)[`]?\s+(?:LIKE|NOT\s+LIKE|!=|<>)\s', re.IGNORECASE
)
_SQL_SELECT_RE = re.compile(r'SELECT\s+(.*?)\s+FROM\b', re.IGNORECASE | re.DOTALL)
_SQL_GROUP_BY_RE = re.compile(
    r'GROUP\s+BY\s+(.*?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|$)', re.IGNORECASE
)
_SQL_ORDER_BY_RE = re.compile(r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)', re.IGNORECASE)
_SQL_FILTERINDEX_RE = re.compile(r"filterIndex\s*\(\s*'(\w[\w.]*)'\s*=\s*", re.IGNORECASE)

# PPL patterns
_PPL_WHERE_EQUALITY_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s*=\s*', re.IGNORECASE)
_PPL_WHERE_IN_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s+IN\s*\[', re.IGNORECASE)
_PPL_WHERE_NON_EQ_RE = re.compile(r'\bwhere\s+(\w[\w.]*)\s+(?:like|!=|<|>|<=|>=)', re.IGNORECASE)

# Reserved keywords per language
_RESERVED_KEYWORDS = {
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


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
def _strip_comments(query_string: str) -> str:
    """Strip inline comments (CWLI #, SQL -- and /* */)."""
    cleaned = re.sub(r'/\*.*?\*/', '', query_string, flags=re.DOTALL)
    cleaned = re.sub(r'--[^\n]*', '', cleaned)
    cleaned = re.sub(r'#[^\n]*', '', cleaned)
    return cleaned


def _strip_values(query_string: str) -> str:
    """Strip quoted strings, regex patterns, and comments to avoid false field matches."""
    cleaned = _strip_comments(query_string)
    cleaned = re.sub(r'/[^/]*/', '""', cleaned)
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cleaned)
    cleaned = re.sub(r"'(?:[^'\\]|\\.)*'", '""', cleaned)
    return cleaned


def _extract_field_names(text: str, language: str = 'cwli') -> List[str]:
    """Extract field names from a comma-separated field list, ignoring functions and keywords."""
    reserved = _RESERVED_KEYWORDS.get(language.lower(), _RESERVED_KEYWORDS['cwli'])
    cleaned = re.sub(r'\bas\s+\w[\w.]*', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'`(\w[\w.]*)`', r'\1', cleaned)
    names = re.findall(r'@[\w.]+|\b(\w[\w.]*)\b', cleaned)
    func_names = {
        m.group(1).lower() for m in re.finditer(r'\b(\w[\w.]*)\s*\(', cleaned, re.IGNORECASE)
    }
    return [
        n
        for n in names
        if n and n.lower() not in reserved and not n[0].isdigit() and n.lower() not in func_names
    ]


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
def detect_language(query_string: str) -> str:
    """Detect query language: 'sql', 'ppl', or 'cwli'."""
    if not query_string:
        return 'cwli'
    stripped = query_string.strip()
    if re.match(r'\s*SELECT\b', stripped, re.IGNORECASE):
        return 'sql'
    if re.match(r'\s*SOURCE\b', stripped, re.IGNORECASE):
        if re.search(r'\|\s*where\b', stripped, re.IGNORECASE):
            return 'ppl'
    if re.search(r'\|\s*where\b', stripped, re.IGNORECASE) and not re.search(
        r'\|\s*filter\b', stripped, re.IGNORECASE
    ):
        return 'ppl'
    return 'cwli'


# ---------------------------------------------------------------------------
# Per-language parsers
# ---------------------------------------------------------------------------
def _parse_sql_fields(query_string: str) -> Dict[str, str]:
    """Parse a SQL query string and return {field_name: usage_type}."""
    fields: Dict[str, str] = {}
    for m in _SQL_FILTERINDEX_RE.finditer(query_string):
        fields[m.group(1)] = 'filter_equality'
    cleaned = _strip_values(query_string)
    where_match = re.search(
        r'\bWHERE\b(.*?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', cleaned, re.IGNORECASE | re.DOTALL
    )
    if where_match:
        wc = where_match.group(1)
        for m in _SQL_WHERE_EQUALITY_RE.finditer(wc):
            fields[m.group(1)] = 'filter_equality'
        for m in _SQL_WHERE_IN_RE.finditer(wc):
            fields[m.group(1)] = 'filter_equality'
        for m in _SQL_WHERE_NON_EQ_RE.finditer(wc):
            if m.group(1) not in fields:
                fields[m.group(1)] = 'filter_non_equality'
    for m in _SQL_SELECT_RE.finditer(cleaned):
        if m.group(1).strip() != '*':
            for name in _extract_field_names(m.group(1), 'sql'):
                if name not in fields:
                    fields[name] = 'display'
    for m in _SQL_GROUP_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'sql'):
            if name not in fields:
                fields[name] = 'display'
    for m in _SQL_ORDER_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'sql'):
            if name not in fields:
                fields[name] = 'display'
    return fields


def _parse_ppl_fields(query_string: str) -> Dict[str, str]:
    """Parse a PPL query string and return {field_name: usage_type}."""
    fields: Dict[str, str] = {}
    cleaned = _strip_values(query_string)
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
    for m in _FIELDS_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'ppl'):
            if name not in fields:
                fields[name] = 'display'
    for m in _STATS_BY_RE.finditer(cleaned):
        for name in _extract_field_names(m.group(1), 'ppl'):
            if name not in fields:
                fields[name] = 'display'
    for m in _SORT_RE.finditer(cleaned):
        if m.group(1) not in fields:
            fields[m.group(1)] = 'display'
    return fields


def _parse_cwli_fields(query_string: str) -> Dict[str, str]:
    """Parse a CWLI query string and return {field_name: usage_type}."""
    fields: Dict[str, str] = {}
    cleaned = re.sub(r'\bparse\b.*?\bas\b[^|]*', '', query_string, flags=re.IGNORECASE)
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
# Public API
# ---------------------------------------------------------------------------
def parse_query_fields(query_string: str, language: Optional[str] = None) -> Dict[str, str]:
    """Parse a CWLI, SQL, or PPL query string and return {field_name: usage_type}.

    Args:
        query_string: The query string to parse
        language: Optional language hint ('CWLI', 'SQL', 'PPL'). Auto-detects if not provided.

    Returns:
        Dict mapping field names to usage_type ('filter_equality', 'filter_non_equality', 'display')
    """
    if not query_string:
        return {}
    lang = language.lower() if language else detect_language(query_string)
    if lang == 'sql':
        return _parse_sql_fields(query_string)
    if lang == 'ppl':
        return _parse_ppl_fields(query_string)
    return _parse_cwli_fields(query_string)
