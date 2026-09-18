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

"""Tests for running a statement: the batch, the wrapper, transactions, and the fallback."""

import asyncio
import pytest
import time
from awslabs.redshift_mcp_server import redshift as redshift_module
from awslabs.redshift_mcp_server.consts import (
    MAX_SQL_LEN,
    QUERY_LONG_POLL,
)
from awslabs.redshift_mcp_server.redshift import (
    _APP_NAME_SQL,
    _SESSION_DRAIN,
    _begin_transaction,
    _execute_batch,
    _execute_batch_for_statement,
    _execute_statement_fallback_no_batch,
    _execute_statement_in_transaction,
    _is_no_batch,
    _latch_no_batch,
    _no_batch_active,
    _resolve_transaction_action,
    _settle_statement,
    execute_query,
    execute_standalone_statement,
)
from awslabs.redshift_mcp_server.settings import (
    session_keepalive,
)
from awslabs.redshift_mcp_server.transactions import RedshiftTransactionManager
from botocore.exceptions import ClientError
from helpers import _batch_denied_error, _fake_batch, _fake_cluster
from mcp.server.mcpserver.exceptions import ToolError
from typing import Any


class TestExecuteProtectedStatement:
    """Tests for execute_standalone_statement function."""

    @pytest.mark.asyncio
    async def test_read_is_wrapped_in_a_read_only_transaction(self, mocker):
        """A caller's read runs as one batch wrapped in BEGIN READ ONLY ... ROLLBACK."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', 'FINISHED', 'FINISHED']),
        )

        _, query_id = await execute_standalone_statement(
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED']),
        )

        _, query_id = await execute_standalone_statement(
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED']),
        )

        await execute_standalone_statement(
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            await execute_standalone_statement(
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        for sql in ('UNLOAD ($$SELECT 1$$) TO $$s3://b/k$$ IAM_ROLE $$r$$', 'VACUUM t', 'COMMIT'):
            with pytest.raises(ToolError):
                await execute_standalone_statement('test-cluster', 'test-db', sql)

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_oversized_sql_rejected(self, mocker):
        """SQL beyond MAX_SQL_LEN is rejected before parsing."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='exceeds the maximum allowed length'):
            await execute_standalone_statement(
                'test-cluster', 'test-db', 'SELECT ' + 'x' * MAX_SQL_LEN
            )

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_cluster_not_found_when_none_discovered(self, mocker):
        """An unknown cluster is named in the error, with the tool that lists valid ones."""
        mocker.patch('awslabs.redshift_mcp_server.clusters.discover_clusters', return_value=[])

        with pytest.raises(ToolError, match='Cluster nonexistent-cluster not found'):
            await execute_standalone_statement('nonexistent-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_cluster_not_in_list(self, mocker):
        """A cluster missing from a non-empty discovery result is still not found."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster(identifier='other-cluster')],
        )

        with pytest.raises(ToolError, match='Cluster target-cluster not found'):
            await execute_standalone_statement('target-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_results_are_fetched_for_the_callers_statement_only(self, mocker):
        """The result comes from the caller's sub-statement, not the batch or a wrapper."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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

        results_response, query_id = await execute_standalone_statement(
            'test-cluster', 'test-db', 'SELECT 1 AS one'
        )

        mock_data_client.get_statement_result.assert_called_once_with(Id='batch-id:3')
        assert results_response == expected
        assert query_id == 'batch-id:3'

    @pytest.mark.asyncio
    async def test_no_result_set_returns_empty_without_asking_for_results(self, mocker):
        """GetStatementResult raises for a statement without a result set, so it is skipped."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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

        results_response, _ = await execute_standalone_statement(
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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
            await execute_standalone_statement('test-cluster', 'test-db', 'SELECT * FROM nope')

    @pytest.mark.asyncio
    async def test_a_refused_connection_reports_the_reason_the_batch_carries(self, mocker):
        """Nothing ran, so every statement holds a placeholder and only the batch knows why."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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
            await execute_standalone_statement(
                'test-cluster', 'awsdatacatalog', 'SHOW SCHEMAS', enforce_read_only=False
            )

    @pytest.mark.asyncio
    async def test_failed_caller_statement_without_an_error_field(self, mocker):
        """A failure the Data API does not explain still fails, and says so."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', {'status': 'ABORTED'}, 'FINISHED']),
        )

        with pytest.raises(ToolError, match='Statement failed: Unknown error'):
            await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_failed_wrapper_fails_the_call_even_though_the_read_ran(self, mocker):
        """A wrapper statement that failed means the call did not run as designed.

        A read is in no danger of persisting either way, since the failure aborts the
        transaction and the connection closes at batch end. What is reported is that the batch
        did not complete, rather than a result passed off as cleanly wrapped.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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
            await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_parameters_are_passed_through_to_the_batch(self, mocker):
        """Only the caller's statement carries placeholders, so the batch takes them as given."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mock_execute_batch = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED', 'FINISHED', 'FINISHED']),
        )
        parameters = [{'name': 'answer', 'value': '365'}]

        await execute_standalone_statement(
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
    async def test_a_failure_anywhere_in_the_batch_fails_the_call(self, mocker):
        """The engine's reason is what the caller gets, whichever statement it came from.

        A batch keeps going after one of its statements fails, so the caller's own may well
        have run. Saying so was tried and withdrawn: the same branch fires when the failed
        statement is the closer, where the effect did not persist, and it sent the caller
        looking for one anyway.
        """
        self._data_client(
            mocker,
            describes=[
                _fake_batch(
                    [{'status': 'FAILED', 'error': 'ERROR: syntax error'}, 'FINISHED'],
                )
            ],
        )

        with pytest.raises(ToolError, match='Statement failed: ERROR: syntax error'):
            await _execute_batch_for_statement(
                _fake_cluster(),
                'test-cluster',
                'test-db',
                ['BEGIN READ ONLYY', 'CREATE TABLE t (i int)'],
                caller_index=1,
            )

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
    async def test_a_finished_batch_is_recorded_before_its_result_is_read(self, mocker):
        """Everything in it has run by then, so nothing later can undo it.

        Recorded after the confirming describe instead, a throttle on that call would look to
        the caller like a batch that never ran, and a committed transaction would stay open.
        """
        mock_data_client = self._data_client(mocker, describes=[_fake_batch(['FINISHED'])])
        mock_data_client.describe_statement.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )
        mock_data_client.batch_execute_statement.return_value = {
            'Id': 'batch-id',
            'Status': 'FINISHED',
        }
        settled: list[str] = []

        with pytest.raises(ClientError, match='Rate exceeded'):
            await _execute_batch(
                _fake_cluster(),
                'test-cluster',
                'test-db',
                ['COMMIT'],
                settled_sink=settled,
            )

        assert settled == ['batch-id']

    @pytest.mark.asyncio
    async def test_an_accepted_batch_is_recorded_before_it_settles(self, mocker):
        """Abandoning the poll does not cancel it, so what it did is unknown, not undone.

        Recorded only on settling instead, a batch whose COMMIT was accepted and then lost
        would look to the caller like one that never ran.
        """
        mock_data_client = self._data_client(mocker, submit={'Id': 'batch-id', 'Status': 'PICKED'})
        mock_data_client.describe_statement.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )
        submitted: list[str] = []
        settled: list[str] = []

        with pytest.raises(ClientError, match='Rate exceeded'):
            await _execute_batch(
                _fake_cluster(),
                'test-cluster',
                'test-db',
                ['COMMIT'],
                submitted_sink=submitted,
                settled_sink=settled,
                query_poll_interval=0,
            )

        assert submitted == ['batch-id']
        # Nothing reached a terminal status, so the two sinks disagree, which is the whole
        # point of having both.
        assert settled == []

    @pytest.mark.asyncio
    async def test_a_batch_that_did_not_finish_is_not_recorded(self, mocker):
        """The sink is what tells a caller its closer ran, so a failure must not fill it."""
        self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'FAILED'},
            describes=[_fake_batch([{'status': 'FAILED', 'error': 'ERROR: nope'}])],
        )
        settled: list[str] = []

        await _execute_batch(
            _fake_cluster(), 'test-cluster', 'test-db', ['COMMIT'], settled_sink=settled
        )

        assert settled == []

    @pytest.mark.asyncio
    async def test_every_submit_carries_its_own_client_token(self, mocker):
        """A submit whose response was lost is retried by botocore, which would write twice."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['UPDATE t SET n = 1'])
        first = mock_data_client.batch_execute_statement.call_args[1]['ClientToken']

        await _execute_batch(_fake_cluster(), 'test-cluster', 'test-db', ['UPDATE t SET n = 1'])
        second = mock_data_client.batch_execute_statement.call_args[1]['ClientToken']

        # One token per submit: shared across submits it would suppress the second write.
        assert first and second and first != second

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


class TestAnUnwatchedStandaloneWrite:
    """Outside a transaction the only thing a failure leaves behind is the statement itself."""

    def _wire(self, mocker, side_effect):
        """Resolve a cluster and script the batch helper's failure."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=side_effect,
        )

    @pytest.mark.asyncio
    async def test_an_accepted_write_that_never_settles_is_not_reported_as_not_having_run(
        self, mocker
    ):
        """Unwrapped, the batch autocommits, and abandoning the poll cancels nothing.

        Reported as a bare timeout, a write that was still committing read as one that had not
        happened, so a caller who retried wrote twice.
        """

        async def accept_then_time_out(*args, **kwargs):
            kwargs['submitted_sink'].append('batch-id')
            raise ToolError('Statement timed out after 3600 seconds')

        self._wire(mocker, accept_then_time_out)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', enforce_read_only=False
            )

        assert 'may or may not have been applied' in str(raised.value)
        assert 'timed out' in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_read_only_failure_says_nothing_of_the_kind(self, mocker):
        """The wrapper's trailing ROLLBACK runs even after a statement fails, so nothing lands."""

        async def accept_then_time_out(*args, **kwargs):
            kwargs['submitted_sink'].append('batch-id')
            raise ToolError('Statement timed out after 3600 seconds')

        self._wire(mocker, accept_then_time_out)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement('test-cluster', 'dev', 'SELECT 1')

        assert 'may or may not have been applied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_write_that_concluded_is_reported_as_it_concluded(self, mocker):
        """A batch seen to conclude needs no hedging: its outcome is known."""

        async def conclude_badly(*args, **kwargs):
            kwargs['submitted_sink'].append('batch-id')
            kwargs['terminal_sink'].append('batch-id')
            raise ToolError('Statement failed: ERROR: division by zero')

        self._wire(mocker, conclude_badly)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1/0)', enforce_read_only=False
            )

        assert 'may or may not have been applied' not in str(raised.value)
        assert 'division by zero' in str(raised.value)


class TestConcurrency:
    """Concurrent calls against one cluster and database."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_each_get_their_own_batch(self, mocker):
        """Nothing is shared between calls, so a read never waits on an unrelated one."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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
                execute_standalone_statement('test-cluster', 'test-db', f'SELECT {i}')
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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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

        await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert 'SessionId' not in request
        assert 'SessionKeepAliveSeconds' not in request

    @pytest.mark.asyncio
    async def test_a_name_closed_and_reopened_while_the_cluster_resolves_is_refused(self, mocker):
        """The generation has to be captured before the first await, not after it.

        Resolving the cluster suspends for two control-plane calls. Read after that, the
        generation already counts the close that happened during it, so the check passes and
        the statement joins whatever transaction took the name over.
        """
        manager = redshift_module.transaction_manager
        key, target = 'test-cluster:dev:load', 'test-cluster:dev'
        manager.reserve(key, target, 'load')
        manager.attach(key, 'session-original')

        resolving = asyncio.Event()
        reopened = asyncio.Event()

        async def park_in_resolve(_cluster_identifier):
            resolving.set()
            await reopened.wait()
            return _fake_cluster()

        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', side_effect=park_in_resolve
        )
        batches = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            return_value=(_fake_batch(['FINISHED']), 'batch-id:1', None),
        )

        adding = asyncio.create_task(
            _execute_statement_in_transaction('test-cluster', 'dev', 'load', 'SELECT 1')
        )
        await resolving.wait()

        # The transaction it named is committed, and the name is taken by a new one.
        manager.forget(key)
        manager.reserve(key, target, 'load')
        manager.attach(key, 'session-someone-else')
        reopened.set()

        with pytest.raises(ToolError, match='closed while this statement was waiting'):
            await adding

        # Nothing was sent, so the new transaction never saw a statement it did not ask for.
        batches.assert_not_called()


class TestExecuteQuery:
    """Tests for execute_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, mocker):
        """Test successful query execution."""
        # Mock execute_standalone_statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
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
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement',
            return_value=({'ColumnMetadata': [], 'Records': []}, 'query-123'),
        )

        await execute_query('test-cluster', 'dev', 'SELECT 1', enforce_read_only=True)
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is True

        await execute_query('test-cluster', 'dev', 'VACUUM t', enforce_read_only=False)
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is False

    @pytest.mark.asyncio
    async def test_execute_query_no_result_set(self, mocker):
        """SET-style statements with no result set return an empty, successful result."""
        # Mock execute_standalone_statement to mimic a no-result-set statement
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
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
        # Mock execute_standalone_statement to raise exception
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement'
        )
        mock_execute_protected.side_effect = Exception('Query execution failed')

        with pytest.raises(Exception, match='Query execution failed'):
            await execute_query('test-cluster', 'dev', 'SELECT * FROM nonexistent')


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

    def test_a_padded_name_is_the_same_transaction_as_an_unpadded_one(self):
        """Otherwise a name padded on one call opens a transaction the next cannot address."""
        assert _resolve_transaction_action('SELECT 1', ' load ', None, None, None) == (
            'begin_transaction',
            'load',
        )
        assert _resolve_transaction_action(None, None, None, '\tload\n', None) == (
            'commit_transaction',
            'load',
        )

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
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
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

        await asyncio.sleep(0)

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

        # The rollback is fired without being awaited, so it lands on the next tick.
        await asyncio.sleep(0)

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
        # Measured on one session as it went: the expiry wording for about half a minute, then
        # 'not available' from there on. An unknown id gives the third.
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
    @pytest.mark.parametrize(
        ('parameter', 'error', 'expected'),
        [
            (
                'commit_transaction',
                ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    'GetStatementResult',
                ),
                'Rate exceeded',
            ),
            # A network failure reading the result, which is what can follow a settled batch.
            # A timeout cannot: it is raised only when no terminal status ever arrived, and the
            # sink is filled only when one did.
            (
                'rollback_transaction',
                ConnectionError('connection reset'),
                'connection reset',
            ),
        ],
    )
    async def test_a_closer_that_ran_closes_the_name_even_if_the_call_then_fails(
        self, mocker, parameter, error, expected
    ):
        """Reading a result can fail after the closer is already durable.

        Keeping the name would let the caller roll back work that is committed and be told it
        succeeded, which is the outcome named transactions exist to prevent.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        async def settle_then_fail(*args, **kwargs):
            # Everything in the batch ran, the closer included, and only reading the result of
            # it failed. All three sinks fill, in the order the real batch fills them: settling
            # is something only an accepted batch that concluded can do.
            kwargs['submitted_sink'].append('batch-id')
            kwargs['terminal_sink'].append('batch-id')
            kwargs['settled_sink'].append('batch-id')
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=settle_then_fail,
        )

        closing: dict[str, Any] = {parameter: 'load'}
        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'dev', 'SELECT 1', **closing)

        # Both facts reach the caller: the closer stands, and what failed afterwards. Reported
        # bare, a committed write would read as a failed one.
        assert 'which stands' in str(raised.value)
        assert expected in str(raised.value)
        assert raised.value.__cause__ is error

        # The name is gone, so the caller cannot be told the closed transaction is still theirs.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_closer_still_in_flight_closes_the_name_and_reports_the_outcome_unknown(
        self, mocker
    ):
        """A poll can fail after the submit was accepted, and that does not cancel the batch.

        Left open, the caller rolls the name back, is told it worked, and concludes the work
        was discarded when the COMMIT may already have landed.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )

        async def submit_then_fail(*args, **kwargs):
            # The service took the batch, so its COMMIT runs whatever happens to this call.
            # Nothing reached a terminal status, so the settled sink stays empty.
            kwargs['submitted_sink'].append('batch-id')
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_fail,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', commit_transaction='load'
            )

        # Neither outcome is claimed, and the caller is told how to settle it.
        assert 'may or may not have been applied' in str(raised.value)
        assert 'which stands' not in str(raised.value)
        assert 'Rate exceeded' in str(raised.value)
        assert raised.value.__cause__ is error

        # And the name is gone, so the caller cannot roll it back and be told that worked.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_commit_abandoned_by_a_timeout_claims_neither_outcome(self, mocker):
        """Only a ClientError used to reach the arm above, and a timeout is a ToolError.

        The service had taken the COMMIT, so it runs whether or not this call sees it. Reported
        as a plain failure, the name was dropped as rolled back and the next call on it said so,
        while a detached ROLLBACK was fired at a session that may have been committing.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        timed_out = ToolError('Statement timed out after 3600 seconds')

        async def submit_then_time_out(*args, **kwargs):
            # Accepted, and no status ever seen: neither sink for a conclusion is filled.
            kwargs['submitted_sink'].append('batch-id')
            raise timed_out

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_time_out,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', commit_transaction='load'
            )

        assert 'may or may not have been applied' in str(raised.value)
        assert 'which stands' not in str(raised.value)
        assert 'timed out' in str(raised.value)

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_cancellation_with_the_closer_unwatched_claims_neither_outcome(self, mocker):
        """Keyed on `settled` alone, this arm rolled back a COMMIT that may have been applying.

        Its two siblings call the same state unknown and fire nothing. The operator's log was
        the only record, and it said the transaction was cancelled.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        async def accept_then_cancel(*args, **kwargs):
            # Taken by the service, and never watched to a conclusion.
            kwargs['submitted_sink'].append('batch-id')
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=accept_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', commit_transaction='load'
            )
        await asyncio.sleep(0)

        # No rollback at a session that may be committing.
        rollback.assert_not_called()
        assert any('may have been applied' in call[0][0] for call in warning.call_args_list)

        # And the name is gone either way, so nobody rolls back work that landed.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_failed_commit_releases_the_name_on_either_arm(self, mocker):
        """A ClientError never reaches the arm that handles this, so it is handled twice over.

        The closer's batch aborted on the cluster, so the transaction is gone there. Reported
        bare, the name outlived it and held a slot against the cap until a later call failed
        session-gone or the reaper took it.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        throttled = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )

        async def conclude_then_throttle(*args, **kwargs):
            # Watched to a conclusion, and it was not FINISHED.
            kwargs['submitted_sink'].append('batch-id')
            kwargs['terminal_sink'].append('batch-id')
            raise throttled

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=conclude_then_throttle,
        )

        with pytest.raises(ClientError):
            await execute_query(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', commit_transaction='load'
            )

        # Released, so the caller is not holding a name for a transaction that no longer exists.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_commit_whose_batch_failed_is_not_called_unknown(self, mocker):
        """A batch that reached FAILED did abort, so its outcome is known and must be said.

        This is why the arm keys on a terminal status rather than on submission alone: both a
        failure and an abandoned poll leave the settled sink empty.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        async def submit_then_fail_in_the_engine(*args, **kwargs):
            kwargs['submitted_sink'].append('batch-id')
            # Watched to a conclusion, and the conclusion was failure.
            kwargs['terminal_sink'].append('batch-id')
            raise ToolError('Statement failed: ERROR: division by zero')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_fail_in_the_engine,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'dev', 'SELECT 1/0', commit_transaction='load')

        assert 'division by zero' in str(raised.value)
        assert 'may or may not have been applied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_cancelled_open_releases_the_name(self, mocker):
        """Cancellation is a BaseException, so the failure handlers never see it.

        Left claimed, the name answers both 'already open' and 'no open transaction', and no
        call the caller can make clears it.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )

        async def cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=cancelled,
        )

        with pytest.raises(asyncio.CancelledError):
            await _begin_transaction('test-cluster', 'test-db', 'load')

        # Free again, rather than claimed by a transaction that never opened.
        assert redshift_module.transaction_manager._transactions == {}

    @pytest.mark.asyncio
    async def test_a_cancelled_open_rolls_back_the_session_it_minted(self, mocker):
        """Freeing the name alone would leave more live sessions than the cap admits.

        The rollback is detached because a task being torn down cannot await its own cleanup,
        so this waits a tick for it to run.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        async def mint_then_cancel(*args, **kwargs):
            kwargs['session_sink'].append('session-1')
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=mint_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await _begin_transaction('test-cluster', 'test-db', 'load')

        await asyncio.sleep(0)

        assert rollback.call_args[0][3] == 'session-1'
        assert redshift_module.transaction_manager._transactions == {}

    @pytest.mark.asyncio
    async def test_an_unrelated_aws_error_is_not_disguised_as_a_missing_transaction(self, mocker):
        """Throttling or a credential problem is not the transaction's fault.

        It is refused at submit, so nothing ran and the transaction is untouched. Dropping the
        name here would leave it open on the cluster with no call able to close it, and would
        turn a retryable error into lost work.
        """
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'BatchExecuteStatement',
            ),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        with pytest.raises(ClientError):
            await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

        # Nothing was rolled back, and the name is still the caller's to close.
        await execute_query('test-cluster', 'dev', rollback_transaction='load')
        assert batches.call_args[1]['sqls'] == ['ROLLBACK']
        assert batches.call_args[1]['session_id'] == 'session-1'

    @pytest.mark.asyncio
    async def test_a_cancellation_after_the_closer_ran_still_reports_it_closed(self, mocker):
        """A durable COMMIT is the fact, whatever cut the call short afterwards.

        Reported as a cancellation instead, the one record saying the work persisted would
        never be written, and an operator reading the log after a client timeout would have
        nothing to tell them the commit landed.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        await execute_query('test-cluster', 'dev', begin_transaction='load')

        async def settle_then_cancel(*args, **kwargs):
            # Every sink a finished batch fills, in the order the real path fills them.
            kwargs['submitted_sink'].append('batch-id')
            kwargs['terminal_sink'].append('batch-id')
            kwargs['settled_sink'].append('batch-id')
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=settle_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query('test-cluster', 'dev', 'SELECT 1', commit_transaction='load')

        await asyncio.sleep(0)

        # Nothing is rolled back over a commit that already stands.
        rollback.assert_not_called()
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_cancelled_statement_drops_the_name_and_drains_its_session(self, mocker):
        """Cancellation is not an Exception, so the arms above it never see it.

        The transaction is left mid-flight on a session nothing will reach again, so the name
        must go, and the session is drained rather than held for the whole keepalive.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        await execute_query('test-cluster', 'dev', begin_transaction='load')

        async def cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=cancelled,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query('test-cluster', 'dev', 'SELECT 1', in_transaction='load')

        await asyncio.sleep(0)

        assert rollback.call_args[0][3] == 'session-1'
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'dev', commit_transaction='load')

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


class TestTransactionOutcome:
    """One reading of the three sinks, so three arms cannot answer one state differently.

    Each arm used to test the sinks itself, with conditions that drifted apart: one keyed on
    `settled` alone, one required a closer where none was needed. Both defects were invisible
    at the call site and are a table lookup here.
    """

    @pytest.mark.parametrize(
        ('closer', 'submitted', 'settled', 'terminal', 'expected'),
        [
            # A closer watched to a finish stands, whatever failed afterwards.
            ('COMMIT', True, True, True, redshift_module._CLOSER_RAN),
            ('ROLLBACK', True, True, True, redshift_module._CLOSER_RAN),
            # Accepted and never seen to end: it may be applying right now.
            ('COMMIT', True, False, False, redshift_module._CLOSER_UNKNOWN),
            # Concluded, and not as a finish, so the transaction is gone on the cluster. Not
            # conditioned on a closer: a statement that aborts ends it either way.
            ('COMMIT', True, False, True, redshift_module._ABORTED),
            (None, True, False, True, redshift_module._ABORTED),
            # Nothing accepted, so the transaction is as the caller left it.
            ('COMMIT', False, False, False, redshift_module._UNRESOLVED),
            (None, True, False, False, redshift_module._UNRESOLVED),
            (None, False, False, False, redshift_module._UNRESOLVED),
        ],
    )
    def test_the_outcome_of_every_reachable_state(
        self, closer, submitted, settled, terminal, expected
    ):
        """The sinks hold batch ids, and only whether each is filled decides the outcome."""
        outcome = redshift_module._transaction_outcome(
            closer,
            ['batch-id'] if submitted else [],
            ['batch-id'] if settled else [],
            ['batch-id'] if terminal else [],
        )

        assert outcome == expected


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

    @pytest.mark.parametrize(
        'action',
        [
            'redshift:GetClusterCredentialsWithIAM',
            'redshift-serverless:GetCredentials',
            'secretsmanager:GetSecretValue',
        ],
    )
    def test_a_denial_of_a_grant_the_data_api_needs_is_not_the_signal(self, action):
        """The batch call reports these on its own operation, and the fallback needs them too.

        Latching on one would tell the operator to grant BatchExecuteStatement, which they
        already hold, while the compatibility path fails on the very same missing grant.
        """
        assert _is_no_batch(_batch_denied_error(action)) is False

    def test_a_denial_that_names_no_action_still_latches(self):
        """The message shape is AWS's, not a contract, so an unparseable one keeps the old rule.

        Read the other way, a reworded message would stop the fallback engaging at all and
        leave denied credentials with raw AWS errors instead of the compatibility path.
        """
        error = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'BatchExecuteStatement',
        )

        assert _is_no_batch(error) is True


class TestSettleRechecksTheConfirmingDescribe:
    """A submit settled by long polling is owed one describe, whose answer is not taken on trust.

    Only describe carries the sub-statement ids, so that call has to happen; returning it
    unchecked meant whatever it answered became the caller's terminal batch.
    """

    def _data_client(self, mocker, describes):
        """Wire a Data API client scripted to answer describe_statement in order."""
        client = mocker.Mock()
        client.describe_statement.side_effect = describes
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=client,
        )
        return client

    async def _settle(self, submit, **kwargs):
        """Settle a submit response with intervals short enough not to slow the suite."""
        return await _settle_statement(
            statement_id='batch-id',
            response=submit,
            query_poll_interval=0.001,
            query_timeout=5,
            query_long_poll=0,
            **kwargs,
        )

    @pytest.mark.asyncio
    async def test_a_non_terminal_confirming_describe_is_polled_on(self, mocker):
        """Returned as-is, it reached the caller as a settled batch with no SubStatements."""
        settled = _fake_batch(['FINISHED'])
        client = self._data_client(
            mocker,
            # The status went backwards, so this answer is not the batch's outcome.
            [{'Id': 'batch-id', 'Status': 'STARTED'}, settled],
        )

        result = await self._settle({'Id': 'batch-id', 'Status': 'FINISHED'})

        assert result is settled
        assert 'SubStatements' in result
        assert client.describe_statement.call_count == 2

    @pytest.mark.asyncio
    async def test_a_confirming_describe_with_no_status_is_polled_on(self, mocker):
        """It used to be subscripted for the log line, which raised a bare KeyError."""
        settled = _fake_batch(['FINISHED'])
        self._data_client(mocker, [{'Id': 'batch-id'}, settled])

        assert await self._settle({'Id': 'batch-id', 'Status': 'FINISHED'}) is settled

    @pytest.mark.asyncio
    async def test_the_settled_sink_is_filled_exactly_once(self, mocker):
        """The re-check passes the terminal branch twice, and the sink counts statements."""
        self._data_client(
            mocker, [{'Id': 'batch-id', 'Status': 'STARTED'}, _fake_batch(['FINISHED'])]
        )
        settled: list[str] = []

        await self._settle({'Id': 'batch-id', 'Status': 'FINISHED'}, settled_sink=settled)

        assert settled == ['batch-id']

    @pytest.mark.asyncio
    async def test_only_one_describe_is_taken_when_the_submit_already_carries_the_ids(
        self, mocker
    ):
        """The ordinary settled submit must not pay a second round trip for the re-check."""
        client = self._data_client(mocker, [_fake_batch(['FINISHED'])])

        await self._settle({'Id': 'batch-id', 'Status': 'FINISHED'})

        assert client.describe_statement.call_count == 1

    @pytest.mark.asyncio
    async def test_a_conclusion_is_recorded_whatever_it_was(self, mocker):
        """The two sinks answer different questions, and a failure separates them.

        settled_sink says the statement finished; terminal_sink says this call saw it conclude
        at all. Only the second distinguishes a batch that failed from one whose poll was
        abandoned, which is what decides whether a closer's outcome is known.
        """
        self._data_client(mocker, [_fake_batch(['FAILED'])])
        settled: list[str] = []
        terminal: list[str] = []

        await self._settle(
            {'Id': 'batch-id', 'Status': 'FAILED'},
            settled_sink=settled,
            terminal_sink=terminal,
        )

        assert settled == []
        assert terminal == ['batch-id']

    @pytest.mark.asyncio
    async def test_a_conclusion_is_recorded_once(self, mocker):
        """The re-check passes the terminal branch twice, and both sinks count statements."""
        self._data_client(
            mocker, [{'Id': 'batch-id', 'Status': 'STARTED'}, _fake_batch(['FINISHED'])]
        )
        terminal: list[str] = []

        await self._settle({'Id': 'batch-id', 'Status': 'FINISHED'}, terminal_sink=terminal)

        assert terminal == ['batch-id']

    @pytest.mark.asyncio
    async def test_an_unrecognized_status_is_polled_on_and_reported_once(self, mocker):
        """A status the API adds must not fail every statement, nor poll out in silence."""
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        self._data_client(
            mocker,
            [
                {'Id': 'batch-id', 'Status': 'QUEUED'},
                {'Id': 'batch-id', 'Status': 'QUEUED'},
                _fake_batch(['FINISHED']),
            ],
        )

        result = await self._settle({'Id': 'batch-id', 'Status': 'QUEUED'})

        assert result['Status'] == 'FINISHED'
        assert warning.call_count == 1
        assert "'QUEUED'" in warning.call_args[0][0]


class TestBatchLatch:
    """The latch holds the compatibility path without paying a denied call per statement."""

    def test_the_batch_path_is_attempted_by_default(self):
        """Nothing is assumed about the credentials until a call is refused."""
        assert _no_batch_active('test-cluster') is False

    def test_a_denial_latches_and_names_the_grant(self, mocker):
        """One warning per latch, carrying the action to grant."""
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        assert _no_batch_active('test-cluster') is True
        assert warning.call_count == 1
        assert 'redshift-data:BatchExecuteStatement' in warning.call_args[0][0]

    def test_the_batch_path_is_probed_again_once_the_window_elapses(self, mocker):
        """A granted policy is picked up without restarting the server."""
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        assert _no_batch_active('test-cluster') is False
        # Consumed, so a still-denied batch latches again rather than warning per statement.
        assert redshift_module._no_batch_since == {}

    def test_a_denial_on_one_cluster_says_nothing_about_another(self, mocker):
        """The action takes resource-level permissions, so one denial is not a verdict on all.

        Held process-wide, a denial on one cluster refused writes and named transactions on
        every other, and told the caller their credentials lacked an action they held.
        """
        mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        _latch_no_batch(_batch_denied_error(), 'denied-cluster')

        assert _no_batch_active('denied-cluster') is True
        assert _no_batch_active('permitted-cluster') is False

        # And the reprobe on one does not consume the other's.
        _latch_no_batch(_batch_denied_error(), 'permitted-cluster')
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)
        assert _no_batch_active('denied-cluster') is False
        assert set(redshift_module._no_batch_since) == {'permitted-cluster'}


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
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        batch = self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        _, query_id = await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        assert batch.call_count == 1
        assert single.call_args[1]['sql'] == 'SELECT 1'
        assert query_id == 'stmt-id'
        assert _no_batch_active('test-cluster') is True

    @pytest.mark.asyncio
    async def test_the_wrapper_is_dropped_with_the_batch(self, mocker):
        """One statement per connection leaves nowhere to put BEGIN READ ONLY."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        assert single.call_args[1]['sql'] == 'SELECT 1'

    @pytest.mark.asyncio
    async def test_a_latched_server_does_not_attempt_the_batch(self, mocker):
        """The point of the latch is to stop paying a denied call per statement."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch_for_statement')
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        batch.assert_not_called()
        assert single.call_count == 1

    @pytest.mark.asyncio
    async def test_server_authored_discovery_still_works(self, mocker):
        """Every SHOW this server issues classifies as a read, so discovery survives."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        await execute_standalone_statement(
            'test-cluster', 'test-db', 'SHOW DATABASES;', enforce_read_only=False
        )

        assert single.call_args[1]['sql'] == 'SHOW DATABASES;'

    @pytest.mark.asyncio
    async def test_a_write_is_refused_and_names_the_grant(self, mocker):
        """Without the wrapper a write cannot be contained, so it is refused rather than run."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        with pytest.raises(ToolError, match='redshift-data:BatchExecuteStatement'):
            await execute_standalone_statement(
                'test-cluster', 'test-db', 'INSERT INTO t VALUES (1)', enforce_read_only=False
            )

        single.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_unrelated_client_error_is_not_absorbed(self, mocker):
        """A denial that is not about the batch action must not select the fallback."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'nope'}}, 'Batch'
            ),
        )
        single = self._capture_single(mocker)

        with pytest.raises(ClientError):
            await execute_standalone_statement('test-cluster', 'test-db', 'SELECT 1')

        single.assert_not_called()
        assert _no_batch_active('test-cluster') is False


class TestTransactionsNeedTheBatch:
    """A transaction is several statements on one connection, which the fallback cannot give."""

    @pytest.mark.asyncio
    async def test_opening_is_refused_while_latched(self):
        """Refused before any work, so no name is reserved."""
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        with pytest.raises(ToolError, match='Named transactions need'):
            await _begin_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_adding_to_one_is_refused_while_latched(self):
        """The same refusal, so the caller is not told the name is merely unknown."""
        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        with pytest.raises(ToolError, match='Named transactions need'):
            await _execute_statement_in_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_closing_one_is_honoured_while_latched(self, mocker):
        """A closer needs nothing from the batch, and refusing it stranded the caller.

        The name could not be closed and its slot stayed against the cap until the re-probe,
        which is up to FALLBACK_NO_BATCH_REPROBE away.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        manager = redshift_module.transaction_manager
        key = redshift_module.transaction_key('test-cluster', 'test-db', 'load')
        target = redshift_module.transaction_target('test-cluster', 'test-db')

        _latch_no_batch(_batch_denied_error(), 'test-cluster')

        for closer in ('COMMIT', 'ROLLBACK'):
            manager.reserve(key, target, 'load')
            manager.attach(key, 'session-1')

            with pytest.raises(ToolError, match='cannot be closed on the cluster'):
                await _execute_statement_in_transaction(
                    'test-cluster', 'test-db', 'load', None, closer=closer
                )

            # Released here, so the caller is not holding a name they cannot use.
            assert key not in manager._transactions

    @pytest.mark.asyncio
    async def test_a_denial_while_opening_drops_the_name(self, mocker):
        """A reserved name must not linger when the batch it needed was refused."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )

        with pytest.raises(ToolError, match='Named transactions need'):
            await _begin_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')

        assert _no_batch_active('test-cluster') is True
        # The name is free again, so a later call under it reports it as unknown.
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.session_id(
                'test-cluster:test-db:load', 'load', 'test-cluster:test-db'
            )

    @pytest.mark.asyncio
    async def test_a_session_minted_by_a_failed_open_is_rolled_back(self, mocker):
        """A transaction that opened and then failed must not leave its session holding it.

        Dropping the name alone would leave an aborted transaction alive on a session nobody
        can reach, until its keepalive expires, and outside the cap the whole time.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
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
            redshift_module.transaction_manager.session_id(
                'test-cluster:test-db:load', 'load', 'test-cluster:test-db'
            )

    @pytest.mark.asyncio
    async def test_a_denial_inside_one_drops_the_name(self, mocker):
        """An open transaction turns unreachable, so its name goes rather than misleading.

        And the refusal says so. Told only that transactions need the action, the caller
        would grant it and go looking for a transaction this call had already given up on.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )
        key = 'test-cluster:test-db:load'
        redshift_module.transaction_manager.reserve(key, 'test-cluster:test-db', 'load')
        redshift_module.transaction_manager.attach(key, 'session-1')

        with pytest.raises(ToolError, match='denied partway through') as raised:
            await _execute_statement_in_transaction('test-cluster', 'test-db', 'load', 'SELECT 1')
        assert 'had not committed is discarded' in str(raised.value)

        assert _no_batch_active('test-cluster') is True
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.session_id(key, 'load', 'test-cluster:test-db')


class TestGuaranteesNothingElsePins:
    """Guarantees a mutation sweep could break with the rest of the suite still passing.

    Each of these is a property some earlier fix on this branch established, and each was
    invisible to the tests until now: removing the check, or inverting it, changed no result
    anything asserted on.
    """

    def test_reaping_is_scoped_to_the_target_being_opened(self, mocker):
        """One cluster's idle transactions are not another's to reap.

        Dropping the target comparison reaped every idle transaction in the process whenever
        any target opened one, and nothing noticed.
        """
        mocker.patch('awslabs.redshift_mcp_server.transactions.session_keepalive', return_value=0)
        manager = RedshiftTransactionManager()

        for cluster in ('cluster-a', 'cluster-b'):
            key = redshift_module.transaction_key(cluster, 'dev', 'load')
            manager.reserve(key, redshift_module.transaction_target(cluster, 'dev'), 'load')
            manager.attach(key, f'session-{cluster}')

        # Opening on A reaps A's expired entry and must leave B's alone.
        manager.reserve(
            redshift_module.transaction_key('cluster-a', 'dev', 'other'),
            redshift_module.transaction_target('cluster-a', 'dev'),
            'other',
        )

        assert redshift_module.transaction_key('cluster-b', 'dev', 'load') in manager._transactions

    def test_in_use_means_the_lock_is_held_not_merely_created(self, mocker):
        """`forget` keeps the lock object, so its existence cannot be what exempts a key.

        Read as "a lock exists", every key that had ever been claimed was exempt and reaping
        stopped happening at all.
        """
        mocker.patch('awslabs.redshift_mcp_server.transactions.session_keepalive', return_value=0)
        manager = RedshiftTransactionManager()
        key = redshift_module.transaction_key('test-cluster', 'dev', 'load')
        target = redshift_module.transaction_target('test-cluster', 'dev')
        manager.reserve(key, target, 'load')
        manager.attach(key, 'session-1')
        # Claimed and released, so a lock exists and nobody holds it.
        manager.claim(key)

        manager.reserve(
            redshift_module.transaction_key('test-cluster', 'dev', 'other'), target, 'other'
        )

        assert key not in manager._transactions

    def test_the_latch_peek_does_not_consume_the_reprobe(self, mocker):
        """`no_batch_latched` answers a question; only `_no_batch_active` decides a path.

        Consuming the re-probe here would let a confirmation prompt clear the latch, so the
        statement that followed took the batch path the peek had just said was denied.
        """
        mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        _latch_no_batch(_batch_denied_error(), 'test-cluster')
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)

        assert redshift_module.no_batch_latched('test-cluster') is True
        assert redshift_module.no_batch_latched('test-cluster') is True
        # And the probe is still there for the call that decides.
        assert _no_batch_active('test-cluster') is False

    @pytest.mark.asyncio
    async def test_a_read_only_statement_raises_no_unwatched_write_report(self, mocker):
        """The wrapper discards whatever ran, so there is nothing to warn about."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )

        async def accept_then_time_out(*args, **kwargs):
            kwargs['submitted_sink'].append('batch-id')
            raise ToolError('Statement timed out after 3600 seconds')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=accept_then_time_out,
        )

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', enforce_read_only=True
            )

        assert 'may or may not have been applied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_write_that_never_reached_the_service_is_not_called_unknown(self, mocker):
        """Nothing was accepted, so nothing can have been applied."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=ToolError('Statement failed: could not connect'),
        )

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'dev', 'INSERT INTO t VALUES (1)', enforce_read_only=False
            )

        assert 'may or may not have been applied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_aborted_ends_the_poll(self, mocker):
        """A cancelled statement is terminal, and polling one to the deadline would hang a call."""
        client = mocker.Mock()
        client.describe_statement.return_value = {'Id': 'stmt-id', 'Status': 'ABORTED'}
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=client,
        )

        settled = await _settle_statement(
            statement_id='stmt-id',
            response={'Id': 'stmt-id', 'Status': 'ABORTED'},
            query_poll_interval=0.001,
            query_timeout=5,
            query_long_poll=0,
        )

        assert settled['Status'] == 'ABORTED'
        assert client.describe_statement.call_count == 1
