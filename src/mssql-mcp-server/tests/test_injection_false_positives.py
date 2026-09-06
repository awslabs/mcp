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

"""Tests for SQL injection detection false positives."""

from awslabs.mssql_mcp_server.mutable_sql_detector import check_sql_injection_risk


# ─── UNION SELECT false positive fix ────────────────────────────────────────────


def test_legitimate_union_select_not_flagged():
    """A legitimate UNION SELECT query should not be flagged as injection."""
    sql = 'SELECT name FROM users UNION SELECT name FROM admins'
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_legitimate_union_all_select_not_flagged():
    """A legitimate UNION ALL SELECT query should not be flagged."""
    sql = 'SELECT id, name FROM table1 UNION ALL SELECT id, name FROM table2'
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_legitimate_multi_union_not_flagged():
    """Multiple UNION clauses in a query should not be flagged."""
    sql = 'SELECT col1 FROM t1 UNION SELECT col1 FROM t2 UNION SELECT col1 FROM t3'
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_injection_union_select_with_string_closing_flagged():
    """UNION SELECT preceded by string-closing is flagged as injection."""
    sql = "SELECT * FROM users WHERE name = '' UNION SELECT password FROM credentials"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_injection_union_select_typical_sqli_flagged():
    """Typical SQL injection pattern with UNION is flagged."""
    sql = "' UNION SELECT username, password FROM users--"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_injection_union_select_with_numeric_column_flagged():
    """UNION injection with numeric columns after string literal is flagged."""
    sql = "SELECT * FROM products WHERE id = '1' UNION SELECT null, table_name FROM information_schema.tables"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


# ─── string literal content not flagged ──────────────────────────────────────────


def test_keyword_inside_string_literal_not_flagged():
    """Keywords inside string literals should not trigger injection detection."""
    sql = "SELECT * FROM logs WHERE message = 'User tried WAITFOR DELAY attack'"
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_union_keyword_inside_string_literal_not_flagged():
    """UNION inside a string literal without injection context should not be flagged."""
    sql = "SELECT * FROM logs WHERE message = 'UNION SELECT is a SQL keyword'"
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_sp_name_inside_string_literal_not_flagged():
    """sp_ prefix inside a string literal should not be flagged."""
    sql = "SELECT * FROM docs WHERE content = 'Call sp_configure to change settings'"
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_xp_name_inside_string_literal_not_flagged():
    """xp_ prefix inside a string literal should not be flagged."""
    sql = "SELECT * FROM audit WHERE note = 'Blocked xp_cmdshell attempt'"
    issues = check_sql_injection_risk(sql)
    assert issues == []


# ─── comment injection pattern false-positive fix ──────────────────────────────


def test_comment_injection_no_space_detected():
    """Comment injection with no space between quote and -- is flagged."""
    sql = "SELECT * FROM users WHERE name = 'admin'-- AND password = 'x'"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_comment_injection_with_space_detected():
    """Comment injection with space between quote and -- is also flagged."""
    sql = "SELECT * FROM users WHERE name = 'admin' -- AND password = 'x'"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_standard_comment_injection_attack():
    """Classic comment injection: attacker closes string and comments out the rest."""
    sql = "SELECT * FROM users WHERE name = 'admin'-- AND active = 1"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_standard_union_injection_attack():
    """Classic UNION injection: attacker closes string then appends UNION SELECT."""
    sql = "SELECT * FROM users WHERE name = '' UNION SELECT username, password FROM credentials--"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_standalone_comment_line_allowed():
    """A standalone comment line (-- at start of line) is allowed."""
    sql = "-- this is a comment\nSELECT * FROM users WHERE name = 'admin'"
    issues = check_sql_injection_risk(sql)
    assert issues == []


def test_inline_comment_blocked():
    """Inline comments (-- after code on same line) are blocked."""
    sql = "SELECT * FROM users WHERE name = 'admin' -- look up the admin user"
    issues = check_sql_injection_risk(sql)
    assert len(issues) == 1


def test_standalone_comment_with_union_allowed():
    """A UNION query with comments on their own lines is allowed."""
    sql = '-- combined employee and contractor list\nSELECT id, name FROM employees UNION SELECT id, name FROM contractors'
    issues = check_sql_injection_risk(sql)
    assert issues == []


# ─── SELECT INTO false-positive fix ────────────────────────────────────────────


def test_column_name_containing_into_not_flagged():
    """A column name containing 'into' (e.g. shipped_into) should not trigger SELECT INTO."""
    from awslabs.mssql_mcp_server.mutable_sql_detector import detect_mutating_keywords

    sql = "SELECT * FROM orders WHERE shipped_into = 'warehouse'"
    keywords = detect_mutating_keywords(sql)
    assert 'SELECT INTO' not in keywords


def test_table_alias_into_not_flagged():
    """A table/column with 'into' as a word should not trigger SELECT INTO without table token."""
    from awslabs.mssql_mcp_server.mutable_sql_detector import detect_mutating_keywords

    sql = 'SELECT * FROM logs WHERE inserted_into_queue = 1'
    keywords = detect_mutating_keywords(sql)
    assert 'SELECT INTO' not in keywords


def test_real_select_into_still_detected():
    """A real SELECT INTO #temp is still detected."""
    from awslabs.mssql_mcp_server.mutable_sql_detector import detect_mutating_keywords

    sql = 'SELECT col1, col2 INTO #temp_table FROM source_table'
    keywords = detect_mutating_keywords(sql)
    assert 'SELECT INTO' in keywords
