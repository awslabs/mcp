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


"""Tests for the transaction manager."""

import asyncio
import pytest
from awslabs.redshift_mcp_server.consts import SESSION_KEEPALIVE_MAX
from awslabs.redshift_mcp_server.settings import max_open_transactions_per_target
from awslabs.redshift_mcp_server.transactions import RedshiftTransactionManager
from mcp.server.mcpserver.exceptions import ToolError


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
            manager.session_id('stale', 'abandoned', 'c:db')

    def test_a_transaction_with_a_statement_in_flight_is_not_reaped(self):
        """It is in use, not idle, however long its statement runs.

        Reaping one would hand its name to another caller while the first still holds it: the
        statement would report success, the work would be stranded on a session nobody tracks,
        and a later commit would report success for a different transaction.
        """
        manager = self._manager(max_open_per_target=1)
        manager.reserve('busy', 'target', 'busy')
        manager.attach('busy', 'session-1')
        manager._transactions['busy']['touched_at'] -= SESSION_KEEPALIVE_MAX + 1

        lock, _ = manager.claim('busy')

        async def reap_while_it_is_held():
            async with lock:
                manager._reap_expired('target')

        asyncio.run(reap_while_it_is_held())

        assert manager.session_id('busy', 'busy', 'c:db') == 'session-1'

    def test_opening_a_transaction_starts_its_idle_clock_at_the_end_of_the_batch(self):
        """Redshift counts idle time from when the opening batch finishes, so this must too.

        Stamped at `reserve` instead, the whole opening batch counts as idle, and a transaction
        whose first statement ran longer than the keepalive is reapable the moment it returns.
        """
        manager = self._manager(max_open_per_target=1)
        manager.reserve('key', 'target', 'load')

        # As if the opening batch had run longer than any keepalive the server accepts.
        manager._transactions['key']['touched_at'] -= SESSION_KEEPALIVE_MAX + 1
        manager.attach('key', 'session-1')

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.reserve('other', 'target', 'second')

    def test_touching_a_name_that_is_gone_does_not_recreate_it(self):
        """The in-use check should prevent this, so it reports rather than resurrecting."""
        manager = self._manager()

        manager.touch('never-reserved')

        assert manager._transactions == {}

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

        assert manager.session_id('key', 'load', 'c:db') == 'session-1'

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
            manager.session_id('key', 'load', 'c:db')

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
