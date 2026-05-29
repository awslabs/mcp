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
    _generate_performance_suggestions,
    _parse_explain_verbose,
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
        """Test discover_clusters function with provisioned clusters.

        Tests both complete cluster data and clusters with optional fields omitted
        to ensure proper default handling (e.g., DBName defaults to 'dev').
        Fixes: https://github.com/awslabs/mcp/issues/2331
        """
        # Define minimal cluster first (with defaults omitted)
        minimal_cluster = {
            'ClusterIdentifier': 'minimal-cluster',
            'ClusterStatus': 'available',
            # DBName intentionally omitted - tests .get('DBName', 'dev')
            'Endpoint': {'Address': 'minimal.redshift.amazonaws.com', 'Port': 5439},
            'VpcId': 'vpc-456',
            'NodeType': 'ra3.xlplus',
            'NumberOfNodes': 1,
            'ClusterCreateTime': '2024-06-01T00:00:00Z',
            'MasterUsername': 'admin',
            'PubliclyAccessible': False,
            'Encrypted': True,
            'Tags': [],
        }

        # Full cluster extends minimal (avoids code duplication)
        full_cluster = {
            **minimal_cluster,
            'ClusterIdentifier': 'test-cluster',
            'DBName': 'dev',
            'Endpoint': {'Address': 'test.redshift.amazonaws.com', 'Port': 5439},
            'VpcId': 'vpc-123',
            'NodeType': 'dc2.large',
            'NumberOfNodes': 2,
            'ClusterCreateTime': '2024-01-01T00:00:00Z',
            'Tags': [{'Key': 'env', 'Value': 'test'}],
        }

        # Mock redshift client with both clusters
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [full_cluster, minimal_cluster]}
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

        assert len(result) == 2

        # Verify full cluster (with all fields)
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

        # Verify minimal cluster (with defaults applied)
        minimal = result[1]
        assert minimal['identifier'] == 'minimal-cluster'
        assert minimal['type'] == 'provisioned'
        assert minimal['status'] == 'available'
        assert minimal['database_name'] == 'dev'  # Should default to 'dev', not KeyError
        assert minimal['endpoint'] == 'minimal.redshift.amazonaws.com'
        assert minimal['port'] == 5439
        assert minimal['node_type'] == 'ra3.xlplus'
        assert minimal['number_of_nodes'] == 1
        assert minimal['tags'] == {}

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
        # First call: TABLES_SQL, Second call: TABLES_EXTRA_SQL
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
                            {'stringValue': None},
                            {'stringValue': None},
                        ]
                    ]
                },
                'query-789',
            ),
            (
                {
                    'Records': [
                        [
                            {'stringValue': 'public'},
                            {'stringValue': 'users'},
                            {'stringValue': 'KEY'},
                            {'longValue': 1000},
                            {'longValue': 50},
                            {'longValue': 5000},
                            {'longValue': 100},
                            {'longValue': 20},
                            {'longValue': 5},
                        ]
                    ]
                },
                'query-extra',
            ),
        ]

        result = await discover_tables('test-cluster', 'dev', 'public')

        assert len(result) == 1
        assert result[0]['database_name'] == 'dev'
        assert result[0]['schema_name'] == 'public'
        assert result[0]['table_name'] == 'users'
        assert result[0]['table_type'] == 'TABLE'
        # Verify extra stats were merged
        assert result[0]['redshift_diststyle'] == 'KEY'
        assert result[0]['redshift_estimated_row_count'] == 1000
        assert result[0]['stats_sequential_scans'] == 50
        assert result[0]['stats_rows_inserted'] == 100

        # Verify parameters were passed correctly for first call
        first_call_args = mock_execute_protected.call_args_list[0]
        expected_params = [
            {'name': 'database_name', 'value': 'dev'},
            {'name': 'schema_name', 'value': 'public'},
        ]
        assert first_call_args[1]['parameters'] == expected_params

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
    async def test_discover_tables_extra_stats_failure(self, mocker):
        """Test that TABLES_EXTRA_SQL failure raises an error."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        # First call (TABLES_SQL) succeeds, second call (TABLES_EXTRA_SQL) fails
        mock_execute_protected.side_effect = [
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
                'query-tables',
            ),
            Exception('pg_class_info not accessible'),
        ]

        with pytest.raises(Exception, match='pg_class_info not accessible'):
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
        assert result[0]['database_name'] == 'dev'
        assert result[0]['schema_name'] == 'public'
        assert result[0]['table_name'] == 'users'
        assert result[0]['column_name'] == 'id'
        assert result[0]['ordinal_position'] == 1
        assert result[0]['data_type'] == 'integer'
        assert result[0]['redshift_encoding'] == 'lzo'
        assert result[0]['redshift_is_distkey'] is True
        assert result[0]['redshift_sortkey_position'] == 1
        assert result[0]['external_partition_key'] is None

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

        assert 'rule_based_suggestions' in result
        assert isinstance(result['rule_based_suggestions'], list)

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
        """Test that table designs are fetched via OID resolution."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call: EXPLAIN VERBOSE with :resorigtbl
        explain_response = (
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
                    [{'stringValue': '   :resorigtbl 12345'}],
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

        # Second call: TABLES_EXTRA_BY_OID_SQL response
        design_response = (
            {
                'Records': [
                    [
                        {'longValue': 12345},
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'KEY'},
                        {'longValue': 50000},
                        {'longValue': 120},
                        {'longValue': 6000000},
                        {'longValue': 5000},
                        {'longValue': 200},
                        {'longValue': 50},
                    ]
                ]
            },
            'design-query',
        )

        # Third call: COLUMN_STATS_SQL batch response (schema_name, table_name, column_name, ...)
        col_stats_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'doubleValue': -1.0},
                        {'doubleValue': 0.0},
                        {'longValue': 4},
                        {'doubleValue': 0.99},
                        {'stringValue': '{1,2,3}'},
                        {'stringValue': '{0.5,0.3,0.2}'},
                        {'stringValue': '{1,1000,2000,3000,5000}'},
                    ],
                ]
            },
            'stats-query',
        )

        mock_execute_protected.side_effect = [
            explain_response,
            design_response,
            col_stats_response,
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = [
            {
                'column_name': 'id',
                'redshift_encoding': 'lzo',
                'redshift_is_distkey': True,
                'redshift_sortkey_position': 1,
            }
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM public.users')

        assert len(result['table_designs']) == 1
        td = result['table_designs'][0]
        assert td['database_name'] == 'dev'
        assert td['schema_name'] == 'public'
        assert td['table_name'] == 'users'
        assert td['redshift_diststyle'] == 'KEY'
        assert td['redshift_estimated_row_count'] == 50000
        assert td['stats_sequential_scans'] == 120

        # Verify relation_name set from OID resolution
        assert result['plan_nodes'][0]['relation_name'] == 'public.users'

        # Verify column stats enrichment
        id_col = td['columns'][0]
        assert id_col['column_name'] == 'id'
        assert id_col['redshift_is_distkey'] is True
        assert id_col['stats_n_distinct'] == -1.0
        assert id_col['stats_correlation'] == 0.99

        assert isinstance(result['rule_based_suggestions'], list)

    @pytest.mark.asyncio
    async def test_describe_execution_plan_schema_qualified_table(self, mocker):
        """Test table design fetching via OID resolution with schema-qualified table."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        explain_response = (
            {
                'Records': [
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   :resorigtbl 54321'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Seq Scan on sales'}],
                ]
            },
            'explain-123',
        )

        design_response = (
            {
                'Records': [
                    [
                        {'longValue': 54321},
                        {'stringValue': 'tickit'},
                        {'stringValue': 'sales'},
                        {'stringValue': 'KEY'},
                        {'longValue': 172456},
                        {'longValue': 500},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'stringValue': None},
                        {'stringValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                    ]
                ]
            },
            'design-query',
        )

        col_stats_response = ({'Records': []}, 'stats-query')

        mock_execute_protected.side_effect = [
            explain_response,
            design_response,
            col_stats_response,
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = [
            {'column_name': 'salesid', 'redshift_encoding': 'lzo', 'redshift_sortkey_position': 1},
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM tickit.sales')

        assert len(result['table_designs']) == 1
        td = result['table_designs'][0]
        assert td['schema_name'] == 'tickit'
        assert td['table_name'] == 'sales'
        assert td['redshift_diststyle'] == 'KEY'
        assert td['redshift_estimated_row_count'] == 172456
        assert result['plan_nodes'][0]['relation_name'] == 'tickit.sales'

    @pytest.mark.asyncio
    async def test_describe_execution_plan_sql_hint_resolves_schema(self, mocker):
        """Test that unqualified table names in plan are resolved using SQL schema hints.

        Redshift's human-readable plan often omits the schema prefix (e.g., "Seq Scan on sales"
        instead of "Seq Scan on tickit.sales"). The SQL hint resolution extracts schema-qualified
        references from the original SQL to resolve these.
        """
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Human-readable plan has unqualified table names (real Redshift behavior)
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': '   { HASHJOIN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 2'}],
                    [{'stringValue': '   :parent_id 1'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 3'}],
                    [{'stringValue': '   :parent_id 1'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Hash Join DS_DIST_NONE'}],
                    [{'stringValue': '  ->  XN Seq Scan on sales s'}],
                    [{'stringValue': '  ->  XN Hash'}],
                    [{'stringValue': '        ->  XN Seq Scan on event e'}],
                ]
            },
            'explain-123',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'tickit',
                'table_name': 'sales',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 172456,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            },
            {
                'database_name': 'dev',
                'schema_name': 'tickit',
                'table_name': 'event',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 8798,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            },
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        # SQL has schema-qualified names, but plan output won't
        result = await describe_execution_plan(
            'test-cluster',
            'dev',
            'SELECT s.salesid FROM tickit.sales s JOIN tickit.event e ON s.eventid = e.eventid',
        )

        # Both tables should be resolved to tickit schema via SQL hints (fallback path)
        assert len(result['table_designs']) == 2
        table_names = {td['table_name'] for td in result['table_designs']}
        assert table_names == {'sales', 'event'}

        # Verify discover_tables was called with tickit schema (not public)
        for call in mock_discover_tables.call_args_list:
            assert call[1]['table_schema_name'] == 'tickit'

    @pytest.mark.asyncio
    async def test_describe_execution_plan_table_not_found(self, mocker):
        """Test table_designs when table is not found in discover_tables."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Seq Scan on nonexistent'}],
                ]
            },
            'explain-123',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        # Return tables that don't include the referenced one
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'other_table',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 100,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            }
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM nonexistent')

        # Table not found — table_designs should be empty
        assert len(result['table_designs']) == 0

    @pytest.mark.asyncio
    async def test_describe_execution_plan_multiple_tables(self, mocker):
        """Test table_designs with multiple tables referenced in the plan."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': '   { HASHJOIN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 2'}],
                    [{'stringValue': '   :parent_id 1'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 3'}],
                    [{'stringValue': '   :parent_id 1'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Hash Join'}],
                    [{'stringValue': '  ->  XN Seq Scan on orders'}],
                    [{'stringValue': '  ->  XN Seq Scan on customers'}],
                ]
            },
            'explain-123',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            },
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'customers',
                'redshift_diststyle': 'ALL',
                'redshift_estimated_row_count': 5000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            },
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan(
            'test-cluster',
            'dev',
            'SELECT * FROM orders JOIN customers ON orders.cid = customers.id',
        )

        # Both tables should be in table_designs
        assert len(result['table_designs']) == 2
        table_names = {td['table_name'] for td in result['table_designs']}
        assert table_names == {'orders', 'customers'}

    @pytest.mark.asyncio
    async def test_describe_execution_plan_external_table(self, mocker):
        """Test table_designs fallback for external tables (no OID in pg_class_info)."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Real external table EXPLAIN VERBOSE output: OID 1999999994 is a synthetic
        # sentinel that won't resolve in pg_class_info. The human-readable plan uses
        # "S3 Seq Scan" and "Seq Scan PartitionInfo of" patterns instead of "Seq Scan on".
        explain_response = (
            {
                'Records': [
                    [{'stringValue': '   { LIMIT'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   :startup_cost 0.00'}],
                    [{'stringValue': '   :total_cost 0.20'}],
                    [{'stringValue': '   :plan_rows 10'}],
                    [{'stringValue': '     :resorigtbl 1999999994'}],
                    [{'stringValue': '   { PARTITIONLOOP'}],
                    [{'stringValue': '   :node_id 2'}],
                    [{'stringValue': '   :parent_id 1'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 3'}],
                    [{'stringValue': '   :parent_id 2'}],
                    [{'stringValue': '     :resorigtbl 0'}],
                    [{'stringValue': '   { SUBQUERYSCAN'}],
                    [{'stringValue': '   :node_id 4'}],
                    [{'stringValue': '   :parent_id 2'}],
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 5'}],
                    [{'stringValue': '   :parent_id 4'}],
                    [{'stringValue': '     :resorigtbl 0'}],
                    [{'stringValue': ''}],
                    [{'stringValue': ' XN Limit  (cost=0.00..0.20 rows=10 width=17794)'}],
                    [
                        {
                            'stringValue': '   ->  XN Partition Loop  (cost=0.00..200200000010.00 rows=10000000000000 width=17794)'
                        }
                    ],
                    [
                        {
                            'stringValue': '         ->  XN Seq Scan PartitionInfo of extdata.ext_events  (cost=0.00..10.00 rows=1000 width=410)'
                        }
                    ],
                    [
                        {
                            'stringValue': '         ->  XN S3 Query Scan ext_events  (cost=0.00..200000000.00 rows=10000000000 width=17384)'
                        }
                    ],
                    [
                        {
                            'stringValue': '               ->  S3 Seq Scan extdata.ext_events location:"s3://my-bucket/events/" format:PARQUET  (cost=0.00..100000000.00 rows=10000000000 width=17384)'
                        }
                    ],
                ]
            },
            'explain-123',
        )

        # OID 1999999994 query returns empty (synthetic OID not in pg_class_info)
        oid_response = ({'Records': []}, 'oid-query-123')

        mock_execute_protected.side_effect = [explain_response, oid_response]

        # Fallback path uses discover_tables
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'extdata',
                'table_name': 'ext_events',
                'redshift_diststyle': None,
                'redshift_estimated_row_count': None,
                'external_location': 's3://my-bucket/events/',
                'external_parameters': '{"partition_columns": ["year", "month"]}',
                'stats_sequential_scans': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = [
            {'column_name': 'event_id', 'redshift_encoding': None, 'redshift_sortkey_position': 0},
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM extdata.ext_events LIMIT 10'
        )

        # Fallback path should find the table via human-readable plan with correct schema
        assert len(result['table_designs']) == 1
        td = result['table_designs'][0]
        assert td['table_name'] == 'ext_events'
        assert td['schema_name'] == 'extdata'
        assert td.get('external_location') == 's3://my-bucket/events/'

    @pytest.mark.asyncio
    async def test_describe_execution_plan_with_all_node_types(self, mocker):
        """Test execution plan parsing with all node types."""
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
                    [{'stringValue': '   { JOIN'}],
                    [{'stringValue': '   :node_id 29'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { MATERIAL'}],
                    [{'stringValue': '   :node_id 30'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { TABLEFUNCTIONSCAN'}],
                    [{'stringValue': '   :node_id 31'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   { TOPKPLANINFO'}],
                    [{'stringValue': '   :node_id 32'}],
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

        assert len(result['plan_nodes']) == 32

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
        assert result['plan_nodes'][28]['operation'] == 'Join'
        assert result['plan_nodes'][29]['operation'] == 'Materialize'
        assert result['plan_nodes'][30]['operation'] == 'Table Function Scan'
        assert result['plan_nodes'][31]['operation'] == 'TopK'

        for i, node in enumerate(result['plan_nodes']):
            assert node['node_id'] == i + 1

    @pytest.mark.asyncio
    async def test_describe_execution_plan_with_column_stats(self, mocker):
        """Test that column stats from pg_stats are fetched and merged into columns."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # First call: EXPLAIN VERBOSE with a table reference
        explain_response = (
            {
                'Records': [
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Seq Scan on users  (cost=0.00..10.00 rows=100 width=8)'}],
                ]
            },
            'explain-123',
        )

        # Third call: COLUMN_STATS_SQL batch response (schema_name, table_name, column_name, ...)
        column_stats_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'doubleValue': -1.0},
                        {'doubleValue': 0.0},
                        {'longValue': 4},
                        {'doubleValue': 0.98},
                        {'stringValue': '{1,2,3,4,5}'},
                        {'stringValue': '{0.3,0.25,0.2,0.15,0.1}'},
                        {'stringValue': '{1,100,500,1000,5000}'},
                    ],
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'name'},
                        {'doubleValue': -0.5},
                        {'doubleValue': 0.1},
                        {'longValue': 12},
                        {'doubleValue': 0.05},
                        {'stringValue': '{Alice,Bob,Charlie}'},
                        {'stringValue': '{0.4,0.35,0.25}'},
                        {'stringValue': '{Adam,Eve,Frank,Grace,Henry}'},
                    ],
                ]
            },
            'stats-123',
        )

        # side_effect: EXPLAIN, then batch column stats
        mock_execute_protected.side_effect = [explain_response, column_stats_response]

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 10000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = [
            {
                'column_name': 'id',
                'redshift_encoding': 'lzo',
                'redshift_is_distkey': True,
                'redshift_sortkey_position': 1,
            },
            {
                'column_name': 'name',
                'redshift_encoding': 'lzo',
                'redshift_is_distkey': False,
                'redshift_sortkey_position': 0,
            },
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        assert len(result['table_designs']) == 1
        columns = result['table_designs'][0]['columns']
        assert len(columns) == 2

        # Verify pg_stats were merged into column dicts
        id_col = next(c for c in columns if c['column_name'] == 'id')
        assert id_col['stats_n_distinct'] == -1.0
        assert id_col['stats_null_frac'] == 0.0
        assert id_col['stats_avg_width'] == 4
        assert id_col['stats_correlation'] == 0.98
        assert id_col['stats_most_common_vals'] == '{1,2,3,4,5}'
        assert id_col['stats_most_common_freqs'] == '{0.3,0.25,0.2,0.15,0.1}'
        assert id_col['stats_histogram_bounds'] == '{1,100,500,1000,5000}'

        name_col = next(c for c in columns if c['column_name'] == 'name')
        assert name_col['stats_n_distinct'] == -0.5
        assert name_col['stats_null_frac'] == 0.1
        assert name_col['stats_avg_width'] == 12
        assert name_col['stats_correlation'] == 0.05
        assert name_col['stats_most_common_vals'] == '{Alice,Bob,Charlie}'
        assert name_col['stats_most_common_freqs'] == '{0.4,0.35,0.25}'
        assert name_col['stats_histogram_bounds'] == '{Adam,Eve,Frank,Grace,Henry}'

    @pytest.mark.asyncio
    async def test_describe_execution_plan_column_stats_failure(self, mocker):
        """Test that column stats failure is handled gracefully."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        explain_response = (
            {
                'Records': [
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Seq Scan on users'}],
                ]
            },
            'explain-123',
        )

        # Column stats call fails
        mock_execute_protected.side_effect = [
            explain_response,
            Exception('pg_stats access denied'),
        ]

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = [
            {
                'column_name': 'id',
                'redshift_encoding': 'lzo',
                'redshift_sortkey_position': 1,
            },
        ]

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        # Should still succeed — columns just won't have stats
        assert len(result['table_designs']) == 1
        columns = result['table_designs'][0]['columns']
        assert len(columns) == 1
        assert 'stats_n_distinct' not in columns[0]

    @pytest.mark.asyncio
    async def test_describe_execution_plan_empty_and_partial_records(self, mocker):
        """Test handling of empty records in EXPLAIN output and partial OID records."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN output with an empty record and a normal record
        explain_response = (
            {
                'Records': [
                    [],  # empty record — should be skipped
                    [{'stringValue': '   { SEQSCAN'}],
                    [{'stringValue': '   :node_id 1'}],
                    [{'stringValue': '   :parent_id 0'}],
                    [{'stringValue': '   :resorigtbl 12345'}],
                    [{'stringValue': ''}],
                    [{'stringValue': 'XN Seq Scan on users'}],
                ]
            },
            'explain-123',
        )

        # OID resolution returns a record with missing schema (partial data)
        design_response = (
            {
                'Records': [
                    [
                        {'longValue': 12345},
                        {'stringValue': None},  # missing schema
                        {'stringValue': 'users'},
                        {'stringValue': 'KEY'},
                        {'longValue': 1000},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ],
                ]
            },
            'design-query',
        )

        # Batch column stats — empty since no valid table_refs
        stats_response = ({'Records': []}, 'stats-query')

        mock_execute_protected.side_effect = [explain_response, design_response, stats_response]

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = []

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        # Plan should parse successfully despite empty record
        assert len(result['plan_nodes']) == 1
        # OID record had missing schema, but fallback found table from human-readable plan
        assert len(result['table_designs']) == 1
        assert result['table_designs'][0]['table_name'] == 'users'
        # No design metadata since OID resolution failed
        assert result['table_designs'][0].get('redshift_diststyle') is None

    # --- EXPLAIN VERBOSE parsing tests ---

    @pytest.mark.asyncio
    async def test_explain_verbose_with_node_properties(self, mocker):
        """Test parsing EXPLAIN VERBOSE with various node properties."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE format with node properties
        verbose_output = """{AGG
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
{AGG
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
        """Test parsing resorigtbl for table OID resolution."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # EXPLAIN VERBOSE with :resorigtbl (real Redshift format)
        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:scanrelid 1
:resorigtbl 12345
}

XN Seq Scan on myschema.mytable  (cost=0.00..100.00 rows=1000 width=50)"""

        # First call: EXPLAIN, second call: OID resolution query
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
                            {'longValue': 12345},
                            {'stringValue': 'myschema'},
                            {'stringValue': 'mytable'},
                        ]
                    ]
                },
                'oid-query',
            ),
        ]

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'myschema',
                'table_name': 'mytable',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM myschema.mytable'
        )

        nodes = result['plan_nodes']
        assert len(nodes) == 1
        assert nodes[0]['relation_name'] == 'myschema.mytable'
        assert nodes[0].get('source_table_oid') == 12345
        assert len(result['table_designs']) == 1

    @pytest.mark.asyncio
    async def test_explain_verbose_unqualified_table(self, mocker):
        """Test OID resolution for table reference."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:resorigtbl 99999
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
                            {'longValue': 99999},
                            {'stringValue': 'public'},
                            {'stringValue': 'users'},
                        ]
                    ]
                },
                'oid-query',
            ),
        ]

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = [
            {
                'database_name': 'dev',
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000,
                'external_location': None,
                'external_parameters': None,
                'stats_sequential_scans': None,
            }
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        nodes = result['plan_nodes']
        assert len(nodes) == 1
        assert nodes[0]['relation_name'] == 'public.users'

    @pytest.mark.asyncio
    async def test_explain_verbose_table_fetch_error(self, mocker):
        """Test error handling when TABLES_EXTRA_BY_OID_SQL fails."""
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        verbose_output = """{SEQSCAN
:node_id 1
:parent_id 0
:resorigtbl 55555
}

XN Seq Scan on users  (cost=0.00..100.00 rows=1000 width=50)"""

        mock_execute_protected.side_effect = [
            # Call 1: EXPLAIN VERBOSE
            (
                {
                    'ColumnMetadata': [{'name': 'QUERY PLAN'}],
                    'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
                },
                'explain-123',
            ),
            # Call 2: TABLES_EXTRA_BY_OID_SQL fails
            Exception('Permission denied'),
        ]

        # Fallback calls discover_tables which also fails since mock is exhausted
        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.side_effect = Exception('Fallback also failed')

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM users')

        # Should handle error gracefully
        assert 'plan_nodes' in result
        assert 'table_designs' in result
        # Table designs will be empty due to errors in both primary and fallback paths
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

        # Verify summary for large plans (first 10 + last 10 lines with omission note)
        assert 'human_readable_plan' in result
        plan = result['human_readable_plan']
        # Should contain first lines (table0)
        assert 'table0' in plan
        # Should contain last lines (table34)
        assert 'table34' in plan
        # Should contain omission note
        assert 'lines omitted' in plan
        assert f'first 10 and last 10 of {35} lines' in plan
        assert 'Run EXPLAIN directly' in plan

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
{AGG
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
:resorigtbl 77777
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
        assert scan_node['source_table_oid'] == 77777

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

    @pytest.mark.asyncio
    async def test_explain_verbose_nested_structures_skipped(self, mocker):
        """Test that properties inside nested structures don't leak to plan nodes.

        Properties like :resorigtbl inside TARGETENTRY/RESDOM blocks should not be
        assigned to non-scan nodes. Only scan nodes capture :resorigtbl for OID resolution.
        """
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Real Redshift EXPLAIN VERBOSE structure with nested TARGETENTRY/RESDOM blocks
        verbose_output = """{LIMIT
:node_id 1
:parent_id 0
:startup_cost 0.00
:total_cost 10.00
:plan_rows 10
:plan_width 8
:targetlist ({ TARGETENTRY
:resdom
{ RESDOM
:resno 1
:restype 23
:resname salesid
:resorigtbl 3082398
:resorigcol 1
:resjunk false
}
:expr
{ VAR
:varno 1
:varattno 1
}
})
:lefttree
{ SEQSCAN
:node_id 2
:parent_id 1
:startup_cost 0.00
:total_cost 100.00
:plan_rows 1000
:plan_width 8
:scanrelid 1
:targetlist ({ TARGETENTRY
:resdom
{ RESDOM
:resno 1
:resorigtbl 3082398
:resorigcol 1
}
})
}
}

XN Limit  (cost=0.00..10.00 rows=10 width=8)
  ->  XN Seq Scan on sales  (cost=0.00..100.00 rows=1000 width=8)"""

        mock_execute_protected.return_value = (
            {
                'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
            },
            'explain-123',
        )

        mock_discover_tables = mocker.patch('awslabs.redshift_mcp_server.redshift.discover_tables')
        mock_discover_tables.return_value = []

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM sales')

        nodes = result['plan_nodes']
        assert len(nodes) == 2

        # LIMIT node should NOT have source_table_oid (resorigtbl was inside RESDOM)
        limit_node = next(n for n in nodes if n['node_id'] == 1)
        assert 'source_table_oid' not in limit_node
        assert 'relation_name' not in limit_node or limit_node.get('relation_name') is None

        # SEQSCAN node SHOULD have source_table_oid (captured from nested RESDOM)
        scan_node = next(n for n in nodes if n['node_id'] == 2)
        assert scan_node.get('source_table_oid') == 3082398

    @pytest.mark.asyncio
    async def test_explain_verbose_cte_inlined(self, mocker):
        """Test that CTEs inlined by Redshift optimizer resolve to real table OIDs.

        Redshift inlines simple CTEs, so the plan contains Seq Scan nodes with
        :resorigtbl pointing to the real tables, not CTE Scan nodes.
        """
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Real Redshift output for a CTE query — CTE is inlined, plan shows real tables
        verbose_output = """{LIMIT
:node_id 1
:parent_id 0
:resorigtbl 3082398
}
{HASHJOIN
:node_id 2
:parent_id 1
:resorigtbl 3082398
}
{SEQSCAN
:node_id 3
:parent_id 2
:resorigtbl 3082398
}
{SEQSCAN
:node_id 5
:parent_id 2
:resorigtbl 3082395
}

XN Limit  (cost=122.47..123.12 rows=10 width=21)
  ->  XN Hash Join DS_DIST_NONE  (cost=122.47..6739.79 rows=101250 width=21)
        ->  XN Seq Scan on sales s  (cost=0.00..1724.56 rows=172456 width=8)
        ->  XN Hash  (cost=109.98..109.98 rows=4998 width=21)
              ->  XN Seq Scan on event  (cost=0.00..109.98 rows=4998 width=21)"""

        # Call 1: EXPLAIN, Call 2: OID resolution, Call 3: batch column stats
        mock_execute_protected.side_effect = [
            (
                {
                    'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
                },
                'explain-123',
            ),
            (
                {
                    'Records': [
                        [
                            {'longValue': 3082398},
                            {'stringValue': 'tickit'},
                            {'stringValue': 'sales'},
                            {'stringValue': 'KEY'},
                            {'longValue': 172456},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                        ],
                        [
                            {'longValue': 3082395},
                            {'stringValue': 'tickit'},
                            {'stringValue': 'event'},
                            {'stringValue': 'KEY'},
                            {'longValue': 8798},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                        ],
                    ]
                },
                'oid-query',
            ),
            ({'Records': []}, 'stats-query'),
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan(
            'test-cluster',
            'dev',
            'WITH top AS (SELECT eventid FROM tickit.event WHERE catid = 9) '
            'SELECT s.salesid FROM tickit.sales s JOIN top ON s.eventid = top.eventid',
        )

        # CTE is inlined — both real tables should be resolved via OID
        assert len(result['table_designs']) == 2
        table_names = {td['table_name'] for td in result['table_designs']}
        assert table_names == {'sales', 'event'}

    @pytest.mark.asyncio
    async def test_explain_verbose_subquery_inlined(self, mocker):
        """Test that subqueries inlined by Redshift optimizer resolve to real table OIDs.

        Redshift inlines simple subqueries, so the plan contains Seq Scan nodes with
        :resorigtbl pointing to the real tables, not Subquery Scan nodes.
        """
        from awslabs.redshift_mcp_server.redshift import describe_execution_plan

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Same plan structure as CTE — Redshift produces identical plans
        verbose_output = """{LIMIT
:node_id 1
:parent_id 0
:resorigtbl 3082398
}
{HASHJOIN
:node_id 2
:parent_id 1
}
{SEQSCAN
:node_id 3
:parent_id 2
:resorigtbl 3082398
}
{SEQSCAN
:node_id 5
:parent_id 2
:resorigtbl 3082395
}

XN Limit  (cost=122.47..123.12 rows=10 width=21)
  ->  XN Hash Join DS_DIST_NONE  (cost=122.47..6739.79 rows=101250 width=21)
        ->  XN Seq Scan on sales s  (cost=0.00..1724.56 rows=172456 width=8)
        ->  XN Hash  (cost=109.98..109.98 rows=4998 width=21)
              ->  XN Seq Scan on event  (cost=0.00..109.98 rows=4998 width=21)"""

        mock_execute_protected.side_effect = [
            (
                {
                    'Records': [[{'stringValue': line}] for line in verbose_output.split('\n')],
                },
                'explain-123',
            ),
            (
                {
                    'Records': [
                        [
                            {'longValue': 3082398},
                            {'stringValue': 'tickit'},
                            {'stringValue': 'sales'},
                            {'stringValue': 'KEY'},
                            {'longValue': 172456},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                        ],
                        [
                            {'longValue': 3082395},
                            {'stringValue': 'tickit'},
                            {'stringValue': 'event'},
                            {'stringValue': 'KEY'},
                            {'longValue': 8798},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                            {'longValue': 0},
                        ],
                    ]
                },
                'oid-query',
            ),
            ({'Records': []}, 'stats-query'),
        ]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )
        mock_discover_columns.return_value = []

        mock_time = mocker.patch('time.time')
        mock_time.side_effect = [1000.0, 1000.1]

        result = await describe_execution_plan(
            'test-cluster',
            'dev',
            'SELECT s.salesid FROM tickit.sales s '
            'JOIN (SELECT eventid FROM tickit.event WHERE catid = 9) sub '
            'ON s.eventid = sub.eventid LIMIT 10',
        )

        # Subquery is inlined — both real tables should be resolved via OID
        assert len(result['table_designs']) == 2
        table_names = {td['table_name'] for td in result['table_designs']}
        assert table_names == {'sales', 'event'}

    # --- Plan enrichment tests ---

    def _build_explain_verbose_lines(self) -> list[str]:
        """Build a realistic EXPLAIN VERBOSE output with enrichment scenarios.

        Tree structure:
          SORT (1) → AGG (2) → HASHJOIN (3)
            ├─ NETWORK (4) → SEQSCAN users (5)
            └─ HASH (6) → SEQSCAN orders (7)
        """
        return [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 100.00',
            ':total_cost 200.00',
            ':plan_rows 50',
            ':plan_width 32',
            '}',
            '{ AGG',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 50.00',
            ':total_cost 150.00',
            ':plan_rows 50',
            ':plan_width 32',
            ':aggstrategy 2',
            '}',
            '{ HASHJOIN',
            ':node_id 3',
            ':parent_id 2',
            ':startup_cost 10.00',
            ':total_cost 80.00',
            ':plan_rows 200',
            ':plan_width 24',
            ':jointype 0',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
            '{ NETWORK',
            ':node_id 4',
            ':parent_id 3',
            ':startup_cost 0.00',
            ':total_cost 40.00',
            ':plan_rows 100',
            ':plan_width 16',
            ':dataMovement Broadcast',
            '}',
            '{ SEQSCAN',
            ':node_id 5',
            ':parent_id 4',
            ':startup_cost 0.00',
            ':total_cost 30.00',
            ':plan_rows 100',
            ':plan_width 16',
            ':scanrelid 1',
            '}',
            '{ HASH',
            ':node_id 6',
            ':parent_id 3',
            ':startup_cost 25.00',
            ':total_cost 25.00',
            ':plan_rows 100',
            ':plan_width 8',
            '}',
            '{ SEQSCAN',
            ':node_id 7',
            ':parent_id 6',
            ':startup_cost 0.00',
            ':total_cost 25.00',
            ':plan_rows 100',
            ':plan_width 8',
            ':scanrelid 2',
            '}',
            '',
            'XN Sort  (cost=100.00..200.00 rows=50 width=32)',
            '  Sort Key: o.total_spent DESC',
            '  ->  XN HashAggregate  (cost=50.00..150.00 rows=50 width=32)',
            '        ->  XN Hash Join DS_DIST_NONE  (cost=10.00..80.00 rows=200 width=24)',
            '              Hash Cond: (u.id = o.user_id)',
            '              ->  XN Network  (cost=0.00..40.00 rows=100 width=16)',
            '                    Send to leader',
            '                    ->  XN Seq Scan on users u  (cost=0.00..30.00 rows=100 width=16)',
            '              ->  XN Hash  (cost=25.00..25.00 rows=100 width=8)',
            '                    ->  XN Seq Scan on orders o  (cost=0.00..25.00 rows=100 width=8)',
            '                          Filter: (o.quantity > 0)',
        ]

    def test_scan_node_table_name_and_alias(self):
        """Scan node has relation_name and alias from human-readable plan."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        scan_node = next(n for n in result_nodes if n.get('node_id') == 5)
        assert scan_node.get('relation_name') == 'users'
        assert scan_node.get('alias') == 'u'

    def test_join_condition_extracted(self):
        """Hash Join node has join_condition from human-readable plan."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        join_node = next(n for n in result_nodes if n.get('node_id') == 3)
        assert join_node.get('join_condition') == '(u.id = o.user_id)'

    def test_filter_expression_extracted(self):
        """Scan node has filter_condition from human-readable plan."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        scan_node = next(n for n in result_nodes if n.get('node_id') == 7)
        assert scan_node.get('filter_condition') == '(o.quantity > 0)'

    def test_sort_key_extracted(self):
        """Sort node has sort_key from human-readable plan."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        sort_node = next(n for n in result_nodes if n.get('node_id') == 1)
        assert sort_node.get('sort_key') == 'o.total_spent DESC'

    def test_hashed_aggregate_operation_naming(self):
        """AGG node with :aggstrategy 2 has operation 'HashAggregate'."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        agg_node = next(n for n in result_nodes if n.get('node_id') == 2)
        assert agg_node.get('agg_strategy') == 'Hashed'
        assert agg_node.get('operation') == 'HashAggregate'

    def test_data_movement_on_network_node(self):
        """Network node has data_movement from verbose tree."""
        lines = self._build_explain_verbose_lines()
        result_nodes, _ = _parse_explain_verbose(lines)

        network_node = next(n for n in result_nodes if n.get('node_id') == 4)
        assert network_node.get('data_movement') == 'Broadcast'

    def test_deeply_nested_tree_property_assignment(self):
        """Properties after child subtrees are assigned to the correct parent node.

        Verifies :dataMovement, :jointype, and :aggstrategy that appear AFTER
        child subtrees land on their actual parent nodes, not the last leaf.
        """
        lines = [
            '{ LIMIT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 100.00',
            ':total_cost 100.00',
            ':plan_rows 3',
            ':plan_width 51',
            ':lefttree',
            '  { MERGE',
            '  :node_id 2',
            '  :parent_id 1',
            '  :startup_cost 100.00',
            '  :total_cost 200.00',
            '  :plan_rows 50000',
            '  :plan_width 51',
            '  :lefttree',
            '    { NETWORK',
            '    :node_id 3',
            '    :parent_id 2',
            '    :startup_cost 100.00',
            '    :total_cost 200.00',
            '    :plan_rows 50000',
            '    :plan_width 51',
            '    :lefttree',
            '      { SORT',
            '      :node_id 4',
            '      :parent_id 3',
            '      :startup_cost 100.00',
            '      :total_cost 200.00',
            '      :plan_rows 50000',
            '      :plan_width 51',
            '      :lefttree',
            '        { AGG',
            '        :node_id 5',
            '        :parent_id 4',
            '        :startup_cost 50.00',
            '        :total_cost 150.00',
            '        :plan_rows 50000',
            '        :plan_width 51',
            '        :lefttree',
            '          { HASHJOIN',
            '          :node_id 6',
            '          :parent_id 5',
            '          :startup_cost 10.00',
            '          :total_cost 80.00',
            '          :plan_rows 350000',
            '          :plan_width 51',
            '          :dist_info.dist_strategy DS_BCAST_INNER',
            '          :lefttree',
            '            { SEQSCAN',
            '            :node_id 7',
            '            :parent_id 6',
            '            :startup_cost 0.00',
            '            :total_cost 35.00',
            '            :plan_rows 350000',
            '            :plan_width 20',
            '            :scanrelid 1',
            '            }',
            '          :righttree',
            '            { HASH',
            '            :node_id 8',
            '            :parent_id 6',
            '            :startup_cost 5.00',
            '            :total_cost 5.00',
            '            :plan_rows 50000',
            '            :plan_width 35',
            '            :lefttree',
            '              { SEQSCAN',
            '              :node_id 9',
            '              :parent_id 8',
            '              :startup_cost 0.00',
            '              :total_cost 5.00',
            '              :plan_rows 50000',
            '              :plan_width 35',
            '              :scanrelid 2',
            '              }',
            '            }',
            '          :jointype 0',
            '          :hashclauses ({ OPEXPR',
            '          :opno 96',
            '          :args ({ VAR :varno 65001 :varattno 2 } { VAR :varno 65000 :varattno 1 })',
            '          })',
            '          }',
            '        :aggstrategy 2',
            '        :numCols 4',
            '        :grpColIdx 1 2 3 4',
            '        }',
            '      :numCols 1',
            '      :sortColIdx 5',
            '      }',
            '    :dataMovement Send to leader',
            '    }',
            '  :numCols 1',
            '  :sortColIdx 5',
            '  }',
            '}',
            '',
            'XN Limit  (cost=100.00..100.00 rows=3 width=51)',
            '  ->  XN Merge  (cost=100.00..200.00 rows=50000 width=51)',
            '        Merge Key: sum(s.pricepaid)',
            '        ->  XN Network  (cost=100.00..200.00 rows=50000 width=51)',
            '              Send to leader',
            '              ->  XN Sort  (cost=100.00..200.00 rows=50000 width=51)',
            '                    Sort Key: sum(s.pricepaid)',
            '                    ->  XN HashAggregate  (cost=50.00..150.00 rows=50000 width=51)',
            '                          ->  XN Hash Join DS_BCAST_INNER  (cost=10.00..80.00 rows=350000 width=51)',
            '                                Hash Cond: ("outer".buyerid = "inner".userid)',
            '                                ->  XN Seq Scan on sales s  (cost=0.00..35.00 rows=350000 width=20)',
            '                                ->  XN Hash  (cost=5.00..5.00 rows=50000 width=35)',
            '                                      ->  XN Seq Scan on users u  (cost=0.00..5.00 rows=50000 width=35)',
        ]

        result_nodes, _ = _parse_explain_verbose(lines)

        # Build a lookup by node_id for easy assertions
        nodes_by_id = {n['node_id']: n for n in result_nodes}

        # All 9 nodes should be parsed
        assert len(result_nodes) == 9, f'Expected 9 nodes, got {len(result_nodes)}'

        # :dataMovement "Send to leader" must be on NETWORK (node 3), NOT on last SEQSCAN
        network_node = nodes_by_id[3]
        assert network_node['operation'] == 'Network'
        assert network_node.get('data_movement') == 'Send to leader'

        hashjoin_node = nodes_by_id[6]
        assert hashjoin_node['operation'] == 'Hash Join'
        assert hashjoin_node.get('join_type') == 'Inner'

        agg_node = nodes_by_id[5]
        assert agg_node.get('agg_strategy') == 'Hashed'
        assert agg_node.get('operation') == 'HashAggregate'

        # Last SEQSCAN (node 9) must NOT have properties that belong to parent nodes
        last_seqscan = nodes_by_id[9]
        assert last_seqscan['operation'] == 'Seq Scan'
        assert last_seqscan.get('join_type') is None
        assert last_seqscan.get('agg_strategy') is None
        assert last_seqscan.get('data_movement') is None

    # --- Parsing preservation tests ---

    # ---------------------------------------------------------------
    # Core properties
    # ---------------------------------------------------------------

    def test_core_properties_extracted_correctly(self):
        """Core properties are extracted identically from the verbose tree.

        For any EXPLAIN VERBOSE input, node_id, parent_node_id, cost_startup,
        cost_total, rows, width, distribution_type, scan_relid, join_type,
        agg_strategy are extracted correctly from the verbose tree section.

        """
        lines = [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 100.50',
            ':total_cost 250.75',
            ':plan_rows 500',
            ':plan_width 64',
            '}',
            '{ HASHJOIN',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 10.00',
            ':total_cost 80.00',
            ':plan_rows 200',
            ':plan_width 24',
            ':jointype 1',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
            '{ SEQSCAN',
            ':node_id 3',
            ':parent_id 2',
            ':startup_cost 0.00',
            ':total_cost 30.00',
            ':plan_rows 100',
            ':plan_width 16',
            ':scanrelid 1',
            '}',
            '{ AGG',
            ':node_id 4',
            ':parent_id 1',
            ':startup_cost 50.00',
            ':total_cost 150.00',
            ':plan_rows 50',
            ':plan_width 32',
            ':aggstrategy 2',
            '}',
        ]

        result_nodes, _ = _parse_explain_verbose(lines)

        # Verify all 4 nodes were parsed
        assert len(result_nodes) == 4

        # SORT node
        sort_node = next(n for n in result_nodes if n['node_id'] == 1)
        assert sort_node['node_id'] == 1
        assert sort_node['parent_node_id'] is None  # parent_id 0 maps to None
        assert sort_node['cost_startup'] == 100.50
        assert sort_node['cost_total'] == 250.75
        assert sort_node['rows'] == 500
        assert sort_node['width'] == 64

        # HASHJOIN node
        join_node = next(n for n in result_nodes if n['node_id'] == 2)
        assert join_node['node_id'] == 2
        assert join_node['parent_node_id'] == 1
        assert join_node['cost_startup'] == 10.00
        assert join_node['cost_total'] == 80.00
        assert join_node['rows'] == 200
        assert join_node['width'] == 24
        assert join_node['join_type'] == 'Left'
        assert join_node['distribution_type'] == 'DS_DIST_NONE'

        # SEQSCAN node
        scan_node = next(n for n in result_nodes if n['node_id'] == 3)
        assert scan_node['node_id'] == 3
        assert scan_node['parent_node_id'] == 2
        assert scan_node['cost_startup'] == 0.00
        assert scan_node['cost_total'] == 30.00
        assert scan_node['rows'] == 100
        assert scan_node['width'] == 16
        assert scan_node['scan_relid'] == 1

        # AGG node
        agg_node = next(n for n in result_nodes if n['node_id'] == 4)
        assert agg_node['node_id'] == 4
        assert agg_node['parent_node_id'] == 1
        assert agg_node['agg_strategy'] == 'Hashed'

    def test_core_properties_with_all_join_types(self):
        """All join type mappings are extracted correctly."""
        join_type_map = {
            0: 'Inner',
            1: 'Left',
            2: 'Full',
            3: 'Right',
            4: 'Semi',
            5: 'Anti',
        }

        for join_code, expected_name in join_type_map.items():
            lines = [
                '{ HASHJOIN',
                ':node_id 1',
                ':parent_id 0',
                ':startup_cost 0.00',
                ':total_cost 10.00',
                ':plan_rows 10',
                ':plan_width 8',
                f':jointype {join_code}',
                '}',
            ]
            result_nodes, _ = _parse_explain_verbose(lines)
            assert len(result_nodes) == 1
            assert result_nodes[0]['join_type'] == expected_name, (
                f'jointype {join_code} should map to {expected_name!r}'
            )

    def test_core_properties_with_all_agg_strategies(self):
        """All agg_strategy mappings are extracted correctly."""
        agg_strategy_map = {
            0: 'Plain',
            1: 'Sorted',
            2: 'Hashed',
        }

        for agg_code, expected_name in agg_strategy_map.items():
            lines = [
                '{ AGG',
                ':node_id 1',
                ':parent_id 0',
                ':startup_cost 0.00',
                ':total_cost 10.00',
                ':plan_rows 10',
                ':plan_width 8',
                f':aggstrategy {agg_code}',
                '}',
            ]
            result_nodes, _ = _parse_explain_verbose(lines)
            assert len(result_nodes) == 1
            assert result_nodes[0]['agg_strategy'] == expected_name, (
                f'aggstrategy {agg_code} should map to {expected_name!r}'
            )

    def test_core_properties_distribution_type_filtering(self):
        """Distribution types DS_DIST_ERR and <> are filtered out."""
        # Valid distribution type
        lines_valid = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':dist_info.dist_strategy DS_BCAST_INNER',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines_valid)
        assert result_nodes[0]['distribution_type'] == 'DS_BCAST_INNER'

        # DS_DIST_ERR should be filtered out
        lines_err = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':dist_info.dist_strategy DS_DIST_ERR',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines_err)
        assert 'distribution_type' not in result_nodes[0]

        # <> should be filtered out
        lines_empty = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':dist_info.dist_strategy <>',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines_empty)
        assert 'distribution_type' not in result_nodes[0]

    def test_core_properties_level_calculation(self):
        """Node levels are calculated correctly from parent chain."""
        lines = [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
            '{ HASHJOIN',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
            '{ SEQSCAN',
            ':node_id 3',
            ':parent_id 2',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['level'] == 0  # root
        assert result_nodes[1]['level'] == 1  # child of root
        assert result_nodes[2]['level'] == 2  # grandchild

    def test_core_properties_data_movement(self):
        """Data movement is extracted from verbose tree for Network nodes."""
        lines = [
            '{ NETWORK',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':dataMovement Broadcast',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['data_movement'] == 'Broadcast'

        # Node without data movement should not have the field
        lines_no_dm = [
            '{ SEQSCAN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines_no_dm)
        assert 'data_movement' not in result_nodes[0]

    def test_core_properties_source_table_oid(self):
        """Source table OID is extracted for scan nodes from :resorigtbl."""
        lines = [
            '{ SEQSCAN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':scanrelid 1',
            ':resorigtbl 12345',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['source_table_oid'] == 12345

    # ---------------------------------------------------------------
    # Human-readable plan text
    # ---------------------------------------------------------------

    def test_human_readable_plan_captured_unchanged(self):
        """The human_readable_plan string is captured unchanged from the input."""
        human_plan_lines = [
            'XN Sort  (cost=100.00..200.00 rows=50 width=32)',
            '  Sort Key: total_spent DESC',
            '  ->  XN Seq Scan on users u  (cost=0.00..30.00 rows=100 width=16)',
            '        Filter: (active = true)',
        ]
        lines = [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 100.00',
            ':total_cost 200.00',
            ':plan_rows 50',
            ':plan_width 32',
            '}',
            '{ SEQSCAN',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 0.00',
            ':total_cost 30.00',
            ':plan_rows 100',
            ':plan_width 16',
            '}',
            '',  # empty line separator
        ] + human_plan_lines

        _, human_readable_plan = _parse_explain_verbose(lines)

        expected = '\n'.join(human_plan_lines)
        assert human_readable_plan == expected, (
            f'Human-readable plan text should be captured unchanged.\n'
            f'Expected:\n{expected!r}\n'
            f'Got:\n{human_readable_plan!r}'
        )

    def test_human_readable_plan_empty_when_no_section(self):
        """When there is no human-readable plan section, the string is empty."""
        lines = [
            '{ SEQSCAN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
        ]
        _, human_readable_plan = _parse_explain_verbose(lines)
        assert human_readable_plan == '', (
            'Human-readable plan should be empty when no plan section exists'
        )

    def test_human_readable_plan_multiline_preserved(self):
        """Multi-line human-readable plan text preserves all lines and indentation."""
        human_plan_lines = [
            'XN Merge Join DS_DIST_NONE  (cost=0.00..100.00 rows=1000 width=48)',
            '  Merge Cond: (a.id = b.id)',
            '  ->  XN Seq Scan on table_a a  (cost=0.00..50.00 rows=500 width=24)',
            '  ->  XN Seq Scan on table_b b  (cost=0.00..50.00 rows=500 width=24)',
            "        Filter: (b.status = 'active')",
        ]
        lines = [
            '{ MERGEJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 100.00',
            ':plan_rows 1000',
            ':plan_width 48',
            '}',
            '',  # separator
        ] + human_plan_lines

        _, human_readable_plan = _parse_explain_verbose(lines)
        expected = '\n'.join(human_plan_lines)
        assert human_readable_plan == expected

    # ---------------------------------------------------------------
    # Plain aggregate naming
    # ---------------------------------------------------------------

    def test_plain_aggregate_keeps_aggregate_operation(self):
        """AGG nodes with :aggstrategy 0 (Plain) continue to have operation == 'Aggregate'."""
        lines = [
            '{ AGG',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 1',
            ':plan_width 8',
            ':aggstrategy 0',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert len(result_nodes) == 1
        assert result_nodes[0]['operation'] == 'Aggregate', (
            'Plain aggregate (aggstrategy 0) must keep operation="Aggregate"'
        )
        assert result_nodes[0]['agg_strategy'] == 'Plain'

    # ---------------------------------------------------------------
    # None defaults for missing enrichment
    # ---------------------------------------------------------------

    def test_none_for_missing_join_condition(self):
        """Join nodes without join condition lines in human-readable plan retain None."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':jointype 0',
            '}',
            '',  # separator
            'XN Hash Join DS_DIST_NONE  (cost=0.00..10.00 rows=10 width=8)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0].get('join_condition') is None, (
            'join_condition should be None when no condition line exists'
        )

    def test_none_for_missing_filter_condition(self):
        """Nodes without filter lines in human-readable plan retain None."""
        lines = [
            '{ SEQSCAN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
            '',  # separator
            'XN Seq Scan on users  (cost=0.00..10.00 rows=10 width=8)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0].get('filter_condition') is None, (
            'filter_condition should be None when no filter line exists'
        )

    def test_none_for_missing_sort_key(self):
        """Sort nodes without sort key lines in human-readable plan retain None."""
        lines = [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            '}',
            '',  # separator
            'XN Sort  (cost=0.00..10.00 rows=10 width=8)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0].get('sort_key') is None, (
            'sort_key should be None when no sort key line exists'
        )

    def test_none_for_all_enrichment_fields_without_human_plan(self):
        """When there is no human-readable plan section, all enrichment fields remain None."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 10.00',
            ':total_cost 80.00',
            ':plan_rows 200',
            ':plan_width 24',
            ':jointype 0',
            '}',
            '{ SEQSCAN',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 0.00',
            ':total_cost 30.00',
            ':plan_rows 100',
            ':plan_width 16',
            ':scanrelid 1',
            '}',
            '{ SORT',
            ':node_id 3',
            ':parent_id 1',
            ':startup_cost 0.00',
            ':total_cost 20.00',
            ':plan_rows 50',
            ':plan_width 8',
            '}',
        ]
        result_nodes, human_readable_plan = _parse_explain_verbose(lines)

        assert human_readable_plan == ''

        for node in result_nodes:
            assert node.get('join_condition') is None, (
                f'node_id {node["node_id"]}: join_condition should be None without human plan'
            )
            assert node.get('filter_condition') is None, (
                f'node_id {node["node_id"]}: filter_condition should be None without human plan'
            )
            assert node.get('sort_key') is None, (
                f'node_id {node["node_id"]}: sort_key should be None without human plan'
            )
            assert node.get('relation_name') is None, (
                f'node_id {node["node_id"]}: relation_name should be None without human plan'
            )

    def test_none_enrichment_with_human_plan_but_no_detail_lines(self):
        """When human-readable plan has node lines but no detail lines, enrichment stays None."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 10.00',
            ':total_cost 80.00',
            ':plan_rows 200',
            ':plan_width 24',
            ':jointype 0',
            '}',
            '{ SEQSCAN',
            ':node_id 2',
            ':parent_id 1',
            ':startup_cost 0.00',
            ':total_cost 30.00',
            ':plan_rows 100',
            ':plan_width 16',
            '}',
            '',  # separator
            'XN Hash Join DS_DIST_NONE  (cost=10.00..80.00 rows=200 width=24)',
            '  ->  XN Seq Scan on users  (cost=0.00..30.00 rows=100 width=16)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)

        join_node = next(n for n in result_nodes if n['node_id'] == 1)
        assert join_node.get('join_condition') is None
        assert join_node.get('filter_condition') is None

        scan_node = next(n for n in result_nodes if n['node_id'] == 2)
        assert scan_node.get('filter_condition') is None
        assert scan_node.get('sort_key') is None

    # ---------------------------------------------------------------
    # Operation name mapping
    # ---------------------------------------------------------------

    def test_operation_names_mapped_correctly(self):
        """All known operation types map to their expected human-readable names."""
        operation_tests = [
            ('LIMIT', 'Limit'),
            ('MERGE', 'Merge'),
            ('NETWORK', 'Network'),
            ('SORT', 'Sort'),
            ('AGG', 'Aggregate'),
            ('HASHJOIN', 'Hash Join'),
            ('MERGEJOIN', 'Merge Join'),
            ('NESTLOOP', 'Nested Loop'),
            ('SEQSCAN', 'Seq Scan'),
            ('HASH', 'Hash'),
            ('SUBQUERYSCAN', 'Subquery Scan'),
            ('APPEND', 'Append'),
            ('RESULT', 'Result'),
            ('UNIQUE', 'Unique'),
            ('SETOP', 'SetOp'),
            ('WINDOW', 'Window'),
            ('INDEXSCAN', 'Index Scan'),
        ]

        for verbose_name, expected_operation in operation_tests:
            lines = [
                f'{{ {verbose_name}',
                ':node_id 1',
                ':parent_id 0',
                ':startup_cost 0.00',
                ':total_cost 10.00',
                ':plan_rows 10',
                ':plan_width 8',
                '}',
            ]
            result_nodes, _ = _parse_explain_verbose(lines)
            assert len(result_nodes) == 1, f'{verbose_name} should produce exactly one node'
            assert result_nodes[0]['operation'] == expected_operation, (
                f'{verbose_name} should map to {expected_operation!r}, '
                f'got {result_nodes[0]["operation"]!r}'
            )

    # ---------------------------------------------------------------
    # Nested structures (TARGETENTRY, VAR, etc.)
    # ---------------------------------------------------------------

    def test_nested_structures_skipped_correctly(self):
        """Nested structures like TARGETENTRY, VAR, CONST are not treated as plan nodes."""
        lines = [
            '{ SEQSCAN',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 0.00',
            ':total_cost 10.00',
            ':plan_rows 10',
            ':plan_width 8',
            ':scanrelid 1',
            '{ TARGETENTRY',
            ':resno 1',
            ':resorigtbl 99999',
            '}',
            '{ VAR',
            ':varno 1',
            ':varattno 1',
            '}',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        # Only the SEQSCAN should be a plan node, not TARGETENTRY or VAR
        assert len(result_nodes) == 1
        assert result_nodes[0]['operation'] == 'Seq Scan'
        # The :resorigtbl from TARGETENTRY should be captured for scan nodes
        assert result_nodes[0].get('source_table_oid') == 99999

    # ---------------------------------------------------------------
    # Additional parsing from real execution plan outcomes
    # ---------------------------------------------------------------

    def test_window_node_parsed(self):
        """WINDOW operation type is parsed correctly."""
        lines = [
            '{ WINDOW',
            ':node_id 1',
            ':parent_id 0',
            ':startup_cost 200.00',
            ':total_cost 300.00',
            ':plan_rows 1441',
            ':plan_width 88',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert len(result_nodes) == 1
        assert result_nodes[0]['operation'] == 'Window'
        assert result_nodes[0]['rows'] == 1441
        assert result_nodes[0]['distribution_type'] == 'DS_DIST_NONE'

    def test_append_node_parsed(self):
        """APPEND operation type is parsed for UNION ALL queries."""
        lines = [
            '{ APPEND',
            ':node_id 1',
            ':parent_id 0',
            ':plan_rows 5000000',
            '}',
            '{ SEQSCAN',
            ':node_id 2',
            ':parent_id 1',
            ':plan_rows 2880404',
            '}',
            '{ SEQSCAN',
            ':node_id 3',
            ':parent_id 1',
            ':plan_rows 1441548',
            '}',
            '{ SEQSCAN',
            ':node_id 4',
            ':parent_id 1',
            ':plan_rows 719384',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert len(result_nodes) == 4
        assert result_nodes[0]['operation'] == 'Append'
        for n in result_nodes[1:]:
            assert n['parent_node_id'] == 1

    def test_merge_key_extracted_from_human_plan(self):
        """Merge Key detail line is extracted into the Merge node."""
        lines = [
            '{ MERGE',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '{ SEQSCAN',
            ':node_id 2',
            ':parent_id 1',
            '}',
            '',
            'XN Merge  (cost=100.00..200.00 rows=25 width=104)',
            '  Merge Key: sum(l.l_extendedprice)',
            '  ->  XN Seq Scan on nation n  (cost=0.00..50.00 rows=25 width=104)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        merge_node = next(n for n in result_nodes if n['node_id'] == 1)
        assert merge_node.get('merge_key') == 'sum(l.l_extendedprice)'

    def test_ds_dist_outer_parsed(self):
        """DS_DIST_OUTER distribution type is preserved."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':dist_info.dist_strategy DS_DIST_OUTER',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['distribution_type'] == 'DS_DIST_OUTER'

    def test_ds_dist_all_none_parsed(self):
        """DS_DIST_ALL_NONE distribution type is preserved."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':dist_info.dist_strategy DS_DIST_ALL_NONE',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['distribution_type'] == 'DS_DIST_ALL_NONE'

    def test_dual_window_functions_produce_two_window_nodes(self):
        """Two window functions produce two Window nodes with interleaved Sort/Network."""
        lines = [
            '{ SORT',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '{ WINDOW',
            ':node_id 2',
            ':parent_id 1',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
            '{ SORT',
            ':node_id 3',
            ':parent_id 2',
            '}',
            '{ NETWORK',
            ':node_id 4',
            ':parent_id 3',
            ':dataMovement Distribute',
            '}',
            '{ WINDOW',
            ':node_id 5',
            ':parent_id 4',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
            '{ SORT',
            ':node_id 6',
            ':parent_id 5',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        window_nodes = [n for n in result_nodes if n['operation'] == 'Window']
        assert len(window_nodes) == 2
        network_node = next(n for n in result_nodes if n['node_id'] == 4)
        assert network_node['data_movement'] == 'Distribute'

    def test_sorted_aggregate_becomes_group_aggregate(self):
        """AGG with :aggstrategy 1 becomes GroupAggregate."""
        lines = [
            '{ AGG',
            ':node_id 1',
            ':parent_id 0',
            ':aggstrategy 1',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['operation'] == 'GroupAggregate'
        assert result_nodes[0]['agg_strategy'] == 'Sorted'

    def test_network_data_movement_fallback_from_human_plan(self):
        """Network node gets data_movement from human-readable plan op line when verbose lacks it.

        The fallback regex checks the operation line (not detail lines), so the
        movement keyword must appear in the op line itself (e.g. "XN Network Distribute").
        """
        lines = [
            '{ NETWORK',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '',
            'XN Network Distribute  (cost=0.00..10.00 rows=100 width=16)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0].get('data_movement') == 'Distribute'

    def test_network_data_movement_not_set_from_detail_line(self):
        """Network node does NOT get data_movement when keyword is only in a detail line."""
        lines = [
            '{ NETWORK',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '',
            'XN Network  (cost=0.00..10.00 rows=100 width=16)',
            '  Send to leader',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0].get('data_movement') is None

    def test_anti_join_type_parsed(self):
        """Anti-join (jointype 5) is parsed correctly from verbose tree."""
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':jointype 5',
            ':dist_info.dist_strategy DS_DIST_NONE',
            '}',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert result_nodes[0]['join_type'] == 'Anti'
        assert result_nodes[0]['distribution_type'] == 'DS_DIST_NONE'

    def test_initplan_does_not_break_node_matching(self):
        """InitPlan lines in human-readable plan do not misalign positional matching."""
        lines = [
            '{ MERGE',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '{ AGG',
            ':node_id 2',
            ':parent_id 1',
            '}',
            '{ SEQSCAN',
            ':node_id 3',
            ':parent_id 2',
            '}',
            '{ NETWORK',
            ':node_id 4',
            ':parent_id 1',
            '}',
            '{ SEQSCAN',
            ':node_id 5',
            ':parent_id 4',
            '}',
            '',
            'XN Merge  (cost=100.00..200.00 rows=25 width=104)',
            '  Merge Key: revenue',
            '  InitPlan',
            '    ->  XN Aggregate  (cost=75.00..75.00 rows=1 width=16)',
            '          ->  XN Seq Scan on lineitem l2  (cost=0.00..60.00 rows=6000000 width=16)',
            '  ->  XN Network  (cost=100.00..200.00 rows=25 width=104)',
            '        Send to leader',
            '        ->  XN Seq Scan on orders o  (cost=0.00..50.00 rows=500 width=40)',
            "              Filter: (o_orderdate >= '1995-01-01')",
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert len(result_nodes) == 5
        merge_node = next(n for n in result_nodes if n['node_id'] == 1)
        assert merge_node.get('merge_key') == 'revenue'

    def test_empty_explain_output(self):
        """Empty EXPLAIN output produces no nodes and empty human-readable plan."""
        result_nodes, human_readable_plan = _parse_explain_verbose([])
        assert result_nodes == []
        assert human_readable_plan == ''

    def test_only_human_readable_plan_no_verbose_tree(self):
        """When verbose tree is absent, human-readable plan is not captured.

        The parser only switches to human-readable mode after an empty line
        when at least one verbose node has been parsed. With no nodes, the
        empty line is ignored and subsequent lines are also ignored.
        """
        lines = [
            '',
            'XN Seq Scan on users  (cost=0.00..1.00 rows=100 width=27)',
        ]
        result_nodes, human_readable_plan = _parse_explain_verbose(lines)
        assert result_nodes == []
        assert human_readable_plan == ''

    def test_positional_matching_5_table_join(self):
        """Positional matching works for a 5-table join (provisioned Q1 pattern).

        Verbose tree and human-readable plan have the same node count and order,
        so enrichment (join conditions, filters, sort keys) lands on the correct nodes.
        """
        lines = [
            '{ LIMIT',
            ':node_id 1',
            ':parent_id 0',
            '}',
            '{ SORT',
            ':node_id 2',
            ':parent_id 1',
            '}',
            '{ HASHJOIN',
            ':node_id 3',
            ':parent_id 2',
            ':jointype 0',
            ':dist_info.dist_strategy DS_BCAST_INNER',
            '}',
            '{ SEQSCAN',
            ':node_id 4',
            ':parent_id 3',
            '}',
            '{ HASH',
            ':node_id 5',
            ':parent_id 3',
            '}',
            '{ SEQSCAN',
            ':node_id 6',
            ':parent_id 5',
            '}',
            '',
            'XN Limit  (cost=0.00..100.00 rows=100 width=88)',
            '  ->  XN Sort  (cost=0.00..200.00 rows=1441 width=88)',
            '        Sort Key: s.pricepaid',
            '        ->  XN Hash Join DS_BCAST_INNER  (cost=0.00..300.00 rows=1441 width=88)',
            '              Hash Cond: ("outer".catid = "inner".catid)',
            '              ->  XN Seq Scan on sales s  (cost=0.00..50.00 rows=129157 width=36)',
            '                    Filter: (pricepaid > 500.00)',
            '              ->  XN Hash  (cost=0.11..0.11 rows=11 width=10)',
            '                    ->  XN Seq Scan on category c  (cost=0.00..0.11 rows=11 width=10)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)
        assert len(result_nodes) == 6

        sort_node = next(n for n in result_nodes if n['node_id'] == 2)
        assert sort_node.get('sort_key') == 's.pricepaid'

        join_node = next(n for n in result_nodes if n['node_id'] == 3)
        assert join_node.get('join_condition') == '("outer".catid = "inner".catid)'

        sales_scan = next(n for n in result_nodes if n['node_id'] == 4)
        assert sales_scan.get('relation_name') == 'sales'
        assert sales_scan.get('alias') == 's'
        assert sales_scan.get('filter_condition') == '(pricepaid > 500.00)'

        cat_scan = next(n for n in result_nodes if n['node_id'] == 6)
        assert cat_scan.get('relation_name') == 'category'
        assert cat_scan.get('alias') == 'c'

    def test_append_subquery_scan_misaligns_enrichment(self):
        """Subquery Scan wrappers in verbose tree cause positional mismatch with human plan.

        The verbose tree emits Subquery Scan nodes wrapping each leg of a UNION ALL
        inside an Append, but the human-readable plan shows "Multi Scan" with direct
        Seq Scans. The verbose tree has more nodes than the human-readable plan,
        so enrichment misaligns after the Append.
        """
        lines = [
            '{ HASHJOIN',
            ':node_id 1',
            ':parent_id 0',
            ':jointype 0',
            '}',
            '{ SUBQUERYSCAN',
            ':node_id 2',
            ':parent_id 1',
            '}',
            '{ APPEND',
            ':node_id 3',
            ':parent_id 2',
            '}',
            '{ SUBQUERYSCAN',
            ':node_id 4',
            ':parent_id 3',
            '}',
            '{ SEQSCAN',
            ':node_id 5',
            ':parent_id 4',
            '}',
            '{ SUBQUERYSCAN',
            ':node_id 6',
            ':parent_id 3',
            '}',
            '{ SEQSCAN',
            ':node_id 7',
            ':parent_id 6',
            '}',
            '{ HASH',
            ':node_id 8',
            ':parent_id 1',
            '}',
            '{ SEQSCAN',
            ':node_id 9',
            ':parent_id 8',
            '}',
            '',
            # Human-readable plan has fewer nodes (no Subquery Scan wrappers)
            'XN Hash Join DS_DIST_OUTER  (cost=0.00..100.00 rows=24638 width=184)',
            '  Hash Cond: ("outer".item_sk = "inner".i_item_sk)',
            '  ->  XN Subquery Scan cs  (cost=0.00..50.00 rows=5041336 width=76)',
            '        ->  XN Multi Scan  (cost=0.00..30.00 rows=5041336 width=28)',
            '              ->  XN Seq Scan on store_sales  (cost=0.00..10.00 rows=2880404 width=28)',
            '              ->  XN Seq Scan on catalog_sales  (cost=0.00..10.00 rows=1441548 width=28)',
            '  ->  XN Hash  (cost=1.00..1.00 rows=18000 width=112)',
            '        ->  XN Seq Scan on item i  (cost=0.00..1.00 rows=18000 width=112)',
        ]
        result_nodes, _ = _parse_explain_verbose(lines)

        # All 9 verbose nodes are parsed
        assert len(result_nodes) == 9

        # The Hash Join (node 1) correctly gets its join condition (position 0 matches)
        join_node = next(n for n in result_nodes if n['node_id'] == 1)
        assert join_node.get('join_condition') == '("outer".item_sk = "inner".i_item_sk)'

        # After the Append, enrichment is misaligned because the verbose tree has
        # extra Subquery Scan nodes not present in the human-readable plan.
        item_scan = next(n for n in result_nodes if n['node_id'] == 9)
        assert item_scan['operation'] == 'Seq Scan'

    def test_suggestions_for_data_broadcast(self):
        """Test suggestions are generated for DS_BCAST_INNER distribution."""
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
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'EVEN',
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('EVEN distribution' in s for s in suggestions)

    def test_suggestions_for_missing_sortkey(self):
        """Test suggestions are generated for tables without SORTKEY."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                    {
                        'column_name': 'name',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('SORTKEY' in s for s in suggestions)

    def test_suggestions_for_no_compression(self):
        """Test suggestions are generated for columns without compression."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 1,
                    },
                    {
                        'column_name': 'name',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('compression' in s.lower() for s in suggestions)

    def test_no_duplicate_suggestions(self):
        """Test that duplicate suggestions are removed."""
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
        suggestions = _generate_performance_suggestions([], [])
        assert suggestions == []

    def test_optimal_plan_no_suggestions(self):
        """Test that optimal plans generate no suggestions."""
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
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)

        assert suggestions == []

    def test_suggestions_for_dist_all_inner(self):
        """Test suggestions for DS_DIST_ALL_INNER distribution."""
        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_ALL_INNER',
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert len(suggestions) == 1
        assert 'Full table redistribution detected' in suggestions[0]
        assert 'DISTSTYLE ALL' in suggestions[0]
        assert '< 1-2M rows' in suggestions[0]

    def test_suggestions_for_small_table_diststyle_all(self):
        """Test DISTSTYLE ALL suggestion for small dimension tables."""
        tables = [
            {
                'schema_name': 'public',
                'table_name': 'dim_date',
                'redshift_diststyle': 'EVEN',
                'redshift_estimated_row_count': 365,
                'columns': [],
            }
        ]
        suggestions = _generate_performance_suggestions([], tables)

        assert len(suggestions) == 1
        assert 'dim_date' in suggestions[0]
        assert '365 rows' in suggestions[0]
        assert 'DISTSTYLE ALL' in suggestions[0]
        assert 'dimension table' in suggestions[0]

    def test_suggestions_for_dist_inner(self):
        """Test suggestions for DS_DIST_INNER distribution."""
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
        columns = [{'column_name': f'col{i}', 'redshift_encoding': 'none'} for i in range(10)]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'large_table',
                'redshift_diststyle': 'KEY',
                'columns': columns,
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert len(suggestions) >= 1
        assert any('columns' in s and 'compression' in s.lower() for s in suggestions)

    def test_suggestions_for_high_sequential_scans_no_sortkey(self):
        """Test suggestions when sequential scans are high and no sort key is defined."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'stats_sequential_scans': 5000,
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                    {
                        'column_name': 'ts',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any('5,000 sequential scans' in s and 'SORTKEY' in s for s in suggestions)

    def test_suggestions_for_low_correlation(self):
        """Test suggestions when a non-sortkey column has low correlation."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'order_date',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.05,
                    },
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                        'stats_correlation': 0.99,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        # Should suggest SORTKEY for order_date (low correlation, not a sortkey)
        assert any(
            'order_date' in s and 'correlation' in s and 'SORTKEY' in s for s in suggestions
        )
        # Should NOT suggest for id (already a sortkey)
        assert not any('column id' in s.lower() for s in suggestions)

    def test_no_correlation_suggestion_when_already_sortkey(self):
        """Test no correlation suggestion for columns that are already sort keys."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'event_time',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                        'stats_correlation': 0.01,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        # No correlation suggestion since column is already a sortkey
        assert not any('correlation' in s for s in suggestions)

    def test_no_correlation_suggestion_when_high_correlation(self):
        """Test no correlation suggestion when correlation is high."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.95,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert not any('correlation' in s for s in suggestions)

    def test_suggestions_for_low_cardinality_distkey(self):
        """Test suggestion when DISTKEY column has very low cardinality."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000000,
                'columns': [
                    {
                        'column_name': 'status',
                        'redshift_encoding': 'lzo',
                        'redshift_is_distkey': True,
                        'redshift_sortkey_position': 0,
                        'stats_n_distinct': 5,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any('DISTKEY column status' in s and 'low cardinality' in s for s in suggestions)

    def test_no_distkey_suggestion_when_high_cardinality(self):
        """Test no low-cardinality suggestion when DISTKEY has many distinct values."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000000,
                'columns': [
                    {
                        'column_name': 'order_id',
                        'redshift_encoding': 'lzo',
                        'redshift_is_distkey': True,
                        'redshift_sortkey_position': 0,
                        'stats_n_distinct': -1.0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert not any('low cardinality' in s for s in suggestions)

    def test_suggestions_for_high_null_sortkey(self):
        """Test suggestion when SORTKEY column is mostly NULL."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'deleted_at',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                        'stats_null_frac': 0.95,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any('SORTKEY column deleted_at' in s and '95% NULL' in s for s in suggestions)

    def test_no_null_suggestion_when_low_null_frac(self):
        """Test no NULL suggestion when SORTKEY column has low null fraction."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'event_time',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                        'stats_null_frac': 0.01,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert not any('NULL' in s and 'SORTKEY' in s for s in suggestions)

    def test_suggestions_for_wide_uncompressed_columns(self):
        """Test suggestion for wide variable-length columns with no compression."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'logs',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'message',
                        'data_type': 'character varying',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'stats_avg_width': 256,
                    },
                    {
                        'column_name': 'id',
                        'data_type': 'integer',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                        'stats_avg_width': 4,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any(
            'Wide columns' in s and 'message' in s and '>200 bytes' in s for s in suggestions
        )

    def test_no_wide_uncompressed_for_fixed_width_types(self):
        """Fixed-width types (int/bigint/date) should not be flagged as wide even with high avg_width."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'data_type': 'bigint',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'stats_avg_width': 250,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        # No "Wide columns" suggestion since bigint is fixed-width
        assert not any('Wide columns' in s for s in suggestions)

    def test_no_wide_uncompressed_below_threshold(self):
        """Variable-length columns under 200 bytes should not be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'logs',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'code',
                        'data_type': 'varchar',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'stats_avg_width': 100,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert not any('Wide columns' in s for s in suggestions)

    def test_no_suggestion_for_ds_dist_none(self):
        """DS_DIST_NONE (co-located join) should not generate redistribution suggestions."""
        nodes = [
            {'node_id': 1, 'operation': 'Hash Join', 'distribution_type': 'DS_DIST_NONE'},
        ]
        suggestions = _generate_performance_suggestions(nodes, [])
        assert len(suggestions) == 0

    def test_no_suggestion_for_ds_dist_all_none(self):
        """DS_DIST_ALL_NONE (DISTSTYLE ALL join) should not generate suggestions."""
        nodes = [
            {'node_id': 1, 'operation': 'Hash Join', 'distribution_type': 'DS_DIST_ALL_NONE'},
        ]
        suggestions = _generate_performance_suggestions(nodes, [])
        assert len(suggestions) == 0

    def test_suggestion_for_small_table_auto_diststyle(self):
        """Small tables with AUTO(EVEN) or AUTO(KEY) get DISTSTYLE ALL suggestion."""
        for style in ('AUTO(EVEN)', 'AUTO(KEY)'):
            table_designs = [
                {
                    'schema_name': 'tickit',
                    'table_name': 'venue',
                    'redshift_diststyle': style,
                    'redshift_estimated_row_count': 202,
                    'columns': [
                        {
                            'column_name': 'venueid',
                            'redshift_encoding': 'lzo',
                            'redshift_sortkey_position': 1,
                        },
                    ],
                }
            ]
            suggestions = _generate_performance_suggestions([], table_designs)
            assert any('DISTSTYLE ALL' in s for s in suggestions), (
                f'{style} small table should get DISTSTYLE ALL suggestion'
            )

    def test_no_diststyle_all_for_large_key_table(self):
        """Tables >= 2M rows with KEY distribution should not get DISTSTYLE ALL suggestion."""
        table_designs = [
            {
                'schema_name': 'tpch',
                'table_name': 'lineitem',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 6001215,
                'columns': [
                    {
                        'column_name': 'l_orderkey',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                    {
                        'column_name': 'l_shipdate',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 1,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('DISTSTYLE ALL' in s for s in suggestions)

    def test_suggestion_for_table_with_no_row_count(self):
        """Table with None row count should not crash or suggest DISTSTYLE ALL."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'mystery',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': None,
                'columns': [],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('DISTSTYLE ALL' in s for s in suggestions)

    def test_combined_node_and_table_suggestions(self):
        """Both node-level and table-level suggestions are generated together."""
        nodes = [
            {'node_id': 1, 'operation': 'Hash Join', 'distribution_type': 'DS_BCAST_INNER'},
        ]
        table_designs = [
            {
                'schema_name': 'tickit',
                'table_name': 'category',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 11,
                'columns': [
                    {
                        'column_name': 'catid',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 1,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert any('broadcast' in s.lower() for s in suggestions)
        assert any('DISTSTYLE ALL' in s for s in suggestions)

    def test_no_correlation_suggestion_for_small_table(self):
        """Low correlation on a <100K row table should NOT trigger a SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'small_table',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 50000,
                'columns': [
                    {
                        'column_name': 'col1',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.05,
                        'stats_n_distinct': 10000,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('correlation' in s for s in suggestions)

    def test_no_correlation_suggestion_for_low_cardinality_column(self):
        """Low correlation on a very low-cardinality column should NOT trigger a SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'big_table',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 10000000,
                'columns': [
                    {
                        'column_name': 'flag',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.05,
                        # Only 5 distinct values — zone maps are fine regardless
                        'stats_n_distinct': 5,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('correlation' in s for s in suggestions)

    def test_correlation_suggestion_for_large_high_cardinality_table(self):
        """Low correlation on a large, high-cardinality column should trigger a SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 10000000,
                'columns': [
                    {
                        'column_name': 'order_date',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.05,
                        'stats_n_distinct': 365,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert any(
            'order_date' in s and 'correlation' in s and 'SORTKEY' in s for s in suggestions
        )

    def test_no_low_cardinality_distkey_for_small_table(self):
        """Low distinct-count on a small table (high selectivity) should NOT be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'tiny',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 100,
                'columns': [
                    {
                        'column_name': 'status',
                        'redshift_encoding': 'lzo',
                        'redshift_is_distkey': True,
                        'redshift_sortkey_position': 0,
                        'stats_n_distinct': 50,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        # 50 distinct / 100 rows = 0.5 selectivity — not low-cardinality
        assert not any('low cardinality' in s for s in suggestions)

    def test_no_low_cardinality_distkey_when_absolute_count_high(self):
        """Many distinct values should not be flagged even if selectivity is low."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'big',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 1000000000,
                'columns': [
                    {
                        'column_name': 'cust_id',
                        'redshift_encoding': 'lzo',
                        'redshift_is_distkey': True,
                        'redshift_sortkey_position': 0,
                        # 5000 distinct is above the 100 absolute-count threshold
                        'stats_n_distinct': 5000,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('low cardinality' in s for s in suggestions)

    def test_no_encoding_suggestion_for_first_sortkey(self):
        """First column of compound SORTKEY must be RAW and should not be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'event_time',
                        'data_type': 'timestamp without time zone',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 1,  # first sortkey — must stay RAW
                    },
                    {
                        'column_name': 'user_id',
                        'data_type': 'bigint',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        # No compression suggestion since the only RAW column is the first sortkey
        assert not any('compression' in s.lower() for s in suggestions)

    def test_no_encoding_suggestion_for_boolean(self):
        """BOOLEAN columns cannot be encoded and should not be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'flags',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'is_active',
                        'data_type': 'boolean',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                    },
                    {
                        'column_name': 'id',
                        'data_type': 'bigint',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 1,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        # No compression suggestion — is_active is boolean (excluded), id has a sortkey
        assert not any('compression' in s.lower() for s in suggestions)

    def test_encoding_suggestion_for_non_sortkey_non_boolean(self):
        """Regular RAW columns (not sortkey[1], not boolean) should still be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 't',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'name',
                        'data_type': 'character varying',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert any('name' in s and 'compression' in s.lower() for s in suggestions)

    def test_no_seq_scan_suggestion_for_small_table(self):
        """High seq_scans on a small table (<100K rows) should not be flagged."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'small',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 50000,
                'stats_sequential_scans': 10000,
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('sequential scans' in s for s in suggestions)

    def test_no_seq_scan_suggestion_for_diststyle_all(self):
        """DISTSTYLE ALL tables are expected to be seq-scanned locally on each node."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'dim_country',
                'redshift_diststyle': 'ALL',
                'redshift_estimated_row_count': 1000000,
                'stats_sequential_scans': 10000,
                'columns': [
                    {
                        'column_name': 'country_id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('sequential scans' in s for s in suggestions)

    def test_no_seq_scan_suggestion_for_auto_all(self):
        """AUTO(ALL) should also be suppressed like ALL."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'dim',
                'redshift_diststyle': 'AUTO(ALL)',
                'redshift_estimated_row_count': 1000000,
                'stats_sequential_scans': 10000,
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)
        assert not any('sequential scans' in s for s in suggestions)

    def test_join_numeric_type_mismatch_flagged(self):
        """Join between integer and bigint columns should flag numeric-type mismatch."""
        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(orders.cust_id = customers.id)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'cust_id',
                        'data_type': 'integer',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 0,
                    },
                ],
            },
            {
                'schema_name': 'public',
                'table_name': 'customers',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'data_type': 'bigint',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 1,
                    },
                ],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert any(
            'mismatched numeric types' in s and 'cust_id' in s and 'id' in s for s in suggestions
        )

    def test_join_char_length_difference_not_flagged(self):
        """Join between varchar(10) and varchar(20) should NOT be flagged (no cast)."""
        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(a.code = b.code)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'a',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'code',
                        'data_type': 'character varying(10)',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            },
            {
                'schema_name': 'public',
                'table_name': 'b',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'code',
                        'data_type': 'character varying(20)',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                    },
                ],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert not any('mismatched numeric types' in s for s in suggestions)

    def test_join_same_numeric_type_not_flagged(self):
        """Join between columns with the same numeric type should not be flagged."""
        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(a.x = b.y)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'a',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'x',
                        'data_type': 'bigint',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 0,
                    },
                ],
            },
            {
                'schema_name': 'public',
                'table_name': 'b',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'y',
                        'data_type': 'bigint',
                        'redshift_encoding': 'az64',
                        'redshift_sortkey_position': 1,
                    },
                ],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert not any('mismatched numeric types' in s for s in suggestions)

    def test_join_condition_without_types_not_flagged(self):
        """Missing data_type info on one side should silently skip the mismatch check."""
        nodes = [
            {
                'node_id': 1,
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(a.x = b.y)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'a',
                'columns': [{'column_name': 'x'}],  # no data_type
            },
            {
                'schema_name': 'public',
                'table_name': 'b',
                'columns': [{'column_name': 'y', 'data_type': 'bigint'}],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert not any('mismatched numeric types' in s for s in suggestions)


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
