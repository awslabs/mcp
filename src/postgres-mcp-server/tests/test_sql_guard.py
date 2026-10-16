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
    READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS,
    READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS,
    SECURITY_SENSITIVE_GUCS,
    SqlPolicyError,
    _normalize_placeholders,
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


# --- Write set (design section 3.1): one entry per category ----------------
# Every write-set statement must be REJECTED in read-only mode (FR3) and
# ALLOWED past the guard in write mode (none are in the dangerous set). The two
# tests below drive this single list both ways, so the two invariants stay in
# lock-step and every category is covered.

WRITE_SET_STATEMENTS = [
    # DML
    'INSERT INTO t VALUES (1)',
    'UPDATE t SET x = 1',
    'DELETE FROM t',
    'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE',
    'TRUNCATE t',
    # DDL
    'CREATE TABLE t (id int)',
    'ALTER TABLE t ADD COLUMN c int',
    'DROP TABLE t',
    'ALTER TABLE t RENAME TO t2',
    'CREATE VIEW v AS SELECT 1',
    'CREATE INDEX idx ON t (a)',
    'CREATE SEQUENCE seq',
    'CREATE SCHEMA s',
    'CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql',
    'CREATE EXTENSION IF NOT EXISTS citext',
    'CREATE TABLE t2 AS SELECT * FROM t',
    'CREATE MATERIALIZED VIEW mv AS SELECT 1',
    # Metadata
    "COMMENT ON TABLE t IS 'x'",
    "SECURITY LABEL ON TABLE t IS 'x'",
    'IMPORT FOREIGN SCHEMA remote FROM SERVER srv INTO local',
    # Permissions
    'GRANT SELECT ON t TO r',
    'REVOKE SELECT ON t FROM r',
    # Maintenance
    'VACUUM t',
    'ANALYZE t',
    'CLUSTER t USING idx',
    'REINDEX TABLE t',
    'REFRESH MATERIALIZED VIEW mv',
    # Procedural / dynamic
    'DO $$ BEGIN PERFORM 1; END $$',
    'CALL proc()',
    # Prepared statements
    'PREPARE p AS SELECT 1',
    'EXECUTE p',
    'DEALLOCATE p',
    # Async / locking
    'LISTEN chan',
    'NOTIFY chan',
    'UNLISTEN chan',
    'LOCK TABLE t',
    # Session / backend state. Narrow RESET/DISCARD forms are ordinary writes;
    # bulk RESET ALL / DISCARD ALL are dangerous below because they include
    # security-sensitive GUCs.
    "SET work_mem = '64MB'",
    'RESET work_mem',
    'DISCARD PLANS',
    'DISCARD SEQUENCES',
    'DISCARD TEMP',
    "LOAD 'lib'",
    "SELECT set_config('work_mem', '64MB', false)",  # function form of SET
    # Transaction control
    'BEGIN',
    'COMMIT',
    'ROLLBACK',
    'SAVEPOINT s',
    'ALTER SYSTEM SET wal_level = replica',
    # Client-side COPY (not PROGRAM, not a server file -> write set, not dangerous)
    'COPY t FROM STDIN',
    'COPY t TO STDOUT',
    # SelectStmt-that-writes, EXPLAIN-of-write, and DML-in-CTE (FR3)
    'SELECT * INTO t2 FROM t',
    'EXPLAIN INSERT INTO t VALUES (1)',
    'EXPLAIN ANALYZE INSERT INTO t VALUES (1)',
    'WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x',
    'WITH x AS (UPDATE t SET a = 1 RETURNING *) SELECT * FROM x',
    # Cursor family (Decision A tightening)
    'DECLARE c CURSOR FOR SELECT 1',
    'FETCH 1 FROM c',
    'MOVE 1 IN c',
    'CLOSE c',
    # Latent-gap commands the old regex missed
    'REASSIGN OWNED BY a TO b',
    'CHECKPOINT',
    "COMMIT PREPARED 'gid'",
]


@pytest.mark.parametrize('sql', WRITE_SET_STATEMENTS)
def test_write_set_rejected_in_read_only(sql):
    """Every write-set statement is rejected in read-only mode (FR3)."""
    assert not _allowed(sql, allow_write_query=False)


@pytest.mark.parametrize('sql', WRITE_SET_STATEMENTS)
def test_write_set_allowed_in_write_mode(sql):
    """Every write-set statement is allowed past the guard when writes are enabled.

    None of these are in the dangerous set, so allow_write_query=True must let
    them through (they may still fail at the DB, but the guard must not reject).
    """
    assert_executable(sql, allow_write_query=True)


# --- Dangerous set: rejected in BOTH modes (FR4, FR5, FR6) -----------------

DANGEROUS_BOTH_MODES = [
    # Bulk session resets include row_security/session_replication_role.
    'RESET ALL',
    'DISCARD ALL',
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


@pytest.mark.parametrize('depth', [500, 2000, 5000, 8000])
@pytest.mark.parametrize('allow_write_query', [False, True])
def test_deeply_nested_input_never_raises_uncaught(depth, allow_write_query):
    """Deeply nested input must fail closed or parse cleanly -- never crash (FR7).

    A recursive tree walk would raise RecursionError on a deep parse tree and
    escape as an uncaught exception (a DoS). The guard walks iteratively and
    wraps analysis, so the only outcomes are: allowed (a valid deep read) or
    SqlPolicyError. Any other exception fails the test.
    """
    sql = 'SELECT 1 WHERE ' + 'NOT (' * depth + 'true' + ')' * depth
    try:
        assert_executable(sql, allow_write_query=allow_write_query)
    except SqlPolicyError:
        pass  # fail-closed is an acceptable outcome


def test_rejection_message_does_not_echo_sensitive_literal():
    """Rejection messages name the construct, not the query's literal values (FR8)."""
    with pytest.raises(SqlPolicyError) as exc:
        assert_executable("SELECT pg_read_file('/etc/shadow_secret_path')")
    message = str(exc.value)
    assert 'pg_read_file' in message  # names the offending construct
    assert '/etc/shadow_secret_path' not in message  # does not echo the literal


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
    'SELECT * FROM t WHERE id=:id',  # no space before placeholder
    'SELECT * FROM t WHERE a>:x AND b<:y',  # operator-adjacent placeholders
    'SELECT ARRAY[:a] FROM t',  # placeholder as an array element
    'SELECT * FROM t WHERE id IN (:a, :b)',  # ( and , adjacency
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


# --- Array slices must not be mangled by :name normalization ----------------
# Regression: the old pattern rewrote a[1:n] -> a[1$1] (unparseable), so valid
# slice queries were wrongly rejected. The slice colon must be left alone.

ARRAY_SLICE_READS = [
    'SELECT a[1:n] FROM t',  # numeric lower bound (the reported break)
    'SELECT a[i:j] FROM t',  # identifier bounds
    'SELECT tags[1:limit_idx] FROM items',  # reviewer's real-world example
    'SELECT a[f():n] FROM t',  # lower bound ends in )
    'SELECT a[b[0]:n] FROM t',  # lower bound ends in ]
    'SELECT a[:n] FROM t',  # omitted lower bound
    'SELECT a[1:2] FROM t',  # both numeric
]


@pytest.mark.parametrize('sql', ARRAY_SLICE_READS)
def test_array_slice_not_mangled(sql):
    """Array-slice reads parse and are allowed; the slice colon is not rewritten."""
    assert_executable(sql, allow_write_query=False)


def test_normalize_placeholders_leaves_array_slices_intact():
    """The slice colon (preceded by a word char / ] / )) is not turned into $1."""
    assert _normalize_placeholders('SELECT a[1:n] FROM t') == 'SELECT a[1:n] FROM t'
    assert _normalize_placeholders('SELECT a[i:j] FROM t') == 'SELECT a[i:j] FROM t'
    assert _normalize_placeholders('SELECT a[f():n] FROM t') == 'SELECT a[f():n] FROM t'


def test_normalize_placeholders_still_rewrites_real_params():
    """Genuine :name placeholders in value positions are still replaced with $1."""
    assert _normalize_placeholders('WHERE id = :id') == 'WHERE id = $1'
    assert _normalize_placeholders('WHERE id=:id') == 'WHERE id=$1'
    assert _normalize_placeholders('(:a, :b)') == '($1, $1)'
    assert _normalize_placeholders(':v::int') == '$1::int'  # placeholder, cast preserved
    assert _normalize_placeholders('SELECT x::int') == 'SELECT x::int'  # bare cast untouched


# --- set_config first-argument edge cases -----------------------------------


@pytest.mark.parametrize(
    'sql',
    [
        'SELECT set_config()',  # no arguments
        "SELECT set_config(col, 'x', false)",  # first arg is a column, not a literal
        # A computed GUC name that resolves to a security-sensitive GUC at run
        # time -- the reported bypass. row_security is disabled for the pooled
        # connection, leaking RLS-protected rows to later queries.
        "SELECT set_config('row_' || 'security', 'off', false)",
        # A bound parameter as the GUC name (Aurora :name -> $1 after parse-only
        # normalization); the name is unknown at check time.
        "SELECT set_config(:guc, 'off', false)",
        "SELECT set_config($1, 'off', false)",
        # A function call producing the GUC name.
        "SELECT set_config(lower('ROW_SECURITY'), 'off', false)",
    ],
)
def test_set_config_non_literal_guc_rejected_in_both_modes(sql):
    """set_config with a non-literal GUC name fails closed in both modes.

    A dynamic GUC name cannot be proven safe from syntax, so it is rejected
    rather than allowed -- otherwise a computed name (``'row_' || 'security'``)
    or a bound parameter could disable a security-sensitive GUC in write mode.
    """
    assert not _allowed(sql, allow_write_query=False)
    assert not _allowed(sql, allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        "SELECT set_config('work_mem', '64MB', false)",
        "SELECT set_config('statement_timeout', '0', true)",
    ],
)
def test_set_config_literal_non_security_guc_allowed_in_write_mode(sql):
    """set_config with a literal, non-security GUC name is a plain write.

    Allowed in write mode; rejected in read-only mode (set_config for any GUC
    mutates session state -- READ_ONLY_PROHIBITED_FUNCTIONS).
    """
    assert_executable(sql, allow_write_query=True)
    assert not _allowed(sql, allow_write_query=False)


# --- Semantic function writes inside otherwise-read SelectStmt --------------


@pytest.mark.parametrize('func', sorted(READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS))
def test_every_known_mutating_function_is_read_only_blocked(func):
    """Every audited bare mutator is rejected read-only but allowed in write mode."""
    sql = f'SELECT {func}()'
    assert not _allowed(sql, allow_write_query=False)
    assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize('schema,name', sorted(READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS))
def test_every_known_qualified_mutator_is_read_only_blocked(schema, name):
    """Every audited generic extension mutator is matched by schema/name."""
    sql = f'SELECT {schema}.{name}()'
    assert not _allowed(sql, allow_write_query=False)
    assert_executable(sql, allow_write_query=True)


def test_schema_qualified_core_mutator_is_matched_by_bare_name():
    """Explicit pg_catalog qualification cannot evade the bare mutator inventory."""
    assert not _allowed("SELECT pg_catalog.nextval('s')", allow_write_query=False)
    assert not _allowed('SELECT pg_catalog.pg_switch_wal()', allow_write_query=False)


def test_pg13_pg14_legacy_backup_functions_are_read_only_writes():
    """Pre-PG15 backup entry points stay covered by the PG13-PG18 audit claim."""
    assert not _allowed("SELECT pg_start_backup('label', true)", allow_write_query=False)
    assert not _allowed('SELECT pg_stop_backup(false)', allow_write_query=False)
    assert_executable("SELECT pg_start_backup('label', true)", allow_write_query=True)
    assert_executable('SELECT pg_stop_backup(false)', allow_write_query=True)


@pytest.mark.parametrize(
    'sql',
    [
        # Sequence observation, not advancement.
        "SELECT currval('s')",
        'SELECT lastval()',
        # Ordinary volatile calculations/observations remain reads.
        'SELECT random()',
        'SELECT clock_timestamp()',
        'SELECT gen_random_uuid()',
        # Statistics, transaction-ID observation/allocation, WAL, replication,
        # and size observation. XID assignment is incidental bookkeeping needed
        # to return the current ID; it is not the requested semantic effect.
        'SELECT pg_stat_get_snapshot_timestamp()',
        'SELECT pg_stat_clear_snapshot()',
        'SELECT txid_current()',
        'SELECT pg_current_xact_id()',
        "SELECT pg_relation_size('t')",
        "SELECT pg_logical_slot_peek_changes('s', NULL, 1)",
        "SELECT pg_replication_origin_progress('origin', false)",
        # Read coordination / database-data reads.
        'SELECT pg_export_snapshot()',
        'SELECT lo_get(1)',
        'SELECT loread(1, 10)',
        # Selected extension boundaries: cache warming and FDW inspection do
        # not modify durable/logical state.
        "SELECT pg_prewarm('t')",
        'SELECT * FROM postgres_fdw_get_connections()',
        # Built-in operators calculate values; user-defined operator semantics
        # are catalog/runtime-owned and documented as outside static coverage.
        'SELECT 1 + 2',
        'SELECT ARRAY[1,2] || ARRAY[3]',
    ],
)
def test_semantic_read_function_boundaries_allowed(sql):
    """Confusing but observational/calculation cases remain allowed read-only."""
    assert_executable(sql, allow_write_query=False)


def test_qualified_mutator_does_not_overblock_same_name_elsewhere():
    """Generic pg_cron names are writes only in the audited cron schema."""
    assert_executable("SELECT schedule('* * * * *', 'SELECT 1')", allow_write_query=False)
    assert_executable("SELECT app.schedule('* * * * *', 'SELECT 1')", allow_write_query=False)
    assert not _allowed("SELECT cron.schedule('* * * * *', 'SELECT 1')", allow_write_query=False)


# --- Fail-closed wrapper: any analysis error becomes a rejection (FR7) -------


def test_analysis_exception_fails_closed(monkeypatch):
    """An unexpected error during tree analysis is converted to a rejection.

    Guards the wrapper that turns non-SqlPolicyError exceptions into a
    fail-closed SqlPolicyError instead of letting them escape uncaught.
    """

    def boom(_node):
        raise ValueError('induced analysis failure')

    # Patch by dotted path so we don't import the module under a second name
    # (a top-level `from ... import` plus `import ... as guard` trips the
    # "module imported with import and import from" lint finding).
    monkeypatch.setattr('awslabs.postgres_mcp_server.sql_guard._check_dangerous', boom)
    with pytest.raises(SqlPolicyError):
        assert_executable('SELECT 1', allow_write_query=True)
