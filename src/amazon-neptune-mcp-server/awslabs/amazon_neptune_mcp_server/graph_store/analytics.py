from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.models import GraphSchema, Relationship, RelationshipPattern, Property, Node
from typing import Optional
import boto3
import json
from loguru import logger


class NeptuneAnalytics(NeptuneGraph):
    """Neptune Analytics wrapper for graph operations.

    Args:
        graph_identifier: the graph identifier for a Neptune Analytics graph

    Example:
        .. code-block:: python

        graph = NeptuneAnalytics(
            graph_identifier='<my-graph-id>'
        )
    """
    schema:Optional[GraphSchema] = None

    def __init__(
        self,
        graph_identifier: str,
        credentials_profile_name: Optional[str] = None        
    ) -> None:
        """Create a new Neptune Analytics graph wrapper instance."""

        self.graph_identifier = graph_identifier

        try:
            if not credentials_profile_name:
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=credentials_profile_name)

            self.client = session.client("neptune-graph")

        except Exception as e:
            logger.exception("Could not load credentials to authenticate with AWS client. Please check that credentials in the specified profile name are valid.")
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
                })


    def _refresh_schema(self) -> GraphSchema:
        """
        Refreshes the Neptune graph schema information.
        """
        pg_schema_query = """
        CALL neptune.graph.pg_schema()
        YIELD schema
        RETURN schema
        """

        data = self.query_opencypher(pg_schema_query)
        print('Here')
        raw_schema = data[0]["schema"]
        graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

        # Process relationship patterns
        for i in raw_schema["labelTriples"]:
            graph.relationship_patterns.append(
                RelationshipPattern(
                    left_node=i["~from"], relation=i["~type"], right_node=i["~to"]
                )
            )

        # Process node labels and properties
        for l in raw_schema["nodeLabels"]:
            details = raw_schema["nodeLabelDetails"][l]
            props = []
            for p in details["properties"]:
                props.append(
                    Property(name=p, type=details["properties"][p]["datatypes"])
                )
            graph.nodes.append(Node(labels=l, properties=props))

        # Process edge labels and properties
        for l in raw_schema["edgeLabels"]:
            details = raw_schema["edgeLabelDetails"][l]
            props = []
            for p in details["properties"]:
                props.append(
                    Property(name=p, type=details["properties"][p]["datatypes"])
                )
            graph.relationships.append(Relationship(type=l, properties=props))
        self.schema = graph
        return graph

    def get_schema(self) -> GraphSchema:
        if self.schema is None:
            self._refresh_schema()
        return self.schema if self.schema else GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

    def query_opencypher(self, query:str, params: Optional[dict]= None):
        try:
            if params is None:
                params = {}
            resp = self.client.execute_query(
                    graphIdentifier=self.graph_identifier,
                    queryString=query,
                    parameters=params,
                    language="OPEN_CYPHER"
            )
            return json.loads(resp["payload"].read().decode("UTF-8"))["results"]
        except Exception as e:
            raise NeptuneException(
                {
                    "message": "An error occurred while executing the query.",
                    "details": str(e),
                }
            )

    def query_gremlin(self, query:str):
        raise NotImplementedError("Gremlin queries are not supported for Neptune Analytics graphs.")

    def query_sparql(self, query:str):
        raise NotImplementedError("SPARQL queries are not supported for Neptune Analytics graphs.")

    def get_status(self) -> str:
        try:
            self.query_opencypher("RETURN 1")
            return "Available"
        except Exception:
            return "Unavailable"