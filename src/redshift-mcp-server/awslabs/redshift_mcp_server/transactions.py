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

"""One named transaction, the Data API session behind it, and the open ones a caller can reach."""

import asyncio
import time
from awslabs.redshift_mcp_server.settings import (
    max_open_transactions_per_target,
    session_keepalive,
)
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError


def _key(cluster: str, database_name: str, name: str) -> str:
    """Build the map key that identifies one caller's transaction.

    Remote support will add the authenticated principal on the left, so that one caller cannot
    reach another's transaction. This is the format that changes for it, once the caller's
    identity reaches this layer.

    Args:
        cluster: The cluster the transaction runs on, as `redshift._canonical_cluster` names it.
        database_name: The database the transaction runs in.
        name: The caller's name for the transaction.

    Returns:
        The map key.
    """
    return f'{cluster}:{database_name}:{name}'


def unknown_transaction(name: str, target: str) -> ToolError:
    """Build the error for a name that is not open, or is open without a session yet.

    Every cause is indistinguishable from the outside, so one message names them all.

    Args:
        name: The caller's name for the transaction.
        target: The cluster and database searched.

    Returns:
        The error to raise.
    """
    return ToolError(
        f'No open transaction named {name!r} on {target}. An earlier call committed or '
        f'rolled it back, it was released after a failed statement, a cancelled call or a '
        f'denied batch action, it expired after being idle, the call opening it has not returned '
        f'yet, it was never opened, or it was opened against a different cluster or database.'
    )


class NamedTransaction:
    """One open transaction and the Data API session it holds.

    The handle a caller acts through, and the unit of identity: a name closed and reopened
    produces a new instance, so `NamedTransactionManager.holding` compares identity rather than
    tracking a version per name.

    Being registered and being usable are separate. `manager.open` registers one before its
    session exists, and `attach` is what makes it usable.
    """

    def __init__(self, cluster: str, database_name: str, name: str):
        """Initialize a transaction that is claimed but not yet open on the cluster.

        Args:
            cluster: The cluster the transaction runs on.
            database_name: The database the transaction runs in.
            name: The caller's name for the transaction.
        """
        self.cluster = cluster
        self.database_name = database_name
        self.name = name

        # A SessionId is strictly serial: a second statement submitted while one is in flight is
        # refused at submit, so every use of this session has to hold this. Take it through
        # `NamedTransactionManager.holding`, which validates the handle in the same step. One
        # lock per instance, so a waiter on a transaction that has since closed holds a lock
        # nobody else will ever take, rather than one a later transaction of the same name
        # would respect.
        self.lock = asyncio.Lock()

        self.session_id: str | None = None
        self.touched_at = time.monotonic()

    @property
    def key(self) -> str:
        """The map key this transaction is registered under."""
        return _key(self.cluster, self.database_name, self.name)

    @property
    def target(self) -> str:
        """The cluster and database the open-transaction cap is counted against."""
        return f'{self.cluster}:{self.database_name}'

    @property
    def in_use(self) -> bool:
        """Whether a statement is in flight, which is what holding the lock means."""
        return self.lock.locked()

    def attach(self, session_id: str) -> None:
        """Record the session the Data API minted for this transaction.

        Args:
            session_id: The session the transaction runs on.
        """
        self.session_id = session_id
        # Redshift starts the session's idle clock when the opening batch finishes, so the
        # reaper's clock starts here too. Left at the construction stamp, the whole opening batch
        # would count as idle time the transaction spent working.
        self.touched_at = time.monotonic()
        logger.info(f'Opened transaction {self.key} on session {session_id}')

    def touch(self) -> None:
        """Restart the idle clock, after a statement that leaves the transaction open."""
        self.touched_at = time.monotonic()

    def session(self) -> str:
        """Get the session to submit on.

        Returns:
            The session the transaction runs on.

        Raises:
            ToolError: If it has no session, so nothing can be submitted on it.
        """
        if self.session_id is None:
            raise unknown_transaction(self.name, self.target)
        return self.session_id


class NamedTransactionManager:
    """The open transactions, and the names callers reach them by.

    Each open transaction holds one session. Nothing is pooled and nothing is reused: a statement
    outside a transaction mints no session at all, and a dropped name's session is left to end on
    its own idle timeout, rolled back first where that is safe.

    Everything here is about the set - admitting a name, finding one, dropping one, and the
    per-target cap. Everything about a single transaction belongs to `NamedTransaction`.
    """

    def __init__(self, max_open_per_target: int | None = None):
        """Initialize the transaction manager.

        Args:
            max_open_per_target: How many transactions may be open at once per target. Left
                unset, the configured cap is read on first use.
        """
        self._transactions: dict[str, NamedTransaction] = {}
        self._max_open_per_target = max_open_per_target

    def open(self, cluster: str, database_name: str, name: str) -> NamedTransaction:
        """Admit a name and return the transaction to open under it.

        Admitting first means a duplicate name or an exhausted cap is refused before any work is
        done, and that two concurrent opens cannot both pass the cap check.

        Args:
            cluster: The cluster the transaction runs on.
            database_name: The database the transaction runs in.
            name: The caller's name for the transaction.

        Returns:
            The registered transaction, with no session yet.

        Raises:
            ToolError: If the name is already open, or the target is at its cap.
        """
        transaction = NamedTransaction(cluster, database_name, name)

        # Reaped before the name is tested, not just before the cap is counted. A name whose
        # session the service has already ended is free, and refusing it as still open left the
        # caller unable to reopen it until a commit or rollback on it had failed.
        self._reap_expired(transaction.target)

        if transaction.key in self._transactions:
            raise ToolError(
                f'Transaction {name!r} is already open. Use in_transaction to add a statement '
                f'to it, or commit or roll it back before opening it again.'
            )

        cap = (
            self._max_open_per_target
            if self._max_open_per_target is not None
            else max_open_transactions_per_target()
        )
        open_count = sum(
            1 for other in self._transactions.values() if other.target == transaction.target
        )
        if open_count >= cap:
            raise ToolError(
                f'Too many open transactions ({open_count}). Commit or roll one back before '
                f'opening another, or raise MAX_OPEN_TRANSACTIONS_PER_TARGET.'
            )

        self._transactions[transaction.key] = transaction
        return transaction

    def find(self, cluster: str, database_name: str, name: str) -> NamedTransaction | None:
        """Look up a transaction without insisting it exists.

        Args:
            cluster: The cluster the transaction runs on.
            database_name: The database the transaction runs in.
            name: The caller's name for the transaction.

        Returns:
            The transaction registered under that name, or None.
        """
        return self._transactions.get(_key(cluster, database_name, name))

    def get(self, cluster: str, database_name: str, name: str) -> NamedTransaction:
        """Get a transaction that is open and has a session to submit on.

        Args:
            cluster: The cluster the transaction runs on.
            database_name: The database the transaction runs in.
            name: The caller's name for the transaction.

        Returns:
            The transaction registered under that name.

        Raises:
            ToolError: If no transaction is open under that name, or it has no session yet.
        """
        transaction = self.find(cluster, database_name, name)
        if transaction is None or transaction.session_id is None:
            raise unknown_transaction(name, f'{cluster}:{database_name}')
        return transaction

    @asynccontextmanager
    async def holding(self, transaction: NamedTransaction) -> AsyncIterator[NamedTransaction]:
        """Hold a transaction's lock for the statement about to run on it.

        Acquiring and validating in one step, because they are one step: a caller that took the
        lock and skipped the check would submit on the session of a transaction that has closed,
        where the statement runs in autocommit, outside any `BEGIN`. This is how the lock is
        taken; nothing else should reach for it.

        Args:
            transaction: The handle to act on.

        Yields:
            The same transaction, now held and still current.

        Raises:
            ToolError: If the name changed hands while the lock was being acquired.
        """
        async with transaction.lock:
            self._assert_current(transaction)
            yield transaction

    def _assert_current(self, transaction: NamedTransaction) -> None:
        """Refuse to act on a handle whose name has since changed hands.

        Acquiring a transaction's lock is an await, and the name can be closed, or closed and
        reopened, across it. The registry holds whichever transaction owns the name now, so a
        handle that is no longer the registered one is a handle to a transaction that is gone.

        Args:
            transaction: The handle the caller is about to act on.

        Raises:
            ToolError: If the name now belongs to a different transaction, or to none.
        """
        if self._transactions.get(transaction.key) is not transaction:
            # Says only what became of this statement: the name may be open again by now, and a
            # caller told to reopen it was answered 'already open'.
            raise ToolError(
                f'Transaction {transaction.name!r} closed while this statement was waiting for '
                f'it. Nothing ran.'
            )

    def forget(self, transaction: NamedTransaction) -> None:
        """Drop a transaction, whether it closed cleanly or was lost.

        Dropping only the registered instance, so a stale handle cannot evict the transaction
        that took its name.

        Args:
            transaction: The transaction to drop.
        """
        if self._transactions.get(transaction.key) is transaction:
            del self._transactions[transaction.key]
            logger.info(f'Closed transaction {transaction.key}')

    def _reap_expired(self, target: str) -> None:
        """Drop transactions whose session the service has already ended.

        Redshift ends a session left idle for SESSION_KEEPALIVE seconds and says nothing about
        it. Without this, a caller who opens transactions and walks away holds the target's cap
        against everyone else until each dead name is used and found gone.

        A transaction with a statement in flight is in use rather than idle, however long that
        statement runs, and the service has not started counting its idle time yet.

        Args:
            target: The cluster and database whose transactions to check.
        """
        keepalive = session_keepalive()
        now = time.monotonic()
        expired = [
            candidate
            for candidate in self._transactions.values()
            if candidate.target == target
            and now - candidate.touched_at > keepalive
            and not candidate.in_use
        ]

        for candidate in expired:
            logger.info(
                f'Reaped transaction {candidate.key}: idle past SESSION_KEEPALIVE={keepalive}s'
            )
            self.forget(candidate)


# One per process, holding every open transaction.
transaction_manager = NamedTransactionManager()
