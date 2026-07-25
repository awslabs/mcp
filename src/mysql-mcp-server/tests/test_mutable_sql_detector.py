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
