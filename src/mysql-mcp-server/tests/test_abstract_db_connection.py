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

"""Tests for AbstractDBConnection interface."""

import pytest
from awslabs.mysql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from typing import Any, Dict, List, Optional


class ConcreteDBConnection(AbstractDBConnection):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self, readonly: bool):
        """Initialize test connection."""
        super().__init__(readonly)
        self._closed = False
        self._healthy = True

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a test query."""
        return {'columnMetadata': [], 'records': []}

    async def close(self) -> None:
        """Close test connection."""
        self._closed = True

    async def check_connection_health(self) -> bool:
        """Check test connection health."""
        return self._healthy


class TestAbstractDBConnection:
    """Tests for AbstractDBConnection."""

    def test_readonly_true(self):
        """readonly_query should return True when initialized with readonly=True."""
        conn = ConcreteDBConnection(readonly=True)
        assert conn.readonly_query is True

    def test_readonly_false(self):
        """readonly_query should return False when initialized with readonly=False."""
        conn = ConcreteDBConnection(readonly=False)
        assert conn.readonly_query is False

    async def test_execute_query(self):
        """execute_query should return a dict with columnMetadata and records."""
        conn = ConcreteDBConnection(readonly=True)
        result = await conn.execute_query('SELECT 1')
        assert 'columnMetadata' in result
        assert 'records' in result

    async def test_close(self):
        """close() should be callable."""
        conn = ConcreteDBConnection(readonly=True)
        await conn.close()
        assert conn._closed is True

    async def test_check_connection_health(self):
        """check_connection_health() should return a boolean."""
        conn = ConcreteDBConnection(readonly=True)
        result = await conn.check_connection_health()
        assert result is True

    def test_cannot_instantiate_abstract(self):
        """Should not be able to instantiate AbstractDBConnection directly."""
        with pytest.raises(TypeError):
            AbstractDBConnection(readonly=True)  # pyright: ignore[reportAbstractUsage]

    def test_readonly_property_is_property(self):
        """readonly_query should be a property, not a plain attribute."""
        conn = ConcreteDBConnection(readonly=False)
        assert isinstance(type(conn).readonly_query, property)

    async def test_execute_query_with_parameters(self):
        """execute_query should accept optional parameters."""
        conn = ConcreteDBConnection(readonly=True)
        params = [{'name': 'id', 'value': {'longValue': 1}}]
        result = await conn.execute_query('SELECT * FROM t WHERE id = :id', params)
        assert isinstance(result, dict)
