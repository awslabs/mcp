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

"""Enhanced DBConnectionSingleton with connection pooling support."""

from typing import Optional, Union, Dict, Any
from loguru import logger
from .pool_manager import connection_pool_manager
from .rds_connector import RDSDataAPIConnector
from .postgres_connector import PostgreSQLConnector


class DBConnectionSingleton:
    """
    Enhanced singleton for database connections with pooling support.
    
    Maintains backward compatibility while adding connection pooling.
    """
    
    _instance = None
    
    def __init__(
        self,
        resource_arn: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region: str = "us-west-2",
        readonly: bool = True,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        is_test: bool = False
    ):
        """
        Initialize enhanced DB connection singleton.
        
        Args:
            resource_arn: ARN of the RDS resource
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region: AWS region
            readonly: Whether connection is read-only
            hostname: Database hostname (for direct connections)
            port: Database port (for direct connections)
            is_test: Whether this is a test connection
        """
        # Validate required parameters
        if not secret_arn:
            raise ValueError("secret_arn is required")
        
        if not database:
            raise ValueError("database is required")
        
        if not resource_arn and not hostname:
            raise ValueError("Either resource_arn or hostname must be provided")
        
        self.resource_arn = resource_arn
        self.secret_arn = secret_arn
        self.database = database
        self.region = region
        self.readonly = readonly
        self.hostname = hostname
        self.port = port or 5432
        self.is_test = is_test
        self._connection = None
        
        logger.info(f"Initialized DBConnectionSingleton with {'RDS Data API' if resource_arn else 'direct PostgreSQL'}")
    
    @classmethod
    def initialize(
        cls,
        resource_arn: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region: str = "us-west-2",
        readonly: bool = True,
        hostname: Optional[str] = None,
        port: Optional[int] = None,
        is_test: bool = False
    ):
        """
        Initialize the singleton instance if it doesn't exist.
        
        Args:
            resource_arn: ARN of the RDS resource
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region: AWS region
            readonly: Whether connection is read-only
            hostname: Database hostname (for direct connections)
            port: Database port (for direct connections)
            is_test: Whether this is a test connection
        """
        if cls._instance is None:
            cls._instance = cls(
                resource_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
                hostname=hostname,
                port=port,
                is_test=is_test
            )
            logger.info("DBConnectionSingleton initialized")
    
    @classmethod
    def get(cls):
        """
        Get the singleton instance.
        
        Returns:
            DBConnectionSingleton: The singleton instance
            
        Raises:
            RuntimeError: If the singleton has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError("DBConnectionSingleton is not initialized.")
        return cls._instance
    
    async def get_connection(self) -> Union[RDSDataAPIConnector, PostgreSQLConnector]:
        """
        Get a database connection from the pool.
        
        Returns:
            Database connection instance
            
        Raises:
            Exception: If connection cannot be obtained
        """
        if self._connection is None or not await self._connection.health_check():
            # Get new connection from pool
            self._connection = await connection_pool_manager.get_connection(
                secret_arn=self.secret_arn,
                region_name=self.region,
                resource_arn=self.resource_arn,
                database=self.database,
                hostname=self.hostname,
                port=self.port,
                readonly=self.readonly
            )
            logger.info("Obtained new connection from pool")
        
        return self._connection
    
    async def return_connection(self):
        """Return the current connection to the pool."""
        if self._connection:
            await connection_pool_manager.return_connection(self._connection)
            self._connection = None
            logger.debug("Returned connection to pool")
    
    @property
    def db_connection(self):
        """
        Get the database connection (backward compatibility).
        
        Returns:
            Database connection wrapper for backward compatibility
        """
        return DBConnectionWrapper(self)
    
    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            'resource_arn': self.resource_arn,
            'hostname': self.hostname,
            'port': self.port,
            'database': self.database,
            'region': self.region,
            'readonly': self.readonly,
            'connection_type': 'rds_data_api' if self.resource_arn else 'direct_postgres'
        }


class DBConnectionWrapper:
    """
    Wrapper class for backward compatibility with existing code.
    
    This class provides the same interface as the old DBConnection class
    while using the new pooled connection system underneath.
    """
    
    def __init__(self, singleton: DBConnectionSingleton):
        """
        Initialize the wrapper.
        
        Args:
            singleton: The DBConnectionSingleton instance
        """
        self.singleton = singleton
    
    @property
    def cluster_arn(self) -> Optional[str]:
        """Get cluster ARN (backward compatibility)."""
        return self.singleton.resource_arn
    
    @property
    def secret_arn(self) -> Optional[str]:
        """Get secret ARN."""
        return self.singleton.secret_arn
    
    @property
    def database(self) -> Optional[str]:
        """Get database name."""
        return self.singleton.database
    
    @property
    def readonly_query(self) -> bool:
        """Get readonly flag."""
        return self.singleton.readonly
    
    @property
    def data_client(self):
        """Get data client (for RDS Data API compatibility)."""
        # This is a placeholder - actual implementation would need to handle
        # the async nature of getting connections
        return None
