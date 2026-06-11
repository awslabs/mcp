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
import regex
import time
from awslabs.redshift_mcp_server.redshift import (
    RedshiftClientManager,
    RedshiftSessionManager,
    _execute_protected_statement,
    _execute_statement,
    _generate_performance_suggestions,
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
    async def test_execute_protected_statement_oversized_sql_rejected(self, mocker):
        """SQL longer than SUSPICIOUS_QUERY_MAX_LEN is rejected without invoking the regex."""
        from awslabs.redshift_mcp_server.consts import SUSPICIOUS_QUERY_MAX_LEN

        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        # Stand-in regex whose .search must not be called; the length cap should short-circuit.
        sentinel_regex = mocker.Mock()
        sentinel_regex.search.side_effect = AssertionError(
            'regex.search should not be called for oversized SQL'
        )
        mocker.patch('awslabs.redshift_mcp_server.redshift._SUSPICIOUS_QUERY_RE', sentinel_regex)

        oversized_sql = 'SELECT 1' + ' ' * (SUSPICIOUS_QUERY_MAX_LEN + 1)

        with pytest.raises(Exception, match='SQL contains suspicious pattern, execution rejected'):
            await _execute_protected_statement(
                'test-cluster', 'test-db', oversized_sql, allow_read_write=False
            )

        sentinel_regex.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_protected_statement_regex_timeout_rejected(self, mocker):
        """A regex timeout is treated as suspicious and the SQL is rejected."""
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned', 'status': 'available'}
        ]
        mock_session_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.session_manager')
        mock_session_manager.session = mocker.AsyncMock(return_value='test-session-123')

        # Stand-in regex that raises TimeoutError on search.
        timing_out_regex = mocker.Mock()
        timing_out_regex.search.side_effect = TimeoutError('timed out')
        mocker.patch('awslabs.redshift_mcp_server.redshift._SUSPICIOUS_QUERY_RE', timing_out_regex)

        with pytest.raises(Exception, match='SQL contains suspicious pattern, execution rejected'):
            await _execute_protected_statement(
                'test-cluster', 'test-db', 'SELECT 1', allow_read_write=False
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

    @pytest.mark.asyncio
    async def test_execute_protected_follows_next_token_across_pages(self, mocker):
        """Multi-page Data API results are concatenated into one Records list."""
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

        # Three Data API pages: first two carry NextToken, the third closes
        # the iteration. Records from every page must end up concatenated.
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.side_effect = [
            {
                'Records': [[{'stringValue': 'row-1'}]],
                'NextToken': 'tok-1',
                'ColumnMetadata': [],
            },
            {
                'Records': [[{'stringValue': 'row-2'}]],
                'NextToken': 'tok-2',
            },
            {
                'Records': [[{'stringValue': 'row-3'}]],
            },
        ]
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        response, query_id = await _execute_protected_statement(
            'test-cluster', 'test-db', 'SELECT * FROM big_table', allow_read_write=False
        )

        assert query_id == 'user-stmt-id'
        # All three pages' Records are present in source order.
        assert [r[0]['stringValue'] for r in response['Records']] == [
            'row-1',
            'row-2',
            'row-3',
        ]
        # Three GetStatementResult calls: initial + 2 follow-ups.
        assert mock_data_client.get_statement_result.call_count == 3
        assert mock_data_client.get_statement_result.call_args_list[1][1]['NextToken'] == 'tok-1'
        assert mock_data_client.get_statement_result.call_args_list[2][1]['NextToken'] == 'tok-2'

    @pytest.mark.asyncio
    async def test_execute_protected_single_page_does_not_call_get_result_again(self, mocker):
        """No NextToken on the first page → exactly one GetStatementResult call."""
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
        mock_data_client.get_statement_result.return_value = {
            'Records': [[{'stringValue': 'only-row'}]],
            'ColumnMetadata': [],
        }
        mock_client_manager = mocker.patch('awslabs.redshift_mcp_server.redshift.client_manager')
        mock_client_manager.redshift_data_client.return_value = mock_data_client

        response, _ = await _execute_protected_statement(
            'test-cluster', 'test-db', 'SELECT 1', allow_read_write=False
        )

        assert mock_data_client.get_statement_result.call_count == 1
        assert [r[0]['stringValue'] for r in response['Records']] == ['only-row']


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


class TestDescribeExecutionPlan:
    """Tests for ``describe_execution_plan`` and its internal pipeline.

    Covers the public tool plus every internal helper it composes:
    plan-text parser, SQL reference extractor, table metadata fetcher,
    bare-name candidate lookup, ambiguity resolver, suggestion engine,
    and the SQL constants and rendering helpers used along the way.
    """

    @pytest.mark.asyncio
    async def test_describe_execution_plan_already_has_explain(self, mocker):
        """SQL starting with EXPLAIN is rejected."""
        with pytest.raises(
            Exception,
            match='SQL already contains EXPLAIN. Please provide the query without EXPLAIN.',
        ):
            await describe_execution_plan('test-cluster', 'dev', 'EXPLAIN SELECT * FROM users')

    @pytest.mark.asyncio
    async def test_describe_execution_plan_already_has_explain_lowercase(self, mocker):
        """Lowercase 'explain' must also be rejected (case-insensitive)."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        with pytest.raises(
            Exception,
            match='SQL already contains EXPLAIN. Please provide the query without EXPLAIN.',
        ):
            await describe_execution_plan('test-cluster', 'dev', 'explain select * from users')
        mock_execute_protected.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_sql', ['', ' ', '\t', '\n', '   \n\t  '])
    async def test_describe_execution_plan_rejects_empty_sql(self, mocker, bad_sql):
        """Empty/whitespace SQL is rejected before any cluster call."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        with pytest.raises(
            Exception,
            match='SQL is required and must not be empty or whitespace.',
        ):
            await describe_execution_plan('test-cluster', 'dev', bad_sql)
        mock_execute_protected.assert_not_called()

    @pytest.mark.asyncio
    async def test_describe_execution_plan_error_handling(self, mocker):
        """Underlying execution failure propagates as a top-level error."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('EXPLAIN query failed')

        with pytest.raises(Exception, match='EXPLAIN query failed'):
            await describe_execution_plan('test-cluster', 'dev', 'SELECT * FROM invalid_table')

    @pytest.mark.asyncio
    async def test_describe_execution_plan_returns_full_response_shape(self, mocker):
        """Smoke test for the full describe_execution_plan pipeline."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Plain-EXPLAIN output (no VERBOSE syntax — no ``{ NODETYPE``
        # block, no column-0 ``:property`` lines).
        explain_response = (
            {
                'Records': [
                    [{'stringValue': 'XN Limit  (cost=0.00..0.07 rows=5 width=27)'}],
                    [
                        {
                            'stringValue': '  ->  XN Seq Scan on users  '
                            '(cost=0.00..1.00 rows=100 width=27)'
                        }
                    ],
                ]
            },
            'explain-query-id',
        )
        # Bare-candidate lookup: ``users`` resolves to a single
        # (schema, table) pair — public.users.
        candidates_response = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'users'}],
                ]
            },
            'candidates-query-id',
        )
        # Batched table-extra metadata for (public, users).
        tables_extra_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'KEY'},
                        {'longValue': 1000},
                        {'longValue': 5},
                        {'longValue': 100},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ]
                ]
            },
            'tables-extra-query-id',
        )
        # Column stats batched fetch (returns no stats — empty result).
        column_stats_response = ({'Records': []}, 'column-stats-query-id')

        # Batched columns fetch for (public, users) — single column.
        columns_by_pairs_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'longValue': 1},
                        {'stringValue': None},
                        {'stringValue': 'YES'},
                        {'stringValue': 'integer'},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'stringValue': None},
                        {'stringValue': 'lzo'},
                        {'booleanValue': False},
                        {'longValue': 0},
                        {'stringValue': None},
                        {'longValue': None},
                    ],
                ]
            },
            'columns-query-id',
        )

        mock_execute_protected.side_effect = [
            explain_response,
            candidates_response,
            tables_extra_response,
            column_stats_response,
            columns_by_pairs_response,
        ]

        result = await describe_execution_plan(
            'test-cluster', 'dev', 'SELECT * FROM users LIMIT 5'
        )

        # Query identity + timing.
        assert result['query_id'] == 'explain-query-id'
        # explained_query is the user's original SQL, unchanged.
        assert result['explained_query'] == 'SELECT * FROM users LIMIT 5'
        assert result['planning_time_ms'] >= 0

        # plan_text preserves the EXPLAIN output byte-for-byte (records
        # joined by newlines).
        assert result['plan_text'] == (
            'XN Limit  (cost=0.00..0.07 rows=5 width=27)\n'
            '  ->  XN Seq Scan on users  (cost=0.00..1.00 rows=100 width=27)'
        )

        # plan_nodes are reconstructed from operation lines
        # (root + ``->`` lines).
        assert len(result['plan_nodes']) == 2
        assert result['plan_nodes'][0]['operation'] == 'XN Limit'
        assert result['plan_nodes'][1]['operation'] == 'XN Seq Scan'
        assert result['plan_nodes'][1].get('relation_name') == 'users'

        # table_designs carries the bare reference resolved to
        # public.users with metadata + columns merged.
        assert len(result['table_designs']) == 1
        td = result['table_designs'][0]
        assert td['schema_name'] == 'public'
        assert td['table_name'] == 'users'
        assert td['redshift_diststyle'] == 'KEY'
        assert td['redshift_estimated_row_count'] == 1000
        assert len(td['columns']) == 1
        assert td['columns'][0]['column_name'] == 'id'

        # notes is a list (empty here — bare reference resolved cleanly).
        assert isinstance(result['notes'], list)

        # rule_based_suggestions is a list (carry-over).
        assert isinstance(result['rule_based_suggestions'], list)

    def test_suggestions_for_data_broadcast(self):
        """DS_BCAST_INNER on a join emits a broadcast suggestion."""
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
        """DS_DIST_INNER on a join emits a redistribution suggestion."""
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
        """Nested Loop join emits a Nested-Loop suggestion."""
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
        """EVEN-distributed tables emit a DISTKEY suggestion."""
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
        """SORTKEY suggestion emits only when seq_scans > 1000, no SORTKEY,."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 5000,
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

        assert any('5,000 sequential scans' in s and 'SORTKEY' in s for s in suggestions)

    def test_no_sortkey_suggestion_when_seq_scans_unknown(self):
        """No SORTKEY suggestion when stats_sequential_scans is unknown."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
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
        assert not any('SORTKEY' in s for s in suggestions)

    def test_no_sortkey_suggestion_when_seq_scans_zero(self):
        """No SORTKEY suggestion when stats_sequential_scans == 0."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 0,
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
        assert not any('SORTKEY' in s for s in suggestions)

    def test_suggestions_for_no_compression(self):
        """Uncompressed columns emit a compression suggestion."""
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
        """Duplicate suggestion text is deduplicated."""
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
        """Empty inputs yield an empty suggestion list."""
        suggestions = _generate_performance_suggestions([], [])
        assert suggestions == []

    def test_optimal_plan_no_suggestions(self):
        """Optimal plans produce no suggestions."""
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
        """DS_DIST_ALL_INNER on a join emits a redistribution suggestion."""
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
        """Small dimension tables emit a DISTSTYLE ALL suggestion."""
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
        """DS_DIST_INNER on a Hash Join with a real table emits a redistribution suggestion."""
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
        """Tables with many uncompressed columns emit a roll-up compression suggestion."""
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
        """High sequential scans without a SORTKEY emit a SORTKEY suggestion."""
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
        """Low-correlation non-SORTKEY columns emit a SORTKEY suggestion."""
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
        """SORTKEY columns are not flagged for low correlation."""
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
        """High-correlation columns are not flagged for low correlation."""
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
        """Very low-cardinality DISTKEY columns emit a cardinality suggestion."""
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
        """High-cardinality DISTKEY columns are not flagged."""
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
        """Mostly-NULL SORTKEY columns emit a NULL-fraction suggestion."""
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
        """SORTKEY columns with low NULL fraction are not flagged."""
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
        """Wide uncompressed variable-length columns emit a compression suggestion."""
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

    def test_join_filter_numeric_type_mismatch_flagged(self):
        """Mismatched numeric types in ``join_filter`` should flag numeric-type mismatch."""
        nodes = [
            {
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(orders.id = customers.id)',
                'join_filter': '(orders.cust_id = customers.cust_id_big)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'columns': [
                    {'column_name': 'id', 'data_type': 'integer'},
                    {'column_name': 'cust_id', 'data_type': 'integer'},
                ],
            },
            {
                'schema_name': 'public',
                'table_name': 'customers',
                'columns': [
                    {'column_name': 'id', 'data_type': 'integer'},
                    {'column_name': 'cust_id_big', 'data_type': 'bigint'},
                ],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert any(
            'mismatched numeric types' in s and 'cust_id' in s and 'cust_id_big' in s
            for s in suggestions
        )

    def test_join_filter_range_predicate_not_flagged(self):
        """Range predicate in ``join_filter`` should NOT be flagged."""
        nodes = [
            {
                'operation': 'Hash Join',
                'distribution_type': 'DS_DIST_NONE',
                'join_condition': '(orders.id = customers.id)',
                'join_filter': '(orders.amount > customers.threshold)',
            }
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'columns': [
                    {'column_name': 'id', 'data_type': 'integer'},
                    {'column_name': 'amount', 'data_type': 'integer'},
                ],
            },
            {
                'schema_name': 'public',
                'table_name': 'customers',
                'columns': [
                    {'column_name': 'id', 'data_type': 'integer'},
                    {'column_name': 'threshold', 'data_type': 'bigint'},
                ],
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, table_designs)
        assert not any('mismatched numeric types' in s for s in suggestions)

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

    @pytest.mark.asyncio
    async def test_mixed_categories_returns_full_response_shape(self, mocker):
        """SQL mixing every reference category yields the full response shape."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Call 1: plain EXPLAIN. Two operation lines (root + ``->``)
        # produce two ``plan_nodes`` entries.
        explain_response = (
            {
                'Records': [
                    [
                        {
                            'stringValue': 'XN Hash Join DS_DIST_NONE  '
                            '(cost=10.00..50.00 rows=200 width=64)'
                        }
                    ],
                    [
                        {
                            'stringValue': '  ->  XN Seq Scan on users  '
                            '(cost=0.00..10.00 rows=1000 width=27)'
                        }
                    ],
                ]
            },
            'explain-query-id',
        )

        # Call 2: BARE_TABLE_CANDIDATES_SQL.
        candidates_response = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'orders'}],
                    [{'stringValue': 'public'}, {'stringValue': 'users'}],
                    [{'stringValue': 'tpch'}, {'stringValue': 'orders'}],
                ]
            },
            'candidates-query-id',
        )

        # Call 3: TABLES_EXTRA_BY_PAIRS_SQL — batched metadata for the resolved pair set.
        tables_extra_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'orders'},
                        {'stringValue': 'KEY'},
                        {'longValue': 5_000_000},
                        {'longValue': 5000},
                        {'longValue': 1_000_000},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ],
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'KEY'},
                        {'longValue': 1000},
                        {'longValue': 5},
                        {'longValue': 100},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ],
                    [
                        {'stringValue': 'tpch'},
                        {'stringValue': 'orders'},
                        {'stringValue': 'KEY'},
                        {'longValue': 2_000_000},
                        {'longValue': 50},
                        {'longValue': 500_000},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ],
                ]
            },
            'tables-extra-query-id',
        )

        # Call 4: COLUMN_STATS_SQL. Empty result is fine for the
        # integration assertions; ``test_smoke`` already covers
        # column-stats merging.
        column_stats_response = ({'Records': []}, 'column-stats-query-id')

        # Call 5: COLUMNS_BY_PAIRS_SQL — batched columns for all three
        # resolved pairs. Each row has the 17 fields the helper unpacks.
        def _columns_row(schema: str, table: str) -> list[dict]:
            return [
                {'stringValue': 'dev'},
                {'stringValue': schema},
                {'stringValue': table},
                {'stringValue': f'{table}_id'},
                {'longValue': 1},
                {'stringValue': None},
                {'stringValue': 'YES'},
                {'stringValue': 'integer'},
                {'longValue': None},
                {'longValue': None},
                {'longValue': None},
                {'stringValue': None},
                {'stringValue': 'lzo'},
                {'booleanValue': False},
                {'longValue': 0},
                {'stringValue': None},
                {'longValue': None},
            ]

        columns_by_pairs_response = (
            {
                'Records': [
                    _columns_row('public', 'orders'),
                    _columns_row('public', 'users'),
                    _columns_row('tpch', 'orders'),
                ]
            },
            'columns-query-id',
        )

        mock_execute_protected.side_effect = [
            explain_response,
            candidates_response,
            tables_extra_response,
            column_stats_response,
            columns_by_pairs_response,
        ]

        sql = (
            'SELECT u.id FROM tpch.orders o '
            'JOIN users u ON u.id = o.user_id '
            'JOIN orders o2 ON o2.id = o.parent_id '
            'JOIN prod_db.tpch.line_items li ON li.order_id = o.id'
        )

        result = await describe_execution_plan('test-cluster', 'dev', sql)

        # ----- Plan path assertions -----
        assert result['query_id'] == 'explain-query-id'
        assert result['explained_query'] == sql
        assert result['planning_time_ms'] >= 0
        assert result['plan_text'] == (
            'XN Hash Join DS_DIST_NONE  (cost=10.00..50.00 rows=200 width=64)\n'
            '  ->  XN Seq Scan on users  (cost=0.00..10.00 rows=1000 width=27)'
        )
        assert len(result['plan_nodes']) == 2
        assert result['plan_nodes'][0]['operation'] == 'XN Hash Join DS_DIST_NONE'
        assert result['plan_nodes'][1]['operation'] == 'XN Seq Scan'
        assert result['plan_nodes'][1].get('relation_name') == 'users'

        # ----- Notes: exactly one cross-database + one ambiguity -----
        notes = result['notes']
        assert isinstance(notes, list)
        cross_db_notes = [n for n in notes if 'cross-database' in n]
        ambiguity_notes = [n for n in notes if 'ambiguous' in n]
        not_found_notes = [n for n in notes if 'was not found' in n]

        assert len(cross_db_notes) == 1, f'expected exactly one cross-database note; got {notes!r}'
        assert 'prod_db.tpch.line_items' in cross_db_notes[0]
        assert '"dev"' in cross_db_notes[0]
        assert len(ambiguity_notes) == 1, f'expected exactly one ambiguity note; got {notes!r}'
        assert 'orders' in ambiguity_notes[0]
        # Both schemas should be named in the ambiguity note.
        assert 'public' in ambiguity_notes[0]
        assert 'tpch' in ambiguity_notes[0]
        assert not_found_notes == [], f'no reference should be not-found here; got {notes!r}'

        # ----- table_designs -----
        # Three pairs: (public, orders), (public, users), (tpch, orders).
        # The cross-database reference is absent.
        designs = result['table_designs']
        pair_set = {(td['schema_name'], td['table_name']) for td in designs}
        assert pair_set == {
            ('public', 'orders'),
            ('public', 'users'),
            ('tpch', 'orders'),
        }
        # No design entry for the cross-database table.
        assert not any(td['table_name'] == 'line_items' for td in designs)

        # Metadata merged from TABLES_EXTRA_BY_PAIRS_SQL.
        public_users = next(
            td for td in designs if td['schema_name'] == 'public' and td['table_name'] == 'users'
        )
        assert public_users['redshift_diststyle'] == 'KEY'
        assert public_users['redshift_estimated_row_count'] == 1000
        assert len(public_users['columns']) == 1
        assert public_users['columns'][0]['column_name'] == 'users_id'

        # ----- rule_based_suggestions ----- ``public.orders`` has 1M sequential scans, no SORTKEY, 5M estimated rows, KEY diststyle — every condition for the SORTKEY emission rule is met.
        assert isinstance(result['rule_based_suggestions'], list)
        sortkey_suggestions = [
            s
            for s in result['rule_based_suggestions']
            if 'SORTKEY' in s and 'sequential scans' in s
        ]
        assert any('public.orders' in s for s in sortkey_suggestions), (
            f'expected a SORTKEY suggestion for public.orders; '
            f'got {result["rule_based_suggestions"]!r}'
        )

        # ----- Call-count audit: cross-database reference triggers no
        # additional metadata fetch. Five protected statements run:
        # EXPLAIN, BARE_TABLE_CANDIDATES_SQL, TABLES_EXTRA_BY_PAIRS_SQL,
        # COLUMN_STATS_SQL, and COLUMNS_BY_PAIRS_SQL.
        assert mock_execute_protected.call_count == 5

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'sql',
        [
            'EXPLAIN SELECT * FROM users',
            'explain SELECT * FROM users',
            'Explain SELECT * FROM users',
            'eXpLaIn SELECT * FROM users',
            '   EXPLAIN SELECT 1',
            '\tEXPLAIN SELECT 1',
        ],
    )
    async def test_explain_prefixed_sql_rejected_no_statement_executed(self, mocker, sql):
        """SQL prefixed with ``EXPLAIN`` (case-insensitive) raises and runs no statement."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )

        with pytest.raises(
            Exception,
            match='SQL already contains EXPLAIN. Please provide the query without EXPLAIN.',
        ):
            await describe_execution_plan('test-cluster', 'dev', sql)

        mock_execute_protected.assert_not_called()
        mock_discover_columns.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'sql',
        ['', ' ', '   ', '\t', '\n', '\r\n', '   \n\t  '],
    )
    async def test_empty_or_whitespace_sql_rejected_no_statement_executed(self, mocker, sql):
        """Empty / whitespace-only SQL raises and runs no statement."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )

        with pytest.raises(
            Exception,
            match='SQL is required and must not be empty or whitespace.',
        ):
            await describe_execution_plan('test-cluster', 'dev', sql)

        mock_execute_protected.assert_not_called()
        mock_discover_columns.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_explain_output_returns_empty_plan_text_and_nodes(self, mocker):
        """Empty ``EXPLAIN`` output → response with empty plan_text and plan_nodes."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        # Empty EXPLAIN output.
        empty_explain_response = ({'Records': []}, 'empty-explain-query-id')
        mock_execute_protected.side_effect = [empty_explain_response]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT 1')

        assert result['plan_text'] == ''
        assert result['plan_nodes'] == []
        assert result['query_id'] == 'empty-explain-query-id'
        assert result['explained_query'] == 'SELECT 1'
        # No tables → no table_designs and no metadata fetch.
        assert result['table_designs'] == []
        # No reference → no ambiguity / not-found / cross-db notes.
        assert result['notes'] == []
        # Carry-over rule-based suggestions are still a list (empty).
        assert isinstance(result['rule_based_suggestions'], list)

        # Only the ``EXPLAIN`` ran. No bare references → no candidates
        # call. No resolved pairs → no tables_extra call and no
        # column_stats call.
        assert mock_execute_protected.call_count == 1
        mock_discover_columns.assert_not_called()

    @pytest.mark.asyncio
    async def test_cross_database_reference_emits_note_skips_metadata_fetch(self, mocker):
        """Database-qualified ref to a different DB emits a note, no metadata fetch."""
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        explain_response = (
            {
                'Records': [
                    [
                        {
                            'stringValue': 'XN Seq Scan on line_items  '
                            '(cost=0.00..1.00 rows=10 width=8)'
                        }
                    ],
                ]
            },
            'cross-db-explain-query-id',
        )
        mock_execute_protected.side_effect = [explain_response]

        mock_discover_columns = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_columns'
        )

        sql = 'SELECT id FROM prod_db.tpch.line_items'
        result = await describe_execution_plan('test-cluster', 'dev', sql)

        # ----- Notes: exactly one cross-database note -----
        notes = result['notes']
        cross_db_notes = [n for n in notes if 'cross-database' in n]
        assert len(cross_db_notes) == 1
        assert 'prod_db.tpch.line_items' in cross_db_notes[0]
        assert '"dev"' in cross_db_notes[0]

        # ----- No metadata fetched for the cross-database reference -----
        assert result['table_designs'] == []

        # ----- Call-count audit: only the EXPLAIN ran.
        assert mock_execute_protected.call_count == 1
        mock_discover_columns.assert_not_called()

        # Plan path still works.
        assert (
            result['plan_text'] == 'XN Seq Scan on line_items  (cost=0.00..1.00 rows=10 width=8)'
        )
        assert len(result['plan_nodes']) == 1

    def test_tables_extra_by_pairs_sql_constant_is_importable_and_non_empty(self):
        """The constant must be importable and contain SQL text."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL

        assert isinstance(TABLES_EXTRA_BY_PAIRS_SQL, str)
        assert TABLES_EXTRA_BY_PAIRS_SQL.strip() != ''

    def test_format_with_schema_table_pairs_renders_without_keyerror(self):
        """Formatting with ``schema_table_pairs`` must not raise ``KeyError``."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL

        rendered = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        assert isinstance(rendered, str)
        assert rendered.strip() != ''

    def test_tables_extra_by_pairs_sql_format_leaves_no_unfilled_placeholders(self):
        """The rendered SQL must have no leftover ``{...}`` placeholders."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL

        rendered = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        # No bare format placeholders like {foo} should remain. This is a
        # broader check than a specific name lookup so any future stray
        # placeholder is also caught.
        leftovers = regex.findall(r'\{[^{}]*\}', rendered)
        assert leftovers == [], f'Rendered SQL still contains unfilled placeholders: {leftovers!r}'

    def test_format_substitutes_pair_list_into_query(self):
        """The rendered text must contain the substituted pair-list literal."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL

        rendered = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        assert "('s','t')" in rendered

    def test_rendered_sql_looks_like_a_select_statement(self):
        """The rendered SQL must look like a real SELECT against catalog tables."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL

        rendered = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")
        upper = rendered.upper()

        assert 'SELECT' in upper
        assert 'FROM' in upper
        assert 'IN' in upper

    def test_columns_by_pairs_sql_constant_is_importable_and_non_empty(self):
        """The constant must be importable and contain SQL text."""
        from awslabs.redshift_mcp_server.consts import COLUMNS_BY_PAIRS_SQL

        assert isinstance(COLUMNS_BY_PAIRS_SQL, str)
        assert COLUMNS_BY_PAIRS_SQL.strip() != ''

    def test_columns_by_pairs_sql_format_renders_without_keyerror(self):
        """Formatting with ``schema_table_pairs`` must not raise ``KeyError``."""
        from awslabs.redshift_mcp_server.consts import COLUMNS_BY_PAIRS_SQL

        rendered = COLUMNS_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        assert isinstance(rendered, str)
        assert rendered.strip() != ''

    def test_columns_by_pairs_sql_format_leaves_no_unfilled_placeholders(self):
        """The rendered SQL must have no leftover ``{...}`` placeholders."""
        from awslabs.redshift_mcp_server.consts import COLUMNS_BY_PAIRS_SQL

        rendered = COLUMNS_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        leftovers = regex.findall(r'\{[^{}]*\}', rendered)
        assert leftovers == [], f'Rendered SQL still contains unfilled placeholders: {leftovers!r}'

    def test_columns_by_pairs_sql_substitutes_pair_list_into_query(self):
        """The rendered text must contain the substituted pair-list literal."""
        from awslabs.redshift_mcp_server.consts import COLUMNS_BY_PAIRS_SQL

        rendered = COLUMNS_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")

        # Both UNION branches reference the same {schema_table_pairs}
        # slot, so the rendered literal appears in both.
        assert rendered.count("('s','t')") >= 2

    def test_columns_by_pairs_sql_unions_internal_and_external_columns(self):
        """The rendered SQL must UNION both column views."""
        from awslabs.redshift_mcp_server.consts import COLUMNS_BY_PAIRS_SQL

        rendered = COLUMNS_BY_PAIRS_SQL.format(schema_table_pairs="('s','t')")
        upper = rendered.upper()

        assert 'SVV_REDSHIFT_COLUMNS' in upper
        assert 'SVV_EXTERNAL_COLUMNS' in upper
        assert 'UNION ALL' in upper

    def test_one_node_per_operation_line(self):
        """A 3-operation-line plan produces exactly 3 nodes."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join DS_BCAST_INNER  (cost=0.00..1.00 rows=1 width=8)',
            '  Hash Cond: (a.id = b.id)',
            '  ->  Seq Scan on a  (cost=0.00..1.00 rows=1 width=8)',
            '        Filter: (x > 0)',
            '  ->  Seq Scan on b  (cost=0.00..1.00 rows=1 width=8)',
        ]

        result = _parse_plan_text(records)

        # Three operation lines (root + two ``->``) → three nodes.
        assert len(result) == 3

    def test_detail_lines_attach_to_most_recent_operation_node(self):
        """Hash Cond / Filter / Sort Key / Merge Key land on the right node."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Merge Join  (cost=0.00..1.00 rows=1 width=8)',
            '  Merge Cond: (a.id = b.id)',
            '  Sort Key: a.id',
            '  ->  Seq Scan on a  (cost=0.00..1.00 rows=1 width=8)',
            '        Filter: (a.x > 0)',
            '  ->  Seq Scan on b  (cost=0.00..1.00 rows=1 width=8)',
            '        Merge Key: b.id',
        ]

        result = _parse_plan_text(records)

        # Three operation nodes in document order (Merge Join, Seq Scan a,
        # Seq Scan b). Each detail line attached to the most recently
        # seen operation node.
        assert len(result) == 3
        merge_join, scan_a, scan_b = result

        # ``Merge Cond:`` maps to ``join_condition``; attached
        # to the Merge Join node.
        assert merge_join.join_condition == '(a.id = b.id)'
        # ``Sort Key:`` also attached to the Merge Join.
        assert merge_join.sort_key == 'a.id'

        # ``Filter:`` attached to the first Seq Scan (most
        # recent operation node when the detail line was seen).
        assert scan_a.filter_condition == '(a.x > 0)'
        assert scan_a.join_condition is None
        assert scan_a.sort_key is None

        # ``Merge Key:`` attached to the second Seq Scan.
        assert scan_b.merge_key == 'b.id'
        assert scan_b.filter_condition is None

    def test_operation_name_with_cost_and_relation_segments_dropped(self):
        """``Seq Scan on users (cost=...)`` → ``operation == 'Seq Scan'``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['Seq Scan on users  (cost=0.00..1.00 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].operation == 'Seq Scan'

    def test_operation_name_without_cost_block(self):
        """``XN Aggregate`` (no ``(cost=...)``) → ``operation == 'XN Aggregate'``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        result = _parse_plan_text(['XN Aggregate'])

        assert result[0].operation == 'XN Aggregate'
        # No cost block → all four cost fields unset.
        node = result[0]
        assert node.cost_startup is None
        assert node.cost_total is None
        assert node.rows is None
        assert node.width is None

    def test_operation_name_with_arrow_prefix_is_stripped(self):
        """A leading ``->`` is stripped from the extracted operation name."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN root  (cost=0.00..1.00 rows=1 width=8)',
            '  ->  XN Hash Join DS_BCAST_INNER  (cost=0..1 rows=1 width=8)',
        ]

        result = _parse_plan_text(records)

        # The arrow line is the second operation node; the ``->`` is gone from ``operation`` and the ``DS_*`` token is preserved in the operation text (the distribution_type field is also populated separately).
        assert result[1].operation == 'XN Hash Join DS_BCAST_INNER'

    def test_relation_and_alias_extraction_seq_scan(self):
        """``Seq Scan on users u`` → ``relation_name == 'users'``, ``alias == 'u'``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['Seq Scan on users u  (cost=0.00..1.00 rows=1 width=8)']

        result = _parse_plan_text(records)
        node = result[0]

        assert node.relation_name == 'users'
        assert node.alias == 'u'

    def test_relation_extraction_without_alias(self):
        """``Seq Scan on users (cost=...)`` → relation set, alias ``None``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['Seq Scan on users  (cost=0.00..1.00 rows=1 width=8)']

        result = _parse_plan_text(records)
        node = result[0]

        assert node.relation_name == 'users'
        assert node.alias is None

    def test_relation_extraction_index_scan_backward(self):
        """``Index Scan Backward on orders`` → ``relation_name == 'orders'``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['Index Scan Backward on orders  (cost=0.00..1.00 rows=1 width=8)']

        result = _parse_plan_text(records)
        node = result[0]

        assert node.relation_name == 'orders'

    def test_cost_block_extraction(self):
        """Cost block populates startup/total floats and rows/width ints."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['Hash Join  (cost=12.34..56.78 rows=100 width=64)']

        result = _parse_plan_text(records)
        node = result[0]

        assert node.cost_startup == 12.34
        assert node.cost_total == 56.78
        assert node.rows == 100
        assert node.width == 64
        # Cost fields are numeric, not strings.
        assert isinstance(node.cost_startup, float)
        assert isinstance(node.cost_total, float)
        assert isinstance(node.rows, int)
        assert isinstance(node.width, int)

    def test_cost_block_absent_leaves_all_four_fields_unset(self):
        """An operation line without ``cost=...`` leaves all cost fields ``None``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        # No cost block on this operation line.
        result = _parse_plan_text(['Sort'])
        node = result[0]

        assert node.cost_startup is None
        assert node.cost_total is None
        assert node.rows is None
        assert node.width is None

    def test_distribution_type_extraction_bcast_inner(self):
        """``DS_BCAST_INNER`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_BCAST_INNER  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_BCAST_INNER'

    def test_distribution_type_extraction_dist_inner(self):
        """``DS_DIST_INNER`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_DIST_INNER  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_DIST_INNER'

    def test_distribution_type_extraction_dist_all_inner(self):
        """``DS_DIST_ALL_INNER`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_DIST_ALL_INNER  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_DIST_ALL_INNER'

    def test_distribution_type_extraction_dist_none(self):
        """``DS_DIST_NONE`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_DIST_NONE  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_DIST_NONE'

    def test_distribution_type_extraction_dist_all_none(self):
        """``DS_DIST_ALL_NONE`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_DIST_ALL_NONE  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_DIST_ALL_NONE'

    def test_distribution_type_extraction_dist_outer(self):
        """``DS_DIST_OUTER`` token populates ``distribution_type``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join DS_DIST_OUTER  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type == 'DS_DIST_OUTER'

    def test_distribution_type_absent_leaves_field_unset(self):
        """A line without any ``DS_*`` token leaves ``distribution_type`` ``None``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = ['XN Hash Join  (cost=0..1 rows=1 width=8)']

        result = _parse_plan_text(records)

        assert result[0].distribution_type is None

    def test_detail_line_hash_cond_maps_to_join_condition(self):
        """``Hash Cond:`` populates ``join_condition``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join  (cost=0..1 rows=1 width=8)',
            '  Hash Cond: (a.id = b.id)',
        ]

        result = _parse_plan_text(records)

        assert result[0].join_condition == '(a.id = b.id)'

    def test_detail_line_merge_cond_maps_to_join_condition(self):
        """``Merge Cond:`` populates ``join_condition``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Merge Join  (cost=0..1 rows=1 width=8)',
            '  Merge Cond: (a.id = b.id)',
        ]

        result = _parse_plan_text(records)

        assert result[0].join_condition == '(a.id = b.id)'

    def test_detail_line_join_filter_maps_to_join_filter(self):
        """``Join Filter:`` populates ``join_filter``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join  (cost=0..1 rows=1 width=8)',
            '  Join Filter: (a.x > b.x)',
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.join_filter == '(a.x > b.x)'
        assert node.join_condition is None
        assert node.filter_condition is None

    def test_detail_line_hash_cond_and_join_filter_coexist_on_hash_join(self):
        """``Hash Cond:`` and ``Join Filter:`` populate distinct fields on the same node."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join  (cost=0..1 rows=1 width=8)',
            '  Hash Cond: (a.id = b.id)',
            "  Join Filter: (a.name ~~ 'foo%'::text)",
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.join_condition == '(a.id = b.id)'
        assert node.join_filter == "(a.name ~~ 'foo%'::text)"

    def test_detail_line_merge_cond_and_join_filter_coexist_on_merge_join(self):
        """``Merge Cond:`` and ``Join Filter:`` populate distinct fields on the same node."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Merge Join  (cost=0..1 rows=1 width=8)',
            '  Merge Cond: (a.id = b.id)',
            '  Join Filter: (a.x > b.x)',
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.join_condition == '(a.id = b.id)'
        assert node.join_filter == '(a.x > b.x)'

    def test_detail_line_filter_maps_to_filter_condition(self):
        """``Filter:`` populates ``filter_condition``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'Seq Scan on users  (cost=0..1 rows=1 width=8)',
            '  Filter: (id > 0)',
        ]

        result = _parse_plan_text(records)

        assert result[0].filter_condition == '(id > 0)'

    def test_detail_line_sort_key_maps_to_sort_key(self):
        """``Sort Key:`` populates ``sort_key``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Sort  (cost=0..1 rows=1 width=8)',
            '  Sort Key: orders.o_orderkey',
        ]

        result = _parse_plan_text(records)

        assert result[0].sort_key == 'orders.o_orderkey'

    def test_detail_line_merge_key_maps_to_merge_key(self):
        """``Merge Key:`` populates ``merge_key``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Merge  (cost=0..1 rows=1 width=8)',
            '  Merge Key: orders.o_orderkey',
        ]

        result = _parse_plan_text(records)

        assert result[0].merge_key == 'orders.o_orderkey'

    @pytest.mark.parametrize(
        'detail_text',
        [
            'Send to leader',
            'Send to slice 0',
            'Distribute',
            'Broadcast',
            'Distribute Round Robin',
        ],
    )
    def test_detail_line_data_movement_populates_data_movement(self, detail_text):
        """Label-less Network detail line populates ``data_movement``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Limit  (cost=0..1 rows=1 width=8)',
            '  ->  XN Network  (cost=0..1 rows=1 width=8)',
            f'        {detail_text}',
        ]

        result = _parse_plan_text(records)
        network_node = next(n for n in result if n.operation == 'XN Network')

        assert network_node.data_movement == detail_text

    def test_unrecognized_detail_line_does_not_populate_data_movement(self):
        """Unknown label-less detail lines leave ``data_movement`` as None."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Network  (cost=0..1 rows=1 width=8)',
            '  Some Unknown Annotation',
        ]

        result = _parse_plan_text(records)

        assert result[0].data_movement is None

    def test_detail_line_index_cond_maps_to_index_condition(self):
        """``Index Cond:`` populates ``index_condition``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Index Scan using pg_class_oid_index on pg_class  (cost=0..1 rows=1 width=8)',
            '  Index Cond: (oid > 1000::oid)',
        ]

        result = _parse_plan_text(records)

        assert result[0].index_condition == '(oid > 1000::oid)'

    def test_detail_line_inner_dist_key_maps_to_inner_dist_key(self):
        """``Inner Dist Key:`` populates ``inner_dist_key``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join DS_DIST_INNER  (cost=0..1 rows=1 width=8)',
            '  Inner Dist Key: s.eventid',
            '  Hash Cond: ("outer".eventid = "inner".eventid)',
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.inner_dist_key == 's.eventid'
        # Ensure existing labels still work alongside the new one.
        assert node.join_condition == '("outer".eventid = "inner".eventid)'

    def test_detail_line_partition_and_order_populate_window_fields(self):
        """``Partition:`` and ``Order:`` populate window-function fields."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Window  (cost=0..1 rows=1 width=8)',
            '  Partition: v.venuestate',
            '  Order: sum(s.pricepaid)',
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.partition_key == 'v.venuestate'
        assert node.order_key == 'sum(s.pricepaid)'

    def test_detail_line_outer_dist_key_maps_to_outer_dist_key(self):
        """``Outer Dist Key:`` populates ``outer_dist_key``."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join DS_DIST_BOTH  (cost=0..1 rows=1 width=8)',
            '  Outer Dist Key: s1.buyerid',
            '  Inner Dist Key: s2.sellerid',
            '  Hash Cond: ("outer".buyerid = "inner".sellerid)',
        ]

        result = _parse_plan_text(records)
        node = result[0]

        assert node.outer_dist_key == 's1.buyerid'
        # Both dist-key labels coexist on a DS_DIST_BOTH node.
        assert node.inner_dist_key == 's2.sellerid'
        assert node.join_condition == '("outer".buyerid = "inner".sellerid)'

    def test_detail_line_grouping_sets_populates_agg_strategy(self):
        """``GROUPING SETS(...)`` populates ``agg_strategy`` verbatim."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN HashAggregate  (cost=0..1 rows=1 width=8)',
            '  GROUPING SETS((a),(b),(a,b))',
        ]

        result = _parse_plan_text(records)

        assert result[0].agg_strategy == 'GROUPING SETS((a),(b),(a,b))'

    def test_document_order_preserved_across_operation_lines(self):
        """Operation lines appear in ``plan_nodes`` in their document order."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Hash Join  (cost=0..10 rows=1 width=8)',
            '  Hash Cond: (a.id = b.id)',
            '  ->  XN Seq Scan on a  (cost=0..1 rows=1 width=8)',
            '  ->  XN Hash  (cost=0..5 rows=1 width=8)',
            '    ->  XN Seq Scan on b  (cost=0..2 rows=1 width=8)',
        ]

        result = _parse_plan_text(records)

        # Operations appear in the same order as their operation lines
        # in the input records.
        assert [n.operation for n in result] == [
            'XN Hash Join',
            'XN Seq Scan',
            'XN Hash',
            'XN Seq Scan',
        ]
        # The two Seq Scan nodes are distinguished by their relation
        # name in document order: ``a`` before ``b``.
        scan_relations = [n.relation_name for n in result if n.operation == 'XN Seq Scan']
        assert scan_relations == ['a', 'b']

    def test_tree_structure_derivable_from_level_and_position(self):
        """Three-level plan: ``[node.level for node in plan_nodes]`` matches expected."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        # Indent: 0, 2, 2, 4 → levels 0, 1, 1, 2.
        records = [
            'XN Hash Join  (cost=0..10 rows=1 width=8)',
            '  ->  XN Seq Scan on a  (cost=0..1 rows=1 width=8)',
            '  ->  XN Hash  (cost=0..5 rows=1 width=8)',
            '    ->  XN Seq Scan on b  (cost=0..2 rows=1 width=8)',
        ]

        result = _parse_plan_text(records)

        assert [n.level for n in result] == [0, 1, 1, 2]
        # Sanity: the deepest node's parent (per the level rule) is the most recent preceding node at level 1, which is the ``XN Hash`` node at index 2 — confirming tree structure is derivable from ``level`` + position.
        assert result[2].operation == 'XN Hash'
        assert result[3].level == 2

    def test_level_skip_does_not_drop_plan_nodes(self):
        """Operation lines at any indent depth all produce nodes via the stack rule."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        # Root at indent 0, then a line indented 6 spaces — under the old rule this would have been level 3 (a forbidden skip).
        records = ['root', '      ->  child']

        result = _parse_plan_text(records)

        assert [n.level for n in result] == [0, 1]
        assert len(result) == 2

    def test_real_redshift_six_space_per_level_indentation(self):
        """Real Redshift output with 2/8/14/20/..."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        records = [
            'XN Limit  (cost=0.00..0.00 rows=1 width=8)',
            '  ->  XN Merge  (cost=0.00..0.00 rows=1 width=8)',
            '        Merge Key: sum(s.pricepaid)',
            '        ->  XN Network  (cost=0.00..0.00 rows=1 width=8)',
            '              Send to leader',
            '              ->  XN Sort  (cost=0.00..0.00 rows=1 width=8)',
            '                    Sort Key: sum(s.pricepaid)',
            '                    ->  XN HashAggregate  (cost=0.00..0.00 rows=1 width=8)',
            '                          ->  XN Hash Join DS_BCAST_INNER  (cost=0.00..0.00 rows=1 width=8)',
            '                                Hash Cond: ("outer".buyerid = "inner".userid)',
            '                                ->  XN Seq Scan on sales s  (cost=0.00..0.00 rows=1 width=8)',
            '                                ->  XN Hash  (cost=0.00..0.00 rows=1 width=8)',
            '                                      ->  XN Seq Scan on users u  (cost=0.00..0.00 rows=1 width=8)',
        ]

        result = _parse_plan_text(records)

        # All 9 operation lines (root + 8 arrow lines) produce nodes
        # with contiguous levels.
        assert len(result) == 9
        assert [n.level for n in result] == [0, 1, 2, 3, 4, 5, 6, 6, 7]

    @pytest.mark.parametrize(
        'raw_records',
        [
            pytest.param([], id='empty'),
            pytest.param(
                ['XN Limit  (cost=0.00..0.07 rows=5 width=27)'],
                id='root_only',
            ),
            pytest.param(
                [
                    'XN Hash Join DS_BCAST_INNER  (cost=10.00..50.00 rows=200 width=64)',
                    '  ->  XN Seq Scan on users  (cost=0.00..10.00 rows=1000 width=27)',
                    '        Hash Cond: (a.id = b.id)',
                    '',
                    '  ->  XN Seq Scan on orders o  (cost=0.00..5.00 rows=500 width=37)',
                    '        Filter: (id > 0)',
                ],
                id='join_with_detail_and_blank_lines',
            ),
        ],
    )
    def test_parse_is_idempotent(self, raw_records):
        """Parsing the same records twice yields equal node lists."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        first = _parse_plan_text(raw_records)
        second = _parse_plan_text(raw_records)

        assert first == second

    @pytest.mark.parametrize(
        'raw_records,expected_count',
        [
            pytest.param([], 0, id='empty'),
            pytest.param(['root  (cost=0..1 rows=1 width=8)'], 1, id='root_only'),
            pytest.param(
                [
                    'root  (cost=0..1 rows=1 width=8)',
                    '  ->  child  (cost=0..1 rows=1 width=8)',
                ],
                2,
                id='root_plus_one_arrow',
            ),
            pytest.param(
                [
                    'root  (cost=0..1 rows=1 width=8)',
                    '  ->  Hash Join  (cost=0..1 rows=1 width=8)',
                    '        Hash Cond: (a.id = b.id)',
                    '        Filter: (a.x > 0)',
                ],
                2,
                id='detail_lines_do_not_count',
            ),
            pytest.param(
                [
                    'root  (cost=0..1 rows=1 width=8)',
                    '',
                    '   ',
                    '  ->  child  (cost=0..1 rows=1 width=8)',
                ],
                2,
                id='blank_and_whitespace_lines_do_not_count',
            ),
            pytest.param(
                [
                    'root  (cost=0..1 rows=1 width=8)',
                    '  ->  child1  (cost=0..1 rows=1 width=8)',
                    '        ->  grandchild  (cost=0..1 rows=1 width=8)',
                    '  ->  child2  (cost=0..1 rows=1 width=8)',
                ],
                4,
                id='nested_arrow_levels',
            ),
        ],
    )
    def test_node_count_matches_operation_line_count(self, raw_records, expected_count):
        """``len(plan_nodes)`` equals the count of operation lines."""
        from awslabs.redshift_mcp_server.redshift import _parse_plan_text

        nodes = _parse_plan_text(raw_records)

        assert len(nodes) == expected_count

    def test_emits_identifier_token_for_unquoted_word(self):
        """An unquoted regular identifier emits a single ``'identifier'``."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('orders')

        assert tokens == [type(tokens[0])(kind='identifier', value='orders')]

    def test_preserves_identifier_case_for_unquoted(self):
        """Unquoted identifier case is preserved as written."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('Orders')

        assert tokens[0].value == 'Orders'

    def test_keywords_recognized_case_insensitively(self):
        """``from``, ``From``, ``FROM`` all emit a ``'keyword'`` ``'FROM'``."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        for sql in ('from', 'From', 'FROM', 'fRoM'):
            tokens = _tokenize_sql(sql)
            assert len(tokens) == 1
            assert tokens[0].kind == 'keyword'
            assert tokens[0].value == 'FROM'

    def test_all_four_recognized_keywords(self):
        """``WITH``, ``AS``, ``FROM``, ``JOIN`` all emit keyword tokens."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('with as from join')
        kinds = [t.kind for t in tokens]
        values = [t.value for t in tokens]

        assert kinds == ['keyword'] * 4
        assert values == ['WITH', 'AS', 'FROM', 'JOIN']

    def test_select_is_not_a_recognized_keyword(self):
        """``SELECT`` is NOT in the recognized-keyword set; emits identifier."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('SELECT')

        # Only ``WITH``, ``AS``, ``FROM``, ``JOIN`` are tokenized as keywords.
        assert len(tokens) == 1
        assert tokens[0].kind == 'identifier'
        assert tokens[0].value == 'SELECT'

    def test_dot_emits_dot_token(self):
        """The ``.`` separator emits a ``'dot'`` token (kind != ``'punctuation'``)."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a.b')

        assert [t.kind for t in tokens] == ['identifier', 'dot', 'identifier']
        assert [t.value for t in tokens] == ['a', '.', 'b']

    def test_dotted_identifier_sequence_three_parts(self):
        """``db.schema.table`` produces alternating identifier/dot tokens."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('prod_db.tpch.orders')

        assert [t.kind for t in tokens] == [
            'identifier',
            'dot',
            'identifier',
            'dot',
            'identifier',
        ]
        assert [t.value for t in tokens] == ['prod_db', '.', 'tpch', '.', 'orders']

    def test_grouping_punctuation_emits_punctuation_tokens(self):
        """``(``, ``)``, ``,``, ``;`` each emit a ``'punctuation'`` token."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('(),;')

        assert [t.kind for t in tokens] == ['punctuation'] * 4
        assert [t.value for t in tokens] == ['(', ')', ',', ';']

    def test_whitespace_is_consumed_and_not_emitted(self):
        """Spaces, tabs, and newlines emit no tokens."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a   b\tc\nd')

        assert [t.value for t in tokens] == ['a', 'b', 'c', 'd']
        assert all(t.kind == 'identifier' for t in tokens)

    def test_empty_string_produces_no_tokens(self):
        """An empty SQL string produces an empty token list."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        assert _tokenize_sql('') == []

    def test_identifier_with_dollar_and_digits(self):
        """An identifier may contain ``$`` and digits after the first char."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('table_1$ extra2')

        assert [t.value for t in tokens] == ['table_1$', 'extra2']
        assert all(t.kind == 'identifier' for t in tokens)

    def test_identifier_cannot_start_with_digit(self):
        """An identifier cannot start with a digit; the digit is silently skipped."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        # ``9foo`` — the leading digit is not in the start-char set, so
        # the scanner skips it; ``foo`` then begins a fresh identifier.
        tokens = _tokenize_sql('9foo')

        # Note: digits as identifier-start are not currently produced by the scanner — the current behavior is to silently skip the leading digit and pick up the trailing identifier characters as a regular identifier.
        assert tokens == [type(tokens[0])(kind='identifier', value='foo')]

    def test_single_quoted_string_literal_emits_no_tokens(self):
        """A ``'...'`` literal emits no tokens; the literal text is consumed."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql("'abc def'")

        assert tokens == []

    def test_single_quoted_string_with_doubled_quote_escape(self):
        """A ``''`` inside ``'...'`` is an escape and does not close the literal."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        # The literal contains an escaped single quote: ``can't``. The
        # scanner must consume the entire literal and emit nothing. The
        # ``orders`` token after it must still be tokenized.
        tokens = _tokenize_sql("'can''t' orders")

        assert tokens == [type(tokens[0])(kind='identifier', value='orders')]

    def test_string_literal_does_not_produce_false_references(self):
        """Identifier-looking text inside a string literal must not emit tokens."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql("select x from 'literal FROM tpch.orders' real_table")

        # The identifier-looking text inside the literal (``literal``,
        # ``FROM``, ``tpch``, ``orders``) must NOT appear as tokens.
        values = [t.value for t in tokens]
        assert 'literal' not in values
        assert 'tpch' not in values
        assert 'orders' not in values
        # The identifier after the literal IS tokenized.
        assert 'real_table' in values

    def test_double_quoted_identifier_emits_one_token_with_quotes_consumed(self):
        """``"foo"`` emits one ``'identifier'`` token with value ``foo``."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('"foo"')

        assert len(tokens) == 1
        assert tokens[0].kind == 'identifier'
        assert tokens[0].value == 'foo'

    def test_double_quoted_identifier_preserves_case(self):
        """Double-quoted identifiers preserve original case."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('"MixedCase"')

        assert tokens[0].value == 'MixedCase'

    def test_double_quoted_identifier_with_embedded_doubled_quote_is_one_token(self):
        """A ``""`` inside ``"..."`` is an escape that becomes a single ``"``."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        # The identifier is ``foo"bar`` (a quote in the middle). Encoded
        # in SQL as ``"foo""bar"``. The scanner must emit a single
        # identifier token with the un-escaped value.
        tokens = _tokenize_sql('"foo""bar"')

        assert len(tokens) == 1
        assert tokens[0].kind == 'identifier'
        assert tokens[0].value == 'foo"bar'

    def test_double_quoted_identifier_can_contain_spaces(self):
        """A double-quoted identifier may contain whitespace and punctuation."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('"my table.col"')

        assert len(tokens) == 1
        assert tokens[0].value == 'my table.col'

    def test_double_quoted_keyword_is_not_tokenized_as_keyword(self):
        """``"FROM"`` is an identifier, not the FROM keyword (case preserved)."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('"FROM"')

        # Double-quoted text is always an identifier — keyword
        # recognition only applies to unquoted words.
        assert tokens[0].kind == 'identifier'
        assert tokens[0].value == 'FROM'

    def test_line_comment_to_end_of_line_emits_no_tokens(self):
        """``-- ...`` consumes through the next newline and emits nothing."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a -- ignored from tpch.orders\n b')

        # ``a`` and ``b`` survive; everything between ``--`` and the
        # newline is silently consumed.
        assert [t.value for t in tokens] == ['a', 'b']

    def test_line_comment_at_end_of_input_without_newline(self):
        """A trailing ``-- ...`` without a newline still consumes the rest."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a -- trailing comment with no newline')

        assert [t.value for t in tokens] == ['a']

    def test_block_comment_emits_no_tokens(self):
        """``/* ... */`` consumes content and emits nothing."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a /* ignored from tpch.orders */ b')

        assert [t.value for t in tokens] == ['a', 'b']

    def test_block_comment_is_not_nested_first_close_wins(self):
        """``/* /* still in comment */`` — the first ``*/`` closes the comment."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        # Per the non-nested rule, the ``*/`` after ``still in comment`` closes the comment.
        tokens = _tokenize_sql('/* /* still in comment */ trailing */')

        # The single surviving identifier is ``trailing``. The trailing
        # ``*/`` characters are skipped as non-identifier punctuation.
        assert [t.value for t in tokens] == ['trailing']

    def test_unterminated_block_comment_consumes_to_end(self):
        """An unterminated ``/* ...`` consumes through end-of-input silently."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        tokens = _tokenize_sql('a /* never closes')

        assert [t.value for t in tokens] == ['a']

    def test_realistic_select_statement_yields_expected_token_stream(self):
        """A realistic FROM/JOIN clause yields a recognizable token sequence."""
        from awslabs.redshift_mcp_server.redshift import _tokenize_sql

        sql = 'SELECT a FROM tpch.orders o JOIN customers AS c ON o.x = c.x;'
        tokens = _tokenize_sql(sql)

        # Build a (kind, value) projection so the assertion stays
        # readable.
        projection = [(t.kind, t.value) for t in tokens]

        # Operators ``=`` and the column-list ``a`` are silently
        # consumed (the scanner doesn't know about column lists; the
        # categorization layer tracks FROM/JOIN positions).
        assert projection == [
            ('identifier', 'SELECT'),
            ('identifier', 'a'),
            ('keyword', 'FROM'),
            ('identifier', 'tpch'),
            ('dot', '.'),
            ('identifier', 'orders'),
            ('identifier', 'o'),
            ('keyword', 'JOIN'),
            ('identifier', 'customers'),
            ('keyword', 'AS'),
            ('identifier', 'c'),
            ('identifier', 'ON'),
            ('identifier', 'o'),
            ('dot', '.'),
            ('identifier', 'x'),
            ('identifier', 'c'),
            ('dot', '.'),
            ('identifier', 'x'),
            ('punctuation', ';'),
        ]

    def test_extract_returns_empty_list_placeholder(self):
        """``extract`` on ``SELECT * FROM tpch.orders`` returns one schema-qualified reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        result = _extract_sql_references('SELECT * FROM tpch.orders')

        assert result == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_sql_reference_extract_error_is_defined_and_subclass_of_exception(self):
        """``SqlReferenceExtractError`` is exported and inherits from ``Exception``."""
        from awslabs.redshift_mcp_server.redshift import SqlReferenceExtractError

        # Defined now for use by tasks 6.2 and 6.6 to signal
        # malformed dotted-identifier sequences and empty/whitespace
        # SQL. Not raised by itself.
        assert issubclass(SqlReferenceExtractError, Exception)

    # -----------------------------------------------------------------
    # Categorization
    # -----------------------------------------------------------------

    def test_bare_reference_one_part(self):
        """``FROM orders`` emits one ``BARE`` reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM orders')

        assert refs == [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

    def test_schema_qualified_reference_two_parts(self):
        """``FROM tpch.orders`` emits one ``SCHEMA_QUALIFIED`` reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.orders')

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_database_qualified_reference_three_parts(self):
        """``FROM prod_db.tpch.orders`` emits a ``DATABASE_QUALIFIED`` reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM prod_db.tpch.orders')

        assert refs == [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                database_name='prod_db',
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_join_clause_emits_reference(self):
        """``JOIN <ref>`` is a FROM/JOIN position and emits a reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM tpch.orders JOIN tpch.customers'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='customers',
            ),
        ]

    def test_comma_separated_from_list_emits_each_reference(self):
        """``FROM a, b`` emits one reference per comma-separated table."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM orders, customers')

        assert refs == [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
            TableReference(category=TABLE_REF_BARE, table_name='customers'),
        ]

    def test_comma_separated_from_list_with_alias_emits_each_reference(self):
        """``FROM a o, b c`` emits two references; aliases are not emitted."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM orders o, customers c')

        assert refs == [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
            TableReference(category=TABLE_REF_BARE, table_name='customers'),
        ]

    def test_alias_with_as_keyword_does_not_become_reference(self):
        """``FROM a AS o`` consumes the alias and emits only ``a``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.orders AS o')

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Identifier case preservation
    # -----------------------------------------------------------------

    def test_identifier_case_preserved_unquoted(self):
        """Unquoted identifier case is preserved exactly as written."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('select * from MyDB.MySchema.MyTable')

        assert refs == [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                database_name='MyDB',
                schema_name='MySchema',
                table_name='MyTable',
            ),
        ]

    def test_keywords_are_recognized_case_insensitively(self):
        """``from`` and ``FROM`` both arm the FROM/JOIN position."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        for sql in (
            'select * from tpch.orders',
            'SELECT * FROM tpch.orders',
            'SeLeCt * FrOm tpch.orders',
        ):
            refs = _extract_sql_references(sql)
            assert refs == [
                TableReference(
                    category=TABLE_REF_SCHEMA_QUALIFIED,
                    schema_name='tpch',
                    table_name='orders',
                ),
            ]

    # -----------------------------------------------------------------
    # Parse-failure contract
    # -----------------------------------------------------------------

    def test_zero_part_sequence_at_from_position_raises(self):
        """``FROM ,`` (no identifier after FROM) raises ``SqlReferenceExtractError``."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        # ``FROM`` followed by a comma — the next position expects a
        # table identifier but gets punctuation. Per the parse-failure
        # contract, this is a 0-part sequence.
        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT 1 FROM , customers')

    def test_zero_part_sequence_at_join_position_raises(self):
        """``JOIN ;`` raises ``SqlReferenceExtractError`` (0-part at JOIN)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT 1 FROM a JOIN ;')

    def test_four_part_sequence_raises(self):
        """``FROM a.b.c.d`` raises ``SqlReferenceExtractError`` (4+ parts)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT * FROM a.b.c.d')

    # -----------------------------------------------------------------
    # Deduplication () — pinned here in the
    # categorization class because dedup is the final layer on top of
    # FROM/JOIN-position categorization.
    # -----------------------------------------------------------------

    def test_repeated_reference_is_deduplicated(self):
        """Identical schema-qualified references collapse to one."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.orders JOIN tpch.orders ON 1=1')

        # Per the second emission is collapsed; first
        # occurrence wins to preserve source order.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_bare_and_schema_qualified_are_not_deduplicated(self):
        """``orders`` and ``tpch.orders`` are distinct ``TableReference`` records."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.orders JOIN orders ON 1=1')

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_BARE,
                table_name='orders',
            ),
        ]

    def test_dedup_preserves_first_occurrence_source_order(self):
        """Across multiple repeats and interleaved tables, source order is preserved."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = (
            'SELECT * FROM tpch.orders '
            'JOIN tpch.customers '
            'JOIN tpch.orders ON 1=1 '
            'JOIN tpch.customers ON 1=1'
        )
        refs = _extract_sql_references(sql)

        # First occurrence wins: orders before customers; both repeats
        # collapsed.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='customers',
            ),
        ]

    def test_dedup_is_case_sensitive_on_identifiers(self):
        """``Orders`` and ``orders`` are NOT deduplicated."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.Orders JOIN tpch.orders ON 1=1')

        # Case-preserved identifiers participate in dedup
        # under exact tuple equality — different case, no
        # collapse.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='Orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_cte_name_excluded_after_task_6_3(self):
        """``WITH cte AS (...)`` causes ``cte`` to be excluded as a table reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TableReference,
            _extract_sql_references,
        )

        sql = 'WITH cte AS (SELECT 1) SELECT * FROM cte'
        refs = _extract_sql_references(sql)

        # ``cte`` is a CTE name, so the BARE reference at ``FROM cte``
        # is excluded; no real-table references in this SQL.
        assert refs == []
        # Specifically: ``cte`` MUST NOT appear as a BARE reference.
        assert all(ref.table_name != 'cte' for ref in refs), (
            f'CTE name should be excluded, got: {refs}'
        )
        # Belt-and-braces: also confirm a hypothetical BARE ``cte`` is
        # not in the emitted list.
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
        )

        assert TableReference(category=TABLE_REF_BARE, table_name='cte') not in refs

    def test_single_cte_name_excluded_at_top_level_select(self):
        """``WITH a AS (...) SELECT * FROM a`` emits no references."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        refs = _extract_sql_references('WITH a AS (SELECT 1) SELECT * FROM a')

        assert refs == []

    def test_multiple_comma_separated_ctes_all_excluded(self):
        """All names in a single ``WITH`` clause register in the same frame."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        sql = (
            'WITH a AS (SELECT 1), b AS (SELECT 2), c AS (SELECT 3) '
            'SELECT * FROM a JOIN b ON 1=1 JOIN c ON 1=1'
        )
        refs = _extract_sql_references(sql)

        # All three references are CTE names; nothing emitted.
        assert refs == []

    def test_real_table_alongside_cte_still_emitted(self):
        """Real tables in the main statement still appear; only CTE names are excluded."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'WITH cte AS (SELECT 1) SELECT * FROM cte JOIN tpch.orders ON 1=1'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_real_table_inside_cte_body_emitted(self):
        """Tables inside a CTE body are real references and must be emitted."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'WITH recent AS (SELECT * FROM tpch.orders) SELECT * FROM recent'
        refs = _extract_sql_references(sql)

        # ``tpch.orders`` is a real schema-qualified reference inside
        # the CTE body. ``recent`` at the top level is a CTE name and
        # must be excluded.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_cte_name_shadows_real_table(self):
        """A CTE name shadows a real table of the same name."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        # ``orders`` would normally be a BARE reference, but the
        # ``WITH orders AS (...)`` clause shadows it.
        sql = 'WITH orders AS (SELECT 1) SELECT * FROM orders'
        refs = _extract_sql_references(sql)

        assert refs == []

    def test_schema_qualified_reference_never_treated_as_cte(self):
        """Even when a CTE name matches the table half, ``schema.table`` is NOT excluded."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'WITH orders AS (SELECT 1) SELECT * FROM tpch.orders'
        refs = _extract_sql_references(sql)

        # ``tpch.orders`` is schema-qualified and is therefore emitted
        # even though ``orders`` is in scope as a CTE name.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_database_qualified_reference_never_treated_as_cte(self):
        """``db.schema.table`` is emitted even when ``table`` is a CTE name."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'WITH orders AS (SELECT 1) SELECT * FROM prod_db.tpch.orders'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                database_name='prod_db',
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_cte_name_match_is_case_sensitive(self):
        """CTE-name matching uses the original-case identifier value."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        # ``Orders`` is registered as a CTE name (mixed case). A BARE
        # reference to ``orders`` (lowercase) is a DIFFERENT identifier
        # by case-sensitive comparison and therefore is NOT excluded.
        sql = 'WITH Orders AS (SELECT 1) SELECT * FROM orders'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

    def test_nested_with_inside_cte_body_pushes_inner_frame(self):
        """A ``WITH`` inside a CTE body produces a nested frame."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        # ``inner`` is a CTE in the inner WITH; ``outer`` is the outer CTE; ``tpch.orders`` is a real table referenced inside the inner CTE body.
        sql = (
            'WITH outer_cte AS ('
            '    WITH inner_cte AS (SELECT * FROM tpch.orders) '
            '    SELECT * FROM inner_cte'
            ') '
            'SELECT * FROM outer_cte JOIN tpch.users ON 1=1'
        )
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='users',
            ),
        ]

    def test_inner_cte_name_does_not_leak_to_outer_scope(self):
        """An inner-WITH CTE name is excluded only inside its frame, not after pop."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        # ``inner_cte`` is registered inside the outer CTE body.
        sql = (
            'WITH outer_cte AS ('
            '    WITH inner_cte AS (SELECT 1) SELECT * FROM inner_cte'
            ') '
            'SELECT * FROM inner_cte'
        )
        refs = _extract_sql_references(sql)

        # The inner ``FROM inner_cte`` is excluded (inner frame
        # active). The outer ``FROM inner_cte`` (after inner frame
        # popped) is emitted as a BARE reference.
        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='inner_cte',
            ),
        ]

    def test_innermost_frame_wins_for_shadowing(self):
        """When a name appears in both inner and outer frames, exclusion still applies."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        # ``a`` is defined in both the outer and inner WITH.
        sql = 'WITH a AS (    WITH a AS (SELECT 1) SELECT * FROM a) SELECT * FROM a'
        refs = _extract_sql_references(sql)

        assert refs == []

    def test_with_recursive_modifier_supported(self):
        """The optional ``RECURSIVE`` keyword between ``WITH`` and the first CTE is skipped."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        sql = 'WITH RECURSIVE r AS (SELECT 1) SELECT * FROM r'
        refs = _extract_sql_references(sql)

        assert refs == []

    def test_with_clause_with_column_list_collected(self):
        """A CTE may include an optional ``(col1, col2)`` column list before ``AS``."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        sql = 'WITH a (x, y) AS (SELECT 1, 2) SELECT * FROM a'
        refs = _extract_sql_references(sql)

        assert refs == []

    def test_cte_in_subquery_does_not_affect_outer_scope(self):
        """A WITH inside a parenthesized subquery only scopes inside that paren."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        # The inner WITH defines ``q`` in a frame at depth 1.
        sql = 'SELECT * FROM tpch.orders WHERE x IN (    WITH q AS (SELECT 1) SELECT * FROM q)'
        refs = _extract_sql_references(sql)

        # Outer ``FROM tpch.orders`` is emitted; inner ``FROM q`` is
        # excluded by the inner frame.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Subquery alias
    # -----------------------------------------------------------------

    def test_subquery_alias_not_emitted_with_as(self):
        """``FROM (SELECT ...) AS sub`` does not emit ``sub``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM (SELECT 1) AS sub'
        refs = _extract_sql_references(sql)

        # No table references: the subquery body has no FROM, and
        # ``sub`` is a subquery alias (excluded).
        assert refs == []
        assert TableReference(category=TABLE_REF_BARE, table_name='sub') not in refs

    def test_subquery_alias_not_emitted_without_as(self):
        """``FROM (SELECT ...) sub`` does not emit ``sub``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM (SELECT 1) sub'
        refs = _extract_sql_references(sql)

        assert refs == []
        assert TableReference(category=TABLE_REF_BARE, table_name='sub') not in refs

    def test_subquery_body_scanned_for_inner_table_references(self):
        """Inner ``FROM tpch.orders`` is emitted; alias is not."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM (SELECT * FROM tpch.orders) AS sub'
        refs = _extract_sql_references(sql)

        # The inner table reference is emitted; the subquery alias
        # ``sub`` is not.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_subquery_alias_in_join_position(self):
        """``JOIN (SELECT ...) j`` does not emit ``j``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM tpch.orders o JOIN (SELECT * FROM tpch.customers) j ON o.cid = j.cid'
        refs = _extract_sql_references(sql)

        # Both inner table references are emitted; ``j`` and ``o``
        # (column aliases) are not.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='customers',
            ),
        ]

    def test_subquery_followed_by_comma_rearms_from_list(self):
        """``FROM (SELECT ...) a, t`` emits ``t`` (alias-comma re-arm)."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM (SELECT 1) a, tpch.orders'
        refs = _extract_sql_references(sql)

        # ``a`` is a subquery alias (not emitted); ``tpch.orders``
        # after the comma is.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_subquery_with_no_alias_does_not_emit(self):
        """``FROM (SELECT ...)`` with no alias still excludes inner from raising."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        # A subquery with no trailing alias is unusual but should not
        # emit anything for the missing alias and should not raise.
        # (The inner body has no FROM, so no references at all.)
        sql = 'SELECT * FROM (SELECT 1)'
        refs = _extract_sql_references(sql)

        assert refs == []

    def test_nested_subquery_excludes_all_aliases(self):
        """Nested ``FROM (SELECT ... FROM (SELECT ...) inner) outer`` excludes both aliases."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = (
            'SELECT * FROM ('
            '  SELECT * FROM ('
            '    SELECT * FROM tpch.orders'
            '  ) inner_alias'
            ') outer_alias'
        )
        refs = _extract_sql_references(sql)

        # Only the deepest table reference is emitted; both aliases
        # are excluded.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Column alias
    # -----------------------------------------------------------------

    def test_column_alias_after_schema_qualified_not_emitted(self):
        """``FROM tpch.orders o`` emits only ``tpch.orders``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM tpch.orders o'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]
        # ``o`` is not emitted as a separate reference.
        assert TableReference(category=TABLE_REF_BARE, table_name='o') not in refs

    def test_column_alias_with_as_keyword_not_emitted(self):
        """``FROM tpch.orders AS o`` emits only ``tpch.orders``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM tpch.orders AS o'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    def test_column_alias_after_bare_reference_not_emitted(self):
        """``FROM orders o`` emits only ``orders``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM orders o'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='orders',
            ),
        ]

    def test_join_with_column_aliases_emits_both_tables(self):
        """``FROM users u JOIN orders o`` emits ``users`` and ``orders``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM users u JOIN orders o ON u.id = o.uid'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='users',
            ),
            TableReference(
                category=TABLE_REF_BARE,
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: Three categorized forms (bare, schema-qualified,
    # database-qualified). 4.4, 4.5.
    # -----------------------------------------------------------------

    def test_three_forms_in_one_query_each_categorized_correctly(self):
        """A single SQL with all three reference forms emits one of each."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TABLE_REF_DATABASE_QUALIFIED,
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM orders JOIN tpch.customers ON 1=1 JOIN prod_db.tpch.line_items ON 1=1'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='customers',
            ),
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                database_name='prod_db',
                schema_name='tpch',
                table_name='line_items',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: Identifier case preserved; keywords matched
    # case-insensitively. Validates .
    # -----------------------------------------------------------------

    def test_identifier_case_preserved_keywords_case_insensitive_at_extract_layer(self):
        """Keywords match in any case; identifier case is preserved exactly."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        # Mixed keyword case (``SeLeCt``, ``FrOm``, ``JoIn``, ``oN``) must still recognize FROM and JOIN; identifier case (``MyDb``, ``MyTpch``, ``MyOrders``) must be preserved verbatim in the emitted references.
        sql = 'SeLeCt * FrOm MyDb.MyTpch.MyOrders JoIn AnotherSchema.AnotherTable oN 1=1'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                database_name='MyDb',
                schema_name='MyTpch',
                table_name='MyOrders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='AnotherSchema',
                table_name='AnotherTable',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: CTE name exclusion (single, multiple comma-separated,
    # nested WITH). 5.5.
    # -----------------------------------------------------------------

    def test_cte_exclusion_single_multiple_and_nested_in_one_query(self):
        """Single, multiple comma-separated, and nested WITH CTEs are all excluded."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = (
            'WITH a AS (SELECT 1), b AS (SELECT 2) '
            'SELECT * FROM ('
            '    WITH c AS (SELECT * FROM tpch.orders) SELECT * FROM c'
            ') sub '
            'JOIN a ON 1=1 '
            'JOIN b ON 1=1'
        )
        refs = _extract_sql_references(sql)

        # ``a``, ``b``, ``c`` are all CTE names and must be excluded.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: Subquery alias exclusion (with and without ``AS``).
    # Validates .
    # -----------------------------------------------------------------

    def test_subquery_alias_exclusion_with_and_without_as_in_one_query(self):
        """A query mixing ``(...) AS sub`` and ``(...) sub`` excludes both aliases."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        sql = (
            'SELECT * FROM (SELECT * FROM tpch.orders) AS sub_with_as '
            'JOIN (SELECT * FROM tpch.customers) sub_without_as ON 1=1'
        )
        refs = _extract_sql_references(sql)

        # Both aliases excluded; only the real inner tables are
        # emitted.
        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='customers',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: Column alias not emitted (``FROM tpch.orders o`` →
    # only ``tpch.orders``). Validates .
    # -----------------------------------------------------------------

    def test_column_alias_not_emitted_explicit_orders_o_case(self):
        """The exact case from the bullet: ``FROM tpch.orders o`` emits only ``tpch.orders``."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        refs = _extract_sql_references('SELECT * FROM tpch.orders o')

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: CTE name shadowing real table → CTE wins.
    # Validates .
    # -----------------------------------------------------------------

    def test_cte_name_shadowing_real_bare_table_cte_wins(self):
        """A CTE name shadows a same-name real table reference."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        # ``orders`` would normally be a BARE reference, but the
        # ``WITH orders AS (...)`` clause shadows it. Per the
        # CTE wins: no real-table reference emitted.
        sql = 'WITH orders AS (SELECT 1) SELECT * FROM orders'
        refs = _extract_sql_references(sql)

        assert refs == []

    # -----------------------------------------------------------------
    # Bullet: Deduplication of identical references. Validates .
    # -----------------------------------------------------------------

    def test_deduplication_of_identical_references_at_extract_layer(self):
        """Repeated identical references collapse to one."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _extract_sql_references,
        )

        # ``tpch.orders`` appears three times; dedup collapses to one.
        sql = 'SELECT * FROM tpch.orders JOIN tpch.orders ON 1=1 JOIN tpch.orders ON 1=1'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                schema_name='tpch',
                table_name='orders',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: String literals, double-quoted identifiers, line and
    # block comments do not produce false references. Validates
    # 4.7.
    #
    # The tokenizer class already pins this at the token level
    # (string literals and comments emit no tokens; double-quoted
    # text always emits an identifier with original case). These
    # tests pin the same property at the ``extract()`` boundary so a
    # regression in the categorization layer can't sneak a
    # false-positive reference past the dedicated extract tests.
    # -----------------------------------------------------------------

    def test_string_literal_text_does_not_produce_table_reference(self):
        """``'FROM tpch.orders'`` inside a literal emits no reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        # Only the real ``FROM real_table`` outside the literal emits a reference.
        sql = "SELECT 'FROM tpch.orders' AS x FROM real_table"
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='real_table',
            ),
        ]

    def test_line_comment_text_does_not_produce_table_reference(self):
        """``-- FROM tpch.orders`` inside a line comment emits no reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * -- FROM tpch.orders\nFROM real_table'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='real_table',
            ),
        ]

    def test_block_comment_text_does_not_produce_table_reference(self):
        """``/* FROM tpch.orders */`` inside a block comment emits no reference."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * /* FROM tpch.orders */ FROM real_table'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='real_table',
            ),
        ]

    def test_double_quoted_identifier_emits_real_reference_with_preserved_case(self):
        """A double-quoted identifier participates in references with original case."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _extract_sql_references,
        )

        sql = 'SELECT * FROM "MixedCase"'
        refs = _extract_sql_references(sql)

        assert refs == [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='MixedCase',
            ),
        ]

    # -----------------------------------------------------------------
    # Bullet: Empty/whitespace SQL → parse error.
    #
    # Validates ``_extract_sql_references`` parse-failure
    # contract: empty or whitespace-only SQL is rejected with
    # :class:`SqlReferenceExtractError` rather than silently returning
    # an empty list. The simplest sufficient implementation rule is
    # "no productive tokens": the scanner consumes whitespace, line
    # comments, and block comments silently, so an SQL that contains
    # only those constructs produces zero tokens and is rejected at
    # the same boundary as a truly empty input.
    # -----------------------------------------------------------------

    def test_empty_sql_raises(self):
        """``extract('')`` raises :class:`SqlReferenceExtractError`."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('')

    def test_whitespace_only_sql_raises(self):
        """``extract('   ')`` raises :class:`SqlReferenceExtractError`."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('   ')

    def test_whitespace_with_newlines_and_tabs_raises(self):
        """Pure whitespace including newlines and tabs raises."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references(' \t\n\r\n  \t ')

    def test_line_comment_only_sql_raises(self):
        """``extract('-- only a comment')`` raises (no productive tokens)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('-- only a comment')

    def test_block_comment_only_sql_raises(self):
        """A block-comment-only SQL raises (no productive tokens)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('/* only a block comment */')

    def test_mixed_whitespace_and_comments_only_raises(self):
        """SQL containing only whitespace and comments raises."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        # Newline-separated mix of line and block comments with
        # interleaved whitespace. None of these emit tokens, so the
        # parse-failure contract triggers.
        sql = '  -- a line comment\n  /* a block comment */\n   '
        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references(sql)

    def test_non_empty_sql_with_no_from_clause_does_not_raise(self):
        """``SELECT 1`` has tokens (productive) but no FROM/JOIN; returns ``[]`` without raising."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        refs = _extract_sql_references('SELECT 1')

        assert refs == []

    # -----------------------------------------------------------------
    # Bullet: Malformed reference (0 or 4+ parts) → parse error.
    ## -----------------------------------------------------------------

    def test_zero_part_at_from_position_raises(self):
        """``FROM ,`` raises :class:`SqlReferenceExtractError` (0-part)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT 1 FROM , customers')

    def test_four_part_at_from_position_raises(self):
        """``FROM a.b.c.d`` raises :class:`SqlReferenceExtractError` (4+ parts)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT * FROM a.b.c.d')

    def test_five_part_at_from_position_raises(self):
        """A 5-part dotted sequence is also rejected (not silently truncated)."""
        from awslabs.redshift_mcp_server.redshift import (
            SqlReferenceExtractError,
            _extract_sql_references,
        )

        with pytest.raises(SqlReferenceExtractError):
            _extract_sql_references('SELECT * FROM a.b.c.d.e')

    @pytest.mark.parametrize(
        'sql',
        [
            pytest.param('SELECT * FROM users', id='simple'),
            pytest.param(
                'WITH cte AS (SELECT 1 AS a) SELECT * FROM cte JOIN users ON cte.a = users.id',
                id='cte_shadowing',
            ),
            pytest.param(
                'SELECT * FROM (SELECT id FROM tickit.sales) s JOIN tickit.event e ON s.id = e.eventid',
                id='subquery_with_schema_qualified',
            ),
        ],
    )
    def test_extract_is_stable_across_invocations(self, sql):
        """Calling the extractor twice on the same SQL yields equal output."""
        from awslabs.redshift_mcp_server.redshift import _extract_sql_references

        first = _extract_sql_references(sql)
        second = _extract_sql_references(sql)

        assert first == second

    def test_render_schema_table_pairs_empty_iterable_returns_empty_string(self):
        """Empty input → empty string, no parentheses, no commas."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        assert _render_schema_table_pairs([]) == ''
        assert _render_schema_table_pairs(iter(())) == ''
        assert _render_schema_table_pairs(set()) == ''

    def test_single_pair_renders_as_one_quoted_tuple(self):
        """One pair → exactly one ``('<schema>','<table>')`` literal."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([('public', 'orders')])

        assert rendered == "('public','orders')"

    def test_multiple_pairs_joined_by_comma_no_space(self):
        """Multiple pairs are joined by ``,`` with no surrounding whitespace."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([('public', 'orders'), ('tpch', 'lineitem')])

        # Pairs are sorted ascending by (schema, table); ``public`` <
        # ``tpch`` so ``public`` appears first.
        assert rendered == "('public','orders'),('tpch','lineitem')"
        assert ', ' not in rendered

    def test_pairs_are_sorted_for_deterministic_output(self):
        """Different iteration orders produce byte-identical output."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        pairs = [('zeta', 't'), ('alpha', 't'), ('beta', 't')]
        from_list = _render_schema_table_pairs(pairs)
        from_set = _render_schema_table_pairs(set(pairs))
        from_reversed = _render_schema_table_pairs(reversed(pairs))

        assert from_list == "('alpha','t'),('beta','t'),('zeta','t')"
        assert from_list == from_set == from_reversed

    def test_sorts_by_table_within_same_schema(self):
        """Within a schema, pairs sort ascending by table name."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs(
            [('s', 'orders'), ('s', 'customers'), ('s', 'lineitem')]
        )

        assert rendered == "('s','customers'),('s','lineitem'),('s','orders')"

    def test_single_quote_in_schema_is_doubled(self):
        """A literal ``'`` in the schema component is doubled (``''``)."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([("o'reilly", 'orders')])

        assert rendered == "('o''reilly','orders')"

    def test_single_quote_in_table_is_doubled(self):
        """A literal ``'`` in the table component is doubled (``''``)."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([('public', "weird'name")])

        assert rendered == "('public','weird''name')"

    def test_multiple_quotes_in_one_value_each_doubled(self):
        """Every literal ``'`` is doubled, regardless of count."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([("a'b'c", "x'y")])

        assert rendered == "('a''b''c','x''y')"

    def test_render_schema_table_pairs_case_preserved_exactly(self):
        """Identifier case is preserved as written."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        rendered = _render_schema_table_pairs([('PuBlIc', 'OrDeRs')])

        assert rendered == "('PuBlIc','OrDeRs')"

    def test_render_schema_table_pairs_repeated_calls_are_idempotent(self):
        """Same input → byte-identical output across calls."""
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        pairs = [('s2', 't2'), ('s1', 't1')]

        first = _render_schema_table_pairs(pairs)
        second = _render_schema_table_pairs(pairs)

        assert first == second

    def test_rendered_fragment_drops_into_tables_extra_by_pairs_sql(self):
        """The rendered fragment formats cleanly into the SQL constant."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL
        from awslabs.redshift_mcp_server.redshift import _render_schema_table_pairs

        fragment = _render_schema_table_pairs([('public', 'orders'), ('tpch', 'lineitem')])

        rendered = TABLES_EXTRA_BY_PAIRS_SQL.format(schema_table_pairs=fragment)

        # No leftover ``{...}`` placeholders, and the literal pair-list
        # appears in the resulting SQL exactly as rendered.

        assert not regex.search(r'\{[a-zA-Z_]+\}', rendered)
        assert fragment in rendered

    @pytest.mark.asyncio
    async def test_empty_pairs_executes_zero_statements(self, mocker):
        """Empty pair set → no batched query executed, returns ``{}``."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs=set(),
        )

        assert result == {}
        mock_execute_protected.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_pair_executes_exactly_one_statement(self, mocker):
        """Single pair → exactly one ``TABLES_EXTRA_BY_PAIRS_SQL`` call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_many_pairs_still_executes_exactly_one_statement(self, mocker):
        """50 pairs → still exactly one batched call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        pairs = {('public', f't{i}') for i in range(50)}

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs=pairs,
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_invokes_tables_extra_by_pairs_sql_with_rendered_pair_list(self, mocker):
        """SQL passed to ``_execute_protected_statement`` is the formatted constant."""
        from awslabs.redshift_mcp_server.consts import TABLES_EXTRA_BY_PAIRS_SQL
        from awslabs.redshift_mcp_server.redshift import (
            _fetch_table_metadata,
            _render_schema_table_pairs,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        pairs = {('public', 'orders'), ('tpch', 'lineitem')}
        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs=pairs,
        )

        # Exactly one call, with the SQL formed from the constant and
        # the rendered pair-list helper.
        ((), kwargs) = (
            mock_execute_protected.call_args.args,
            mock_execute_protected.call_args.kwargs,
        )
        expected_sql = TABLES_EXTRA_BY_PAIRS_SQL.format(
            schema_table_pairs=_render_schema_table_pairs(pairs)
        )
        assert kwargs['sql'] == expected_sql
        assert kwargs['cluster_identifier'] == 'c1'
        assert kwargs['database_name'] == 'dev'

    @pytest.mark.asyncio
    async def test_parses_response_into_pair_keyed_metadata_dict(self, mocker):
        """Response rows parse into ``(schema, table) -> RedshiftTable-shaped`` dict."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'orders'},
                        {'stringValue': 'KEY'},
                        {'longValue': 12345},
                        {'longValue': 7},
                        {'longValue': 90000},
                        {'longValue': 1},
                        {'longValue': 2},
                        {'longValue': 3},
                    ],
                    [
                        {'stringValue': 'tpch'},
                        {'stringValue': 'lineitem'},
                        {'stringValue': 'ALL'},
                        {'longValue': 600000},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ],
                ]
            },
            'qid',
        )

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders'), ('tpch', 'lineitem')},
        )

        assert set(result.keys()) == {('public', 'orders'), ('tpch', 'lineitem')}
        assert result[('public', 'orders')] == {
            'redshift_diststyle': 'KEY',
            'redshift_estimated_row_count': 12345,
            'stats_sequential_scans': 7,
            'stats_sequential_tuples_read': 90000,
            'stats_rows_inserted': 1,
            'stats_rows_updated': 2,
            'stats_rows_deleted': 3,
        }
        assert result[('tpch', 'lineitem')] == {
            'redshift_diststyle': 'ALL',
            'redshift_estimated_row_count': 600000,
            'stats_sequential_scans': 0,
            'stats_sequential_tuples_read': 0,
            'stats_rows_inserted': 0,
            'stats_rows_updated': 0,
            'stats_rows_deleted': 0,
        }

    @pytest.mark.asyncio
    async def test_zero_records_returns_empty_mapping(self, mocker):
        """Non-empty pair set but zero matching rows → empty mapping, one call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_table_metadata_swallows_execute_protected_exception_returns_empty(
        self, mocker
    ):
        """``_execute_protected_statement`` failure → ``{}``, no retry."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Data API failure')

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        # No retry: the batched call is attempted exactly once per
        # ``fetch`` invocation, even when it raises.
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_table_metadata_swallows_row_parsing_exception_returns_empty(self, mocker):
        """Malformed response rows → ``{}`` (no propagation)."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        # Each record has only 2 columns instead of the expected 9 →
        # ``record[2].get(...)`` raises ``IndexError`` during parsing.
        mock_execute_protected.return_value = (
            {'Records': [[{'stringValue': 'public'}, {'stringValue': 'orders'}]]},
            'qid',
        )

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_table_metadata_logs_warning_on_execute_protected_exception(self, mocker):
        """A warning is logged when the batched call fails."""
        from awslabs.redshift_mcp_server import redshift as redshift_module
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('boom')

        warning_spy = mocker.patch.object(redshift_module.logger, 'warning')

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        assert warning_spy.call_count == 1
        # The warning message references the underlying error so an
        # operator can see why the metadata mapping is empty.
        warning_text = warning_spy.call_args.args[0]
        assert 'boom' in warning_text

    # -----------------------------------------------------------------
    # Bullet: Empty pair set → no batched query executed.
    # Validates .
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_pair_set_executes_zero_statements_at_fetcher_boundary(self, mocker):
        """``fetch(pairs=set())`` returns ``{}`` and never calls the protected statement."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs=set(),
        )

        assert result == {}
        mock_execute_protected.assert_not_called()

    # -----------------------------------------------------------------
    # Bullet: Non-empty pair set (1, 50 pairs) → exactly one
    # ``TABLES_EXTRA_BY_PAIRS_SQL`` invocation per call.
    # 7.5, 7.7.
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_one_pair_executes_exactly_one_invocation_at_fetcher_boundary(self, mocker):
        """One pair → exactly one batched call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fifty_pairs_still_one_invocation_at_fetcher_boundary(self, mocker):
        """50 pairs → still exactly one batched call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        pairs = {('public', f't{i}') for i in range(50)}

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs=pairs,
        )

        assert mock_execute_protected.call_count == 1

    # -----------------------------------------------------------------
    # Bullet: Pair-list rendering: ``('<schema>','<table>')`` tuples.
    # # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rendered_pair_list_uses_quoted_tuple_form_in_executed_sql(self, mocker):
        """The SQL handed to the executor contains ``('<schema>','<table>')`` tuples."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders'), ('tpch', 'lineitem')},
        )

        executed_sql = mock_execute_protected.call_args.kwargs['sql']
        # Each pair appears in the executed SQL as a quoted 2-tuple,
        # joined by a single ``,`` (no surrounding whitespace).
        assert "('public','orders')" in executed_sql
        assert "('tpch','lineitem')" in executed_sql
        # And the pair-list fragment is comma-joined inside the SQL.
        assert "('public','orders'),('tpch','lineitem')" in executed_sql

    # -----------------------------------------------------------------
    # Bullet: Single-quote escaping by doubling.
    # Validates .
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_single_quote_in_pair_components_doubled_in_executed_sql(self, mocker):
        """A literal ``'`` in either component is doubled in the executed SQL."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={("o'reilly", "weird'name")},
        )

        executed_sql = mock_execute_protected.call_args.kwargs['sql']
        # The pair is rendered with each literal ``'`` doubled.
        assert "('o''reilly','weird''name')" in executed_sql
        # Sanity: no raw, unescaped single quote sequence appears
        # inside the rendered pair (which would break the surrounding
        # SQL string-literal quoting).
        assert "'o'reilly'" not in executed_sql
        assert "'weird'name'" not in executed_sql

    # -----------------------------------------------------------------
    # Bullet: Query failure → empty mapping returned, no retry,
    # ``COLUMN_STATS_SQL`` fetch unaffected.
    # # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_mapping_with_no_retry(self, mocker):
        """Any exception → ``{}``, exactly one attempted call (no retry)."""
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Data API failure')

        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        # Exactly one attempted call; no retry on failure.
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_query_failure_does_not_block_independent_column_stats_call_site(self, mocker):
        """A fetcher-side failure is contained: an independent."""
        from awslabs.redshift_mcp_server import redshift as redshift_module
        from awslabs.redshift_mcp_server.consts import COLUMN_STATS_SQL
        from awslabs.redshift_mcp_server.redshift import _fetch_table_metadata

        # First call (the fetcher's batched ``TABLES_EXTRA_BY_PAIRS_SQL``) raises; second call (representing the independent ``COLUMN_STATS_SQL`` site) succeeds.
        column_stats_response = ({'Records': [['col_stats_record_marker']]}, 'qid_stats')
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement',
            side_effect=[Exception('fetcher failure'), column_stats_response],
        )

        # Step 1: the fetcher's batched call fails; the fetcher
        # swallows the exception and returns ``{}``.
        result = await _fetch_table_metadata(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}

        # Step 2: an independent ``_execute_protected_statement`` call representing the ``COLUMN_STATS_SQL`` site is unaffected by the prior failure.
        column_stats_sql = COLUMN_STATS_SQL.format(schema_table_pairs="('public','orders')")
        column_stats_result = await redshift_module._execute_protected_statement(
            cluster_identifier='c1',
            database_name='dev',
            sql=column_stats_sql,
        )

        assert column_stats_result == column_stats_response
        # The mock was called exactly twice — once by the fetcher
        # (which raised) and once by the independent column-stats site
        # (which succeeded). No retry on either path.
        assert mock_execute_protected.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_empty_pair_set_executes_zero_statements(self, mocker):
        """``_fetch_columns_by_pairs(pairs=set())`` returns ``{}`` and never calls the protected statement."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        result = await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs=set(),
        )

        assert result == {}
        mock_execute_protected.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_one_pair_executes_exactly_one_invocation(self, mocker):
        """One pair → exactly one batched call."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_parses_response_into_pair_keyed_columns_dict(
        self, mocker
    ):
        """Response rows parse into ``(schema, table) -> [column_dict]`` mapping."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        def _row(schema: str, table: str, col: str, pos: int) -> list[dict]:
            return [
                {'stringValue': 'dev'},
                {'stringValue': schema},
                {'stringValue': table},
                {'stringValue': col},
                {'longValue': pos},
                {'stringValue': None},
                {'stringValue': 'YES'},
                {'stringValue': 'integer'},
                {'longValue': None},
                {'longValue': None},
                {'longValue': None},
                {'stringValue': None},
                {'stringValue': 'lzo'},
                {'booleanValue': False},
                {'longValue': 0},
                {'stringValue': None},
                {'longValue': None},
            ]

        mock_execute_protected.return_value = (
            {
                'Records': [
                    _row('public', 'orders', 'id', 1),
                    _row('public', 'orders', 'amount', 2),
                    _row('tpch', 'lineitem', 'orderkey', 1),
                ]
            },
            'qid',
        )

        result = await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders'), ('tpch', 'lineitem')},
        )

        assert set(result.keys()) == {('public', 'orders'), ('tpch', 'lineitem')}
        # Two columns for orders (in source order); one column for lineitem.
        assert [c['column_name'] for c in result[('public', 'orders')]] == ['id', 'amount']
        assert [c['column_name'] for c in result[('tpch', 'lineitem')]] == ['orderkey']
        # Per-column dict matches the discover_columns record shape.
        first = result[('public', 'orders')][0]
        assert first['database_name'] == 'dev'
        assert first['data_type'] == 'integer'
        assert first['redshift_encoding'] == 'lzo'

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_swallows_execute_protected_exception_returns_empty(
        self, mocker
    ):
        """``_execute_protected_statement`` failure → ``{}``, no retry."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Data API failure')

        result = await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_swallows_row_parsing_exception_returns_empty(
        self, mocker
    ):
        """Malformed response rows → ``{}`` (no propagation)."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        # Two-column row truncates field unpacking and raises IndexError.
        mock_execute_protected.return_value = (
            {'Records': [[{'stringValue': 'dev'}, {'stringValue': 'public'}]]},
            'qid',
        )

        result = await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_logs_warning_on_execute_protected_exception(
        self, mocker
    ):
        """A warning is logged when the batched call fails."""
        from awslabs.redshift_mcp_server import redshift as redshift_module
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('boom')

        warning_spy = mocker.patch.object(redshift_module.logger, 'warning')

        result = await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='dev',
            pairs={('public', 'orders')},
        )

        assert result == {}
        assert warning_spy.call_count == 1
        warning_text = warning_spy.call_args.args[0]
        assert 'boom' in warning_text

    @pytest.mark.asyncio
    async def test_fetch_columns_by_pairs_binds_database_name_for_cross_db_isolation(self, mocker):
        """The connected database is bound on the SQL to scope columns to one database."""
        from awslabs.redshift_mcp_server.redshift import _fetch_columns_by_pairs

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _fetch_columns_by_pairs(
            cluster_identifier='c1',
            database_name='sample_data_dev',
            pairs={('tickit', 'sales')},
        )

        kwargs = mock_execute_protected.call_args.kwargs
        # Both UNION branches must filter by the connected database.
        assert 'database_name = :database_name' in kwargs['sql']
        assert 'redshift_database_name = :database_name' in kwargs['sql']
        assert kwargs['parameters'] == [{'name': 'database_name', 'value': 'sample_data_dev'}]

    def test_bare_table_candidates_sql_constant_is_importable_and_non_empty(self):
        """The constant must be importable and contain SQL text."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        assert isinstance(BARE_TABLE_CANDIDATES_SQL, str)
        assert BARE_TABLE_CANDIDATES_SQL.strip() != ''

    def test_format_with_names_list_renders_without_keyerror(self):
        """The constant must format with ``names_list`` cleanly."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list="'orders','customers'")

        assert isinstance(rendered, str)

    def test_bare_table_candidates_sql_format_leaves_no_unfilled_placeholders(self):
        """No leftover ``{...}`` format placeholders after substitution."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list="'orders'")

        # Bare format placeholders like ``{foo}`` should not remain.
        # ``{{`` and ``}}`` literal braces are escaped form and are
        # acceptable; this regex matches a single-brace placeholder.
        assert regex.search(r'(?<!\{)\{[^{}]+\}(?!\})', rendered) is None

    def test_format_substitutes_names_list_into_query(self):
        """The rendered text must contain the substituted name-list literal."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list="'orders','customers'")

        assert "'orders','customers'" in rendered

    def test_rendered_sql_uses_pg_class_and_pg_namespace(self):
        """Rendered SQL queries pg_class joined with pg_namespace."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list="'t'")
        upper = rendered.upper()

        assert 'PG_CLASS' in upper
        assert 'PG_NAMESPACE' in upper
        assert 'SELECT' in upper

    def test_rendered_sql_filters_by_relname(self):
        """Rendered SQL filters by ``c.relname``."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list="'t'")

        # The candidate-lookup is filtered by table name (relname).
        # Whitespace around the operator is allowed; exact-match the
        # core token sequence.
        assert 'c.relname' in rendered

    def test_render_name_list_empty_iterable_returns_empty_string(self):
        """Empty input → empty string, no quotes, no commas."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        assert _render_name_list([]) == ''
        assert _render_name_list(iter(())) == ''
        assert _render_name_list(set()) == ''

    def test_single_name_renders_as_one_quoted_literal(self):
        """One name → exactly one ``'<name>'`` literal."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(['orders'])

        assert rendered == "'orders'"

    def test_multiple_names_joined_by_comma_no_space(self):
        """Multiple names are joined by ``,`` with no surrounding whitespace."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(['orders', 'customers'])

        # Sorted ascending → ``'customers','orders'``.
        assert rendered == "'customers','orders'"

    def test_names_are_sorted_for_deterministic_output(self):
        """Different iteration orders produce byte-identical output."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        names = ['zeta', 'alpha', 'beta']
        from_list = _render_name_list(names)
        from_set = _render_name_list(set(names))
        from_reversed = _render_name_list(reversed(names))

        assert from_list == "'alpha','beta','zeta'"
        assert from_list == from_set == from_reversed

    def test_duplicate_names_are_deduplicated(self):
        """Repeated names render exactly once in the output."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(['orders', 'orders', 'customers'])

        assert rendered == "'customers','orders'"

    def test_single_quote_in_name_is_doubled(self):
        """A literal ``'`` in a name is doubled (``''``)."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(["o'reilly"])

        assert rendered == "'o''reilly'"

    def test_multiple_quotes_in_one_name_each_doubled(self):
        """Every literal ``'`` in a name is doubled, regardless of count."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(["a'b'c"])

        assert rendered == "'a''b''c'"

    def test_render_name_list_case_preserved_exactly(self):
        """Identifier case is preserved as written."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        rendered = _render_name_list(['Orders', 'customers'])

        # Sort is case-sensitive (uppercase before lowercase in ASCII),
        # but the values are emitted with original case preserved.
        assert "'Orders'" in rendered
        assert "'customers'" in rendered

    def test_render_name_list_repeated_calls_are_idempotent(self):
        """Same input → byte-identical output across calls."""
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        names = ['t2', 't1']

        first = _render_name_list(names)
        second = _render_name_list(names)

        assert first == second

    def test_rendered_fragment_drops_into_bare_table_candidates_sql(self):
        """The rendered fragment formats cleanly into the SQL constant."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL
        from awslabs.redshift_mcp_server.redshift import _render_name_list

        fragment = _render_name_list(['orders', 'customers'])

        rendered = BARE_TABLE_CANDIDATES_SQL.format(names_list=fragment)

        # No leftover ``{...}`` placeholders, and the literal name-list
        # appears in the rendered SQL.
        assert "'customers','orders'" in rendered

        assert regex.search(r'(?<!\{)\{[^{}]+\}(?!\})', rendered) is None

    @pytest.mark.asyncio
    async def test_empty_bare_names_executes_zero_statements(self, mocker):
        """Empty input → no batched query executed, returns ``{}``."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names=set(),
        )

        assert result == {}
        mock_execute_protected.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_name_executes_exactly_one_statement(self, mocker):
        """Single bare name → exactly one ``BARE_TABLE_CANDIDATES_SQL`` call."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_many_names_still_executes_exactly_one_statement(self, mocker):
        """50 distinct names → still exactly one batched call (no per-name query)."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        bare_names = {f't{i}' for i in range(50)}

        await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names=bare_names,
        )

        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_invokes_bare_table_candidates_sql_with_rendered_name_list(self, mocker):
        """SQL passed to the executor is the formatted constant."""
        from awslabs.redshift_mcp_server.consts import BARE_TABLE_CANDIDATES_SQL
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
            _render_name_list,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        bare_names = {'orders', 'customers'}

        await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names=bare_names,
        )

        kwargs = mock_execute_protected.call_args.kwargs
        expected_sql = BARE_TABLE_CANDIDATES_SQL.format(names_list=_render_name_list(bare_names))
        assert kwargs['sql'] == expected_sql
        assert kwargs['cluster_identifier'] == 'c1'
        assert kwargs['database_name'] == 'dev'

    @pytest.mark.asyncio
    async def test_parses_response_into_per_name_candidate_lists(self, mocker):
        """Response rows parse into ``name -> [(schema, table), ...]`` mapping."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'orders'}],
                    [{'stringValue': 'tpch'}, {'stringValue': 'orders'}],
                    [{'stringValue': 'public'}, {'stringValue': 'customers'}],
                ]
            },
            'qid',
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders', 'customers'},
        )

        assert set(result.keys()) == {'orders', 'customers'}
        assert sorted(result['orders']) == [('public', 'orders'), ('tpch', 'orders')]
        assert result['customers'] == [('public', 'customers')]

    @pytest.mark.asyncio
    async def test_zero_matches_returns_empty_list_per_name(self, mocker):
        """Bare names with zero matching rows map to empty lists, not missing keys."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = ({'Records': []}, 'qid')

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders', 'customers'},
        )

        # Both names are present in the mapping with empty lists; the
        # _resolve_ambiguities relies on this contract to emit the
        # not-found note.
        assert set(result.keys()) == {'orders', 'customers'}
        assert result['orders'] == []
        assert result['customers'] == []
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_partial_match_returns_empty_list_for_unmatched_names(self, mocker):
        """A bare name with no rows still appears in output with an empty list."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'orders'}],
                ]
            },
            'qid',
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders', 'missing_table'},
        )

        assert result['orders'] == [('public', 'orders')]
        # ``missing_table`` is present as an empty list — it was looked
        # up, just with zero matches.
        assert result['missing_table'] == []

    @pytest.mark.asyncio
    async def test_lookup_bare_table_candidates_swallows_execute_protected_exception_returns_empty(
        self, mocker
    ):
        """``_execute_protected_statement`` failure → ``{}``, no retry."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('Data API failure')

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        assert result == {}
        # No retry: the batched call is attempted exactly once per
        # ``lookup`` invocation, even when it raises.
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_lookup_bare_table_candidates_swallows_row_parsing_exception_returns_empty(
        self, mocker
    ):
        """Malformed response rows → ``{}`` (no propagation)."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        # Each record has zero columns → ``record[0].get(...)`` raises
        # ``IndexError`` during parsing.
        mock_execute_protected.return_value = (
            {'Records': [[]]},
            'qid',
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        assert result == {}
        assert mock_execute_protected.call_count == 1

    @pytest.mark.asyncio
    async def test_lookup_bare_table_candidates_logs_warning_on_execute_protected_exception(
        self, mocker
    ):
        """A warning is logged when the batched call fails."""
        from awslabs.redshift_mcp_server import redshift as redshift_module
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.side_effect = Exception('boom')

        warning_spy = mocker.patch.object(redshift_module.logger, 'warning')

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        assert result == {}
        assert warning_spy.call_count == 1
        warning_text = warning_spy.call_args.args[0]
        assert 'boom' in warning_text

    @pytest.mark.asyncio
    async def test_skips_rows_missing_schema_or_table(self, mocker):
        """Records with NULL schema or table values are skipped, not raised."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'orders'}],
                    # NULL row: ``stringValue`` absent → ``.get`` returns None.
                    [{}, {}],
                ]
            },
            'qid',
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        # The NULL row is silently dropped; the well-formed row is kept.
        assert result['orders'] == [('public', 'orders')]

    @pytest.mark.asyncio
    async def test_ignores_rows_for_names_not_in_input(self, mocker):
        """Rows for names outside the input set are not attached to output."""
        from awslabs.redshift_mcp_server.redshift import (
            _lookup_bare_table_candidates,
        )

        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute_protected.return_value = (
            {
                'Records': [
                    [{'stringValue': 'public'}, {'stringValue': 'orders'}],
                    # ``other_table`` is not in the requested set;
                    # defensive check that it is dropped.
                    [{'stringValue': 'public'}, {'stringValue': 'other_table'}],
                ]
            },
            'qid',
        )

        result = await _lookup_bare_table_candidates(
            cluster_identifier='c1',
            database_name='dev',
            bare_names={'orders'},
        )

        assert set(result.keys()) == {'orders'}
        assert result['orders'] == [('public', 'orders')]

    @staticmethod
    def _mock_candidate_lookup(mocker, candidates_by_name=None):
        """Build a mock async callable for injection as ``lookup_fn``.

        The returned object is an :class:`AsyncMock` that, when
        awaited, yields ``candidates_by_name`` (defaulting to ``{}``).
        This matches the shape of the real
        :func:`_lookup_bare_table_candidates` helper, where every
        requested bare name is pre-populated with a (possibly empty)
        candidate list.
        """
        return mocker.AsyncMock(return_value=candidates_by_name or {})

    @pytest.mark.asyncio
    async def test_schema_qualified_binds_with_no_note_and_no_lookup(self, mocker):
        """SCHEMA_QUALIFIED → resolved pair added, no note, lookup not called."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_SCHEMA_QUALIFIED,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(mocker)

        references = [
            TableReference(
                category=TABLE_REF_SCHEMA_QUALIFIED,
                table_name='orders',
                schema_name='tpch',
            ),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        assert resolved_pairs == {('tpch', 'orders')}
        assert notes == []
        # No bare references → candidate lookup is never invoked.
        mock_lookup.assert_not_called()

    @pytest.mark.asyncio
    async def test_bare_one_schema_binds_with_no_note(self, mocker):
        """BARE with 1 candidate match → bound, no note, single resolved pair."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={'orders': [('tpch', 'orders')]},
        )

        references = [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        assert resolved_pairs == {('tpch', 'orders')}
        assert notes == []
        mock_lookup.assert_called_once()

    @pytest.mark.asyncio
    async def test_bare_multiple_schemas_emits_single_note_and_all_pairs(self, mocker):
        """BARE with ≥2 candidate matches → 1 ambiguity note, ALL pairs resolved."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={
                'orders': [
                    ('public', 'orders'),
                    ('tpch', 'orders'),
                    ('staging', 'orders'),
                ],
            },
        )

        references = [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        # All matching pairs flow into resolved_pairs so each appears
        # in the downstream table_designs list.
        assert resolved_pairs == {
            ('public', 'orders'),
            ('tpch', 'orders'),
            ('staging', 'orders'),
        }
        # Exactly one ambiguity note that names the bare reference and
        # every matching schema.
        assert len(notes) == 1
        note = notes[0]
        assert 'orders' in note
        assert 'ambiguous' in note
        assert 'public' in note
        assert 'tpch' in note
        assert 'staging' in note
        # Connected database is surfaced so the user knows where we
        # looked.
        assert 'dev' in note

    @pytest.mark.asyncio
    async def test_bare_zero_schemas_emits_not_found_note_and_no_pair(self, mocker):
        """BARE with 0 candidate matches → 1 not-found note, no resolved pair."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        # The real lookup pre-populates input names with empty lists.
        # We mirror that contract here.
        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={'missing_table': []},
        )

        references = [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='missing_table',
            ),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        assert resolved_pairs == set()
        assert len(notes) == 1
        note = notes[0]
        assert 'missing_table' in note
        # The note should indicate the table was not found and name
        # the connected database we looked in.
        assert 'not found' in note
        assert 'dev' in note

    @pytest.mark.asyncio
    async def test_database_qualified_different_database_emits_cross_database_note(self, mocker):
        """DATABASE_QUALIFIED targeting a different database → cross-db note, no fetch."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(mocker)

        references = [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                table_name='orders',
                schema_name='tpch',
                database_name='prod_db',
            ),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        # Cross-database reference is NOT added to resolved pairs and
        # the metadata fetch in the wider pipeline therefore receives
        # no entry for it.
        assert resolved_pairs == set()
        assert len(notes) == 1
        note = notes[0]
        assert 'prod_db' in note
        assert 'dev' in note
        # The fully-qualified reference appears in the note so the
        # user can identify which reference was skipped.
        assert 'tpch' in note
        assert 'orders' in note
        # No bare references → no candidate-lookup call.
        mock_lookup.assert_not_called()

    @pytest.mark.asyncio
    async def test_database_qualified_connected_database_treated_as_schema_qualified(self, mocker):
        """DATABASE_QUALIFIED with database == connected → bound, no note."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_DATABASE_QUALIFIED,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(mocker)

        references = [
            TableReference(
                category=TABLE_REF_DATABASE_QUALIFIED,
                table_name='orders',
                schema_name='tpch',
                database_name='dev',
            ),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        # When the database matches, the reference resolves exactly
        # like a SCHEMA_QUALIFIED one: pair added, no note emitted
        # .
        assert resolved_pairs == {('tpch', 'orders')}
        assert notes == []
        mock_lookup.assert_not_called()

    @pytest.mark.asyncio
    async def test_repeated_identical_references_dedupe_notes(self, mocker):
        """Repeated identical not-found references collapse into one note."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={'missing_table': []},
        )

        references = [
            TableReference(
                category=TABLE_REF_BARE,
                table_name='missing_table',
            ),
            TableReference(
                category=TABLE_REF_BARE,
                table_name='missing_table',
            ),
            TableReference(
                category=TABLE_REF_BARE,
                table_name='missing_table',
            ),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        # Three identical bare references produce a single deduped
        # not-found note.
        assert resolved_pairs == set()
        assert len(notes) == 1
        assert 'missing_table' in notes[0]

    @pytest.mark.asyncio
    async def test_case_sensitive_distinct_names_produce_distinct_notes(self, mocker):
        """``Orders`` and ``orders`` are not equal → two distinct notes."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        # Both names map to empty candidate lists so each fires the not-found note path.
        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={'Orders': [], 'orders': []},
        )

        references = [
            TableReference(category=TABLE_REF_BARE, table_name='Orders'),
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        assert resolved_pairs == set()
        assert len(notes) == 2
        # Both surface forms appear, exactly once each, in their own
        # note string.
        assert sum('"Orders"' in note for note in notes) == 1
        assert sum('"orders"' in note for note in notes) == 1

    @pytest.mark.asyncio
    async def test_repeated_bare_references_use_single_lookup_call(self, mocker):
        """Multiple references to the same bare name share one lookup call."""
        from awslabs.redshift_mcp_server.redshift import (
            TABLE_REF_BARE,
            TableReference,
            _resolve_ambiguities,
        )

        mock_lookup = self._mock_candidate_lookup(
            mocker,
            candidates_by_name={'orders': [('tpch', 'orders')]},
        )

        references = [
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
            TableReference(category=TABLE_REF_BARE, table_name='orders'),
        ]

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=references,
            lookup_fn=mock_lookup,
        )

        assert resolved_pairs == {('tpch', 'orders')}
        assert notes == []
        # The resolver collapses bare-name lookups into a single
        # batched call regardless of how many references reuse the
        # same name.
        assert mock_lookup.call_count == 1
        # The lookup was passed the connected database verbatim and
        # the deduplicated name set.
        kwargs = mock_lookup.call_args.kwargs
        assert kwargs['cluster_identifier'] == 'c1'
        assert kwargs['database_name'] == 'dev'
        assert kwargs['bare_names'] == {'orders'}

    @pytest.mark.asyncio
    async def test_empty_references_returns_empty_outputs_no_lookup(self, mocker):
        """Empty input → empty resolved_pairs, empty notes, no lookup call."""
        from awslabs.redshift_mcp_server.redshift import _resolve_ambiguities

        mock_lookup = self._mock_candidate_lookup(mocker)

        resolved_pairs, notes = await _resolve_ambiguities(
            cluster_identifier='c1',
            connected_database_name='dev',
            references=[],
        )

        assert resolved_pairs == set()
        assert notes == []
        mock_lookup.assert_not_called()

    def test_suggestion_engine_is_idempotent_on_empty_inputs(self):
        """Two calls on empty inputs produce equal output."""
        from awslabs.redshift_mcp_server.redshift import (
            _generate_performance_suggestions,
        )

        first = _generate_performance_suggestions([], [])
        second = _generate_performance_suggestions([], [])

        assert first == second

    def test_suggestion_engine_is_idempotent_on_realistic_plan(self):
        """Two calls on a non-trivial plan produce equal output."""
        from awslabs.redshift_mcp_server.redshift import (
            _generate_performance_suggestions,
        )

        plan_nodes = [
            {'operation': 'XN Hash Join', 'distribution_type': 'DS_BCAST_INNER'},
            {'operation': 'XN Seq Scan', 'distribution_type': None},
            {'operation': 'XN Nested Loop', 'distribution_type': None},
        ]
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'EVEN',
                'redshift_estimated_row_count': 5_000_000,
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'data_type': 'integer',
                    },
                ],
            },
        ]

        first = _generate_performance_suggestions(plan_nodes, table_designs)
        second = _generate_performance_suggestions(plan_nodes, table_designs)

        assert first == second
        # Sanity: the realistic input actually produces suggestions, so
        # the equality check is non-trivial.
        assert len(first) > 0

    # ------------------------------------------------------------------
    # SORTKEY suppression
    # ------------------------------------------------------------------
    def test_sortkey_suggestion_suppressed_for_small_table(self):
        """Small table (< 100K rows) suppresses the SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'small_dim',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 50_000,
                'stats_sequential_scans': 5_000,
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

        assert not any('sequential scans' in s and 'SORTKEY' in s for s in suggestions), (
            f'expected no SORTKEY suggestion for small table; got {suggestions!r}'
        )

    def test_sortkey_suggestion_suppressed_for_diststyle_all(self):
        """``DISTSTYLE ALL`` suppresses the SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'replicated_dim',
                'redshift_diststyle': 'ALL',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 5_000,
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

        assert not any('sequential scans' in s and 'SORTKEY' in s for s in suggestions), (
            f'expected no SORTKEY suggestion for DISTSTYLE ALL table; got {suggestions!r}'
        )

    def test_sortkey_suggestion_suppressed_for_auto_all(self):
        """``AUTO(ALL)`` is treated like ALL and suppresses the SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'auto_replicated',
                'redshift_diststyle': 'AUTO(ALL)',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 5_000,
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

        assert not any('sequential scans' in s and 'SORTKEY' in s for s in suggestions), (
            f'expected no SORTKEY suggestion for AUTO(ALL) table; got {suggestions!r}'
        )

    def test_sortkey_suggestion_suppressed_when_seq_scans_zero(self):
        """``stats_sequential_scans == 0`` suppresses the SORTKEY suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'never_scanned',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 0,
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

        assert not any('sequential scans' in s and 'SORTKEY' in s for s in suggestions), (
            f'expected no SORTKEY suggestion when seq_scans == 0; got {suggestions!r}'
        )

    # ------------------------------------------------------------------
    # SORTKEY emission with all four conditions met
    # ------------------------------------------------------------------
    def test_sortkey_suggestion_emitted_when_all_conditions_met(self):
        """Emits SORTKEY suggestion when scans>1000, no SORTKEY, >=100K rows,."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
                'stats_sequential_scans': 12_345,
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

        # Emission text MUST include the scan count (formatted with thousands
        # separators by the engine).
        assert any(
            '12,345 sequential scans' in s and 'SORTKEY' in s and 'events' in s
            for s in suggestions
        ), f'expected SORTKEY suggestion naming scan count; got {suggestions!r}'

    # ------------------------------------------------------------------
    # distribution_type keyword fallback
    # ------------------------------------------------------------------
    def test_keyword_fallback_broadcast_emits_suggestion(self):
        """``distribution_type`` unset + ``Broadcast`` keyword in operation."""
        nodes = [
            {
                'operation': 'XN Network Broadcast',
                'distribution_type': None,
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert any('broadcast' in s.lower() and 'DISTKEY' in s for s in suggestions), (
            f'expected broadcast suggestion via keyword fallback; got {suggestions!r}'
        )

    def test_keyword_fallback_distribute_emits_suggestion(self):
        """``distribution_type`` unset + ``Distribute`` keyword in operation."""
        nodes = [
            {
                'operation': 'XN Network Distribute',
                'distribution_type': None,
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert any('redistribution' in s.lower() and 'DISTKEY' in s for s in suggestions), (
            f'expected redistribution suggestion via keyword fallback; got {suggestions!r}'
        )

    def test_keyword_fallback_gather_emits_suggestion(self):
        """``distribution_type`` unset + ``Gather`` keyword in operation."""
        nodes = [
            {
                'operation': 'Gather Motion 4:1',
                'distribution_type': None,
            }
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert any('gather' in s.lower() and 'DISTKEY' in s for s in suggestions), (
            f'expected gather suggestion via keyword fallback; got {suggestions!r}'
        )

    def test_keyword_fallback_no_keyword_no_suggestion(self):
        """``distribution_type`` unset + no redistribution keyword emits no."""
        nodes = [
            {
                'operation': 'Hash Join',
                'distribution_type': None,
            },
            {
                'operation': 'Seq Scan',
                'distribution_type': None,
            },
            {
                'operation': 'XN Aggregate',
                'distribution_type': None,
            },
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        # None of the engine's redistribution suggestions should fire.
        for s in suggestions:
            lowered = s.lower()
            assert 'broadcast' not in lowered, f'unexpected broadcast suggestion: {s!r}'
            assert 'redistribution' not in lowered, f'unexpected redistribution suggestion: {s!r}'
            assert 'gather' not in lowered, f'unexpected gather suggestion: {s!r}'

    # ------------------------------------------------------------------
    # Carried-over rules
    # ------------------------------------------------------------------
    def test_carried_over_nested_loop_rule(self):
        """``Nested Loop`` operation still emits the existing suggestion."""
        nodes = [{'operation': 'Nested Loop'}]
        suggestions = _generate_performance_suggestions(nodes, [])

        assert any('Nested Loop' in s for s in suggestions), (
            f'expected Nested Loop suggestion; got {suggestions!r}'
        )

    def test_carried_over_low_correlation_rule(self):
        """Low ``stats_correlation`` on a non-sortkey column still emits the."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 5_000_000,
                'columns': [
                    {
                        'column_name': 'order_date',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'stats_correlation': 0.05,
                        'stats_n_distinct': 1_000_000,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any(
            'order_date' in s and 'correlation' in s and 'SORTKEY' in s for s in suggestions
        ), f'expected low-correlation suggestion; got {suggestions!r}'

    def test_carried_over_low_cardinality_distkey_rule(self):
        """Low-cardinality DISTKEY column still emits the existing."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'events',
                'redshift_diststyle': 'KEY',
                'redshift_estimated_row_count': 10_000_000,
                'columns': [
                    {
                        'column_name': 'status',
                        'redshift_encoding': 'lzo',
                        'redshift_sortkey_position': 0,
                        'redshift_is_distkey': True,
                        'stats_n_distinct': 5,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any('DISTKEY column status' in s and 'low cardinality' in s for s in suggestions), (
            f'expected low-cardinality DISTKEY suggestion; got {suggestions!r}'
        )

    def test_carried_over_high_null_sortkey_rule(self):
        """High-NULL SORTKEY column still emits the existing suggestion."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'orders',
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

        assert any('SORTKEY column deleted_at' in s and 'NULL' in s for s in suggestions), (
            f'expected high-NULL SORTKEY suggestion; got {suggestions!r}'
        )

    def test_carried_over_wide_uncompressed_columns_rule(self):
        """Wide uncompressed varchar columns still emit the existing."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'logs',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'payload',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'data_type': 'character varying',
                        'stats_avg_width': 350,
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any(
            'Wide columns' in s and 'payload' in s and 'compression' in s.lower()
            for s in suggestions
        ), f'expected wide-uncompressed-column suggestion; got {suggestions!r}'

    def test_carried_over_raw_encoding_rule(self):
        """RAW (``none``) encoding on non-first-sortkey, non-boolean columns."""
        table_designs = [
            {
                'schema_name': 'public',
                'table_name': 'users',
                'redshift_diststyle': 'KEY',
                'columns': [
                    {
                        'column_name': 'id',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 1,  # exempt: first SORTKEY
                        'data_type': 'integer',
                    },
                    {
                        'column_name': 'email',
                        'redshift_encoding': 'none',
                        'redshift_sortkey_position': 0,
                        'data_type': 'character varying',
                    },
                ],
            }
        ]
        suggestions = _generate_performance_suggestions([], table_designs)

        assert any('email' in s and 'compression' in s.lower() for s in suggestions), (
            f'expected RAW-encoding compression suggestion; got {suggestions!r}'
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------
    def test_identical_suggestion_text_appears_at_most_once(self):
        """Identical suggestion text emitted by multiple rule paths is."""
        # Two nodes that produce the same broadcast suggestion text
        # (operation strings are identical, so the ``f'... in {operation}.'``
        # template renders to the same string).
        nodes = [
            {'operation': 'Hash Join', 'distribution_type': 'DS_BCAST_INNER'},
            {'operation': 'Hash Join', 'distribution_type': 'DS_BCAST_INNER'},
            {'operation': 'Hash Join', 'distribution_type': 'DS_BCAST_INNER'},
        ]
        suggestions = _generate_performance_suggestions(nodes, [])

        # Exactly one broadcast suggestion despite three matching nodes.
        broadcast_suggestions = [s for s in suggestions if 'broadcast' in s.lower()]
        assert len(broadcast_suggestions) == 1, (
            f'expected single deduplicated broadcast suggestion; got {broadcast_suggestions!r}'
        )

        # And the global list has no duplicates.
        assert len(suggestions) == len(set(suggestions)), (
            f'expected no duplicate suggestions overall; got {suggestions!r}'
        )

    @pytest.mark.asyncio
    async def test_describe_execution_plan_enriches_columns_with_stats(self, mocker):
        """A matching column-stats record is merged into the referenced table's columns."""
        mock_execute = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        explain_response = (
            {
                'Records': [
                    [{'stringValue': 'XN Seq Scan on users  (cost=0.00..1.00 rows=1 width=4)'}]
                ]
            },
            'explain-query-id',
        )
        candidates_response = (
            {'Records': [[{'stringValue': 'public'}, {'stringValue': 'users'}]]},
            'candidates-query-id',
        )
        tables_extra_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'KEY'},
                        {'longValue': 1000},
                        {'longValue': 5},
                        {'longValue': 100},
                        {'longValue': 0},
                        {'longValue': 0},
                        {'longValue': 0},
                    ]
                ]
            },
            'tables-extra-query-id',
        )
        # Non-empty column stats for public.users.id drives the stats loop and enrichment.
        column_stats_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'doubleValue': -0.5},
                        {'doubleValue': 0.0},
                        {'longValue': 4},
                        {'doubleValue': 0.95},
                        {'stringValue': None},
                        {'stringValue': None},
                        {'stringValue': '1,2,3'},
                    ]
                ]
            },
            'column-stats-query-id',
        )
        columns_by_pairs_response = (
            {
                'Records': [
                    [
                        {'stringValue': 'dev'},
                        {'stringValue': 'public'},
                        {'stringValue': 'users'},
                        {'stringValue': 'id'},
                        {'longValue': 1},
                        {'stringValue': None},
                        {'stringValue': 'YES'},
                        {'stringValue': 'integer'},
                        {'longValue': None},
                        {'longValue': None},
                        {'longValue': None},
                        {'stringValue': None},
                        {'stringValue': 'lzo'},
                        {'booleanValue': False},
                        {'longValue': 0},
                        {'stringValue': None},
                        {'longValue': None},
                    ]
                ]
            },
            'columns-query-id',
        )
        mock_execute.side_effect = [
            explain_response,
            candidates_response,
            tables_extra_response,
            column_stats_response,
            columns_by_pairs_response,
        ]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT id FROM users')

        col = result['table_designs'][0]['columns'][0]
        assert col['column_name'] == 'id'
        assert col['stats_n_distinct'] == -0.5
        assert col['stats_correlation'] == 0.95
        assert col['stats_histogram_bounds'] == '1,2,3'

    @pytest.mark.asyncio
    async def test_describe_execution_plan_soft_fails_on_unparseable_references(self, mocker):
        """Unparseable table references degrade gracefully; the plan still returns."""
        mock_execute = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        mock_execute.return_value = (
            {'Records': [[{'stringValue': 'XN Seq Scan  (cost=0.00..1.00 rows=1 width=4)'}]]},
            'explain-query-id',
        )
        # A 4-part dotted table name makes _extract_sql_references raise; the
        # pipeline catches it, sets references=[], and still returns the plan.
        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT 1 FROM a.b.c.d')

        assert result['query_id'] == 'explain-query-id'
        assert result['table_designs'] == []
        assert len(result['plan_nodes']) == 1

    @pytest.mark.asyncio
    async def test_describe_execution_plan_continues_when_column_stats_fetch_fails(self, mocker):
        """A column-stats fetch failure is swallowed; the rest of the response is intact."""
        mock_execute = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_protected_statement'
        )
        explain_response = (
            {
                'Records': [
                    [{'stringValue': 'XN Seq Scan on users  (cost=0.00..1.00 rows=1 width=4)'}]
                ]
            },
            'explain-query-id',
        )
        candidates_response = (
            {'Records': [[{'stringValue': 'public'}, {'stringValue': 'users'}]]},
            'candidates-query-id',
        )
        empty_response = ({'Records': []}, 'empty-query-id')
        mock_execute.side_effect = [
            explain_response,
            candidates_response,
            empty_response,  # table metadata
            Exception('column stats boom'),  # column-stats fetch fails
            empty_response,  # columns fetch
        ]

        result = await describe_execution_plan('test-cluster', 'dev', 'SELECT id FROM users')

        assert result['query_id'] == 'explain-query-id'
        assert len(result['table_designs']) == 1
