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

"""Test fixtures for mssql MCP Server tests."""

import asyncio
import pytest
from awslabs.mssql_mcp_server.connection.db_connection_map import DBConnectionMap
from awslabs.mssql_mcp_server.connection.pymssql_pool_connection import PymssqlPoolConnection


class MockPymssqlConnection:
    """Mock pymssql connection."""

    def __init__(self):
        """Initialize mock connection with a cursor."""
        self._cursor = MockPymssqlCursor()

    def cursor(self):
        """Return the mock cursor."""
        return self._cursor

    def rollback(self):
        """No-op rollback."""
        pass

    def close(self):
        """No-op close."""
        pass


class MockPymssqlCursor:
    """Mock pymssql cursor."""

    def __init__(self):
        """Initialize mock cursor with test data."""
        self.description = [('id',), ('name',)]
        self._rows = [(1, 'test')]

    def execute(self, sql, params=None):
        """No-op execute."""
        pass

    def fetchall(self):
        """Return mock rows."""
        return self._rows


class DummyCtx:
    """Dummy context for testing."""

    async def error(self, message):
        """No-op error handler."""
        pass


@pytest.fixture
def mock_pymssql_connection():
    """Fixture providing a mock pymssql connection."""
    return MockPymssqlConnection()


@pytest.fixture
def mock_db_connection_map():
    """Fixture providing an empty DBConnectionMap."""
    return DBConnectionMap()


@pytest.fixture
def mock_pool_connection(mock_pymssql_connection):
    """Create a PymssqlPoolConnection with mocked internals."""
    conn = PymssqlPoolConnection(
        host='localhost',
        port=1433,
        database='testdb',
        readonly=True,
        secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test',  # pragma: allowlist secret
        region='us-east-1',
        is_test=True,
    )
    conn._pool = asyncio.Queue(maxsize=10)
    conn._pool.put_nowait(mock_pymssql_connection)
    return conn
