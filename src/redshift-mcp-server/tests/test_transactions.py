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


"""Tests for named transactions and the manager that registers them."""

import asyncio
import pytest
from awslabs.redshift_mcp_server.consts import SESSION_KEEPALIVE_MAX
from awslabs.redshift_mcp_server.settings import max_open_transactions_per_target
from awslabs.redshift_mcp_server.transactions import (
    NamedTransaction,
    NamedTransactionManager,
)
from mcp.server.mcpserver.exceptions import ToolError


class TestNamedTransaction:
    """Tests for the handle a caller acts through."""

    def test_the_key_carries_all_three_parts(self):
        """The name alone is not the identity: the same name on another target is another one."""
        transaction = NamedTransaction('c', 'dev', 'load')

        assert transaction.key == 'c:dev:load'
        assert transaction.target == 'c:dev'

    def test_a_name_containing_a_colon_is_not_parsed_back(self):
        """The name is the caller's to choose, so the target cannot be recovered from the key.

        This is why the target is carried rather than split off the key.
        """
        transaction = NamedTransaction('c', 'dev', 'load:2')

        assert transaction.key == 'c:dev:load:2'
        assert transaction.target == 'c:dev'
        assert transaction.key.rsplit(':', 1)[0] != transaction.target

    def test_an_unattached_transaction_has_no_session_to_submit_on(self):
        """Registered and usable are separate: the opening batch is what mints the session."""
        transaction = NamedTransaction('c', 'dev', 'load')

        with pytest.raises(ToolError, match='No open transaction'):
            transaction.session()

    def test_attaching_starts_the_idle_clock_over(self):
        """Redshift counts idle time from when the opening batch finishes, so this must too.

        Left at the construction stamp, the whole opening batch counts as idle, and a
        transaction whose first statement ran longer than the keepalive is reapable the moment
        it returns.
        """
        transaction = NamedTransaction('c', 'dev', 'load')
        transaction.touched_at -= SESSION_KEEPALIVE_MAX + 1
        stale = transaction.touched_at

        transaction.attach('session-1')

        assert transaction.session() == 'session-1'
        assert transaction.touched_at > stale

    def test_in_use_means_the_lock_is_held_not_merely_created(self):
        """Reaping a transaction whose statement is in flight would hand its name away."""
        transaction = NamedTransaction('c', 'dev', 'load')

        assert transaction.in_use is False

        async def hold_it():
            async with transaction.lock:
                return transaction.in_use

        assert asyncio.run(hold_it()) is True


class TestNamedTransactionManager:
    """Tests for the registry of open transactions."""

    def _manager(self, max_open_per_target=10):
        """Build a manager with no transactions in it."""
        return NamedTransactionManager(max_open_per_target=max_open_per_target)

    def test_each_transaction_has_its_own_lock(self):
        """Two statements in one transaction must serialize; two transactions must not."""
        manager = self._manager()

        one = manager.open('c', 'dev', 'one')
        two = manager.open('c', 'dev', 'two')

        assert one.lock is not two.lock
        assert manager.find('c', 'dev', 'one') is one

    def test_a_name_still_being_opened_is_named_as_such(self):
        """Registered before its session exists, so a concurrent call finds it without one.

        Every cause the message listed was false then, and the name was open once the opening
        call returned.
        """
        manager = self._manager()
        manager.open('c', 'dev', 'load')

        with pytest.raises(ToolError, match='the call opening it has not returned yet'):
            manager.get('c', 'dev', 'load')

    def test_a_reopened_name_is_a_different_transaction_with_a_different_lock(self):
        """A waiter holding the closed one must not be respected by whatever took the name.

        Acquiring a lock is an await, so the name can be closed and reopened across it. One
        lock per transaction means the waiter wakes holding a lock nobody else will ever take,
        and `_assert_current` is what tells it the transaction it queued for is gone.
        """
        manager = self._manager()
        first = manager.open('c', 'dev', 'load')
        first.attach('session-1')

        manager.forget(first)
        second = manager.open('c', 'dev', 'load')
        second.attach('session-2')

        assert second is not first
        assert second.lock is not first.lock
        with pytest.raises(ToolError, match='closed while this statement was waiting'):
            manager._assert_current(first)

    def test_holding_refuses_a_handle_the_name_no_longer_belongs_to(self):
        """Taking the lock and validating are one step, so neither can be had without the other.

        Two steps let a caller hold the lock and skip the check, and submit onto whatever
        transaction now holds the name.
        """
        manager = self._manager()
        first = manager.open('c', 'dev', 'load')
        first.attach('session-1')
        manager.forget(first)
        manager.open('c', 'dev', 'load').attach('session-2')

        async def act_on_the_stale_handle():
            async with manager.holding(first):
                pass  # pragma: no cover - the refusal is the assertion

        with pytest.raises(ToolError, match='closed while this statement was waiting'):
            asyncio.run(act_on_the_stale_handle())

    def test_holding_releases_the_lock_when_the_body_raises(self):
        """A failed statement must not strand the transaction its caller still owns."""
        manager = self._manager()
        transaction = manager.open('c', 'dev', 'load')
        transaction.attach('session-1')

        async def fail_while_held():
            with pytest.raises(RuntimeError):
                async with manager.holding(transaction):
                    raise RuntimeError('statement failed')
            return transaction.in_use

        assert asyncio.run(fail_while_held()) is False

    def test_a_closed_transaction_is_refused_even_if_the_name_is_free(self):
        """Closed and not reopened is the same answer as closed and reopened: not yours."""
        manager = self._manager()
        transaction = manager.open('c', 'dev', 'load')
        transaction.attach('session-1')

        manager.forget(transaction)

        with pytest.raises(ToolError, match='closed while this statement was waiting'):
            manager._assert_current(transaction)

    def test_a_refused_open_leaves_the_holder_alone(self):
        """A second caller's failed open must not disturb the transaction holding the name."""
        manager = self._manager()
        transaction = manager.open('c', 'dev', 'load')
        transaction.attach('session-1')

        with pytest.raises(ToolError, match='already open'):
            manager.open('c', 'dev', 'load')

        manager._assert_current(transaction)

    def test_a_stale_handle_cannot_evict_the_transaction_that_took_its_name(self):
        """Cleanup runs on failure paths, and one of them may hold a handle already replaced."""
        manager = self._manager()
        first = manager.open('c', 'dev', 'load')
        manager.forget(first)
        second = manager.open('c', 'dev', 'load')
        second.attach('session-2')

        manager.forget(first)

        assert manager.find('c', 'dev', 'load') is second

    def test_a_transaction_idle_past_its_keepalive_stops_holding_the_cap(self):
        """Redshift ends an idle session silently, so its entry must not hold the cap forever.

        Without reaping, a caller who opens transactions and walks away blocks the target for
        everyone until each dead name is used and found gone.
        """
        manager = self._manager(max_open_per_target=1)
        stale = manager.open('c', 'dev', 'abandoned')
        stale.attach('session-1')
        stale.touched_at -= SESSION_KEEPALIVE_MAX + 1

        # Opening at all is the assertion: the cap is 1, so this only fits if the stale
        # transaction was reaped rather than counted.
        manager.open('c', 'dev', 'wanted')

        with pytest.raises(ToolError, match='No open transaction'):
            manager.get('c', 'dev', 'abandoned')

    def test_a_transaction_with_a_statement_in_flight_is_not_reaped(self):
        """It is in use, not idle, however long its statement runs.

        Reaping one would hand its name to another caller while the first still holds it: the
        statement would report success, the work would be stranded on a session nobody tracks,
        and a later commit would report success for a different transaction.
        """
        manager = self._manager(max_open_per_target=1)
        busy = manager.open('c', 'dev', 'busy')
        busy.attach('session-1')
        busy.touched_at -= SESSION_KEEPALIVE_MAX + 1

        async def reap_while_it_is_held():
            async with manager.holding(busy):
                manager._reap_expired('c:dev')

        asyncio.run(reap_while_it_is_held())

        assert manager.get('c', 'dev', 'busy').session() == 'session-1'

    def test_an_expired_name_can_be_opened_again(self):
        """Refused as still open, the name was unusable: closing it needs the session that is gone.

        The cap is not the only thing reaping frees. Tested under a cap of two so the refusal
        cannot be mistaken for the cap being reached.
        """
        manager = self._manager(max_open_per_target=2)
        stale = manager.open('c', 'dev', 'load')
        stale.attach('session-1')
        stale.touched_at -= SESSION_KEEPALIVE_MAX + 1

        reopened = manager.open('c', 'dev', 'load')

        assert reopened is not stale
        assert manager.find('c', 'dev', 'load') is reopened

    def test_using_a_transaction_restarts_its_idle_clock(self):
        """The keepalive counts idle time, so a transaction in use must not be reaped."""
        manager = self._manager(max_open_per_target=1)
        transaction = manager.open('c', 'dev', 'load')
        transaction.attach('session-1')
        transaction.touched_at -= SESSION_KEEPALIVE_MAX + 1

        transaction.touch()

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.open('c', 'dev', 'second')

    def test_an_open_and_attached_transaction_reports_its_session(self):
        """The session is what every later statement in the transaction runs on."""
        manager = self._manager()
        manager.open('c', 'dev', 'load').attach('session-1')

        assert manager.get('c', 'dev', 'load').session() == 'session-1'

    def test_opening_an_open_name_is_refused(self):
        """Silently joining someone else's transaction is the failure mode to avoid."""
        manager = self._manager()
        manager.open('c', 'dev', 'load')

        with pytest.raises(ToolError, match="Transaction 'load' is already open"):
            manager.open('c', 'dev', 'load')

    def test_the_cap_is_counted_per_target(self):
        """A busy database must not stop work on another one."""
        manager = self._manager(max_open_per_target=2)
        manager.open('c', 'dev', 'one')
        manager.open('c', 'dev', 'two')

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.open('c', 'dev', 'three')

        # Another database is a different target, so it still has room.
        manager.open('c', 'other', 'one')

    def test_a_closed_name_frees_its_slot(self):
        """The cap bounds what is open, not what was ever opened."""
        manager = self._manager(max_open_per_target=1)
        transaction = manager.open('c', 'dev', 'load')
        manager.forget(transaction)

        manager.open('c', 'dev', 'load')

    @pytest.mark.parametrize(
        'open_first', [False, True], ids=['never_opened', 'open_but_not_attached']
    )
    def test_an_unknown_transaction_names_every_way_it_could_be_gone(self, open_first):
        """Every cause is indistinguishable from here, so the message covers all of them."""
        manager = self._manager()
        if open_first:
            manager.open('c', 'dev', 'load')

        with pytest.raises(ToolError) as failure:
            manager.get('c', 'dev', 'load')

        message = str(failure.value)
        assert "No open transaction named 'load'" in message
        assert 'never opened' in message
        assert 'released after a failed statement' in message
        assert 'expired' in message

    def test_finding_an_unknown_transaction_answers_nothing(self):
        """The paths that clean up after a denial need to ask without being refused."""
        assert self._manager().find('c', 'dev', 'load') is None

    def test_forgetting_an_unregistered_transaction_is_harmless(self):
        """Cleanup runs on paths that may never have registered anything."""
        self._manager().forget(NamedTransaction('c', 'dev', 'load'))

    def test_an_unset_cap_falls_back_to_the_configured_one(self):
        """The server's own manager takes no cap, so the setting is read on first use."""
        manager = NamedTransactionManager()

        for i in range(max_open_transactions_per_target()):
            manager.open('c', 'dev', str(i))

        with pytest.raises(ToolError, match='Too many open transactions'):
            manager.open('c', 'dev', 'over')
