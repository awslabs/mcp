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

"""Test fixtures for oracle MCP Server tests."""

import pytest
from awslabs.oracle_mcp_server.connection.db_connection_map import (
    DBConnectionMap,
)
from awslabs.oracle_mcp_server.connection.oracledb_pool_connection import OracledbPoolConnection


class MockOracleConnection:
    """Mock oracledb async connection."""

    def __init__(self):
        """Initialize mock connection."""
        self._cursor = MockOracleCursor()

    async def execute(self, sql, params=None):
        """Execute a query (no-op)."""
        pass

    async def rollback(self):
        """Rollback (no-op)."""
        pass

    def cursor(self):
        """Return the mock cursor."""
        return self._cursor

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, *args):
        """Exit async context."""
        pass


class MockOracleCursor:
    """Mock oracledb async cursor."""

    def __init__(self):
        """Initialize mock cursor."""
        self.description = [('ID',), ('NAME',)]
        self._rows = [(1, 'test')]

    async def execute(self, sql, params=None):
        """Execute a query (no-op)."""
        pass

    async def fetchall(self):
        """Return mock rows."""
        return self._rows

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, *args):
        """Exit async context."""
        pass


class MockOraclePool:
    """Mock oracledb AsyncConnectionPool."""

    def __init__(self):
        """Initialize mock pool."""
        self._conn = MockOracleConnection()

    def acquire(self):
        """Acquire a mock connection."""
        return self._conn

    async def close(self):
        """Close the pool (no-op)."""
        pass


@pytest.fixture
def mock_oracle_pool():
    """Return a MockOraclePool instance."""
    return MockOraclePool()


@pytest.fixture
def mock_db_connection_map():
    """Return an empty DBConnectionMap."""
    return DBConnectionMap()


@pytest.fixture
def mock_pool_connection():
    """Create an OracledbPoolConnection with mocked pool."""
    conn = OracledbPoolConnection(
        host='localhost',
        port=1521,
        database='ORCL',
        readonly=True,
        secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test',  # pragma: allowlist secret
        region='us-east-1',
        service_name='ORCL',
        is_test=True,
    )
    conn.pool = MockOraclePool()  # type: ignore[assignment]
    return conn
