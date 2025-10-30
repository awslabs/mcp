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

"""Line-coverage tests for abstract_db_connection.py."""

import pytest
from awslabs.mysql_mcp_server.connection.abstract_db_connection import (
    AbstractDBConnection,
)


class _Concrete(AbstractDBConnection):
    """Concrete subclass to allow instantiation."""

    async def execute_query(self, sql: str, parameters=None):
        """Minimal implementation."""
        return {'columnMetadata': [], 'records': []}

    async def close(self) -> None:
        """Minimal implementation."""
        return None

    async def check_connection_health(self) -> bool:
        """Minimal implementation."""
        return True


def test_readonly_property_covers_return_line():
    """Covers the readonly_query property return (line ~39)."""
    conn = _Concrete(readonly=True)
    assert conn.readonly_query is True
    conn_false = _Concrete(readonly=False)
    assert conn_false.readonly_query is False


@pytest.mark.asyncio
async def test_calling_base_execute_query_noop_covers_line():
    """Directly call base execute_query to cover abstract body (line ~54)."""
    conn = _Concrete(readonly=False)
    # Call the base method explicitly; this executes the 'pass' line.
    result = await AbstractDBConnection.execute_query(conn, 'SELECT 1', None)
    assert result is None


@pytest.mark.asyncio
async def test_calling_base_close_noop_covers_line():
    """Directly call base close to cover abstract body (line ~59)."""
    conn = _Concrete(readonly=False)
    result = await AbstractDBConnection.close(conn)
    assert result is None


@pytest.mark.asyncio
async def test_calling_base_check_connection_health_noop_covers_line():
    """Directly call base check_connection_health to cover abstract body (line ~68)."""
    conn = _Concrete(readonly=False)
    result = await AbstractDBConnection.check_connection_health(conn)
    assert result is None
