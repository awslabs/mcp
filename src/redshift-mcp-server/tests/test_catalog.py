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


"""Tests for catalog discovery."""

import pytest
import sqlglot
from awslabs.redshift_mcp_server.catalog import (
    _sql_identifier,
    discover_columns,
    discover_databases,
    discover_schemas,
    discover_tables,
)
from sqlglot import exp


class TestDiscoverCatalog:
    """Tests for the SHOW-based discovery of what a warehouse contains."""

    @pytest.mark.asyncio
    async def test_discover_databases(self, mocker):
        """Test discover_databases function."""
        # Mock execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        # Verify column order is handled correctly.
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [
                    {'name': 'database_type'},
                    {'name': 'database_name'},
                    {'name': 'database_isolation_level'},
                    {'name': 'database_owner'},
                    {'name': 'parameters'},
                    {'name': 'database_acl'},
                ],
                'Records': [
                    [
                        {'stringValue': 'local'},
                        {'stringValue': 'dev'},
                        {'stringValue': 'Snapshot Isolation'},
                        {'longValue': 100},
                        {'stringValue': 'encoding=utf8'},
                        {'stringValue': 'user=admin'},
                    ]
                ],
            },
            'query-123',
        )

        result = await discover_databases('test-cluster', 'dev')

        assert len(result) == 1
        assert result[0].database_name == 'dev'
        assert result[0].database_owner == 100
        assert result[0].database_type == 'local'
        assert result[0].parameters == 'encoding=utf8'
        assert result[0].database_isolation_level == 'Snapshot Isolation'

        # SHOW DATABASES takes no bind parameters.
        sql = mock_execute_protected.call_args[1]['sql']
        assert 'SHOW DATABASES' in sql
        assert mock_execute_protected.call_args[1].get('parameters') is None

        # This server's own SQL, so it runs without the read-only wrapper while the guard
        # still applies.
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is False

    @pytest.mark.asyncio
    async def test_discover_databases_error(self, mocker):
        """Test error handling in discover_databases."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Database discovery failed')

        with pytest.raises(Exception, match='Database discovery failed'):
            await discover_databases('test-cluster')

    @pytest.mark.asyncio
    async def test_discover_schemas(self, mocker):
        """Test discover_schemas function."""
        # Mock execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [
                    {'name': 'database_name'},
                    {'name': 'schema_name'},
                    {'name': 'schema_owner'},
                    {'name': 'schema_type'},
                    {'name': 'schema_acl'},
                    {'name': 'source_database'},
                    {'name': 'schema_option'},
                ],
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'stringValue': 'public'},
                        {'longValue': 100},
                        {'stringValue': 'local'},
                        {'stringValue': 'user=admin'},
                        {'stringValue': None},
                        {'stringValue': None},
                    ]
                ],
            },
            'query-456',
        )

        result = await discover_schemas('test-cluster', 'dev')

        assert len(result) == 1
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].schema_owner == 100

        # The database is embedded as a quoted identifier (no bind params).
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        sql = call_args[1]['sql']
        assert 'SHOW SCHEMAS FROM DATABASE' in sql
        assert '"dev"' in sql
        assert call_args[1].get('parameters') is None

        # A double quote in the database name is doubled so the value cannot
        # break out of the identifier (injection-safe).
        mock_execute_protected.return_value = ({'Records': []}, 'query-457')
        await discover_schemas('test-cluster', 'd"b')
        assert '"d""b"' in mock_execute_protected.call_args[1]['sql']

    @pytest.mark.asyncio
    async def test_discover_schemas_error(self, mocker):
        """Test error handling in discover_schemas."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Schema discovery failed')

        with pytest.raises(Exception, match='Schema discovery failed'):
            await discover_schemas('test-cluster', 'dev')

    @pytest.mark.asyncio
    async def test_discover_tables(self, mocker):
        """Test discover_tables function."""
        # Mock execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [
                    {'name': 'database_name'},
                    {'name': 'schema_name'},
                    {'name': 'table_name'},
                    {'name': 'table_type'},
                    {'name': 'table_acl'},
                    {'name': 'remarks'},
                ],
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'TABLE'},
                        {'stringValue': 'user=admin'},
                        {'stringValue': 'User data table'},
                    ]
                ],
            },
            'query-789',
        )

        result = await discover_tables('test-cluster', 'dev', 'public')

        assert len(result) == 1
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].table_name == 'users'
        # type and acl are mapped by column name, not swapped by position.
        assert result[0].table_type == 'TABLE'
        assert result[0].table_acl == 'user=admin'
        assert result[0].remarks == 'User data table'

        # db.schema is embedded as quoted identifiers (no bind params).
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        sql = call_args[1]['sql']
        assert 'SHOW TABLES FROM SCHEMA' in sql
        assert '"dev"."public"' in sql
        assert call_args[1].get('parameters') is None

        # Double quotes in the identifiers are doubled so the values cannot
        # break out of them (injection-safe).
        mock_execute_protected.return_value = ({'Records': []}, 'query-790')
        await discover_tables('test-cluster', 'd"b', 's"c')
        assert '"d""b"."s""c"' in mock_execute_protected.call_args[1]['sql']

    @pytest.mark.asyncio
    async def test_discover_tables_error(self, mocker):
        """Test error handling in discover_tables."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Table discovery failed')

        with pytest.raises(Exception, match='Table discovery failed'):
            await discover_tables('test-cluster', 'dev', 'public')

    @pytest.mark.asyncio
    async def test_discover_columns(self, mocker):
        """Test discover_columns function."""
        # Mock execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [
                    {'name': 'database_name'},
                    {'name': 'schema_name'},
                    {'name': 'table_name'},
                    {'name': 'column_name'},
                    {'name': 'ordinal_position'},
                    {'name': 'column_default'},
                    {'name': 'is_nullable'},
                    {'name': 'data_type'},
                    {'name': 'character_maximum_length'},
                    {'name': 'numeric_precision'},
                    {'name': 'numeric_scale'},
                    {'name': 'remarks'},
                ],
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'longValue': 1},
                        {'stringValue': None},
                        {'stringValue': 'NO'},
                        {'stringValue': 'integer'},
                        {'longValue': None},
                        {'longValue': 32},
                        {'longValue': 0},
                        {'stringValue': 'Primary key'},
                    ]
                ],
            },
            'query-101',
        )

        result = await discover_columns('test-cluster', 'dev', 'public', 'users')

        assert len(result) == 1
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].table_name == 'users'
        assert result[0].column_name == 'id'
        assert result[0].ordinal_position == 1
        assert result[0].data_type == 'integer'

        # db.schema.table is embedded as quoted identifiers (no bind params).
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        sql = call_args[1]['sql']
        assert 'SHOW COLUMNS FROM TABLE' in sql
        assert '"dev"."public"."users"' in sql
        assert call_args[1].get('parameters') is None

        # Double quotes in the identifiers are doubled so the values cannot
        # break out of them (injection-safe).
        mock_execute_protected.return_value = ({'Records': []}, 'query-102')
        await discover_columns('test-cluster', 'd"b', 's"c', 't"l')
        assert '"d""b"."s""c"."t""l"' in mock_execute_protected.call_args[1]['sql']

    @pytest.mark.asyncio
    async def test_discover_columns_error(self, mocker):
        """Test error handling in discover_columns."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Column discovery failed')

        with pytest.raises(Exception, match='Column discovery failed'):
            await discover_columns('test-cluster', 'dev', 'public', 'users')


class TestSqlIdentifier:
    """`_sql_identifier` renders a value as one safely-quoted identifier that round-trips unchanged."""

    @pytest.mark.parametrize(
        'value',
        [
            'dev',
            'sample_data_dev',
            'MixedCase',  # case is preserved because the identifier is quoted
            'weird name',  # spaces require quoting
            'd"b',  # embedded double quote must be doubled
            'a""b',  # an already-doubled sequence still round-trips
            'a\\',  # trailing backslash must not escape the closing quote
            '"; DROP TABLE users; --',  # injection attempt via a double quote
            "'; DROP TABLE users; --",  # single quotes are not special in an identifier
        ],
    )
    def test_value_round_trips_as_a_single_identifier(self, value):
        """Parsing the rendered identifier yields exactly one identifier equal to the input."""
        statement = 'SELECT * FROM ' + _sql_identifier(value)

        # Exactly one statement -- the value cannot introduce extra statements.
        statements = sqlglot.parse(statement, read='redshift')
        assert len(statements) == 1

        # The parsed identifier's name equals the original input.
        identifier = sqlglot.parse_one(statement, read='redshift').find(exp.Identifier)
        assert identifier is not None
        assert identifier.name == value
