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

"""Unit tests for the mutating-SQL keyword detector and dangerous-function check.

These tests cover the security additions documented in the module's
comments: session-state mutation keywords (SET, RESET, DISCARD, LOAD),
anonymous code execution (DO), the IMPORT FOREIGN SCHEMA missing-comma
fix, and the dangerous-function blocklist.
"""

import pytest
from awslabs.postgres_mcp_server.mutable_sql_detector import (
    DANGEROUS_FUNCTIONS,
    MUTATING_KEYWORDS,
    SECURITY_SENSITIVE_GUCS,
    check_sql_injection_risk,
    detect_mutating_keywords,
)


class TestAllMutatingKeywords:
    """Every entry in MUTATING_KEYWORDS must be detected.

    These are the verbs rejected when readonly_query is True. The
    data-driven test iterates the actual set so any future addition is
    automatically covered; the explicit-SQL test documents real attack
    inputs for the common DML/DDL verbs.
    """

    @pytest.mark.parametrize('keyword', sorted(MUTATING_KEYWORDS))
    def test_every_keyword_detected(self, keyword):
        """Each keyword in the set is matched by the detector.

        Detection is a word-boundary regex match, so embedding the
        keyword in a minimal statement is sufficient and works for
        multi-word entries (e.g. 'IMPORT FOREIGN SCHEMA') too.
        """
        sql = f'{keyword} something_follows'
        matches = detect_mutating_keywords(sql)
        assert keyword in matches, f'{keyword!r} not detected in {sql!r}, got {matches}'

    @pytest.mark.parametrize(
        'sql,expected_keyword',
        [
            ("INSERT INTO t (a) VALUES (1)", 'INSERT'),
            ("UPDATE t SET a = 1 WHERE id = 2", 'UPDATE'),
            ('DELETE FROM t WHERE id = 1', 'DELETE'),
            ('MERGE INTO t USING s ON t.id = s.id', 'MERGE'),
            ('TRUNCATE TABLE t', 'TRUNCATE'),
            ("COPY t FROM '/tmp/x.csv'", 'COPY'),
            ('LISTEN my_channel', 'LISTEN'),
            ('LOCK TABLE t IN EXCLUSIVE MODE', 'LOCK'),
            ("NOTIFY my_channel, 'payload'", 'NOTIFY'),
            ('REFRESH MATERIALIZED VIEW mv', 'REFRESH'),
            ('PREPARE stmt AS SELECT 1', 'PREPARE'),
            ('CREATE TABLE t (id int)', 'CREATE'),
            ('DROP TABLE t', 'DROP'),
            ('ALTER TABLE t ADD COLUMN c int', 'ALTER'),
            ('ALTER TABLE t RENAME TO t2', 'RENAME'),
            ('GRANT SELECT ON t TO bob', 'GRANT'),
            ('REVOKE SELECT ON t FROM bob', 'REVOKE'),
            ("COMMENT ON TABLE t IS 'x'", 'COMMENT ON'),
            ("SECURITY LABEL ON TABLE t IS 'x'", 'SECURITY LABEL'),
            ('CREATE EXTENSION pg_stat_statements', 'CREATE EXTENSION'),
            ('CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql', 'CREATE FUNCTION'),
            ('INSTALL some_thing', 'INSTALL'),
            ('CALL my_procedure()', 'CALL'),
            ('EXECUTE stmt', 'EXECUTE'),
            ('CLUSTER t USING t_idx', 'CLUSTER'),
            ('REINDEX TABLE t', 'REINDEX'),
            ('VACUUM FULL t', 'VACUUM'),
            ('ANALYZE t', 'ANALYZE'),
            ('SET search_path TO x', 'SET'),
            ('RESET ALL', 'RESET'),
            ('DISCARD ALL', 'DISCARD'),
            ("LOAD 'auto_explain'", 'LOAD'),
            ('DO $$ BEGIN PERFORM 1; END $$', 'DO'),
            (
                'IMPORT FOREIGN SCHEMA public FROM SERVER s INTO local',
                'IMPORT FOREIGN SCHEMA',
            ),
        ],
    )
    def test_representative_sql_detected(self, sql, expected_keyword):
        """Realistic statements for each verb are detected."""
        matches = detect_mutating_keywords(sql)
        assert expected_keyword in matches, (
            f'expected {expected_keyword} in {matches} for {sql!r}'
        )

    def test_benign_select_has_no_mutating_keyword(self):
        """A plain SELECT must not match any mutating keyword."""
        assert detect_mutating_keywords('SELECT id, name FROM users WHERE id = 1') == []


class TestSuspiciousPatterns:
    """check_sql_injection_risk's SUSPICIOUS_PATTERNS catch injection shapes.

    These run in both read and write mode. Each representative input
    must produce at least one issue. Note that pg_sleep is now caught
    earlier by the dangerous-function check; the bare sleep( pattern
    still exercises the suspicious-pattern path.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            # comment injection
            "SELECT * FROM t WHERE name = '' OR ''='' --",
            # numeric tautology OR 1=1
            'SELECT * FROM t WHERE id = 1 OR 1=1',
            # string tautology OR 'a'='a'
            "SELECT * FROM t WHERE name = 'x' OR 'a'='a'",
            # UNION SELECT
            'SELECT a FROM t UNION SELECT password FROM users',
            # DROP
            'DROP TABLE t',
            # TRUNCATE
            'TRUNCATE TABLE t',
            # GRANT / REVOKE
            'GRANT SELECT ON t TO bob',
            'REVOKE SELECT ON t FROM bob',
            # stacked queries
            'SELECT 1; SELECT 2',
            # delay-based probe (bare sleep, not pg_sleep)
            'SELECT sleep(5)',
            # MySQL-ism file read primitive
            "SELECT load_file('/etc/passwd')",
            # MySQL-ism file write
            "SELECT * INTO OUTFILE '/tmp/x' FROM t",
        ],
    )
    def test_suspicious_pattern_flagged(self, sql):
        """Each suspicious-pattern shape produces at least one issue."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) >= 1, f'expected an issue for {sql!r}'
        assert issues[0]['severity'] == 'high'

    def test_clean_query_has_no_issue(self):
        """A parameterized-style clean query produces no issue."""
        assert check_sql_injection_risk('SELECT id, name FROM users WHERE id = 1') == []


class TestSessionStateKeywords:
    """SET / RESET / DISCARD / LOAD mutate session state on the connection.

    Even though they don't mutate rows, they alter the session context
    for every subsequent query on a pooled connection, which can poison
    later queries the agent issues.
    """

    @pytest.mark.parametrize(
        'sql,expected_keyword',
        [
            ('SET search_path TO public, attacker_schema', 'SET'),
            ("set statement_timeout = '0'", 'SET'),
            ('RESET ALL', 'RESET'),
            ('reset session_replication_role', 'RESET'),
            ('DISCARD ALL', 'DISCARD'),
            ('discard temp', 'DISCARD'),
            ("LOAD '/tmp/lib.so'", 'LOAD'),
            ('load \'auto_explain\'', 'LOAD'),
        ],
    )
    def test_session_state_keyword_detected(self, sql, expected_keyword):
        """Each session-state verb is in the mutating-keyword set."""
        matches = detect_mutating_keywords(sql)
        assert expected_keyword in matches, (
            f'expected {expected_keyword} for {sql!r}, got {matches}'
        )

    def test_select_with_similar_word_not_flagged(self):
        """Word-boundary regex avoids false positives on identifiers."""
        # Names that contain the keyword as a substring should not match.
        assert detect_mutating_keywords('SELECT * FROM resets WHERE id = 1') == []
        assert detect_mutating_keywords('SELECT load_balancer FROM cfg') == []
        assert detect_mutating_keywords('SELECT discarded_at FROM events') == []


class TestDoBlock:
    """DO $$ ... $$ runs PL/pgSQL even inside read-only transactions.

    Procedural side effects (pg_sleep loops, RAISE, PERFORM SECURITY
    DEFINER funcs) execute regardless of the read-only constraint.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            'DO $$ BEGIN PERFORM 1; END $$',
            'do $$ begin perform pg_sleep(10); end $$',
            "DO LANGUAGE plpgsql $$ BEGIN RAISE NOTICE 'x'; END $$",
            # Mixed leading whitespace
            '   DO $$ BEGIN END $$',
        ],
    )
    def test_do_block_detected(self, sql):
        """DO is detected regardless of casing or surrounding whitespace."""
        assert 'DO' in detect_mutating_keywords(sql)

    def test_identifiers_starting_with_do_not_flagged(self):
        """Word boundaries keep 'do_thing' / 'done_things' from matching DO."""
        assert detect_mutating_keywords('SELECT do_not_match(1)') == []
        assert detect_mutating_keywords('SELECT * FROM done_things') == []


class TestImportForeignSchemaCommaFix:
    """Regression test for the IMPORT FOREIGN SCHEMA missing-comma bug.

    A missing trailing comma silently merged ``'IMPORT FOREIGN SCHEMA'``
    with the next entry into one string, so neither IMPORT FOREIGN
    SCHEMA nor the merged-into entry matched on its own. Both must now
    match independently.
    """

    def test_import_foreign_schema_detected(self):
        """IMPORT FOREIGN SCHEMA is matched as a single multi-word keyword."""
        sql = (
            'IMPORT FOREIGN SCHEMA public LIMIT TO (t1) '
            'FROM SERVER fs INTO local_schema'
        )
        matches = detect_mutating_keywords(sql)
        assert 'IMPORT FOREIGN SCHEMA' in matches

    def test_grant_still_detected_independently(self):
        """GRANT matches on its own even though it followed the broken entry."""
        # Pre-fix the merged 'IMPORT FOREIGN SCHEMAGRANT' meant GRANT
        # also failed to match. Confirm GRANT works on its own.
        matches = detect_mutating_keywords('GRANT SELECT ON tbl TO bob')
        assert 'GRANT' in matches

    def test_revoke_still_detected_independently(self):
        """REVOKE matches on its own."""
        matches = detect_mutating_keywords('REVOKE SELECT ON tbl FROM bob')
        assert 'REVOKE' in matches


class TestDangerousFunctions:
    """Functions that are dangerous regardless of read/write mode.

    These fire from check_sql_injection_risk so they're rejected even
    when readonly_query is False.
    """

    @pytest.mark.parametrize(
        'sql,expected_function',
        [
            ('SELECT pg_cancel_backend(99999)', 'pg_cancel_backend'),
            ('SELECT pg_terminate_backend(123)', 'pg_terminate_backend'),
            ('select pg_sleep(10)', 'pg_sleep'),
            ("SELECT pg_sleep_for(interval '1 second')", 'pg_sleep_for'),
            ("SELECT pg_sleep_until(now() + interval '1 minute')", 'pg_sleep_until'),
            ("SELECT pg_read_file('/etc/passwd')", 'pg_read_file'),
            ("SELECT pg_read_binary_file('/etc/passwd', 0, 100)", 'pg_read_binary_file'),
            ("SELECT * FROM pg_ls_dir('pg_log')", 'pg_ls_dir'),
            ("SELECT pg_stat_file('pg_log/postgresql.log')", 'pg_stat_file'),
            ("SELECT lo_import('/tmp/x')", 'lo_import'),
            ("SELECT lo_export(0, '/tmp/x')", 'lo_export'),
            ('SELECT pg_reload_conf()', 'pg_reload_conf'),
            ('SELECT pg_rotate_logfile()', 'pg_rotate_logfile'),
            # Advisory-lock family (Class L). Each variant must match
            # because each one independently allows an attacker to
            # acquire an application coordination lock.
            ('SELECT pg_advisory_lock(42)', 'pg_advisory_lock'),
            ('SELECT pg_advisory_lock_shared(42)', 'pg_advisory_lock_shared'),
            ('SELECT pg_advisory_xact_lock(42)', 'pg_advisory_xact_lock'),
            ('SELECT pg_advisory_xact_lock_shared(42)', 'pg_advisory_xact_lock_shared'),
            ('SELECT pg_try_advisory_lock(42)', 'pg_try_advisory_lock'),
            ('SELECT pg_try_advisory_lock_shared(42)', 'pg_try_advisory_lock_shared'),
            ('SELECT pg_try_advisory_xact_lock(42)', 'pg_try_advisory_xact_lock'),
            (
                'SELECT pg_try_advisory_xact_lock_shared(42)',
                'pg_try_advisory_xact_lock_shared',
            ),
            # NOTIFY-channel side-channel.
            ("SELECT pg_notify('ch', 'payload')", 'pg_notify'),
        ],
    )
    def test_each_dangerous_function_rejected(self, sql, expected_function):
        """Each dangerous function in the blocklist is rejected with a named reason."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert issues[0]['type'] == 'sql'
        assert issues[0]['severity'] == 'high'
        # The rejection message should name the specific function so
        # the operator can see what was blocked.
        assert expected_function in issues[0]['message']

    def test_advisory_lock_prefix_overlap_resolved_correctly(self):
        """pg_advisory_lock and pg_advisory_lock_shared are prefix-overlapping.

        The regex must report the longer name when the input is the
        longer one. If the shorter name's alternative wins, the
        operator gets a misleading rejection reason and a
        downstream test that checks 'pg_advisory_lock_shared' in the
        message would silently fail.
        """
        for short_name, long_name in [
            ('pg_advisory_lock', 'pg_advisory_lock_shared'),
            ('pg_advisory_xact_lock', 'pg_advisory_xact_lock_shared'),
            ('pg_try_advisory_lock', 'pg_try_advisory_lock_shared'),
            ('pg_try_advisory_xact_lock', 'pg_try_advisory_xact_lock_shared'),
        ]:
            issues = check_sql_injection_risk(f'SELECT {long_name}(42)')
            assert len(issues) == 1
            # The longer name must appear; the shorter is also a substring
            # of the message but only because it's a substring of the
            # longer name. Check by structural assertion: the short name
            # alone must not be the only thing the regex captured.
            assert long_name in issues[0]['message'], (
                f'expected {long_name} in message, got {issues[0]["message"]!r}'
            )
            # And, just to be explicit: a query for the short name
            # alone resolves to the short name.
            short_issues = check_sql_injection_risk(f'SELECT {short_name}(42)')
            assert short_name in short_issues[0]['message']
            assert long_name not in short_issues[0]['message']

    def test_schema_qualified_call_rejected(self):
        """Schema-qualified calls (pg_catalog.pg_terminate_backend) match."""
        issues = check_sql_injection_risk(
            'SELECT pg_catalog.pg_terminate_backend(123)'
        )
        assert len(issues) == 1
        assert 'pg_terminate_backend' in issues[0]['message']

    def test_uppercase_function_call_rejected(self):
        """Uppercase / mixed-case spellings are still detected.

        Postgres folds unquoted identifiers to lowercase, but our regex
        must still match the upper-case spellings an LLM might emit.
        """
        issues = check_sql_injection_risk('SELECT PG_TERMINATE_BACKEND(123)')
        assert len(issues) == 1

    def test_dangerous_function_message_explains_why(self):
        """The rejection message names the function and the reason category.

        Operator readability matters — the message shouldn't just say
        'suspicious'. It must identify which function was blocked and
        why so the operator can decide whether to allow it via role
        permissions instead.
        """
        issues = check_sql_injection_risk('SELECT pg_terminate_backend(1)')
        msg = issues[0]['message']
        assert 'pg_terminate_backend' in msg
        # Mentions the impact category so the operator understands the
        # block isn't arbitrary.
        assert 'cluster-wide side effects' in msg or 'DoS' in msg

    @pytest.mark.parametrize(
        'sql',
        [
            # Identifier coincidentally containing the function name
            'SELECT my_pg_sleep_helper(10)',
            'SELECT * FROM pg_terminate_backend_audit',
            # Function name without a call (no opening paren)
            'SELECT pg_terminate_backend',
            # Referenced as a string literal, not a call
            "SELECT 'pg_terminate_backend' AS name",
        ],
    )
    def test_false_positive_avoidance(self, sql):
        """Word-boundary + open-paren requirement avoids false positives."""
        # check_sql_injection_risk may flag these via OTHER patterns
        # (e.g. comment injection), but the dangerous-function check
        # specifically must not fire. Easiest assertion: if there's an
        # issue, its message must NOT mention "Dangerous function".
        issues = check_sql_injection_risk(sql)
        for issue in issues:
            assert 'Dangerous function call' not in issue['message'], (
                f'unexpected dangerous-function rejection for {sql!r}'
            )

    def test_dangerous_functions_list_is_non_empty(self):
        """Sanity check that the blocklist hasn't been emptied accidentally."""
        # 13 originals + 8 advisory + 1 pg_notify = 22.
        assert len(DANGEROUS_FUNCTIONS) >= 22
        # The two specifically called out in the threat model must be
        # present; treat their absence as a regression.
        assert 'pg_cancel_backend' in DANGEROUS_FUNCTIONS
        assert 'pg_terminate_backend' in DANGEROUS_FUNCTIONS
        # Advisory-lock family — Class L threat model.
        assert 'pg_advisory_lock' in DANGEROUS_FUNCTIONS
        assert 'pg_advisory_xact_lock' in DANGEROUS_FUNCTIONS
        assert 'pg_try_advisory_xact_lock_shared' in DANGEROUS_FUNCTIONS

    def test_safe_select_passes(self):
        """Confirm a benign SELECT yields no issues."""
        assert check_sql_injection_risk('SELECT id, name FROM users WHERE id = 1') == []


class TestSecuritySensitiveGucs:
    """SET row_security / session_replication_role disable access controls.

    Unlike generic SET (which is only blocked in read-only mode via the
    mutating-keyword path), these two GUCs are rejected from
    check_sql_injection_risk so they're blocked even when the server
    runs with writes enabled — setting them silently weakens RLS or
    trigger-based integrity for every subsequent query on the
    connection.
    """

    @pytest.mark.parametrize(
        'sql,expected_guc',
        [
            ('SET row_security = off', 'row_security'),
            ('SET row_security TO off', 'row_security'),
            ('set session row_security = off', 'row_security'),
            ('SET LOCAL row_security = off', 'row_security'),
            ('SET session_replication_role = replica', 'session_replication_role'),
            ('set session_replication_role to replica', 'session_replication_role'),
            (
                'SET SESSION session_replication_role = replica',
                'session_replication_role',
            ),
        ],
    )
    def test_security_guc_rejected(self, sql, expected_guc):
        """Each security-sensitive GUC is rejected with a named reason."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert issues[0]['type'] == 'sql'
        assert issues[0]['severity'] == 'high'
        assert expected_guc in issues[0]['message']

    def test_benign_guc_not_flagged_by_security_check(self):
        """A non-sensitive SET is not caught by the security-GUC check.

        It may still be blocked in read-only mode by the mutating-keyword
        path, but check_sql_injection_risk (which runs in both modes)
        must not reject an ordinary GUC like statement_timeout.
        """
        issues = check_sql_injection_risk('SET statement_timeout = 0')
        for issue in issues:
            assert 'Security-sensitive SET' not in issue['message']

    def test_guc_name_as_column_not_flagged(self):
        """Reading a column named row_security is not a SET and is allowed."""
        issues = check_sql_injection_risk('SELECT row_security FROM cfg')
        for issue in issues:
            assert 'Security-sensitive SET' not in issue['message']

    def test_security_guc_set_is_mode_independent(self):
        """A security GUC is rejected by the mode-independent check.

        The check lives in check_sql_injection_risk, not the readonly
        path, so it doesn't depend on readonly_query. This asserts the
        function-level contract: a security GUC is always rejected.
        """
        # Both calls go through the same mode-independent function.
        assert check_sql_injection_risk('SET row_security = off')
        assert check_sql_injection_risk('SET session_replication_role = replica')

    def test_security_sensitive_guc_set_contents(self):
        """Sanity check the GUC set has exactly the two intended entries."""
        assert SECURITY_SENSITIVE_GUCS == {'row_security', 'session_replication_role'}


class TestLegitimateReadQueriesAllowed:
    """Positive-path coverage: realistic read queries must NOT be blocked.

    The blocking tests above prove dangerous input is rejected. These
    tests prove the detector doesn't over-block — a read-only agent
    issuing ordinary SELECTs (joins, CTEs, window functions, aggregates,
    catalog introspection) must pass both the mutating-keyword check
    (readonly path) and check_sql_injection_risk (always-on path).

    A query is considered "allowed" only if BOTH checks pass:
      - detect_mutating_keywords(sql) == []   (not blocked in readonly mode)
      - check_sql_injection_risk(sql) == []   (not blocked in any mode)
    """

    ALLOWED_QUERIES = [
        # Basic filtered select
        'SELECT id, name FROM users WHERE id = 1',
        # Aggregate
        'SELECT count(*) FROM orders',
        # Join
        'SELECT u.name, o.total FROM users u JOIN orders o ON o.user_id = u.id',
        # GROUP BY / HAVING / ORDER BY / LIMIT
        (
            'SELECT dept, avg(salary) FROM emp GROUP BY dept '
            'HAVING avg(salary) > 1000 ORDER BY dept LIMIT 10'
        ),
        # CTE
        (
            "WITH recent AS (SELECT * FROM events WHERE ts > now() - interval '1 day') "
            'SELECT * FROM recent'
        ),
        # Window function
        'SELECT row_number() OVER (PARTITION BY dept ORDER BY salary DESC) FROM emp',
        # Built-in informational function
        'SELECT version()',
        # Constant select
        'SELECT 1',
        # Escaped single quote in a string literal (not comment injection)
        "SELECT id FROM t WHERE name = 'O''Brien'",
        # Tables whose names embed a mutating keyword as a substring
        'SELECT * FROM created_users',
        'SELECT * FROM updates',
        'SELECT * FROM deleted_items',
        # Reading the settings catalog is a legitimate read (vs SET which mutates)
        'SELECT setting FROM pg_settings',
        "SELECT current_setting('search_path')",
        # Column name that is a prefix of a dangerous function (no call)
        'SELECT loadavg FROM metrics',
        # Plain OR with column refs (not an OR-tautology)
        'SELECT id FROM t WHERE a = 1 OR b = 2',
        # Single trailing semicolon is tolerated (not a stacked query)
        'SELECT id, name FROM users WHERE id = 1;',
        # The real introspection query get_table_schema issues
        (
            'SELECT a.attname FROM pg_attribute a '
            "WHERE a.attrelid = to_regclass('t') AND a.attnum > 0 ORDER BY a.attnum"
        ),
        # information_schema introspection
        "SELECT * FROM information_schema.columns WHERE table_name = 'users'",
        # coalesce / scalar functions
        "SELECT coalesce(name, 'n/a') FROM users",
        # EXTRACT
        'SELECT EXTRACT(YEAR FROM created_at) FROM orders',
        # Plain EXPLAIN (without ANALYZE) is a read-only planner inspection
        'EXPLAIN SELECT * FROM t',
    ]

    @pytest.mark.parametrize('sql', ALLOWED_QUERIES)
    def test_not_blocked_in_readonly_mode(self, sql):
        """No mutating keyword is detected, so the readonly path allows it."""
        matches = detect_mutating_keywords(sql)
        assert matches == [], f'unexpected mutating-keyword block for {sql!r}: {matches}'

    @pytest.mark.parametrize('sql', ALLOWED_QUERIES)
    def test_not_blocked_by_injection_check(self, sql):
        """check_sql_injection_risk (always-on) raises no issue."""
        issues = check_sql_injection_risk(sql)
        assert issues == [], f'unexpected injection-risk block for {sql!r}: {issues}'


class TestKnownFalsePositives:
    """Document detector limitations as explicit, intentional tests.

    These inputs are benign but get blocked by the regex-based detector.
    They are recorded here so the behaviour is intentional and visible:
    if a future change accidentally *fixes* one, the maintainer sees the
    test fail and can decide whether the fix is desired. The detector is
    documented as best-effort defence-in-depth, so over-blocking these
    edge cases is an accepted trade-off.
    """

    def test_explain_analyze_blocked_in_readonly(self):
        """EXPLAIN ANALYZE trips the ANALYZE keyword in readonly mode.

        ANALYZE-the-statistics-command and ANALYZE-the-EXPLAIN-option
        share a keyword. Plain EXPLAIN (tested in the allow list) is
        fine; EXPLAIN ANALYZE is over-blocked in readonly mode.
        """
        assert 'ANALYZE' in detect_mutating_keywords('EXPLAIN ANALYZE SELECT * FROM t')

    def test_double_dash_inside_string_literal_flagged(self):
        """A literal containing '--' trips the comment-injection pattern.

        The regex can't distinguish a real trailing comment from '--'
        appearing inside a quoted string. Accepted limitation.
        """
        issues = check_sql_injection_risk(
            "SELECT * FROM t WHERE note = 'see comment -- here'"
        )
        assert len(issues) >= 1
