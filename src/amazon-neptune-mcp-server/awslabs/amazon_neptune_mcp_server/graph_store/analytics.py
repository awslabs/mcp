import boto3
import json
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.graph_store import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.models import (
    GraphSchema,
    Node,
    Property,
    Relationship,
    RelationshipPattern,
)
from loguru import logger
from typing import Optional


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

    schema: Optional[GraphSchema] = None

    def __init__(
        self, graph_identifier: str, credentials_profile_name: Optional[str] = None
    ) -> None:
        """Create a new Neptune Analytics graph wrapper instance."""
        self.graph_identifier = graph_identifier

        try:
            if not credentials_profile_name:
                session = boto3.Session()
            else:
                session = boto3.Session(profile_name=credentials_profile_name)

            self.client = session.client('neptune-graph')

        except Exception as e:
            logger.exception(
                'Could not load credentials to authenticate with AWS client. Please check that credentials in the specified profile name are valid.'
            )
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

    def _refresh_schema(self) -> GraphSchema:
        """Refreshes the Neptune graph schema information.

        This method queries the Neptune Analytics graph to build a complete schema
        representation including nodes, relationships, and relationship patterns
        using the pg_schema procedure.

        Returns:
            GraphSchema: Complete schema information for the graph
        """
        pg_schema_query = """
        CALL neptune.graph.pg_schema()
        YIELD schema
        RETURN schema
        """

        data = self.query_opencypher(pg_schema_query)
        raw_schema = data[0]['schema']
        graph = GraphSchema(nodes=[], relationships=[], relationship_patterns=[])

        # Process relationship patterns
        for i in raw_schema['labelTriples']:
            graph.relationship_patterns.append(
                RelationshipPattern(left_node=i['~from'], relation=i['~type'], right_node=i['~to'])
            )

        # Process node labels and properties
        for l in raw_schema['nodeLabels']:
            details = raw_schema['nodeLabelDetails'][l]
            props = []
            for p in details['properties']:
                props.append(Property(name=p, type=details['properties'][p]['datatypes']))
            graph.nodes.append(Node(labels=l, properties=props))

        # Process edge labels and properties
        for l in raw_schema['edgeLabels']:
            details = raw_schema['edgeLabelDetails'][l]
            props = []
            for p in details['properties']:
                props.append(Property(name=p, type=details['properties'][p]['datatypes']))
            graph.relationships.append(Relationship(type=l, properties=props))
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
        """Executes an openCypher query against the Neptune Analytics graph.

        Args:
            query (str): The openCypher query string to execute
            params (Optional[dict]): Optional parameters for the query, defaults to None

        Returns:
            Any: The query results as a list

        Raises:
            NeptuneException: If an error occurs during query execution
        """
        try:
            if params is None:
                params = {}
            resp = self.client.execute_query(
                graphIdentifier=self.graph_identifier,
                queryString=query,
                parameters=params,
                language='OPEN_CYPHER',
            )
            return json.loads(resp['payload'].read().decode('UTF-8'))['results']
        except Exception as e:
            raise NeptuneException(
                {
                    'message': 'An error occurred while executing the query.',
                    'details': str(e),
                }
            )

    def query_gremlin(self, query: str):
        """Not supported for Neptune Analytics graphs.

        Args:
            query (str): The Gremlin query string

        Raises:
            NotImplementedError: Always raised as Gremlin is not supported for Neptune Analytics
        """
        raise NotImplementedError(
            'Gremlin queries are not supported for Neptune Analytics graphs.'
        )
