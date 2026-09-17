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

"""The Data API session behind each open transaction, and the names callers reach it by."""

import asyncio
import time
from awslabs.redshift_mcp_server.settings import (
    max_open_transactions_per_target,
    session_keepalive,
)
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError


def transaction_key(cluster_identifier: str, database_name: str, name: str) -> str:
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


def transaction_target(cluster_identifier: str, database_name: str) -> str:
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

    def _in_use(self, key: str) -> bool:
        """Report whether a statement is in flight on this transaction.

        Every use of a session holds the name's lock for as long as the statement runs, so a
        held lock is what being in use means here.

        Args:
            key: The transaction key to check.

        Returns:
            True while a caller holds the lock.
        """
        lock = self._locks.get(key)
        return lock is not None and lock.locked()

    def _reap_expired(self, target: str) -> None:
        """Drop entries whose session the service has already ended.

        Redshift ends a session left idle for SESSION_KEEPALIVE seconds and says nothing about
        it. Without this, a caller who opens transactions and walks away holds the target's
        cap against everyone else until each dead name is touched and found gone.

        A transaction with a statement in flight is in use rather than idle, however long that
        statement runs, and the service has not started counting its idle time yet.

        Args:
            target: The cluster and database whose entries to check.
        """
        keepalive = session_keepalive()
        now = time.monotonic()
        expired = [
            key
            for key, entry in self._transactions.items()
            if entry['target'] == target
            and now - entry['touched_at'] > keepalive
            and not self._in_use(key)
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
        if entry is None:
            # The in-use check in `_reap_expired` is what keeps this from happening, so
            # reaching it means a name was dropped while its statement was still running.
            logger.warning(f'Transaction {key} was dropped while its statement was running')
            return
        entry['touched_at'] = time.monotonic()

    def attach(self, key: str, session_id: str) -> None:
        """Record the session the Data API minted for a claimed transaction.

        Args:
            key: The claimed transaction key.
            session_id: The session the transaction runs on.
        """
        entry = self._transactions[key]
        entry['session_id'] = session_id
        # Redshift starts the session's idle clock when the opening batch finishes, so the
        # reaper's clock starts here too. Left at the `reserve` stamp, the whole opening batch
        # would count as idle time the transaction spent working.
        entry['touched_at'] = time.monotonic()
        logger.info(f'Opened transaction {key} on session {session_id}')

    def session_id(self, key: str, name: str, target: str) -> str:
        """Get the session of an open transaction.

        Args:
            key: The transaction key to look up.
            name: The caller's name for the transaction, for the error message.
            target: The cluster and database searched, for the error message.

        Returns:
            The session the transaction runs on.

        Raises:
            ToolError: If no transaction is open under that name.
        """
        entry = self._transactions.get(key)
        if entry is None or entry['session_id'] is None:
            raise ToolError(
                f'No open transaction named {name!r} on {target}. An earlier call committed or '
                f'rolled it back, it was never opened, it was rolled back after a failed '
                f'statement, it expired after being idle, or it was opened against a '
                f'different cluster or database.'
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


# One per process, holding every session this server owns.
transaction_manager = RedshiftTransactionManager()
