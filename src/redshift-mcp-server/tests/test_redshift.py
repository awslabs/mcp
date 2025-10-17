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

        # Verify boto3.Session was called with correct parameters
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

        # First call should create client
        client1 = manager.redshift_client()
        # Second call should return cached client
        client2 = manager.redshift_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
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

        # Verify session was created with profile and region
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

        # Verify boto3.Session was called with correct parameters
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

        # Verify session was created with profile and region
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

        # First call should create client
        client1 = manager.redshift_serverless_client()
        # Second call should return cached client
        client2 = manager.redshift_serverless_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
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

        # Verify boto3.Session was called with correct parameters
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

        # Verify session was created with profile and region
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

        # First call should create client
        client1 = manager.redshift_data_client()
        # Second call should return cached client
        client2 = manager.redshift_data_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
        mock_boto3_session.assert_called_once()


class TestExecuteProtectedStatement:
    """Tests for _execute_protected_statement function."""

    @pytest.mark.asyncio
    async def test_execute_protected_statement_read_only(self, mocker):
        """Test executing protected statement in read-only mode."""
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        # Mock _execute_statement
        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )
        mock_execute_statement.side_effect = ['begin-stmt-id', 'user-stmt-id', 'end-stmt-id']

        # Mock data client
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = {'Records': [], 'ColumnMetadata': []}
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        result = await _execute_protected_statement(
            'test-cluster', 'test-db', 'SELECT 1', allow_read_write=False
        )

        # Verify session was created
        mock_session_manager.session.assert_called_once()

        # Verify three statements were executed: BEGIN READ ONLY, user SQL, END
        assert mock_execute_statement.call_count == 3
        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ ONLY;'
        assert calls[1][1]['sql'] == 'SELECT 1'
        assert calls[2][1]['sql'] == 'END;'

        assert result[1] == 'user-stmt-id'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_read_write(self, mocker):
        """Test executing protected statement in read-write mode."""
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        # Mock _execute_statement
        mock_execute_statement = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement'
        )
        mock_execute_statement.side_effect = ['begin-stmt-id', 'user-stmt-id', 'end-stmt-id']

        # Mock data client
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = {'Records': [], 'ColumnMetadata': []}
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        await _execute_protected_statement(
            'test-cluster', 'test-db', 'DROP TABLE test', allow_read_write=True
        )

        # Verify BEGIN READ WRITE was used
        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ WRITE;'
        assert calls[1][1]['sql'] == 'DROP TABLE test'
        assert calls[2][1]['sql'] == 'END;'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_transaction_breaker_error(self, mocker):
        """Test transaction breaker protection in read-only mode."""
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        # Test suspicious SQL patterns that should be rejected
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
        # Mock discover_clusters to return empty list
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
        # Mock discover_clusters to return different clusters
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
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        # Mock _execute_statement to fail for user SQL, succeed for BEGIN and END
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

        # Verify END was still called
        assert mock_execute_statement.call_count == 3
        calls = mock_execute_statement.call_args_list
        assert calls[0][1]['sql'] == 'BEGIN READ ONLY;'
        assert calls[1][1]['sql'] == 'SELECT invalid_syntax'
        assert calls[2][1]['sql'] == 'END;'

    @pytest.mark.asyncio
    async def test_execute_protected_statement_user_sql_succeeds_end_fails(self, mocker):
        """Test user SQL succeeds but END fails - should raise END error."""
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        # Mock _execute_statement to succeed for user SQL, fail for END
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
        # Mock discover_clusters
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock session manager
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='session-123')

        # Mock _execute_statement to fail for both user SQL and END
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
        # Use small timeout and poll interval to trigger timeout quickly
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
        # Mock discover_clusters to return cluster with unknown type
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

        # This should trigger the unknown cluster type error (lines 324, 331)
        with pytest.raises(Exception, match='Unknown cluster type: unknown-type'):
            await _execute_statement(cluster_info, 'test-cluster', 'dev', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_execute_statement_with_parameters(self, mocker):
        """Test _execute_statement with parameters to cover line 335."""
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

        # This should cover line 335 (parameters path)
        await _execute_statement(
            cluster_info, 'test-cluster', 'dev', 'SELECT 1', parameters=parameters
        )

        # Verify parameters were added to request
        call_args = mock_client.execute_statement.call_args[1]
        assert 'Parameters' in call_args
        assert call_args['Parameters'] == parameters

    @pytest.mark.asyncio
    async def test_execute_statement_with_session_id(self, mocker):
        """Test _execute_statement with session_id to cover line 339."""
        mock_client = mocker.Mock()
        mock_client.execute_statement.return_value = {'Id': 'stmt-123'}
        mock_client.describe_statement.return_value = {'Status': 'FINISHED'}

        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_client

        cluster_info = {'type': 'provisioned', 'identifier': 'test-cluster'}

        # This should cover line 339 (session_id path)
        await _execute_statement(
            cluster_info, 'test-cluster', 'dev', 'SELECT 1', session_id='session-123'
        )

        # Verify session_id was added to request
        call_args = mock_client.execute_statement.call_args[1]
        assert 'SessionId' in call_args
        assert call_args['SessionId'] == 'session-123'
        # Verify database and cluster are NOT added when using session
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

        # First call creates session
        session_id1 = await session_manager.session('test-cluster', 'test-db', cluster_info)

        # Second call should reuse session
        session_id2 = await session_manager.session('test-cluster', 'test-db', cluster_info)

        assert session_id1 == session_id2 == 'test-session-123'
        # execute_statement should only be called once (for session creation)
        mock_data_client.execute_statement.assert_called_once()

    def test_session_expiration_check(self):
        """Test session expiration logic."""
        session_keepalive = 600
        session_manager = RedshiftSessionManager(
            session_keepalive=session_keepalive, app_name='test-app/1.0'
        )

        # Fresh session should not be expired
        fresh_session = {'created_at': time.time()}
        assert not session_manager._is_session_expired(fresh_session)

        # Old session should be expired
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
        # Mock redshift client
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

        # Mock serverless client (empty response)
        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

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
        cluster = result[0]
        assert cluster['identifier'] == 'test-cluster'
        assert cluster['type'] == 'provisioned'
        assert cluster['status'] == 'available'
        assert cluster['database_name'] == 'dev'
        assert cluster['endpoint'] == 'test.redshift.amazonaws.com'
        assert cluster['port'] == 5439
        assert cluster['node_type'] == 'dc2.large'
        assert cluster['number_of_nodes'] == 2
        assert cluster['tags'] == {'env': 'test'}

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
        # Mock _execute_protected_statement
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
        # Mock _execute_protected_statement
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
        assert result[0]['schema_owner'] == 100

        # Verify parameters were passed correctly
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        assert call_args[1]['parameters'] == [{'name': 'database_name', 'value': 'dev'}]

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
        """Test discover_tables function."""
        # Mock _execute_protected_statement
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
                        {'stringValue': 'user=admin'},
                        {'stringValue': 'TABLE'},
                        {'stringValue': 'User data table'},
                    ]
                ]
            },
            'query-789',
        )

        result = await discover_tables('test-cluster', 'dev', 'public')

        assert len(result) == 1
        assert result[0]['database_name'] == 'dev'
        assert result[0]['schema_name'] == 'public'
        assert result[0]['table_name'] == 'users'
        assert result[0]['table_type'] == 'TABLE'

        # Verify parameters were passed correctly
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        expected_params = [
            {'name': 'database_name', 'value': 'dev'},
            {'name': 'schema_name', 'value': 'public'},
        ]
        assert call_args[1]['parameters'] == expected_params

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
        # Mock _execute_protected_statement
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
                    ]
                ]
            },
            'query-101',
        )

        result = await discover_columns('test-cluster', 'dev', 'public', 'users')

        assert len(result) == 1
        assert result[0]['database_name'] == 'dev'
        assert result[0]['schema_name'] == 'public'
        assert result[0]['table_name'] == 'users'
        assert result[0]['column_name'] == 'id'
        assert result[0]['ordinal_position'] == 1
        assert result[0]['data_type'] == 'integer'

        # Verify parameters were passed correctly
        mock_execute_protected.assert_called_once()
        call_args = mock_execute_protected.call_args
        expected_params = [
            {'name': 'database_name', 'value': 'dev'},
            {'name': 'schema_name', 'value': 'public'},
            {'name': 'table_name', 'value': 'users'},
        ]
        assert call_args[1]['parameters'] == expected_params

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
        # Mock _execute_protected_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'ColumnMetadata': [
                    {'name': 'id'},
                    {'name': 'name'},
                    {'name': 'score'},
                    {'name': 'active'},
                    {'name': 'deleted'},
                    {'name': 'unknown'},
                ],
                'Records': [
                    [
                        {'longValue': 1},
                        {'stringValue': 'Test User'},
                        {'doubleValue': 95.5},
                        {'booleanValue': True},
                        {'isNull': True},
                        {'unknownType': 'fallback'},
                    ]
                ],
            },
            'query-123',
        )

        # Mock time for execution time calculation
        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.123]  # start_time, end_time

        result = await execute_query(
            'test-cluster',
            'dev',
            'SELECT id, name, score, active, deleted, unknown FROM users LIMIT 1',
        )

        assert result['columns'] == ['id', 'name', 'score', 'active', 'deleted', 'unknown']
        assert result['rows'] == [
            [1, 'Test User', 95.5, True, None, "{'unknownType': 'fallback'}"]
        ]
        assert result['row_count'] == 1
        assert result['execution_time_ms'] == 123
        assert result['query_id'] == 'query-123'

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, mocker):
        """Test error handling in execute_query."""
        # Mock _execute_protected_statement to raise exception
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Query execution failed')

        with pytest.raises(Exception, match='Query execution failed'):
            await execute_query('test-cluster', 'dev', 'SELECT * FROM nonexistent')
