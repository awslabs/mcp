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

"""Running one SQL statement for a caller: the batch, the read-only wrapper, transactions."""

import asyncio
import re
import time
import uuid
from awslabs.redshift_mcp_server import __version__, clusters
from awslabs.redshift_mcp_server.clients import (
    ACCESS_DENIED,
    BATCH_ACTION,
    BATCH_OPERATION,
    client_manager,
)
from awslabs.redshift_mcp_server.consts import (
    CLIENT_USER_AGENT_NAME,
    FALLBACK_NO_BATCH_REPROBE,
    QUERY_LONG_POLL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
)
from awslabs.redshift_mcp_server.models import (
    RedshiftCluster,
    RedshiftDataModel,
)
from awslabs.redshift_mcp_server.settings import (
    session_keepalive,
)
from awslabs.redshift_mcp_server.sql_guard import assert_executable, might_write
from awslabs.redshift_mcp_server.transactions import (
    transaction_key,
    transaction_manager,
    transaction_target,
)
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from typing import NoReturn


# Keepalive sent on the batch that closes a transaction, so its session is released soon after
# rather than idling for SESSION_KEEPALIVE with nothing left to run. The Data API has no close
# operation, and omitting the parameter keeps the timeout the session already had, so a small
# value is the only lever; zero mints no session at all. Reaping runs on the Data API's own
# schedule, so release lands tens of seconds after the close, not on the second. It cannot cut a
# slow COMMIT short, since the timer counts idle time from when the statement finishes.
_SESSION_DRAIN = 1

# Statement statuses the Data API does not move on from.
_TERMINAL_STATUSES = frozenset({'FINISHED', 'FAILED', 'ABORTED'})
# The rest of what the Data API reports, kept only to tell a status this code does not know
# from one it is waiting on. A status in neither set is still polled for, since a new
# non-terminal one would otherwise fail every statement, but it is worth a line in the log.
_POLLING_STATUSES = frozenset({'SUBMITTED', 'PICKED', 'STARTED'})

# The statement that ends a transaction, per the parameter that asked for it.
_TRANSACTION_CLOSERS = {'commit_transaction': 'COMMIT', 'rollback_transaction': 'ROLLBACK'}

# Tags the connection with an application name.
_APP_NAME_SQL = f"SET application_name TO '{CLIENT_USER_AGENT_NAME}/{__version__}'"

# Cluster identifier to the moment the batch action was last seen denied on it, which holds the
# compatibility path in place without paying a denied call per statement. A cluster believed
# permitted is absent rather than present with a null. Keyed by cluster
# because the action takes resource-level permissions, so a denial on one says nothing about
# another.
_no_batch_since: dict[str, float] = {}

# Refusals for what the compatibility path will not carry, kept together so they stay consistent
# with each other. A transaction cannot be grouped by one statement per call. A write is declined
# for a different reason: this path keeps the contract of the release before read-write mode,
# which served reads only, so it refuses writes at every access mode.
_FALLBACK_NO_BATCH_REFUSES_WRITE = (
    'Writes need redshift-data:BatchExecuteStatement, which the current credentials are denied. '
    'Without it the server serves reads only, whatever the access mode. Granting the action '
    'restores writes in read-write mode; in read-only mode this statement is refused either '
    'way.'
)

_FALLBACK_NO_BATCH_REFUSES_TRANSACTION = (
    'Named transactions need redshift-data:BatchExecuteStatement, which the current '
    'credentials are denied. Without it each statement runs on its own connection, so there '
    'is nothing to group. Reads still work; grant the action to use transactions.'
)


# --- Submitting a batch ---


async def _execute_batch(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sqls: list[str],
    session_sink: list[str] | None = None,
    submitted_sink: list[str] | None = None,
    settled_sink: list[str] | None = None,
    terminal_sink: list[str] | None = None,
    parameters: list[dict] | None = None,
    session_id: str | None = None,
    session_keepalive: int | None = None,
    query_poll_interval: float = QUERY_POLL_INTERVAL,
    query_timeout: float = QUERY_TIMEOUT,
    query_long_poll: int = QUERY_LONG_POLL,
) -> dict:
    """Execute a batch of statements and wait for it to settle.

    Returns the terminal response whatever the outcome, including a failure: only the caller
    knows which statement was its own, so only the caller can turn a failed one into a
    useful message.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database name.
        sqls: The statements to run, in order, on one connection.
        session_sink: Appended with the session id as soon as one is minted, so a caller can
            end it even when the batch then fails and never returns it.
        submitted_sink: Appended with the batch id once the service has accepted it, so a
            caller can tell a batch that never ran from one still in flight. Abandoning the
            poll does not cancel an accepted batch.
        settled_sink: Appended with the batch id as soon as it is seen to have finished, so a
            caller can tell a batch that never ran from one whose result could not be read.
        terminal_sink: Appended with the batch id once it reached any terminal status, so a
            caller can tell a batch that failed from one this call stopped watching.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        session_id: Run on this existing session instead of a fresh connection.
        session_keepalive: Mint a session with this idle timeout, in seconds. Re-sent on
            every statement of a transaction, since the timeout counts idle time only.
        query_poll_interval: Polling interval in seconds for checking batch status.
        query_timeout: Maximum time in seconds to wait for the batch to settle.
        query_long_poll: Data API WaitTimeSeconds, 1-30, or 0 to disable long polling.

    Returns:
        The terminal DescribeStatement response, carrying Status and SubStatements.

    Raises:
        ToolError: If the batch does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()

    request_params: dict[str, str | int | list] = {
        'Sqls': sqls,
        # The Data API's default TRANSACTION mode wraps the whole batch and commits at its
        # end, which would defeat BEGIN READ ONLY and let a write persist. This server runs
        # its own transactions, so it opts out of that wrapper.
        'ExecutionMode': 'AUTO_COMMIT',
        # botocore retries a submit whose response was lost, which for a write means applying
        # it twice. A fresh token per submit is what makes the retry a no-op rather than a
        # second write; the service answers a repeat with the original statement id.
        'ClientToken': str(uuid.uuid4()),
    }

    if session_id:
        # A session already holds the connection, and the API refuses to be told again.
        request_params['SessionId'] = session_id
    else:
        request_params['Database'] = database_name
        if cluster_info.type == 'provisioned':
            request_params['ClusterIdentifier'] = cluster_identifier
        elif cluster_info.type == 'serverless':
            request_params['WorkgroupName'] = cluster_identifier
        else:
            # Discovery only ever sets 'provisioned' or 'serverless', so reaching this is
            # our bug, not something the caller can act on. Left as a bare exception so the
            # SDK reports it as a crash and logs the traceback.
            raise Exception(f'Unknown cluster type: {cluster_info.type}')

    if session_keepalive is not None:
        request_params['SessionKeepAliveSeconds'] = session_keepalive

    if parameters:
        request_params['Parameters'] = parameters

    long_poll_params = {'WaitTimeSeconds': query_long_poll} if query_long_poll else {}

    # boto3 is synchronous and a long poll holds the caller for up to query_long_poll
    # seconds, so every Data API call here runs off the event loop.
    response = await asyncio.to_thread(
        data_client.batch_execute_statement, **request_params, **long_poll_params
    )
    statement_id = response['Id']

    if submitted_sink is not None:
        # Recorded the moment the service accepts the batch, because from here on its
        # statements run whatever happens to this call: nothing below cancels them.
        submitted_sink.append(statement_id)

    if session_sink is not None and response.get('SessionId'):
        # Recorded before settling, because a batch that mints a session and then fails still
        # leaves that session alive for its keepalive. The caller needs the id to end it.
        session_sink.append(response['SessionId'])

    logger.debug(f'Executed batch {statement_id} of {len(sqls)} statements')

    return await _settle_statement(
        statement_id=statement_id,
        response=response,
        query_poll_interval=query_poll_interval,
        query_timeout=query_timeout,
        query_long_poll=query_long_poll,
        settled_sink=settled_sink,
        terminal_sink=terminal_sink,
    )


# --- Settling a submitted statement ---


async def _settle_statement(
    statement_id: str,
    response: dict,
    query_poll_interval: float,
    query_timeout: float,
    query_long_poll: int,
    settled_sink: list[str] | None = None,
    terminal_sink: list[str] | None = None,
) -> dict:
    """Poll one submitted statement or batch until it reaches a terminal status.

    Submit and describe report status alike, so one loop settles the long-polled submit and
    every later poll. A terminal submit response still gets one describe, because only
    describe carries the sub-statement ids and the result-set flag the caller needs.

    Args:
        statement_id: The id returned at submit.
        response: The submit response, already carrying a status when long polling settled it.
        query_poll_interval: Polling interval in seconds.
        query_timeout: Maximum time in seconds to wait.
        query_long_poll: Data API WaitTimeSeconds, 1-30, or 0 to disable long polling.
        settled_sink: Appended with the statement id the moment a FINISHED status is seen,
            before anything else can fail.
        terminal_sink: Appended with the statement id on any terminal status, FAILED and
            ABORTED included. Tells a statement this call watched conclude from one it stopped
            watching, which settled_sink alone cannot: both are empty when a poll is abandoned
            and when it ends in failure.

    Returns:
        The terminal DescribeStatement response.

    Raises:
        ToolError: If it does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()
    long_poll_params = {'WaitTimeSeconds': query_long_poll} if query_long_poll else {}
    described = False
    recorded = False
    warned_unknown = False

    # Wall clock, since a long poll blocks server-side.
    deadline = time.monotonic() + query_timeout
    while True:
        status = response.get('Status')

        if status in _TERMINAL_STATUSES:
            # Recorded the moment the status is seen, before the confirming describe below,
            # because everything in the batch has already run and no failure from here on can
            # undo it. Filled after that call instead, a throttled describe would look to the
            # caller like a batch that never ran. One flag for both sinks, and set on any
            # terminal status rather than on FINISHED, because the re-check below brings a
            # settled statement back through here a second time.
            if not recorded:
                recorded = True
                if terminal_sink is not None:
                    terminal_sink.append(statement_id)
                if settled_sink is not None and status == 'FINISHED':
                    settled_sink.append(statement_id)

            if described:
                logger.debug(f'Statement settled: {statement_id} ({status})')
                return response

            # Only describe carries the sub-statement ids and the result-set flag, so a submit
            # that long polling settled is owed one. Its answer goes back through this loop
            # rather than being returned on trust: returned unchecked, a describe that came
            # back without a status, or with a non-terminal one, reached the caller as a
            # settled batch and failed there as a bare KeyError.
            response = await asyncio.to_thread(data_client.describe_statement, Id=statement_id)
            described = True
            continue

        if status not in _POLLING_STATUSES and not warned_unknown:
            # Polled for anyway, so a status added to the API keeps working, but silence here
            # looked exactly like a statement that never finished.
            warned_unknown = True
            logger.warning(f'Unrecognized status {status!r}, polling on: {statement_id}')

        if time.monotonic() >= deadline:
            logger.error(f'Statement timed out: {statement_id}')
            raise ToolError(f'Statement timed out after {query_timeout} seconds')

        await asyncio.sleep(query_poll_interval)

        try:
            response = await asyncio.to_thread(
                data_client.describe_statement, Id=statement_id, **long_poll_params
            )
            described = True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') != 'ActiveWaitingRequestsExceededException':
                raise
            logger.warning(f'Long polling limit reached, polling instead: {statement_id}')
            long_poll_params = {}


# --- Running one statement ---
# One shared helper and the three entry points that use it. Each turns a caller's statement into
# a batch: standalone with the read-only wrapper around it, or on a named transaction's session
# with a closer after it.


async def _execute_batch_for_statement(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sqls: list[str],
    caller_index: int | None,
    session_sink: list[str] | None = None,
    submitted_sink: list[str] | None = None,
    settled_sink: list[str] | None = None,
    terminal_sink: list[str] | None = None,
    parameters: list[dict] | None = None,
    session_id: str | None = None,
    session_keepalive: int | None = None,
) -> tuple[dict, str, str | None]:
    """Execute a batch on one statement's behalf and return that statement's result.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database name.
        sqls: The statements to run, in order, on one connection.
        caller_index: Index of the caller's statement in `sqls`, or None when the batch
            carries none of the caller's SQL, as a bare COMMIT does.
        session_sink: Appended with the session id as soon as one is minted, so a caller can
            end it even when the batch then fails and never returns it.
        submitted_sink: Appended with the batch id once the service has accepted it, so a
            caller can tell a batch that never ran from one still in flight.
        settled_sink: Appended with the batch id once every statement in it has run, so a
            caller can tell a failure that stopped the batch from one that only stopped its
            result being read.
        terminal_sink: Appended with the batch id once it reached any terminal status, so a
            caller can tell a batch that failed from one this call stopped watching.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        session_id: Session to run on, for a statement inside a transaction.
        session_keepalive: Idle timeout to mint a session with, when opening a transaction.

    Returns:
        Tuple of the raw get_statement_result response, the caller statement's id, and the
        session the batch ran on when one was minted.

    Raises:
        ToolError: If a statement fails or the batch times out.
    """
    batch = await _execute_batch(
        cluster_info=cluster_info,
        cluster_identifier=cluster_identifier,
        database_name=database_name,
        sqls=sqls,
        session_sink=session_sink,
        submitted_sink=submitted_sink,
        settled_sink=settled_sink,
        terminal_sink=terminal_sink,
        parameters=parameters,
        session_id=session_id,
        session_keepalive=session_keepalive,
    )

    sub_statements = batch['SubStatements']

    # Any statement failing fails the batch, and a surrounding failure matters as much as the
    # caller's own: a failed BEGIN READ ONLY leaves the statement running unwrapped, with
    # nothing to make the engine refuse a write or to discard one.
    if batch['Status'] != 'FINISHED':
        # A statement that ran and failed carries the engine's message. When the connection
        # itself was refused nothing ran, every statement is ABORTED with a placeholder, and
        # only the batch carries the reason.
        failed = next((sub for sub in sub_statements if sub['Status'] == 'FAILED'), None)
        error = (failed or batch).get('Error', 'Unknown error')
        logger.debug(f'Statement failed: {error}')
        raise ToolError(f'Statement failed: {error}')

    if caller_index is None:
        return {'Records': [], 'ColumnMetadata': []}, batch['Id'], batch.get('SessionId')

    caller_statement = sub_statements[caller_index]
    query_id = caller_statement['Id']

    # Only fetch results when the statement produced a result set. SET and DDL do not, and
    # GetStatementResult answers ResourceNotFoundException for them.
    if caller_statement.get('HasResultSet'):
        data_client = client_manager.redshift_data_client()
        results_response = await asyncio.to_thread(data_client.get_statement_result, Id=query_id)
    else:
        results_response = {'Records': [], 'ColumnMetadata': []}

    return results_response, query_id, batch.get('SessionId')


async def execute_standalone_statement(
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    enforce_read_only: bool = True,
) -> tuple[dict, str]:
    """Execute one standalone SQL statement, outside any transaction the caller named.

    The statement is validated by the SQL guard, then sent as a single batch whose
    surrounding statements depend on `enforce_read_only`:

    Enforced (`enforce_read_only=True`):
        `SET application_name` -> `BEGIN READ ONLY` -> caller SQL -> `ROLLBACK`

    Not enforced (`enforce_read_only=False`):
        `SET application_name` -> caller SQL

    The batch runs with `ExecutionMode=AUTO_COMMIT`, so the Data API adds no transaction of
    its own and the wrapper, where applied, is the only transaction in play. Statements in a
    batch run serially on one connection, so `SET application_name` applies to the statements
    after it and no session is needed to carry it.

    The wrapper is what actually blocks a write: the engine rejects writes the guard's
    deny-list does not enumerate, and the closing `ROLLBACK` discards anything uncommitted.
    It also runs when the caller's statement fails, so a failure cannot leave a transaction
    open.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the statement against.
        sql: The single SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
            Only the caller's statement carries placeholders, which the Data API accepts.
        enforce_read_only: Whether to apply read-only protection: the guard's statement-type
            deny-list and the transaction wrapper. Clear it for a caller permitted to write,
            and for this server's own SQL, which it authors and so does not police.
            Single-statement enforcement applies either way.

    Returns:
        Tuple containing:
        - Dictionary with the raw results_response from get_statement_result.
        - String with the query_id of the caller's statement.

    Raises:
        ToolError: If the cluster is unknown, a statement fails, or the batch times out.
    """
    # Validate the statement with the SQL guard before doing any work.
    assert_executable(sql, enforce_read_only=enforce_read_only)

    cluster_info = await clusters.resolve_cluster(cluster_identifier)

    if not _no_batch_active(cluster_identifier):
        sqls = [_APP_NAME_SQL]
        if enforce_read_only:
            sqls.append('BEGIN READ ONLY')
        caller_index = len(sqls)
        sqls.append(sql)
        if enforce_read_only:
            sqls.append('ROLLBACK')

        # Without the wrapper nothing discards a statement this call stops watching, so an
        # unwrapped write that is accepted and never seen to end may still land.
        submitted: list[str] = []
        terminal: list[str] = []

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                submitted_sink=submitted,
                terminal_sink=terminal,
                parameters=parameters,
            )
            return results_response, query_id
        except ClientError as e:
            if not _is_no_batch(e):
                _report_unwatched_write(sql, enforce_read_only, submitted, terminal, e)
                raise
            # Nothing ran, so the same statement can be retried below rather than failing
            # this call on a permissions problem the compatibility path can absorb.
            _latch_no_batch(e, cluster_identifier)
        except Exception as e:
            _report_unwatched_write(sql, enforce_read_only, submitted, terminal, e)
            raise

    if might_write(sql):
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_WRITE)

    # A recognized read cannot write, so it needs no wrapper and can go on its own.
    return await _execute_statement_fallback_no_batch(
        cluster_info=cluster_info,
        cluster_identifier=cluster_identifier,
        database_name=database_name,
        sql=sql,
        parameters=parameters,
    )


async def _begin_transaction(
    cluster_identifier: str,
    database_name: str,
    name: str,
    sql: str | None = None,
    parameters: list[dict] | None = None,
    enforce_read_only: bool = True,
) -> tuple[dict, str]:
    """Open a named transaction, optionally running its first statement.

    The transaction holds a Data API session for as long as it stays open, which is the only
    reason this server ever creates one. The access mode picks the transaction's own mode:
    read-only callers get `BEGIN READ ONLY`, so the engine refuses a write inside it just as
    it does outside one.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to open the transaction in.
        name: The caller's name for the transaction.
        sql: Optional first statement to run inside it.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        enforce_read_only: Whether to apply read-only protection.

    Returns:
        Tuple of the raw results_response and the query_id of `sql`, or of the batch when no
        statement was given.

    Raises:
        ToolError: If the name is already open, the target is at its cap, the cluster is
            unknown, or a statement fails.
    """
    if _no_batch_active(cluster_identifier):
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION)

    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    cluster_info = await clusters.resolve_cluster(cluster_identifier)

    key = transaction_key(cluster_identifier, database_name, name)
    target = transaction_target(cluster_identifier, database_name)
    transaction_manager.reserve(key, target, name)

    sqls = [_APP_NAME_SQL, 'BEGIN READ ONLY' if enforce_read_only else 'BEGIN']
    caller_index = None
    if sql is not None:
        caller_index = len(sqls)
        sqls.append(sql)

    lock, generation = transaction_manager.claim(key)
    # A batch that mints a session and then fails leaves that session alive and holding an
    # aborted transaction. The id never reaches the return value in that case, so it is
    # collected here and rolled back below.
    opened_session: list[str] = []
    attached = False
    rolled_back = False

    try:
        async with lock:
            transaction_manager.assert_current(key, generation, name)
            try:
                results_response, query_id, session_id = await _execute_batch_for_statement(
                    cluster_info=cluster_info,
                    cluster_identifier=cluster_identifier,
                    database_name=database_name,
                    sqls=sqls,
                    caller_index=caller_index,
                    session_sink=opened_session,
                    parameters=parameters,
                    session_keepalive=session_keepalive(),
                )
            except Exception as e:
                # The transaction never opened, or opened and then failed. Either way a
                # session that did get minted has to be ended rather than left to idle out
                # holding an aborted transaction. The name is released by the `finally`.
                if opened_session:
                    await _rollback_lost_transaction(
                        cluster_info, cluster_identifier, database_name, opened_session[0]
                    )
                    rolled_back = True
                if isinstance(e, ClientError) and _is_no_batch(e):
                    _latch_no_batch(e, cluster_identifier)
                    raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION) from e
                raise

            if session_id is None:
                # A batch carrying SessionKeepAliveSeconds always mints a session, so this
                # only happens if that stops holding. Without the id there is no way to reach
                # the transaction again, so refuse the name and let the idle timeout end it.
                raise ToolError(
                    f'Transaction {name!r} could not be opened: the Data API returned no session.'
                )

            transaction_manager.attach(key, session_id)
            attached = True
    finally:
        if not attached:
            # Reached by every way this can end without an open transaction, including
            # cancellation while the lock is being acquired. Cancellation is a BaseException,
            # so the handler above never sees it.
            transaction_manager.forget(key)
            if opened_session and not rolled_back:
                # Freeing the name without ending the session would put more live sessions
                # against the target than the cap admits. A task being torn down cannot await
                # its own cleanup, so the rollback is detached; it swallows and logs its own
                # failures, and carries the drain keepalive with it.
                logger.warning(
                    f'Transaction {key} ended before it opened; rolling back the session it '
                    f'minted, {opened_session[0]}'
                )
                asyncio.ensure_future(  # noqa: RUF006 - deliberately not awaited
                    _rollback_lost_transaction(
                        cluster_info, cluster_identifier, database_name, opened_session[0]
                    )
                )

    return results_response, query_id


async def _execute_statement_in_transaction(
    cluster_identifier: str,
    database_name: str,
    name: str,
    sql: str | None = None,
    parameters: list[dict] | None = None,
    closer: str | None = None,
    enforce_read_only: bool = True,
) -> tuple[dict, str]:
    """Execute a statement on an open transaction's session, optionally closing it.

    A statement inside a transaction is sent bare: the transaction is already the wrapper,
    so wrapping again would nest a `BEGIN`. The guard still runs on it, which is what keeps a
    read-only caller from writing inside a transaction just as outside one.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database the transaction runs in.
        name: The caller's name for the transaction.
        sql: Optional statement to run on the session.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        closer: `COMMIT` or `ROLLBACK` to end the transaction with, or None to leave it open.
        enforce_read_only: Whether to apply read-only protection.

    Returns:
        Tuple of the raw results_response and the query_id of `sql`, or of the batch when no
        statement was given.

    Raises:
        ToolError: If no transaction is open under that name, its session is gone, or a
            statement fails.
    """
    if _no_batch_active(cluster_identifier):
        if closer is not None:
            # Ending a transaction needs nothing from the batch path. Refusing here left the
            # caller unable to close what they had opened, and holding a slot against the cap,
            # until the re-probe came round. The name goes, as it does when the denial is
            # discovered mid-call, and the session ends on its idle timeout.
            transaction_manager.forget(transaction_key(cluster_identifier, database_name, name))
            raise ToolError(
                f'{BATCH_ACTION} is now denied, so {name!r} cannot be closed on the cluster. '
                f'The name is released here and its session ends when it goes idle; anything it '
                f'had not committed is discarded. Grant the action to use transactions.'
            )
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION)

    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    key = transaction_key(cluster_identifier, database_name, name)
    target = transaction_target(cluster_identifier, database_name)

    # Claimed before the first await, not after. Every await is a window in which the name can
    # be closed and reopened, and a generation read after one already reflects the transaction
    # that took the name over, so `assert_current` below would pass on it and add this
    # statement to a stranger's transaction.
    lock, generation = transaction_manager.claim(key)

    cluster_info = await clusters.resolve_cluster(cluster_identifier)

    sqls = [] if sql is None else [sql]
    caller_index = None if sql is None else 0
    if closer is not None:
        sqls.append(closer)

    # A closer that has already run ends the transaction whatever happens next, so anything
    # raised after this is filled cannot be treated as though the transaction survived.
    settled: list[str] = []
    # A closer the service accepted but that never settled ends it too, for all the caller can
    # tell: abandoning the poll does not cancel it.
    submitted: list[str] = []
    # Filled on any terminal status, which is what separates the two: a batch that concluded
    # badly is not a batch this call stopped watching, and `settled` is empty for both.
    terminal: list[str] = []

    async with lock:
        transaction_manager.assert_current(key, generation, name)
        session_id = transaction_manager.session_id(key, name, target)

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                submitted_sink=submitted,
                settled_sink=settled,
                terminal_sink=terminal,
                parameters=parameters,
                session_id=session_id,
                session_keepalive=_SESSION_DRAIN if closer is not None else session_keepalive(),
            )
        except ClientError as e:
            outcome = _transaction_outcome(closer, submitted, settled, terminal)
            if closer is not None and outcome in (_CLOSER_RAN, _CLOSER_UNKNOWN):
                # The service took the closer, so it runs whether or not this call saw it
                # finish, and the name has to go either way or the caller could roll back work
                # already committed and be told that worked.
                _forget_closed_transaction(key, name, closer, e, ran=outcome == _CLOSER_RAN)
            if outcome == _ABORTED:
                # The batch concluded badly, so the transaction is gone on the cluster whatever
                # this call goes on to report. Handled here and not left to the arm below,
                # which is a sibling `except` a ClientError never reaches.
                _abandon_transaction(
                    key, cluster_info, cluster_identifier, database_name, session_id
                )
            if _is_no_batch(e):
                # The transaction stays open on the cluster but is now unreachable, so drop
                # the name and let its idle timeout end it. Told only that transactions need
                # the action, the caller would grant it and look for a transaction that this
                # call had already given up on.
                _latch_no_batch(e, cluster_identifier)
                transaction_manager.forget(key)
                raise ToolError(
                    f'{BATCH_ACTION} was denied partway through {name!r}, which can no longer '
                    f'be reached. The name is released here and its session ends when it goes '
                    f'idle; anything it had not committed is discarded. Reads still work; '
                    f'grant the action to use transactions again.'
                ) from e
            if not _is_session_gone(e):
                # A closer the service took is handled above, whether it concluded or not, so
                # what reaches here either never left this process or was a statement in a
                # transaction that stays the caller's: the error is reported and the name is
                # still theirs to close.
                raise
            # The service took the session away, so the transaction is gone with everything
            # it had not committed. Report it as missing rather than as an AWS error.
            logger.warning(f'Transaction {key} lost its session: {e}')
            transaction_manager.forget(key)
            raise ToolError(
                f'No open transaction named {name!r} on {target}. An earlier call committed or '
                f'rolled it back, it was never opened, it was rolled back after a failed '
                f'statement, it expired after being idle, or it was opened against a '
                f'different cluster or database.'
            ) from e
        except Exception as e:
            outcome = _transaction_outcome(closer, submitted, settled, terminal)
            if closer is not None and outcome in (_CLOSER_RAN, _CLOSER_UNKNOWN):
                _forget_closed_transaction(key, name, closer, e, ran=outcome == _CLOSER_RAN)
            # Everything else here aborts the transaction, including the case where nothing was
            # accepted: reaching this arm at all means the statement did not come back, and a
            # later COMMIT would report success while persisting nothing.
            _abandon_transaction(key, cluster_info, cluster_identifier, database_name, session_id)
            raise
        except BaseException:
            # Cancellation, which is not an Exception and so reaches neither arm above. There is
            # no caller left to tell, so what became of the closer is recorded in the log and
            # the cancellation is left to propagate.
            outcome = _transaction_outcome(closer, submitted, settled, terminal)
            if outcome == _CLOSER_RAN:
                logger.warning(
                    f'Transaction {name!r} was cancelled after its {closer} ran, which stands'
                )
                transaction_manager.forget(key)
                raise
            if outcome == _CLOSER_UNKNOWN:
                # No rollback here: the service holds the closer and this call never saw it
                # end, so it may be applying right now. Keyed on `settled` alone, this arm
                # fired one and recorded a cancellation, where its siblings call the same state
                # unknown.
                logger.warning(
                    f'Transaction {name!r} was cancelled with its {closer} accepted, which may '
                    f'have been applied'
                )
                transaction_manager.forget(key)
                raise
            logger.warning(f'Transaction {key} was cancelled')
            _abandon_transaction(key, cluster_info, cluster_identifier, database_name, session_id)
            raise

        if closer is not None:
            transaction_manager.forget(key)
        else:
            # Still open, and just used, so its idle clock starts again from here.
            transaction_manager.touch(key)

    return results_response, query_id


# --- What a failed call left behind ---
# Reached from the failure arms above, which decide only how to deliver the news. One reading of
# how far the batch got, then the three ways a transaction can end: dropped with its outcome
# reported, dropped and rolled back, or - outside a transaction, where there is no name to drop -
# reported as possibly applied.

# What a failed call leaves behind, decided by how far its batch got rather than by which
# exception arrived.
_CLOSER_RAN = 'closer_ran'
_CLOSER_UNKNOWN = 'closer_unknown'
_ABORTED = 'aborted'
_UNRESOLVED = 'unresolved'


def _report_unwatched_write(
    sql: str, enforce_read_only: bool, submitted: list[str], terminal: list[str], error: Exception
) -> None:
    """Raise over `error` when a write was accepted and this call never saw it end.

    Outside a transaction there is no name to drop and no session to end, so the only thing a
    failure can leave behind is the statement itself. Under the read-only wrapper that costs
    nothing, because the trailing ROLLBACK runs even after a statement fails. Without it the
    batch autocommits, and abandoning the poll cancels nothing: reported as a bare timeout, a
    write that was still committing read as one that had not happened, and a caller who retried
    wrote twice.

    Args:
        sql: The caller's statement, to tell a write from a read.
        enforce_read_only: Whether the wrapper was applied, which decides whether it can persist.
        submitted: Non-empty once the service accepted the batch.
        terminal: Non-empty once the batch was seen to conclude.
        error: What the call failed with, kept as the cause.

    Raises:
        ToolError: If the statement may have been applied.
    """
    if enforce_read_only or not submitted or terminal or not might_write(sql):
        return

    raise ToolError(
        f'The statement was accepted but this call did not see it finish, so it may or may not '
        f'have been applied. It runs with autocommit and nothing here cancels it: check the '
        f'data before retrying. {error}'
    ) from error


def _transaction_outcome(
    closer: str | None, submitted: list[str], settled: list[str], terminal: list[str]
) -> str:
    """Say what a failed call left of its transaction, from how far its batch got.

    The three failure arms above differ only in how they deliver the news; what happened is the
    same fact for all of them, and reading it out of the three sinks at each arm is what let one
    arm answer a state differently from its siblings. Decided here once instead.

    Args:
        closer: COMMIT or ROLLBACK when the call was ending the transaction, else None.
        submitted: Non-empty once the service accepted the batch.
        settled: Non-empty once the batch was seen to finish.
        terminal: Non-empty once the batch was seen to conclude, however it concluded.

    Returns:
        `_CLOSER_RAN` when a closer committed or discarded and so stands; `_CLOSER_UNKNOWN`
        when a closer was accepted but never watched to a conclusion, so it may have applied;
        `_ABORTED` when the batch concluded as something other than finished, which ends the
        transaction on the cluster; `_UNRESOLVED` when nothing was accepted, leaving the
        transaction as it was.
    """
    # Checked first, and without regard to `closer`: a statement that concluded badly aborts
    # the transaction whether or not this call was also closing it.
    if terminal and not settled:
        return _ABORTED

    if closer is not None and submitted:
        return _CLOSER_RAN if settled else _CLOSER_UNKNOWN

    return _UNRESOLVED


def _forget_closed_transaction(
    key: str, name: str, closer: str, error: Exception, *, ran: bool
) -> NoReturn:
    """Drop a name whose closer reached the cluster and report what is known of it.

    Either way the name has to go, or the caller could roll back work that is already
    committed and be told it succeeded. But the failure still has to be reported, and
    reporting it bare would say a write failed when it landed, and answer the next call on the
    name with 'was rolled back after a failed statement'.

    What differs is how much is known. Reading a result can fail after the batch has settled,
    and by then the `COMMIT` is durable or the `ROLLBACK` has discarded, so the closer stands.
    A failure on the poll itself leaves it accepted but unsettled, and since abandoning the
    poll does not cancel it, the caller has to be told the outcome is unknown rather than
    guessed at either way.

    Args:
        key: The transaction key to drop.
        name: The caller's name for the transaction.
        closer: The `COMMIT` or `ROLLBACK` that reached the cluster.
        error: What failed.
        ran: Whether the closer was seen to finish.

    Raises:
        ToolError: Always, carrying both facts.
    """
    if ran:
        logger.warning(f'Transaction {name!r} failed after its {closer} ran: {error}')
        outcome = (
            f'ran its {closer}, which stands, and then failed while its result was being read'
        )
    else:
        logger.warning(f'Transaction {name!r} failed with its {closer} in flight: {error}')
        outcome = (
            f'submitted its {closer} and then lost contact before it settled, so it may or may '
            f'not have been applied. Query the data to find out which'
        )

    transaction_manager.forget(key)
    raise ToolError(f'Transaction {name!r} {outcome}: {error}') from error


def _abandon_transaction(
    key: str,
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    session_id: str,
) -> None:
    """Drop a transaction's name and end the session it was running on.

    The rollback is not awaited. Awaiting it would put an await between dropping the name and
    ending the session, and a cancellation there leaves the session alive holding an aborted
    transaction and its locks. Nothing waits on the outcome either way: the helper swallows and
    logs its own failures, and carries the drain keepalive with it.

    Args:
        key: The transaction key to drop.
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database the transaction runs in.
        session_id: The session the transaction runs on.
    """
    transaction_manager.forget(key)
    asyncio.ensure_future(  # noqa: RUF006 - see the docstring
        _rollback_lost_transaction(cluster_info, cluster_identifier, database_name, session_id)
    )


async def _rollback_lost_transaction(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    session_id: str,
) -> None:
    """Roll back a transaction whose statement failed, best effort.

    The session is being dropped either way, so a failure here changes nothing the caller can
    act on: the transaction is already aborted, and the session's idle timeout ends it. The
    name is gone by the time this runs, so the session is drained rather than left to idle.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database the transaction runs in.
        session_id: The session the transaction runs on.
    """
    try:
        await _execute_batch(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sqls=['ROLLBACK'],
            session_id=session_id,
            session_keepalive=_SESSION_DRAIN,
        )
    except Exception as e:  # noqa: BLE001 - nothing here is actionable
        logger.warning(f'Rollback of the aborted transaction on {session_id} failed: {e}')


# --- Reading an error ---


def _is_session_gone(error: ClientError) -> bool:
    """Report whether a Data API error means the session no longer exists.

    Args:
        error: The botocore error raised at submit.

    Returns:
        True when the session is expired, reclaimed or unknown.
    """
    if error.response.get('Error', {}).get('Code') != 'ValidationException':
        return False
    # All three are the same fact worded differently, and the service moves between them.
    # Measured on one session: 'Session is expired' for the first half minute after it went,
    # then 'Session is not available' from there on; an unknown id gives 'is invalid'. A
    # session also disappears under lock contention within seconds, not only at the keepalive,
    # so matching the expiry wording alone leaves a name no call can close.
    message = error.response.get('Error', {}).get('Message', '')
    return any(
        marker in message
        for marker in ('Session is expired', 'Session is not available', 'is invalid')
    )


# --- Fallback: no_batch ---
# Serves credentials denied redshift-data:BatchExecuteStatement by running one statement
# per call, which keeps the read-only contract of the release before named transactions.
# Everything tagged no_batch belongs to it and nothing above depends on it, so the whole
# path can be deleted with its constants and tests once the action is universal.
#
# It stays in this module rather than taking one of its own because it is temporary: when the
# action is universal this section is deleted and the file gets shorter.


def _is_no_batch(error: ClientError) -> bool:
    """Report whether the error means BatchExecuteStatement itself is denied.

    The operation is checked as well as the code, because the callers wrap the whole batch
    flow: the submit, the DescribeStatement that settles it, and the GetStatementResult that
    reads it. A denial on either of those two is not something this path can absorb - it
    needs both itself - so treating it as a denied batch would latch the fallback, refuse
    writes and transactions, and still fail on the very next call.

    A cluster the credentials cannot reach answers ValidationException rather than a denial,
    so that case does not reach here at all.

    Args:
        error: The botocore error raised by one of the batch flow's calls.

    Returns:
        True when the batch action, specifically, is denied to these credentials.
    """
    if error.response.get('Error', {}).get('Code') not in ACCESS_DENIED:
        return False
    if error.operation_name != BATCH_OPERATION:
        return False

    # The operation alone is not enough. The batch call also reports denials of the grants the
    # Data API needs on the caller's behalf - GetClusterCredentialsWithIAM, GetCredentials,
    # GetSecretValue - and latching on one of those would tell the operator to grant an action
    # they already hold, while the fallback fails on the very same missing grant. So the denied
    # action has to be the batch action, whenever the message names an action at all.
    denied = re.search(
        r'not authorized to perform:\s*(\S+)', error.response.get('Error', {}).get('Message', '')
    )
    return denied is None or denied.group(1) == BATCH_ACTION


def _no_batch_active(cluster_identifier: str) -> bool:
    """Report whether the no_batch fallback is in force for one cluster, consuming a due re-probe.

    Args:
        cluster_identifier: The cluster the caller addressed.

    Returns:
        True while the batch path is known denied on that cluster, and False once per
        FALLBACK_NO_BATCH_REPROBE seconds after that, so a granted policy is picked up
        without a restart.
    """
    since = _no_batch_since.get(cluster_identifier)

    if since is None:
        return False

    if time.monotonic() - since < FALLBACK_NO_BATCH_REPROBE:
        return True

    # Due for a probe. Clearing it first means a still-denied batch latches again, which is
    # what keeps the warning to one per re-probe window rather than one per statement.
    del _no_batch_since[cluster_identifier]
    return False


def no_batch_latched(cluster_identifier: str) -> bool:
    """Report whether the batch path is known denied on one cluster, without probing.

    `_no_batch_active` consumes a due re-probe as a side effect, so it decides a statement's
    path and must be called once per statement. This answers the same question for anything
    that only needs to know, such as whether to raise a confirmation prompt for a statement
    that is about to be refused anyway.

    Args:
        cluster_identifier: The cluster the caller addressed.

    Returns:
        True while a denial is recorded for that cluster, re-probe due or not.
    """
    return cluster_identifier in _no_batch_since


def _latch_no_batch(error: ClientError, cluster_identifier: str) -> None:
    """Record that the batch action is denied on one cluster, and name the grant that restores it.

    Kept per cluster because the action takes resource-level permissions: a principal can be
    denied it on one cluster and hold it on another, and a process-wide latch refused statements
    on the second that would have run.

    Args:
        error: The denial, quoted so the operator can see which principal was refused.
        cluster_identifier: The cluster the denial came from.
    """
    _no_batch_since[cluster_identifier] = time.monotonic()
    logger.warning(
        f'{BATCH_ACTION} is denied on {cluster_identifier}, so statements there now run one at '
        'a time: reads still work, writes and named transactions do not. Grant the action to '
        f'restore them; the batch path is retried in {FALLBACK_NO_BATCH_REPROBE}s. {error}'
    )


async def _execute_statement_fallback_no_batch(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    query_poll_interval: float = QUERY_POLL_INTERVAL,
    query_timeout: float = QUERY_TIMEOUT,
    query_long_poll: int = QUERY_LONG_POLL,
) -> tuple[dict, str]:
    """Execute one statement through ExecuteStatement, for credentials denied the batch.

    The compatibility path, used only while redshift-data:BatchExecuteStatement is denied.
    One statement per call means no connection is shared, so there is nowhere to put
    `BEGIN READ ONLY` or `SET application_name`: the caller must have established that this
    statement cannot write before choosing this path.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database to execute against.
        sql: The single statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        query_poll_interval: Polling interval in seconds.
        query_timeout: Maximum time in seconds to wait.
        query_long_poll: Data API WaitTimeSeconds, 1-30, or 0 to disable long polling.

    Returns:
        Tuple of the raw get_statement_result response and the statement's id.

    Raises:
        ToolError: If the statement fails or does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()

    request_params: dict[str, str | int | list] = {'Sql': sql, 'Database': database_name}
    if cluster_info.type == 'provisioned':
        request_params['ClusterIdentifier'] = cluster_identifier
    elif cluster_info.type == 'serverless':
        request_params['WorkgroupName'] = cluster_identifier
    else:
        # Discovery only ever sets 'provisioned' or 'serverless', so reaching this is our
        # bug, not something the caller can act on.
        raise Exception(f'Unknown cluster type: {cluster_info.type}')

    if parameters:
        request_params['Parameters'] = parameters

    long_poll_params = {'WaitTimeSeconds': query_long_poll} if query_long_poll else {}

    response = await asyncio.to_thread(
        data_client.execute_statement, **request_params, **long_poll_params
    )
    statement_id = response['Id']
    logger.debug(f'Executed statement {statement_id} on the compatibility path')

    settled = await _settle_statement(
        statement_id=statement_id,
        response=response,
        query_poll_interval=query_poll_interval,
        query_timeout=query_timeout,
        query_long_poll=query_long_poll,
    )

    if settled['Status'] != 'FINISHED':
        error = settled.get('Error', 'Unknown error')
        logger.debug(f'Statement failed: {error}')
        raise ToolError(f'Statement failed: {error}')

    if not settled.get('HasResultSet'):
        return {'Records': [], 'ColumnMetadata': []}, statement_id

    results_response = await asyncio.to_thread(data_client.get_statement_result, Id=statement_id)
    return results_response, statement_id


# --- Reading the caller's transaction parameters ---


def _resolve_transaction_action(
    sql: str | None,
    begin_transaction: str | None,
    in_transaction: str | None,
    commit_transaction: str | None,
    rollback_transaction: str | None,
) -> tuple[str | None, str | None]:
    """Work out which transaction the caller addressed, and how.

    Exactly one transaction parameter may be given, which collapses every invalid combination
    into one rule. A name is always the caller's own choice, so a typo opens a new transaction
    rather than joining an existing one only when `begin_transaction` asked for that; the other
    three refuse an unknown name.

    Args:
        sql: The statement the caller passed, if any.
        begin_transaction: Name of a transaction to open.
        in_transaction: Name of an open transaction to add a statement to.
        commit_transaction: Name of an open transaction to commit.
        rollback_transaction: Name of an open transaction to roll back.

    Returns:
        Tuple of the parameter that was given and the transaction name, or (None, None) when
        the statement runs outside any transaction.

    Raises:
        ToolError: If more than one transaction parameter is given, a name is blank, or `sql`
            is missing where it is required.
    """
    given = {
        parameter: name
        for parameter, name in (
            ('begin_transaction', begin_transaction),
            ('in_transaction', in_transaction),
            ('commit_transaction', commit_transaction),
            ('rollback_transaction', rollback_transaction),
        )
        if name is not None
    }

    if len(given) > 1:
        raise ToolError(
            f'Only one transaction parameter is allowed per call, but '
            f'{", ".join(sorted(given))} were given.'
        )

    if not given:
        if sql is None:
            raise ToolError(
                'sql is required, except when committing or rolling back a transaction.'
            )
        return None, None

    action, name = next(iter(given.items()))

    if not name.strip():
        raise ToolError(f'{action} needs the name of a transaction.')

    if sql is None and action == 'in_transaction':
        raise ToolError('sql is required with in_transaction.')

    # Stripped, so that a name padded on one call and not the next addresses one transaction
    # rather than opening a second the caller cannot then reach.
    return action, name.strip()


# --- The tool ---


async def execute_query(
    cluster_identifier: str,
    database_name: str,
    sql: str | None = None,
    enforce_read_only: bool = True,
    begin_transaction: str | None = None,
    in_transaction: str | None = None,
    commit_transaction: str | None = None,
    rollback_transaction: str | None = None,
) -> dict:
    """Execute a SQL statement against a Redshift cluster using the Data API.

    Without a transaction parameter the statement runs on its own connection and nothing
    carries over to the next call. A transaction parameter names a transaction the caller
    controls across calls, which holds a session open for as long as it stays open.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute against.
        sql: The SQL statement to execute. Optional only when closing a transaction.
        enforce_read_only: Whether to apply read-only protection. Defaults to True.
        begin_transaction: Open a transaction under this name and run `sql` inside it, if
            given. Fails when the name is already open.
        in_transaction: Run `sql` inside the transaction already open under this name.
        commit_transaction: Run `sql`, if given, then commit this transaction.
        rollback_transaction: Run `sql`, if given, then roll this transaction back.

    Returns:
        Dictionary with query results including columns, rows, and metadata.

    Raises:
        ToolError: If the parameters conflict, the transaction is unknown, the SQL is
            rejected by the guard, or a statement fails.
    """
    try:
        logger.info(f'Executing query on cluster {cluster_identifier} in database {database_name}')
        logger.debug(f'SQL: {sql}')

        action, name = _resolve_transaction_action(
            sql, begin_transaction, in_transaction, commit_transaction, rollback_transaction
        )

        if action is None:
            results_response, query_id = await execute_standalone_statement(
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sql=sql,  # pyright: ignore[reportArgumentType] - checked above
                enforce_read_only=enforce_read_only,
            )
        elif action == 'begin_transaction':
            results_response, query_id = await _begin_transaction(
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                name=name,  # pyright: ignore[reportArgumentType] - set with the action
                sql=sql,
                enforce_read_only=enforce_read_only,
            )
        else:
            results_response, query_id = await _execute_statement_in_transaction(
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                name=name,  # pyright: ignore[reportArgumentType] - set with the action
                sql=sql,
                closer=_TRANSACTION_CLOSERS.get(action),
                enforce_read_only=enforce_read_only,
            )

        # Extract column names
        columns = [col.get('name') for col in results_response.get('ColumnMetadata', [])]

        # Extract rows
        rows = [
            [RedshiftDataModel.cell_value(cell) for cell in record]
            for record in results_response.get('Records', [])
        ]

        query_result = {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows),
            'query_id': query_id,
        }

        logger.info(f'Query executed successfully: {query_id}, returned {len(rows)} rows')
        return query_result

    except Exception as e:
        logger.debug(f'Query failed on cluster {cluster_identifier}: {str(e)}')
        raise
