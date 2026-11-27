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

"""Direct connections, standing in for the Data API where the credentials may not call it.

For credentials that may fetch cluster credentials (redshift:GetClusterCredentialsWithIAM) but
not call the Data API. `DirectConnectionClient` answers the three Data API calls the server
makes, in the shapes it reads, so nothing that runs statements changes.
"""

import contextlib
import os
import threading
import time
import uuid
from awslabs.redshift_mcp_server.consts import CONNECTION_MODE_DIRECT, QUERY_TIMEOUT
from awslabs.redshift_mcp_server.settings import max_result_rows, resolve_direct_sslmode
from collections import OrderedDict
from dataclasses import dataclass, field
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from typing import Any, Callable


# How much longer than QUERY_TIMEOUT a direct connection waits on the cluster before giving up on
# it. The engine's statement_timeout, set to QUERY_TIMEOUT, ends a slow statement first and leaves
# the connection usable; this bounds a connection that stops answering.
_SOCKET_GRACE = 60

# How many batches a direct client keeps for describe_statement and get_statement_result. The
# server reads each back as soon as it is submitted, so this bounds only what is never read.
_BATCHES_KEPT = 64


@dataclass(eq=False)
class _Connection:
    """One connection to a cluster and database, used by one batch at a time."""

    cluster: str
    database: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    # The driver's connection while open, and its backend pid: the only one this server cancels.
    driver: Any = None
    pid: int | None = None
    # Whether it has run a batch since it opened, so a failure can be one that went stale idle.
    used: bool = False
    # Sessions only: the idle timeout, when it runs out, and the timer that then ends it.
    keepalive: float = 0
    expires_at: float = 0
    timer: threading.Timer | None = None


class _ConnectionLost(Exception):
    """The connection, not the engine, failed while statement `args[0]` of a batch ran."""


def _close_quietly(driver: Any) -> None:
    """Close a driver connection, if there is one, ignoring a failure: nothing is left to do."""
    if driver is None:
        return
    with contextlib.suppress(Exception):
        driver.close()


def _cell(value: Any) -> dict:
    """Shape one value the driver read as a Data API result cell."""
    if value is None:
        return {'isNull': True}
    # Before int, which bool is a subclass of.
    if isinstance(value, bool):
        return {'booleanValue': value}
    if isinstance(value, int):
        return {'longValue': value}
    if isinstance(value, float):
        return {'doubleValue': value}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'blobValue': bytes(value)}
    # DECIMAL, dates, times and the rest, as text, which is how the Data API sends them.
    return {'stringValue': str(value)}


def _leaves_no_state(sqls: list[str]) -> bool:
    """Whether a batch is the server's read, which may share a connection with later batches.

    That is `SET application_name; BEGIN READ ONLY; <sql>; ROLLBACK`. The engine refuses any
    write inside the transaction and the ROLLBACK discards the rest, so the only state left is
    the application name, which every batch sets again.
    """
    return len(sqls) >= 3 and sqls[1] == 'BEGIN READ ONLY' and sqls[-1] == 'ROLLBACK'


def _result_set(cursor: Any, cap: int) -> dict | None:
    """Read a statement's result set as GetStatementResult answers it, or None when it has none.

    The driver has read the whole result before the statement returns, so the cap bounds only
    what is kept: one row past MAX_RESULT_ROWS, which is enough for the server to refuse it. The
    size is reported when known, so the refusal can state it.
    """
    if not cursor.description:
        return None
    rows = cursor.fetchmany(cap + 1)
    result = {
        'ColumnMetadata': [{'name': column[0]} for column in cursor.description],
        'Records': [[_cell(value) for value in row] for row in rows],
    }
    total = len(rows) if len(rows) <= cap else cursor.rowcount
    if total >= len(rows):
        result['TotalNumRows'] = total
    return result


class DirectConnectionClient:
    """Runs the server's statements over direct connections, answering as the Data API does.

    It implements `batch_execute_statement`, `describe_statement` and `get_statement_result`.
    A batch has ended by the time its submit returns, so the server's poll ends at its first
    describe. It raises no `ClientError`, so the fallback for a denied batch action, the only
    caller of `execute_statement`, never engages; `execute_statement` itself refuses. Provisioned
    clusters only.

    Reads outside a transaction, which run inside `BEGIN READ ONLY ... ROLLBACK`, share one
    connection per cluster and database. Any other batch outside a transaction runs on a
    connection of its own, closed when it ends, so no state it leaves reaches a later call. A
    batch that asks for a session keepalive gets a connection of its own, which is the session: it
    closes once idle for its keepalive - about a second after the server's closer, which sends a
    keepalive of 1 - and when the process exits.
    """

    def __init__(self, region: Callable[[], str]):
        """Initialize the client.

        Args:
            region: Returns the AWS region to fetch cluster credentials in.
        """
        # Imported here, so the Data API mode never loads the driver, which is an optional extra.
        try:
            import redshift_connector
            from redshift_connector.error import Error
        except ImportError as e:
            raise ToolError(
                f'REDSHIFT_CONNECTION_MODE={CONNECTION_MODE_DIRECT} needs the Amazon Redshift '
                f"Python driver: pip install 'awslabs-redshift-mcp-server[direct]'"
            ) from e

        self._driver = redshift_connector
        self._driver_error = Error
        self._sslmode = resolve_direct_sslmode()
        self._region = region
        # Guards the maps below. Never held across a call to the cluster.
        self._lock = threading.Lock()
        self._shared: dict[tuple[str, str], _Connection] = {}
        self._sessions: dict[str, _Connection] = {}
        self._batches: OrderedDict[str, tuple[dict, dict]] = OrderedDict()

    def batch_execute_statement(
        self,
        Sqls: list[str],
        Database: str = '',
        ClusterIdentifier: str = '',
        WorkgroupName: str | None = None,
        SessionId: str | None = None,
        SessionKeepAliveSeconds: int | None = None,
        Parameters: list[dict] | None = None,
        **_ignored: Any,
    ) -> dict:
        """Run statements in order on one connection, stopping at the first that fails.

        Every connection runs with autocommit, nothing that may have run is sent twice, and the
        batch ends before this returns, so ExecutionMode, ClientToken and WaitTimeSeconds are
        accepted and ignored.

        Args:
            Sqls: The statements.
            Database: The database, outside a session.
            ClusterIdentifier: The provisioned cluster, outside a session.
            WorkgroupName: A serverless workgroup, which is refused.
            SessionId: Run on this session.
            SessionKeepAliveSeconds: Without SessionId, open a session with this idle timeout;
                with it, set the session's idle timeout.
            Parameters: Statement parameters, which are refused.
            **_ignored: The other Data API parameters.

        Returns:
            The batch's Id, its terminal Status, Error when it failed, and SessionId on a session.

        Raises:
            ToolError: If the request is one this client refuses, the session is not available,
                or the connection cannot be opened or fails while a statement runs.
        """
        if WorkgroupName is not None:
            raise ToolError(
                f'REDSHIFT_CONNECTION_MODE={CONNECTION_MODE_DIRECT} supports provisioned clusters '
                f'only; a serverless workgroup needs the Data API.'
            )
        if Parameters:
            raise ToolError(
                f'Statement parameters are not supported with '
                f'REDSHIFT_CONNECTION_MODE={CONNECTION_MODE_DIRECT}.'
            )

        session_id = SessionId
        if SessionId is not None:
            connection = self._session(SessionId)
        elif SessionKeepAliveSeconds is not None:
            session_id = str(uuid.uuid4())
            connection = _Connection(ClusterIdentifier, Database)
            connection.lock.acquire()
            with self._lock:
                self._sessions[session_id] = connection
        elif _leaves_no_state(Sqls):
            with self._lock:
                connection = self._shared.setdefault(
                    (ClusterIdentifier, Database), _Connection(ClusterIdentifier, Database)
                )
            connection.lock.acquire()
        else:
            # Anything else may leave a SET or a temporary table behind, which a shared
            # connection would hand to the next, unrelated call. Redshift has no DISCARD TEMP to
            # clear it, so the batch gets a connection of its own and ends it, as the Data API
            # isolates every call.
            connection = _Connection(ClusterIdentifier, Database)
            connection.lock.acquire()

        batch_id = str(uuid.uuid4())
        try:
            # A session's statements are never sent twice: they belong to its transaction.
            sub_statements, results = self._run_batch(
                connection, batch_id, Sqls, may_retry=session_id is None
            )
        finally:
            if session_id is None and not _leaves_no_state(Sqls):
                self._close(connection)
            self._release(connection, session_id, SessionKeepAliveSeconds)

        response: dict[str, Any] = {'Id': batch_id, 'Status': 'FINISHED'}
        failed = next((sub for sub in sub_statements if sub['Status'] == 'FAILED'), None)
        if failed is not None:
            response.update(Status='FAILED', Error=failed['Error'])
        if session_id is not None:
            response['SessionId'] = session_id

        with self._lock:
            self._batches[batch_id] = ({**response, 'SubStatements': sub_statements}, results)
            while len(self._batches) > _BATCHES_KEPT:
                self._batches.popitem(last=False)
        return response

    def describe_statement(self, Id: str, **_ignored: Any) -> dict:
        """Describe a batch this client ran, which has always ended.

        Args:
            Id: The batch id.
            **_ignored: The other Data API parameters, WaitTimeSeconds among them.

        Returns:
            What the submit returned, with SubStatements.

        Raises:
            ToolError: If the batch is not one this client still holds.
        """
        with self._lock:
            batch = self._batches.get(Id)
        if batch is None:
            raise ToolError(f'Statement {Id} is not known to this server.')
        return batch[0]

    def get_statement_result(self, Id: str, **_ignored: Any) -> dict:
        """Hand over a sub-statement's result set, once, as a single page.

        Args:
            Id: The sub-statement id, `<batch id>:<position>`.
            **_ignored: The other Data API parameters, NextToken among them.

        Returns:
            ColumnMetadata, Records, and TotalNumRows when the size is known.

        Raises:
            ToolError: If there is no unread result set under that id.
        """
        with self._lock:
            _, results = self._batches.get(Id.rpartition(':')[0], (None, {}))
            result = results.pop(Id, None)
        if result is None:
            raise ToolError(f'No result set for statement {Id}.')
        return result

    def execute_statement(self, **_: Any) -> dict:
        """Refuse the single-statement fallback, which only a denied batch action engages.

        This client never raises the ClientError that engages it, so a call here means that
        invariant broke; it is refused clearly rather than failing with AttributeError.

        Raises:
            ToolError: Always.
        """
        raise ToolError(
            f'REDSHIFT_CONNECTION_MODE={CONNECTION_MODE_DIRECT}: direct mode has no Data API '
            f'fallback, so execute_statement is not supported.'
        )

    def close(self) -> None:
        """Close every connection, which ends their open transactions without committing."""
        with self._lock:
            connections = [*self._shared.values(), *self._sessions.values()]
            self._shared.clear()
            self._sessions.clear()
        for connection in connections:
            self._close(connection)

    def _session(self, session_id: str) -> _Connection:
        """Take a session's connection, refusing rather than waiting, as the Data API does."""
        with self._lock:
            connection = self._sessions.get(session_id)
        if connection is None or not connection.lock.acquire(blocking=False):
            raise ToolError(f'Session {session_id} is not available.')
        if connection.driver is None:
            # Its idle timer closed it while this call was finding it.
            connection.lock.release()
            raise ToolError(f'Session {session_id} is not available.')
        return connection

    def _release(
        self, connection: _Connection, session_id: str | None, keepalive: int | None
    ) -> None:
        """Let the next batch have a connection, restarting a session's idle clock."""
        try:
            if session_id is not None and connection.driver is None:
                self._forget(session_id, connection)
            if session_id is not None and connection.driver is not None:
                self._arm_expiry(session_id, connection, keepalive)
        finally:
            connection.lock.release()

    def _run_batch(
        self, connection: _Connection, batch_id: str, sqls: list[str], may_retry: bool
    ) -> tuple[list[dict], dict]:
        """Run a batch on a held connection, opening it first when it is closed.

        A connection that fails while a statement runs is closed, after cancelling the statement
        when it timed out, since it may still be running. The batch is sent again once, on a new
        connection, only when nothing of the caller's can have run: the connection sat idle since
        its last batch, and the first statement failed, which outside a session is always the
        server's own `SET application_name`.
        """
        while True:
            if connection.driver is None:
                self._open(connection)
            stale = connection.used
            try:
                outcome = self._run(connection, batch_id, sqls)
            except _ConnectionLost as lost:
                index, cause = lost.args[0], lost.__cause__
                timed_out = isinstance(cause, TimeoutError)
                if timed_out:
                    self._cancel(connection)
                self._close(connection)
                if may_retry and stale and index == 0 and not timed_out:
                    logger.info(f'Reconnecting to {connection.cluster}: {cause!r}')
                    may_retry = False
                    continue
                what = 'timed out and was cancelled' if timed_out else 'lost its connection'
                raise ToolError(
                    f'Statement {index + 1} of {len(sqls)} on {connection.cluster} {what}, so '
                    f'whether it ran is unknown: {cause!r}'
                ) from cause
            connection.used = True
            return outcome

    def _run(
        self, connection: _Connection, batch_id: str, sqls: list[str]
    ) -> tuple[list[dict], dict]:
        """Run each statement in turn, stopping at the first the engine refuses.

        The statements after it are reported ABORTED and not run, so a failed `BEGIN READ ONLY`
        cannot leave the next one running unwrapped. A transaction the failure aborted is rolled
        back, since it would refuse everything after it.

        Raises:
            _ConnectionLost: If the connection, rather than the engine, failed.
        """
        cap = max_result_rows()
        cursor = connection.driver.cursor()
        sub_statements: list[dict] = []
        results: dict[str, dict | None] = {}
        error = None

        for index, sql in enumerate(sqls):
            sub = {'Id': f'{batch_id}:{index + 1}', 'Status': 'ABORTED', 'HasResultSet': False}
            sub_statements.append(sub)
            if error is not None:
                continue
            try:
                cursor.execute(sql)
            except Exception as e:
                error = self._engine_error(e)
                if error is None:
                    raise _ConnectionLost(index) from e
                sub.update(Status='FAILED', Error=error)
                continue
            results[sub['Id']] = _result_set(cursor, cap)
            sub.update(Status='FINISHED', HasResultSet=results[sub['Id']] is not None)

        if error is None or not connection.driver.in_transaction:
            return sub_statements, results
        try:
            cursor.execute('ROLLBACK')
        except Exception as e:  # noqa: BLE001 - the batch's outcome stands; the connection goes
            logger.warning(f'Rolling back after a failed statement failed, closing: {e!r}')
            self._close(connection)
        return sub_statements, results

    def _engine_error(self, error: Exception) -> str | None:
        """Read the engine's message, `ERROR: <message>` as the Data API words it, or None.

        The driver raises an ErrorResponse as the fields it carried, once the connection is ready
        for the next statement, so such a failure leaves the connection usable. Anything else is
        a failure of the connection, not of the statement.
        """
        fields = error.args[0] if isinstance(error, self._driver_error) and error.args else None
        if not isinstance(fields, dict) or 'M' not in fields:
            return None
        return f'{fields.get("S", "ERROR")}: {fields["M"]}'

    def _open(self, connection: _Connection) -> None:
        """Open a connection, bound its statements by QUERY_TIMEOUT, and record its backend pid."""
        driver = None
        try:
            driver = self._connect(connection)
            cursor = driver.cursor()
            cursor.execute(f'SET statement_timeout TO {QUERY_TIMEOUT * 1000}')
            cursor.execute('SELECT pg_backend_pid()')
            connection.pid = int(cursor.fetchone()[0])
        except Exception as e:
            _close_quietly(driver)
            raise ToolError(
                f'Could not connect to {connection.cluster}, database {connection.database}: {e!r}'
            ) from e
        connection.driver = driver
        connection.used = False

    def _connect(self, connection: _Connection) -> Any:
        """Connect as the server's IAM identity, the database user the Data API would use.

        That is `IAM:<user>` or `IAMR:<role>`, through GetClusterCredentialsWithIAM. The driver
        looks up the endpoint itself, and credentials are fetched for each connection rather than
        reused from its cache, so none starts on expired ones.
        """
        driver = self._driver.connect(
            iam=True,
            group_federation=True,
            cluster_identifier=connection.cluster,
            database=connection.database,
            region=self._region(),
            profile=os.environ.get('AWS_PROFILE'),
            ssl=True,
            sslmode=self._sslmode,
            timeout=QUERY_TIMEOUT + _SOCKET_GRACE,
            iam_disable_cache=True,
        )
        driver.autocommit = True
        return driver

    def _cancel(self, connection: _Connection) -> None:
        """Cancel a connection's own statement, by the pid recorded when it opened. Best effort."""
        # A pid alone is not a safe cancel target: if the backend had already ended, rather than
        # being slow, Redshift may have given its pid to another session, and this cancels that
        # session's query. The window is narrow. statement_timeout (QUERY_TIMEOUT) ends a slow
        # statement server-side before the socket gives up _SOCKET_GRACE seconds later, so only
        # a backend that stopped answering reaches here, and the pid is always this client's own
        # most recent backend, read when the connection opened and cleared when it closed.
        try:
            with self._connect(connection) as canceller:
                canceller.cursor().execute(f'SELECT pg_cancel_backend({connection.pid})')
            logger.warning(f'Cancelled backend {connection.pid} on {connection.cluster}')
        except Exception as e:  # noqa: BLE001 - logged; the connection is closed either way
            logger.warning(f'Could not cancel backend {connection.pid}: {e!r}')

    def _arm_expiry(self, session_id: str, connection: _Connection, keepalive: int | None) -> None:
        """Start a session's idle clock again, with a new keepalive when one was sent."""
        if connection.timer is not None:
            connection.timer.cancel()
        connection.keepalive = connection.keepalive if keepalive is None else keepalive
        connection.expires_at = time.monotonic() + connection.keepalive
        connection.timer = threading.Timer(
            connection.keepalive, self._expire, (session_id, connection, connection.expires_at)
        )
        connection.timer.daemon = True
        connection.timer.start()

    def _expire(self, session_id: str, connection: _Connection, expires_at: float) -> None:
        """End a session left idle for its keepalive, unless a batch has used it since."""
        # A batch running on it arms a new timer as it ends.
        if not connection.lock.acquire(blocking=False):
            return
        try:
            if connection.expires_at == expires_at:
                self._forget(session_id, connection)
                self._close(connection)
        finally:
            connection.lock.release()

    def _forget(self, session_id: str, connection: _Connection) -> None:
        """Drop a session from the map, if it is still this connection's."""
        with self._lock:
            if self._sessions.get(session_id) is connection:
                del self._sessions[session_id]

    def _close(self, connection: _Connection) -> None:
        """Close a connection and stop its idle timer."""
        if connection.timer is not None:
            connection.timer.cancel()
        _close_quietly(connection.driver)
        connection.driver = connection.pid = connection.timer = None
