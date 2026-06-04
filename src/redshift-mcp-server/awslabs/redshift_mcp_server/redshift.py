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

"""AWS client management for Redshift MCP Server."""

import asyncio
import boto3
import os
import regex
import time
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    BARE_TABLE_CANDIDATES_SQL,
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
    CLIENT_USER_AGENT_NAME,
    COLUMN_STATS_SQL,
    COLUMNS_BY_PAIRS_SQL,
    COLUMNS_SQL,
    DATABASES_SQL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SCHEMAS_SQL,
    SESSION_KEEPALIVE,
    SUSPICIOUS_QUERY_MAX_LEN,
    SUSPICIOUS_QUERY_REGEXP,
    SUSPICIOUS_QUERY_TIMEOUT,
    TABLES_EXTRA_BY_PAIRS_SQL,
    TABLES_EXTRA_SQL,
    TABLES_SQL,
)
from awslabs.redshift_mcp_server.models import ExecutionPlanNode
from botocore.config import Config
from loguru import logger
from typing import Iterable, NamedTuple, Optional, cast


# Compile once; the pattern uses recursive subroutines so compilation is non-trivial.
_SUSPICIOUS_QUERY_RE = regex.compile(SUSPICIOUS_QUERY_REGEXP)


def _is_suspicious(sql: str) -> bool:
    """Return True if `sql` looks like it tries to break out of the read-only wrapper.

    Fails closed on oversized input and regex timeouts.
    """
    if len(sql) > SUSPICIOUS_QUERY_MAX_LEN:
        return True
    try:
        return bool(_SUSPICIOUS_QUERY_RE.search(sql, timeout=SUSPICIOUS_QUERY_TIMEOUT))
    except TimeoutError:
        logger.warning(
            f'Suspicious-query regex timed out after {SUSPICIOUS_QUERY_TIMEOUT}s; '
            f'treating SQL as suspicious (length={len(sql)})'
        )
        return True


# Category labels for ``TableReference``: how a table is named in user SQL.
# ``BARE`` = ``table``; ``SCHEMA_QUALIFIED`` = ``schema.table``;
# ``DATABASE_QUALIFIED`` = ``database.schema.table``.
TABLE_REF_BARE = 'bare'
TABLE_REF_SCHEMA_QUALIFIED = 'schema_qualified'
TABLE_REF_DATABASE_QUALIFIED = 'database_qualified'


class TableReference(NamedTuple):
    """A categorized table reference extracted from user SQL.

    Identifier case is preserved as written; hashable so the extractor
    can deduplicate via a ``set``.
    """

    category: str
    table_name: str
    schema_name: Optional[str] = None
    database_name: Optional[str] = None


# Captures relation name (group 1) and optional alias (group 2) from a
# Seq/Tid/Index Scan operation line. Redshift emits one of three shapes:
# ``Seq Scan on <rel>``, ``Tid Scan on <rel>``, or
# ``Index Scan[ Backward] using <indname>[, <indname>]* on <rel>``.
_OP_RELATION_ALIAS_PATTERN = regex.compile(
    r'(?:Seq Scan|Tid Scan|Index Scan(?: Backward)?(?: using [^\s,]+(?:, [^\s,]+)*)?)'
    r' on (\S+)(?:\s+([a-zA-Z_]\w*))?'
)

# Captures the cost block as (startup, total, rows, width).
_OP_COST_PATTERN = regex.compile(
    r'cost=(\d+(?:\.\d+)?)\.\.(\d+(?:\.\d+)?)\s+rows=(\d+)\s+width=(\d+)'
)

# Captures any DS_* distribution token. Longer alternatives first.
_OP_DISTRIBUTION_PATTERN = regex.compile(
    r'\b('
    r'DS_DIST_ALL_INNER'
    r'|DS_DIST_ALL_NONE'
    r'|DS_BCAST_INNER'
    r'|DS_DIST_INNER'
    r'|DS_DIST_NONE'
    r'|DS_DIST_OUTER'
    r')\b'
)


# Detail-line label → ``ExecutionPlanNode`` field. Longer labels first so
# ``Join Filter:`` matches before ``Filter:``.
_DETAIL_LINE_LABELS: tuple[tuple[str, str], ...] = (
    ('Hash Cond:', 'join_condition'),
    ('Merge Cond:', 'join_condition'),
    ('Join Filter:', 'join_filter'),
    ('Inner Dist Key:', 'inner_dist_key'),
    ('Outer Dist Key:', 'outer_dist_key'),
    ('Sort Key:', 'sort_key'),
    ('Merge Key:', 'merge_key'),
    ('Index Cond:', 'index_condition'),
    ('Partition:', 'partition_key'),
    ('Order:', 'order_key'),
    ('Filter:', 'filter_condition'),
)

# Label-less detail strings emitted by Network nodes describing the
# data-movement direction. Matched exactly (no colon, no value).
_DATA_MOVEMENT_VALUES: frozenset[str] = frozenset(
    {
        'Send to leader',
        'Send to slice 0',
        'Distribute',
        'Broadcast',
        'Distribute Round Robin',
    }
)


def _apply_detail_line(node: ExecutionPlanNode, line_text: str) -> None:
    """Apply any recognized detail-line field to ``node`` in place.

    Args:
        node: The most recently seen operation node. Mutated in place.
        line_text: The raw text of the detail line.
    """
    stripped = line_text.lstrip()
    for label, field in _DETAIL_LINE_LABELS:
        if stripped.startswith(label):
            value = stripped[len(label) :].strip()
            setattr(node, field, value)
            return
    if stripped in _DATA_MOVEMENT_VALUES:
        node.data_movement = stripped
        return
    # GROUPING SETS(...) line on aggregate nodes; stored verbatim.
    if stripped.startswith('GROUPING SETS('):
        node.agg_strategy = stripped
        return


def _extract_operation_name(op_line: str) -> str:
    """Extract the operation name from an operation-line text.

    Strips any leading ``->`` arrow, the ``using <indname>...`` segment
    on Index Scan lines, and everything from `` on <relation>`` or
    ``(cost=`` onward. Returns the cleaned operation name.

    Args:
        op_line: The operation-line text after :meth:`str.lstrip`.

    Returns:
        The operation name (e.g., ``XN Seq Scan`` or
        ``XN Hash Join DS_BCAST_INNER``).
    """
    text = op_line
    if text.startswith('->'):
        text = text[len('->') :].lstrip()

    # Drop the ``using <indname>...`` tail Redshift appends to Index Scan lines.
    using_idx = text.find(' using ')
    if using_idx >= 0:
        text = text[:using_idx]

    cut_points: list[int] = []
    on_idx = text.find(' on ')
    if on_idx >= 0:
        cut_points.append(on_idx)
    cost_idx = text.find('(cost=')
    if cost_idx >= 0:
        cut_points.append(cost_idx)
    if cut_points:
        text = text[: min(cut_points)]

    return text.strip()


def _build_operation_node(stripped_line: str, level: int) -> ExecutionPlanNode:
    """Allocate one :class:`ExecutionPlanNode` from an operation-line text.

    Args:
        stripped_line: The operation-line text after :meth:`str.lstrip`.
        level: The level assigned by :func:`_parse_plan_text`'s indent-stack walk.

    Returns:
        A populated :class:`ExecutionPlanNode`. Optional fields are
        ``None`` when the corresponding information is not present.
    """
    operation = _extract_operation_name(stripped_line)

    relation_name: Optional[str] = None
    alias: Optional[str] = None
    relation_match = _OP_RELATION_ALIAS_PATTERN.search(stripped_line)
    if relation_match:
        relation_name = relation_match.group(1)
        alias = relation_match.group(2)

    cost_startup: Optional[float] = None
    cost_total: Optional[float] = None
    rows: Optional[int] = None
    width: Optional[int] = None
    cost_match = _OP_COST_PATTERN.search(stripped_line)
    if cost_match:
        cost_startup = float(cost_match.group(1))
        cost_total = float(cost_match.group(2))
        rows = int(cost_match.group(3))
        width = int(cost_match.group(4))

    distribution_type: Optional[str] = None
    dist_match = _OP_DISTRIBUTION_PATTERN.search(stripped_line)
    if dist_match:
        distribution_type = dist_match.group(1)

    return ExecutionPlanNode(
        level=level,
        operation=operation,
        relation_name=relation_name,
        alias=alias,
        distribution_type=distribution_type,
        cost_startup=cost_startup,
        cost_total=cost_total,
        rows=rows,
        width=width,
    )


def _parse_plan_text(raw_records: list[str]) -> list[ExecutionPlanNode]:
    """Parse raw EXPLAIN records into structured :class:`ExecutionPlanNode` list.

    Walks the records once, allocating one node per operation line
    (root + ``->``-prefixed lines) and folding detail lines (``Hash Cond:``,
    ``Filter:`` …) into the most recent operation node. Blank lines are
    ignored. Node levels are derived from a stack of operation-line indent
    widths so the level sequence stays contiguous regardless of Redshift's
    actual indent step (2 / 8 / 14 / 20 / ...).

    Args:
        raw_records: One string per Data API record from the EXPLAIN
            response, in source order. Empty list returns ``[]``.

    Returns:
        One :class:`ExecutionPlanNode` per operation line in document order.
    """
    if not raw_records:
        return []

    plan_nodes: list[ExecutionPlanNode] = []
    current_node: Optional[ExecutionPlanNode] = None
    # Stack of (indent_width, level) for currently-open ancestors.
    op_stack: list[tuple[int, int]] = []

    for text in raw_records:
        stripped = text.lstrip()
        if not stripped:
            continue

        is_operation_line = not op_stack or stripped.startswith('->')

        if is_operation_line:
            indent_width = len(text) - len(stripped)
            while op_stack and op_stack[-1][0] >= indent_width:
                op_stack.pop()
            node_level = 0 if not op_stack else op_stack[-1][1] + 1
            op_stack.append((indent_width, node_level))

            node = _build_operation_node(stripped, node_level)
            plan_nodes.append(node)
            current_node = node
        else:
            if current_node is None:
                continue
            _apply_detail_line(current_node, text)

    return plan_nodes


# Tokenizer keywords (case-insensitive). Compared after uppercasing.
_SQL_KEYWORDS: frozenset[str] = frozenset({'WITH', 'AS', 'FROM', 'JOIN'})


class _SqlToken(NamedTuple):
    """A single token emitted by :func:`_tokenize_sql`.

    Attributes:
        kind: One of ``'identifier'``, ``'keyword'``, ``'punctuation'``,
            ``'dot'``.
        value: Token text — original case for identifiers, uppercase for
            keywords, raw character for punctuation/dot.
    """

    kind: str
    value: str


class SqlReferenceExtractError(Exception):
    """Raised when :func:`_extract_sql_references` cannot parse its input."""


# Unquoted identifier character classes (Redshift dialect).
_ID_START_CHARS: frozenset[str] = frozenset(
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'  # pragma: allowlist secret
)
_ID_CONT_CHARS: frozenset[str] = frozenset(
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789$'  # pragma: allowlist secret
)


def _tokenize_sql(sql: str) -> list[_SqlToken]:
    """Tokenize ``sql`` for reference extraction.

    Single-pass scanner. Skips whitespace, line/block comments, and
    single-quoted string literals. Emits ``'identifier'``, ``'keyword'``
    (``WITH``/``AS``/``FROM``/``JOIN``), ``'punctuation'`` (``(``, ``)``,
    ``,``, ``;``), and ``'dot'`` (``.``) tokens. Double-quoted identifiers
    are emitted as ``'identifier'`` with original case preserved.

    Args:
        sql: The SQL string to tokenize. May be empty.

    Returns:
        A list of :class:`_SqlToken` records in source order.
    """
    tokens: list[_SqlToken] = []
    n = len(sql)
    i = 0

    while i < n:
        ch = sql[i]

        # Whitespace.
        if ch.isspace():
            i += 1
            continue

        # Line comment ``-- ...`` to end of line. Redshift accepts
        # ``--foo`` without a trailing space, so we don't require
        # one.
        if ch == '-' and i + 1 < n and sql[i + 1] == '-':
            i += 2
            while i < n and sql[i] != '\n':
                i += 1
            continue

        # Block comment ``/* ... */``, NON-nested per Redshift
        # dialect: the first ``*/`` closes the comment regardless of
        # inner ``/*`` sequences. An unterminated block comment
        # consumes the rest of the input silently.
        if ch == '/' and i + 1 < n and sql[i + 1] == '*':
            i += 2
            while i < n:
                if sql[i] == '*' and i + 1 < n and sql[i + 1] == '/':
                    i += 2
                    break
                i += 1
            continue

        # Single-quoted string literal ``'...'`` with ``''`` escape.
        # Inside a literal, no tokens are emitted. An unterminated
        # literal consumes the rest of the input.
        if ch == "'":
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        # Escaped quote: stay inside the literal.
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # Double-quoted identifier ``"..."`` with ``""`` escape. Emits
        # a single ``'identifier'`` token preserving the original
        # case.
        if ch == '"':
            i += 1
            buf: list[str] = []
            while i < n:
                if sql[i] == '"':
                    if i + 1 < n and sql[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    # Closing quote.
                    i += 1
                    break
                buf.append(sql[i])
                i += 1
            tokens.append(_SqlToken(kind='identifier', value=''.join(buf)))
            continue

        # Grouping/separator punctuation.
        if ch == '.':
            tokens.append(_SqlToken(kind='dot', value='.'))
            i += 1
            continue
        if ch in '(),;':
            tokens.append(_SqlToken(kind='punctuation', value=ch))
            i += 1
            continue

        # Unquoted identifier or keyword. Identifier start: ASCII
        # letter or underscore (Redshift rule). The continuation set
        # additionally includes ASCII digits and ``$``. Keyword check
        # uses the uppercase form; misses fall through to
        # ``'identifier'`` with original case preserved.
        if ch in _ID_START_CHARS:
            start = i
            i += 1
            while i < n and sql[i] in _ID_CONT_CHARS:
                i += 1
            word = sql[start:i]
            upper = word.upper()
            if upper in _SQL_KEYWORDS:
                tokens.append(_SqlToken(kind='keyword', value=upper))
            else:
                tokens.append(_SqlToken(kind='identifier', value=word))
            continue

        # Anything else (operators, unknown characters): skip
        # silently. Operators like ``=``, ``<``, ``+`` are not
        # relevant to table-reference extraction.
        i += 1

    return tokens


def _skip_to_matching_paren(tokens: list[_SqlToken], open_idx: int) -> int:
    """Return the index just past the ``)`` that matches ``tokens[open_idx]``.

    Tracks nested parens via ``(``/``)`` punctuation tokens; other
    tokens do not affect depth (string literals and comments do not
    emit tokens, so they cannot perturb the count).

    Args:
        tokens: The token stream from :func:`_tokenize_sql`.
        open_idx: Index of the opening ``(`` to start from.

    Returns:
        The index immediately after the matching ``)``, or ``-1`` when
        no matching close paren is found before end of input.
    """
    n = len(tokens)
    j = open_idx + 1
    inner_depth = 1
    while j < n:
        tok = tokens[j]
        if tok.kind == 'punctuation':
            if tok.value == '(':
                inner_depth += 1
            elif tok.value == ')':
                inner_depth -= 1
                if inner_depth == 0:
                    return j + 1
        j += 1
    return -1


def _collect_cte_names(tokens: list[_SqlToken], start_idx: int) -> set[str]:
    """Collect CTE names from a ``WITH`` clause via look-ahead.

    Walks each comma-separated ``<name> [(<col-list>)] [AS] (<body>)``
    definition until the trailing main statement (``SELECT`` / ``INSERT``
    / ``UPDATE`` / ``DELETE``). Pure look-ahead; does not modify caller
    state. An optional ``RECURSIVE`` modifier after ``WITH`` is skipped.

    Args:
        tokens: The token stream from :func:`_tokenize_sql`.
        start_idx: Index of the first token after ``WITH``.

    Returns:
        The set of CTE names declared by this ``WITH`` clause. May be
        empty for malformed input.
    """
    names: set[str] = set()
    n = len(tokens)
    j = start_idx

    # Optional ``RECURSIVE`` modifier (not a recognized keyword,
    # appears as an identifier).
    if j < n and tokens[j].kind == 'identifier' and tokens[j].value.upper() == 'RECURSIVE':
        j += 1

    while j < n:
        tok = tokens[j]

        # Trailing main statement terminator. ``SELECT`` / ``INSERT`` /
        # ``UPDATE`` / ``DELETE`` are not in the recognized keyword
        # set, so they show up as identifiers.
        if tok.kind == 'identifier' and tok.value.upper() in (
            'SELECT',
            'INSERT',
            'UPDATE',
            'DELETE',
        ):
            break

        # Anything else that isn't an identifier here is malformed;
        # stop collecting and let the main loop handle it.
        if tok.kind != 'identifier':
            break

        # Record the CTE name (original case preserved).
        names.add(tok.value)
        j += 1

        # Optional column list ``(col1, col2, ...)``.
        if j < n and tokens[j].kind == 'punctuation' and tokens[j].value == '(':
            end = _skip_to_matching_paren(tokens, j)
            if end < 0:
                break
            j = end

        # Optional ``AS`` keyword.
        if j < n and tokens[j].kind == 'keyword' and tokens[j].value == 'AS':
            j += 1

        # Body ``(...)``.
        if j < n and tokens[j].kind == 'punctuation' and tokens[j].value == '(':
            end = _skip_to_matching_paren(tokens, j)
            if end < 0:
                break
            j = end
        else:
            # No body — malformed; stop collecting.
            break

        # Optional ``,`` for the next CTE in the list.
        if j < n and tokens[j].kind == 'punctuation' and tokens[j].value == ',':
            j += 1
            continue
        break

    return names


def _extract_sql_references(sql: str) -> list[TableReference]:
    """Extract categorized table references from a raw user SQL string.

    Walks the token stream from :func:`_tokenize_sql` and emits one
    :class:`TableReference` per dotted-identifier sequence at a
    ``FROM``/``JOIN`` position. Categorizes 1 part as BARE, 2 parts as
    SCHEMA_QUALIFIED, 3 parts as DATABASE_QUALIFIED. CTE names declared
    in active ``WITH`` scopes are excluded from BARE references.
    Subquery and column aliases are consumed but not emitted.
    Identifier case is preserved; results are deduplicated by exact
    tuple equality with first-occurrence ordering.

    Args:
        sql: The original SQL query passed to ``describe_execution_plan``.

    Returns:
        A list of :class:`TableReference` records in source order.

    Raises:
        SqlReferenceExtractError: When the input is empty / comment-only,
            or a ``FROM``/``JOIN`` position is followed by a 0-part or
            4+-part dotted-identifier sequence.
    """
    tokens = _tokenize_sql(sql)

    # Empty / whitespace / comment-only SQL: an empty token stream is
    # a sufficient signal — whitespace and comments are consumed
    # silently by the scanner.
    if not tokens:
        raise SqlReferenceExtractError(
            'Cannot extract table references from empty or comment-only SQL.'
        )

    refs: list[TableReference] = []
    # Order-preserving dedup set keyed on the full TableReference
    # tuple. ``TableReference`` is frozen and hashable on all four
    # fields.
    seen: set[TableReference] = set()

    def _emit(ref: TableReference) -> None:
        """Append ``ref`` to ``refs`` only if not previously seen."""
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)

    n = len(tokens)
    i = 0
    expecting_table = False
    depth = 0
    # Stack of (entry_depth, cte_names) frames; popped when paren depth drops.
    cte_frames: list[tuple[int, set[str]]] = []
    # Parallel to paren depth: True at indices where ``(`` opened a subquery.
    subquery_open_stack: list[bool] = []

    def _is_cte_name(name: str) -> bool:
        """True iff ``name`` is in any active CTE frame."""
        for _, names in reversed(cte_frames):
            if name in names:
                return True
        return False

    while i < n:
        tok = tokens[i]

        # ``WITH`` opens a CTE-name frame at the current paren depth.
        if tok.kind == 'keyword' and tok.value == 'WITH':
            i += 1
            cte_names = _collect_cte_names(tokens, i)
            cte_frames.append((depth, cte_names))
            continue

        # ``FROM`` / ``JOIN`` re-arms the next position as a table reference.
        if tok.kind == 'keyword' and tok.value in ('FROM', 'JOIN'):
            expecting_table = True
            i += 1
            continue

        if expecting_table:
            # ``FROM (`` / ``JOIN (`` — derived-table subquery.
            if tok.kind == 'punctuation' and tok.value == '(':
                expecting_table = False
                depth += 1
                subquery_open_stack.append(True)
                i += 1
                continue

            if tok.kind != 'identifier':
                raise SqlReferenceExtractError(
                    f"Expected table reference at FROM/JOIN position, got {tok.kind} '{tok.value}'"
                )

            # Read a dotted identifier sequence ``<id>(.<id>)*``; 4+ parts → reject.
            parts: list[str] = [tok.value]
            i += 1
            while i + 1 < n and tokens[i].kind == 'dot' and tokens[i + 1].kind == 'identifier':
                parts.append(tokens[i + 1].value)
                i += 2

            if len(parts) == 1:
                # BARE — only check active CTE frames here; qualified refs are never CTEs.
                if not _is_cte_name(parts[0]):
                    _emit(
                        TableReference(
                            category=TABLE_REF_BARE,
                            table_name=parts[0],
                        )
                    )
            elif len(parts) == 2:
                _emit(
                    TableReference(
                        category=TABLE_REF_SCHEMA_QUALIFIED,
                        schema_name=parts[0],
                        table_name=parts[1],
                    )
                )
            elif len(parts) == 3:
                _emit(
                    TableReference(
                        category=TABLE_REF_DATABASE_QUALIFIED,
                        database_name=parts[0],
                        schema_name=parts[1],
                        table_name=parts[2],
                    )
                )
            else:
                raise SqlReferenceExtractError(
                    f'Malformed table reference with {len(parts)} parts: {".".join(parts)}'
                )

            expecting_table = False

            # Optional ``[AS] <identifier>`` column alias — consumed but not emitted.
            if i < n and tokens[i].kind == 'keyword' and tokens[i].value == 'AS':
                i += 1
            if i < n and tokens[i].kind == 'identifier':
                i += 1

            # Trailing comma re-arms the FROM list for the next table.
            if i < n and tokens[i].kind == 'punctuation' and tokens[i].value == ',':
                expecting_table = True
                i += 1

            continue

        # Track paren depth so CTE frames pop when their scope ends.
        if tok.kind == 'punctuation' and tok.value == '(':
            depth += 1
            subquery_open_stack.append(False)
            i += 1
            continue
        elif tok.kind == 'punctuation' and tok.value == ')':
            depth -= 1
            while cte_frames and cte_frames[-1][0] > depth:
                cte_frames.pop()
            was_subquery = subquery_open_stack.pop() if subquery_open_stack else False
            i += 1
            if was_subquery:
                # Consume optional ``[AS] <alias>`` after the subquery; trailing
                # comma re-arms the FROM list.
                if i < n and tokens[i].kind == 'keyword' and tokens[i].value == 'AS':
                    i += 1
                if i < n and tokens[i].kind == 'identifier':
                    i += 1
                if i < n and tokens[i].kind == 'punctuation' and tokens[i].value == ',':
                    expecting_table = True
                    i += 1
            continue

        i += 1

    return refs


def _render_schema_table_pairs(pairs: Iterable[tuple[str, str]]) -> str:
    """Render ``(schema, table)`` pairs as a SQL pair-list literal.

    Produces ``('s1','t1'),('s2','t2'),...`` (no outer parens) for the
    ``{schema_table_pairs}`` slot in ``TABLES_EXTRA_BY_PAIRS_SQL``.
    Single quotes in either component are doubled per Redshift's
    string-literal escape rule. Pairs are sorted ascending for
    deterministic output.

    Args:
        pairs: An iterable of ``(schema, table)`` 2-tuples.

    Returns:
        The pair-list SQL fragment, or an empty string when ``pairs``
        is empty.
    """
    sorted_pairs = sorted(pairs)
    if not sorted_pairs:
        return ''

    def _escape(value: str) -> str:
        return value.replace("'", "''")

    return ','.join(f"('{_escape(schema)}','{_escape(table)}')" for schema, table in sorted_pairs)


async def _fetch_table_metadata(
    cluster_identifier: str,
    database_name: str,
    pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], dict]:
    """Fetch batched table metadata for a set of ``(schema, table)`` pairs.

    Issues a single ``TABLES_EXTRA_BY_PAIRS_SQL`` call covering every
    pair. Returns ``{}`` on empty input or on any error so the
    ``describe_execution_plan`` pipeline keeps running.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: Database to execute the metadata query against.
        pairs: Set of ``(schema, table)`` tuples to look up.

    Returns:
        Mapping from ``(schema, table)`` to a metadata dict with
        ``redshift_diststyle``, ``redshift_estimated_row_count``, and
        the ``stats_*`` activity counters.
    """
    if not pairs:
        return {}

    rendered = _render_schema_table_pairs(pairs)
    if not rendered:
        return {}

    sql = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs=rendered)

    try:
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
        )

        # Field order from TABLES_EXTRA_BY_PAIRS_SQL: schema_name(0),
        # table_name(1), diststyle(2), estimated_row_count(3),
        # sequential_scans(4), sequential_tuples_read(5),
        # rows_inserted(6), rows_updated(7), rows_deleted(8).
        metadata: dict[tuple[str, str], dict] = {}
        for record in results_response.get('Records', []):
            schema_value = record[0].get('stringValue')
            table_value = record[1].get('stringValue')
            if schema_value is None or table_value is None:
                continue
            metadata[(schema_value, table_value)] = {
                'redshift_diststyle': record[2].get('stringValue'),
                'redshift_estimated_row_count': record[3].get('longValue'),
                'stats_sequential_scans': record[4].get('longValue'),
                'stats_sequential_tuples_read': record[5].get('longValue'),
                'stats_rows_inserted': record[6].get('longValue'),
                'stats_rows_updated': record[7].get('longValue'),
                'stats_rows_deleted': record[8].get('longValue'),
            }

        return metadata
    except Exception as fetch_error:
        # Non-fatal: keep the column-stats and table-design paths alive.
        logger.warning(
            f'_fetch_table_metadata: batched metadata fetch failed; '
            f'returning empty mapping. Error: {fetch_error}'
        )
        return {}


async def _fetch_columns_by_pairs(
    cluster_identifier: str,
    database_name: str,
    pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], list[dict]]:
    """Fetch batched per-column metadata for a set of ``(schema, table)`` pairs.

    Issues a single ``COLUMNS_BY_PAIRS_SQL`` call covering every pair.
    Returns ``{}`` on empty input or on any error so the
    ``describe_execution_plan`` pipeline keeps running.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: Database to execute the columns query against.
        pairs: Set of ``(schema, table)`` tuples to look up.

    Returns:
        Mapping from ``(schema, table)`` to a list of column dicts. Each
        column dict carries the same keys as :func:`discover_columns`
        records.
    """
    if not pairs:
        return {}

    rendered = _render_schema_table_pairs(pairs)
    if not rendered:
        return {}

    sql = COLUMNS_BY_PAIRS_SQL.format(schema_table_pairs=rendered)

    try:
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
            parameters=[{'name': 'database_name', 'value': database_name}],
        )

        # Field order from COLUMNS_BY_PAIRS_SQL: database_name(0),
        # schema_name(1), table_name(2), column_name(3),
        # ordinal_position(4), column_default(5), is_nullable(6),
        # data_type(7), character_maximum_length(8), numeric_precision(9),
        # numeric_scale(10), remarks(11), redshift_encoding(12),
        # redshift_is_distkey(13), redshift_sortkey_position(14),
        # external_type(15), external_partition_key(16).
        columns_by_pair: dict[tuple[str, str], list[dict]] = {}
        for record in results_response.get('Records', []):
            schema_value = record[1].get('stringValue')
            table_value = record[2].get('stringValue')
            if schema_value is None or table_value is None:
                continue
            column_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': schema_value,
                'table_name': table_value,
                'column_name': record[3].get('stringValue'),
                'ordinal_position': record[4].get('longValue'),
                'column_default': record[5].get('stringValue'),
                'is_nullable': record[6].get('stringValue'),
                'data_type': record[7].get('stringValue'),
                'character_maximum_length': record[8].get('longValue'),
                'numeric_precision': record[9].get('longValue'),
                'numeric_scale': record[10].get('longValue'),
                'remarks': record[11].get('stringValue'),
                'redshift_encoding': record[12].get('stringValue'),
                'redshift_is_distkey': record[13].get('booleanValue'),
                'redshift_sortkey_position': record[14].get('longValue'),
                'external_type': record[15].get('stringValue'),
                'external_partition_key': record[16].get('longValue'),
            }
            columns_by_pair.setdefault((schema_value, table_value), []).append(column_info)

        return columns_by_pair
    except Exception as fetch_error:
        # Non-fatal: keep the rest of the response alive.
        logger.warning(
            f'_fetch_columns_by_pairs: batched columns fetch failed; '
            f'returning empty mapping. Error: {fetch_error}'
        )
        return {}


def _render_name_list(names: Iterable[str]) -> str:
    """Render bare table names as a SQL name-list literal.

    Produces ``'n1','n2',...`` for the ``{names_list}`` slot in
    ``BARE_TABLE_CANDIDATES_SQL``. Single quotes are doubled per
    Redshift's string-literal escape rule. Names are sorted ascending
    and deduplicated.

    Args:
        names: An iterable of bare table-name strings.

    Returns:
        The name-list SQL fragment, or an empty string when ``names``
        is empty.
    """
    sorted_names = sorted(set(names))
    if not sorted_names:
        return ''

    def _escape(value: str) -> str:
        return value.replace("'", "''")

    return ','.join(f"'{_escape(name)}'" for name in sorted_names)


async def _lookup_bare_table_candidates(
    cluster_identifier: str,
    database_name: str,
    bare_names: set[str],
) -> dict[str, list[tuple[str, str]]]:
    """Resolve bare table-name references to candidate (schema, table) pairs.

    Issues a single ``BARE_TABLE_CANDIDATES_SQL`` call covering every
    distinct bare name. Returns ``{}`` on empty input or on any error
    so the ``describe_execution_plan`` pipeline keeps running.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: Database to execute the candidate-lookup query
            against.
        bare_names: Set of bare (unqualified) table-name strings.

    Returns:
        Mapping from each bare name to a list of ``(schema, table)``
        candidate pairs. Names with zero matches map to an empty list.
    """
    if not bare_names:
        return {}

    rendered = _render_name_list(bare_names)
    if not rendered:
        return {}

    sql = BARE_TABLE_CANDIDATES_SQL.format(names_list=rendered)

    try:
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
        )

        # Pre-populate so callers can distinguish "looked up, not found"
        # from "not looked up at all".
        candidates: dict[str, list[tuple[str, str]]] = {name: [] for name in bare_names}

        for record in results_response.get('Records', []):
            schema_value = record[0].get('stringValue')
            table_value = record[1].get('stringValue')
            if schema_value is None or table_value is None:
                continue
            if table_value in candidates:
                candidates[table_value].append((schema_value, table_value))

        return candidates
    except Exception as lookup_error:
        logger.warning(
            f'_lookup_bare_table_candidates: batched candidate lookup '
            f'failed; returning empty mapping. Error: {lookup_error}'
        )
        return {}


async def _resolve_ambiguities(
    cluster_identifier: str,
    connected_database_name: str,
    references: list[TableReference],
    *,
    lookup_fn=_lookup_bare_table_candidates,
) -> tuple[set[tuple[str, str]], list[str]]:
    """Resolve a list of ``TableReference`` records into pairs and notes.

    Per-category dispatch over :func:`_extract_sql_references` output:

    - SCHEMA_QUALIFIED → bind directly, no note.
    - DATABASE_QUALIFIED matching the connected database → bind directly.
    - DATABASE_QUALIFIED targeting a different database → cross-database
      note, no metadata fetch.
    - BARE with 0 candidates → not-found note.
    - BARE with 1 candidate → bind to that pair.
    - BARE with ≥2 candidates → ambiguity note + all matching pairs.

    Bare names are resolved in a single batched call to ``lookup_fn``.
    Notes are deduplicated by exact string equality (first-occurrence
    order preserved).

    Args:
        cluster_identifier: The cluster identifier to query.
        connected_database_name: The ``database_name`` from
            ``describe_execution_plan``.
        references: Output of :func:`_extract_sql_references`.
        lookup_fn: Async callable used to resolve bare names. Defaults
            to :func:`_lookup_bare_table_candidates`; tests inject a
            stub or mock.

    Returns:
        Tuple ``(resolved_pairs, notes)``. ``resolved_pairs`` feeds
        into :func:`_fetch_table_metadata`; ``notes`` surfaces on
        ``ExecutionPlan.notes``.
    """
    resolved_pairs: set[tuple[str, str]] = set()
    notes: list[str] = []

    # SCHEMA_QUALIFIED and DATABASE_QUALIFIED resolve in memory; only
    # BARE needs a network round-trip.
    schema_qualified_refs: list[TableReference] = []
    database_qualified_refs: list[TableReference] = []
    bare_refs: list[TableReference] = []
    for ref in references:
        if ref.category == TABLE_REF_SCHEMA_QUALIFIED:
            schema_qualified_refs.append(ref)
        elif ref.category == TABLE_REF_DATABASE_QUALIFIED:
            database_qualified_refs.append(ref)
        elif ref.category == TABLE_REF_BARE:
            bare_refs.append(ref)

    for ref in schema_qualified_refs:
        resolved_pairs.add((cast(str, ref.schema_name), ref.table_name))

    for ref in database_qualified_refs:
        if ref.database_name == connected_database_name:
            resolved_pairs.add((cast(str, ref.schema_name), ref.table_name))
        else:
            notes.append(
                f'Table "{ref.database_name}.{ref.schema_name}.{ref.table_name}" '
                f'targets database "{ref.database_name}" but the tool is connected '
                f'to database "{connected_database_name}"; cross-database table '
                f'metadata cannot be retrieved through the connected database.'
            )

    if bare_refs:
        unique_bare_names: set[str] = {ref.table_name for ref in bare_refs}

        candidates_by_name = await lookup_fn(
            cluster_identifier=cluster_identifier,
            database_name=connected_database_name,
            bare_names=unique_bare_names,
        )

        for ref in bare_refs:
            matches = candidates_by_name.get(ref.table_name, [])
            match_count = len(matches)

            if match_count == 0:
                notes.append(
                    f'Table "{ref.table_name}" was not found in any schema '
                    f'in database "{connected_database_name}".'
                )
            elif match_count == 1:
                resolved_pairs.add(matches[0])
            else:
                # ≥2 matches: ambiguity note + all matching pairs so
                # each appears in ``table_designs``.
                matching_schemas = sorted({schema for schema, _ in matches})
                notes.append(
                    f'Table "{ref.table_name}" is ambiguous: matches schemas '
                    f'{matching_schemas} in database '
                    f'"{connected_database_name}".'
                )
                for pair in matches:
                    resolved_pairs.add(pair)

    # Deduplicate notes preserving first-occurrence order.
    deduped_notes: list[str] = []
    seen_notes: set[str] = set()
    for note in notes:
        if note not in seen_notes:
            seen_notes.add(note)
            deduped_notes.append(note)

    return resolved_pairs, deduped_notes


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(
        self, config: Config, aws_region: str | None = None, aws_profile: str | None = None
    ):
        """Initialize the client manager."""
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self._redshift_client = None
        self._redshift_serverless_client = None
        self._redshift_data_client = None
        self._config = config

    def redshift_client(self):
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_client = session.client('redshift', config=self._config)
                logger.info(
                    f'Created Redshift client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift client: {str(e)}')
                raise

        return self._redshift_client

    def redshift_serverless_client(self):
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_serverless_client = session.client(
                    'redshift-serverless', config=self._config
                )
                logger.info(
                    f'Created Redshift Serverless client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Serverless client: {str(e)}')
                raise

        return self._redshift_serverless_client

    def redshift_data_client(self):
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_data_client = session.client('redshift-data', config=self._config)
                logger.info(
                    f'Created Redshift Data API client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Data API client: {str(e)}')
                raise

        return self._redshift_data_client


class RedshiftSessionManager:
    """Manages Redshift Data API sessions for connection reuse."""

    def __init__(self, session_keepalive: int, app_name: str):
        """Initialize the session manager.

        Args:
            session_keepalive: Session keepalive timeout in seconds.
            app_name: Application name to set in sessions.
        """
        self._sessions = {}  # {cluster:database -> session_info}
        self._session_keepalive = session_keepalive
        self._app_name = app_name

    async def session(
        self, cluster_identifier: str, database_name: str, cluster_info: dict
    ) -> str:
        """Get or create a session for the given cluster and database.

        Args:
            cluster_identifier: The cluster identifier to get session for.
            database_name: The database name to get session for.
            cluster_info: Cluster information dictionary from discover_clusters.

        Returns:
            Session ID for use in ExecuteStatement calls.
        """
        # Check existing session
        session_key = f'{cluster_identifier}:{database_name}'
        if session_key in self._sessions:
            session_info = self._sessions[session_key]
            if not self._is_session_expired(session_info):
                logger.debug(f'Reusing existing session: {session_info["session_id"]}')
                return session_info['session_id']
            else:
                logger.debug(f'Session expired, removing: {session_info["session_id"]}')
                del self._sessions[session_key]

        # Create new session with application name
        session_id = await self._create_session_with_app_name(
            cluster_identifier, database_name, cluster_info
        )

        # Store session
        self._sessions[session_key] = {'session_id': session_id, 'created_at': time.time()}

        logger.info(f'Created new session: {session_id} for {cluster_identifier}:{database_name}')
        return session_id

    async def _create_session_with_app_name(
        self, cluster_identifier: str, database_name: str, cluster_info: dict
    ) -> str:
        """Create a new session by executing SET application_name.

        Args:
            cluster_identifier: The cluster identifier.
            database_name: The database name.
            cluster_info: Cluster information dictionary.

        Returns:
            Session ID from the ExecuteStatement response.
        """
        # Set application name to create session
        app_name_sql = f"SET application_name TO '{self._app_name}';"

        # Execute statement to create session
        statement_id = await _execute_statement(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=app_name_sql,
            session_keepalive=self._session_keepalive,
        )

        # Get session ID from the response
        data_client = client_manager.redshift_data_client()
        status_response = data_client.describe_statement(Id=statement_id)
        session_id = status_response['SessionId']

        logger.debug(f'Created session with application name: {session_id}')
        return session_id

    def _is_session_expired(self, session_info: dict) -> bool:
        """Check if a session has expired based on keepalive timeout.

        Args:
            session_info: Session information dictionary.

        Returns:
            True if session is expired, False otherwise.
        """
        return (time.time() - session_info['created_at']) > self._session_keepalive


async def _execute_protected_statement(
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    allow_read_write: bool = False,
) -> tuple[dict, str]:
    """Execute a SQL statement against a Redshift cluster in a protected fashion.

    The SQL is protected by wrapping it in a transaction block with READ ONLY or READ WRITE mode
    based on allow_read_write flag. Transaction breaker protection is implemented
    to prevent unauthorized modifications.

    The SQL execution takes the form:
    1. Get or create session (with SET application_name)
    2. BEGIN [READ ONLY|READ WRITE];
    3. <user sql>
    4. END;

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        allow_read_write: Indicates if read-write mode should be activated.

    Returns:
        Tuple containing:
        - Dictionary with the raw results_response from get_statement_result.
          When the result spans multiple Data API pages, every page's
          ``Records`` are concatenated into a single list.
        - String with the query_id.

    Raises:
        Exception: If cluster not found, query fails, or times out.
    """
    # Get cluster info
    clusters = await discover_clusters()
    cluster_info = None
    for cluster in clusters:
        if cluster['identifier'] == cluster_identifier:
            cluster_info = cluster
            break

    if not cluster_info:
        raise Exception(
            f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
        )

    # Get session (creates if needed, sets app name automatically)
    session_id = await session_manager.session(cluster_identifier, database_name, cluster_info)

    # Check for suspicious patterns in read-only mode
    if not allow_read_write:
        if _is_suspicious(sql):
            sql_preview = (
                sql if len(sql) <= 500 else f'{sql[:500]}...(truncated, length={len(sql)})'
            )
            logger.error(f'SQL contains suspicious pattern, execution rejected: {sql_preview}')
            raise Exception('SQL contains suspicious pattern, execution rejected')

    # Execute BEGIN statement
    begin_sql = 'BEGIN READ WRITE;' if allow_read_write else 'BEGIN READ ONLY;'
    await _execute_statement(
        cluster_info=cluster_info,
        cluster_identifier=cluster_identifier,
        database_name=database_name,
        sql=begin_sql,
        session_id=session_id,
    )

    # Execute user SQL with parameters, ensuring transaction is always closed
    user_query_id = None
    user_sql_error = None

    try:
        user_query_id = await _execute_statement(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
            parameters=parameters,
            session_id=session_id,
        )
    except Exception as e:
        user_sql_error = e
        logger.error(f'User SQL execution failed: {e}')

    # Always execute END statement to close transaction
    try:
        await _execute_statement(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql='END;',
            session_id=session_id,
        )
    except Exception as end_error:
        logger.error(f'END statement execution failed: {end_error}')
        if user_sql_error:
            # Both failed - raise combined error
            raise Exception(
                f'User SQL failed: {user_sql_error}; END statement failed: {end_error}'
            )
        else:
            # Only END failed
            raise end_error

    # If user SQL failed but END succeeded, raise user SQL error
    if user_sql_error:
        raise user_sql_error

    # Get results from user query. Follow NextToken so the full result
    # set is returned even when it spans multiple Data API pages.
    data_client = client_manager.redshift_data_client()
    assert user_query_id is not None, 'user_query_id should not be None at this point'

    results_response = data_client.get_statement_result(Id=user_query_id)
    next_token = results_response.get('NextToken')
    while next_token:
        next_page = data_client.get_statement_result(Id=user_query_id, NextToken=next_token)
        results_response['Records'].extend(next_page.get('Records', []))
        next_token = next_page.get('NextToken')

    return results_response, user_query_id


async def _execute_statement(
    cluster_info: dict,
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    session_id: str | None = None,
    session_keepalive: int | None = None,
    query_poll_interval: float = QUERY_POLL_INTERVAL,
    query_timeout: float = QUERY_TIMEOUT,
) -> str:
    """Execute a single statement with optional session support and parameters.

    Args:
        cluster_info: Cluster information dictionary.
        cluster_identifier: The cluster identifier.
        database_name: The database name.
        sql: The SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        session_id: Optional session ID to use.
        session_keepalive: Optional session keepalive seconds (only used when session_id is None).
        query_poll_interval: Polling interval in seconds for checking query status.
        query_timeout: Maximum time in seconds to wait for query completion.

    Returns:
        Statement ID from the ExecuteStatement response.
    """
    data_client = client_manager.redshift_data_client()

    # Build request parameters
    request_params: dict[str, str | int | list[dict]] = {'Sql': sql}

    # Add database and cluster/workgroup identifier only if not using session
    if not session_id:
        request_params['Database'] = database_name
        if cluster_info['type'] == 'provisioned':
            request_params['ClusterIdentifier'] = cluster_identifier
        elif cluster_info['type'] == 'serverless':
            request_params['WorkgroupName'] = cluster_identifier
        else:
            raise Exception(f'Unknown cluster type: {cluster_info["type"]}')

    # Add parameters if provided
    if parameters:
        request_params['Parameters'] = parameters

    # Add session ID if provided, otherwise add session keepalive
    if session_id:
        request_params['SessionId'] = session_id
    elif session_keepalive is not None:
        request_params['SessionKeepAliveSeconds'] = session_keepalive

    response = data_client.execute_statement(**request_params)
    statement_id = response['Id']

    logger.debug(
        f'Executed statement: {statement_id}' + (f' in session {session_id}' if session_id else '')
    )

    # Wait for statement completion
    wait_time = 0
    while wait_time < query_timeout:
        status_response = data_client.describe_statement(Id=statement_id)
        status = status_response['Status']

        if status == 'FINISHED':
            logger.debug(f'Statement completed: {statement_id}')
            break
        elif status in ['FAILED', 'ABORTED']:
            error_msg = status_response.get('Error', 'Unknown error')
            logger.error(f'Statement failed: {error_msg}')
            raise Exception(f'Statement failed: {error_msg}')

        await asyncio.sleep(query_poll_interval)
        wait_time += query_poll_interval

    if wait_time >= query_timeout:
        logger.error(f'Statement timed out: {statement_id}')
        raise Exception(f'Statement timed out after {wait_time} seconds')

    return statement_id


async def discover_clusters() -> list[dict]:
    """Discover all Redshift clusters and serverless workgroups.

    Returns:
        List of cluster information dictionaries.
    """
    clusters = []

    try:
        # Get provisioned clusters
        logger.debug('Discovering provisioned Redshift clusters')
        redshift_client = client_manager.redshift_client()

        paginator = redshift_client.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_info = {
                    'identifier': cluster['ClusterIdentifier'],
                    'type': 'provisioned',
                    'status': cluster['ClusterStatus'],
                    'database_name': cluster.get('DBName', 'dev'),
                    'endpoint': cluster.get('Endpoint', {}).get('Address'),
                    'port': cluster.get('Endpoint', {}).get('Port'),
                    'vpc_id': cluster.get('VpcId'),
                    'node_type': cluster.get('NodeType'),
                    'number_of_nodes': cluster.get('NumberOfNodes'),
                    'creation_time': cluster.get('ClusterCreateTime'),
                    'master_username': cluster.get('MasterUsername'),
                    'publicly_accessible': cluster.get('PubliclyAccessible'),
                    'encrypted': cluster.get('Encrypted'),
                    'tags': {tag['Key']: tag['Value'] for tag in cluster.get('Tags', [])},
                }
                clusters.append(cluster_info)

        logger.info(f'Found {len(clusters)} provisioned clusters')

    except Exception as e:
        logger.error(f'Error discovering provisioned clusters: {str(e)}')
        raise

    try:
        # Get serverless workgroups
        logger.debug('Discovering Redshift Serverless workgroups')
        serverless_client = client_manager.redshift_serverless_client()

        paginator = serverless_client.get_paginator('list_workgroups')
        for page in paginator.paginate():
            for workgroup in page.get('workgroups', []):
                # Get detailed workgroup information
                workgroup_detail = serverless_client.get_workgroup(
                    workgroupName=workgroup['workgroupName']
                )['workgroup']

                cluster_info = {
                    'identifier': workgroup['workgroupName'],
                    'type': 'serverless',
                    'status': workgroup['status'],
                    'database_name': workgroup_detail.get('configParameters', [{}])[0].get(
                        'parameterValue', 'dev'
                    ),
                    'endpoint': workgroup_detail.get('endpoint', {}).get('address'),
                    'port': workgroup_detail.get('endpoint', {}).get('port'),
                    'vpc_id': workgroup_detail.get('subnetIds', [None])[
                        0
                    ],  # Approximate VPC from subnet
                    'node_type': None,  # Not applicable for serverless
                    'number_of_nodes': None,  # Not applicable for serverless
                    'creation_time': workgroup.get('creationDate'),
                    'master_username': None,  # Serverless uses IAM
                    'publicly_accessible': workgroup_detail.get('publiclyAccessible'),
                    'encrypted': True,  # Serverless is always encrypted
                    'tags': {tag['key']: tag['value'] for tag in workgroup_detail.get('tags', [])},
                }
                clusters.append(cluster_info)

        serverless_count = len([c for c in clusters if c['type'] == 'serverless'])
        logger.info(f'Found {serverless_count} serverless workgroups')

    except Exception as e:
        logger.error(f'Error discovering serverless workgroups: {str(e)}')
        raise

    logger.info(f'Total clusters discovered: {len(clusters)}')
    return clusters


async def discover_databases(cluster_identifier: str, database_name: str = 'dev') -> list[dict]:
    """Discover databases in a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to connect to for querying system views.

    Returns:
        List of database information dictionaries.
    """
    try:
        logger.info(f'Discovering databases in cluster {cluster_identifier}')

        # Execute the query using the common function
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=DATABASES_SQL,
        )

        databases = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
            database_info = {
                'database_name': record[0].get('stringValue'),
                'database_owner': record[1].get('longValue'),
                'database_type': record[2].get('stringValue'),
                'database_acl': record[3].get('stringValue'),
                'database_options': record[4].get('stringValue'),
                'database_isolation_level': record[5].get('stringValue'),
            }
            databases.append(database_info)

        logger.info(f'Found {len(databases)} databases in cluster {cluster_identifier}')
        return databases

    except Exception as e:
        logger.error(f'Error discovering databases in cluster {cluster_identifier}: {str(e)}')
        raise


async def discover_schemas(cluster_identifier: str, schema_database_name: str) -> list[dict]:
    """Discover schemas in a Redshift database using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        schema_database_name: The database name to filter schemas for. Also used to connect to.

    Returns:
        List of schema information dictionaries.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )

        # Execute the query using the common function
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=SCHEMAS_SQL,
            parameters=[{'name': 'database_name', 'value': schema_database_name}],
        )

        schemas = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
            schema_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'schema_owner': record[2].get('longValue'),
                'schema_type': record[3].get('stringValue'),
                'schema_acl': record[4].get('stringValue'),
                'source_database': record[5].get('stringValue'),
                'schema_option': record[6].get('stringValue'),
            }
            schemas.append(schema_info)

        logger.info(
            f'Found {len(schemas)} schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        logger.error(
            f'Error discovering schemas in database {schema_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_tables(
    cluster_identifier: str, table_database_name: str, table_schema_name: str
) -> list[dict]:
    """Discover tables in a Redshift schema using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        table_database_name: The database name to filter tables for. Also used to connect to.
        table_schema_name: The schema name to filter tables for.

    Returns:
        List of table information dictionaries.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )

        # Execute the main tables query
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=TABLES_SQL,
            parameters=[
                {'name': 'database_name', 'value': table_database_name},
                {'name': 'schema_name', 'value': table_schema_name},
            ],
        )

        tables = []
        records = results_response.get('Records', [])

        for record in records:
            table_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'table_name': record[2].get('stringValue'),
                'table_acl': record[3].get('stringValue'),
                'table_type': record[4].get('stringValue'),
                'remarks': record[5].get('stringValue'),
                'external_location': record[6].get('stringValue'),
                'external_parameters': record[7].get('stringValue'),
                # Initialize Redshift-specific fields as None
                'redshift_diststyle': None,
                'redshift_estimated_row_count': None,
                'stats_sequential_scans': None,
                'stats_sequential_tuples_read': None,
                'stats_rows_inserted': None,
                'stats_rows_updated': None,
                'stats_rows_deleted': None,
            }
            tables.append(table_info)

        # Try to fetch table info separately
        try:
            table_info_response, _ = await _execute_protected_statement(
                cluster_identifier=cluster_identifier,
                database_name=table_database_name,
                sql=TABLES_EXTRA_SQL,
                parameters=[
                    {'name': 'schema_name', 'value': table_schema_name},
                ],
            )

            # Create a lookup dictionary for table info
            # TABLES_EXTRA_SQL returns: schema_name(0), table_name(1), diststyle(2),
            # estimated_row_count(3), sequential_scans(4), sequential_tuples_read(5),
            # rows_inserted(6), rows_updated(7), rows_deleted(8)
            table_info_map: dict[str, dict[str, str | int | float | None]] = {}
            for record in table_info_response.get('Records', []):
                table_name = record[1].get('stringValue')  # table_name at index 1
                table_info_map[table_name] = {
                    'redshift_diststyle': record[2].get('stringValue'),
                    'redshift_estimated_row_count': record[3].get('longValue'),
                    'stats_sequential_scans': record[4].get('longValue'),
                    'stats_sequential_tuples_read': record[5].get('longValue'),
                    'stats_rows_inserted': record[6].get('longValue'),
                    'stats_rows_updated': record[7].get('longValue'),
                    'stats_rows_deleted': record[8].get('longValue'),
                }

            # Merge table info into tables
            for table in tables:
                table_name = table['table_name']
                if table_name in table_info_map:
                    table.update(table_info_map[table_name])

            logger.debug(
                f'Successfully enriched {len(table_info_map)} tables with extra stats data'
            )

        except Exception as table_info_error:
            # TABLES_EXTRA_SQL uses pg_class, pg_class_info, and pg_stat_user_tables which are
            # accessible to all users on both provisioned and serverless clusters.
            # If this fails, it's an unexpected error that should be raised.
            logger.error(f'Failed to fetch table extra stats: {table_info_error}')
            raise

        logger.info(
            f'Found {len(tables)} tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        logger.error(
            f'Error discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str,
) -> list[dict]:
    """Discover columns in a Redshift table using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        column_database_name: The database name to filter columns for. Also used to connect to.
        column_schema_name: The schema name to filter columns for.
        column_table_name: The table name to filter columns for.

    Returns:
        List of column information dictionaries.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=COLUMNS_SQL,
            parameters=[
                {'name': 'database_name', 'value': column_database_name},
                {'name': 'schema_name', 'value': column_schema_name},
                {'name': 'table_name', 'value': column_table_name},
            ],
        )

        columns = []
        records = results_response.get('Records', [])

        for record in records:
            column_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'table_name': record[2].get('stringValue'),
                'column_name': record[3].get('stringValue'),
                'ordinal_position': record[4].get('longValue'),
                'column_default': record[5].get('stringValue'),
                'is_nullable': record[6].get('stringValue'),
                'data_type': record[7].get('stringValue'),
                'character_maximum_length': record[8].get('longValue'),
                'numeric_precision': record[9].get('longValue'),
                'numeric_scale': record[10].get('longValue'),
                'remarks': record[11].get('stringValue'),
                'redshift_encoding': record[12].get('stringValue'),
                'redshift_is_distkey': record[13].get('booleanValue'),
                'redshift_sortkey_position': record[14].get('longValue'),
                'external_type': record[15].get('stringValue'),
                'external_partition_key': record[16].get('longValue'),
            }
            columns.append(column_info)

        logger.info(
            f'Found {len(columns)} columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(
            f'Error discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def execute_query(cluster_identifier: str, database_name: str, sql: str) -> dict:
    """Execute a SQL query against a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.

    Returns:
        Dictionary with query results including columns, rows, and metadata.
    """
    try:
        logger.info(f'Executing query on cluster {cluster_identifier} in database {database_name}')
        logger.debug(f'SQL: {sql}')

        # Record start time for execution time calculation
        import time

        start_time = time.time()

        # Execute the query using the common function
        results_response, query_id = await _execute_protected_statement(
            cluster_identifier=cluster_identifier, database_name=database_name, sql=sql
        )

        # Calculate execution time
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)

        # Extract column names
        columns = []
        column_metadata = results_response.get('ColumnMetadata', [])
        for col_meta in column_metadata:
            columns.append(col_meta.get('name'))

        # Extract rows
        rows = []
        records = results_response.get('Records', [])

        for record in records:
            row = []
            for field in record:
                # Extract the actual value from the field based on its type
                if 'stringValue' in field:
                    row.append(field['stringValue'])
                elif 'longValue' in field:
                    row.append(field['longValue'])
                elif 'doubleValue' in field:
                    row.append(field['doubleValue'])
                elif 'booleanValue' in field:
                    row.append(field['booleanValue'])
                elif 'isNull' in field and field['isNull']:
                    row.append(None)
                else:
                    # Fallback for unknown field types
                    row.append(str(field))
            rows.append(row)

        query_result = {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows),
            'execution_time_ms': execution_time_ms,
            'query_id': query_id,
        }

        logger.info(
            f'Query executed successfully: {query_id}, returned {len(rows)} rows in {execution_time_ms}ms'
        )
        return query_result

    except Exception as e:
        logger.error(f'Error executing query on cluster {cluster_identifier}: {str(e)}')
        raise


def _generate_performance_suggestions(
    parsed_nodes: list[dict], table_designs: list[dict]
) -> list[str]:
    """Generate performance optimization suggestions based on execution plan analysis.

    Args:
        parsed_nodes: List of parsed execution plan nodes.
        table_designs: List of table design information dictionaries.

    Returns:
        List of performance suggestion strings.
    """
    suggestions = []

    # Fixed-width types (int, bigint, date, timestamp) are excluded — compression
    # gain is small and avg_width is a poor signal for them.
    VARIABLE_LENGTH_TYPES = {
        'character varying',
        'varchar',
        'text',
        'super',
        'varbyte',
        'nvarchar',
    }
    # Character-length differences (e.g. varchar(10) = varchar(20)) don't
    # trigger implicit casts, so they're safe to skip in the join check below.
    CHAR_TYPES = {
        'character',
        'character varying',
        'varchar',
        'text',
        'nvarchar',
        'char',
        'bpchar',
    }
    # Numeric-type mismatches (e.g. integer = bigint) force implicit casts
    # that can defeat co-located joins.
    NUMERIC_TYPES = {
        'smallint',
        'integer',
        'bigint',
        'real',
        'double precision',
        'numeric',
        'decimal',
        'int2',
        'int4',
        'int8',
        'float4',
        'float8',
    }

    # Analyze distribution strategies in plan nodes
    for node in parsed_nodes:
        dist_type = node.get('distribution_type')
        operation = node.get('operation', '')

        # Check for data redistribution (expensive operations)
        if dist_type == 'DS_BCAST_INNER':
            suggestions.append(
                f'Data broadcast detected in {operation}. Consider using a common DISTKEY '
                'on join columns to co-locate data and avoid broadcasting.'
            )
        elif dist_type == 'DS_DIST_INNER':
            suggestions.append(
                f'Data redistribution detected in {operation}. Review DISTKEY choices '
                'to ensure joined tables are distributed on the join column.'
            )
        elif dist_type == 'DS_DIST_ALL_INNER':
            # DS_DIST_ALL_INNER means full table redistribution to all nodes
            # This is expensive for large tables but acceptable for small dimension tables
            suggestions.append(
                f'Full table redistribution detected in {operation}. '
                'For small dimension tables (< 1-2M rows), consider DISTSTYLE ALL to replicate data. '
                'For larger tables, align DISTKEYs on join columns to avoid redistribution.'
            )
        elif dist_type is None:
            # Keyword-fallback path: when distribution_type is unset
            # but the operation text contains an unambiguous
            # redistribution keyword, emit the corresponding
            # suggestion. Keywords are matched case-sensitively because
            # Redshift's EXPLAIN output capitalizes them as proper-noun
            # operation tokens (e.g. "XN Network Broadcast",
            # "XN Network Distribute", "Gather Motion").
            if 'Broadcast' in operation:
                suggestions.append(
                    f'Data broadcast detected in {operation}. Consider using a common DISTKEY '
                    'on join columns to co-locate data and avoid broadcasting.'
                )
            elif 'Distribute' in operation:
                suggestions.append(
                    f'Data redistribution detected in {operation}. Review DISTKEY choices '
                    'to ensure joined tables are distributed on the join column.'
                )
            elif 'Gather' in operation:
                suggestions.append(
                    f'Data gather detected in {operation}. Review DISTKEY choices '
                    'to ensure joined tables are distributed on the join column.'
                )

        # Check for nested loops (often indicates missing join condition)
        if 'Nested Loop' in operation:
            suggestions.append(
                'Nested Loop join detected. Verify join conditions are correct. '
                'For large tables, Hash Join or Merge Join are typically more efficient.'
            )

    # Build a column name -> (table, data_type) lookup for the join type-
    # mismatch check below. Join conditions expose only column names, so we
    # index by name; ambiguous matches are skipped.
    col_type_index: dict[str, list[tuple[str, str]]] = {}
    for td in table_designs:
        td_table = td.get('table_name', '')
        for col in td.get('columns', []):
            c_name = col.get('column_name')
            c_type = (col.get('data_type') or '').strip()
            if c_name and c_type:
                col_type_index.setdefault(c_name, []).append((td_table, c_type))

    # Check join-column data-type mismatches (force implicit casts).
    if col_type_index:
        join_eq_pattern = regex.compile(
            r'(?:"?(\w+)"?\.)?"?(\w+)"?\s*=\s*(?:"?(\w+)"?\.)?"?(\w+)"?'
        )
        for node in parsed_nodes:
            cond = node.get('join_condition') or ''
            filt = node.get('join_filter') or ''
            combined = f'{cond} {filt}'.strip()
            if not combined:
                continue
            for m in join_eq_pattern.finditer(combined):
                lcol, rcol = m.group(2), m.group(4)
                ltypes = col_type_index.get(lcol, [])
                rtypes = col_type_index.get(rcol, [])
                if not ltypes or not rtypes:
                    continue
                _, ltype = ltypes[0]
                _, rtype = rtypes[0]
                if ltype == rtype:
                    continue
                lbase = ltype.split('(')[0].strip().lower()
                rbase = rtype.split('(')[0].strip().lower()
                if lbase in CHAR_TYPES and rbase in CHAR_TYPES:
                    continue
                if lbase in NUMERIC_TYPES and rbase in NUMERIC_TYPES:
                    suggestions.append(
                        f'Join columns {lcol} ({ltype}) and {rcol} ({rtype}) '
                        'have mismatched numeric types. The planner will insert '
                        'implicit casts which can degrade join performance and '
                        'prevent co-located joins. Consider aligning the column types.'
                    )

    # Analyze table designs
    for table in table_designs:
        schema_name = table.get('schema_name', '')
        table_name = table.get('table_name', '')
        redshift_diststyle = table.get('redshift_diststyle', '')
        redshift_tbl_rows = table.get('redshift_estimated_row_count')
        columns = table.get('columns', [])

        full_name = f'{schema_name}.{table_name}' if schema_name else table_name

        # Suggest DISTSTYLE ALL for small dimension tables
        # Small tables benefit from replication to avoid redistribution during joins
        if redshift_tbl_rows is not None and redshift_tbl_rows < 2000000:  # < 2M rows
            if redshift_diststyle in ('EVEN', 'KEY', 'AUTO(EVEN)', 'AUTO(KEY)'):
                suggestions.append(
                    f'Table {full_name} is small ({redshift_tbl_rows:,} rows) and uses {redshift_diststyle} distribution. '
                    'Consider DISTSTYLE ALL to replicate this dimension table and eliminate redistribution during joins.'
                )
        # Check for EVEN distribution on larger tables (may cause redistribution)
        elif redshift_diststyle == 'EVEN':
            suggestions.append(
                f'Table {full_name} uses EVEN distribution. If this table is frequently '
                'joined, consider using DISTKEY on the join column to improve performance.'
            )

        # NOTE: The "no SORTKEY" rule is implemented in the
        # table-activity-stats pass below (driven by
        # stats_sequential_scans). Emitting a SORTKEY suggestion here
        # unconditionally would bypass the documented suppressions
        # (DISTSTYLE ALL/AUTO(ALL), small tables, zero scans).

        # Check for low correlation on non-sortkey columns (poor zone map effectiveness).
        # Suppress for small tables and low-cardinality columns where zone maps
        # are effective regardless of correlation.
        for col in columns:
            correlation = col.get('stats_correlation')
            sortkey_pos = col.get('redshift_sortkey_position', 0)
            col_name = col.get('column_name', '')
            if correlation is None or sortkey_pos != 0:
                continue
            if not (-0.2 < correlation < 0.2):
                continue
            if redshift_tbl_rows is not None and redshift_tbl_rows < 100000:
                continue
            n_distinct = col.get('stats_n_distinct')
            if n_distinct is not None:
                effective_distinct = (
                    n_distinct if n_distinct > 0 else abs(n_distinct) * (redshift_tbl_rows or 0)
                )
                if 0 < effective_distinct < 20:
                    continue
            suggestions.append(
                f'Column {col_name} in {full_name} has low correlation '
                f'({correlation:.2f}), meaning physical row order does not match value order. '
                'If this column is frequently used in range filters or WHERE clauses, '
                'consider adding it as a SORTKEY for better zone map block skipping.'
            )

        # Check for low-cardinality DISTKEY columns (selectivity-based to avoid
        # flagging small tables with proportionally few distinct values).
        for col in columns:
            n_distinct = col.get('stats_n_distinct')
            is_distkey = col.get('redshift_is_distkey')
            col_name = col.get('column_name', '')
            if not (is_distkey and n_distinct is not None):
                continue
            # Positive n_distinct = absolute count, negative = fraction of rows
            effective_distinct = (
                n_distinct if n_distinct > 0 else abs(n_distinct) * (redshift_tbl_rows or 0)
            )
            if n_distinct < 0:
                selectivity = abs(n_distinct)
            elif redshift_tbl_rows and redshift_tbl_rows > 0:
                selectivity = n_distinct / redshift_tbl_rows
            else:
                selectivity = None
            # Flag only if absolute count is low AND selectivity < 0.1%.
            if 0 < effective_distinct < 100 and selectivity is not None and selectivity < 0.001:
                suggestions.append(
                    f'DISTKEY column {col_name} in {full_name} has low cardinality '
                    f'(~{int(effective_distinct)} distinct values across '
                    f'{redshift_tbl_rows:,} rows), which causes data skew across slices. '
                    'Consider choosing a higher-cardinality column as DISTKEY.'
                )

        # Check for high NULL fraction on SORTKEY columns.
        # A SORTKEY on a mostly-NULL column provides little zone map benefit.
        for col in columns:
            null_frac = col.get('stats_null_frac')
            sortkey_pos = col.get('redshift_sortkey_position', 0)
            col_name = col.get('column_name', '')
            if null_frac is not None and sortkey_pos > 0 and null_frac > 0.9:
                suggestions.append(
                    f'SORTKEY column {col_name} in {full_name} is {null_frac:.0%} NULL. '
                    'Zone maps are less effective on mostly-NULL sort keys. '
                    'Consider choosing a less sparse column as SORTKEY.'
                )

        # Check for wide uncompressed variable-length columns (high storage/IO impact).
        wide_raw_columns = [
            col['column_name']
            for col in columns
            if col.get('redshift_encoding') == 'none'
            and col.get('stats_avg_width') is not None
            and col.get('stats_avg_width') > 200
            and (col.get('data_type') or '').lower() in VARIABLE_LENGTH_TYPES
        ]
        if wide_raw_columns:
            suggestions.append(
                f'Wide columns {", ".join(wide_raw_columns)} in {full_name} have no compression '
                'and high average width (>200 bytes). Compressing these columns would significantly '
                'reduce storage and improve I/O performance.'
            )

        # Check for RAW encoding (no compression). Exclude the first SORTKEY
        # column (must stay RAW for zone maps) and BOOLEAN columns (cannot be
        # encoded in Redshift).
        raw_columns = [
            col['column_name']
            for col in columns
            if col.get('redshift_encoding') == 'none'
            and col.get('redshift_sortkey_position', 0) != 1
            and (col.get('data_type') or '').lower() != 'boolean'
        ]
        if raw_columns and len(raw_columns) <= 3:
            suggestions.append(
                f'Columns {", ".join(raw_columns)} in {full_name} have no compression. '
                'Consider using ENCODE AUTO or specific encodings to reduce storage and improve I/O.'
            )
        elif raw_columns:
            suggestions.append(
                f'{len(raw_columns)} columns in {full_name} have no compression. '
                'Consider using ENCODE AUTO to improve storage efficiency.'
            )

    # Analyze table activity stats for performance insights
    for table in table_designs:
        schema_name = table.get('schema_name', '')
        table_name = table.get('table_name', '')
        redshift_diststyle = table.get('redshift_diststyle', '')
        redshift_tbl_rows = table.get('redshift_estimated_row_count')
        full_name = f'{schema_name}.{table_name}' if schema_name else table_name

        # High sequential scans without sort key. Suppress for small tables
        # and DISTSTYLE ALL (seq scan is the expected access pattern there).
        seq_scans = table.get('stats_sequential_scans')
        columns = table.get('columns', [])
        has_sortkey = any(col.get('redshift_sortkey_position', 0) > 0 for col in columns)
        if (
            seq_scans is not None
            and seq_scans > 1000
            and not has_sortkey
            and columns
            and (redshift_tbl_rows is None or redshift_tbl_rows >= 100000)
            and redshift_diststyle not in ('ALL', 'AUTO(ALL)')
        ):
            suggestions.append(
                f'Table {full_name} has {seq_scans:,} sequential scans and no SORTKEY. '
                'Adding a SORTKEY on frequently filtered columns can reduce scan I/O.'
            )

    # Remove duplicates while preserving order. If deduplication
    # raises for any reason, fall back to returning all generated
    # suggestions including duplicates rather than raising or omitting
    # suggestions.
    try:
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        return unique_suggestions
    except Exception:
        return suggestions


async def describe_execution_plan(cluster_identifier: str, database_name: str, sql: str) -> dict:
    """Get the execution plan for a SQL query using plain ``EXPLAIN``.

    Runs ``EXPLAIN <sql>`` against the cluster, parses the output into
    structured plan nodes, resolves the user's table references against
    the connected database, batch-fetches design metadata and column
    statistics, and runs the rule-based suggestion engine.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to explain. Must not begin with
            ``EXPLAIN``; the tool prepends it.

    Returns:
        Dictionary matching the :class:`ExecutionPlan` schema:
        ``query_id``, ``explained_query``, ``planning_time_ms``,
        ``plan_text``, ``plan_nodes``, ``table_designs``, ``notes``,
        ``rule_based_suggestions``.
    """
    try:
        logger.info(
            f'Getting execution plan for query on cluster {cluster_identifier} in database {database_name}'
        )
        logger.debug(f'SQL to explain: {sql}')

        # Reject empty/whitespace-only SQL before any cluster call.
        if not sql or not sql.strip():
            raise Exception('SQL is required and must not be empty or whitespace.')

        # The tool prepends EXPLAIN itself; user SQL must not already contain it.
        sql_trimmed = sql.strip().upper()
        if sql_trimmed.startswith('EXPLAIN'):
            raise Exception(
                'SQL already contains EXPLAIN. Please provide the query without EXPLAIN.'
            )

        explain_sql = f'EXPLAIN {sql}'

        start_time = time.time()

        results_response, query_id = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=explain_sql,
        )

        planning_time_ms = int((time.time() - start_time) * 1000)

        # Collect raw records; they feed both the human-readable
        # ``plan_text`` and the structured ``plan_nodes``.
        raw_records: list[str] = []
        for record in results_response.get('Records', []):
            if record and len(record) > 0:
                raw_records.append(record[0].get('stringValue', '') or '')

        plan_text = '\n'.join(raw_records)

        notes: list[str] = []

        plan_nodes = _parse_plan_text(raw_records)

        # Extract table references from the user's SQL (not the EXPLAIN
        # output); soft-fail so plan_text/plan_nodes still surface.
        try:
            references = _extract_sql_references(sql)
        except SqlReferenceExtractError as ref_error:
            logger.warning(
                f'SQL reference extraction failed: {ref_error}; '
                'continuing with empty reference list.'
            )
            references = []

        resolved_pairs, detector_notes = await _resolve_ambiguities(
            cluster_identifier=cluster_identifier,
            connected_database_name=database_name,
            references=references,
        )
        notes.extend(detector_notes)

        metadata_by_pair = await _fetch_table_metadata(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            pairs=resolved_pairs,
        )

        # Sort for deterministic output. _resolve_ambiguities already deduplicated.
        sorted_pairs = sorted(resolved_pairs)

        # Single batched column-stats fetch across all resolved pairs;
        # failure here MUST NOT cancel the rest of the response.
        col_stats_map: dict[tuple[str, str], dict[str, dict]] = {}
        if sorted_pairs:
            try:
                rendered_pairs = _render_schema_table_pairs(sorted_pairs)
                stats_sql = COLUMN_STATS_SQL.format(schema_table_pairs=rendered_pairs)
                stats_response, _ = await _execute_protected_statement(
                    cluster_identifier=cluster_identifier,
                    database_name=database_name,
                    sql=stats_sql,
                )
                # COLUMN_STATS_SQL fields: schema_name(0), table_name(1),
                # column_name(2), n_distinct(3), null_frac(4), avg_width(5),
                # correlation(6), most_common_vals(7), most_common_freqs(8),
                # histogram_bounds(9).
                for record in stats_response.get('Records', []):
                    schema_v = record[0].get('stringValue')
                    table_v = record[1].get('stringValue')
                    col_v = record[2].get('stringValue')
                    if schema_v and table_v and col_v:
                        key = (schema_v, table_v)
                        if key not in col_stats_map:
                            col_stats_map[key] = {}
                        col_stats_map[key][col_v] = {
                            'stats_n_distinct': record[3].get('doubleValue'),
                            'stats_null_frac': record[4].get('doubleValue'),
                            'stats_avg_width': record[5].get('longValue'),
                            'stats_correlation': record[6].get('doubleValue'),
                            'stats_most_common_vals': record[7].get('stringValue'),
                            'stats_most_common_freqs': record[8].get('stringValue'),
                            'stats_histogram_bounds': record[9].get('stringValue'),
                        }
                logger.debug(f'Fetched column stats for {len(col_stats_map)} tables in one batch')
            except Exception as stats_error:
                logger.warning(f'Could not fetch batch column stats: {stats_error}')

        # Single batched columns fetch across all resolved pairs;
        # failure here MUST NOT cancel the rest of the response.
        columns_by_pair = await _fetch_columns_by_pairs(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            pairs=resolved_pairs,
        )

        table_designs: list[dict] = []
        for schema_name, table_name in sorted_pairs:
            columns = columns_by_pair.get((schema_name, table_name), [])

            # Enrich columns with pre-fetched planner statistics.
            table_col_stats = col_stats_map.get((schema_name, table_name), {})
            for col in columns:
                col_name = col.get('column_name')
                if col_name and col_name in table_col_stats:
                    col.update(table_col_stats[col_name])

            # Merge batched table metadata; emit even on miss so every
            # referenced table appears in the response.
            metadata = metadata_by_pair.get((schema_name, table_name), {})
            table_design: dict = {
                'database_name': database_name,
                'schema_name': schema_name,
                'table_name': table_name,
                **metadata,
                'columns': columns,
            }
            table_designs.append(table_design)
            logger.debug(
                f'Built design for {schema_name}.{table_name}: '
                f'{table_design.get("redshift_diststyle")} with {len(columns)} columns'
            )

        # Suggestion engine consumes dict-shaped nodes.
        plan_nodes_dicts = [node.model_dump() for node in plan_nodes]
        rule_based_suggestions = _generate_performance_suggestions(plan_nodes_dicts, table_designs)

        execution_plan = {
            'query_id': query_id,
            'explained_query': sql,
            'planning_time_ms': planning_time_ms,
            'plan_text': plan_text,
            'plan_nodes': plan_nodes_dicts,
            'table_designs': table_designs,
            'notes': notes,
            'rule_based_suggestions': rule_based_suggestions,
        }

        logger.info(
            f'Execution plan generated successfully: {query_id}, '
            f'{len(raw_records)} plan records, {len(plan_nodes)} plan nodes, '
            f'{len(table_designs)} table designs, '
            f'{len(rule_based_suggestions)} suggestions, '
            f'{len(notes)} notes in {planning_time_ms}ms'
        )
        return execution_plan

    except Exception as e:
        logger.error(f'Error getting execution plan for cluster {cluster_identifier}: {str(e)}')
        raise


# Global client manager instance
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'md/awslabs#mcp#redshift-mcp-server#{__version__}',
    ),
    aws_region=os.environ.get('AWS_REGION'),
    aws_profile=os.environ.get('AWS_PROFILE'),
)

# Global session manager instance
session_manager = RedshiftSessionManager(
    session_keepalive=SESSION_KEEPALIVE, app_name=f'{CLIENT_USER_AGENT_NAME}/{__version__}'
)
