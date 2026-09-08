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

"""Parser-based SQL policy for the Postgres MCP Server.

Replaces the former regex-based ``mutable_sql_detector`` with a guard built on
``pglast`` (libpg_query -- PostgreSQL's own parser compiled in), so identifiers,
string literals, comments, and Unicode escapes cannot disguise an operation:
the checker and the database read the same bytes the same way.

Two classifications (see docs/design/parser-based-sql-policy.md, section 3.1):

* Write set -- mutating / state-changing statements. Enforced fail-closed as an
  allowlist: in read-only mode only read *statement* node types are permitted
  anywhere in the parse tree; any other statement node is a write and is
  rejected. Function calls are classified separately and only best-effort: a
  small denylist of clearly-mutating built-ins (sequence ``nextval``/``setval``,
  the ``pg_stat_reset*`` family, ``pg_logical_emit_message``) and ``set_config``
  are rejected in read-only mode, but an arbitrary user-defined or volatile
  function that writes internally cannot be recognized from syntax (§5.6). Those
  remain owned by the least-privilege database role and the backend
  ``SET TRANSACTION READ ONLY`` backstop -- which stops DML and ``setval`` but
  not ``nextval``/``pg_stat_reset*``/``pg_logical_emit_message``, which is why
  those are enumerated here.
* Dangerous set -- command execution / SSRF / host filesystem / DoS /
  security-control-disabling constructs. Rejected in BOTH modes (defense in
  depth; the authoritative control is the least-privilege database role).

The dangerous-set check inspects only constructs the parser surfaces as nodes.
The body of a ``DO`` block, a ``CREATE FUNCTION``/``CREATE PROCEDURE``, and any
SQL assembled at run time (``EXECUTE`` dynamic SQL) parse as an opaque string,
not as nested statement/function nodes, so a dangerous call hidden inside such a
body is NOT seen here. In read-only mode this is moot -- ``DO`` and
``CREATE FUNCTION`` are non-read statement types and are rejected outright. In
write mode they are permitted, so an opaque body is the §5.6 semantic gap that
no static parser closes; the authoritative control there is the least-privilege
database role, which is privilege-checked on the resolved object at execution
time regardless of how the SQL was written.

This guard is defense-in-depth, not a security boundary. It fails closed: any
parse error, oversized input, or multi-statement submission is rejected.
"""

import re
from loguru import logger
from pglast import ast, parse_sql
from typing import NoReturn


# Maximum accepted SQL length; oversized input is rejected fail-closed.
# Aligned with redshift-mcp-server's MAX_SQL_LEN.
MAX_SQL_LEN = 65_536

# --- Read-only allowlist (write-set enforcement) ---------------------------
# The only statement node types permitted in read-only mode. SelectStmt covers
# SELECT / WITH ... SELECT / VALUES / TABLE. RawStmt is the per-statement
# wrapper. ExplainStmt / VariableShowStmt are read wrappers (their inner query,
# for EXPLAIN, is validated by the same tree walk). Any other *Stmt node
# anywhere in the tree is, by definition, in the write set and is rejected.
READ_ONLY_ALLOWED_ROOT = frozenset({'SelectStmt', 'VariableShowStmt', 'ExplainStmt'})
READ_ONLY_ALLOWED_STMT_NODES = frozenset(
    {'RawStmt', 'SelectStmt', 'VariableShowStmt', 'ExplainStmt'}
)

# The one write-set member that is a function rather than a statement node.
# set_config(name, value, is_local) is the function form of SET; it mutates
# session state for any GUC and so is rejected in read-only mode.
READ_ONLY_PROHIBITED_FUNCTIONS = frozenset({'set_config'})

# Clearly-mutating built-in functions that parse as a FuncCall inside an
# otherwise-read SelectStmt, so the statement-node allowlist does not catch
# them. Rejected in read-only mode. This is best-effort defense-in-depth, NOT a
# complete guarantee: an arbitrary user-defined or volatile function that writes
# internally cannot be recognized from syntax (§5.6) and remains owned by the
# database role and the backend SET TRANSACTION READ ONLY backstop. The point of
# enumerating these is that PostgreSQL's read-only transaction does NOT block
# them -- nextval(), pg_stat_reset*(), and pg_logical_emit_message() all execute
# in a read-only transaction (unlike setval()/DML, which PreventCommandIfReadOnly
# stops) -- so listing them closes a real residual gap. None has any legitimate
# use in a read query. currval()/lastval() are reads and are deliberately absent.
READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS = frozenset(
    {
        # Sequence writes. nextval advances the sequence; setval sets it.
        'nextval',
        'setval',
        # Statistics-reset family -- destroys the cluster's cumulative stats.
        'pg_stat_reset',
        'pg_stat_reset_shared',
        'pg_stat_reset_single_table_counters',
        'pg_stat_reset_single_function_counters',
        'pg_stat_reset_slru',
        'pg_stat_reset_replication_slot',
        'pg_stat_reset_subscription_stats',
        # Emits a WAL record.
        'pg_logical_emit_message',
    }
)

# --- Dangerous set (rejected in BOTH modes) --------------------------------
# Bare function names matched against the final element of the (possibly
# schema-qualified) function name, so pg_catalog.pg_read_file and pg_read_file
# are detected identically. pglast has already decoded any U&/quoted spelling,
# so the value compared is the real resolved name.
DANGEROUS_FUNCTIONS = frozenset(
    {
        # DoS: session control.
        'pg_cancel_backend',
        'pg_terminate_backend',
        # DoS: connection hold / pool exhaustion.
        'pg_sleep',
        'pg_sleep_for',
        'pg_sleep_until',
        # Filesystem read.
        'pg_read_file',
        'pg_read_binary_file',
        'pg_stat_file',
        'lo_import',
        'lo_export',
        # Filesystem enumeration -- pg_ls_dir and its siblings (Tier 1).
        'pg_ls_dir',
        'pg_ls_logdir',
        'pg_ls_waldir',
        'pg_ls_tmpdir',
        'pg_ls_archive_statusdir',
        'pg_ls_logicalmapdir',
        'pg_ls_logicalsnapdir',
        'pg_ls_replslotdir',
        # Host file write / RCE -- adminpack (Tier 2). pg_file_write is an
        # arbitrary host-file write.
        'pg_file_write',
        'pg_file_sync',
        'pg_file_rename',
        'pg_file_unlink',
        'pg_logdir_ls',
        # Server control.
        'pg_reload_conf',
        'pg_rotate_logfile',
        # Advisory-lock family -- application-level DoS.
        'pg_advisory_lock',
        'pg_advisory_lock_shared',
        'pg_advisory_xact_lock',
        'pg_advisory_xact_lock_shared',
        'pg_try_advisory_lock',
        'pg_try_advisory_lock_shared',
        'pg_try_advisory_xact_lock',
        'pg_try_advisory_xact_lock_shared',
        # NOTIFY-channel side channel.
        'pg_notify',
        # dblink family -- Server-Side Request Forgery.
        'dblink',
        'dblink_connect',
        'dblink_connect_u',
        'dblink_exec',
        'dblink_send_query',
        'dblink_open',
        'dblink_fetch',
        'dblink_close',
        'dblink_get_connections',
    }
)

# Schema-qualified dangerous functions (Tier 3). Matched against the full
# (schema, name) pair rather than the bare last element, because these
# extension functions have generic last names (e.g. aws_lambda.invoke -> the
# bare name "invoke" would over-block innocent user functions). Stored and
# compared lowercased.
DANGEROUS_QUALIFIED_FUNCTIONS = frozenset(
    {
        ('aws_lambda', 'invoke'),  # invoke a Lambda function from SQL
        ('aws_s3', 'query_export_to_s3'),  # data exfiltration to S3
        ('aws_s3', 'table_import_from_s3'),  # external fetch / write
    }
)

# GUCs that disable data-access or integrity controls. Rejected in BOTH modes
# whether set via the SET statement or the set_config() function form.
SECURITY_SENSITIVE_GUCS = frozenset({'row_security', 'session_replication_role'})

# Aurora / RDS Data API style named placeholders (``:name``) are not valid
# PostgreSQL syntax, so pglast cannot parse a statement that contains them. For
# parsing only, substitute a positional placeholder ($1) -- a value position, so
# it never changes the statement type, function names, or GUC targets the guard
# classifies. Only the guard's copy is rewritten; the ORIGINAL SQL is what
# executes (the RDS Data API binds ``:name`` parameters natively).
#
# The negative lookbehind refuses to rewrite a colon preceded by ``:`` (the
# ``::`` cast operator), a word character, ``]``, or ``)``. None of those
# prefixes can begin a real ``:name`` placeholder, but each occurs before an
# array-slice colon whose lower bound is non-empty (``a[1:n]``, ``a[i:j]``,
# ``a[f():n]``, ``a[b[0]:n]``). Leaving the slice colon alone lets pglast parse
# the slice as ordinary SQL. Without this guard, ``a[1:n]`` was rewritten to the
# unparseable ``a[1$1]`` and valid queries such as
# ``SELECT tags[1:limit_idx] FROM items`` were wrongly rejected. A placeholder in
# a value position is still matched: ``= :id``, ``id=:id``, ``(:a, :b)``,
# ``ARRAY[:a]``, ``:v::int``. (A slice with an omitted lower bound, ``a[:n]``,
# becomes ``a[$1]`` -- a subscript that still parses, and the guard inspects only
# structure, so the classification is unaffected.)
#
# The substitution is not literal-aware, so a ``:name``-shaped sequence inside a
# string literal (``SELECT 'ping :host'`` -> ``SELECT 'ping $1'``) is rewritten
# too. This is deliberately safe: the guard only inspects statement node types,
# function names, and GUC names -- never arbitrary string contents -- and ``$1``
# inside quotes remains a string literal, so classification is unaffected.
_NAMED_PARAM_PATTERN = re.compile(r'(?<![\w:\]\)]):([a-zA-Z_]\w*)')


def _normalize_placeholders(sql: str) -> str:
    """Replace ``:name`` placeholders with ``$1`` so pglast can parse (parse-only)."""
    return _NAMED_PARAM_PATTERN.sub('$1', sql)


class SqlPolicyError(Exception):
    """Raised when a SQL statement is rejected by the policy guard.

    The message is non-sensitive and names the offending construct; it does not
    echo secrets or parser internals.
    """


def _reject(reason: str, cause: BaseException | None = None) -> NoReturn:
    """Log and raise for a rejected query.

    Args:
        reason: Non-sensitive explanation surfaced to the caller.
        cause: Optional underlying exception to chain so the real error is not
            hidden in logs.

    Raises:
        SqlPolicyError: Always, with ``reason`` (chained from ``cause`` when given).
    """
    logger.warning(f'SQL policy guard rejected query: {reason}')
    if cause is not None:
        raise SqlPolicyError(reason) from cause
    raise SqlPolicyError(reason)


def _collect_nodes(raw_stmt: ast.Node) -> list:
    """Return every node in the parse tree rooted at ``raw_stmt`` (RawStmt).

    Iterative (explicit stack) rather than recursive: a deeply nested statement
    (e.g. thousands of nested ``NOT (...)``) produces a deep parse tree that
    would blow Python's recursion limit and escape as an uncaught
    ``RecursionError``. Input size is capped by ``MAX_SQL_LEN``, so the tree is
    bounded. Traversal order does not matter -- the checks scan the flat list.
    """
    out: list = []
    stack: list = [raw_stmt]
    while stack:
        item = stack.pop()
        if isinstance(item, ast.Node):
            out.append(item)
            # pglast Node.__iter__ yields attribute names; push their values.
            for attr in item:
                stack.append(getattr(item, attr, None))
        elif isinstance(item, (tuple, list)):
            stack.extend(item)
        # scalars (str / int / enum / None) hold no child nodes -> skip.
    return out


def _func_name_parts(node: ast.FuncCall) -> list[str]:
    """Return the (lowercased) dotted components of a FuncCall's name."""
    parts = []
    for element in node.funcname or ():
        sval = getattr(element, 'sval', None)
        if sval is not None:
            parts.append(sval.lower())
    return parts


def _first_arg_string(node: ast.FuncCall) -> str | None:
    """Return the first argument of a FuncCall if it is a string literal, else None."""
    args = node.args or ()
    if not args:
        return None
    first = args[0]
    if isinstance(first, ast.A_Const):
        return getattr(first.val, 'sval', None)
    return None


def _check_dangerous(node) -> None:
    """Reject dangerous constructs that are prohibited in BOTH modes.

    Args:
        node: A node from the parse tree.

    Raises:
        SqlPolicyError: If the node is a dangerous construct (see section 3.1).
    """
    # COPY ... TO/FROM PROGRAM (command execution) or a server-side file target
    # (host filesystem read/write). STDIN/STDOUT present as is_program=False,
    # filename=None and are handled by the read-only write-set check instead.
    if isinstance(node, ast.CopyStmt):
        if node.is_program:
            _reject('COPY ... TO/FROM PROGRAM executes a host command (RCE)')
        if node.filename is not None:
            _reject('COPY ... TO/FROM a server-side file accesses the host filesystem')
        return

    if isinstance(node, ast.FuncCall):
        parts = _func_name_parts(node)
        if not parts:  # pragma: no cover - defensive; a FuncCall always has a name
            return
        bare = parts[-1]
        if bare in DANGEROUS_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {bare}')
        if len(parts) >= 2 and (parts[-2], bare) in DANGEROUS_QUALIFIED_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {parts[-2]}.{bare}')
        # set_config() targeting a security-sensitive GUC (function form of SET).
        if bare == 'set_config':
            guc = _first_arg_string(node)
            if guc is None:
                # The GUC name is not a resolvable string literal -- it is a
                # concatenation, a bound parameter, a column, or a function
                # call (e.g. set_config('row_' || 'security', 'off', false) or
                # set_config($1, 'off', false)). We cannot prove it is not a
                # security-sensitive GUC, so fail closed. In write mode a
                # computed name could disable row_security /
                # session_replication_role, and because connections are pooled
                # that leak persists for every later query on the connection. A
                # dynamic GUC name has no legitimate use in an agent query. (In
                # read-only mode any set_config is already rejected by the
                # write-set check.)
                _reject('set_config() with a non-literal GUC name is not allowed')
            if guc.lower() in SECURITY_SENSITIVE_GUCS:
                _reject(f'Security-sensitive session setting not allowed: {guc}')
        return

    # SET / RESET ... targeting a security-sensitive GUC. This matches any
    # VariableSetStmt naming a sensitive GUC, so RESET row_security is rejected
    # alongside SET -- intentional: RESET reverts the GUC to a default that a
    # superuser could have set to a weaker value, so both are blocked in both
    # modes (conservative, safe direction).
    if isinstance(node, ast.VariableSetStmt):
        name = (node.name or '').lower()
        if name in SECURITY_SENSITIVE_GUCS:
            _reject(f'Security-sensitive session setting not allowed: {node.name}')


def _check_read_only(root, nodes: list) -> None:
    """Reject write-set constructs when the connection is read-only.

    Enforced fail-closed as an allowlist: the root must be a read node type and
    every statement node in the tree must be a permitted read type. Write-set
    members that parse as an allowed ``SelectStmt`` are caught by explicit field
    checks: ``SELECT ... INTO`` (a table-creating write), ``set_config()``
    (session-state mutation for any GUC), and the clearly-mutating built-in
    functions in ``READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS``
    (``nextval``/``setval``, ``pg_stat_reset*``, ``pg_logical_emit_message``)
    that the ``SET TRANSACTION READ ONLY`` backstop does not stop. Arbitrary
    user-defined/volatile writer functions remain undetectable from syntax
    (§5.6) and are owned by the database role.

    Args:
        root: The single top-level statement node (``RawStmt.stmt``).
        nodes: Every node in the parse tree.

    Raises:
        SqlPolicyError: If any write-set construct is present.
    """
    root_type = type(root).__name__
    if root_type not in READ_ONLY_ALLOWED_ROOT:
        _reject(f'Statement type not allowed in read-only mode: {root_type}')

    for node in nodes:
        node_type = type(node).__name__
        # Any statement node that is not a permitted read type is a write.
        if node_type.endswith('Stmt') and node_type not in READ_ONLY_ALLOWED_STMT_NODES:
            _reject(f'Statement type not allowed in read-only mode: {node_type}')
        # SELECT ... INTO creates a table -- a write disguised as a SelectStmt.
        if isinstance(node, ast.SelectStmt) and node.intoClause is not None:
            _reject('SELECT ... INTO creates a table and is not allowed in read-only mode')
        # set_config() for any GUC mutates session state; and the clearly
        # -mutating built-ins the read-only transaction does not stop
        # (nextval/setval, pg_stat_reset*, pg_logical_emit_message).
        if isinstance(node, ast.FuncCall):
            parts = _func_name_parts(node)
            if not parts:  # pragma: no cover - defensive; a FuncCall always has a name
                continue
            fn = parts[-1]
            if fn in READ_ONLY_PROHIBITED_FUNCTIONS:
                _reject('set_config() mutates session state and is not allowed in read-only mode')
            if fn in READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS:
                _reject(f'Function mutates state and is not allowed in read-only mode: {fn}')


def assert_executable(sql: str, allow_write_query: bool = False) -> None:
    """Validate that ``sql`` is a single permitted statement, else raise.

    Fails closed: oversized input, any parser error, and multi- or zero-statement
    submissions are rejected. Dangerous constructs are rejected regardless of
    ``allow_write_query`` *when the parser surfaces them as nodes*; a dangerous
    call hidden inside an opaque body (a ``DO``/``CREATE FUNCTION`` body or
    ``EXECUTE`` dynamic SQL) is not inspected. In read-only mode those statement
    types are rejected outright; in write mode they are permitted and the
    least-privilege database role is the authoritative control (§5.6 semantic
    gap). Write-set constructs are rejected only when ``allow_write_query`` is
    False.

    Args:
        sql: The SQL statement to validate.
        allow_write_query: When True the connection permits writes, so the
            read-only write-set allowlist is skipped (dangerous-set and
            single-statement checks still apply).

    Raises:
        SqlPolicyError: If the statement is rejected by the guard.
    """
    if len(sql) > MAX_SQL_LEN:
        _reject('SQL exceeds the maximum allowed length')

    normalized = _normalize_placeholders(sql)
    try:
        statements = parse_sql(normalized)
    except Exception as e:  # pglast.parser.ParseError and any other parse failure
        # Log the original and the normalized text at DEBUG so a
        # guard-induced placeholder rewrite (``original != normalized``) can be
        # told apart from genuinely malformed input in a bug report. DEBUG, not
        # the default level, because the SQL text may contain literal values.
        logger.debug(
            f'SQL policy guard could not parse query. original={sql!r} normalized={normalized!r}'
        )
        _reject('SQL could not be parsed', cause=e)

    if len(statements) != 1:
        _reject('Exactly one SQL statement is allowed')

    raw_stmt = statements[0]
    root = raw_stmt.stmt
    if root is None:  # pragma: no cover - defensive; empty/';' input yields 0 statements
        _reject('Empty statement is not allowed')

    # Analyze the parse tree. Any unexpected failure here (an unforeseen node
    # shape, resource limit, etc.) must fail closed rather than escape as an
    # uncaught exception, so we convert non-SqlPolicyError exceptions into a
    # rejection. SqlPolicyError (the intended rejection) is re-raised as-is.
    try:
        nodes = _collect_nodes(raw_stmt)

        # Dangerous-set pass runs in both modes.
        for node in nodes:
            _check_dangerous(node)

        # Write-set (read-only) pass runs only when writes are not permitted.
        if not allow_write_query:
            _check_read_only(root, nodes)
    except SqlPolicyError:
        raise
    except Exception as e:
        _reject('SQL could not be analyzed', cause=e)
