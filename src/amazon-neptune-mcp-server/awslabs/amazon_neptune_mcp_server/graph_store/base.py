from abc import ABC, abstractmethod
from typing import Optional
from awslabs.amazon_neptune_mcp_server.models import GraphSchema

class NeptuneGraph(ABC):
    @abstractmethod
    def get_schema(self) -> GraphSchema:
        raise NotImplementedError()

    @abstractmethod
    def query_opencypher(self, query: str, params: Optional[dict] = None) -> dict:
        raise NotImplementedError()
    
    @abstractmethod
    def query_gremlin(self, query: str) -> dict:
        raise NotImplementedError()
