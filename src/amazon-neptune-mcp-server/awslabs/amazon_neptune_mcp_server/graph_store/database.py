from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.models import GraphSchema, Relationship, RelationshipPattern, Node, Property
from typing import Any, Dict, List, Optional, Tuple 
import boto3
import json
from loguru import logger

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

    schema:Optional[GraphSchema] = None

    def __init__(
        self,
        host: str,
        port: int = 8182,
        use_https: bool = True,
        credentials_profile_name: Optional[str] = None
    ) -> None:
        """Create a new Neptune graph wrapper instance."""

        try:
            if not credentials_profile_name:
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=credentials_profile_name)

            client_params = {}
            protocol = "https" if use_https else "http"
            client_params["endpoint_url"] = f"{protocol}://{host}:{port}"
            self.client = session.client("neptunedata", **client_params)

        except Exception as e:
            logger.exception("Could not load credentials to authenticate with AWS client")
            raise ValueError(
                    "Could not load credentials to authenticate with AWS client. "
                    "Please check that credentials in the specified "
                    "profile name are valid."
                ) from e

        try:
            self._refresh_schema()
        except Exception as e:
            logger.exception("Could not get schema for Neptune database")
            raise NeptuneException(
                {
                    "message": "Could not get schema for Neptune database",
                    "detail": str(e),
                }
            )
           
    def _get_summary(self) -> Dict:
        try:
            response = self.client.get_propertygraph_summary()
        except Exception as e:
            raise NeptuneException(
                {
                    "message": (
                        "Summary API is not available for this instance of Neptune,"
                        "ensure the engine version is >=1.2.1.0"
                    ),
                    "details": str(e),
                }
            )

        try:
            summary = response["payload"]["graphSummary"]
        except Exception:
            raise NeptuneException(
                {
                    "message": "Summary API did not return a valid response.",
                    "details": response.content.decode(),
                }
            )
        else:
            return summary

    def _get_labels(self) -> Tuple[List[str], List[str]]:
        """Get node and edge labels from the Neptune statistics summary"""
        summary = self._get_summary()
        n_labels = summary["nodeLabels"]
        e_labels = summary["edgeLabels"]
        return n_labels, e_labels

    def _get_triples(self, e_labels: List[str]) -> List[RelationshipPattern]:
        triple_query = """
        MATCH (a)-[e:`{e_label}`]->(b)
        WITH a,e,b LIMIT 3000
        RETURN DISTINCT labels(a) AS from, type(e) AS edge, labels(b) AS to
        LIMIT 10
        """

        triple_schema:List[RelationshipPattern] = []
        for label in e_labels:
            q = triple_query.format(e_label=label)
            data = self.query_opencypher(q)
            for d in data:
                triple_schema.append(RelationshipPattern(left_node=d["from"][0], right_node=d["to"][0], relation=d["edge"]))

        return triple_schema

    def _get_node_properties(self, n_labels: List[str], types: Dict) -> List:
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
                for k, v in p["props"].items():
                    prop_type = types[type(v).__name__]
                    if k not in props:
                        props[k] = set([prop_type])
                    else:
                        props[k].update([prop_type])
            
            properties = []
            for k, v in props.items():
                properties.append(Property(name=k, type=list(v)))

            nodes.append(Node(labels=label, properties=properties))           
        return nodes

    def _get_edge_properties(self, e_labels: List[str], types: Dict[str, Any]) -> List:
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
                for k, v in p["props"].items():
                    prop_type = types[type(v).__name__]
                    if k not in props:
                        props[k] = set([prop_type])
                    else:
                        props[k].update([prop_type])
            
            properties = []
            for k, v in props.items():
                properties.append(Property(name=k, type=list(v)))

            edges.append(Relationship(type=label, properties=properties)) 

        return edges

    def _refresh_schema(self) -> GraphSchema:
        """
        Refreshes the Neptune graph schema information.
        """

        types = {
            "str": "STRING",
            "float": "DOUBLE",
            "int": "INTEGER",
            "list": "LIST",
            "dict": "MAP",
            "bool": "BOOLEAN",
        }
        n_labels, e_labels = self._get_labels()
        triple_schema = self._get_triples(e_labels)
        nodes = self._get_node_properties(n_labels, types)
        rels = self._get_edge_properties(e_labels, types)

        graph = GraphSchema(nodes=nodes, relationships=rels, relationship_patterns=triple_schema)

        self.schema = graph
        return graph


    def get_schema(self) -> GraphSchema:
        if self.schema is None:
            self._refresh_schema()
        return self.schema if self.schema else GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

    def query_opencypher(self, query:str, params:Optional[dict] = None):
        if params:
            resp = self.client.execute_open_cypher_query(
                            openCypherQuery=query,
                            parameters=json.dumps(params),
                        )
        else:
            resp = self.client.execute_open_cypher_query(openCypherQuery=query)

        return resp["result"] if "result" in resp else resp["results"]
    
    def query_gremlin(self, query):
        resp = self.client.execute_gremlin_query(gremlinQuery=query,
                    serializer="application/vnd.gremlin-v1.0+json")
        return resp["result"] if "result" in resp else resp["results"]

