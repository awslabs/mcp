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

from awslabs.mssql_mcp_server.connection.abstract_db_connection import AbstractDBConnection


class ConcreteDBConnection(AbstractDBConnection):
    """Concrete implementation of AbstractDBConnection for testing."""

    async def execute_query(self, sql, parameters=None):
        """Return an empty result set."""
        return {'columnMetadata': [], 'records': []}

    async def close(self):
        """No-op close."""
        pass

    async def check_connection_health(self):
        """Return True unconditionally."""
        return True


def test_readonly_defaults_true():
    """readonly_query is True when readonly=True."""
    conn = ConcreteDBConnection(readonly=True)
    assert conn.readonly_query is True


def test_readonly_false():
    """readonly_query is False when readonly=False."""
    conn = ConcreteDBConnection(readonly=False)
    assert conn.readonly_query is False
