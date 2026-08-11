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
from awslabs.redshift_mcp_server.sql_guard import assert_executable


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
        with pytest.raises(Exception):
            assert_executable(sql)

    def test_nested_comment_prefix_then_select_cannot_smuggle_a_denied_op(self):
        """A benign SELECT after the comment prefix is allowed; the same prefix before a denied statement is rejected."""
        # Accepted: parses to a single benign SELECT.
        assert_executable('/* a /* b */ SELECT 1 FROM */ SELECT 99 AS pwned')

        # The same prefix before a denied statement is rejected, so it cannot smuggle.
        with pytest.raises(Exception):
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
        with pytest.raises(Exception):
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
        with pytest.raises(Exception):
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
        with pytest.raises(Exception):
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
            'CANCEL 12345',
            'CALL my_proc()',
            "UNLOAD ('SELECT 1') TO 's3://bucket/prefix'",
            f"UNLOAD ('SELECT 1') TO 's3://bucket/prefix' IAM_ROLE '{_ARN}'",
        ],
    )
    def test_egress_dcl_maintenance_and_call_are_rejected(self, sql):
        """Egress, DCL, maintenance, comment, cancel, and CALL statements are rejected."""
        with pytest.raises(Exception):
            assert_executable(sql)

    @pytest.mark.parametrize(
        'sql',
        [
            ';COMMIT',
        ],
    )
    def test_leading_semicolon_before_deny_keyword_is_rejected(self, sql):
        """Leading semicolons cannot smuggle a deny-listed keyword past the guard."""
        with pytest.raises(Exception):
            assert_executable(sql)

    def test_truncate_rejection_reason_is_pinned(self):
        """A denied TRUNCATE surfaces the `Statement type not allowed` reason."""
        with pytest.raises(Exception, match='Statement type not allowed'):
            assert_executable('TRUNCATE foo')


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
        with pytest.raises(Exception, match='single SQL statement is allowed'):
            assert_executable(sql)


class TestSessionSettings:
    """Session-setting statements are allowed (rendered inert by single-statement + BEGIN READ ONLY)."""

    @pytest.mark.parametrize(
        'sql',
        [
            'SET search_path TO public',
            "SET SESSION query_group = 'x'",
            'RESET search_path',
        ],
    )
    def test_session_settings_are_allowed(self, sql):
        """`SET`/`RESET` session settings pass the guard."""
        assert_executable(sql)


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

    def test_dollar_quoted_body_with_semicolons_is_a_single_statement(self):
        """A `$$…$$` body containing `;` is one statement (not split), and allowed."""
        assert_executable('SELECT $$ a ; COMMIT ; b $$ AS payload')


class TestFailClosed:
    """The guard denies when it cannot confidently classify the input."""

    def test_oversized_sql_is_rejected(self):
        """SQL longer than MAX_SQL_LEN is rejected without further parsing."""
        from awslabs.redshift_mcp_server.consts import MAX_SQL_LEN

        oversized = 'SELECT 1' + ' ' * (MAX_SQL_LEN + 1)
        with pytest.raises(Exception, match='maximum allowed length'):
            assert_executable(oversized)

    def test_unparseable_sql_is_rejected_and_chains_the_cause(self):
        """An unparseable statement fails closed with a generic reason; the parser error is preserved via the chained cause, not the message."""
        with pytest.raises(Exception, match='could not be parsed') as exc_info:
            assert_executable('SELECT FROM WHERE')

        # The reason is a stable, generic message (does not embed the submitted SQL or parser text).
        assert str(exc_info.value) == 'SQL could not be parsed'
        # The real parser error is preserved, not swallowed.
        assert exc_info.value.__cause__ is not None

    def test_deeply_nested_input_is_rejected(self):
        """Deeply nested input (parser recursion limit) fails closed."""
        sql = '(' * 5000 + 'SELECT 1' + ')' * 5000
        with pytest.raises(Exception, match='could not be parsed'):
            assert_executable(sql)


class TestReadWriteMode:
    """With allow_read_write=True the deny-list is skipped but single-statement still holds."""

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
        assert_executable(sql, allow_read_write=True)

    def test_multi_statement_still_rejected_in_read_write(self):
        """Statement stacking is rejected regardless of mode."""
        with pytest.raises(Exception, match='single SQL statement is allowed'):
            assert_executable('SELECT 1; SELECT 2', allow_read_write=True)


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
