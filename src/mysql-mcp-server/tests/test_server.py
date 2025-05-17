# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the MySQL MCP Server."""

import asyncio
import datetime
import decimal
import json
import pytest
import sys
import uuid
from awslabs.mysql_mcp_server.mutable_sql_detector import (
    QueryType,
    check_sql_injection_risk,
    classify_query,
)
from awslabs.mysql_mcp_server.server import DBConnectionSingleton, main, run_query
from conftest import DummyCtx, Mock_DBConnection


def wrap_value(val):
    """Convert a Python value into an AWS RDS Data API-compatible field dict."""
    if isinstance(val, str):
        return {'stringValue': val}
    elif isinstance(val, bool):
        return {'booleanValue': val}
    elif isinstance(val, int):
        return {'longValue': val}
    elif isinstance(val, float):
        return {'doubleValue': val}
    elif isinstance(val, decimal.Decimal):
        return {'stringValue': str(val)}
    elif isinstance(val, uuid.UUID):
        return {'stringValue': str(val)}
    elif isinstance(val, datetime.datetime):
        return {'stringValue': val.isoformat()}
    elif isinstance(val, datetime.date):
        return {'stringValue': val.isoformat()}
    elif isinstance(val, datetime.time):
        return {'stringValue': val.isoformat()}
    elif isinstance(val, list):
        return {'arrayValue': {'stringValues': [str(v) for v in val]}}
    elif isinstance(val, dict):
        return {'stringValue': json.dumps(val)}
    elif val is None:
        return {'isNull': True}
    else:
        raise TypeError(f'Unsupported value type: {type(val)}')


def mock_execute_statement_response(
    columns: list[str],
    rows: list[list],
    number_of_records_updated: int = 0,
    generated_fields: list | None = None,
):
    """Generate a complete mock RDS Data API response from a SQL query."""
    return {
        'columnMetadata': [
            {
                'name': col,
                'label': col,
                'typeName': 'text',  # simplified for mocking
                'nullable': True,
                'isSigned': False,
                'arrayBaseColumnType': 0,
                'scale': 0,
                'precision': 0,
                'type': 12,  # JDBC type for VARCHAR
            }
            for col in columns
        ],
        'records': [[wrap_value(cell) for cell in row] for row in rows],
        'numberOfRecordsUpdated': number_of_records_updated,
        'generatedFields': generated_fields if generated_fields is not None else [],
        'formattedRecords': '',
        'responseMetadata': {
            'RequestId': 'mock-request-id',
            'HTTPStatusCode': 200,
            'HTTPHeaders': {
                'content-type': 'application/x-amz-json-1.1',
                'x-amzn-requestid': 'mock-request-id',
                'content-length': '123',
            },
            'RetryAttempts': 0,
        },
    }


@pytest.mark.asyncio
async def test_run_query_well_formatted_response():
    """Test that run_query correctly handles a well-formatted response from MySQL."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(True)

    columns = [
        'text_column',
        'tinyint_column',  # Changed from boolean
        'int_column',  # Changed from integer
        'double_column',  # Changed from float
        'decimal_column',  # Changed from numeric
        'varchar_column',  # Changed from uuid
        'datetime_column',  # Changed from timestamp
        'date_column',
        'time_column',
        'text_column_list',  # Changed from text_array
        'json_column',
        'null_column',
    ]

    row = [
        'Hello world',  # VARCHAR/TEXT
        1,  # TINYINT (0 or 1 for boolean)
        123,  # INT
        45.67,  # DOUBLE
        decimal.Decimal('12345.6789'),  # DECIMAL
        '550e8400-e29b-41d4-a716-446655440000',  # VARCHAR
        datetime.datetime(2023, 1, 1, 12, 0),  # DATETIME
        datetime.date(2023, 1, 1),  # DATE
        datetime.time(14, 30),  # TIME
        'one,two,three',  # TEXT (comma-separated as MySQL doesn't have array type)
        json.dumps({'key': 'value', 'flag': True}),  # JSON
        None,  # NULL
    ]

    sql_text = 'SELECT * FROM example_table'
    response = mock_execute_statement_response(columns=columns, rows=[row])

    ctx = DummyCtx()
    mock_db_connection.data_client.add_mock_response(response)
    tool_response = await run_query(sql_text, ctx, mock_db_connection)

    # validate tool_response
    assert (
        isinstance(tool_response, (list, tuple))
        and len(tool_response) == 1
        and isinstance(tool_response[0], dict)
    )
    column_records = tool_response[0]
    assert len(column_records) == len(columns)
    for col_name in columns:
        assert col_name in column_records


@pytest.mark.asyncio
async def test_run_query_bad_rds_response():
    """Test that run_query handles malformed responses from RDS Data API appropriately."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)

    mock_db_connection = Mock_DBConnection(True)
    sql_text = r"""SELECT 1"""

    response = [{'bad': 'bad'}]
    mock_db_connection.data_client.add_mock_response(response)

    ctx = DummyCtx()
    with pytest.raises(RuntimeError):
        await run_query(sql_text, ctx, mock_db_connection)


@pytest.mark.asyncio
async def test_run_query_risky_parameters():
    """Test that run_query rejects queries with potentially risky parameters."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(True)

    sql_text = r"""SELECT 1"""
    query_parameters = [{'name': 'id', 'value': {'stringValue': '1 OR 1=1'}}]

    ctx = DummyCtx()
    with pytest.raises(RuntimeError):
        await run_query(sql_text, ctx, mock_db_connection, query_parameters)


@pytest.mark.asyncio
async def test_run_query_throw_client_error():
    """Test that run_query properly handles client errors from RDS Data API."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(True, True)
    sql_text = r"""SELECT 1"""

    ctx = DummyCtx()
    with pytest.raises(RuntimeError):
        await run_query(sql_text, ctx, mock_db_connection)


@pytest.mark.asyncio
async def test_run_query_write_prohibited():
    """Test that run_query rejects write queries when in read-only mode."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)

    # Set readonly to be true and send write query
    mock_db_connection = Mock_DBConnection(True)

    sql_text = r"""WITH new_users AS (
        SELECT * FROM staging_users WHERE is_valid = true
    )
    INSERT INTO users (id, name, email)
    SELECT id, name, email FROM new_users
    RETURNING id;"""

    ctx = DummyCtx()
    with pytest.raises(RuntimeError):
        await run_query(sql_text, ctx, mock_db_connection)

    # Set readonly to be false and send write query
    mock_db_connection2 = Mock_DBConnection(False)

    columns = [
        'text_column',
        'boolean_column',
        'integer_column',
        'float_column',
        'numeric_column',
        'uuid_column',
        'timestamp_column',
        'date_column',
        'time_column',
        'text_array_column',
        'json_column',
        'null_column',
    ]

    row = [
        'Hello world',  # TEXT
        True,  # BOOLEAN
        123,  # INTEGER
        45.67,  # FLOAT
        decimal.Decimal('12345.6789'),  # NUMERIC
        uuid.uuid4(),  # UUID
        datetime.datetime(2023, 1, 1, 12, 0),  # TIMESTAMP
        datetime.date(2023, 1, 1),  # DATE
        datetime.time(14, 30),  # TIME
        ['one', 'two', 'three'],  # TEXT[]
        {'key': 'value', 'flag': True},  # JSON
        None,  # NULL
    ]

    response = mock_execute_statement_response(columns=columns, rows=[row])

    mock_db_connection2.data_client.add_mock_response(response)
    tool_response = await run_query(sql_text, ctx, mock_db_connection2)

    # validate tool_response
    assert (
        isinstance(tool_response, (list, tuple))
        and len(tool_response) == 1
        and isinstance(tool_response[0], dict)
    )
    column_records = tool_response[0]
    assert len(column_records) == len(columns)
    for col_name in columns:
        assert col_name in column_records


def test_detect_non_mutating_keywords():
    """Test that detect_mutating_keywords correctly identifies non-mutating SQL queries."""
    non_mutating_queries = [
        # Simple SELECTs
        'SELECT * FROM users;',
        'SELECT id, name FROM customers WHERE active = 1;',
        # Aggregate functions
        'SELECT department, COUNT(*) FROM employees GROUP BY department;',
        "SELECT AVG(salary) FROM employees WHERE title = 'Manager';",
        # JOINs
        'SELECT o.id, u.name FROM orders o JOIN users u ON o.user_id = u.id;',
        'SELECT * FROM products p LEFT JOIN categories c ON p.cat_id = c.id;',
        # Subqueries
        'SELECT name FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100);',
        'SELECT name, (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count FROM users u;',
        # EXISTS / NOT EXISTS
        'SELECT name FROM users WHERE EXISTS (SELECT 1 FROM logins WHERE logins.user_id = users.id);',
        'SELECT * FROM accounts a WHERE NOT EXISTS (SELECT 1 FROM bans WHERE bans.user_id = a.id);',
        # CTEs (WITH clauses)
        """
        WITH recent_orders AS (
            SELECT * FROM orders WHERE order_date > CURRENT_DATE - INTERVAL 7 DAY
        )
        SELECT u.name, r.total FROM users u JOIN recent_orders r ON u.id = r.user_id;
        """,
        # Window functions
        'SELECT id, salary, RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank FROM employees;',
        # LIMIT and ORDER
        'SELECT * FROM logs ORDER BY created_at DESC LIMIT 100;',
        # String functions
        "SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM users;",
        # Mathematical expressions
        'SELECT ROUND(price * 1.1, 2) AS adjusted_price FROM products;',
        # Date/time functions
        "SELECT DATE_FORMAT(order_date, '%Y-%m-%d') FROM orders;",
        # Safe stored function call (read-only)
        'SELECT calculate_tax(total_amount) FROM invoices;',
        # Information schema introspection
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'mydb';",
        # Prepared-like behavior
        'SELECT ? AS input_value;',
        # Reading from views
        'SELECT * FROM active_customers_view;',
    ]

    for sql in non_mutating_queries:
        qtype, clean_sql = classify_query(sql)
        assert qtype == QueryType.SAFE


def test_detect_mutating_keywords():
    """Test that detect_mutating_keywords correctly identifies mutating MySQL SQL queries."""
    ddl_test_cases = [
        'CREATE TABLE users (id INT);',
        'CREATE VIEW my_view AS SELECT * FROM users;',
        'CREATE INDEX idx_name ON users(name);',
        'CREATE TRIGGER trg AFTER INSERT ON users FOR EACH ROW SET NEW.id = 1;',
        'CREATE PROCEDURE my_proc() BEGIN SELECT 1; END;',
        'CREATE FUNCTION my_func() RETURNS INT DETERMINISTIC RETURN 1;',
        'CREATE EVENT my_event ON SCHEDULE EVERY 1 DAY DO BEGIN END;',
        'DROP TABLE users;',
        'DROP VIEW my_view;',
        'DROP INDEX idx_name ON users;',
        'DROP TRIGGER trg;',
        'DROP PROCEDURE my_proc;',
        'DROP FUNCTION my_func;',
        'DROP EVENT my_event;',
        'ALTER TABLE users ADD COLUMN age INT;',
        'ALTER VIEW my_view AS SELECT name FROM users;',
        'ALTER TRIGGER trg BEFORE INSERT ON users FOR EACH ROW SET NEW.id = 2;',
        "ALTER PROCEDURE my_proc COMMENT 'Updated';",
        "ALTER FUNCTION my_func COMMENT 'Updated';",
        'ALTER EVENT my_event DISABLE;',
        'RENAME TABLE old_name TO new_name;',
        'TRUNCATE TABLE logs;',
    ]

    for sql in ddl_test_cases:
        qtype, clean_sql = classify_query(sql)
        assert qtype == QueryType.MUTATING_DDL, (
            'failing for:' + clean_sql + ' type is:' + str(qtype)
        )

    permission_test_cases = [
        "GRANT SELECT ON db.* TO 'user';",
        "GRANT ROLE admin TO 'user';",
        "REVOKE SELECT ON db.* FROM 'user';",
        "REVOKE ROLE admin FROM 'user';",
        "CREATE USER 'user1' IDENTIFIED BY 'pwd';",
        "CREATE ROLE 'reader';",
        "DROP USER 'user1';",
        "DROP ROLE 'reader';",
        "SET DEFAULT ROLE ALL TO 'user';",
        "SET PASSWORD FOR 'user' = 'newpass';",
        "ALTER USER 'user' IDENTIFIED BY 'pwd';",
        "RENAME USER 'a' TO 'b';",
    ]

    for sql in permission_test_cases:
        qtype, clean_sql = classify_query(sql)
        assert qtype == QueryType.PERMISSION_MODIFYING, (
            'failing for:' + clean_sql + ' type is:' + str(qtype)
        )

    system_test_cases = [
        'SET GLOBAL max_connections = 300;',
        "SET PERSIST sql_mode = 'STRICT_ALL_TABLES';",
        'SET SESSION wait_timeout = 100;',
        'RESET MASTER;',
        'RESET SLAVE;',
        'RESET PERSIST;',
        'FLUSH PRIVILEGES;',
        'FLUSH HOSTS;',
        'FLUSH LOGS;',
        'FLUSH STATUS;',
        'FLUSH TABLES;',
        "INSTALL PLUGIN plugin_name SONAME 'plugin.so';",
        'UNINSTALL PLUGIN plugin_name;',
        "CHANGE MASTER TO MASTER_HOST='127.0.0.1';",
        'START SLAVE;',
        'STOP SLAVE;',
        "SET GTID_PURGED = 'uuid:1-10';",
        "PURGE BINARY LOGS TO 'log.000005';",
        "LOAD DATA INFILE 'data.csv' INTO TABLE t;",
        "SELECT * FROM t INTO OUTFILE 'output.csv';",
        'USE my_database;',
        'SET autocommit = 0;',
    ]

    for sql in system_test_cases:
        qtype, clean_sql = classify_query(sql)
        assert qtype == QueryType.SYSTEM_MODIFYING


def test_safe_param():
    """Test that check_sql_injection_risk accepts safe parameter values."""
    params = [{'name': 'id', 'value': {'stringValue': '123'}}]
    result = check_sql_injection_risk(params)
    assert result == []


def test_none_parameters_should_be_safe():
    """Test that check_sql_injection_risk handles None parameters safely."""
    params = None
    result = check_sql_injection_risk(params)
    assert result == []


def test_or_true_clause_in_param():
    """Test that check_sql_injection_risk detects OR 1=1 injection attempts."""
    params = [{'name': 'id', 'value': {'stringValue': '1 OR 1=1'}}]
    result = check_sql_injection_risk(params)
    assert any('1 OR 1=1' in r['message'] for r in result), 'result is ' + str(result)


def test_union_select_in_param():
    """Test that check_sql_injection_risk detects UNION SELECT injection attempts."""
    params = [{'name': 'name', 'value': {'stringValue': "' UNION SELECT * FROM passwords -- "}}]
    result = check_sql_injection_risk(params)
    assert any('union' in r['message'].lower() for r in result)


def test_semicolon_in_param():
    """Test that check_sql_injection_risk detects semicolon-based injection attempts."""
    params = [{'name': 'id', 'value': {'stringValue': '1; DROP TABLE users;'}}]
    result = check_sql_injection_risk(params)
    assert any(';' in r['message'] for r in result)


def test_multiple_risks_in_param():
    """Test that check_sql_injection_risk detects multiple injection patterns in a single parameter."""
    params = [{'name': 'id', 'value': {'stringValue': "'; DROP TABLE users -- "}}]
    result = check_sql_injection_risk(params)
    assert len(result) == 1
    assert result[0]['type'] == 'parameter'
    assert 'drop' in result[0]['message'].lower()


def test_mysql_specific_injection():
    """Test MySQL-specific injection patterns."""
    params = [{'name': 'id', 'value': {'stringValue': "1 INTO OUTFILE '/tmp/hack'"}}]
    result = check_sql_injection_risk(params)

    assert any('outfile' in r['message'].lower() for r in result)


def test_mysql_comment_injection_executable_block():
    """Test MySQL-specific executable comment injection (/*! ... */)."""
    params = [{'name': 'id', 'value': {'stringValue': '1 /*! DROP TABLE users */'}}]
    result = check_sql_injection_risk(params)
    assert any(
        'comment' in r['message'].lower() or 'drop' in r['message'].lower() for r in result
    ), 'Expected detection of executable block comment injection'


def test_mysql_comment_injection_double_dash():
    """Test MySQL '--' comment injection."""
    params = [{'name': 'id', 'value': {'stringValue': '1 -- DROP TABLE users'}}]
    result = check_sql_injection_risk(params)
    assert any('--' in r['message'] or 'comment' in r['message'].lower() for r in result), (
        'Expected detection of -- comment injection'
    )


def test_mysql_comment_injection_hash():
    """Test MySQL '#' comment injection."""
    params = [{'name': 'id', 'value': {'stringValue': '1 # DROP TABLE users'}}]
    result = check_sql_injection_risk(params)
    assert any('#' in r['message'] or 'comment' in r['message'].lower() for r in result), (
        'Expected detection of # comment injection'
    )


def test_or_string_comparison_injection():
    """Test 'OR 'a'='a' type injection."""
    params = [{'name': 'id', 'value': {'stringValue': "' OR 'a'='a"}}]
    result = check_sql_injection_risk(params)
    assert any("OR 'a'='a" in r['message'] for r in result)


def test_sleep_injection():
    """Test SLEEP() injection attempt."""
    params = [{'name': 'id', 'value': {'stringValue': '1; SELECT SLEEP(10);'}}]
    result = check_sql_injection_risk(params)
    assert any('sleep' in r['message'].lower() for r in result)


def test_load_file_injection():
    """Test LOAD_FILE() injection attempt."""
    params = [{'name': 'id', 'value': {'stringValue': "1 UNION SELECT LOAD_FILE('/etc/passwd')"}}]
    result = check_sql_injection_risk(params)
    assert any('load_file' in r['message'].lower() for r in result)


def test_main_with_valid_parameters(monkeypatch, capsys):
    """Test main function with valid command line parameters.

    This test verifies that the main function correctly parses valid command line arguments
    and attempts to initialize the database connection. The test expects a SystemExit
    since we're not using real AWS credentials.

    Args:
        monkeypatch: pytest fixture for patching
        capsys: pytest fixture for capturing stdout/stderr
    """
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'server.py',
            '--resource_arn',
            'arn:aws:rds:us-west-2:123456789012:cluster:example-cluster-name',
            '--secret_arn',
            'arn:aws:secretsmanager:us-west-2:123456789012:secret:my-secret-name-abc123',
            '--database',
            'mysql',
            '--region',
            'us-west-2',
            '--readonly',
            'True',
        ],
    )
    monkeypatch.setattr('awslabs.mysql_mcp_server.server.mcp.run', lambda: None)

    # This test of main() will succeed in parsing parameters and create connection object.
    # However, since connection object is not boto3 client with real credential, the validate of connection will fail and cause system exit
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_main_with_invalid_parameters(monkeypatch, capsys):
    """Test main function with invalid command line parameters.

    This test verifies that the main function correctly handles invalid command line arguments
    and exits with an error code. The test expects a SystemExit since the parameters
    are invalid and we're not using real AWS credentials.

    Args:
        monkeypatch: pytest fixture for patching
        capsys: pytest fixture for capturing stdout/stderr
    """
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'server.py',
            '--resource_arn',
            'invalid',
            '--secret_arn',
            'invalid',
            '--database',
            'mysql',
            '--region',
            'invalid',
            '--readonly',
            'True',
        ],
    )
    monkeypatch.setattr('awslabs.mysql_mcp_server.server.mcp.run', lambda: None)

    # This test of main() will succeed in parsing parameters and create connection object.
    # However, since connection object is not boto3 client with real credential, the validate of connection will fail and cause system exit
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


if __name__ == '__main__':
    test_detect_non_mutating_keywords()
    test_detect_mutating_keywords()
    test_safe_param()
    test_none_parameters_should_be_safe()
    test_or_true_clause_in_param()
    test_union_select_in_param()
    test_semicolon_in_param()
    test_multiple_risks_in_param()
    test_mysql_comment_injection_executable_block()
    test_mysql_comment_injection_double_dash
    test_mysql_comment_injection_hash

    test_or_string_comparison_injection()
    test_sleep_injection()
    test_load_file_injection()

    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    asyncio.run(test_run_query_well_formatted_response())
    asyncio.run(test_run_query_bad_rds_response())
    asyncio.run(test_run_query_write_prohibited())
    asyncio.run(test_run_query_risky_parameters())
    asyncio.run(test_run_query_throw_client_error())
