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

"""Unit tests for the parser-based SQL policy guard (``sql_guard``).

Covers, per docs/design/parser-based-sql-policy.md section 7:
* the evasion corpus (U&/UESCAPE/quoted/comment variants),
* dangerous functions Tiers 1-3 and the schema-qualified negative case,
* the read-only allow-set and reject-set (incl. EXPLAIN, SELECT INTO,
  cursor family, latent-gap commands),
* write-mode behavior, and
* fail-closed handling (parse error, oversized, multi-statement).
"""

import pytest
from awslabs.postgres_mcp_server.sql_guard import (
    DANGEROUS_FUNCTIONS,
    DANGEROUS_QUALIFIED_FUNCTIONS,
    MAX_SQL_LEN,
    SECURITY_SENSITIVE_GUCS,
    SqlPolicyError,
    assert_executable,
)


def _allowed(sql: str, allow_write_query: bool = False) -> bool:
    """Return True if the guard accepts ``sql``, False if it raises SqlPolicyError."""
    try:
        assert_executable(sql, allow_write_query=allow_write_query)
        return True
    except SqlPolicyError:
        return False


# --- Read-only allow-set (FR2) ---------------------------------------------

READ_ONLY_ALLOWED = [
    'SELECT 1',
    'SELECT * FROM t WHERE id = 5',
    'WITH x AS (SELECT 1) SELECT * FROM x',
    'VALUES (1), (2)',
    'TABLE t',
    'SHOW work_mem',
    'SHOW ALL',
    'EXPLAIN SELECT 1',
    'EXPLAIN ANALYZE SELECT 1',
    'EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM t',
    'SELECT * FROM t FOR UPDATE',  # locking clause, still a read
    'SELECT a FROM t UNION SELECT b FROM u',  # group-3 heuristic dropped
    'SELECT * FROM t WHERE id = 5 OR 1=1',  # group-3 heuristic dropped
    "SELECT 'please drop by the office'",  # string literal containing 'drop'
    'SELECT count(*) FROM t GROUP BY x HAVING count(*) > 1',
]


@pytest.mark.parametrize('sql', READ_ONLY_ALLOWED)
def test_read_only_allowed(sql):
    """Legitimate reads pass in read-only mode."""
    assert_executable(sql, allow_write_query=False)


# --- Read-only reject-set (write set, FR3) ---------------------------------

READ_ONLY_REJECTED = [
    'INSERT INTO t VALUES (1)',
    'UPDATE t SET x = 1',
    'DELETE FROM t',
    'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE',
    'TRUNCATE t',
    'CREATE TABLE t (id int)',
    'DROP TABLE t',
    'ALTER TABLE t ADD COLUMN c int',
    'GRANT SELECT ON t TO r',
    'REVOKE SELECT ON t FROM r',
    'CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql',
    'CALL proc()',
    'DO $$ BEGIN PERFORM 1; END $$',
    'VACUUM t',
    'REINDEX TABLE t',
    'REFRESH MATERIALIZED VIEW mv',
    'LOCK TABLE t',
    'LISTEN chan',
    'NOTIFY chan',
    "LOAD 'lib'",
    'CREATE TABLE t2 AS SELECT * FROM t',
    'CREATE MATERIALIZED VIEW mv AS SELECT 1',
    # SelectStmt-that-writes (field checks)
    'SELECT * INTO t2 FROM t',
    "SELECT set_config('work_mem', '64MB', false)",
    # EXPLAIN of a write
    'EXPLAIN INSERT INTO t VALUES (1)',
    'EXPLAIN ANALYZE INSERT INTO t VALUES (1)',
    # data-modifying CTE
    'WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x',
    'WITH x AS (UPDATE t SET a = 1 RETURNING *) SELECT * FROM x',
    # latent-gap commands the old regex missed
    'REASSIGN OWNED BY a TO b',
    'CHECKPOINT',
    "COMMIT PREPARED 'gid'",
    'UNLISTEN chan',
    'DEALLOCATE p',
    'BEGIN',
    'COMMIT',
    'ROLLBACK',
    'SAVEPOINT s',
    'ALTER SYSTEM SET wal_level = replica',
    # cursor family (Decision A tightening)
    'DECLARE c CURSOR FOR SELECT 1',
    'FETCH 1 FROM c',
    'MOVE 1 IN c',
    'CLOSE c',
    # prepared statements
    'PREPARE p AS SELECT 1',
    'EXECUTE p',
]


@pytest.mark.parametrize('sql', READ_ONLY_REJECTED)
def test_read_only_rejected(sql):
    """Write-set / cursor / latent-gap statements are rejected in read-only mode."""
    assert not _allowed(sql, allow_write_query=False)


# --- Dangerous set: rejected in BOTH modes (FR4, FR5, FR6) -----------------

DANGEROUS_BOTH_MODES = [
    # COPY command execution / host filesystem
    "COPY (SELECT 1) TO PROGRAM 'id'",
    "COPY t FROM PROGRAM 'curl http://x'",
    "COPY t TO '/tmp/out.csv'",
    "COPY t FROM '/etc/passwd'",
    # dangerous functions (bare)
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT pg_read_binary_file('/etc/passwd')",
    "SELECT lo_import('/etc/passwd')",
    'SELECT pg_sleep(10)',
    'SELECT pg_terminate_backend(123)',
    'SELECT pg_advisory_lock(1)',
    "SELECT dblink('host=169.254.169.254', 'SELECT 1')",
    "SELECT dblink_connect('h=1')",
    "SELECT pg_notify('c', 'p')",
    # Tier 1 - pg_ls_dir siblings
    "SELECT pg_ls_dir('/')",
    'SELECT pg_ls_waldir()',
    'SELECT pg_ls_tmpdir()',
    'SELECT pg_ls_logdir()',
    # Tier 2 - adminpack
    "SELECT pg_file_write('/tmp/x', 'data', false)",
    "SELECT pg_file_unlink('/tmp/x')",
    # Tier 3 - schema-qualified Aurora
    "SELECT aws_lambda.invoke('arn', '{}')",
    "SELECT aws_s3.query_export_to_s3('SELECT 1', 'bucket', 'key')",
    "SELECT aws_s3.table_import_from_s3('t', '', '', 'b', 'k', 'r')",
    # security-sensitive GUCs (SET and set_config forms)
    'SET row_security = off',
    'SET session_replication_role = replica',
    "SELECT set_config('row_security', 'off', false)",
    "SELECT set_config('session_replication_role', 'replica', false)",
    # dangerous inside FROM / subquery / CTE
    "SELECT * FROM dblink('h', 'q') AS t(a text)",
    "SELECT (SELECT pg_read_file('/x'))",
    "WITH x AS (SELECT pg_read_file('/x')) SELECT * FROM x",
]


@pytest.mark.parametrize('sql', DANGEROUS_BOTH_MODES)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_dangerous_rejected_both_modes(sql, allow_write_query):
    """Dangerous constructs are rejected regardless of read/write mode."""
    assert not _allowed(sql, allow_write_query=allow_write_query)


# --- Encoding evasion: U& / quoted / comment spellings still rejected -------

EVASION_VARIANTS = [
    # U&-escaped identifiers resolving to a dangerous function (the reported bug)
    r"""SELECT U&"pg_read_fil\0065"('/etc/passwd')""",
    r"""SELECT U&"lo_impor\0074"(0, '/etc/passwd')""",
    r"""SELECT U&"pg_sl\0065ep"(10)""",
    r"""SELECT U&"dblin\006b"('host=169.254.169.254', 'SELECT 1')""",
    r"""SELECT set_config(U&'row_securit\0079', 'off', false)""",
    # double-quoted identifier
    'SELECT "pg_read_file"(\'/x\')',
    # comment wedged between name and paren
    "SELECT pg_read_file /**/ ('/x')",
    # dollar-quoted / mixed case
    "SELECT PG_READ_FILE('/x')",
]


@pytest.mark.parametrize('sql', EVASION_VARIANTS)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_encoding_evasions_rejected(sql, allow_write_query):
    """U&/quoted/comment/case spellings of dangerous names are still rejected."""
    assert not _allowed(sql, allow_write_query=allow_write_query)


# --- Schema-qualified matching must not over-block innocent names ----------

QUALIFIED_NEGATIVE = [
    'SELECT invoke(1)',  # bare user function named invoke
    "SELECT myschema.invoke('a')",  # invoke in a non-aws_lambda schema
    'SELECT query_export_to_s3(1)',  # bare name, different schema semantics
]


@pytest.mark.parametrize('sql', QUALIFIED_NEGATIVE)
def test_qualified_negative_not_overblocked(sql):
    """A generic name (invoke) outside its dangerous schema is allowed."""
    assert_executable(sql, allow_write_query=True)


# --- Write mode: writes allowed, dangerous still blocked -------------------

WRITE_MODE_ALLOWED = [
    'INSERT INTO t VALUES (1)',
    'UPDATE t SET x = 1',
    'DELETE FROM t WHERE id = 1',
    'DROP TABLE t',
    'TRUNCATE t',
    'GRANT SELECT ON t TO r',
    'CREATE TABLE t (id int)',
    'SELECT * INTO t2 FROM t',
    "SELECT set_config('work_mem', '64MB', false)",  # generic GUC ok in write mode
    'CALL proc()',
    'DO $$ BEGIN PERFORM 1; END $$',
]


@pytest.mark.parametrize('sql', WRITE_MODE_ALLOWED)
def test_write_mode_allows_writes(sql):
    """With writes enabled, write-set statements are permitted."""
    assert_executable(sql, allow_write_query=True)


# --- Fail-closed (FR7, FR1) ------------------------------------------------

FAIL_CLOSED = [
    '',
    '   ',
    '-- only a comment',
    '/* block comment */',
    ';',
    'SELECT 1; SELECT 2',  # multi-statement
    'INSERT INTO t VALUES (1); DROP TABLE t',  # stacked
    'SELCT bogus (((',  # syntax error
    'SELECT * FROM',  # incomplete
]


@pytest.mark.parametrize('sql', FAIL_CLOSED)
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_fail_closed(sql, allow_write_query):
    """Empty, multi-statement, and malformed input is rejected in both modes."""
    assert not _allowed(sql, allow_write_query=allow_write_query)


def test_oversized_rejected():
    """Input beyond MAX_SQL_LEN is rejected before parsing."""
    huge = 'SELECT ' + ('1,' * MAX_SQL_LEN) + '1'
    assert len(huge) > MAX_SQL_LEN
    assert not _allowed(huge, allow_write_query=True)


def test_reject_raises_sql_policy_error():
    """Rejections raise SqlPolicyError with a non-empty message."""
    with pytest.raises(SqlPolicyError) as exc:
        assert_executable('DROP TABLE t', allow_write_query=False)
    assert str(exc.value)


# --- Data-driven drift guards ----------------------------------------------


@pytest.mark.parametrize('func', sorted(DANGEROUS_FUNCTIONS))
def test_every_dangerous_function_is_blocked(func):
    """Each bare dangerous function name is rejected when called (both modes)."""
    sql = f'SELECT {func}()'
    assert not _allowed(sql, allow_write_query=False)
    assert not _allowed(sql, allow_write_query=True)


@pytest.mark.parametrize('schema,name', sorted(DANGEROUS_QUALIFIED_FUNCTIONS))
def test_every_qualified_dangerous_function_is_blocked(schema, name):
    """Each schema-qualified dangerous function is rejected (both modes)."""
    sql = f'SELECT {schema}.{name}()'
    assert not _allowed(sql, allow_write_query=False)
    assert not _allowed(sql, allow_write_query=True)


@pytest.mark.parametrize('guc', sorted(SECURITY_SENSITIVE_GUCS))
def test_every_security_guc_is_blocked(guc):
    """Each security-sensitive GUC is rejected via SET and set_config (both modes)."""
    for sql in (f'SET {guc} = off', f"SELECT set_config('{guc}', 'x', false)"):
        assert not _allowed(sql, allow_write_query=False)
        assert not _allowed(sql, allow_write_query=True)


# --- Named-placeholder (:name) parse-only normalization --------------------

NAMED_PARAM_ALLOWED = [
    'SELECT * FROM users WHERE id = :id',
    'SELECT * FROM t WHERE a = :a AND b = :b',
    'SELECT * FROM t WHERE name = :name AND flag = :flag::bool',  # :: cast preserved
    'SELECT * FROM information_schema.columns WHERE table_name = :table_name',
]


@pytest.mark.parametrize('sql', NAMED_PARAM_ALLOWED)
def test_named_placeholder_reads_allowed(sql):
    """Aurora-style :name placeholders in a read parse and pass (parse-only $1)."""
    assert_executable(sql, allow_write_query=False)


def test_named_placeholder_does_not_hide_writes():
    """A write using :name placeholders is still rejected in read-only mode."""
    assert not _allowed('INSERT INTO t (a) VALUES (:a)', allow_write_query=False)


def test_named_placeholder_does_not_hide_dangerous():
    """A dangerous call using :name placeholders is rejected in both modes."""
    assert not _allowed('SELECT pg_read_file(:path)', allow_write_query=False)
    assert not _allowed('SELECT pg_read_file(:path)', allow_write_query=True)
