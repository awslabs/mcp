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

import asyncio
import pytest
import sqlglot
import time
from awslabs.redshift_mcp_server import redshift as redshift_module
from awslabs.redshift_mcp_server.consts import (
    MAX_SQL_LEN,
    QUERY_LONG_POLL,
    SESSION_KEEPALIVE_MAX,
)
from awslabs.redshift_mcp_server.models import RedshiftCluster
from awslabs.redshift_mcp_server.redshift import (
    _APP_NAME_SQL,
    _SESSION_DRAIN,
    RedshiftClientManager,
    RedshiftTransactionManager,
    _begin_transaction,
    _execute_batch,
    _execute_batch_for_statement,
    _execute_standalone_statement,
    _execute_statement_fallback_no_batch,
    _execute_statement_in_transaction,
    _is_no_batch,
    _latch_no_batch,
    _no_batch_active,
    _resolve_int_env,
    _resolve_transaction_action,
    _sql_identifier,
    discover_clusters,
    discover_columns,
    discover_databases,
    discover_schemas,
    discover_tables,
    execute_query,
    max_open_transactions_per_target,
    session_keepalive,
)
from botocore.config import Config
from botocore.exceptions import ClientError
from mcp.server.mcpserver.exceptions import ToolError
from sqlglot import exp
from typing import Any


def _fake_cluster(identifier='test-cluster', type='provisioned', status='available'):
    """Build a RedshiftCluster for mocking discover_clusters() return values."""
    return RedshiftCluster.model_validate(
        {'identifier': identifier, 'type': type, 'status': status, 'database_name': 'dev'}
    )


def _fake_sub(index, status='FINISHED', has_result_set=False, error=None):
    """Build one sub-statement of a batch, numbered as the Data API numbers them."""
    sub = {'Id': f'batch-id:{index + 1}', 'Status': status, 'HasResultSet': has_result_set}
    if error is not None:
        sub['Error'] = error
    return sub


def _fake_batch(subs, status=None, error=None, session_id=None):
    """Build the terminal batch response that _execute_batch() returns.

    Each entry of `subs` is either a status string or the keyword arguments for _fake_sub.
    The batch status defaults to whatever its statements imply.
    """
    sub_statements = [
        _fake_sub(i, **(sub if isinstance(sub, dict) else {'status': sub}))
        for i, sub in enumerate(subs)
    ]
    if status is None:
        status = (
            'FINISHED' if all(sub['Status'] == 'FINISHED' for sub in sub_statements) else 'FAILED'
        )
    batch = {'Id': 'batch-id', 'Status': status, 'SubStatements': sub_statements}
    if error is not None:
        batch['Error'] = error
    if session_id is not None:
        batch['SessionId'] = session_id
    return batch


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Clear the batch-denied latch and any open transaction, both module state."""
    redshift_module._no_batch_since = None
    redshift_module.transaction_manager._transactions.clear()
    redshift_module.transaction_manager._locks.clear()
    yield
    redshift_module._no_batch_since = None
    redshift_module.transaction_manager._transactions.clear()
    redshift_module.transaction_manager._locks.clear()


def _batch_denied_error(action='redshift-data:BatchExecuteStatement'):
    """Build the AccessDeniedException the Data API raises for a denied action."""
    return ClientError(
        {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': (
                    'User: arn:aws:sts::1:assumed-role/r/s is not authorized to perform: '
                    f'{action} on resource: arn:aws:redshift:us-east-1:1:cluster:c'
                ),
            }
        },
        'BatchExecuteStatement',
    )


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
    """Tests for _execute_standalone_statement function."""

    @pytest.mark.asyncio
    async def test_read_is_wrapped_in_a_read_only_transaction(self, mocker):
        """A caller's read runs as one batch wrapped in BEGIN READ ONLY ... ROLLBACK."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', 'FINISHED', 'FINISHED']),
        )

        _, query_id = await _execute_standalone_statement(
            'test-cluster', 'test-db', 'SELECT 1', enforce_read_only=True
        )

        assert mock_execute_batch.call_count == 1
        assert mock_execute_batch.call_args[1]['sqls'] == [
            _APP_NAME_SQL,
            'BEGIN READ ONLY',
            'SELECT 1',
            'ROLLBACK',
        ]
        # The caller's statement is the third of four, so its result is the one reported.
        assert query_id == 'batch-id:3'

    @pytest.mark.asyncio
    async def test_write_is_not_wrapped(self, mocker):
        """A write runs unwrapped, so non-transactional statements are not broken."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED']),
        )

        _, query_id = await _execute_standalone_statement(
            'test-cluster',
            'test-db',
            'CREATE TABLE t (id int)',
            enforce_read_only=False,
        )

        assert mock_execute_batch.call_args[1]['sqls'] == [
            _APP_NAME_SQL,
            'CREATE TABLE t (id int)',
        ]
        assert query_id == 'batch-id:2'

    @pytest.mark.asyncio
    async def test_this_servers_own_sql_runs_unwrapped_under_the_read_only_guard(self, mocker):
        """Discovery keeps the guard but drops the wrapper, which is its own combination."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED']),
        )

        await _execute_standalone_statement(
            'test-cluster',
            'test-db',
            'SHOW DATABASES;',
            enforce_read_only=False,
        )

        assert mock_execute_batch.call_args[1]['sqls'] == [_APP_NAME_SQL, 'SHOW DATABASES;']

    @pytest.mark.asyncio
    async def test_read_write_rejects_multi_statement(self, mocker):
        """Read-write still enforces single-statement: a stacked submission is rejected."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            await _execute_standalone_statement(
                'test-cluster',
                'test-db',
                'CREATE TABLE t (id int); DROP TABLE t;',
                enforce_read_only=False,
            )

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_denylisted_statements_rejected(self, mocker):
        """Read-only mode rejects deny-listed statement types before execution."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        for sql in ('UNLOAD ($$SELECT 1$$) TO $$s3://b/k$$ IAM_ROLE $$r$$', 'VACUUM t', 'COMMIT'):
            with pytest.raises(ToolError):
                await _execute_standalone_statement('test-cluster', 'test-db', sql)

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_oversized_sql_rejected(self, mocker):
        """SQL beyond MAX_SQL_LEN is rejected before parsing."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='exceeds the maximum allowed length'):
            await _execute_standalone_statement(
                'test-cluster', 'test-db', 'SELECT ' + 'x' * MAX_SQL_LEN
            )

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_cluster_not_found_when_none_discovered(self, mocker):
        """An unknown cluster is named in the error, with the tool that lists valid ones."""
        mocker.patch('awslabs.redshift_mcp_server.redshift.discover_clusters', return_value=[])

        with pytest.raises(ToolError, match='Cluster nonexistent-cluster not found'):
            await _execute_standalone_statement('nonexistent-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_cluster_not_in_list(self, mocker):
        """A cluster missing from a non-empty discovery result is still not found."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster(identifier='other-cluster')],
        )

        with pytest.raises(ToolError, match='Cluster target-cluster not found'):
            await _execute_standalone_statement('target-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_results_are_fetched_for_the_callers_statement_only(self, mocker):
        """The result comes from the caller's sub-statement, not the batch or a wrapper."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                ['FINISHED', 'FINISHED', {'has_result_set': True}, 'FINISHED']
            ),
        )
        expected = {
            'Records': [[{'longValue': 1}]],
            'ColumnMetadata': [{'name': 'one'}],
        }
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = expected
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        results_response, query_id = await _execute_standalone_statement(
            'test-cluster', 'test-db', 'SELECT 1 AS one'
        )

        mock_data_client.get_statement_result.assert_called_once_with(Id='batch-id:3')
        assert results_response == expected
        assert query_id == 'batch-id:3'

    @pytest.mark.asyncio
    async def test_no_result_set_returns_empty_without_asking_for_results(self, mocker):
        """GetStatementResult raises for a statement without a result set, so it is skipped."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED']),
        )
        mock_data_client = mocker.Mock()
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        results_response, _ = await _execute_standalone_statement(
            'test-cluster',
            'test-db',
            'SET timezone TO UTC',
            enforce_read_only=False,
        )

        mock_data_client.get_statement_result.assert_not_called()
        assert results_response == {'Records': [], 'ColumnMetadata': []}

    @pytest.mark.asyncio
    async def test_failed_caller_statement_reports_its_own_error(self, mocker):
        """The batch-level error only names indices, so the failing statement's text is used."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                [
                    'FINISHED',
                    'FINISHED',
                    {'status': 'FAILED', 'error': 'ERROR: relation "nope" does not exist'},
                    'FINISHED',
                ]
            ),
        )

        with pytest.raises(ToolError, match='relation "nope" does not exist'):
            await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT * FROM nope')

    @pytest.mark.asyncio
    async def test_a_refused_connection_reports_the_reason_the_batch_carries(self, mocker):
        """Nothing ran, so every statement holds a placeholder and only the batch knows why."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                [
                    {'status': 'ABORTED', 'error': 'Connection or an prior query failed.'},
                    {'status': 'ABORTED', 'error': 'Connection or an prior query failed.'},
                ],
                error=(
                    'FATAL: Cannot connect to shared database "awsdatacatalog" created from '
                    'Data Catalog ARN. Connect to a database in your cluster ... instead'
                ),
            ),
        )

        with pytest.raises(ToolError, match='Cannot connect to shared database'):
            await _execute_standalone_statement(
                'test-cluster', 'awsdatacatalog', 'SHOW SCHEMAS', enforce_read_only=False
            )

    @pytest.mark.asyncio
    async def test_failed_caller_statement_without_an_error_field(self, mocker):
        """A failure the Data API does not explain still fails, and says so."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', {'status': 'ABORTED'}, 'FINISHED']),
        )

        with pytest.raises(ToolError, match='Statement failed: Unknown error'):
            await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_failed_wrapper_fails_the_call_even_though_the_read_ran(self, mocker):
        """A failed ROLLBACK means the read may not have been discarded, so it is not trusted."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                [
                    'FINISHED',
                    'FINISHED',
                    {'has_result_set': True},
                    {'status': 'FAILED', 'error': 'ERROR: ROLLBACK went wrong'},
                ]
            ),
        )

        with pytest.raises(ToolError, match='ROLLBACK went wrong'):
            await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_parameters_are_passed_through_to_the_batch(self, mocker):
        """Only the caller's statement carries placeholders, so the batch takes them as given."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', 'FINISHED', 'FINISHED']),
        )
        parameters = [{'name': 'answer', 'value': '365'}]

        await _execute_standalone_statement(
            'test-cluster', 'test-db', 'SELECT :answer', parameters=parameters
        )

        assert mock_execute_batch.call_args[1]['parameters'] == parameters


class TestExecuteBatch:
    """Tests for _execute_batch function."""

    def _data_client(self, mocker, submit=None, describes=None):
        """Wire a Data API client whose submit and describe responses are scripted."""
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = submit or {
            'Id': 'batch-id',
            'Status': 'FINISHED',
        }
        if describes is not None:
            mock_data_client.describe_statement.side_effect = describes
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )
        return mock_data_client

    @pytest.mark.asyncio
    async def test_a_minted_session_is_reported_before_the_batch_settles(self, mocker):
        """A batch that mints a session and then fails still leaves that session alive.

        The id is recorded at submit rather than on return, so the caller can end a session
        belonging to a transaction that never opened.
        """
        self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'SessionId': 'session-1'},
            describes=[_fake_batch(['FINISHED', 'FAILED'])],
        )
        opened_session: list[str] = []

        with pytest.raises(ToolError, match='Statement failed'):
            await _execute_batch_for_statement(
                _fake_cluster(),
                'test-cluster',
                'test-db',
                [_APP_NAME_SQL, 'BEGIN'],
                caller_index=1,
                session_sink=opened_session,
                session_keepalive=60,
            )

        assert opened_session == ['session-1']

    @pytest.mark.asyncio
    async def test_batch_runs_with_auto_commit_and_no_data_api_transaction(self, mocker):
        """TRANSACTION mode would commit at batch end and defeat the read-only wrapper."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED', 'FINISHED'])]
        )

        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', [_APP_NAME_SQL, 'SELECT 1']
        )

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert request['ExecutionMode'] == 'AUTO_COMMIT'
        assert request['Sqls'] == [_APP_NAME_SQL, 'SELECT 1']
        assert request['Database'] == 'test-db'

    @pytest.mark.asyncio
    async def test_provisioned_and_serverless_are_addressed_differently(self, mocker):
        """A workgroup is not a cluster, and the Data API takes them under different names."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])
        assert mock_data_client.batch_execute_statement.call_args[1]['ClusterIdentifier'] == (
            'test-cluster'
        )

        await _execute_batch(
            _fake_cluster(type='serverless'), 'test-workgroup', 'test-db', ['SELECT 1']
        )
        assert mock_data_client.batch_execute_statement.call_args[1]['WorkgroupName'] == (
            'test-workgroup'
        )

    @pytest.mark.asyncio
    async def test_unknown_cluster_type_is_a_crash_not_a_tool_error(self, mocker):
        """Discovery only sets provisioned or serverless, so anything else is this server's bug."""
        self._data_client(mocker)

        with pytest.raises(Exception, match='Unknown cluster type: unknown-type') as failure:
            await _execute_batch(
                _fake_cluster(type='unknown-type'), 'test-cluster', 'test-db', ['SELECT 1']
            )

        assert not isinstance(failure.value, ToolError)

    @pytest.mark.asyncio
    async def test_parameters_are_sent_only_when_present(self, mocker):
        """An empty Parameters list is not the same as omitting it, so it is omitted."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])
        assert 'Parameters' not in mock_data_client.batch_execute_statement.call_args[1]

        parameters = [{'name': 'answer', 'value': '365'}]
        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', ['SELECT :answer'], parameters=parameters
        )
        assert mock_data_client.batch_execute_statement.call_args[1]['Parameters'] == parameters

    @pytest.mark.asyncio
    async def test_a_session_replaces_the_cluster_and_database(self, mocker):
        """A session already holds the connection, and the API refuses to be told again."""
        mock_data_client = self._data_client(mocker, describes=[_fake_batch(['FINISHED'])])

        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'], session_id='session-1'
        )

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert request['SessionId'] == 'session-1'
        assert 'ClusterIdentifier' not in request
        assert 'WorkgroupName' not in request
        assert 'Database' not in request

    @pytest.mark.asyncio
    async def test_a_keepalive_is_sent_when_given(self, mocker):
        """It is what mints a session on an open, and what restarts the idle clock later."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['BEGIN'])
        assert (
            'SessionKeepAliveSeconds'
            not in (mock_data_client.batch_execute_statement.call_args[1])
        )

        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', ['BEGIN'], session_keepalive=42
        )
        assert (
            mock_data_client.batch_execute_statement.call_args[1]['SessionKeepAliveSeconds'] == 42
        )

    @pytest.mark.asyncio
    async def test_a_settled_submit_still_describes_for_the_sub_statement_ids(self, mocker):
        """BatchExecuteStatement never returns SubStatements, and their ids reach the results."""
        mock_data_client = self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'FINISHED'},
            describes=[_fake_batch(['FINISHED', 'FINISHED'])],
        )

        batch = await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', [_APP_NAME_SQL, 'SELECT 1']
        )

        mock_data_client.describe_statement.assert_called_once_with(Id='batch-id')
        assert [sub['Id'] for sub in batch['SubStatements']] == ['batch-id:1', 'batch-id:2']

    @pytest.mark.asyncio
    async def test_a_failed_batch_is_returned_rather_than_raised(self, mocker):
        """Only the caller knows which statement was its own, so only it can explain a failure."""
        self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'FAILED'},
            describes=[
                _fake_batch([{'status': 'FAILED', 'error': 'ERROR: nope'}], status='FAILED')
            ],
        )

        batch = await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])

        assert batch['Status'] == 'FAILED'
        assert batch['SubStatements'][0]['Error'] == 'ERROR: nope'

    @pytest.mark.asyncio
    async def test_long_polls_both_the_submit_and_each_describe(self, mocker):
        """The long poll is what keeps a fast batch down to one round trip."""
        mock_data_client = self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'STARTED'},
            describes=[
                {'Id': 'batch-id', 'Status': 'PICKED'},
                _fake_batch(['FINISHED']),
            ],
        )
        mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])

        assert mock_data_client.batch_execute_statement.call_args[1]['WaitTimeSeconds'] == (
            QUERY_LONG_POLL
        )
        for call in mock_data_client.describe_statement.call_args_list:
            assert call[1]['WaitTimeSeconds'] == QUERY_LONG_POLL

    @pytest.mark.asyncio
    async def test_long_polling_can_be_disabled(self, mocker):
        """Zero means the parameter is omitted, not sent as zero."""
        mock_data_client = self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'STARTED'},
            describes=[_fake_batch(['FINISHED'])],
        )
        mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'], query_long_poll=0
        )

        assert 'WaitTimeSeconds' not in mock_data_client.batch_execute_statement.call_args[1]
        assert 'WaitTimeSeconds' not in mock_data_client.describe_statement.call_args[1]

    @pytest.mark.asyncio
    async def test_long_poll_limit_falls_back_to_plain_polling(self, mocker):
        """The account-wide waiting-request limit must not fail a statement that is running."""
        mock_data_client = self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'STARTED'},
            describes=[
                ClientError(
                    {'Error': {'Code': 'ActiveWaitingRequestsExceededException'}},
                    'DescribeStatement',
                ),
                _fake_batch(['FINISHED']),
            ],
        )
        mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])

        calls = mock_data_client.describe_statement.call_args_list
        assert calls[0][1]['WaitTimeSeconds'] == QUERY_LONG_POLL
        assert 'WaitTimeSeconds' not in calls[1][1]

    @pytest.mark.asyncio
    async def test_other_client_errors_propagate(self, mocker):
        """Only the waiting-request limit is recoverable; everything else is the caller's problem."""
        self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'STARTED'},
            describes=[
                ClientError({'Error': {'Code': 'ValidationException'}}, 'DescribeStatement')
            ],
        )
        mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        with pytest.raises(ClientError):
            await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'])

    @pytest.mark.asyncio
    async def test_timeout_is_reported_as_an_anticipated_failure(self, mocker):
        """A batch that never settles is the caller's to know about, not a crash."""
        mock_data_client = self._data_client(
            mocker, submit={'Id': 'batch-id', 'Status': 'STARTED'}
        )

        # A zero budget is spent by the time the first non-terminal status is read.
        with pytest.raises(ToolError, match='Statement timed out after 0 seconds'):
            await _execute_batch(
                _fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1'], query_timeout=0
            )

        mock_data_client.describe_statement.assert_not_called()

    @pytest.mark.asyncio
    async def test_data_api_calls_do_not_block_the_event_loop(self, mocker):
        """boto3 is synchronous and a long poll parks the thread for up to 30 seconds."""
        submitted = asyncio.Event()

        def blocking_submit(**_kwargs):
            time.sleep(0.05)
            return {'Id': 'batch-id', 'Status': 'FINISHED'}

        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = blocking_submit
        mock_data_client.describe_statement.return_value = _fake_batch(['FINISHED'])
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        async def ticker():
            # Runs only if the event loop is free while boto3 is blocking in its thread.
            submitted.set()

        _, _ = await asyncio.gather(
            _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['SELECT 1']),
            ticker(),
        )

        assert submitted.is_set()


class TestConcurrency:
    """Concurrent calls against one cluster and database."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_each_get_their_own_batch(self, mocker):
        """Nothing is shared between calls, so a read never waits on an unrelated one."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = [
            {'Id': f'batch-{i}', 'Status': 'FINISHED'} for i in range(5)
        ]
        mock_data_client.describe_statement.side_effect = [
            {
                'Id': f'batch-{i}',
                'Status': 'FINISHED',
                'SubStatements': [
                    {'Id': f'batch-{i}:1', 'Status': 'FINISHED', 'HasResultSet': False},
                    {'Id': f'batch-{i}:2', 'Status': 'FINISHED', 'HasResultSet': False},
                    {'Id': f'batch-{i}:3', 'Status': 'FINISHED', 'HasResultSet': True},
                    {'Id': f'batch-{i}:4', 'Status': 'FINISHED', 'HasResultSet': False},
                ],
            }
            for i in range(5)
        ]
        mock_data_client.get_statement_result.side_effect = lambda Id: {
            'Records': [[{'stringValue': Id}]],
            'ColumnMetadata': [{'name': 'id'}],
        }
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        results = await asyncio.gather(
            *[
                _execute_standalone_statement('test-cluster', 'test-db', f'SELECT {i}')
                for i in range(5)
            ]
        )

        # Every call got its own batch and its own statement's result back.
        assert sorted(query_id for _, query_id in results) == [f'batch-{i}:3' for i in range(5)]
        assert mock_data_client.batch_execute_statement.call_count == 5

    @pytest.mark.asyncio
    async def test_no_session_is_ever_created(self, mocker):
        """A session is what serialized calls before; a read now needs none."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {
            'Id': 'batch-id',
            'Status': 'FINISHED',
        }
        mock_data_client.describe_statement.return_value = _fake_batch(
            ['FINISHED', 'FINISHED', 'FINISHED', 'FINISHED']
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert 'SessionId' not in request
        assert 'SessionKeepAliveSeconds' not in request


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
        assert cluster.identifier == 'test-cluster'
        assert cluster.type == 'provisioned'
        assert cluster.status == 'available'
        assert cluster.database_name == 'dev'
        assert cluster.endpoint == 'test.redshift.amazonaws.com'
        assert cluster.port == 5439
        assert cluster.node_type == 'dc2.large'
        assert cluster.number_of_nodes == 2
        assert cluster.tags == {'env': 'test'}

        # Verify minimal cluster (with defaults applied)
        minimal = result[1]
        assert minimal.identifier == 'minimal-cluster'
        assert minimal.type == 'provisioned'
        assert minimal.status == 'available'
        assert minimal.database_name == 'dev'  # default to 'dev'
        assert minimal.endpoint == 'minimal.redshift.amazonaws.com'
        assert minimal.port == 5439
        assert minimal.node_type == 'ra3.xlplus'
        assert minimal.number_of_nodes == 1
        assert minimal.tags == {}

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
        """Test discover_clusters with serverless workgroups.

        The serverless database_name is always reported as the built-in 'dev';
        """
        # Mock redshift client (empty response)
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        # Mock serverless client with one workgroup
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
        assert workgroup.identifier == 'test-workgroup'
        assert workgroup.type == 'serverless'
        assert workgroup.status == 'AVAILABLE'
        assert workgroup.database_name == 'dev'
        assert workgroup.endpoint == 'test.serverless.amazonaws.com'
        assert workgroup.port == 5439
        assert workgroup.node_type is None
        assert workgroup.number_of_nodes is None
        assert workgroup.encrypted is True
        assert workgroup.tags == {'team': 'data'}

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_empty_subnet_ids(self, mocker):
        """Serverless workgroup with an empty subnetIds list must not raise (vpc_id=None)."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

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
                'configParameters': [],
                'endpoint': {'address': 'test.serverless.amazonaws.com', 'port': 5439},
                'subnetIds': [],  # present but empty - previously caused IndexError
            }
        }

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
        assert result[0].vpc_id is None

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
    async def test_discover_clusters_both_access_denied_raises_tool_error(self, mocker):
        """Test that ToolError is raised when both clients get access-denied."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Not authorized'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ToolError, match='IAM lacks both redshift and redshift-serverless'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_provisioned_access_denied_serverless_succeeds(self, mocker):
        """Test partial results when provisioned gets access-denied but serverless succeeds."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Not authorized'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'my-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'configParameters': [{'parameterValue': 'dev'}],
                'endpoint': {'address': 'wg.serverless.amazonaws.com', 'port': 5439},
                'subnetIds': ['subnet-abc'],
                'publiclyAccessible': False,
                'tags': [],
            }
        }

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
        assert result[0].identifier == 'my-workgroup'
        assert result[0].type == 'serverless'

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_access_denied_provisioned_succeeds(self, mocker):
        """Test partial results when serverless gets access-denied but provisioned succeeds."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {
                'Clusters': [
                    {
                        'ClusterIdentifier': 'my-cluster',
                        'ClusterStatus': 'available',
                        'DBName': 'dev',
                        'Endpoint': {'Address': 'cluster.redshift.amazonaws.com', 'Port': 5439},
                        'VpcId': 'vpc-123',
                        'NodeType': 'dc2.large',
                        'NumberOfNodes': 2,
                        'ClusterCreateTime': '2024-01-01T00:00:00Z',
                        'MasterUsername': 'admin',
                        'PubliclyAccessible': False,
                        'Encrypted': True,
                        'Tags': [],
                    }
                ]
            }
        ]

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

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
        assert result[0].identifier == 'my-cluster'
        assert result[0].type == 'provisioned'

    @pytest.mark.asyncio
    async def test_discover_clusters_non_access_denied_provisioned_bubbles_up(self, mocker):
        """Test that non-access-denied ClientError from provisioned discovery re-raises immediately."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Something broke'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

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

        with pytest.raises(ClientError):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_non_access_denied_serverless_bubbles_up(self, mocker):
        """Test that non-access-denied ClientError from serverless discovery re-raises immediately."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ClientError):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_both_non_access_denied_first_bubbles_up(self, mocker):
        """Test that when both clients raise non-access-denied ClientError, the first one (provisioned) re-raises."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Provisioned broke'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ClientError, match='Provisioned broke'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_databases(self, mocker):
        """Test discover_databases function."""
        # Mock _execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
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
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Database discovery failed')

        with pytest.raises(Exception, match='Database discovery failed'):
            await discover_databases('test-cluster')

    @pytest.mark.asyncio
    async def test_discover_schemas(self, mocker):
        """Test discover_schemas function."""
        # Mock _execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
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
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Schema discovery failed')

        with pytest.raises(Exception, match='Schema discovery failed'):
            await discover_schemas('test-cluster', 'dev')

    @pytest.mark.asyncio
    async def test_discover_tables(self, mocker):
        """Test discover_tables function."""
        # Mock _execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
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
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Table discovery failed')

        with pytest.raises(Exception, match='Table discovery failed'):
            await discover_tables('test-cluster', 'dev', 'public')

    @pytest.mark.asyncio
    async def test_discover_columns(self, mocker):
        """Test discover_columns function."""
        # Mock _execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
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
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Column discovery failed')

        with pytest.raises(Exception, match='Column discovery failed'):
            await discover_columns('test-cluster', 'dev', 'public', 'users')


class TestExecuteQuery:
    """Tests for execute_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, mocker):
        """Test successful query execution."""
        # Mock _execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
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
        assert result['query_id'] == 'query-123'

    @pytest.mark.asyncio
    async def test_read_only_enforcement_is_passed_through_unchanged(self, mocker):
        """One flag decides the guard and the wrapper, so it must not be re-derived here.

        The mapping from ACCESS_MODE onto this flag happens once, in the tool.
        """
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement',
            return_value=({'ColumnMetadata': [], 'Records': []}, 'query-123'),
        )

        await execute_query('test-cluster', 'dev', 'SELECT 1', enforce_read_only=True)
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is True

        await execute_query('test-cluster', 'dev', 'VACUUM t', enforce_read_only=False)
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is False

    @pytest.mark.asyncio
    async def test_execute_query_no_result_set(self, mocker):
        """SET-style statements with no result set return an empty, successful result."""
        # Mock _execute_standalone_statement to mimic a no-result-set statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.return_value = (
            {'Records': [], 'ColumnMetadata': []},
            'set-query-123',
        )

        result = await execute_query(
            'test-cluster',
            'dev',
            "SET search_path TO 'public'",
        )

        assert result['columns'] == []
        assert result['rows'] == []
        assert result['row_count'] == 0
        assert result['query_id'] == 'set-query-123'

    @pytest.mark.asyncio
    async def test_execute_query_error_handling(self, mocker):
        """Test error handling in execute_query."""
        # Mock _execute_standalone_statement to raise exception
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Query execution failed')

        with pytest.raises(Exception, match='Query execution failed'):
            await execute_query('test-cluster', 'dev', 'SELECT * FROM nonexistent')


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


class TestResolveIntEnv:
    """`_resolve_int_env` reads a setting without letting a typo stop the server."""

    def test_unset_uses_the_default(self, monkeypatch):
        """Nothing configured is the normal case."""
        monkeypatch.delenv('PROBE_SETTING', raising=False)
        assert _resolve_int_env('PROBE_SETTING', 600) == 600

    def test_a_valid_value_is_taken_with_surrounding_space_ignored(self, monkeypatch):
        """Values arrive from shells and JSON config, where stray space is common."""
        monkeypatch.setenv('PROBE_SETTING', '  120  ')
        assert _resolve_int_env('PROBE_SETTING', 600) == 120

    @pytest.mark.parametrize(
        'value',
        ['abc', '', '12.5', '0', '-1'],
        ids=['letters', 'empty', 'fractional', 'zero', 'negative'],
    )
    def test_an_unusable_value_falls_back(self, monkeypatch, value):
        """A mistyped timeout should not take the server down at import."""
        monkeypatch.setenv('PROBE_SETTING', value)
        assert _resolve_int_env('PROBE_SETTING', 600) == 600

    def test_a_value_past_the_ceiling_falls_back(self, monkeypatch):
        """The Data API refuses a keepalive above 86400, so sending one would fail every call."""
        monkeypatch.setenv('PROBE_SETTING', '86401')
        assert _resolve_int_env('PROBE_SETTING', 600, maximum=86400) == 600

    def test_a_value_below_the_floor_falls_back(self, monkeypatch):
        """A floor above 1 is rejected on its own terms, not just against zero."""
        monkeypatch.setenv('PROBE_SETTING', '5')
        assert _resolve_int_env('PROBE_SETTING', 600, minimum=10) == 600


class TestRedshiftTransactionManager:
    """Tests for RedshiftTransactionManager."""

    def _manager(self, max_open_per_target=10):
        """Build a manager with no transactions in it."""
        return RedshiftTransactionManager(max_open_per_target=max_open_per_target)

    def test_one_lock_per_transaction(self):
        """Two statements in one transaction must serialize; two transactions must not."""
        manager = self._manager()

        assert manager.claim('a')[0] is manager.claim('a')[0]
        assert manager.claim('a')[0] is not manager.claim('b')[0]

    def test_a_name_that_changed_hands_while_waiting_is_refused(self):
        """A caller queued on the lock must not land in whatever transaction now holds the name.

        Acquiring the lock is an await, so the name can be closed and reopened across it. The
        lock is deliberately not replaced on close, since a waiter already holds a reference to
        it; the generation is what tells that waiter the transaction it queued for is gone.
        """
        manager = self._manager()
        manager.reserve('key', 'target', 'load')
        manager.attach('key', 'session-1')

        lock, generation = manager.claim('key')

        # Closed and reopened under the same name, as another call would do.
        manager.forget('key')
        manager.reserve('key', 'target', 'load')
        manager.attach('key', 'session-2')

        assert manager.claim('key')[0] is lock, 'the lock must survive the close'
        with pytest.raises(ToolError, match='closed while this statement was waiting'):
            manager.assert_current('key', generation, 'load')

    def test_a_transaction_idle_past_its_keepalive_stops_holding_the_cap(self):
        """Redshift ends an idle session silently, so its entry must not hold the cap forever.

        Without reaping, a caller who opens transactions and walks away blocks the target for
        everyone until each dead name is touched and found gone.
        """
        manager = self._manager(max_open_per_target=1)
        manager.reserve('stale', 'target', 'abandoned')
        manager.attach('stale', 'session-1')

        # Older than any keepalive the server accepts, as an abandoned transaction becomes.
        manager._transactions['stale']['touched_at'] -= SESSION_KEEPALIVE_MAX + 1

        # Reserving at all is the assertion: the cap is 1, so this only fits if the stale
        # entry was reaped rather than counted.
        manager.reserve('fresh', 'target', 'wanted')

        with pytest.raises(ToolError, match='No open transaction'):
            manager.session_id('stale', 'abandoned')

    def test_using_a_transaction_restarts_its_idle_clock(self):
        """The keepalive counts idle time, so a transaction in use must not be reaped."""
        manager = self._manager(max_open_per_target=1)
        manager.reserve('key', 'target', 'load')
        manager.attach('key', 'session-1')
        manager._transactions['key']['touched_at'] -= SESSION_KEEPALIVE_MAX + 1

        manager.touch('key')

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.reserve('other', 'target', 'second')

    def test_a_reserved_and_attached_transaction_reports_its_session(self):
        """The session is what every later statement in the transaction runs on."""
        manager = self._manager()

        manager.reserve('key', 'target', 'load')
        manager.attach('key', 'session-1')

        assert manager.session_id('key', 'load') == 'session-1'

    def test_reserving_an_open_name_is_refused(self):
        """Silently joining someone else's transaction is the failure mode to avoid."""
        manager = self._manager()
        manager.reserve('key', 'target', 'load')

        with pytest.raises(ToolError, match="Transaction 'load' is already open"):
            manager.reserve('key', 'target', 'load')

    def test_the_cap_is_counted_per_target(self):
        """A busy database must not stop work on another one."""
        manager = self._manager(max_open_per_target=2)
        manager.reserve('a:dev:one', 'a:dev', 'one')
        manager.reserve('a:dev:two', 'a:dev', 'two')

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.reserve('a:dev:three', 'a:dev', 'three')

        # Another database is a different target, so it still has room.
        manager.reserve('a:other:one', 'a:other', 'one')

    def test_a_closed_name_frees_its_slot(self):
        """The cap bounds what is open, not what was ever opened."""
        manager = self._manager(max_open_per_target=1)
        manager.reserve('key', 'target', 'load')
        manager.forget('key')

        manager.reserve('key', 'target', 'load')

    @pytest.mark.parametrize(
        'reserve_first', [False, True], ids=['never_opened', 'reserved_but_not_attached']
    )
    def test_an_unknown_transaction_names_every_way_it_could_be_gone(self, reserve_first):
        """Three causes are indistinguishable from here, so the message covers all of them."""
        manager = self._manager()
        if reserve_first:
            manager.reserve('key', 'target', 'load')

        with pytest.raises(ToolError) as failure:
            manager.session_id('key', 'load')

        message = str(failure.value)
        assert "No open transaction named 'load'" in message
        assert 'never opened' in message
        assert 'rolled back' in message
        assert 'expired' in message

    def test_forgetting_an_unknown_transaction_is_harmless(self):
        """Cleanup runs on paths that may not have reserved anything."""
        self._manager().forget('key')

    def test_an_unset_cap_falls_back_to_the_configured_one(self):
        """The server's own manager takes no cap, so the setting is read on first use."""
        manager = RedshiftTransactionManager()

        for i in range(max_open_transactions_per_target()):
            manager.reserve(f'target:{i}', 'target', str(i))

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.reserve('target:over', 'target', 'over')


class TestResolveTransaction:
    """`_resolve_transaction_action` reduces every invalid combination to one rule."""

    def test_no_transaction_parameter_runs_the_statement_alone(self):
        """The ordinary call is unaffected by any of this."""
        assert _resolve_transaction_action('SELECT 1', None, None, None, None) == (None, None)

    @pytest.mark.parametrize(
        ('parameter', 'arguments'),
        [
            ('begin_transaction', ('load', None, None, None)),
            ('in_transaction', (None, 'load', None, None)),
            ('commit_transaction', (None, None, 'load', None)),
            ('rollback_transaction', (None, None, None, 'load')),
        ],
    )
    def test_one_parameter_names_the_action_and_the_transaction(self, parameter, arguments):
        """Each parameter both picks the action and carries the name."""
        assert _resolve_transaction_action('SELECT 1', *arguments) == (parameter, 'load')

    def test_two_parameters_are_refused_and_both_are_named(self):
        """The caller has to know which two conflicted to fix the call."""
        with pytest.raises(ToolError) as failure:
            _resolve_transaction_action('SELECT 1', 'load', None, 'other', None)

        assert 'Only one transaction parameter' in str(failure.value)
        assert 'begin_transaction' in str(failure.value)
        assert 'commit_transaction' in str(failure.value)

    @pytest.mark.parametrize('name', ['', '   '], ids=['empty', 'blank'])
    def test_a_blank_name_is_refused(self, name):
        """An empty name would key a transaction nobody can address again."""
        with pytest.raises(ToolError, match='needs the name of a transaction'):
            _resolve_transaction_action('SELECT 1', name, None, None, None)

    def test_sql_is_required_without_a_transaction_parameter(self):
        """Otherwise the call asks for nothing at all."""
        with pytest.raises(ToolError, match='sql is required'):
            _resolve_transaction_action(None, None, None, None, None)

    def test_sql_is_required_to_add_to_a_transaction(self):
        """in_transaction with no statement would open nothing and run nothing."""
        with pytest.raises(ToolError, match='sql is required with in_transaction'):
            _resolve_transaction_action(None, None, 'load', None, None)

    @pytest.mark.parametrize(
        'arguments',
        [('load', None, None, None), (None, None, 'load', None), (None, None, None, 'load')],
        ids=['begin', 'commit', 'rollback'],
    )
    def test_sql_is_optional_when_opening_or_closing(self, arguments):
        """A transaction can be opened, or closed, without a statement of its own."""
        action, name = _resolve_transaction_action(None, *arguments)

        assert name == 'load'
        assert action is not None


class TestTransactionLifecycle:
    """Opening, adding to, and closing a named transaction."""

    @pytest.fixture(autouse=True)
    def _isolate_transactions(self, mocker):
        """Give each test its own manager, since the real one outlives a single call."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            RedshiftTransactionManager(max_open_per_target=10),
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters',
            return_value=[_fake_cluster()],
        )

    def _batches(self, mocker, *responses):
        """Script the batches the Data API will answer with."""
        return mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch', side_effect=list(responses)
        )

    @pytest.mark.asyncio
    async def test_opening_a_read_only_transaction(self, mocker):
        """A read-only caller gets a read-only transaction, so the engine still refuses writes."""
        batches = self._batches(
            mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1')
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        assert batches.call_args[1]['sqls'] == [_APP_NAME_SQL, 'BEGIN READ ONLY']
        assert batches.call_args[1]['session_keepalive'] == session_keepalive()
        assert batches.call_args[1]['session_id'] is None

    @pytest.mark.asyncio
    async def test_opening_a_read_write_transaction(self, mocker):
        """A read-write caller gets a writable transaction."""
        batches = self._batches(
            mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1')
        )

        await execute_query(
            'test-cluster', 'dev', begin_transaction='load', enforce_read_only=False
        )

        assert batches.call_args[1]['sqls'] == [_APP_NAME_SQL, 'BEGIN']

    @pytest.mark.asyncio
    async def test_opening_with_a_first_statement_returns_that_statement(self, mocker):
        """Opening and running the first statement in one call saves a round trip."""
        self._batches(
            mocker,
            _fake_batch(
                ['FINISHED', 'FINISHED', {'has_result_set': True}], session_id='session-1'
            ),
        )
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.return_value = {
            'Records': [[{'longValue': 1}]],
            'ColumnMetadata': [{'name': 'one'}],
        }
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        result = await execute_query(
            'test-cluster', 'dev', 'SELECT 1 AS one', begin_transaction='load'
        )

        assert result['rows'] == [[1]]
        assert result['query_id'] == 'batch-id:3'

    @pytest.mark.asyncio
    async def test_opening_without_a_statement_reports_the_batch(self, mocker):
        """There is no statement of the caller's to report, so the batch stands in for it."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        result = await execute_query('test-cluster', 'dev', begin_transaction='load')

        assert result == {'columns': [], 'rows': [], 'row_count': 0, 'query_id': 'batch-id'}

    @pytest.mark.asyncio
    async def test_a_statement_inside_a_transaction_is_sent_bare_on_its_session(self, mocker):
        """The transaction is already the wrapper, so wrapping again would nest a BEGIN."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

        assert batches.call_args[1]['sqls'] == ['SELECT 1']
        assert batches.call_args[1]['session_id'] == 'session-1'
        # Re-sent so the idle clock restarts on every statement of the transaction.
        assert batches.call_args[1]['session_keepalive'] == session_keepalive()

    @pytest.mark.asyncio
    async def test_the_guard_still_applies_inside_a_read_only_transaction(self, mocker):
        """A transaction is not a way around read-only mode."""
        batches = self._batches(
            mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1')
        )
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            await execute_query('test-cluster', 'dev', 'TRUNCATE t', in_transaction='load')

        # The rejected statement never reached the cluster.
        assert batches.call_count == 1

    @pytest.mark.asyncio
    async def test_a_statement_the_guard_rejects_leaves_the_transaction_open(self, mocker):
        """It never ran, so the transaction is not aborted and the caller can carry on."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            await execute_query('test-cluster', 'dev', 'SELECT 1; SELECT 2', in_transaction='load')

        # Still usable, on the same session.
        await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')
        assert batches.call_args[1]['session_id'] == 'session-1'

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('parameter', 'closer'),
        [('commit_transaction', 'COMMIT'), ('rollback_transaction', 'ROLLBACK')],
    )
    async def test_closing_on_its_own(self, mocker, parameter, closer):
        """A transaction can be ended without a last statement."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        closing: dict[str, Any] = {parameter: 'load'}

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'dev', **closing)

        assert batches.call_args[1]['sqls'] == [closer]
        assert batches.call_args[1]['session_id'] == 'session-1'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('parameter', ['commit_transaction', 'rollback_transaction'])
    async def test_closing_drains_the_session(self, mocker, parameter):
        """Nothing is left to run on it, so it should not idle for the whole keepalive."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

        # Mid-transaction the session is still wanted, so it keeps the configured timeout.
        assert batches.call_args[1]['session_keepalive'] == session_keepalive()

        closing: dict[str, Any] = {parameter: 'load'}
        await execute_query('test-cluster', 'dev', **closing)

        assert batches.call_args[1]['session_keepalive'] == _SESSION_DRAIN
        assert _SESSION_DRAIN < session_keepalive()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('parameter', 'closer'),
        [('commit_transaction', 'COMMIT'), ('rollback_transaction', 'ROLLBACK')],
    )
    async def test_closing_with_a_last_statement(self, mocker, parameter, closer):
        """One batch runs the statement and ends the transaction, which is one round trip."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED', 'FINISHED']),
        )

        closing: dict[str, Any] = {parameter: 'load'}

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'dev', 'SELECT 1', **closing)

        assert batches.call_args[1]['sqls'] == ['SELECT 1', closer]

    @pytest.mark.asyncio
    async def test_a_closed_transaction_is_gone(self, mocker):
        """The name must not outlive the transaction, or a later call looks like it worked."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'dev', commit_transaction='load')

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_reopening_the_same_name_is_refused_while_it_is_open(self, mocker):
        """Fail closed: the alternative is silently joining a transaction the caller forgot."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match="Transaction 'load' is already open"):
            await execute_query('test-cluster', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_a_failed_open_does_not_leave_the_name_claimed(self, mocker):
        """Otherwise a failed open would block the name until the process restarted."""
        self._batches(
            mocker,
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: nope'}, 'FINISHED']),
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-2'),
        )

        with pytest.raises(ToolError, match='ERROR: nope'):
            await execute_query('test-cluster', 'dev', begin_transaction='load')

        # The name is free again.
        await execute_query('test-cluster', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_an_open_without_a_session_is_refused(self, mocker):
        """Without the session id there is no way to reach the transaction again."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED']))

        with pytest.raises(ToolError, match='the Data API returned no session'):
            await execute_query('test-cluster', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_a_failed_statement_rolls_the_transaction_back_and_drops_it(self, mocker):
        """An aborted transaction refuses everything later and would commit nothing."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: division by zero'}]),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero'):
            await execute_query('test-cluster', 'dev', 'SELECT 1/0', in_transaction='load')

        # Rolled back on the way out, on the transaction's own session.
        assert batches.call_args[1]['sqls'] == ['ROLLBACK']
        assert batches.call_args[1]['session_id'] == 'session-1'

        # And the name is gone, so a later commit cannot look successful.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_the_rollback_of_an_aborted_transaction_drains_its_session(self, mocker):
        """The name goes with it, so nothing can reach the session the rollback ran on."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: division by zero'}]),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero'):
            await execute_query('test-cluster', 'dev', 'SELECT 1/0', in_transaction='load')

        assert batches.call_args[1]['sqls'] == ['ROLLBACK']
        assert batches.call_args[1]['session_keepalive'] == _SESSION_DRAIN

    @pytest.mark.asyncio
    async def test_a_failing_rollback_does_not_replace_the_real_error(self, mocker):
        """The caller needs the statement's failure; the idle timeout ends the session anyway."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: division by zero'}]),
            ClientError({'Error': {'Code': 'ValidationException'}}, 'BatchExecuteStatement'),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero'):
            await execute_query('test-cluster', 'dev', 'SELECT 1/0', in_transaction='load')

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'message',
        ['Session is expired', 'Session is not available', 'Session with Id: x is invalid'],
    )
    async def test_a_session_taken_away_reads_as_a_missing_transaction(self, mocker, message):
        """The transaction is gone with everything it had not committed, which is the fact."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': message}},
                'BatchExecuteStatement',
            ),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

        # Dropped, so the caller is not told to commit something that no longer exists.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_an_unrelated_aws_error_is_not_disguised_as_a_missing_transaction(self, mocker):
        """Throttling or a credential problem is not the transaction's fault."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'BatchExecuteStatement',
            ),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ClientError):
            await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

    @pytest.mark.asyncio
    async def test_transactions_on_different_databases_are_independent(self, mocker):
        """The name is scoped to the cluster and database it was opened against."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-dev'),
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-other'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'other', begin_transaction='load')

        # Closing one leaves the other open.
        await execute_query('test-cluster', 'dev', commit_transaction='load')

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_the_cap_refuses_the_next_transaction(self, mocker):
        """A runaway caller would otherwise hold connections until they timed out."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            RedshiftTransactionManager(max_open_per_target=1),
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        await execute_query('test-cluster', 'dev', begin_transaction='one')

        with pytest.raises(ToolError, match='Too many open transactions'):
            await execute_query('test-cluster', 'dev', begin_transaction='two')

    @pytest.mark.asyncio
    async def test_statements_in_one_transaction_are_serialized(self, mocker):
        """A SessionId is strictly serial: a second concurrent submit is refused at submit."""
        in_flight = 0
        overlapped = False

        async def batch(**kwargs):
            nonlocal in_flight, overlapped
            if kwargs.get('session_id') is not None:
                in_flight += 1
                overlapped = overlapped or in_flight > 1
                await asyncio.sleep(0)
                in_flight -= 1
                return _fake_batch(['FINISHED'])
            return _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1')

        mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch', side_effect=batch)

        await execute_query('test-cluster', 'dev', begin_transaction='load')
        await asyncio.gather(
            *[
                execute_query('test-cluster', 'dev', f'SELECT {i}', in_transaction='load')
                for i in range(4)
            ]
        )

        assert not overlapped


class TestBatchDeniedDetection:
    """Only the batch action being denied selects the compatibility path."""

    def test_access_denied_is_the_signal(self):
        """A denied BatchExecuteStatement arrives as AccessDeniedException."""
        assert _is_no_batch(_batch_denied_error()) is True

    def test_an_unreachable_cluster_is_not_the_signal(self):
        """Denied cluster credentials answer ValidationException, so the two do not collide.

        Measured against the Data API: revoking redshift:GetClusterCredentialsWithIAM makes
        both ExecuteStatement and BatchExecuteStatement fail with ValidationException, which
        is why the error code alone is a safe discriminator.
        """
        error = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'is not authorized to perform: redshift:GetClusterCredentialsWithIAM',
                }
            },
            'BatchExecuteStatement',
        )

        assert _is_no_batch(error) is False

    def test_a_denial_of_another_call_in_the_flow_is_not_the_signal(self):
        """The callers wrap the whole batch flow, so the operation has to be checked too.

        A batch is submitted, settled with DescribeStatement, then read with
        GetStatementResult, and one `except ClientError` covers all three. The compatibility
        path needs the latter two itself, so latching on a denial of either would refuse
        writes and transactions and then fail anyway on the next call.
        """
        for operation in ('DescribeStatement', 'GetStatementResult'):
            error = ClientError(
                {
                    'Error': {
                        'Code': 'AccessDeniedException',
                        'Message': (
                            'User: arn:aws:sts::1:assumed-role/r/s is not authorized to '
                            f'perform: redshift-data:{operation}'
                        ),
                    }
                },
                operation,
            )

            assert _is_no_batch(error) is False, operation


class TestBatchLatch:
    """The latch holds the compatibility path without paying a denied call per statement."""

    def test_the_batch_path_is_attempted_by_default(self):
        """Nothing is assumed about the credentials until a call is refused."""
        assert _no_batch_active() is False

    def test_a_denial_latches_and_names_the_grant(self, mocker):
        """One warning per latch, carrying the action to grant."""
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        _latch_no_batch(_batch_denied_error())

        assert _no_batch_active() is True
        assert warning.call_count == 1
        assert 'redshift-data:BatchExecuteStatement' in warning.call_args[0][0]

    def test_the_batch_path_is_probed_again_once_the_window_elapses(self, mocker):
        """A granted policy is picked up without restarting the server."""
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)
        _latch_no_batch(_batch_denied_error())

        assert _no_batch_active() is False
        # Consumed, so a still-denied batch latches again rather than warning per statement.
        assert redshift_module._no_batch_since is None


class TestExecuteSingleStatement:
    """The compatibility path runs one statement on its own connection."""

    def _data_client(self, mocker, submit=None, describe=None, records=None):
        """Wire a Data API client scripted for ExecuteStatement."""
        client = mocker.Mock()
        client.execute_statement.return_value = submit or {'Id': 'stmt-id', 'Status': 'FINISHED'}
        client.describe_statement.return_value = describe or {
            'Id': 'stmt-id',
            'Status': 'FINISHED',
            'HasResultSet': records is not None,
        }
        client.get_statement_result.return_value = records or {'Records': [], 'ColumnMetadata': []}
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=client,
        )
        return client

    @pytest.mark.asyncio
    async def test_a_result_set_is_fetched(self, mocker):
        """The statement's own id reaches its result, with no sub-statement to index."""
        records = {'Records': [[{'longValue': 1}]], 'ColumnMetadata': [{'name': 'n'}]}
        client = self._data_client(mocker, records=records)

        results, query_id = await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-cluster', 'test-db', 'SELECT 1'
        )

        assert results == records
        assert query_id == 'stmt-id'
        assert client.execute_statement.call_args[1]['Sql'] == 'SELECT 1'

    @pytest.mark.asyncio
    async def test_no_result_set_is_not_fetched(self, mocker):
        """GetStatementResult answers ResourceNotFoundException for a statement without one."""
        client = self._data_client(mocker)

        results, _ = await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-cluster', 'test-db', 'SET x TO 1'
        )

        assert results == {'Records': [], 'ColumnMetadata': []}
        client.get_statement_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_provisioned_and_serverless_are_addressed_differently(self, mocker):
        """A workgroup is not a cluster, and the Data API takes them under different names."""
        client = self._data_client(mocker)

        await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-cluster', 'test-db', 'SELECT 1'
        )
        assert client.execute_statement.call_args[1]['ClusterIdentifier'] == 'test-cluster'

        await _execute_statement_fallback_no_batch(
            _fake_cluster(type='serverless'), 'test-wg', 'test-db', 'SELECT 1'
        )
        assert client.execute_statement.call_args[1]['WorkgroupName'] == 'test-wg'

    @pytest.mark.asyncio
    async def test_an_engine_failure_carries_its_message(self, mocker):
        """The caller needs the engine's reason, not a generic failure."""
        self._data_client(
            mocker,
            describe={'Id': 'stmt-id', 'Status': 'FAILED', 'Error': 'ERROR: relation not found'},
        )

        with pytest.raises(ToolError, match='relation not found'):
            await _execute_statement_fallback_no_batch(
                _fake_cluster(), 'test-cluster', 'test-db', 'SELECT * FROM nope'
            )

    @pytest.mark.asyncio
    async def test_an_unknown_cluster_type_is_our_bug(self, mocker):
        """Discovery only ever sets provisioned or serverless."""
        self._data_client(mocker)

        with pytest.raises(Exception, match='Unknown cluster type'):
            await _execute_statement_fallback_no_batch(
                _fake_cluster(type='mystery'), 'test-cluster', 'test-db', 'SELECT 1'
            )

    @pytest.mark.asyncio
    async def test_parameters_are_forwarded(self, mocker):
        """A parameterised read still binds its placeholders on the compatibility path."""
        client = self._data_client(mocker)
        parameters = [{'name': 'id', 'value': '1'}]

        await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-cluster', 'test-db', 'SELECT :id', parameters=parameters
        )

        assert client.execute_statement.call_args[1]['Parameters'] == parameters


class TestCompatibilityPathRouting:
    """A denied batch falls back for reads, and refuses what it cannot wrap."""

    def _deny_the_batch(self, mocker):
        """Make the batch path answer AccessDeniedException."""
        return mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )

    def _capture_single(self, mocker):
        """Stand in for the compatibility path."""
        return mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_statement_fallback_no_batch',
            return_value=({'Records': [], 'ColumnMetadata': []}, 'stmt-id'),
        )

    @pytest.mark.asyncio
    async def test_a_read_falls_back_on_the_same_call(self, mocker):
        """Nothing ran, so the statement is retried rather than failing the caller's call."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        batch = self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        _, query_id = await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        assert batch.call_count == 1
        assert single.call_args[1]['sql'] == 'SELECT 1'
        assert query_id == 'stmt-id'
        assert _no_batch_active() is True

    @pytest.mark.asyncio
    async def test_the_wrapper_is_dropped_with_the_batch(self, mocker):
        """One statement per connection leaves nowhere to put BEGIN READ ONLY."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        assert single.call_args[1]['sql'] == 'SELECT 1'

    @pytest.mark.asyncio
    async def test_a_latched_server_does_not_attempt_the_batch(self, mocker):
        """The point of the latch is to stop paying a denied call per statement."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch_for_statement')
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error())

        await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        batch.assert_not_called()
        assert single.call_count == 1

    @pytest.mark.asyncio
    async def test_server_authored_discovery_still_works(self, mocker):
        """Every SHOW this server issues classifies as a read, so discovery survives."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error())

        await _execute_standalone_statement(
            'test-cluster', 'test-db', 'SHOW DATABASES;', enforce_read_only=False
        )

        assert single.call_args[1]['sql'] == 'SHOW DATABASES;'

    @pytest.mark.asyncio
    async def test_a_write_is_refused_and_names_the_grant(self, mocker):
        """Without the wrapper a write cannot be contained, so it is refused rather than run."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error())

        with pytest.raises(ToolError, match='redshift-data:BatchExecuteStatement'):
            await _execute_standalone_statement(
                'test-cluster', 'test-db', 'INSERT INTO t VALUES (1)', enforce_read_only=False
            )

        single.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_unrelated_client_error_is_not_absorbed(self, mocker):
        """A denial that is not about the batch action must not select the fallback."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'nope'}}, 'Batch'
            ),
        )
        single = self._capture_single(mocker)

        with pytest.raises(ClientError):
            await _execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        single.assert_not_called()
        assert _no_batch_active() is False


class TestTransactionsNeedTheBatch:
    """A transaction is several statements on one connection, which the fallback cannot give."""

    @pytest.mark.asyncio
    async def test_opening_is_refused_while_latched(self):
        """Refused before any work, so no name is reserved."""
        _latch_no_batch(_batch_denied_error())

        with pytest.raises(ToolError, match='Named transactions need'):
            await _begin_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_adding_to_one_is_refused_while_latched(self):
        """The same refusal, so the caller is not told the name is merely unknown."""
        _latch_no_batch(_batch_denied_error())

        with pytest.raises(ToolError, match='Named transactions need'):
            await _execute_statement_in_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_a_denial_while_opening_drops_the_name(self, mocker):
        """A reserved name must not linger when the batch it needed was refused."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )

        with pytest.raises(ToolError, match='Named transactions need'):
            await _begin_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

        assert _no_batch_active() is True
        # The name is free again, so a later call under it reports it as unknown.
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.session_id('test-cluster:test-db:load', 'load')

    @pytest.mark.asyncio
    async def test_a_session_minted_by_a_failed_open_is_rolled_back(self, mocker):
        """A transaction that opened and then failed must not leave its session holding it.

        Dropping the name alone would leave an aborted transaction alive on a session nobody
        can reach, until its keepalive expires, and outside the cap the whole time.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        async def mint_then_fail(*args, **kwargs):
            kwargs['session_sink'].append('session-1')
            raise ToolError('Statement failed: ERROR: syntax error')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=mint_then_fail,
        )

        with pytest.raises(ToolError, match='Statement failed'):
            await _begin_transaction('test-cluster', 'test-db', 'load', 'SELECT bad syntax')

        assert rollback.call_args[0][3] == 'session-1'
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.session_id('test-cluster:test-db:load', 'load')

    @pytest.mark.asyncio
    async def test_a_denial_inside_one_drops_the_name(self, mocker):
        """An open transaction turns unreachable, so its name goes rather than misleading."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )
        key = 'test-cluster:test-db:load'
        redshift_module.transaction_manager.reserve(key, 'test-cluster:test-db', 'load')
        redshift_module.transaction_manager.attach(key, 'session-1')

        with pytest.raises(ToolError, match='Named transactions need'):
            await _execute_statement_in_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

        assert _no_batch_active() is True
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.session_id(key, 'load')
