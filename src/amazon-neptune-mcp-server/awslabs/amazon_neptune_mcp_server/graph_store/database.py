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
import json
import requests
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.models import (
    ClassItem,
    DatatypePropertyItem,
    GraphSchema,
    Node,
    ObjectPropertyItem,
    OntologyItem,
    Property,
    RDFGraphSchema,
    Relationship,
    RelationshipPattern,
    URIItem,
)
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from loguru import logger
from SPARQLWrapper import SPARQLWrapper
from typing import Any, Dict, List, Optional, Sequence, Tuple


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
    rdf_schema: Optional[RDFGraphSchema] = None

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
            self.session = session
            client_params = {}
            protocol = 'https' if use_https else 'http'
            client_params['endpoint_url'] = f'{protocol}://{host}:{port}'
            self.client = session.client('neptunedata', **client_params)
            self.endpoint_url = client_params['endpoint_url']
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
            print('Here')
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

    def _refresh_lpg_schema(self) -> GraphSchema:
        """Refreshes the Neptune lpg graph schema information.

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

    def get_lpg_schema(self) -> GraphSchema:
        """Returns the current LPG graph schema, refreshing it if necessary.

        Returns:
            PropertyGraphSchema: Complete schema information for the property graph
        """
        if self.schema is None:
            self._refresh_lpg_schema()
        return (
            self.schema
            if self.schema
            else GraphSchema(nodes=[], relationships=[], relationship_patterns=[])
        )

    def propertygraph_schema(self) -> GraphSchema:
        """Returns the property graph schema, refreshing it if necessary.

        Returns:
            PropertyGraphSchema: Complete schema information for the property graph
        """
        return self.get_lpg_schema()

    def query_opencypher(self, query: str, params: Optional[dict] = None):
        """Executes an openCypher query against the Neptune database.

        Args:
            query (str): The openCypher query string to execute
            params (Optional[dict]): Optional parameters for the query

        Returns:
            Any: The query results, either as a single result or a list of results
        """
        logger.debug(f'Querying Neptune with OpenCypher: {query}')
        if params:
            logger.debug(f'Querying Neptune with params: {params}')

        if params:
            resp = self.client.execute_open_cypher_query(
                openCypherQuery=query,
                parameters=json.dumps(params),
            )
        else:
            resp = self.client.execute_open_cypher_query(openCypherQuery=query)

        logger.debug(f'Neptune response: {json.dumps(resp, indent=2)}')
        return resp['result'] if 'result' in resp else resp['results']

    def query_gremlin(self, query: str):
        """Executes a Gremlin query against the Neptune database.

        Args:
            query (str): The Gremlin query string to execute

        Returns:
            Any: The query results, either as a single result or a list of results
        """
        logger.debug(f'Querying Neptune with Gremlin: {query}')
        resp = self.client.execute_gremlin_query(gremlinQuery=query)

        logger.debug(f'Neptune response: {json.dumps(resp, indent=2)}')
        return resp['result'] if 'result' in resp else resp['results']

    def query_sparql(self, query: str) -> dict:
        """Executes a SPARQL query against the Neptune database.

        Args:
            query (str): The SPARQL query string to execute

        Returns:
            dict: The query results
        """
        return self._query_sparql(query)

    def _get_local_name(self, iri: str) -> Sequence[str]:
        """Split IRI into prefix and local."""
        if '#' in iri:
            tokens = iri.split('#')
            prefix = tokens[0] + '#'
            local = tokens[1]
            return prefix, local
        elif '/' in iri:
            tokens = iri.rsplit('/', 1)
            prefix = tokens[0] + '/'
            local = tokens[1]
            return prefix, local
        else:
            raise ValueError(f"Unexpected IRI '{iri}', contains neither '#' nor '/'.")

    def get_rdf_schema(self) -> RDFGraphSchema:
        """Returns the RDF schema for the Neptune database.

        Returns:
            RDFGraphSchema: Complete schema information for the RDF graph
        """
        schema_elements: RDFGraphSchema = RDFGraphSchema(
            distinct_prefixes={},
            classes=[],
            rels=[],
            dtprops=[],
            oprops=[],
            rdfclasses=[],
            predicates=[],
        )

        if self.rdf_schema is not None:
            return self.rdf_schema

        # First get the schema from the summary
        resp = self.client.get_rdf_graph_summary()
        schema_elements.rdfclasses = list(resp['payload']['graphSummary']['classes'])
        schema_elements.predicates = [
            key for d in resp['payload']['graphSummary']['predicates'] for key in d.keys()
        ]

        # Prefixes
        prefixes = {}

        # SPARQL query for ontology, classes, and properties
        classes_query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX gb: <http://graph.build/ontology/>
        PREFIX sh: <http://www.w3.org/ns/shacl#>

        CONSTRUCT {
          ?ontology a owl:Ontology ;
            rdfs:label ?label ;
            rdfs:comment ?comment .

          ?class a owl:Class ;
            rdfs:subClassOf ?classParent ;
            rdfs:label ?classLabel ;
            rdfs:comment ?classComment .

          ?datatypeProperty a owl:DatatypeProperty ;
            rdfs:subPropertyOf ?datatypePropertyParent ;
            rdfs:domain ?datatypePropertyDomain ;
            rdfs:range ?datatypePropertyRange ;
            rdfs:label ?datatypePropertyLabel ;
            rdfs:comment ?datatypePropertyComment .

          ?objectProperty a owl:ObjectProperty ;
            rdfs:subPropertyOf ?objectPropertyParent ;
            rdfs:domain ?objectPropertyDomain ;
            rdfs:range ?objectPropertyRange ;
            rdfs:label ?objectPropertyLabel ;
            rdfs:comment ?objectPropertyComment .
        }
        WHERE {
          OPTIONAL {
            ?ontology a owl:Ontology .
            OPTIONAL { ?ontology rdfs:label ?label . }
            OPTIONAL { ?ontology rdfs:comment ?comment . }
          }

          OPTIONAL {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:subClassOf ?classParent . }
            OPTIONAL { ?class rdfs:label ?classLabel . }
            OPTIONAL { ?class rdfs:comment ?classComment . }
          }

          OPTIONAL {
            ?datatypeProperty a owl:DatatypeProperty .
            OPTIONAL { ?datatypeProperty rdfs:subPropertyOf ?datatypePropertyParent . }
            OPTIONAL { ?datatypeProperty rdfs:domain ?datatypePropertyDomain . }
            OPTIONAL { ?datatypeProperty rdfs:range ?datatypePropertyRange . }
            OPTIONAL { ?datatypeProperty rdfs:label ?datatypePropertyLabel . }
            OPTIONAL { ?datatypeProperty rdfs:comment ?datatypePropertyComment . }
          }

          OPTIONAL {
            ?objectProperty a owl:ObjectProperty .
            OPTIONAL { ?objectProperty rdfs:subPropertyOf ?objectPropertyParent . }
            OPTIONAL { ?objectProperty rdfs:domain ?objectPropertyDomain . }
            OPTIONAL { ?objectProperty rdfs:range ?objectPropertyRange . }
            OPTIONAL { ?objectProperty rdfs:label ?objectPropertyLabel . }
            OPTIONAL { ?objectProperty rdfs:comment ?objectPropertyComment . }
          }
        }
        """
        results = self._query_sparql(classes_query)

        # Process results
        ontologies = {}
        classes = {}
        dtprops = {}
        oprops = {}
        rels = []

        # Extract triples from results
        if 'results' in results:
            bindings = results['results'].get('bindings', [])
            for binding in bindings:
                if 's' in binding and 'p' in binding and 'o' in binding:
                    s = binding['s']['value']
                    p = binding['p']['value']
                    o = binding['o']['value']

                    # Process ontology
                    if (
                        p == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                        and o == 'http://www.w3.org/2002/07/owl#Ontology'
                    ):
                        ontologies[s] = OntologyItem(uri=s)
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#label' and s in ontologies:
                        ontologies[s].label = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#comment' and s in ontologies:
                        ontologies[s].comment = o

                    # Process classes
                    if (
                        p == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                        and o == 'http://www.w3.org/2002/07/owl#Class'
                    ):
                        try:
                            prefix, local = self._get_local_name(s)
                            if prefix not in prefixes:
                                prefixes[prefix] = f'ns{len(prefixes)}'
                            if s not in classes:
                                classes[s] = ClassItem(uri=s, local=local)
                        except ValueError:
                            pass
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#subClassOf' and s in classes:
                        classes[s].parent_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#label' and s in classes:
                        classes[s].label = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#comment' and s in classes:
                        classes[s].comment = o

                    # Process datatype properties
                    if (
                        p == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                        and o == 'http://www.w3.org/2002/07/owl#DatatypeProperty'
                    ):
                        try:
                            prefix, local = self._get_local_name(s)
                            if prefix not in prefixes:
                                prefixes[prefix] = f'ns{len(prefixes)}'
                            if s not in dtprops:
                                dtprops[s] = DatatypePropertyItem(uri=s, local=local)
                        except ValueError:
                            pass
                    elif (
                        p == 'http://www.w3.org/2000/01/rdf-schema#subPropertyOf' and s in dtprops
                    ):
                        dtprops[s].parent_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#domain' and s in dtprops:
                        dtprops[s].domain_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#range' and s in dtprops:
                        dtprops[s].range_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#label' and s in dtprops:
                        dtprops[s].label = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#comment' and s in dtprops:
                        dtprops[s].comment = o

                    # Process object properties
                    if (
                        p == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                        and o == 'http://www.w3.org/2002/07/owl#ObjectProperty'
                    ):
                        try:
                            prefix, local = self._get_local_name(s)
                            if prefix not in prefixes:
                                prefixes[prefix] = f'ns{len(prefixes)}'
                            if s not in oprops:
                                oprops[s] = ObjectPropertyItem(uri=s, local=local)
                                rels.append(URIItem(uri=s, local=local))
                        except ValueError:
                            pass
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#subPropertyOf' and s in oprops:
                        oprops[s].parent_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#domain' and s in oprops:
                        oprops[s].domain_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#range' and s in oprops:
                        oprops[s].range_uri = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#label' and s in oprops:
                        oprops[s].label = o
                    elif p == 'http://www.w3.org/2000/01/rdf-schema#comment' and s in oprops:
                        oprops[s].comment = o

        # Update schema elements
        schema_elements.distinct_prefixes = prefixes
        schema_elements.ontologies = list(ontologies.values())
        schema_elements.classes = list(classes.values())
        schema_elements.rels = rels
        schema_elements.dtprops = list(dtprops.values())
        schema_elements.oprops = list(oprops.values())

        self.rdf_schema = schema_elements
        return schema_elements

    def _query_sparql(self, query: str) -> dict:
        """Executes a SPARQL query against the Neptune database using SigV4 authentication.

        Args:
            query (str): The SPARQL query string to execute

        Returns:
            dict: The query results
        """
        logger.debug(f'Querying Neptune with SPARQL: {query}')
        s = SPARQLWrapper('')
        s.setQuery(query)
        query = ' '.join(line.strip() for line in query.splitlines())
        query_type = str(s.queryType).upper()
        headers = {}
        headers['Accept'] = 'application/json'
        if query_type in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']:
            logger.debug('_query_sparql query type: query')
            data = f'query={query}'
            headers['Content-Type'] = 'application/sparql-query'
        else:
            logger.debug('_query_sparql query type: query')
            data = f'update={query}'
            headers['Content-Type'] = 'application/sparql-update'

        url = f'{self.endpoint_url}/sparql'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = AWSRequest(method='POST', url=url, data=data, params=None, headers=headers)

        SigV4Auth(
            self.session.get_credentials(), 'neptunedata', self.session.region_name
        ).add_auth(request)

        resp = requests.request(method='POST', url=url, headers=dict(request.headers), data=data)

        logger.debug(f'Neptune response: {json.dumps(resp.text, indent=2)}')

        return json.loads(resp.text)
