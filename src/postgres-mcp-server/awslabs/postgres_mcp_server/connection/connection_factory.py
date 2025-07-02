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

"""Database connection factory for postgres MCP Server."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from loguru import logger
from typing import Any, Dict, List, Optional


class ConnectionType(Enum):
    """Enum representing the type of database connection."""
    RDS_DATA_API = auto()
    PSYCOPG = auto()


class AbstractDBConnection(ABC):
    """Abstract base class for database connections."""

    def __init__(self, readonly: bool):
        """Initialize the database connection.
        
        Args:
            readonly: Whether the connection should be read-only
        """
        self._readonly = readonly

    @property
    def readonly_query(self) -> bool:
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self._readonly

    @abstractmethod
    async def execute_query(
        self, 
        sql: str, 
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query.
        
        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query
            
        Returns:
            Dict containing query results with column metadata and records
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass


class DBConnectionFactory:
    """Factory class for creating database connections."""
    
    @staticmethod
    def create_connection(
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region_name: Optional[str] = None,
        port: int = 5432,
        readonly: bool = True,
        **kwargs
    ) -> AbstractDBConnection:
        """Create a database connection based on the provided parameters.
        
        This method will determine which connection type to use based on the
        parameters provided:
        - If resource_arn is provided, it will use RDS Data API
        - If hostname is provided, it will use direct psycopg connection
        
        Args:
            resource_arn: ARN of the RDS cluster (for RDS Data API)
            hostname: Database host (for psycopg)
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region_name: AWS region (for RDS Data API)
            port: Database port (for psycopg, default: 5432)
            readonly: Whether the connection should be read-only (default: True)
            **kwargs: Additional connection parameters
            
        Returns:
            An instance of AbstractDBConnection
            
        Raises:
            ValueError: If required parameters are missing
        """
        # Import here to avoid circular imports
        from awslabs.postgres_mcp_server.connection.rds_connector import RDSDataAPIConnection
        from awslabs.postgres_mcp_server.connection.psycopg_connector import PsycopgPoolConnection
        
        # Validate that secret_arn is provided
        if not secret_arn:
            raise ValueError("Missing required parameter: secret_arn")
            
        # Validate that database is provided
        if not database:
            raise ValueError("Missing required parameter: database")
        
        # Check if RDS Data API parameters are provided
        if resource_arn:
            # Validate region_name for RDS Data API
            if not region_name:
                raise ValueError("Missing required parameter for RDS Data API: region_name")
            
            # Create RDS Data API connection
            return RDSDataAPIConnection(
                cluster_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region=region_name,
                readonly=readonly,
                is_test=kwargs.get('is_test', False)
            )
        elif hostname:
            # For psycopg, we can use either direct credentials or get them from Secrets Manager
            user = kwargs.get('user')
            password = kwargs.get('password')
            
            try:
                # Try to create psycopg connection with appropriate parameters
                logger.info(f"Attempting to connect to PostgreSQL at {hostname}:{port}/{database} using psycopg")
                return PsycopgPoolConnection(
                    host=hostname,
                    port=port,
                    database=database,
                    readonly=readonly,
                    user=user,
                    password=password,
                    secret_arn=secret_arn,
                    region_name=region_name,
                    min_size=kwargs.get('min_pool_size', 1),
                    max_size=kwargs.get('max_pool_size', 10),
                    is_test=kwargs.get('is_test', False)
                )
            except Exception as e:
                # If resource_arn is provided, fall back to RDS Data API
                if resource_arn:
                    logger.warning(f"Failed to connect using psycopg: {str(e)}")
                    logger.warning(f"Falling back to RDS Data API with resource_arn: {resource_arn}")
                    
                    # Import here to avoid circular imports
                    from awslabs.postgres_mcp_server.connection.rds_connector import RDSDataAPIConnection
                    
                    return RDSDataAPIConnection(
                        cluster_arn=resource_arn,
                        secret_arn=secret_arn,
                        database=database,
                        region=region_name,
                        readonly=readonly,
                        is_test=kwargs.get('is_test', False)
                    )
                else:
                    # Re-raise the exception if we can't fall back
                    logger.error(f"Failed to connect using psycopg and no resource_arn provided for fallback: {str(e)}")
                    raise
        else:
            raise ValueError("Either resource_arn or hostname must be provided")


class DBConnectionSingleton:
    """Manages a single DBConnection instance across the application."""

    _instance = None

    def __init__(self, 
                 resource_arn: Optional[str] = None,
                 hostname: Optional[str] = None,
                 secret_arn: Optional[str] = None,
                 database: Optional[str] = None,
                 region_name: Optional[str] = None,
                 port: int = 5432,
                 readonly: bool = True,
                 **kwargs):
        """Initialize a new DB connection singleton.

        Args:
            resource_arn: ARN of the RDS cluster (for RDS Data API)
            hostname: Database host (for psycopg)
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region_name: AWS region (for RDS Data API)
            port: Database port (for psycopg, default: 5432)
            readonly: Whether the connection should be read-only (default: True)
            **kwargs: Additional connection parameters
        """
        self._db_connection = DBConnectionFactory.create_connection(
            resource_arn=resource_arn,
            hostname=hostname,
            secret_arn=secret_arn,
            database=database,
            region_name=region_name,
            port=port,
            readonly=readonly,
            **kwargs
        )

    @classmethod
    def initialize(cls, 
                  resource_arn: Optional[str] = None,
                  hostname: Optional[str] = None,
                  secret_arn: Optional[str] = None,
                  database: Optional[str] = None,
                  region_name: Optional[str] = None,
                  port: int = 5432,
                  readonly: bool = True,
                  **kwargs):
        """Initialize the singleton instance if it doesn't exist.
        
        Args:
            resource_arn: ARN of the RDS cluster (for RDS Data API)
            hostname: Database host (for psycopg)
            secret_arn: ARN of the secret containing credentials
            database: Database name
            region_name: AWS region (for RDS Data API)
            port: Database port (for psycopg, default: 5432)
            readonly: Whether the connection should be read-only (default: True)
            **kwargs: Additional connection parameters
        """
        if cls._instance is None:
            cls._instance = cls(
                resource_arn=resource_arn,
                hostname=hostname,
                secret_arn=secret_arn,
                database=database,
                region_name=region_name,
                port=port,
                readonly=readonly,
                **kwargs
            )

    @classmethod
    def get(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            raise RuntimeError('DBConnectionSingleton is not initialized.')
        return cls._instance

    @property
    def db_connection(self):
        """Get the database connection."""
        return self._db_connection
    
    @classmethod
    def cleanup(cls):
        """Clean up resources when shutting down."""
        if cls._instance and cls._instance._db_connection:
            cls._instance._db_connection.close()
