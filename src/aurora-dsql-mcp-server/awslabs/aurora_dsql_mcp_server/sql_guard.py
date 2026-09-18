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

import re
from loguru import logger
from pglast import ast, parse_sql
from pglast.enums import DiscardMode, VariableSetKind
from typing import NoReturn


MAX_SQL_LEN = 65_536

READ_ONLY_ALLOWED_ROOT = frozenset({'SelectStmt', 'VariableShowStmt', 'ExplainStmt'})
READ_ONLY_ALLOWED_STMT_NODES = frozenset(
    {'RawStmt', 'SelectStmt', 'VariableShowStmt', 'ExplainStmt'}
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

_DOLLAR_TAG_RE = re.compile(r'\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$')


class SqlPolicyError(Exception):
    """Raised when SQL is rejected by the parser-based policy."""


def _reject(reason: str, cause: BaseException | None = None) -> NoReturn:
    """Raise a non-sensitive policy error."""
    logger.warning(f'SQL policy guard rejected query: {reason}')
    if cause is not None:
        raise SqlPolicyError(reason) from cause
    raise SqlPolicyError(reason)


def _end_single_quote(sql: str, start: int) -> int:
    """Return the position after a PostgreSQL single-quoted string."""
    escaped = (
        start > 0
        and sql[start - 1] in ('E', 'e')
        and (start == 1 or not (sql[start - 2].isalnum() or sql[start - 2] == '_'))
    )
    i = start + 1
    while i < len(sql):
        if escaped and sql[i] == '\\' and i + 1 < len(sql):
            i += 2
        elif sql[i] == "'" and i + 1 < len(sql) and sql[i + 1] == "'":
            i += 2
        elif sql[i] == "'":
            return i + 1
        else:
            i += 1
    return len(sql)


def _end_double_quote(sql: str, start: int) -> int:
    """Return the position after a PostgreSQL quoted identifier."""
    i = start + 1
    while i < len(sql):
        if sql[i] == '"' and i + 1 < len(sql) and sql[i + 1] == '"':
            i += 2
        elif sql[i] == '"':
            return i + 1
        else:
            i += 1
    return len(sql)


def _end_dollar_quote(sql: str, start: int) -> int | None:
    """Return the position after a dollar-quoted string, or None."""
    match = _DOLLAR_TAG_RE.match(sql, start)
    if not match:
        return None
    tag = match.group(0)
    end = sql.find(tag, match.end())
    return len(sql) if end == -1 else end + len(tag)


def _normalize_placeholders(sql: str) -> str:
    """Rewrite psycopg ``%s``/``%b``/``%t`` placeholders for parser input only.

    The original SQL is always sent to psycopg. Replacements happen only in
    executable SQL, not inside strings, quoted identifiers, dollar-quoted
    bodies, or comments. ``%%`` is rewritten to the literal PostgreSQL modulo
    operator that psycopg sends to the server.
    """
    out: list[str] = []
    parameter = 1
    i = 0
    while i < len(sql):
        if sql[i] == "'":
            end = _end_single_quote(sql, i)
            out.append(sql[i:end])
            i = end
            continue
        if sql[i] == '"':
            end = _end_double_quote(sql, i)
            out.append(sql[i:end])
            i = end
            continue
        if sql[i] == '$':
            end = _end_dollar_quote(sql, i)
            if end is not None:
                out.append(sql[i:end])
                i = end
                continue
        if sql.startswith('--', i):
            end = sql.find('\n', i + 2)
            end = len(sql) if end == -1 else end
            out.append(sql[i:end])
            i = end
            continue
        if sql.startswith('/*', i):
            depth = 1
            end = i + 2
            while end < len(sql) and depth:
                if sql.startswith('/*', end):
                    depth += 1
                    end += 2
                elif sql.startswith('*/', end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            out.append(sql[i:end])
            i = end
            continue
        if sql.startswith('%%', i):
            out.append('%')
            i += 2
            continue
        if i + 1 < len(sql) and sql[i] == '%' and sql[i + 1] in ('s', 'b', 't'):
            out.append(f'${parameter}')
            parameter += 1
            i += 2
            continue
        out.append(sql[i])
        i += 1
    return ''.join(out)


def _normalize_dsql_syntax(sql: str) -> str:
    """Remove DSQL's ``ASYNC`` extension from a parser-only copy of DDL.

    Aurora DSQL requires ``CREATE [UNIQUE] INDEX ASYNC`` and
    ``ALTER TABLE ASYNC ... VALIDATE CONSTRAINT``. PostgreSQL's parser
    understands the corresponding statements without ``ASYNC``. This removes
    only that leading keyword token, outside comments and quoted content. The
    original DSQL statement is still what executes.
    """
    words: list[tuple[str, int, int]] = []
    i = 0
    while i < len(sql) and len(words) < 4:
        if sql[i] == "'":
            i = _end_single_quote(sql, i)
            continue
        if sql[i] == '"':
            i = _end_double_quote(sql, i)
            continue
        if sql[i] == '$':
            end = _end_dollar_quote(sql, i)
            if end is not None:
                i = end
                continue
        if sql.startswith('--', i):
            end = sql.find('\n', i + 2)
            i = len(sql) if end == -1 else end
            continue
        if sql.startswith('/*', i):
            depth = 1
            i += 2
            while i < len(sql) and depth:
                if sql.startswith('/*', i):
                    depth += 1
                    i += 2
                elif sql.startswith('*/', i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        if sql[i].isalpha() or sql[i] == '_':
            start = i
            i += 1
            while i < len(sql) and (sql[i].isalnum() or sql[i] in ('_', '$')):
                i += 1
            words.append((sql[start:i].upper(), start, i))
            continue
        i += 1

    names = [word[0] for word in words]
    async_index: int | None = None
    if names[:3] == ['CREATE', 'INDEX', 'ASYNC']:
        async_index = 2
    elif names[:4] == ['CREATE', 'UNIQUE', 'INDEX', 'ASYNC']:
        async_index = 3
    elif names[:3] == ['ALTER', 'TABLE', 'ASYNC']:
        async_index = 2

    if async_index is None:
        return sql
    _, start, end = words[async_index]
    return sql[:start] + sql[end:]


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
    """Return lower-case components of a function name."""
    return [
        value.lower()
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
    if isinstance(node, ast.CopyStmt):
        if node.is_program:
            _reject('COPY ... TO/FROM PROGRAM executes a host command')
        if node.filename is not None:
            _reject('COPY ... TO/FROM a server-side file accesses the host filesystem')
    elif isinstance(node, ast.DiscardStmt) and node.target == DiscardMode.DISCARD_ALL:
        _reject('DISCARD ALL can reset security-sensitive session settings')
    elif isinstance(node, ast.FuncCall):
        parts = _func_name_parts(node)
        if not parts:
            return
        function = parts[-1]
        if function in DANGEROUS_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {function}')
        if len(parts) >= 2 and (parts[-2], function) in DANGEROUS_QUALIFIED_FUNCTIONS:
            _reject(f'Dangerous function call not allowed: {parts[-2]}.{function}')
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


def _check_read_only(root: ast.Node, nodes: list[ast.Node]) -> None:
    """Reject syntax that is not read-only."""
    root_type = type(root).__name__
    if root_type not in READ_ONLY_ALLOWED_ROOT:
        _reject(f'Statement type not allowed in read-only mode: {root_type}')

    for node in nodes:
        node_type = type(node).__name__
        if node_type.endswith('Stmt') and node_type not in READ_ONLY_ALLOWED_STMT_NODES:
            _reject(f'Statement type not allowed in read-only mode: {node_type}')
        if isinstance(node, ast.SelectStmt) and node.intoClause is not None:
            _reject('SELECT ... INTO creates a table and is not allowed in read-only mode')
        if isinstance(node, ast.FuncCall):
            parts = _func_name_parts(node)
            if not parts:
                continue
            function = parts[-1]
            if function in READ_ONLY_PROHIBITED_FUNCTIONS:
                _reject('set_config() mutates session state and is not allowed in read-only mode')
            if function in READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS:
                _reject(f'Function mutates state and is not allowed in read-only mode: {function}')
            if (
                len(parts) >= 2
                and (parts[-2], function) in READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS
            ):
                _reject(
                    'Function mutates state and is not allowed in read-only mode: '
                    f'{parts[-2]}.{function}'
                )


def assert_executable(sql: str, allow_write_query: bool = False) -> None:
    """Require one parser-approved SQL statement."""
    if len(sql) > MAX_SQL_LEN:
        _reject('SQL exceeds the maximum allowed length')

    normalized = _normalize_placeholders(_normalize_dsql_syntax(sql))
    try:
        statements = parse_sql(normalized)
    except Exception as error:
        logger.debug(
            f'SQL policy guard could not parse query. original={sql!r} normalized={normalized!r}'
        )
        _reject('SQL could not be parsed', cause=error)

    if len(statements) != 1:
        _reject('Exactly one SQL statement is allowed')

    raw_stmt = statements[0]
    root = raw_stmt.stmt
    if root is None:
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
