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

"""Tests for AbstractDBConnection."""

from awslabs.oracle_mcp_server.connection.abstract_db_connection import AbstractDBConnection


class ConcreteDBConnection(AbstractDBConnection):
    """Minimal concrete implementation for testing."""

    async def execute_query(self, sql, parameters=None, max_rows=0):
        """Execute query stub."""
        return []

    async def close(self):
        """Close stub."""
        pass

    async def check_connection_health(self):
        """Health check stub."""
        return True


def test_readonly_true():
    """Verify readonly=True is stored correctly."""
    conn = ConcreteDBConnection(readonly=True)
    assert conn.readonly_query is True


def test_readonly_false():
    """Verify readonly=False is stored correctly."""
    conn = ConcreteDBConnection(readonly=False)
    assert conn.readonly_query is False
