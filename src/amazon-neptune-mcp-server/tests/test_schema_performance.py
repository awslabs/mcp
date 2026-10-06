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
"""Regression tests for lazy schema discovery, concurrency, and cache lifetime."""

import pytest
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store import database as database_module
from awslabs.amazon_neptune_mcp_server.graph_store.database import NeptuneDatabase
from awslabs.amazon_neptune_mcp_server.models import GraphSchema, Node
from botocore.credentials import Credentials
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def reset_cache():
    """Keep cache tests independent of their execution order."""
    database_module._SCHEMA_CACHE.clear()
    yield
    database_module._SCHEMA_CACHE.clear()


@pytest.fixture
def database_factory():
    """Create database wrappers with distinct endpoints and real credential values."""

    def create(host='schema-tests', access_key='access-key', use_https=True):
        session = MagicMock()
        session.get_credentials.return_value = Credentials(access_key, 'secret', 'token')
        with patch('boto3.Session', return_value=session):
            return NeptuneDatabase(host, use_https=use_https)

    return create


def test_startup_and_queries_do_not_discover_schema(database_factory):
    """Queries can run without requiring statistics or property scans."""
    with patch.object(NeptuneDatabase, '_refresh_schema') as refresh:
        db = database_factory()
        db.client.execute_open_cypher_query.return_value = {'results': []}
        db.client.execute_gremlin_query.return_value = {'result': []}
        db.query_opencypher('RETURN 1')
        db.query_gremlin('g.V().limit(1)')
        refresh.assert_not_called()
        db.client.get_propertygraph_summary.assert_not_called()


def test_schema_reused_and_expired_across_instances(database_factory):
    """Reuse a schema without extending its expiry or sharing mutable models."""
    graph = GraphSchema(
        nodes=[Node(labels='Person', properties=[])], relationships=[], relationship_patterns=[]
    )
    with patch.object(NeptuneDatabase, '_refresh_schema', return_value=graph) as refresh:
        with patch(
            'awslabs.amazon_neptune_mcp_server.graph_store.database.monotonic', return_value=100
        ):
            first = database_factory('reuse-test')
            assert first.get_schema() == graph
            second = database_factory('reuse-test')
            second.get_schema().nodes.clear()
            assert first.get_schema().nodes[0].labels == 'Person'
            refresh.assert_called_once()
        with patch(
            'awslabs.amazon_neptune_mcp_server.graph_store.database.monotonic', return_value=399
        ):
            third = database_factory('reuse-test')
            assert third.get_schema() == graph
            refresh.assert_called_once()
        with patch(
            'awslabs.amazon_neptune_mcp_server.graph_store.database.monotonic', return_value=401
        ):
            third.get_schema()
            assert refresh.call_count == 2


def test_cache_isolated_by_credentials_and_endpoint(database_factory):
    """Different credentials, hosts, and protocols must discover their own schema."""
    graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
    with patch.object(NeptuneDatabase, '_refresh_schema', return_value=graph) as refresh:
        for db in [
            database_factory('isolation-test'),
            database_factory('isolation-test', 'other-key'),
            database_factory('other-host'),
            database_factory('isolation-test', use_https=False),
        ]:
            db.get_schema()
        assert refresh.call_count == 4


def test_failed_discovery_can_be_retried(database_factory):
    """An error must not poison the cache or prevent subsequent queries."""
    db = database_factory('retry-test')
    graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
    with patch.object(
        NeptuneDatabase, '_refresh_schema', side_effect=[RuntimeError('unavailable'), graph]
    ) as refresh:
        with pytest.raises(NeptuneException, match='Could not get schema'):
            db.get_schema()
        assert db.get_schema() == graph
        assert refresh.call_count == 2


def test_concurrent_callers_share_one_discovery(database_factory):
    """Simultaneous clients for one graph perform one schema refresh."""
    clients = [database_factory('concurrent-test') for _ in range(8)]
    start = Barrier(8)
    graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

    def fetch(db):
        start.wait(timeout=5)
        return db.get_schema()

    with patch.object(NeptuneDatabase, '_refresh_schema', return_value=graph) as refresh:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(fetch, clients))
        assert all(result == graph for result in results)
        refresh.assert_called_once()


def test_label_scans_are_parallel_bounded_and_preserve_order(database_factory):
    """Four scans overlap while preserving the existing schema shape and label order."""
    db = database_factory('parallel-test')
    db._get_labels = MagicMock(return_value=([f'Label{i}' for i in range(12)], []))
    overlap = Barrier(4)
    lock = Lock()
    active = 0
    peak = 0

    def query(query_text, params=None):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        overlap.wait(timeout=5)
        with lock:
            active -= 1
        assert 'LIMIT 100' in query_text
        return [{'props': {'name': 'value', 'count': 2}}]

    db.query_opencypher = query
    graph = db._refresh_schema()
    assert peak == 4
    assert [node.labels for node in graph.nodes] == [f'Label{i}' for i in range(12)]
    assert [prop.type for prop in graph.nodes[0].properties] == [['STRING'], ['INTEGER']]
    assert graph.relationships == []
    assert graph.relationship_patterns == []


def test_cache_evicts_old_entries(database_factory):
    """Cache reuse remains bounded when many graphs are visited."""
    graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
    with patch.object(NeptuneDatabase, '_refresh_schema', return_value=graph) as refresh:
        for i in range(33):
            database_factory(f'eviction-{i}').get_schema()
        database_factory('eviction-0').get_schema()
        assert refresh.call_count == 34


def test_clients_without_credentials_only_cache_locally(database_factory):
    """Never share schemas if credential identity cannot be determined."""
    first = database_factory('anonymous')
    second = database_factory('anonymous')
    first._session.get_credentials.return_value = None
    second._session.get_credentials.return_value = None
    graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
    with patch.object(NeptuneDatabase, '_refresh_schema', return_value=graph) as refresh:
        first.get_schema()
        first.get_schema()
        second.get_schema()
        assert refresh.call_count == 2


def test_parallel_discovery_preserves_properties_and_relationships(database_factory):
    """Bounded scans still infer types and collect node-edge-node patterns."""
    db = database_factory('schema-shape')
    db._get_labels = MagicMock(return_value=(['Person', 'City'], ['LIVES_IN']))

    def query(text, params=None):
        if 'RETURN DISTINCT labels' in text:
            assert 'LIMIT 3000' in text and 'LIMIT 10' in text
            return [{'from': ['Person'], 'edge': 'LIVES_IN', 'to': ['City']}]
        assert 'LIMIT 100' in text
        if 'MATCH (a:`Person`)' in text:
            return [{'props': {'name': 'Ada', 'age': 37}}, {'props': {'age': 38.5}}]
        if 'MATCH (a:`City`)' in text:
            return [{'props': {'name': 'London'}}]
        return [{'props': {'since': 2020, 'current': True}}]

    db.query_opencypher = query
    graph = db.get_schema()
    assert [node.labels for node in graph.nodes] == ['Person', 'City']
    assert {prop.name: set(prop.type) for prop in graph.nodes[0].properties} == {
        'name': {'STRING'},
        'age': {'INTEGER', 'DOUBLE'},
    }
    assert graph.relationships[0].type == 'LIVES_IN'
    assert {prop.name: prop.type for prop in graph.relationships[0].properties} == {
        'since': ['INTEGER'],
        'current': ['BOOLEAN'],
    }
    assert graph.relationship_patterns[0].model_dump() == {
        'left_node': 'Person',
        'right_node': 'City',
        'relation': 'LIVES_IN',
    }
