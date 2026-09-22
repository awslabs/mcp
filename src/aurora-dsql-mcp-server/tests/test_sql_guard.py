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
from awslabs.aurora_dsql_mcp_server import sql_guard
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
        "SELECT '%s is data', $tagé$%s is also data$tagé$",
        'EXPLAIN ANALYZE SELECT * FROM t',
        'SELECT 10 % sqrt(4)',
    ],
)
def test_unparameterized_read_queries_are_allowed(sql):
    """Valid reads preserve PostgreSQL percent operators and quoted data."""
    assert_executable(sql)


@pytest.mark.parametrize(
    ('sql', 'parameter_count'),
    [
        ('SELECT * FROM t WHERE tenant_id = %s', 1),
        ('SELECT * FROM t WHERE a = %b AND b = %t', 2),
        ('SELECT 10 %% 3', 0),
        ('SELECT %s -- progress 100%', 1),
        ('SELECT %s -- progress 100%\n', 1),
    ],
)
def test_bound_psycopg_placeholders_are_allowed(sql, parameter_count):
    """Psycopg placeholders are normalized only when parameters are supplied."""
    assert_executable(sql, parameter_count=parameter_count)


def test_placeholder_normalization_matches_psycopg_raw_query_scanning():
    """Placeholders are converted across the raw text exactly as psycopg does."""
    sql = (
        """SELECT '%s', "%s", U&"%s", $tagé$%s$tagé$, value FROM t -- %s\r"""
        'WHERE id = %s AND payload = %b AND label = %t AND ratio = 10 %% 3'
    )
    assert _normalize_placeholders(sql, parameter_count=8) == (
        """SELECT '$1', "$2", U&"$3", $tagé$$4$tagé$, value FROM t -- $5\r"""
        'WHERE id = $6 AND payload = $7 AND label = $8 AND ratio = 10 % 3'
    )


def test_placeholder_normalization_matches_reported_driver_differential():
    """Markers inside strings and comments contribute to psycopg numbering."""
    sql = "SELECT '%s', id FROM t WHERE id = %s -- %s"
    assert _normalize_placeholders(sql, parameter_count=3) == (
        "SELECT '$1', id FROM t WHERE id = $2 -- $3"
    )


@pytest.mark.parametrize(
    'sql',
    [
        'SELECT %s -- progress 100%',
        'SELECT %s -- progress 100%\n',
    ],
)
def test_placeholder_normalization_preserves_psycopg_unmatched_percent(sql):
    """Terminal percent and percent before a line feed remain unchanged."""
    assert _normalize_placeholders(sql, parameter_count=1) == sql.replace('%s', '$1')


@pytest.mark.parametrize(
    ('sql', 'parameter_count'),
    [
        ('SELECT %s', 0),
        ('SELECT 1', 1),
        ("SELECT '%s', id FROM t WHERE id = %s -- %s", 1),
    ],
)
def test_placeholder_count_must_match_bound_parameters(sql, parameter_count):
    """The policy rejects the same positional parameter-count mismatches as psycopg."""
    with pytest.raises(SqlPolicyError, match='placeholders'):
        assert_executable(sql, parameter_count=parameter_count)


def test_unbound_percent_does_not_hide_mutating_function():
    """An unbound modulo operator must remain visible to the parser."""
    with pytest.raises(SqlPolicyError, match='setseed'):
        assert_executable('SELECT 1%setseed(0.5)')


@pytest.mark.parametrize('sql', ['SELECT 1 % q', 'SELECT %s -- progress 100%\r\n'])
def test_invalid_bound_placeholder_syntax_is_rejected(sql):
    """A parameters object makes unescaped percent operators invalid to psycopg."""
    with pytest.raises(SqlPolicyError, match='placeholder'):
        assert_executable(sql, parameter_count=0)


def test_malformed_normalized_sql_is_rejected():
    """Malformed parameterized SQL still fails closed after placeholder conversion."""
    with pytest.raises(SqlPolicyError, match='scanned'):
        assert_executable("SELECT '%s", parameter_count=1)


@pytest.mark.parametrize(
    'sql',
    [
        'INSERT INTO t VALUES (1)',
        "SELECT set_config('search_path', 'pg_temp', false)",
        "SELECT nextval('seq')",
        'SELECT 1; SELECT 2',
    ],
)
def test_read_only_policy_rejects_writes_and_multiple_statements(sql):
    """The parser guard fails closed for non-read SQL."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql)


def test_write_mode_allows_normal_parameterized_writes():
    """Write mode skips the read-only allowlist."""
    assert_executable('INSERT INTO t VALUES (%s)', allow_write_query=True, parameter_count=1)
    assert_executable('COPY t TO STDOUT', allow_write_query=True)
    assert_executable("SELECT set_config('work_mem', '64MB', false)", allow_write_query=True)
    assert_executable('RESET work_mem', allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        'BEGIN',
        'COMMIT',
        'ROLLBACK',
        'SAVEPOINT s',
        'RELEASE SAVEPOINT s',
    ],
)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_caller_transaction_control_is_rejected(sql, allow_write_query):
    """Callers cannot end or replace the transaction managed by transact."""
    with pytest.raises(SqlPolicyError, match='transaction control'):
        assert_executable(sql, allow_write_query=allow_write_query)


@pytest.mark.parametrize(
    'sql',
    [
        "LOAD 'library'",
        'DO $$ BEGIN PERFORM pg_sleep(1); END $$',
        'CREATE FUNCTION f() RETURNS int LANGUAGE sql AS $$ SELECT pg_sleep(1) $$',
        'CREATE PROCEDURE p() LANGUAGE sql AS $$ SELECT pg_sleep(1) $$',
        'CALL p()',
    ],
)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_native_and_opaque_execution_is_rejected(sql, allow_write_query):
    """Native loads and opaque executable definitions cannot hide denied calls."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=allow_write_query)


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


def test_table_named_async_is_not_normalized():
    """A valid PostgreSQL identifier named async remains the table name."""
    sql = 'ALTER TABLE async ADD COLUMN value int'
    assert _normalize_dsql_syntax(sql) == sql
    assert_executable(sql, allow_write_query=True)


def test_incomplete_async_shape_is_not_normalized():
    """Only ALTER TABLE ASYNC ... VALIDATE CONSTRAINT uses the DSQL extension."""
    sql = 'ALTER TABLE ASYNC t ADD COLUMN value int'
    assert _normalize_dsql_syntax(sql, postgres_parse_failed=True) == sql
    with pytest.raises(SqlPolicyError, match='parsed'):
        assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        "AWS IAM GRANT app_readonly TO 'arn:aws:iam::*:role/AppReadOnlyRole'",
        "AWS IAM REVOKE app_readonly FROM 'arn:aws:iam::*:role/AppReadOnlyRole';",
        """/* access */ AWS IAM GRANT "AppRole" TO U&'arn:aws:iam::\\0031:role/Test'""",
    ],
)
def test_dsql_iam_statements_are_allowed_in_write_mode(sql):
    """Valid Aurora DSQL IAM extensions receive parser-based classification."""
    assert_executable(sql, allow_write_query=True)


def test_dsql_iam_statement_is_rejected_in_read_only_mode():
    """DSQL IAM changes remain writes after parser-only normalization."""
    with pytest.raises(SqlPolicyError, match='read-only mode'):
        assert_executable("AWS IAM GRANT app TO 'arn:aws:iam::*:role/Test'")


@pytest.mark.parametrize(
    'sql',
    [
        "AWS IAM GRANT app FROM 'arn'",
        "AWS IAM GRANT app TO 'arn' EXTRA",
        "AWS IAM GRANT 123 TO 'arn'",
    ],
)
def test_malformed_dsql_iam_statements_fail_closed(sql):
    """Near-miss IAM syntax is rejected rather than broadly rewritten."""
    with pytest.raises(SqlPolicyError, match='parsed'):
        assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        'SET TRANSACTION READ ONLY',
        'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ',
        'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE',
        'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE, READ ONLY',
    ],
)
def test_safe_transaction_local_settings_are_allowed_in_read_only_mode(sql):
    """Read-only and isolation-only transaction settings remain compatible."""
    assert_executable(sql)


@pytest.mark.parametrize(
    'sql',
    [
        'SET TRANSACTION READ WRITE',
        'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE, READ WRITE',
        "SET work_mem = '64MB'",
    ],
)
def test_other_settings_are_rejected_in_read_only_mode(sql):
    """Session mutation and read-write escalation remain prohibited."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql)


@pytest.mark.parametrize(
    'sql',
    [
        'EXPLAIN EXECUTE prepared_read',
        'EXPLAIN (BUFFERS) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE false) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE 0) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE true, ANALYZE false) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE 1, ANALYZE 0) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE, ANALYZE false) EXECUTE prepared_read',
    ],
)
def test_explain_execute_is_allowed_when_final_analyze_option_is_disabled(sql):
    """EXPLAIN may inspect a prepared plan but ANALYZE may not execute it."""
    assert_executable(sql)


@pytest.mark.parametrize(
    'sql',
    [
        'EXPLAIN ANALYZE EXECUTE prepared_read',
        'EXPLAIN (ANALYZE 1) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE false, ANALYZE true) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE 0, ANALYZE 1) EXECUTE prepared_read',
        'EXPLAIN (ANALYZE false, ANALYZE) EXECUTE prepared_read',
    ],
)
def test_explain_execute_is_rejected_when_final_analyze_option_is_enabled(sql):
    """The last repeated ANALYZE option determines whether EXPLAIN executes."""
    with pytest.raises(SqlPolicyError, match='without ANALYZE'):
        assert_executable(sql)


def test_execute_without_explain_is_rejected():
    """EXECUTE is permitted only as a non-executing EXPLAIN target."""
    with pytest.raises(SqlPolicyError):
        assert_executable('EXECUTE prepared_read')


def test_explain_of_write_is_rejected_in_read_only_mode():
    """Nested statement nodes remain subject to the read-only allowlist."""
    with pytest.raises(SqlPolicyError, match='InsertStmt'):
        assert_executable('EXPLAIN INSERT INTO t VALUES (1)')


@pytest.mark.parametrize(
    'sql',
    [
        'SELECT invoke(1)',
        'SELECT query_export_to_s3(1)',
        'SELECT table_import_from_s3(1)',
    ],
)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_qualified_dangerous_basenames_cannot_use_search_path(sql, allow_write_query):
    """Unqualified extension calls cannot bypass schema-qualified denials."""
    with pytest.raises(SqlPolicyError, match='Dangerous function'):
        assert_executable(sql, allow_write_query=allow_write_query)


@pytest.mark.parametrize(
    'sql',
    [
        'SELECT schedule(1)',
        'SELECT schedule_in_database(1)',
        'SELECT alter_job(1)',
        'SELECT unschedule(1)',
    ],
)
def test_qualified_mutator_basenames_cannot_use_search_path_in_read_only_mode(sql):
    """Unqualified extension mutators remain blocked in read-only mode."""
    with pytest.raises(SqlPolicyError, match='mutates state'):
        assert_executable(sql)


def test_quoted_identifier_case_is_preserved():
    """Quoted case-distinct identifiers are not folded by the policy layer."""
    assert_executable('SELECT "PG_SLEEP"(1)', allow_write_query=True)
    with pytest.raises(SqlPolicyError, match='pg_sleep'):
        assert_executable('SELECT "pg_sleep"(1)', allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        "COPY (SELECT 1) TO PROGRAM 'id'",
        "COPY t FROM '/etc/passwd'",
        'DISCARD ALL',
        'RESET ALL',
        'SET row_security = off',
        'SET session_replication_role = replica',
        "SELECT set_config('row_security', 'off', false)",
        "SELECT set_config(current_setting('x'), 'off', false)",
    ],
)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_other_mode_independent_dangerous_constructs(sql, allow_write_query):
    """Host access and security-control changes are rejected in every mode."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=allow_write_query)


def test_select_into_is_rejected_in_read_only_mode():
    """SELECT INTO is represented as a SelectStmt but still writes."""
    with pytest.raises(SqlPolicyError, match='SELECT ... INTO'):
        assert_executable('SELECT 1 INTO created_table')


def test_analysis_failures_are_converted_to_policy_errors(monkeypatch):
    """Unexpected AST-analysis errors fail closed."""
    monkeypatch.setattr(sql_guard, '_collect_nodes', lambda _: (_ for _ in ()).throw(TypeError()))
    with pytest.raises(SqlPolicyError, match='analyzed'):
        assert_executable('SELECT 1')


def test_dsql_normalization_scanner_failures_are_policy_errors(monkeypatch):
    """Unexpected DSQL scanner failures also use the policy exception."""
    monkeypatch.setattr(
        sql_guard,
        '_normalize_dsql_syntax',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError()),
    )
    with pytest.raises(SqlPolicyError, match='scanned'):
        assert_executable('not valid PostgreSQL')
