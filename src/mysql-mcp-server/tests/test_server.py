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
from awslabs.mysql_mcp_server.server import (
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
    # 1. Simple SELECT
    'SELECT * FROM employees',
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
    # 5. Basic aggregation
    """SELECT
        department_id,
        COUNT(*) AS employee_count,
        AVG(salary) AS avg_salary,
        MAX(salary) AS max_salary
       FROM employees
       GROUP BY department_id""",
    # 6. HAVING clause
    """SELECT
        category_id,
        COUNT(*) AS product_count,
        AVG(unit_price) AS avg_price
       FROM products
       GROUP BY category_id
       HAVING COUNT(*) > 10""",
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
         WHERE e.department_id = d.department_id) AS employee_count
       FROM departments d""",
    # 11. Subquery in FROM
    """SELECT
        dept_summary.department_id,
        dept_summary.avg_salary
       FROM (
           SELECT
               department_id,
               AVG(salary) AS avg_salary
           FROM employees
           GROUP BY department_id
       ) AS dept_summary
       WHERE dept_summary.avg_salary > 60000""",
    # 12. Simple CTE
    """WITH employee_stats AS (
           SELECT
               department_id,
               COUNT(*) AS emp_count,
               AVG(salary) AS avg_salary
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
               COUNT(*) AS emp_count
           FROM employees
           GROUP BY department_id
       ),
       salary_stats AS (
           SELECT
               department_id,
               AVG(salary) AS avg_salary
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
               1 AS level
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
    # 15. Complex analytics query
    """WITH monthly_sales AS (
           SELECT
               DATE_FORMAT(order_date, '%Y-%m-01') AS month,
               SUM(total_amount) AS total_sales
           FROM orders
           GROUP BY DATE_FORMAT(order_date, '%Y-%m-01')
       ),
       sales_stats AS (
           SELECT
               month,
               total_sales,
               LAG(total_sales) OVER (ORDER BY month) AS prev_month_sales,
               LEAD(total_sales) OVER (ORDER BY month) AS next_month_sales
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
           END AS sales_trend,
           ROUND(((total_sales - prev_month_sales) / prev_month_sales * 100), 2) AS growth_percentage
       FROM sales_stats
       WHERE month >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 12 MONTH), '%Y-%m-01')
       ORDER BY month""",
    # 16. Metadata from information_schema.tables
    """SELECT table_name, table_schema
       FROM information_schema.tables
       WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')""",
    # 17. Metadata from information_schema.columns
    """SELECT column_name, data_type, is_nullable
       FROM information_schema.columns
       WHERE table_name = 'employees'""",
    # 18. List schemas
    'SELECT schema_name FROM information_schema.schemata',
    # 19. List tables in current database
    'SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()',
    # 20. Explain query plan
    'EXPLAIN SELECT * FROM orders WHERE customer_id = 123',
    # 21. Window function with rank
    """SELECT
           employee_id,
           department_id,
           salary,
           RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dept_rank
       FROM employees""",
    # 22. Date range query
    """SELECT *
       FROM orders
       WHERE order_date BETWEEN CURDATE() - INTERVAL 30 DAY AND CURDATE()""",
]


SAFE_MUTATING_QUERIES = [
    # DML: Inserts
    "INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@example.com')",
    "INSERT INTO logs (user_id, action) SELECT id, 'login' FROM users WHERE active = TRUE",
    "INSERT INTO audit_log (event_type, description, created_at) VALUES ('user_created', 'User Alice created', NOW())",
    "INSERT INTO products (sku, name) VALUES ('abc123', 'Widget') ON DUPLICATE KEY UPDATE name = VALUES(name)",
    'INSERT INTO archive_users SELECT * FROM users WHERE active = FALSE',
    # DML: Updates
    'UPDATE users SET last_login = NOW() WHERE id = 42',
    "UPDATE orders SET status = 'shipped' WHERE shipped_at IS NOT NULL AND status = 'processing'",
    'UPDATE inventory SET quantity = quantity - 1 WHERE product_id = 10 AND quantity > 0',
    # DML: Deletes
    'DELETE FROM sessions WHERE expires_at < NOW()',
    'DELETE FROM cart_items WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = cart_items.user_id)',
    'DELETE FROM temp_files WHERE created_at < (NOW() - INTERVAL 7 DAY)',
    # DDL: Table and index creation
    'CREATE TABLE employees (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, email VARCHAR(255) UNIQUE)',
    'CREATE TABLE archive_users LIKE users',
    "CREATE TABLE order_status_example (status ENUM('pending', 'shipped', 'delivered'))",
    'CREATE INDEX idx_orders_user_id ON orders(user_id)',
    # DDL: Table alteration
    'ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE',
    'ALTER TABLE users CHANGE COLUMN fullname full_name VARCHAR(255)',
    'ALTER TABLE orders MODIFY COLUMN status VARCHAR(20) NOT NULL',
    'ALTER TABLE invoices AUTO_INCREMENT = 1000',
    # DDL: Views
    'CREATE VIEW active_users AS SELECT id, name FROM users WHERE active = TRUE',
]


MUTATING_QUERIES = [
    # DML
    """WITH new_users AS (
        SELECT * FROM staging_users WHERE is_valid = TRUE
    )
    INSERT INTO users (id, name, email)
    SELECT id, name, email FROM new_users""",
    """UPDATE orders
    SET status = 'shipped'
    WHERE id IN (
        SELECT order_id FROM shipping_queue WHERE priority = 'high'
    )""",
    """WITH old_logs AS (
        SELECT id FROM logs WHERE created_at < NOW() - INTERVAL 30 DAY
    )
    DELETE FROM logs WHERE id IN (SELECT id FROM old_logs)""",
    # DDL
    """CREATE TABLE IF NOT EXISTS archive_data
    AS SELECT * FROM data WHERE created_at < NOW() - INTERVAL 1 YEAR""",
    """DROP TABLE IF EXISTS temp_data, old_archive""",
    """ALTER TABLE users
    ADD COLUMN last_login TIMESTAMP,
    MODIFY email VARCHAR(255) NOT NULL""",
    # Procedures & Triggers
    """DELIMITER //
    CREATE PROCEDURE log_activity()
    BEGIN
    INSERT INTO activity_log(user_id, action) VALUES (1, 'inserted');
    END//
    DELIMITER ;""",
    """DROP PROCEDURE IF EXISTS log_activity""",
    """DELIMITER //
    CREATE TRIGGER before_insert_user
    BEFORE INSERT ON users
    FOR EACH ROW
    BEGIN
        INSERT INTO audit_log(user_id, action) VALUES (NEW.id, 'created');
    END//
    DELIMITER ;""",
    """DROP TRIGGER IF EXISTS before_insert_user""",
    # Permissions
    """GRANT SELECT, INSERT ON orders TO 'analyst_role'""",
    """REVOKE ALL PRIVILEGES ON users FROM 'guest_role'""",
    # Index & View Management
    """CREATE INDEX idx_users_active ON users (last_login)""",
    """DROP INDEX idx_users_active ON users""",
    """CREATE VIEW vip_customers AS
    SELECT * FROM customers WHERE loyalty_tier = 'Platinum'""",
    """DROP VIEW IF EXISTS vip_customers""",
    # Materialized view equivalent
    """CREATE TABLE recent_signups AS
    SELECT * FROM users WHERE created_at > CURRENT_DATE - INTERVAL 30 DAY""",
    """DROP TABLE IF EXISTS recent_signups""",
    # Auto-increment sequence behavior
    """ALTER TABLE users AUTO_INCREMENT = 1000""",
    # ENUM usage
    """CREATE TABLE order_status_example (
        id INT PRIMARY KEY,
        status ENUM('pending', 'shipped', 'delivered')
    )""",
    # Schema (database) management
    """CREATE DATABASE reporting""",
    """DROP DATABASE IF EXISTS reporting""",
    # Users & roles
    """CREATE USER 'data_analyst'@'%' IDENTIFIED BY 'an@lyt1c'""",
    """ALTER USER 'data_analyst'@'%' IDENTIFIED WITH mysql_native_password BY 'an@lyt1c'""",
    """DROP USER IF EXISTS 'data_analyst'@'%'""",
    """GRANT SELECT ON analytics.* TO 'data_analyst'@'%'""",
    # Configuration
    """SET GLOBAL max_connections = 200""",
    """SET SESSION sql_mode = 'STRICT_ALL_TABLES'""",
    # Plugins
    """INSTALL PLUGIN validate_password SONAME 'validate_password.so'""",
    """UNINSTALL PLUGIN validate_password""",
    # Event scheduler
    """CREATE EVENT purge_old_logs
    ON SCHEDULE EVERY 1 DAY
    DO DELETE FROM logs WHERE created_at < NOW() - INTERVAL 7 DAY""",
    """DROP EVENT IF EXISTS purge_old_logs""",
]

RISKY_QUERY_WITHOUT_PARAMETERS = [
    # Matches: r'--.*$' and r"(?i)'.*?--"
    "SELECT * FROM users WHERE username = 'admin' --",
    # Matches: r'/\*.*?\*/'
    'SELECT * FROM users /* get all users including admins */ WHERE is_active = 1',
    # Matches: r"(?i)'.*?--"
    "SELECT * FROM users WHERE username = '' -- and password = 'x'",
    # Matches: r'(?i)\bor\b\s+\d+\s*=\s*\d+'
    'SELECT * FROM users WHERE id = 1 OR 1 = 1',
    # Matches: r"(?i)\bor\b\s*'[^']+'\s*=\s*'[^']+'"
    "SELECT * FROM users WHERE username = '' OR 'x' = 'x'",
    # Matches: r'(?i)\bunion\b.*\bselect\b'
    'SELECT id FROM users WHERE id = -1 UNION SELECT password FROM admin_users',
    # Matches: r'(?i)\bdrop\b'
    'DROP TABLE users',
    # Matches: r'(?i)\btruncate\b'
    'TRUNCATE TABLE logs',
    # Matches: r'(?i)\bgrant\b|\brevoke\b'
    "GRANT ALL PRIVILEGES ON *.* TO 'attacker'@'%'",
    "REVOKE SELECT ON users FROM 'guest'@'%'",
    # Matches: r'(?i);'
    'SELECT * FROM users; DROP TABLE users',
    # Matches: r'(?i)\bsleep\s*\('
    'SELECT * FROM users WHERE id = 1 OR SLEEP(5)',
    # Matches: r'(?i)\bload_file\s*\('
    "SELECT LOAD_FILE('/etc/passwd')",
    # Matches: r'(?i)\binto\s+outfile\b'
    "SELECT * FROM users INTO OUTFILE '/tmp/users.txt'",
    # Bonus: triggers multiple patterns: comment, stacked query, union, tautology
    "SELECT * FROM users WHERE username = '' OR 1=1; -- DROP TABLE users",
    # Bonus: INTO DUMPFILE is another variation of INTO OUTFILE
    "SELECT '<?php system($_GET[\"cmd\"]); ?>' INTO DUMPFILE '/var/www/html/shell.php'",
    # Bonus: sleep nested inside subquery
    'SELECT * FROM users WHERE id = (SELECT IF(1=1, SLEEP(3), 1))',
    # Bonus: load_file with alias
    "SELECT LOAD_FILE('/etc/passwd') AS data",
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
    tool_response = await get_table_schema(table_name='table_name', database_name='mysql', ctx=ctx)

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
            'mysql',
            '--region',
            'us-west-2',
            '--readonly',
            'True',
        ],
    )
    monkeypatch.setattr('awslabs.mysql_mcp_server.server.mcp.run', lambda: None)

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
    DBConnectionSingleton.initialize('mock', 'mock', 'mock', 'mock', readonly=True, is_test=True)
    asyncio.run(test_run_query_well_formatted_response())
    asyncio.run(test_run_query_safe_read_queries_on_redonly_settings())
    asyncio.run(test_run_query_risky_queries_without_parameters())
    asyncio.run(test_run_query_throw_client_error())
    asyncio.run(test_run_query_write_queries_on_readonly_setting())
    asyncio.run(test_run_query_write_queries_on_readonly_setting())
