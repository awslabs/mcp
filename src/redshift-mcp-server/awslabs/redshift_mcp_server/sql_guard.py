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


# Transaction control, denied in every access mode. The server owns transaction boundaries and
# offers them as parameters; a caller's COMMIT inside a named transaction ends it while the
# server still believes it open, so later statements autocommit while the caller thinks they are
# staged and a rollback reports success having undone nothing. Outside a transaction these are
# no-ops on a connection about to be discarded, so denying them everywhere costs nothing.
_TRANSACTION_CONTROL_KEYWORD_LIST = frozenset(
    {
        'BEGIN',
        'START',
        'COMMIT',
        'END',
        'ROLLBACK',
        'ABORT',
    }
)

# Statements that can commit whatever transaction they run in, denied inside a named transaction
# in every access mode. TRUNCATE commits and cannot be rolled back, so inside a transaction it
# ends it exactly as a COMMIT would, from a statement that reads as ordinary DML. CALL carries a
# procedure body this guard cannot read, and a NONATOMIC procedure invoked from inside a
# transaction block may issue its own COMMIT, after which the closing ROLLBACK discards nothing
# and reports success. Standalone both are honest writes, so they are refused only where a
# transaction is in play.
_IMPLICIT_COMMIT_KEYWORD_LIST = frozenset({'TRUNCATE', 'CALL'})

# The function form of SET, named here because it is matched as a function call rather than as
# a statement type or a command name.
_SET_CONFIG = 'SET_CONFIG'

# Operations denied in read-only mode: the ones a read-only transaction cannot
# neutralize. Each keyword maps to a sqlglot node type, or to a bare-command name.
_READ_ONLY_DENY_KEYWORD_LIST = (
    _TRANSACTION_CONTROL_KEYWORD_LIST
    | _IMPLICIT_COMMIT_KEYWORD_LIST
    | frozenset(
        {
            'UNLOAD',
            'CALL',
            'GRANT',
            'REVOKE',
            'VACUUM',
            'ANALYZE',
            'COMMENT',
            # Only bare `CANCEL` reaches this list. `CANCEL <pid>`, the form that does
            # anything, does not parse in this dialect and is rejected as unparseable instead.
            'CANCEL',
            # A session setting can clear the read-only property BEGIN READ ONLY established:
            # `SET transaction_read_only TO off`, `SET TRANSACTION READ WRITE`, `SET SESSION
            # CHARACTERISTICS AS TRANSACTION READ WRITE`, and `RESET` of any of those or of
            # ALL. A single statement could not exploit that, since its transaction ends with
            # the call, but a named transaction spans calls and a later statement in it would
            # write. Nothing is lost by denying them: outside a transaction a setting has no
            # future to apply to.
            'SET',
            'RESET',
            # The function form of SET, which reaches the same settings from inside an
            # ordinary projection.
            _SET_CONFIG,
            # Statements that carry SQL this guard never sees: sqlglot parses each as a bare
            # command whose body stays text, so nothing in the tree says what will run and
            # every check above is blind to it. One of these can therefore run anything the
            # rest of this list denies. `might_write` already counts all four as writes, so
            # this only brings the read-only path in line with the fallback.
            'PREPARE',
            'EXECUTE',
            'DECLARE',
            'FETCH',
        }
    )
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
        Parsed statements, with the fragments that are nothing to run dropped. A stray
        semicolon or comment-only input usually parses as ``None``, and a comment followed
        by a semicolon as a `Semicolon` node; neither carries a statement.

    Raises:
        ToolError: via `_reject` on any sqlglot error (parse/tokenize, or
            `RecursionError` on deep nesting); the original error is chained as the
            cause, not swallowed.
    """
    try:
        statements = sqlglot.parse(sql, read='redshift')
    except Exception as e:
        _reject('SQL could not be parsed', cause=e)
    return [
        statement
        for statement in statements
        if statement is not None and not isinstance(statement, exp.Semicolon)
    ]


# --- Read-only deny-list ---


def _denied_keyword(node: exp.Expression) -> str | None:
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
    # `set_config('transaction_read_only', 'off', false)` clears the property BEGIN READ ONLY
    # established, exactly as the SET statement would, while parsing as a projection with no
    # write node anywhere in it. Measured: after it, a CREATE TABLE inside the read-only
    # transaction succeeds and a commit persists it. Schema qualification does not hide it,
    # since pg_catalog.set_config parses to this same node.
    if isinstance(node, exp.Anonymous) and (node.name or '').upper() == _SET_CONFIG:
        return _SET_CONFIG
    # Generic/bare commands sqlglot has no dedicated class for: UNLOAD, CALL, VACUUM,
    # and any other deny-listed word surfaced as a command (matched by name).
    if isinstance(node, exp.Command):
        name = (node.name or '').upper()
        if name in _READ_ONLY_DENY_KEYWORD_LIST:
            return name
    return None


def _denied_root(statement: exp.Expression, keywords: frozenset[str]) -> str | None:
    """Map a whole-statement bare identifier to one of `keywords`, or None.

    sqlglot parses `START`/`ABORT` (and their WORK/TRANSACTION variants) as bare
    identifiers rather than statement nodes, so they are classified by the root
    identifier only. The check is root-only so a deny-listed word used as a column
    deeper in a query (e.g. `SELECT abort FROM t`) is not flagged.

    Args:
        statement: The parsed statement (tree root).
        keywords: The deny-list to match against.

    Returns:
        The matching keyword, or None.
    """
    node = statement.this if isinstance(statement, exp.Alias) else statement
    if isinstance(node, exp.Column):
        name = node.name.upper()
        if name in keywords:
            return name
    return None


def _denied_operation(statement: exp.Expression, keywords: frozenset[str]) -> str | None:
    """Return the keyword if the statement is, or contains, one of `keywords`.

    First classifies a whole-statement bare identifier (the `START`/`ABORT` family),
    then walks the entire parse tree (defense-in-depth, not just the root) so a denied
    operation cannot hide behind comment/parenthesis/position desync.

    Args:
        statement: A parsed sqlglot statement.
        keywords: The deny-list to match against.

    Returns:
        The matching keyword, or None if no node is one of them.
    """
    keyword = _denied_root(statement, keywords)
    if keyword is not None:
        return keyword
    for node in statement.walk():
        keyword = _denied_keyword(node)
        if keyword is not None and keyword in keywords:
            return keyword
    return None


def assert_executable(
    sql: str, enforce_read_only: bool = True, in_transaction: bool = False
) -> None:
    """Validate that the SQL is a single permitted statement.

    Fails closed: oversized input and any parser error are rejected.

    Args:
        sql: The SQL statement to validate.
        enforce_read_only: When False, skip the read-only statement-type deny-list. The
            single-statement rule and the transaction-control denial apply either way.
        in_transaction: True when the statement runs inside a named transaction, which also
            denies statements that would commit it out from under the server.

    Raises:
        ToolError: If the SQL is rejected by the guard.
    """
    if len(sql) > MAX_SQL_LEN:
        _reject('SQL exceeds the maximum allowed length')

    statements = _parse(sql)  # fails closed on parse/tokenize error

    # Nothing to run is its own condition. Folded into the rule below, whitespace or a comment
    # was answered with 'only a single statement is allowed', which names the opposite problem.
    if not statements:
        _reject('sql holds no statement to execute')

    if len(statements) != 1:
        _reject('Only a single SQL statement is allowed')

    # Read-only first: its list already contains everything the two below match, so in read-only
    # mode they never fire and its wording, the one callers have always seen, is preserved. Only
    # read-write reaches them.
    if enforce_read_only:
        keyword = _denied_operation(statements[0], _READ_ONLY_DENY_KEYWORD_LIST)
        if keyword is not None:
            _reject(f'Statement type not allowed in read-only mode: {keyword}')

    keyword = _denied_operation(statements[0], _TRANSACTION_CONTROL_KEYWORD_LIST)
    if keyword is not None:
        _reject(
            f'Transaction control is not available to a statement: {keyword}. Use the '
            f'begin_transaction, in_transaction, commit_transaction and rollback_transaction '
            f'parameters, which keep this server and the engine agreeing on what is open.'
        )

    if in_transaction:
        keyword = _denied_operation(statements[0], _IMPLICIT_COMMIT_KEYWORD_LIST)
        if keyword is not None:
            _reject(
                f'{keyword} can commit the transaction it runs in, and what it commits cannot '
                f'be rolled back, so it is not available inside a named transaction. Close the '
                f'transaction first, then run it on its own.'
            )


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

    # Changing session state is not a read either. This is what keeps the fallback, where
    # `might_write` is the only gate, from running the function form of SET unwrapped.
    if any((node.name or '').upper() == _SET_CONFIG for node in statement.find_all(exp.Anonymous)):
        return False

    # `SELECT ... INTO` creates a table, so it is a write despite the Select root. Searched
    # for anywhere in the tree rather than on the root, because Redshift's grammar allows a
    # set operation or parentheses around it, which put the Select carrying INTO under a
    # Union, Intersect, Except or Subquery root that _READ_ROOT_NODES would otherwise accept.
    if any(True for _ in statement.find_all(exp.Into)):
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
