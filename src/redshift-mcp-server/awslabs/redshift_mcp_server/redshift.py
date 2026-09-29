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
    MAX_RESULT_PAGES,
    QUERY_LONG_POLL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
)
from awslabs.redshift_mcp_server.models import (
    RedshiftCluster,
    RedshiftDataModel,
)
from awslabs.redshift_mcp_server.settings import (
    max_result_rows,
    session_keepalive,
)
from awslabs.redshift_mcp_server.sql_guard import (
    assert_executable,
    may_commit_partway,
    might_write,
)
from awslabs.redshift_mcp_server.transactions import (
    NamedTransaction,
    transaction_manager,
)
from botocore.exceptions import BotoCoreError, ClientError
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

# Cluster, as `_canonical_cluster` names it, to the moment the batch action was last seen denied
# on it, which holds the compatibility path in place without paying a denied call per statement.
# A cluster believed permitted is absent rather than present with a null. Keyed by cluster
# because the action takes resource-level permissions, so a denial on one says nothing about
# another.
_no_batch_since: dict[str, float] = {}

# Refusals for what the compatibility path will not carry, kept together so they stay consistent
# with each other. A transaction cannot be grouped by one statement per call. A write is declined
# for a different reason: this path keeps the contract of the release before read-write mode,
# which served reads only, so it refuses writes at every access mode.
#
# Both are also sent from the latch, which can be up to FALLBACK_NO_BATCH_REPROBE old, so they say
# when the denial was seen and when a grant takes effect. Worded as current, an operator who had
# just granted the action was told the credentials lack it and to grant it.
_FALLBACK_NO_BATCH_REFUSES_WRITE = (
    'Writes need redshift-data:BatchExecuteStatement, which was denied to the current '
    f'credentials on this cluster within the last {FALLBACK_NO_BATCH_REPROBE} seconds. Without '
    'it the server serves reads only, whatever the access mode. Granting the action restores '
    f'writes in read-write mode within {FALLBACK_NO_BATCH_REPROBE} seconds; in read-only mode '
    'this statement is refused either way.'
)

_FALLBACK_NO_BATCH_REFUSES_TRANSACTION = (
    'Named transactions need redshift-data:BatchExecuteStatement, which was denied to the '
    f'current credentials on this cluster within the last {FALLBACK_NO_BATCH_REPROBE} seconds. '
    'Without it each statement runs on its own connection, so there is nothing to group. Reads '
    'still work where redshift-data:ExecuteStatement is granted; a grant of the batch action '
    f'takes effect within {FALLBACK_NO_BATCH_REPROBE} seconds.'
)


def _canonical_cluster(cluster_info: RedshiftCluster) -> str:
    """Name one cluster the same way however the caller addressed it.

    What this server keys per cluster - open transactions, the per-target cap, the batch-denial
    latch - has to agree on which cluster that is. Keyed on the caller's arguments, a name given
    with and without its `cluster_type` was two clusters: one name held two live transactions on
    one cluster and database, the cap counted each separately, and a commit could reach only one
    of them while the other held its locks until its session timed out.

    Args:
        cluster_info: The resolved cluster.

    Returns:
        The identifier with its type after it. The type is part of it because the two AWS
        namespaces are separate, so a provisioned cluster and a workgroup can share a name. Shown
        in errors, so not written as `<type>:<identifier>`, which looks like an identifier to pass
        back.
    """
    return f'{cluster_info.identifier} ({cluster_info.type})'


# --- Submitting a batch ---


async def _execute_batch(
    cluster_info: RedshiftCluster,
    database_name: str,
    sqls: list[str],
    session_sink: list[str] | None = None,
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
        database_name: The database name.
        sqls: The statements to run, in order, on one connection.
        session_sink: Appended with the session id as soon as one is minted, so a caller can
            end it even when the batch then fails and never returns it.
        settled_sink: Appended with the batch id as soon as it is seen to have finished, so a
            caller can tell a batch that finished from one this call did not see finish.
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
            request_params['ClusterIdentifier'] = cluster_info.identifier
        elif cluster_info.type == 'serverless':
            request_params['WorkgroupName'] = cluster_info.identifier
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

    # Accepted, so the action is permitted on this cluster now, whichever call latched a denial.
    # Left latched, every write and transaction there was refused as denied until the re-probe,
    # though the grant had been restored.
    _no_batch_since.pop(_canonical_cluster(cluster_info), None)

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
            # because the batch has concluded: no further statement in it will run, and no
            # failure from here on can undo what did. Whether every statement succeeded is a
            # separate question - a FAILED batch had one fail, and one refused at the connection
            # ran none - which is why only FINISHED fills `settled_sink`. Filled after that call
            # instead, a throttled describe would look to the caller like a batch this call never
            # saw conclude. One flag for both sinks, and set on any terminal status rather than on
            # FINISHED, because the re-check below brings a settled statement back through here
            # a second time.
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


# --- Reading a result set ---


async def _read_result(statement_id: str) -> dict:
    """Read a finished statement's result set, following the service's paging.

    GetStatementResult answers one page and a NextToken while records remain. Read once, a
    result longer than a page reached the caller as though it were the whole answer: rows were
    missing and `row_count` reported the page as the total, with nothing to say so.

    A result over MAX_RESULT_ROWS is refused rather than returned whole or cut short; the first
    page reports the whole result's size, so the refusal costs one page. The statement has run by
    then, and the callers handle that as any failure after the statement: `_report_write_outcome`
    outside a transaction, `_report_staged_statement` and `_forget_closed_transaction` inside
    one, while `_begin_transaction` rolls back the transaction it was opening.

    The paging is bounded too, because a loop that never ends is worse than any answer: it
    holds the transaction's lock while it spins, so the name can never be reached again, and
    `_reap_expired` skips a transaction in use, so it holds a slot against the per-target cap
    forever. Two bounds, because a token that repeats is the shape a stuck service actually
    returns and catching it costs one page, where MAX_RESULT_PAGES catches every other shape.

    Says nothing about retrying. Whether a retry is safe depends on what the statement was and
    where it ran, which only its callers know, and they append what this raises to their own
    advice - so a retry told here landed after `_report_staged_statement` and
    `_report_write_outcome` had said not to, and an agent following the last line committed a
    second copy.

    Args:
        statement_id: The statement whose result to read.

    Returns:
        The first page, with every page's records concatenated into `Records` and its
        `NextToken` removed.

    Raises:
        ToolError: If the result has more rows than MAX_RESULT_ROWS, or the paging does not end -
            the same page token twice, or more pages than MAX_RESULT_PAGES.
    """
    cap = max_result_rows()
    data_client = client_manager.redshift_data_client()
    first = await asyncio.to_thread(data_client.get_statement_result, Id=statement_id)

    records = list(first.get('Records', []))
    total = first.get('TotalNumRows')
    if max(len(records), total or 0) > cap:
        raise _over_row_cap(cap, total)
    # Popped: the merged result is the whole answer, and the token would say more remains.
    token = first.pop('NextToken', None)
    seen = {token}
    while token:
        if len(seen) > MAX_RESULT_PAGES:
            raise ToolError(
                f'Reading this result did not end: more than {MAX_RESULT_PAGES} pages, '
                f'{len(records)} rows so far. What was read is discarded rather than returned as '
                f'the whole result.'
            )
        page = await asyncio.to_thread(
            data_client.get_statement_result, Id=statement_id, NextToken=token
        )
        records.extend(page.get('Records', []))
        # Counted as well, for a first page that did not report the total.
        if len(records) > cap:
            raise _over_row_cap(cap, total)
        token = page.get('NextToken')
        if token in seen:
            raise ToolError(
                f'Reading this result did not advance: the service repeated a page token after '
                f'{len(records)} rows. What was read is discarded rather than returned as the '
                f'whole result.'
            )
        seen.add(token)

    return {**first, 'Records': records}


def _over_row_cap(cap: int, total: int | None) -> ToolError:
    """Build the refusal for a result larger than MAX_RESULT_ROWS.

    Names how to shape a result that fits, but not whether to run anything again, for the reason
    `_read_result` gives.

    Args:
        cap: The configured MAX_RESULT_ROWS.
        total: The result's size as the service reported it, or None when it did not. Quoted
            only when over the cap; a refusal made on the rows counted would otherwise state a
            size under the limit.

    Returns:
        The error to raise.
    """
    size = f'{total} rows' if total is not None and total > cap else f'more than {cap} rows'
    return ToolError(
        f'The result has {size}, over the MAX_RESULT_ROWS limit of {cap}, so none of it is '
        f'returned. In execute_query, a LIMIT, a narrower predicate or an aggregate keeps a '
        f'result within the limit; the operator can raise MAX_RESULT_ROWS.'
    )


# --- Running one statement ---
# One shared helper and the three entry points that use it. Each turns a caller's statement into
# a batch: standalone with the read-only wrapper around it, or on a named transaction's session
# with a closer after it.


async def _execute_batch_for_statement(
    cluster_info: RedshiftCluster,
    database_name: str,
    sqls: list[str],
    caller_index: int | None,
    session_sink: list[str] | None = None,
    settled_sink: list[str] | None = None,
    terminal_sink: list[str] | None = None,
    parameters: list[dict] | None = None,
    session_id: str | None = None,
    session_keepalive: int | None = None,
) -> tuple[dict, str, str | None]:
    """Execute a batch on one statement's behalf and return that statement's result.

    Args:
        cluster_info: Cluster information model.
        database_name: The database name.
        sqls: The statements to run, in order, on one connection.
        caller_index: Index of the caller's statement in `sqls`, or None when the batch
            carries none of the caller's SQL, as a bare COMMIT does.
        session_sink: Appended with the session id as soon as one is minted, so a caller can
            end it even when the batch then fails and never returns it.
        settled_sink: Appended with the batch id once it is seen to finish with every statement
            succeeded, so a caller can tell a failure after the batch, reading its result, from
            a failure in it.
        terminal_sink: Appended with the batch id once it reached any terminal status, so a
            caller can tell a batch that failed from one this call stopped watching.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        session_id: Session to run on, for a statement inside a transaction.
        session_keepalive: Idle timeout to mint a session with, when opening a transaction.

    Returns:
        Tuple of the caller statement's result as `_read_result` returns it, empty when there
        is none; that statement's id, or the batch's when it carries none of the caller's SQL;
        and the session the batch ran on when one was minted.

    Raises:
        ToolError: If a statement fails or the batch times out.
    """
    batch = await _execute_batch(
        cluster_info=cluster_info,
        database_name=database_name,
        sqls=sqls,
        session_sink=session_sink,
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
        results_response = await _read_result(query_id)
    else:
        results_response = {'Records': [], 'ColumnMetadata': []}

    return results_response, query_id, batch.get('SessionId')


async def execute_standalone_statement(
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    enforce_read_only: bool = True,
    cluster_type: str | None = None,
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
    It also runs when the caller's statement fails, since a batch in this mode carries on past
    a failed statement, so a failure cannot leave a transaction open.

    While the batch action is latched as denied on the cluster there is neither batch nor
    wrapper: a read runs alone on the compatibility path, and anything `might_write` flags is
    refused before it is sent.

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
        cluster_type: `provisioned` or `serverless`, needed only when the identifier names both.

    Returns:
        Tuple of the statement's result as `_read_result` returns it, and its query_id.

    Raises:
        ToolError: If the cluster is unknown, a statement fails, the batch times out, or a write
            meets the batch-denial latch.
    """
    # Validate the statement with the SQL guard before doing any work.
    assert_executable(sql, enforce_read_only=enforce_read_only)

    cluster_info = await clusters.resolve_cluster(cluster_identifier, cluster_type)
    cluster = _canonical_cluster(cluster_info)

    if not _no_batch_active(cluster):
        sqls = [_APP_NAME_SQL]
        if enforce_read_only:
            sqls.append('BEGIN READ ONLY')
        caller_index = len(sqls)
        sqls.append(sql)
        if enforce_read_only:
            sqls.append('ROLLBACK')

        # Without the wrapper nothing discards a statement this call stops watching, so an
        # unwrapped write that never came back may still land - and one seen to finish has
        # landed, however this call then fails.
        settled: list[str] = []
        terminal: list[str] = []

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                settled_sink=settled,
                terminal_sink=terminal,
                parameters=parameters,
            )
            return results_response, query_id
        except Exception as e:
            if not (isinstance(e, ClientError) and _is_no_batch(e)):
                _report_write_outcome(sql, enforce_read_only, settled, terminal, e)
                raise
            # Reported as refused, where every other refusal is hedged. A denial of the batch
            # action is the steady state of a principal never granted it - the case this path
            # exists for - so a hedge would tell every such caller, on every re-probe, that a
            # write the service almost certainly refused may have landed. The cost is one race: a
            # write an earlier retry attempt carried, with the grant revoked before the next
            # attempt of the same call. A read runs again below either way, which is harmless.
            _latch_no_batch(e, cluster)

    if might_write(sql):
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_WRITE)

    # A recognized read cannot write, so it needs no wrapper and can go on its own.
    return await _execute_statement_fallback_no_batch(
        cluster_info=cluster_info,
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
    cluster_type: str | None = None,
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
        cluster_type: `provisioned` or `serverless`, needed only when the identifier names both.

    Returns:
        Tuple of the result of `sql` as `_read_result` returns it, and its query_id; an empty
        result and the batch's id when no statement was given.

    Raises:
        ToolError: If the name is already open, the target is at its cap, the cluster is
            unknown, or a statement fails.
    """
    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    cluster_info = await clusters.resolve_cluster(cluster_identifier, cluster_type)
    cluster = _canonical_cluster(cluster_info)

    if _no_batch_active(cluster):
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION)

    transaction = transaction_manager.open(cluster, database_name, name)

    sqls = [_APP_NAME_SQL, 'BEGIN READ ONLY' if enforce_read_only else 'BEGIN']
    caller_index = None
    if sql is not None:
        caller_index = len(sqls)
        sqls.append(sql)

    # A batch that mints a session and then fails leaves that session alive and holding an
    # aborted transaction. The id never reaches the return value in that case, so it is
    # collected here and rolled back below.
    opened_session: list[str] = []
    # Filled once the batch is seen to conclude, which is what says its statement is not still
    # running when this call fails.
    terminal: list[str] = []
    attached = False
    rolled_back = False

    try:
        async with transaction_manager.holding(transaction):
            try:
                results_response, query_id, session_id = await _execute_batch_for_statement(
                    cluster_info=cluster_info,
                    database_name=database_name,
                    sqls=sqls,
                    caller_index=caller_index,
                    session_sink=opened_session,
                    terminal_sink=terminal,
                    parameters=parameters,
                    session_keepalive=session_keepalive(),
                )
            except Exception as e:
                # Whether the batch is known to have ended: seen to conclude, or proved ended by
                # the rollback below finishing on its session, since a session refuses a submit
                # while it runs a statement.
                ended = bool(terminal)
                # The transaction never opened, or opened and then failed. Either way a
                # session that did get minted has to be ended rather than left to idle out
                # holding an aborted transaction. The name is released by the `finally`.
                if opened_session:
                    if await _rollback_lost_transaction(
                        cluster_info, database_name, opened_session[0]
                    ):
                        ended = True
                    rolled_back = True
                if isinstance(e, ClientError) and _is_no_batch(e):
                    _latch_no_batch(e, cluster)
                    raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION) from e
                if isinstance(e, (ToolError, ClientError, BotoCoreError)):
                    # Raised bare, it read as a failure of the first statement only, and a caller
                    # took the transaction for open. Anything else is a defect, left bare so its
                    # text is withheld, as `server._tool_failed` withholds it. A caller's
                    # statement not known to have ended may still be running and holding its
                    # locks, so a retry is told it may wait, as `_report_abandoned_transaction`
                    # tells one in a transaction. Without one, nothing is: BEGIN takes no locks.
                    running = (
                        ' Its statement may still be running, and a retry may wait on it.'
                        if sql is not None and not ended
                        else ''
                    )
                    raise ToolError(f'Transaction {name!r} was not opened.{running} {e}') from e
                raise

            if session_id is None:
                # A batch carrying SessionKeepAliveSeconds always mints a session, so this
                # only happens if that stops holding. Without the id there is no way to reach
                # the transaction again, so the name is refused; a session the submit named is
                # rolled back below, and one it did not is left to its idle timeout.
                raise ToolError(
                    f'Transaction {name!r} could not be opened: the Data API returned no session.'
                )

            transaction.attach(session_id)
            attached = True
    finally:
        if not attached:
            # Reached by every way this can end without an open transaction, including
            # cancellation. Cancellation is a BaseException, so the handler above never sees it.
            transaction_manager.forget(transaction)
            if opened_session and not rolled_back:
                # Freed without ending the session, the name could be opened again while the old
                # session still held its transaction and locks, for up to SESSION_KEEPALIVE. A
                # task being torn down cannot await its own cleanup, so the rollback is detached;
                # it swallows and logs its own failures, and carries the drain keepalive with it.
                logger.warning(
                    f'Transaction {transaction.key} ended before it opened; rolling back the '
                    f'session it minted, {opened_session[0]}'
                )
                asyncio.ensure_future(  # noqa: RUF006 - deliberately not awaited
                    _rollback_lost_transaction(cluster_info, database_name, opened_session[0])
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
    cluster_type: str | None = None,
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
        cluster_type: `provisioned` or `serverless`, needed only when the identifier names both.

    Returns:
        Tuple of the result of `sql` as `_read_result` returns it, and its query_id; an empty
        result and the batch's id when no statement was given.

    Raises:
        ToolError: If no transaction is open under that name, or a statement fails.
    """
    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    # Before everything keyed per cluster, because the caller's arguments are not the key: see
    # `_canonical_cluster`. Answered from the stored discovery, so the common case costs nothing.
    cluster_info = await clusters.resolve_cluster(cluster_identifier, cluster_type)
    cluster = _canonical_cluster(cluster_info)

    # Sent whatever the batch latch says. The latch can be another call's and stale, the grant
    # restored since: refused on it, a COMMIT that would have landed was dropped, and a statement
    # was refused with its transaction still open and the caller not told. A denial that is real
    # reaches the batch path below, which releases the name.
    transaction = transaction_manager.get(cluster, database_name, name)

    sqls = [] if sql is None else [sql]
    caller_index = None if sql is None else 0
    if closer is not None:
        sqls.append(closer)

    # A closer that has already run ends the transaction whatever happens next, so anything
    # raised after this is filled cannot be treated as though the transaction survived.
    settled: list[str] = []
    # Filled on any terminal status, which is what separates a batch that concluded badly from one
    # this call stopped watching: `settled` is empty for both.
    terminal: list[str] = []

    async with transaction_manager.holding(transaction):
        session_id = transaction.session()

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                settled_sink=settled,
                terminal_sink=terminal,
                parameters=parameters,
                session_id=session_id,
                session_keepalive=_SESSION_DRAIN if closer is not None else session_keepalive(),
            )
        except Exception as e:
            outcome = _transaction_outcome(closer, settled, terminal)
            if isinstance(e, ClientError) and _is_no_batch(e):
                # A denial comes from the submit, so nothing in the batch was seen to run. It is
                # latched before anything raises: left unlatched, the next standalone or opening
                # call on the cluster paid a denied batch call before latching. Here it means the
                # grant was revoked after the transaction opened, not the steady state the
                # standalone path reports as refused, so a closer it may follow is reported below
                # as unconfirmed. As the denial alone, a durable COMMIT an earlier attempt carried
                # read as work discarded for want of the grant.
                _latch_no_batch(e, cluster)
                if closer is None:
                    # The transaction stays open on the cluster but is now unreachable, so drop
                    # the name and let its idle timeout end it. Told only that transactions need
                    # the action, the caller would grant it and look for a transaction that this
                    # call had already given up on.
                    transaction_manager.forget(transaction)
                    raise ToolError(
                        f'{BATCH_ACTION} was denied partway through {name!r}, which can no '
                        f'longer be reached. The name is released here and its session ends when '
                        f'it goes idle; anything it had not committed is discarded. Reads still '
                        f'work where redshift-data:ExecuteStatement is granted; grant the batch '
                        f'action to use transactions again.'
                    ) from e
            if closer is not None and outcome in (_CLOSER_RAN, _CLOSER_UNKNOWN):
                # Seen to finish, the closer stands whatever the error says; never seen to end, the
                # service may hold it. Either way the name goes, or the caller could roll back
                # work already committed and be told that worked.
                _forget_closed_transaction(transaction, closer, e, ran=outcome == _CLOSER_RAN)
            if outcome == _STATEMENT_RAN:
                # The reaper measures idleness from the last touch, so left at the stamp this
                # statement started from, one that finished after running longer than
                # SESSION_KEEPALIVE made the transaction look abandoned the moment the lock was
                # released, and the next open on this target reaped one whose session the service
                # was still holding. Safe only here: the service restarts its own idle clock when
                # the batch finishes, which is what makes this stamp no earlier than the
                # service's.
                transaction.touch()
                _report_staged_statement(transaction, e)
            _report_abandoned_transaction(
                transaction, cluster_info, database_name, session_id, e, concluded=bool(terminal)
            )
        except BaseException:
            # Cancellation, which is not an Exception and so does not reach the arm above. There
            # is no caller left to tell, so what became of the closer is recorded in the log and
            # the cancellation is left to propagate.
            outcome = _transaction_outcome(closer, settled, terminal)
            if outcome == _CLOSER_RAN:
                logger.warning(
                    f'Transaction {name!r} was cancelled after its {closer} ran, which stands'
                )
                transaction_manager.forget(transaction)
                raise
            if outcome == _CLOSER_UNKNOWN:
                # No rollback here: the service may hold the closer and this call never saw it
                # end, so a COMMIT may be applying right now. Keyed on `settled` alone, this arm
                # fired one and recorded a cancellation, where the arm above calls the same state
                # unknown. Worded as `_forget_closed_transaction` words it, since it is the same
                # state: a ROLLBACK ends the same way whatever became of it, a COMMIT does not.
                logger.warning(
                    f'Transaction {name!r} was cancelled without its {closer} confirmed, and is '
                    f'discarded either way'
                    if closer == 'ROLLBACK'
                    else f'Transaction {name!r} was cancelled without its {closer} confirmed, '
                    f'which the service may hold and may have applied'
                )
                transaction_manager.forget(transaction)
                raise
            if not terminal:
                # No rollback while the submit may still be in flight: the worker thread is not
                # cancelled with this call. A rollback that landed first ended the transaction
                # block, and the statement landing after it ran on the session in autocommit -
                # outside `BEGIN READ ONLY`, and committed. Left alone, the statement runs inside
                # a transaction nothing will commit, and the session's idle timeout discards it.
                logger.warning(
                    f'Transaction {transaction.key} was cancelled with its statement unconfirmed; '
                    f'its session ends when it goes idle'
                )
                transaction_manager.forget(transaction)
                raise
            logger.warning(f'Transaction {transaction.key} was cancelled')
            _abandon_transaction(transaction, cluster_info, database_name, session_id)
            raise

        if closer is not None:
            transaction_manager.forget(transaction)
        else:
            # Still open, and just used, so its idle clock starts again from here.
            transaction.touch()

    return results_response, query_id


# --- What a failed call left behind ---
# Reached from the failure arms above. One reading of how far the batch got, then the ways a
# transaction can end: dropped with its outcome reported, dropped and rolled back, kept because
# its statement's work is still staged in it, or - outside a transaction, where there is no name
# to drop - reported as applied or as possibly applied.

# What a failed call leaves behind, decided by how far its batch got rather than by which
# exception arrived.
_CLOSER_RAN = 'closer_ran'
_CLOSER_UNKNOWN = 'closer_unknown'
_ABORTED = 'aborted'
_STATEMENT_RAN = 'statement_ran'


def _report_write_outcome(
    sql: str,
    enforce_read_only: bool,
    settled: list[str],
    terminal: list[str],
    error: Exception,
) -> None:
    """Raise over `error` when a write outside a transaction was applied, or may have been.

    Outside a transaction there is no name to drop and no session to end, so the only thing a
    failure can leave behind is the statement itself. Under the read-only wrapper that costs
    nothing: the statement runs inside `BEGIN READ ONLY`, so it cannot have written, unless the
    `BEGIN` itself failed, which nothing known triggers. Without it the batch autocommits, and
    abandoning the poll cancels nothing: reported as a bare timeout, a write that was still
    committing read as one that had not happened, and a caller who retried wrote twice.

    Args:
        sql: The caller's statement, to tell a write from a read.
        enforce_read_only: Whether the wrapper was applied, which decides whether it can persist.
        settled: Non-empty once the batch was seen to finish, so the write is durable.
        terminal: Non-empty once the batch was seen to conclude, however it concluded.
        error: What the call failed with, kept as the cause.

    Raises:
        ToolError: If the statement was applied, or may have been.
    """
    if enforce_read_only or not might_write(sql):
        return

    if settled:
        # The batch finished and the failure came after it - the confirming describe, or reading
        # the result. Silenced along with a batch that concluded badly, because `terminal` is
        # filled for both, this reached the caller as a bare AWS error over a durable write.
        raise ToolError(
            f'The statement finished and was applied, and this call then failed while reading '
            f'its outcome. It runs with autocommit, so do not retry it. {error}'
        ) from error

    if terminal:
        # Concluded as something other than finished, so nothing persisted - unless the
        # statement commits inside itself. Reported bare, a procedure that committed part of its
        # work and then failed read as one that had not run, and a retry applied that part twice.
        if not may_commit_partway(sql):
            return
        # Conditional, because a batch refused at the connection fails with the procedure never
        # started, and nothing here tells the two apart.
        raise ToolError(
            f'A procedure can commit part of its work before it fails, so if this one started, '
            f'some of it may have been applied. Check the data before retrying. {error}'
        ) from error

    # Nothing came back. What the submit raised is no evidence either way - see
    # `_transaction_outcome` - so the caller is told to look rather than left to assume.
    raise ToolError(
        f'This call did not see the statement finish and cannot tell whether it ran, so it may '
        f'or may not have been applied, and it may still be running. It runs with autocommit and '
        f'nothing here cancels it: once SYS_QUERY_HISTORY no longer shows it running, check the '
        f'data before retrying. {error}'
    ) from error


def _transaction_outcome(closer: str | None, settled: list[str], terminal: list[str]) -> str:
    """Say what a failed call left of its transaction, from how far its batch got.

    What happened is one fact for the failure arms above, whatever each then does about it, and
    reading it out of the sinks at each arm is what let one arm answer a state differently from
    another. Decided here once instead.

    Only these sinks are evidence. What a failed submit raised is not: the client makes up to
    CLIENT_RETRIES attempts and raises the last one's error, so an attempt that transmitted and
    lost its response can be followed by one that fails at the connection, at signing, or with the
    service refusing it - a limit like ActiveStatementsExceededException can even be raised because
    the attempt that landed is holding that limit. On a transaction's session the refusal can be
    'Session is not available': measured, a session still running the attempt that landed answers
    that, even to a repeat of its ClientToken, just as a session that is gone does. So a batch
    with no answer recorded is taken as one that may have run, whatever it raised. The opposite
    mistake is the expensive one: a caller told nothing ran retries a write already durable, or a
    statement already in their transaction.

    Args:
        closer: COMMIT or ROLLBACK when the call was ending the transaction, else None.
        settled: Non-empty once the batch was seen to finish.
        terminal: Non-empty once the batch was seen to conclude, however it concluded.

    Returns:
        `_ABORTED` when the transaction cannot survive this call; `_CLOSER_RAN` or
        `_STATEMENT_RAN`, by whether a closer was in the batch, when it finished and the call
        failed after it; `_CLOSER_UNKNOWN` when a closer may have reached the cluster and was
        never watched to a conclusion.
    """
    # Checked first, and without regard to `closer`: a batch that concluded badly ends the
    # transaction, and says a closer in it did not apply.
    if terminal and not settled:
        return _ABORTED

    if settled:
        return _CLOSER_RAN if closer is not None else _STATEMENT_RAN

    # No answer. A closer that may have applied is its own outcome, because its effect would
    # persist. A statement's would not: the transaction is never committed, so whatever it staged
    # is discarded either way, and all that is left to decide is that the name cannot stay - kept,
    # the caller would retry a statement that may already be in the transaction and commit both.
    return _CLOSER_UNKNOWN if closer is not None else _ABORTED


def _forget_closed_transaction(
    transaction: NamedTransaction, closer: str, error: Exception, *, ran: bool
) -> NoReturn:
    """Drop a name whose closer this call put in a batch, and report what is known of it.

    Either way the name has to go, or the caller could roll back work that is already
    committed and be told it succeeded. But the failure still has to be reported, and
    reporting it bare would say a write failed when it landed, and leave the next call on the
    name to be told it was released after a failed statement.

    What differs is how much is known. Seen to finish, the `COMMIT` is durable or the `ROLLBACK`
    has discarded, so the closer stands. Never seen to conclude, only a `COMMIT` is in doubt: it
    may be applying right now, and this call cannot tell that from one the service never
    received. A `ROLLBACK` is not, because every way it can have gone ends the same - applied, or
    still queued, or never sent at all, since the name is dropped here so nothing can commit the
    transaction and the session's idle timeout ends it. Told it might have applied, the caller was
    sent to inspect data over a state that was already settled, and could read it as their writes
    having persisted.

    Args:
        transaction: The transaction to drop.
        closer: The `COMMIT` or `ROLLBACK` this call put in the batch.
        error: What failed.
        ran: Whether the closer was seen to finish.

    Raises:
        ToolError: Always, carrying both facts.
    """
    name = transaction.name

    if ran:
        logger.warning(f'Transaction {name!r} failed after its {closer} ran: {error}')
        outcome = (
            f'ran its {closer}, which stands, and then failed while its result was being read'
        )
    elif closer == 'ROLLBACK':
        logger.warning(f'Transaction {name!r} failed with its ROLLBACK unconfirmed: {error}')
        outcome = (
            'failed before its ROLLBACK was confirmed, and is discarded either way: nothing it '
            'staged can be committed now, and its session ends when it goes idle. Its statements '
            'may still be running, and a retry may wait on them'
        )
    else:
        # Still running, a COMMIT reads as not applied and can apply after this reply, so a
        # caller who looked at once and redid the work applied it twice.
        logger.warning(f'Transaction {name!r} failed with its {closer} unconfirmed: {error}')
        outcome = (
            f'was never seen to finish its {closer}, which may have applied, or may still be '
            f'running and apply after this reply. Once SYS_QUERY_HISTORY no longer shows its '
            f'statements running, query the data to find out whether it applied'
        )

    transaction_manager.forget(transaction)
    raise ToolError(f'Transaction {name!r} {outcome}. {error}') from error


def _report_staged_statement(transaction: NamedTransaction, error: Exception) -> NoReturn:
    """Report a statement that ran, over the failure that came after it.

    The batch finished, so the transaction is still open and the caller's; only reading the
    outcome failed. Reported bare, the caller read the transport error as the statement not having
    happened, ran a write again, and committed two copies - the same harm `_report_write_outcome`
    raises over outside a transaction. Worded for both kinds, because a read staged nothing and
    running it again is the only way to get its rows. A FETCH is named on its own: run again, it
    returns the rows after the ones this call lost, as if they were the first.

    Args:
        transaction: The transaction the statement ran in, which stays open.
        error: What failed after it, kept as the cause.

    Raises:
        ToolError: Always, over `error`.
    """
    raise ToolError(
        f'The statement ran and transaction {transaction.name!r} is still open; this call then '
        f'failed while reading its outcome. Do not run a write again: its changes to the database '
        f'are staged, to commit or roll back, and what it wrote outside the database, such as an '
        f'UNLOAD to S3, is already there. A FETCH has already moved its cursor past the rows it '
        f'read, so running it again returns the rows after them; CLOSE and DECLARE the cursor to '
        f'reread them. A read is safe to run again. {error}'
    ) from error


def _report_abandoned_transaction(
    transaction: NamedTransaction,
    cluster_info: RedshiftCluster,
    database_name: str,
    session_id: str,
    error: Exception,
    *,
    concluded: bool,
) -> NoReturn:
    """Drop a transaction this call cannot leave open, and say so over the error that caused it.

    Reported bare, the name was gone and the caller was not told: their next statement on it
    answered 'no open transaction', and they had no way to know whether to inspect the data or
    simply open it again. Its siblings all name what became of the transaction, and this is the
    same obligation.

    The rollback is best effort - a statement still holding the session refuses it, and the
    session's idle timeout ends the transaction instead - so what is claimed is what holds either
    way: the transaction is never committed, so nothing it staged can persist. A batch never seen
    to conclude may still be running, and a retry may wait on it, so that is said too. Said of a
    batch seen to fail, it told the caller to hold off over a statement that had already ended.

    Args:
        transaction: The transaction to drop.
        cluster_info: Cluster information model.
        database_name: The database the transaction runs in.
        session_id: The session the transaction runs on.
        error: What failed, kept as the cause.
        concluded: Whether the batch was seen to reach a terminal status.

    Raises:
        ToolError: Always, over `error`.
    """
    _abandon_transaction(transaction, cluster_info, database_name, session_id)
    running = (
        '' if concluded else 'Its statement may still be running, and a retry may wait on it. '
    )
    raise ToolError(
        f'Transaction {transaction.name!r} is released and nothing it staged can be committed. '
        f'{running}Open it again if the work still applies. {error}'
    ) from error


def _abandon_transaction(
    transaction: NamedTransaction,
    cluster_info: RedshiftCluster,
    database_name: str,
    session_id: str,
) -> None:
    """Drop a transaction's name and end the session it was running on.

    The rollback is not awaited. Awaiting it would put an await between dropping the name and
    ending the session, and a cancellation there leaves the session alive holding an aborted
    transaction and its locks. Nothing waits on the outcome either way: the helper swallows and
    logs its own failures, and carries the drain keepalive with it.

    Args:
        transaction: The transaction to drop.
        cluster_info: Cluster information model.
        database_name: The database the transaction runs in.
        session_id: The session the transaction runs on.
    """
    transaction_manager.forget(transaction)
    asyncio.ensure_future(  # noqa: RUF006 - see the docstring
        _rollback_lost_transaction(cluster_info, database_name, session_id)
    )


async def _rollback_lost_transaction(
    cluster_info: RedshiftCluster,
    database_name: str,
    session_id: str,
) -> bool:
    """Roll back a transaction this server is abandoning, whatever state it is in, best effort.

    A failure here leaves the transaction's fate as it was: the name is gone, so nothing can
    commit it, and the session's idle timeout ends it. No call will reach this session again -
    its name is gone, or is dropped by the caller on the way out - so the session is drained
    rather than left to idle.

    Args:
        cluster_info: Cluster information model.
        database_name: The database the transaction runs in.
        session_id: The session the transaction runs on.

    Returns:
        Whether the ROLLBACK finished. A session refuses a submit while it runs a statement, so a
        finished one also proves nothing else was running on the session when it was sent, which
        `_begin_transaction` reports on.
    """
    try:
        batch = await _execute_batch(
            cluster_info=cluster_info,
            database_name=database_name,
            sqls=['ROLLBACK'],
            session_id=session_id,
            session_keepalive=_SESSION_DRAIN,
        )
    except Exception as e:  # noqa: BLE001 - reported as not finished, which is all that is known
        logger.warning(f'Rollback of the aborted transaction on {session_id} failed: {e}')
        return False

    return batch.get('Status') == 'FINISHED'


# --- Fallback: no_batch ---
# Serves credentials denied redshift-data:BatchExecuteStatement by running one statement
# per call, which keeps the read-only contract of the release before named transactions.
# Everything tagged no_batch belongs to it, so the whole path can be deleted with its constants
# and tests once the action is universal - along with its uses above: the latch clear in
# `_execute_batch`, and the latch and denial checks in the three entry points.
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


def _no_batch_active(cluster: str) -> bool:
    """Report whether the no_batch fallback is in force for one cluster, consuming a due re-probe.

    Args:
        cluster: The cluster, as `_canonical_cluster` names it.

    Returns:
        True while the batch path is known denied on that cluster, and False once per
        FALLBACK_NO_BATCH_REPROBE seconds after that, so a granted policy is picked up
        without a restart.
    """
    since = _no_batch_since.get(cluster)

    if since is None:
        return False

    if time.monotonic() - since < FALLBACK_NO_BATCH_REPROBE:
        return True

    # Due for a probe. Clearing it first means a still-denied batch latches again, which is
    # what keeps the warning to one per re-probe window rather than one per statement.
    del _no_batch_since[cluster]
    return False


def _latch_no_batch(error: ClientError, cluster: str) -> None:
    """Record that the batch action is denied on one cluster, and name the grant that restores it.

    Kept per cluster because the action takes resource-level permissions: a principal can be
    denied it on one cluster and hold it on another, and a process-wide latch refused statements
    on the second that would have run.

    Args:
        error: The denial, quoted so the operator can see which principal was refused.
        cluster: The cluster the denial came from, as `_canonical_cluster` names it.
    """
    _no_batch_since[cluster] = time.monotonic()
    logger.warning(
        f'{BATCH_ACTION} is denied on {cluster}, so statements there now run one at a time: '
        'reads still work where redshift-data:ExecuteStatement is granted, writes and named '
        'transactions do not. Grant the action to restore them; the batch path is retried in '
        f'{FALLBACK_NO_BATCH_REPROBE}s. {error}'
    )


async def _execute_statement_fallback_no_batch(
    cluster_info: RedshiftCluster,
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
        database_name: The database to execute against.
        sql: The single statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        query_poll_interval: Polling interval in seconds.
        query_timeout: Maximum time in seconds to wait.
        query_long_poll: Data API WaitTimeSeconds, 1-30, or 0 to disable long polling.

    Returns:
        Tuple of the statement's result as `_read_result` returns it, and its id.

    Raises:
        ToolError: If the statement fails or does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()

    request_params: dict[str, str | int | list] = {'Sql': sql, 'Database': database_name}
    if cluster_info.type == 'provisioned':
        request_params['ClusterIdentifier'] = cluster_info.identifier
    elif cluster_info.type == 'serverless':
        request_params['WorkgroupName'] = cluster_info.identifier
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

    return await _read_result(statement_id), statement_id


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
                'sql is required, except when opening, committing or rolling back a transaction.'
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
    cluster_type: str | None = None,
) -> dict:
    """Execute a SQL statement against a Redshift cluster using the Data API.

    Without a transaction parameter the statement runs on its own connection and nothing
    carries over to the next call. A transaction parameter names a transaction the caller
    controls across calls, which holds a session open for as long as it stays open.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute against.
        sql: The SQL statement to execute. Required on its own and with `in_transaction`;
            optional with the other three.
        enforce_read_only: Whether to apply read-only protection. Defaults to True.
        begin_transaction: Open a transaction under this name and run `sql` inside it, if
            given. Fails when the name is already open.
        in_transaction: Run `sql` inside the transaction already open under this name.
        commit_transaction: Run `sql`, if given, then commit this transaction.
        rollback_transaction: Run `sql`, if given, then roll this transaction back.
        cluster_type: `provisioned` or `serverless`, needed only when the identifier names both.

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
                cluster_type=cluster_type,
            )
        elif action == 'begin_transaction':
            results_response, query_id = await _begin_transaction(
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                name=name,  # pyright: ignore[reportArgumentType] - set with the action
                sql=sql,
                enforce_read_only=enforce_read_only,
                cluster_type=cluster_type,
            )
        else:
            results_response, query_id = await _execute_statement_in_transaction(
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                name=name,  # pyright: ignore[reportArgumentType] - set with the action
                sql=sql,
                closer=_TRANSACTION_CLOSERS.get(action),
                enforce_read_only=enforce_read_only,
                cluster_type=cluster_type,
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
