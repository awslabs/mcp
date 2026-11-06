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

"""Tests for AbstractDBConnection class."""

from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from typing import Any, Dict, List, Optional


class ConcreteDBConnection(AbstractDBConnection):
    """Minimal concrete implementation for testing AbstractDBConnection initialization.

    These abstract method implementations are required by Python's ABC but are not
    used in the tests. They exist only to allow instantiation of the class.
    """

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Minimal implementation."""
        return {}

    async def close(self) -> None:
        """Minimal implementation."""
        pass

    async def check_connection_health(self) -> bool:
        """Minimal implementation."""
        return True


class TestAbstractDBConnection:
    """Test suite for AbstractDBConnection class.

    Note: This class primarily tests the initialization and readonly_query property.
    The abstract methods (execute_query, close, check_connection_health) are tested
    in the concrete implementation test files (test_rds_api_connection.py,
    test_psycopg_connector.py).
    """

    def test_initialization_readonly_true(self):
        """Test initialization with readonly=True."""
        conn = ConcreteDBConnection(readonly=True)
        assert conn.readonly_query is True

    def test_initialization_readonly_false(self):
        """Test initialization with readonly=False."""
        conn = ConcreteDBConnection(readonly=False)
        assert conn.readonly_query is False

    def test_proxy_endpoint_defaults_to_none(self):
        """A connection is direct until told otherwise.

        Defaulting to None rather than '' matters: callers distinguish "not
        proxied" from "proxied" by presence, and the connect response omits the
        field entirely when this is unset.
        """
        conn = ConcreteDBConnection(readonly=True)
        assert conn.proxy_endpoint is None

    def test_proxy_endpoint_round_trips(self):
        """The proxy endpoint must survive being recorded.

        This is the only place proxied-ness is visible on paths that do not re-run
        the proxy lookup -- a connection-map cache hit, and
        get_database_connection_info -- so it has to be readable back off the
        connection object.
        """
        conn = ConcreteDBConnection(readonly=True)
        conn.proxy_endpoint = 'p.proxy-abc.us-east-1.rds.amazonaws.com'
        assert conn.proxy_endpoint == 'p.proxy-abc.us-east-1.rds.amazonaws.com'

        conn.proxy_endpoint = None
        assert conn.proxy_endpoint is None

    def test_proxy_endpoint_is_per_instance(self):
        """Two connections must not share proxy state."""
        first, second = ConcreteDBConnection(readonly=True), ConcreteDBConnection(readonly=True)
        first.proxy_endpoint = 'p.proxy-abc.us-east-1.rds.amazonaws.com'
        assert second.proxy_endpoint is None
