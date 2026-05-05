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
        """Close all connections and clear the map."""
        with self._lock:
            for key, conn in self.map.items():
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f'Failed to close connection {key}: {e}')
            self.map.clear()
