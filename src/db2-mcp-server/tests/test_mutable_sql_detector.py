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

"""Tests for the Db2 SQL mutation/injection detector."""

import pytest
from awslabs.db2_mcp_server.mutable_sql_detector import (
    _strip_sql_comments,
    check_sql_injection_risk,
    detect_mutating_keywords,
    detect_transaction_bypass_attempt,
)


class TestDetectMutatingKeywords:
    """Tests for detect_mutating_keywords."""

    @pytest.mark.parametrize(
        'sql,expected',
        [
            ('SELECT * FROM EMPLOYEE', []),
            ('INSERT INTO T VALUES (1)', ['INSERT']),
            ('update t set c = 1', ['UPDATE', 'SET']),
            ('DELETE FROM T', ['DELETE']),
            ('DROP TABLE T', ['DROP']),
            ("CALL SYSPROC.ADMIN_CMD('REORG TABLE T')", ['CALL']),
            ("COMMENT ON TABLE T IS 'x'", ['COMMENT ON']),
        ],
    )
    def test_keywords(self, sql, expected):
        """Mutating keywords are detected; SELECT is clean."""
        assert sorted(detect_mutating_keywords(sql)) == sorted(expected)

    @pytest.mark.parametrize(
        'sql,expected_keyword',
        [
            ('INSERT INTO T VALUES (1)', 'INSERT'),
            ('UPDATE T SET C = 1', 'UPDATE'),
            ('DELETE FROM T', 'DELETE'),
            ('MERGE INTO T USING S ON T.ID = S.ID', 'MERGE'),
            ('TRUNCATE TABLE T', 'TRUNCATE'),
            ('CREATE TABLE T (C INT)', 'CREATE'),
            ('DROP TABLE T', 'DROP'),
            ('ALTER TABLE T ADD COLUMN C INT', 'ALTER'),
            ('RENAME TABLE T TO T2', 'RENAME'),
            ('GRANT SELECT ON T TO USER x', 'GRANT'),
            ('REVOKE SELECT ON T FROM USER x', 'REVOKE'),
            # Multi-word keyword: not detected via its individual words, so it needs
            # its own coverage -- if the multi-word pattern regresses, this is the
            # only test that would catch a mutating statement slipping through.
            ('TRANSFER OWNERSHIP OF TABLE T TO USER x', 'TRANSFER OWNERSHIP'),
            ("COMMENT ON TABLE T IS 'x'", 'COMMENT ON'),
            # Multi-word keyword, same rationale as TRANSFER OWNERSHIP above.
            ('LOCK TABLE T IN EXCLUSIVE MODE', 'LOCK TABLE'),
            ("CALL SYSPROC.ADMIN_CMD('REORG TABLE T')", 'CALL'),
            ('BEGIN\n  DECLARE X INT;\nEND', 'BEGIN'),
            ('DECLARE X INT DEFAULT 0', 'DECLARE'),
            ('SET CURRENT SCHEMA = MYSCHEMA', 'SET'),
            ('SET INTEGRITY FOR T IMMEDIATE CHECKED', 'SET INTEGRITY'),
            ('REORG TABLE T', 'REORG'),
            ('RUNSTATS ON TABLE T', 'RUNSTATS'),
            ('IMPORT FROM file.del OF DEL INSERT INTO T', 'IMPORT'),
            ('LOAD FROM file.del OF DEL INSERT INTO T', 'LOAD'),
            ('EXPORT TO file.del OF DEL SELECT * FROM T', 'EXPORT'),
            ('FLUSH PACKAGE CACHE DYNAMIC', 'FLUSH'),
            ('REFRESH TABLE MV1', 'REFRESH'),
        ],
    )
    def test_every_mutating_keyword_is_detected(self, sql, expected_keyword):
        """Every entry in MUTATING_KEYWORDS has at least one exercised detection case.

        detect_mutating_keywords is the sole gate for read-only enforcement, so an
        untested entry (especially a multi-word literal like LOCK TABLE or TRANSFER
        OWNERSHIP, whose individual words are not standalone keywords) could regress
        silently and let a mutating statement through with no failing test.
        """
        assert expected_keyword in detect_mutating_keywords(sql)

    def test_all_keywords_have_coverage(self):
        """Guard against a new keyword being added without a matching test case."""
        from awslabs.db2_mcp_server.mutable_sql_detector import MUTATING_KEYWORDS

        exercised = {
            'INSERT',
            'UPDATE',
            'SET',
            'DELETE',
            'DROP',
            'CALL',
            'COMMENT ON',
            'MERGE',
            'TRUNCATE',
            'CREATE',
            'ALTER',
            'RENAME',
            'GRANT',
            'REVOKE',
            'TRANSFER OWNERSHIP',
            'LOCK TABLE',
            'BEGIN',
            'DECLARE',
            'SET INTEGRITY',
            'REORG',
            'RUNSTATS',
            'IMPORT',
            'LOAD',
            'EXPORT',
            'FLUSH',
            'REFRESH',
        }
        missing = MUTATING_KEYWORDS - exercised
        assert not missing, f'MUTATING_KEYWORDS added without test coverage: {missing}'

    def test_keyword_in_string_literal_is_ignored(self):
        """A keyword inside a string literal must not trigger detection."""
        assert detect_mutating_keywords("SELECT 'DELETE me' FROM SYSIBM.SYSDUMMY1") == []

    def test_keyword_in_comment_is_ignored(self):
        """A keyword inside a comment must not trigger detection."""
        assert detect_mutating_keywords('SELECT 1 FROM SYSIBM.SYSDUMMY1 -- DROP TABLE T') == []


class TestInjectionRisk:
    """Tests for check_sql_injection_risk."""

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT * FROM T WHERE x = 1 OR 1=1',
            "SELECT * FROM T WHERE name = '' OR '1'='1'",
            'SELECT * FROM A UNION SELECT * FROM B',
            # Newline between UNION and SELECT must still be flagged (re.DOTALL):
            # without it an injected newline bypasses the guard.
            'SELECT * FROM A UNION\nSELECT * FROM B',
            'SELECT 1 UNION\n   SELECT pwd FROM SYSCAT.DBAUTH',
            "CALL SYSPROC.ADMIN_CMD('REORG TABLE T')",
            'SELECT 1; DROP TABLE T',
            # Previously untested SUSPICIOUS_PATTERNS entries -- each is a distinct
            # regex in the list, so a regression in any one wouldn't be caught by
            # the cases above.
            'SELECT * FROM T WHERE SLEEP(5) = 0',
            "EXECUTE IMMEDIATE 'SELECT 1 FROM SYSIBM.SYSDUMMY1'",
            "CALL DBMS_PIPE.RECEIVE_MESSAGE('x', 1)",
            'CALL SYSPROC.ADMIN_CMD_FAKE()',
            'CALL SYSPROC.SYSINSTALLOBJECTS(?, ?, ?, ?)',
        ],
    )
    def test_suspicious(self, sql):
        """Known-risky patterns are flagged."""
        assert check_sql_injection_risk(sql) != []

    def test_clean_query(self):
        """A normal parameterized query has no issues."""
        assert (
            check_sql_injection_risk('SELECT COLNAME FROM SYSCAT.COLUMNS WHERE TABNAME = ?') == []
        )

    def test_readonly_blocks_auth_catalog(self):
        """Read-only mode blocks authorization catalog views."""
        sql = 'SELECT * FROM SYSCAT.DBAUTH'
        assert check_sql_injection_risk(sql, readonly=False) == []
        assert check_sql_injection_risk(sql, readonly=True) != []

    @pytest.mark.parametrize(
        'sql',
        [
            # Enumeration gaps: the previous regex named 4 views, and these carry the
            # same grant data under names it never listed.
            'SELECT * FROM SYSCAT.SCHEMAAUTH',
            'SELECT * FROM SYSCAT.ROLEAUTH',
            'SELECT * FROM SYSCAT.COLAUTH',
            'SELECT * FROM SYSCAT.PACKAGEAUTH',
            'SELECT * FROM SYSCAT.INDEXAUTH',
            'SELECT * FROM SYSCAT.TBSPACEAUTH',
            'SELECT * FROM SYSIBM.SYSDBAUTH',
            # Quoting/spacing forms. NOTE: that Db2 resolves these to the same object is
            # inferred from ordinary identifier rules, not measured against an engine --
            # tolerating them is free and fail-closed, so it is done regardless.
            'SELECT * FROM SYSCAT."DBAUTH"',
            'SELECT * FROM "SYSCAT".DBAUTH',
            'SELECT * FROM SYSCAT . DBAUTH',
            # Federated options can expose remote credentials.
            'SELECT * FROM SYSCAT.USEROPTIONS',
            'SELECT * FROM SYSCAT.SERVEROPTIONS',
            # Grant-bearing admin view with no 'AUTH' in the name.
            'SELECT * FROM SYSIBMADM.PRIVILEGES',
        ],
    )
    def test_readonly_blocks_auth_catalog_variants(self, sql):
        """The block is by object-name shape, so it is not escaped by quoting or spacing."""
        assert check_sql_injection_risk(sql, readonly=True) != []

    @pytest.mark.parametrize(
        'sql',
        [
            'SELECT * FROM APP.AUTHORS',  # user table whose name contains AUTH
            'SELECT AUTHOR FROM APP.BOOKS',  # column whose name contains AUTH
            'SELECT * FROM SYSCAT.TABLES',
            'SELECT COLNAME FROM SYSCAT.COLUMNS WHERE TABNAME = ?',
            'SELECT 1 FROM SYSIBM.SYSDUMMY1',
        ],
    )
    def test_readonly_auth_catalog_false_positive_boundary(self, sql):
        r"""`\w*auth\w*` is deliberately broad, so pin what it must NOT catch.

        The pattern is anchored to the system qualifiers (syscat/sysibm/sysibmadm), so a
        user object merely containing "AUTH" stays allowed. Without this, widening the
        pattern could silently start rejecting ordinary read-only queries.
        """
        assert check_sql_injection_risk(sql, readonly=True) == []

    def test_auth_catalog_block_is_readonly_only(self):
        """None of the auth-catalog forms are blocked in write mode.

        The block is a read-only confidentiality measure, not part of the write-
        prevention guarantee, so widening it must not leak into write mode.
        """
        for sql in [
            'SELECT * FROM SYSCAT.SCHEMAAUTH',
            'SELECT * FROM SYSCAT."DBAUTH"',
            'SELECT * FROM SYSIBMADM.PRIVILEGES',
        ]:
            assert check_sql_injection_risk(sql, readonly=False) == []


class TestTransactionBypass:
    """Tests for detect_transaction_bypass_attempt."""

    def test_commit_detected(self):
        """COMMIT is detected as a transaction-control bypass."""
        assert 'COMMIT' in detect_transaction_bypass_attempt('SELECT 1; COMMIT')

    def test_release_savepoint(self):
        """RELEASE SAVEPOINT collapses to RELEASE."""
        assert detect_transaction_bypass_attempt('RELEASE SAVEPOINT s1') == ['RELEASE']

    def test_clean(self):
        """A plain SELECT has no transaction control."""
        assert detect_transaction_bypass_attempt('SELECT 1 FROM SYSIBM.SYSDUMMY1') == []


class TestStripComments:
    """Tests for _strip_sql_comments."""

    def test_line_comment(self):
        """Line comments are stripped."""
        assert 'DROP' not in _strip_sql_comments('SELECT 1 -- DROP')

    def test_block_comment(self):
        """Block comments are stripped."""
        assert 'DROP' not in _strip_sql_comments('SELECT 1 /* DROP */ FROM T')

    def test_string_literal_emptied(self):
        """String-literal contents are emptied."""
        assert 'secret' not in _strip_sql_comments("SELECT 'secret'")

    def test_quoted_identifier_preserved(self):
        """Double-quoted identifiers are preserved (and still keyword-scanned)."""
        assert detect_mutating_keywords('SELECT * FROM "DELETE"') == ['DELETE']

    def test_escaped_quote_in_identifier(self):
        """An escaped double-quote inside an identifier is handled."""
        stripped = _strip_sql_comments('SELECT "a""b" FROM T')
        assert '"a""b"' in stripped

    def test_block_comment_multiline(self):
        """A multi-line block comment is stripped."""
        assert 'DROP' not in _strip_sql_comments('SELECT /* a\nDROP\nb */ 1 FROM T')

    def test_savepoint_bypass(self):
        """SAVEPOINT is detected as a transaction-control bypass."""
        assert 'SAVEPOINT' in detect_transaction_bypass_attempt('SAVEPOINT s1')


def test_data_change_table_reference_blocked():
    """Db2 data-change-table-references (SELECT ... FROM FINAL TABLE(INSERT ...)) are caught.

    These embed a mutation inside a SELECT; the mutating-keyword detector must still
    flag the INSERT so read-only mode rejects them.
    """
    sql = 'SELECT a FROM FINAL TABLE (INSERT INTO t(a) VALUES (1))'
    assert 'INSERT' in detect_mutating_keywords(sql)

    sql_update = 'SELECT a FROM OLD TABLE (UPDATE t SET a = 2 WHERE a = 1)'
    assert 'UPDATE' in detect_mutating_keywords(sql_update)


# --------------------------------------------------------------------------- #
# Round-9: line terminators other than LF must terminate a `--` comment
# --------------------------------------------------------------------------- #


class TestLineCommentTerminators:
    r"""A `--` comment ends at ANY line terminator, not just LF.

    This is defence in depth, not a regression test for a known hole. It was
    suggested that breaking only on '\n' was an exploitable read-only bypass, but
    measurement showed Db2 treats a bare CR as ordinary comment text -- so the
    previous behaviour already matched the server's. See the note on
    _LINE_TERMINATORS in mutable_sql_detector.py for the evidence.

    These cases pin the intentionally-conservative behaviour: the scanner analyses
    the text after any line terminator, which is strictly fail-closed and guards
    against CR->LF normalisation elsewhere in the path and against untested
    versions/terminators.
    """

    # Every terminator in Python's universal-newline set.
    TERMINATORS = [
        pytest.param('\n', id='LF'),
        pytest.param('\r', id='CR'),
        pytest.param('\r\n', id='CRLF'),
        pytest.param('\x0b', id='VT'),
        pytest.param('\x0c', id='FF'),
        pytest.param('\x1c', id='FS'),
        pytest.param('\x1d', id='GS'),
        pytest.param('\x1e', id='RS'),
        pytest.param('\x85', id='NEL'),
        pytest.param('\u2028', id='LS'),
        pytest.param('\u2029', id='PS'),
    ]

    @pytest.mark.parametrize('term', TERMINATORS)
    def test_drop_after_terminator_is_detected(self, term):
        """`--x<TERM>DROP TABLE t` must still be seen as mutating."""
        assert 'DROP' in detect_mutating_keywords(f'SELECT 1 --x{term}DROP TABLE important')

    @pytest.mark.parametrize('term', TERMINATORS)
    def test_grant_after_terminator_is_detected(self, term):
        """GRANT is not undoable by rollback, so it must never slip past the denylist."""
        sql = f'SELECT 1 --x{term}GRANT DBADM ON DATABASE TO USER attacker'
        assert 'GRANT' in detect_mutating_keywords(sql)

    @pytest.mark.parametrize('term', TERMINATORS)
    def test_admin_cmd_after_terminator_is_flagged(self, term):
        """ADMIN_CMD runs arbitrary admin operations; rollback cannot undo it."""
        sql = f"SELECT 1 --x{term}CALL SYSPROC.ADMIN_CMD('REORG TABLE t')"
        assert detect_mutating_keywords(sql) or check_sql_injection_risk(sql, readonly=True)

    @pytest.mark.parametrize('term', TERMINATORS)
    def test_data_change_table_reference_after_terminator_is_detected(self, term):
        """The data-change-table-reference form must be caught for every terminator."""
        sql = f'SELECT a FROM FINAL TABLE (--z{term}INSERT INTO t(a) VALUES (1))'
        assert 'INSERT' in detect_mutating_keywords(sql)

    @pytest.mark.parametrize('term', TERMINATORS)
    def test_text_after_terminator_survives_stripping(self, term):
        """The post-terminator text must remain in the analyzed string."""
        stripped = _strip_sql_comments(f'SELECT 1 --x{term}DROP TABLE important')
        assert 'DROP TABLE important' in stripped

    def test_genuine_trailing_comment_still_stripped(self):
        """A real trailing comment is still removed (no false positive from the fix)."""
        assert detect_mutating_keywords('SELECT 1 FROM SYSIBM.SYSDUMMY1 -- DROP TABLE T') == []

    def test_comment_at_end_of_input_without_terminator(self):
        """A comment running to end-of-input is still fully stripped."""
        assert detect_mutating_keywords('SELECT 1 -- DROP TABLE T') == []
