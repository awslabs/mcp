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

1. The reported bypass class where SQL inline comments
   (``/* ... */``, ``-- ...``, ``#``) and MySQL conditional comments
   (``/*!50000 ... */``) sneak forbidden keywords past the regex-based
   detector because Python regex treats those tokens as opaque characters
   while the MySQL parser treats them as whitespace.

2. The benign-comment cases that real users have in real queries, so a
   future change to the detector cannot silently start blocking
   ``SELECT id /* primary key */ FROM users`` and similar.

The test cases include the reporter's verbatim payloads so a security
reviewer can match them against the report 1:1.
"""

import pytest
from awslabs.mysql_mcp_server.mutable_sql_detector import (
    MUTATING_KEYWORDS,
    SECURITY_SENSITIVE_VARS,
    SIDE_EFFECTING_FUNCTIONS,
    STATEMENT_START_MUTATING_KEYWORDS,
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


# ---------------------------------------------------------------------------
# Completeness of MUTATING_KEYWORDS
#
# These pin every entry in the set against a minimal payload so that:
#   1. any future commit that removes a keyword fails CI loudly, and
#   2. the security reviewer can match the test list against the ticket
#      payload list 1:1 without having to read the regex.
# ---------------------------------------------------------------------------


# Mapping of every keyword in MUTATING_KEYWORDS to a minimal payload
# that contains it as a top-level mutation. Listed by hand (not generated
# from the set) so adding a keyword without thinking about the payload
# fails the parametrize collection — that is the regression guard.
_MUTATING_KEYWORD_PAYLOADS: dict[str, str] = {
    # DML
    'INSERT': "INSERT INTO t VALUES (1, 'x')",
    'UPDATE': "UPDATE t SET name = 'x' WHERE id = 1",
    'DELETE': 'DELETE FROM t WHERE id = 1',
    'MERGE': 'MERGE INTO t USING s ON (t.id = s.id) WHEN MATCHED THEN UPDATE SET t.x = s.x',
    'TRUNCATE': 'TRUNCATE TABLE t',
    'REPLACE INTO': "REPLACE INTO t (id, name) VALUES (1, 'x')",
    'LOAD DATA': "LOAD DATA INFILE '/etc/passwd' INTO TABLE t",
    'LOAD XML': "LOAD XML INFILE '/etc/passwd' INTO TABLE t",
    # DDL
    'CREATE': 'CREATE TABLE t (id INT)',
    'DROP': 'DROP TABLE t',
    'ALTER': 'ALTER TABLE t ADD COLUMN x INT',
    'RENAME': 'RENAME USER a TO b',
    'RENAME TABLE': 'RENAME TABLE old_t TO new_t',
    # Permissions
    'GRANT': "GRANT SELECT ON t TO 'u'@'%'",
    'REVOKE': "REVOKE SELECT ON t FROM 'u'@'%'",
    # Extensions and functions
    'CREATE FUNCTION': 'CREATE FUNCTION f() RETURNS INT RETURN 1',
    'CREATE PROCEDURE': 'CREATE PROCEDURE p() BEGIN END',
    'INSTALL': "INSTALL PLUGIN x SONAME 'x.so'",
    'UNINSTALL': 'UNINSTALL PLUGIN x',
    # Storage-level
    'OPTIMIZE': 'OPTIMIZE TABLE t',
    'REPAIR': 'REPAIR TABLE t',
    'ANALYZE': 'ANALYZE TABLE t',
    # Session / server config
    'SET': "SET sql_mode = 'TRADITIONAL'",
    # Stored-program execution
    'CALL': 'CALL p()',
    # Dynamic SQL
    'PREPARE': "PREPARE s FROM 'SELECT 1'",
    'EXECUTE': 'EXECUTE s',
    'DEALLOCATE': 'DEALLOCATE PREPARE s',
    # Direct storage-engine access
    'HANDLER': 'HANDLER t OPEN',
    # Lock and admin state
    'LOCK': 'LOCK INSTANCE FOR BACKUP',
    'LOCK TABLES': 'LOCK TABLES t WRITE',
    'UNLOCK': 'UNLOCK INSTANCE',
    'UNLOCK TABLES': 'UNLOCK TABLES',
    'FLUSH': 'FLUSH PRIVILEGES',
    'RESET': 'RESET MASTER',
    'KILL': 'KILL 1',
}


def test_every_mutating_keyword_has_a_payload():
    """The payload table must cover every entry in MUTATING_KEYWORDS.

    Adding a keyword to MUTATING_KEYWORDS without adding a payload here
    fails this test, forcing the author to think about how the new
    keyword is exercised in a query.
    """
    missing = MUTATING_KEYWORDS - set(_MUTATING_KEYWORD_PAYLOADS.keys())
    assert not missing, f'Missing test payloads for: {sorted(missing)}'


@pytest.mark.parametrize(
    'keyword,payload',
    sorted(_MUTATING_KEYWORD_PAYLOADS.items()),
)
def test_mutating_keyword_is_detected(keyword, payload):
    """Every keyword in MUTATING_KEYWORDS must be detected on its payload.

    Mirrors the Postgres sibling's TestAllMutatingKeywords. Pins the set
    against any future change that silently removes a keyword.
    """
    matches = detect_mutating_keywords(payload)
    assert keyword in matches, (
        f'Expected {keyword!r} in detect_mutating_keywords({payload!r}), got {matches!r}'
    )


# ---------------------------------------------------------------------------
# Ticket payloads — verbatim from the external security report
#
# Each test asserts the exact payload from the security report is
# rejected by the readonly gate. A reviewer can match these 1:1 against
# the report without reading the regex.
# ---------------------------------------------------------------------------


class TestReportedReadonlyBypassPayloads:
    """Verbatim ticket payloads must each be reported as mutations."""

    def test_set_global_general_log_is_detected(self):
        """``SET GLOBAL general_log = 'ON'`` — server-config write."""
        assert 'SET' in detect_mutating_keywords("SET GLOBAL general_log = 'ON'")

    def test_set_sql_log_bin_is_detected_as_mutation(self):
        """``SET sql_log_bin = 0`` — disables binlog for the session.

        Caught by the SET keyword in MUTATING_KEYWORDS in readonly mode.
        Also caught by SECURITY_SENSITIVE_VAR_PATTERN regardless of mode
        — see TestSecuritySensitiveVarsAlwaysBlocked below.
        """
        assert 'SET' in detect_mutating_keywords('SET sql_log_bin = 0')

    def test_call_some_proc_is_detected(self):
        """``CALL some_proc()`` — stored proc body can mutate."""
        assert 'CALL' in detect_mutating_keywords('CALL some_proc()')

    def test_prepare_is_detected(self):
        """``PREPARE s FROM @x`` — dynamic SQL setup."""
        assert 'PREPARE' in detect_mutating_keywords('PREPARE s FROM @x')

    def test_execute_is_detected(self):
        """``EXECUTE s`` — dynamic SQL fire."""
        assert 'EXECUTE' in detect_mutating_keywords('EXECUTE s')

    def test_deallocate_is_detected(self):
        """``DEALLOCATE PREPARE s`` — dynamic SQL teardown."""
        assert 'DEALLOCATE' in detect_mutating_keywords('DEALLOCATE PREPARE s')

    def test_handler_open_is_detected(self):
        """``HANDLER t OPEN`` — direct storage-engine access."""
        assert 'HANDLER' in detect_mutating_keywords('HANDLER t OPEN')

    def test_flush_privileges_is_detected(self):
        """``FLUSH PRIVILEGES`` — admin state change."""
        assert 'FLUSH' in detect_mutating_keywords('FLUSH PRIVILEGES')

    def test_reset_master_is_detected(self):
        """``RESET MASTER`` — admin state change."""
        assert 'RESET' in detect_mutating_keywords('RESET MASTER')

    def test_lock_tables_write_is_detected(self):
        """``LOCK TABLES t WRITE`` — write lock acquisition.

        The longer phrase ``LOCK TABLES`` should win the regex race over
        bare ``LOCK`` because of the length-descending sort. Either is
        sufficient for the gate to fire; we assert the longer phrase
        for log clarity.
        """
        assert 'LOCK TABLES' in detect_mutating_keywords('LOCK TABLES t WRITE')

    def test_kill_is_detected(self):
        """``KILL <id>`` — terminates other sessions."""
        assert 'KILL' in detect_mutating_keywords('KILL 1')

    def test_uninstall_plugin_is_detected(self):
        """``UNINSTALL PLUGIN x`` — plugin lifecycle."""
        assert 'UNINSTALL' in detect_mutating_keywords('UNINSTALL PLUGIN x')


# ---------------------------------------------------------------------------
# SET is blanket-blocked in readonly mode
#
# Pins the design choice that bare SET (without distinguishing user
# vars from system vars) is rejected. This is the cost of the closed-
# by-construction approach — a future change that allowlists SET @var
# or SET NAMES must update these tests deliberately, with a CR linked
# to the security review.
# ---------------------------------------------------------------------------


class TestSetVariantsAreBlocked:
    """All SET forms are rejected in readonly mode by design."""

    def test_set_user_variable_is_blocked(self):
        """``SET @x = 1`` — benign in isolation, blocked by blanket rule."""
        assert 'SET' in detect_mutating_keywords('SET @x = 1')

    def test_set_names_is_blocked(self):
        """``SET NAMES utf8mb4`` — character set, blocked by blanket rule."""
        assert 'SET' in detect_mutating_keywords('SET NAMES utf8mb4')

    def test_set_session_sql_mode_is_blocked(self):
        """``SET SESSION sql_mode = 'TRADITIONAL'`` — session config."""
        assert 'SET' in detect_mutating_keywords("SET SESSION sql_mode = 'TRADITIONAL'")

    def test_set_global_is_blocked(self):
        """``SET GLOBAL general_log = 'ON'`` — server-wide config."""
        assert 'SET' in detect_mutating_keywords("SET GLOBAL general_log = 'ON'")

    def test_set_with_double_at_prefix_is_blocked(self):
        """``SET @@session.sql_mode = '...'`` — at-prefix syntax."""
        assert 'SET' in detect_mutating_keywords("SET @@session.sql_mode = 'TRADITIONAL'")

    def test_set_transaction_is_blocked(self):
        """``SET TRANSACTION READ WRITE`` — would re-arm writes."""
        assert 'SET' in detect_mutating_keywords('SET TRANSACTION READ WRITE')


# ---------------------------------------------------------------------------
# Security-sensitive variables are blocked in BOTH modes
#
# These run against check_sql_injection_risk, not detect_mutating_keywords,
# because the always-block lives there. In readonly mode the SET keyword
# fires first and these payloads are rejected by detect_mutating_keywords;
# in write mode (with --allow_write_query) the keyword path is bypassed
# and only this check stands between the LLM and the variable flip.
# ---------------------------------------------------------------------------


class TestSecuritySensitiveVarsAlwaysBlocked:
    """SET of binlog / FK / uniqueness toggles is rejected in every mode."""

    def test_set_sql_log_bin_zero_is_rejected(self):
        """Reporter's payload: ``SET sql_log_bin = 0``."""
        issues = check_sql_injection_risk('SET sql_log_bin = 0')
        assert issues, 'Expected SET sql_log_bin = 0 to be flagged'
        assert issues[0]['type'] == 'sql'
        assert 'sql_log_bin' in issues[0]['message']

    def test_set_session_sql_log_bin_is_rejected(self):
        """``SET SESSION sql_log_bin = 0`` — explicit session modifier."""
        assert check_sql_injection_risk('SET SESSION sql_log_bin = 0')

    def test_set_global_sql_log_bin_is_rejected(self):
        """``SET GLOBAL sql_log_bin = 0`` — global modifier (rare but valid)."""
        assert check_sql_injection_risk('SET GLOBAL sql_log_bin = 0')

    def test_set_at_at_sql_log_bin_is_rejected(self):
        """``SET @@sql_log_bin = 0`` — at-prefix syntax."""
        assert check_sql_injection_risk('SET @@sql_log_bin = 0')

    def test_set_at_at_session_sql_log_bin_is_rejected(self):
        """``SET @@session.sql_log_bin = 0`` — at-prefix with scope."""
        assert check_sql_injection_risk('SET @@session.sql_log_bin = 0')

    def test_set_at_at_global_sql_log_bin_is_rejected(self):
        """``SET @@global.sql_log_bin = 0`` — at-prefix global."""
        assert check_sql_injection_risk('SET @@global.sql_log_bin = 0')

    def test_set_local_sql_log_bin_is_rejected(self):
        """``SET LOCAL sql_log_bin = 0`` — LOCAL alias for SESSION."""
        assert check_sql_injection_risk('SET LOCAL sql_log_bin = 0')

    def test_set_foreign_key_checks_is_rejected(self):
        """``SET foreign_key_checks = 0`` — FK bypass."""
        issues = check_sql_injection_risk('SET foreign_key_checks = 0')
        assert issues
        assert 'foreign_key_checks' in issues[0]['message']

    def test_set_unique_checks_is_rejected(self):
        """``SET unique_checks = 0`` — uniqueness bypass."""
        issues = check_sql_injection_risk('SET unique_checks = 0')
        assert issues
        assert 'unique_checks' in issues[0]['message']

    def test_lowercase_set_is_rejected(self):
        """Case-insensitive: lowercase ``set`` still fires."""
        assert check_sql_injection_risk('set sql_log_bin = 0')

    def test_security_sensitive_var_check_survives_block_comment(self):
        """``SET /**/ sql_log_bin = 0`` — comment between SET and var.

        sqlparse strips the comment before the regex sweep, so the
        normalised form ``SET  sql_log_bin = 0`` matches the pattern.
        """
        assert check_sql_injection_risk('SET /**/ sql_log_bin = 0')

    def test_prefix_match_does_not_false_positive(self):
        r"""``SET sql_log_bin_extra = 0`` — \b prevents prefix collision.

        There is no real MySQL variable named ``sql_log_bin_extra``,
        but the principle matters: the pattern must require a word
        boundary after the variable name so a longer identifier is
        not flagged as the security-sensitive one.
        """
        # Note: the SET keyword itself still fires in readonly mode via
        # MUTATING_KEYWORDS, so this test specifically asserts that
        # check_sql_injection_risk does NOT flag the security-sensitive
        # message — the readonly path uses detect_mutating_keywords.
        issues = check_sql_injection_risk('SET sql_log_bin_extra = 0')
        for issue in issues:
            assert 'sql_log_bin' not in issue['message'], f'Prefix collision: {issue!r}'


# ---------------------------------------------------------------------------
# Multi-variable SET coverage
#
# MySQL allows comma-separated assignments in a single SET statement:
#   SET @x = 1, sql_log_bin = 0
# The previous pattern anchored on the first assignment slot only, so a
# security-sensitive variable in any later position slipped through in
# write mode. These tests pin the fix: the danger variable is detected
# in any position of a multi-variable SET, with or without scope qualifiers,
# across newlines, and even when earlier assignments contain commas
# inside function call arguments.
# ---------------------------------------------------------------------------


class TestMultiVariableSetCoverage:
    """Security-sensitive vars must be detected in any position of a multi-var SET."""

    def test_danger_var_in_position_two_is_rejected(self):
        """``SET @x = 1, sql_log_bin = 0`` — reviewer's verbatim payload."""
        issues = check_sql_injection_risk('SET @x = 1, sql_log_bin = 0')
        assert issues, 'Multi-var SET with danger var in position 2 must be flagged'
        assert 'sql_log_bin' in issues[0]['message']

    def test_danger_var_in_position_three_is_rejected(self):
        """``SET @x = 1, @y = 2, foreign_key_checks = 0``."""
        issues = check_sql_injection_risk('SET @x = 1, @y = 2, foreign_key_checks = 0')
        assert issues
        assert 'foreign_key_checks' in issues[0]['message']

    def test_danger_var_in_position_four_is_rejected(self):
        """``SET @x = 1, @y = 2, @z = 3, unique_checks = 0``."""
        issues = check_sql_injection_risk('SET @x = 1, @y = 2, @z = 3, unique_checks = 0')
        assert issues
        assert 'unique_checks' in issues[0]['message']

    def test_danger_var_in_position_one_still_works(self):
        """``SET sql_log_bin = 0, @x = 1`` — regression guard.

        The new optional skip group must not break the position-1 case
        that previously already worked correctly.
        """
        assert check_sql_injection_risk('SET sql_log_bin = 0, @x = 1')

    def test_newline_between_assignments_is_handled(self):
        r"""``SET @x = 1,\n sql_log_bin = 0`` — motivates re.DOTALL.

        Without DOTALL, ``.`` does not match ``\n`` and the skip group
        cannot span the newline. With DOTALL the payload is caught.
        """
        assert check_sql_injection_risk('SET @x = 1,\n sql_log_bin = 0')

    def test_scope_qualifier_on_later_var_is_handled(self):
        """``SET @x = 1, @@session.sql_log_bin = 0`` — scope on second var."""
        assert check_sql_injection_risk('SET @x = 1, @@session.sql_log_bin = 0')

    def test_function_call_comma_in_earlier_slot_is_handled(self):
        """``SET @x = CONCAT('a', 'b'), sql_log_bin = 0``.

        A naive comma-split would mis-tokenise the CONCAT call. The
        regex approach handles this because the wildcard skip includes
        the inner comma in its non-greedy span; the engine extends past
        it until the security variable is reached.
        """
        assert check_sql_injection_risk("SET @x = CONCAT('a', 'b'), sql_log_bin = 0")

    def test_long_preceding_assignment_within_bound_is_handled(self):
        """A 100-char REPEAT() expression in slot 1 still leaves slot 2 detectable.

        Pins that the 500-char wildcard bound is comfortable for
        realistic payloads.
        """
        assert check_sql_injection_risk("SET @x = REPEAT('a', 100), sql_log_bin = 0")

    def test_mixed_security_vars_in_one_statement_is_rejected(self):
        """``SET sql_log_bin = 0, foreign_key_checks = 0`` — two danger vars.

        Either match is sufficient to reject; we don't care which one
        the regex reports first, only that the statement is rejected.
        """
        issues = check_sql_injection_risk('SET sql_log_bin = 0, foreign_key_checks = 0')
        assert issues
        # The reported variable is implementation-defined; assert one of them is named.
        assert any(v in issues[0]['message'] for v in ('sql_log_bin', 'foreign_key_checks'))

    def test_uppercase_set_with_multi_var_is_handled(self):
        """Case-insensitive matching survives the multi-var path."""
        assert check_sql_injection_risk('SET @X = 1, SQL_LOG_BIN = 0')


class TestMultiVariableSetFalsePositiveBoundary:
    """Pin the known false-positive limitation as deliberate, not accidental.

    ``UPDATE t SET sql_log_bin = 0`` would match the regex (the parser
    sees ``set sql_log_bin``). This is a deliberate trade-off: closing
    it requires sqlparse tokenisation to distinguish statement-level
    SET from UPDATE's SET clause. Real-world impact is rejecting one
    weird query in write mode, not a security leak.

    These tests document the boundary so a future "fix" that changes
    the behaviour must update the tests deliberately.
    """

    def test_update_with_column_named_like_session_var_is_flagged(self):
        """Documents the false positive: column named ``sql_log_bin``.

        If a future change uses sqlparse to distinguish UPDATE-SET from
        statement-level SET, this test must be updated to assert NO
        match. Right now it asserts the false positive exists so the
        trade-off is visible.
        """
        # No realistic schema names a column after a MySQL session
        # variable; this test exists to make the boundary explicit.
        assert check_sql_injection_risk('UPDATE t SET sql_log_bin = 0 WHERE id = 1')


# ---------------------------------------------------------------------------
# Security-sensitive vars set is well-formed
# ---------------------------------------------------------------------------


def test_security_sensitive_vars_is_non_empty():
    """The set must have at least the three ticket-required entries."""
    assert {'sql_log_bin', 'foreign_key_checks', 'unique_checks'} <= SECURITY_SENSITIVE_VARS


# ---------------------------------------------------------------------------
# Pin the existing stacked-queries protection against transaction-bypass
# payloads.
#
# The initial assessment proposed adding a dedicated
# detect_transaction_bypass_attempt function mirroring the Aurora-DSQL
# sibling. On closer inspection the existing stacked-queries pattern
# in SUSPICIOUS_PATTERNS already rejects every canonical bypass payload
# the security report names, matching the Postgres sibling's design
# choice. Rather than adding a new function with overlapping logic, we
# pin the existing protection here so a future "let's relax stacked
# queries" change has to update these tests deliberately.
#
# Each parametrised case exercises a real attack shape against
# check_sql_injection_risk and asserts a rejection. detect_mutating_keywords
# also fires on most of these because they contain mutating verbs after
# the transaction-control keyword; we deliberately route through
# check_sql_injection_risk to pin the SUSPICIOUS_PATTERNS layer
# independently.
# ---------------------------------------------------------------------------


class TestTransactionBypassCoverage:
    """Stacked-queries pattern must reject transaction-bypass payloads."""

    @pytest.mark.parametrize(
        'payload',
        [
            # Canonical: COMMIT mid-chain re-arms writes in a new transaction.
            'SELECT 1; COMMIT; INSERT INTO t VALUES (1)',
            # ROLLBACK variant — same shape.
            'SELECT 1; ROLLBACK; INSERT INTO t VALUES (1)',
            # SAVEPOINT manipulates nested transaction scope.
            'SELECT 1; SAVEPOINT sp1',
            # RELEASE SAVEPOINT — release of nested scope.
            'SELECT 1; RELEASE SAVEPOINT sp1',
            # START TRANSACTION re-arms a fresh writable transaction.
            'SELECT 1; START TRANSACTION; INSERT INTO t VALUES (1)',
            # BEGIN is a synonym for START TRANSACTION in MySQL.
            'SELECT 1; BEGIN; INSERT INTO t VALUES (1)',
            # Case-insensitive: lowercase variant must still fire.
            'select 1; commit; insert into t values (1)',
            # Comment between SELECT and COMMIT: sqlparse strip leaves the
            # semicolon and the chained statement intact, so the stacked-
            # queries pattern still matches.
            'SELECT 1; /* annotation */ COMMIT; INSERT INTO t VALUES (1)',
            # Whitespace variants: tab and newline as the post-semicolon
            # separator both still leave a non-whitespace next char.
            'SELECT 1;\tCOMMIT;\tINSERT INTO t VALUES (1)',
            'SELECT 1;\nCOMMIT;\nINSERT INTO t VALUES (1)',
        ],
    )
    def test_bypass_payload_is_rejected(self, payload):
        """Every canonical bypass shape must be flagged by the injection check."""
        issues = check_sql_injection_risk(payload)
        assert issues, f'Bypass payload not rejected: {payload!r}'
        assert issues[0]['type'] == 'sql'

    def test_single_statement_with_commit_in_line_comment_is_benign(self):
        """``SELECT 1 -- COMMIT`` is a comment, not a bypass — must pass.

        Negative case: regression guard against an overzealous future
        change that flags transaction-control keywords inside comments.
        """
        assert check_sql_injection_risk('SELECT 1 -- COMMIT') == []

    def test_single_statement_with_commit_in_block_comment_is_benign(self):
        """``SELECT 1 /* COMMIT */`` is a comment, not a bypass — must pass."""
        assert check_sql_injection_risk('SELECT 1 /* COMMIT */') == []


# ---------------------------------------------------------------------------
# Statement-leading mutating keywords
#
# These verbs mutate state (transactions, replication, server lifecycle,
# side-effecting stored functions) but are anchored to statement start in
# the detector because several of them are also common identifiers or
# functions. The tests below pin two things:
#   1. each keyword is detected when it leads a statement, and
#   2. the same word is NOT flagged when it appears as a column name, an
#      alias, or a function call inside a read-only SELECT.
# ---------------------------------------------------------------------------


# Minimal payload for every statement-leading keyword, each a real MySQL
# statement whose leading verb is the keyword under test. Listed by hand so
# adding a keyword without a payload fails the collection below.
_STATEMENT_START_KEYWORD_PAYLOADS: dict[str, str] = {
    # DML / expression execution
    'IMPORT': "IMPORT TABLE FROM 't.sdi'",
    'REPLACE': 'REPLACE t SET id = 1',
    'DO': "DO GET_LOCK('t', 60)",
    # Transaction control
    'START': 'START TRANSACTION',
    'BEGIN': 'BEGIN',
    'COMMIT': 'COMMIT',
    'ROLLBACK': 'ROLLBACK TO SAVEPOINT sp1',
    'SAVEPOINT': 'SAVEPOINT sp1',
    'RELEASE': 'RELEASE SAVEPOINT sp1',
    'XA': "XA START 'xid'",
    # Replication management
    'CHANGE': "CHANGE REPLICATION SOURCE TO SOURCE_HOST = 'h'",
    'PURGE': "PURGE BINARY LOGS TO 'mysql-bin.000001'",
    'STOP': 'STOP REPLICA',
    'BINLOG': "BINLOG 'base64encodedevent'",
    # Server administration
    'CLONE': "CLONE INSTANCE FROM 'user'@'host':3306 IDENTIFIED BY 'pw'",
    'RESTART': 'RESTART',
    'SHUTDOWN': 'SHUTDOWN',
    # Session / server state
    'USE': 'USE mydb',
    'CACHE': 'CACHE INDEX t IN kc',
    'LOAD INDEX': 'LOAD INDEX INTO CACHE t',
}


def test_every_statement_start_keyword_has_a_payload():
    """The payload table must cover every entry in STATEMENT_START_MUTATING_KEYWORDS.

    Adding a keyword to the set without adding a payload here fails this
    test, forcing the author to think about how the new keyword leads a
    real statement.
    """
    missing = STATEMENT_START_MUTATING_KEYWORDS - set(_STATEMENT_START_KEYWORD_PAYLOADS.keys())
    assert not missing, f'Missing test payloads for: {sorted(missing)}'


@pytest.mark.parametrize(
    'keyword,payload',
    sorted(_STATEMENT_START_KEYWORD_PAYLOADS.items()),
)
def test_statement_start_keyword_is_detected(keyword, payload):
    """Every statement-leading keyword must be detected on its payload."""
    matches = detect_mutating_keywords(payload)
    assert keyword in matches, (
        f'Expected {keyword!r} in detect_mutating_keywords({payload!r}), got {matches!r}'
    )


class TestStatementStartMutatingKeywords:
    """Representative payloads for the statement-leading mutating verbs."""

    def test_do_get_lock_is_detected(self):
        """Primary payload: ``DO GET_LOCK('tablename', 60)``.

        ``DO`` returns no result set, so it slips past result-shape checks,
        yet it acquires a server lock that can stall other sessions.
        """
        assert 'DO' in detect_mutating_keywords("DO GET_LOCK('tablename', 60)")

    def test_do_side_effecting_function_is_detected(self):
        """``DO <side_effecting_function>()`` — invokes a writing stored function."""
        assert 'DO' in detect_mutating_keywords('DO my_writing_function()')

    def test_import_table_is_detected(self):
        """``IMPORT TABLE`` — bulk import via .ibd files, creates/populates tables."""
        assert 'IMPORT' in detect_mutating_keywords("IMPORT TABLE FROM 't.sdi'")

    def test_commit_is_detected(self):
        """``COMMIT`` — makes pending mutations durable."""
        assert 'COMMIT' in detect_mutating_keywords('COMMIT')

    def test_start_transaction_is_detected(self):
        """``START TRANSACTION`` — begins a writable transaction."""
        assert 'START' in detect_mutating_keywords('START TRANSACTION')

    def test_start_replica_is_detected(self):
        """``START REPLICA`` — starts replication threads."""
        assert 'START' in detect_mutating_keywords('START REPLICA')

    def test_begin_is_detected(self):
        """``BEGIN`` — alias for START TRANSACTION."""
        assert 'BEGIN' in detect_mutating_keywords('BEGIN')

    def test_rollback_is_detected(self):
        """``ROLLBACK`` — rolls back a transaction."""
        assert 'ROLLBACK' in detect_mutating_keywords('ROLLBACK')

    def test_rollback_to_savepoint_is_detected(self):
        """``ROLLBACK TO SAVEPOINT sp1`` — partial rollback."""
        assert 'ROLLBACK' in detect_mutating_keywords('ROLLBACK TO SAVEPOINT sp1')

    def test_savepoint_is_detected(self):
        """``SAVEPOINT sp1`` — creates a named transaction savepoint."""
        assert 'SAVEPOINT' in detect_mutating_keywords('SAVEPOINT sp1')

    def test_release_savepoint_is_detected(self):
        """``RELEASE SAVEPOINT sp1`` — releases a savepoint."""
        assert 'RELEASE' in detect_mutating_keywords('RELEASE SAVEPOINT sp1')

    def test_xa_start_is_detected(self):
        """``XA START 'xid'`` — distributed-transaction lifecycle."""
        assert 'XA' in detect_mutating_keywords("XA START 'xid'")

    def test_change_replication_source_is_detected(self):
        """``CHANGE REPLICATION SOURCE TO ...`` — rewrites replication config."""
        assert 'CHANGE' in detect_mutating_keywords(
            "CHANGE REPLICATION SOURCE TO SOURCE_HOST = 'h'"
        )

    def test_purge_binary_logs_is_detected(self):
        """``PURGE BINARY LOGS ...`` — deletes binlog files from disk."""
        assert 'PURGE' in detect_mutating_keywords("PURGE BINARY LOGS TO 'mysql-bin.000001'")

    def test_stop_replica_is_detected(self):
        """``STOP REPLICA`` — halts replication threads."""
        assert 'STOP' in detect_mutating_keywords('STOP REPLICA')

    def test_binlog_is_detected(self):
        """``BINLOG '...'`` — injects a raw binary log event."""
        assert 'BINLOG' in detect_mutating_keywords("BINLOG 'base64encodedevent'")

    def test_clone_is_detected(self):
        """``CLONE INSTANCE ...`` — copies the entire instance data directory."""
        assert 'CLONE' in detect_mutating_keywords(
            "CLONE INSTANCE FROM 'user'@'host':3306 IDENTIFIED BY 'pw'"
        )

    def test_restart_is_detected(self):
        """``RESTART`` — restarts the server process."""
        assert 'RESTART' in detect_mutating_keywords('RESTART')

    def test_shutdown_is_detected(self):
        """``SHUTDOWN`` — terminates the server."""
        assert 'SHUTDOWN' in detect_mutating_keywords('SHUTDOWN')

    def test_bare_replace_set_is_detected(self):
        """``REPLACE t SET ...`` — bare REPLACE (no INTO) is still a mutation."""
        assert 'REPLACE' in detect_mutating_keywords('REPLACE t SET id = 1')

    def test_lowercase_leading_verb_is_detected(self):
        """Case-insensitive: lowercase leading verb still fires."""
        assert 'COMMIT' in detect_mutating_keywords('commit')

    def test_leading_whitespace_is_handled(self):
        """Leading whitespace/newlines before the verb do not hide it."""
        assert 'START' in detect_mutating_keywords('\n\t  START TRANSACTION')

    def test_leading_block_comment_then_verb_is_detected(self):
        """``/* header */ COMMIT`` — sqlparse strips the comment, verb still leads."""
        assert 'COMMIT' in detect_mutating_keywords('/* durable now */ COMMIT')


class TestStatementStartKeywordsAfterSemicolon:
    """Statement-leading verbs are detected as the head of a chained statement."""

    def test_commit_after_select_is_detected(self):
        """``SELECT 1; COMMIT`` — COMMIT leads the second statement."""
        assert 'COMMIT' in detect_mutating_keywords('SELECT 1; COMMIT')

    def test_start_transaction_after_select_is_detected(self):
        """``SELECT 1; START TRANSACTION`` — re-arms a writable transaction."""
        assert 'START' in detect_mutating_keywords('SELECT 1; START TRANSACTION')

    def test_do_after_select_is_detected(self):
        """``SELECT 1; DO GET_LOCK('t', 60)`` — DO leads the second statement."""
        assert 'DO' in detect_mutating_keywords("SELECT 1; DO GET_LOCK('t', 60)")


class TestStatementStartKeywordsNoFalsePositives:
    r"""These verbs are common identifiers/functions and MUST NOT fire mid-statement.

    Every payload here is a legitimate read-only query. A regression that
    reverts the statement-start anchoring back to a bare ``\\b`` anywhere
    match would fail these by flagging benign SELECTs.
    """

    def test_column_named_start_is_not_flagged(self):
        """``SELECT start, stop FROM schedule`` — columns, not verbs."""
        assert detect_mutating_keywords('SELECT start, stop FROM schedule') == []

    def test_column_named_change_is_not_flagged(self):
        """``SELECT change FROM ledger`` — column, not CHANGE REPLICATION."""
        assert detect_mutating_keywords('SELECT change FROM ledger') == []

    def test_column_named_release_is_not_flagged(self):
        """``SELECT release FROM versions`` — column, not RELEASE SAVEPOINT."""
        assert detect_mutating_keywords('SELECT release FROM versions') == []

    def test_replace_function_call_is_not_flagged(self):
        """``SELECT REPLACE(name, 'a', 'b') FROM t`` — string function, not a mutation."""
        assert detect_mutating_keywords("SELECT REPLACE(name, 'a', 'b') FROM t") == []

    def test_do_prefixed_identifier_is_not_flagged(self):
        """``SELECT do_work, doing FROM tasks`` — identifiers, not DO expr."""
        assert detect_mutating_keywords('SELECT do_work, doing FROM tasks') == []

    def test_prefixed_identifiers_are_not_flagged(self):
        r"""Columns whose names start with a keyword must not match (``\b`` guard)."""
        sql = 'SELECT begin_date, start_ts, change_log, clone_id FROM events'
        assert detect_mutating_keywords(sql) == []

    def test_xa_as_alias_is_not_flagged(self):
        """``SELECT x.id FROM t AS xa`` — ``xa`` as a table alias is benign."""
        assert detect_mutating_keywords('SELECT xa.id FROM t AS xa') == []

    def test_multiline_select_with_keyword_column_is_not_flagged(self):
        """A keyword-named column on its own line must not match.

        Pins that ``^`` is NOT compiled with re.MULTILINE: a line break
        inside a statement does not create a new statement-start anchor.
        """
        sql = 'SELECT id,\nstart,\nstop\nFROM ranges'
        assert detect_mutating_keywords(sql) == []


def test_statement_start_and_general_keyword_sets_are_disjoint():
    """The two keyword sets must be string-disjoint.

    A keyword string belongs in exactly one set: MUTATING_KEYWORDS (matched
    anywhere) or STATEMENT_START_MUTATING_KEYWORDS (matched only at
    statement start). Overlap would mean an anchored verb is also matched
    anywhere, silently defeating the false-positive protection.

    Note: string-disjoint is not behaviour-disjoint. ``REPLACE`` (here) and
    ``REPLACE INTO`` (in MUTATING_KEYWORDS) are different strings but overlap
    on the ``REPLACE INTO ...`` token, which both scans report; that overlap
    is intentional and harmless (deduped by the caller).
    """
    overlap = MUTATING_KEYWORDS & STATEMENT_START_MUTATING_KEYWORDS
    assert not overlap, f'Keyword in both sets: {sorted(overlap)}'


# ---------------------------------------------------------------------------
# Full-coverage matrix for statement-leading mutating keywords
#
# This is a security control, so the matrix pins BOTH directions for EVERY
# keyword in STATEMENT_START_MUTATING_KEYWORDS, driven off the set itself so
# a future addition to the set is automatically exercised:
#
#   * no false negatives (bypass) — the keyword is detected when it leads a
#     statement, when it leads a chained statement after ``;``, after a bare
#     leading ``;``, and case-insensitively; and
#   * no false positives (over-block) — the same word is NOT flagged when it
#     appears inside a string literal or as an identifier in a read query.
#
# String literals are the critical false-positive surface here: unlike
# comments, they are NOT stripped before the regex scan, so a naive bare
# ``\b<kw>\b`` anywhere-match would reject benign reads like
# ``WHERE note = 'things to do'``. The statement-start anchor is what makes
# these safe, and this matrix guards that guarantee for the whole set.
# ---------------------------------------------------------------------------


class TestStatementStartKeywordFullCoverageMatrix:
    """Every statement-leading keyword: detected as a verb, ignored as data."""

    @pytest.mark.parametrize(
        'keyword,payload',
        sorted(_STATEMENT_START_KEYWORD_PAYLOADS.items()),
    )
    def test_keyword_detected_at_statement_start(self, keyword, payload):
        """The keyword leading a real statement is reported (no false negative)."""
        assert keyword in detect_mutating_keywords(payload)

    @pytest.mark.parametrize(
        'keyword,payload',
        sorted(_STATEMENT_START_KEYWORD_PAYLOADS.items()),
    )
    def test_keyword_detected_lowercase(self, keyword, payload):
        """Detection is case-insensitive."""
        assert keyword in detect_mutating_keywords(payload.lower())

    @pytest.mark.parametrize(
        'keyword,payload',
        sorted(_STATEMENT_START_KEYWORD_PAYLOADS.items()),
    )
    def test_keyword_detected_after_semicolon(self, keyword, payload):
        """A chained statement after ``;`` is reported by keyword.

        Stacked queries are also rejected by SUSPICIOUS_PATTERNS, but the
        readonly gate (detect_mutating_keywords) must name the mutating verb
        of the chained statement in its own right.
        """
        assert keyword in detect_mutating_keywords(f'SELECT 1; {payload}')

    @pytest.mark.parametrize('keyword', sorted(STATEMENT_START_MUTATING_KEYWORDS))
    def test_keyword_detected_after_bare_leading_semicolon(self, keyword):
        """A leading ``;`` before the verb must not hide it."""
        assert keyword in detect_mutating_keywords(f'; {keyword} some_expr()')

    @pytest.mark.parametrize('keyword', sorted(STATEMENT_START_MUTATING_KEYWORDS))
    def test_keyword_in_string_literal_is_not_flagged(self, keyword):
        """The keyword inside a string literal in a read query is NOT flagged.

        String literals are not comment-stripped, so this is the primary
        false-positive surface. The statement-start anchor is what keeps a
        benign ``WHERE col = '<kw> ...'`` read from being rejected.
        """
        sql = f"SELECT id FROM t WHERE label = '{keyword.lower()} pending'"
        assert keyword not in detect_mutating_keywords(sql)

    @pytest.mark.parametrize('keyword', sorted(STATEMENT_START_MUTATING_KEYWORDS))
    def test_keyword_as_identifier_prefix_is_not_flagged(self, keyword):
        r"""A column/identifier that starts with the keyword is NOT flagged.

        The trailing ``\b`` in the pattern prevents ``start_date``,
        ``do_work``, ``change_log`` etc. from matching.
        """
        sql = f'SELECT {keyword.lower()}_col FROM events'
        assert keyword not in detect_mutating_keywords(sql)

    @pytest.mark.parametrize('keyword', sorted(STATEMENT_START_MUTATING_KEYWORDS))
    def test_read_query_with_keyword_only_as_data_is_allowed(self, keyword):
        """End-to-end: a read query that merely mentions the word passes both gates.

        Combines the readonly gate and the injection gate the way
        server.run_query() does, proving the query is actually allowed and
        not rejected for an unrelated reason.
        """
        sql = f"SELECT id, note FROM tasks WHERE note = '{keyword.lower()} later'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []


class TestStatementStartStringLiteralFalsePositives:
    """Named, reviewer-facing pins for the common-English-word keywords.

    These duplicate a slice of the parametrized matrix above with explicit,
    readable payloads so a security reviewer can eyeball the exact benign
    reads that must never be blocked.
    """

    def test_do_inside_string_literal_is_not_flagged(self):
        """``WHERE note = 'things to do'`` — the word "do" as data."""
        assert 'DO' not in detect_mutating_keywords(
            "SELECT note FROM tasks WHERE note = 'things to do'"
        )

    def test_start_inside_string_literal_is_not_flagged(self):
        """``WHERE label = 'start of quarter'`` — "start" as data."""
        assert 'START' not in detect_mutating_keywords(
            "SELECT id FROM events WHERE label = 'start of quarter'"
        )

    def test_stop_inside_string_literal_is_not_flagged(self):
        """``WHERE name = 'bus stop 5'`` — "stop" as data."""
        assert 'STOP' not in detect_mutating_keywords(
            "SELECT id FROM places WHERE name = 'bus stop 5'"
        )

    def test_change_inside_string_literal_is_not_flagged(self):
        """``WHERE action = 'change requested'`` — "change" as data."""
        assert 'CHANGE' not in detect_mutating_keywords(
            "SELECT id FROM tickets WHERE action = 'change requested'"
        )

    def test_release_inside_string_literal_is_not_flagged(self):
        """``WHERE tag = 'release candidate'`` — "release" as data."""
        assert 'RELEASE' not in detect_mutating_keywords(
            "SELECT id FROM builds WHERE tag = 'release candidate'"
        )

    def test_commit_inside_string_literal_is_not_flagged(self):
        """``WHERE kind = 'commit'`` — "commit" as data."""
        assert 'COMMIT' not in detect_mutating_keywords(
            "SELECT sha FROM vcs_log WHERE kind = 'commit'"
        )

    def test_begin_inside_string_literal_is_not_flagged(self):
        """``WHERE phase = 'begin'`` — "begin" as data."""
        assert 'BEGIN' not in detect_mutating_keywords(
            "SELECT id FROM phases WHERE phase = 'begin'"
        )

    def test_replace_function_call_is_not_flagged(self):
        """``SELECT REPLACE(col, 'a', 'b')`` — REPLACE the string function, not the verb."""
        assert 'REPLACE' not in detect_mutating_keywords(
            "SELECT REPLACE(name, 'a', 'b') FROM users"
        )

    def test_multiple_keywords_as_data_in_one_read_is_not_flagged(self):
        """A single read mentioning several keywords as data is fully allowed."""
        sql = "SELECT id FROM audit WHERE note = 'do a change, then commit and release the stop'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []


# ---------------------------------------------------------------------------
# Edge cases and obfuscation for the DO statement
#
# DO is the highest false-positive risk of the statement-leading verbs (it
# is a two-letter common English word), so its detection is pinned here
# against evasion attempts, whitespace/comment permutations, and the benign
# forms that must stay allowed.
# ---------------------------------------------------------------------------


class TestDoStatementEdgeCases:
    """DO detection across whitespace, comments, semicolons, and casing."""

    def test_do_bare_is_detected(self):
        """A lone ``DO`` token is reported (invalid SQL, but flagged safely)."""
        assert 'DO' in detect_mutating_keywords('DO')

    def test_do_no_space_before_paren_is_detected(self):
        """``DO(1)`` — no space between DO and its expression."""
        assert 'DO' in detect_mutating_keywords('DO(1)')

    def test_do_tab_separator_is_detected(self):
        r"""``DO\tSLEEP(1)`` — tab between DO and expression."""
        assert 'DO' in detect_mutating_keywords('DO\tSLEEP(1)')

    def test_do_crlf_leading_is_detected(self):
        """Carriage-return / newline / tab before DO must not hide it."""
        assert 'DO' in detect_mutating_keywords('\r\n\t DO my_udf()')

    def test_do_comment_between_keyword_and_expr_is_detected(self):
        """``DO/**/GET_LOCK(...)`` — comment AFTER the intact keyword is stripped."""
        assert 'DO' in detect_mutating_keywords("DO/**/GET_LOCK('x', 1)")

    def test_do_line_comment_after_keyword_is_detected(self):
        r"""``DO -- c\n GET_LOCK(...)`` — line comment after DO is stripped."""
        assert 'DO' in detect_mutating_keywords("DO -- c\n GET_LOCK('x', 1)")

    def test_do_trailing_comment_is_detected(self):
        """``DO GET_LOCK(...) -- trailing`` — trailing comment does not hide DO."""
        assert 'DO' in detect_mutating_keywords("DO GET_LOCK('x', 1) -- trailing")

    def test_do_trailing_semicolon_is_detected(self):
        """``DO GET_LOCK(...);`` — trailing semicolon."""
        assert 'DO' in detect_mutating_keywords("DO GET_LOCK('x', 1);")

    def test_do_after_semicolon_no_space_is_detected(self):
        """``SELECT 1;DO GET_LOCK(...)`` — no space after the separator."""
        assert 'DO' in detect_mutating_keywords("SELECT 1;DO GET_LOCK('x', 1)")

    def test_do_after_multiple_leading_semicolons_is_detected(self):
        r"""``;;\n DO ...`` — several separators before the verb."""
        assert 'DO' in detect_mutating_keywords(';;\n DO my_udf()')

    def test_do_conditional_comment_is_rejected(self):
        """``/*! DO SLEEP(1) */`` — MySQL conditional comment is rejected."""
        assert detect_mutating_keywords('/*! DO SLEEP(1) */')

    # ---- DO forms that are NOT flagged because they are not runnable ----

    def test_split_do_identifier_is_not_flagged(self):
        """``D/**/O GET_LOCK(...)`` — splitting the keyword yields ``D O``.

        After comment-stripping this is ``D O GET_LOCK(...)`` which is not a
        DO statement and not valid MySQL, so the database rejects it. The
        detector deliberately does not pretend to recognise a DO here.
        """
        assert 'DO' not in detect_mutating_keywords("D/**/O GET_LOCK('x', 1)")

    def test_paren_wrapped_do_is_not_flagged(self):
        """``(DO GET_LOCK(...))`` — a parenthesised DO is not valid MySQL.

        Not a bypass: MySQL does not accept a parenthesised DO statement,
        so it cannot execute even though the anchored pattern does not fire.
        """
        assert 'DO' not in detect_mutating_keywords("(DO GET_LOCK('x', 1))")

    # ---- DO as data / identifier: must stay allowed ----

    def test_do_substrings_are_not_flagged(self):
        """``undo``, ``redo``, ``todo``, ``doing`` etc. are not DO statements."""
        sql = "SELECT undo_id, redo_flag, doing, dojo FROM t WHERE note = 'todo'"
        assert 'DO' not in detect_mutating_keywords(sql)
        assert check_sql_injection_risk(sql) == []

    def test_do_as_trailing_word_in_string_is_not_flagged(self):
        """``'things to do'`` — the word "do" ending a string literal."""
        assert 'DO' not in detect_mutating_keywords("SELECT 'things to do' AS note")

    def test_show_variables_like_undo_is_allowed(self):
        """``SHOW VARIABLES LIKE '%undo%'`` is a benign metadata read."""
        sql = "SHOW VARIABLES LIKE '%undo%'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []


# ---------------------------------------------------------------------------
# DO used as an action clause inside compound / schedule / handler syntax.
#
# In these constructs the ``DO`` is NOT a statement-leading verb, so the DO
# rule correctly does not fire on it. They are still rejected — by the outer
# mutating verb (CREATE / ALTER / HANDLER) or the mutating body — and are in
# any case only valid inside a stored program. These tests pin that the
# block comes from the right place and that DO is not misattributed.
# ---------------------------------------------------------------------------


class TestDoAsActionClauseIsCoveredByOuterVerb:
    """`WHILE ... DO`, `EVENT ... DO`, `HANDLER ... DO` are covered elsewhere."""

    def test_alter_event_with_do_delete_is_blocked_by_alter(self):
        """``ALTER EVENT ... DO DELETE ...`` — caught by ALTER (and DELETE)."""
        sql = (
            'ALTER EVENT my_cleanup_event ON SCHEDULE EVERY 12 HOUR '
            'DO DELETE FROM logs WHERE log_date < NOW() - INTERVAL 15 DAY'
        )
        matches = detect_mutating_keywords(sql)
        assert 'ALTER' in matches
        assert 'DELETE' in matches

    def test_create_event_with_do_is_blocked_by_create(self):
        """``CREATE EVENT ... DO SELECT 1`` — caught by CREATE."""
        assert 'CREATE' in detect_mutating_keywords(
            'CREATE EVENT e ON SCHEDULE EVERY 12 HOUR DO SELECT 1'
        )

    def test_declare_handler_do_set_is_blocked_by_handler_and_set(self):
        """``DECLARE ... HANDLER ... DO SET ...`` — caught by HANDLER and SET."""
        matches = detect_mutating_keywords(
            'DECLARE CONTINUE HANDLER FOR NOT FOUND DO SET completed = 1;'
        )
        assert 'HANDLER' in matches
        assert 'SET' in matches

    def test_while_do_placeholder_body_is_not_flagged_as_do(self):
        """``WHILE cond DO ... END WHILE`` — the loop ``DO`` is not a DO statement.

        A placeholder body is not runnable as a top-level statement (MySQL
        only accepts WHILE inside a stored program), and the loop keyword
        DO must not be misattributed as a ``DO expr`` mutation.
        """
        sql = 'WHILE search_condition DO\n    statement_list\nEND WHILE;'
        assert 'DO' not in detect_mutating_keywords(sql)

    def test_while_do_with_real_mutation_is_blocked_by_body(self):
        """``WHILE ... DO INSERT ...`` — the body's INSERT is caught anywhere."""
        assert 'INSERT' in detect_mutating_keywords(
            'WHILE x DO INSERT INTO t VALUES (1); END WHILE;'
        )


# ---------------------------------------------------------------------------
# Additional real-world false-positive guards for the new keywords.
# ---------------------------------------------------------------------------


class TestNewKeywordAdditionalFalsePositives:
    """Reads that mention the new verbs as data / identifiers stay allowed."""

    def test_keywords_in_in_list_are_not_flagged(self):
        """Keywords as string literals in an ``IN (...)`` list are benign."""
        sql = "SELECT id FROM orders WHERE status IN ('start', 'stop', 'change', 'commit')"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_keywords_as_aliases_are_not_flagged(self):
        """Keywords as string-literal column aliases are benign."""
        sql = "SELECT 'commit' AS action, 'rollback' AS undo_action"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_backticked_keyword_identifiers_are_not_flagged(self):
        """Backticked identifiers named after keywords are benign reads."""
        sql = 'SELECT `start`, `end` FROM `change`'
        assert detect_mutating_keywords(sql) == []

    def test_keyword_prefixed_identifiers_are_not_flagged(self):
        """Identifiers that merely start with a keyword are benign."""
        sql = (
            'SELECT restart_required, xa_flag, savepoint_id, purged_at, '
            'clone_url, changelog, binlog_file FROM cfg'
        )
        assert detect_mutating_keywords(sql) == []

    def test_keyword_substring_in_like_is_allowed(self):
        """``LIKE '%shutdown%'`` — keyword as a search substring is benign."""
        sql = "SELECT id FROM logs WHERE msg LIKE '%shutdown%'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []


# ---------------------------------------------------------------------------
# Documented over-block: a semicolon inside a string literal.
#
# ``WHERE note = 'a; commit b'`` is rejected. This is a deliberate,
# pre-existing trade-off: the stacked-queries pattern in
# check_sql_injection_risk flags any ``;`` followed by non-whitespace,
# independent of the statement-start keyword scan. Pinned so a future change
# that relaxes it must do so deliberately.
# ---------------------------------------------------------------------------


class TestSemicolonInStringLiteralOverBlock:
    """A semicolon inside a string literal is blocked (documented trade-off)."""

    def test_semicolon_in_string_is_rejected(self):
        """``WHERE note = 'a; commit b'`` — blocked by the stacked-queries rule."""
        assert check_sql_injection_risk("SELECT * FROM t WHERE note = 'a; commit b'")


# ---------------------------------------------------------------------------
# Comment / whitespace obfuscation dimension for statement-leading verbs.
#
# The keyword-coverage matrix above varies the *keyword*; this class varies
# the *comment/whitespace prefix* for a fixed set of high-value verbs. It
# specifically pins the MySQL ``#`` line comment (including the no-space
# ``#x`` form that sqlparse leaves in place), which would otherwise hide a
# leading verb from the anchored scan on the RDS Data API path where
# detect_mutating_keywords is the sole gate.
# ---------------------------------------------------------------------------


class TestLeadingCommentObfuscationIsStripped:
    """A leading comment must not hide a statement-leading mutating verb."""

    @pytest.mark.parametrize(
        'prefix',
        [
            '',
            '-- c\n',
            '--\n',
            '/* c */',
            '/* c */ ',
            '# c\n',  # hash comment WITH space (sqlparse strips)
            '#\n',  # bare hash
            '#c\n',  # hash comment NO space (sqlparse leaves it — must strip explicitly)
            '#x\n',
            '   \n\t',  # whitespace only
        ],
    )
    @pytest.mark.parametrize('verb', ["DO GET_LOCK('x', 60)", 'SHUTDOWN', 'START REPLICA'])
    def test_leading_comment_or_ws_does_not_hide_verb(self, prefix, verb):
        """``<prefix><verb>`` is still detected regardless of the prefix form."""
        expected = verb.split()[0].split('(')[0].upper()
        assert expected in detect_mutating_keywords(prefix + verb)

    @pytest.mark.parametrize(
        'prefix',
        ['#c\n', '#x\n', '# \n', '-- c\n', '/* c */'],
    )
    def test_comment_before_verb_after_semicolon_is_detected(self, prefix):
        """``SELECT 1;<comment>DO ...`` — comment after ``;`` must not hide DO."""
        assert 'DO' in detect_mutating_keywords(f"SELECT 1;{prefix}DO GET_LOCK('x', 1)")

    def test_hash_no_space_bypass_is_closed(self):
        r"""Regression: ``#x\nDO GET_LOCK(...)`` and ``#c\nSHUTDOWN`` are rejected.

        sqlparse does not strip a ``#`` comment unless a space follows it, so
        without an explicit ``#`` strip these single statements slipped past
        the anchored scan (the stacked-queries rule does not apply — there is
        no ``;``). This is the sole gate on the RDS Data API path.
        """
        assert 'DO' in detect_mutating_keywords("#x\nDO GET_LOCK('x', 60)")
        assert 'SHUTDOWN' in detect_mutating_keywords('#c\nSHUTDOWN')

    def test_hash_inside_string_literal_is_not_a_false_positive(self):
        """A ``#`` inside a string literal in a benign read is not over-stripped into a match."""
        sql = "SELECT id FROM t WHERE tag = '#sale'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []


# ---------------------------------------------------------------------------
# Side-effecting functions blocked regardless of invocation form.
#
# Blocking the statement verb (``DO``) is not enough: the read-shaped twin
# ``SELECT GET_LOCK(...)`` calls the same side-effecting function. These are
# rejected via SUSPICIOUS_PATTERNS in both read and write mode, matching the
# existing sleep()/benchmark()/load_file() treatment. Anchored to a ``(`` so
# same-named identifiers are not flagged.
# ---------------------------------------------------------------------------


class TestSideEffectingFunctions:
    """`SELECT f(...)` for a side-effecting function is blocked, symmetric with `DO f(...)`."""

    @pytest.mark.parametrize('fn', sorted(SIDE_EFFECTING_FUNCTIONS))
    def test_side_effecting_function_in_select_is_blocked(self, fn):
        """Each side-effecting function is rejected when wrapped in a SELECT."""
        assert check_sql_injection_risk(f"SELECT {fn}('x')")

    @pytest.mark.parametrize('fn', sorted(SIDE_EFFECTING_FUNCTIONS))
    def test_side_effecting_function_case_insensitive(self, fn):
        """Detection is case-insensitive."""
        assert check_sql_injection_risk(f'SELECT {fn.upper()}(1)')

    def test_do_and_select_get_lock_are_symmetric(self):
        """The reported asymmetry is closed: both DO and SELECT forms are blocked."""
        do_blocked = bool(detect_mutating_keywords("DO GET_LOCK('x', 60)"))
        select_blocked = bool(check_sql_injection_risk("SELECT GET_LOCK('x', 60)"))
        assert do_blocked and select_blocked

    def test_get_lock_with_whitespace_before_paren_is_blocked(self):
        """``GET_LOCK ('x', 60)`` — whitespace before the paren still matches."""
        assert check_sql_injection_risk("SELECT GET_LOCK ('x', 60)")

    def test_sys_exec_in_where_clause_is_blocked(self):
        """A side-effecting function anywhere in the query (not just the select list)."""
        assert check_sql_injection_risk("SELECT id FROM t WHERE sys_exec('id') = 0")

    # ---- false-positive guards ----

    def test_last_insert_id_no_arg_is_allowed(self):
        """``LAST_INSERT_ID()`` (no arg) is a benign read and must be allowed."""
        assert check_sql_injection_risk('SELECT LAST_INSERT_ID()') == []
        assert detect_mutating_keywords('SELECT LAST_INSERT_ID()') == []

    def test_last_insert_id_with_arg_is_blocked(self):
        """``LAST_INSERT_ID(expr)`` sets the session value (side effect) — blocked."""
        assert check_sql_injection_risk('SELECT LAST_INSERT_ID(5)')

    def test_last_insert_id_empty_parens_with_spaces_is_allowed(self):
        """``LAST_INSERT_ID(  )`` is still the no-arg read form."""
        assert check_sql_injection_risk('SELECT LAST_INSERT_ID(  )') == []

    def test_read_only_lock_status_probes_are_allowed(self):
        """``IS_FREE_LOCK`` / ``IS_USED_LOCK`` report status only — not blocked."""
        assert check_sql_injection_risk("SELECT IS_FREE_LOCK('x')") == []
        assert check_sql_injection_risk("SELECT IS_USED_LOCK('x')") == []

    def test_same_named_identifier_is_not_blocked(self):
        """A column/table named like a function (no following ``(``) is not flagged."""
        assert check_sql_injection_risk('SELECT get_lock FROM t') == []
        assert check_sql_injection_risk('SELECT id FROM release_lock') == []


# ---------------------------------------------------------------------------
# Session / server-state statement verbs (USE, CACHE INDEX, LOAD INDEX ...).
# ---------------------------------------------------------------------------


class TestSessionStateStatementVerbs:
    """USE / CACHE INDEX / LOAD INDEX INTO CACHE are gated; hints/identifiers are not."""

    def test_use_database_is_detected(self):
        """``USE <db>`` switches the session default database (session state)."""
        assert 'USE' in detect_mutating_keywords('USE mydb')

    def test_cache_index_is_detected(self):
        """``CACHE INDEX ... IN ...`` assigns indexes to a key cache."""
        assert 'CACHE' in detect_mutating_keywords('CACHE INDEX t IN kc')

    def test_load_index_into_cache_is_detected(self):
        """``LOAD INDEX INTO CACHE ...`` preloads indexes into a key cache."""
        assert 'LOAD INDEX' in detect_mutating_keywords('LOAD INDEX INTO CACHE t')

    def test_use_after_semicolon_is_detected(self):
        """``SELECT 1; USE mydb`` — USE leads the chained statement."""
        assert 'USE' in detect_mutating_keywords('SELECT 1; USE mydb')

    # ---- false-positive guards ----

    def test_use_index_optimizer_hint_is_not_flagged(self):
        """``SELECT ... USE INDEX (idx)`` — the USE here is an index hint, not USE <db>.

        The statement-start anchor is what distinguishes the two: the hint's
        USE is mid-statement, so it must not be flagged.
        """
        assert detect_mutating_keywords('SELECT * FROM t USE INDEX (idx)') == []
        assert check_sql_injection_risk('SELECT * FROM t USE INDEX (idx)') == []

    def test_force_and_ignore_index_hints_are_not_flagged(self):
        """Sibling optimizer hints are unaffected."""
        assert detect_mutating_keywords('SELECT * FROM t FORCE INDEX (idx)') == []
        assert detect_mutating_keywords('SELECT * FROM t IGNORE INDEX (idx)') == []

    def test_use_cache_prefixed_identifiers_are_not_flagged(self):
        """Columns like ``use_flag``, ``cache_size``, ``usage`` are not verbs."""
        assert detect_mutating_keywords('SELECT use_flag, cache_size, usage FROM t') == []


# ---------------------------------------------------------------------------
# The `#`-comment strip must be string-literal aware.
#
# A ``#`` inside a string literal or backtick identifier is data, not a
# comment, so stripping ``#...EOL`` there would delete trailing real SQL and
# hide a mutation. These pin the false-NEGATIVE direction (mutation after a
# ``#``-bearing string must still be detected) as well as the benign reads.
# ---------------------------------------------------------------------------


class TestHashStripIsStringLiteralAware:
    """`#` inside quotes is preserved; a `#` comment outside quotes is stripped."""

    # ---- false negatives: mutation after a #-bearing string MUST be caught ----

    def test_hash_in_string_then_stacked_drop_is_detected(self):
        """``WHERE c = '#foo'; DROP TABLE t`` — the trailing DROP must survive."""
        sql = "SELECT id FROM t WHERE c = '#foo'; DROP TABLE t"
        assert 'DROP' in detect_mutating_keywords(sql)
        assert check_sql_injection_risk(sql)  # stacked-query + DROP patterns

    def test_hash_only_string_then_stacked_drop_is_detected(self):
        """``SELECT '#' ; DROP TABLE users`` — string is just ``#``."""
        sql = "SELECT '#' ; DROP TABLE users"
        assert 'DROP' in detect_mutating_keywords(sql)
        assert check_sql_injection_risk(sql)

    def test_hash_in_string_then_sleep_probe_is_detected(self):
        """``WHERE c = '#x' OR SLEEP(5)`` — the SLEEP probe must survive."""
        assert check_sql_injection_risk("SELECT id FROM t WHERE c = '#x' OR SLEEP(5)")

    def test_hash_in_backtick_identifier_then_get_lock_is_detected(self):
        """``SELECT `a#b`, GET_LOCK('x',1)`` — GET_LOCK after a #-identifier."""
        assert check_sql_injection_risk("SELECT `a#b`, GET_LOCK('x', 1)")

    def test_hash_in_string_then_union_select_is_detected(self):
        """``SELECT '#a' UNION SELECT ...`` — UNION-injection must survive."""
        assert check_sql_injection_risk("SELECT '#a' UNION SELECT password FROM users")

    def test_backslash_escaped_quote_then_hash_then_drop_is_detected(self):
        r"""``SELECT 'a\'#b'; DROP TABLE t`` — escaped quote keeps the string open."""
        sql = "SELECT 'a\\'#b'; DROP TABLE t"
        assert 'DROP' in detect_mutating_keywords(sql)

    def test_doubled_quote_then_hash_then_drop_is_detected(self):
        """``SELECT 'it''s a #test'; DROP TABLE t`` — doubled-quote escape."""
        sql = "SELECT 'it''s a #test'; DROP TABLE t"
        assert 'DROP' in detect_mutating_keywords(sql)

    def test_double_quoted_string_with_hash_then_delete_is_detected(self):
        """``SELECT "d#e"; DELETE FROM t`` — double-quoted string with a ``#``."""
        assert 'DELETE' in detect_mutating_keywords('SELECT "d#e"; DELETE FROM t')

    def test_multiple_hash_comment_lines_then_verb_is_detected(self):
        r"""``#a\n#b\nDO GET_LOCK(...)`` — real comment lines before a verb."""
        assert 'DO' in detect_mutating_keywords("#a\n#b\nDO GET_LOCK('x', 1)")

    # ---- false positives: benign #-bearing data must stay allowed ----

    def test_hashtag_string_is_allowed(self):
        """``tag = '#sale'`` — a hashtag literal is benign."""
        sql = "SELECT id FROM t WHERE tag = '#sale'"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_hex_color_string_is_allowed(self):
        """``'#ffffff'`` — a hex colour literal is benign."""
        sql = "SELECT '#ffffff' AS color FROM t"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_multiple_hash_strings_are_allowed(self):
        """Several ``#``-bearing string literals in one read are benign."""
        sql = "SELECT '#a', '#b' FROM t"
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_backtick_hash_identifiers_are_allowed(self):
        """Backtick identifiers containing ``#`` are benign."""
        assert detect_mutating_keywords('SELECT `c#1`, `c#2` FROM t') == []

    def test_doubled_quote_hash_string_is_allowed(self):
        """``'it''s #1'`` — doubled-quote escape with a ``#`` is benign data."""
        assert detect_mutating_keywords("SELECT 'it''s #1' AS n") == []
        assert check_sql_injection_risk("SELECT 'it''s #1' AS n") == []

    def test_trailing_hash_comment_after_read_is_allowed(self):
        """A genuine trailing ``#`` comment on a read is stripped, not flagged."""
        sql = 'SELECT id FROM users # trailing note\nWHERE active = 1'
        assert detect_mutating_keywords(sql) == []
        assert check_sql_injection_risk(sql) == []

    def test_fully_commented_line_is_inert_but_next_line_is_not(self):
        """A whole-line ``#`` comment is inert, but the next line is not.

        A whole-line ``#`` comment executes nothing in MySQL, so a verb
        entirely inside the comment is inert (allowed); the same verb on a
        line AFTER the comment is a real statement and must be blocked. (The
        pre-`#`-strip code false-positive-blocked the inert form because the
        commented-out keyword text was still scanned.)
        """
        # entire line is a comment -> no statement executes -> allowed
        assert detect_mutating_keywords('#x DROP TABLE t') == []
        assert check_sql_injection_risk('#x DROP TABLE t') == []
        # real statement on the next line -> blocked
        assert 'DROP' in detect_mutating_keywords('#x\nDROP TABLE t')
