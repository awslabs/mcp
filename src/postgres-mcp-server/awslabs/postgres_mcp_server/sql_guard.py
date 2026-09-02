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
  allowlist: in read-only mode only read node types are permitted anywhere in
  the parse tree; anything else is a write and is rejected.
* Dangerous set -- command execution / SSRF / host filesystem / DoS /
  security-control-disabling constructs. Rejected in BOTH modes (defense in
  depth; the authoritative control is the least-privilege database role).

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
# parsing only, substitute a positional placeholder ($1) -- a value position,
# so it never changes the statement type, function names, or GUC targets the
# guard classifies. The negative lookbehind leaves the ``::`` cast operator
# alone. This mirrors the connection layer's own ``:name`` conversion; the
# ORIGINAL SQL is what executes.
_NAMED_PARAM_PATTERN = re.compile(r'(?<!:):([a-zA-Z_]\w*)')


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
        if not parts:
            return
        bare = parts[-1]
        if bare in DANGEROUS_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {bare}')
        if len(parts) >= 2 and (parts[-2], bare) in DANGEROUS_QUALIFIED_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {parts[-2]}.{bare}')
        # set_config() targeting a security-sensitive GUC (function form of SET).
        if bare == 'set_config':
            guc = _first_arg_string(node)
            if guc is not None and guc.lower() in SECURITY_SENSITIVE_GUCS:
                _reject(f'Security-sensitive session setting not allowed: {guc}')
        return

    # SET / SET SESSION ... targeting a security-sensitive GUC.
    if isinstance(node, ast.VariableSetStmt):
        name = (node.name or '').lower()
        if name in SECURITY_SENSITIVE_GUCS:
            _reject(f'Security-sensitive session setting not allowed: {node.name}')


def _check_read_only(root, nodes: list) -> None:
    """Reject write-set constructs when the connection is read-only.

    Enforced fail-closed as an allowlist: the root must be a read node type and
    every statement node in the tree must be a permitted read type. Two write-set
    members that parse as an allowed ``SelectStmt`` are caught by explicit field
    checks: ``SELECT ... INTO`` (a table-creating write) and ``set_config()``
    (session-state mutation for any GUC).

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
        # set_config() for any GUC mutates session state.
        if isinstance(node, ast.FuncCall):
            parts = _func_name_parts(node)
            if parts and parts[-1] in READ_ONLY_PROHIBITED_FUNCTIONS:
                _reject('set_config() mutates session state and is not allowed in read-only mode')


def assert_executable(sql: str, allow_write_query: bool = False) -> None:
    """Validate that ``sql`` is a single permitted statement, else raise.

    Fails closed: oversized input, any parser error, and multi- or zero-statement
    submissions are rejected. Dangerous constructs are rejected regardless of
    ``allow_write_query``; write-set constructs are rejected only when it is False.

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

    try:
        statements = parse_sql(_normalize_placeholders(sql))
    except Exception as e:  # pglast.parser.ParseError and any other parse failure
        _reject('SQL could not be parsed', cause=e)

    if len(statements) != 1:
        _reject('Exactly one SQL statement is allowed')

    raw_stmt = statements[0]
    root = raw_stmt.stmt
    if root is None:
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
