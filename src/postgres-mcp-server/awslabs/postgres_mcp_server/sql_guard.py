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

* Write set -- operations whose requested purpose is to modify application,
  sequence, session, statistics, WAL, replication, catalog, large-object, or
  index state. In read-only mode only read *statement* node types are permitted
  anywhere in the parse tree; any other statement node is rejected. Known core
  and selected common-extension functions with explicit mutating semantics are
  also rejected even though they parse inside a ``SelectStmt``. Ordinary reads
  stay reads despite incidental execution bookkeeping (statistics increments,
  cache warming, snapshots, and transient locks). This function inventory is
  best-effort: arbitrary user-defined/third-party functions and overloaded
  operators cannot be resolved from syntax (§5.6) and remain owned by the
  least-privilege database role plus ``SET TRANSACTION READ ONLY`` backstop.
* Dangerous set -- command execution / SSRF / host filesystem / DoS /
  corruption / severe server-control / security-control-disabling constructs.
  Rejected in BOTH modes (defense in depth; the authoritative control is the
  least-privilege database role).

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

from awslabs.postgres_mcp_server.named_params import to_parse_placeholders
from loguru import logger
from pglast import ast, parse_sql
from pglast.enums import DiscardMode, VariableSetKind
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

# Known functions whose requested purpose is to mutate durable or session state,
# despite parsing as a FuncCall inside an otherwise-read SelectStmt. Rejected in
# read-only mode, allowed in write mode. This is a versioned, best-effort
# inventory of PostgreSQL core through PG18 plus selected PostgreSQL-supplied /
# common RDS extensions -- NOT a claim that syntax can reveal arbitrary function
# semantics (§5.6). Some entries are also blocked by PostgreSQL's transaction
# backstop (PG16 blocks nextval/setval and large-object writes); others execute
# under SET TRANSACTION READ ONLY (stats/WAL/replication/index/catalog helpers).
# Classification is semantic and deliberately independent of that implementation
# detail. Pure observation/calculation stays allowed: currval/lastval, stats
# readers, random/clock/UUID generation, pg_prewarm (cache-only), exported
# snapshots, logical-slot peek, replication progress, and large-object reads.
READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS = frozenset(
    {
        # Sequence state.
        'nextval',
        'setval',
        # Core statistics flush/reset/import (PG13-PG18).
        'pg_stat_force_next_flush',
        'pg_stat_reset',
        'pg_stat_reset_backend_stats',
        'pg_stat_reset_shared',
        'pg_stat_reset_single_table_counters',
        'pg_stat_reset_single_function_counters',
        'pg_stat_reset_slru',
        'pg_stat_reset_replication_slot',
        'pg_stat_reset_subscription_stats',
        'pg_restore_relation_stats',
        'pg_clear_relation_stats',
        'pg_restore_attribute_stats',
        'pg_clear_attribute_stats',
        # Common statistics extension resets (grantable to non-superusers).
        'pg_stat_statements_reset',
        'pg_stat_monitor_reset',
        # WAL, online-backup, and restore-point state. pg_start/stop_backup
        # are the PG13/14 names; PG15+ renamed them to pg_backup_start/stop.
        'pg_start_backup',
        'pg_stop_backup',
        'pg_backup_start',
        'pg_backup_stop',
        'pg_switch_wal',
        'pg_create_restore_point',
        'pg_log_standby_snapshot',
        'pg_logical_emit_message',
        # Replication slots: create/copy/drop, consume changes, or advance.
        'pg_create_physical_replication_slot',
        'pg_create_logical_replication_slot',
        'pg_copy_physical_replication_slot',
        'pg_copy_logical_replication_slot',
        'pg_drop_replication_slot',
        'pg_replication_slot_advance',
        'pg_sync_replication_slots',
        'pg_logical_slot_get_changes',
        'pg_logical_slot_get_binary_changes',
        # Replication-origin durable, session, and transaction state.
        'pg_replication_origin_create',
        'pg_replication_origin_drop',
        'pg_replication_origin_advance',
        'pg_replication_origin_session_setup',
        'pg_replication_origin_session_reset',
        'pg_replication_origin_xact_setup',
        'pg_replication_origin_xact_reset',
        # Index maintenance writes persistent BRIN / GIN index pages.
        'brin_summarize_new_values',
        'brin_summarize_range',
        'brin_desummarize_range',
        'gin_clean_pending_list',
        # Database large-object create/write/truncate/delete. Reads such as
        # lo_get/loread remain allowed; lo_import/export are dangerous below.
        'lo_creat',
        'lo_create',
        'lo_from_bytea',
        'lo_put',
        'lo_truncate',
        'lo_truncate64',
        'lo_unlink',
        'lowrite',
        # Catalog, session, and shared-lock cleanup state.
        'pg_import_system_collations',
        'setseed',
        'pg_advisory_unlock',
        'pg_advisory_unlock_shared',
        'pg_advisory_unlock_all',
        # PostgreSQL-supplied/common extensions.
        'autoprewarm_dump_now',
        'pg_truncate_visibility_map',
        'postgres_fdw_disconnect',
        'postgres_fdw_disconnect_all',
    }
)

# Generic extension function names need schema-qualified matching to avoid
# blocking unrelated user functions with names such as schedule/alter_job.
READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS = frozenset(
    {
        ('cron', 'schedule'),
        ('cron', 'schedule_in_database'),
        ('cron', 'alter_job'),
        ('cron', 'unschedule'),
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
        'pg_ls_summariesdir',
        # Host file write / RCE -- adminpack (Tier 2). pg_file_write is an
        # arbitrary host-file write.
        'pg_file_write',
        'pg_file_sync',
        'pg_file_rename',
        'pg_file_unlink',
        'pg_logdir_ls',
        # Severe server control / availability impact.
        'pg_reload_conf',
        'pg_rotate_logfile',
        'pg_promote',
        'pg_wal_replay_pause',
        'pg_wal_replay_resume',
        'pg_log_backend_memory_contexts',
        'autoprewarm_start_worker',
        # Low-level corruption / cache-eviction testing extensions.
        'heap_force_kill',
        'heap_force_freeze',
        'pg_buffercache_evict',
        'pg_buffercache_evict_relation',
        'pg_buffercache_evict_all',
        # Advisory-lock acquisition -- application-level DoS / shared lock state.
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
# parsing only, substitute a positional placeholder ($1). Only the guard's copy
# is rewritten; the ORIGINAL SQL is what executes (the RDS Data API binds
# ``:name`` parameters natively, and the psycopg path applies the *same*
# placeholder rule from ``named_params`` to produce its own ``%(name)s`` form).
# The matching rule is defined once in ``named_params`` so the guard and the
# executor can never disagree about which colons are placeholders.
_normalize_placeholders = to_parse_placeholders


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

    # DISCARD ALL performs a bulk session reset equivalent in part to RESET
    # ALL, including security-sensitive GUCs. Other DISCARD targets remain
    # ordinary write-set operations (read-only rejects; write mode permits).
    if isinstance(node, ast.DiscardStmt):
        if node.target == DiscardMode.DISCARD_ALL:
            _reject('DISCARD ALL can reset security-sensitive session settings')
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

    # SET / RESET ... targeting a security-sensitive GUC. RESET ALL has no
    # ``name`` in the AST but resets every GUC, including row_security and
    # session_replication_role, so it is blocked explicitly as the bulk form of
    # the individually-blocked RESET operations.
    if isinstance(node, ast.VariableSetStmt):
        if node.kind == VariableSetKind.VAR_RESET_ALL:
            _reject('RESET ALL can reset security-sensitive session settings')
        name = (node.name or '').lower()
        if name in SECURITY_SENSITIVE_GUCS:
            _reject(f'Security-sensitive session setting not allowed: {node.name}')


def _check_read_only(root, nodes: list) -> None:
    """Reject write-set constructs when the connection is read-only.

    Enforced fail-closed as an allowlist: the root must be a read node type and
    every statement node in the tree must be a permitted read type. Write-set
    members that parse as an allowed ``SelectStmt`` are caught explicitly:
    ``SELECT ... INTO`` (table creation), ``set_config()`` (session state), and
    the known bare / schema-qualified semantic mutators in
    ``READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS`` and
    ``READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS``. This inventory covers core
    through PG18 plus selected PostgreSQL-supplied/common RDS extensions, but
    arbitrary user-defined/third-party function and operator semantics remain
    undetectable from syntax (§5.6) and are owned by the database role.

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
        # Function-form writes inside SelectStmt. Bare names cover distinctive
        # core/contrib functions; generic extension names are schema-qualified.
        if isinstance(node, ast.FuncCall):
            parts = _func_name_parts(node)
            if not parts:  # pragma: no cover - defensive; a FuncCall always has a name
                continue
            fn = parts[-1]
            if fn in READ_ONLY_PROHIBITED_FUNCTIONS:
                _reject('set_config() mutates session state and is not allowed in read-only mode')
            if fn in READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS:
                _reject(f'Function mutates state and is not allowed in read-only mode: {fn}')
            if len(parts) >= 2 and (parts[-2], fn) in READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS:
                _reject(
                    f'Function mutates state and is not allowed in read-only mode: '
                    f'{parts[-2]}.{fn}'
                )


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
