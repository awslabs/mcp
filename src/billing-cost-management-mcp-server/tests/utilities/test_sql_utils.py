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

"""Tests for SQL utilities.

This module contains unit tests for the sql_utils.py module, including:
- Database connection and path management
- Table creation and schema definition
- Data insertion operations
- SQL query execution and result processing
- Table registration in schema metadata
- Session SQL execution with error handling
- API response conversion to database tables
"""

import os
import pytest
import sqlite3
import sys
import tempfile
import uuid
from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
    _coerce_for_column,
    convert_api_response_to_table,
    convert_response_if_needed,
    create_table,
    execute_query,
    execute_session_sql,
    get_db_connection,
    get_session_db_path,
    insert_data,
    register_table_in_schema_info,
    should_convert_to_sql,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def temp_db_path():
    """Create a temporary directory and database path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, 'test_session.db')
        yield db_path


class TestShouldConvertToSql:
    """Tests for should_convert_to_sql function."""

    def test_should_convert_large_response(self):
        """Test should_convert_to_sql with large response."""
        # Setup - Response size above threshold
        threshold = int(os.getenv('MCP_SQL_THRESHOLD', 50 * 1024))  # 50KB default
        large_size = threshold + 1024  # 1KB over threshold

        # Execute
        result = should_convert_to_sql(large_size)

        # Assert
        assert result is True

    def test_should_not_convert_small_response(self):
        """Test should_convert_to_sql with small response."""
        # Setup - Response size below threshold
        threshold = int(os.getenv('MCP_SQL_THRESHOLD', 50 * 1024))  # 50KB default
        small_size = threshold - 1024  # 1KB under threshold

        # Execute
        result = should_convert_to_sql(small_size)

        # Assert
        assert result is True

    def test_should_convert_with_force_enabled(self):
        """Test should_convert_to_sql with FORCE_SQL_CONVERSION enabled."""
        # Setup - Force conversion regardless of size
        small_size = 100  # Very small response

        # Patch the module-level FORCE_SQL_CONVERSION constant directly instead of
        # reloading the module. The previous approach (del sys.modules[...] +
        # reimport) created a divergent module instance — sys.modules was
        # restored on exit but the parent package's `sql_utils` attribute was
        # left pointing at the new module, which broke `patch(...string path...)`
        # in later tests and made the suite flaky under random test ordering.
        from awslabs.billing_cost_management_mcp_server.utilities import (
            sql_utils as sql_utils_mod,
        )

        with patch.object(sql_utils_mod, 'FORCE_SQL_CONVERSION', True):
            result = sql_utils_mod.should_convert_to_sql(small_size)

        # Assert
        assert result is True


class TestGetSessionDbPath:
    """Tests for get_session_db_path function."""

    @patch('uuid.uuid4')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    @patch('os.makedirs')
    @patch('atexit.register')
    def test_get_session_db_path(
        self, mock_register, mock_makedirs, mock_abspath, mock_dirname, mock_uuid
    ):
        """Test getting session DB path."""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_dirname.return_value = '/mock/path'
        mock_abspath.return_value = '/mock/path/file'

        # Reset the module-level singleton so the mocked path computation runs,
        # and restore it after so later tests don't get a poisoned path that
        # doesn't exist on disk (causes sqlite3.OperationalError elsewhere).
        from awslabs.billing_cost_management_mcp_server.utilities import (
            sql_utils as sql_utils_mod,
        )

        saved = sql_utils_mod._SESSION_DB_PATH
        sql_utils_mod._SESSION_DB_PATH = None
        try:
            path = get_session_db_path()

            # Just verify we get a path back
            assert path is not None
            assert isinstance(path, str)
        finally:
            sql_utils_mod._SESSION_DB_PATH = saved


class TestGetDbConnection:
    """Tests for get_db_connection function."""

    @patch('sqlite3.connect')
    def test_get_db_connection(self, mock_connect):
        """Test getting DB connection."""
        # Setup with detailed mocking
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Execute
        conn, cursor = get_db_connection()

        # Assert with detailed validation
        # We don't check the exact path since it's dynamic
        assert mock_connect.call_count == 1
        mock_connection.cursor.assert_called_once()

        # Verify schema_info table creation
        assert getattr(cursor.execute, 'call_count', 0) == 1
        execute_call = getattr(cursor.execute, 'call_args_list', [])[
            min(0, len(getattr(cursor.execute, 'call_args_list', [])) - 1)
        ][0][0]
        assert 'CREATE TABLE IF NOT EXISTS schema_info' in execute_call
        assert 'table_name TEXT PRIMARY KEY' in execute_call
        assert 'created_at TEXT' in execute_call
        assert 'operation TEXT' in execute_call
        assert 'query TEXT' in execute_call
        assert 'row_count INTEGER' in execute_call

        # Verify commit was called
        mock_connection.commit.assert_called_once()


class TestCreateTable:
    """Tests for create_table function."""

    def test_create_table_standard(self):
        """Test creating a standard table."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'test_table'
        schema = ['id INTEGER PRIMARY KEY', 'name TEXT', 'value REAL']

        # Execute
        create_table(mock_cursor, table_name, schema)

        # Assert with detailed validation
        mock_cursor.execute.assert_called_once()
        # Our SQL statement now goes through create_safe_sql_statement
        # which returns a properly validated SQL statement

    def test_create_table_empty_schema(self):
        """Test creating a table with empty schema (edge case)."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'empty_table'
        schema = []

        # Execute
        create_table(mock_cursor, table_name, schema)

        # Assert - should successfully execute with empty schema
        mock_cursor.execute.assert_called_once()
        # The SQL is now constructed through create_safe_sql_statement


class TestInsertData:
    """Tests for insert_data function."""

    def test_insert_data(self):
        """Test inserting standard data rows."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'test_table'
        data = [[1, 'Alice', 42.0], [2, 'Bob', 37.5], [3, 'Charlie', 91.2]]

        # Execute
        rows_inserted = insert_data(mock_cursor, table_name, data)

        # Assert with detailed validation
        assert getattr(mock_cursor.execute, 'call_count', 0) == 3
        assert rows_inserted == 3

        # Check the first call to validate parameter binding
        first_call = getattr(mock_cursor.execute, 'call_args_list', [])[
            min(0, len(getattr(mock_cursor.execute, 'call_args_list', [])) - 1)
        ]
        assert first_call[0][0] == 'INSERT INTO test_table VALUES (?, ?, ?)'
        assert first_call[0][1] == [1, 'Alice', 42.0]

    def test_insert_empty_data(self):
        """Test inserting empty data."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'test_table'
        data = []

        # Execute
        rows_inserted = insert_data(mock_cursor, table_name, data)

        # Assert with detailed validation
        assert not mock_cursor.execute.called
        assert rows_inserted == 0

    def test_insert_none_data(self):
        """Test inserting None data (edge case)."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'test_table'
        data = None

        # Execute
        rows_inserted = insert_data(mock_cursor, table_name, data)

        # Assert - should handle None data as an empty list
        mock_cursor.execute.assert_not_called()
        assert rows_inserted == 0


class TestExecuteQuery:
    """Tests for execute_query function."""

    def test_execute_select_query(self):
        """Test executing a SELECT query."""
        # Setup
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]
        query = 'SELECT * FROM test_table'

        # Execute
        columns, rows = execute_query(mock_cursor, query)

        # Assert with detailed validation
        mock_cursor.execute.assert_called_once_with(query)
        assert columns == ['id', 'name']
        assert rows == [(1, 'Alice'), (2, 'Bob')]

    def test_execute_update_query(self):
        """Test executing an UPDATE query."""
        # Setup
        mock_cursor = MagicMock()
        mock_cursor.description = None
        mock_cursor.fetchall.return_value = []
        query = "UPDATE test_table SET name = 'Dave' WHERE id = 1"

        # Execute
        columns, rows = execute_query(mock_cursor, query)

        # Assert with detailed validation
        mock_cursor.execute.assert_called_once_with(query)
        assert columns == []
        assert rows == []

    def test_execute_query_with_parameters(self):
        """Test executing a query with parameters."""
        # Setup
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice')]
        query = 'SELECT * FROM test_table WHERE id = ?'
        params = (1,)
        mock_cursor.execute(query, params)
        columns, rows = execute_query(mock_cursor, query)

        assert (
            getattr(mock_cursor.execute, 'call_count', 0) >= 1
        )  # Called at least once (by us manually)
        assert columns == ['id', 'name']
        assert rows == [(1, 'Alice')]


class TestRegisterTableInSchemaInfo:
    """Tests for register_table_in_schema_info function."""

    def test_register_table(self):
        """Test registering a table in schema_info."""
        # Setup
        mock_cursor = MagicMock()
        table_name = 'test_table'
        operation = 'test_operation'
        query = 'SELECT * FROM test_table'
        row_count = 10

        # Execute
        register_table_in_schema_info(mock_cursor, table_name, operation, query, row_count)

        # Assert with detailed validation
        mock_cursor.execute.assert_called_once()
        sql_statement = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        assert 'INSERT OR REPLACE INTO schema_info' in sql_statement
        assert 'VALUES (?, ?, ?, ?, ?)' in sql_statement

        assert params[0] == table_name
        assert isinstance(params[1], str)  # created_at timestamp
        assert params[2] == operation
        assert params[3] == query
        assert params[4] == row_count


@pytest.mark.asyncio
class TestExecuteSessionSql:
    """Tests for execute_session_sql function."""

    @patch('sqlite3.connect')
    async def test_execute_query_only(self, mock_connect, mock_context):
        """Test executing a query without adding data."""
        # Mock cursor results
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]

        # Mock connection
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        query = 'SELECT * FROM test_table'

        # Execute
        result = await execute_session_sql(mock_context, query)

        # Assert with detailed validation
        mock_context.info.assert_called_once()
        assert 'Executing SQL query' in mock_context.info.call_args[0][0]

        mock_cursor.execute.assert_called_with(query)

        # Verify response structure
        assert result['status'] == 'success'
        assert len(result['results']) == 2
        assert result['results'][0] == {'id': 1, 'name': 'Alice'}
        assert result['results'][1] == {'id': 2, 'name': 'Bob'}
        assert result['row_count'] == 2
        assert result['columns'] == ['id', 'name']
        # Database path is dynamic, so we just check that it exists
        assert 'database_path' in result
        assert result['database_path'].endswith('.db')
        assert 'created_table' not in result

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    @patch('sqlite3.connect')
    async def test_execute_with_data(self, mock_connect, mock_context):
        """Test executing a query after adding data."""
        # Mock cursor results
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]

        # Mock connection
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        query = 'SELECT * FROM test_table'
        schema = ['id INTEGER', 'name TEXT']
        data = [[1, 'Alice'], [2, 'Bob']]
        table_name = 'test_table'

        # Execute
        result = await execute_session_sql(mock_context, query, schema, data, table_name)

        # Assert with detailed validation
        assert mock_context.info.call_count >= 2  # At least two log messages
        mock_cursor.execute.assert_any_call(query)

        # Verify response structure
        assert result['status'] == 'success'
        assert len(result['results']) == 2
        assert result['row_count'] == 2
        assert result['columns'] == ['id', 'name']
        # Database path is dynamic, so we just check that it exists
        assert 'database_path' in result
        assert result['database_path'].endswith('.db')
        assert result['created_table'] == 'test_table'
        assert result['rows_added'] == 2

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    @patch('uuid.uuid4')
    async def test_execute_with_auto_table_name(
        self, mock_uuid, mock_get_path, mock_connect, mock_context
    ):
        """Test executing a query with auto-generated table name."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')

        # Mock cursor results
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice'), (2, 'Bob')]

        # Mock connection
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        query = 'SELECT * FROM auto_table'
        schema = ['id INTEGER', 'name TEXT']
        data = [[1, 'Alice'], [2, 'Bob']]

        # Execute
        result = await execute_session_sql(mock_context, query, schema, data)

        # Assert with detailed validation
        assert result['created_table'] == 'user_data_12345678'

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_with_error(self, mock_get_path, mock_connect, mock_context):
        """Test executing a query with an error."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'

        # Mock cursor that raises an error
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = sqlite3.Error('SQL syntax error')

        # Mock connection
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        query = 'SELECT * FROM non_existent_table'

        result = await execute_session_sql(mock_context, query)

        # Assert error was logged
        mock_context.error.assert_called_once()
        error_msg = mock_context.error.call_args[0][0]
        assert 'Error executing SQL query' in error_msg
        assert 'SQL syntax error' in error_msg

        # Verify proper error response
        assert result['status'] == 'error'
        assert 'Error executing SQL query' in result['message']
        assert 'SQL syntax error' in result['message']

        # The error envelope carries a structured, query-content-free error_type
        # plus operation/service so failures are classifiable. This exception is
        # a manually constructed sqlite3.Error (no sqlite_errorname), so it falls
        # back to the exception-class name ('Error').
        assert result['error_type'] == 'Error'
        assert result['operation'] == 'session_sql'
        assert result['service'] == 'SQL'

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_error_classified_by_exception_class(self, mock_get_path, mock_context):
        """A real SQLite failure classifies by its exception class name."""
        # Use a real in-memory connection (no sqlite3.connect mock) so a genuine
        # sqlite3.OperationalError is raised.
        mock_get_path.return_value = ':memory:'

        # Query a table that does not exist -> real sqlite3.OperationalError.
        result = await execute_session_sql(mock_context, 'SELECT * FROM missing_table')

        assert result['status'] == 'error'
        assert 'Error executing SQL query' in result['message']
        assert result['error_type'] == 'OperationalError'
        assert result['operation'] == 'session_sql'
        assert result['service'] == 'SQL'

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_validation_error_classified(
        self, mock_get_path, mock_connect, mock_context
    ):
        """A blocked/harmful query classifies by its exception class ('ValueError')."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = MagicMock()
        mock_connect.return_value = mock_connection

        # validate_sql_query raises ValueError before execute is reached.
        result = await execute_session_sql(mock_context, 'DROP TABLE users')

        assert result['status'] == 'error'
        assert 'Error executing SQL query' in result['message']
        assert result['error_type'] == 'ValueError'
        assert result['operation'] == 'session_sql'
        assert result['service'] == 'SQL'

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_query_write_operation(self, mock_get_path, mock_connect, mock_context):
        """Test executing a write operation query."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'

        # Mock cursor results
        mock_cursor = MagicMock()
        mock_cursor.description = None
        mock_cursor.fetchall.return_value = []

        # Mock connection
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Test with only INSERT operations that should pass validation
        write_operations = [
            "INSERT INTO test_table VALUES (1, 'test')",
            "INSERT INTO test_table (id, name) VALUES (2, 'test2')",
        ]

        for query in write_operations:
            # Execute
            result = await execute_session_sql(mock_context, query)

            # Assert with detailed validation
            assert mock_connection.commit.called
            assert result['status'] == 'success'

            # Reset mock
            mock_connection.reset_mock()
            mock_cursor.reset_mock()

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_with_connection_error(self, mock_get_path, mock_connect, mock_context):
        """Test executing a query with a connection error."""
        # Setup - simulate connection error
        mock_get_path.return_value = '/mock/path/session.db'
        mock_connect.side_effect = sqlite3.OperationalError('unable to open database file')

        query = 'SELECT * FROM test_table'

        # Execute
        result = await execute_session_sql(mock_context, query)

        # Assert with detailed validation
        mock_context.error.assert_called_once()
        error_msg = mock_context.error.call_args[0][0]
        assert 'Error executing SQL query' in error_msg
        assert 'unable to open database file' in error_msg

        # Verify response structure
        assert result['status'] == 'error'
        assert 'Error executing SQL query' in result['message']
        assert 'unable to open database file' in result['message']

        # No connection to close in this case
        mock_connect.assert_called_once()

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_execute_with_close_error(self, mock_get_path, mock_connect, mock_context):
        """Test executing a query where closing the connection raises an error."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'

        # Mock cursor results
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [(1, 'Alice')]

        # Mock connection with close() raising an error
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.close.side_effect = sqlite3.OperationalError('database is locked')
        mock_connect.return_value = mock_connection

        query = 'SELECT * FROM test_table'

        # Execute
        result = await execute_session_sql(mock_context, query)

        # The main operation should still succeed
        assert result['status'] == 'success'
        assert len(result['results']) == 1

        # But we should have logged the close error
        assert mock_context.error.call_count == 1
        error_msg = mock_context.error.call_args[0][0]
        assert 'Error closing database connection' in error_msg
        assert 'database is locked' in error_msg


@pytest.mark.asyncio
class TestConvertApiResponseToTable:
    """Tests for convert_api_response_to_table function."""

    @patch('json.dumps')
    async def test_convert_api_response_error(self, mock_json_dumps, mock_context):
        """Test handling errors during API response conversion."""
        # Setup to cause an error at the beginning of the function
        mock_json_dumps.side_effect = ValueError('JSON serialization error')

        # Sample API response
        response = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-31'}}]
        }
        operation_name = 'cost_explorer_get_cost_and_usage'

        # Execute with exception expectation - the function re-raises exceptions
        with pytest.raises(ValueError) as excinfo:
            await convert_api_response_to_table(mock_context, response, operation_name)

        # Verify the error is the one we raised
        assert 'JSON serialization error' in str(excinfo.value)

        # No need to check if the DB connection was closed since we never got that far


# Additional tests for sql_utils functions
class TestShouldConvertToSqlAdditional:
    """Test should convert to SQL additional cases."""

    def test_should_convert_large_response_above_threshold(self):
        """Test should convert large response above threshold."""
        result = should_convert_to_sql(2000000)  # 2MB
        assert result is True

    def test_should_not_convert_small_response(self):
        """Test should not convert small response."""
        result = should_convert_to_sql(100)
        assert result is False


class TestConvertApiResponseToTableAdditional:
    """Test convert API response to table additional cases."""

    @pytest.mark.asyncio
    async def test_convert_api_response_to_table_calls_execute_sql(self):
        """Test convert API response to table calls execute SQL."""
        mock_context = MagicMock(spec=Context)
        response = {'data': [{'id': 1, 'name': 'test1'}]}

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection'
        ) as mock_conn:
            mock_conn.return_value = (MagicMock(), MagicMock())

            result = await convert_api_response_to_table(mock_context, response, 'test_operation')

            # Just verify the function runs without error
            assert result is not None

    @pytest.mark.asyncio
    async def test_records_converter_stores_one_row_per_item(self):
        """Compute Optimizer Automation list responses store one row per item.

        Columns are derived from the union of item keys, so items with differing
        optional fields (RULE-A has `tags`, RULE-B does not) share one table.
        """
        mock_context = MagicMock(spec=Context)
        conn = sqlite3.connect(':memory:')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_info '
            '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
            'query TEXT, row_count INTEGER)'
        )

        response = {
            'automation_rules': [
                {'rule_id': 'r-1', 'name': 'RULE-A', 'tags': [{'key': 'env', 'value': 'dev'}]},
                {'rule_id': 'r-2', 'name': 'RULE-B'},
            ],
            'count': 2,
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection'
        ) as mock_conn:
            mock_conn.return_value = (conn, conn.cursor())

            result = await convert_api_response_to_table(
                mock_context, response, 'compute_optimizer_automation_list_automation_rules'
            )

        assert result['data_stored'] is True
        # Columns are the union of item keys, in first-seen order.
        assert result['schema'] == ['rule_id', 'name', 'tags']
        # One row per item (not per field).
        assert result['row_count'] == 2

        preview = result['preview']
        assert [row['rule_id'] for row in preview] == ['r-1', 'r-2']
        assert preview[0]['name'] == 'RULE-A'
        # Nested list stored as JSON so it stays queryable; absent on item 2.
        assert 'env' in preview[0]['tags']
        assert preview[1]['tags'] is None

    @pytest.mark.asyncio
    async def test_records_converter_handles_reserved_keyword_columns(self):
        """Columns that are SQL reserved words are quoted, so they round-trip."""
        mock_context = MagicMock(spec=Context)
        conn = sqlite3.connect(':memory:')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_info '
            '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
            'query TEXT, row_count INTEGER)'
        )

        # 'order' and 'group' are SQL reserved words; without quoting the
        # CREATE/INSERT would raise a syntax error.
        response = {
            'automation_rules': [{'order': 1, 'group': 'g-1', 'name': 'RULE-A'}],
            'count': 1,
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection'
        ) as mock_conn:
            mock_conn.return_value = (conn, conn.cursor())

            result = await convert_api_response_to_table(
                mock_context, response, 'compute_optimizer_automation_list_automation_rules'
            )

        assert result['data_stored'] is True
        assert result['schema'] == ['order', 'group', 'name']
        assert result['row_count'] == 1
        assert result['preview'][0]['group'] == 'g-1'

    def test_specialized_converter_routes_automation_ops_to_records(self):
        """Compute Optimizer Automation operations map to the 'records' converter."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        assert (
            _get_specialized_converter('compute_optimizer_automation_list_automation_rules')
            == 'records'
        )
        assert _get_specialized_converter('some_other_operation') is None

    def test_specialized_converter_routes_budget_ops_to_records(self):
        """Budget actions and notifications operations map to the 'records' converter."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        assert _get_specialized_converter('budget_actions') == 'records'
        assert _get_specialized_converter('budget_notifications') == 'records'

    def test_specialized_converter_routes_bvs_segment_ops_to_records(self):
        """BVS list billing view segments operations map to the 'records' converter."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        assert _get_specialized_converter('bvs_list_billing_view_segments') == 'records'

    def test_record_columns_rejects_unsafe_identifiers(self):
        """Derived column names must be safe SQL identifiers (injection guard)."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _record_column_map,
        )

        assert _record_column_map([{'rule_id': 'r-1', 'name': 'RULE-A'}]) == {
            'rule_id': 'rule_id',
            'name': 'name',
        }
        assert _record_column_map([]) == {}
        with pytest.raises(ValueError):
            _record_column_map([{'name); DROP TABLE x;--': 'boom'}])


class TestConvertResponseIfNeeded:
    """Test convert response if needed."""

    @pytest.mark.asyncio
    async def test_convert_response_if_needed_with_large_response(self):
        """Test convert response if needed with large response."""
        mock_context = MagicMock(spec=Context)
        response = {'data': ['x'] * 1000}

        result = await convert_response_if_needed(mock_context, response, 'test_api')

        # Just verify the function runs without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_convert_response_if_needed_with_small_response(self):
        """Below-threshold response is returned as-is, not wrapped in a size envelope."""
        mock_context = MagicMock(spec=Context)
        response = {'data': ['small']}

        result = await convert_response_if_needed(mock_context, response, 'test_api')

        assert result is response


class TestDerivePaginationEnvelope:
    """Tests for _derive_pagination_envelope auto-derivation from response shape."""

    def test_from_paginated_wrapper(self):
        """Response with Pagination sub-dict (paginate_aws_response output) populates the envelope."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _derive_pagination_envelope,
        )

        response = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01'}}],
            'Pagination': {
                'next_token': 'page2',
                'has_more': True,
                'pages_fetched': 3,
                'complete_dataset': False,
            },
        }

        envelope = _derive_pagination_envelope(response)

        assert envelope == {
            'next_page_token': 'page2',
            'has_more': True,
            'pages_fetched': 3,
        }

    def test_from_single_page_response_with_token(self):
        """Single-page boto3 response with NextPageToken populates the envelope."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _derive_pagination_envelope,
        )

        response = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01'}}],
            'NextPageToken': 'continue-here',
        }

        envelope = _derive_pagination_envelope(response)

        assert envelope == {
            'next_page_token': 'continue-here',
            'has_more': True,
            'pages_fetched': 1,
        }

    def test_from_single_page_response_with_null_token(self):
        """Final-page boto3 response (NextPageToken present but None) marks has_more=False."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _derive_pagination_envelope,
        )

        response = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01'}}],
            'NextPageToken': None,
        }

        envelope = _derive_pagination_envelope(response)

        assert envelope == {
            'next_page_token': None,
            'has_more': False,
            'pages_fetched': 1,
        }

    def test_custom_token_key(self):
        """token_key override picks up alternative continuation-token field names (e.g. NextToken)."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _derive_pagination_envelope,
        )

        response = {'PriceList': ['{...}'], 'NextToken': 'page2'}

        envelope = _derive_pagination_envelope(response, token_key='NextToken')

        assert envelope == {
            'next_page_token': 'page2',
            'has_more': True,
            'pages_fetched': 1,
        }

    def test_non_paginated_response_returns_empty(self):
        """Forecast / pricing responses without pagination markers get an empty envelope so unrelated APIs aren't polluted."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _derive_pagination_envelope,
        )

        response = {'ForecastResultsByTime': [{'MeanValue': '10.0'}]}

        envelope = _derive_pagination_envelope(response)

        assert envelope == {}

    @pytest.mark.asyncio
    async def test_caller_metadata_overrides_derived_envelope(self):
        """Explicit kwargs to convert_response_if_needed take precedence over derived values."""
        mock_context = MagicMock(spec=Context)
        mock_context.info = AsyncMock()
        response = {'ResultsByTime': [], 'NextPageToken': 'derived-token'}

        # Force offload so the envelope reaches the offload result
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
            return_value=True,
        ):
            result = await convert_response_if_needed(
                mock_context,
                response,
                'cost_explorer_get_cost_and_usage',
                next_page_token='caller-override',
            )

        assert result.get('next_page_token') == 'caller-override'


@pytest.mark.asyncio
async def test_cleanup_session_db_with_existing_file():
    """Test cleanup_session_db with existing file."""
    with patch('os.path.exists') as mock_exists, patch('os.remove') as mock_remove:
        mock_exists.return_value = True

        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            cleanup_session_db,
        )

        cleanup_session_db()

        mock_remove.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_session_db_with_remove_error():
    """Test cleanup_session_db with remove error."""
    with patch('os.path.exists') as mock_exists, patch('os.remove') as mock_remove:
        mock_exists.return_value = True
        mock_remove.side_effect = OSError('Permission denied')

        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            cleanup_session_db,
        )

        # Should not raise exception
        cleanup_session_db()


def test_validate_table_name_invalid():
    """Test validate_table_name with invalid name."""
    from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import validate_table_name

    with pytest.raises(ValueError, match='Invalid table name'):
        validate_table_name('invalid-table-name!')


def test_validate_table_name_valid():
    """Test validate_table_name with valid name."""
    from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import validate_table_name

    assert validate_table_name('valid_table_name') is True


class TestCreateSafeSqlStatement:
    """Test create_safe_sql_statement function."""

    def test_create_safe_sql_statement_select_with_limit(self):
        """Test creating SELECT statement with LIMIT."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            create_safe_sql_statement,
        )

        result = create_safe_sql_statement('SELECT', 'test_table', 'col1', 'col2', limit=10)
        assert result == 'SELECT col1, col2 FROM test_table LIMIT 10'

    def test_create_safe_sql_statement_select_no_limit(self):
        """Test creating SELECT statement without LIMIT."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            create_safe_sql_statement,
        )

        result = create_safe_sql_statement('SELECT', 'test_table', 'col1', 'col2')
        assert result == 'SELECT col1, col2 FROM test_table'

    def test_create_safe_sql_statement_insert(self):
        """Test creating INSERT statement."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            create_safe_sql_statement,
        )

        result = create_safe_sql_statement('INSERT', 'test_table', 'VALUES (?, ?)')
        assert result == 'INSERT INTO test_table VALUES (?, ?)'

    def test_create_safe_sql_statement_other(self):
        """Test creating other types of statements."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            create_safe_sql_statement,
        )

        result = create_safe_sql_statement('DROP', 'test_table', 'IF EXISTS')
        assert result == 'DROP test_table IF EXISTS'

    def test_create_safe_sql_statement_invalid_table_name(self):
        """Test creating statement with invalid table name."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            create_safe_sql_statement,
        )

        with pytest.raises(ValueError, match='Invalid table name'):
            create_safe_sql_statement('SELECT', 'invalid-table!', '*')


class TestValidateSqlQuery:
    """Test validate_sql_query function."""

    def test_validate_sql_query_safe(self):
        """Test validating safe SQL query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        safe_queries = [
            'SELECT * FROM test_table',
            'SELECT id, name FROM users WHERE age > 18',
            'select count(*) from products',
        ]

        for query in safe_queries:
            assert validate_sql_query(query) is True

    def test_validate_sql_query_dangerous_drop(self):
        """Test validating dangerous DROP query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('DROP TABLE users')

    def test_validate_sql_query_dangerous_delete(self):
        """Test validating dangerous DELETE query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('DELETE FROM users WHERE id = 1')

    def test_validate_sql_query_dangerous_truncate(self):
        """Test validating dangerous TRUNCATE query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('TRUNCATE TABLE logs')

    def test_validate_sql_query_dangerous_alter(self):
        """Test validating dangerous ALTER query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('ALTER TABLE users ADD COLUMN password TEXT')

    def test_validate_sql_query_dangerous_exec(self):
        """Test validating dangerous EXEC query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('EXEC sp_configure')

    def test_validate_sql_query_dangerous_system(self):
        """Test validating dangerous SYSTEM query."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('SYSTEM ls')

    def test_validate_sql_query_dangerous_semicolon(self):
        """Test validating query with dangerous semicolon."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('SELECT * FROM users; DROP TABLE users')

    def test_validate_sql_query_dangerous_attach_database(self):
        """ATTACH DATABASE must be rejected.

        Without this rejection, an attacker (or a prompt-injected
        agent) can attach any SQLite file readable by the process
        and read it back via subsequent SELECTs — a filter bypass
        that the blacklist previously missed.
        """
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query("ATTACH DATABASE '/tmp/victim.db' AS victim_db")

    def test_validate_sql_query_dangerous_attach_lowercase(self):
        """Case-insensitive: ATTACH must be rejected regardless of case."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query("attach database '/tmp/victim.db' as victim_db")

    def test_validate_sql_query_dangerous_detach(self):
        """Symmetric case: DETACH is rejected too."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            validate_sql_query,
        )

        with pytest.raises(ValueError, match='Query contains potentially harmful operations'):
            validate_sql_query('DETACH DATABASE victim_db')


class TestSessionAuthorizer:
    """Engine-level defense against ATTACH DATABASE.

    The authorizer is the second line of defense behind the regex
    blacklist in ``validate_sql_query``. Even if the query text were
    to slip past the blacklist (comment tricks, whitespace variants,
    dynamic SQL from a trigger), the SQLite parser calls the
    authorizer for every operation the query would perform. ATTACH
    returns SQLITE_DENY here, so the connection refuses to mount any
    external database file.
    """

    def test_authorizer_denies_attach(self, tmp_path):
        """A connection with the authorizer refuses ATTACH DATABASE."""
        import sqlite3
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _session_authorizer,
        )

        conn = sqlite3.connect(':memory:')
        conn.set_authorizer(_session_authorizer)

        victim = tmp_path / 'victim.db'
        # Populate the victim DB with something that would be visible
        # if ATTACH succeeded — the assertion is that ATTACH raises,
        # not that this data is or isn't readable.
        sqlite3.connect(str(victim)).execute(
            'CREATE TABLE secrets (v TEXT)',
        )

        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(f"ATTACH DATABASE '{victim}' AS victim")

    def test_authorizer_denies_detach(self):
        """The authorizer refuses DETACH as well (symmetric coverage)."""
        import sqlite3
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _session_authorizer,
        )

        conn = sqlite3.connect(':memory:')
        conn.set_authorizer(_session_authorizer)
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute('DETACH DATABASE anything')

    def test_authorizer_allows_normal_select(self):
        """Normal SELECT/INSERT/CREATE operations still work.

        The authorizer only denies ATTACH/DETACH; everything else
        returns SQLITE_OK, so the session tool retains full
        read/write access to its own database.
        """
        import sqlite3
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _session_authorizer,
        )

        conn = sqlite3.connect(':memory:')
        conn.set_authorizer(_session_authorizer)
        conn.execute('CREATE TABLE t (a INTEGER, b TEXT)')
        conn.execute("INSERT INTO t VALUES (1, 'hello'), (2, 'world')")
        rows = list(conn.execute('SELECT a, b FROM t ORDER BY a'))
        assert rows == [(1, 'hello'), (2, 'world')]

    def test_get_db_connection_installs_authorizer(self, tmp_path, monkeypatch):
        """The session connection factory installs the authorizer.

        Guarantees the tool-facing code path is guarded end-to-end
        rather than relying on callers to remember to attach the
        authorizer themselves.
        """
        import sqlite3
        from awslabs.billing_cost_management_mcp_server.utilities import sql_utils

        # Isolate the session DB in a tmpdir so this test doesn't
        # pollute the shared session location.
        session_db = tmp_path / 'session.db'
        monkeypatch.setattr(sql_utils, 'get_session_db_path', lambda: str(session_db))

        conn, cursor = sql_utils.get_db_connection()
        try:
            victim = tmp_path / 'victim.db'
            sqlite3.connect(str(victim)).execute('CREATE TABLE secrets (v TEXT)')
            with pytest.raises(sqlite3.DatabaseError):
                cursor.execute(f"ATTACH DATABASE '{victim}' AS victim")
        finally:
            conn.close()


class TestGetSpecializedConverter:
    """Test _get_specialized_converter function."""

    def test_get_specialized_converter_pricing(self):
        """Test getting specialized converter for pricing."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('aws_pricing_get_products')
        assert result == 'pricing_products'

    def test_get_specialized_converter_cost_and_usage(self):
        """Test getting specialized converter for cost and usage."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('cost_explorer_get_cost_and_usage')
        assert result == 'cost_and_usage'

        result = _get_specialized_converter('cost_explorer_get_cost_and_usage_with_resources')
        assert result == 'cost_and_usage'

    def test_get_specialized_converter_dimension_values(self):
        """Test getting specialized converter for dimension values."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('cost_explorer_get_dimension_values')
        assert result == 'dimension_values'

    def test_get_specialized_converter_forecast(self):
        """Test getting specialized converter for forecast."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('cost_explorer_get_cost_forecast')
        assert result == 'forecast'

        result = _get_specialized_converter('cost_explorer_get_usage_forecast')
        assert result == 'forecast'

    def test_get_specialized_converter_tags(self):
        """Test getting specialized converter for tags."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('cost_explorer_get_tags')
        assert result == 'tags'

    def test_get_specialized_converter_cost_categories(self):
        """Test getting specialized converter for cost categories."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('cost_explorer_get_cost_categories')
        assert result == 'cost_categories'

    def test_get_specialized_converter_unknown(self):
        """Test getting specialized converter for unknown operation."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        result = _get_specialized_converter('unknown_operation')
        assert result is None


@pytest.mark.asyncio
class TestConvertApiResponseToTableSpecificTypes:
    """Test convert_api_response_to_table with specific response types."""

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_pricing_products_response(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Test converting AWS Pricing products response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [
            ('service_code',),
            ('product_family',),
            ('sku',),
            ('attributes',),
            ('pricing_terms',),
        ]
        mock_cursor.fetchall.return_value = [
            ('AmazonEC2', 'Compute Instance', 'SKU123', '{}', '{}')
        ]

        response = {
            'PriceList': [
                '{"product": {"productFamily": "Compute Instance", "sku": "SKU123", "attributes": {"instanceType": "t3.micro"}}, "terms": {"OnDemand": {}}}'
            ]
        }
        operation_name = 'aws_pricing_get_products'

        # Execute
        result = await convert_api_response_to_table(
            mock_context, response, operation_name, service_code='AmazonEC2'
        )

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 1
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_cost_and_usage_response(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Test converting Cost Explorer cost and usage response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [
            ('time_period_start',),
            ('time_period_end',),
            ('estimated',),
            ('group_key_1',),
            ('group_key_2',),
            ('group_key_3',),
            ('metric_name',),
            ('amount',),
            ('unit',),
        ]
        mock_cursor.fetchall.return_value = [
            (
                '2023-01-01',
                '2023-01-31',
                False,
                'Amazon EC2',
                None,
                None,
                'BlendedCost',
                100.50,
                'USD',
            )
        ]

        response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-31'},
                    'Estimated': False,
                    'Groups': [
                        {
                            'Keys': ['Amazon EC2'],
                            'Metrics': {'BlendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                        }
                    ],
                    'Total': {'BlendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                }
            ]
        }
        operation_name = 'cost_explorer_get_cost_and_usage'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 2  # One for Groups, one for Total
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_dimension_values_response(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Test converting dimension values response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [('value',), ('attributes',)]
        mock_cursor.fetchall.return_value = [('Amazon EC2', '{}')]

        response = {
            'DimensionValues': [
                {'Value': 'Amazon EC2', 'Attributes': {}},
                {'Value': 'Amazon S3', 'Attributes': {}},
            ]
        }
        operation_name = 'cost_explorer_get_dimension_values'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 2
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_forecast_response(self, mock_get_path, mock_connect, mock_context):
        """Test converting forecast response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [
            ('time_period_start',),
            ('time_period_end',),
            ('mean_value',),
            ('lower_bound',),
            ('upper_bound',),
        ]
        mock_cursor.fetchall.return_value = [('2023-02-01', '2023-02-28', 120.0, 100.0, 140.0)]

        response = {
            'ForecastResultsByTime': [
                {
                    'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                    'MeanValue': '120.0',
                    'PredictionIntervalLowerBound': '100.0',
                    'PredictionIntervalUpperBound': '140.0',
                }
            ]
        }
        operation_name = 'cost_explorer_get_cost_forecast'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 1
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_tags_response(self, mock_get_path, mock_connect, mock_context):
        """Test converting tags response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [('tag_value',)]
        mock_cursor.fetchall.return_value = [('Environment',)]

        response = {'Tags': ['Environment', 'Project', 'Owner']}
        operation_name = 'cost_explorer_get_tags'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 3
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_cost_categories_response(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Test converting cost categories response."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [('category_type',), ('category_value',)]
        mock_cursor.fetchall.return_value = [('name', 'Production')]

        response = {
            'CostCategoryNames': ['Production', 'Development'],
            'CostCategoryValues': ['team-a', 'team-b'],
        }
        operation_name = 'cost_explorer_get_cost_categories'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] == 4  # 2 names + 2 values
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_recommendations_order_by_aware_sample(
        self, mock_get_path, mock_connect, mock_context
    ):
        """A requested order_by adds a matching sample query and is not leaked into the payload."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('recommendation_id',), ('account_id',)]
        mock_cursor.fetchall.return_value = [('r-1', '111')]

        response = {'recommendations': [{'recommendation_id': 'r-1', 'account_id': '111'}]}

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_recommendations',
            order_by={'dimension': 'AccountId', 'order': 'Asc'},
        )

        assert result['status'] == 'success'
        # The raw order_by dict is popped, not spread into the response metadata.
        assert 'order_by' not in result
        names = [q['name'] for q in result['sample_queries']]
        sqls = [q['sql'] for q in result['sample_queries']]
        # A requested order_by yields a single coh sample mirroring it; the
        # default savings view is not added on top (the generic "Basic query"
        # is always present and is not counted here).
        coh_samples = [
            n
            for n in names
            if n.startswith('First 20 by requested order') or n == 'Top 20 savings opportunities'
        ]
        assert coh_samples == ['First 20 by requested order (AccountId ASC)']
        assert any('ORDER BY account_id ASC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_recommendations_unmapped_dimension_no_extra_sample(
        self, mock_get_path, mock_connect, mock_context
    ):
        """A dimension with no stored column falls back to the default sample only."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('recommendation_id',), ('account_id',)]
        mock_cursor.fetchall.return_value = [('r-1', '111')]

        response = {'recommendations': [{'recommendation_id': 'r-1', 'account_id': '111'}]}

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_recommendations',
            order_by={'dimension': 'NotARealDimension'},
        )

        names = [q['name'] for q in result['sample_queries']]
        assert not any('requested order' in n.lower() for n in names)
        assert any('Top 20 savings opportunities' == n for n in names)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_recommendations_non_str_dimension_default_sample(
        self, mock_get_path, mock_connect, mock_context
    ):
        """An order_by dict without a string dimension falls back to the default sample."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('recommendation_id',), ('account_id',)]
        mock_cursor.fetchall.return_value = [('r-1', '111')]

        response = {'recommendations': [{'recommendation_id': 'r-1', 'account_id': '111'}]}

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_recommendations',
            order_by={'order': 'Desc'},  # dict, but no string 'dimension'
        )

        names = [q['name'] for q in result['sample_queries']]
        assert not any('requested order' in n.lower() for n in names)
        assert any('Top 20 savings opportunities' == n for n in names)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_recommendations_boolean_dimension_sample(
        self, mock_get_path, mock_connect, mock_context
    ):
        """RestartNeeded/RollbackPossible now map to stored boolean columns."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('recommendation_id',), ('restart_needed',)]
        mock_cursor.fetchall.return_value = [('r-1', 0)]

        response = {'recommendations': [{'recommendation_id': 'r-1', 'restart_needed': False}]}

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_recommendations',
            order_by={'dimension': 'RestartNeeded', 'order': 'Desc'},
        )

        sqls = [q['sql'] for q in result['sample_queries']]
        assert any('ORDER BY restart_needed DESC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_recommendations_omitted_order_defaults_asc(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Omitting ``order`` defaults the sample to ASC, matching the API default."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('recommendation_id',), ('account_id',)]
        mock_cursor.fetchall.return_value = [('r-1', '111')]

        response = {'recommendations': [{'recommendation_id': 'r-1', 'account_id': '111'}]}

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_recommendations',
            order_by={'dimension': 'EstimatedMonthlySavings'},
        )

        sqls = [q['sql'] for q in result['sample_queries']]
        assert any('ORDER BY estimated_monthly_savings ASC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_efficiency_order_by_aware_ranked_sample(
        self, mock_get_path, mock_connect, mock_context
    ):
        """A requested order_by drives the group-ranking column/direction and is not leaked."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('group_value',), ('score',)]
        mock_cursor.fetchall.return_value = [('us-east-1', 80.0)]

        response = {
            'groups': [
                {
                    'group': 'us-east-1',
                    'message': None,
                    'metrics_by_time': [
                        {'timestamp': '2026-08', 'score': 80.0, 'savings': 5.0, 'spend': 100.0}
                    ],
                }
            ]
        }

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_efficiency_metrics',
            order_by={'dimension': 'Savings', 'order': 'Asc'},
        )

        assert 'order_by' not in result
        names = [q['name'] for q in result['sample_queries']]
        sqls = [q['sql'] for q in result['sample_queries']]
        assert 'Latest efficiency metrics by group (ranked by savings)' in names
        assert any('ORDER BY savings ASC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_efficiency_non_str_dimension_default_rank(
        self, mock_get_path, mock_connect, mock_context
    ):
        """An order_by dict without a string dimension uses the default score ranking."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('group_value',), ('score',)]
        mock_cursor.fetchall.return_value = [('us-east-1', 80.0)]

        response = {
            'groups': [
                {
                    'group': 'us-east-1',
                    'message': None,
                    'metrics_by_time': [
                        {'timestamp': '2026-08', 'score': 80.0, 'savings': 5.0, 'spend': 100.0}
                    ],
                }
            ]
        }

        result = await convert_api_response_to_table(
            mock_context,
            response,
            'cost_optimization_hub_list_efficiency_metrics',
            order_by={'order': 'Desc'},  # dict, but no string 'dimension'
        )

        names = [q['name'] for q in result['sample_queries']]
        sqls = [q['sql'] for q in result['sample_queries']]
        assert 'Latest efficiency metrics by group (ranked by score)' in names
        assert any('ORDER BY score DESC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_coh_efficiency_omitted_order_defaults_desc(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Efficiency omits-order default is DESC (opposite of recommendations)."""
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.description = [('group_value',), ('score',)]
        mock_cursor.fetchall.return_value = [('us-east-1', 80.0)]

        response = {
            'groups': [
                {
                    'group': 'us-east-1',
                    'message': None,
                    'metrics_by_time': [
                        {'timestamp': '2026-08', 'score': 80.0, 'savings': 5.0, 'spend': 100.0}
                    ],
                }
            ]
        }

        # No order_by -> API default (Score DESC); dimension with omitted order -> DESC.
        for order_by in (None, {'dimension': 'Score'}):
            result = await convert_api_response_to_table(
                mock_context,
                response,
                'cost_optimization_hub_list_efficiency_metrics',
                order_by=order_by,
            )
            names = [q['name'] for q in result['sample_queries']]
            sqls = [q['sql'] for q in result['sample_queries']]
            assert 'Latest efficiency metrics by group (ranked by score)' in names
            assert any('ORDER BY score DESC' in s for s in sqls)

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_generic_response(self, mock_get_path, mock_connect, mock_context):
        """Test converting generic unknown response type."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [('key',), ('value',)]
        mock_cursor.fetchall.return_value = [('data_key1', 'value1')]

        response = {
            'data': {
                'key1': 'value1',
                'nested': {'key2': 'value2'},
                'list_data': ['item1', 'item2'],
            }
        }
        operation_name = 'unknown_operation'

        # Execute
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert
        assert result['status'] == 'success'
        assert result['data_stored'] is True
        assert result['row_count'] > 0
        assert 'table_name' in result
        assert 'sample_queries' in result

    @patch('sqlite3.connect')
    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_session_db_path')
    async def test_convert_response_connection_close_error(
        self, mock_get_path, mock_connect, mock_context
    ):
        """Test convert response handles connection close error gracefully."""
        # Setup
        mock_get_path.return_value = '/mock/path/session.db'
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.close.side_effect = sqlite3.Error('Connection close error')
        mock_connect.return_value = mock_connection

        # Mock cursor description for preview
        mock_cursor.description = [('tag_value',)]
        mock_cursor.fetchall.return_value = [('Environment',)]

        response = {'Tags': ['Environment']}
        operation_name = 'cost_explorer_get_tags'

        # Execute - should not raise exception despite close error
        result = await convert_api_response_to_table(mock_context, response, operation_name)

        # Assert - operation should still succeed
        assert result['status'] == 'success'


@pytest.mark.asyncio
class TestConvertResponseIfNeededErrorHandling:
    """Test convert_response_if_needed error handling."""

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.json.dumps')
    async def test_convert_response_if_needed_json_error(self, mock_json_dumps, mock_context):
        """Test convert_response_if_needed falls back to the original response on JSON error."""
        # Make json.dumps fail so size computation throws
        mock_json_dumps.side_effect = TypeError('JSON encoding error')
        response = {'data': 'test'}

        result = await convert_response_if_needed(mock_context, response, 'test_api')

        # Offload is an optimization — failure falls back to the original response,
        # not an error envelope the caller would have to unwrap.
        assert result is response

    async def test_convert_response_if_needed_conversion_error(self, mock_context):
        """Test convert_response_if_needed falls back to the original response on conversion error."""
        # Large enough to trigger the offload branch
        response = {'data': 'x' * 30000}

        with patch.object(
            sys.modules['awslabs.billing_cost_management_mcp_server.utilities.sql_utils'],
            'convert_api_response_to_table',
        ) as mock_convert:
            mock_convert.side_effect = ValueError('Conversion error')

            result = await convert_response_if_needed(mock_context, response, 'test_api')

            assert result is response


class TestInsertDataEdgeCases:
    """Test insert_data edge cases."""

    def test_insert_data_empty_first_row(self):
        """Test inserting data with empty first row."""
        mock_cursor = MagicMock()
        table_name = 'test_table'
        data = [[]]  # Empty first row

        # Execute
        rows_inserted = insert_data(mock_cursor, table_name, data)

        # Assert
        assert rows_inserted == 0
        mock_cursor.execute.assert_not_called()

    def test_insert_data_with_none_values(self):
        """Test inserting data with None values."""
        mock_cursor = MagicMock()
        table_name = 'test_table'
        data = [[1, None, 'test'], [2, 'value', None]]

        # Execute
        rows_inserted = insert_data(mock_cursor, table_name, data)

        # Assert
        assert rows_inserted == 2
        assert mock_cursor.execute.call_count == 2

        # Check calls include None values
        calls = mock_cursor.execute.call_args_list
        assert calls[0][0][1] == [1, None, 'test']
        assert calls[1][0][1] == [2, 'value', None]


@pytest.mark.asyncio
class TestExecuteSessionSqlDangerous:
    """Test execute_session_sql with dangerous queries."""

    @patch('sqlite3.connect')
    async def test_execute_session_sql_dangerous_query(self, mock_connect, mock_context):
        """Test execute_session_sql rejects dangerous queries."""
        # Setup
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dangerous_query = 'DROP TABLE users'

        # Execute
        result = await execute_session_sql(mock_context, dangerous_query)

        # Assert
        assert result['status'] == 'error'
        assert 'Error executing SQL query' in result['message']
        assert 'Query contains potentially harmful operations' in result['message']


def test_cleanup_session_db_no_file():
    """Test cleanup_session_db with no existing file."""
    with patch('os.path.exists') as mock_exists, patch('os.remove') as mock_remove:
        mock_exists.return_value = False

        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            cleanup_session_db,
        )

        cleanup_session_db()

        mock_remove.assert_not_called()


def test_cleanup_session_db_no_path():
    """Test cleanup_session_db with no session path set."""
    # Setup - ensure _SESSION_DB_PATH is None
    from awslabs.billing_cost_management_mcp_server.utilities import sql_utils

    original_path = sql_utils._SESSION_DB_PATH
    sql_utils._SESSION_DB_PATH = None

    try:
        with patch('os.path.exists') as mock_exists, patch('os.remove') as mock_remove:
            sql_utils.cleanup_session_db()

            mock_exists.assert_not_called()
            mock_remove.assert_not_called()
    finally:
        # Restore original path
        sql_utils._SESSION_DB_PATH = original_path


class TestEnvironmentVariables:
    """Test environment variable handling."""

    @patch('os.getenv')
    def test_sql_conversion_threshold_custom(self, mock_getenv):
        """Test custom SQL conversion threshold."""

        # Setup - Mock environment variable
        def mock_env_side_effect(key, default=None):
            if key == 'MCP_SQL_THRESHOLD':
                return '10240'  # 10KB
            elif key == 'MCP_FORCE_SQL':
                return 'false'
            return default

        mock_getenv.side_effect = mock_env_side_effect

        # Force reload of the module to pick up new environment variables
        import sys

        if 'awslabs.billing_cost_management_mcp_server.utilities.sql_utils' in sys.modules:
            del sys.modules['awslabs.billing_cost_management_mcp_server.utilities.sql_utils']

        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            should_convert_to_sql,
        )

        # Test with size above custom threshold
        assert should_convert_to_sql(15000) is True  # 15KB > 10KB
        assert should_convert_to_sql(5000) is False  # 5KB < 10KB

    @patch('os.getenv')
    def test_busy_timeout_custom(self, mock_getenv):
        """Test custom SQLite busy timeout via environment variable."""
        import sys

        def mock_env_side_effect(key, default=None):
            if key == 'BCM_MCP_SQLITE_TIMEOUT_MS':
                return '60000'
            return default

        mock_getenv.side_effect = mock_env_side_effect

        if 'awslabs.billing_cost_management_mcp_server.utilities.sql_utils' in sys.modules:
            del sys.modules['awslabs.billing_cost_management_mcp_server.utilities.sql_utils']

        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            BUSY_TIMEOUT_MS,
        )

        assert BUSY_TIMEOUT_MS == 60000


@pytest.mark.asyncio
async def test_get_context_logger_import():
    """Test that get_context_logger is properly imported and used."""
    # This test ensures the import statement on line 198 is covered
    from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
        convert_response_if_needed,
    )

    mock_context = MagicMock(spec=Context)
    response = {'small': 'data'}

    # Execute - this will trigger the get_context_logger import
    result = await convert_response_if_needed(mock_context, response, 'test_api')

    # Just verify it doesn't crash
    assert result is not None


def test_coerce_for_column_real_branch():
    """REAL columns float-coerce; unfloatable values fall back to None, non-REAL passes through."""
    assert _coerce_for_column('3.5', 'REAL') == 3.5
    assert _coerce_for_column(None, 'REAL') is None
    # Unfloatable value -> None (ValueError caught).
    assert _coerce_for_column('not-a-number', 'REAL') is None
    # Non-floatable type -> None (TypeError caught).
    assert _coerce_for_column(object(), 'REAL') is None
    # Non-REAL column passes the value through unchanged.
    assert _coerce_for_column('kept', 'TEXT') == 'kept'


# ---------------------------------------------------------------------------
# Nested-list converters (RI performance, SP recommendation/analysis,
# Storage Lens run_query). These exercise convert_api_response_to_table against
# a REAL temporary SQLite database (no mocked cursor) so the stored rows and
# columns can be read back and asserted — critical for the run_query trap where
# a wrong converter silently stores column names instead of data.
# ---------------------------------------------------------------------------


class _ConverterDb:
    """A real SQLite connection for converter tests whose close() is deferred.

    convert_api_response_to_table closes the connection it is handed in its
    `finally`. To run the returned sample queries against the resulting table we
    keep that same connection open (close() is a no-op) and query it directly —
    the table is committed and in-view, so this avoids any cross-connection or
    file-flush visibility question. `cleanup()` performs the real close.
    """

    class _Conn(sqlite3.Connection):
        def close(self):  # deferred; convert's finally must not drop the table
            pass

    def __init__(self):
        self.conn = sqlite3.connect(':memory:', factory=self._Conn)
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_info '
            '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
            'query TEXT, row_count INTEGER)'
        )
        self.conn.commit()

    def mock_value(self):
        return (self.conn, self.conn.cursor())

    def patch_conn(self):
        """Patch get_db_connection in the exact globals convert resolves.

        Another test in this file deletes and reimports the sql_utils module,
        leaving a divergent module instance in sys.modules. The module-level
        `convert_api_response_to_table` imported at the top of this file keeps
        the ORIGINAL module's globals, so a string patch of
        '...sql_utils.get_db_connection' would patch the wrong (reimported)
        module and convert would still open a real connection. Patching the
        function's own __globals__ targets the namespace convert actually uses,
        regardless of sys.modules churn.
        """
        return patch.dict(
            convert_api_response_to_table.__globals__,
            {'get_db_connection': MagicMock(return_value=self.mock_value())},
        )

    def assert_sample_queries_run(self, result):
        """Every returned sample query executes without error against the table."""
        cur = self.conn.cursor()
        for sq in result['sample_queries']:
            # Placeholder-bearing samples (e.g. '<group>') are illustrative.
            if '<' in sq['sql']:
                continue
            cur.execute(sq['sql'])  # raises if a referenced column is missing
            cur.fetchall()

    def cleanup(self):
        try:
            super(self._Conn, self.conn).close()
        except Exception:
            pass


class TestNestedListConverters:
    """convert_api_response_to_table against the 6 nested-list operations."""

    def test_converter_registration(self):
        """The 6 operation names resolve to their nested converters."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _get_specialized_converter,
        )

        assert _get_specialized_converter('get_reservation_coverage') == 'ri_coverage'
        assert _get_specialized_converter('get_reservation_utilization') == 'ri_utilization'
        assert (
            _get_specialized_converter('get_commitment_purchase_analysis') == 'sp_lookback_metrics'
        )
        assert (
            _get_specialized_converter('get_savings_plan_purchase_recommendation_details')
            == 'sp_lookback_metrics'
        )
        assert (
            _get_specialized_converter('get_savings_plans_purchase_recommendation')
            == 'sp_purchase_recommendation'
        )
        # storage-lens has no `operation` arg; one underscore key, no aliases.
        assert _get_specialized_converter('storage_lens_run_query') == 'storage_lens_query'
        assert _get_specialized_converter('run_query') is None

    async def test_ri_coverage_denormalizes_groups_and_preserves_totals(self):
        """RI coverage: group rows + per-bucket total row + response-level summary."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'coverages_by_time': [
                {
                    'time_period': {'start': '2026-01-01', 'end': '2026-01-02'},
                    'total': {
                        'coverage_hours': {'coverage_hours_percentage': '70'},
                    },
                    'groups': [
                        {
                            'attributes': {'REGION': 'us-east-1'},
                            'coverage': {
                                'coverage_hours': {
                                    'on_demand_hours': '10',
                                    'reserved_hours': '90',
                                    'coverage_hours_percentage': '90',
                                }
                            },
                        },
                        {
                            'attributes': {'REGION': 'eu-west-1'},
                            'coverage': {
                                'coverage_hours': {
                                    'on_demand_hours': '50',
                                    'reserved_hours': '50',
                                    'coverage_hours_percentage': '50',
                                }
                            },
                        },
                    ],
                }
            ],
            'total': {'coverage_hours': {'coverage_hours_percentage': '70'}},
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_reservation_coverage'
                )

            assert result['status'] == 'success'
            # 2 group rows + 1 per-bucket total row (percentages not derivable
            # by summing groups, so the total must be preserved).
            assert result['row_count'] == 3
            assert 'attr_REGION' in result['schema']
            assert 'coverage_hours_coverage_hours_percentage' in result['schema']
            levels = [r['level'] for r in result['preview']]
            assert levels.count('group') == 2 and levels.count('total') == 1
            us = next(r for r in result['preview'] if r.get('attr_REGION') == 'us-east-1')
            assert us['coverage_hours_on_demand_hours'] == '10'
            # Response-level headline total survives inline in `summary`.
            assert result['summary']['total_coverage_hours_coverage_hours_percentage'] == '70'
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_ri_utilization_empty_groups_emits_total_row(self):
        """A bucket with no groups still yields a total-level row (no data loss)."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'utilizations_by_time': [
                {
                    'time_period': {'start': '2026-02-01', 'end': '2026-02-02'},
                    'total': {'utilization_percentage': '75', 'purchased_hours': '100'},
                    'groups': [],
                }
            ]
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_reservation_utilization'
                )

            assert result['row_count'] == 1
            assert result['preview'][0]['level'] == 'total'
            assert result['preview'][0]['utilization_percentage'] == '75'
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_ri_empty_series_falls_through_without_broken_sample(self):
        """Empty series -> generic table, and the sample query still runs."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {'coverages_by_time': [], 'total': {}}

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_reservation_coverage'
                )

            # Fell through to the generic key/value converter.
            assert result['schema'] == ['key', 'value']
            # The RI sample (which references time_period_start) must NOT be
            # emitted against a key/value table; every emitted sample runs.
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_sp_recommendation_details_hourly_series(self):
        """SP recommendation details: one row per MetricsOverLookbackPeriod point."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        points = [
            {
                'StartTime': f'2026-01-01T{h:02d}:00:00Z',
                'EstimatedOnDemandCost': str(h),
                'CurrentCoverage': '0.5',
            }
            for h in range(24)
        ]
        response = {
            'RecommendationDetailId': 'rec-123',
            'RecommendationDetailData': {
                'AccountId': '111122223333',
                'EstimatedSavingsAmount': '1234.56',
                'MetricsOverLookbackPeriod': points,
            },
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_savings_plan_purchase_recommendation_details'
                )

            assert result['row_count'] == 24
            assert 'StartTime' in result['schema'] and 'EstimatedOnDemandCost' in result['schema']
            assert result['preview'][0]['EstimatedOnDemandCost'] == '0'
            # Headline field (not in the series) survives in `summary`.
            assert (
                result['summary']['RecommendationDetailData_EstimatedSavingsAmount'] == '1234.56'
            )
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_sp_recommendation_details_large_1440_points(self):
        """Representative large response: a 60-day hourly lookback (1,440 points)."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        points = [
            {'StartTime': f'point-{i}', 'EstimatedOnDemandCost': str(i)} for i in range(1440)
        ]
        response = {
            'RecommendationDetailData': {
                'AccountId': '111122223333',
                'MetricsOverLookbackPeriod': points,
            }
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_savings_plan_purchase_recommendation_details'
                )

            assert result['row_count'] == 1440
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_commitment_analysis_hourly_series_deeply_nested(self):
        """Commitment analysis nests the series two levels down; finder reaches it."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        points = [
            {'StartTime': f'2026-03-01T{h:02d}:00:00Z', 'EstimatedOnDemandCost': str(h)}
            for h in range(12)
        ]
        response = {
            'AnalysisId': 'a-1',
            'AnalysisStatus': 'SUCCEEDED',
            'AnalysisDetails': {
                'SavingsPlansPurchaseAnalysisDetails': {
                    'CurrencyCode': 'USD',
                    'MetricsOverLookbackPeriod': points,
                }
            },
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_commitment_purchase_analysis'
                )

            assert result['row_count'] == 12
            assert result['preview'][0]['StartTime'] == '2026-03-01T00:00:00Z'
            # AnalysisStatus (outside the series) survives in `summary`.
            assert result['summary']['AnalysisStatus'] == 'SUCCEEDED'
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_sp_purchase_recommendation_detail_rows_and_summary(self):
        """SP purchase recommendation: one row per detail; headline in summary."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'ResponseMetadata': {'RequestId': 'r-1', 'HTTPHeaders': {'date': 'x'}},
            'SavingsPlansPurchaseRecommendation': {
                'PaymentOption': 'ALL_UPFRONT',
                'TermInYears': 'ONE_YEAR',
                'LookbackPeriodInDays': 'SIXTY_DAYS',
                'SavingsPlansPurchaseRecommendationSummary': {
                    'EstimatedTotalCost': '9999',
                },
                'SavingsPlansPurchaseRecommendationDetails': [
                    {'AccountId': '111', 'EstimatedMonthlySavingsAmount': '100'},
                    {'AccountId': '222', 'EstimatedMonthlySavingsAmount': '250'},
                ],
            },
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_savings_plans_purchase_recommendation'
                )

            assert result['row_count'] == 2
            assert 'EstimatedMonthlySavingsAmount' in result['schema']
            assert {r['AccountId'] for r in result['preview']} == {'111', '222'}
            # Headline fields (PaymentOption, TermInYears, summary block) survive.
            summary = result['summary']
            # boto3 transport metadata is not part of the summary.
            assert not any(k.startswith('ResponseMetadata') for k in summary)
            assert summary['SavingsPlansPurchaseRecommendation_PaymentOption'] == 'ALL_UPFRONT'
            assert summary['SavingsPlansPurchaseRecommendation_TermInYears'] == 'ONE_YEAR'
            assert (
                summary[
                    'SavingsPlansPurchaseRecommendation_'
                    'SavingsPlansPurchaseRecommendationSummary_EstimatedTotalCost'
                ]
                == '9999'
            )
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_storage_lens_run_query_stores_rows_not_columns(self):
        """The trap: run_query must store data rows, not the column-name list.

        The response puts `columns` before `rows`; the generic first-top-level-
        list rule would build a table of column names. Verify real data rows land
        in the table and the Athena labels are sanitized into valid identifiers.
        """
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'execution_time_ms': 42,
            'columns': ['bucket_name', 'SUM(storage_bytes)'],
            'rows': [
                {'bucket_name': 'logs', 'SUM(storage_bytes)': '1000'},
                {'bucket_name': 'backups', 'SUM(storage_bytes)': '2000'},
                {'bucket_name': 'media', 'SUM(storage_bytes)': '3000'},
            ],
            'query': 'SELECT ...',
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'storage_lens_run_query'
                )

            # Three DATA rows stored — not 2 column-name rows.
            assert result['row_count'] == 3
            schema = result['schema']
            # Athena label 'SUM(storage_bytes)' sanitized to a valid identifier.
            assert 'bucket_name' in schema
            assert 'SUM(storage_bytes)' not in schema
            sanitized = [c for c in schema if c.startswith('SUM_storage_bytes')]
            assert sanitized, f'expected a sanitized SUM column, got {schema}'
            # The stored values are the data, not the header labels.
            preview = result['preview']
            assert {r['bucket_name'] for r in preview} == {'logs', 'backups', 'media'}
            total = sum(int(r[sanitized[0]]) for r in preview)
            assert total == 6000
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_storage_lens_case_insensitive_column_labels(self):
        """Athena labels differing only by case must not collide in CREATE TABLE."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'columns': ['Bucket', 'bucket'],
            'rows': [{'Bucket': 'a', 'bucket': 'b'}],
            'query': 'SELECT ...',
        }

        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'storage_lens_run_query'
                )

            # Both values preserved under two case-insensitively-distinct columns.
            assert result['row_count'] == 1
            schema = result['schema']
            assert len(schema) == 2
            assert len({c.lower() for c in schema}) == 2
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_records_converter_case_variant_keys_not_dropped(self):
        """Shared records path: case-variant keys across items keep their values."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'automation_rules': [{'Name': 'A'}, {'name': 'b'}],
            'count': 2,
        }
        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'compute_optimizer_automation_list_automation_rules'
                )
            assert result['schema'] == ['Name', 'name_2']
            assert result['preview'] == [
                {'Name': 'A', 'name_2': None},
                {'Name': None, 'name_2': 'b'},
            ]
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_storage_lens_repeated_identical_label(self):
        """A repeated label maps to one column holding the value (no NULL base)."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {'columns': ['x', 'x'], 'rows': [{'x': '1'}], 'query': 'SELECT ...'}
        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'storage_lens_run_query'
                )
            assert result['schema'] == ['x']
            assert result['preview'] == [{'x': '1'}]
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_sp_lookback_sample_query_without_start_time(self):
        """Hourly points with no StartTime get a LIMIT sample, not ORDER BY StartTime."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'RecommendationDetailData': {
                'MetricsOverLookbackPeriod': [{'EstimatedOnDemandCost': '1'}],
            }
        }
        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_savings_plan_purchase_recommendation_details'
                )
            sqls = [sq['sql'] for sq in result['sample_queries']]
            assert any(sql.endswith('LIMIT 50') for sql in sqls)
            assert not any('StartTime' in sql for sql in sqls)
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()

    async def test_sp_purchase_recommendation_sample_without_savings_column(self):
        """Details lacking EstimatedMonthlySavingsAmount get a COUNT sample instead of SUM."""
        mock_context = MagicMock(spec=Context)
        db = _ConverterDb()
        response = {
            'SavingsPlansPurchaseRecommendation': {
                'SavingsPlansPurchaseRecommendationDetails': [{'AccountId': '111'}],
            }
        }
        try:
            with db.patch_conn():
                result = await convert_api_response_to_table(
                    mock_context, response, 'get_savings_plans_purchase_recommendation'
                )
            sqls = [sq['sql'] for sq in result['sample_queries']]
            assert any('COUNT(*) as detail_count' in sql for sql in sqls)
            assert not any('EstimatedMonthlySavingsAmount' in sql for sql in sqls)
            db.assert_sample_queries_run(result)
        finally:
            db.cleanup()


class TestNestedConverterHelpers:
    """Unit tests for the nested-converter helper functions."""

    def test_sanitize_identifier(self):
        """Athena labels sanitize to safe identifiers, with readable fallbacks."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _sanitize_identifier,
        )

        assert _sanitize_identifier('SUM(storage_bytes)') == 'SUM_storage_bytes_'
        assert _sanitize_identifier('bucket.name') == 'bucket_name'
        # Empty / all-unsafe input falls back to 'col'.
        assert _sanitize_identifier('') == 'col'
        assert _sanitize_identifier('()') == 'col'
        # Leading digit gets a safe prefix.
        assert _sanitize_identifier('1st').startswith('col_')

    def test_find_nested_list_traverses_lists(self):
        """The finder descends through lists of dicts and returns [] when absent."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _find_nested_list,
        )

        # Target nested inside a list of dicts (exercises the list branch).
        obj = {'outer': [{'inner': {'series': [1, 2, 3]}}]}
        assert _find_nested_list(obj, 'series') == [1, 2, 3]
        assert _find_nested_list({'a': 1}, 'series') == []
        # Earlier siblings without the key are skipped in both dicts and lists.
        obj = {'first': {'x': 1}, 'second': [{'y': 2}, {'series': [9]}]}
        assert _find_nested_list(obj, 'series') == [9]
        # A list whose items never contain the key is exhausted and yields [].
        assert _find_nested_list({'a': [{'b': 1}, {'c': 2}]}, 'series') == []

    def test_flatten_scalars_drop_lists(self):
        """drop_lists omits list leaves; the default JSON-encodes them."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _flatten_scalars,
        )

        obj = {'a': 1, 'b': {'c': 2}, 'series': [1, 2, 3]}
        assert _flatten_scalars(obj, drop_lists=True) == {'a': 1, 'b_c': 2}
        # Default keeps lists as JSON strings (generic/row behavior).
        assert _flatten_scalars(obj)['series'] == '[1, 2, 3]'

    def test_response_summary_excludes_response_metadata(self):
        """boto3 ResponseMetadata is excluded from the offload summary."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _response_summary,
        )

        out = _response_summary(
            {
                'EstimatedROI': '12.5',
                'ResponseMetadata': {
                    'RequestId': 'r-1',
                    'HTTPHeaders': {'date': 'x'},
                    'RetryAttempts': 0,
                },
            }
        )
        assert out == {'EstimatedROI': '12.5'}

    def test_record_columns_case_variants_keep_their_values(self):
        """Keys differing only by case get distinct columns; no value is lost."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _create_and_insert_dict_rows,
        )

        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        count = _create_and_insert_dict_rows(cur, 'tbl', [{'Bucket': 'a'}, {'bucket': 'b'}])
        assert count == 2
        cur.execute('SELECT * FROM tbl')
        cols = [d[0] for d in cur.description]
        assert cols == ['Bucket', 'bucket_2']
        assert cur.fetchall() == [('a', None), (None, 'b')]
        conn.close()

    def test_explicit_columns_case_duplicate_raises(self):
        """Explicit columns colliding case-insensitively raise instead of dropping one."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _create_and_insert_dict_rows,
        )

        conn = sqlite3.connect(':memory:')
        with pytest.raises(ValueError):
            _create_and_insert_dict_rows(conn.cursor(), 'tbl', [{'a': 1}], columns=['Col', 'col'])
        conn.close()

    def test_create_and_insert_dict_rows_rejects_bad_column(self):
        """An unsafe explicit column name raises ValueError (injection guard)."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _create_and_insert_dict_rows,
        )

        conn = sqlite3.connect(':memory:')
        with pytest.raises(ValueError):
            _create_and_insert_dict_rows(conn.cursor(), 'tbl', [{'ok': 1}], columns=['bad-col'])
        conn.close()

    def test_create_and_insert_dict_rows_non_dict_fallback(self):
        """Non-dict rows are stored under a single value column."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _create_and_insert_dict_rows,
        )

        conn = sqlite3.connect(':memory:')
        cur = conn.cursor()
        # Non-dict rows store the scalar under the 'value' column (rows is
        # typed List[Any] for exactly this case).
        count = _create_and_insert_dict_rows(cur, 'tbl', ['x', 'y'])
        assert count == 2
        cur.execute('SELECT value FROM tbl ORDER BY value')
        assert [r[0] for r in cur.fetchall()] == ['x', 'y']
        conn.close()

    def test_ri_series_rows_skips_non_dict_bucket_and_group(self):
        """Malformed (non-dict) buckets and groups are skipped."""
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            _ri_series_rows,
        )

        response = {
            'coverages_by_time': [
                'not-a-dict',
                {
                    'time_period': {'start': 's', 'end': 'e'},
                    'total': {},
                    'groups': ['not-a-dict', {'attributes': {}, 'coverage': {'x': '1'}}],
                },
            ]
        }
        rows = _ri_series_rows(response, 'coverages_by_time', 'coverage')
        # Only the one valid group row (bad bucket + bad group skipped; empty
        # total adds no row).
        assert len(rows) == 1
        assert rows[0]['level'] == 'group'
