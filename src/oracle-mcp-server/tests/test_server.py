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

"""Tests for the oracle MCP server tools."""

import pytest
from awslabs.oracle_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
)
from awslabs.oracle_mcp_server.connection.oracledb_pool_connection import OracledbPoolConnection
from awslabs.oracle_mcp_server.mutable_sql_detector import (
    _strip_sql_comments,
    check_sql_injection_risk,
    detect_mutating_keywords,
    detect_transaction_bypass_attempt,
)
from awslabs.oracle_mcp_server.server import (
    ServerConfig,
    _catalog_form,
    _identifier_to_catalog_form,
    db_connection_map,
    internal_create_connection,
    is_database_connected,
    server_config,
    validate_table_name,
)
from unittest.mock import AsyncMock, MagicMock


class DummyCtx:
    """Minimal context stub for testing server tools."""

    async def error(self, message):
        """Record an error message (no-op for tests)."""
        pass


@pytest.fixture(autouse=True)
def _reset_server_config():
    """Reset server_config to defaults after each test."""
    defaults = ServerConfig()
    yield
    server_config.readonly_query = defaults.readonly_query
    server_config.default_secret_arn = defaults.default_secret_arn
    server_config.ssl_encryption_mode = defaults.ssl_encryption_mode
    server_config.configured_port = defaults.configured_port
    server_config.max_rows = defaults.max_rows


# --- validate_table_name ---


def test_validate_simple_table():
    """Simple unqualified table name is accepted."""
    assert validate_table_name('USERS') is True


def test_validate_schema_qualified():
    """Schema-qualified table name is accepted."""
    assert validate_table_name('HR.EMPLOYEES') is True


def test_validate_double_quoted():
    """Double-quoted identifiers are accepted."""
    assert validate_table_name('"HR"."EMPLOYEES"') is True


def test_validate_three_part():
    """Three-part name (db.schema.table) is accepted."""
    assert validate_table_name('MYDB.HR.EMPLOYEES') is True


def test_validate_four_parts_rejected():
    """Four-part name is rejected."""
    assert validate_table_name('a.b.c.d') is False


def test_validate_empty_rejected():
    """Empty string is rejected."""
    assert validate_table_name('') is False


def test_validate_none_rejected():
    """None is rejected."""
    assert validate_table_name(None) is False


def test_validate_injection_rejected():
    """SQL injection attempt in table name is rejected."""
    assert validate_table_name("USERS'; DROP TABLE foo--") is False


def test_validate_leading_digit_rejected():
    """Table name starting with a digit is rejected."""
    assert validate_table_name('123TABLE') is False


# --- _catalog_form ---


def test_catalog_form_unquoted():
    """Unquoted identifiers are uppercased for catalog lookup."""
    assert _catalog_form('employees', False) == 'EMPLOYEES'


def test_catalog_form_quoted():
    """Quoted identifiers preserve their original case."""
    assert _catalog_form('myTable', True) == 'myTable'


def test_catalog_form_quoted_uppercase():
    """Quoted uppercase identifiers stay uppercase."""
    assert _catalog_form('EMPLOYEES', True) == 'EMPLOYEES'


# --- _identifier_to_catalog_form ---


def test_identifier_to_catalog_form_unquoted():
    """Raw unquoted identifier is uppercased."""
    assert _identifier_to_catalog_form('employees') == 'EMPLOYEES'


def test_identifier_to_catalog_form_quoted():
    """Raw quoted identifier preserves case."""
    assert _identifier_to_catalog_form('"myTable"') == 'myTable'


def test_identifier_to_catalog_form_unquoted_mixed_case():
    """Raw unquoted mixed-case identifier is uppercased."""
    assert _identifier_to_catalog_form('MyTable') == 'MYTABLE'


# --- is_database_connected ---


def test_is_database_connected_true(mocker):
    """Returns True when a connection exists."""
    mock_conn = MagicMock()
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    result = is_database_connected(
        db_endpoint='endpoint1', instance_identifier='inst1', database='ORCL'
    )
    assert result is True


def test_is_database_connected_false(mocker):
    """Returns False when no connection exists."""
    mocker.patch.object(db_connection_map, 'get', return_value=None)
    result = is_database_connected(
        db_endpoint='ep_nope', instance_identifier='inst_nope', database='ORCL'
    )
    assert result is False


def test_is_database_connected_explicit_method(mocker):
    """Passes the explicit connection_method to the connection map."""
    mock_get = mocker.patch.object(db_connection_map, 'get', return_value=MagicMock())
    is_database_connected(
        db_endpoint='ep1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        database='ORCL',
    )
    call_args = mock_get.call_args
    assert call_args[1].get('method', call_args[0][0]) == ConnectionMethod.ORACLE_PASSWORD


# --- mutating keyword blocking ---


@pytest.mark.asyncio
async def test_run_query_blocks_drop(mocker):
    """DROP is blocked in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='DROP TABLE HR.EMPLOYEES',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_audit(mocker):
    """AUDIT is blocked in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='AUDIT SELECT TABLE BY ACCESS',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_no_connection(mocker):
    """Returns error when no database connection is available."""
    from awslabs.oracle_mcp_server.server import run_query

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    ctx = DummyCtx()
    result = await run_query(
        sql='SELECT 1 FROM DUAL',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='noexist',
        db_endpoint='nowhere',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


# --- get_table_schema ---


@pytest.mark.asyncio
async def test_get_table_schema_uppercases_table_name(mocker):
    """Unquoted table name is uppercased before querying ALL_TAB_COLUMNS."""
    from awslabs.oracle_mcp_server.server import get_table_schema

    run_query_mock = AsyncMock(return_value=[{'COLUMN_NAME': 'ID'}])
    mocker.patch('awslabs.oracle_mcp_server.server.run_query', run_query_mock)
    ctx = DummyCtx()
    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    await get_table_schema(
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        database='ORCL',
        table_name='employees',
        ctx=ctx,
    )

    call_args = run_query_mock.call_args
    params = call_args.kwargs.get('query_parameters', [])
    table_param = next(p for p in params if p['name'] == 'table_name')
    assert table_param['value']['stringValue'] == 'EMPLOYEES'


@pytest.mark.asyncio
async def test_get_table_schema_preserves_quoted_case(mocker):
    """Quoted table name preserves case for catalog lookup."""
    from awslabs.oracle_mcp_server.server import get_table_schema

    run_query_mock = AsyncMock(return_value=[{'COLUMN_NAME': 'ID'}])
    mocker.patch('awslabs.oracle_mcp_server.server.run_query', run_query_mock)
    ctx = DummyCtx()
    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    await get_table_schema(
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        database='ORCL',
        table_name='"myTable"',
        ctx=ctx,
    )

    call_args = run_query_mock.call_args
    params = call_args.kwargs.get('query_parameters', [])
    table_param = next(p for p in params if p['name'] == 'table_name')
    assert table_param['value']['stringValue'] == 'myTable'


@pytest.mark.asyncio
async def test_get_table_schema_extracts_schema_from_qualified_name(mocker):
    """Schema-qualified table name extracts both schema and table for catalog lookup."""
    from awslabs.oracle_mcp_server.server import get_table_schema

    run_query_mock = AsyncMock(return_value=[{'COLUMN_NAME': 'ID'}])
    mocker.patch('awslabs.oracle_mcp_server.server.run_query', run_query_mock)
    ctx = DummyCtx()
    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    await get_table_schema(
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        database='ORCL',
        table_name='"hr"."myTable"',
        ctx=ctx,
    )

    call_args = run_query_mock.call_args
    params = call_args.kwargs.get('query_parameters', [])
    table_param = next(p for p in params if p['name'] == 'table_name')
    schema_param = next(p for p in params if p['name'] == 'schema_name')
    assert table_param['value']['stringValue'] == 'myTable'
    assert schema_param['value']['stringValue'] == 'hr'


@pytest.mark.asyncio
async def test_get_table_schema_with_port(mocker):
    """Port parameter is forwarded to run_query."""
    from awslabs.oracle_mcp_server.server import get_table_schema

    run_query_mock = AsyncMock(return_value='ok')
    mocker.patch('awslabs.oracle_mcp_server.server.run_query', run_query_mock)
    ctx = DummyCtx()

    await get_table_schema(
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        database='ORCL',
        table_name='EMPLOYEES',
        ctx=ctx,
        port=2484,
    )

    call_args = run_query_mock.call_args
    assert call_args.kwargs.get('port') == 2484


# --- comment stripping ---


def test_strip_line_comments():
    """Line comments are removed from SQL text."""
    sql = 'SELECT * FROM t -- this is a CREATE comment'
    assert 'CREATE' not in _strip_sql_comments(sql).upper().split()


def test_strip_block_comments():
    """Block comments are removed from SQL text."""
    sql = 'SELECT /* DROP TABLE evil */ * FROM t'
    assert 'DROP' not in _strip_sql_comments(sql)


def test_strip_multiline_block_comment():
    """Multiline block comments are removed from SQL text."""
    sql = 'SELECT /*\nDROP TABLE evil\n*/ * FROM t'
    assert 'DROP' not in _strip_sql_comments(sql)


# --- string-literal-aware comment stripping ---


def test_dash_inside_string_literal_not_stripped():
    """Double-dash inside a single-quoted string is not treated as a comment."""
    sql = "SELECT 'safe--',dbms_scheduler.create_job('evil') FROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'dbms_scheduler' in stripped


def test_block_comment_inside_string_literal_not_stripped():
    """Block comment markers inside a string literal are preserved."""
    sql = "SELECT '/* not a comment */', DROP TABLE t FROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'DROP' in stripped


def test_escaped_quote_inside_string():
    """Escaped single quotes ('') inside a string don't end the literal early."""
    sql = "SELECT 'it''s--fine', dbms_output.put_line('x') FROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'dbms_output' in stripped


def test_real_comment_after_string_still_stripped():
    """A real line comment after a string literal is still stripped."""
    sql = "SELECT 'hello' -- DROP TABLE evil\nFROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'DROP' not in stripped


def test_real_block_comment_after_string_still_stripped():
    """A real block comment after a string literal is still stripped."""
    sql = "SELECT 'hello' /* DROP TABLE evil */ FROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'DROP' not in stripped


def test_alt_quoting_preserves_content():
    """Oracle alternative quoting q'[...]' preserves content inside."""
    sql = "SELECT q'[it's -- tricky]', dbms_pipe.send('x') FROM DUAL"
    stripped = _strip_sql_comments(sql)
    assert 'dbms_pipe' in stripped


def test_injection_detected_through_string_with_dashes():
    """The bypass SELECT 'x--',dbms_scheduler... is caught by injection detector."""
    sql = "SELECT 'safe--',dbms_scheduler.create_job('evil') FROM DUAL"
    assert len(check_sql_injection_risk(sql)) > 0


def test_double_quoted_identifier_with_block_comment_chars():
    """Block comment markers inside double-quoted identifiers are not comments."""
    sql = """SELECT "/*",dbms_scheduler.create_job('evil'),"*/" FROM DUAL"""
    stripped = _strip_sql_comments(sql)
    assert 'dbms_scheduler' in stripped


def test_multiline_double_quoted_identifier_bypass():
    """Multi-line payload hidden between double-quoted identifier comment markers."""
    sql = 'SELECT "/*",\nutl_http.request(\'http://evil.com\'),\n"*/" FROM employees'
    stripped = _strip_sql_comments(sql)
    assert 'utl_http' in stripped


def test_injection_detected_through_double_quoted_identifier():
    """The bypass SELECT "/*",dbms_scheduler...,"*/" is caught by injection detector."""
    sql = """SELECT "/*",dbms_scheduler.create_job('evil'),"*/" FROM DUAL"""
    assert len(check_sql_injection_risk(sql)) > 0


def test_real_comment_after_double_quoted_identifier():
    """A real comment after a double-quoted identifier is still stripped."""
    sql = 'SELECT "col" -- DROP TABLE evil\nFROM t'
    stripped = _strip_sql_comments(sql)
    assert 'DROP' not in stripped


def test_comment_precedence_line_then_block():
    """Line comment on same line as /* prevents block comment from opening."""
    sql = '--/*\nDROP TABLE FOOBAR;\n--*/'
    stripped = _strip_sql_comments(sql)
    assert 'DROP' in stripped
    assert 'DROP' in detect_mutating_keywords(sql)


# --- mutating keyword detection with comments ---


def test_keyword_inside_line_comment_not_detected():
    """Mutating keywords inside line comments are ignored."""
    sql = 'SELECT 1 FROM DUAL -- DROP TABLE users'
    assert detect_mutating_keywords(sql) == []


def test_keyword_inside_block_comment_not_detected():
    """Mutating keywords inside block comments are ignored."""
    sql = 'SELECT /* INSERT INTO evil */ * FROM t'
    assert detect_mutating_keywords(sql) == []


def test_keyword_outside_comment_detected():
    """Mutating keywords outside comments are detected."""
    sql = 'INSERT INTO t VALUES (1)'
    assert 'INSERT' in detect_mutating_keywords(sql)


# --- new mutating keywords ---


def test_detect_flashback():
    """FLASHBACK is detected as a mutating keyword."""
    assert 'FLASHBACK' in detect_mutating_keywords(
        'FLASHBACK TABLE hr.employees TO TIMESTAMP sysdate - 1'
    )


def test_detect_analyze():
    """ANALYZE is detected as a mutating keyword."""
    assert 'ANALYZE' in detect_mutating_keywords('ANALYZE TABLE hr.employees COMPUTE STATISTICS')


def test_detect_lock_table():
    """LOCK TABLE is detected as a mutating keyword."""
    assert 'LOCK TABLE' in detect_mutating_keywords('LOCK TABLE hr.employees IN EXCLUSIVE MODE')


def test_detect_call():
    """CALL is detected as a mutating keyword."""
    assert 'CALL' in detect_mutating_keywords('CALL my_procedure()')


def test_detect_comment_on():
    """COMMENT ON is detected as a mutating keyword."""
    assert 'COMMENT ON' in detect_mutating_keywords(
        "COMMENT ON TABLE hr.employees IS 'Employee data'"
    )


def test_detect_begin():
    """BEGIN is detected as a mutating keyword."""
    assert 'BEGIN' in detect_mutating_keywords('BEGIN my_pkg.wipe_data; END;')


def test_detect_declare():
    """DECLARE is detected as a mutating keyword."""
    assert 'DECLARE' in detect_mutating_keywords('DECLARE v_x NUMBER; BEGIN NULL; END;')


def test_detect_set_role():
    """SET ROLE is detected as a mutating keyword."""
    assert 'SET ROLE' in detect_mutating_keywords('SET ROLE DBA')


def test_detect_administer():
    """ADMINISTER is detected as a mutating keyword."""
    assert 'ADMINISTER' in detect_mutating_keywords('ADMINISTER KEY MANAGEMENT')


def test_detect_associate_statistics():
    """ASSOCIATE STATISTICS is detected as a mutating keyword."""
    assert 'ASSOCIATE STATISTICS' in detect_mutating_keywords(
        'ASSOCIATE STATISTICS WITH COLUMNS hr.employees.salary'
    )


def test_detect_disassociate_statistics():
    """DISASSOCIATE STATISTICS is detected as a mutating keyword."""
    assert 'DISASSOCIATE STATISTICS' in detect_mutating_keywords(
        'DISASSOCIATE STATISTICS FROM COLUMNS hr.employees.salary'
    )


def test_detect_explain_plan():
    """EXPLAIN PLAN is detected as a mutating keyword (writes to PLAN_TABLE)."""
    assert 'EXPLAIN PLAN' in detect_mutating_keywords(
        'EXPLAIN PLAN FOR SELECT * FROM hr.employees'
    )


def test_detect_explain_plan_with_into():
    """EXPLAIN PLAN with INTO clause is detected."""
    assert 'EXPLAIN PLAN' in detect_mutating_keywords(
        "EXPLAIN PLAN SET STATEMENT_ID = 'test' INTO my_plan_table FOR SELECT 1 FROM DUAL"
    )


def test_select_not_flagged():
    """Plain SELECT is not flagged as mutating."""
    assert detect_mutating_keywords('SELECT * FROM employees') == []


def test_select_from_dual_not_flagged():
    """SELECT FROM DUAL is not flagged as mutating."""
    assert detect_mutating_keywords('SELECT 1 FROM DUAL') == []


# --- suspicious patterns: Oracle-specific injection vectors ---


def test_injection_execute_immediate():
    """EXECUTE IMMEDIATE is flagged as injection risk."""
    issues = check_sql_injection_risk("BEGIN EXECUTE IMMEDIATE 'DROP TABLE users'; END;")
    assert len(issues) == 1
    assert issues[0]['severity'] == 'high'


def test_injection_alter_system():
    """ALTER SYSTEM is flagged as injection risk."""
    issues = check_sql_injection_risk('ALTER SYSTEM SET audit_trail=NONE')
    assert len(issues) == 1


def test_injection_alter_session():
    """ALTER SESSION is flagged as injection risk."""
    issues = check_sql_injection_risk('ALTER SESSION SET CURRENT_SCHEMA = SYS')
    assert len(issues) == 1


def test_injection_create_directory():
    """CREATE DIRECTORY is flagged as injection risk."""
    issues = check_sql_injection_risk("CREATE DIRECTORY evil_dir AS '/tmp'")
    assert len(issues) == 1


def test_injection_create_database_link():
    """CREATE DATABASE LINK is flagged as injection risk."""
    issues = check_sql_injection_risk(
        'CREATE DATABASE LINK remote_db CONNECT TO user IDENTIFIED BY pass'
    )
    assert len(issues) == 1


def test_injection_create_or_replace():
    """CREATE OR REPLACE is flagged as injection risk."""
    issues = check_sql_injection_risk(
        'CREATE OR REPLACE FUNCTION backdoor RETURN NUMBER IS BEGIN RETURN 1; END;'
    )
    assert len(issues) == 1


def test_injection_autonomous_transaction():
    """AUTONOMOUS_TRANSACTION pragma is flagged as injection risk."""
    issues = check_sql_injection_risk('PRAGMA AUTONOMOUS_TRANSACTION')
    assert len(issues) == 1


def test_injection_owa_util():
    """OWA_UTIL access is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT owa_util.get_cgi_env('REMOTE_ADDR') FROM DUAL")
    assert len(issues) == 1


def test_injection_htp():
    """HTP package usage is flagged as injection risk."""
    issues = check_sql_injection_risk("BEGIN htp.print('hello'); END;")
    assert len(issues) == 1


def test_injection_htf():
    """HTF package usage is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT htf.anchor('http://evil.com','click') FROM DUAL")
    assert len(issues) == 1


def test_injection_dbms_package():
    """DBMS_* package usage is flagged as injection risk."""
    issues = check_sql_injection_risk("BEGIN dbms_scheduler.create_job('evil'); END;")
    assert len(issues) == 1


def test_injection_utl_package():
    """UTL_* package usage is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT utl_http.request('http://evil.com') FROM DUAL")
    assert len(issues) == 1


def test_injection_create_java():
    """CREATE JAVA is flagged as injection risk."""
    issues = check_sql_injection_risk('CREATE JAVA SOURCE NAMED evil AS public class Evil {}')
    assert len(issues) == 1


def test_injection_xmltype():
    """XMLTYPE constructor is flagged as injection risk (XXE vector)."""
    issues = check_sql_injection_risk(
        'SELECT xmltype(\'<!DOCTYPE foo SYSTEM "http://evil.com">\') FROM DUAL'
    )
    assert len(issues) == 1


def test_injection_alternative_quoting():
    """Oracle alternative quoting syntax is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT q'[malicious'--payload]' FROM DUAL")
    assert len(issues) == 1


def test_injection_sys_internal_table():
    """Access to SYS internal tables is flagged as injection risk."""
    issues = check_sql_injection_risk('SELECT password FROM sys.user$')
    assert len(issues) == 1


def test_injection_v_dollar_view():
    """V$ dynamic performance view access is flagged as injection risk."""
    issues = check_sql_injection_risk('SELECT sql_text FROM v$sql')
    assert len(issues) == 1


def test_injection_gv_dollar_view():
    """GV$ global dynamic performance view access is flagged as injection risk."""
    issues = check_sql_injection_risk('SELECT * FROM gv$session')
    assert len(issues) == 1


def test_injection_dba_view():
    """DBA_ dictionary view access is flagged as injection risk."""
    issues = check_sql_injection_risk('SELECT username, password FROM dba_users')
    assert len(issues) == 1


def test_injection_httpuritype():
    """HTTPURITYPE usage is flagged as injection risk (SSRF vector)."""
    issues = check_sql_injection_risk("SELECT HTTPURITYPE('http://evil.com').getclob() FROM DUAL")
    assert len(issues) == 1


def test_injection_uritype():
    """URITYPE usage is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT URITYPE('/etc/passwd').getclob() FROM DUAL")
    assert len(issues) == 1


def test_injection_ctxsys():
    """CTXSYS schema access is flagged as injection risk."""
    issues = check_sql_injection_risk("SELECT CTXSYS.DRITHSX.SN(1, 'evil') FROM DUAL")
    assert len(issues) == 1


def test_injection_connect_by_tautology():
    """CONNECT BY tautology is flagged as injection risk (DoS vector)."""
    issues = check_sql_injection_risk('SELECT LEVEL FROM DUAL CONNECT BY 1=1')
    assert len(issues) == 1


def test_injection_connect_by_level():
    """CONNECT BY LEVEL is flagged as injection risk (DoS via row generation)."""
    issues = check_sql_injection_risk('SELECT LEVEL FROM dual CONNECT BY LEVEL <= 1000000')
    assert len(issues) == 1


def test_injection_connect_by_rownum():
    """CONNECT BY ROWNUM is flagged as injection risk (DoS via row generation)."""
    issues = check_sql_injection_risk('SELECT 1 FROM dual CONNECT BY ROWNUM <= 1000000')
    assert len(issues) == 1


# --- injection detection only checks stripped SQL ---


def test_injection_comment_hidden_not_detected():
    """Injection pattern inside a comment is not flagged after stripping."""
    issues = check_sql_injection_risk('SELECT 1 FROM DUAL -- ALTER SYSTEM SET x=1')
    assert issues == []


# --- comment-evasion detection ---


def test_injection_stacked_queries_comment_evasion():
    """Stacked query hidden behind a line comment is still detected."""
    issues = check_sql_injection_risk('SELECT 1;\n--\nCOMMIT')
    assert len(issues) == 1


# --- removed patterns: MySQL-only and redundant patterns should not cause false matches ---


def test_into_outfile_not_flagged():
    """INTO OUTFILE is MySQL syntax, not Oracle — should not be in suspicious patterns."""
    issues = check_sql_injection_risk("SELECT * INTO OUTFILE '/tmp/data.csv' FROM users")
    assert issues == []


# --- write-mode fix: DROP/TRUNCATE/GRANT/REVOKE no longer blocked by injection check ---


def test_drop_not_flagged_as_injection():
    """DROP should be caught by mutating keywords, not injection patterns."""
    issues = check_sql_injection_risk('DROP TABLE temp_data')
    assert issues == []


def test_truncate_not_flagged_as_injection():
    """TRUNCATE should be caught by mutating keywords, not injection patterns."""
    issues = check_sql_injection_risk('TRUNCATE TABLE temp_data')
    assert issues == []


def test_grant_not_flagged_as_injection():
    """GRANT should be caught by mutating keywords, not injection patterns."""
    issues = check_sql_injection_risk('GRANT SELECT ON hr.employees TO readonly_user')
    assert issues == []


def test_revoke_not_flagged_as_injection():
    """REVOKE should be caught by mutating keywords, not injection patterns."""
    issues = check_sql_injection_risk('REVOKE SELECT ON hr.employees FROM old_user')
    assert issues == []


# --- transaction bypass detection ---


def test_transaction_bypass_commit():
    """COMMIT is detected as transaction control."""
    matches = detect_transaction_bypass_attempt('COMMIT')
    assert 'COMMIT' in matches


def test_transaction_bypass_rollback():
    """ROLLBACK is detected as transaction control."""
    matches = detect_transaction_bypass_attempt('ROLLBACK')
    assert 'ROLLBACK' in matches


def test_transaction_bypass_savepoint():
    """SAVEPOINT is detected as transaction control."""
    matches = detect_transaction_bypass_attempt('SAVEPOINT sp1')
    assert 'SAVEPOINT' in matches


def test_transaction_bypass_set_transaction():
    """SET TRANSACTION is detected as transaction control."""
    matches = detect_transaction_bypass_attempt('SET TRANSACTION READ WRITE')
    assert 'SET TRANSACTION' in matches


def test_transaction_bypass_in_comment_not_detected():
    """Transaction control keywords inside comments are ignored."""
    matches = detect_transaction_bypass_attempt('SELECT 1 FROM DUAL -- COMMIT')
    assert matches == []


def test_no_transaction_bypass_in_select():
    """Plain SELECT has no transaction control keywords."""
    matches = detect_transaction_bypass_attempt('SELECT * FROM employees')
    assert matches == []


# --- transaction bypass blocks in read-only mode via run_query ---


@pytest.mark.asyncio
async def test_run_query_blocks_commit_in_readonly(mocker):
    """COMMIT is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='COMMIT',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_plsql_begin_in_readonly(mocker):
    """PL/SQL BEGIN block is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='BEGIN my_pkg.delete_all; END;',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_plsql_declare_in_readonly(mocker):
    """PL/SQL DECLARE block is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='DECLARE v_x NUMBER; BEGIN NULL; END;',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_set_role_in_readonly(mocker):
    """SET ROLE is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='SET ROLE DBA',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_explain_plan_in_readonly(mocker):
    """EXPLAIN PLAN is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='EXPLAIN PLAN FOR SELECT * FROM HR.EMPLOYEES',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


@pytest.mark.asyncio
async def test_run_query_blocks_set_transaction_in_readonly(mocker):
    """SET TRANSACTION is blocked via run_query in read-only mode."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='SET TRANSACTION READ WRITE',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert isinstance(result, dict)
    assert 'error' in result


# --- read-only mode message in successful queries ---


@pytest.mark.asyncio
async def test_run_query_readonly_appends_message(mocker):
    """Successful SELECT in read-only mode appends a note about uncommitted changes."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mock_conn.execute_query = AsyncMock(return_value=[{'ID': 1, 'NAME': 'Alice'}])
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='SELECT * FROM HR.EMPLOYEES',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert 'MCP server is in read-only mode' in result
    assert 'will NOT be committed' in result


# --- max_rows truncation ---


@pytest.mark.asyncio
async def test_run_query_truncates_large_results(mocker):
    """Results exceeding max_rows are truncated with a note."""
    from awslabs.oracle_mcp_server.server import run_query

    server_config.max_rows = 5

    mock_conn = MagicMock()
    mock_conn.readonly_query = False
    # execute_query returns max_rows + 1 rows (6 > 5)
    mock_conn.execute_query = AsyncMock(return_value=[{'ID': i} for i in range(6)])
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='SELECT * FROM big_table',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert 'truncated to 5 rows' in result


@pytest.mark.asyncio
async def test_run_query_no_truncation_within_limit(mocker):
    """Results within max_rows are not truncated."""
    from awslabs.oracle_mcp_server.server import run_query

    server_config.max_rows = 10

    mock_conn = MagicMock()
    mock_conn.readonly_query = False
    mock_conn.execute_query = AsyncMock(return_value=[{'ID': i} for i in range(5)])
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()
    result = await run_query(
        sql='SELECT * FROM small_table',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='endpoint1',
        database='ORCL',
    )
    assert 'truncated' not in result


# --- connect_to_database ---


@pytest.mark.asyncio
async def test_connect_to_database_success(mocker):
    """Successful connection returns the LLM response dict."""
    from awslabs.oracle_mcp_server.server import connect_to_database

    mock_pool_conn = MagicMock(spec=OracledbPoolConnection)
    mock_pool_conn.initialize_pool = AsyncMock()

    llm_response = {
        'connection_method': ConnectionMethod.ORACLE_PASSWORD,
        'instance_identifier': 'inst1',
        'db_endpoint': 'ep1',
        'database': 'ORCL',
        'port': 1521,
        'service_name': 'ORCL',
        'sid': None,
    }

    mocker.patch(
        'awslabs.oracle_mcp_server.server.internal_create_connection',
        return_value=(mock_pool_conn, llm_response, None),
    )

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        instance_identifier='inst1',
        service_name='ORCL',
    )

    assert result == llm_response
    mock_pool_conn.initialize_pool.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_to_database_both_service_and_sid():
    """Both service_name and sid returns an error."""
    from awslabs.oracle_mcp_server.server import connect_to_database

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        service_name='ORCL',
        sid='ORCL',
    )
    assert result['status'] == 'Failed'
    assert 'not both' in result['error']


@pytest.mark.asyncio
async def test_connect_to_database_neither_service_nor_sid():
    """Neither service_name nor sid returns an error."""
    from awslabs.oracle_mcp_server.server import connect_to_database

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
    )
    assert result['status'] == 'Failed'
    assert 'must be provided' in result['error']


@pytest.mark.asyncio
async def test_connect_to_database_pool_init_failure(mocker):
    """Pool initialization failure removes connection from map and returns error."""
    from awslabs.oracle_mcp_server.server import connect_to_database

    mock_pool_conn = MagicMock(spec=OracledbPoolConnection)
    mock_pool_conn.initialize_pool = AsyncMock(side_effect=Exception('pool init failed'))

    mocker.patch(
        'awslabs.oracle_mcp_server.server.internal_create_connection',
        return_value=(mock_pool_conn, {}, None),
    )
    remove_mock = mocker.patch.object(db_connection_map, 'remove')

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        instance_identifier='inst1',
        service_name='ORCL',
    )

    assert result['status'] == 'Failed'
    assert 'pool init failed' in result['error']
    remove_mock.assert_called_once()


@pytest.mark.asyncio
async def test_connect_to_database_closes_replaced_connection(mocker):
    """Replaced connection is closed when secret_arn changes."""
    from awslabs.oracle_mcp_server.server import connect_to_database

    replaced_conn = AsyncMock()
    mock_pool_conn = MagicMock(spec=OracledbPoolConnection)
    mock_pool_conn.initialize_pool = AsyncMock()

    mocker.patch(
        'awslabs.oracle_mcp_server.server.internal_create_connection',
        return_value=(mock_pool_conn, {}, replaced_conn),
    )

    await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        service_name='ORCL',
    )

    replaced_conn.close.assert_awaited_once()


# --- internal_create_connection ---


def test_internal_create_connection_returns_existing(mocker):
    """Returns existing connection without creating a new one."""
    mock_conn = MagicMock()
    mock_conn.secret_arn = 'arn:test'  # pragma: allowlist secret
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    conn, response, replaced = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        port=1521,
        database='ORCL',
        service_name='ORCL',
        secret_arn='arn:test',  # pragma: allowlist secret
    )

    assert conn is mock_conn
    assert replaced is None


def test_internal_create_connection_replaces_on_secret_change(mocker):
    """Replaces existing connection when secret_arn changes."""
    old_conn = MagicMock()
    old_conn.secret_arn = 'arn:old'  # pragma: allowlist secret
    mocker.patch.object(db_connection_map, 'get', return_value=old_conn)
    mock_remove = mocker.patch.object(db_connection_map, 'remove')
    mocker.patch.object(db_connection_map, 'set')

    conn, response, replaced = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        port=1521,
        database='ORCL',
        service_name='ORCL',
        secret_arn='arn:new',  # pragma: allowlist secret
    )

    assert replaced is old_conn
    assert isinstance(conn, OracledbPoolConnection)
    mock_remove.assert_called_once()


def test_internal_create_connection_uses_default_secret_arn(mocker):
    """Falls back to default_secret_arn when no explicit secret_arn is given."""
    server_config.default_secret_arn = 'arn:default'  # pragma: allowlist secret
    mocker.patch.object(db_connection_map, 'get', return_value=None)
    mocker.patch.object(db_connection_map, 'set')

    conn, response, replaced = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='inst1',
        db_endpoint='ep1',
        port=1521,
        database='ORCL',
        service_name='ORCL',
    )

    assert isinstance(conn, OracledbPoolConnection)
    assert conn.secret_arn == 'arn:default'  # pragma: allowlist secret


def test_internal_create_connection_missing_region():
    """Raises ValueError when region is empty."""
    with pytest.raises(ValueError, match='region'):
        internal_create_connection(
            region='',
            connection_method=ConnectionMethod.ORACLE_PASSWORD,
            instance_identifier='inst1',
            db_endpoint='ep1',
            port=1521,
            database='ORCL',
            service_name='ORCL',
        )


# --- main() ---


def test_main_sets_server_config(mocker):
    """main() parses args and configures server_config."""
    from awslabs.oracle_mcp_server import server as server_module

    mocker.patch(
        'sys.argv',
        [
            'prog',
            '--allow_write_query',
            '--port',
            '2484',
            '--ssl_encryption',
            'noverify',
            '--max_rows',
            '500',
        ],
    )
    mock_mcp = mocker.patch.object(server_module, 'mcp')

    server_module.main()

    assert server_module.server_config.readonly_query is False
    assert server_module.server_config.configured_port == 2484
    assert server_module.server_config.ssl_encryption_mode == 'noverify'
    assert server_module.server_config.max_rows == 500
    mock_mcp.run.assert_called_once()


def test_main_startup_connection_validation(mocker):
    """main() validates connection at startup using validate_sync()."""
    from awslabs.oracle_mcp_server import server as server_module

    mock_pool_conn = MagicMock(spec=OracledbPoolConnection)
    mock_pool_conn.validate_sync = MagicMock()

    mocker.patch(
        'sys.argv',
        [
            'prog',
            '--connection_method',
            'ORACLE_PASSWORD',
            '--db_endpoint',
            'myhost.rds.amazonaws.com',
            '--region',
            'us-east-1',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:test',
        ],
    )
    mocker.patch.object(server_module, 'mcp')
    mocker.patch(
        'awslabs.oracle_mcp_server.server.internal_create_connection',
        return_value=(mock_pool_conn, {}, None),
    )

    server_module.main()

    mock_pool_conn.validate_sync.assert_called_once()


# --- rollback in read-only mode for non-result queries ---


@pytest.mark.asyncio
async def test_execute_query_readonly_rollback_no_cursor_description():
    """In read-only mode, rollback is called even when cursor.description is None."""
    conn_obj = OracledbPoolConnection(
        host='localhost',
        port=1521,
        database='ORCL',
        readonly=True,
        secret_arn='arn:aws:secretsmanager:us-west-2:123456789:secret:test',  # pragma: allowlist secret
        region='us-west-2',
        service_name='ORCL',
        is_test=True,
    )

    mock_cursor = MagicMock()
    mock_cursor.description = None
    mock_cursor.execute = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.rollback = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn_obj.pool = mock_pool
    conn_obj.created_time = __import__('datetime').datetime.now()

    result = await conn_obj.execute_query('SELECT 1 FROM DUAL')

    mock_conn.rollback.assert_awaited_once()
    mock_conn.commit.assert_not_awaited()
    assert result == []
