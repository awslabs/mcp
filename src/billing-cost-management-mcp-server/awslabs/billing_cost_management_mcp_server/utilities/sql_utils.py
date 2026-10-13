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

"""SQL utilities for AWS Billing and Cost Management MCP Server.

This module provides utilities for working with SQLite databases,
including database connection management, table creation, and
converting large API responses to SQLite tables.

Security model:
- SQL injection prevention through table name validation (validate_table_name)
- Centralized SQL statement construction (create_safe_sql_statement)
- Parameter binding for all data values
- Query validation to prevent harmful operations
"""

import atexit
import json
import os
import re
import sqlite3
import uuid
from .constants import (
    COST_OPTIMIZATION_HUB_EFFICIENCY_METRICS_COLUMNS,
    COST_OPTIMIZATION_HUB_EFFICIENCY_ORDER_DIMENSION_TO_COLUMN,
    COST_OPTIMIZATION_HUB_ORDER_DIMENSION_TO_COLUMN,
    COST_OPTIMIZATION_HUB_RECOMMENDATION_COLUMNS,
    ColumnSpec,
)
from .logging_utils import get_context_logger, get_logger
from datetime import datetime
from fastmcp import Context
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Configure logger for this module
logger = get_logger(__name__)


# Constants for SQL conversion
SQL_CONVERSION_THRESHOLD = int(
    os.getenv('MCP_SQL_THRESHOLD', 25 * 1024)
)  # 25KB default (lowered from 50KB)
FORCE_SQL_CONVERSION = os.getenv('MCP_FORCE_SQL', 'false').lower() == 'true'
BUSY_TIMEOUT_MS = int(
    os.getenv('BCM_MCP_SQLITE_TIMEOUT_MS', 30000)
)  # 30s default — handles concurrent subagent writes

# Session database path singleton
_SESSION_DB_PATH = None


def should_convert_to_sql(response_size: int) -> bool:
    """Determine if response should be converted to SQL based on config.

    Converts responses larger than SQL_CONVERSION_THRESHOLD (default 25KB) to SQL
    to prevent context window overflow and improve performance.

    Args:
        response_size: Size of the response in bytes

    Returns:
        bool: True if the response should be converted to SQL

    Environment Variables:
        MCP_SQL_THRESHOLD: Override the default threshold (in bytes)
        MCP_FORCE_SQL: If 'true', always convert to SQL regardless of size
    """
    if FORCE_SQL_CONVERSION:
        return True
    return response_size > SQL_CONVERSION_THRESHOLD


def get_session_db_path() -> str:
    """Get the path to the session database.

    Creates the sessions directory if it doesn't exist.
    Registers a cleanup function to delete the database on exit.

    Returns:
        str: Path to the SQLite database file
    """
    global _SESSION_DB_PATH

    if _SESSION_DB_PATH is None:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())[:8]

        # Get the base directory for the session database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        session_dir = os.path.join(base_dir, 'sessions')

        # Create sessions directory if it doesn't exist
        os.makedirs(session_dir, exist_ok=True)

        # Set the database path
        _SESSION_DB_PATH = os.path.join(session_dir, f'session_{session_id}.db')

        # Register cleanup function
        atexit.register(cleanup_session_db)

    return _SESSION_DB_PATH


def cleanup_session_db() -> None:
    """Clean up the session database on exit."""
    global _SESSION_DB_PATH

    if _SESSION_DB_PATH and os.path.exists(_SESSION_DB_PATH):
        try:
            os.remove(_SESSION_DB_PATH)
            logger.debug(f'Removed session database: {_SESSION_DB_PATH}')
        except Exception as e:
            logger.warning(f'Failed to remove session database: {str(e)}')


def _session_authorizer(action, arg1, arg2, db_name, trigger_name):
    """SQLite authorizer callback: deny cross-DB attach/detach.

    Belt-and-suspenders with the regex blacklist in
    :func:`validate_sql_query`. The regex catches the query text
    before SQLite parses it; this authorizer catches every SQL parser
    action the connection actually attempts, including anything the
    regex filter might miss (comment tricks, whitespace variants,
    dynamic SQL from triggers, etc.).

    Any ATTACH/DETACH DATABASE attempt returns ``SQLITE_DENY``; every
    other action returns ``SQLITE_OK`` so the session tool retains
    full read/write access to its own database.
    """
    if action == sqlite3.SQLITE_ATTACH or action == sqlite3.SQLITE_DETACH:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def get_db_connection() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Get a connection to the session database.

    Creates the schema_info table if it doesn't exist.

    Returns:
        Tuple[sqlite3.Connection, sqlite3.Cursor]: Database connection and cursor
    """
    # Get database path
    db_path = get_session_db_path()

    # Create connection and cursor
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute(f'PRAGMA busy_timeout={BUSY_TIMEOUT_MS}')
    # Install the engine-level authorizer AFTER PRAGMA setup — the
    # authorizer denies ATTACH/DETACH but SQLITE_PRAGMA is separately
    # gated, so setup pragmas above still run. Every subsequent call
    # through this connection (including anything from the
    # session-sql tool) is guarded. See _session_authorizer.
    conn.set_authorizer(_session_authorizer)
    cursor = conn.cursor()

    # Create schema_info table to track created tables if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_info (
        table_name TEXT PRIMARY KEY,
        created_at TEXT,
        operation TEXT,
        query TEXT,
        row_count INTEGER
    )
    """)

    # Commit the changes
    conn.commit()

    return conn, cursor


def validate_table_name(table_name: str) -> bool:
    """Validate table name for SQL injection prevention.

    Args:
        table_name: Name of the table to validate

    Returns:
        bool: True if the table name is valid

    Raises:
        ValueError: If the table name contains invalid characters
    """
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise ValueError(
            f'Invalid table name: {table_name}. Table names must only contain letters, numbers, and underscores.'
        )
    return True


def create_safe_sql_statement(
    statement_type: str, table_name: str, *args, limit: Optional[int] = None
) -> str:
    """Create a SQL statement with validated table name.

    Args:
        statement_type: Type of SQL statement (CREATE, SELECT, INSERT, etc.)
        table_name: Name of the table (will be validated)
        *args: Additional SQL statement parts
        limit: Optional LIMIT clause value

    Returns:
        str: A safe SQL statement

    Raises:
        ValueError: If the table name is invalid
    """
    validate_table_name(table_name)

    if statement_type.upper() == 'CREATE':
        return f'CREATE TABLE {table_name} ({", ".join(args)})'
    elif statement_type.upper() == 'SELECT':
        base_sql = f'SELECT {", ".join(args)} FROM {table_name}'
        if limit is not None and isinstance(limit, int) and limit > 0:
            base_sql += f' LIMIT {limit}'
        return base_sql
    elif statement_type.upper() == 'INSERT':
        return f'INSERT INTO {table_name} {args[0]}'
    else:
        return f'{statement_type} {table_name} {" ".join(args)}'


def create_table(cursor: sqlite3.Cursor, table_name: str, schema: List[str]) -> None:
    """Create a table with the specified schema.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table to create
        schema: List of column definitions (e.g., ["id INTEGER", "name TEXT"])

    Raises:
        ValueError: If the table name contains invalid characters
    """
    # Validate table name for SQL injection prevention
    validate_table_name(table_name)

    # Create a safe SQL statement
    sql = create_safe_sql_statement('CREATE', table_name, *schema)

    # Execute the safe SQL statement
    cursor.execute(sql)


def insert_data(cursor: sqlite3.Cursor, table_name: str, data: Optional[List[List[Any]]]) -> int:
    """Insert data into a table.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table
        data: List of rows to insert

    Returns:
        int: Number of rows inserted

    Raises:
        ValueError: If the table name contains invalid characters
    """
    if not data or not data[0]:
        return 0

    # Validate table name for SQL injection prevention
    validate_table_name(table_name)

    # Create placeholders for prepared statement
    placeholders = ', '.join(['?' for _ in range(len(data[0]))])
    # Build the query safely
    insert_sql = create_safe_sql_statement('INSERT', table_name, f'VALUES ({placeholders})')

    # Insert data
    for row in data:
        cursor.execute(insert_sql, row)

    return len(data)


def register_table_in_schema_info(
    cursor: sqlite3.Cursor, table_name: str, operation: str, query: str, row_count: int
) -> None:
    """Register a table in the schema_info table.

    Args:
        cursor: SQLite cursor
        table_name: Name of the table
        operation: Operation that created the table
        query: Query used to create the table
        row_count: Number of rows in the table
    """
    now = datetime.now().isoformat()

    cursor.execute(
        'INSERT OR REPLACE INTO schema_info VALUES (?, ?, ?, ?, ?)',
        (table_name, now, operation, query, row_count),
    )


def validate_sql_query(query: str) -> bool:
    """Validate SQL query for security issues.

    Args:
        query: SQL query to validate

    Returns:
        bool: True if the query is valid

    Raises:
        ValueError: If the query contains potentially harmful operations
    """
    dangerous_patterns = [
        r'\bDROP\b.*\bTABLE\b',
        r'\bDELETE\b.*\bFROM\b',
        r'\bTRUNCATE\b.*\bTABLE\b',
        r'\bALTER\b.*\bTABLE\b',
        # ATTACH / DETACH must NOT be allowed on the session
        # connection. ATTACH DATABASE lets a caller mount any SQLite
        # file readable by the process (browser cookie stores,
        # credential DBs, other files under the same user) as an
        # alias inside the session, and then read its contents back
        # via SELECT. The engine-level `set_authorizer` on the
        # session connection is the primary defense; this regex is
        # the first-line filter that gives callers a clear error
        # message.
        r'\bATTACH\b',
        r'\bDETACH\b',
        r'\bEXEC\b',
        r'\bSYSTEM\b',
        r';.*\b',
    ]

    query_upper = query.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper, re.IGNORECASE):
            raise ValueError(f'Query contains potentially harmful operations: {query}')

    return True


def execute_query(cursor: sqlite3.Cursor, query: str) -> Tuple[List[str], List[Tuple]]:
    """Execute a SQL query.

    Args:
        cursor: SQLite cursor
        query: SQL query to execute

    Returns:
        Tuple[List[str], List[Tuple]]: Column names and rows

    Raises:
        ValueError: If the query contains potentially harmful operations
    """
    # Validate query for security issues
    validate_sql_query(query)
    cursor.execute(query)

    # Get column names
    column_names = (
        [description[0] for description in cursor.description] if cursor.description else []
    )

    # Get rows
    rows = cursor.fetchall()

    return column_names, rows


def _get_specialized_converter(operation_name: str) -> Optional[str]:
    """Get specific converter function for API.

    Args:
        operation_name: Name of the API operation. MUST match the string the
            caller passes to ``convert_api_response_to_table`` /
            ``convert_response_if_needed`` (e.g. ``cost_explorer_get_cost_and_usage``).

    Returns:
        Optional[str]: Type of specialized converter to use, or None for generic
    """
    # Keys must match operation_name strings the callers pass; mismatches
    # silently fall through to the generic (key, value) flatten branch.
    converters = {
        'cost_explorer_get_cost_and_usage': 'cost_and_usage',
        'cost_explorer_get_cost_and_usage_with_resources': 'cost_and_usage',
        'cost_explorer_get_dimension_values': 'dimension_values',
        'cost_explorer_get_cost_forecast': 'forecast',
        'cost_explorer_get_usage_forecast': 'forecast',
        'cost_explorer_get_tags': 'tags',
        'cost_explorer_get_cost_categories': 'cost_categories',
        'aws_pricing_get_products': 'pricing_products',
        'cost_optimization_hub_list_recommendations': 'coh_recommendations',
        'cost_optimization_hub_list_efficiency_metrics': 'coh_efficiency_metrics',
        'budget_actions': 'records',
        'budget_notifications': 'records',
        'sp_explorer_describe_savings_plans': 'records',
        'sp_explorer_describe_savings_plan_rates': 'records',
        'sp_explorer_describe_savings_plans_offerings': 'records',
        'sp_explorer_describe_savings_plans_offering_rates': 'records',
        # Nested-list operations, keyed by the bare `operation` argument the
        # offload middleware passes as operation_name (confirmed with garyga,
        # AIC-2524). See the PR / AIC-2532 for the full middleware contract.
        'get_reservation_coverage': 'ri_coverage',
        'get_reservation_utilization': 'ri_utilization',
        'get_commitment_purchase_analysis': 'sp_lookback_metrics',
        'get_savings_plan_purchase_recommendation_details': 'sp_lookback_metrics',
        'get_savings_plans_purchase_recommendation': 'sp_purchase_recommendation',
        # storage-lens has no `operation` arg; the middleware passes this
        # underscore name for it (must be a valid SQL identifier, since
        # table_name is f'{operation_name}_{id}').
        'storage_lens_run_query': 'storage_lens_query',
    }

    if operation_name in converters:
        return converters[operation_name]

    # Compute Optimizer Automation list operations all return a uniform
    # {<list_key>: [...], count, next_token} shape; store one row per item so
    # the offloaded data stays queryable instead of a single JSON blob.
    if operation_name.startswith('compute_optimizer_automation_'):
        return 'records'

    # Credits operations return {<list_key>: [...]} plus sibling metadata blocks;
    # store one row per item so an offloaded credit ledger stays aggregatable.
    if operation_name.startswith('credits_get_'):
        return 'records'

    # Billing preference operations return {billing_preferences: [...]}.
    # One row per preference keeps an offloaded organization
    # filterable by account and value
    if operation_name.startswith('billing_preferences_'):
        return 'records'

    # BVS segment operations return {segments: [...]}.
    # One row per segment keeps an offloaded result filterable by domain
    # and account.
    if operation_name.startswith('bvs_list_billing_view_segments'):
        return 'records'

    return None


def _extract_record_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull the item list out of a {<list_key>: [...], count, next_token} response.

    Returns the first list-valued field (the item collection), ignoring the
    scalar pagination fields (`count`, `next_token`). Returns an empty list if
    the response carries no list field.

    Args:
        response: A uniform list response.

    Returns:
        The list of item dicts, or an empty list.
    """
    for value in response.values():
        if isinstance(value, list):
            return value
    return []


def _record_column_map(items: List[Any]) -> Dict[str, str]:
    """Map each distinct item key to a unique SQLite column name.

    Keys are visited in first-seen order. SQLite column names are
    case-insensitive, so a key that differs from an earlier one only by case
    (``'Bucket'`` then ``'bucket'``) gets a suffixed column (``bucket_2``)
    instead of colliding in CREATE TABLE or being merged into the first
    spelling's column — which would silently store the second key's values as
    NULL. Every distinct key therefore keeps its own column and its values.

    Args:
        items: The list of items to store.

    Returns:
        Ordered ``{original_key: column_name}``; empty if no dict items.

    Raises:
        ValueError: If an item key is not a safe SQL identifier.
    """
    key_to_col: Dict[str, str] = {}
    used_lower: set = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key in key_to_col:
                continue
            _validate_column_name(key)
            candidate = key
            suffix = 1
            while candidate.lower() in used_lower:
                suffix += 1
                candidate = f'{key}_{suffix}'
            used_lower.add(candidate.lower())
            key_to_col[key] = candidate
    return key_to_col


def _validate_column_name(name: Any) -> str:
    """Validate a value is a safe SQL column identifier and return it.

    Column names are interpolated into CREATE/INSERT SQL, so each must match
    ``^[a-zA-Z0-9_]+$`` (same model as ``validate_table_name``). Shared by
    ``_record_column_map`` and ``_create_and_insert_dict_rows`` so the injection
    check lives in one place.

    Args:
        name: Candidate column name.

    Returns:
        The name unchanged when valid.

    Raises:
        ValueError: If the name is not a safe SQL identifier.
    """
    if not isinstance(name, str) or not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError(f'Invalid column name for SQL table: {name!r}')
    return name


def _response_summary(response: Dict[str, Any]) -> Dict[str, Any]:
    """Headline scalar fields of a nested-series response, for the offload envelope.

    The nested-series converters store the big list(s) as table rows; this
    captures everything else — the single-value headline numbers these APIs exist
    to return (``EstimatedSavingsAmount``, ``EstimatedROI``, coverage/utilization
    totals and percentages, ``PaymentOption``, ``TermInYears``, ...) — so they
    survive offload inline rather than being dropped. Lists are omitted, so the
    summary stays small regardless of series size. boto3's ``ResponseMetadata``
    (request id, HTTP headers, retry count) is transport noise, not data, and is
    excluded.

    Args:
        response: The (inner data) response being offloaded.

    Returns:
        A flat dict of scalar headline values.
    """
    return _flatten_scalars(
        {k: v for k, v in response.items() if k != 'ResponseMetadata'}, drop_lists=True
    )


# ---------------------------------------------------------------------------
# Column-spec driven inserts
#
# A `ColumnSpec` declares one SQLite column as ``(name, sqlite_type)``. With a
# list of specs, `_create_and_insert` builds the CREATE TABLE schema, the
# INSERT column list, and the parameter binding order in one pass — so each
# column is declared exactly once instead of being repeated across the schema,
# the INSERT column list, the placeholder count, and the values tuple.
#
# Coercion is driven by ``sqlite_type``: REAL values go through ``float()`` so
# Decimal-typed values from boto3 (which sqlite3 cannot bind natively) become
# proper REAL columns. TEXT/INTEGER/BOOLEAN pass through — SQLite's type
# affinity handles those.
# ---------------------------------------------------------------------------


def _coerce_for_column(value: Any, sqlite_type: str) -> Any:
    """Coerce a value for binding into a SQLite column of ``sqlite_type``.

    Only REAL needs active coercion: boto3 occasionally returns ``Decimal``
    instances for float fields, and ``sqlite3`` raises ``InterfaceError`` when
    asked to bind a ``Decimal``. Everything else is left to SQLite's dynamic
    type system.

    Args:
        value: Raw value from a record dict (may be ``None``).
        sqlite_type: Declared column type (``TEXT``, ``REAL``, ``INTEGER``, ...).

    Returns:
        A bind-safe value: ``None``, a float for REAL columns, or the value
        unchanged.
    """
    if value is None:
        return None
    if sqlite_type == 'REAL':
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return value


def _create_and_insert(
    cursor: sqlite3.Cursor,
    table_name: str,
    columns: List[ColumnSpec],
    records: Iterable[Dict[str, Any]],
) -> int:
    """Create a table from a column spec and insert records using ``rec.get(name)``.

    Args:
        cursor: SQLite cursor used to execute CREATE TABLE and INSERTs.
        table_name: Validated table name; injection-checked by
            ``create_safe_sql_statement``.
        columns: Ordered list of ``(column_name, sqlite_type)`` specs. The
            schema, INSERT column list, placeholder count, and value tuple are
            all derived from this list, so each column appears once. Column
            names must match the record dict's keys.
        records: Iterable of record dicts. Each column's value is read via
            ``rec.get(column_name)`` and coerced per its ``sqlite_type``.

    Returns:
        Number of rows inserted.
    """
    schema = [f'{name} {sqlite_type}' for name, sqlite_type in columns]
    cursor.execute(create_safe_sql_statement('CREATE', table_name, *schema))

    col_list = ', '.join(name for name, _ in columns)
    placeholders = ', '.join('?' for _ in columns)
    insert_sql = create_safe_sql_statement(
        'INSERT', table_name, f'({col_list}) VALUES ({placeholders})'
    )

    count = 0
    for rec in records:
        values = tuple(
            _coerce_for_column(rec.get(name), sqlite_type) for name, sqlite_type in columns
        )
        cursor.execute(insert_sql, values)
        count += 1
    return count


def _sanitize_identifier(name: str) -> str:
    """Coerce an arbitrary label into a safe SQL identifier.

    Replaces every character outside ``[A-Za-z0-9_]`` with ``_`` and prefixes
    the result when it does not start with a letter or underscore. Used for
    column labels that are not under our control — notably Athena result column
    labels from storage-lens ``run_query`` (e.g. ``SUM(storage_bytes)`` or
    ``bucket.name``), which would otherwise be rejected by the identifier
    validation that protects the CREATE/INSERT SQL.

    Args:
        name: Raw label.

    Returns:
        A string matching ``^[A-Za-z_][A-Za-z0-9_]*$``.
    """
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # All-unsafe input (e.g. '()' -> '__') has no alphanumeric character; fall
    # back to a readable default rather than an all-underscore column name.
    if not re.search(r'[a-zA-Z0-9]', safe):
        return 'col'
    if not re.match(r'^[a-zA-Z_]', safe):
        safe = f'col_{safe}'
    return safe


def _flatten_scalars(
    obj: Dict[str, Any], parent_key: str = '', sep: str = '_', *, drop_lists: bool = False
) -> Dict[str, Any]:
    """Flatten a nested dict into a single-level ``{flat_key: scalar}`` map.

    Nested dicts are recursed with their key path joined by ``sep`` (so
    ``{'coverage_hours': {'reserved_hours': 1}}`` becomes
    ``{'coverage_hours_reserved_hours': 1}``) and scalars pass through. Lists
    are stored as JSON strings, or omitted entirely when ``drop_lists`` is set.
    This is the single flatten implementation shared by the nested-series
    converters (row building), the offload ``summary`` (``drop_lists=True``),
    and the generic key/value fallback.

    Args:
        obj: The dict to flatten.
        parent_key: Prefix for recursion (callers pass '').
        sep: Separator between key path segments.
        drop_lists: Omit list-valued leaves instead of JSON-encoding them.

    Returns:
        A flat dict of scalar (or JSON-string) values.
    """
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else str(k)
        if isinstance(v, dict):
            out.update(_flatten_scalars(v, new_key, sep=sep, drop_lists=drop_lists))
        elif isinstance(v, list):
            if not drop_lists:
                out[new_key] = json.dumps(v)
        else:
            out[new_key] = v
    return out


def _find_nested_list(obj: Any, target_key: str) -> List[Any]:
    """Depth-first search for the first list stored under ``target_key``.

    The hourly ``MetricsOverLookbackPeriod`` series lives at different parent
    paths across operations (under ``RecommendationDetailData`` for SP
    recommendation details, under ``AnalysisDetails.SavingsPlansPurchaseAnalysisDetails``
    for commitment purchase analysis). Searching by key name rather than a fixed
    path handles both shapes and is resilient to upstream re-nesting.

    Args:
        obj: Response fragment to search (dict, list, or scalar).
        target_key: The dict key whose list value we want.

    Returns:
        The first list found under ``target_key``, or an empty list.
    """
    if isinstance(obj, dict):
        value = obj.get(target_key)
        if isinstance(value, list):
            return value
        for v in obj.values():
            found = _find_nested_list(v, target_key)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_nested_list(item, target_key)
            if found:
                return found
    return []


def _create_and_insert_dict_rows(
    cursor: sqlite3.Cursor,
    table_name: str,
    rows: List[Any],
    columns: Optional[List[str]] = None,
) -> int:
    """Create a TEXT table from already-shaped row dicts and insert them.

    Generalizes the ``records`` converter for the nested-series converters:
    given a list of flat row dicts, derive the column set (union of keys in
    first-seen order) or use an explicit ordered ``columns`` list, create a TEXT
    table, and insert one row per dict. Nested dict/list values are stored as
    JSON strings (queryable via SQLite ``json_extract``). SQLite's dynamic
    typing lets numeric strings in TEXT columns aggregate normally (``SUM``,
    ``AVG``), matching the existing ``records`` converter.

    Column names are validated as safe SQL identifiers and double-quoted so
    reserved words (``order``, ``group``) are legal and injection is prevented.
    Callers passing externally-sourced labels (e.g. Athena columns) must
    sanitize them with ``_sanitize_identifier`` first.

    Args:
        cursor: SQLite cursor.
        table_name: Validated table name.
        rows: Row dicts to store. A non-dict row is stored under a single
            ``value`` column.
        columns: Optional explicit ordered column list; derived from ``rows``
            when omitted or empty.

    Returns:
        Number of rows inserted.

    Raises:
        ValueError: If a column name is not a safe SQL identifier.
    """
    if not columns:
        # Derived columns: each distinct key keeps its own column (case variants
        # are suffixed), and values are read by ORIGINAL key so none are dropped.
        key_to_col = _record_column_map(rows) or {'value': 'value'}
    else:
        # Explicit columns are already-shaped row keys. A case-insensitive
        # duplicate would collide in CREATE TABLE; fail loudly (convert then
        # returns the raw response) rather than silently dropping a column.
        key_to_col = {}
        seen_lower: set = set()
        for col in columns:
            _validate_column_name(col)
            if col.lower() in seen_lower:
                raise ValueError(f'Duplicate column name (case-insensitive): {col!r}')
            seen_lower.add(col.lower())
            key_to_col[col] = col

    keys = list(key_to_col.keys())
    quoted_columns = [f'"{key_to_col[k]}"' for k in keys]
    schema = [f'{col} TEXT' for col in quoted_columns]
    cursor.execute(create_safe_sql_statement('CREATE', table_name, *schema))

    validate_table_name(table_name)
    column_list = ', '.join(quoted_columns)
    placeholders = ', '.join('?' for _ in keys)
    insert_sql = create_safe_sql_statement(
        'INSERT', table_name, f'({column_list}) VALUES ({placeholders})'
    )

    count = 0
    for row in rows:
        src = row if isinstance(row, dict) else {'value': row}
        values = []
        for key in keys:
            raw = src.get(key)
            values.append(json.dumps(raw) if isinstance(raw, (dict, list)) else raw)
        cursor.execute(insert_sql, values)
        count += 1
    return count


def _ri_series_rows(
    response: Dict[str, Any], series_key: str, metric_key: str
) -> List[Dict[str, Any]]:
    """Denormalize an RI coverage/utilization response into one row per group.

    Walks the ``<series_key>`` time buckets (``coverages_by_time`` or
    ``utilizations_by_time``) and emits one flat row per (time period, group),
    carrying the group's ``attributes`` (prefixed ``attr_``) and its flattened
    ``<metric_key>`` metrics. Whenever a bucket has groups, its bucket-level
    ``total`` is ALSO emitted as a ``level='total'`` row, because coverage and
    utilization percentages cannot be rebuilt by summing the group rows. A bucket
    with no groups emits only its ``total`` row so empty periods survive offload
    rather than vanishing — mirroring the ``coh_efficiency_metrics`` no-data
    handling.

    Args:
        response: The formatted RI response.
        series_key: ``coverages_by_time`` or ``utilizations_by_time``.
        metric_key: ``coverage`` or ``utilization`` (the per-group metric block).

    Returns:
        Flat row dicts ready for ``_create_and_insert_dict_rows``.
    """
    rows: List[Dict[str, Any]] = []
    for bucket in response.get(series_key, []):
        if not isinstance(bucket, dict):
            continue
        time_period = bucket.get('time_period') or {}
        start = time_period.get('start')
        end = time_period.get('end')
        groups = bucket.get('groups') or []
        if groups:
            for group in groups:
                if not isinstance(group, dict):
                    continue
                row: Dict[str, Any] = {
                    'time_period_start': start,
                    'time_period_end': end,
                    'level': 'group',
                }
                for attr_key, attr_val in (group.get('attributes') or {}).items():
                    row[f'attr_{attr_key}'] = attr_val
                row.update(_flatten_scalars(group.get(metric_key) or {}))
                rows.append(row)
            # Preserve the per-bucket total alongside the groups — its
            # percentages are not derivable by summing the group rows.
            bucket_total = bucket.get('total') or {}
            if bucket_total:
                total_row: Dict[str, Any] = {
                    'time_period_start': start,
                    'time_period_end': end,
                    'level': 'total',
                }
                total_row.update(_flatten_scalars(bucket_total))
                rows.append(total_row)
        else:
            row = {'time_period_start': start, 'time_period_end': end, 'level': 'total'}
            row.update(_flatten_scalars(bucket.get('total') or {}))
            rows.append(row)
    return rows


def _derive_pagination_envelope(
    response: Dict[str, Any], token_key: str = 'NextPageToken'
) -> Dict[str, Any]:
    """Extract pagination metadata from a response so it survives SQL offload.

    Recognizes two shapes produced upstream:

    - Multi-page wrapper built by callers after `paginate_aws_response`:
      ``{'<ResultsKey>': [...], 'Pagination': {next_token, has_more, pages_fetched, ...}}``
    - Single-page raw boto3 response with a continuation-token field (e.g.
      ``NextPageToken``).

    Args:
        response: The API response (or paginated wrapper) being offloaded.
        token_key: Name of the continuation-token field in the single-page
            boto3 response. Defaults to ``NextPageToken`` (used by Cost
            Explorer ops); pass e.g. ``NextToken`` for AWS Pricing.

    Returns:
        Dict with ``next_page_token``, ``has_more``, ``pages_fetched`` keys.
        Empty dict if the response carries no pagination markers (e.g. a
        forecast response), so unrelated APIs aren't polluted with bogus
        pagination metadata.
    """
    if 'Pagination' in response and isinstance(response['Pagination'], dict):
        pag_meta = response['Pagination']
        return {
            'next_page_token': pag_meta.get('next_token'),
            'has_more': pag_meta.get('has_more', False),
            'pages_fetched': pag_meta.get('pages_fetched'),
        }
    if token_key in response:
        token = response.get(token_key)
        return {
            'next_page_token': token,
            'has_more': bool(token),
            'pages_fetched': 1,
        }
    return {}


async def convert_response_if_needed(
    ctx: Context,
    response: Dict[str, Any],
    api_name: str,
    pagination_token_key: str = 'NextPageToken',
    **metadata,
) -> Dict[str, Any]:
    """Offload an API response to SQL if it exceeds the size threshold.

    Auto-derives pagination metadata (`next_page_token`, `has_more`,
    `pages_fetched`) from the response shape so callers don't have to
    pass it explicitly. Explicit kwargs in `metadata` override the
    derived values.

    Return contract — always returns something the caller can pass
    straight through to `format_response`:
    - Offload happened: the offload sentinel dict (with `data_stored=True`,
      `table_name`, sample queries, etc.).
    - No offload (size below threshold): the original `response`.
    - Conversion errored: log + return the original `response`.

    The original response is returned on no-offload and on error so
    callers don't need to unwrap a size-meta or error envelope.

    Args:
        ctx: MCP context
        response: API response data
        api_name: Name of the API operation (e.g. 'aws_pricing_get_products')
        pagination_token_key: Name of the continuation-token field in
            single-page boto3 responses. Defaults to 'NextPageToken'.
        **metadata: Additional metadata to include in the offload sentinel.

    Returns:
        Either the offload sentinel dict or the original response.
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    # Pull pagination markers out of the response so they survive offload —
    # caller-provided metadata still wins on key conflict.
    metadata = {**_derive_pagination_envelope(response, pagination_token_key), **metadata}

    try:
        response_size = len(json.dumps(response).encode('utf-8'))

        if not should_convert_to_sql(response_size):
            await ctx_logger.debug(
                f'Response size {response_size / 1024:.2f}KB below threshold, returning directly'
            )
            return response

        await ctx_logger.info(
            f'Response size {response_size / 1024:.2f}KB exceeds threshold, converting to SQL'
        )
        return await convert_api_response_to_table(ctx, response, api_name, **metadata)
    except Exception as e:
        # Offload is an optimization — if it fails, fall back to the original
        # response rather than propagating an error envelope the caller would
        # have to unwrap anyway.
        await ctx_logger.error(
            f'Error processing response for {api_name}: {str(e)}', exc_info=True
        )
        return response


async def convert_api_response_to_table(
    ctx: Context, response: Dict[str, Any], operation_name: str, **metadata
) -> Dict[str, Any]:
    """Convert a large API response to a SQLite table.

    This function stores API response data in a SQLite table for easier querying
    with the session_sql tool.

    Args:
        ctx: MCP context
        response: API response to convert
        operation_name: Name of the operation (used for table name prefix)
        **metadata: Additional metadata to store with the table

    Returns:
        Dict[str, Any]: Response with information about the created table
    """
    await ctx.info(
        f'Response size: {len(json.dumps(response).encode("utf-8")) / 1024:.1f}KB - Converting to SQL table'
    )

    # Get converter for specific API type
    converter_type = _get_specialized_converter(operation_name)

    # Pull the caller's requested ordering out of metadata (if any) so it can
    # drive a matching sample query, without leaking the raw dict into the
    # returned payload's metadata spread.
    requested_order_by = metadata.pop('order_by', None)

    # Generate a unique table name
    table_id = str(uuid.uuid4())[:8]
    table_name = f'{operation_name}_{table_id}'

    # Get database connection
    conn, cursor = get_db_connection()

    try:
        rows_inserted = 0
        # Headline scalar fields for the nested-series converters, surfaced
        # inline in the offload envelope so threshold-0 offload does not drop the
        # top-level numbers these APIs return. None for all other converters.
        summary_data: Optional[Dict[str, Any]] = None

        # Create table and insert data based on response type
        if converter_type == 'pricing_products' and 'PriceList' in response:
            # AWS Pricing API response
            schema = [
                'service_code TEXT',
                'product_family TEXT',
                'sku TEXT',
                'attributes TEXT',
                'pricing_terms TEXT',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Insert pricing data
            price_list = response.get('PriceList', [])
            for product_json in price_list:
                product = json.loads(product_json)

                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT',
                    table_name,
                    '(service_code, product_family, sku, attributes, pricing_terms) VALUES (?, ?, ?, ?, ?)',
                )
                cursor.execute(
                    insert_sql,
                    (
                        metadata.get('service_code', ''),
                        product.get('product', {}).get('productFamily'),
                        product.get('product', {}).get('sku'),
                        json.dumps(product.get('product', {}).get('attributes', {})),
                        json.dumps(product.get('terms', {})),
                    ),
                )
                rows_inserted += 1

        elif converter_type == 'cost_and_usage' and 'ResultsByTime' in response:
            # Cost Explorer GetCostAndUsage response
            schema = [
                'time_period_start TEXT',
                'time_period_end TEXT',
                'estimated BOOLEAN',
                'group_key_1 TEXT',
                'group_key_2 TEXT',
                'group_key_3 TEXT',
                'metric_name TEXT',
                'amount REAL',
                'unit TEXT',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for result_by_time in response.get('ResultsByTime', []):
                time_period = result_by_time.get('TimePeriod', {})
                start = time_period.get('Start')
                end = time_period.get('End')
                estimated = result_by_time.get('Estimated', False)

                # Handle grouped data
                for group in result_by_time.get('Groups', []):
                    keys = group.get('Keys', [])
                    padded_keys = (keys + [None, None, None])[:3]

                    for metric_name, metric_data in group.get('Metrics', {}).items():
                        # Use validated table name
                        validate_table_name(table_name)
                        insert_sql = create_safe_sql_statement(
                            'INSERT',
                            table_name,
                            '(time_period_start, time_period_end, estimated, group_key_1, group_key_2, group_key_3, metric_name, amount, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        )
                        cursor.execute(
                            insert_sql,
                            (
                                start,
                                end,
                                estimated,
                                padded_keys[0],
                                padded_keys[1],
                                padded_keys[2],
                                metric_name,
                                float(metric_data.get('Amount', 0)),
                                metric_data.get('Unit'),
                            ),
                        )
                        rows_inserted += 1

                # Handle total data
                for metric_name, metric_data in result_by_time.get('Total', {}).items():
                    # Use validated table name
                    validate_table_name(table_name)
                    insert_sql = create_safe_sql_statement(
                        'INSERT',
                        table_name,
                        '(time_period_start, time_period_end, estimated, group_key_1, group_key_2, group_key_3, metric_name, amount, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    )
                    cursor.execute(
                        insert_sql,
                        (
                            start,
                            end,
                            estimated,
                            None,
                            None,
                            None,
                            metric_name,
                            float(metric_data.get('Amount', 0)),
                            metric_data.get('Unit'),
                        ),
                    )
                    rows_inserted += 1

        elif converter_type == 'dimension_values' and 'DimensionValues' in response:
            # Cost Explorer GetDimensionValues response
            schema = ['value TEXT', 'attributes TEXT']
            # We use create_safe_sql_statement which validates table_name to prevent SQL injection
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            # nosem: python.lang.security.audit.formatted-sql-query.formatted-sql-query
            # nosem: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(sql)

            for dim_value in response.get('DimensionValues', []):
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(value, attributes) VALUES (?, ?)'
                )
                cursor.execute(
                    insert_sql,
                    (dim_value.get('Value'), json.dumps(dim_value.get('Attributes', {}))),
                )
                rows_inserted += 1

        elif converter_type == 'forecast' and 'ForecastResultsByTime' in response:
            # Cost Explorer forecast responses
            schema = [
                'time_period_start TEXT',
                'time_period_end TEXT',
                'mean_value REAL',
                'lower_bound REAL',
                'upper_bound REAL',
            ]
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for forecast in response.get('ForecastResultsByTime', []):
                time_period = forecast.get('TimePeriod', {})
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT',
                    table_name,
                    '(time_period_start, time_period_end, mean_value, lower_bound, upper_bound) VALUES (?, ?, ?, ?, ?)',
                )
                cursor.execute(
                    insert_sql,
                    (
                        time_period.get('Start'),
                        time_period.get('End'),
                        float(forecast.get('MeanValue', 0)),
                        float(forecast.get('PredictionIntervalLowerBound', 0)),
                        float(forecast.get('PredictionIntervalUpperBound', 0)),
                    ),
                )
                rows_inserted += 1

        elif converter_type == 'tags' and 'Tags' in response:
            # Cost Explorer GetTags response
            schema = ['tag_value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Use validated table name
            validate_table_name(table_name)
            for tag in response.get('Tags', []):
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(tag_value) VALUES (?)'
                )
                cursor.execute(insert_sql, (tag,))
                rows_inserted += 1

        elif converter_type == 'cost_categories' and (
            'CostCategoryNames' in response or 'CostCategoryValues' in response
        ):
            # Cost Explorer GetCostCategories response
            schema = ['category_type TEXT', 'category_value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            for name in response.get('CostCategoryNames', []):
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(category_type, category_value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, ('name', name))
                rows_inserted += 1

            for value in response.get('CostCategoryValues', []):
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(category_type, category_value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, ('value', value))
                rows_inserted += 1

        elif converter_type == 'records':
            # Generic one-row-per-item converter for responses shaped like
            # {<list_key>: [ {..}, {..} ], count, next_token}. Unlike the bespoke
            # converters above (which hardcode a schema for one known API), this
            # derives the columns from the union of item keys, so any uniform list
            # response can be stored with real, queryable columns. Nested dict/list
            # values are stored as JSON strings (query with SQLite's json_extract).
            # Delegates to the shared helper so quoting/validation/JSON encoding
            # live in one place.
            rows_inserted = _create_and_insert_dict_rows(
                cursor, table_name, _extract_record_list(response)
            )

        elif converter_type == 'coh_recommendations' and 'recommendations' in response:
            # Cost Optimization Hub ListRecommendations.
            # Schema, INSERT, and value tuple are all driven by
            # ``COST_OPTIMIZATION_HUB_RECOMMENDATION_COLUMNS`` so each column is declared once.
            rows_inserted = _create_and_insert(
                cursor,
                table_name,
                COST_OPTIMIZATION_HUB_RECOMMENDATION_COLUMNS,
                response.get('recommendations', []),
            )

        elif converter_type == 'coh_efficiency_metrics' and 'groups' in response:
            # Cost Optimization Hub ListEfficiencyMetrics. The response nests a
            # per-timestamp series under each group, so denormalize to one row
            # per (group, timestamp). A no-data group (empty metrics_by_time) is
            # preserved as a single row with null metrics so the group and its
            # explanatory ``message`` survive offload rather than vanishing.
            efficiency_rows: List[Dict[str, Any]] = []
            for grp in response.get('groups', []):
                group_value = grp.get('group')
                message = grp.get('message')
                points = grp.get('metrics_by_time') or []
                if points:
                    for point in points:
                        efficiency_rows.append(
                            {
                                'group_value': group_value,
                                'message': message,
                                'timestamp': point.get('timestamp'),
                                'score': point.get('score'),
                                'savings': point.get('savings'),
                                'spend': point.get('spend'),
                            }
                        )
                else:
                    efficiency_rows.append(
                        {
                            'group_value': group_value,
                            'message': message,
                            'timestamp': None,
                            'score': None,
                            'savings': None,
                            'spend': None,
                        }
                    )
            rows_inserted = _create_and_insert(
                cursor,
                table_name,
                COST_OPTIMIZATION_HUB_EFFICIENCY_METRICS_COLUMNS,
                efficiency_rows,
            )

        elif converter_type == 'ri_coverage' and (
            ri_rows := _ri_series_rows(response, 'coverages_by_time', 'coverage')
        ):
            # Reservation coverage: one row per (time period, group) plus a
            # per-bucket total row, with the nested coverage metrics flattened
            # into columns. Response-level headline totals/percentages are kept
            # in `summary`. Empty series falls through to the generic branch so
            # the sample query always matches the stored columns.
            rows_inserted = _create_and_insert_dict_rows(cursor, table_name, ri_rows)
            summary_data = _response_summary(response)

        elif converter_type == 'ri_utilization' and (
            ri_rows := _ri_series_rows(response, 'utilizations_by_time', 'utilization')
        ):
            # Reservation utilization: same shape as coverage.
            rows_inserted = _create_and_insert_dict_rows(cursor, table_name, ri_rows)
            summary_data = _response_summary(response)

        elif converter_type == 'sp_lookback_metrics' and (
            metric_points := [
                point
                for point in _find_nested_list(response, 'MetricsOverLookbackPeriod')
                if isinstance(point, dict)
            ]
        ):
            # Savings Plans commitment purchase analysis and recommendation
            # details both nest an hourly MetricsOverLookbackPeriod series (at
            # different parent paths). Store one row per hourly data point so the
            # 276-338KB series is queryable rather than a single JSON blob, and
            # keep the headline fields (EstimatedSavingsAmount, EstimatedROI,
            # HourlyCommitmentToPurchase, AnalysisStatus, ...) in `summary`.
            rows_inserted = _create_and_insert_dict_rows(cursor, table_name, metric_points)
            summary_data = _response_summary(response)

        elif converter_type == 'sp_purchase_recommendation' and (
            detail_rows := [
                _flatten_scalars(d)
                for d in (
                    (response.get('SavingsPlansPurchaseRecommendation') or {}).get(
                        'SavingsPlansPurchaseRecommendationDetails'
                    )
                    or []
                )
                if isinstance(d, dict)
            ]
        ):
            # Savings Plans purchase recommendation: the detail list is nested
            # two levels down. Store one row per detail; keep the summary block,
            # TermInYears, PaymentOption and LookbackPeriodInDays in `summary`.
            rows_inserted = _create_and_insert_dict_rows(cursor, table_name, detail_rows)
            summary_data = _response_summary(response)

        elif converter_type == 'storage_lens_query' and response.get('rows'):
            # Storage Lens Athena run_query returns a `columns` list BEFORE the
            # `rows`, so the generic first-top-level-list rule would build a table
            # of column *names* and silently drop every data row. Store `rows`
            # (dicts keyed by column label, per AthenaHandler.get_query_results);
            # use `columns` for ordering. Athena labels (e.g. 'SUM(storage_bytes)')
            # are not safe SQL identifiers, so sanitize them and remap the row keys
            # to match. Labels are de-duplicated first: the rows are dicts, so an
            # identical repeated label was already merged into one key upstream.
            # Sanitized names are made unique case-insensitively (SQLite column
            # names are case-insensitive).
            raw_rows = response.get('rows') or []

            safe_columns: List[str] = []
            seen_lower: set = set()
            label_to_safe: Dict[str, str] = {}
            for label in dict.fromkeys(response.get('columns') or []):
                base = _sanitize_identifier(str(label))
                candidate = base
                suffix = 1
                while candidate.lower() in seen_lower:
                    suffix += 1
                    candidate = f'{base}_{suffix}'
                seen_lower.add(candidate.lower())
                safe_columns.append(candidate)
                label_to_safe[label] = candidate

            storage_rows = [
                {label_to_safe.get(k, _sanitize_identifier(str(k))): v for k, v in raw_row.items()}
                for raw_row in raw_rows
                if isinstance(raw_row, dict)
            ]
            rows_inserted = _create_and_insert_dict_rows(
                cursor, table_name, storage_rows, columns=safe_columns
            )
            summary_data = _response_summary(response)

        else:
            # Generic fallback for unknown response types
            schema = ['key TEXT', 'value TEXT']
            sql = create_safe_sql_statement('CREATE', table_name, *schema)
            cursor.execute(sql)

            # Flatten response to key-value pairs (lists JSON-encoded) using the
            # shared helper; str() at insert time preserves the TEXT values this
            # branch has always produced.
            flattened = _flatten_scalars(response)

            for key, value in flattened.items():
                # Use validated table name
                validate_table_name(table_name)
                insert_sql = create_safe_sql_statement(
                    'INSERT', table_name, '(key, value) VALUES (?, ?)'
                )
                cursor.execute(insert_sql, (key, str(value)))
                rows_inserted += 1

        conn.commit()

        # Get preview
        sql = create_safe_sql_statement('SELECT', table_name, '*', limit=5)
        cursor.execute(sql)
        preview_rows = cursor.fetchall()

        # Get column names for preview
        columns = [description[0] for description in cursor.description]

        # Format preview as list of dictionaries
        preview = []
        for row in preview_rows:
            preview_item = {}
            for i, col in enumerate(columns):
                preview_item[col] = row[i]
            preview.append(preview_item)

        # Register table in schema info
        register_table_in_schema_info(
            cursor, table_name, operation_name, json.dumps(metadata), rows_inserted
        )

        await ctx.info(f'Converted {rows_inserted} rows to SQL table: {table_name}')

        # Get sample queries based on table type with enhanced examples
        # Start with a basic query for all tables
        base_query = create_safe_sql_statement('SELECT', table_name, '*') + ' LIMIT 10'
        sample_queries = [
            {
                'name': 'Basic query',
                'description': 'Retrieve the first 10 rows from the table',
                'sql': base_query,
            }
        ]

        # Add specialized queries based on table type
        if converter_type == 'cost_and_usage':
            # Cost Explorer cost_and_usage queries

            # Total cost by service/dimension
            cost_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'group_key_1, SUM(amount) as total_cost, unit'
                )
                + ' GROUP BY group_key_1, unit ORDER BY total_cost DESC'
            )
            sample_queries.append(
                {
                    'name': 'Total cost by service/dimension',
                    'description': 'Summarizes costs by the primary dimension (usually service)',
                    'sql': cost_query,
                }
            )

            # Cost trends over time
            trend_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'time_period_start, SUM(amount) as daily_cost'
                )
                + ' GROUP BY time_period_start ORDER BY time_period_start'
            )
            sample_queries.append(
                {
                    'name': 'Cost trend over time',
                    'description': 'Shows cost pattern across the time period',
                    'sql': trend_query,
                }
            )

            # Top 5 services/resources
            top_items_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'group_key_1, SUM(amount) as total_cost'
                )
                + ' GROUP BY group_key_1 ORDER BY total_cost DESC LIMIT 5'
            )
            sample_queries.append(
                {
                    'name': 'Top 5 cost items',
                    'description': 'Shows the 5 highest-cost items',
                    'sql': top_items_query,
                }
            )

        elif converter_type == 'dimension_values':
            # DimensionValues queries

            # Basic alphabetical list
            value_query = (
                create_safe_sql_statement('SELECT', table_name, 'value') + ' ORDER BY value'
            )
            sample_queries.append(
                {
                    'name': 'Values in alphabetical order',
                    'description': 'Lists all dimension values alphabetically',
                    'sql': value_query,
                }
            )

            # Values with attributes
            attr_query = (
                create_safe_sql_statement('SELECT', table_name, 'value, attributes')
                + ' ORDER BY value'
            )
            sample_queries.append(
                {
                    'name': 'Values with attributes',
                    'description': 'Shows values with their attributes as JSON',
                    'sql': attr_query,
                }
            )

        elif converter_type == 'pricing_products':
            # AWS Pricing queries

            # Count by product family
            product_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'product_family, COUNT(*) as product_count'
                )
                + ' GROUP BY product_family ORDER BY product_count DESC'
            )
            sample_queries.append(
                {
                    'name': 'Products by family',
                    'description': 'Counts products in each product family',
                    'sql': product_query,
                }
            )

            # EC2 instance types (if applicable)
            ec2_query = (
                create_safe_sql_statement('SELECT', table_name, 'sku, attributes, pricing_terms')
                + " WHERE attributes LIKE '%instanceType%' LIMIT 10"
            )
            sample_queries.append(
                {
                    'name': 'EC2 instance types',
                    'description': 'Shows EC2 instance types with pricing data',
                    'sql': ec2_query,
                }
            )

        elif converter_type == 'forecast':
            # Cost Explorer forecast queries

            # Forecast trend
            forecast_query = (
                create_safe_sql_statement(
                    'SELECT', table_name, 'time_period_start, mean_value, lower_bound, upper_bound'
                )
                + ' ORDER BY time_period_start'
            )
            sample_queries.append(
                {
                    'name': 'Forecast trend',
                    'description': 'Shows forecast values with confidence bounds over time',
                    'sql': forecast_query,
                }
            )

        elif converter_type == 'tags':
            # Tags-related queries
            tags_query = (
                create_safe_sql_statement('SELECT', table_name, 'tag_value')
                + " WHERE tag_value LIKE '%env%' OR tag_value LIKE '%project%' OR tag_value LIKE '%name%'"
            )
            sample_queries.append(
                {
                    'name': 'Common tags',
                    'description': 'Finds common tags like environment, project, or name',
                    'sql': tags_query,
                }
            )

        elif converter_type == 'cost_categories':
            # Cost Categories queries

            # Category names only
            names_query = (
                create_safe_sql_statement('SELECT', table_name, 'category_value')
                + " WHERE category_type = 'name' ORDER BY category_value"
            )
            sample_queries.append(
                {
                    'name': 'Cost category names',
                    'description': 'Lists all cost category names alphabetically',
                    'sql': names_query,
                }
            )

            # Category values only
            values_query = (
                create_safe_sql_statement('SELECT', table_name, 'category_value')
                + " WHERE category_type = 'value' ORDER BY category_value"
            )
            sample_queries.append(
                {
                    'name': 'Cost category values',
                    'description': 'Lists all cost category values alphabetically',
                    'sql': values_query,
                }
            )

        elif converter_type == 'records':
            # Records are one row per item with a column per field.
            count_query = create_safe_sql_statement('SELECT', table_name, 'COUNT(*) as item_count')
            sample_queries.append(
                {
                    'name': 'Item count',
                    'description': 'Counts the number of items stored',
                    'sql': count_query,
                }
            )

        elif converter_type == 'coh_recommendations':
            # Cost Optimization Hub recommendations. One sample query reflecting
            # the effective ordering: the caller's requested order_by when given,
            # otherwise a default "highest savings first" view. The requested
            # column comes from the dimension->column allowlist and the direction
            # from Asc/Desc (defaulting to ASC, which is how the API sorts when
            # ``order`` is omitted), so
            # the interpolated ORDER BY is injection-safe.
            order_column = 'estimated_monthly_savings'
            order_direction = 'DESC'
            query_name = 'Top 20 savings opportunities'
            query_description = 'Highest-impact recommendations by estimated monthly savings'

            mapped_column = None
            if isinstance(requested_order_by, dict):
                dimension = requested_order_by.get('dimension')
                if isinstance(dimension, str):
                    mapped_column = COST_OPTIMIZATION_HUB_ORDER_DIMENSION_TO_COLUMN.get(dimension)
            if mapped_column:
                order_column = mapped_column
                order_direction = 'DESC' if requested_order_by.get('order') == 'Desc' else 'ASC'
                query_name = (
                    f'First 20 by requested order '
                    f'({requested_order_by.get("dimension")} {order_direction})'
                )
                query_description = 'Recommendations in the order requested on the API call'

            sample_query = (
                create_safe_sql_statement(
                    'SELECT',
                    table_name,
                    'recommendation_id, account_id, resource_id, action_type, '
                    'current_resource_type, estimated_monthly_savings, currency_code',
                )
                + f' ORDER BY {order_column} {order_direction} LIMIT 20'
            )
            sample_queries.append(
                {
                    'name': query_name,
                    'description': query_description,
                    'sql': sample_query,
                }
            )

        elif converter_type == 'coh_efficiency_metrics':
            # Cost Optimization Hub efficiency-metrics queries.

            # Latest metrics per group, ranked. SQLite's min/max bare-column
            # rule makes the score/savings/spend come from the row with the
            # newest (MAX) timestamp within each group. The ranking column and
            # direction mirror the caller's requested order_by when given, else
            # the API default of Score descending. The API sorts descending when
            # ``order`` is omitted, so
            # DESC is the default direction. Column and direction come from
            # controlled allowlists, so the interpolated ORDER BY is
            # injection-safe.
            rank_column = 'score'
            rank_direction = 'DESC'
            mapped_rank = None
            if isinstance(requested_order_by, dict):
                dimension = requested_order_by.get('dimension')
                if isinstance(dimension, str):
                    mapped_rank = COST_OPTIMIZATION_HUB_EFFICIENCY_ORDER_DIMENSION_TO_COLUMN.get(
                        dimension
                    )
            if mapped_rank:
                rank_column = mapped_rank
                rank_direction = 'ASC' if requested_order_by.get('order') == 'Asc' else 'DESC'

            latest_ranked_query = (
                create_safe_sql_statement(
                    'SELECT',
                    table_name,
                    'group_value, MAX(timestamp) as latest_timestamp, score, savings, spend',
                )
                + f' GROUP BY group_value ORDER BY {rank_column} {rank_direction}'
            )
            sample_queries.append(
                {
                    'name': f'Latest efficiency metrics by group (ranked by {rank_column})',
                    'description': 'Most recent score, savings, and spend per group, ranked by the requested (or default) dimension',
                    'sql': latest_ranked_query,
                }
            )

            # Score/savings/spend trend over time for a single group.
            trend_query = (
                create_safe_sql_statement('SELECT', table_name, 'timestamp, score, savings, spend')
                + " WHERE group_value = '<group>' ORDER BY timestamp"
            )
            sample_queries.append(
                {
                    'name': 'Trend for one group',
                    'description': 'Time series for a single group (replace <group> with an account id or region)',
                    'sql': trend_query,
                }
            )

        elif (
            converter_type in ('ri_coverage', 'ri_utilization') and 'time_period_start' in columns
        ):
            # One row per (time period, group) plus a per-bucket total row.
            # Guarded on 'time_period_start' so that if an empty series fell
            # through to the generic key/value table, this sample is skipped
            # (and the generic sample is used) instead of referencing a column
            # that was never created.
            trend_query = (
                create_safe_sql_statement('SELECT', table_name, '*')
                + " WHERE level = 'total' ORDER BY time_period_start"
            )
            sample_queries.append(
                {
                    'name': 'Totals over time',
                    'description': "Per-period totals (level='total'); drop the WHERE to also see per-group rows, which carry attr_* dimension columns",
                    'sql': trend_query,
                }
            )

        elif converter_type == 'sp_lookback_metrics':
            # One row per hourly data point. Order by StartTime when present
            # (guarded so the sample never references a missing column).
            if 'StartTime' in columns:
                series_query = (
                    create_safe_sql_statement('SELECT', table_name, '*') + ' ORDER BY StartTime'
                )
            else:
                series_query = create_safe_sql_statement('SELECT', table_name, '*') + ' LIMIT 50'
            sample_queries.append(
                {
                    'name': 'Hourly series over lookback period',
                    'description': 'Hourly MetricsOverLookbackPeriod data points; headline totals are in the result `summary`',
                    'sql': series_query,
                }
            )

        elif converter_type == 'sp_purchase_recommendation':
            # Prefer a savings aggregate when the column is present; else count.
            if 'EstimatedMonthlySavingsAmount' in columns:
                agg_query = create_safe_sql_statement(
                    'SELECT',
                    table_name,
                    'COUNT(*) as detail_count, '
                    'SUM(EstimatedMonthlySavingsAmount) as total_monthly_savings',
                )
                description = 'Total estimated monthly savings across all recommendation details'
            else:
                agg_query = create_safe_sql_statement(
                    'SELECT', table_name, 'COUNT(*) as detail_count'
                )
                description = 'Counts the Savings Plans purchase recommendation details stored'
            sample_queries.append(
                {'name': 'Savings summary', 'description': description, 'sql': agg_query}
            )

        elif converter_type == 'storage_lens_query':
            count_query = create_safe_sql_statement('SELECT', table_name, 'COUNT(*) as row_count')
            sample_queries.append(
                {
                    'name': 'Row count',
                    'description': 'Counts the Storage Lens query result rows stored; use SELECT * to inspect columns',
                    'sql': count_query,
                }
            )

        else:
            # Generic key-value pair queries for other types
            key_query = (
                create_safe_sql_statement('SELECT', table_name, 'key, value')
                + " WHERE key LIKE '%total%' OR key LIKE '%cost%' OR key LIKE '%amount%'"
            )
            sample_queries.append(
                {
                    'name': 'Cost-related fields',
                    'description': 'Finds key-value pairs related to costs or totals',
                    'sql': key_query,
                }
            )

        # Return info about the stored data
        db_path = get_session_db_path()

        return {
            'status': 'success',
            'data_stored': True,
            'session_db': db_path,
            'table_name': table_name,
            'schema': columns,
            'row_count': rows_inserted,
            'sample_queries': sample_queries,
            'preview': preview,
            # Headline scalar fields the nested-series converters would otherwise
            # drop (totals, savings, ROI, payment option, ...). Omitted entirely
            # for converters that don't produce one, so existing envelopes are
            # unchanged.
            **({'summary': summary_data} if summary_data else {}),
            **metadata,
        }

    except Exception as e:
        error_message = f'Error converting response to SQL: {str(e)}'
        # Use context logger for consistent error reporting
        ctx_logger = get_context_logger(ctx, __name__)
        await ctx_logger.error(error_message, exc_info=True)
        raise
    finally:
        # Close connection if it was successfully created
        if 'conn' in locals() and conn is not None:
            try:
                conn.close()
                logger.debug('Closed database connection')
            except Exception as e:
                logger.warning(f'Error closing database connection: {str(e)}')


async def execute_session_sql(
    ctx: Context,
    query: str,
    schema: Optional[List[str]] = None,
    data: Optional[List[List[Any]]] = None,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute SQL query on the session database.

    Optionally adds user data to the database before querying.

    Args:
        ctx: MCP context
        query: SQL query to execute
        schema: Optional column definitions for user data
        data: Optional array of data rows to add before querying
        table_name: Optional name for user data table

    Returns:
        Dict[str, Any]: Query results
    """
    # Initialize connection to None in case of early exception
    conn = None
    try:
        # Get database connection
        conn, cursor = get_db_connection()

        # If user provided data, add it to the database first
        if data and schema:
            if not table_name:
                table_name = f'user_data_{str(uuid.uuid4())[:8]}'

            await ctx.info(f'Adding {len(data)} rows to table: {table_name}')

            # Create table with provided schema
            create_table(cursor, table_name, schema)

            # Insert data
            if data:
                insert_data(cursor, table_name, data)

            conn.commit()
            await ctx.info(f'Created table {table_name} with {len(data)} rows')

        # Execute the main query
        await ctx.info(f'Executing SQL query: {query[:100]}...')

        # Get query type (read or write)
        query_upper = query.strip().upper()
        is_write_operation = any(
            query_upper.startswith(cmd)
            for cmd in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        )

        # Execute the query with validation
        validate_sql_query(query)
        cursor.execute(query)

        # Commit if this is a write operation
        if is_write_operation:
            conn.commit()

        # Get results
        columns = (
            [description[0] for description in cursor.description] if cursor.description else []
        )
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))

        # Get database path
        db_path = get_session_db_path()

        # Create response
        response = {
            'status': 'success',
            'results': results,
            'row_count': len(results),
            'columns': columns,
            'database_path': db_path,
        }

        # Include table info if data was added
        if data and schema:
            response['created_table'] = table_name
            response['rows_added'] = len(data)

        return response

    except Exception as e:
        error_message = f'Error executing SQL query: {str(e)}'
        # Use context logger for consistent error reporting
        ctx_logger = get_context_logger(ctx, __name__)
        await ctx_logger.error(error_message, exc_info=True)

        # Add a structured error_type/operation/service so failures are
        # classifiable. error_type is the exception class name only (e.g.
        # 'OperationalError').
        return {
            'status': 'error',
            'service': 'SQL',
            'operation': 'session_sql',
            'error_type': type(e).__name__,
            'message': error_message,
        }

    finally:
        # Close connection only if it was successfully opened
        if conn is not None:
            try:
                conn.close()
                logger.debug('Closed database connection')
            except Exception as e:
                error_message = f'Error closing database connection: {str(e)}'
                # Use context logger for consistent error reporting
                ctx_logger = get_context_logger(ctx, __name__)
                await ctx_logger.error(error_message)
