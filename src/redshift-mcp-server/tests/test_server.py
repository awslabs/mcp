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

"""Tests for the Redshift MCP Server tools."""

import pytest
from awslabs.redshift_mcp_server.models import (
    QueryResult,
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.server import (
    execute_query_tool,
    list_clusters_tool,
    list_columns_tool,
    list_databases_tool,
    list_schemas_tool,
    list_tables_tool,
)
from mcp.server.fastmcp import Context


class TestListClustersTool:
    """Tests for the list_clusters MCP tool."""

    @pytest.mark.asyncio
    async def test_list_clusters_tool_success(self, mocker):
        """Test successful cluster discovery."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {
                'identifier': 'test-cluster',
                'type': 'provisioned',
                'status': 'available',
                'database_name': 'dev',
                'endpoint': 'test-cluster.abc123.us-east-1.redshift.amazonaws.com',
                'port': 5439,
                'vpc_id': 'vpc-12345',
                'node_type': 'dc2.large',
                'number_of_nodes': 2,
                'creation_time': '2023-01-01T00:00:00Z',
                'master_username': 'testuser',
                'publicly_accessible': False,
                'encrypted': True,
                'tags': {'Environment': 'test'},
            },
            {
                'identifier': 'test-workgroup',
                'type': 'serverless',
                'status': 'AVAILABLE',
                'database_name': 'dev',
                'endpoint': 'test-workgroup.123456.us-east-1.redshift-serverless.amazonaws.com',
                'port': 5439,
                'vpc_id': 'subnet-12345',
                'node_type': None,
                'number_of_nodes': None,
                'creation_time': '2023-01-01T00:00:00Z',
                'master_username': None,
                'publicly_accessible': False,
                'encrypted': True,
                'tags': {},
            },
        ]

        result = await list_clusters_tool(Context())

        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(cluster, RedshiftCluster) for cluster in result)

        # Verify first cluster
        assert result[0].identifier == 'test-cluster'
        assert result[0].type == 'provisioned'
        assert result[0].status == 'available'
        assert result[0].database_name == 'dev'

        # Verify second cluster
        assert result[1].identifier == 'test-workgroup'
        assert result[1].type == 'serverless'
        assert result[1].status == 'AVAILABLE'

    @pytest.mark.asyncio
    async def test_list_clusters_tool_empty(self, mocker):
        """Test when no clusters are found."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_clusters'
        )
        mock_discover_clusters.return_value = []

        result = await list_clusters_tool(Context())

        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_clusters_tool_error(self, mocker):
        """Test list_clusters_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_clusters',
            side_effect=Exception('Test error'),
        )

        with pytest.raises(Exception, match='Test error'):
            await list_clusters_tool(mock_ctx)

        mock_ctx.error.assert_called_once_with('Failed to list clusters: Test error')


class TestListDatabasesTool:
    """Tests for the list_databases MCP tool."""

    @pytest.mark.asyncio
    async def test_list_databases_tool_success(self, mocker):
        """Test successful database discovery."""
        mock_discover_databases = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_databases'
        )
        mock_discover_databases.return_value = [
            {
                'database_name': 'dev',
                'database_owner': 100,
                'database_type': 'local',
                'database_acl': 'user=admin',
                'database_options': 'encoding=utf8',
                'database_isolation_level': 'Snapshot Isolation',
            },
            {
                'database_name': 'test',
                'database_owner': 101,
                'database_type': 'shared',
                'database_acl': 'user=readonly',
                'database_options': 'encoding=utf8',
                'database_isolation_level': 'Serializable',
            },
        ]

        result = await list_databases_tool(Context(), 'test-cluster', 'dev')

        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(db, RedshiftDatabase) for db in result)

        # Verify database properties
        assert result[0].database_name == 'dev'
        assert result[0].database_type == 'local'
        assert result[0].database_owner == 100
        assert result[1].database_name == 'test'
        assert result[1].database_type == 'shared'

    @pytest.mark.asyncio
    async def test_list_databases_tool_empty(self, mocker):
        """Test when no databases are found."""
        mock_discover_databases = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_databases'
        )
        mock_discover_databases.return_value = []

        result = await list_databases_tool(Context(), 'test-cluster', 'dev')

        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_databases_tool_error(self, mocker):
        """Test list_databases_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_databases',
            side_effect=Exception('DB error'),
        )

        with pytest.raises(Exception, match='DB error'):
            await list_databases_tool(mock_ctx, 'test-cluster')

        mock_ctx.error.assert_called_once_with(
            'Failed to list databases on cluster test-cluster: DB error'
        )


class TestListSchemasTool:
    """Tests for the list_schemas MCP tool."""

    @pytest.mark.asyncio
    async def test_list_schemas_tool_success(self, mocker):
        """Test successful schema discovery."""
        mock_discover_schemas = mocker.patch('awslabs.redshift_mcp_server.server.discover_schemas')
        mock_discover_schemas.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'schema_owner': 100,
                'schema_type': 'local',
                'schema_acl': 'user=admin',
                'source_database': None,
                'schema_option': None,
            },
            {
                'database_name': 'dev',
                'schema_name': 'external_schema',
                'schema_owner': 100,
                'schema_type': 'external',
                'schema_acl': 'user=admin',
                'source_database': 's3_source',
                'schema_option': 'IAM_ROLE arn:aws:iam::123456789012:role/RedshiftRole',
            },
        ]

        result = await list_schemas_tool(Context(), 'test-cluster', 'dev')

        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(schema, RedshiftSchema) for schema in result)

        # Verify schema properties
        assert result[0].schema_name == 'public'
        assert result[0].schema_type == 'local'
        assert result[0].database_name == 'dev'
        assert result[1].schema_name == 'external_schema'
        assert result[1].schema_type == 'external'

    @pytest.mark.asyncio
    async def test_list_schemas_tool_empty(self, mocker):
        """Test when no schemas are found."""
        mock_discover_schemas = mocker.patch('awslabs.redshift_mcp_server.server.discover_schemas')
        mock_discover_schemas.return_value = []

        result = await list_schemas_tool(Context(), 'test-cluster', 'dev')

        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_schemas_tool_error(self, mocker):
        """Test list_schemas_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_schemas',
            side_effect=Exception('Schema error'),
        )

        with pytest.raises(Exception, match='Schema error'):
            await list_schemas_tool(mock_ctx, 'test-cluster', 'test-db')

        mock_ctx.error.assert_called_once_with(
            'Failed to list schemas in database test-db on cluster test-cluster: Schema error'
        )


class TestListTablesTool:
    """Tests for the list_tables MCP tool."""

    @pytest.mark.asyncio
    async def test_list_tables_tool_success(self, mocker):
        """Test successful table discovery."""
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.server.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'table_acl': 'user=admin',
                'table_type': 'TABLE',
                'remarks': 'User data table',
            },
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'user_view',
                'table_acl': 'user=admin',
                'table_type': 'VIEW',
                'remarks': 'User view',
            },
        ]

        result = await list_tables_tool(Context(), 'test-cluster', 'dev', 'public')

        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(table, RedshiftTable) for table in result)

        # Verify table properties
        assert result[0].table_name == 'users'
        assert result[0].table_type == 'TABLE'
        assert result[0].schema_name == 'public'
        assert result[1].table_name == 'user_view'
        assert result[1].table_type == 'VIEW'

    @pytest.mark.asyncio
    async def test_list_tables_tool_empty(self, mocker):
        """Test when no tables are found."""
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.server.discover_tables')
        mock_discover_tables.return_value = []

        result = await list_tables_tool(Context(), 'test-cluster', 'dev', 'public')

        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_tables_tool_error(self, mocker):
        """Test list_tables_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_tables',
            side_effect=Exception('Table error'),
        )

        with pytest.raises(Exception, match='Table error'):
            await list_tables_tool(mock_ctx, 'test-cluster', 'test-db', 'test-schema')

        mock_ctx.error.assert_called_once_with(
            'Failed to list tables in schema test-schema in database test-db on cluster test-cluster: Table error'
        )


class TestListColumnsTool:
    """Tests for the list_columns MCP tool."""

    @pytest.mark.asyncio
    async def test_list_columns_tool_success(self, mocker):
        """Test successful column discovery."""
        mock_discover_columns = mocker.patch('awslabs.redshift_mcp_server.server.discover_columns')
        mock_discover_columns.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'column_name': 'id',
                'ordinal_position': 1,
                'column_default': None,
                'is_nullable': 'NO',
                'data_type': 'integer',
                'character_maximum_length': None,
                'numeric_precision': None,
                'numeric_scale': None,
                'remarks': 'Primary key',
            },
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'column_name': 'name',
                'ordinal_position': 2,
                'column_default': None,
                'is_nullable': 'YES',
                'data_type': 'varchar',
                'character_maximum_length': 255,
                'numeric_precision': None,
                'numeric_scale': None,
                'remarks': 'User name',
            },
        ]

        result = await list_columns_tool(Context(), 'test-cluster', 'dev', 'public', 'users')

        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(column, RedshiftColumn) for column in result)

        # Verify column properties
        assert result[0].column_name == 'id'
        assert result[0].data_type == 'integer'
        assert result[0].is_nullable == 'NO'
        assert result[0].ordinal_position == 1
        assert result[1].column_name == 'name'
        assert result[1].data_type == 'varchar'
        assert result[1].character_maximum_length == 255

    @pytest.mark.asyncio
    async def test_list_columns_tool_empty(self, mocker):
        """Test when no columns are found."""
        mock_discover_columns = mocker.patch('awslabs.redshift_mcp_server.server.discover_columns')
        mock_discover_columns.return_value = []

        result = await list_columns_tool(Context(), 'test-cluster', 'dev', 'public', 'users')

        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_columns_tool_error(self, mocker):
        """Test list_columns_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_columns',
            side_effect=Exception('Column error'),
        )

        with pytest.raises(Exception, match='Column error'):
            await list_columns_tool(
                mock_ctx, 'test-cluster', 'test-db', 'test-schema', 'test-table'
            )

        mock_ctx.error.assert_called_once_with(
            'Failed to list columns in table test-table in schema test-schema in database test-db on cluster test-cluster: Column error'
        )


class TestExecuteQueryTool:
    """Tests for the execute_query MCP tool."""

    @pytest.mark.asyncio
    async def test_execute_query_tool_success(self, mocker):
        """Test successful query execution."""
        mock_execute_query = mocker.patch('awslabs.redshift_mcp_server.server.execute_query')
        mock_execute_query.return_value = {
            'columns': ['id', 'name', 'age', 'active', 'score'],
            'rows': [
                [1, 'Sergey', 54, True, 95.5],
                [2, 'Max', 42, False, None],
            ],
            'row_count': 2,
            'execution_time_ms': 123,
            'query_id': 'query-123',
        }

        result = await execute_query_tool(
            Context(),
            cluster_identifier='test-cluster',
            database_name='dev',
            sql='SELECT id, name, age, active, score FROM users LIMIT 2',
        )

        # Verify return type and structure
        assert isinstance(result, QueryResult)

        # Verify query result properties
        assert result.columns == ['id', 'name', 'age', 'active', 'score']
        assert len(result.rows) == 2
        assert result.rows[0] == [1, 'Sergey', 54, True, 95.5]
        assert result.rows[1] == [2, 'Max', 42, False, None]
        assert result.row_count == 2
        assert result.execution_time_ms == 123
        assert result.query_id == 'query-123'

    @pytest.mark.asyncio
    async def test_execute_query_tool_empty_results(self, mocker):
        """Test query execution with no results."""
        mock_execute_query = mocker.patch('awslabs.redshift_mcp_server.server.execute_query')
        mock_execute_query.return_value = {
            'columns': ['count'],
            'rows': [],
            'row_count': 0,
            'execution_time_ms': 45,
            'query_id': 'query-456',
        }

        result = await execute_query_tool(
            Context(),
            cluster_identifier='test-workgroup',
            database_name='test_db',
            sql='SELECT COUNT(*) FROM empty_table',
        )

        # Verify return type and structure
        assert isinstance(result, QueryResult)

        # Verify empty result properties
        assert result.columns == ['count']
        assert len(result.rows) == 0
        assert result.row_count == 0
        assert result.execution_time_ms == 45
        assert result.query_id == 'query-456'

    @pytest.mark.asyncio
    async def test_execute_query_tool_error(self, mocker):
        """Test execute_query_tool error handling."""
        from unittest.mock import AsyncMock, Mock

        mock_ctx = Mock()
        mock_ctx.error = AsyncMock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.execute_query',
            side_effect=Exception('Query error'),
        )

        with pytest.raises(Exception, match='Query error'):
            await execute_query_tool(mock_ctx, 'test-cluster', 'test-db', 'SELECT 1')

        mock_ctx.error.assert_called_once_with(
            'Failed to execute query on cluster test-cluster in database test-db: Query error'
        )
