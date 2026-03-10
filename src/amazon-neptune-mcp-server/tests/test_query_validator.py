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

"""Tests for query validation in the Neptune MCP Server."""

import pytest
from unittest.mock import MagicMock, patch

import awslabs.amazon_neptune_mcp_server.query_validator as qv
from awslabs.amazon_neptune_mcp_server.query_validator import (
    set_read_only,
    validate_gremlin_query,
    validate_opencypher_query,
)
from awslabs.amazon_neptune_mcp_server.server import (
    run_gremlin_query,
    run_opencypher_query,
)


@pytest.fixture(autouse=True)
def _reset_read_only():
    """Reset read_only to default (True) before each test."""
    set_read_only(True)
    yield
    set_read_only(True)


# ---------------------------------------------------------------------------
# openCypher — read-only mode (default)
# ---------------------------------------------------------------------------


class TestOpenCypherReadOnly:
    def test_read_query_allowed(self):
        validate_opencypher_query('MATCH (n) RETURN n LIMIT 10')

    def test_create_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('CREATE (n:Person {name: "Alice"})')

    def test_merge_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('MERGE (n:Person {name: "Alice"})')

    def test_delete_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('MATCH (n) DELETE n')

    def test_detach_delete_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('MATCH (n) DETACH DELETE n')

    def test_set_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('MATCH (n) SET n.name = "Bob"')

    def test_remove_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('MATCH (n) REMOVE n.name')

    def test_drop_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('DROP CONSTRAINT ON (n:Person) ASSERT n.name IS UNIQUE')

    def test_case_insensitive_blocking(self):
        with pytest.raises(PermissionError):
            validate_opencypher_query('match (n) delete n')

    def test_mixed_case_blocking(self):
        with pytest.raises(PermissionError):
            validate_opencypher_query('MATCH (n) DeLeTe n')

    def test_call_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_opencypher_query('CALL db.index.create()')

    def test_set_as_property_name_allowed(self):
        """Property access like n.set should not trigger SET detection."""
        validate_opencypher_query('MATCH (n) RETURN n.set')

    def test_set_in_word_allowed(self):
        """Words containing 'set' like 'dataset' should not be blocked."""
        validate_opencypher_query('MATCH (n) WHERE n.dataset = "training" RETURN n')


# ---------------------------------------------------------------------------
# openCypher — write mode (--allow-writes)
# ---------------------------------------------------------------------------


class TestOpenCypherWriteMode:
    def test_create_allowed(self):
        set_read_only(False)
        validate_opencypher_query('CREATE (n:Person {name: "Alice"})')

    def test_delete_allowed(self):
        set_read_only(False)
        validate_opencypher_query('MATCH (n) DELETE n')

    def test_default_is_read_only(self):
        """Without --allow-writes the server defaults to read-only."""
        with pytest.raises(PermissionError):
            validate_opencypher_query('CREATE (n:Person {name: "Alice"})')


# ---------------------------------------------------------------------------
# Gremlin — read-only mode (default)
# ---------------------------------------------------------------------------


class TestGremlinReadOnly:
    def test_read_query_allowed(self):
        validate_gremlin_query('g.V().limit(10)')

    def test_addV_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.addV('person').property('name','Alice')")

    def test_addE_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.V('1').addE('knows').to(g.V('2'))")

    def test_drop_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query('g.V().drop()')

    def test_property_mutation_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.V('1').property('age', 30)")

    def test_sideEffect_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.V().sideEffect(addV('test'))")

    def test_mergeV_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.mergeV([T.label, 'person', 'name', 'Alice'])")

    def test_mergeE_blocked(self):
        with pytest.raises(PermissionError, match='read-only mode'):
            validate_gremlin_query("g.mergeE([T.label, 'knows'])")


# ---------------------------------------------------------------------------
# Gremlin — write mode
# ---------------------------------------------------------------------------


class TestGremlinWriteMode:
    def test_addV_allowed(self):
        set_read_only(False)
        validate_gremlin_query("g.addV('person').property('name','Alice')")

    def test_drop_allowed(self):
        set_read_only(False)
        validate_gremlin_query('g.V().drop()')

    def test_sideEffect_allowed(self):
        set_read_only(False)
        validate_gremlin_query("g.V().sideEffect(addV('test'))")


# ---------------------------------------------------------------------------
# Integration: validation wired into server.py tool functions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestServerQueryValidation:
    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_opencypher_read_allowed_in_readonly(self, mock_get_graph):
        mock_graph = MagicMock()
        mock_graph.query_opencypher.return_value = {'results': []}
        mock_get_graph.return_value = mock_graph

        result = run_opencypher_query('MATCH (n) RETURN n LIMIT 1')
        assert result == {'results': []}
        mock_graph.query_opencypher.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_opencypher_mutate_blocked_in_readonly(self, mock_get_graph):
        with pytest.raises(PermissionError):
            run_opencypher_query('CREATE (n:Person {name: "Alice"})')
        mock_get_graph.assert_not_called()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_gremlin_read_allowed_in_readonly(self, mock_get_graph):
        mock_graph = MagicMock()
        mock_graph.query_gremlin.return_value = {'results': []}
        mock_get_graph.return_value = mock_graph

        result = run_gremlin_query('g.V().limit(1)')
        assert result == {'results': []}
        mock_graph.query_gremlin.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_gremlin_mutate_blocked_in_readonly(self, mock_get_graph):
        with pytest.raises(PermissionError):
            run_gremlin_query('g.V().drop()')
        mock_get_graph.assert_not_called()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_opencypher_mutate_allowed_with_allow_writes(self, mock_get_graph):
        set_read_only(False)
        mock_graph = MagicMock()
        mock_graph.query_opencypher.return_value = {'results': []}
        mock_get_graph.return_value = mock_graph

        result = run_opencypher_query('CREATE (n:Person {name: "Alice"})')
        assert result == {'results': []}
        mock_graph.query_opencypher.assert_called_once()

    @patch('awslabs.amazon_neptune_mcp_server.server.get_graph')
    async def test_gremlin_mutate_allowed_with_allow_writes(self, mock_get_graph):
        set_read_only(False)
        mock_graph = MagicMock()
        mock_graph.query_gremlin.return_value = {'results': []}
        mock_get_graph.return_value = mock_graph

        result = run_gremlin_query("g.addV('person').property('name','Alice')")
        assert result == {'results': []}
        mock_graph.query_gremlin.assert_called_once()


# ---------------------------------------------------------------------------
# CLI --allow-writes flag
# ---------------------------------------------------------------------------


class TestAllowWritesFlag:
    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    def test_main_defaults_to_read_only(self, mock_mcp):
        from awslabs.amazon_neptune_mcp_server.server import main

        with patch('sys.argv', ['server']):
            main()
        assert qv.read_only is True

    @patch('awslabs.amazon_neptune_mcp_server.server.mcp')
    def test_main_allow_writes_sets_read_only_false(self, mock_mcp):
        from awslabs.amazon_neptune_mcp_server.server import main

        with patch('sys.argv', ['server', '--allow-writes']):
            main()
        assert qv.read_only is False


# ---------------------------------------------------------------------------
# Graph store level: NeptuneDatabase query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatabaseQueryValidation:
    """Tests that NeptuneDatabase enforces query validation at the graph store level."""

    @patch('boto3.Session')
    async def test_opencypher_read_allowed(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase

        mock_client = MagicMock()
        mock_client.execute_open_cypher_query.return_value = {'results': []}
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneDatabase, '_refresh_schema'):
            db = NeptuneDatabase(host='test', port=8182)
        result = db.query_opencypher('MATCH (n) RETURN n LIMIT 1')
        assert result == []

    @patch('boto3.Session')
    async def test_opencypher_mutate_blocked(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneDatabase, '_refresh_schema'):
            db = NeptuneDatabase(host='test', port=8182)
        with pytest.raises(PermissionError):
            db.query_opencypher('CREATE (n:Person {name: "Alice"})')
        mock_client.execute_open_cypher_query.assert_not_called()

    @patch('boto3.Session')
    async def test_gremlin_read_allowed(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase

        mock_client = MagicMock()
        mock_client.execute_gremlin_query.return_value = {'results': []}
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneDatabase, '_refresh_schema'):
            db = NeptuneDatabase(host='test', port=8182)
        result = db.query_gremlin('g.V().limit(1)')
        assert result == []

    @patch('boto3.Session')
    async def test_gremlin_mutate_blocked(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneDatabase, '_refresh_schema'):
            db = NeptuneDatabase(host='test', port=8182)
        with pytest.raises(PermissionError):
            db.query_gremlin('g.V().drop()')
        mock_client.execute_gremlin_query.assert_not_called()

    @patch('boto3.Session')
    async def test_opencypher_mutate_allowed_in_write_mode(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase

        set_read_only(False)
        mock_client = MagicMock()
        mock_client.execute_open_cypher_query.return_value = {'results': []}
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneDatabase, '_refresh_schema'):
            db = NeptuneDatabase(host='test', port=8182)
        result = db.query_opencypher('CREATE (n:Person {name: "Alice"})')
        assert result == []


# ---------------------------------------------------------------------------
# Graph store level: NeptuneAnalytics query validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAnalyticsQueryValidation:
    """Tests that NeptuneAnalytics enforces query validation at the graph store level."""

    @patch('boto3.Session')
    async def test_opencypher_read_allowed(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.analytics import NeptuneAnalytics

        mock_client = MagicMock()
        payload_mock = MagicMock()
        payload_mock.read.return_value = b'{"results": []}'
        mock_client.execute_query.return_value = {'payload': payload_mock}
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            ga = NeptuneAnalytics(graph_identifier='test-graph')
        result = ga.query_opencypher('MATCH (n) RETURN n LIMIT 1')
        assert result == []

    @patch('boto3.Session')
    async def test_opencypher_mutate_blocked(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.analytics import NeptuneAnalytics

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            ga = NeptuneAnalytics(graph_identifier='test-graph')
        with pytest.raises(PermissionError):
            ga.query_opencypher('CREATE (n:Person {name: "Alice"})')
        mock_client.execute_query.assert_not_called()

    @patch('boto3.Session')
    async def test_opencypher_mutate_allowed_in_write_mode(self, mock_session):
        from awslabs.amazon_neptune_mcp_server.graph_store.analytics import NeptuneAnalytics

        set_read_only(False)
        mock_client = MagicMock()
        payload_mock = MagicMock()
        payload_mock.read.return_value = b'{"results": []}'
        mock_client.execute_query.return_value = {'payload': payload_mock}
        mock_session.return_value.client.return_value = mock_client

        with patch.object(NeptuneAnalytics, '_refresh_schema'):
            ga = NeptuneAnalytics(graph_identifier='test-graph')
        result = ga.query_opencypher('CREATE (n:Person {name: "Alice"})')
        assert result == []
