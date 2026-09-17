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
from awslabs.redshift_mcp_server.consts import (
    ACCESS_MODE_READ_ONLY,
    ACCESS_MODE_READ_WRITE,
)
from awslabs.redshift_mcp_server.models import (
    QueryResult,
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.review.models import (
    ReviewFinding,
    ReviewRecommendation,
    ReviewResult,
)
from awslabs.redshift_mcp_server.server import (
    ConfirmWrite,
    _current_settings,
    _execute_query_annotations,
    _tool_failed,
    _write_confirmation,
    execute_query_tool,
    list_clusters_tool,
    list_columns_tool,
    list_databases_tool,
    list_schemas_tool,
    list_tables_tool,
    mcp,
    review_cluster_tool,
)
from awslabs.redshift_mcp_server.settings import (
    max_open_transactions_per_target,
    session_keepalive,
)
from botocore.exceptions import ClientError, NoRegionError
from datetime import datetime
from mcp.server.mcpserver import Context, Elicit, MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError


class TestWriteConfirmation:
    """The resolver asks the client only when a write needs confirming."""

    def _configure(self, mocker, access_mode, skip):
        """Pin the resolved access mode and confirmation opt-out."""
        mocker.patch('awslabs.redshift_mcp_server.server.ACCESS_MODE', access_mode)
        mocker.patch('awslabs.redshift_mcp_server.server.SKIP_WRITE_CONFIRMATION', skip)

    def _ctx(self, mocker, *, can_elicit=True):
        """Build a context whose session reports the client's elicitation support."""
        ctx = mocker.Mock()
        ctx.session.check_client_capability = mocker.Mock(return_value=can_elicit)
        return ctx

    def test_read_write_asks_the_client(self, mocker):
        """Read-write mode returns a request to elicit, against the ConfirmWrite schema."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t')

        assert isinstance(result, Elicit)
        assert result.schema is ConfirmWrite

    def test_a_write_the_fallback_will_refuse_raises_no_prompt(self, mocker):
        """Asking about a statement certain to be refused spends the caller's attention.

        While the batch action is denied the compatibility path serves reads only, so the write
        is refused in the tool body a moment later whatever the caller answers.
        """
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)
        mocker.patch('awslabs.redshift_mcp_server.server.no_batch_latched', return_value=True)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t')

        assert not isinstance(result, Elicit)
        assert result.confirmed is True

    def test_prompt_names_target_and_statement(self, mocker):
        """The prompt tells the user which cluster and statement they are approving."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t')

        assert isinstance(result, Elicit)
        assert 'test-cluster:dev' in result.message
        assert 'DELETE FROM t' in result.message
        assert 'cannot be rolled back' in result.message

    def test_a_write_inside_a_transaction_is_not_described_as_final(self, mocker):
        """Inside a transaction the write is not final until it is committed."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(
            self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t', in_transaction='load'
        )

        assert isinstance(result, Elicit)
        assert "transaction 'load'" in result.message
        assert 'not final until you commit' in result.message
        # Scoped the same way the rollback branch is: a rollback does not reach S3.
        assert 'outside the database' in result.message
        assert 'cannot be rolled back' not in result.message

    def test_a_write_that_commits_in_the_same_call_is_described_as_final(self, mocker):
        """The call being approved takes the commit decision, so it cannot be called pending."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(
            self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t', commit_transaction='load'
        )

        assert isinstance(result, Elicit)
        assert "transaction 'load'" in result.message
        assert 'commits it' in result.message
        assert 'cannot be rolled back' in result.message
        assert 'not final until you commit' not in result.message

    def test_a_write_that_is_rolled_back_in_the_same_call_says_it_is_discarded(self, mocker):
        """Promising a pending commit would overstate what approving it keeps."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(
            self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t', rollback_transaction='load'
        )

        assert isinstance(result, Elicit)
        assert "transaction 'load'" in result.message
        assert 'in the database is discarded' in result.message
        # Scoped, because a rollback does not reach what UNLOAD already wrote to S3.
        assert 'outside the database' in result.message
        assert 'not final until you commit' not in result.message

    def test_closing_a_transaction_asks_nothing(self, mocker):
        """A bare commit or rollback runs no statement of the caller's."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(
            self._ctx(mocker), 'test-cluster', 'dev', None, commit_transaction='load'
        )

        assert result == ConfirmWrite(confirmed=True)

    def test_read_in_read_write_mode_asks_nothing(self, mocker):
        """A recognized read is not confirmed, even when writes are permitted."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'SELECT 1')

        assert result == ConfirmWrite(confirmed=True)

    def test_read_only_asks_nothing(self, mocker):
        """Read-only mode approves without asking, since nothing can be persisted."""
        self._configure(mocker, ACCESS_MODE_READ_ONLY, False)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'SELECT 1')

        assert result == ConfirmWrite(confirmed=True)

    def test_opt_out_asks_nothing(self, mocker):
        """The opt-out approves without asking."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, True)

        result = _write_confirmation(self._ctx(mocker), 'test-cluster', 'dev', 'DELETE FROM t')

        assert result == ConfirmWrite(confirmed=True)

    def test_rejected_sql_is_not_prompted_for(self, mocker):
        """Stacked statements are rejected by the guard before anyone is asked."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)
        ctx = self._ctx(mocker)

        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            _write_confirmation(ctx, 'test-cluster', 'dev', 'SELECT 1; DROP TABLE t')

        ctx.session.check_client_capability.assert_not_called()

    def test_client_that_cannot_prompt_is_refused(self, mocker):
        """A client without elicitation support is refused rather than run unconfirmed."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        with pytest.raises(ToolError, match='cannot prompt for confirmation'):
            _write_confirmation(
                self._ctx(mocker, can_elicit=False), 'test-cluster', 'dev', 'DELETE FROM t'
            )

    def test_refusal_names_the_opt_out(self, mocker):
        """The refusal tells the operator which setting lets them proceed."""
        self._configure(mocker, ACCESS_MODE_READ_WRITE, False)

        with pytest.raises(ToolError, match='UNSAFE_SKIP_WRITE_CONFIRMATION'):
            _write_confirmation(
                self._ctx(mocker, can_elicit=False), 'test-cluster', 'dev', 'DELETE FROM t'
            )


class TestExecuteQueryAnnotations:
    """The execute_query annotations describe the mode the server actually runs in."""

    def test_read_only_mode_advertises_read_only(self):
        """Read-only mode keeps the read-only hints and title."""
        annotations = _execute_query_annotations(ACCESS_MODE_READ_ONLY)

        assert annotations.title == 'Execute read-only Redshift query'
        assert annotations.read_only_hint is True
        assert annotations.destructive_hint is False
        assert annotations.idempotent_hint is True
        assert annotations.open_world_hint is True

    def test_read_write_mode_advertises_destructive(self):
        """Read-write mode drops the read-only claim and flags the tool as destructive."""
        annotations = _execute_query_annotations(ACCESS_MODE_READ_WRITE)

        assert annotations.title == 'Execute read-write Redshift query'
        assert annotations.read_only_hint is False
        assert annotations.destructive_hint is True
        assert annotations.idempotent_hint is False
        assert annotations.open_world_hint is True


class TestCurrentSettings:
    """The settings block reports resolved values the caller cannot read for itself."""

    def test_lists_every_setting_with_its_value(self):
        """Each setting the prose names appears with the value this server resolved."""
        settings = _current_settings()

        assert '## Current Settings' in settings
        assert f'`ACCESS_MODE`: {ACCESS_MODE_READ_ONLY}' in settings
        assert '`UNSAFE_SKIP_WRITE_CONFIRMATION`: false' in settings
        assert f'`SESSION_KEEPALIVE`: {session_keepalive()} seconds' in settings
        assert (
            f'`MAX_OPEN_TRANSACTIONS_PER_TARGET`: {max_open_transactions_per_target()}' in settings
        )

    def test_confirmed_writes_hand_over_nothing(self):
        """With the prompt on, the caller is asked to take on no duty of its own."""
        assert 'get their agreement yourself' not in _current_settings()

    def test_skipped_confirmation_states_it_and_delegates_the_check(self, mocker):
        """With the prompt off, the block reports the mechanism and hands over the duty."""
        mocker.patch('awslabs.redshift_mcp_server.server.SKIP_WRITE_CONFIRMATION', True)

        settings = _current_settings()

        assert '`UNSAFE_SKIP_WRITE_CONFIRMATION`: true' in settings
        assert 'get their agreement yourself' in settings

    def test_the_instructions_end_with_the_settings(self):
        """The instructions are the one place the block appears, so the caller reads it once."""
        assert mcp.instructions is not None
        assert mcp.instructions.endswith(_current_settings())


@pytest.mark.asyncio
async def test_tool_annotations():
    """Test that every tool advertises its read-only behavior to MCP clients.

    The server under test is registered with the default (read-only) mode, since the
    tests do not set ACCESS_MODE.
    """
    expected_titles = {
        'list_clusters': 'List Redshift clusters and workgroups',
        'list_databases': 'List Redshift databases',
        'list_schemas': 'List Redshift schemas',
        'list_tables': 'List Redshift tables',
        'list_columns': 'List Redshift columns',
        'execute_query': 'Execute read-only Redshift query',
        'review_cluster': 'Review Redshift cluster',
    }

    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert tools.keys() == expected_titles.keys()
    for name, title in expected_titles.items():
        annotations = tools[name].annotations
        assert annotations is not None
        assert annotations.title == title
        assert annotations.read_only_hint is True
        assert annotations.destructive_hint is False
        assert annotations.idempotent_hint is True
        assert annotations.open_world_hint is True


@pytest.mark.asyncio
async def test_resolved_confirmation_is_not_a_tool_argument():
    """The confirmation is resolved server-side, so the model cannot supply it."""
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    properties = tools['execute_query'].input_schema['properties']

    assert set(properties) == {
        'cluster_identifier',
        'database_name',
        'sql',
        'begin_transaction',
        'in_transaction',
        'commit_transaction',
        'rollback_transaction',
    }


class TestListClustersTool:
    """Tests for the list_clusters MCP tool."""

    @pytest.mark.asyncio
    async def test_list_clusters_tool_success(self, mocker):
        """Test successful cluster discovery."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            RedshiftCluster(
                identifier='test-cluster',
                type='provisioned',
                status='available',
                database_name='dev',
                endpoint='test-cluster.abc123.us-east-1.redshift.amazonaws.com',
                port=5439,
                vpc_id='vpc-12345',
                node_type='dc2.large',
                number_of_nodes=2,
                creation_time=datetime(2023, 1, 1),
                master_username='testuser',
                publicly_accessible=False,
                encrypted=True,
                tags={'Environment': 'test'},
            ),
            RedshiftCluster(
                identifier='test-workgroup',
                type='serverless',
                status='AVAILABLE',
                database_name='dev',
                endpoint='test-workgroup.123456.us-east-1.redshift-serverless.amazonaws.com',
                port=5439,
                vpc_id='subnet-12345',
                node_type=None,
                number_of_nodes=None,
                creation_time=datetime(2023, 1, 1),
                master_username=None,
                publicly_accessible=False,
                encrypted=True,
                tags={},
            ),
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
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_clusters',
            side_effect=Exception('Test error'),
        )

        with pytest.raises(Exception, match='Test error'):
            await list_clusters_tool(mock_ctx)


class TestListDatabasesTool:
    """Tests for the list_databases MCP tool."""

    @pytest.mark.asyncio
    async def test_list_databases_tool_success(self, mocker):
        """Test successful database discovery."""
        mock_discover_databases = mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_databases'
        )
        mock_discover_databases.return_value = [
            RedshiftDatabase(
                database_name='dev',
                database_owner=100,
                database_type='local',
                database_acl='user=admin',
                parameters='encoding=utf8',
                database_isolation_level='Snapshot Isolation',
            ),
            RedshiftDatabase(
                database_name='test',
                database_owner=101,
                database_type='shared',
                database_acl='user=readonly',
                parameters='encoding=utf8',
                database_isolation_level='Serializable',
            ),
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
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_databases',
            side_effect=Exception('DB error'),
        )

        with pytest.raises(Exception, match='DB error'):
            await list_databases_tool(mock_ctx, 'test-cluster')


class TestListSchemasTool:
    """Tests for the list_schemas MCP tool."""

    @pytest.mark.asyncio
    async def test_list_schemas_tool_success(self, mocker):
        """Test successful schema discovery."""
        mock_discover_schemas = mocker.patch('awslabs.redshift_mcp_server.server.discover_schemas')
        mock_discover_schemas.return_value = [
            RedshiftSchema(
                database_name='dev',
                schema_name='public',
                schema_owner=100,
                schema_type='local',
                schema_acl='user=admin',
                source_database=None,
                schema_option=None,
            ),
            RedshiftSchema(
                database_name='dev',
                schema_name='external_schema',
                schema_owner=100,
                schema_type='external',
                schema_acl='user=admin',
                source_database='s3_source',
                schema_option='IAM_ROLE arn:aws:iam::123456789012:role/RedshiftRole',
            ),
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
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_schemas',
            side_effect=Exception('Schema error'),
        )

        with pytest.raises(Exception, match='Schema error'):
            await list_schemas_tool(mock_ctx, 'test-cluster', 'test-db')


class TestListTablesTool:
    """Tests for the list_tables MCP tool."""

    @pytest.mark.asyncio
    async def test_list_tables_tool_success(self, mocker):
        """Test successful table discovery."""
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.server.discover_tables')
        mock_discover_tables.return_value = [
            RedshiftTable(
                database_name='dev',
                schema_name='public',
                table_name='users',
                table_acl='user=admin',
                table_type='TABLE',
                remarks='User data table',
            ),
            RedshiftTable(
                database_name='dev',
                schema_name='public',
                table_name='user_view',
                table_acl='user=admin',
                table_type='VIEW',
                remarks='User view',
            ),
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
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_tables',
            side_effect=Exception('Table error'),
        )

        with pytest.raises(Exception, match='Table error'):
            await list_tables_tool(mock_ctx, 'test-cluster', 'test-db', 'test-schema')


class TestListColumnsTool:
    """Tests for the list_columns MCP tool."""

    @pytest.mark.asyncio
    async def test_list_columns_tool_success(self, mocker):
        """Test successful column discovery."""
        mock_discover_columns = mocker.patch('awslabs.redshift_mcp_server.server.discover_columns')
        mock_discover_columns.return_value = [
            RedshiftColumn(
                database_name='dev',
                schema_name='public',
                table_name='users',
                column_name='id',
                ordinal_position=1,
                column_default=None,
                is_nullable='NO',
                data_type='integer',
                character_maximum_length=None,
                numeric_precision=None,
                numeric_scale=None,
                remarks='Primary key',
            ),
            RedshiftColumn(
                database_name='dev',
                schema_name='public',
                table_name='users',
                column_name='name',
                ordinal_position=2,
                column_default=None,
                is_nullable='YES',
                data_type='varchar',
                character_maximum_length=255,
                numeric_precision=None,
                numeric_scale=None,
                remarks='User name',
            ),
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
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.discover_columns',
            side_effect=Exception('Column error'),
        )

        with pytest.raises(Exception, match='Column error'):
            await list_columns_tool(
                mock_ctx, 'test-cluster', 'test-db', 'test-schema', 'test-table'
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
            'query_id': 'query-123',
        }

        result = await execute_query_tool(
            Context(),
            ConfirmWrite(confirmed=True),
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
        assert result.query_id == 'query-123'

    @pytest.mark.parametrize(
        ('access_mode', 'allow_writes'),
        [(ACCESS_MODE_READ_ONLY, False), (ACCESS_MODE_READ_WRITE, True)],
    )
    @pytest.mark.asyncio
    async def test_execute_query_tool_forwards_configured_mode(
        self, mocker, access_mode, allow_writes
    ):
        """The tool translates the server's configured mode into the execute_query flag."""
        mocker.patch('awslabs.redshift_mcp_server.server.ACCESS_MODE', access_mode)
        mock_execute_query = mocker.patch('awslabs.redshift_mcp_server.server.execute_query')
        mock_execute_query.return_value = {
            'columns': ['id'],
            'rows': [[1]],
            'row_count': 1,
            'query_id': 'query-123',
        }

        await execute_query_tool(
            Context(),
            ConfirmWrite(confirmed=True),
            cluster_identifier='test-cluster',
            database_name='dev',
            sql='SELECT 1 AS id',
        )

        mock_execute_query.assert_called_once_with(
            cluster_identifier='test-cluster',
            database_name='dev',
            sql='SELECT 1 AS id',
            enforce_read_only=not allow_writes,
            begin_transaction=None,
            in_transaction=None,
            commit_transaction=None,
            rollback_transaction=None,
        )

    @pytest.mark.asyncio
    async def test_accepted_but_unconfirmed_statement_is_not_executed(self, mocker):
        """An accepted prompt answered `confirmed: false` stops the statement.

        Decline and cancel never reach here: the framework aborts the call at the
        resolver, so this covers only the accepted-but-refused path.
        """
        from unittest.mock import Mock

        mock_execute_query = mocker.patch('awslabs.redshift_mcp_server.server.execute_query')
        mock_ctx = Mock()

        with pytest.raises(ToolError, match='not confirmed'):
            await execute_query_tool(
                mock_ctx,
                ConfirmWrite(confirmed=False),
                cluster_identifier='test-cluster',
                database_name='dev',
                sql='DELETE FROM t',
            )

        mock_execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_query_tool_empty_results(self, mocker):
        """Test query execution with no results."""
        mock_execute_query = mocker.patch('awslabs.redshift_mcp_server.server.execute_query')
        mock_execute_query.return_value = {
            'columns': ['count'],
            'rows': [],
            'row_count': 0,
            'query_id': 'query-456',
        }

        result = await execute_query_tool(
            Context(),
            ConfirmWrite(confirmed=True),
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
        assert result.query_id == 'query-456'

    @pytest.mark.asyncio
    async def test_execute_query_tool_error(self, mocker):
        """Test execute_query_tool error handling."""
        from unittest.mock import Mock

        mock_ctx = Mock()

        mocker.patch(
            'awslabs.redshift_mcp_server.server.execute_query',
            side_effect=Exception('Query error'),
        )

        with pytest.raises(Exception, match='Query error'):
            await execute_query_tool(
                mock_ctx, ConfirmWrite(confirmed=True), 'test-cluster', 'test-db', 'SELECT 1'
            )


class TestReviewClusterTool:
    """Tests for the review_cluster MCP tool."""

    def _make_review_result(self, findings=None):
        """Helper to build a ReviewResult with sensible defaults."""
        return ReviewResult(
            signals_evaluated=13,
            findings=findings or [],
            recommendations=[
                ReviewRecommendation(
                    id='REC_017',
                    text='## For additional scalability, enable short query acceleration\n\n...',
                    triggered_by_signals=['WLMConfig'],
                ),
            ]
            if findings
            else [],
            queries_executed=['NodeDetails', 'WLMConfig'],
        )

    def _make_mock_ctx(self, mocker):
        """Build a mock Context."""
        mock_ctx = mocker.Mock(spec=Context)
        mock_ctx.request_context = mocker.Mock()
        return mock_ctx

    @pytest.mark.asyncio
    async def test_review_cluster_success(self, mocker):
        """Test review_cluster returns a ReviewResult on success."""
        findings = [
            ReviewFinding(
                signal_name='HighSQAEligibility',
                section='WLMConfig',
                affected_row_count=3,
                unit='queues',
                recommendation_ids=['REC_017'],
            ),
        ]
        expected = self._make_review_result(findings=findings)

        mock_pipeline = mocker.patch(
            'awslabs.redshift_mcp_server.server.review_cluster',
            return_value=expected,
        )
        mock_ctx = self._make_mock_ctx(mocker)

        result = await review_cluster_tool(
            ctx=mock_ctx,
            cluster_identifier='test-cluster',
            database_name='dev',
        )

        assert isinstance(result, ReviewResult)
        assert result.signals_evaluated == 13
        assert len(result.findings) == 1
        assert result.findings[0].signal_name == 'HighSQAEligibility'
        assert result.findings[0].affected_row_count == 3
        assert len(result.recommendations) == 1
        assert result.recommendations[0].id == 'REC_017'

        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args.kwargs
        assert call_kwargs['cluster_identifier'] == 'test-cluster'
        assert call_kwargs['database_name'] == 'dev'

    @pytest.mark.asyncio
    async def test_review_cluster_empty_results(self, mocker):
        """Test review_cluster with no findings returns a clean response."""
        expected = self._make_review_result(findings=[])

        mocker.patch(
            'awslabs.redshift_mcp_server.server.review_cluster',
            return_value=expected,
        )
        mock_ctx = self._make_mock_ctx(mocker)

        result = await review_cluster_tool(
            ctx=mock_ctx,
            cluster_identifier='test-cluster',
            database_name='dev',
        )

        assert isinstance(result, ReviewResult)
        assert result.findings == []
        assert result.recommendations == []
        assert result.signals_evaluated == 13

    @pytest.mark.asyncio
    async def test_review_cluster_error(self, mocker):
        """Test review_cluster propagates pipeline errors."""
        mocker.patch(
            'awslabs.redshift_mcp_server.server.review_cluster',
            side_effect=Exception('Data API timeout'),
        )
        mock_ctx = self._make_mock_ctx(mocker)

        with pytest.raises(Exception, match='Data API timeout'):
            await review_cluster_tool(
                ctx=mock_ctx,
                cluster_identifier='test-cluster',
                database_name='dev',
            )


class TestAnticipatedFailuresReachTheModel:
    """Regression cover for GH #4603: anticipated failures keep their text."""

    @pytest.mark.asyncio
    async def test_tool_error_keeps_its_message_and_bare_exception_does_not(self):
        """Pin the SDK contract this server's exception choice depends on.

        The SDK classifies a tool failure by its exception type: `ToolError` is
        anticipated and its message reaches the model, anything else is a crash whose
        text is withheld. Every failure the caller can act on is therefore raised as
        `ToolError`. If a future SDK release changes that split, this test fails and
        names the reason rather than leaving the server quietly opaque again.
        """
        message = 'Statement failed: ERROR: column "error" does not exist'
        scratch = MCPServer('test-anticipated-failures')

        @scratch.tool(name='anticipated')
        async def anticipated() -> str:
            """Fails the way this server's tools fail."""
            raise ToolError(message)

        @scratch.tool(name='crash')
        async def crash() -> str:
            """Fails with a bare exception, as this server used to."""
            raise Exception(message)

        with pytest.raises(ToolError) as anticipated_failure:
            await scratch.call_tool('anticipated', {})
        assert message in str(anticipated_failure.value)
        assert not isinstance(anticipated_failure.value, UnexpectedToolError)

        with pytest.raises(UnexpectedToolError) as crash_failure:
            await scratch.call_tool('crash', {})
        assert message not in str(crash_failure.value)

    @pytest.mark.asyncio
    async def test_aws_reported_failures_keep_their_message(self):
        """An AWS error reaches the caller; a defect in this server does not.

        Found end to end against a paused cluster: the Data API refused the submission with
        `Redshift endpoint is not available`, the server logged exactly that, and the caller
        got a bare "Error executing tool execute_query" with nothing to act on. Every
        infrastructure condition failed the same way, because a `ClientError` was re-raised
        as itself and the SDK withholds the text of anything that is not a `ToolError`.
        """
        denied = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'Redshift endpoint is not available.',
                }
            },
            'BatchExecuteStatement',
        )

        with pytest.raises(ToolError) as reported:
            _tool_failed('execute_query_tool', denied)
        assert 'Redshift endpoint is not available.' in str(reported.value)
        assert not isinstance(reported.value, UnexpectedToolError)

        # The SDK refusing to make the call at all names something the operator must fix, and
        # reaches them as a bare 'Error executing tool ...' unless it is wrapped.
        misconfigured = NoRegionError()
        with pytest.raises(ToolError) as reported:
            _tool_failed('list_clusters_tool', misconfigured)
        assert 'You must specify a region' in str(reported.value)
        assert not isinstance(reported.value, UnexpectedToolError)

        # A bug here tells the caller nothing, so it stays a crash rather than becoming advice.
        defect = KeyError('Records')
        with pytest.raises(KeyError):
            _tool_failed('execute_query_tool', defect)
