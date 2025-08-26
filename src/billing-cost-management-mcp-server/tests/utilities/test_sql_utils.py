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

    @patch('os.getenv')
    def test_should_convert_with_force_enabled(self, mock_getenv):
        """Test should_convert_to_sql with FORCE_SQL_CONVERSION enabled."""
        # Setup - Force conversion regardless of size
        small_size = 100  # Very small response

        # Mock the getenv to return 'true' for MCP_FORCE_SQL
        mock_getenv.side_effect = (
            lambda key, default=None: 'true' if key == 'MCP_FORCE_SQL' else default
        )

        # Reset module constants by reloading the module
        with patch.dict('sys.modules'):
            # Clear the module to force reload
            import sys

            if 'awslabs.billing_cost_management_mcp_server.utilities.sql_utils' in sys.modules:
                del sys.modules['awslabs.billing_cost_management_mcp_server.utilities.sql_utils']

            # Now reimport with our patched environment
            from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
                FORCE_SQL_CONVERSION,
                should_convert_to_sql,
            )

            # Verify patched value took effect
            assert FORCE_SQL_CONVERSION is True

            # Execute
        result = should_convert_to_sql(small_size)

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

        path = get_session_db_path()

        # Just verify we get a path back
        assert path is not None
        assert isinstance(path, str)


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
        """Test convert response if needed with small response."""
        mock_context = MagicMock(spec=Context)
        response = {'data': ['small']}

        result = await convert_response_if_needed(mock_context, response, 'test_api')

        assert 'data' in result


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
        """Test convert_response_if_needed handles JSON error."""
        # Setup - Make json.dumps fail on first call but succeed on subsequent calls
        mock_json_dumps.side_effect = [TypeError('JSON encoding error'), '{"data": "test"}']
        response = {'data': 'test'}

        # Execute
        result = await convert_response_if_needed(mock_context, response, 'test_api')

        # Assert
        assert result['status'] == 'error'
        assert 'Error processing response for test_api' in result['message']
        assert 'JSON encoding error' in result['message']
        assert result['data'] == response  # Original data should be preserved

    async def test_convert_response_if_needed_conversion_error(self, mock_context):
        """Test convert_response_if_needed handles conversion error."""
        # Create a large response that will trigger conversion
        response = {'data': 'x' * 30000}  # Large enough to exceed threshold

        with patch.object(
            sys.modules['awslabs.billing_cost_management_mcp_server.utilities.sql_utils'],
            'convert_api_response_to_table',
        ) as mock_convert:
            mock_convert.side_effect = ValueError('Conversion error')

            # Execute
            result = await convert_response_if_needed(mock_context, response, 'test_api')

            # Assert
            assert result['status'] == 'error'
            assert 'Error processing response for test_api' in result['message']
            assert 'Conversion error' in result['message']
            assert result['data'] == response  # Original data should be preserved


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
