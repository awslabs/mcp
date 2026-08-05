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

"""Read-only SQL guard for the Redshift MCP Server.

Validates that submitted SQL is a single statement and, in read-only mode, not a
denied operation -- classified structurally from the sqlglot AST (Redshift dialect),
so a deny-listed word used as an identifier, alias, or string literal is not flagged.
Fails closed on any parse error.
"""

import sqlglot
from awslabs.redshift_mcp_server.consts import MAX_SQL_LEN, READ_ONLY_DENY_LIST
from loguru import logger
from sqlglot import exp
from typing import NoReturn


def _reject(reason: str, cause: BaseException | None = None) -> NoReturn:
    """Log and raise for a rejected query.

    Args:
        reason: Non-sensitive explanation surfaced to the caller.
        cause: Optional underlying exception to chain so the real error is not hidden.

    Raises:
        Exception: Always raised with `reason`, chained from `cause` when provided.
    """
    logger.warning(f'Read-only guard rejected query: {reason}')
    if cause is not None:
        raise Exception(reason) from cause
    raise Exception(reason)


def _parse(sql: str) -> list[exp.Expression]:
    """Parse SQL with the Redshift dialect, failing closed on any error.

    Args:
        sql: The raw SQL submitted by the caller.

    Returns:
        Parsed statements, excluding empty (``None``) fragments from stray
        semicolons or comment/whitespace-only input.

    Raises:
        Exception: via `_reject` on any sqlglot error (parse/tokenize, or
            `RecursionError` on deep nesting); the original error is chained as the
            cause, not swallowed.
    """
    try:
        statements = sqlglot.parse(sql, read='redshift')
    except Exception as e:
        _reject('SQL could not be parsed', cause=e)
    return [statement for statement in statements if statement is not None]


def _operation_keyword(node: exp.Expression) -> str | None:
    """Map a single AST node to a deny-list keyword, or None.

    Detection is structural (node type, or for generic commands the command name),
    so a deny-listed word used as an identifier, alias, or string literal is not
    matched here.

    Args:
        node: A node from the parsed statement's tree.

    Returns:
        The matching deny-list keyword, or None if the node is not a denied operation.
    """
    # Transaction control mapping: BEGIN/BEGIN WORK/BEGIN TRANSACTION -> Transaction;
    # COMMIT (+WORK/TRANSACTION) and END WORK/END TRANSACTION -> Commit; ROLLBACK
    # (+WORK/TRANSACTION) -> Rollback; bare END -> EndStatement. (START/ABORT: see below.)
    if isinstance(node, exp.Transaction):
        return 'BEGIN'
    if isinstance(node, exp.Commit):
        return 'COMMIT'
    if isinstance(node, exp.Rollback):
        return 'ROLLBACK'
    if isinstance(node, exp.EndStatement):
        return 'END'
    # TRUNCATE, including `TRUNCATE TABLE foo` and the no-space `TRUNCATE"foo"` form.
    if isinstance(node, exp.TruncateTable):
        return 'TRUNCATE'
    # DCL: GRANT and REVOKE are both dedicated nodes in this dialect.
    if isinstance(node, exp.Grant):
        return 'GRANT'
    if isinstance(node, exp.Revoke):
        return 'REVOKE'
    # COMMENT ON ... (the statement; inline SQL comments are not modeled as this node).
    if isinstance(node, exp.Comment):
        return 'COMMENT'
    # ANALYZE, including `ANALYZE <table>`.
    if isinstance(node, exp.Analyze):
        return 'ANALYZE'
    # Generic/bare commands sqlglot has no dedicated class for: UNLOAD, CALL, VACUUM,
    # and any other deny-listed word surfaced as a command (matched by name).
    if isinstance(node, exp.Command):
        name = (node.name or '').upper()
        if name in READ_ONLY_DENY_LIST:
            return name
    return None


def _root_identifier_keyword(statement: exp.Expression) -> str | None:
    """Map a whole-statement bare identifier to a deny-list keyword, or None.

    sqlglot parses `START`/`ABORT` (and their WORK/TRANSACTION variants) as bare
    identifiers rather than statement nodes, so they are classified by the root
    identifier only. The check is root-only so a deny-listed word used as a column
    deeper in a query (e.g. `SELECT abort FROM t`) is not flagged.

    Args:
        statement: The parsed statement (tree root).

    Returns:
        The matching deny-list keyword, or None.
    """
    node = statement.this if isinstance(statement, exp.Alias) else statement
    if isinstance(node, exp.Column):
        name = node.name.upper()
        if name in READ_ONLY_DENY_LIST:
            return name
    return None


def _denied_operation(statement: exp.Expression) -> str | None:
    """Return the deny-list keyword if the statement is, or contains, a denied operation.

    First classifies a whole-statement bare identifier (the `START`/`ABORT` family),
    then walks the entire parse tree (defense-in-depth, not just the root) so a denied
    operation cannot hide behind comment/parenthesis/position desync.

    Args:
        statement: A parsed sqlglot statement.

    Returns:
        The matching deny-list keyword, or None if no node is a denied operation.
    """
    keyword = _root_identifier_keyword(statement)
    if keyword is not None:
        return keyword
    for node in statement.walk():
        keyword = _operation_keyword(node)
        if keyword is not None and keyword in READ_ONLY_DENY_LIST:
            return keyword
    return None


def assert_executable(sql: str, allow_read_write: bool = False) -> None:
    """Validate that the SQL is a single permitted statement.

    Fails closed: oversized input and any parser error are rejected.

    Args:
        sql: The SQL statement to validate.
        allow_read_write: When True, enforce single-statement only and skip the
            read-only statement-type deny-list.

    Raises:
        Exception: If the SQL is rejected by the guard.
    """
    if len(sql) > MAX_SQL_LEN:
        _reject('SQL exceeds the maximum allowed length')

    statements = _parse(sql)  # fails closed on parse/tokenize error

    if len(statements) != 1:
        _reject('Only a single SQL statement is allowed')

    if allow_read_write:
        return

    keyword = _denied_operation(statements[0])
    if keyword is not None:
        _reject(f'Statement type not allowed in read-only mode: {keyword}')
