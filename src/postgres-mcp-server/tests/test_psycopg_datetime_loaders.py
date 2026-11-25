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

"""PG Wire must not fail a query over a date or time Python can't represent.

PostgreSQL accepts ``infinity``, BC dates, years after 9999, ``24:00:00`` and very
long intervals. psycopg's default loaders raise ``DataError`` for them, which made
``run_query`` return an error for the whole result set. The loaders registered on
each pool connection return the server's text for those values instead and load
everything else as before.
"""

import pytest
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import (
    _DATETIME_LOADERS,
    PsycopgPoolConnection,
    _configure_connection,
)
from datetime import date, datetime, time, timedelta, timezone
from psycopg import adapters, postgres
from psycopg.adapt import AdaptersMap
from psycopg.pq import Format
from unittest.mock import AsyncMock, MagicMock, patch


def _load(type_name, text):
    """Load ``text`` with the registered loader for ``type_name``, as psycopg would."""
    # No connection: psycopg then assumes ISO dates and UTC, as a default server sends.
    loader = _DATETIME_LOADERS[type_name](postgres.types[type_name].oid, None)
    return loader.load(text.encode())


@pytest.mark.parametrize(
    'type_name,text',
    [
        ('date', 'infinity'),
        ('date', '-infinity'),
        ('date', '0044-03-15 BC'),
        ('date', '12000-01-01'),
        ('timestamp', 'infinity'),
        ('timestamp', '2026-01-01 10:00:00 BC'),
        ('timestamptz', '-infinity'),
        ('time', '24:00:00'),
        ('timetz', '24:00:00+00'),
        ('interval', '100000000 years'),
    ],
)
def test_out_of_range_value_comes_back_as_postgres_text(type_name, text):
    """A value Python can't hold is returned as the server sent it."""
    assert _load(type_name, text) == text


@pytest.mark.parametrize(
    'type_name,text,expected',
    [
        ('date', '2026-01-01', date(2026, 1, 1)),
        ('timestamp', '2026-01-01 12:30:45.123456', datetime(2026, 1, 1, 12, 30, 45, 123456)),
        (
            'timestamptz',
            '2026-01-01 12:30:00+00',
            datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc),
        ),
        ('time', '12:30:00', time(12, 30)),
        ('interval', '1 day 02:03:04', timedelta(days=1, hours=2, minutes=3, seconds=4)),
    ],
)
def test_in_range_value_loads_as_before(type_name, text, expected):
    """Values Python can hold still load to the usual datetime objects."""
    assert _load(type_name, text) == expected


async def test_configure_connection_registers_every_loader():
    """Each new connection gets the loader for every datetime type."""
    conn = MagicMock(adapters=AdaptersMap(adapters))
    await _configure_connection(conn)
    for type_name, loader in _DATETIME_LOADERS.items():
        oid = postgres.types[type_name].oid
        assert conn.adapters.get_loader(oid, Format.TEXT) is loader


async def test_pool_configures_new_connections():
    """The pool is created with the hook that registers the loaders."""
    with (
        patch(
            'awslabs.postgres_mcp_server.connection.psycopg_pool_connection.AsyncConnectionPool'
        ) as mock_pool_class,
        patch.object(
            PsycopgPoolConnection,
            '_get_credentials_from_secret',
            return_value=('db_user', 'db_password'),
        ),
    ):
        mock_pool_class.return_value = AsyncMock()
        conn = PsycopgPoolConnection(
            host='localhost',
            port=5432,
            database='test_db',
            readonly=True,
            secret_arn='arn:secret',  # pragma: allowlist secret
            db_user='',
            region='us-east-1',
            is_test=True,
        )
        await conn.initialize_pool()

    assert mock_pool_class.call_args.kwargs['configure'] is _configure_connection
