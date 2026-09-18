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

"""Regression tests for the parser-based Aurora DSQL SQL guard."""

import pytest
from awslabs.aurora_dsql_mcp_server.sql_guard import (
    SqlPolicyError,
    _normalize_dsql_syntax,
    _normalize_placeholders,
    assert_executable,
)


@pytest.mark.parametrize(
    'sql',
    [
        r'''SELECT U&"pg_read_fil\0065"('/etc/passwd')''',
        r'''SELECT U&"lo_impor\0074"(0, '/etc/passwd')''',
        r'''SELECT U&"pg_sl\0065ep"(10)''',
        r'''SELECT U&"dblin\006b"('host=169.254.169.254', 'SELECT 1')''',
    ],
)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_unicode_escaped_dangerous_functions_are_rejected(sql, allow_write_query):
    """PostgreSQL-decoded function names cannot bypass the denylist."""
    with pytest.raises(SqlPolicyError, match='Dangerous function'):
        assert_executable(sql, allow_write_query=allow_write_query)


@pytest.mark.parametrize(
    'sql',
    [
        'SELECT 1',
        'SELECT * FROM t WHERE tenant_id = %s',
        'SELECT * FROM t WHERE a = %s AND b = %s',
        "SELECT '%s is data', $$%s is also data$$",
        'EXPLAIN ANALYZE SELECT * FROM t',
    ],
)
def test_read_queries_and_psycopg_placeholders_are_allowed(sql):
    """Valid reads keep working with Aurora DSQL's psycopg placeholder syntax."""
    assert_executable(sql)


def test_placeholder_normalization_skips_literals_identifiers_and_comments():
    """Only executable placeholders are rewritten."""
    sql = """SELECT '%s', "%s", $$%s$$, value FROM t -- %s
WHERE id = %s AND ratio = 10 %% 3"""
    assert _normalize_placeholders(sql) == """SELECT '%s', "%s", $$%s$$, value FROM t -- %s
WHERE id = $1 AND ratio = 10 % 3"""


@pytest.mark.parametrize(
    'sql',
    [
        'INSERT INTO t VALUES (1)',
        "SELECT set_config('search_path', 'pg_temp', false)",
        'SELECT nextval(\'seq\')',
        'SELECT 1; SELECT 2',
    ],
)
def test_read_only_policy_rejects_writes_and_multiple_statements(sql):
    """The parser guard fails closed for non-read SQL."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql)


def test_write_mode_allows_normal_writes():
    """Write mode skips the read-only allowlist."""
    assert_executable('INSERT INTO t VALUES (%s)', allow_write_query=True)


@pytest.mark.parametrize(
    ('sql', 'postgres_equivalent'),
    [
        ('CREATE INDEX ASYNC idx ON t (id)', 'CREATE INDEX  idx ON t (id)'),
        (
            'CREATE UNIQUE INDEX ASYNC idx ON t (id)',
            'CREATE UNIQUE INDEX  idx ON t (id)',
        ),
        (
            '/* migration */ ALTER TABLE ASYNC t VALIDATE CONSTRAINT valid_id',
            '/* migration */ ALTER TABLE  t VALIDATE CONSTRAINT valid_id',
        ),
    ],
)
def test_dsql_async_ddl_is_normalized_for_write_mode(sql, postgres_equivalent):
    """DSQL-only ASYNC syntax is parsed without changing executed SQL."""
    assert _normalize_dsql_syntax(sql) == postgres_equivalent
    assert_executable(sql, allow_write_query=True)


def test_dsql_async_ddl_is_still_rejected_in_read_only_mode():
    """Parser normalization must not turn DSQL DDL into an allowed read."""
    with pytest.raises(SqlPolicyError, match='Statement type not allowed'):
        assert_executable('CREATE INDEX ASYNC idx ON t (id)')
