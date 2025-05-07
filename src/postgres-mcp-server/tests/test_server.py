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
"""Tests for the postgres MCP Server."""

import asyncio
import datetime
import decimal
import json
import pytest
import uuid
from awslabs.postgres_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)
from awslabs.postgres_mcp_server.server import (
    DBConnectionSingleton,
    run_query,
)
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
    generated_fields: list = None,
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
        'generatedFields': generated_fields or [],
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
    """Test that run_query correctly handles a well-formatted response from RDS Data API."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(True)

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
    allowed_sqls = [
        r"""-- Select with join]
        SELECT u.id, u.name, o.order_date, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE o.total > 100
        ORDER BY o.order_date DESC
        LIMIT 10;""",
        r"""-- Aggregation with GROUP BY and HAVING
        SELECT department_id, COUNT(*) AS employee_count, AVG(salary) AS avg_salary
        FROM employees
        GROUP BY department_id
        HAVING COUNT(*) > 5;""",
        r"""-- Subquery in WHERE UPDATE
        SELECT *
        FROM products
        WHERE price < (
            SELECT AVG(price)
            FROM products
        );""",
        r"""-- CTE and Window Function
        WITH ranked_orders AS (
            SELECT
                o.*,
                RANK() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS rank
            FROM orders o
        )
        SELECT *
        FROM ranked_orders
        WHERE rank = 1;""",
        r"""-- EXISTS with correlated subquery
        SELECT name
        FROM customers c
        WHERE EXISTS (
            SELECT 1
            FROM orders o
            WHERE o.customer_id = c.id
            AND o.status = 'shipped'
        );""",
        r"""-- Subquery in FROM clause (derived table)
        SELECT avg_by_category.category_id, avg_by_category.avg_price
        FROM (
            SELECT category_id, AVG(price) AS avg_price
            FROM products
            GROUP BY category_id
        ) AS avg_by_category
        WHERE avg_price > 50;""",
        r"""-- SELECT with CASE expression
        SELECT
            id,
            name,
            CASE
                WHEN score >= 90 THEN 'A'
                WHEN score >= 80 THEN 'B'
                WHEN score >= 70 THEN 'C'
                ELSE 'F'
            END AS grade
        FROM students;""",
        r"""-- Windowed aggregates with ROW_NUMBER
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
        FROM employees;""",
        r"""-- IN and BETWEEN usage
        SELECT *
        FROM sales
        WHERE region IN ('North', 'South')
        AND sale_date BETWEEN '2023-01-01' AND '2023-12-31';""",
        r"""-- Pattern match with LIKE
        SELECT name
        FROM customers
        WHERE email LIKE '%@gmail.com';""",
        r"""SELECT 'This is not a real DELETE statement' AS example;""",
        r"""SELECT "DROP" FROM actions;""",
        r"""SELECT * FROM logs WHERE message LIKE '%CREATE TABLE%';""",
        r"""SELECT json_extract_path_text(payload, 'DROP TABLE users') FROM logs;""",
        r"""SELECT 1 /* DROP TABLE abc */;""",
        r"""-- DELETE FROM customers;
        SELECT * FROM customers;""",
    ]

    for sql in allowed_sqls:
        assert not detect_mutating_keywords(sql)


def test_detect_mutating_keywords():
    """Test that detect_mutating_keywords correctly identifies mutating SQL queries."""
    test_sqls = [
        # DML
        r"""WITH new_users AS (
        SELECT * FROM staging_users WHERE is_valid = true
    )
    INSERT INTO users (id, name, email)
    SELECT id, name, email FROM new_users
    RETURNING id;""",
        r"""UPDATE orders
    SET status = 'shipped'
    WHERE id IN (
        SELECT order_id FROM shipping_queue WHERE priority = 'high'
    )
    RETURNING id;""",
        r"""WITH old_logs AS (
        SELECT id FROM logs WHERE created_at < NOW() - INTERVAL '30 days'
    )
    DELETE FROM logs WHERE id IN (SELECT id FROM old_logs);""",
        # DDL
        r"""CREATE TABLE IF NOT EXISTS archive_data AS
    SELECT * FROM data WHERE created_at < NOW() - INTERVAL '1 year';""",
        r"""DROP TABLE IF EXISTS temp_data, old_archive CASCADE;""",
        r"""ALTER TABLE users
    ADD COLUMN last_login TIMESTAMP,
    ALTER COLUMN email SET NOT NULL;""",
        # Functions & Procedural
        r"""CREATE FUNCTION log_activity() RETURNS trigger AS $$
    BEGIN
    INSERT INTO activity_log(user_id, action) VALUES (NEW.id, 'inserted');
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;""",
        r"""DROP FUNCTION IF EXISTS log_activity();""",
        # Permissions
        r"""GRANT SELECT, INSERT ON orders TO analyst_role;""",
        r"""REVOKE ALL ON users FROM guest_role;""",
        # Index & View Management
        r"""CREATE INDEX IF NOT EXISTS idx_users_active ON users (last_login) WHERE is_active = true;""",
        r"""DROP INDEX IF EXISTS idx_users_active;""",
        r"""REINDEX TABLE users;""",
        r"""CREATE VIEW vip_customers AS
    SELECT * FROM customers WHERE loyalty_tier = 'Platinum';""",
        r"""DROP VIEW IF EXISTS vip_customers CASCADE;""",
        r"""CREATE MATERIALIZED VIEW recent_signups AS
    SELECT * FROM users WHERE created_at > CURRENT_DATE - INTERVAL '30 days';""",
        r"""DROP MATERIALIZED VIEW IF EXISTS recent_signups;""",
        # Sequences
        r"""CREATE SEQUENCE user_id_seq START 1000 INCREMENT 5;""",
        r"""ALTER SEQUENCE user_id_seq RESTART WITH 5000;""",
        r"""DROP SEQUENCE IF EXISTS user_id_seq;""",
        # Types & Domains
        r"""CREATE TYPE currency AS ENUM ('USD', 'EUR', 'JPY');""",
        r"""DROP TYPE IF EXISTS currency;""",
        r"""CREATE DOMAIN us_phone_number AS TEXT CHECK (VALUE ~ '^\\(\\d{3}\\) \\d{3}-\\d{4}$');""",
        r"""DROP DOMAIN IF EXISTS us_phone_number;""",
        # Schemas & Aggregates
        r"""CREATE SCHEMA reporting;""",
        r"""DROP SCHEMA IF EXISTS reporting CASCADE;""",
        r"""CREATE AGGREGATE product_sum (sfunc = int4mul, basetype = int, stype = int);""",
        r"""DROP AGGREGATE IF EXISTS product_sum(int);""",
        # Roles & Users
        r"""CREATE ROLE data_analyst LOGIN PASSWORD 'an@lyt1c';""",  # pragma: allowlist secret
        r"""ALTER ROLE data_analyst SET search_path = analytics, public;""",  # pragma: allowlist secret
        r"""DROP ROLE IF EXISTS data_analyst;""",
        r"""CREATE USER batch_processor WITH PASSWORD 'proc123';""",  # pragma: allowlist secret
        r"""DROP USER IF EXISTS batch_processor;""",
        # PL & Procedures
        r"""CREATE PROCEDURE cleanup_old_data() LANGUAGE plpgsql AS $$
    BEGIN
    DELETE FROM logs WHERE created_at < NOW() - INTERVAL '6 months';
    END;
    $$;""",
        r"""DROP PROCEDURE IF EXISTS cleanup_old_data();""",
        r"""CREATE LANGUAGE IF NOT EXISTS plpython3u;""",
        r"""DROP LANGUAGE IF EXISTS plpython3u;""",
        # Extensions
        r"""CREATE EXTENSION IF NOT EXISTS pg_trgm;""",
        r"""DROP EXTENSION IF EXISTS pg_trgm;""",
        r"""ALTER EXTENSION pg_trgm UPDATE;""",
        # Runtime & Config
        r"""ALTER SYSTEM SET shared_buffers = '512MB';""",
        # Security
        r"""SECURITY LABEL FOR selinux ON FUNCTION log_activity IS 'system_u:object_r:sepgsql_proc_exec_t:s0';""",
    ]

    for sql in test_sqls:
        assert detect_mutating_keywords(sql)


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
    assert any('1 OR 1=1' in r['message'] for r in result)


def test_union_select_in_param():
    """Test that check_sql_injection_risk detects UNION SELECT injection attempts."""
    params = [{'name': 'name', 'value': {'stringValue': "' UNION SELECT * FROM passwords --"}}]
    result = check_sql_injection_risk(params)
    assert any('union' in r['message'].lower() for r in result)


def test_semicolon_in_param():
    """Test that check_sql_injection_risk detects semicolon-based injection attempts."""
    params = [{'name': 'id', 'value': {'stringValue': '1; DROP TABLE users;'}}]
    result = check_sql_injection_risk(params)
    assert any(';' in r['message'] for r in result)


def test_multiple_risks_in_param():
    """Test that check_sql_injection_risk detects multiple injection patterns in a single parameter."""
    params = [{'name': 'id', 'value': {'stringValue': "'; DROP TABLE users --"}}]
    result = check_sql_injection_risk(params)
    assert len(result) == 1
    assert result[0]['type'] == 'parameter'
    assert 'drop' in result[0]['message'].lower()


if __name__ == '__main__':
    test_detect_non_mutating_keywords()
    test_detect_mutating_keywords()
    test_safe_param()
    test_none_parameters_should_be_safe()
    test_or_true_clause_in_param()
    test_union_select_in_param()
    test_semicolon_in_param()
    test_multiple_risks_in_param()

    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    asyncio.run(test_run_query_well_formatted_response())
    asyncio.run(test_run_query_write_prohibited())
    asyncio.run(test_run_query_risky_parameters())
    asyncio.run(test_run_query_throw_client_error())
