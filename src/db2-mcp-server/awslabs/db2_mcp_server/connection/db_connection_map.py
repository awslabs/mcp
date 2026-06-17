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

"""Database connection map for the RDS for Db2 MCP Server."""

import asyncio
import inspect
import threading
from awslabs.db2_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from enum import Enum
from loguru import logger
from typing import List, Optional


# RDS for Db2 in this ecosystem is SSL-only: the provisioning skill enforces
# DB2COMM=SSL with ssl_svcename=50443 and leaves the plain TCP listener (8392)
# dormant and closed in the security group. 50443 is therefore the default.
DEFAULT_DB2_SSL_PORT = 50443


class ConnectionMethod(str, Enum):
    """Connection method enumeration."""

    # Enum member naming the password-auth connection method; not a credential.
    DB2_PASSWORD = 'db2_password'  # nosec B105  # pragma: allowlist secret


class DBConnectionMap:
    """Manages Db2 DB connection map."""

    def __init__(self):
        """Initialize the connection map."""
        self.map = {}
        self._lock = threading.Lock()

    def get(
        self,
        method: ConnectionMethod,
        instance_identifier: str,
        db_endpoint: str,
        database: str,
        port: int = DEFAULT_DB2_SSL_PORT,
        secret_arn: Optional[str] = None,
    ) -> AbstractDBConnection | None:
        """Get a database connection from the map.

        If no exact match is found and instance_identifier equals db_endpoint (i.e. the
        caller did not supply an explicit identifier), fall back to searching for any
        connection that matches on method, db_endpoint, database, and port regardless of
        the instance_identifier that was used at connect time.

        When ``secret_arn`` is provided, only a connection created with the same secret
        is returned (for both the exact-match and fallback paths), so a cached connection
        built with different credentials is never crossed back to a caller. When
        ``secret_arn`` is None the secret is not considered (back-compatible).
        """
        if not method:
            raise ValueError('method cannot be None')

        if not database:
            raise ValueError('database cannot be None or empty')

        def _secret_ok(c: AbstractDBConnection) -> bool:
            return secret_arn is None or getattr(c, 'secret_arn', None) == secret_arn

        with self._lock:
            conn = self.map.get((method, instance_identifier, db_endpoint, database, port))
            if conn is not None and _secret_ok(conn):
                return conn
            if instance_identifier == db_endpoint:
                for key, stored_conn in self.map.items():
                    if (
                        key[0] == method
                        and key[2] == db_endpoint
                        and key[3] == database
                        and key[4] == port
                        and _secret_ok(stored_conn)
                    ):
                        return stored_conn
            return None

    def set(
        self,
        method: ConnectionMethod,
        instance_identifier: str,
        db_endpoint: str,
        database: str,
        conn: AbstractDBConnection,
        port: int = DEFAULT_DB2_SSL_PORT,
    ) -> None:
        """Set a database connection in the map."""
        if not database:
            raise ValueError('database cannot be None or empty')

        if not conn:
            raise ValueError('conn cannot be None')

        with self._lock:
            self.map[(method, instance_identifier, db_endpoint, database, port)] = conn

    def remove(
        self,
        method: ConnectionMethod,
        instance_identifier: str,
        db_endpoint: str,
        database: str,
        port: int = DEFAULT_DB2_SSL_PORT,
    ) -> None:
        """Remove a database connection from the map."""
        if not database:
            raise ValueError('database cannot be None or empty')

        with self._lock:
            try:
                self.map.pop((method, instance_identifier, db_endpoint, database, port))
            except KeyError:
                logger.info(
                    f'Try to remove a non-existing connection. {method} {instance_identifier} '
                    f'{db_endpoint} {database} {port}'
                )

    def get_keys(self) -> List[dict]:
        """Get all connection keys as a list of dicts."""
        entries: List[dict] = []
        with self._lock:
            for key, conn in self.map.items():
                entry = {
                    'connection_method': key[0],
                    'instance_identifier': key[1],
                    'db_endpoint': key[2],
                    'database': key[3],
                    'port': key[4],
                    'secret_arn': getattr(conn, 'secret_arn', None),
                }
                entries.append(entry)
        return entries

    def close_all(self) -> None:
        """Close all connections and clear the map."""
        with self._lock:
            coros = []
            keys = []
            for key, conn in self.map.items():
                try:
                    result = conn.close()
                    if inspect.isawaitable(result):
                        coros.append(result)
                        keys.append(key)
                except Exception as e:
                    logger.warning(f'Failed to close connection {key}: {e}')
            if coros:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    for key, coro in zip(keys, coros):
                        task = loop.create_task(coro)

                        def _done_cb(t, k=key):
                            if t.cancelled():
                                logger.warning(f'Close task for connection {k} was cancelled')
                            elif t.exception():
                                logger.warning(f'Failed to close connection {k}: {t.exception()}')

                        task.add_done_callback(_done_cb)
                    logger.info('Scheduled connection close tasks on running event loop')
                else:

                    async def _close_all():
                        results = await asyncio.gather(*coros, return_exceptions=True)
                        for k, r in zip(keys, results):
                            if isinstance(r, Exception):
                                logger.warning(f'Failed to close connection {k}: {r}')

                    asyncio.run(_close_all())
            self.map.clear()
