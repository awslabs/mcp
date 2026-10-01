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
import re
import time
from awslabs.redshift_mcp_server import redshift as redshift_module
from awslabs.redshift_mcp_server.consts import (
    MAX_SQL_LEN,
    QUERY_LONG_POLL,
)
from awslabs.redshift_mcp_server.models import ClusterKey, RedshiftDataModel
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
    _read_result,
    _resolve_transaction_action,
    _settle_statement,
    execute_query,
    execute_standalone_statement,
)
from awslabs.redshift_mcp_server.settings import (
    session_keepalive,
)
from awslabs.redshift_mcp_server.transactions import NamedTransactionManager
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)
from helpers import _batch_denied_error, _client_error, _fake_batch, _fake_cluster
from mcp.server.mcpserver.exceptions import ToolError
from typing import Any


# What `_fake_cluster()` is keyed as: its identifier and type.
_CLUSTER = ClusterKey('test-cluster', 'provisioned')


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
            'test-cluster', 'provisioned', 'test-db', 'SELECT 1', enforce_read_only=True
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
            'provisioned',
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
            'provisioned',
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
                'provisioned',
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
                await execute_standalone_statement('test-cluster', 'provisioned', 'test-db', sql)

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
                'test-cluster', 'provisioned', 'test-db', 'SELECT ' + 'x' * MAX_SQL_LEN
            )

        mock_execute_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_cluster_not_found_when_none_discovered(self, mocker):
        """An unknown cluster is named in the error, with the tool that lists valid ones."""
        mocker.patch('awslabs.redshift_mcp_server.clusters.discover_clusters', return_value=[])

        with pytest.raises(ToolError, match='Cluster nonexistent-cluster not found'):
            await execute_standalone_statement(
                'nonexistent-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

    @pytest.mark.asyncio
    async def test_cluster_not_in_list(self, mocker):
        """A cluster missing from a non-empty discovery result is still not found."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster(identifier='other-cluster')],
        )

        with pytest.raises(ToolError, match='Cluster target-cluster not found'):
            await execute_standalone_statement(
                'target-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

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
            'test-cluster', 'provisioned', 'test-db', 'SELECT 1 AS one'
        )

        mock_data_client.get_statement_result.assert_called_once_with(Id='batch-id:3')
        assert results_response == expected
        assert query_id == 'batch-id:3'

    @pytest.mark.parametrize(('cap', 'refused'), [(2, False), (1, True)], ids=['whole', 'over'])
    @pytest.mark.asyncio
    async def test_the_batch_path_reads_every_page_and_holds_to_the_cap(
        self, mocker, cap, refused
    ):
        """Every tool runs through here when the batch action is granted.

        Paging and the cap were pinned only on the fallback and on the reader itself, so a batch
        path that read one page would have passed.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch.object(redshift_module, 'max_result_rows', return_value=cap)
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                ['FINISHED', 'FINISHED', {'has_result_set': True}, 'FINISHED']
            ),
        )
        mock_data_client = mocker.Mock()
        mock_data_client.get_statement_result.side_effect = [
            {
                'ColumnMetadata': [{'name': 'n'}],
                'Records': [[{'longValue': 1}]],
                'NextToken': 'p2',
            },
            {'Records': [[{'longValue': 2}]]},
            AssertionError('read past the scripted pages'),
        ]
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        if refused:
            with pytest.raises(ToolError, match='more than 1 rows'):
                await execute_standalone_statement(
                    'test-cluster', 'provisioned', 'test-db', 'SELECT n FROM t'
                )
            return

        results_response, _ = await execute_standalone_statement(
            'test-cluster', 'provisioned', 'test-db', 'SELECT n FROM t'
        )
        assert results_response['Records'] == [[{'longValue': 1}], [{'longValue': 2}]]

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
            'provisioned',
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
                    # The ROLLBACK after it still runs: an AUTO_COMMIT batch carries on.
                    'FINISHED',
                ],
                error='Query #3 failed',
            ),
        )

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'test-db', 'SELECT * FROM nope'
            )

        assert str(raised.value) == 'Statement failed: ERROR: relation "nope" does not exist'

    @pytest.mark.asyncio
    async def test_a_batch_that_aborted_is_a_failure(self, mocker):
        """ABORTED is terminal and is not FINISHED, so nothing it carried can be returned.

        Checked for failure by name instead, a batch cancelled on the cluster came back as an
        empty success - and a COMMIT among its statements read as applied.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(
                ['FINISHED', 'FINISHED', 'ABORTED', 'ABORTED'],
                status='ABORTED',
                error='Query was cancelled',
            ),
        )

        with pytest.raises(ToolError, match='Statement failed: Query was cancelled'):
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

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
                'test-cluster',
                'provisioned',
                'awsdatacatalog',
                'SHOW SCHEMAS',
                enforce_read_only=False,
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
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

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
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

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
            'test-cluster', 'provisioned', 'test-db', 'SELECT :answer', parameters=parameters
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
            # Ends in a failure, because running out inside asyncio.to_thread hangs.
            mock_data_client.describe_statement.side_effect = [
                *describes,
                AssertionError('described more often than scripted'),
            ]
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
                'test-db',
                ['BEGIN READ ONLYY', 'CREATE TABLE t (i int)'],
                caller_index=1,
            )

    @pytest.mark.asyncio
    async def test_an_accepted_batch_clears_its_clusters_latch(self, mocker):
        """Accepted, the action is permitted there now, whichever call latched the denial.

        Cleared by a closer alone, a statement that ran on a restored grant left every write and
        transaction on the cluster refused as denied until the re-probe.
        """
        self._data_client(mocker, describes=[_fake_batch(['FINISHED'])])
        mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        other = ClusterKey('other-cluster', 'provisioned')
        _latch_no_batch(_batch_denied_error(), _CLUSTER)
        _latch_no_batch(_batch_denied_error(), other)

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])

        assert set(redshift_module._no_batch_since) == {other}

    @pytest.mark.asyncio
    async def test_batch_runs_with_auto_commit_and_no_data_api_transaction(self, mocker):
        """TRANSACTION mode would commit at batch end and defeat the read-only wrapper."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED', 'FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-db', [_APP_NAME_SQL, 'SELECT 1'])

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert request['ExecutionMode'] == 'AUTO_COMMIT'
        assert request['Sqls'] == [_APP_NAME_SQL, 'SELECT 1']
        assert request['Database'] == 'test-db'

    @pytest.mark.asyncio
    async def test_a_finished_batch_is_recorded_before_its_result_is_read(self, mocker):
        """Everything in it has run by then, so nothing later can undo it.

        Recorded after the confirming describe instead, a throttle on that call would look to
        the caller like a batch this call never saw conclude, and a COMMIT that had applied would
        be reported as possibly applied.
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
                'test-db',
                ['COMMIT'],
                settled_sink=settled,
            )

        assert settled == ['batch-id']

    @pytest.mark.asyncio
    async def test_a_batch_that_never_concludes_fills_no_sink(self, mocker):
        """Which is how a failed call tells an unanswered batch from one it watched conclude."""
        mock_data_client = self._data_client(mocker, submit={'Id': 'batch-id', 'Status': 'PICKED'})
        mock_data_client.describe_statement.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )
        settled: list[str] = []
        terminal: list[str] = []

        with pytest.raises(ClientError, match='Rate exceeded'):
            await _execute_batch(
                _fake_cluster(),
                'test-db',
                ['COMMIT'],
                settled_sink=settled,
                terminal_sink=terminal,
                query_poll_interval=0,
            )

        assert settled == []
        assert terminal == []

    @pytest.mark.asyncio
    async def test_a_batch_that_did_not_finish_is_not_recorded(self, mocker):
        """The sink is what tells a caller its closer ran, so a failure must not fill it."""
        self._data_client(
            mocker,
            submit={'Id': 'batch-id', 'Status': 'FAILED'},
            describes=[_fake_batch([{'status': 'FAILED', 'error': 'ERROR: nope'}])],
        )
        settled: list[str] = []

        await _execute_batch(_fake_cluster(), 'test-db', ['COMMIT'], settled_sink=settled)

        assert settled == []

    @pytest.mark.asyncio
    async def test_every_submit_carries_its_own_client_token(self, mocker):
        """A submit whose response was lost is retried by botocore, which would write twice."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-db', ['UPDATE t SET n = 1'])
        first = mock_data_client.batch_execute_statement.call_args[1]['ClientToken']

        await _execute_batch(_fake_cluster(), 'test-db', ['UPDATE t SET n = 1'])
        second = mock_data_client.batch_execute_statement.call_args[1]['ClientToken']

        # One token per submit: shared across submits it would suppress the second write.
        assert first and second and first != second

    @pytest.mark.asyncio
    async def test_provisioned_and_serverless_are_addressed_differently(self, mocker):
        """A workgroup is not a cluster, and the Data API takes them under different names."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])
        assert mock_data_client.batch_execute_statement.call_args[1]['ClusterIdentifier'] == (
            'test-cluster'
        )

        await _execute_batch(
            _fake_cluster(identifier='test-workgroup', type='serverless'), 'test-db', ['SELECT 1']
        )
        assert mock_data_client.batch_execute_statement.call_args[1]['WorkgroupName'] == (
            'test-workgroup'
        )

    @pytest.mark.asyncio
    async def test_unknown_cluster_type_is_a_crash_not_a_tool_error(self, mocker):
        """Discovery only sets provisioned or serverless, so anything else is this server's bug."""
        self._data_client(mocker)

        with pytest.raises(Exception, match='Unknown cluster type: unknown-type') as failure:
            await _execute_batch(_fake_cluster(type='unknown-type'), 'test-db', ['SELECT 1'])

        assert not isinstance(failure.value, ToolError)

    @pytest.mark.asyncio
    async def test_parameters_are_sent_only_when_present(self, mocker):
        """An empty Parameters list is not the same as omitting it, so it is omitted."""
        mock_data_client = self._data_client(
            mocker, describes=[_fake_batch(['FINISHED']), _fake_batch(['FINISHED'])]
        )

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])
        assert 'Parameters' not in mock_data_client.batch_execute_statement.call_args[1]

        parameters = [{'name': 'answer', 'value': '365'}]
        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT :answer'], parameters=parameters)
        assert mock_data_client.batch_execute_statement.call_args[1]['Parameters'] == parameters

    @pytest.mark.asyncio
    async def test_a_session_replaces_the_cluster_and_database(self, mocker):
        """A session already holds the connection, and the API refuses to be told again."""
        mock_data_client = self._data_client(mocker, describes=[_fake_batch(['FINISHED'])])

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'], session_id='session-1')

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

        await _execute_batch(_fake_cluster(), 'test-db', ['BEGIN'])
        assert (
            'SessionKeepAliveSeconds'
            not in (mock_data_client.batch_execute_statement.call_args[1])
        )

        await _execute_batch(_fake_cluster(), 'test-db', ['BEGIN'], session_keepalive=42)
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

        batch = await _execute_batch(_fake_cluster(), 'test-db', [_APP_NAME_SQL, 'SELECT 1'])

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

        batch = await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])

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

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])

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

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'], query_long_poll=0)

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

        await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])

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
            await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'])

    @pytest.mark.asyncio
    async def test_timeout_is_reported_as_an_anticipated_failure(self, mocker):
        """A batch that never settles is the caller's to know about, not a crash."""
        mock_data_client = self._data_client(
            mocker, submit={'Id': 'batch-id', 'Status': 'STARTED'}
        )

        # A zero budget is spent by the time the first non-terminal status is read.
        with pytest.raises(ToolError, match='Statement timed out after 0 seconds'):
            await _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1'], query_timeout=0)

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
            _execute_batch(_fake_cluster(), 'test-db', ['SELECT 1']),
            ticker(),
        )

        assert submitted.is_set()


class TestReadingAResultSet:
    """A result set is read to its end, or the call says why it was not."""

    def _pages(self, mocker, *pages):
        """Script the pages GetStatementResult will answer with."""
        client = mocker.Mock()
        # Ended with a failure: a list that runs out raises StopIteration on the worker thread, which
        # hangs the awaiting call instead of failing it.
        client.get_statement_result.side_effect = [
            *pages,
            AssertionError('read past the scripted pages'),
        ]
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=client,
        )
        return client

    @pytest.mark.asyncio
    async def test_every_page_is_read(self, mocker):
        """One read returned the first page as though it were the whole answer.

        The service pages a result set and hands back a NextToken while records remain. Rows were
        missing, `row_count` reported the page as the total, and nothing said so.
        """
        client = self._pages(
            mocker,
            {
                'ColumnMetadata': [{'name': 'id'}],
                'Records': [[{'longValue': 1}]],
                'NextToken': 'p2',
            },
            {'Records': [[{'longValue': 2}]], 'NextToken': 'p3'},
            {'Records': [[{'longValue': 3}]]},
        )

        result = await _read_result('stmt-id')

        assert result['Records'] == [
            [{'longValue': 1}],
            [{'longValue': 2}],
            [{'longValue': 3}],
        ]
        # The first page's metadata survives the concatenation, and each token is sent back.
        assert result['ColumnMetadata'] == [{'name': 'id'}]
        assert [
            call[1].get('NextToken') for call in client.get_statement_result.call_args_list
        ] == [
            None,
            'p2',
            'p3',
        ]
        # The whole answer, so it carries no token saying more remains.
        assert 'NextToken' not in result

    @pytest.mark.asyncio
    async def test_a_token_the_service_repeats_ends_the_read(self, mocker):
        """A token that comes back again is a page this would otherwise read forever.

        Inside a transaction it holds the name's lock while it spins, so nothing could reach that
        transaction again. The repeat is the bound that stops it after one page, where
        MAX_RESULT_PAGES would read thousands.
        """
        self._pages(
            mocker,
            {
                'ColumnMetadata': [{'name': 'id'}],
                'Records': [[{'longValue': 1}]],
                'NextToken': 'p',
            },
            {'Records': [[{'longValue': 2}]], 'NextToken': 'p'},
        )

        with pytest.raises(ToolError) as raised:
            await _read_result('stmt-id')

        # Named as a read that did not finish, not returned as though it were the whole result.
        assert 'did not advance' in str(raised.value)
        assert 'repeated a page token after 2 rows' in str(raised.value)

    @pytest.mark.asyncio
    async def test_paging_that_never_ends_is_bounded(self, mocker):
        """A fresh token every page is the shape the repeat guard does not catch.

        Left unbounded it holds the transaction's lock forever, and `_reap_expired` skips a
        transaction in use, so the name is unreachable and holds a slot against the cap for good.
        """
        mocker.patch.object(redshift_module, 'MAX_RESULT_PAGES', 3)
        client = mocker.Mock()
        client.get_statement_result.side_effect = lambda **kwargs: {
            'ColumnMetadata': [{'name': 'id'}],
            'Records': [[{'longValue': 1}]],
            'NextToken': f'p{client.get_statement_result.call_count}',
        }
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=client,
        )

        with pytest.raises(ToolError) as raised:
            await _read_result('stmt-id')

        assert 'did not end' in str(raised.value)
        assert 'more than 3 pages' in str(raised.value)
        # The bound is the pages read, not one more.
        assert client.get_statement_result.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize('reported', [3, 1], ids=['fewer_than_reported', 'more_than_reported'])
    async def test_pages_that_disagree_with_the_reported_size_are_not_the_result(
        self, mocker, reported
    ):
        """Returned, part of a result read as the whole of it, which paging exists to prevent.

        More rows than reported is no better an answer: one of the two is wrong, and nothing
        says which.
        """
        self._pages(
            mocker,
            {
                'ColumnMetadata': [{'name': 'id'}],
                'Records': [[{'longValue': 1}]],
                'NextToken': 'p2',
                'TotalNumRows': reported,
            },
            {'Records': [[{'longValue': 2}]]},
        )

        with pytest.raises(
            ToolError, match=f'reported {reported} rows for this result, but its pages carried 2'
        ):
            await _read_result('stmt-id')

    @pytest.mark.asyncio
    @pytest.mark.parametrize('stuck', ['repeated_token', 'page_bound'])
    async def test_nothing_read_here_tells_the_caller_to_run_the_statement_again(
        self, mocker, stuck
    ):
        """This does not know whether the statement ran; the callers that do already say.

        Appended to `_report_staged_statement` or `_report_write_outcome`, a retry told here
        landed last, after they had said not to - and an agent following the last line committed
        a second copy. Both ways the paging can fail to end raise here, so both are checked.
        """
        if stuck == 'repeated_token':
            self._pages(
                mocker,
                {'ColumnMetadata': [], 'Records': [[{'longValue': 1}]], 'NextToken': 'p'},
                {'Records': [], 'NextToken': 'p'},
            )
        else:
            mocker.patch.object(redshift_module, 'MAX_RESULT_PAGES', 1)
            self._pages(
                mocker,
                {'ColumnMetadata': [], 'Records': [[{'longValue': 1}]], 'NextToken': 'p1'},
                {'Records': [], 'NextToken': 'p2'},
            )

        with pytest.raises(ToolError) as raised:
            await _read_result('stmt-id')

        message = str(raised.value).lower()
        assert 'run the statement again' not in message
        assert 'retry' not in message

    @pytest.mark.asyncio
    async def test_a_result_over_the_cap_is_refused_from_its_first_page(self, mocker):
        """The first page reports the whole result's size, so nothing past it is read.

        Returned, a result this large is more than an agent can read; cut short, it reads as the
        whole. Refused, the caller is told the size and how to shape a result that fits.
        """
        mocker.patch.object(redshift_module, 'max_result_rows', return_value=1000)
        client = self._pages(
            mocker,
            {
                'ColumnMetadata': [{'name': 'id'}],
                'Records': [[{'longValue': 1}]] * 1000,
                'NextToken': 'p2',
                'TotalNumRows': 5000,
            },
            # Scripted so that reading on fails the call count below rather than hanging.
            {'Records': [[{'longValue': 1}]] * 1000},
        )

        with pytest.raises(ToolError) as raised:
            await _read_result('stmt-id')

        assert 'The result has 5000 rows, over the MAX_RESULT_ROWS limit of 1000' in str(
            raised.value
        )
        assert 'LIMIT' in str(raised.value)
        assert client.get_statement_result.call_count == 1

    @pytest.mark.asyncio
    async def test_a_result_whose_size_is_not_reported_is_counted(self, mocker):
        """Without the total on the first page, the rows read so far decide it."""
        mocker.patch.object(redshift_module, 'max_result_rows', return_value=3)
        client = self._pages(
            mocker,
            {'ColumnMetadata': [], 'Records': [[{'longValue': 1}]] * 2, 'NextToken': 'p2'},
            {'Records': [[{'longValue': 1}]] * 2},
        )

        with pytest.raises(ToolError, match='more than 3 rows, over the MAX_RESULT_ROWS limit'):
            await _read_result('stmt-id')

        assert client.get_statement_result.call_count == 2

    @pytest.mark.asyncio
    async def test_a_reported_size_under_the_cap_is_not_quoted_as_over_it(self, mocker):
        """Refused on the rows counted, it said 'The result has 2 rows, over the limit of 3'."""
        mocker.patch.object(redshift_module, 'max_result_rows', return_value=3)
        self._pages(
            mocker,
            {
                'ColumnMetadata': [],
                'Records': [[{'longValue': 1}]] * 2,
                'NextToken': 'p2',
                'TotalNumRows': 2,
            },
            {'Records': [[{'longValue': 1}]] * 2},
        )

        with pytest.raises(ToolError, match='The result has more than 3 rows, over the'):
            await _read_result('stmt-id')

    @pytest.mark.asyncio
    async def test_a_result_at_the_cap_is_returned_whole(self, mocker):
        """The cap is the most rows returned, so a result of exactly that many is not refused."""
        mocker.patch.object(redshift_module, 'max_result_rows', return_value=4)
        self._pages(
            mocker,
            {
                'ColumnMetadata': [],
                'Records': [[{'longValue': 1}]] * 2,
                'NextToken': 'p2',
                'TotalNumRows': 4,
            },
            {'Records': [[{'longValue': 1}]] * 2},
        )

        result = await _read_result('stmt-id')

        assert len(result['Records']) == 4

    @pytest.mark.asyncio
    async def test_a_result_that_fits_in_one_page_costs_one_call(self, mocker):
        """No token means no more records, so the common case is unchanged."""
        client = self._pages(mocker, {'ColumnMetadata': [], 'Records': [[{'longValue': 1}]]})

        result = await _read_result('stmt-id')

        assert result['Records'] == [[{'longValue': 1}]]
        assert client.get_statement_result.call_count == 1


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
    @pytest.mark.parametrize(
        ('sql', 'sinks', 'outcome'),
        [
            (
                'INSERT INTO t VALUES (1)',
                ('settled_sink', 'terminal_sink'),
                'after it finished, so it was applied (batch batch-1)',
            ),
            ('INSERT INTO t VALUES (1)', ('terminal_sink',), 'after it failed (batch batch-1)'),
            (
                'CALL p()',
                ('terminal_sink',),
                'after it failed, though a procedure may have committed part of it (batch batch-1)',
            ),
            (
                'INSERT INTO t VALUES (1)',
                (),
                'before it was seen to finish, so it may or may not have been applied',
            ),
        ],
        ids=['finished', 'failed', 'procedure_failed', 'unwatched'],
    )
    async def test_a_cancelled_write_records_what_became_of_it(self, mocker, sql, sinks, outcome):
        """No caller is left to tell, so the log is the only record.

        Cancellation skips the handler that reports a write's outcome, so a write that landed was
        not even logged, where the transaction path logs what became of a cancelled closer.
        """

        async def conclude_then_cancel(*args, **kwargs):
            for sink in sinks:
                kwargs[sink].append('batch-1')
            raise asyncio.CancelledError()

        self._wire(mocker, conclude_then_cancel)
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        with pytest.raises(asyncio.CancelledError):
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'dev', sql, enforce_read_only=False
            )

        warning.assert_called_once_with(
            f'A write on test-cluster (provisioned):dev was cancelled {outcome}'
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('sql', 'enforce_read_only'),
        [('SELECT 1', False), ('INSERT INTO t VALUES (1)', True)],
        ids=['read', 'read_only_mode'],
    )
    async def test_a_cancelled_statement_that_cannot_have_written_logs_nothing(
        self, mocker, sql, enforce_read_only
    ):
        """A read writes nothing, and the read-only wrapper discards what it ran."""

        async def cancel(*args, **kwargs):
            raise asyncio.CancelledError()

        self._wire(mocker, cancel)
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        with pytest.raises(asyncio.CancelledError):
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'dev', sql, enforce_read_only=enforce_read_only
            )

        warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_accepted_write_that_never_settles_is_not_reported_as_not_having_run(
        self, mocker
    ):
        """Unwrapped, the batch autocommits, and abandoning the poll cancels nothing.

        Reported as a bare timeout, a write that was still committing read as one that had not
        happened, so a caller who retried wrote twice.
        """

        async def accept_then_time_out(*args, **kwargs):
            raise ToolError('Statement timed out after 3600 seconds')

        self._wire(mocker, accept_then_time_out)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

        assert 'may or may not have been applied' in str(raised.value)
        # Still running, the write can land after the caller looks, so looking at once settles
        # nothing.
        assert 'once SYS_QUERY_HISTORY no longer shows it running' in str(raised.value)
        assert 'timed out' in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_read_in_read_write_mode_says_nothing_of_the_kind(self, mocker):
        """Unwrapped in read-write mode, a read still cannot write, so a failure needs no hedge.

        The catalog and discovery statements all run this way. Keyed on the access mode alone, a
        `SHOW` or `SELECT` that timed out was reported as possibly applied.
        """

        async def accept_then_time_out(*args, **kwargs):
            raise ToolError('Statement timed out after 3600 seconds')

        self._wire(mocker, accept_then_time_out)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', enforce_read_only=False
            )

        assert 'may or may not have been applied' not in str(raised.value)
        assert 'timed out' in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_read_only_failure_says_nothing_of_the_kind(self, mocker):
        """The wrapper's trailing ROLLBACK runs even after a statement fails, so nothing lands."""

        async def accept_then_time_out(*args, **kwargs):
            raise ToolError('Statement timed out after 3600 seconds')

        self._wire(mocker, accept_then_time_out)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement('test-cluster', 'provisioned', 'dev', 'SELECT 1')

        assert 'may or may not have been applied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_write_that_concluded_is_reported_as_it_concluded(self, mocker):
        """A batch seen to conclude needs no hedging: its outcome is known."""

        async def conclude_badly(*args, **kwargs):
            kwargs['terminal_sink'].append('batch-id')
            raise ToolError('Statement failed: ERROR: division by zero')

        self._wire(mocker, conclude_badly)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1/0)',
                enforce_read_only=False,
            )

        # Exactly the engine's failure: neither hedged nor reported as applied.
        assert str(raised.value) == 'Statement failed: ERROR: division by zero'

    @pytest.mark.asyncio
    async def test_a_procedure_that_failed_may_have_committed_part_of_its_work(self, mocker):
        """A procedure run outside a transaction block may COMMIT in its body.

        What it committed before failing stands. Reported as the bare failure, it read as a
        procedure that had not run, and a retry applied the committed part twice.
        """

        async def conclude_badly(*args, **kwargs):
            kwargs['terminal_sink'].append('batch-id')
            raise ToolError('Statement failed: ERROR: division by zero')

        self._wire(mocker, conclude_badly)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'dev', 'CALL load_orders()', enforce_read_only=False
            )

        assert 'some of it may have been applied' in str(raised.value)
        # Conditional, since a batch refused at the connection fails without the procedure ever
        # starting, and nothing here tells the two apart.
        assert 'if this one started' in str(raised.value)
        assert 'division by zero' in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_write_that_finished_is_not_silently_reported_as_an_aws_error(self, mocker):
        """A batch is recorded terminal the moment a status is seen, before anything reads it.

        So a write that finished and then failed on the confirming describe, or on reading its
        result, was silenced along with one that concluded badly: both fill `terminal`. The
        caller got a bare AWS error over a durable write and retried it.
        """

        async def finish_then_fail_reading(*args, **kwargs):
            for sink in ('settled_sink', 'terminal_sink'):
                kwargs[sink].append('batch-id')
            raise ConnectionClosedError(endpoint_url='https://redshift-data')

        self._wire(mocker, finish_then_fail_reading)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

        assert 'finished and was applied' in str(raised.value)
        assert 'do not retry it' in str(raised.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'error',
        [
            ReadTimeoutError(endpoint_url='https://redshift-data'),
            ConnectionClosedError(endpoint_url='https://redshift-data'),
            _client_error('InternalServerException', 'Internal error', status=500),
            # Raised at the connection and at signing: the last attempt's answer, which an
            # earlier attempt that transmitted and lost its response can precede.
            EndpointConnectionError(endpoint_url='https://redshift-data'),
            NoCredentialsError(),
        ],
        ids=['read_timeout', 'connection_closed', 'server_error', 'connect_failed', 'unsigned'],
    )
    async def test_a_submit_that_went_unanswered_is_not_silence(self, mocker, error):
        """With no conclusion seen, what the submit raised is no evidence the write did not land.

        It is the last retry attempt's answer, and an earlier attempt may have transmitted and
        lost its response. Reported bare, a write that may already be durable read as one that
        failed, and the agent retried it.
        """

        async def fail_at_submit(*args, **kwargs):
            raise error

        self._wire(mocker, fail_at_submit)

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

        assert 'may or may not have been applied' in str(raised.value)

    @pytest.mark.asyncio
    async def test_even_a_refusal_at_submit_is_hedged(self, mocker):
        """A refusal is the last attempt's answer, so it does not say the batch never ran.

        The client retries a throttle, and a limit error like ActiveStatementsExceededException can
        be raised precisely because an earlier attempt landed and is holding that limit. Read as
        proof that nothing ran, the caller retried a write that was already durable. The cost of
        hedging is one needless look at the data.
        """
        error = _client_error('ThrottlingException', 'Rate exceeded', status=429)

        async def fail_at_submit(*args, **kwargs):
            raise error

        self._wire(mocker, fail_at_submit)

        with pytest.raises(ToolError, match='may or may not have been applied'):
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

    @pytest.mark.asyncio
    async def test_a_read_only_statement_that_finished_says_nothing_of_the_kind(self, mocker):
        """The wrapper's trailing ROLLBACK ran with it, so a finished batch persisted nothing."""

        async def finish_then_fail_reading(*args, **kwargs):
            for sink in ('settled_sink', 'terminal_sink'):
                kwargs[sink].append('batch-id')
            raise ConnectionClosedError(endpoint_url='https://redshift-data')

        self._wire(mocker, finish_then_fail_reading)

        with pytest.raises(ConnectionClosedError):
            await execute_standalone_statement('test-cluster', 'provisioned', 'dev', 'SELECT 1')


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
            *({'Id': f'batch-{i}', 'Status': 'FINISHED'} for i in range(5)),
            AssertionError('submitted more often than scripted'),
        ]
        mock_data_client.describe_statement.side_effect = [
            *(
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
            ),
            AssertionError('described more often than scripted'),
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
                execute_standalone_statement(
                    'test-cluster', 'provisioned', 'test-db', f'SELECT {i}'
                )
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

        await execute_standalone_statement('test-cluster', 'provisioned', 'test-db', 'SELECT 1')

        request = mock_data_client.batch_execute_statement.call_args[1]
        assert 'SessionId' not in request
        assert 'SessionKeepAliveSeconds' not in request

    @pytest.mark.asyncio
    async def test_a_name_reopened_while_a_statement_waits_for_the_lock_is_refused(self, mocker):
        """The handle is validated where the lock is taken, not where it was obtained.

        Waiting for the lock is an await, and the name can be closed and reopened across it.
        Submitted on the handle it started with, the statement ran on the closed transaction's
        session after its COMMIT: in autocommit and outside `BEGIN READ ONLY`, where a write
        persists.
        """
        manager = redshift_module.transaction_manager
        original = manager.open(_CLUSTER, 'dev', 'load')
        original.attach('session-original')

        at_the_lock = asyncio.Event()
        reopened = asyncio.Event()

        async def resolve_and_leave_it_at_the_lock(*_args):
            # Nothing after this suspends until the lock, so the statement is waiting on it by
            # the time this event wakes the test.
            at_the_lock.set()
            return _fake_cluster()

        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster',
            side_effect=resolve_and_leave_it_at_the_lock,
        )
        batches = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            return_value=(_fake_batch(['FINISHED']), 'batch-id:1', None),
        )

        async def hold_it_until_reopened():
            async with manager.holding(original):
                await reopened.wait()

        parked = asyncio.create_task(hold_it_until_reopened())
        await asyncio.sleep(0)

        adding = asyncio.create_task(
            _execute_statement_in_transaction(
                'test-cluster', 'provisioned', 'dev', 'load', 'SELECT 1'
            )
        )
        await at_the_lock.wait()

        # The transaction it named is committed, and the name is taken by a new one.
        manager.forget(original)
        manager.open(_CLUSTER, 'dev', 'load').attach('session-someone-else')
        reopened.set()
        await parked

        with pytest.raises(ToolError, match='closed while this statement was waiting') as raised:
            await adding

        # The name is open again, so advice to reopen it is answered 'already open'.
        assert 'Open it again' not in str(raised.value)
        # Nothing was sent, on either session.
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
                    {'name': 'raw'},
                    {'name': 'from_the_future'},
                ],
                'Records': [
                    [
                        {'longValue': 1},
                        {'stringValue': 'Test User'},
                        {'doubleValue': 95.5},
                        {'booleanValue': True},
                        {'isNull': True},
                        # A blob, a member the API defines; Redshift sends VARBYTE as base64 in
                        # stringValue. Passed through as bytes, the MCP layer decoded it as UTF-8:
                        # silently a string the caller cannot tell from a real one, or a
                        # UnicodeDecodeError raised past this server's error handling.
                        {'blobValue': b'\xff\xfe'},
                        # A member the pinned botocore does not know, which it hands over under
                        # this name having already discarded the value. Returned as the member
                        # itself, it reached a model expecting a scalar as a dict.
                        {'SDK_UNKNOWN_MEMBER': {'name': 'somethingNew'}},
                    ]
                ],
            },
            'query-123',
        )

        result = await execute_query(
            'test-cluster',
            'provisioned',
            'dev',
            'SELECT id, name, score, active, deleted, raw FROM users LIMIT 1',
        )

        assert result['columns'] == [
            'id',
            'name',
            'score',
            'active',
            'deleted',
            'raw',
            'from_the_future',
        ]
        # Every cell is a scalar: the blob as the hex Redshift itself prints, and the member
        # nothing here knows as the string the contract promises for everything else.
        assert result['rows'] == [
            [
                1,
                'Test User',
                95.5,
                True,
                None,
                'fffe',
                "{'SDK_UNKNOWN_MEMBER': {'name': 'somethingNew'}}",
            ]
        ]
        assert result['row_count'] == 1
        assert result['query_id'] == 'query-123'

    def test_an_empty_blob_is_an_empty_value(self):
        """Tested for truthiness, an empty blob fell through to the unknown-member string."""
        assert RedshiftDataModel.cell_value({'blobValue': b''}) == ''

    @pytest.mark.asyncio
    async def test_read_only_enforcement_is_passed_through_unchanged(self, mocker):
        """One flag decides the guard and the wrapper, so it must not be re-derived here.

        The mapping from ACCESS_MODE onto this flag happens once, in the tool.
        """
        mock_execute_protected = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.execute_standalone_statement',
            return_value=({'ColumnMetadata': [], 'Records': []}, 'query-123'),
        )

        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'SELECT 1', enforce_read_only=True
        )
        assert mock_execute_protected.call_args[1]['enforce_read_only'] is True

        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'VACUUM t', enforce_read_only=False
        )
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
            'provisioned',
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
            await execute_query('test-cluster', 'provisioned', 'dev', 'SELECT * FROM nonexistent')


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
        """Give each test its own manager, since the real one outlives a single call.

        And keep every call off the Data API unless a test scripts its own client.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            NamedTransactionManager(max_open_per_target=10),
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        # Checked at teardown too: raised inside a failure arm, the AssertionError is wrapped or
        # swallowed, and a test expecting a ToolError would pass.
        tripwire = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            side_effect=AssertionError('reached the Data API'),
        )
        yield
        assert tripwire.call_count == 0

    def _batches(self, mocker, *responses):
        """Script the batches the Data API will answer with, one per submit.

        A batch fills the sinks as `_settle_statement` does, since what a failure reports depends
        on them: `terminal_sink` for any batch, `settled_sink` for a finished one. An exception is
        raised at submit, before either is filled.
        """
        answers = iter(responses)

        async def answer(*args, **kwargs):
            response = next(answers)
            if isinstance(response, BaseException):
                raise response
            if kwargs.get('terminal_sink') is not None:
                kwargs['terminal_sink'].append(response['Id'])
            if kwargs.get('settled_sink') is not None and response['Status'] == 'FINISHED':
                kwargs['settled_sink'].append(response['Id'])
            return response

        return mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch', side_effect=answer
        )

    @pytest.mark.asyncio
    async def test_opening_a_read_only_transaction(self, mocker):
        """A read-only caller gets a read-only transaction, so the engine still refuses writes."""
        batches = self._batches(
            mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1')
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

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
            'test-cluster', 'provisioned', 'dev', begin_transaction='load', enforce_read_only=False
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
            'test-cluster', 'provisioned', 'dev', 'SELECT 1 AS one', begin_transaction='load'
        )

        assert result['rows'] == [[1]]
        assert result['query_id'] == 'batch-id:3'

    @pytest.mark.asyncio
    async def test_opening_without_a_statement_reports_the_batch(self, mocker):
        """There is no statement of the caller's to report, so the batch stands in for it."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        result = await execute_query(
            'test-cluster', 'provisioned', 'dev', begin_transaction='load'
        )

        assert result == {'columns': [], 'rows': [], 'row_count': 0, 'query_id': 'batch-id'}

    @pytest.mark.asyncio
    async def test_a_statement_inside_a_transaction_is_sent_bare_on_its_session(self, mocker):
        """The transaction is already the wrapper, so wrapping again would nest a BEGIN."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
        )

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
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='Statement type not allowed in read-only mode'):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'TRUNCATE t', in_transaction='load'
            )

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
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='single SQL statement is allowed'):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1; SELECT 2', in_transaction='load'
            )

        # Still usable, on the same session.
        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
        )
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

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'provisioned', 'dev', **closing)

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

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
        )

        # Mid-transaction the session is still wanted, so it keeps the configured timeout.
        assert batches.call_args[1]['session_keepalive'] == session_keepalive()

        closing: dict[str, Any] = {parameter: 'load'}
        await execute_query('test-cluster', 'provisioned', 'dev', **closing)

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

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'provisioned', 'dev', 'SELECT 1', **closing)

        assert batches.call_args[1]['sqls'] == ['SELECT 1', closer]

    @pytest.mark.asyncio
    async def test_a_closed_transaction_is_gone(self, mocker):
        """The name must not outlive the transaction, or a later call looks like it worked."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_reopening_the_same_name_is_refused_while_it_is_open(self, mocker):
        """Fail closed: the alternative is silently joining a transaction the caller forgot."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match="Transaction 'load' is already open"):
            await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_a_statement_that_succeeded_restarts_the_idle_clock(self, mocker):
        """The reaper measures idleness from the last touch, so each statement has to move it.

        Left at the open, a transaction in steady use looked abandoned once SESSION_KEEPALIVE had
        passed since it opened, and the next open on the target reaped a live transaction.
        """
        manager = redshift_module.transaction_manager
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        transaction = manager.get(_CLUSTER, 'dev', 'load')
        transaction.touched_at -= session_keepalive() + 1

        await execute_query(
            'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
        )

        manager._reap_expired(transaction.target)
        assert manager.find(_CLUSTER, 'dev', 'load') is transaction

    @pytest.mark.asyncio
    async def test_two_clusters_of_the_same_name_are_two_namespaces(self, mocker):
        """One identifier can name a provisioned cluster and a serverless workgroup at once.

        Keyed on the identifier alone, those two clusters shared one set of names and one cap:
        opening 'load' on each was refused as already open, and a closer sent to one ran on the
        other's session - a COMMIT on the wrong cluster.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[
                _fake_cluster(identifier='shared', type='provisioned'),
                _fake_cluster(identifier='shared', type='serverless'),
            ],
        )
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-provisioned'),
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-serverless'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('shared', 'provisioned', 'dev', begin_transaction='load')
        await execute_query('shared', 'serverless', 'dev', begin_transaction='load')

        await execute_query('shared', 'serverless', 'dev', commit_transaction='load')
        assert batches.call_args[1]['session_id'] == 'session-serverless'

    @pytest.mark.asyncio
    async def test_a_statement_outside_a_transaction_reaches_the_type_it_names(self, mocker):
        """Forwarded as given, the type decides which warehouse of a shared name is reached."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[
                _fake_cluster(identifier='shared', type='provisioned'),
                _fake_cluster(identifier='shared', type='serverless'),
            ],
        )
        batches = self._batches(mocker, _fake_batch(['FINISHED'] * 4))

        await execute_query('shared', 'serverless', 'dev', 'SELECT 1')

        assert batches.call_args[1]['cluster_info'].type == 'serverless'

    @pytest.mark.asyncio
    async def test_a_failed_open_does_not_leave_the_name_claimed(self, mocker):
        """Otherwise a failed open would block the name until the process restarted."""
        self._batches(
            mocker,
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: nope'}, 'FINISHED']),
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-2'),
        )

        with pytest.raises(ToolError, match='ERROR: nope'):
            await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        # The name is free again.
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_an_open_without_a_session_is_refused(self, mocker):
        """Without the session id there is no way to reach the transaction again."""
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED']))

        with pytest.raises(ToolError, match='the Data API returned no session'):
            await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

    @pytest.mark.asyncio
    async def test_a_failed_statement_rolls_the_transaction_back_and_drops_it(self, mocker):
        """An aborted transaction refuses everything later and would commit nothing."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: division by zero'}]),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero'):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1/0', in_transaction='load'
            )

        await asyncio.sleep(0)

        # Rolled back on the way out, on the transaction's own session.
        assert batches.call_args[1]['sqls'] == ['ROLLBACK']
        assert batches.call_args[1]['session_id'] == 'session-1'

        # And the name is gone, so a later commit cannot look successful.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_the_rollback_of_an_aborted_transaction_drains_its_session(self, mocker):
        """The name goes with it, so nothing can reach the session the rollback ran on."""
        batches = self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'status': 'FAILED', 'error': 'ERROR: division by zero'}]),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero') as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1/0', in_transaction='load'
            )

        # Seen to fail, so not said to be running. Said of a finished batch, it told the caller to
        # hold off over a statement that had already ended.
        assert 'may still be running' not in str(raised.value)

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

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError, match='division by zero'):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1/0', in_transaction='load'
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'message',
        # Measured: an expired session answers the first for about half a minute and the second
        # from then on, and a session still running a statement answers the second too. An
        # unknown id gives the third.
        ['Session is expired', 'Session is not available', 'Session with Id: x is invalid'],
    )
    async def test_a_session_reply_releases_the_transaction_and_says_it_may_still_run(
        self, mocker, message
    ):
        """The reply cannot tell a session that is gone from one running this call's statement.

        Read as the session being gone, the call reported no open transaction, every cause it
        listed false, while the statement ran on and held its locks against the caller's retry.
        """
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _client_error('ValidationException', message),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
            )

        assert "Transaction 'load' is released" in str(raised.value)
        assert 'may still be running' in str(raised.value)
        assert message in str(raised.value)

        # Dropped, so the caller is not told to commit something that no longer exists.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_a_closer_met_by_a_session_reply_is_hedged_not_called_never_open(self, mocker):
        """A drained session is the expected aftermath of a COMMIT that ran.

        A closer is sent with `_SESSION_DRAIN`, so the session ends a second after it applies. If
        the response is lost, the retry is answered `Session is not available` - the same reply
        as when the session died before the call, or is still running the closer's first attempt.
        Read as the session being gone, a durable COMMIT was reported as a transaction that was
        never open, whose stated causes are all the caller's own doing, and they redid committed
        work. Hedging costs one look at the data.
        """
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _client_error('ValidationException', 'Session is not available'),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

        assert 'may have applied' in str(raised.value)
        assert 'No open transaction' not in str(raised.value)
        # Over the scripted reply, not a call past the script.
        assert 'Session is not available' in str(raised.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('closing', 'expected'),
        [
            ({'commit_transaction': 'load'}, 'may have applied'),
            # A ROLLBACK ends the same way whatever became of it.
            ({'rollback_transaction': 'load'}, 'discarded either way'),
        ],
        ids=['commit', 'rollback'],
    )
    async def test_a_closer_met_by_a_batch_denial_latches_and_reports_it_unconfirmed(
        self, mocker, closing, expected
    ):
        """The denial is latched, and the closer it may follow is still reported as unconfirmed.

        Read below the closer's report, `_latch_no_batch` never ran: the fallback stayed
        disengaged, the operator never saw the warning naming the grant, and the next standalone
        or opening call paid a denied batch call before latching. Reported as the denial alone, a
        COMMIT an earlier retry attempt carried read as work discarded - and the caller redid
        committed work.
        """
        denial = _batch_denied_error()
        self._batches(
            mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'), denial
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'provisioned', 'dev', **closing)

        assert _no_batch_active(_CLUSTER)
        assert expected in str(raised.value)
        # The denial is still named, carried as the cause.
        assert raised.value.__cause__ is denial
        assert 'redshift-data:BatchExecuteStatement' in str(raised.value)

        # And the name is gone, so the caller cannot close it again and be told that worked.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

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
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def settle_then_fail(*args, **kwargs):
            # Everything in the batch ran, the closer included, and only reading the result of
            # it failed. Both sinks fill, terminal first, as `_settle_statement` fills them.
            kwargs['terminal_sink'].append('batch-id')
            kwargs['settled_sink'].append('batch-id')
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=settle_then_fail,
        )

        closing: dict[str, Any] = {parameter: 'load'}
        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'provisioned', 'dev', 'SELECT 1', **closing)

        # Both facts reach the caller: the closer stands, and what failed afterwards. Reported
        # bare, a committed write would read as a failed one.
        assert 'which stands' in str(raised.value)
        assert expected in str(raised.value)
        assert raised.value.__cause__ is error

        # The name is gone, so the caller cannot be told the closed transaction is still theirs.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

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
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeStatement',
        )

        async def submit_then_fail(*args, **kwargs):
            # The service took the batch, so its COMMIT runs whatever happens to this call.
            # Nothing reached a terminal status, so the settled sink stays empty.
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_fail,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                commit_transaction='load',
            )

        # Neither outcome is claimed, and the caller is told how to settle it: after the COMMIT
        # stops running, since until then it can still apply.
        assert 'may have applied' in str(raised.value)
        assert 'Once SYS_QUERY_HISTORY no longer shows its statements running' in str(raised.value)
        assert 'which stands' not in str(raised.value)
        assert 'Rate exceeded' in str(raised.value)
        assert raised.value.__cause__ is error

        # And the name is gone, so the caller cannot roll it back and be told that worked.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_rollback_never_seen_to_finish_is_reported_as_settled(self, mocker):
        """Every way an unconfirmed ROLLBACK can have gone ends the same, so nothing is in doubt.

        Applied, still queued, or never sent: the name is dropped here, so nothing can commit the
        transaction, and the session's idle timeout ends it. Reported like an unconfirmed COMMIT,
        the caller was sent to inspect data over a state already settled, and could read what they
        found as their writes having persisted.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        error = _client_error('ThrottlingException', 'Rate exceeded', status=429)

        async def submit_then_fail(*args, **kwargs):
            # Accepted, and no status ever seen, so neither sink is filled.
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_fail,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

        assert 'discarded either way' in str(raised.value)
        assert 'may have applied' not in str(raised.value)
        # Its statements may still hold their locks, which decides whether to retry now.
        assert 'may still be running' in str(raised.value)
        assert 'Rate exceeded' in str(raised.value)

        # And the name is gone, as it is for a COMMIT.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

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
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        timed_out = ToolError('Statement timed out after 3600 seconds')

        async def submit_then_time_out(*args, **kwargs):
            # Accepted, and no status ever seen: neither sink is filled.
            raise timed_out

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_time_out,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                commit_transaction='load',
            )

        assert 'may have applied' in str(raised.value)
        assert 'which stands' not in str(raised.value)
        assert 'timed out' in str(raised.value)

        # No ROLLBACK at a session that may be committing.
        rollback.assert_not_called()

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('closing', 'logged'),
        [
            ({'commit_transaction': 'load'}, 'may have applied'),
            # Worded as `_forget_closed_transaction` words the same state: a ROLLBACK ends the
            # same way whatever became of it.
            ({'rollback_transaction': 'load'}, 'discarded either way'),
        ],
        ids=['commit', 'rollback'],
    )
    async def test_a_cancellation_with_the_closer_unwatched_claims_neither_outcome(
        self, mocker, closing, logged
    ):
        """Keyed on `settled` alone, this arm rolled back a COMMIT that may have been applying.

        The arm above calls the same state unknown and fires nothing. The operator's log was the
        only record, and it said the transaction was cancelled.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def accept_then_cancel(*args, **kwargs):
            # Taken by the service, and never watched to a conclusion.
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=accept_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query('test-cluster', 'provisioned', 'dev', **closing)
        await asyncio.sleep(0)

        # No rollback at a session that may be committing.
        rollback.assert_not_called()
        assert any(logged in call[0][0] for call in warning.call_args_list)

        # And the name is gone either way, so nobody rolls back work that landed.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'error',
        [
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'DescribeStatement',
            ),
            ConnectionClosedError(endpoint_url='https://redshift-data'),
        ],
        ids=['client_error', 'transport_failure'],
    )
    async def test_a_failed_commit_releases_the_name_whatever_failed(self, mocker, error):
        """The COMMIT failed; whether the call then met a ClientError or not, the name is released.

        The closer's batch aborted on the cluster, so the transaction is gone there. Reported
        bare, the name outlived it and held a slot against the cap until a later call on it
        failed or the reaper took it.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def conclude_then_fail(*args, **kwargs):
            # Watched to a conclusion, and it was not FINISHED.
            kwargs['terminal_sink'].append('batch-id')
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=conclude_then_fail,
        )

        with pytest.raises(ToolError, match=re.escape(str(error))) as raised:
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                commit_transaction='load',
            )

        # The release is named, not left for the caller to discover on their next call.
        assert 'is released' in str(raised.value)

        # Released, so the caller is not holding a name for a transaction that no longer exists.
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_commit_whose_batch_failed_is_not_called_unknown(self, mocker):
        """A batch that reached FAILED did abort, so its outcome is known and must be said.

        This is why the outcome keys on a terminal status as well as on a finish: both a failure
        and an abandoned poll leave the settled sink empty.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def submit_then_fail_in_the_engine(*args, **kwargs):
            # Watched to a conclusion, and the conclusion was failure.
            kwargs['terminal_sink'].append('batch-id')
            raise ToolError('Statement failed: ERROR: division by zero')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=submit_then_fail_in_the_engine,
        )

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1/0', commit_transaction='load'
            )

        assert 'division by zero' in str(raised.value)
        # Released as a transaction that failed: not hedged, and not reported as committed.
        assert 'is released' in str(raised.value)
        assert 'may have applied' not in str(raised.value)
        assert 'which stands' not in str(raised.value)

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
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load')

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
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load')

        await asyncio.sleep(0)

        assert rollback.call_args[0][2] == 'session-1'
        assert redshift_module.transaction_manager._transactions == {}

    @pytest.mark.asyncio
    async def test_a_statement_that_ran_keeps_its_transaction_when_its_result_cannot_be_read(
        self, mocker
    ):
        """The work is staged in a transaction still open on the cluster; only the read failed.

        The two failure arms disagreed on this. A ClientError left the transaction the caller's,
        while a transport failure on the same read rolled it back and dropped the name,
        discarding work the caller could still have committed.

        The Data API is scripted rather than the batch helper, so the sinks fill exactly where
        they do in production.
        """
        manager = redshift_module.transaction_manager
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = [
            {'Id': 'batch-1', 'Status': 'FINISHED'},
            {'Id': 'batch-2', 'Status': 'FINISHED'},
            AssertionError('submitted more often than scripted'),
        ]
        mock_data_client.describe_statement.side_effect = [
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'has_result_set': True}]),
            AssertionError('described more often than scripted'),
        ]
        read_error = ConnectionClosedError(endpoint_url='https://redshift-data')
        mock_data_client.get_statement_result.side_effect = read_error
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        transaction = manager.get(_CLUSTER, 'dev', 'load')

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
            )

        # Over the scripted read failure, not a call past the script.
        assert raised.value.__cause__ is read_error

        # Named, not raised bare: the transport error alone reads as the statement not having
        # happened, and a caller who ran a write again would stage and commit two copies. Worded
        # for a read too, which staged nothing and can only get its rows by running again.
        assert "transaction 'load' is still open" in str(raised.value)
        assert 'Do not run a write again' in str(raised.value)
        # Not staged, and not undone by a rollback: said so, or a caller rolling back to undo an
        # UNLOAD would believe its files were gone.
        assert 'UNLOAD to S3, is already there' in str(raised.value)
        # Run again, a FETCH returns the rows after the lost ones, as if they were the first.
        assert 'A FETCH has already moved its cursor' in str(raised.value)
        assert 'A read is safe to run again' in str(raised.value)

        # Still theirs to commit, and nothing was discarded on their behalf.
        assert manager.find(_CLUSTER, 'dev', 'load') is transaction
        rollback.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'error',
        [
            ToolError('Statement timed out after 3600 seconds'),
            _client_error('InternalServerException', 'Internal error', status=500),
            # Not ClientErrors, and a failure at the connection or at signing is still only the
            # last attempt's answer.
            EndpointConnectionError(endpoint_url='https://redshift-data'),
            NoCredentialsError(),
        ],
        ids=['timed_out_in_flight', 'submit_unanswered', 'connect_failed', 'unsigned'],
    )
    async def test_a_statement_that_may_have_run_ends_the_transaction(self, mocker, error):
        """Kept open, the caller retried a statement that may already be in it and committed both.

        The two failure arms used to disagree: a ClientError kept the transaction where anything
        else rolled it back. The one arm ends it now, and the caller still gets the error that
        explains why rather than a claim about what was rolled back - the rollback is best effort,
        and a statement still holding the session refuses it.
        """
        manager = redshift_module.transaction_manager
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        async def accept_then_fail(*args, **kwargs):
            if kwargs['sqls'] == [_APP_NAME_SQL, 'BEGIN READ ONLY']:
                return {}, 'batch-1', 'session-1'
            # No sink filled: the batch was never seen to conclude, whichever way it failed.
            raise error

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=accept_then_fail,
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                in_transaction='load',
            )

        # The release is named, and the error that caused it is carried rather than replaced.
        assert 'is released' in str(raised.value)
        assert str(error) in str(raised.value)
        # And that the statement may still hold its locks, which decides whether to reopen now.
        assert 'may still be running' in str(raised.value)
        assert manager.find(_CLUSTER, 'dev', 'load') is None
        assert rollback.call_args[0][2] == 'session-1'

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'read_error',
        [
            ConnectionClosedError(endpoint_url='https://redshift-data'),
            _client_error(
                'ThrottlingException',
                'Rate exceeded',
                status=429,
                operation='GetStatementResult',
            ),
        ],
        ids=['transport_failure', 'client_error'],
    )
    async def test_a_statement_that_finished_restarts_the_idle_clock_it_consumed(
        self, mocker, read_error
    ):
        """A statement that ran longer than the keepalive and then failed is not abandonment.

        The reaper measures idleness from the last touch, and only the success path moved it. So a
        statement that finished after running that long left its transaction looking abandoned the
        moment the lock was released, and the next open on the target reaped one whose session the
        service was still holding - reported to its caller as expired.

        Both kinds of failure, since the same read can fail either way and the arms that handled
        them used to disagree.
        """
        manager = redshift_module.transaction_manager
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = [
            {'Id': 'batch-1', 'Status': 'FINISHED'},
            {'Id': 'batch-2', 'Status': 'FINISHED'},
            AssertionError('submitted more often than scripted'),
        ]
        mock_data_client.describe_statement.side_effect = [
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _fake_batch([{'has_result_set': True}]),
            AssertionError('described more often than scripted'),
        ]
        mock_data_client.get_statement_result.side_effect = read_error
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        transaction = manager.get(_CLUSTER, 'dev', 'load')
        # As though the statement below held the session for longer than one may sit idle. The
        # service restarts its own clock when the batch finishes, so this one may too.
        transaction.touched_at -= session_keepalive() + 1

        with pytest.raises(ToolError, match="transaction 'load' is still open") as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
            )
        # Over the scripted read failure, not a call past the script.
        assert raised.value.__cause__ is read_error

        manager._reap_expired(transaction.target)
        assert manager.find(_CLUSTER, 'dev', 'load') is transaction

    @pytest.mark.asyncio
    async def test_a_cancellation_after_the_closer_ran_still_reports_it_closed(self, mocker):
        """A durable COMMIT is the fact, whatever cut the call short afterwards.

        Reported as a cancellation instead, the one record saying the work persisted would
        never be written, and an operator reading the log after a client timeout would have
        nothing to tell them the commit landed.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def settle_then_cancel(*args, **kwargs):
            # Every sink a finished batch fills, in the order the real path fills them.
            kwargs['terminal_sink'].append('batch-id')
            kwargs['settled_sink'].append('batch-id')
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=settle_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', commit_transaction='load'
            )

        await asyncio.sleep(0)

        # Nothing is rolled back over a commit that already stands.
        rollback.assert_not_called()
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', rollback_transaction='load')

    @pytest.mark.asyncio
    async def test_a_cancelled_statement_drops_the_name_and_drains_its_session(self, mocker):
        """Cancellation is not an Exception, so the arm above it never sees it.

        Seen to conclude, the batch is done with the session, so the transaction is left on one
        nothing will reach again: the name must go, and the session is drained rather than held
        for the whole keepalive.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def conclude_then_cancel(*args, **kwargs):
            kwargs['terminal_sink'].append('batch-id')
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=conclude_then_cancel,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', in_transaction='load'
            )

        await asyncio.sleep(0)

        assert rollback.call_args[0][2] == 'session-1'
        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_a_statement_cancelled_before_it_was_confirmed_is_not_rolled_back(self, mocker):
        """The submit runs on a worker thread that the cancellation does not stop.

        A rollback fired now can land before that submit does, ending the transaction block, and
        the statement then runs on the session in autocommit: outside `BEGIN READ ONLY`, and
        committed. Left alone, it runs inside a transaction nothing will commit.
        """
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))
        rollback = mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        async def cancel_in_flight(*args, **kwargs):
            raise asyncio.CancelledError()

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=cancel_in_flight,
        )

        with pytest.raises(asyncio.CancelledError):
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                in_transaction='load',
            )

        await asyncio.sleep(0)

        rollback.assert_not_called()
        # The name still goes: nothing can reach the transaction again. The cancellation is
        # among the causes named, since the caller may not know its client cancelled.
        with pytest.raises(ToolError, match="No open transaction named 'load'.*a cancelled call"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_a_batch_seen_to_fail_before_its_describe_was_throttled_is_not_called_running(
        self, mocker
    ):
        """The statement settled as FAILED, then the confirming describe was throttled.

        The batch concluded, so nothing is running and a retry waits on nothing.
        """
        mocker.patch('awslabs.redshift_mcp_server.redshift._rollback_lost_transaction')
        data = mocker.Mock()
        # Each list ends in a failure, because running out inside asyncio.to_thread hangs.
        data.batch_execute_statement.side_effect = [
            {'Id': 'batch-1', 'Status': 'FINISHED'},
            {'Id': 'batch-2', 'Status': 'FAILED'},
            AssertionError('submitted more often than scripted'),
        ]
        data.describe_statement.side_effect = [
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
            _client_error(
                'ThrottlingException', 'Rate exceeded', status=400, operation='DescribeStatement'
            ),
            AssertionError('described more often than scripted'),
        ]
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=data,
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')

        with pytest.raises(ToolError) as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1/0', in_transaction='load'
            )

        assert 'is released' in str(raised.value)
        assert 'may still be running' not in str(raised.value)
        # Over the throttled describe, not a call past the script.
        assert 'Rate exceeded' in str(raised.value)

    @pytest.mark.asyncio
    async def test_transactions_on_different_databases_are_independent(self, mocker):
        """The name is scoped to the cluster and database it was opened against."""
        self._batches(
            mocker,
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-dev'),
            _fake_batch(['FINISHED', 'FINISHED'], session_id='session-other'),
            _fake_batch(['FINISHED']),
        )

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await execute_query('test-cluster', 'provisioned', 'other', begin_transaction='load')

        # Closing one leaves the other open.
        await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

        with pytest.raises(ToolError, match="No open transaction named 'load'"):
            await execute_query('test-cluster', 'provisioned', 'dev', commit_transaction='load')

    @pytest.mark.asyncio
    async def test_the_cap_refuses_the_next_transaction(self, mocker):
        """A runaway caller would otherwise hold connections until they timed out."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            NamedTransactionManager(max_open_per_target=1),
        )
        self._batches(mocker, _fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'))

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='one')

        with pytest.raises(ToolError, match='Too many open transactions'):
            await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='two')

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

        await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='load')
        await asyncio.gather(
            *[
                execute_query(
                    'test-cluster', 'provisioned', 'dev', f'SELECT {i}', in_transaction='load'
                )
                for i in range(4)
            ]
        )

        assert not overlapped


class TestTheGuardAppliesToEveryStatementInATransaction:
    """Each entry point runs the guard for its own statement, with its own mode and context."""

    @pytest.fixture(autouse=True)
    def _isolate_transactions(self, mocker):
        """Give each test its own manager, and one cluster to resolve to."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            NamedTransactionManager(max_open_per_target=10),
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'sql',
        [
            "UNLOAD ('SELECT 1') TO 's3://bucket/key' IAM_ROLE 'arn:aws:iam::1:role/r'",
            'SET transaction_read_only TO off',
            'GRANT SELECT ON t TO u',
        ],
        ids=['unload', 'leave_read_only', 'grant'],
    )
    async def test_an_opening_statement_the_read_only_list_denies_is_refused(self, mocker, sql):
        """The write confirmation calls no guard in read-only mode, so this one is the barrier.

        Guarded as read-write, an UNLOAD wrote to S3 from a read-only server, and turning off
        `transaction_read_only` let later statements in the transaction commit writes.
        """
        batches = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='not allowed in read-only mode'):
            await execute_query('test-cluster', 'provisioned', 'dev', sql, begin_transaction='t')

        batches.assert_not_called()

    @pytest.mark.asyncio
    async def test_truncate_is_refused_as_an_opening_statement(self, mocker):
        """It commits the transaction it runs in, which a later rollback then cannot undo."""
        batches = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch')

        with pytest.raises(ToolError, match='can commit the transaction'):
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'TRUNCATE t',
                begin_transaction='t',
                enforce_read_only=False,
            )

        batches.assert_not_called()

    @pytest.mark.asyncio
    async def test_truncate_is_refused_inside_an_open_transaction(self, mocker):
        """Committed out from under the server, later statements autocommit one by one.

        And `rollback_transaction` then reports success having undone nothing.
        """
        batches = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED', 'FINISHED'], session_id='session-1'),
        )
        await execute_query(
            'test-cluster', 'provisioned', 'dev', begin_transaction='t', enforce_read_only=False
        )

        with pytest.raises(ToolError, match='can commit the transaction'):
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'TRUNCATE t',
                in_transaction='t',
                enforce_read_only=False,
            )

        assert batches.call_count == 1


class TestAFailedOpenReportsItsOwnFailure:
    """A failed open says the name was not opened, and whether its statement may still run.

    What it says rests on how far the batch got and on its best-effort cleanup, whose own failure
    never replaces the cause.
    """

    @pytest.fixture(autouse=True)
    def _discover(self, mocker):
        """Every open here resolves the one provisioned cluster, and none reaches the Data API."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.discover_clusters',
            return_value=[_fake_cluster()],
        )
        # Checked at teardown, as in `TestTransactionLifecycle._isolate_transactions`.
        tripwire = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            side_effect=AssertionError('reached the Data API'),
        )
        yield
        assert tripwire.call_count == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'error',
        [
            _client_error('ThrottlingException', 'Rate exceeded'),
            EndpointConnectionError(endpoint_url='https://redshift-data'),
        ],
        ids=['client_error', 'transport'],
    )
    async def test_a_failed_open_says_the_transaction_was_not_opened(self, mocker, error):
        """Raised bare, it read as the first statement's failure, and the name was taken for open."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=error,
        )

        with pytest.raises(ToolError, match="Transaction 'load' was not opened"):
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    @pytest.mark.parametrize('concluded', [True, False], ids=['seen_to_fail', 'timed_out'])
    async def test_a_failed_open_says_whether_its_statement_may_still_run(self, mocker, concluded):
        """A batch never seen to conclude may still hold its locks, so a retry may wait on them.

        Told only that the transaction was not opened, a caller retried at once and waited on the
        first attempt's locks. Said of a batch seen to fail, the warning sends them to wait on
        nothing.
        """

        async def fail(*args, **kwargs):
            if concluded:
                kwargs['terminal_sink'].append('batch-1')
                raise ToolError('Statement failed: ERROR: syntax error')
            raise ToolError('Statement timed out after 900 seconds')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement', side_effect=fail
        )

        with pytest.raises(ToolError, match="Transaction 'load' was not opened") as raised:
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1')

        assert ('may still be running' in str(raised.value)) is not concluded

    @pytest.mark.asyncio
    async def test_a_defect_in_a_failed_open_is_not_reported_as_a_refusal(self, mocker):
        """Wrapped in a ToolError, a bug's text reached the caller as though AWS had said it."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=RuntimeError('a bug'),
        )

        with pytest.raises(RuntimeError, match='a bug'):
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_a_failed_cleanup_rollback_does_not_mask_the_statement_error(self, mocker):
        """Raised from the cleanup, the caller got `Session is not available` for a typo."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.transaction_manager',
            NamedTransactionManager(max_open_per_target=10),
        )

        def minted_then_failed(kwargs):
            kwargs['session_sink'].append('session-1')
            # Seen to fail, as a FAILED batch is.
            kwargs['terminal_sink'].append('batch-1')
            raise ToolError('Statement failed: relation "missing" does not exist')

        answers = iter(
            [minted_then_failed, _client_error('ValidationException', 'Session is not available')]
        )

        async def answer(*args, **kwargs):
            response = next(answers)
            if callable(response):
                return response(kwargs)
            raise response

        mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch', side_effect=answer)

        with pytest.raises(ToolError, match='relation "missing" does not exist'):
            await execute_query(
                'test-cluster',
                'provisioned',
                'dev',
                'SELECT * FROM missing',
                begin_transaction='t',
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('rollback', 'running'),
        [
            (_fake_batch(['FINISHED']), False),
            (_client_error('ValidationException', 'Session is not available'), True),
            # Only a finished ROLLBACK is taken as proof.
            (_fake_batch([{'status': 'FAILED', 'error': 'ERROR: x'}]), True),
        ],
        ids=['rollback_finished', 'rollback_refused', 'rollback_failed'],
    )
    async def test_a_rollback_that_finished_proves_the_statement_ended(
        self, mocker, rollback, running
    ):
        """A busy session refuses a submit, so a finished ROLLBACK proves the statement ended.

        Keyed on the batch being seen to conclude alone, a poll that failed after the submit said
        the statement may still be running though the rollback had just run on its session.
        """

        def accepted_then_poll_failed(kwargs):
            kwargs['session_sink'].append('session-1')
            raise _client_error(
                'ThrottlingException', 'Rate exceeded', operation='DescribeStatement'
            )

        answers = iter([accepted_then_poll_failed, rollback])

        async def answer(*args, **kwargs):
            response = next(answers)
            if callable(response):
                return response(kwargs)
            if isinstance(response, Exception):
                raise response
            return response

        mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch', side_effect=answer)

        with pytest.raises(ToolError, match="Transaction 't' was not opened") as raised:
            await execute_query(
                'test-cluster', 'provisioned', 'dev', 'SELECT 1', begin_transaction='t'
            )

        assert ('may still be running' in str(raised.value)) is running

    @pytest.mark.asyncio
    async def test_an_open_without_a_statement_is_not_said_to_leave_one_running(self, mocker):
        """BEGIN takes no locks, so nothing of the caller's can be holding any."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            side_effect=_client_error('ThrottlingException', 'Rate exceeded'),
        )

        with pytest.raises(ToolError, match="Transaction 't' was not opened") as raised:
            await execute_query('test-cluster', 'provisioned', 'dev', begin_transaction='t')

        assert 'may still be running' not in str(raised.value)


class TestTransactionOutcome:
    """One reading of the two sinks, so the failure arms cannot answer one state differently.

    Each arm used to test the sinks itself, with conditions that drifted apart: one keyed on
    `settled` alone, one required a closer where none was needed. Both defects were invisible
    at the call site and are a table lookup here.
    """

    @pytest.mark.parametrize(
        ('closer', 'settled', 'terminal', 'expected'),
        [
            # A closer watched to a finish stands, whatever failed afterwards.
            ('COMMIT', True, True, redshift_module._CLOSER_RAN),
            ('ROLLBACK', True, True, redshift_module._CLOSER_RAN),
            # Finished, and the call failed after it, so the statement's work is staged in a
            # transaction that is still open.
            (None, True, True, redshift_module._STATEMENT_RAN),
            # Concluded, and not as a finish, so the transaction is gone on the cluster. Not
            # conditioned on a closer: a statement that aborts ends it either way, and a closer
            # that aborts did not apply.
            ('COMMIT', False, True, redshift_module._ABORTED),
            ('ROLLBACK', False, True, redshift_module._ABORTED),
            (None, False, True, redshift_module._ABORTED),
            # No answer at all. A closer may be applying right now, so its outcome is unknown -
            # which is the state, whichever closer it was. What differs is what the caller is told
            # about it, and that belongs to `_forget_closed_transaction`: a ROLLBACK ends the same
            # way whatever became of it, a COMMIT does not.
            ('COMMIT', False, False, redshift_module._CLOSER_UNKNOWN),
            ('ROLLBACK', False, False, redshift_module._CLOSER_UNKNOWN),
            # A statement's would not persist either way, since the transaction is never
            # committed, so the only decision is that the name cannot stay: kept, a retry would
            # be the second copy in one transaction.
            (None, False, False, redshift_module._ABORTED),
        ],
    )
    def test_the_outcome_of_every_reachable_state(self, closer, settled, terminal, expected):
        """`settled` implies `terminal`, so these nine are every reachable combination.

        What the failed call raised is deliberately not an input: the client raises the last
        retry attempt's error, so an attempt that transmitted and lost its response can be
        followed by one that fails at the connection, at signing, or with the service refusing it
        outright. Read as proof that nothing ran, any of those lets a caller retry a write already
        durable, or a statement already in their transaction.
        """
        outcome = redshift_module._transaction_outcome(
            closer,
            ['batch-id'] if settled else [],
            ['batch-id'] if terminal else [],
        )

        assert outcome == expected


class TestBatchDeniedDetection:
    """Only the batch action being denied selects the compatibility path."""

    def test_access_denied_is_the_signal(self):
        """A denied BatchExecuteStatement arrives as AccessDeniedException."""
        assert _is_no_batch(_batch_denied_error()) is True

    def test_a_denial_of_another_call_that_names_no_action_is_not_the_signal(self):
        """Only the operation check keeps this out: with no action named, the pattern cannot."""
        error = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'DescribeStatement',
        )

        assert _is_no_batch(error) is False

    @pytest.mark.asyncio
    async def test_a_write_that_finished_is_not_reported_refused_over_a_describe_denial(
        self, mocker
    ):
        """Read as a batch denial, a durable write was told it was refused, and the cluster latched.

        Latched, every write and transaction on it was then refused for FALLBACK_NO_BATCH_REPROBE.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        data = mocker.Mock()
        data.batch_execute_statement.return_value = {'Id': 'batch-1', 'Status': 'FINISHED'}
        data.describe_statement.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'DescribeStatement',
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=data,
        )

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

        assert 'finished and was applied' in str(raised.value)
        assert 'Writes need' not in str(raised.value)
        assert _no_batch_active(_CLUSTER) is False

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
        GetStatementResult, and one handler covers all three. The compatibility
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
        # Ends in a failure, because running out inside asyncio.to_thread hangs.
        client.describe_statement.side_effect = [
            *describes,
            AssertionError('described more often than scripted'),
        ]
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
    @pytest.mark.parametrize('status', ['FAILED', 'ABORTED'])
    async def test_a_conclusion_is_recorded_whatever_it_was(self, mocker, status):
        """The two sinks answer different questions, and a failure separates them.

        settled_sink says the statement finished; terminal_sink says this call saw it conclude
        at all. Only the second distinguishes a batch that failed from one whose poll was
        abandoned, which is what decides whether a closer's outcome is known. An aborted batch
        concluded as surely as a failed one, and finished no more.
        """
        self._data_client(mocker, [_fake_batch([status], status=status)])
        settled: list[str] = []
        terminal: list[str] = []

        await self._settle(
            {'Id': 'batch-id', 'Status': status},
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
        assert _no_batch_active(_CLUSTER) is False

    def test_a_denial_latches_and_names_the_grant(self, mocker):
        """One warning per latch, carrying the action to grant."""
        warning = mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')

        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        assert _no_batch_active(_CLUSTER) is True
        assert warning.call_count == 1
        assert 'redshift-data:BatchExecuteStatement' in warning.call_args[0][0]

    def test_the_batch_path_is_probed_again_once_the_window_elapses(self, mocker):
        """A granted policy is picked up without restarting the server."""
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        assert _no_batch_active(_CLUSTER) is False
        # Consumed, so a still-denied batch latches again rather than warning per statement.
        assert redshift_module._no_batch_since == {}

    def test_a_denial_on_one_cluster_says_nothing_about_another(self, mocker):
        """The action takes resource-level permissions, so one denial is not a verdict on all.

        Held process-wide, a denial on one cluster refused writes and named transactions on
        every other, and told the caller their credentials lacked an action they held.
        """
        mocker.patch('awslabs.redshift_mcp_server.redshift.logger.warning')
        denied = ClusterKey('denied-cluster', 'provisioned')
        permitted = ClusterKey('permitted-cluster', 'provisioned')

        _latch_no_batch(_batch_denied_error(), denied)

        assert _no_batch_active(denied) is True
        assert _no_batch_active(permitted) is False

        # And the reprobe on one does not consume the other's.
        _latch_no_batch(_batch_denied_error(), permitted)
        mocker.patch('awslabs.redshift_mcp_server.redshift.FALLBACK_NO_BATCH_REPROBE', 0)
        assert _no_batch_active(denied) is False
        assert set(redshift_module._no_batch_since) == {permitted}


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
            _fake_cluster(), 'test-db', 'SELECT 1'
        )

        assert results == records
        assert query_id == 'stmt-id'
        assert client.execute_statement.call_args[1]['Sql'] == 'SELECT 1'

    @pytest.mark.asyncio
    async def test_every_page_of_the_result_is_read(self, mocker):
        """Read once, a result longer than a page came back as though it were the whole answer."""
        client = self._data_client(mocker, records={'Records': [], 'ColumnMetadata': []})
        client.get_statement_result.side_effect = [
            {
                'ColumnMetadata': [{'name': 'n'}],
                'Records': [[{'longValue': 1}]],
                'NextToken': 'p2',
            },
            {'Records': [[{'longValue': 2}]]},
            AssertionError('read past the scripted pages'),
        ]

        results, _ = await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-db', 'SELECT n FROM t'
        )

        assert results['Records'] == [[{'longValue': 1}], [{'longValue': 2}]]

    @pytest.mark.asyncio
    async def test_a_statement_that_aborted_is_a_failure(self, mocker):
        """Checked for failure by name instead, a cancelled statement read as an empty success."""
        self._data_client(
            mocker,
            describe={'Id': 'stmt-id', 'Status': 'ABORTED', 'Error': 'Query was cancelled'},
        )

        with pytest.raises(ToolError, match='Statement failed: Query was cancelled'):
            await _execute_statement_fallback_no_batch(_fake_cluster(), 'test-db', 'SELECT 1')

    @pytest.mark.asyncio
    async def test_no_result_set_is_not_fetched(self, mocker):
        """GetStatementResult answers ResourceNotFoundException for a statement without one."""
        client = self._data_client(mocker)

        results, _ = await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-db', 'SET x TO 1'
        )

        assert results == {'Records': [], 'ColumnMetadata': []}
        client.get_statement_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_provisioned_and_serverless_are_addressed_differently(self, mocker):
        """A workgroup is not a cluster, and the Data API takes them under different names."""
        client = self._data_client(mocker)

        await _execute_statement_fallback_no_batch(_fake_cluster(), 'test-db', 'SELECT 1')
        assert client.execute_statement.call_args[1]['ClusterIdentifier'] == 'test-cluster'

        await _execute_statement_fallback_no_batch(
            _fake_cluster(identifier='test-wg', type='serverless'), 'test-db', 'SELECT 1'
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
                _fake_cluster(), 'test-db', 'SELECT * FROM nope'
            )

    @pytest.mark.asyncio
    async def test_an_unknown_cluster_type_is_our_bug(self, mocker):
        """Discovery only ever sets provisioned or serverless."""
        self._data_client(mocker)

        with pytest.raises(Exception, match='Unknown cluster type'):
            await _execute_statement_fallback_no_batch(
                _fake_cluster(type='mystery'), 'test-db', 'SELECT 1'
            )

    @pytest.mark.asyncio
    async def test_parameters_are_forwarded(self, mocker):
        """A parameterised read still binds its placeholders on the compatibility path."""
        client = self._data_client(mocker)
        parameters = [{'name': 'id', 'value': '1'}]

        await _execute_statement_fallback_no_batch(
            _fake_cluster(), 'test-db', 'SELECT :id', parameters=parameters
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
        """A read runs again whether or not an earlier attempt ran it, rather than failing."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        batch = self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        _, query_id = await execute_standalone_statement(
            'test-cluster', 'provisioned', 'test-db', 'SELECT 1'
        )

        assert batch.call_count == 1
        assert single.call_args[1]['sql'] == 'SELECT 1'
        assert query_id == 'stmt-id'
        assert _no_batch_active(_CLUSTER) is True

    @pytest.mark.asyncio
    async def test_the_wrapper_is_dropped_with_the_batch(self, mocker):
        """One statement per connection leaves nowhere to put BEGIN READ ONLY."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        await execute_standalone_statement('test-cluster', 'provisioned', 'test-db', 'SELECT 1')

        assert single.call_args[1]['sql'] == 'SELECT 1'

    @pytest.mark.asyncio
    async def test_a_latched_server_does_not_attempt_the_batch(self, mocker):
        """The point of the latch is to stop paying a denied call per statement."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        batch = mocker.patch('awslabs.redshift_mcp_server.redshift._execute_batch_for_statement')
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        await execute_standalone_statement('test-cluster', 'provisioned', 'test-db', 'SELECT 1')

        batch.assert_not_called()
        assert single.call_count == 1

    @pytest.mark.asyncio
    async def test_server_authored_discovery_still_works(self, mocker):
        """Every SHOW this server issues classifies as a read, so discovery survives."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        await execute_standalone_statement(
            'test-cluster', 'provisioned', 'test-db', 'SHOW DATABASES;', enforce_read_only=False
        )

        assert single.call_args[1]['sql'] == 'SHOW DATABASES;'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('enforce_read_only', [True, False], ids=['read_only', 'read_write'])
    async def test_a_write_is_refused_and_names_the_grant(self, mocker, enforce_read_only):
        """Without the wrapper a write cannot be contained, so it is refused rather than run.

        In both modes. Read-only mode relies on the wrapper to stop a write the guard lets through,
        so refused only in read-write mode, an INSERT in read-only mode ran unwrapped.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        single = self._capture_single(mocker)
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        with pytest.raises(ToolError, match='redshift-data:BatchExecuteStatement') as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'test-db',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=enforce_read_only,
            )

        single.assert_not_called()
        # Sent from a latch that can be minutes old, so it says when a grant takes effect.
        assert 'restores writes in read-write mode within' in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_write_denied_on_the_call_is_refused_not_hedged(self, mocker):
        """A denial of the batch action is the steady state of a principal never granted it.

        Hedged as a write that never answered is, each such caller was told on every re-probe that
        a write the service had refused may have landed.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        self._deny_the_batch(mocker)
        single = self._capture_single(mocker)

        with pytest.raises(ToolError, match='redshift-data:BatchExecuteStatement') as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'test-db',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=False,
            )

        assert 'may or may not have been applied' not in str(raised.value)
        single.assert_not_called()
        assert _no_batch_active(_CLUSTER) is True

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
            await execute_standalone_statement(
                'test-cluster', 'provisioned', 'test-db', 'SELECT 1'
            )

        single.assert_not_called()
        assert _no_batch_active(_CLUSTER) is False


class TestTransactionsNeedTheBatch:
    """A transaction is several statements on one connection, which the fallback cannot give."""

    @pytest.fixture(autouse=True)
    def _resolve(self, mocker):
        """The latch is keyed on the resolved cluster, so every call here resolves first.

        And none reaches the Data API, where a regression past the latch would send a real batch
        on whatever credentials the environment holds.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )
        # Checked at teardown, as in `TestTransactionLifecycle._isolate_transactions`.
        tripwire = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            side_effect=AssertionError('reached the Data API'),
        )
        yield
        assert tripwire.call_count == 0

    @pytest.mark.asyncio
    async def test_opening_is_refused_while_latched(self):
        """Refused before any name is reserved.

        The latch can be minutes old, so the refusal says when a grant takes effect. Worded as
        current, it told an operator who had just granted the action to grant it.
        """
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        with pytest.raises(ToolError, match='Named transactions need') as raised:
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1')

        assert 'takes effect within' in str(raised.value)
        assert redshift_module.transaction_manager._transactions == {}

    @pytest.mark.asyncio
    async def test_a_statement_on_an_open_one_is_tried_whatever_the_latch_says(self, mocker):
        """The latch can be another call's and stale, with the grant restored since.

        Refused on it, the statement did not run and the transaction stayed open with nothing
        telling the caller so. Sent, it runs, or a denial that is real releases the name and
        says so.
        """
        manager = redshift_module.transaction_manager
        manager.open(_CLUSTER, 'test-db', 'load').attach('session-1')
        batches = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED']),
        )
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        await _execute_statement_in_transaction(
            'test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1'
        )

        assert batches.call_args[1]['sqls'] == ['SELECT 1']
        assert batches.call_args[1]['session_id'] == 'session-1'
        assert manager.find(_CLUSTER, 'test-db', 'load') is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize('closer', ['COMMIT', 'ROLLBACK'])
    async def test_a_closer_is_tried_whatever_the_latch_says(self, mocker, closer):
        """The latch can be another call's and stale, with the grant restored since.

        Refused on it, a COMMIT that would have landed was dropped unsent, and the caller was told
        the action was denied and their work discarded. So it is sent; a denial that is real is
        reported by the batch path instead.
        """
        manager = redshift_module.transaction_manager
        manager.open(_CLUSTER, 'test-db', 'load').attach('session-1')
        batches = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch',
            return_value=_fake_batch(['FINISHED']),
        )
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        await _execute_statement_in_transaction(
            'test-cluster', 'provisioned', 'test-db', 'load', None, closer=closer
        )

        assert batches.call_args[1]['sqls'] == [closer]
        assert batches.call_args[1]['session_id'] == 'session-1'
        assert manager.find(_CLUSTER, 'test-db', 'load') is None

    @pytest.mark.asyncio
    async def test_using_a_name_that_is_not_open_reports_it_missing_while_latched(self):
        """Nothing was released and nothing was staged, so the denial is not what to report.

        Told the action is denied and that uncommitted work was discarded, a caller would go
        looking for a transaction that never existed and for work it never staged.
        """
        _latch_no_batch(_batch_denied_error(), _CLUSTER)

        for sql, closer in (('SELECT 1', None), (None, 'COMMIT'), (None, 'ROLLBACK')):
            with pytest.raises(ToolError, match="No open transaction named 'load'"):
                await _execute_statement_in_transaction(
                    'test-cluster', 'provisioned', 'test-db', 'load', sql, closer=closer
                )

    @pytest.mark.asyncio
    async def test_a_denial_while_opening_drops_the_name(self, mocker):
        """A reserved name must not linger when the batch it needed was refused."""
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )

        with pytest.raises(ToolError, match='Named transactions need'):
            await _begin_transaction('test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1')

        assert _no_batch_active(_CLUSTER) is True
        # The name is free again, so a later call under it reports it as unknown.
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.get(_CLUSTER, 'test-db', 'load')

    @pytest.mark.asyncio
    async def test_a_session_minted_by_a_failed_open_is_rolled_back(self, mocker):
        """A transaction that opened and then failed must not leave its session holding it.

        Dropping the name alone would leave an aborted transaction alive on a session nobody
        can reach, until its keepalive expires, and outside the cap the whole time.
        """
        # Not finished, so only the batch seen to fail says the statement ended.
        rollback = mocker.patch(
            'awslabs.redshift_mcp_server.redshift._rollback_lost_transaction', return_value=False
        )

        async def mint_then_fail(*args, **kwargs):
            kwargs['session_sink'].append('session-1')
            # Seen to fail, as a FAILED batch is.
            kwargs['terminal_sink'].append('batch-1')
            raise ToolError('Statement failed: ERROR: syntax error')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=mint_then_fail,
        )

        # Named, so the caller does not take the name for open.
        with pytest.raises(ToolError, match="Transaction 'load' was not opened. Statement failed"):
            await _begin_transaction(
                'test-cluster', 'provisioned', 'test-db', 'load', 'SELECT bad syntax'
            )

        assert rollback.call_args[0][2] == 'session-1'
        with pytest.raises(ToolError, match='No open transaction'):
            redshift_module.transaction_manager.get(_CLUSTER, 'test-db', 'load')

    @pytest.mark.asyncio
    async def test_a_denial_inside_one_drops_the_name(self, mocker):
        """An open transaction turns unreachable, so its name goes rather than misleading.

        And the refusal says so. Told only that transactions need the action, the caller
        would grant it and go looking for a transaction this call had already given up on.
        """
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=_batch_denied_error(),
        )
        manager = redshift_module.transaction_manager
        manager.open(_CLUSTER, 'test-db', 'load').attach('session-1')

        with pytest.raises(ToolError, match='denied partway through') as raised:
            await _execute_statement_in_transaction(
                'test-cluster', 'provisioned', 'test-db', 'load', 'SELECT 1'
            )
        assert 'had not committed is discarded' in str(raised.value)

        assert _no_batch_active(_CLUSTER) is True
        with pytest.raises(ToolError, match='No open transaction'):
            manager.get(_CLUSTER, 'test-db', 'load')


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
        manager = NamedTransactionManager()

        cluster_a = ClusterKey('cluster-a', 'provisioned')
        cluster_b = ClusterKey('cluster-b', 'provisioned')
        for cluster in (cluster_a, cluster_b):
            manager.open(cluster, 'dev', 'load').attach(f'session-{cluster.identifier}')

        # Opening on A reaps A's expired transaction and must leave B's alone.
        manager.open(cluster_a, 'dev', 'other')

        assert manager.find(cluster_b, 'dev', 'load') is not None

    @pytest.mark.asyncio
    async def test_a_read_only_statement_raises_no_unwatched_write_report(self, mocker):
        """The wrapper discards whatever ran, so there is nothing to warn about."""
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster', return_value=_fake_cluster()
        )

        async def accept_then_time_out(*args, **kwargs):
            raise ToolError('Statement timed out after 3600 seconds')

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift._execute_batch_for_statement',
            side_effect=accept_then_time_out,
        )

        with pytest.raises(ToolError) as raised:
            await execute_standalone_statement(
                'test-cluster',
                'provisioned',
                'dev',
                'INSERT INTO t VALUES (1)',
                enforce_read_only=True,
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
