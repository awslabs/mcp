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

r"""Parser-based SQL policy for the Aurora DSQL MCP Server.

The policy uses PostgreSQL's parser through pglast. PostgreSQL escape syntax,
including Unicode-escaped identifiers such as ``U&"pg_sl\\0065ep"``, is decoded
before names are checked. The guard and Aurora DSQL therefore interpret
identifiers with the same PostgreSQL lexical rules.

This is defense in depth. Database permissions and read-only transactions remain
the authoritative controls for function semantics that cannot be inferred from
syntax, such as user-defined wrapper functions.
"""

from loguru import logger
from pglast import ast, parse_sql, scan
from pglast.enums import DiscardMode, VariableSetKind
from typing import NoReturn


READ_ONLY_ALLOWED_ROOT = frozenset(
    {'SelectStmt', 'VariableShowStmt', 'ExplainStmt', 'VariableSetStmt'}
)
READ_ONLY_ALLOWED_STMT_NODES = frozenset(
    {
        'RawStmt',
        'SelectStmt',
        'VariableShowStmt',
        'ExplainStmt',
        'ExecuteStmt',
        'VariableSetStmt',
    }
)

READ_ONLY_PROHIBITED_FUNCTIONS = frozenset({'set_config'})

READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS = frozenset(
    {
        'nextval',
        'setval',
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
        'pg_stat_statements_reset',
        'pg_stat_monitor_reset',
        'pg_start_backup',
        'pg_stop_backup',
        'pg_backup_start',
        'pg_backup_stop',
        'pg_switch_wal',
        'pg_create_restore_point',
        'pg_log_standby_snapshot',
        'pg_logical_emit_message',
        'pg_create_physical_replication_slot',
        'pg_create_logical_replication_slot',
        'pg_copy_physical_replication_slot',
        'pg_copy_logical_replication_slot',
        'pg_drop_replication_slot',
        'pg_replication_slot_advance',
        'pg_sync_replication_slots',
        'pg_logical_slot_get_changes',
        'pg_logical_slot_get_binary_changes',
        'pg_replication_origin_create',
        'pg_replication_origin_drop',
        'pg_replication_origin_advance',
        'pg_replication_origin_session_setup',
        'pg_replication_origin_session_reset',
        'pg_replication_origin_xact_setup',
        'pg_replication_origin_xact_reset',
        'brin_summarize_new_values',
        'brin_summarize_range',
        'brin_desummarize_range',
        'gin_clean_pending_list',
        'lo_creat',
        'lo_create',
        'lo_from_bytea',
        'lo_put',
        'lo_truncate',
        'lo_truncate64',
        'lo_unlink',
        'lowrite',
        'pg_import_system_collations',
        'setseed',
        'pg_advisory_unlock',
        'pg_advisory_unlock_shared',
        'pg_advisory_unlock_all',
        'autoprewarm_dump_now',
        'pg_truncate_visibility_map',
        'postgres_fdw_disconnect',
        'postgres_fdw_disconnect_all',
    }
)

READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS = frozenset(
    {
        ('cron', 'schedule'),
        ('cron', 'schedule_in_database'),
        ('cron', 'alter_job'),
        ('cron', 'unschedule'),
    }
)

DANGEROUS_FUNCTIONS = frozenset(
    {
        'pg_cancel_backend',
        'pg_terminate_backend',
        'pg_sleep',
        'pg_sleep_for',
        'pg_sleep_until',
        'pg_read_file',
        'pg_read_binary_file',
        'pg_stat_file',
        'lo_import',
        'lo_export',
        'pg_ls_dir',
        'pg_ls_logdir',
        'pg_ls_waldir',
        'pg_ls_tmpdir',
        'pg_ls_archive_statusdir',
        'pg_ls_logicalmapdir',
        'pg_ls_logicalsnapdir',
        'pg_ls_replslotdir',
        'pg_ls_summariesdir',
        'pg_file_write',
        'pg_file_sync',
        'pg_file_rename',
        'pg_file_unlink',
        'pg_logdir_ls',
        'pg_reload_conf',
        'pg_rotate_logfile',
        'pg_promote',
        'pg_wal_replay_pause',
        'pg_wal_replay_resume',
        'pg_log_backend_memory_contexts',
        'autoprewarm_start_worker',
        'heap_force_kill',
        'heap_force_freeze',
        'pg_buffercache_evict',
        'pg_buffercache_evict_relation',
        'pg_buffercache_evict_all',
        'pg_advisory_lock',
        'pg_advisory_lock_shared',
        'pg_advisory_xact_lock',
        'pg_advisory_xact_lock_shared',
        'pg_try_advisory_lock',
        'pg_try_advisory_lock_shared',
        'pg_try_advisory_xact_lock',
        'pg_try_advisory_xact_lock_shared',
        'pg_notify',
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

DANGEROUS_QUALIFIED_FUNCTIONS = frozenset(
    {
        ('aws_lambda', 'invoke'),
        ('aws_s3', 'query_export_to_s3'),
        ('aws_s3', 'table_import_from_s3'),
    }
)

SECURITY_SENSITIVE_GUCS = frozenset({'row_security', 'session_replication_role'})

_COMMENT_TOKENS = frozenset({'C_COMMENT', 'SQL_COMMENT'})
_IAM_PRINCIPAL_TOKENS = frozenset({'SCONST', 'USCONST'})
_DANGEROUS_QUALIFIED_BASENAMES = frozenset(
    function for _, function in DANGEROUS_QUALIFIED_FUNCTIONS
)
_READ_ONLY_QUALIFIED_BASENAMES = frozenset(
    function for _, function in READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS
)


class SqlPolicyError(Exception):
    """Raised when SQL is rejected by the parser-based policy."""


def _reject(reason: str, cause: BaseException | None = None) -> NoReturn:
    """Raise a non-sensitive policy error."""
    logger.warning(f'SQL policy guard rejected query: {reason}')
    if cause is not None:
        raise SqlPolicyError(reason) from cause
    raise SqlPolicyError(reason)


def _apply_replacements(sql: str, replacements: list[tuple[int, int, str]]) -> str:
    """Apply inclusive source-span replacements from right to left."""
    for start, end, replacement in reversed(replacements):
        sql = sql[:start] + replacement + sql[end + 1 :]
    return sql


def _normalize_placeholders(sql: str, parameter_count: int | None = None) -> str:
    """Match psycopg placeholder handling in the parser-only SQL copy.

    When a parameters object is supplied to ``execute``, psycopg scans the raw
    query text rather than PostgreSQL tokens. It therefore interprets ``%s``,
    ``%b``, ``%t``, and ``%%`` even inside strings, identifiers, dollar quotes,
    and comments. A terminal percent or percent immediately before a line feed
    is not matched by psycopg and remains unchanged.
    """
    if parameter_count is None:
        return sql

    chunks: list[str] = []
    parameter = 1
    position = 0
    while position < len(sql):
        character = sql[position]
        if character != '%':
            chunks.append(character)
            position += 1
            continue

        marker_position = position + 1
        if marker_position >= len(sql) or sql[marker_position] == '\n':
            chunks.append('%')
            position += 1
            continue
        marker = sql[marker_position]
        if marker in ('s', 'b', 't'):
            chunks.append(f'${parameter}')
            parameter += 1
        elif marker == '%':
            chunks.append('%')
        else:
            _reject('Invalid psycopg placeholder syntax')
        position += 2

    placeholders = parameter - 1
    if placeholders != parameter_count:
        _reject(
            f'Query has {placeholders} placeholders but {parameter_count} parameters were supplied'
        )
    return ''.join(chunks)


def _significant_tokens(sql: str) -> list:
    """Return PostgreSQL tokens other than comments."""
    return [token for token in scan(sql) if token.name not in _COMMENT_TOKENS]


def _token_text(sql: str, token) -> str:
    """Return the source text represented by a scanner token."""
    return sql[token.start : token.end + 1]


def _normalize_dsql_syntax(sql: str, postgres_parse_failed: bool = False) -> str:
    """Normalize narrowly recognized Aurora DSQL syntax for parser input only."""
    if not postgres_parse_failed:
        try:
            parse_sql(sql)
        except Exception:
            logger.debug('Checking PostgreSQL parse failure for recognized DSQL syntax')
        else:
            return sql

    tokens = _significant_tokens(sql)
    core_tokens = tokens[:-1] if tokens and tokens[-1].name == 'ASCII_59' else tokens
    words = [_token_text(sql, token).upper() for token in core_tokens]

    # AWS IAM GRANT role TO 'principal' and AWS IAM REVOKE role FROM 'principal'
    # are DSQL extensions. Convert only the exact six-token shape to an
    # equivalent PostgreSQL role grant/revoke for policy classification.
    if (
        len(core_tokens) == 6
        and words[:2] == ['AWS', 'IAM']
        and words[2] in ('GRANT', 'REVOKE')
        and words[4] == ('TO' if words[2] == 'GRANT' else 'FROM')
        and core_tokens[5].name in _IAM_PRINCIPAL_TOKENS
    ):
        semicolon = ';' if len(tokens) != len(core_tokens) else ''
        role = _token_text(sql, core_tokens[3])
        return f'{words[2]} {role} {words[4]} CURRENT_USER{semicolon}'

    async_index: int | None = None
    if words[:3] == ['CREATE', 'INDEX', 'ASYNC'] and len(core_tokens) > 3:
        async_index = 2
    elif words[:4] == ['CREATE', 'UNIQUE', 'INDEX', 'ASYNC'] and len(core_tokens) > 4:
        async_index = 3
    elif words[:3] == ['ALTER', 'TABLE', 'ASYNC']:
        for index in range(4, len(core_tokens) - 1):
            if words[index : index + 2] == ['VALIDATE', 'CONSTRAINT']:
                async_index = 2
                break

    if async_index is None:
        return sql
    token = core_tokens[async_index]
    return _apply_replacements(sql, [(token.start, token.end, '')])


def _collect_nodes(raw_stmt: ast.Node) -> list[ast.Node]:
    """Return all AST nodes using an iterative walk."""
    nodes: list[ast.Node] = []
    stack: list = [raw_stmt]
    while stack:
        item = stack.pop()
        if isinstance(item, ast.Node):
            nodes.append(item)
            for attribute in item:
                stack.append(getattr(item, attribute, None))
        elif isinstance(item, (tuple, list)):
            stack.extend(item)
    return nodes


def _func_name_parts(node: ast.FuncCall) -> list[str]:
    """Return function-name components with PostgreSQL identifier semantics."""
    return [
        value
        for element in node.funcname or ()
        if (value := getattr(element, 'sval', None)) is not None
    ]


def _first_arg_string(node: ast.FuncCall) -> str | None:
    """Return a literal first function argument, if present."""
    args = node.args or ()
    if args and isinstance(args[0], ast.A_Const):
        return getattr(args[0].val, 'sval', None)
    return None


def _check_dangerous(node: ast.Node) -> None:
    """Reject constructs prohibited in read-only and write modes."""
    if isinstance(node, ast.TransactionStmt):
        _reject('Caller-supplied transaction control is not allowed')
    elif isinstance(node, ast.LoadStmt):
        _reject('LOAD can execute a native library and is not allowed')
    elif isinstance(node, ast.DoStmt):
        _reject('Opaque executable DO blocks are not allowed')
    elif isinstance(node, ast.CreateFunctionStmt):
        _reject('Function and procedure definitions are not allowed')
    elif isinstance(node, ast.CallStmt):
        _reject('Stored procedure calls are not allowed')
    elif isinstance(node, ast.CopyStmt):
        if node.is_program:
            _reject('COPY ... TO/FROM PROGRAM executes a host command')
        if node.filename is not None:
            _reject('COPY ... TO/FROM a server-side file accesses the host filesystem')
    elif isinstance(node, ast.DiscardStmt) and node.target == DiscardMode.DISCARD_ALL:
        _reject('DISCARD ALL can reset security-sensitive session settings')
    elif isinstance(node, ast.FuncCall):
        parts = _func_name_parts(node)
        if not parts:  # pragma: no cover - pglast FuncCall always has a name
            return
        function = parts[-1]
        if function in DANGEROUS_FUNCTIONS or function in _DANGEROUS_QUALIFIED_BASENAMES:
            _reject(f'Dangerous function call not allowed: {function}')
        if function == 'set_config':
            guc = _first_arg_string(node)
            if guc is None:
                _reject('set_config() with a non-literal GUC name is not allowed')
            if guc.lower() in SECURITY_SENSITIVE_GUCS:
                _reject(f'Security-sensitive session setting not allowed: {guc}')
    elif isinstance(node, ast.VariableSetStmt):
        if node.kind == VariableSetKind.VAR_RESET_ALL:
            _reject('RESET ALL can reset security-sensitive session settings')
        if (node.name or '').lower() in SECURITY_SENSITIVE_GUCS:
            _reject(f'Security-sensitive session setting not allowed: {node.name}')


def _is_safe_transaction_setting(node: ast.VariableSetStmt) -> bool:
    """Return whether SET TRANSACTION only tightens read behavior or isolation."""
    if node.kind != VariableSetKind.VAR_SET_MULTI or (node.name or '').upper() != 'TRANSACTION':
        return False
    args = node.args or ()
    if not args:  # pragma: no cover - PostgreSQL rejects an empty SET TRANSACTION
        return False
    for option in args:
        argument = getattr(option, 'arg', None)
        value = getattr(getattr(argument, 'val', None), 'ival', None)
        if option.defname == 'transaction_read_only' and value == 1:
            continue
        isolation = getattr(getattr(argument, 'val', None), 'sval', None)
        if option.defname == 'transaction_isolation' and isolation is not None:
            continue
        return False
    return True


def _explain_executes(root: ast.ExplainStmt) -> bool:
    """Return whether EXPLAIN has ANALYZE enabled."""
    analyze = False
    for option in root.options or ():
        if option.defname != 'analyze':
            continue
        if option.arg is None:
            analyze = True
            continue
        integer_value = getattr(option.arg, 'ival', None)
        if integer_value is not None:
            analyze = integer_value != 0
            continue
        string_value = getattr(option.arg, 'sval', None)
        if string_value is not None:
            analyze = string_value.lower() in ('true', 'on', 'yes', '1')
            continue
        analyze = bool(getattr(option.arg, 'boolval', True))  # pragma: no cover
    return analyze


def _check_read_only(root: ast.Node, nodes: list[ast.Node]) -> None:
    """Reject syntax that is not read-only."""
    root_type = type(root).__name__
    if root_type not in READ_ONLY_ALLOWED_ROOT:
        _reject(f'Statement type not allowed in read-only mode: {root_type}')

    for node in nodes:
        node_type = type(node).__name__
        if node_type.endswith('Stmt') and node_type not in READ_ONLY_ALLOWED_STMT_NODES:
            _reject(f'Statement type not allowed in read-only mode: {node_type}')
        if isinstance(node, ast.VariableSetStmt) and not _is_safe_transaction_setting(node):
            _reject('Only read-only or isolation-only SET TRANSACTION is allowed')
        if isinstance(node, ast.ExecuteStmt):
            if (
                not isinstance(root, ast.ExplainStmt)
                or root.query is not node
                or _explain_executes(root)
            ):
                _reject('EXECUTE is allowed only under EXPLAIN without ANALYZE')
        if isinstance(node, ast.SelectStmt) and node.intoClause is not None:
            _reject('SELECT ... INTO creates a table and is not allowed in read-only mode')
        if isinstance(node, ast.FuncCall):
            parts = _func_name_parts(node)
            if not parts:  # pragma: no cover - pglast FuncCall always has a name
                continue
            function = parts[-1]
            if function in READ_ONLY_PROHIBITED_FUNCTIONS:
                _reject('set_config() mutates session state and is not allowed in read-only mode')
            if function in READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS:
                _reject(f'Function mutates state and is not allowed in read-only mode: {function}')
            if function in _READ_ONLY_QUALIFIED_BASENAMES:
                _reject(f'Function mutates state and is not allowed in read-only mode: {function}')


def assert_executable(
    sql: str, allow_write_query: bool = False, parameter_count: int | None = None
) -> None:
    """Require one parser-approved SQL statement.

    ``parameter_count`` must be ``None`` when no parameters object is supplied,
    or the number of values supplied to psycopg otherwise.
    """
    try:
        normalized = _normalize_placeholders(sql, parameter_count=parameter_count)
    except SqlPolicyError:
        raise
    except Exception as error:
        _reject('SQL could not be scanned', cause=error)
    try:
        statements = parse_sql(normalized)
    except Exception as error:
        try:
            dsql_normalized = _normalize_dsql_syntax(normalized, postgres_parse_failed=True)
        except Exception as scan_error:
            _reject('SQL could not be scanned', cause=scan_error)
        if dsql_normalized == normalized:
            logger.debug(
                f'SQL policy guard could not parse query. original={sql!r} normalized={normalized!r}'
            )
            _reject('SQL could not be parsed', cause=error)
        try:
            statements = parse_sql(dsql_normalized)
        except Exception as dsql_error:
            logger.debug(
                'SQL policy guard could not parse DSQL-normalized query. '
                f'original={sql!r} normalized={dsql_normalized!r}'
            )
            _reject('SQL could not be parsed', cause=dsql_error)

    if len(statements) != 1:
        _reject('Exactly one SQL statement is allowed')

    raw_stmt = statements[0]
    root = raw_stmt.stmt
    if root is None:  # pragma: no cover - empty input yields zero RawStmt objects
        _reject('Empty statement is not allowed')

    try:
        nodes = _collect_nodes(raw_stmt)
        for node in nodes:
            _check_dangerous(node)
        if not allow_write_query:
            _check_read_only(root, nodes)
    except SqlPolicyError:
        raise
    except Exception as error:
        _reject('SQL could not be analyzed', cause=error)
