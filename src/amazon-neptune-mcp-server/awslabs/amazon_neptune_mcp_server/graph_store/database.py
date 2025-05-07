from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph
from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException
from awslabs.amazon_neptune_mcp_server.models import GraphSchema
from typing import Optional 
import boto3
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
        
    def _refresh_schema(self):
        self.schema = self.get_schema()

    def get_schema(self) -> GraphSchema:
        return self.schema

    def query_opencypher(self, query, params = ...):
        raise NotImplementedError

    def query_gremlin(self, query, params = ...):
        raise NotImplementedError

    def query_sparql(self, query, params = ...):
        raise NotImplementedError

    def get_status(self):
        raise NotImplementedError

