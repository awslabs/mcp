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

"""Unified connection manager that supports both RDS Data API and Direct PostgreSQL connections."""

import boto3
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from botocore.exceptions import BotoCoreError

from .connection.connection_factory import ConnectionFactory
from .connection.postgres_connector import PostgreSQLConnector


class UnifiedDBConnection:
    """Unified database connection that supports both RDS Data API and Direct PostgreSQL."""
    
    def __init__(
        self,
        connection_type: str,
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        port: int = 5432,
        secret_arn: str = None,
        database: str = None,
        region: str = None,
        readonly: bool = True,
        is_test: bool = False
    ):
        """
        Initialize unified database connection.
        
        Args:
            connection_type: 'rds_data_api' or 'direct_postgres'
            resource_arn: ARN of RDS cluster (for RDS Data API)
            hostname: Database hostname (for direct PostgreSQL)
            port: Database port (for direct PostgreSQL)
            secret_arn: ARN of secret containing credentials
            database: Database name
            region: AWS region
            readonly: Whether connection is read-only
            is_test: Whether this is a test connection
        """
        self.connection_type = connection_type
        self.resource_arn = resource_arn
        self.hostname = hostname
        self.port = port
        self.secret_arn = secret_arn
        self.database = database
        self.region = region
        self.readonly = readonly
        self.is_test = is_test
        
        # Initialize the appropriate connection
        if connection_type == "rds_data_api":
            self._init_rds_data_api()
        elif connection_type == "direct_postgres":
            self._init_direct_postgres()
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")
    
    def _init_rds_data_api(self):
        """Initialize RDS Data API connection."""
        if not all([self.resource_arn, self.secret_arn, self.database, self.region]):
            raise ValueError(
                'Missing required RDS Data API parameters. '
                'Please provide resource_arn, secret_arn, database, and region.'
            )
        
        if not self.is_test:
            self.data_client = boto3.client('rds-data', region_name=self.region)
        
        logger.info(f"Initialized RDS Data API connection to {self.resource_arn}")
    
    def _init_direct_postgres(self):
        """Initialize Direct PostgreSQL connection."""
        if not all([self.hostname, self.secret_arn, self.database, self.region]):
            raise ValueError(
                'Missing required Direct PostgreSQL parameters. '
                'Please provide hostname, secret_arn, database, and region.'
            )
        
        self.postgres_connector = PostgreSQLConnector(
            hostname=self.hostname,
            database=self.database,
            secret_arn=self.secret_arn,
            region_name=self.region,
            port=self.port,
            readonly=self.readonly
        )
        
        logger.info(f"Initialized Direct PostgreSQL connection to {self.hostname}:{self.port}")
    
    async def execute_query(
        self,
        sql: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query using the appropriate connection method.
        
        Args:
            sql: SQL query to execute
            parameters: Query parameters
            
        Returns:
            Query result in RDS Data API format (for compatibility)
        """
        if self.connection_type == "rds_data_api":
            return await self._execute_rds_data_api(sql, parameters)
        elif self.connection_type == "direct_postgres":
            return await self._execute_direct_postgres(sql, parameters)
        else:
            raise ValueError(f"Unsupported connection type: {self.connection_type}")
    
    async def _execute_rds_data_api(
        self,
        sql: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute query using RDS Data API."""
        try:
            execute_params = {
                'resourceArn': self.resource_arn,
                'secretArn': self.secret_arn,
                'database': self.database,
                'sql': sql,
                'includeResultMetadata': True
            }
            
            if parameters:
                execute_params['parameters'] = parameters
            
            # Execute in thread to avoid blocking
            response = await asyncio.to_thread(
                self.data_client.execute_statement,
                **execute_params
            )
            
            return response
            
        except Exception as e:
            logger.error(f"RDS Data API query failed: {str(e)}")
            raise
    
    async def _execute_direct_postgres(
        self,
        sql: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute query using Direct PostgreSQL connection."""
        try:
            return await self.postgres_connector.execute_query(sql, parameters)
        except Exception as e:
            logger.error(f"Direct PostgreSQL query failed: {str(e)}")
            raise
    
    async def test_connection(self) -> bool:
        """Test the database connection without full initialization."""
        try:
            if self.connection_type == "rds_data_api":
                # For RDS Data API, just test with a simple query
                result = await self.execute_query("SELECT 1 as test")
                return len(result.get('records', [])) > 0
            elif self.connection_type == "direct_postgres":
                # For Direct PostgreSQL, just validate parameters
                return await self.postgres_connector.test_connection_parameters()
            else:
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def close(self):
        """Close the database connection."""
        if self.connection_type == "direct_postgres" and hasattr(self, 'postgres_connector'):
            await self.postgres_connector.disconnect()
        # RDS Data API doesn't need explicit closing
    
    @property
    def readonly_query(self) -> bool:
        """Get whether this connection is read-only."""
        return self.readonly


class UnifiedDBConnectionSingleton:
    """Manages a single UnifiedDBConnection instance across the application."""

    _instance = None

    def __init__(
        self,
        connection_type: str,
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        port: int = 5432,
        secret_arn: str = None,
        database: str = None,
        region: str = None,
        readonly: bool = True,
        is_test: bool = False
    ):
        """Initialize a new unified DB connection singleton."""
        self._db_connection = UnifiedDBConnection(
            connection_type=connection_type,
            resource_arn=resource_arn,
            hostname=hostname,
            port=port,
            secret_arn=secret_arn,
            database=database,
            region=region,
            readonly=readonly,
            is_test=is_test
        )

    @classmethod
    def initialize(
        cls,
        connection_type: str,
        resource_arn: Optional[str] = None,
        hostname: Optional[str] = None,
        port: int = 5432,
        secret_arn: str = None,
        database: str = None,
        region: str = None,
        readonly: bool = True,
        is_test: bool = False
    ):
        """Initialize the singleton instance if it doesn't exist."""
        if cls._instance is None:
            cls._instance = cls(
                connection_type=connection_type,
                resource_arn=resource_arn,
                hostname=hostname,
                port=port,
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
            raise RuntimeError('UnifiedDBConnectionSingleton is not initialized.')
        return cls._instance

    @property
    def db_connection(self):
        """Get the database connection."""
        return self._db_connection
