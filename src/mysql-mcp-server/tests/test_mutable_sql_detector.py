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

"""Tests for mutable_sql_detector.

These pin two things at once:

1. The reported bypass class
   where SQL inline comments (``/* ... */``, ``-- ...``, ``#``) and MySQL
   conditional comments (``/*!50000 ... */``) sneak forbidden keywords past
   the regex-based detector because Python regex treats those tokens as
   opaque characters while the MySQL parser treats them as whitespace.

2. The benign-comment cases that real users have in real queries, so a
   future change to the detector cannot silently start blocking
   ``SELECT id /* primary key */ FROM users`` and similar.

The test cases include the reporter's verbatim payloads so a security
reviewer can match them against the report 1:1.
"""

from awslabs.mysql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)


# ---------------------------------------------------------------------------
# Bypass class: comment-based evasion of the suspicious-pattern gate
# ---------------------------------------------------------------------------


class TestCommentBypassSuspiciousPatterns:
    """Suspicious-pattern detection must survive ``/* */``, ``--``, ``#``."""

    def test_into_outfile_with_block_comment_is_detected(self):
        """Reporter's payload: SELECT * FROM mysql.user INTO/**/OUTFILE '/tmp/x'."""
        sql = "SELECT * FROM mysql.user INTO/**/OUTFILE '/tmp/x'"
        issues = check_sql_injection_risk(sql)
        assert issues, f'Expected detector to flag {sql!r}'
        assert issues[0]['type'] == 'sql'

    def test_into_outfile_with_padded_block_comment_is_detected(self):
        """Variant with whitespace surrounding the comment."""
        sql = "SELECT password FROM users INTO /**/ OUTFILE '/tmp/p'"
        assert check_sql_injection_risk(sql)

    def test_into_dumpfile_with_block_comment_is_detected(self):
        """DUMPFILE is the binary-write sibling of OUTFILE; same bypass shape."""
        sql = "SELECT 1 INTO/**/DUMPFILE '/tmp/x'"
        assert check_sql_injection_risk(sql)

    def test_into_outfile_with_line_comment_is_detected(self):
        """Line comment between INTO and OUTFILE; sqlparse normalises it."""
        sql = "SELECT password FROM users INTO -- pivot\nOUTFILE '/tmp/p'"
        assert check_sql_injection_risk(sql)

    def test_into_outfile_with_hash_comment_is_detected(self):
        """MySQL-specific ``#`` line comment; sqlparse strips it."""
        sql = "SELECT password FROM users INTO # pivot\nOUTFILE '/tmp/p'"
        assert check_sql_injection_risk(sql)

    def test_load_file_function_call_still_detected(self):
        """``load_file(...)`` is a single identifier; comment trick doesn't apply.

        Included because the reporter explicitly notes this pattern was not
        bypassable. We assert the existing behaviour didn't regress.
        """
        sql = "SELECT load_file('/etc/passwd')"
        assert check_sql_injection_risk(sql)


class TestMySQLConditionalCommentBypass:
    """``/*!`` conditional comments execute on the server and must be rejected."""

    def test_conditional_comment_with_into_outfile_is_rejected(self):
        """``/*!50000 INTO OUTFILE ... */`` runs on MySQL 5.0+; reject pre-strip."""
        sql = "SELECT 1 /*!50000 INTO OUTFILE '/tmp/x' */"
        assert check_sql_injection_risk(sql)

    def test_conditional_comment_with_insert_is_rejected(self):
        """A conditional comment containing INSERT must be rejected."""
        sql = 'SELECT 1 /*! INSERT INTO log VALUES (1) */'
        assert check_sql_injection_risk(sql)

    def test_conditional_comment_without_inner_payload_is_rejected(self):
        """Even a no-op ``/*!*/`` is rejected; no benign caller emits one."""
        sql = 'SELECT 1 /*!*/'
        assert check_sql_injection_risk(sql)


class TestMySQLConditionalCommentInMutationGate:
    """``detect_mutating_keywords`` must catch ``/*!`` independently.

    sqlparse strips conditional-comment bodies before the regex runs, so
    without an explicit guard a payload like ``/*!50000 DELETE FROM users */``
    would normalise to whitespace and ``MUTATING_PATTERN`` would find
    nothing. The readonly gate would then let the query through to
    ``check_sql_injection_risk``, which catches it — but only because the
    two functions are coupled through the server's call order. This class
    pins the behaviour that the function is correct in isolation, regardless
    of who calls it next.
    """

    def test_conditional_comment_with_delete_is_reported_as_mutation(self):
        """``/*!50000 DELETE */`` returns a non-empty list."""
        sql = '/*!50000 DELETE FROM users */'
        matches = detect_mutating_keywords(sql)
        assert matches, f'Expected non-empty list, got {matches!r}'

    def test_conditional_comment_with_drop_is_reported_as_mutation(self):
        """``/*!50000 DROP */`` returns a non-empty list."""
        sql = 'SELECT 1 /*!50000 DROP TABLE users */'
        matches = detect_mutating_keywords(sql)
        assert matches

    def test_conditional_comment_marker_alone_is_reported_as_mutation(self):
        """Bare ``/*!`` marker is sufficient to be reported."""
        sql = 'SELECT 1 /*!*/'
        matches = detect_mutating_keywords(sql)
        assert matches

    def test_mutation_sentinel_is_used_for_conditional_comments(self):
        """The sentinel is a recognisable non-keyword for log clarity."""
        matches = detect_mutating_keywords('/*!50000 DELETE FROM users */')
        assert matches == ['MYSQL_CONDITIONAL_COMMENT']

    def test_real_mutation_with_conditional_comment_still_flagged(self):
        """A query with both a conditional comment and a real mutation is flagged.

        Whether the guard or the keyword scan reports first, callers see a
        non-empty list. The guard takes precedence in the current
        implementation; this test pins that callers' ``bool(matches)``
        check fires either way.
        """
        sql = 'INSERT INTO logs VALUES (1) /*! ignored */'
        matches = detect_mutating_keywords(sql)
        assert matches


# ---------------------------------------------------------------------------
# Bypass class: comment-based evasion of the readonly mutation gate
# ---------------------------------------------------------------------------


class TestCommentBypassMutatingKeywords:
    """Multi-word mutating keywords must be detected even with ``/**/`` between words."""

    def test_load_data_with_block_comment_is_detected(self):
        """Reporter's payload: LOAD/**/DATA INFILE '/etc/passwd' INTO TABLE t."""
        sql = "LOAD/**/DATA INFILE '/etc/passwd' INTO TABLE t"
        matches = detect_mutating_keywords(sql)
        assert 'LOAD DATA' in matches, f'Got {matches!r}'

    def test_load_xml_with_block_comment_is_detected(self):
        """LOAD XML is a sibling form of LOAD DATA and must also be caught."""
        sql = "LOAD/**/XML INFILE '/etc/passwd' INTO TABLE t"
        assert 'LOAD XML' in detect_mutating_keywords(sql)

    def test_replace_into_with_block_comment_is_detected(self):
        """REPLACE INTO is a mutation; the comment between words must not hide it."""
        sql = "REPLACE/**/INTO users (id, name) VALUES (1, 'x')"
        assert 'REPLACE INTO' in detect_mutating_keywords(sql)

    def test_rename_table_with_block_comment_is_detected(self):
        """RENAME TABLE is a mutation; the comment between words must not hide it."""
        sql = 'RENAME/**/TABLE old_users TO users'
        assert 'RENAME TABLE' in detect_mutating_keywords(sql)

    def test_create_function_with_block_comment_is_detected(self):
        """CREATE FUNCTION is a mutation; the comment between words must not hide it."""
        sql = 'CREATE/**/FUNCTION foo() RETURNS INT RETURN 1'
        assert 'CREATE FUNCTION' in detect_mutating_keywords(sql)


# ---------------------------------------------------------------------------
# Baselines: payloads the original detector already caught must still pass
# ---------------------------------------------------------------------------


class TestBaselineDetections:
    """Payloads the previous detector already caught must remain caught."""

    def test_plain_into_outfile_is_detected(self):
        """Bare INTO OUTFILE without comments was already caught and still is."""
        sql = "SELECT * FROM mysql.user INTO OUTFILE '/tmp/x'"
        assert check_sql_injection_risk(sql)

    def test_plain_into_dumpfile_is_detected(self):
        """Bare INTO DUMPFILE without comments was already caught and still is."""
        sql = "SELECT 1 INTO DUMPFILE '/tmp/x'"
        assert check_sql_injection_risk(sql)

    def test_plain_load_data_infile_is_detected_in_readonly(self):
        """Bare LOAD DATA INFILE is reported as a mutation in readonly mode."""
        sql = "LOAD DATA INFILE '/etc/passwd' INTO TABLE t"
        assert 'LOAD DATA' in detect_mutating_keywords(sql)

    def test_union_select_is_detected(self):
        """UNION SELECT is the canonical SQLi pivot and must remain blocked."""
        sql = 'SELECT 1 UNION SELECT password FROM users'
        assert check_sql_injection_risk(sql)

    def test_drop_table_is_detected(self):
        """DROP must remain blocked even outside readonly mode."""
        sql = 'DROP TABLE users'
        assert check_sql_injection_risk(sql)

    def test_stacked_queries_are_detected(self):
        """A semicolon-separated stacked query must be flagged."""
        sql = 'SELECT 1; DROP TABLE users'
        assert check_sql_injection_risk(sql)

    def test_numeric_tautology_is_detected(self):
        """OR 1=1 must remain blocked."""
        sql = 'SELECT * FROM users WHERE id = 1 OR 1=1'
        assert check_sql_injection_risk(sql)

    def test_string_tautology_is_detected(self):
        """OR '1'='1' must remain blocked."""
        sql = "SELECT * FROM users WHERE name = '' OR 'x'='x'"
        assert check_sql_injection_risk(sql)

    def test_sleep_probe_is_detected(self):
        """sleep() time-based SQLi probe must remain blocked."""
        sql = 'SELECT * FROM users WHERE id = 1 AND sleep(5)'
        assert check_sql_injection_risk(sql)

    def test_benchmark_probe_is_detected(self):
        """benchmark() time-based SQLi probe must remain blocked."""
        sql = 'SELECT 1 FROM dual WHERE benchmark(1000000, MD5(1))'
        assert check_sql_injection_risk(sql)


class TestBaselineMutatingDetection:
    """Mutating keyword detection on plain queries (no comments)."""

    def test_insert_is_detected(self):
        """Plain INSERT is reported as INSERT."""
        assert 'INSERT' in detect_mutating_keywords("INSERT INTO users VALUES (1, 'x')")

    def test_update_is_detected(self):
        """Plain UPDATE is reported as UPDATE."""
        assert 'UPDATE' in detect_mutating_keywords("UPDATE users SET name = 'x'")

    def test_delete_is_detected(self):
        """Plain DELETE is reported as DELETE."""
        assert 'DELETE' in detect_mutating_keywords('DELETE FROM users WHERE id = 1')

    def test_select_is_not_mutating(self):
        """SELECT must not be reported as a mutation."""
        assert detect_mutating_keywords('SELECT id FROM users') == []


class TestMultiWordKeywordsPreferredOverPrefixes:
    """Multi-word keywords must win over their single-word prefixes.

    ``MUTATING_KEYWORDS`` is a Python set; without explicit length-sorting,
    the alternation order is hash-seed dependent and ``RENAME`` can match
    before ``RENAME TABLE`` is even tried. These tests pin the longer
    phrase as the reported match so multi-word entries are not vestigial.

    The readonly gate fires on either spelling (both ``RENAME`` and
    ``RENAME TABLE`` are in the mutating set), so this is a labelling /
    determinism fix, not a security fix.
    """

    def test_rename_table_wins_over_rename(self):
        """RENAME TABLE must be reported in full, not as bare RENAME."""
        assert 'RENAME TABLE' in detect_mutating_keywords('RENAME TABLE a TO b')

    def test_create_function_wins_over_create(self):
        """CREATE FUNCTION must be reported in full, not as bare CREATE."""
        assert 'CREATE FUNCTION' in detect_mutating_keywords(
            'CREATE FUNCTION foo() RETURNS INT RETURN 1'
        )

    def test_create_procedure_wins_over_create(self):
        """CREATE PROCEDURE must be reported in full, not as bare CREATE."""
        assert 'CREATE PROCEDURE' in detect_mutating_keywords('CREATE PROCEDURE bar() BEGIN END')

    def test_load_data_wins_over_load_alone(self):
        """LOAD DATA must be reported in full; bare LOAD isn't in the set."""
        assert 'LOAD DATA' in detect_mutating_keywords(
            "LOAD DATA INFILE '/etc/passwd' INTO TABLE t"
        )

    def test_replace_into_wins_over_replace(self):
        """REPLACE INTO must be reported in full, not as bare REPLACE."""
        assert 'REPLACE INTO' in detect_mutating_keywords(
            "REPLACE INTO users (id, name) VALUES (1, 'x')"
        )


# ---------------------------------------------------------------------------
# False-positive guards: benign queries with comments must continue to pass
# ---------------------------------------------------------------------------


class TestBenignCommentsPass:
    """Comments that genuinely appear in real queries must not be blocked.

    These pin the design choice that the regex sweep runs against the
    comment-stripped SQL only (not the raw SQL as a fallback). A future
    change that re-introduces the raw-SQL fallback would fail these.
    """

    def test_select_with_block_comment_passes(self):
        """A short ``/* ... */`` annotation between columns is benign."""
        sql = 'SELECT id, /* primary key */ name FROM users'
        assert check_sql_injection_risk(sql) == []

    def test_select_with_line_comment_passes(self):
        """A ``-- ...`` annotation at end-of-line is benign."""
        sql = 'SELECT id FROM users -- get all users\nWHERE active = 1'
        assert check_sql_injection_risk(sql) == []

    def test_select_with_hash_comment_passes(self):
        """A ``#`` annotation at end-of-line is benign in MySQL."""
        sql = 'SELECT id FROM users # get all users\nWHERE active = 1'
        assert check_sql_injection_risk(sql) == []

    def test_multi_line_block_comment_header_passes(self):
        """A leading ``/* ... */`` header is benign."""
        sql = '/* monthly active users */\nSELECT COUNT(*) FROM events'
        assert check_sql_injection_risk(sql) == []

    def test_comment_text_containing_into_outfile_passes(self):
        """Benign query whose comment happens to mention ``INTO OUTFILE``.

        Regression test: V1 of the fix would have flagged this because it
        ran the regex against the raw SQL too. V2 strips first and only
        runs against the stripped form, which is the correct behaviour.
        """
        sql = 'SELECT id FROM users -- export INTO OUTFILE later'
        assert check_sql_injection_risk(sql) == []

    def test_comment_text_containing_load_data_passes(self):
        """Benign query whose comment happens to mention ``LOAD DATA``."""
        sql = 'SELECT id FROM users /* equivalent to LOAD DATA INFILE */'
        assert check_sql_injection_risk(sql) == []

    def test_explanatory_comments_in_cte_pass(self):
        """A multi-line readonly CTE with comments must not be flagged."""
        sql = """
            /* monthly active users */
            WITH active AS (
                SELECT user_id FROM events
                WHERE event_date >= NOW() - INTERVAL 30 DAY
            )
            SELECT COUNT(*) AS mau FROM active
        """
        assert check_sql_injection_risk(sql) == []


class TestCommentDoesNotReassembleIdentifiers:
    """Comments split inside an identifier do NOT yield a keyword.

    ``INS/**/ERT`` is not an INSERT to the database (parsers don't treat
    a comment as zero-width inside an identifier). After sqlparse strip
    you get ``INS  ERT`` which still doesn't match any mutating keyword.
    Pin this so a future "let's also strip inner whitespace" change
    doesn't accidentally flag random identifiers that happen to look
    like split keywords.
    """

    def test_split_insert_identifier_is_not_a_mutation(self):
        """``INS/**/ERT`` must not be reported as INSERT."""
        sql = 'INS/**/ERT INTO users VALUES (1)'
        assert 'INSERT' not in detect_mutating_keywords(sql)

    def test_split_drop_identifier_is_not_flagged_as_drop(self):
        """``DR/**/OP`` must not be reported as DROP.

        Note: this query DOES still get blocked because the database
        would reject it as a syntax error, but our detector specifically
        should not pretend to recognise a DROP.
        """
        sql = 'DR/**/OP TABLE users'
        assert 'DROP' not in detect_mutating_keywords(sql)
