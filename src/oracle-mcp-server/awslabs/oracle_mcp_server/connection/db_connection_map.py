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

"""Database connection map for oracle MCP Server."""

import asyncio
import inspect
import threading
from awslabs.oracle_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from enum import Enum
from loguru import logger
from typing import List


class ConnectionMethod(str, Enum):
    """Connection method enumeration."""

    ORACLE_PASSWORD = 'oracle_password'  # pragma: allowlist secret


class DBConnectionMap:
    """Manages Oracle DB connection map."""

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
        port: int = 1521,
    ) -> AbstractDBConnection | None:
        """Get a database connection from the map.

        If no exact match is found and instance_identifier equals db_endpoint (i.e. the
        caller did not supply an explicit identifier), fall back to searching for any
        connection that matches on method, db_endpoint, database, and port regardless of
        the instance_identifier that was used at connect time.
        """
        if not method:
            raise ValueError('method cannot be None')

        if not database:
            raise ValueError('database cannot be None or empty')

        with self._lock:
            conn = self.map.get((method, instance_identifier, db_endpoint, database, port))
            if conn is not None:
                return conn
            # Fallback: if the caller did not supply an explicit instance_identifier
            # (signalled by instance_identifier == db_endpoint), search for any stored
            # connection that matches on the remaining fields.
            if instance_identifier == db_endpoint:
                for key, stored_conn in self.map.items():
                    if (
                        key[0] == method
                        and key[2] == db_endpoint
                        and key[3] == database
                        and key[4] == port
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
        port: int = 1521,
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
        port: int = 1521,
    ) -> None:
        """Remove a database connection from the map."""
        if not database:
            raise ValueError('database cannot be None or empty')

        with self._lock:
            try:
                self.map.pop((method, instance_identifier, db_endpoint, database, port))
            except KeyError:
                logger.info(
                    f'Try to remove a non-existing connection. {method} {instance_identifier} {db_endpoint} {database} {port}'
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
                    'service_name': getattr(conn, 'service_name', None),
                    'sid': getattr(conn, 'sid', None),
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

                async def _close_all():
                    results = await asyncio.gather(*coros, return_exceptions=True)
                    for k, r in zip(keys, results):
                        if isinstance(r, Exception):
                            logger.warning(f'Failed to close connection {k}: {r}')

                try:
                    asyncio.run(_close_all())
                except RuntimeError:
                    logger.warning('Event loop active; connections may not be fully closed')
            self.map.clear()
