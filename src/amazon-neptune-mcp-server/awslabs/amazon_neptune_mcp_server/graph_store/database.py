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

import boto3
import hashlib
import json
from awslabs.amazon_neptune_mcp_server.constants import USER_AGENT_CONFIG
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.models import (
    GraphSchema,
    Node,
    Property,
    Relationship,
    RelationshipPattern,
)
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from threading import Lock
from time import monotonic
from typing import Any, Dict, List, Optional, Tuple


_SCHEMA_TTL_SECONDS = 300
_SCHEMA_CACHE_SIZE = 32
_SCHEMA_QUERY_WORKERS = 4
_SchemaKey = Tuple[str, str]
_SCHEMA_CACHE: OrderedDict[_SchemaKey, Tuple[float, GraphSchema]] = OrderedDict()
_SCHEMA_CACHE_LOCK = Lock()
# Bounded locks coalesce refreshes for the same endpoint and credentials.
_SCHEMA_REFRESH_LOCKS = tuple(Lock() for _ in range(_SCHEMA_CACHE_SIZE))


class NeptuneDatabase(NeptuneGraph):
    """Neptune wrapper for graph operations.

    Args:
        host: endpoint for the database instance
        port: port number for the database instance, default is 8182
        use_https: whether to use secure connection, default is True
        credentials_profile_name: optional AWS profile name

    Example:
        .. code-block:: python

        graph = NeptuneDatabase(
            host='<my-cluster>',
            port=8182
        )
    """

    schema: Optional[GraphSchema] = None

    def __init__(
        self,
        host: str,
        port: int = 8182,
        use_https: bool = True,
        credentials_profile_name: Optional[str] = None,
    ) -> None:
        """Create a new Neptune graph wrapper instance."""
        try:
            if not credentials_profile_name:
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=credentials_profile_name)

            client_params = {}
            protocol = 'https' if use_https else 'http'
            client_params['endpoint_url'] = f'{protocol}://{host}:{port}'
            self.client = session.client('neptunedata', config=USER_AGENT_CONFIG, **client_params)
            self._session = session
            self._endpoint = client_params['endpoint_url']
            self.schema = None
            self._schema_expires_at = 0.0
            self._schema_key: Optional[_SchemaKey] = None
            self._schema_lock = Lock()

        except Exception as e:
            logger.exception('Could not load credentials to authenticate with AWS client')
            raise ValueError(
                'Could not load credentials to authenticate with AWS client. '
                'Please check that credentials in the specified '
                'profile name are valid.'
            ) from e

    def _get_summary(self) -> Dict:
        """Retrieves the graph summary from Neptune's property graph summary API.

        Returns:
            Dict: A dictionary containing the graph summary information

        Raises:
            NeptuneException: If the summary API is not available or returns an invalid response
        """
        try:
            response = self.client.get_propertygraph_summary()
        except Exception as e:
            raise NeptuneException(
                {
                    'message': (
                        'Summary API is not available for this instance of Neptune,'
                        'ensure the engine version is >=1.2.1.0'
                    ),
                    'details': str(e),
                }
            )

        try:
            summary = response['payload']['graphSummary']
        except Exception:
            raise NeptuneException(
                {
                    'message': 'Summary API did not return a valid response.',
                    'details': response.content.decode(),
                }
            )
        else:
            return summary

    def _get_labels(self) -> Tuple[List[str], List[str]]:
        """Get node and edge labels from the Neptune statistics summary.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing two lists:
                1. List of node labels
                2. List of edge labels
        """
        summary = self._get_summary()
        n_labels = summary['nodeLabels']
        e_labels = summary['edgeLabels']
        return n_labels, e_labels

    def _get_triples(self, e_labels: List[str]) -> List[RelationshipPattern]:
        """Retrieves relationship patterns (triples) from the graph based on edge labels.

        This method queries the graph to find distinct patterns of node-edge-node
        relationships for each edge label.

        Args:
            e_labels (List[str]): List of edge labels to query for relationship patterns

        Returns:
            List[RelationshipPattern]: List of relationship patterns found in the graph
        """
        triple_query = """
        MATCH (a)-[e:`{e_label}`]->(b)
        WITH a,e,b LIMIT 3000
        RETURN DISTINCT labels(a) AS from, type(e) AS edge, labels(b) AS to
        LIMIT 10
        """

        triple_schema: List[RelationshipPattern] = []
        for label in e_labels:
            q = triple_query.format(e_label=label)
            data = self.query_opencypher(q)
            for d in data:
                triple_schema.append(
                    RelationshipPattern(
                        left_node=d['from'][0], right_node=d['to'][0], relation=d['edge']
                    )
                )

        return triple_schema

    def _get_node_properties(self, n_labels: List[str], types: Dict) -> List:
        """Retrieves property information for each node label in the graph.

        This method queries the graph to find all properties associated with each
        node label and their data types.

        Args:
            n_labels (List[str]): List of node labels to query for properties
            types (Dict): Dictionary mapping Python types to Neptune data types

        Returns:
            List[Node]: List of Node objects with their properties
        """
        node_properties_query = """
        MATCH (a:`{n_label}`)
        RETURN properties(a) AS props
        LIMIT 100
        """
        nodes = []
        for label in n_labels:
            q = node_properties_query.format(n_label=label)
            resp = self.query_opencypher(q)
            props = {}
            for p in resp:
                for k, v in p['props'].items():
                    prop_type = types[type(v).__name__]
                    if k not in props:
                        props[k] = {prop_type}
                    else:
                        props[k].update([prop_type])

            properties = []
            for k, v in props.items():
                properties.append(Property(name=k, type=list(v)))

            nodes.append(Node(labels=label, properties=properties))
        return nodes

    def _get_edge_properties(self, e_labels: List[str], types: Dict[str, Any]) -> List:
        """Retrieves property information for each edge label in the graph.

        This method queries the graph to find all properties associated with each
        edge label and their data types.

        Args:
            e_labels (List[str]): List of edge labels to query for properties
            types (Dict[str, Any]): Dictionary mapping Python types to Neptune data types

        Returns:
            List[Relationship]: List of Relationship objects with their properties
        """
        edge_properties_query = """
        MATCH ()-[e:`{e_label}`]->()
        RETURN properties(e) AS props
        LIMIT 100
        """
        edges = []
        for label in e_labels:
            q = edge_properties_query.format(e_label=label)
            resp = self.query_opencypher(q)
            props = {}
            for p in resp:
                for k, v in p['props'].items():
                    prop_type = types[type(v).__name__]
                    if k not in props:
                        props[k] = {prop_type}
                    else:
                        props[k].update([prop_type])

            properties = []
            for k, v in props.items():
                properties.append(Property(name=k, type=list(v)))

            edges.append(Relationship(type=label, properties=properties))

        return edges

    def _refresh_schema(self) -> GraphSchema:
        """Refreshes the Neptune graph schema information.

        This method queries the graph to build a complete schema representation
        including nodes, relationships, and relationship patterns.

        Returns:
            GraphSchema: Complete schema information for the graph
        """
        types = {
            'str': 'STRING',
            'float': 'DOUBLE',
            'int': 'INTEGER',
            'list': 'LIST',
            'dict': 'MAP',
            'bool': 'BOOLEAN',
        }
        n_labels, e_labels = self._get_labels()
        with ThreadPoolExecutor(max_workers=_SCHEMA_QUERY_WORKERS) as executor:
            triples = [executor.submit(self._get_triples, [label]) for label in e_labels]
            node_properties = [
                executor.submit(self._get_node_properties, [label], types) for label in n_labels
            ]
            edge_properties = [
                executor.submit(self._get_edge_properties, [label], types) for label in e_labels
            ]
            triple_schema = [pattern for future in triples for pattern in future.result()]
            nodes = [node for future in node_properties for node in future.result()]
            rels = [rel for future in edge_properties for rel in future.result()]

        graph = GraphSchema(nodes=nodes, relationships=rels, relationship_patterns=triple_schema)

        self.schema = graph
        return graph

    def _cache_key(self) -> Optional[_SchemaKey]:
        """Scope shared schemas to the endpoint and current AWS credentials."""
        credentials = self._session.get_credentials()
        if credentials is None:
            return None
        frozen = credentials.get_frozen_credentials()
        # Never retain credential values in the cache or share anonymous clients.
        values = (frozen.access_key, frozen.secret_key, frozen.token or '')
        if not all(isinstance(value, str) for value in values):
            return None
        digest = hashlib.sha256(json.dumps(values).encode()).hexdigest()
        return self._endpoint, digest

    def _get_cached_schema(self, key: _SchemaKey) -> Tuple[GraphSchema, float]:
        """Reuse fresh schemas and allow only one refresh for each cache key."""
        with _SCHEMA_REFRESH_LOCKS[hash(key) % len(_SCHEMA_REFRESH_LOCKS)]:
            with _SCHEMA_CACHE_LOCK:
                cached = _SCHEMA_CACHE.get(key)
                if cached is not None and monotonic() < cached[0]:
                    _SCHEMA_CACHE.move_to_end(key)
                    return cached[1].model_copy(deep=True), cached[0]
            graph = self._refresh_schema()
            expires_at = monotonic() + _SCHEMA_TTL_SECONDS
            with _SCHEMA_CACHE_LOCK:
                _SCHEMA_CACHE[key] = expires_at, graph.model_copy(deep=True)
                _SCHEMA_CACHE.move_to_end(key)
                while len(_SCHEMA_CACHE) > _SCHEMA_CACHE_SIZE:
                    _SCHEMA_CACHE.popitem(last=False)
            return graph, expires_at

    def get_schema(self) -> GraphSchema:
        """Discover schema on demand, reusing results for up to five minutes.

        Schemas are shared by clients with the same endpoint and credentials in
        this process. Discovery still uses the existing bounded property samples.

        Returns:
            GraphSchema: Complete schema information for the graph
        """
        with self._schema_lock:
            try:
                key = self._cache_key()
                if (
                    self.schema is not None
                    and key == self._schema_key
                    and monotonic() < self._schema_expires_at
                ):
                    return self.schema
                if key is None:
                    graph = self._refresh_schema()
                    expires_at = monotonic() + _SCHEMA_TTL_SECONDS
                else:
                    graph, expires_at = self._get_cached_schema(key)
                self.schema = graph
                self._schema_key = key
                self._schema_expires_at = expires_at
                return graph
            except Exception as e:
                logger.exception('Could not get schema for Neptune database')
                raise NeptuneException(
                    {
                        'message': 'Could not get schema for Neptune database',
                        'detail': str(e),
                    }
                ) from e

    def query_opencypher(self, query: str, params: Optional[dict] = None):
        """Executes an openCypher query against the Neptune database.

        Args:
            query (str): The openCypher query string to execute
            params (Optional[dict]): Optional parameters for the query

        Returns:
            Any: The query results, either as a single result or a list of results
        """
        if params:
            resp = self.client.execute_open_cypher_query(
                openCypherQuery=query,
                parameters=json.dumps(params),
            )
        else:
            resp = self.client.execute_open_cypher_query(openCypherQuery=query)

        return resp['result'] if 'result' in resp else resp['results']

    def query_gremlin(self, query):
        """Executes a Gremlin query against the Neptune database.

        Args:
            query (str): The Gremlin query string to execute

        Returns:
            Any: The query results, either as a single result or a list of results
        """
        resp = self.client.execute_gremlin_query(gremlinQuery=query)
        return resp['result'] if 'result' in resp else resp['results']
