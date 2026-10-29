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

"""Tests for the connection map."""

import asyncio
import pytest
from awslabs.db2_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from awslabs.db2_mcp_server.connection.db_connection_map import (
    AmbiguousConnectionError,
    ConnectionMethod,
    DBConnectionMap,
)
from typing import cast


M = ConnectionMethod.DB2_PASSWORD
DUMMY_ARN = 'arn:s'  # pragma: allowlist secret
DUMMY_ARN_XYZ = 'arn:xyz'  # pragma: allowlist secret


class FakeConn(AbstractDBConnection):
    """Minimal connection stand-in with optional async/sync close."""

    def __init__(
        self,
        secret_arn=DUMMY_ARN,
        async_close=False,
        raise_close=False,
    ):
        """Initialize the fake connection."""
        super().__init__(readonly=True)
        self.secret_arn = secret_arn
        self._async = async_close
        self._raise = raise_close
        self.closed = False

    async def execute_query(self, sql, parameters=None, max_rows=0):  # pragma: no cover
        """Unused query stub required by the abstract base."""
        return []

    async def check_connection_health(self):  # pragma: no cover
        """Unused health stub required by the abstract base."""
        return True

    # Intentionally synchronous: exercises close_all's handling of a close()
    # that may return an awaitable.
    def close(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        """Close synchronously, or return a coroutine when async_close is set."""
        if self._async:

            async def _c():
                if self._raise:
                    raise RuntimeError('close failed')
                self.closed = True

            return _c()
        if self._raise:
            raise RuntimeError('sync close failed')
        self.closed = True
        return None


def test_set_get_roundtrip():
    """A stored connection is retrievable by its exact key."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    assert m.get(M, 'id', 'host', 'DB2DB', 50443) is c


def test_get_missing_returns_none():
    """A key with no entry returns None."""
    assert DBConnectionMap().get(M, 'id', 'host', 'DB2DB', 50443) is None


def test_get_fallback_when_identifier_equals_endpoint():
    """When instance_identifier == db_endpoint, a single matching stored conn is found."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'real-id', 'host', 'DB2DB', c, 50443)
    # Caller did not supply an identifier (defaults to db_endpoint).
    assert m.get(M, 'host', 'host', 'DB2DB', 50443) is c


def test_ambiguous_fallback_refuses_instead_of_picking_by_dict_order():
    """Two connections under different identifiers must not be silently disambiguated.

    instance_identifier IS part of the cache key, so a read-only and an admin connection to
    the same endpoint/database/port coexist. The fallback never compared key[1] and returned
    the first match in dict order, and run_query omits secret_arn (so _secret_ok is
    vacuously true and cannot disambiguate) -- meaning a query that omitted
    instance_identifier could silently execute as the admin.
    """
    m = DBConnectionMap()
    ro, admin = FakeConn(), FakeConn()
    ro.secret_arn = 'arn:readonly'  # pragma: allowlist secret
    admin.secret_arn = 'arn:master'  # pragma: allowlist secret
    m.set(M, 'ro', 'host', 'DB2DB', ro, 50443)
    m.set(M, 'admin', 'host', 'DB2DB', admin, 50443)

    with pytest.raises(AmbiguousConnectionError) as exc:
        m.get(M, 'host', 'host', 'DB2DB', 50443)
    # The message must name both candidates so the caller can pick.
    assert 'admin' in str(exc.value) and 'ro' in str(exc.value)


def test_ambiguity_is_resolved_by_an_explicit_identifier():
    """Naming the identifier selects deterministically, with no ambiguity error."""
    m = DBConnectionMap()
    ro, admin = FakeConn(), FakeConn()
    m.set(M, 'ro', 'host', 'DB2DB', ro, 50443)
    m.set(M, 'admin', 'host', 'DB2DB', admin, 50443)
    assert m.get(M, 'ro', 'host', 'DB2DB', 50443) is ro
    assert m.get(M, 'admin', 'host', 'DB2DB', 50443) is admin


def test_ambiguity_not_raised_for_different_endpoints_or_databases():
    """Entries that differ on endpoint/database/port are not candidates, so no ambiguity."""
    m = DBConnectionMap()
    a, b, c = FakeConn(), FakeConn(), FakeConn()
    m.set(M, 'x', 'host', 'DB2DB', a, 50443)
    m.set(M, 'y', 'other-host', 'DB2DB', b, 50443)  # different endpoint
    m.set(M, 'z', 'host', 'OTHERDB', c, 50443)  # different database
    assert m.get(M, 'host', 'host', 'DB2DB', 50443) is a


def test_ambiguous_candidates_filtered_by_secret_arn():
    """A supplied secret_arn narrows the candidates, so a unique match is still returned."""
    m = DBConnectionMap()
    ro, admin = FakeConn(), FakeConn()
    ro.secret_arn = 'arn:readonly'  # pragma: allowlist secret
    admin.secret_arn = 'arn:master'  # pragma: allowlist secret
    m.set(M, 'ro', 'host', 'DB2DB', ro, 50443)
    m.set(M, 'admin', 'host', 'DB2DB', admin, 50443)
    got = m.get(
        M,
        'host',
        'host',
        'DB2DB',
        50443,
        secret_arn='arn:readonly',  # pragma: allowlist secret
    )
    assert got is ro


def test_get_secret_arn_match_filters_exact_and_fallback():
    """A secret_arn that differs from the cached connection's is never returned.

    Guards against crossing a connection built with different credentials back to
    a caller (both the exact-match and the identifier==endpoint fallback paths).
    """
    m = DBConnectionMap()
    c = FakeConn(secret_arn=DUMMY_ARN)
    m.set(M, 'real-id', 'host', 'DB2DB', c, 50443)

    # Exact identifier, matching secret -> returned; mismatched secret -> None.
    assert m.get(M, 'real-id', 'host', 'DB2DB', 50443, secret_arn=DUMMY_ARN) is c
    assert m.get(M, 'real-id', 'host', 'DB2DB', 50443, secret_arn=DUMMY_ARN_XYZ) is None

    # Fallback path (identifier defaults to endpoint): same secret filtering applies.
    assert m.get(M, 'host', 'host', 'DB2DB', 50443, secret_arn=DUMMY_ARN) is c
    assert m.get(M, 'host', 'host', 'DB2DB', 50443, secret_arn=DUMMY_ARN_XYZ) is None

    # secret_arn=None preserves the original, secret-agnostic behavior.
    assert m.get(M, 'host', 'host', 'DB2DB', 50443) is c


def test_get_validation():
    """Get rejects a missing method or database."""
    m = DBConnectionMap()
    with pytest.raises(ValueError):
        m.get(cast(ConnectionMethod, None), 'id', 'host', 'DB2DB', 50443)
    with pytest.raises(ValueError):
        m.get(M, 'id', 'host', '', 50443)


def test_set_validation():
    """Set rejects an empty database or a None connection."""
    m = DBConnectionMap()
    with pytest.raises(ValueError):
        m.set(M, 'id', 'host', '', FakeConn(), 50443)
    with pytest.raises(ValueError):
        m.set(M, 'id', 'host', 'DB2DB', cast(AbstractDBConnection, None), 50443)


def test_remove_existing_and_missing():
    """Remove deletes an entry and tolerates a missing key."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    m.remove(M, 'id', 'host', 'DB2DB', 50443)
    assert m.get(M, 'id', 'host', 'DB2DB', 50443) is None
    m.remove(M, 'id', 'host', 'DB2DB', 50443)  # no error
    with pytest.raises(ValueError):
        m.remove(M, 'id', 'host', '', 50443)


def test_get_keys():
    """get_keys returns one dict per connection with its secret ARN."""
    m = DBConnectionMap()
    m.set(
        M,
        'id',
        'host',
        'DB2DB',
        FakeConn(secret_arn=DUMMY_ARN_XYZ),
        50443,
    )
    keys = m.get_keys()
    assert keys[0]['db_endpoint'] == 'host'
    assert keys[0]['secret_arn'] == DUMMY_ARN_XYZ


def test_close_all_sync():
    """close_all closes synchronous connections and clears the map."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    m.close_all()
    assert c.closed is True and m.map == {}


def test_close_all_async_no_running_loop():
    """close_all drives async close() via asyncio.run when no loop is running."""
    m = DBConnectionMap()
    c = FakeConn(async_close=True)
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    m.close_all()
    assert c.closed is True and m.map == {}


def test_close_all_tolerates_errors():
    """A failing close does not prevent the map from clearing."""
    m = DBConnectionMap()
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(raise_close=True), 50443)
    m.close_all()
    assert m.map == {}


async def test_close_all_with_running_loop():
    """close_all schedules async closes on the running loop and clears the map."""
    m = DBConnectionMap()
    c = FakeConn(async_close=True)
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    m.close_all()
    await asyncio.sleep(0.05)  # let the scheduled close task run
    assert m.map == {}
    assert c.closed is True


async def test_close_all_running_loop_tolerates_task_error():
    """A failing async close on the running loop is logged and the map still clears."""
    m = DBConnectionMap()
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(async_close=True, raise_close=True), 50443)
    m.close_all()
    await asyncio.sleep(0.05)  # let the failing close task run + done-callback fire
    assert m.map == {}


async def test_close_all_running_loop_logs_scheduling_warning(mocker):
    """close_all logs a warning at scheduling time, before the map is cleared.

    On the running-loop path, close tasks are scheduled but not awaited, and the map
    is cleared unconditionally right after. If the loop stops before a scheduled task
    runs, that close silently never happens with no trace -- so a diagnostic must be
    emitted at scheduling time, not only from the (possibly-never-firing) done
    callback.
    """
    log_warning = mocker.patch(
        'awslabs.db2_mcp_server.connection.db_connection_map.logger.warning'
    )
    m = DBConnectionMap()
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(async_close=True), 50443)
    m.close_all()
    assert log_warning.called
    assert 'Scheduling' in log_warning.call_args_list[0].args[0]
    await asyncio.sleep(0.05)  # let the scheduled close task run
    assert m.map == {}


def test_set_closes_replaced_connection_on_overwrite():
    """Re-setting the same key with a new connection closes the previous one (no leak)."""
    m = DBConnectionMap()
    old = FakeConn()
    new = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', old, 50443)
    m.set(M, 'id', 'host', 'DB2DB', new, 50443)
    assert old.closed is True
    assert m.get(M, 'id', 'host', 'DB2DB', 50443) is new


def test_set_same_connection_not_closed():
    """Setting the identical connection object again does not close it."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    m.set(M, 'id', 'host', 'DB2DB', c, 50443)
    assert c.closed is False


def test_set_closes_replaced_async_no_running_loop():
    """Overwriting with an async-close connection drives close() via asyncio.run."""
    m = DBConnectionMap()
    old = FakeConn(async_close=True)
    m.set(M, 'id', 'host', 'DB2DB', old, 50443)
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(), 50443)
    assert old.closed is True


def test_set_close_error_is_tolerated():
    """A failing close on the replaced connection is logged, not raised."""
    m = DBConnectionMap()
    old = FakeConn(raise_close=True)
    m.set(M, 'id', 'host', 'DB2DB', old, 50443)
    # Should not raise despite the replaced connection's close() throwing.
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(), 50443)


async def test_set_closes_replaced_async_running_loop():
    """On a running loop, the replaced async connection is closed via a scheduled task."""
    m = DBConnectionMap()
    old = FakeConn(async_close=True)
    m.set(M, 'id', 'host', 'DB2DB', old, 50443)
    m.set(M, 'id', 'host', 'DB2DB', FakeConn(), 50443)
    await asyncio.sleep(0.05)  # let the scheduled close task run
    assert old.closed is True


async def test_set_closes_replaced_async_running_loop_tolerates_error():
    """A failing async close on the running loop is logged; the map still updates."""
    m = DBConnectionMap()
    old = FakeConn(async_close=True, raise_close=True)
    new = FakeConn()
    m.set(M, 'id', 'host', 'DB2DB', old, 50443)
    m.set(M, 'id', 'host', 'DB2DB', new, 50443)
    await asyncio.sleep(0.05)  # let the failing close task run + done-callback fire
    assert m.get(M, 'id', 'host', 'DB2DB', 50443) is new
