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
            "CALL SYSPROC.ADMIN_CMD('REORG TABLE T')",
            'SELECT 1; DROP TABLE T',
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
