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

"""Tests for the SqlAnalyzer utility class."""

from awslabs.aws_dataprocessing_mcp_server.utils.sql_analyzer import SqlAnalyzer


class TestSqlAnalyzer:
    """Tests for the SqlAnalyzer utility class."""

    def test_remove_sql_comments_multiline(self):
        """Test that _remove_sql_comments correctly removes multiline comments."""
        sql = 'SELECT * /* this is a comment */ FROM table'
        result = SqlAnalyzer._remove_sql_comments(sql)
        assert result == 'SELECT *   FROM table'

    def test_remove_sql_comments_multiline_nested(self):
        """Test that _remove_sql_comments handles multiline comments with newlines."""
        sql = """SELECT * /*
        this is a
        multiline comment
        */ FROM table"""
        result = SqlAnalyzer._remove_sql_comments(sql)
        assert 'SELECT *' in result
        assert 'FROM table' in result
        assert 'comment' not in result

    def test_remove_sql_comments_single_line(self):
        """Test that _remove_sql_comments correctly removes single-line comments."""
        sql = 'SELECT * FROM table -- this is a comment'
        result = SqlAnalyzer._remove_sql_comments(sql)
        assert result == 'SELECT * FROM table  '

    def test_remove_sql_comments_multiple_single_line(self):
        """Test that _remove_sql_comments handles multiple single-line comments."""
        sql = """SELECT col1, -- first comment
        col2 -- second comment
        FROM table"""
        result = SqlAnalyzer._remove_sql_comments(sql)
        assert 'SELECT col1,  ' in result
        assert 'col2  ' in result
        assert 'FROM table' in result
        assert 'comment' not in result

    def test_remove_sql_comments_mixed(self):
        """Test that _remove_sql_comments handles both comment types."""
        sql = 'SELECT /* block comment */ col1, col2 -- line comment'
        result = SqlAnalyzer._remove_sql_comments(sql)
        assert result == 'SELECT   col1, col2  '

    def test_normalize_whitespace_basic(self):
        """Test that _normalize_whitespace handles basic whitespace normalization."""
        sql = '  SELECT   *    FROM     table  '
        result = SqlAnalyzer._normalize_whitespace(sql)
        assert result == 'SELECT * FROM table'

    def test_normalize_whitespace_tabs_newlines(self):
        """Test that _normalize_whitespace handles tabs and newlines."""
        sql = 'SELECT\t*\nFROM\r\n   table'
        result = SqlAnalyzer._normalize_whitespace(sql)
        assert result == 'SELECT * FROM table'

    def test_preprocess_sql_complete(self):
        """Test that _preprocess_sql correctly combines comment removal and whitespace normalization."""
        sql = """  SELECT   /* comment */  *
        FROM     table -- another comment   """
        result = SqlAnalyzer._preprocess_sql(sql)
        assert result == 'SELECT * FROM table'

    def test_preprocess_sql_empty_string(self):
        """Test that _preprocess_sql handles empty strings."""
        assert SqlAnalyzer._preprocess_sql('') == ''

    def test_preprocess_sql_whitespace_only(self):
        """Test that _preprocess_sql handles whitespace-only strings."""
        assert SqlAnalyzer._preprocess_sql('   \t\n   ') == ''

    def test_contains_write_operations_select_queries(self):
        """Test that contains_write_operations correctly identifies SELECT as read-only."""
        test_cases = [
            'SELECT * FROM table',
            'select col1, col2 from table',
            'SELECT COUNT(*) FROM table WHERE col > 5',
            'WITH cte AS (SELECT * FROM t1) SELECT * FROM cte',
        ]
        for query in test_cases:
            assert not SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_insert_queries(self):
        """Test that contains_write_operations correctly identifies INSERT as write operation."""
        test_cases = [
            'INSERT INTO table VALUES (1, 2, 3)',
            'insert into table (col1, col2) values (1, 2)',
            'INSERT INTO table SELECT * FROM other_table',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_update_queries(self):
        """Test that contains_write_operations correctly identifies UPDATE as write operation."""
        test_cases = [
            "UPDATE table SET col1 = 'value'",
            'update table set col1 = 1 where col2 > 5',
            'UPDATE t1 SET col = (SELECT col FROM t2 WHERE t2.id = t1.id)',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_delete_queries(self):
        """Test that contains_write_operations correctly identifies DELETE as write operation."""
        test_cases = [
            'DELETE FROM table',
            'delete from table where col > 5',
            'DELETE t1 FROM table1 t1 JOIN table2 t2 ON t1.id = t2.id',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_ddl_queries(self):
        """Test that contains_write_operations correctly identifies DDL as write operations."""
        test_cases = [
            'CREATE TABLE new_table (id INT, name VARCHAR(50))',
            'DROP TABLE old_table',
            'ALTER TABLE table ADD COLUMN new_col INT',
            'CREATE INDEX idx_name ON table (col)',
            'DROP INDEX idx_name',
            'CREATE VIEW view_name AS SELECT * FROM table',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_ctas_queries(self):
        """Test that contains_write_operations correctly identifies CTAS as write operation."""
        test_cases = [
            'CREATE TABLE new_table AS SELECT * FROM existing_table',
            'create table as select col1, col2 from table where col3 > 5',
            'CREATE VIEW new_view AS SELECT * FROM table',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_other_write_operations(self):
        """Test that contains_write_operations identifies other write operations."""
        test_cases = [
            'TRUNCATE TABLE table',
            'MERGE INTO target USING source ON condition',
            'GRANT SELECT ON table TO user',
            'REVOKE INSERT ON table FROM user',
            'CALL procedure_name(param1, param2)',
            'EXECUTE sp_procedure',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_comment_injection(self):
        """Test that contains_write_operations prevents comment-based SQL injection."""
        test_cases = [
            'INSERT /* SELECT */ INTO table VALUES (1, 2, 3)',
            'DELETE /* SELECT comment */ FROM table WHERE id=1',
            'DROP /* SELECT * FROM dummy */ TABLE sensitive_table',
            'UPDATE table SET col=1 -- SELECT comment',
            'CREATE /* SELECT query */ TABLE new_table (id INT)',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_multiline_comment_injection(self):
        """Test that contains_write_operations handles multiline comment injection."""
        query = """INSERT /*
        SELECT * FROM dummy
        multiline comment
        */ INTO table VALUES (1, 2, 3)"""
        assert SqlAnalyzer.contains_write_operations(query)

    def test_contains_write_operations_mixed_case(self):
        """Test that contains_write_operations is case-insensitive."""
        test_cases = [
            'InSeRt InTo TaBlE vAlUeS (1, 2, 3)',
            'UpDaTe TaBlE sEt CoL=1',
            'DeLeTe FrOm TaBlE',
            'CrEaTe TaBlE nEw_TaBlE (iD iNt)',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_whitespace_manipulation(self):
        """Test that contains_write_operations handles various whitespace patterns."""
        test_cases = [
            '    INSERT    INTO table VALUES (1, 2, 3)   ',
            '\t\tUPDATE\t\ttable\t\tSET\t\tcol=1\t\t',
            '\n\nDELETE\n\nFROM\n\ntable\n\n',
            '  INSERT  \n  INTO  \t  table  \r\n  VALUES (1, 2, 3)  ',
        ]
        for query in test_cases:
            assert SqlAnalyzer.contains_write_operations(query), f'Failed for: {query}'

    def test_contains_write_operations_complex_cte_with_write(self):
        """Test that contains_write_operations detects write operations in complex CTEs."""
        query = """
        WITH temp_data AS (
            SELECT col1, col2 FROM source_table WHERE condition = 'value'
        )
        INSERT INTO target_table SELECT * FROM temp_data
        """
        assert SqlAnalyzer.contains_write_operations(query)

    def test_contains_write_operations_complex_cte_read_only(self):
        """Test that contains_write_operations allows complex read-only CTEs."""
        query = """
        WITH
            cte1 AS (SELECT * FROM table1 WHERE col > 5),
            cte2 AS (SELECT col1, COUNT(*) as cnt FROM table2 GROUP BY col1)
        SELECT c1.*, c2.cnt
        FROM cte1 c1
        LEFT JOIN cte2 c2 ON c1.id = c2.col1
        ORDER BY c1.created_date DESC
        """
        assert not SqlAnalyzer.contains_write_operations(query)

    def test_contains_write_operations_empty_and_None(self):
        """Test that contains_write_operations handles empty and None inputs correctly."""
        query = ''
        assert not SqlAnalyzer.contains_write_operations(query)
        assert not SqlAnalyzer.contains_write_operations(None)

    def test_contains_write_operations_empty_after_cleaned(self):
        """Test that contains_write_operations handles whitespace-only strings correctly."""
        query = '    '
        assert not SqlAnalyzer.contains_write_operations(query)

    def test_is_read_only_query_select_statements(self):
        """Test that is_read_only_query correctly identifies SELECT statements."""
        test_cases = [
            'SELECT * FROM table',
            'select col1, col2 from table',
            'WITH cte AS (SELECT * FROM t1) SELECT * FROM cte',
        ]
        for query in test_cases:
            assert SqlAnalyzer.is_read_only_query(query), f'Failed for: {query}'

    def test_is_read_only_query_utility_statements(self):
        """Test that is_read_only_query allows utility/informational statements."""
        test_cases = [
            'SHOW TABLES',
            'SHOW DATABASES',
            'DESCRIBE table_name',
            'DESC table_name',
            'EXPLAIN SELECT * FROM table',
            'ANALYZE TABLE table_name',
        ]
        for query in test_cases:
            assert SqlAnalyzer.is_read_only_query(query), f'Failed for: {query}'

    def test_is_read_only_query_write_operations(self):
        """Test that is_read_only_query rejects write operations."""
        test_cases = [
            'INSERT INTO table VALUES (1, 2, 3)',
            "UPDATE table SET col = 'value'",
            'DELETE FROM table',
            'CREATE TABLE new_table (id INT)',
            'DROP TABLE table',
        ]
        for query in test_cases:
            assert not SqlAnalyzer.is_read_only_query(query), f'Failed for: {query}'

    def test_is_read_only_query_edge_cases(self):
        """Test that is_read_only_query handles edge cases."""
        # Empty or None queries
        assert not SqlAnalyzer.is_read_only_query(None)
        assert not SqlAnalyzer.is_read_only_query('')
        assert not SqlAnalyzer.is_read_only_query('   ')
        assert not SqlAnalyzer.is_read_only_query(';')

        # Unknown statements
        assert not SqlAnalyzer.is_read_only_query('UNKNOWN_STATEMENT')

    def test_get_query_type_basic_statements(self):
        """Test that get_query_type correctly identifies basic statement types."""
        test_cases = [
            ('SELECT * FROM table', 'SELECT'),
            ('INSERT INTO table VALUES (1, 2)', 'INSERT'),
            ('UPDATE table SET col = 1', 'UPDATE'),
            ('DELETE FROM table', 'DELETE'),
            ('CREATE TABLE new_table (id INT)', 'CREATE'),
            ('DROP TABLE table', 'DROP'),
            ('SHOW TABLES', 'SHOW'),
            ('DESCRIBE table', 'DESCRIBE'),
            ('EXPLAIN SELECT * FROM table', 'EXPLAIN'),
        ]
        for query, expected_type in test_cases:
            result = SqlAnalyzer.get_query_type(query)
            assert result == expected_type, (
                f'Expected {expected_type}, got {result} for query: {query}'
            )

    def test_get_query_type_with_comments(self):
        """Test that get_query_type works after comment removal."""
        test_cases = [
            ('/* comment */ SELECT * FROM table', 'SELECT'),
            ('-- comment\nINSERT INTO table VALUES (1, 2)', 'INSERT'),
            ('/* multi\nline\ncomment */ UPDATE table SET col = 1', 'UPDATE'),
        ]
        for query, expected_type in test_cases:
            result = SqlAnalyzer.get_query_type(query)
            assert result == expected_type, (
                f'Expected {expected_type}, got {result} for query: {query}'
            )

    def test_get_query_type_with_whitespace(self):
        """Test that get_query_type works after whitespace normalization."""
        test_cases = [
            ('   \t\n  SELECT * FROM table', 'SELECT'),
            ('\n\n\tINSERT INTO table VALUES (1, 2)\n\n', 'INSERT'),
            ('  \r\n  UPDATE table SET col = 1  \t  ', 'UPDATE'),
        ]
        for query, expected_type in test_cases:
            result = SqlAnalyzer.get_query_type(query)
            assert result == expected_type, (
                f'Expected {expected_type}, got {result} for query: {query}'
            )

    def test_get_query_type_edge_cases(self):
        """Test that get_query_type handles edge cases."""
        # Empty or None queries
        assert SqlAnalyzer.get_query_type(None) == 'UNKNOWN'
        assert SqlAnalyzer.get_query_type('') == 'UNKNOWN'
        assert SqlAnalyzer.get_query_type('   ') == 'UNKNOWN'
        assert SqlAnalyzer.get_query_type(';') == 'UNKNOWN'

        # Only comments
        assert SqlAnalyzer.get_query_type('/* only comment */') == 'UNKNOWN'
        assert SqlAnalyzer.get_query_type('-- only comment') == 'UNKNOWN'

    def test_get_query_type_case_insensitive(self):
        """Test that get_query_type is case-insensitive."""
        test_cases = [
            ('select * from table', 'SELECT'),
            ('SeLeCt * FrOm TaBlE', 'SELECT'),
            ('INSERT into table', 'INSERT'),
            ('insert INTO table', 'INSERT'),
        ]
        for query, expected_type in test_cases:
            result = SqlAnalyzer.get_query_type(query)
            assert result == expected_type, (
                f'Expected {expected_type}, got {result} for query: {query}'
            )

    def test_security_injection_scenarios(self):
        """Test comprehensive SQL injection scenarios that should be blocked."""
        malicious_queries = [
            # Comment-based bypasses
            'INSERT /* SELECT */ INTO table VALUES (1,2,3)',
            'DELETE /* SELECT comment */ FROM table WHERE id=1',
            'DROP /* SELECT * FROM dummy */ TABLE sensitive_table',
            'UPDATE table SET col=1 -- SELECT comment here',
            'TRUNCATE /* contains SELECT keyword */ TABLE important_data',
            # Multi-line comment bypasses
            """INSERT /*
            SELECT * FROM legitimate_table
            This looks like a SELECT but it's really an INSERT
            */ INTO target_table VALUES (1,2,3)""",
            # Mixed case attempts
            'InSeRt /* SELECT */ iNtO TaBlE vAlUeS (1,2,3)',
            'DeLeTe /* select * from dummy */ FrOm SeNsItIvE_tAbLe',
            # Whitespace manipulation
            '    INSERT    /*   SELECT   */    INTO table VALUES (1,2,3)',
            'DELETE\t/*\tSELECT\t*/\tFROM\ttable',
            # Complex nested scenarios
            'WITH fake AS (SELECT 1) INSERT /* SELECT */ INTO table VALUES (1,2,3)',
            'MERGE /* SELECT operation */ INTO target USING source ON condition',
        ]

        for query in malicious_queries:
            assert SqlAnalyzer.contains_write_operations(query), (
                f'Security bypass detected for: {repr(query)}'
            )
            assert not SqlAnalyzer.is_read_only_query(query), (
                f'Security bypass in is_read_only_query for: {repr(query)}'
            )

    def test_legitimate_read_queries(self):
        """Test that legitimate read queries are properly allowed."""
        legitimate_queries = [
            # Basic SELECT statements
            'SELECT * FROM table',
            "SELECT col1, col2 FROM table WHERE condition = 'value'",
            # Complex SELECT with joins
            """SELECT t1.col1, t2.col2
               FROM table1 t1
               JOIN table2 t2 ON t1.id = t2.ref_id
               WHERE t1.status = 'active'""",
            # CTEs with only SELECT
            """WITH cte1 AS (SELECT * FROM table1),
                    cte2 AS (SELECT col1, COUNT(*) as cnt FROM table2 GROUP BY col1)
               SELECT c1.*, c2.cnt
               FROM cte1 c1
               LEFT JOIN cte2 c2 ON c1.id = c2.col1""",
            # Utility commands
            'SHOW TABLES',
            'SHOW DATABASES',
            'DESCRIBE my_table',
            'EXPLAIN SELECT * FROM table',
            'ANALYZE TABLE table_name',
            # Nested subqueries
            """SELECT * FROM (
                   SELECT col1, col2,
                          (SELECT COUNT(*) FROM table2 WHERE table2.id = table1.id) as count_col
                   FROM table1
                   WHERE col3 IN (SELECT DISTINCT col3 FROM table3 WHERE col4 > 100)
               ) AS subquery
               WHERE count_col > 5""",
        ]

        for query in legitimate_queries:
            assert not SqlAnalyzer.contains_write_operations(query), (
                f'Legitimate query blocked: {repr(query)}'
            )
            # Note: Some utility commands might not pass is_read_only_query due to strict first-keyword matching,
            # but they should not be flagged as write operations

    def test_enhanced_write_operations_detection(self):
        """Test detection of enhanced write operations from mutable_sql_detector improvements."""
        enhanced_write_queries = [
            # REPLACE operations
            'REPLACE INTO table (col1, col2) VALUES (1, 2)',
            'replace into table select * from other_table',
            # RENAME operations
            'RENAME TABLE old_name TO new_name',
            'rename table t1 to t2, t3 to t4',
            # LOAD operations
            "LOAD DATA INFILE 'data.csv' INTO TABLE test_table",
            "LOAD XML LOCAL INFILE 'data.xml' INTO TABLE test_table",
            "load data local infile '/path/file.txt' into table my_table",
            # Plugin operations
            "INSTALL PLUGIN plugin_name SONAME 'plugin_lib.so'",
            'UNINSTALL PLUGIN plugin_name',
            "install plugin test_plugin soname 'test.so'",
            # Enhanced DDL with specific object types
            'CREATE TABLE users (id INT, name VARCHAR(50))',
            'DROP VIEW user_summary',
            'ALTER INDEX idx_name REBUILD',
            'CREATE TRIGGER audit_trigger AFTER INSERT ON users',
            'DROP FUNCTION calculate_total',
            'ALTER PROCEDURE update_stats MODIFY SQL SECURITY DEFINER',
            'CREATE EVENT cleanup_event ON SCHEDULE EVERY 1 DAY',
            'DROP EVENT old_cleanup',
        ]

        for query in enhanced_write_queries:
            assert SqlAnalyzer.contains_write_operations(query), (
                f'Enhanced write operation not detected: {repr(query)}'
            )
            assert not SqlAnalyzer.is_read_only_query(query), (
                f'Write operation incorrectly marked as read-only: {repr(query)}'
            )

    def test_enhanced_ddl_object_type_detection(self):
        """Test that enhanced DDL detection works for specific object types."""
        ddl_queries = [
            # Tables
            ('CREATE TABLE test (id INT)', 'CREATE'),
            ('DROP TABLE test', 'DROP'),
            ('ALTER TABLE test ADD COLUMN name VARCHAR(50)', 'ALTER'),
            # Views
            ('CREATE VIEW user_view AS SELECT * FROM users', 'CREATE'),
            ('DROP VIEW user_view', 'DROP'),
            ('ALTER VIEW user_view AS SELECT id, name FROM users', 'ALTER'),
            # Indexes
            ('CREATE INDEX idx_name ON table (column)', 'CREATE'),
            ('DROP INDEX idx_name ON table', 'DROP'),
            ('ALTER INDEX idx_name REBUILD', 'ALTER'),
            # Triggers
            ('CREATE TRIGGER my_trigger BEFORE INSERT ON table', 'CREATE'),
            ('DROP TRIGGER my_trigger', 'DROP'),
            ('ALTER TRIGGER my_trigger ENABLE', 'ALTER'),
            # Procedures
            ('CREATE PROCEDURE proc_name() BEGIN END', 'CREATE'),
            ('DROP PROCEDURE proc_name', 'DROP'),
            ('ALTER PROCEDURE proc_name SQL SECURITY DEFINER', 'ALTER'),
            # Functions
            ('CREATE FUNCTION func_name() RETURNS INT', 'CREATE'),
            ('DROP FUNCTION func_name', 'DROP'),
            ('ALTER FUNCTION func_name SQL SECURITY DEFINER', 'ALTER'),
            # Events
            ('CREATE EVENT event_name ON SCHEDULE EVERY 1 DAY', 'CREATE'),
            ('DROP EVENT event_name', 'DROP'),
            ('ALTER EVENT event_name DISABLE', 'ALTER'),
        ]

        for query, expected_type in ddl_queries:
            assert SqlAnalyzer.contains_write_operations(query), (
                f'DDL operation not detected: {repr(query)}'
            )
            assert SqlAnalyzer.get_query_type(query) == expected_type, (
                f'Wrong query type for: {repr(query)}'
            )
            assert not SqlAnalyzer.is_read_only_query(query), (
                f'DDL operation incorrectly marked as read-only: {repr(query)}'
            )

    def test_case_insensitive_enhanced_operations(self):
        """Test that enhanced operations are detected case-insensitively."""
        case_variations = [
            # Mixed case REPLACE
            'RePlAcE InTo TaBlE vAlUeS (1, 2)',
            'Replace INTO table SELECT * FROM other',
            # Mixed case RENAME
            'ReNaMe TaBlE oLd_NaMe To NeW_nAmE',
            # Mixed case LOAD
            "LoAd DaTa InFiLe 'test.csv' InTo TaBlE test",
            "LOAD xml local INFILE 'data.xml' into TABLE my_table",
            # Mixed case plugins
            "InStAlL pLuGiN test_plugin SoNaMe 'test.so'",
            'UnInStAlL PlUgIn old_plugin',
            # Mixed case enhanced DDL
            'CrEaTe TrIgGeR my_trigger BeForE iNsErT oN table',
            'dRoP fUnCtIoN old_function',
            'AlTeR pRoCeDuRe proc_name',
        ]

        for query in case_variations:
            assert SqlAnalyzer.contains_write_operations(query), (
                f'Case variation not detected: {repr(query)}'
            )
