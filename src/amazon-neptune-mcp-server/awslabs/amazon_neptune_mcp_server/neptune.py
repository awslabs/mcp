#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
"""Neptune Database Interface Module.

This module provides a high-level interface for interacting with Amazon Neptune databases
through the Amazon Q framework. It supports both Neptune Analytics and Neptune Database
instances, handling connection management, query execution, and schema operations.

The module implements classes for managing Neptune connections and executing queries
using different query languages (OpenCypher and Gremlin).
"""

from awslabs.amazon_neptune_mcp_server.graph_store import (
    NeptuneAnalytics,
    NeptuneDatabase,
    NeptuneGraph,
)
from awslabs.amazon_neptune_mcp_server.models import GraphSchema
from loguru import logger
from typing import Optional


class NeptuneServer:
    """A unified interface for interacting with Amazon Neptune instances.

    This class manages connections to both Neptune Analytics and Neptune Database instances,
    providing methods for querying and schema management. It automatically determines
    the appropriate engine type based on the provided endpoint.

    Attributes:
        graph: Active connection to the Neptune instance
    """

    graph: NeptuneGraph

    def __init__(self, endpoint: str, use_https: bool = True, port: int = 8182, *args, **kwargs):
        """Initialize a connection to a Neptune instance.

        Args:
            endpoint (str): Neptune endpoint URL (must start with neptune-db:// or neptune-graph://)
            use_https (bool, optional): Whether to use HTTPS connection. Defaults to True.
            port (int, optional): Port number for connection. Defaults to 8182.
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Raises:
            ValueError: If endpoint is not provided or has invalid format
        """
        if endpoint:
            # self._logger.debug("NeptuneServer host: %s", endpoint)
            if endpoint.startswith('neptune-db://'):
                # This is a Neptune Database Cluster
                endpoint = endpoint.replace('neptune-db://', '')
                self.graph = NeptuneDatabase(endpoint, port, use_https=use_https)
                logger.debug('Creating Neptune Database session for %s', endpoint)
            elif endpoint.startswith('neptune-graph://'):
                # This is a Neptune Analytics Graph
                graphId = endpoint.replace('neptune-graph://', '')
                self.graph = NeptuneAnalytics(graphId)
                logger.debug('Creating Neptune Graph session for %s', endpoint)
            else:
                raise ValueError(
                    'You must provide an endpoint to create a NeptuneServer as either neptune-db://<endpoint> or neptune-graph://<graphid>'
                )
        else:
            raise ValueError('You must provide an endpoint to create a NeptuneServer')

    def status(self) -> str:
        """Check the current status of the Neptune instance.

        Returns:
            str: Status of the Neptune instance ("Available" or "Unavailable")

        Raises:
            AttributeError: If engine type is unknown
        """
        try:
            self.query_opencypher('RETURN 1')
            return 'Available'
        except Exception:
            logger.exception('Could not get status for Neptune instance')
            return 'Unavailable'

    def schema(self) -> GraphSchema:
        """Retrieve the schema information from the Neptune instance.

        Returns:
            GraphSchema: Complete schema information for the graph

        Raises:
            AttributeError: If engine type is unknown
        """
        return self.graph.get_schema()

    def query_opencypher(self, query: str, parameters: Optional[dict] = None) -> dict:
        """Execute an openCypher query against the Neptune instance.

        Args:
            query (str): The openCypher query string to execute
            parameters (map, optional): Query parameters. Defaults to None.

        Returns:
            str: Query results

        Raises:
            ValueError: If using unsupported query language for analytics
        """
        return self.graph.query_opencypher(query, parameters)

    def query_gremlin(self, query: str) -> dict:
        """Execute an Gremlin query against the Neptune instance.

        Args:
            query (str): The Gremlin query string to execute
        Returns:
            str: Query results

        Raises:
            ValueError: If using unsupported query language for analytics
        """
        return self.graph.query_gremlin(query)
