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

"""Database connection interfaces for postgres MCP Server."""

from abc import ABC, abstractmethod
from loguru import logger
from typing import Any, Dict, List, Optional


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
    async def close(self) -> None:
        """Close the database connection."""
        pass
        
    @abstractmethod
    async def check_connection_health(self) -> bool:
        """Check if the database connection is healthy.
        
        Returns:
            bool: True if the connection is healthy, False otherwise
        """
        pass


class DBConnectionSingleton:
    """Manages a single RDS Data API connection instance across the application."""

    _instance = None

    def __init__(self, 
                 resource_arn: str,
                 secret_arn: str,
                 database: str,
                 region: str,
                 readonly: bool = True,
                 is_test: bool = False):
        """Initialize a new DB connection singleton for RDS Data API.

        Args:
            resource_arn: The ARN of the RDS cluster
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only (default: True)
            is_test: Whether this is a test connection (default: False)
        """
        if not all([resource_arn, secret_arn, database, region]):
            raise ValueError(
                'Missing required connection parameters for RDS Data API. '
                'Please provide resource_arn, secret_arn, database, and region.'
            )
        
        # Import here to avoid circular imports
        from awslabs.postgres_mcp_server.connection.rds_connector import RDSDataAPIConnection
        
        self._db_connection = RDSDataAPIConnection(
            cluster_arn=resource_arn,
            secret_arn=secret_arn,
            database=database,
            region=region,
            readonly=readonly,
            is_test=is_test
        )

    @classmethod
    def initialize(cls, 
                  resource_arn: str,
                  secret_arn: str,
                  database: str,
                  region: str,
                  readonly: bool = True,
                  is_test: bool = False):
        """Initialize the singleton instance if it doesn't exist.
        
        Args:
            resource_arn: The ARN of the RDS cluster
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only (default: True)
            is_test: Whether this is a test connection (default: False)
        """
        if cls._instance is None:
            cls._instance = cls(
                resource_arn=resource_arn,
                secret_arn=secret_arn,
                database=database,
                region=region,
                readonly=readonly,
                is_test=is_test
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
            # Handle calling async close method from sync context
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, create a task
                    asyncio.create_task(cls._instance._db_connection.close())
                else:
                    # If we're in a sync context, run the coroutine to completion
                    loop.run_until_complete(cls._instance._db_connection.close())
            except Exception as e:
                logger.error(f"Error during connection cleanup: {str(e)}")
