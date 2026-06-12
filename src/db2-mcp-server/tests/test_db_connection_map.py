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
    """When instance_identifier == db_endpoint, any matching stored conn is found."""
    m = DBConnectionMap()
    c = FakeConn()
    m.set(M, 'real-id', 'host', 'DB2DB', c, 50443)
    # Caller did not supply an identifier (defaults to db_endpoint).
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
