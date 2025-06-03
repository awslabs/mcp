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
from abc import ABC, abstractmethod
from awslabs.amazon_neptune_mcp_server.models import GraphSchema
from typing import Optional


class NeptuneGraph(ABC):
    """Abstract base class for Neptune graph operations.

    This class defines the interface that all Neptune graph implementations
    must implement, providing a consistent API for different Neptune
    graph types (Database and Analytics).
    """

    @abstractmethod
    def get_schema(self) -> GraphSchema:
        """Retrieves the schema information for the graph.

        Returns:
            GraphSchema: Complete schema information for the graph
        """
        raise NotImplementedError()

    @abstractmethod
    def query_opencypher(self, query: str, params: Optional[dict] = None) -> dict:
        """Executes an openCypher query against the graph.

        Args:
            query (str): The openCypher query string to execute
            params (Optional[dict]): Optional parameters for the query

        Returns:
            dict: The query results
        """
        raise NotImplementedError()

    @abstractmethod
    def query_gremlin(self, query: str) -> dict:
        """Executes a Gremlin query against the graph.

        Args:
            query (str): The Gremlin query string to execute

        Returns:
            dict: The query results
        """
        raise NotImplementedError()
