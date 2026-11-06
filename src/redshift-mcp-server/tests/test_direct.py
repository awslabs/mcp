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

"""Tests for the direct connection client, against a fake of the driver."""

import pytest
import subprocess
import sys
from awslabs.redshift_mcp_server import redshift
from awslabs.redshift_mcp_server.clients import client_manager
from awslabs.redshift_mcp_server.consts import QUERY_TIMEOUT
from awslabs.redshift_mcp_server.direct import DirectConnectionClient, _cell
from awslabs.redshift_mcp_server.settings import max_result_rows
from datetime import date, datetime
from decimal import Decimal
from mcp.server.mcpserver.exceptions import ToolError
from redshift_connector.error import InterfaceError, ProgrammingError
from tests.helpers import _fake_cluster
from typing import Any


CLUSTER: dict[str, Any] = {'ClusterIdentifier': 'my-cluster', 'Database': 'dev'}
APP_NAME = 'SET application_name TO x'
LOST = InterfaceError('connection is closed')


def _engine_error(message):
    """Build what the driver raises for an ErrorResponse: the fields it carried."""
    return ProgrammingError({'S': 'ERROR', 'C': '42P01', 'M': message})


def _once(outcome):
    """An answer given the first time a statement runs, and None after."""
    pending = [outcome]
    return lambda: pending.pop() if pending else None


class FakeCursor:
    """Runs a statement by asking the fake cluster how it answers."""

    def __init__(self, driver):
        """Initialize a cursor on one fake connection."""
        self._driver = driver
        self.description = None
        self.rowcount = -1
        self._rows = []

    def execute(self, sql):
        """Record the statement, then raise, or track the transaction it moves and its rows."""
        self._driver.executed.append(sql)
        outcome = self._driver.cluster.answer(sql, self._driver)
        if isinstance(outcome, BaseException):
            raise outcome
        keyword = sql.split()[0].upper()
        if keyword == 'BEGIN':
            self._driver.in_transaction = True
        if keyword in ('COMMIT', 'ROLLBACK'):
            self._driver.in_transaction = False
        columns, self._rows = outcome or (None, [])
        self.description = columns and [
            (name, 25, None, None, None, None, None) for name in columns
        ]
        self.rowcount = len(self._rows)

    def fetchmany(self, size):
        """Return the first rows."""
        return self._rows[:size]

    def fetchone(self):
        """Return the first row."""
        return self._rows[0]


class FakeDriver:
    """One fake connection, with the pid its backend would have."""

    def __init__(self, cluster, pid):
        """Initialize a connection to the fake cluster."""
        self.cluster = cluster
        self.pid = pid
        self.executed = []
        self.in_transaction = False
        self.autocommit = False
        self.closed = False

    def cursor(self):
        """Open a cursor."""
        return FakeCursor(self)

    def close(self):
        """Close the connection."""
        self.closed = True

    def __enter__(self):
        """Use it as a context manager, as the driver's connection can be."""
        return self

    def __exit__(self, *_):
        """Close it on the way out."""
        self.close()


class FakeCluster:
    """What redshift_connector.connect reaches: an answer per statement, and each connection."""

    def __init__(self):
        """Initialize a cluster that answers every statement with nothing."""
        self.drivers = []
        self.connects = []
        # A statement's answer: None, (columns, rows), an exception, or a callable returning one.
        self.answers = {}
        self.refuse_connects = 0

    def connect(self, **kwargs):
        """Stand in for redshift_connector.connect."""
        self.connects.append(kwargs)
        self.refuse_connects -= 1
        if self.refuse_connects >= 0:
            raise InterfaceError('connection refused')
        self.drivers.append(FakeDriver(self, pid=1000 + len(self.drivers)))
        return self.drivers[-1]

    def answer(self, sql, driver):
        """Answer one statement."""
        if sql == 'SELECT pg_backend_pid()':
            return (['pg_backend_pid'], [(driver.pid,)])
        outcome = self.answers.get(sql)
        return outcome() if callable(outcome) else outcome


class FakeTimer:
    """A threading.Timer that runs only when a test fires it."""

    def __init__(self, armed, interval, function, args):
        """Record the timer instead of starting a thread."""
        self.interval, self.function, self.args = interval, function, args
        self.cancelled = False
        armed.append(self)

    def start(self):
        """Do nothing; the test fires it."""

    def cancel(self):
        """Record the cancel."""
        self.cancelled = True

    def fire(self):
        """Run the function, as the timer thread would once its interval passed."""
        self.function(*self.args)


@pytest.fixture
def cluster(mocker):
    """The fake cluster every connection reaches."""
    fake = FakeCluster()
    mocker.patch('redshift_connector.connect', side_effect=fake.connect)
    return fake


@pytest.fixture
def timers(mocker):
    """Every session timer the client arms, in order."""
    armed = []
    mocker.patch(
        'awslabs.redshift_mcp_server.direct.threading.Timer',
        side_effect=lambda interval, function, args: FakeTimer(armed, interval, function, args),
    )
    return armed


@pytest.fixture
def client(cluster, timers):
    """A direct client over the fake cluster, closed after the test."""
    direct = DirectConnectionClient(region=lambda: 'us-east-1')
    yield direct
    direct.close()


@pytest.fixture
def row_cap(monkeypatch):
    """Set MAX_RESULT_ROWS for one test."""

    def set_cap(value):
        monkeypatch.setenv('MAX_RESULT_ROWS', str(value))
        max_result_rows.cache_clear()

    yield set_cap
    max_result_rows.cache_clear()


def _statuses(client, response):
    """The status of each statement in a batch."""
    return [sub['Status'] for sub in client.describe_statement(Id=response['Id'])['SubStatements']]


def _wrapped(*sqls):
    """A batch as the server sends a read: inside BEGIN READ ONLY ... ROLLBACK."""
    return [APP_NAME, 'BEGIN READ ONLY', *sqls, 'ROLLBACK']


def _open_session(client, keepalive=600):
    """Open a session the way the server opens a transaction, and return its id."""
    return client.batch_execute_statement(
        Sqls=[APP_NAME, 'BEGIN READ ONLY'], SessionKeepAliveSeconds=keepalive, **CLUSTER
    )['SessionId']


class TestResponseShapes:
    """What the server reads from each call, in the shapes the Data API gives it."""

    def test_a_batch_answers_as_the_data_api_does(self, client, cluster):
        """Terminal on submit, then described, then its result set read once."""
        cluster.answers['SELECT 1 AS one'] = (['one'], [(1,)])

        response = client.batch_execute_statement(
            Sqls=[APP_NAME, 'SELECT 1 AS one'],
            ExecutionMode='AUTO_COMMIT',
            ClientToken='token',
            WaitTimeSeconds=30,
            **CLUSTER,
        )

        assert response == {'Id': response['Id'], 'Status': 'FINISHED'}
        described = client.describe_statement(Id=response['Id'], WaitTimeSeconds=30)
        assert [(sub['Id'], sub['HasResultSet']) for sub in described['SubStatements']] == [
            (f'{response["Id"]}:1', False),
            (f'{response["Id"]}:2', True),
        ]
        assert client.get_statement_result(Id=f'{response["Id"]}:2') == {
            'ColumnMetadata': [{'name': 'one'}],
            'Records': [[{'longValue': 1}]],
            'TotalNumRows': 1,
        }
        with pytest.raises(ToolError, match='No result set'):
            client.get_statement_result(Id=f'{response["Id"]}:2')
        with pytest.raises(ToolError, match='No result set'):
            client.get_statement_result(Id=f'{response["Id"]}:1')

    def test_the_connection_authenticates_as_the_iam_identity(self, client, cluster, monkeypatch):
        """GetClusterCredentialsWithIAM, as the Data API uses, over TLS with the named profile."""
        monkeypatch.setenv('AWS_PROFILE', 'my-profile')

        client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)

        assert cluster.connects == [
            {
                'iam': True,
                'group_federation': True,
                'cluster_identifier': 'my-cluster',
                'database': 'dev',
                'region': 'us-east-1',
                'profile': 'my-profile',
                'ssl': True,
                'sslmode': 'verify-full',
                'timeout': QUERY_TIMEOUT + 60,
                'iam_disable_cache': True,
            }
        ]
        assert cluster.drivers[0].autocommit is True
        assert cluster.drivers[0].executed[0] == f'SET statement_timeout TO {QUERY_TIMEOUT * 1000}'

    def test_the_tls_mode_can_be_loosened_only_by_name(self, cluster, timers, monkeypatch):
        """REDSHIFT_DIRECT_SSLMODE=verify-ca drops the hostname check; nothing else is taken."""
        monkeypatch.setenv('REDSHIFT_DIRECT_SSLMODE', ' Verify-CA ')
        client = DirectConnectionClient(region=lambda: 'us-east-1')
        client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)
        client.close()
        assert cluster.connects[-1]['sslmode'] == 'verify-ca'

        monkeypatch.setenv('REDSHIFT_DIRECT_SSLMODE', 'disable')
        with pytest.raises(ToolError, match="REDSHIFT_DIRECT_SSLMODE='disable' is not"):
            DirectConnectionClient(region=lambda: 'us-east-1')
        assert len(cluster.connects) == 1

    @pytest.mark.parametrize(
        ('value', 'cell'),
        [
            (None, {'isNull': True}),
            (True, {'booleanValue': True}),
            (7, {'longValue': 7}),
            (1.5, {'doubleValue': 1.5}),
            (Decimal('1.20'), {'stringValue': '1.20'}),
            (date(2008, 1, 2), {'stringValue': '2008-01-02'}),
            (datetime(2008, 1, 2, 3, 4, 5), {'stringValue': '2008-01-02 03:04:05'}),
            (b'\x01\xff', {'blobValue': b'\x01\xff'}),
            ('text', {'stringValue': 'text'}),
        ],
    )
    def test_each_value_takes_the_member_the_data_api_uses(self, value, cell):
        """A bool is checked before an int, which it is a subclass of."""
        assert _cell(value) == cell

    def test_a_write_outside_a_transaction_leaves_no_state_behind(self, client, cluster):
        """Each unwrapped batch gets a connection of its own, closed after, as the Data API's is.

        Redshift has no DISCARD TEMP, so resetting a shared connection could not drop a
        temporary table; a connection that ends takes its SETs and temporary tables with it.
        """
        client.batch_execute_statement(Sqls=[APP_NAME, 'SET search_path TO x'], **CLUSTER)
        client.batch_execute_statement(Sqls=[APP_NAME, 'CREATE TEMP TABLE t (a INT)'], **CLUSTER)
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)

        setter, creator, reader = cluster.drivers
        assert setter.closed and creator.closed and not reader.closed
        assert setter.executed[-1] == 'SET search_path TO x'
        assert creator.executed[-1] == 'CREATE TEMP TABLE t (a INT)'
        assert 'SET search_path TO x' not in reader.executed
        assert 'CREATE TEMP TABLE t (a INT)' not in reader.executed
        assert client._shared.keys() == {('my-cluster', 'dev')}

    def test_statements_outside_a_transaction_share_one_connection(self, client, cluster):
        """Reads share one connection per cluster and database, however many batches."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)

        assert len(cluster.drivers) == 1

    def test_each_database_gets_its_own_shared_connection(self, client, cluster):
        """A read for one database never runs on the connection another database opened."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        client.batch_execute_statement(
            Sqls=_wrapped('SELECT 2'), ClusterIdentifier='my-cluster', Database='other'
        )
        client.batch_execute_statement(Sqls=_wrapped('SELECT 3'), **CLUSTER)

        assert len(cluster.drivers) == 2
        assert cluster.connects[0]['database'] == 'dev'
        assert cluster.connects[1]['database'] == 'other'
        dev, other = cluster.drivers
        assert 'SELECT 2' in other.executed and 'SELECT 2' not in dev.executed
        assert 'SELECT 3' in dev.executed and 'SELECT 3' not in other.executed

    def test_a_read_only_transaction_left_open_does_not_share(self, client, cluster):
        """Without the closing ROLLBACK the transaction stays open, so the batch is not shared."""
        client.batch_execute_statement(Sqls=[APP_NAME, 'BEGIN READ ONLY', 'SELECT 1'], **CLUSTER)

        assert len(cluster.drivers) == 1 and cluster.drivers[0].closed
        assert client._shared == {}

    def test_an_unwrapped_batch_ending_in_rollback_does_not_share(self, client, cluster):
        """Without BEGIN READ ONLY its statements ran in autocommit, so the batch is not shared."""
        client.batch_execute_statement(
            Sqls=[APP_NAME, 'SET search_path TO x', 'ROLLBACK'], **CLUSTER
        )

        assert len(cluster.drivers) == 1 and cluster.drivers[0].closed
        assert client._shared == {}


class TestAFailedStatement:
    """The engine refusing a statement fails the batch and leaves the connection usable."""

    def test_the_batch_stops_and_its_transaction_is_rolled_back(self, client, cluster):
        """The statements after it do not run, so a failed BEGIN cannot leave one unwrapped."""
        cluster.answers['SELECT nope'] = _engine_error('relation "nope" does not exist')

        response = client.batch_execute_statement(
            Sqls=[APP_NAME, 'BEGIN READ ONLY', 'SELECT nope', 'ROLLBACK'], **CLUSTER
        )

        assert response['Status'] == 'FAILED'
        assert response['Error'] == 'ERROR: relation "nope" does not exist'
        assert _statuses(client, response) == ['FINISHED', 'FINISHED', 'FAILED', 'ABORTED']
        assert cluster.drivers[0].executed[-2:] == ['SELECT nope', 'ROLLBACK']
        assert cluster.drivers[0].in_transaction is False
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        assert len(cluster.drivers) == 1

    def test_a_failure_outside_a_transaction_needs_no_rollback(self, client, cluster):
        """Autocommit left nothing open."""
        cluster.answers['DELETE FROM t'] = _engine_error('permission denied for relation t')

        response = client.batch_execute_statement(Sqls=[APP_NAME, 'DELETE FROM t'], **CLUSTER)

        assert response['Status'] == 'FAILED'
        assert 'ROLLBACK' not in cluster.drivers[0].executed

    def test_a_rollback_that_fails_closes_the_connection(self, client, cluster):
        """The batch still reports its own failure; the next one gets a new connection."""
        cluster.answers['SELECT nope'] = _engine_error('relation "nope" does not exist')
        cluster.answers['ROLLBACK'] = LOST

        response = client.batch_execute_statement(
            Sqls=[APP_NAME, 'BEGIN READ ONLY', 'SELECT nope', 'ROLLBACK'], **CLUSTER
        )

        assert response['Status'] == 'FAILED'
        assert cluster.drivers[0].closed
        client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)
        assert len(cluster.drivers) == 2


class TestSessions:
    """A batch asking for a keepalive gets a connection of its own, which ends when idle."""

    def test_a_session_keeps_its_connection_across_batches(self, client, cluster, timers):
        """Apart from the shared one, with its idle clock restarted after each batch."""
        session_id = _open_session(client)
        client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)
        response = client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)

        assert response['SessionId'] == session_id
        session, shared = cluster.drivers
        assert session.executed[-3:] == [APP_NAME, 'BEGIN READ ONLY', 'SELECT 1']
        assert shared.executed[-1] == APP_NAME
        assert [(timer.interval, timer.cancelled) for timer in timers] == [
            (600, True),
            (600, False),
        ]

    def test_the_drain_keepalive_ends_the_session(self, client, cluster, timers):
        """The closer's keepalive of one second, once idle, closes the connection."""
        session_id = _open_session(client)
        client.batch_execute_statement(
            Sqls=['ROLLBACK'], SessionId=session_id, SessionKeepAliveSeconds=1
        )

        assert timers[-1].interval == 1
        timers[-1].fire()

        assert cluster.drivers[0].closed
        assert client._sessions == {}
        with pytest.raises(ToolError, match='not available'):
            client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)

    def test_a_superseded_or_busy_timer_does_nothing(self, client, cluster, timers):
        """One a later batch replaced, or one firing while a batch runs, which arms its own."""
        session_id = _open_session(client)
        client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)
        timers[0].fire()
        with client._sessions[session_id].lock:
            timers[1].fire()

        assert not cluster.drivers[0].closed

    def test_a_busy_ended_or_unknown_session_is_refused(self, client):
        """Refused rather than waited on, as the Data API refuses a session in use."""
        session_id = _open_session(client)
        with client._sessions[session_id].lock:
            with pytest.raises(ToolError, match='not available'):
                client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)
        # Closed by its timer between the lookup and taking its lock.
        client._close(client._sessions[session_id])
        with pytest.raises(ToolError, match='not available'):
            client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)
        with pytest.raises(ToolError, match='not available'):
            client.batch_execute_statement(Sqls=['SELECT 1'], SessionId='no-such-session')

    def test_a_session_that_could_not_connect_is_not_kept(self, client, cluster):
        """Nothing stays registered under an id the caller never received."""
        cluster.refuse_connects = 1

        with pytest.raises(ToolError, match='Could not connect to my-cluster, database dev'):
            _open_session(client)

        assert client._sessions == {}

    def test_close_ends_every_connection(self, client, cluster, mocker):
        """At exit, open transactions end without committing, past a close that fails."""
        _open_session(client)
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        mocker.patch.object(cluster.drivers[0], 'close', side_effect=LOST)

        client.close()

        assert cluster.drivers[1].closed
        assert client._sessions == {} and client._shared == {}


class TestTimeouts:
    """A connection that stops answering is given up on, and its own statement cancelled."""

    def test_only_its_own_backend_is_cancelled(self, client, cluster):
        """From a second connection that runs nothing else, and the statement is not resent."""
        cluster.answers['SELECT slow'] = TimeoutError('timed out')
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)

        with pytest.raises(ToolError, match='timed out and was cancelled, so whether it ran'):
            client.batch_execute_statement(Sqls=_wrapped('SELECT slow'), **CLUSTER)

        timed_out, canceller = cluster.drivers
        assert canceller.executed == [f'SELECT pg_cancel_backend({timed_out.pid})']
        assert canceller.closed and timed_out.closed
        assert timed_out.executed.count('SELECT slow') == 1

    def test_a_timeout_on_the_first_statement_is_not_resent(self, client, cluster):
        """However stale the connection, a statement that may still be running is not resent."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        cluster.answers[APP_NAME] = TimeoutError('timed out')

        with pytest.raises(ToolError, match='timed out'):
            client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)

        assert len(cluster.drivers) == 2

    def test_a_cancel_that_fails_is_logged_not_raised(self, client, cluster):
        """The timeout is still what the caller is told."""
        cluster.answers['SELECT slow'] = TimeoutError('timed out')
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        cluster.refuse_connects = 1

        with pytest.raises(ToolError, match='timed out'):
            client.batch_execute_statement(Sqls=_wrapped('SELECT slow'), **CLUSTER)

        assert cluster.drivers[0].closed


class TestRowCap:
    """At most MAX_RESULT_ROWS plus one row is kept, so a larger result is refused upstream."""

    @pytest.mark.parametrize(('rows', 'kept'), [(2, 2), (5, 3)])
    def test_rows_beyond_the_cap_are_not_kept(self, client, cluster, row_cap, rows, kept):
        """The size is still reported, from the driver's row count."""
        row_cap(2)
        cluster.answers['SELECT n'] = (['n'], [(n,) for n in range(rows)])

        response = client.batch_execute_statement(Sqls=['SELECT n'], **CLUSTER)
        result = client.get_statement_result(Id=f'{response["Id"]}:1')

        assert (len(result['Records']), result['TotalNumRows']) == (kept, rows)

    def test_an_unknown_size_over_the_cap_is_left_out(self, client, cluster, row_cap, mocker):
        """Without a row count, the refusal says more than the cap rather than a wrong size."""
        row_cap(1)
        cluster.answers['SHOW x'] = (['x'], [(1,), (2,)])
        original = FakeCursor.execute

        def no_rowcount(cursor, sql):
            original(cursor, sql)
            cursor.rowcount = -1

        mocker.patch.object(FakeCursor, 'execute', no_rowcount)

        response = client.batch_execute_statement(Sqls=['SHOW x'], **CLUSTER)

        assert 'TotalNumRows' not in client.get_statement_result(Id=f'{response["Id"]}:1')


class TestReconnect:
    """A connection gone stale while idle is replaced once, when nothing can run twice."""

    def test_a_stale_connection_is_replaced_and_the_batch_sent_again(self, client, cluster):
        """The first statement, the server's own SET, is all that can have been lost."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        cluster.answers[APP_NAME] = _once(LOST)

        response = client.batch_execute_statement(Sqls=_wrapped('SELECT 2'), **CLUSTER)

        assert response['Status'] == 'FINISHED'
        stale, fresh = cluster.drivers
        assert stale.closed and 'SELECT 2' not in stale.executed
        assert fresh.executed[-4:] == _wrapped('SELECT 2')

    def test_a_loss_after_the_first_statement_is_not_resent(self, client, cluster):
        """The caller's statement may have run, so it is reported, not run again."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        cluster.answers['SELECT 2'] = LOST

        with pytest.raises(ToolError, match='Statement 3 of 4 on my-cluster lost its connection'):
            client.batch_execute_statement(Sqls=_wrapped('SELECT 2'), **CLUSTER)

        assert len(cluster.drivers) == 1
        assert cluster.drivers[0].executed.count('SELECT 2') == 1

    def test_a_write_on_its_own_connection_is_never_resent(self, client, cluster):
        """Its connection is new, so it cannot have gone stale, and the write may have run."""
        client.batch_execute_statement(Sqls=_wrapped('SELECT 1'), **CLUSTER)
        cluster.answers['DELETE FROM t'] = LOST

        with pytest.raises(ToolError, match='Statement 2 of 2 on my-cluster lost its connection'):
            client.batch_execute_statement(Sqls=[APP_NAME, 'DELETE FROM t'], **CLUSTER)

        shared, writer = cluster.drivers
        assert writer.closed and not shared.closed
        assert writer.executed.count('DELETE FROM t') == 1

    def test_a_new_connection_is_not_retried(self, client, cluster):
        """A connection that fails on its first batch did not go stale."""
        cluster.answers[APP_NAME] = LOST

        with pytest.raises(ToolError, match='lost its connection'):
            client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)

        assert len(cluster.drivers) == 1

    def test_a_session_is_never_retried(self, client, cluster):
        """Its statements belong to its transaction, which a new connection would not have."""
        session_id = _open_session(client)
        cluster.answers['SELECT 1'] = LOST

        with pytest.raises(ToolError, match='lost its connection'):
            client.batch_execute_statement(Sqls=['SELECT 1'], SessionId=session_id)

        assert len(cluster.drivers) == 1
        assert client._sessions == {}


class TestRefusals:
    """What this client does not do is refused with a reason, never half done."""

    def test_a_missing_driver_names_the_extra_to_install(self, monkeypatch):
        """The driver is an optional extra, so its absence says how to add it."""
        # None in sys.modules makes `import redshift_connector` raise ImportError.
        monkeypatch.setitem(sys.modules, 'redshift_connector', None)

        with pytest.raises(
            ToolError, match=r"pip install 'awslabs-redshift-mcp-server\[direct\]'"
        ):
            DirectConnectionClient(region=lambda: 'us-east-1')

    def test_the_server_starts_without_the_driver_and_never_loads_it(self):
        """Run in a fresh interpreter, since this one has already imported the driver.

        Without the extra the Data API mode must still start, and with it the driver must stay
        unloaded until direct mode builds its client.
        """
        script = (
            'import sys\n'
            'blocked = "--blocked" in sys.argv\n'
            'if blocked:\n'
            '    sys.modules["redshift_connector"] = None\n'
            'import awslabs.redshift_mcp_server.server\n'
            'if not blocked and "redshift_connector" in sys.modules:\n'
            '    sys.exit("redshift_connector was imported")\n'
        )
        for args in (['--blocked'], []):
            run = subprocess.run(
                [sys.executable, '-c', script, *args],
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert run.returncode == 0, (args, run.stderr[-2000:])

    def test_the_single_statement_fallback_is_refused(self, client, cluster):
        """It is unreachable here, so reaching it fails loud rather than with AttributeError."""
        with pytest.raises(ToolError, match='direct mode has no Data API fallback'):
            client.execute_statement(Sql='SELECT 1', **CLUSTER)
        assert cluster.connects == []

    def test_serverless_and_parameters_are_refused(self, client, cluster):
        """Before any connection is made."""
        with pytest.raises(ToolError, match='provisioned clusters only'):
            client.batch_execute_statement(Sqls=['SELECT 1'], WorkgroupName='wg', Database='dev')
        with pytest.raises(ToolError, match='parameters are not supported'):
            client.batch_execute_statement(
                Sqls=['SELECT :a'], Parameters=[{'name': 'a', 'value': '1'}], **CLUSTER
            )
        assert cluster.connects == []

    def test_a_connection_that_fails_to_set_up_is_closed(self, client, cluster):
        """Opened, but refused its statement_timeout, it is not left open."""
        cluster.answers[f'SET statement_timeout TO {QUERY_TIMEOUT * 1000}'] = LOST

        with pytest.raises(ToolError, match='Could not connect'):
            client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)

        assert cluster.drivers[0].closed

    def test_only_the_latest_batches_are_kept(self, client, mocker):
        """A batch whose result is never read cannot hold memory for long."""
        mocker.patch('awslabs.redshift_mcp_server.direct._BATCHES_KEPT', 2)
        ids = [client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)['Id'] for _ in range(3)]

        with pytest.raises(ToolError, match='not known'):
            client.describe_statement(Id=ids[0])
        assert list(client._batches) == ids[1:]


class TestThroughTheServer:
    """The server's own execution code, unchanged, running on the direct client."""

    @pytest.fixture(autouse=True)
    def _direct(self, client, monkeypatch, mocker):
        """Route the server's statements through the direct client."""
        monkeypatch.setattr(client_manager, '_redshift_data_client', client)
        mocker.patch(
            'awslabs.redshift_mcp_server.clusters.resolve_cluster',
            return_value=_fake_cluster('my-cluster'),
        )

    async def _query(self, **kwargs):
        return await redshift.execute_query(
            cluster_identifier='my-cluster',
            cluster_type='provisioned',
            database_name='dev',
            **kwargs,
        )

    async def test_a_read_runs_inside_the_read_only_wrapper(self, cluster):
        """SET, BEGIN READ ONLY, the statement and ROLLBACK, on the shared connection."""
        cluster.answers['SELECT 1 AS one'] = (['one'], [(1,)])

        result = await self._query(sql='SELECT 1 AS one')

        assert (result['columns'], result['rows'], result['row_count']) == (['one'], [[1]], 1)
        assert cluster.drivers[0].executed[-3:] == [
            'BEGIN READ ONLY',
            'SELECT 1 AS one',
            'ROLLBACK',
        ]

    async def test_an_engine_error_reaches_the_caller(self, cluster):
        """In the engine's own words."""
        cluster.answers['SELECT * FROM nope'] = _engine_error('relation "nope" does not exist')

        with pytest.raises(ToolError, match='Statement failed: ERROR: relation "nope"'):
            await self._query(sql='SELECT * FROM nope')

    async def test_a_result_over_the_cap_is_refused_with_its_size(self, cluster, row_cap):
        """As a Data API result over the cap is."""
        row_cap(2)
        cluster.answers['SELECT n FROM t'] = (['n'], [(n,) for n in range(5)])

        with pytest.raises(ToolError, match='The result has 5 rows, over the MAX_RESULT_ROWS'):
            await self._query(sql='SELECT n FROM t')

    async def test_a_named_transaction_keeps_its_connection(self, cluster, timers):
        """Every statement on one session, which the closer's drain then ends."""
        cluster.answers['SELECT 1 AS one'] = (['one'], [(1,)])
        cluster.answers['SELECT 2 AS two'] = (['two'], [(2,)])

        await self._query(sql='SELECT 1 AS one', begin_transaction='t')
        second = await self._query(sql='SELECT 2 AS two', in_transaction='t')
        await self._query(rollback_transaction='t')
        timers[-1].fire()

        assert second['rows'] == [[2]]
        assert cluster.drivers[0].executed[-4:] == [
            'BEGIN READ ONLY',
            'SELECT 1 AS one',
            'SELECT 2 AS two',
            'ROLLBACK',
        ]
        assert cluster.drivers[0].closed

    async def test_a_write_does_not_reach_the_next_call(self, cluster):
        """A temporary table one read-write call creates is not there for the next call."""
        cluster.answers['SELECT 1 AS one'] = (['one'], [(1,)])

        await self._query(sql='CREATE TEMP TABLE t (a INT)', enforce_read_only=False)
        await self._query(sql='SELECT 1 AS one')

        writer, reader = cluster.drivers
        assert writer.closed and 'CREATE TEMP TABLE t (a INT)' in writer.executed
        assert 'CREATE TEMP TABLE t (a INT)' not in reader.executed

    async def test_a_lost_connection_reports_a_write_as_unknown(self, client, cluster):
        """The server's own reporting applies: a write that may have landed is not retried."""
        client.batch_execute_statement(Sqls=[APP_NAME], **CLUSTER)
        cluster.answers['DELETE FROM t'] = LOST

        with pytest.raises(ToolError, match='cannot tell whether it ran'):
            await self._query(sql='DELETE FROM t', enforce_read_only=False)
