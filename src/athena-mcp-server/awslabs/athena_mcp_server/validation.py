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

"""SQL validation for Athena MCP server to enforce read-only access."""

from __future__ import annotations

from sqlglot import exp, parse
from sqlglot.errors import ParseError


def _is_read_only_command(node: exp.Expression) -> bool:
    # sqlglot doesn't parse SHOW to exp.Show, so we need to check for it by name
    return isinstance(node, exp.Command) and node.name.upper() in {'SHOW'}


def validate_query(query: str) -> None:
    """Validate that *query* is parsable and read-only.

    Args:
        query: Athena SQL query to validate

    The function raises ``ValueError`` if the query:
    1. is empty,
    2. fails to parse,
    3. contains more than one statement, or
    4. would mutate data or metadata.

    Examples:
    --------
    >>> validate_query('SELECT * FROM sales LIMIT 10')  # passes
    >>> validate_query('INSERT INTO t SELECT 1')  # doctest:+ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: INSERT statements are not permitted
    """
    if not query or not query.strip():
        raise ValueError('Query cannot be empty')

    try:
        [statement, *extra_statements] = parse(query, read='athena')
        if not statement:
            raise ValueError('Parsed statement is None')
    except (ParseError, ValueError) as exc:
        raise ValueError(f'SQL parse error: {exc}') from exc

    if extra_statements:
        raise ValueError('Expected exactly one SQL statement')

    # sqlglot doesn't automatically parse the inner query of EXPLAIN or EXPLAIN ANALYZE
    # statements (the inner query just becomes a single node in the parse tree), so we need to
    # recurse on that inner query to check if it's read-only
    if isinstance(statement, exp.Command) and statement.name.upper().startswith('EXPLAIN'):
        if not statement.expression:
            raise ValueError('Incomplete EXPLAIN statement')
        inner_query = (
            statement.expression.this
            if isinstance(statement.expression, exp.Literal)
            else str(statement.expression)
        )
        # Remove ANALYZE prefix if present
        inner_query = (
            inner_query[8:].strip() if inner_query.upper().startswith('ANALYZE ') else inner_query
        )
        validate_query(inner_query)
        return

    if isinstance(statement, (exp.Query, exp.Values, exp.Describe)) or _is_read_only_command(
        statement
    ):
        for node in statement.walk():
            if isinstance(node, (exp.DML, exp.DDL)):
                raise ValueError(f'{node.key.upper()} statements are not permitted')
            if isinstance(node, exp.Command) and not _is_read_only_command(node):
                raise ValueError(f'{node.name.upper()} commands are not permitted')
    else:
        # Block everything else
        statement_name = (
            statement.key.upper() if hasattr(statement, 'key') else statement.name.upper()
        )
        raise ValueError(f'{statement_name} statements are not permitted')
