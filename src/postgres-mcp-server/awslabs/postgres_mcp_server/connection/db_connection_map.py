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

"""Database connection map for postgres MCP Server."""

import asyncio
import json
import threading
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from enum import Enum
from loguru import logger
from typing import List


class DatabaseType(str, Enum):
    """Database type enumeration."""

    APG = ('APG',)
    RPG = 'RPG'


class ConnectionMethod(str, Enum):
    """Connection method enumeration."""

    RDS_API = 'rdsapi'
    PG_WIRE_PROTOCOL = 'pgwire'
    PG_WIRE_IAM_PROTOCOL = 'pgwire_iam'


class DBConnectionMap:
    """Manages Postgres DB connection map."""

    def __init__(self):
        """Initialize the connection map."""
        self.map = {}
        self._lock = threading.Lock()

    def get(
        self,
        method: ConnectionMethod,
        cluster_identifier: str,
        db_endpoint: str,
        database: str,
        port: int = 5432,
    ) -> AbstractDBConnection | None:
        """Get a database connection from the map."""
        if not method:
            raise ValueError('method cannot be None')

        if not database:
            raise ValueError('database cannot be None or empty')

        with self._lock:
            return self.map.get((method, cluster_identifier, db_endpoint, database, port))

    def set(
        self,
        method: ConnectionMethod,
        cluster_identifier: str,
        db_endpoint: str,
        database: str,
        conn: AbstractDBConnection,
        port: int = 5432,
    ) -> None:
        """Set a database connection in the map."""
        if not database:
            raise ValueError('database cannot be None or empty')

        if not conn:
            raise ValueError('conn cannot be None')

        with self._lock:
            self.map[(method, cluster_identifier, db_endpoint, database, port)] = conn

    def remove(
        self,
        method: ConnectionMethod,
        cluster_identifier: str,
        db_endpoint: str,
        database: str,
        port: int = 5432,
    ) -> None:
        """Remove a database connection from the map."""
        if not database:
            raise ValueError('database cannot be None or empty')

        with self._lock:
            try:
                self.map.pop((method, cluster_identifier, db_endpoint, database, port))
            except KeyError:
                logger.info(
                    f'Try to remove a non-existing connection. {method} {cluster_identifier} {db_endpoint} {database} {port}'
                )

    def remove_connection(self, conn: AbstractDBConnection) -> bool:
        """Remove a connection by object identity, regardless of its map key.

        Prefer this over ``remove()`` when evicting a connection you already
        hold a reference to (e.g. cleaning up a failed/rejected connection in
        ``connect_to_database``).

        Why: the map key is built from the AWS-*resolved* endpoint/port, and
        ``set()`` does not receive ``port`` (so it is always stored as the
        5432 default), whereas callers pass the *caller-supplied* endpoint/port
        to ``get()``/``remove()``. Those keys can diverge (empty db_endpoint,
        non-5432 port, differing host casing), which makes key-based
        ``remove()`` silently no-op and leave the connection cached. Evicting
        by identity sidesteps that entirely. See the tracked follow-up on
        connection-map key normalization for the broader fix.

        Returns:
            True if a matching connection was found and removed, else False.
        """
        with self._lock:
            for key, existing in list(self.map.items()):
                if existing is conn:
                    del self.map[key]
                    return True
        return False

    def get_keys_json(self) -> str:
        """Get all connection keys as JSON string."""
        entries: List[dict] = []
        with self._lock:
            for key in self.map.keys():
                entry = {
                    'connection_method': key[0],
                    'cluster_identifier': key[1],
                    'db_endpoint': key[2],
                    'database': key[3],
                    'port': key[4],
                }
                entries.append(entry)
        return json.dumps(entries, indent=2)

    def close_all(self) -> None:
        """Close all connections and clear the map.

        Connection ``close()`` methods are coroutines (see
        ``AbstractDBConnection.close``). When ``close_all`` is called from
        sync code (e.g. server.main's finally block), we drive each
        coroutine to completion via ``asyncio.run`` so the underlying
        pool workers actually get a chance to shut down. When called
        from inside a running event loop, we fall back to scheduling
        the coroutine and waiting on it via ``run_until_complete`` is
        not possible, so we just drop the coroutine on the floor with a
        warning — the loop's own teardown will reap the workers.
        """
        with self._lock:
            connections = list(self.map.items())
            self.map.clear()

        for key, conn in connections:
            try:
                result = conn.close()
            except Exception as e:
                logger.warning(f'Failed to close connection {key}: {e}')
                continue

            if asyncio.iscoroutine(result):
                try:
                    asyncio.run(result)
                except RuntimeError:
                    # Already inside a running loop; closing the
                    # coroutine cancels it cleanly without spawning a
                    # new event loop. The pool workers will be cleaned
                    # up when the outer loop tears down.
                    result.close()
                except Exception as e:
                    logger.warning(f'Failed to await close() for {key}: {e}')
