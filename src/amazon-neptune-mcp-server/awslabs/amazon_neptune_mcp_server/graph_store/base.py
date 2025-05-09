from abc import ABC, abstractmethod
from typing import Optional
from awslabs.amazon_neptune_mcp_server.models import GraphSchema

class NeptuneGraph(ABC):
    """
    Abstract base class for Neptune graph operations.
    
    This class defines the interface that all Neptune graph implementations
    must implement, providing a consistent API for different Neptune
    graph types (Database and Analytics).
    """
    
    @abstractmethod
    def get_schema(self) -> GraphSchema:
        """
        Retrieves the schema information for the graph.
        
        Returns:
            GraphSchema: Complete schema information for the graph
        """
        raise NotImplementedError()

    @abstractmethod
    def query_opencypher(self, query: str, params: Optional[dict] = None) -> dict:
        """
        Executes an openCypher query against the graph.
        
        Args:
            query (str): The openCypher query string to execute
            params (Optional[dict]): Optional parameters for the query
            
        Returns:
            dict: The query results
        """
        raise NotImplementedError()
    
    @abstractmethod
    def query_gremlin(self, query: str) -> dict:
        """
        Executes a Gremlin query against the graph.
        
        Args:
            query (str): The Gremlin query string to execute
            
        Returns:
            dict: The query results
        """
        raise NotImplementedError()