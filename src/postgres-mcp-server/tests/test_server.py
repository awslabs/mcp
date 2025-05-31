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
import sys
import uuid
from awslabs.postgres_mcp_server.server import (
    DBConnectionSingleton,
    client_error_code_key,
    get_table_schema,
    main,
    run_query,
    unexpected_error_key,
    write_query_prohibited_key,
)
from conftest import DummyCtx, Mock_DBConnection, MockException


SAFE_READONLY_QUERIES = [
    # Basic SELECT Queries
    # 1a. Simple SELECT
    'SELECT * FROM employees',
    # 1b. Simple SELECT with trailing semicolon
    'SELECT * FROM employees;',
    # 1c. Simple SELECT with trailing semicolon and comment
    'SELECT * FROM employees; -- This is a comment',
    # 1d. Simple SELECT with trailing semicolon and multi line comment
    'SELECT * FROM employees; /* This is a comment */',
    # 2. SELECT with WHERE
    """SELECT first_name, last_name, salary
        FROM employees
        WHERE salary > 50000""",
    # 3. SELECT with multiple conditions
    """SELECT product_name, unit_price, category_id
    FROM products
    WHERE unit_price > 20 AND category_id IN (1, 2, 3)""",
    # 4. SELECT with ORDER BY and LIMIT
    """SELECT customer_id, order_date, total_amount
        FROM orders
        ORDER BY order_date DESC
        LIMIT 10""",
    # Aggregate Functions
    # 5. Basic aggregation
    """SELECT
        department_id,
        COUNT(*) as employee_count,
        AVG(salary) as avg_salary,
        MAX(salary) as max_salary
    FROM employees
    GROUP BY department_id""",
    # 6. Having clause
    """SELECT
        category_id,
        COUNT(*) as product_count,
        AVG(unit_price) as avg_price
    FROM products
    GROUP BY category_id
    HAVING COUNT(*) > 10""",
    # JOINs
    # 7. INNER JOIN
    """SELECT
        o.order_id,
        c.customer_name,
        o.order_date
    FROM orders o
    INNER JOIN customers c ON o.customer_id = c.customer_id""",
    # 8. Multiple JOINs
    """SELECT
        o.order_id,
        c.customer_name,
        p.product_name,
        oi.quantity
    FROM orders o
    INNER JOIN customers c ON o.customer_id = c.customer_id
    INNER JOIN order_items oi ON o.order_id = oi.order_id
    INNER JOIN products p ON oi.product_id = p.product_id""",
    # Subqueries
    # 9. Subquery in WHERE
    """SELECT employee_id, first_name, salary
    FROM employees
    WHERE salary > (
        SELECT AVG(salary)
        FROM employees
    )""",
    # 10. Subquery in SELECT
    """SELECT
        department_id,
        department_name,
        (SELECT COUNT(*)
        FROM employees e
        WHERE e.department_id = d.department_id) as employee_count
    FROM departments d""",
    # 11. Subquery in FROM
    """SELECT
        dept_summary.department_id,
        dept_summary.avg_salary
    FROM (
        SELECT
            department_id,
            AVG(salary) as avg_salary
        FROM employees
        GROUP BY department_id
    ) dept_summary
    WHERE dept_summary.avg_salary > 60000""",
    # Common Table Expressions (CTEs)
    # 12. Simple CTE
    """WITH employee_stats AS (
        SELECT
            department_id,
            COUNT(*) as emp_count,
            AVG(salary) as avg_salary
        FROM employees
        GROUP BY department_id
    )
    SELECT
        d.department_name,
        es.emp_count,
        es.avg_salary
    FROM employee_stats es
    JOIN departments d ON es.department_id = d.department_id""",
    # 13. Multiple CTEs
    """WITH dept_stats AS (
        SELECT
            department_id,
            COUNT(*) as emp_count
        FROM employees
        GROUP BY department_id
    ),
    salary_stats AS (
        SELECT
            department_id,
            AVG(salary) as avg_salary
        FROM employees
        GROUP BY department_id
    )
    SELECT
        d.department_name,
        ds.emp_count,
        ss.avg_salary
    FROM departments d
    JOIN dept_stats ds ON d.department_id = ds.department_id
    JOIN salary_stats ss ON d.department_id = ss.department_id""",
    # 14. Recursive CTE
    """WITH RECURSIVE employee_hierarchy AS (
        SELECT
            employee_id,
            first_name,
            manager_id,
            1 as level
        FROM employees
        WHERE manager_id IS NULL

        UNION ALL

        SELECT
            e.employee_id,
            e.first_name,
            e.manager_id,
            eh.level + 1
        FROM employees e
        INNER JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
    )
    SELECT * FROM employee_hierarchy""",
    # 15. Complex Query combining multiple concepts
    """WITH monthly_sales AS (
        SELECT
            DATE_TRUNC('month', order_date) as month,
            SUM(total_amount) as total_sales
        FROM orders
        GROUP BY DATE_TRUNC('month', order_date)
    ),
    sales_stats AS (
        SELECT
            month,
            total_sales,
            LAG(total_sales) OVER (ORDER BY month) as prev_month_sales,
            LEAD(total_sales) OVER (ORDER BY month) as next_month_sales
        FROM monthly_sales
    )
    SELECT
        month,
        total_sales,
        prev_month_sales,
        next_month_sales,
        CASE
            WHEN total_sales > prev_month_sales THEN 'Increased'
            WHEN total_sales < prev_month_sales THEN 'Decreased'
            ELSE 'No Change'
        END as sales_trend,
        ROUND(((total_sales - prev_month_sales) / prev_month_sales * 100)::numeric, 2) as growth_percentage
    FROM sales_stats
    WHERE month >= CURRENT_DATE - INTERVAL '12 months'
    ORDER BY month""",
]


SAFE_MUTATING_QUERIES = [
    # DML
    "INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@example.com')",
    "INSERT INTO logs (user_id, action) SELECT id, 'login' FROM users WHERE active = true",
    'UPDATE users SET last_login = NOW() WHERE id = 42',
    "UPDATE orders SET status = 'shipped' WHERE shipped_at IS NOT NULL AND status = 'processing'",
    'DELETE FROM sessions WHERE expires_at < NOW()',
    "INSERT INTO products (sku, name) VALUES ('abc123', 'Widget') ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name",
    'DELETE FROM cart_items WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = cart_items.user_id)',
    # DDL
    'CREATE TABLE employees (id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE)',
    'CREATE INDEX idx_orders_user_id ON orders(user_id)',
    'ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE',
    'ALTER TABLE users RENAME COLUMN fullname TO full_name',
    'CREATE VIEW active_users AS SELECT id, name FROM users WHERE active = true',
    'CREATE SEQUENCE invoice_seq START 1000 INCREMENT 1',
    "CREATE TYPE order_status AS ENUM ('pending', 'shipped', 'delivered')",
]

MUTATING_QUERIES = [
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


RISKY_QUERY_WITH_PARAMETERS = [
    {
        'sql': 'SELECT * FROM users WHERE username = :username',
        'parameters': [{'name': 'SELECT', 'value': {'stringValue': 'normal value'}}],
    },
    {
        'sql': 'SELECT * FROM users WHERE username = :username',
        'parameters': [{'name': 'username', 'value': {'stringValue': "' OR 42=42"}}],
    },
    {
        'sql': 'SELECT * FROM users WHERE username = :username',
        'parameters': [{'name': 'id', 'value': {'stringValue': '1; DROP TABLE users;'}}],
    },
    {
        'sql': 'SELECT name FROM products WHERE category = :cat',
        'parameters': [
            {'name': 'cat', 'value': {'stringValue': "' UNION SELECT password FROM users --"}}
        ],
    },
    {
        'sql': 'SELECT * FROM users ORDER BY :data',
        'parameters': [{'name': 'data', 'value': {'stringValue': '1; DROP TABLE users; --'}}],
    },
]

RISKY_QUERY_WITHOUT_PARAMETERS = [
    "SELECT * FROM users WHERE username = '' OR 1=1",
    "SELECT * FROM users WHERE username = '' -- and password = 'x'",
    'SELECT * FROM users; DROP TABLE users;',
    'SELECT id FROM users WHERE id = -1 UNION SELECT password FROM admin_users',
    "SELECT * FROM products WHERE id = (SELECT id FROM users WHERE username = '' OR '1'='1')",
    'SELECT * FROM users ORDER BY username; DROP TABLE users;',
    "WITH x AS (SELECT '--') DELETE FROM test",
    "SELECT * FROM users WHERE username = 'admin' --",
    'SELECT * FROM users WHERE id = 1 OR 1=1',
    "SELECT * FROM users WHERE username = '' OR 'x'='x'",
    'DROP TABLE users',
    'TRUNCATE TABLE logs',
    'GRANT ALL PRIVILEGES ON db TO user',
    'REVOKE SELECT ON users FROM public',
    'SELECT * FROM users WHERE id = 1 OR SLEEP(5)',
    'SELECT * FROM users WHERE id = 1 OR pg_sleep(5)',
    "SELECT load_file('/etc/passwd')",
    "SELECT * FROM users INTO OUTFILE '/tmp/users.txt'",
]

MOCK_COLUMNS = [
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

MOCK_ROWS = [
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


def get_mock_normal_query_response():
    """Generate a mock normal query response."""
    response = mock_execute_statement_response(columns=MOCK_COLUMNS, rows=[MOCK_ROWS])
    return response


def validate_normal_query_response(column_records):
    """Validate records portion of the RDS API response."""
    assert len(column_records) == len(MOCK_COLUMNS)
    for col_name in MOCK_COLUMNS:
        assert col_name in column_records


@pytest.mark.asyncio
async def test_run_query_well_formatted_response():
    """Test that run_query correctly handles a well-formatted response from RDS Data API."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=True)

    sql_text = 'SELECT * FROM example_table'

    ctx = DummyCtx()

    # Response for "SET TRANSACTION READ ONLY"
    mock_db_connection.data_client.add_mock_response({})

    # Response for the query itself
    mock_db_connection.data_client.add_mock_response(get_mock_normal_query_response())
    tool_response = await run_query(sql_text, ctx, mock_db_connection)

    # validate tool_response
    assert (
        isinstance(tool_response, (list, tuple))
        and len(tool_response) == 1
        and isinstance(tool_response[0], dict)
    )
    column_records = tool_response[0]
    validate_normal_query_response(column_records)


@pytest.mark.asyncio
async def test_run_query_safe_read_queries_on_redonly_settings():
    """Test that run_query accepts safe readonly queries when readonly setting is true."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=True)

    for sql_text in SAFE_READONLY_QUERIES:
        ctx = DummyCtx()

        # Response for "SET TRANSACTION READ ONLY"
        mock_db_connection.data_client.add_mock_response({})

        # Response for the query itself
        mock_db_connection.data_client.add_mock_response(get_mock_normal_query_response())
        tool_response = await run_query(sql_text, ctx, mock_db_connection)

        # validate tool_response
        assert (
            isinstance(tool_response, (list, tuple))
            and len(tool_response) == 1
            and isinstance(tool_response[0], dict)
            and 'error' not in tool_response[0]
        )
        column_records = tool_response[0]
        validate_normal_query_response(column_records)


@pytest.mark.asyncio
async def test_run_query_risky_queries_without_parameters():
    """Test that run_query rejects queries with potentially risky parameters regardless of readonly setting."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)

    # Under readonly = True
    mock_db_connection = Mock_DBConnection(readonly=True)

    for sql_text in RISKY_QUERY_WITHOUT_PARAMETERS:
        ctx = DummyCtx()
        response = await run_query(sql_text, ctx, mock_db_connection)
        assert len(response) == 1
        assert len(response[0]) == 1
        assert 'error' in response[0]

    # Under readonly = False
    mock_db_connection2 = Mock_DBConnection(readonly=False)

    for sql_text in RISKY_QUERY_WITHOUT_PARAMETERS:
        ctx = DummyCtx()
        response = await run_query(sql_text, ctx, mock_db_connection2)
        assert len(response) == 1
        assert len(response[0]) == 1
        assert 'error' in response[0]


@pytest.mark.asyncio
async def test_run_query_throw_client_error():
    """Test that run_query properly handles client errors from RDS Data API by mokcing the RDA API exception."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=True, error=MockException.Client)
    sql_text = r"""SELECT 1"""

    ctx = DummyCtx()
    response = await run_query(sql_text, ctx, mock_db_connection)

    assert len(response) == 1
    assert len(response[0]) == 1
    assert 'error' in response[0]
    assert response[0].get('error') == client_error_code_key


@pytest.mark.asyncio
async def test_run_query_throw_unexpected_error():
    """Test that run_query properly handles unexpected exception by mokcing the exception."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=True, error=MockException.Unexpected)
    sql_text = r"""SELECT 1"""

    ctx = DummyCtx()
    response = await run_query(sql_text, ctx, mock_db_connection)

    assert len(response) == 1
    assert len(response[0]) == 1
    assert 'error' in response[0]
    assert response[0].get('error') == unexpected_error_key


@pytest.mark.asyncio
async def test_run_query_write_queries_on_readonly_setting():
    """Test that run_query rejects write queries when in read-only mode."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)

    #    Set readonly to be true and send write query
    #    Expect  error is returned for each test query
    mock_db_connection = Mock_DBConnection(readonly=True)

    for sql_text in MUTATING_QUERIES:
        ctx = DummyCtx()
        response = await run_query(sql_text, ctx, mock_db_connection)

        # All query should fail with below signature in response
        assert len(response) == 1
        assert len(response[0]) == 1
        assert 'error' in response[0]
        assert response[0].get('error') == write_query_prohibited_key


@pytest.mark.asyncio
async def test_run_query_write_queries_on_write_allowed_setting():
    """Test that run_query accepts safe write queries when read-only setting is false."""
    #    Set readonly to be false and send write query
    #    Expect no error is returned for every test query
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=False, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=False)

    for sql_text in SAFE_MUTATING_QUERIES:
        ctx = DummyCtx()

        # Response for the query itself
        mock_db_connection.data_client.add_mock_response(get_mock_normal_query_response())

        tool_response = await run_query(sql_text, ctx, mock_db_connection)

        # validate tool_response
        assert (
            isinstance(tool_response, (list, tuple))
            and len(tool_response) == 1
            and isinstance(tool_response[0], dict)
            and 'error' not in tool_response[0]
        )
        column_records = tool_response[0]
        validate_normal_query_response(column_records)


@pytest.mark.asyncio
async def test_get_table_schema():
    """Test test_get_table_schema call in a positive case."""
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=False, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=False)
    mock_db_connection.data_client.add_mock_response(get_mock_normal_query_response())
    DBConnectionSingleton._instance._db_connection = mock_db_connection  # type: ignore

    ctx = DummyCtx()
    tool_response = await get_table_schema('table_name', ctx)

    # validate tool_response
    assert (
        isinstance(tool_response, (list, tuple))
        and len(tool_response) == 1
        and isinstance(tool_response[0], dict)
        and 'error' not in tool_response[0]
    )
    column_records = tool_response[0]
    validate_normal_query_response(column_records)


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
            'postgres',
            '--region',
            'us-west-2',
            '--readonly',
            'True',
        ],
    )
    monkeypatch.setattr('awslabs.postgres_mcp_server.server.mcp.run', lambda: None)

    # Mock the connection so main can complete successfully
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=False, is_test=True)
    mock_db_connection = Mock_DBConnection(readonly=False)
    mock_db_connection.data_client.add_mock_response(get_mock_normal_query_response())
    DBConnectionSingleton._instance._db_connection = mock_db_connection  # type: ignore

    # This test of main() will succeed in parsing parameters and create connection object.
    main()


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
            'postgres',
            '--region',
            'invalid',
            '--readonly',
            'True',
        ],
    )
    monkeypatch.setattr('awslabs.postgres_mcp_server.server.mcp.run', lambda: None)

    # This test of main() will succeed in parsing parameters and create connection object.
    # However, since connection object is not boto3 client with real credential, the validate of connection will fail and cause system exit
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


if __name__ == '__main__':
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    asyncio.run(test_run_query_well_formatted_response())
    asyncio.run(test_run_query_safe_read_queries_on_redonly_settings())
    asyncio.run(test_run_query_risky_queries_without_parameters())
    asyncio.run(test_run_query_throw_client_error())
    asyncio.run(test_run_query_write_queries_on_readonly_setting())
    asyncio.run(test_run_query_write_queries_on_readonly_setting())
