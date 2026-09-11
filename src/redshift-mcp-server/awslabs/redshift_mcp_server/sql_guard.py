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

"""SQL guard and write classification for the Redshift MCP Server.

Two jobs, both classified structurally from the sqlglot AST (Redshift dialect), so a
keyword used as an identifier, alias, or string literal is never matched by text:

- `assert_executable` -- the gate. Rejects oversized input, multiple statements, and,
  in read-only mode, the statement types a read-only transaction cannot neutralize.
- `might_write` -- the classifier. Answers whether a statement could change anything,
  to decide if it needs confirmation. Only recognized reads answer False.

Both fail closed: any parse error is a rejection, and anything unrecognized might write.
"""

import sqlglot
from awslabs.redshift_mcp_server.consts import MAX_SQL_LEN
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from sqlglot import exp
from typing import NoReturn


# Operations denied in read-only mode: the ones a read-only transaction cannot
# neutralize. Each keyword maps to a sqlglot node type, or to a bare-command name.
_READ_ONLY_DENY_KEYWORD_LIST = frozenset(
    {
        'UNLOAD',
        'BEGIN',
        'START',
        'COMMIT',
        'END',
        'ROLLBACK',
        'ABORT',
        'TRUNCATE',
        'CALL',
        'GRANT',
        'REVOKE',
        'VACUUM',
        'ANALYZE',
        'COMMENT',
        # Only bare `CANCEL` reaches this list. `CANCEL <pid>`, the form that does anything,
        # does not parse in this dialect and is rejected as unparseable instead.
        'CANCEL',
        # A session setting can clear the read-only property BEGIN READ ONLY established:
        # `SET transaction_read_only TO off`, `SET TRANSACTION READ WRITE`, `SET SESSION
        # CHARACTERISTICS AS TRANSACTION READ WRITE`, and `RESET` of any of those or of ALL.
        # A single statement could not exploit that, since its transaction ends with the
        # call, but a named transaction spans calls and a later statement in it would write.
        # Nothing is lost by denying them: outside a transaction a setting has no future to
        # apply to.
        'SET',
        'RESET',
    }
)

# Bare commands treated as reads, matched by name because sqlglot has no node class
# for them. Anything not listed might write. `DESC` and `DESCRIBE` are deliberately absent:
# Redshift has neither, so allow-listing them would only widen the surface.
_READ_COMMAND_ALLOW_KEYWORD_LIST = frozenset(
    {
        'SHOW',
        'EXPLAIN',
    }
)

# Nodes that change data, schema, permissions, or transaction state. Matched anywhere
# in the tree, so a write cannot hide inside an otherwise read-shaped statement.
_WRITE_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Copy,
    exp.TruncateTable,
    exp.Grant,
    exp.Revoke,
    exp.Comment,
    exp.Analyze,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.EndStatement,
)

# Root node types a plain read can have. `Intersect` and `Except` are not `Union`
# subclasses, so the shared `SetOperation` base is what covers all three.
_READ_ROOT_NODES = (exp.Select, exp.SetOperation, exp.Subquery)


# --- Parsing, shared by both jobs ---


def _reject(reason: str, cause: BaseException | None = None) -> NoReturn:
    """Log and raise for a rejected query.

    Args:
        reason: Non-sensitive explanation surfaced to the caller.
        cause: Optional underlying exception to chain so the real error is not hidden.

    Raises:
        ToolError: Always raised with `reason`, chained from `cause` when provided.
    """
    logger.warning(f'SQL guard rejected query: {reason}')
    if cause is not None:
        raise ToolError(reason) from cause
    raise ToolError(reason)


def _parse(sql: str) -> list[exp.Expression]:
    """Parse SQL with the Redshift dialect, failing closed on any error.

    Args:
        sql: The raw SQL submitted by the caller.

    Returns:
        Parsed statements, excluding empty (``None``) fragments from stray
        semicolons or comment/whitespace-only input.

    Raises:
        ToolError: via `_reject` on any sqlglot error (parse/tokenize, or
            `RecursionError` on deep nesting); the original error is chained as the
            cause, not swallowed.
    """
    try:
        statements = sqlglot.parse(sql, read='redshift')
    except Exception as e:
        _reject('SQL could not be parsed', cause=e)
    return [statement for statement in statements if statement is not None]


# --- Read-only deny-list ---


def _read_only_denied_keyword(node: exp.Expression) -> str | None:
    """Map a single AST node to a read-only deny-list keyword, or None.

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
    # SET has its own node; RESET and `SET SESSION CHARACTERISTICS` fall through to Command.
    if isinstance(node, exp.Set):
        return 'SET'
    # Generic/bare commands sqlglot has no dedicated class for: UNLOAD, CALL, VACUUM,
    # and any other deny-listed word surfaced as a command (matched by name).
    if isinstance(node, exp.Command):
        name = (node.name or '').upper()
        if name in _READ_ONLY_DENY_KEYWORD_LIST:
            return name
    return None


def _read_only_denied_root(statement: exp.Expression) -> str | None:
    """Map a whole-statement bare identifier to a read-only deny-list keyword, or None.

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
        if name in _READ_ONLY_DENY_KEYWORD_LIST:
            return name
    return None


def _read_only_denied_operation(statement: exp.Expression) -> str | None:
    """Return the deny-list keyword if the statement is, or contains, a denied operation.

    First classifies a whole-statement bare identifier (the `START`/`ABORT` family),
    then walks the entire parse tree (defense-in-depth, not just the root) so a denied
    operation cannot hide behind comment/parenthesis/position desync.

    Args:
        statement: A parsed sqlglot statement.

    Returns:
        The matching deny-list keyword, or None if no node is a denied operation.
    """
    keyword = _read_only_denied_root(statement)
    if keyword is not None:
        return keyword
    for node in statement.walk():
        keyword = _read_only_denied_keyword(node)
        if keyword is not None:
            return keyword
    return None


def assert_executable(sql: str, enforce_read_only: bool = True) -> None:
    """Validate that the SQL is a single permitted statement.

    Fails closed: oversized input and any parser error are rejected.

    Args:
        sql: The SQL statement to validate.
        enforce_read_only: When False, enforce single-statement only and skip the
            read-only statement-type deny-list.

    Raises:
        ToolError: If the SQL is rejected by the guard.
    """
    if len(sql) > MAX_SQL_LEN:
        _reject('SQL exceeds the maximum allowed length')

    statements = _parse(sql)  # fails closed on parse/tokenize error

    if len(statements) != 1:
        _reject('Only a single SQL statement is allowed')

    if not enforce_read_only:
        return

    keyword = _read_only_denied_operation(statements[0])
    if keyword is not None:
        _reject(f'Statement type not allowed in read-only mode: {keyword}')


# --- Write classification ---


def _is_read_statement(statement: exp.Expression) -> bool:
    """Return True only for a statement recognized as a read.

    Args:
        statement: A parsed sqlglot statement.

    Returns:
        True when the statement is a recognized read, False for anything else.
    """
    # A write anywhere in the tree disqualifies the statement, which is what catches a
    # data-modifying CTE fronted by a SELECT.
    if any(True for _ in statement.find_all(*_WRITE_NODES)):
        return False

    # `SELECT ... INTO` creates a table, so it is a write despite the Select root. The
    # INTO forms (plain, TEMP, TEMPORARY, TABLE, and behind a CTE) all set this arg.
    if isinstance(statement, exp.Select) and statement.args.get('into') is not None:
        return False

    if isinstance(statement, _READ_ROOT_NODES):
        return True

    # Bare commands sqlglot has no node class for: reads are allow-listed by name.
    if isinstance(statement, exp.Command):
        return (statement.name or '').upper() in _READ_COMMAND_ALLOW_KEYWORD_LIST

    return False


def might_write(sql: str) -> bool:
    """Report whether the SQL could change anything, erring towards True.

    Recognized reads answer False. Everything else answers True, including input this
    module cannot classify, so an unfamiliar or future statement is treated as a write
    rather than slipping through unconfirmed. False positives are expected; a False
    answer for a statement that writes is not.

    Args:
        sql: The SQL statement to classify.

    Returns:
        True when the statement might change data, schema, permissions, or session state.
    """
    # Oversized input is rejected by `assert_executable`; skip parsing it here.
    if len(sql) > MAX_SQL_LEN:
        return True

    statements = _parse(sql)  # fails closed on parse/tokenize error

    if len(statements) != 1:
        return True

    return not _is_read_statement(statements[0])
