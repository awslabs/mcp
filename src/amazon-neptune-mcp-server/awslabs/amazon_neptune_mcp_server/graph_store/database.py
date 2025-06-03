# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import boto3
import json
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.models import (
    GraphSchema,
    Node,
    Property,
    Relationship,
    RelationshipPattern,
)
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


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
            self.client = session.client('neptunedata', **client_params)

        except Exception as e:
            logger.exception('Could not load credentials to authenticate with AWS client')
            raise ValueError(
                'Could not load credentials to authenticate with AWS client. '
                'Please check that credentials in the specified '
                'profile name are valid.'
            ) from e

        try:
            self._refresh_schema()
        except Exception as e:
            logger.exception('Could not get schema for Neptune database')
            raise NeptuneException(
                {
                    'message': 'Could not get schema for Neptune database',
                    'detail': str(e),
                }
            )

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
        triple_schema = self._get_triples(e_labels)
        nodes = self._get_node_properties(n_labels, types)
        rels = self._get_edge_properties(e_labels, types)

        graph = GraphSchema(nodes=nodes, relationships=rels, relationship_patterns=triple_schema)

        self.schema = graph
        return graph

    def get_schema(self) -> GraphSchema:
        """Returns the current graph schema, refreshing it if necessary.

        Returns:
            GraphSchema: Complete schema information for the graph
        """
        if self.schema is None:
            self._refresh_schema()
        return (
            self.schema
            if self.schema
            else GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
        )

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
