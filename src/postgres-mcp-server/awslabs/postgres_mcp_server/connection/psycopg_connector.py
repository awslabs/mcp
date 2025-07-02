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

"""Psycopg connector for postgres MCP Server.

This connector provides direct connection to PostgreSQL databases using psycopg.
It supports both Aurora PostgreSQL and RDS PostgreSQL instances via direct connection
parameters (host, port, database, user, password).
"""

import asyncio
from loguru import logger
from typing import Any, Dict, List, Optional

from awslabs.postgres_mcp_server.connection.connection_factory import AbstractDBConnection


class PsycopgPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using psycopg connection pool.
    
    This class can connect directly to any PostgreSQL database, including:
    - Aurora PostgreSQL (using the cluster endpoint)
    - RDS PostgreSQL (using the instance endpoint)
    - Self-hosted PostgreSQL
    """

    def __init__(
        self, 
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        readonly: bool,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False
    ):
        """Initialize a new DB connection pool.

        Args:
            host: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            readonly: Whether connections should be read-only
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
            is_test: Whether this is a test connection
        """
        super().__init__(readonly)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_size = min_size
        self.max_size = max_size
        
        # Initialize the connection pool
        if not is_test:
            from psycopg_pool import ConnectionPool
            
            # Connection string
            self.conninfo = f"host={host} port={port} dbname={database} user={user} password={password}"
            
            self.pool = ConnectionPool(
                conninfo=self.conninfo,
                min_size=min_size,
                max_size=max_size,
                # Configure additional pool settings as needed
                # timeout=10.0,  # Connection timeout in seconds
                # max_idle=60.0,  # Max idle time for connections in seconds
                # reconnect_timeout=5.0,  # Time between reconnection attempts
            )
            # Open the pool
            self.pool.open()
            
            # If readonly, set default transaction read only for all connections
            if readonly:
                self._set_all_connections_readonly()
    
    def _set_all_connections_readonly(self) -> None:
        """Set all connections in the pool to read-only mode."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER ROLE CURRENT_USER SET default_transaction_read_only = on;")
    
    async def execute_query(
        self, 
        sql: str, 
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query using the connection pool.
        
        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query
            
        Returns:
            Dict containing query results with column metadata and records
        """
        return await asyncio.to_thread(
            self._execute_query_sync, sql, parameters, self.readonly_query
        )
    
    def _execute_query_sync(
        self, 
        sql: str, 
        parameters: Optional[List[Dict[str, Any]]] = None,
        readonly: bool = False
    ) -> Dict[str, Any]:
        """Synchronous method to execute a query using the connection pool.
        
        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query
            readonly: Whether to execute in a read-only transaction
            
        Returns:
            Dict containing query results with column metadata and records
        """
        # Get a connection from the pool
        with self.pool.connection() as conn:
            try:
                # Begin transaction with appropriate mode
                with conn.transaction():
                    if readonly:
                        # Set transaction to read-only
                        with conn.cursor() as cur:
                            cur.execute("SET TRANSACTION READ ONLY")
                    
                    # Execute the query
                    with conn.cursor() as cur:
                        if parameters:
                            # Convert parameters to the format expected by psycopg
                            params = self._convert_parameters(parameters)
                            cur.execute(sql, params)
                        else:
                            cur.execute(sql)
                        
                        # If there are results to fetch
                        if cur.description:
                            # Get column names
                            columns = [desc[0] for desc in cur.description]
                            
                            # Fetch all rows
                            rows = cur.fetchall()
                            
                            # Format the response similar to RDS Data API
                            column_metadata = [{"name": col} for col in columns]
                            records = []
                            
                            # Convert each row to the expected format
                            for row in rows:
                                record = []
                                for value in row:
                                    if value is None:
                                        record.append({"isNull": True})
                                    elif isinstance(value, str):
                                        record.append({"stringValue": value})
                                    elif isinstance(value, int):
                                        record.append({"longValue": value})
                                    elif isinstance(value, float):
                                        record.append({"doubleValue": value})
                                    elif isinstance(value, bool):
                                        record.append({"booleanValue": value})
                                    elif isinstance(value, bytes):
                                        record.append({"blobValue": value})
                                    else:
                                        # Convert other types to string
                                        record.append({"stringValue": str(value)})
                                records.append(record)
                            
                            return {"columnMetadata": column_metadata, "records": records}
                        else:
                            # No results (e.g., for INSERT, UPDATE, etc.)
                            return {"columnMetadata": [], "records": []}
            except Exception as e:
                # Log the error and re-raise
                logger.error(f"Database query error: {str(e)}")
                raise e

    def _convert_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert query parameters from RDS Data API format to psycopg format.
        
        The RDS Data API uses a structured format with type information:
        [{'name': 'param1', 'value': {'stringValue': 'value1'}}, ...]
        
        Psycopg uses a simpler dictionary format:
        {'param1': 'value1', ...}
        
        This method handles the conversion between these formats to maintain
        a consistent parameter interface across both connection types.
        
        Args:
            parameters: List of parameter dictionaries in RDS Data API format
            
        Returns:
            Dictionary of parameters in psycopg format
        """
        result = {}
        for param in parameters:
            name = param.get('name')
            value = param.get('value', {})
            
            # Extract the value based on its type
            if 'stringValue' in value:
                result[name] = value['stringValue']
            elif 'longValue' in value:
                result[name] = value['longValue']
            elif 'doubleValue' in value:
                result[name] = value['doubleValue']
            elif 'booleanValue' in value:
                result[name] = value['booleanValue']
            elif 'blobValue' in value:
                result[name] = value['blobValue']
            elif 'isNull' in value and value['isNull']:
                result[name] = None
                
        return result
    
    def close(self) -> None:
        """Close the connection pool."""
        if hasattr(self, 'pool'):
            self.pool.close()
