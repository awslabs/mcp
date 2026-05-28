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

"""Database connection map for MySQL MCP Server."""

import json
import threading
from awslabs.mysql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from enum import Enum
from loguru import logger
from typing import List


class DatabaseType(str, Enum):
    """RDS engine the MCP server is connected to.

    Values match the strings AWS RDS expects in the ``Engine`` parameter
    of ``create_db_cluster`` and ``create_db_instance``, so callers can
    forward ``DatabaseType.value`` directly into boto3 calls without a
    translation table.

    This enum is used to gate which connection methods are valid:

    * ``rdsapi`` (RDS Data API) is supported only on Aurora MySQL.
    * ``mysqlwire_iam`` (IAM authentication via generate_db_auth_token)
      is supported on Aurora MySQL and RDS MySQL. RDS MariaDB does not
      support IAM auth.
    * ``mysqlwire`` (direct MySQL wire protocol) is supported on every
      engine in the enum.

    Self-hosted MySQL / MariaDB endpoints do NOT use this enum. The
    wire-protocol path accepts any host without requiring an engine
    type; callers that want to connect to a self-hosted instance simply
    omit ``database_type`` and pass the endpoint directly.
    """

    AURORA_MYSQL = 'aurora-mysql'
    RDS_MYSQL = 'mysql'
    RDS_MARIADB = 'mariadb'


class ConnectionMethod(str, Enum):
    """Connection method enumeration."""

    RDS_API = 'rdsapi'
    MYSQL_WIRE_PROTOCOL = 'mysqlwire'
    MYSQL_WIRE_IAM_PROTOCOL = 'mysqlwire_iam'


# Which (engine, connection-method) pairs are supported.
#
# This is the single source of truth for engine/method routing, used both
# at request validation time (server.py) and by the test suite. When adding
# a new engine or connection method, update this matrix and the tests will
# enforce that the new combination is either handled or explicitly rejected.
SUPPORTED_CONNECTION_METHODS: dict[DatabaseType, frozenset[ConnectionMethod]] = {
    DatabaseType.AURORA_MYSQL: frozenset(
        {
            ConnectionMethod.RDS_API,
            ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
        }
    ),
    # RDS MySQL: no Data API, but IAM auth via generate_db_auth_token works.
    DatabaseType.RDS_MYSQL: frozenset(
        {
            ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
        }
    ),
    # RDS MariaDB: wire protocol only. No Data API, no IAM auth.
    DatabaseType.RDS_MARIADB: frozenset(
        {
            ConnectionMethod.MYSQL_WIRE_PROTOCOL,
        }
    ),
}


def is_connection_method_supported(
    database_type: DatabaseType, connection_method: ConnectionMethod
) -> bool:
    """Return True iff the (engine, method) pair is supported.

    Centralising this lookup keeps server.py free of nested if/else chains
    and makes the supported-methods table easy to test exhaustively.
    """
    return connection_method in SUPPORTED_CONNECTION_METHODS.get(database_type, frozenset())


class DBConnectionMap:
    """Manages MySQL DB connection map."""

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
        port: int | None = None,
    ) -> AbstractDBConnection | None:
        """Return a stored connection or None.

        Two-phase lookup:

        1. **Strict 5-tuple match.** Preserves the original behaviour for
           callers that pass exact (method, cluster, endpoint, database,
           port) tuples — for example, the dedupe check inside
           ``internal_connect_to_database`` immediately after a successful
           connect.

        2. **Relaxed scan on cluster or endpoint.** If the strict match
           misses, scan for an entry that matches ``(method, database)``
           plus *either* ``cluster_identifier`` *or* ``db_endpoint``,
           depending on which one the caller provided. This handles the
           common case where a user calls ``connect_to_database`` with
           ``db_endpoint=''`` (auto-resolved by the connect path to the
           cluster's writer endpoint) and then calls ``run_query`` with
           the same ``db_endpoint=''`` they originally supplied.

        The relaxed scan returns ``None`` if more than one entry matches:
        ambiguity is preferable to silently picking one. The strict-match
        path is unaffected.

        Port handling
        -------------
        ``port`` is ``None`` by default to make the lookup tolerant of
        callers that do not know the port. ``run_query`` and
        ``get_table_schema`` are MCP tools that do not accept a ``port``
        parameter; they call this function without supplying one. With
        ``port=None``:

        * The strict 5-tuple match falls back to the standard MySQL port
          3306 so that connections registered with the default port
          continue to be found by name (existing behaviour).
        * The relaxed scan ignores port, which is the only way a user
          whose database listens on a non-default port (e.g. 3307) can
          reach their connection through ``run_query``. Without this,
          a 3306 lookup would never match a 3307-stored entry and the
          connection would be unreachable through the tool surface.

        When the caller *does* supply a port explicitly (e.g. the dedupe
        check inside ``internal_connect_to_database`` that knows the exact
        port used for the connect), the strict match uses that port
        verbatim and the relaxed scan also filters by it, so explicit
        port intent is honoured.

        The ambiguity guard (return ``None`` when more than one match)
        protects the rare multi-port-same-cluster case from silently
        routing to the wrong port.
        """
        if not method:
            raise ValueError('method cannot be None')

        if not database:
            raise ValueError('database cannot be None or empty')

        # Port semantics:
        #   None  -> "caller does not know / care about port" (run_query etc.)
        #            Strict path falls back to 3306; relaxed scan ignores port.
        #   int   -> "caller knows the port" (dedupe in connect path).
        #            Strict path uses it verbatim; relaxed scan filters by it.
        port_supplied = port is not None
        strict_port = port if port_supplied else 3306

        with self._lock:
            # Phase 1: strict 5-tuple
            hit = self.map.get((method, cluster_identifier, db_endpoint, database, strict_port))
            if hit is not None:
                return hit

            # Phase 2: relaxed scan on whichever identifier the caller has
            if cluster_identifier:
                candidates = [
                    v
                    for k, v in self.map.items()
                    if k[0] == method
                    and k[1] == cluster_identifier
                    and k[3] == database
                    and (not port_supplied or k[4] == port)
                ]
            elif db_endpoint:
                candidates = [
                    v
                    for k, v in self.map.items()
                    if k[0] == method
                    and k[2] == db_endpoint
                    and k[3] == database
                    and (not port_supplied or k[4] == port)
                ]
            else:
                return None

            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                logger.warning(
                    f'Relaxed lookup for ({method}, '
                    f'cluster={cluster_identifier!r}, endpoint={db_endpoint!r}, '
                    f'database={database!r}, port={port!r}) matched {len(candidates)} '
                    'entries; returning None to avoid silent ambiguity.'
                )
                return None
            return None

    def set(
        self,
        method: ConnectionMethod,
        cluster_identifier: str,
        db_endpoint: str,
        database: str,
        conn: AbstractDBConnection,
        port: int = 3306,
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
        port: int = 3306,
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

    def has_connection_for_cluster(self, cluster_identifier: str) -> bool:
        """Return True if any cached connection exists for the given cluster.

        Unlike ``get()``, which requires an exact (method, cluster, endpoint,
        database, port) match, this helper scans by ``cluster_identifier``
        alone. Callers that just want to know "is this cluster connected at
        all" (e.g., the ``is_database_connected`` MCP tool) can use this
        without knowing the endpoint, database, or port that was used when
        the connection was created.
        """
        if not cluster_identifier:
            return False
        with self._lock:
            return any(key[1] == cluster_identifier for key in self.map.keys())

    async def close_all(self) -> None:
        """Close all connections and clear the map."""
        with self._lock:
            connections = list(self.map.items())
            self.map.clear()
        for key, conn in connections:
            try:
                await conn.close()
            except Exception as e:
                logger.warning(f'Failed to close connection {key}: {e}')

    def close_all_sync(self) -> None:
        """Best-effort synchronous close for use outside the event loop.

        Calls each pool's synchronous close() without awaiting wait_closed()
        or acquiring async locks. Use when the event loop is no longer running.
        """
        with self._lock:
            for key, conn in self.map.items():
                try:
                    if hasattr(conn, 'pool') and conn.pool is not None:
                        conn.pool.close()
                except Exception as e:
                    logger.warning(f'Failed to sync-close connection {key}: {e}')
            self.map.clear()
