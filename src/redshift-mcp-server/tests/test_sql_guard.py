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

"""Tests for the read-only SQL guard (`assert_executable`).

Each class drives the guard through its public `assert_executable` entry point and
pins one behavior; cases reflect how sqlglot (Redshift dialect) parses each input.
"""

import pytest
from awslabs.redshift_mcp_server.consts import MAX_SQL_LEN
from awslabs.redshift_mcp_server.sql_guard import assert_executable, might_write
from mcp.server.mcpserver.exceptions import ToolError


# Placeholder IAM role ARN for UNLOAD payloads.
_ARN = 'arn:aws:iam::000000000000:role/none'


class TestNestedCommentBypassRegression:
    """Regression: a denied statement following a nested block-comment prefix is rejected.

    sqlglot nests `/* ... */` the way Redshift does, so the guard classifies the
    statement the engine actually runs, not a decoy hidden by comment desync.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            f"/* a /* b */ SELECT 1 FROM */ UNLOAD ('select 1') TO 's3://b/p' IAM_ROLE '{_ARN}'",
            '/* a /* b */ SELECT 1 FROM */ TRUNCATE x',
            "/* a /* b */ SELECT 1 FROM */ COMMENT ON TABLE x IS 'y'",
        ],
    )
    def test_nested_comment_prefix_then_denied_statement_is_rejected(self, sql):
        """A denied statement hidden behind a nested-comment prefix is rejected."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    def test_nested_comment_prefix_then_select_cannot_smuggle_a_denied_op(self):
        """A benign SELECT after the comment prefix is allowed; the same prefix before a denied statement is rejected."""
        # Accepted: parses to a single benign SELECT.
        assert_executable('/* a /* b */ SELECT 1 FROM */ SELECT 99 AS pwned')

        # The same prefix before a denied statement is rejected, so it cannot smuggle.
        with pytest.raises(ToolError):
            assert_executable('/* a /* b */ SELECT 1 FROM */ TRUNCATE pwned')

    def test_nested_comment_that_swallows_a_denied_op_then_benign_select_is_allowed(self):
        """A denied op enclosed in a nested comment is inert; only the trailing real statement is classified."""
        # sqlglot: parses to one exp.Select (`SELECT 2 AS c`); the `; TRUNCATE ... ;` sits
        # inside the nested comment, not in the AST.
        assert_executable('/* /* */ SELECT 1 ; TRUNCATE public.no_such_xyz ; */ SELECT 2 AS c')


class TestAllowedReads:
    """A single read statement passes the guard without raising."""

    def test_select_literal_is_allowed(self):
        """The simplest read (`SELECT 1`) is permitted."""
        assert_executable('SELECT 1')

    @pytest.mark.parametrize(
        'sql',
        [
            'WITH a AS (SELECT 1) SELECT * FROM a',
            'SHOW search_path',
            'TABLE foo',
            '(SELECT 1)',
        ],
    )
    def test_read_shapes_are_allowed(self, sql):
        """CTE, SHOW, TABLE, and parenthesized SELECT all pass the guard."""
        assert_executable(sql)


class TestDenyList:
    """Statements whose AST operation is deny-listed are rejected."""

    @pytest.mark.parametrize(
        'sql',
        [
            'BEGIN',
            'BEGIN WORK',
            'BEGIN TRANSACTION',
            'START',
            'START TRANSACTION',
            'COMMIT',
            'COMMIT WORK',
            'COMMIT TRANSACTION',
            'END',
            'END WORK',
            'END TRANSACTION',
            'ROLLBACK',
            'ROLLBACK WORK',
            'ROLLBACK TRANSACTION',
            'ABORT',
            'ABORT WORK',
            'ABORT TRANSACTION',
        ],
    )
    def test_transaction_control_is_rejected(self, sql):
        """Transaction-control statements (with WORK/TRANSACTION variants) are rejected."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            'commit',
            'CoMmIt',
            '  COMMIT',
            '\t\r\n COMMIT',
            '/* block */ COMMIT',
            '/* block */COMMIT',
            '-- line comment\nCOMMIT',
            '/* a */ /* b */ rollback',
        ],
    )
    def test_case_and_leading_trivia_variants_are_rejected(self, sql):
        """Mixed case and leading whitespace/comments do not hide a deny-listed keyword."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            'TRUNCATE foo',
            'TRUNCATE TABLE foo',
            'TRUNCATE"foo"',
            'truncate"foo"',
        ],
    )
    def test_truncate_is_rejected(self, sql):
        """`TRUNCATE`, including the no-space `TRUNCATE"tbl"` form, is rejected."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            'GRANT SELECT ON foo TO bob',
            'REVOKE SELECT ON foo FROM bob',
            'VACUUM',
            'VACUUM foo',
            'ANALYZE',
            'ANALYZE foo',
            "COMMENT ON TABLE foo IS 'note'",
            'CALL my_proc()',
            "UNLOAD ('SELECT 1') TO 's3://bucket/prefix'",
            f"UNLOAD ('SELECT 1') TO 's3://bucket/prefix' IAM_ROLE '{_ARN}'",
        ],
    )
    def test_egress_dcl_maintenance_and_call_are_rejected(self, sql):
        """Egress, DCL, maintenance, comment, and CALL statements are rejected."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    def test_cancel_is_rejected_by_whichever_path_reaches_it(self):
        """`CANCEL` is refused either way, but only its bare form reaches the deny list.

        `CANCEL <pid>` does not parse in this dialect, so it is rejected before the deny list
        is consulted. Pinning both paths keeps the entry from looking like it covers the form
        that carries a pid.
        """
        with pytest.raises(ToolError, match='SQL could not be parsed'):
            assert_executable('CANCEL 12345')

        with pytest.raises(ToolError, match='not allowed in read-only mode: CANCEL'):
            assert_executable('CANCEL')

    @pytest.mark.parametrize(
        'sql',
        [
            ';COMMIT',
        ],
    )
    def test_leading_semicolon_before_deny_keyword_is_rejected(self, sql):
        """Leading semicolons cannot smuggle a deny-listed keyword past the guard."""
        with pytest.raises(ToolError):
            assert_executable(sql)

    def test_truncate_rejection_reason_is_pinned(self):
        """A denied TRUNCATE surfaces the `Statement type not allowed` reason."""
        with pytest.raises(ToolError, match='Statement type not allowed'):
            assert_executable('TRUNCATE foo')


class TestTransactionControlIsRefusedInEveryMode:
    """The server owns transaction boundaries, so a statement may never move them.

    Read-write mode used to skip the whole deny-list, which let a caller's COMMIT reach the
    session of a named transaction. The engine committed and the server went on believing the
    transaction open: later statements autocommitted while the caller thought them staged, and
    a rollback reported success having undone nothing.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            'BEGIN',
            'BEGIN WORK',
            'BEGIN TRANSACTION',
            'START',
            'START TRANSACTION',
            'COMMIT',
            'COMMIT WORK',
            'COMMIT TRANSACTION',
            'END',
            'END WORK',
            'END TRANSACTION',
            'ROLLBACK',
            'ROLLBACK WORK',
            'ROLLBACK TRANSACTION',
            'ABORT',
            'ABORT WORK',
            'ABORT TRANSACTION',
        ],
    )
    def test_rejected_with_read_only_enforcement_off(self, sql):
        """Refused in read-write mode too, where the deny-list no longer applies."""
        with pytest.raises(ToolError, match='Transaction control is not available'):
            assert_executable(sql, enforce_read_only=False)

    def test_the_refusal_names_the_parameters_to_use_instead(self):
        """A caller told only "no" would have nowhere to go, since transactions are supported."""
        with pytest.raises(ToolError, match='in_transaction'):
            assert_executable('COMMIT', enforce_read_only=False)


class TestImplicitCommitInsideATransaction:
    """Statements that can commit the transaction they run in are refused inside a named one.

    Both arrive at the same place from different directions. TRUNCATE is documented as
    committing and as impossible to roll back. CALL carries a procedure body the guard cannot
    read, and a NONATOMIC procedure may issue its own COMMIT from inside a transaction block.
    Either ends the transaction while the server still believes it open, which is the COMMIT
    desync arriving from a statement that reads as ordinary DML.

    Measured through this server before CALL was refused: a staged INSERT and the procedure's
    own row both persisted after rollback_transaction reported success.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            'TRUNCATE t',
            'TRUNCATE TABLE t',
            'TRUNCATE"t"',
            'CALL sp_purge(1)',
            'CALL public.sp_purge()',
        ],
    )
    def test_rejected_inside_a_transaction(self, sql):
        """Every spelling the guard recognises, in read-write mode where the deny-list is off."""
        with pytest.raises(ToolError, match='can commit the transaction it runs in'):
            assert_executable(sql, enforce_read_only=False, in_transaction=True)

    @pytest.mark.parametrize(
        'sql', ['TRUNCATE t', 'TRUNCATE TABLE t', 'CALL sp_purge(1)', 'CALL public.sp_purge()']
    )
    def test_allowed_standalone_in_read_write_mode(self, sql):
        """Outside a transaction it is an honest write, and refusing it would remove a capability."""
        assert_executable(sql, enforce_read_only=False)


class TestMultiStatement:
    """Submissions with more than one executable statement are rejected."""

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT 1; SELECT 2',
            'SET transaction_read_only TO off; CREATE TABLE t (id int)',
            'SET transaction_read_only TO off; TRUNCATE"t"',
        ],
    )
    def test_multi_statement_is_rejected(self, sql):
        """Stacked statements (mode-flip + write, GUC-flip + truncate, stacked reads) are rejected."""
        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        ['', '   ', '\n\t ', ';', '-- just a comment', '/* nothing here */'],
        ids=['empty', 'spaces', 'whitespace', 'semicolon', 'line_comment', 'block_comment'],
    )
    def test_a_statement_that_is_absent_is_refused_as_absent(self, sql):
        """Nothing to run is the opposite of too much to run, and must not read as it.

        Folded into the single-statement rule, a caller who sent one blank string was told they
        had sent more than one, and pointed at splitting a submission they never made.
        """
        with pytest.raises(ToolError, match='no statement to execute'):
            assert_executable(sql)


class TestSessionSettings:
    """Session settings are rejected in read-only mode, because one of them clears it.

    They were allowed while every call was its own session, on the grounds that a single
    statement plus `BEGIN READ ONLY` rendered them inert. Named transactions span calls, so
    `SET transaction_read_only TO off` inside one strips the read-only property and every
    later statement in that transaction writes for real. Denying the pair costs nothing:
    outside a transaction a setting has no later statement to apply to.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            'SET transaction_read_only TO off',
            'SET transaction_read_only = off',
            'SET SESSION transaction_read_only TO off',
            'SET LOCAL transaction_read_only TO off',
            'SET TRANSACTION READ WRITE',
            'SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE',
            'RESET transaction_read_only',
            'RESET ALL',
        ],
        ids=[
            'set_to_off',
            'set_equals_off',
            'set_session',
            'set_local',
            'set_transaction',
            'session_characteristics',
            'reset_it',
            'reset_all',
        ],
    )
    def test_statements_that_clear_read_only_are_rejected(self, sql):
        """Each of these would let a later statement in the same transaction write."""
        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            "SELECT set_config('transaction_read_only', 'off', false)",
            "SELECT pg_catalog.set_config('transaction_read_only', 'off', false)",
            "SELECT SET_CONFIG('transaction_read_only', 'off', false) AS applied",
            "WITH c AS (SELECT set_config('transaction_read_only', 'off', false) AS v) "
            'SELECT * FROM c',
        ],
    )
    def test_the_function_form_of_set_is_rejected_too(self, sql):
        """It clears the same property from inside a projection with no write node in it.

        Reproduced on a cluster through this server: after one of these, a CREATE TABLE inside
        the read-only transaction succeeded and commit_transaction persisted it.
        """
        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            assert_executable(sql)

    def test_reading_a_session_setting_is_still_allowed(self):
        """Only changing one is the problem; `current_setting` answers a question."""
        assert_executable("SELECT current_setting('transaction_read_only')")

    @pytest.mark.parametrize(
        'sql',
        [
            "PREPARE p AS SELECT set_config('transaction_read_only', 'off', false)",
            'EXECUTE p',
            "DECLARE c CURSOR FOR SELECT set_config('transaction_read_only', 'off', false)",
            'FETCH ALL FROM c',
        ],
    )
    def test_statements_carrying_hidden_sql_are_rejected(self, sql):
        """Their body stays text, so every check here is blind to what will run.

        One of these can therefore carry anything the rest of the deny-list refuses, which is
        how the function form of SET was reached in read-only mode after being denied directly.
        """
        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            'SET search_path TO public',
            "SET SESSION query_group = 'x'",
            'RESET search_path',
        ],
    )
    def test_harmless_session_settings_are_rejected_too(self, sql):
        """Told apart from the dangerous ones only by a value, so the whole pair goes."""
        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        ['SET search_path TO public', 'SET transaction_read_only TO off', 'RESET ALL'],
    )
    def test_session_settings_are_allowed_when_writes_are(self, sql):
        """A caller permitted to write gains nothing from clearing a property it does not have."""
        assert_executable(sql, enforce_read_only=False)


class TestNoFalsePositives:
    """A deny-listed word used as an identifier, alias, or string literal is allowed.

    Detection is structural, so a deny-listed keyword that appears only as a column,
    alias, string literal, or comment is not a denied node.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            "SELECT '; COMMIT;'",
            'SELECT $$ ; COMMIT ; $$ AS x',
            'SELECT 1 /* outer /* inner */ outer */',
            'SELECT 1 AS grant',
            'SELECT abort FROM t',
            'SELECT start, end FROM t',
        ],
    )
    def test_keyword_text_as_identifier_alias_or_literal_is_allowed(self, sql):
        """A single read is allowed even when it embeds deny-listed keyword text."""
        assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            "SELECT '; COMMIT;'",
            'SELECT $$ ; COMMIT ; $$ AS x',
            'SELECT abort FROM t',
            'SELECT start, end FROM t',
            "INSERT INTO t (note) VALUES ('commit')",
            'UPDATE t SET rollback_count = rollback_count + 1',
        ],
    )
    def test_keyword_text_is_still_allowed_in_read_write_mode(self, sql):
        """The transaction-control check runs in read-write mode, so it must not overreach.

        Read-write mode previously ran no statement-type check at all, so this is the mode
        where a new false positive would first be felt - on ordinary writes, at that.
        """
        assert_executable(sql, enforce_read_only=False)

    def test_dollar_quoted_body_with_semicolons_is_a_single_statement(self):
        """A `$$…$$` body containing `;` is one statement (not split), and allowed."""
        assert_executable('SELECT $$ a ; COMMIT ; b $$ AS payload')


class TestFailClosed:
    """The guard denies when it cannot confidently classify the input."""

    def test_oversized_sql_is_rejected(self):
        """SQL longer than MAX_SQL_LEN is rejected without further parsing."""
        from awslabs.redshift_mcp_server.consts import MAX_SQL_LEN

        oversized = 'SELECT 1' + ' ' * (MAX_SQL_LEN + 1)
        with pytest.raises(ToolError, match='maximum allowed length'):
            assert_executable(oversized)

    def test_unparseable_sql_is_rejected_and_chains_the_cause(self):
        """An unparseable statement fails closed with a generic reason; the parser error is preserved via the chained cause, not the message."""
        with pytest.raises(ToolError, match='could not be parsed') as exc_info:
            assert_executable('SELECT FROM WHERE')

        # The reason is a stable, generic message (does not embed the submitted SQL or parser text).
        assert str(exc_info.value) == 'SQL could not be parsed'
        # The real parser error is preserved, not swallowed.
        assert exc_info.value.__cause__ is not None

    def test_deeply_nested_input_is_rejected(self):
        """Deeply nested input (parser recursion limit) fails closed."""
        sql = '(' * 5000 + 'SELECT 1' + ')' * 5000
        with pytest.raises(ToolError, match='could not be parsed'):
            assert_executable(sql)


class TestReadWriteMode:
    """With enforce_read_only=False the deny-list is skipped but single-statement still holds."""

    @pytest.mark.parametrize(
        'sql',
        [
            'CREATE TABLE t (id int)',
            'VACUUM',
            'TRUNCATE foo',
        ],
    )
    def test_single_statement_is_allowed_in_read_write(self, sql):
        """A single statement passes even when its operation is deny-listed."""
        assert_executable(sql, enforce_read_only=False)

    def test_multi_statement_still_rejected_in_read_write(self):
        """Statement stacking is rejected regardless of mode."""
        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            assert_executable('SELECT 1; SELECT 2', enforce_read_only=False)


class TestReadOnlyPassesWritesToEngineBackstop:
    """Read-only mode allows ordinary writes/DDL past the guard; the engine backstop blocks them (R2.7).

    The deny-list only targets operations the `BEGIN READ ONLY ... ROLLBACK` transaction
    cannot neutralize, so ordinary data writes and DDL pass the guard on purpose and are
    rejected by the read-only transaction at execution time.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            'INSERT INTO t VALUES (1)',  # sqlglot: exp.Insert
            'CREATE TABLE t (id int)',  # sqlglot: exp.Create
            'SELECT 1 INTO t',  # sqlglot: exp.Select (SELECT … INTO)
            f"COPY t FROM 's3://b/p' IAM_ROLE '{_ARN}'",  # sqlglot: exp.Copy
            'LOCK t',  # sqlglot: exp.Alias (parsed as `LOCK AS t`; LOCK is not a denied identifier)
        ],
    )
    def test_non_denied_write_or_ddl_passes_the_guard_in_read_only(self, sql):
        """A non-deny-listed write/DDL is allowed past the guard (the engine enforces read-only)."""
        # Read-only (default): not deny-listed, so allowed past the guard to the engine.
        assert_executable(sql)


class TestReadOnlyPassesWithPrefixedWritesToEngineBackstop:
    """Read-only mode allows a `WITH ... UPDATE/DELETE/INSERT` data-modifying CTE; the engine blocks it (R2.7 + R3).

    A CTE fronting a data write is an ordinary write, not deny-listed, so the guard
    allows it and the `BEGIN READ ONLY` transaction rejects the write at execution time.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            # sqlglot: exp.Update root with the CTE in its subtree (not deny-listed).
            'WITH cte AS (SELECT 1 AS n) UPDATE t SET a = 1 WHERE id IN (SELECT n FROM cte)',
        ],
    )
    def test_with_prefixed_write_passes_the_guard_in_read_only(self, sql):
        """A `WITH (<write>)` data-modifying CTE is allowed past the guard (engine enforces read-only)."""
        # Read-only (default): write node and its CTE are not deny-listed, so allowed past
        # the guard to the engine, where BEGIN READ ONLY rejects the write.
        assert_executable(sql)


class TestMightWriteRecognizesReads:
    """Recognized reads answer False, so they are not confirmed in read-write mode."""

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT 1',
            'SELECT a FROM public.t WHERE a > 1',
            'WITH a AS (SELECT 1) SELECT * FROM a',
            'SELECT a FROM t QUALIFY row_number() OVER (ORDER BY a) = 1',
            '(SELECT 1)',
            # Set operations: Intersect and Except are not Union subclasses, so all
            # three are covered through the shared SetOperation base.
            'SELECT 1 UNION SELECT 2',
            'SELECT 1 UNION ALL SELECT 2',
            'SELECT 1 INTERSECT SELECT 2',
            'SELECT 1 EXCEPT SELECT 2',
        ],
    )
    def test_read_statements_do_not_need_confirmation(self, sql):
        """A plain read is classified as a read."""
        assert might_write(sql) is False

    @pytest.mark.parametrize(
        'sql',
        [
            'SHOW search_path',
            'SHOW DATABASES',
            'SHOW SCHEMAS FROM DATABASE dev',
            'SHOW TABLES FROM SCHEMA dev.public',
            'SHOW COLUMNS FROM TABLE dev.public.t',
            'SHOW GRANTS FOR public.t',
            'SHOW DATASHARES',
        ],
    )
    def test_allow_listed_commands_are_reads(self, sql):
        """Every SHOW form parses as one command name, so the allow-list covers them all."""
        assert might_write(sql) is False

    def test_explain_of_a_read_is_a_read(self):
        """`EXPLAIN` returns a plan without running its payload."""
        assert might_write('EXPLAIN SELECT 1') is False


class TestMightWriteRecognizesWrites:
    """Anything that could change something answers True."""

    @pytest.mark.parametrize(
        'sql',
        [
            'INSERT INTO t VALUES (1)',
            'UPDATE t SET a = 1',
            'DELETE FROM t',
            'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN UPDATE SET a = s.a',
            f"COPY t FROM 's3://b/p' IAM_ROLE '{_ARN}'",
            f"UNLOAD ('select 1') TO 's3://b/p' IAM_ROLE '{_ARN}'",
            'CREATE TABLE t (id int)',
            'CREATE TABLE t AS SELECT 1',
            'CREATE MATERIALIZED VIEW mv AS SELECT 1',
            'REFRESH MATERIALIZED VIEW mv',
            'DROP TABLE t',
            'ALTER TABLE t ADD COLUMN c int',
            'ALTER TABLE t APPEND FROM s',
            'TRUNCATE t',
            'VACUUM',
            'ANALYZE t',
            'GRANT SELECT ON t TO u',
            'REVOKE SELECT ON t FROM u',
            "COMMENT ON TABLE t IS 'x'",
            'CALL p()',
            'EXECUTE p',
            'LOCK t',
            'BEGIN',
            'COMMIT',
            'ROLLBACK',
        ],
    )
    def test_write_statements_need_confirmation(self, sql):
        """A statement that changes data, schema, permissions, or transaction state writes."""
        assert might_write(sql) is True

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT 1 INTO t',
            'SELECT * INTO TEMP tmp FROM t',
            'SELECT * INTO TEMPORARY tmp FROM t',
            'SELECT * INTO TABLE t FROM s',
            'WITH a AS (SELECT 1 AS n) SELECT n INTO t FROM a',
        ],
    )
    def test_select_into_is_a_write_despite_the_select_root(self, sql):
        """`SELECT ... INTO` creates a table, so the Select root must not make it a read."""
        assert might_write(sql) is True

    @pytest.mark.parametrize(
        'sql',
        [
            "SELECT set_config('transaction_read_only', 'off', false)",
            "SELECT pg_catalog.set_config('transaction_read_only', 'off', false)",
            "SELECT SET_CONFIG('a', 'b', false) AS applied",
            "WITH c AS (SELECT set_config('a', 'b', false) AS v) SELECT * FROM c",
            "SELECT set_config('a', 'b', false) FROM t UNION SELECT 1",
        ],
    )
    def test_the_function_form_of_set_is_a_write(self, sql):
        """`set_config` reaches the same session settings as the SET statement.

        Measured on a cluster: after it clears `transaction_read_only`, a CREATE TABLE inside
        the read-only transaction succeeds and a commit persists it. On the fallback this
        answer is the only gate the statement meets.
        """
        assert might_write(sql) is True

    def test_set_config_as_a_string_literal_is_still_a_read(self):
        """Matching is structural, so the name in quotes is data rather than a call."""
        assert might_write("SELECT 'set_config' AS name") is False

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT a INTO t FROM x UNION SELECT b FROM y',
            'SELECT a INTO t FROM x UNION ALL SELECT b FROM y',
            'SELECT a INTO t FROM x INTERSECT SELECT b FROM y',
            'SELECT a INTO t FROM x EXCEPT SELECT b FROM y',
            '(SELECT * INTO t FROM x)',
            '((SELECT * INTO t FROM x))',
            'WITH c AS (SELECT 1 AS n) SELECT n INTO t FROM c UNION SELECT 2',
        ],
    )
    def test_select_into_behind_a_set_operation_is_still_a_write(self, sql):
        """Redshift's grammar allows these, and each one creates the table.

        The INTO then hangs off a child Select rather than the root, so a root-only check reads
        the Union, Intersect, Except or Subquery root as a plain read. On the fallback, which
        has no read-only transaction around it, that answer is the only thing standing between
        the statement and the cluster.
        """
        assert might_write(sql) is True

    def test_data_modifying_cte_under_a_select_is_a_write(self):
        """A write hidden in a CTE is caught by the subtree walk, not the root check."""
        assert might_write('WITH a AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM a')

    @pytest.mark.parametrize(
        'sql',
        [
            'SET search_path TO public',
            'RESET search_path',
            'DECLARE c CURSOR FOR SELECT 1',
            'FETCH 10 FROM c',
            'PREPARE p AS SELECT 1',
        ],
    )
    def test_unlisted_session_statements_are_treated_as_writes(self, sql):
        """Session and cursor statements are not allow-listed, so they fail towards writing."""
        assert might_write(sql) is True


class TestMightWriteFailsTowardsWriting:
    """Input the classifier cannot judge is treated as a write."""

    def test_multi_statement_might_write(self):
        """Stacked statements are not a recognized read."""
        assert might_write('SELECT 1; DROP TABLE t') is True

    def test_oversized_sql_might_write_without_parsing(self):
        """Oversized input short-circuits to True; `assert_executable` rejects it later."""
        assert might_write('SELECT ' + '1' * (MAX_SQL_LEN + 1)) is True

    def test_unparseable_sql_is_rejected(self):
        """A parse failure fails closed, as it does in the guard."""
        with pytest.raises(ToolError, match='could not be parsed'):
            might_write('SELECT FROM WHERE ;;')

    def test_comment_only_input_might_write(self):
        """Input with no statement is not a recognized read."""
        assert might_write('/* just a comment */') is True
