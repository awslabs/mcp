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

"""AWS client management for Redshift MCP Server."""

import asyncio
import boto3
import functools
import os
import time
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
    CLIENT_USER_AGENT_NAME,
    COLUMNS_SQL,
    DATABASES_SQL,
    FALLBACK_NO_BATCH_REPROBE,
    MAX_OPEN_TRANSACTIONS_PER_TARGET_DEFAULT,
    QUERY_LONG_POLL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SCHEMAS_SQL,
    SESSION_KEEPALIVE_DEFAULT,
    SESSION_KEEPALIVE_MAX,
    TABLES_SQL,
)
from awslabs.redshift_mcp_server.models import (
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftDataModel,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.sql_guard import assert_executable, might_write
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from sqlglot import exp


def _sql_identifier(value: str) -> str:
    """Render a value as a Redshift SQL identifier, safely quoted and escaped."""
    return exp.to_identifier(value, quoted=True).sql(dialect='redshift')


# ClientError codes that indicate missing IAM permissions.
_ACCESS_DENIED = {'AccessDeniedException', 'UnauthorizedAccess', 'AccessDenied'}

# botocore's name for the batch call, as it appears on ClientError.operation_name. Used to tell
# a denial of the batch action from a denial of the two calls that settle and read it.
_BATCH_OPERATION = 'BatchExecuteStatement'

# Statement statuses the Data API does not move on from.
_TERMINAL_STATUSES = frozenset({'FINISHED', 'FAILED', 'ABORTED'})

# The statement that ends a transaction, per the parameter that asked for it.
_TRANSACTION_CLOSERS = {'commit_transaction': 'COMMIT', 'rollback_transaction': 'ROLLBACK'}

# Tags the connection with an application name.
_APP_NAME_SQL = f"SET application_name TO '{CLIENT_USER_AGENT_NAME}/{__version__}'"

# When BatchExecuteStatement was last denied, or None while it is believed permitted. Holds
# the compatibility path in place without paying a denied call per statement.
_no_batch_since: float | None = None

# Refusals for what the compatibility path will not carry, kept together so they stay consistent
# with each other. A transaction cannot be grouped by one statement per call. A write is declined
# for a different reason: this path keeps the contract of the release before read-write mode,
# which served reads only, so it refuses writes at every access mode.
_FALLBACK_NO_BATCH_REFUSES_WRITE = (
    'Writes need redshift-data:BatchExecuteStatement, which the current credentials are denied. '
    'Without it the server serves reads only, whatever the access mode. Grant the action to run '
    'anything else.'
)

_FALLBACK_NO_BATCH_REFUSES_TRANSACTION = (
    'Named transactions need redshift-data:BatchExecuteStatement, which the current '
    'credentials are denied. Without it each statement runs on its own connection, so there '
    'is nothing to group. Reads still work; grant the action to use transactions.'
)


def _resolve_int_env(
    name: str, default: int, *, minimum: int = 1, maximum: int | None = None
) -> int:
    """Read an integer setting from the environment, bounded.

    Falls back on the default for anything unusable rather than failing to start, since a
    mistyped timeout should not take the server down.

    Args:
        name: The environment variable to read.
        default: The value to use when it is unset or unusable.
        minimum: The smallest accepted value.
        maximum: The largest accepted value, unbounded when None.

    Returns:
        The configured value, or the default.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default

    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning(f'{name}={raw!r} is not an integer, using {default}')
        return default

    if value < minimum or (maximum is not None and value > maximum):
        bound = f'{minimum} to {maximum}' if maximum is not None else f'{minimum} or more'
        logger.warning(f'{name}={value} is outside the accepted {bound}, using {default}')
        return default

    return value


# Resolved on first use, not at import: this module is imported while the server is still
# running its own import block, before it has pointed the logger at LOG_FILE, so a warning
# raised here at import time would go to stderr and miss the file the operator is watching.
# No setting can change while the server runs, so resolving once is still right.
@functools.cache
def session_keepalive() -> int:
    """How long an open transaction may sit idle, in seconds.

    Returns:
        The configured idle timeout.
    """
    return _resolve_int_env(
        'SESSION_KEEPALIVE', SESSION_KEEPALIVE_DEFAULT, maximum=SESSION_KEEPALIVE_MAX
    )


@functools.cache
def max_open_transactions_per_target() -> int:
    """How many transactions one caller may hold open per cluster and database.

    Returns:
        The configured cap.
    """
    return _resolve_int_env(
        'MAX_OPEN_TRANSACTIONS_PER_TARGET', MAX_OPEN_TRANSACTIONS_PER_TARGET_DEFAULT
    )


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(
        self, config: Config, aws_region: str | None = None, aws_profile: str | None = None
    ):
        """Initialize the client manager."""
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self._redshift_client = None
        self._redshift_serverless_client = None
        self._redshift_data_client = None
        self._config = config

    def redshift_client(self):
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_client = session.client('redshift', config=self._config)
                logger.info(
                    f'Created Redshift client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift client: {str(e)}')
                raise

        return self._redshift_client

    def redshift_serverless_client(self):
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_serverless_client = session.client(
                    'redshift-serverless', config=self._config
                )
                logger.info(
                    f'Created Redshift Serverless client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Serverless client: {str(e)}')
                raise

        return self._redshift_serverless_client

    def redshift_data_client(self):
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_data_client = session.client('redshift-data', config=self._config)
                logger.info(
                    f'Created Redshift Data API client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Data API client: {str(e)}')
                raise

        return self._redshift_data_client


async def _resolve_cluster(cluster_identifier: str) -> RedshiftCluster:
    """Resolve a cluster identifier to its discovered cluster.

    Args:
        cluster_identifier: The cluster identifier to resolve.

    Returns:
        The matching RedshiftCluster model.

    Raises:
        ToolError: If no discovered cluster carries that identifier.
    """
    for cluster in await discover_clusters():
        if cluster.identifier == cluster_identifier:
            return cluster

    raise ToolError(
        f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
    )


def _transaction_key(cluster_identifier: str, database_name: str, name: str) -> str:
    """Build the map key that identifies one caller's transaction.

    Remote support will add the authenticated principal on the left, so that one caller
    cannot reach another's transaction. This is the only place that has to change.

    Args:
        cluster_identifier: The cluster the transaction runs on.
        database_name: The database the transaction runs in.
        name: The caller's name for the transaction.

    Returns:
        The map key.
    """
    return f'{cluster_identifier}:{database_name}:{name}'


def _transaction_target(cluster_identifier: str, database_name: str) -> str:
    """Build the target the open-transaction cap is counted against.

    Args:
        cluster_identifier: The cluster the transaction runs on.
        database_name: The database the transaction runs in.

    Returns:
        The target key.
    """
    return f'{cluster_identifier}:{database_name}'


class RedshiftTransactionManager:
    """Tracks the Data API session behind each open transaction.

    A session exists only while a transaction is open, so this holds every session the
    server owns. Nothing is pooled and nothing is reused: a statement outside a transaction
    mints no session at all.
    """

    def __init__(self, max_open_per_target: int | None = None):
        """Initialize the transaction manager.

        Args:
            max_open_per_target: How many transactions may be open at once per target. Left
                unset, the configured cap is read on first use.
        """
        self._transactions: dict[str, dict] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._generations: dict[str, int] = {}
        self._max_open_per_target = max_open_per_target

    def claim(self, key: str) -> tuple[asyncio.Lock, int]:
        """Get the lock that serializes one transaction, and the generation to check after.

        A SessionId is strictly serial: a second statement submitted while one is in flight
        is refused at submit, so every use of a session has to hold this lock.

        The generation exists because acquiring the lock is an await, and the name can change
        hands across it. A caller queued behind the holder would otherwise wake to find a
        different transaction under the same name and add its statement to that one. Capture
        the generation here, and pass it to `assert_current` once the lock is held.

        Args:
            key: The transaction key to lock on.

        Returns:
            The lock for that name, created on first use, and the generation it was taken at.
        """
        # No await between the get and the set, so lazy creation cannot interleave.
        existing = self._locks.get(key)
        if existing is None:
            existing = asyncio.Lock()
            self._locks[key] = existing
        return existing, self._generations.get(key, 0)

    def assert_current(self, key: str, generation: int, name: str) -> None:
        """Refuse to act on a name that changed hands while the lock was being acquired.

        Args:
            key: The transaction key.
            generation: The generation returned by `claim` before the await.
            name: The caller's name for the transaction, for the error message.

        Raises:
            ToolError: If the name was closed, or closed and reopened, in the meantime.
        """
        if self._generations.get(key, 0) != generation:
            raise ToolError(
                f'Transaction {name!r} closed while this statement was waiting for it. '
                f'Nothing ran. Open it again if the work still applies.'
            )

    def reserve(self, key: str, target: str, name: str) -> None:
        """Claim a name before opening its transaction.

        Claiming first means a duplicate name or an exhausted cap is refused before any work
        is done, and that two concurrent opens cannot both pass the cap check.

        Args:
            key: The transaction key to claim.
            target: The target the cap is counted against.
            name: The caller's name for the transaction, for the error message.

        Raises:
            ToolError: If the name is already open, or the target is at its cap.
        """
        if key in self._transactions:
            raise ToolError(
                f'Transaction {name!r} is already open. Use in_transaction to add a statement '
                f'to it, or commit or roll it back before opening it again.'
            )

        cap = (
            self._max_open_per_target
            if self._max_open_per_target is not None
            else max_open_transactions_per_target()
        )
        self._reap_expired(target)
        open_count = sum(1 for entry in self._transactions.values() if entry['target'] == target)
        if open_count >= cap:
            raise ToolError(
                f'Too many open transactions ({open_count}). Commit or roll one back before '
                f'opening another, or raise MAX_OPEN_TRANSACTIONS_PER_TARGET.'
            )

        self._transactions[key] = {
            'target': target,
            'session_id': None,
            'touched_at': time.monotonic(),
        }

    def _reap_expired(self, target: str) -> None:
        """Drop entries whose session the service has already ended.

        Redshift ends a session left idle for SESSION_KEEPALIVE seconds and says nothing about
        it. Without this, a caller who opens transactions and walks away holds the target's
        cap against everyone else until each dead name is touched and found gone.

        Args:
            target: The cluster and database whose entries to check.
        """
        keepalive = session_keepalive()
        now = time.monotonic()
        expired = [
            key
            for key, entry in self._transactions.items()
            if entry['target'] == target and now - entry['touched_at'] > keepalive
        ]

        for key in expired:
            logger.info(f'Reaped transaction {key}: idle past SESSION_KEEPALIVE={keepalive}s')
            self.forget(key)

    def touch(self, key: str) -> None:
        """Restart the idle clock on a transaction that was just used.

        Args:
            key: The transaction key that just ran a statement.
        """
        entry = self._transactions.get(key)
        if entry is not None:
            entry['touched_at'] = time.monotonic()

    def attach(self, key: str, session_id: str) -> None:
        """Record the session the Data API minted for a claimed transaction.

        Args:
            key: The claimed transaction key.
            session_id: The session the transaction runs on.
        """
        self._transactions[key]['session_id'] = session_id
        logger.info(f'Opened transaction {key} on session {session_id}')

    def session_id(self, key: str, name: str) -> str:
        """Get the session of an open transaction.

        Args:
            key: The transaction key to look up.
            name: The caller's name for the transaction, for the error message.

        Returns:
            The session the transaction runs on.

        Raises:
            ToolError: If no transaction is open under that name.
        """
        entry = self._transactions.get(key)
        if entry is None or entry['session_id'] is None:
            raise ToolError(
                f'No open transaction named {name!r}. It was never opened, was rolled back '
                f'after a failed statement, or expired after being idle.'
            )
        return entry['session_id']

    def forget(self, key: str) -> None:
        """Drop a transaction, whether it closed cleanly or was lost.

        The lock is kept. A caller may already be queued on it, and replacing it would leave
        that caller holding a lock nobody else respects. Bumping the generation is what tells
        it the name it waited for is gone.

        Args:
            key: The transaction key to drop.
        """
        if self._transactions.pop(key, None) is not None:
            logger.info(f'Closed transaction {key}')
        self._generations[key] = self._generations.get(key, 0) + 1


async def _execute_batch_for_statement(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sqls: list[str],
    caller_index: int | None,
    session_sink: list[str] | None = None,
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
        parameters=parameters,
        session_id=session_id,
        session_keepalive=session_keepalive,
    )

    sub_statements = batch['SubStatements']

    # One failed statement fails the batch, so a healthy batch means the caller's statement
    # and everything around it ran. A surrounding failure matters as much as the caller's
    # own: a failed BEGIN means the statement was never read-only, and a failed ROLLBACK
    # means what it did may not have been discarded.
    if batch['Status'] != 'FINISHED':
        # A statement that ran and failed carries the engine's message. When the connection
        # itself was refused nothing ran, every statement is ABORTED with a placeholder, and
        # only the batch carries the reason.
        failed = next((sub for sub in sub_statements if sub['Status'] == 'FAILED'), None)
        error = (failed or batch).get('Error', 'Unknown error')
        logger.error(f'Statement failed: {error}')
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


async def _execute_standalone_statement(
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

    cluster_info = await _resolve_cluster(cluster_identifier)

    if not _no_batch_active():
        sqls = [_APP_NAME_SQL]
        if enforce_read_only:
            sqls.append('BEGIN READ ONLY')
        caller_index = len(sqls)
        sqls.append(sql)
        if enforce_read_only:
            sqls.append('ROLLBACK')

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                parameters=parameters,
            )
            return results_response, query_id
        except ClientError as e:
            if not _is_no_batch(e):
                raise
            # Nothing ran, so the same statement can be retried below rather than failing
            # this call on a permissions problem the compatibility path can absorb.
            _latch_no_batch(e)

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
    if _no_batch_active():
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION)

    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    cluster_info = await _resolve_cluster(cluster_identifier)

    key = _transaction_key(cluster_identifier, database_name, name)
    target = _transaction_target(cluster_identifier, database_name)
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
            # The transaction never opened, or opened and then failed. Either way the name
            # must not linger, and a session that did get minted has to be ended rather than
            # left to idle out holding an aborted transaction.
            if opened_session:
                await _rollback_lost_transaction(
                    cluster_info, cluster_identifier, database_name, opened_session[0]
                )
            transaction_manager.forget(key)
            if isinstance(e, ClientError) and _is_no_batch(e):
                _latch_no_batch(e)
                raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION) from e
            raise

        if session_id is None:
            # A batch carrying SessionKeepAliveSeconds always mints a session, so this only
            # happens if that stops holding. Without the id there is no way to reach the
            # transaction again, so refuse the name and let the idle timeout end it.
            transaction_manager.forget(key)
            raise ToolError(
                f'Transaction {name!r} could not be opened: the Data API returned no session.'
            )

        transaction_manager.attach(key, session_id)

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
    if _no_batch_active():
        raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION)

    if sql is not None:
        assert_executable(sql, enforce_read_only=enforce_read_only, in_transaction=True)

    cluster_info = await _resolve_cluster(cluster_identifier)
    key = _transaction_key(cluster_identifier, database_name, name)

    sqls = [] if sql is None else [sql]
    caller_index = None if sql is None else 0
    if closer is not None:
        sqls.append(closer)

    lock, generation = transaction_manager.claim(key)
    async with lock:
        transaction_manager.assert_current(key, generation, name)
        session_id = transaction_manager.session_id(key, name)

        try:
            results_response, query_id, _ = await _execute_batch_for_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sqls=sqls,
                caller_index=caller_index,
                parameters=parameters,
                session_id=session_id,
                session_keepalive=session_keepalive(),
            )
        except ClientError as e:
            if _is_no_batch(e):
                # The transaction stays open on the cluster but is now unreachable, so drop
                # the name and let its idle timeout end it.
                _latch_no_batch(e)
                transaction_manager.forget(key)
                raise ToolError(_FALLBACK_NO_BATCH_REFUSES_TRANSACTION) from e
            if not _is_session_gone(e):
                raise
            # The service took the session away, so the transaction is gone with everything
            # it had not committed. Report it as missing rather than as an AWS error.
            logger.warning(f'Transaction {key} lost its session: {e}')
            transaction_manager.forget(key)
            raise ToolError(
                f'No open transaction named {name!r}. It was never opened, was rolled back '
                f'after a failed statement, or expired after being idle.'
            ) from e
        except Exception:
            # A failed statement aborts the transaction: every later statement is refused
            # and a COMMIT would report success while persisting nothing. Roll it back and
            # drop the name so the next call cannot be misled.
            await _rollback_lost_transaction(
                cluster_info, cluster_identifier, database_name, session_id
            )
            transaction_manager.forget(key)
            raise

        if closer is not None:
            transaction_manager.forget(key)
        else:
            # Still open, and just used, so its idle clock starts again from here.
            transaction_manager.touch(key)

    return results_response, query_id


async def _rollback_lost_transaction(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    session_id: str,
) -> None:
    """Roll back a transaction whose statement failed, best effort.

    The session is being dropped either way, so a failure here changes nothing the caller can
    act on: the transaction is already aborted, and the session's idle timeout ends it.

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
        )
    except Exception as e:  # noqa: BLE001 - nothing here is actionable
        logger.warning(f'Rollback of the aborted transaction on {session_id} failed: {e}')


def _is_session_gone(error: ClientError) -> bool:
    """Report whether a Data API error means the session no longer exists.

    Args:
        error: The botocore error raised at submit.

    Returns:
        True when the session is expired, reclaimed or unknown.
    """
    if error.response.get('Error', {}).get('Code') != 'ValidationException':
        return False
    message = error.response.get('Error', {}).get('Message', '')
    return any(
        marker in message
        for marker in ('Session is expired', 'Session is not available', 'is invalid')
    )


async def _settle_statement(
    statement_id: str,
    response: dict,
    query_poll_interval: float,
    query_timeout: float,
    query_long_poll: int,
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

    Returns:
        The terminal DescribeStatement response.

    Raises:
        ToolError: If it does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()
    long_poll_params = {'WaitTimeSeconds': query_long_poll} if query_long_poll else {}
    described = False

    # Wall clock, since a long poll blocks server-side.
    deadline = time.monotonic() + query_timeout
    while True:
        if response.get('Status') in _TERMINAL_STATUSES:
            if not described:
                response = await asyncio.to_thread(data_client.describe_statement, Id=statement_id)
            logger.debug(f'Statement settled: {statement_id} ({response["Status"]})')
            return response

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


# --- Fallback: no_batch ---
# Serves credentials denied redshift-data:BatchExecuteStatement by running one statement
# per call, which keeps the read-only contract of the release before named transactions.
# Everything tagged no_batch belongs to it and nothing above depends on it, so the whole
# path can be deleted with its constants and tests once the action is universal.


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
    if error.response.get('Error', {}).get('Code') not in _ACCESS_DENIED:
        return False
    return error.operation_name == _BATCH_OPERATION


def _no_batch_active() -> bool:
    """Report whether the no_batch fallback is in force, and consume a due re-probe.

    Returns:
        True while the batch path is known denied, and False once per
        FALLBACK_NO_BATCH_REPROBE seconds after that, so a granted policy is picked up
        without a restart.
    """
    global _no_batch_since

    if _no_batch_since is None:
        return False

    if time.monotonic() - _no_batch_since < FALLBACK_NO_BATCH_REPROBE:
        return True

    # Due for a probe. Clearing it first means a still-denied batch latches again, which is
    # what keeps the warning to one per re-probe window rather than one per statement.
    _no_batch_since = None
    return False


def _latch_no_batch(error: ClientError) -> None:
    """Record that the batch action is denied, and name the grant that restores it.

    Args:
        error: The denial, quoted so the operator can see which principal was refused.
    """
    global _no_batch_since
    _no_batch_since = time.monotonic()
    logger.warning(
        'redshift-data:BatchExecuteStatement is denied, so statements now run one at a time: '
        'reads still work, writes and named transactions do not. Grant the action to restore '
        f'them; the batch path is retried in {FALLBACK_NO_BATCH_REPROBE}s. {error}'
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
        logger.error(f'Statement failed: {error}')
        raise ToolError(f'Statement failed: {error}')

    if not settled.get('HasResultSet'):
        return {'Records': [], 'ColumnMetadata': []}, statement_id

    results_response = await asyncio.to_thread(data_client.get_statement_result, Id=statement_id)
    return results_response, statement_id


# --- Main path ---


async def _execute_batch(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sqls: list[str],
    session_sink: list[str] | None = None,
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
    )


def _fetch_provisioned_clusters() -> list[dict]:
    """Page through every provisioned cluster.

    Synchronous, and called through asyncio.to_thread: boto3 blocks, and client construction
    on first use blocks for seconds, which would stall every other call on the event loop.

    Returns:
        The raw DescribeClusters entries.
    """
    paginator = client_manager.redshift_client().get_paginator('describe_clusters')
    return [cluster for page in paginator.paginate() for cluster in page.get('Clusters', [])]


def _fetch_serverless_workgroups() -> list[tuple[dict, dict]]:
    """Page through every serverless workgroup and fetch each one's detail.

    Synchronous, and called through asyncio.to_thread, for the same reason as its provisioned
    counterpart. The detail call is per workgroup, so this blocks for longer still.

    Returns:
        Pairs of the ListWorkgroups entry and its GetWorkgroup detail.
    """
    serverless_client = client_manager.redshift_serverless_client()
    paginator = serverless_client.get_paginator('list_workgroups')
    return [
        (
            workgroup,
            serverless_client.get_workgroup(workgroupName=workgroup['workgroupName'])['workgroup'],
        )
        for page in paginator.paginate()
        for workgroup in page.get('workgroups', [])
    ]


async def discover_clusters() -> list[RedshiftCluster]:
    """Discover all Redshift clusters and serverless workgroups.

    Discovery is best-effort for each type: if either provisioned or serverless
    discovery succeeds, the function returns whatever was found. It only raises
    if both fail (i.e., no clusters could be discovered at all).

    Returns:
        List of RedshiftCluster models.

    Raises:
        ToolError: If both provisioned and serverless discovery fail.
    """
    clusters = []
    provisioned_error = None
    serverless_error = None

    # Attempt provisioned cluster discovery
    try:
        # Get provisioned clusters
        logger.debug('Discovering provisioned Redshift clusters')

        for cluster in await asyncio.to_thread(_fetch_provisioned_clusters):
            cluster_info = {
                'identifier': cluster['ClusterIdentifier'],
                'type': 'provisioned',
                'status': cluster['ClusterStatus'],
                'database_name': cluster.get('DBName', 'dev'),
                'endpoint': cluster.get('Endpoint', {}).get('Address'),
                'port': cluster.get('Endpoint', {}).get('Port'),
                'vpc_id': cluster.get('VpcId'),
                'node_type': cluster.get('NodeType'),
                'number_of_nodes': cluster.get('NumberOfNodes'),
                'creation_time': cluster.get('ClusterCreateTime'),
                'master_username': cluster.get('MasterUsername'),
                'publicly_accessible': cluster.get('PubliclyAccessible'),
                'encrypted': cluster.get('Encrypted'),
                'tags': {tag['Key']: tag['Value'] for tag in cluster.get('Tags', [])},
            }
            clusters.append(RedshiftCluster(**cluster_info))

        logger.info(f'Found {len(clusters)} provisioned clusters')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in _ACCESS_DENIED:
            raise
        provisioned_error = e
        logger.warning(f'Skipping provisioned; IAM lacks permission: {e}')

    # Attempt serverless workgroup discovery
    try:
        # Get serverless workgroups
        logger.debug('Discovering Redshift Serverless workgroups')

        for workgroup, workgroup_detail in await asyncio.to_thread(_fetch_serverless_workgroups):
            cluster_info = {
                'identifier': workgroup['workgroupName'],
                'type': 'serverless',
                'status': workgroup['status'],
                # Serverless always exposes the built-in 'dev' database. Reporting the
                # namespace's configured default would require redshift-serverless:GetNamespace;
                # callers can pass an explicit database_name to the other tools instead.
                'database_name': 'dev',
                'endpoint': workgroup_detail.get('endpoint', {}).get('address'),
                'port': workgroup_detail.get('endpoint', {}).get('port'),
                'vpc_id': (workgroup_detail.get('subnetIds') or [None])[
                    0
                ],  # Approximate VPC from subnet
                'node_type': None,  # Not applicable for serverless
                'number_of_nodes': None,  # Not applicable for serverless
                'creation_time': workgroup.get('creationDate'),
                'master_username': None,  # Serverless uses IAM
                'publicly_accessible': workgroup_detail.get('publiclyAccessible'),
                'encrypted': True,  # Serverless is always encrypted
                'tags': {tag['key']: tag['value'] for tag in workgroup_detail.get('tags', [])},
            }
            clusters.append(RedshiftCluster(**cluster_info))

        serverless_count = len([c for c in clusters if c.type == 'serverless'])
        logger.info(f'Found {serverless_count} serverless workgroups')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in _ACCESS_DENIED:
            raise
        serverless_error = e
        logger.warning(f'Skipping serverless; IAM lacks permission: {e}')

    # If both discovery methods failed, raise an error
    if provisioned_error and serverless_error:
        msg = (
            'Unable to discover any Redshift clusters: IAM lacks both redshift and '
            f'redshift-serverless permissions. Provisioned: {provisioned_error}; '
            f'Serverless: {serverless_error}'
        )
        logger.error(msg)
        raise ToolError(msg)

    logger.info(f'Total clusters discovered: {len(clusters)}')
    return clusters


async def discover_databases(
    cluster_identifier: str, database_name: str = 'dev'
) -> list[RedshiftDatabase]:
    """Discover databases in a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to connect to for querying system views.

    Returns:
        List of RedshiftDatabase models.
    """
    try:
        logger.info(f'Discovering databases in cluster {cluster_identifier}')

        results_response, _ = await _execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=DATABASES_SQL,
            # This server's own SQL, so it does not police itself.
            enforce_read_only=False,
        )

        databases = RedshiftDatabase.from_redshift_response(results_response)
        logger.info(f'Found {len(databases)} databases in cluster {cluster_identifier}')
        return databases

    except Exception as e:
        logger.error(f'Error discovering databases in cluster {cluster_identifier}: {str(e)}')
        raise


async def discover_schemas(
    cluster_identifier: str, schema_database_name: str
) -> list[RedshiftSchema]:
    """Discover schemas in a Redshift database using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        schema_database_name: The database name to filter schemas for. Also used to connect to.

    Returns:
        List of RedshiftSchema models.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=SCHEMAS_SQL.format(database=_sql_identifier(schema_database_name)),
            enforce_read_only=False,
        )

        schemas = RedshiftSchema.from_redshift_response(results_response)
        logger.info(
            f'Found {len(schemas)} schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        logger.error(
            f'Error discovering schemas in database {schema_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_tables(
    cluster_identifier: str, table_database_name: str, table_schema_name: str
) -> list[RedshiftTable]:
    """Discover tables in a Redshift schema using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        table_database_name: The database name to filter tables for. Also used to connect to.
        table_schema_name: The schema name to filter tables for.

    Returns:
        List of RedshiftTable models.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=TABLES_SQL.format(
                database=_sql_identifier(table_database_name),
                schema=_sql_identifier(table_schema_name),
            ),
            enforce_read_only=False,
        )

        tables = RedshiftTable.from_redshift_response(results_response)
        logger.info(
            f'Found {len(tables)} tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        logger.error(
            f'Error discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str,
) -> list[RedshiftColumn]:
    """Discover columns in a Redshift table using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        column_database_name: The database name to filter columns for. Also used to connect to.
        column_schema_name: The schema name to filter columns for.
        column_table_name: The table name to filter columns for.

    Returns:
        List of RedshiftColumn models.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_standalone_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=COLUMNS_SQL.format(
                database=_sql_identifier(column_database_name),
                schema=_sql_identifier(column_schema_name),
                table=_sql_identifier(column_table_name),
            ),
            enforce_read_only=False,
        )

        columns = RedshiftColumn.from_redshift_response(results_response)
        logger.info(
            f'Found {len(columns)} columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(
            f'Error discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


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

    return action, name


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
            results_response, query_id = await _execute_standalone_statement(
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
        logger.error(f'Error executing query on cluster {cluster_identifier}: {str(e)}')
        raise


# Global transaction manager instance
transaction_manager = RedshiftTransactionManager()

# Global client manager instance
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'md/awslabs#mcp#redshift-mcp-server#{__version__}',
    ),
    aws_region=os.environ.get('AWS_REGION'),
    aws_profile=os.environ.get('AWS_PROFILE'),
)
