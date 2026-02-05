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

"""Tests for the redshift module."""

import pytest
import time
from awslabs.redshift_mcp_server.redshift import (
    RedshiftClientManager,
    RedshiftSessionManager,
    _execute_protected_statement,
    _execute_statement,
    describe_execution_plan,
    discover_clusters,
    discover_columns,
    discover_databases,
    discover_schemas,
    discover_tables,
    execute_query,
)
from botocore.config import Config


class TestRedshiftClientManagerRedshiftClient:
    """Tests for RedshiftClientManager redshift_client() method."""

    def test_redshift_client_creation_default_credentials(self, mocker):
        """Test Redshift client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_client()

        assert client == mock_client
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with('redshift', config=config)

    def test_redshift_client_creation_error(self, mocker):
        """Test Redshift client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('AWS credentials error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='AWS credentials error'):
            manager.redshift_client()

    def test_client_caching(self, mocker):
        """Test that clients are cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        client1 = manager.redshift_client()
        client2 = manager.redshift_client()

        assert client1 == client2 == mock_client
        mock_boto3_session.assert_called_once()

    def test_redshift_client_creation_with_profile_and_region(self, mocker):
        """Test Redshift client creation with AWS profile and region."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_client()

        assert client == mock_client
        mock_session_class.assert_called_once_with(
            profile_name='test-profile', region_name='us-west-2'
        )
        mock_session.client.assert_called_once_with('redshift', config=config)


class TestRedshiftClientManagerServerlessClient:
    """Tests for RedshiftClientManager redshift_serverless_client() method."""

    def test_redshift_serverless_client_creation_default_credentials(self, mocker):
        """Test Redshift Serverless client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_serverless_client()

        assert client == mock_client
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with(
            'redshift-serverless', config=config
        )

    def test_redshift_serverless_client_creation_error(self, mocker):
        """Test Redshift Serverless client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('Serverless client error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='Serverless client error'):
            manager.redshift_serverless_client()

    def test_redshift_serverless_client_creation_with_profile_and_region(self, mocker):
        """Test Redshift Serverless client creation with AWS profile and region."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_serverless_client()

        assert client == mock_client
        mock_session_class.assert_called_once_with(
            profile_name='test-profile', region_name='us-west-2'
        )
        mock_session.client.assert_called_once_with('redshift-serverless', config=config)

    def test_redshift_serverless_client_caching(self, mocker):
        """Test that redshift serverless client is cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        client1 = manager.redshift_serverless_client()
        client2 = manager.redshift_serverless_client()

        assert client1 == client2 == mock_client
        mock_boto3_session.assert_called_once()


class TestRedshiftClientManagerDataClient:
    """Tests for RedshiftClientManager redshift_data_client() method."""

    def test_redshift_data_client_creation_default_credentials(self, mocker):
        """Test Redshift Data API client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_data_client()

        assert client == mock_client
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with(
            'redshift-data', config=config
        )

    def test_redshift_data_client_creation_error(self, mocker):
        """Test Redshift Data client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('Data client error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='Data client error'):
            manager.redshift_data_client()

    def test_redshift_data_client_creation_with_profile_and_region(self, mocker):
        """Test Redshift Data API client creation with AWS profile and region."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_data_client()

        assert client == mock_client
        mock_session_class.assert_called_once_with(
            profile_name='test-profile', region_name='us-west-2'
        )
        mock_session.client.assert_called_once_with('redshift-data', config=config)

    def test_redshift_data_client_caching(self, mocker):
        """Test that redshift data client is cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        client1 = manager.redshift_data_client()
        client2 = manager.redshift_data_client()

        assert client1 == client2 == mock_client
        mock_boto3_session.assert_called_once()


class TestExecuteProtectedStatement:
    """Tests for _execute_protected_statement function."""

    @pytest.mark.asyncio
    async def test_execute_protected_statement_read_only(self, mocker):
        """Test executing protected statement in read-only mode."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )
        mock_execute_statement.side_effect = ['begin-stmt-id', 'user-stmt-id', 'end-stmt-id']

        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = {'Records': [], 'ColumnMetadata': []}
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        result = await _execute_protected_statement(
            'test-cluster', 'test-db', 'SELECT 1', allow_read_write=False
        )

        mock_session_manager.session.assert_called_once()
        assert mock_execute_statement.call_count == 3
        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ ONLY;'
        assert calls[1][1]['sql'] == 'SELECT 1'
        assert calls[2][1]['sql'] == 'END;'
        assert result[1] == 'user-stmt-id'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_read_write(self, mocker):
        """Test executing protected statement in read-write mode."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )
        mock_execute_statement.side_effect = ['begin-stmt-id', 'user-stmt-id', 'end-stmt-id']

        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = {'Records': [], 'ColumnMetadata': []}
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        await _execute_protected_statement(
            'test-cluster', 'test-db', 'DROP TABLE test', allow_read_write=True
        )

        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ WRITE;'
        assert calls[1][1]['sql'] == 'DROP TABLE test'
        assert calls[2][1]['sql'] == 'END;'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_transaction_breaker_error(self, mocker):
        """Test transaction breaker protection in read-only mode."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        suspicious_sqls = [
            'END; SELECT 1',
            '  COMMIT\t\r\n; SELECT 1',
            ';;;abort -- slc \n; SELECT 1',
            'ABORT work; SELECT 1',
            '/* mlc */ COMMIT work;;   ; SELECT 1',
            'commit   TRANSACTION/* mlc /* /* mlc */ mlc */ */; SELECT 1',
            'rollback  ; -- slc \n SELECT 1',
            'ROLLBACK TRANSACTION;/* mlc /* /* mlc */ mlc */ */SELECT 1',
            ';; \t\r\n; rollback -- slc\n  /* mlc -- mlc \n */  work;-- slc \n SELECT 1',
            'SELECT 1; COMMIT;',
        ]

        for sql in suspicious_sqls:
            with pytest.raises(
                Exception,
                match='SQL contains suspicious pattern, execution rejected',
            ):
                await _execute_protected_statement(
                    'test-cluster', 'test-db', sql, allow_read_write=False
                )

    @pytest.mark.asyncio
    async def test_execute_protected_statement_cluster_not_found(self, mocker):
        """Test error when cluster is not found."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = []

        with pytest.raises(Exception, match='Cluster nonexistent-cluster not found'):
            await _execute_protected_statement(
                'nonexistent-cluster', 'test-db', 'SELECT 1', allow_read_write=False
            )

    @pytest.mark.asyncio
    async def test_execute_protected_statement_cluster_not_in_list(self, mocker):
        """Test error when cluster is not in the returned list."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'other-cluster', 'type': 'provisioned'},
            {'identifier': 'another-cluster', 'type': 'serverless'},
        ]

        with pytest.raises(Exception, match='Cluster target-cluster not found'):
            await _execute_protected_statement(
                'target-cluster', 'test-db', 'SELECT 1', allow_read_write=False
            )

    @pytest.mark.asyncio
    async def test_execute_protected_statement_user_sql_fails_end_succeeds(self, mocker):
        """Test user SQL fails but END succeeds - should raise user SQL error."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )

        def execute_side_effect(cluster_info, cluster_identifier, database_name, sql, **kwargs):
            if sql == 'BEGIN READ ONLY;':
                return 'begin-stmt-id'
            elif sql == 'SELECT invalid_syntax':
                raise Exception('SQL syntax error')
            elif sql == 'END;':
                return 'end-stmt-id'
            return 'stmt-id'

        mock_execute_statement.side_effect = execute_side_effect

        with pytest.raises(Exception, match='SQL syntax error'):
            await _execute_protected_statement(
                'test-cluster', 'test-db', 'SELECT invalid_syntax', allow_read_write=False
            )

        assert mock_execute_statement.call_count == 3
        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ ONLY;'
        assert calls[1][1]['sql'] == 'SELECT invalid_syntax'
        assert calls[2][1]['sql'] == 'END;'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_user_sql_succeeds_end_fails(self, mocker):
        """Test user SQL succeeds but END fails - should raise END error."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )

        def execute_side_effect(cluster_info, cluster_identifier, database_name, sql, **kwargs):
            if sql == 'BEGIN READ ONLY;':
                return 'begin-stmt-id'
            elif sql == 'SELECT 1':
                return 'user-stmt-id'
            elif sql == 'END;':
                raise Exception('END statement failed')
            return 'stmt-id'

        mock_execute_statement.side_effect = execute_side_effect

        with pytest.raises(Exception, match='END statement failed'):
            await _execute_protected_statement(
                'test-cluster', 'test-db', 'SELECT 1', allow_read_write=False
            )

    @pytest.mark.asyncio
    async def test_execute_protected_statement_both_user_sql_and_end_fail(self, mocker):
        """Test both user SQL and END fail - should raise combined error."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )

        def execute_side_effect(cluster_info, cluster_identifier, database_name, sql, **kwargs):
            if sql == 'BEGIN READ ONLY;':
                return 'begin-stmt-id'
            elif sql == 'SELECT invalid_syntax':
                raise Exception('SQL syntax error')
            elif sql == 'END;':
                raise Exception('END statement failed')
            return 'stmt-id'

        mock_execute_statement.side_effect = execute_side_effect

        with pytest.raises(
            Exception,
            match='User SQL failed: SQL syntax error; END statement failed: END statement failed',
        ):
            await _execute_protected_statement(
                'test-cluster', 'test-db', 'SELECT invalid_syntax', allow_read_write=False
            )


class TestExecuteStatement:
    """Tests for _execute_statement function."""

    @pytest.mark.asyncio
    async def test_execute_statement_failed_status(self, mocker):
        """Test _execute_statement with FAILED status."""
        mock_client = mocker.Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {
            'Status': 'FAILED',
            'Error': 'SQL syntax error',
        }

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_client,
        )

        cluster_info = {'type': 'provisioned'}
        with pytest.raises(Exception, match='Statement failed: SQL syntax error'):
            await _execute_statement(cluster_info, 'cluster', 'db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_execute_statement_timeout(self, mocker):
        """Test _execute_statement timeout."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        mock_client = mocker.Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'RUNNING'}

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_client,
        )

        cluster_info = {'type': 'provisioned'}
        with pytest.raises(Exception, match='Statement timed out after'):
            await _execute_statement(
                cluster_info,
                'test-cluster',
                'db',
                'SELECT 1',
                query_timeout=0.1,
                query_poll_interval=0.05,
            )

    @pytest.mark.asyncio
    async def test_execute_statement_unknown_cluster_type(self, mocker):
        """Test _execute_statement with unknown cluster type."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'unknown-type'}
        ]

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_data_client = mocker.Mock()
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        cluster_info = {'type': 'unknown-type', 'identifier': 'test-cluster'}

        with pytest.raises(Exception, match='Unknown cluster type: unknown-type'):
            await _execute_statement(cluster_info, 'test-cluster', 'dev', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_execute_statement_with_parameters(self, mocker):
        """Test _execute_statement with parameters."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        mock_client = mocker.Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_client

        cluster_info = {'type': 'provisioned', 'identifier': 'test-cluster'}
        parameters = [{'name': 'param1', 'value': 'value1'}]

        await _execute_statement(
            cluster_info, 'test-cluster', 'dev', 'SELECT 1', parameters=parameters
        )

        call_args = mock_client.execute_statement.call_args[1]
        assert 'Parameters' in call_args
        assert call_args['Parameters'] == parameters

    @pytest.mark.asyncio
    async def test_execute_statement_with_session_id(self, mocker):
        """Test _execute_statement with session_id."""
        mock_client = mocker.Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_client

        cluster_info = {'type': 'provisioned', 'identifier': 'test-cluster'}

        await _execute_statement(
            cluster_info, 'test-cluster', 'dev', 'SELECT 1', session_id='session-123'
        )

        call_args = mock_client.execute_statement.call_args[1]
        assert 'SessionId' in call_args
        assert call_args['SessionId'] == 'session-123'
        assert 'Database' not in call_args
        assert 'ClusterIdentifier' not in call_args


class TestRedshiftSessionManager:
    """Tests for RedshiftSessionManager."""

    @pytest.mark.asyncio
    async def test_session_creation_provisioned(self, mocker):
        """Test session creation for provisioned cluster."""
        session_manager = RedshiftSessionManager(session_keepalive=600, app_name='test-app/1.0')
        cluster_info = {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}

        mock_response = {'SessionId': 'test-session-123', 'Id': 'statement-456'}

        mock_data_client = mocker.Mock()
        mock_data_client.execute_statement.return_value = mock_response
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SessionId': 'test-session-123',
        }

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        session_id = await session_manager.session('test-cluster', 'test-db', cluster_info)

        assert session_id == 'test-session-123'
        mock_data_client.execute_statement.assert_called_once()
        call_args = mock_data_client.execute_statement.call_args
        assert call_args[1]['ClusterIdentifier'] == 'test-cluster'
        assert call_args[1]['Database'] == 'test-db'
        assert 'SET application_name' in call_args[1]['Sql']

    @pytest.mark.asyncio
    async def test_session_creation_serverless(self, mocker):
        """Test session creation for serverless workgroup."""
        session_manager = RedshiftSessionManager(session_keepalive=600, app_name='test-app/1.0')
        cluster_info = {
            'identifier': 'test-workgroup',
            'type': 'serverless',
            'status': 'available',
        }

        mock_response = {'SessionId': 'test-session-456', 'Id': 'statement-789'}

        mock_data_client = mocker.Mock()
        mock_data_client.execute_statement.return_value = mock_response
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SessionId': 'test-session-456',
        }

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        session_id = await session_manager.session('test-workgroup', 'test-db', cluster_info)

        assert session_id == 'test-session-456'
        call_args = mock_data_client.execute_statement.call_args
        assert call_args[1]['WorkgroupName'] == 'test-workgroup'
        assert 'ClusterIdentifier' not in call_args[1]

    @pytest.mark.asyncio
    async def test_session_reuse(self, mocker):
        """Test that existing sessions are reused."""
        session_manager = RedshiftSessionManager(session_keepalive=600, app_name='test-app/1.0')
        cluster_info = {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}

        mock_response = {'SessionId': 'test-session-123', 'Id': 'statement-456'}

        mock_data_client = mocker.Mock()
        mock_data_client.execute_statement.return_value = mock_response
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SessionId': 'test-session-123',
        }

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        session_id1 = await session_manager.session('test-cluster', 'test-db', cluster_info)
        session_id2 = await session_manager.session('test-cluster', 'test-db', cluster_info)

        assert session_id1 == session_id2 == 'test-session-123'
        mock_data_client.execute_statement.assert_called_once()

    def test_session_expiration_check(self):
        """Test session expiration logic."""
        session_keepalive = 600
        session_manager = RedshiftSessionManager(
            session_keepalive=session_keepalive, app_name='test-app/1.0'
        )

        fresh_session = {'created_at': time.time()}
        assert not session_manager._is_session_expired(fresh_session)

        old_session = {'created_at': time.time() - session_keepalive - 1}
        assert session_manager._is_session_expired(old_session)


class TestDiscoverFunctions:
    """Tests for discover_*() functions."""

    @pytest.mark.asyncio
    async def test_discover_clusters_provisioned(self, mocker):
        """Test discover_clusters function with provisioned clusters."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {
                'Clusters': [
                    {
                        'ClusterIdentifier': 'test-cluster',
                        'ClusterStatus': 'available',
                        'DBName': 'dev',
                        'Endpoint': {'Address': 'test.redshift.amazonaws.com', 'Port': 5439},
                        'VpcId': 'vpc-123',
                        'NodeType': 'dc2.large',
                        'NumberOfNodes': 2,
                        'ClusterCreateTime': '2024-01-01T00:00:00Z',
                        'MasterUsername': 'admin',
                        'PubliclyAccessible': False,
                        'Encrypted': True,
                        'Tags': [{'Key': 'env', 'Value': 'test'}],
                    }
                ]
            }
        ]

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 1
        cluster = result[0]
        assert cluster['identifier'] == 'test-cluster'
        assert cluster['type'] == 'provisioned'
        assert cluster['status'] == 'available'
        assert cluster['database_name'] == 'dev'

    @pytest.mark.asyncio
    async def test_discover_databases(self, mocker):
        """Test discover_databases function."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'longValue': 100},
                        {'stringValue': 'local'},
                        {'stringValue': 'user=admin'},
                        {'stringValue': 'encoding=utf8'},
                        {'stringValue': 'Snapshot Isolation'},
                    ]
                ]
            },
            'query-123',
        )

        result = await discover_databases('test-cluster', 'dev')

        assert len(result) == 1
        assert result[0]['database_name'] == 'dev'
        assert result[0]['database_owner'] == 100
        assert result[0]['database_type'] == 'local'

    @pytest.mark.asyncio
    async def test_discover_schemas(self, mocker):
        """Test discover_schemas function."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
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
                ]
            },
            'query-456',
        )

        result = await discover_schemas('test-cluster', 'dev')

        assert len(result) == 1
        assert result[0]['database_name'] == 'dev'
        assert result[0]['schema_name'] == 'public'

    @pytest.mark.asyncio
    async def test_discover_tables(self, mocker):
        """Test discover_tables function with enhanced metadata."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call returns basic table info
        # Second call returns enhanced metadata from svv_table_info
        mock_execute_protected.side_effect = [
            (
                {
                    'Records': [
                        [
                            {'stringValue': 'dev'},
                            {'stringValue': 'public'},
                            {'stringValue': 'users'},
                            {'stringValue': 'user=admin'},
                            {'stringValue': 'TABLE'},
                            {'stringValue': 'User data table'},
                            {'stringValue': None},  # external_location
                            {'stringValue': None},  # external_parameters
                        ]
                    ]
                },
                'query-789',
            ),
            (
                {
                    'Records': [
                        [
                            {'stringValue': 'dev'},  # database
                            {'stringValue': 'public'},  # schema
                            {'stringValue': 'users'},  # table
                            {'stringValue': 'KEY'},  # diststyle
                            {'stringValue': 'id'},  # sortkey1
                            {'stringValue': 'Y'},  # encoded
                            {'longValue': 1000000},  # tbl_rows
                            {'longValue': 512},  # size
                            {'doubleValue': 75.5},  # pct_used
                            {'doubleValue': 5.2},  # stats_off
                            {'doubleValue': 1.1},  # skew_rows
                        ]
                    ]
                },
                'query-790',
            ),
        ]

        result = await discover_tables('test-cluster', 'dev', 'public')

        assert len(result) == 1
        assert result[0]['table_name'] == 'users'
        assert result[0]['table_type'] == 'TABLE'
        assert result[0]['redshift_diststyle'] == 'KEY'
        assert result[0]['redshift_sortkey1'] == 'id'
        assert result[0]['redshift_encoded'] == 'Y'
        assert result[0]['redshift_tbl_rows'] == 1000000
        assert result[0]['redshift_size'] == 512
        assert result[0]['redshift_pct_used'] == 75.5
        assert result[0]['redshift_stats_off'] == 5.2
        assert result[0]['redshift_skew_rows'] == 1.1

        # Verify both queries were called
        assert mock_execute_protected.call_count == 2

    @pytest.mark.asyncio
    async def test_discover_tables_serverless_fallback(self, mocker):
        """Test discover_tables graceful degradation when svv_table_info fails (serverless)."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call returns basic table info (succeeds)
        # Second call fails (simulating serverless where svv_table_info is not supported)
        mock_execute_protected.side_effect = [
            (
                {
                    'Records': [
                        [
                            {'stringValue': 'dev'},
                            {'stringValue': 'public'},
                            {'stringValue': 'users'},
                            {'stringValue': 'user=admin'},
                            {'stringValue': 'TABLE'},
                            {'stringValue': 'User data table'},
                            {'stringValue': None},  # external_location
                            {'stringValue': None},  # external_parameters
                        ]
                    ]
                },
                'query-789',
            ),
            Exception('Specified types or functions not supported on Redshift tables'),
        ]

        result = await discover_tables('test-cluster', 'dev', 'public')

        # Should still return basic table info
        assert len(result) == 1
        assert result[0]['table_name'] == 'users'
        assert result[0]['table_type'] == 'TABLE'

        # Enhanced metadata should be None (fallback values)
        assert result[0]['redshift_diststyle'] is None
        assert result[0]['redshift_sortkey1'] is None
        assert result[0]['redshift_encoded'] is None
        assert result[0]['redshift_tbl_rows'] is None
        assert result[0]['redshift_size'] is None
        assert result[0]['redshift_pct_used'] is None
        assert result[0]['redshift_stats_off'] is None
        assert result[0]['redshift_skew_rows'] is None

        # Verify both queries were attempted
        assert mock_execute_protected.call_count == 2

    @pytest.mark.asyncio
    async def test_discover_columns(self, mocker):
        """Test discover_columns function."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
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
                        {'stringValue': 'lzo'},
                        {'booleanValue': True},
                        {'longValue': 1},
                        {'stringValue': None},
                        {'longValue': None},
                    ]
                ]
            },
            'query-101',
        )

        result = await discover_columns('test-cluster', 'dev', 'public', 'users')

        assert len(result) == 1
        assert result[0]['column_name'] == 'id'
        assert result[0]['data_type'] == 'integer'
        assert result[0]['redshift_encoding'] == 'lzo'
        assert result[0]['redshift_distkey'] is True
        assert result[0]['redshift_sortkey'] == 1


class TestExecuteQuery:
    """Tests for execute_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, mocker):
        """Test successful query execution."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'id'}, {'name': 'name'}],
                'Records': [[{'longValue': 1}, {'stringValue': 'Test User'}]],
            },
            'query-123',
        )

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.123]

        result = await execute_query('test-cluster', 'dev', 'SELECT id, name FROM users LIMIT 1')

        assert result['columns'] == ['id', 'name']
        assert result['rows'] == [[1, 'Test User']]
        assert result['row_count'] == 1
        assert result['execution_time_ms'] == 123
        assert result['query_id'] == 'query-123'

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, mocker):
        """Test error handling in execute_query."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Query execution failed')

        with pytest.raises(Exception, match='Query execution failed'):
            await execute_query('test-cluster', 'dev', 'SELECT * FROM nonexistent')


class TestDescribeExecutionPlan:
    """Tests for describe_execution_plan function."""

    @pytest.mark.asyncio
    async def test_describe_execution_plan_success(self, mocker):
        """Test successful execution plan generation with verbose tree format."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        # Simulate EXPLAIN VERBOSE output with tree structure and human-readable plan
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': '   { LIMIT'}],
                    [{'stringValue': '   :startup_cost 0.00'}],
                    [{'stringValue': '   :total_cost 0.07'}],
                    [{'stringValue': '   :plan_rows 5'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   :plan_width 27'}],
                    [{'stringValue': '   :dist_info.dist_strategy DS_DIST_ERR'}],
                    [{'stringValue': '     { SEQSCAN'}],
                    [{'stringValue': '     :startup_cost 0.00'}],
                    [{'stringValue': '     :total_cost 1.00'}],
                    [{'stringValue': '     :plan_rows 100'}],
                    [{'stringValue': '     :node_id 2'}],
                    [{'stringValue': '     :parent_id 1'}],
                    [{'stringValue': '     :plan_width 27'}],
                    [{'stringValue': '     :dist_info.dist_strategy DS_DIST_NONE'}],
                    [{'stringValue': '     :table "users"'}],  # Table name from verbose output
                    [{'stringValue': ''}],  # Empty line separator
                    [{'stringValue': 'XN Limit  (cost=0.00..0.07 rows=5 width=27)'}],
                    [
                        {
                            'stringValue': '  ->  XN Seq Scan on users  (cost=0.00..1.00 rows=100 width=27)'
                        }
                    ],
                ]
            },
            'explain-123',
        )

        # Mock discover_tables to return empty
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = []

        # Mock discover_columns to return empty
        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.05]

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM users LIMIT 5'
        )

        assert result['plan_format'] == 'structured'
        assert result['explained_query'] == 'SELECT * FROM users LIMIT 5'
        assert result['query_id'] == 'explain-123'
        assert 49 <= result['planning_time_ms'] <= 51

        assert isinstance(result['query_plan'], list)
        assert len(result['query_plan']) == 2

        node1 = result['query_plan'][0]
        assert node1['node_id'] == 1
        assert node1['operation'] == 'Limit'
        assert node1['cost_startup'] == 0.00
        assert node1['cost_total'] == 0.07
        assert node1['rows'] == 5

        node2 = result['query_plan'][1]
        assert node2['node_id'] == 2
        assert node2['parent_node_id'] == 1
        assert node2['operation'] == 'Seq Scan'
        assert node2['distribution_type'] == 'DS_DIST_NONE'

        assert isinstance(result['table_designs'], list)

        assert 'human_readable_plan' in result
        assert 'XN Limit' in result['human_readable_plan']
        assert 'XN Seq Scan on users' in result['human_readable_plan']

        assert 'suggestions' in result
        assert isinstance(result['suggestions'], list)

    @pytest.mark.asyncio
    async def test_describe_execution_plan_already_has_explain(self, mocker):
        """Test error when SQL already contains EXPLAIN."""
        with pytest.raises(
            Exception,
            match='SQL already contains EXPLAIN. Please provide the query without EXPLAIN.',
        ):
            await describe_execution_plan('test-cluster', 'dev', 'EXPLAIN SELECT * FROM users')

    @pytest.mark.asyncio
    async def test_describe_execution_plan_error_handling(self, mocker):
        """Test error handling in describe_execution_plan."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('EXPLAIN query failed')

        with pytest.raises(Exception, match='EXPLAIN query failed'):
            await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM invalid_table')

    @pytest.mark.asyncio
    async def test_describe_execution_plan_with_table_designs(self, mocker):
        """Test that table designs are fetched and included in execution plan."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Mock for EXPLAIN VERBOSE query
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :startup_cost 0.00'}],
                    [{'stringValue': '   :total_cost 10.00'}],
                    [{'stringValue': '   :plan_rows 100'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   :plan_width 8'}],
                    [{'stringValue': '   :dist_info.dist_strategy DS_DIST_NONE'}],
                    [{'stringValue': '   :table "users"'}],
                    [{'stringValue': ''}],
                    [
                        {
                            'stringValue': 'XN Seq Scan on public.users  (cost=0.00..10.00 rows=100 width=8)'
                        }
                    ],
                ]
            },
            'explain-123',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'table_acl': 'user=admin',
                'table_type': 'TABLE',
                'remarks': 'User data table',
                'redshift_diststyle': 'KEY',
                'redshift_sortkey1': 'id',
                'external_location': None,
                'external_parameters': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
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
                'numeric_precision': 32,
                'numeric_scale': 0,
                'remarks': 'Primary key',
                'redshift_encoding': 'lzo',
                'redshift_distkey': True,
                'redshift_sortkey': 1,
                'external_type': None,
            }
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM public.users')

        assert 'table_designs' in result
        assert isinstance(result['table_designs'], list)
        assert len(result['table_designs']) == 1

        table_design = result['table_designs'][0]
        assert table_design['schema_name'] == 'public'
        assert table_design['table_name'] == 'users'
        assert table_design['redshift_diststyle'] == 'KEY'
        assert len(table_design['columns']) == 1

        id_col = table_design['columns'][0]
        assert id_col['column_name'] == 'id'
        assert id_col['redshift_distkey'] is True
        assert id_col['redshift_sortkey'] == 1

        # suggestions should be generated based on plan analysis
        assert 'suggestions' in result
        assert isinstance(result['suggestions'], list)

    @pytest.mark.asyncio
    async def test_describe_execution_plan_with_all_node_types(self, mocker):
        """Test execution plan parsing with all 28 PADB node types including 11 newly added types."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        mock_execute_protected.return_value = (
            {
                'Records': [
                    # node types
                    [{'stringValue': '   { LIMIT'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { MERGE'}],
                    [{'stringValue': '   :node_id 2'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { NETWORK'}],
                    [{'stringValue': '   :node_id 3'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SORT'}],
                    [{'stringValue': '   :node_id 4'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { AGG'}],
                    [{'stringValue': '   :node_id 5'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { HASHJOIN'}],
                    [{'stringValue': '   :node_id 6'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { MERGEJOIN'}],
                    [{'stringValue': '   :node_id 7'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { NESTLOOP'}],
                    [{'stringValue': '   :node_id 8'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 9'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { HASH'}],
                    [{'stringValue': '   :node_id 10'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SUBQUERYSCAN'}],
                    [{'stringValue': '   :node_id 11'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { APPEND'}],
                    [{'stringValue': '   :node_id 12'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { RESULT'}],
                    [{'stringValue': '   :node_id 13'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { UNIQUE'}],
                    [{'stringValue': '   :node_id 14'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SETOP'}],
                    [{'stringValue': '   :node_id 15'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { WINDOW'}],
                    [{'stringValue': '   :node_id 16'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { MATERIALIZE'}],
                    [{'stringValue': '   :node_id 17'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { CTESCAN'}],
                    [{'stringValue': '   :node_id 18'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { FUNCTIONSCAN'}],
                    [{'stringValue': '   :node_id 19'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { GROUP'}],
                    [{'stringValue': '   :node_id 20'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { INDEXSCAN'}],
                    [{'stringValue': '   :node_id 21'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { METADATAHASH'}],
                    [{'stringValue': '   :node_id 22'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { METADATALOOP'}],
                    [{'stringValue': '   :node_id 23'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { PADBTBLUDFSOURCESCAN'}],
                    [{'stringValue': '   :node_id 24'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { PADBTBLUDFXFORMSCAN'}],
                    [{'stringValue': '   :node_id 25'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { PARTITIONLOOP'}],
                    [{'stringValue': '   :node_id 26'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { TIDSCAN'}],
                    [{'stringValue': '   :node_id 27'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { UNNEST'}],
                    [{'stringValue': '   :node_id 28'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Limit  (cost=0.00..0.07 rows=5 width=27)'}],
                ]
            },
            'explain-all-nodes',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = []

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.05]

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM complex_query'
        )

        assert len(result['query_plan']) == 28

        # Verify node types
        assert result['query_plan'][0]['operation'] == 'Limit'
        assert result['query_plan'][1]['operation'] == 'Merge'
        assert result['query_plan'][2]['operation'] == 'Network'
        assert result['query_plan'][3]['operation'] == 'Sort'
        assert result['query_plan'][4]['operation'] == 'Aggregate'
        assert result['query_plan'][5]['operation'] == 'Hash Join'
        assert result['query_plan'][6]['operation'] == 'Merge Join'
        assert result['query_plan'][7]['operation'] == 'Nested Loop'
        assert result['query_plan'][8]['operation'] == 'Seq Scan'
        assert result['query_plan'][9]['operation'] == 'Hash'
        assert result['query_plan'][10]['operation'] == 'Subquery Scan'
        assert result['query_plan'][11]['operation'] == 'Append'
        assert result['query_plan'][12]['operation'] == 'Result'
        assert result['query_plan'][13]['operation'] == 'Unique'
        assert result['query_plan'][14]['operation'] == 'SetOp'
        assert result['query_plan'][15]['operation'] == 'Window'
        assert result['query_plan'][16]['operation'] == 'Materialize'
        assert result['query_plan'][17]['operation'] == 'CTE Scan'
        assert result['query_plan'][18]['operation'] == 'Function Scan'
        assert result['query_plan'][19]['operation'] == 'Group'
        assert result['query_plan'][20]['operation'] == 'Index Scan'
        assert result['query_plan'][21]['operation'] == 'Metadata Hash'
        assert result['query_plan'][22]['operation'] == 'Metadata Loop'
        assert result['query_plan'][23]['operation'] == 'Table Function Data Source'
        assert result['query_plan'][24]['operation'] == 'Table Function Data Transform'
        assert result['query_plan'][25]['operation'] == 'Partition Loop'
        assert result['query_plan'][26]['operation'] == 'Tid Scan'
        assert result['query_plan'][27]['operation'] == 'Unnest'

        for i, node in enumerate(result['query_plan']):
            assert node['node_id'] == i + 1


class TestGeneratePerformanceSuggestions:
    """Tests for _generate_performance_suggestions function."""

    def test_suggestions_for_data_broadcast(self):
        """Test suggestions are generated for DS_BCAST_INNER distribution."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_BCAST_INNER',
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'broadcast' in suggestions[0].lower()
        assert 'DISTKEY' in suggestions[0]

    def test_suggestions_for_data_redistribution(self):
        """Test suggestions are generated for DS_DIST_INNER distribution."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Merge Join',
                'distribution_type': 'DS_DIST_INNER',
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'redistribution' in suggestions[0].lower()

    def test_suggestions_for_nested_loop(self):
        """Test suggestions are generated for Nested Loop joins."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Nested Loop',
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'Nested Loop' in suggestions[0]

    def test_suggestions_for_even_distribution(self):
        """Test suggestions are generated for EVEN distribution tables."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'EVEN',
                'columns': [
                    {'column_name': 'id', 'redshift_encoding': 'lzo', 'redshift_sortkey': 0},
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('EVEN distribution' in s for s in suggestions)

    def test_suggestions_for_missing_sortkey(self):
        """Test suggestions are generated for tables without SORTKEY."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {'column_name': 'id', 'redshift_encoding': 'lzo', 'redshift_sortkey': 0},
                    {'column_name': 'name', 'redshift_encoding': 'lzo', 'redshift_sortkey': 0},
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('SORTKEY' in s for s in suggestions)

    def test_suggestions_for_no_compression(self):
        """Test suggestions are generated for columns without compression."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {'column_name': 'id', 'redshift_encoding': 'none', 'redshift_sortkey': 1},
                    {'column_name': 'name', 'redshift_encoding': 'none', 'redshift_sortkey': 0},
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('compression' in s.lower() for s in suggestions)

    def test_no_duplicate_suggestions(self):
        """Test that duplicate suggestions are removed."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_BCAST_INNER',
            },
            {
                'node_id': 2,
                'operation': 'Hash Join',
                'distribution_type': 'DS_BCAST_INNER',
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'broadcast' in suggestions[0].lower()

    def test_empty_inputs(self):
        """Test that empty inputs return empty suggestions."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        suggestions = _generate_performance_suggestions([], [])
        assert suggestions == []

    def test_optimal_plan_no_suggestions(self):
        """Test that optimal plans generate no suggestions."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Seq Scan',
                'distribution_type': 'DS_DIST_NONE',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {'column_name': 'id', 'redshift_encoding': 'lzo', 'redshift_sortkey': 1},
                ],
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)

        assert suggestions == []
