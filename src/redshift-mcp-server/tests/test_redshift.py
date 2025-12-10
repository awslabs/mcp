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

    @pytest.mark.asyncio
    async def test_expired_session_cleanup(self, mocker):
        """Test that expired sessions are cleaned up."""
        session_manager = RedshiftSessionManager(session_keepalive=500, app_name='test-app')

        # Mock time to simulate expired session
        mock_time = mocker.patch('awslabs.redshift_mcp_server.redshift.time.time')
        mock_time.side_effect = [2000, 2000, 2000]  # Check at 2000, session created at 1000

        # Add an expired session manually
        session_key = 'test-cluster:dev'
        session_manager._sessions[session_key] = {
            'session_id': 'expired-session',
            'created_at': 1000,
            'last_used': 1000,
        }

        # Mock session creation
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_data_client = mocker.Mock()
        mock_data_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SessionId': 'new-session-id',
        }
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        cluster_info = {'type': 'provisioned', 'identifier': 'test-cluster'}

        # This should clean up the expired session and create a new one
        session_id = await session_manager.session('test-cluster', 'dev', cluster_info)

        assert session_id == 'new-session-id'
        # Verify a new session was created (execute_statement called)
        mock_data_client.execute_statement.assert_called_once()
        # Verify the expired session was deleted and replaced (covers lines 141-142)
        assert session_manager._sessions[session_key]['session_id'] == 'new-session-id'


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
    async def test_discover_clusters_provisioned_error(self, mocker):
        """Test error handling when discovering provisioned clusters fails."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = Exception('AWS API Error')
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.list_workgroups.return_value = {'workgroups': []}

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(Exception, match='AWS API Error'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless(self, mocker):
        """Test discover_clusters function with serverless workgroups."""
        # Mock redshift client (empty response)
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        # Mock serverless client
        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'test-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'configParameters': [{'parameterValue': 'analytics'}],
                'endpoint': {'address': 'test.serverless.amazonaws.com', 'port': 5439},
                'subnetIds': ['subnet-123'],
                'publiclyAccessible': True,
                'tags': [{'key': 'team', 'value': 'data'}],
            }
        }

        # Mock client manager
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
        workgroup = result[0]
        assert workgroup['identifier'] == 'test-workgroup'
        assert workgroup['type'] == 'serverless'
        assert workgroup['status'] == 'AVAILABLE'
        assert workgroup['database_name'] == 'analytics'
        assert workgroup['endpoint'] == 'test.serverless.amazonaws.com'
        assert workgroup['port'] == 5439
        assert workgroup['node_type'] is None
        assert workgroup['number_of_nodes'] is None
        assert workgroup['encrypted'] is True
        assert workgroup['tags'] == {'team': 'data'}

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_error(self, mocker):
        """Test error handling when discovering serverless workgroups fails."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.return_value = []
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = Exception('Serverless API Error')
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(Exception, match='Serverless API Error'):
            await discover_clusters()

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
    async def test_discover_databases_error(self, mocker):
        """Test error handling in discover_databases."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Database discovery failed')

        with pytest.raises(Exception, match='Database discovery failed'):
            await discover_databases('test-cluster')

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
    async def test_discover_schemas_error(self, mocker):
        """Test error handling in discover_schemas."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Schema discovery failed')

        with pytest.raises(Exception, match='Schema discovery failed'):
            await discover_schemas('test-cluster', 'dev')

    @pytest.mark.asyncio
    async def test_discover_tables(self, mocker):
        """Test discover_tables function with enhanced metadata."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call returns basic table info
        # Second call returns enhanced metadata from PG_TABLES_SQL
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
                            {'stringValue': 'public'},  # schema_name (index 0)
                            {'stringValue': 'users'},  # table_name (index 1)
                            {'stringValue': 'KEY'},  # diststyle (index 2)
                            {'stringValue': 'id'},  # sortkey1 (index 3)
                            {'stringValue': 'Y'},  # encoded (index 4)
                            {'longValue': 1000000},  # tbl_rows (index 5)
                            {'longValue': 512},  # size (index 6)
                            {'doubleValue': 75.5},  # pct_used (index 7)
                            {'doubleValue': 5.2},  # stats_off (index 8)
                            {'doubleValue': 1.1},  # skew_rows (index 9)
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
        """Test discover_tables graceful degradation when PG_TABLES_SQL fails (serverless)."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call returns basic table info (succeeds)
        # Second call fails (simulating serverless where pg_stat_user_tables might not be available)
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
    async def test_discover_tables_error(self, mocker):
        """Test error handling in discover_tables."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Table discovery failed')

        with pytest.raises(Exception, match='Table discovery failed'):
            await discover_tables('test-cluster', 'dev', 'public')

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

    @pytest.mark.asyncio
    async def test_discover_columns_error(self, mocker):
        """Test error handling in discover_columns."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Column discovery failed')

        with pytest.raises(Exception, match='Column discovery failed'):
            await discover_columns('test-cluster', 'dev', 'public', 'users')


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

        assert result['explained_query'] == 'SELECT * FROM users LIMIT 5'
        assert result['query_id'] == 'explain-123'
        assert 49 <= result['planning_time_ms'] <= 51

        assert isinstance(result['plan_nodes'], list)
        assert len(result['plan_nodes']) == 2

        node1 = result['plan_nodes'][0]
        assert node1['node_id'] == 1
        assert node1['operation'] == 'Limit'
        assert node1['cost_startup'] == 0.00
        assert node1['cost_total'] == 0.07
        assert node1['rows'] == 5

        node2 = result['plan_nodes'][1]
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

        assert len(result['plan_nodes']) == 28

        # Verify node types
        assert result['plan_nodes'][0]['operation'] == 'Limit'
        assert result['plan_nodes'][1]['operation'] == 'Merge'
        assert result['plan_nodes'][2]['operation'] == 'Network'
        assert result['plan_nodes'][3]['operation'] == 'Sort'
        assert result['plan_nodes'][4]['operation'] == 'Aggregate'
        assert result['plan_nodes'][5]['operation'] == 'Hash Join'
        assert result['plan_nodes'][6]['operation'] == 'Merge Join'
        assert result['plan_nodes'][7]['operation'] == 'Nested Loop'
        assert result['plan_nodes'][8]['operation'] == 'Seq Scan'
        assert result['plan_nodes'][9]['operation'] == 'Hash'
        assert result['plan_nodes'][10]['operation'] == 'Subquery Scan'
        assert result['plan_nodes'][11]['operation'] == 'Append'
        assert result['plan_nodes'][12]['operation'] == 'Result'
        assert result['plan_nodes'][13]['operation'] == 'Unique'
        assert result['plan_nodes'][14]['operation'] == 'SetOp'
        assert result['plan_nodes'][15]['operation'] == 'Window'
        assert result['plan_nodes'][16]['operation'] == 'Materialize'
        assert result['plan_nodes'][17]['operation'] == 'CTE Scan'
        assert result['plan_nodes'][18]['operation'] == 'Function Scan'
        assert result['plan_nodes'][19]['operation'] == 'Group'
        assert result['plan_nodes'][20]['operation'] == 'Index Scan'
        assert result['plan_nodes'][21]['operation'] == 'Metadata Hash'
        assert result['plan_nodes'][22]['operation'] == 'Metadata Loop'
        assert result['plan_nodes'][23]['operation'] == 'Table Function Data Source'
        assert result['plan_nodes'][24]['operation'] == 'Table Function Data Transform'
        assert result['plan_nodes'][25]['operation'] == 'Partition Loop'
        assert result['plan_nodes'][26]['operation'] == 'Tid Scan'
        assert result['plan_nodes'][27]['operation'] == 'Unnest'

        for i, node in enumerate(result['plan_nodes']):
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

    def test_suggestions_for_dist_all_inner(self):
        """Test suggestions for DS_DIST_ALL_INNER distribution."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_ALL_INNER',
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'Full table redistribution' in suggestions[0]
        assert 'DISTSTYLE ALL' in suggestions[0]

    def test_suggestions_for_dist_inner(self):
        """Test suggestions for DS_DIST_INNER distribution."""
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
        assert 'Data redistribution' in suggestions[0]
        assert 'DISTKEY' in suggestions[0]

    def test_suggestions_for_many_uncompressed_columns(self):
        """Test suggestions when many columns have no compression."""
        from awslabs.redshift_mcp_server.redshift import _generate_performance_suggestions

        columns = [{'column_name': f'col{i}', 'redshift_encoding': 'none'} for i in range(10)]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'large_table',
                'redshift_diststyle': 'KEY',
                'redshift_sortkey1': 'col0',
                'columns': columns,
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('columns' in s and 'compression' in s.lower() for s in suggestions)


class TestExecuteQueryDataTypes:
    """Tests for execute_query data type handling."""

    @pytest.mark.asyncio
    async def test_execute_query_with_boolean_values(self, mocker):
        """Test execute_query with boolean data types."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'is_active'}],
                'Records': [[{'booleanValue': True}], [{'booleanValue': False}]],
            },
            'query-123',
        )

        result = await execute_query('test-cluster', 'dev', 'SELECT is_active FROM users')

        assert result['columns'] == ['is_active']
        assert result['rows'] == [[True], [False]]
        assert result['row_count'] == 2

    @pytest.mark.asyncio
    async def test_execute_query_with_unknown_field_type(self, mocker):
        """Test execute_query with unknown field types (fallback to str)."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'data'}],
                'Records': [[{'unknownType': 'some_value'}]],
            },
            'query-123',
        )

        result = await execute_query('test-cluster', 'dev', 'SELECT data FROM test')

        assert result['columns'] == ['data']
        assert len(result['rows']) == 1
        assert isinstance(result['rows'][0][0], str)


class TestDescribeExecutionPlanVerbose:
    """Tests for EXPLAIN VERBOSE parsing to improve coverage."""

    @pytest.mark.asyncio
    async def test_explain_verbose_with_node_properties(self, mocker):
        """Test parsing EXPLAIN VERBOSE with various node properties."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE format with node properties
        verbose_output = """{HASHAGG
:node_id 1
:parent_id 0
:startup_cost 0.00
:total_cost 100.50
:plan_rows 10
:plan_width 8
}
{SEQSCAN
:node_id 2
:parent_id 1
:startup_cost 0.00
:total_cost 50.25
:plan_rows 100
:plan_width 8
:scanrelid 1
}

XN HashAggregate  (cost=0.00..100.50 rows=10 width=8)
  ->  XN Seq Scan on users  (cost=0.00..50.25 rows=100 width=8)"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT COUNT(*) FROM users')

        # Verify nodes were parsed
        assert 'plan_nodes' in result
        nodes = result['plan_nodes']
        assert len(nodes) == 2

        # Find node with node_id 1
        node1 = next((n for n in nodes if n['node_id'] == 1), None)
        assert node1 is not None
        # parent_id 0 is converted to None (root node)
        assert node1['parent_node_id'] is None
        assert node1['cost_startup'] == 0.00
        assert node1['cost_total'] == 100.50
        assert node1['rows'] == 10
        assert node1['width'] == 8

    @pytest.mark.asyncio
    async def test_explain_verbose_with_join_and_agg_properties(self, mocker):
        """Test parsing join and aggregation properties."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE with jointype and aggstrategy
        verbose_output = """{HASHJOIN
:node_id 1
:parent_id 0
:jointype 0
:dist_info.dist_strategy DS_BCAST_INNER
}
{HASHAGG
:node_id 2
:parent_id 1
:aggstrategy 2
:dataMovement Broadcast
}

XN Hash Join  (cost=0.00..100.00 rows=50 width=16)
  ->  XN HashAggregate  (cost=0.00..50.00 rows=10 width=8)"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM t1 JOIN t2')

        # Verify join and agg properties were parsed
        assert 'plan_nodes' in result
        nodes = result['plan_nodes']
        assert len(nodes) == 2

        # Check jointype was parsed
        join_node = next((n for n in nodes if n['node_id'] == 1), None)
        assert join_node is not None
        assert 'join_type' in join_node
        assert join_node['join_type'] == 'Inner'

        # Check aggstrategy was parsed
        agg_node = next((n for n in nodes if n['node_id'] == 2), None)
        assert agg_node is not None
        assert 'agg_strategy' in agg_node
        assert agg_node['agg_strategy'] == 'Hashed'

        # Check dataMovement was parsed
        assert 'data_movement' in agg_node
        assert agg_node['data_movement'] == 'Broadcast'

    @pytest.mark.asyncio
    async def test_explain_verbose_with_table_reference(self, mocker):
        """Test parsing table references in EXPLAIN VERBOSE."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE with table reference
        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:table "myschema"."mytable"
}

XN Seq Scan on myschema.mytable  (cost=0.00..100.00 rows=1000 width=50)"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM myschema.mytable'
        )

        # Verify table reference was parsed
        assert 'plan_nodes' in result
        nodes = result['plan_nodes']
        assert len(nodes) == 1
        node = nodes[0]
        assert 'relation_name' in node
        # Quotes are stripped during parsing
        assert 'myschema' in node['relation_name'] or 'mytable' in node['relation_name']

    @pytest.mark.asyncio
    async def test_explain_verbose_unqualified_table(self, mocker):
        """Test unqualified table reference parsing."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE with unqualified table
        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:table "users"
}

XN Seq Scan on users  (cost=0.00..100.00 rows=1000 width=50)"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        # Verify unqualified table reference was parsed
        assert 'plan_nodes' in result
        nodes = result['plan_nodes']
        assert len(nodes) == 1
        node = nodes[0]
        assert 'relation_name' in node
        # Quotes are stripped during parsing
        assert 'users' in node['relation_name']

    @pytest.mark.asyncio
    async def test_explain_verbose_table_fetch_error(self, mocker):
        """Test error handling when table metadata fetch fails."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:table "users"
}

XN Seq Scan on users  (cost=0.00..100.00 rows=1000 width=50)"""

        mock_execute_protected.side_effect = [
            (
                {
                    'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                    'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
                },
                'explain-123',
            ),
            (
                {
                    'Records': [
                        [
                            {'stringValue': 'dev'},
                            {'stringValue': 'public'},
                            {'stringValue': 'users'},
                            {'stringValue': None},
                            {'stringValue': 'TABLE'},
                            {'stringValue': None},
                            {'stringValue': None},
                            {'stringValue': None},
                        ]
                    ]
                },
                'tables-123',
            ),
            # Simulate error when fetching table metadata
            Exception('Permission denied'),
        ]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        # Should handle error gracefully
        assert 'plan_nodes' in result
        assert 'table_designs' in result
        # Table designs will be empty due to error
        assert len(result['table_designs']) == 0

    @pytest.mark.asyncio
    async def test_explain_verbose_large_plan(self, mocker):
        """Test large plan truncation message."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Create verbose output with >30 lines in human-readable section
        verbose_nodes = '\n'.join(
            [f'{{SEQSCAN\n:node_id {i}\n:parent_id 0\n}}' for i in range(1, 4)]
        )
        human_readable = '\n'.join(
            [
                f'  ->  XN Seq Scan on table{i}  (cost=0.00..100.00 rows=1000 width=50)'
                for i in range(35)
            ]
        )
        verbose_output = f'{verbose_nodes}\n\n{human_readable}'

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM large_query')

        # Verify truncation message for large plans
        assert 'human_readable_plan' in result
        assert 'too large to display inline' in result['human_readable_plan']
        assert '35-line' in result['human_readable_plan']

    @pytest.mark.asyncio
    async def test_explain_verbose_all_property_types(self, mocker):
        """Test parsing all property types."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Comprehensive verbose output with all property types
        verbose_output = """{HASHJOIN
:node_id 1
:parent_id 0
:startup_cost 123.45
:total_cost 678.90
:plan_rows 5000
:plan_width 128
:dist_info.dist_strategy DS_BCAST_INNER
:jointype 1
:dataMovement Broadcast to all slices
}
{AGGREGATE
:node_id 2
:parent_id 1
:startup_cost 50.00
:total_cost 100.00
:plan_rows 1
:plan_width 8
:aggstrategy 2
}
{SEQSCAN
:node_id 3
:parent_id 2
:startup_cost 0.00
:total_cost 50.00
:plan_rows 1000
:plan_width 64
:scanrelid 1
:table "public.orders"
}

XN Hash Join  (cost=123.45..678.90 rows=5000 width=128)
  ->  XN Aggregate  (cost=50.00..100.00 rows=1 width=8)
    ->  XN Seq Scan on public.orders  (cost=0.00..50.00 rows=1000 width=64)"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM orders')

        # Verify all properties were parsed
        nodes = result['plan_nodes']
        assert len(nodes) == 3

        # Check Hash Join node
        join_node = next(n for n in nodes if n['node_id'] == 1)
        assert join_node['cost_startup'] == 123.45
        assert join_node['cost_total'] == 678.90
        assert join_node['rows'] == 5000
        assert join_node['width'] == 128
        assert join_node['distribution_type'] == 'DS_BCAST_INNER'
        assert join_node['join_type'] == 'Left'
        assert join_node['data_movement'] == 'Broadcast to all slices'

        # Check Aggregate node
        agg_node = next(n for n in nodes if n['node_id'] == 2)
        assert agg_node['agg_strategy'] == 'Hashed'

        # Check Seq Scan node
        scan_node = next(n for n in nodes if n['node_id'] == 3)
        assert scan_node['scan_relid'] == 1
        assert scan_node['relation_name'] == 'public.orders'

    @pytest.mark.asyncio
    async def test_explain_verbose_dist_strategy_filtering(self, mocker):
        """Test distribution strategy filtering for DS_DIST_ERR."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Test with DS_DIST_ERR and <> which should be filtered out
        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:dist_info.dist_strategy DS_DIST_ERR
}
{SEQSCAN
:node_id 2
:parent_id 0
:dist_info.dist_strategy <>
}
{SEQSCAN
:node_id 3
:parent_id 0
:dist_info.dist_strategy DS_DIST_NONE
}

XN Seq Scan on table1
XN Seq Scan on table2
XN Seq Scan on table3"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM test')

        # Verify DS_DIST_ERR and <> are filtered out
        nodes = result['plan_nodes']
        node1 = next(n for n in nodes if n['node_id'] == 1)
        node2 = next(n for n in nodes if n['node_id'] == 2)
        node3 = next(n for n in nodes if n['node_id'] == 3)

        assert 'distribution_type' not in node1
        assert 'distribution_type' not in node2
        assert node3['distribution_type'] == 'DS_DIST_NONE'

    @pytest.mark.asyncio
    async def test_explain_verbose_parent_id_zero(self, mocker):
        """Test parent_id handling when it's 0."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Test with parent_id 0 (root node)
        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
}

XN Seq Scan on table1"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM test')

        nodes = result['plan_nodes']
        assert len(nodes) == 1
        assert nodes[0]['parent_node_id'] is None

    @pytest.mark.asyncio
    async def test_explain_verbose_properties_before_node(self, mocker):
        """Test handling properties before any node is defined."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Test with properties appearing before any node definition
        verbose_output = """:startup_cost 100.00
:total_cost 200.00
{SEQSCAN
:node_id 1
:parent_id 0
}

XN Seq Scan on table1"""

        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM test')

        # Verify properties before node are ignored
        nodes = result['plan_nodes']
        assert len(nodes) == 1
        # The orphaned properties should not be in the node
        assert 'cost_startup' not in nodes[0] or nodes[0].get('cost_startup') != 100.00
