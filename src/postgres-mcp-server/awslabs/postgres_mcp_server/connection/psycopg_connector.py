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
parameters (host, port, database, user, password) or via AWS Secrets Manager.
"""

import asyncio
import boto3
import json
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple, Union

from awslabs.postgres_mcp_server.connection.connection_factory import AbstractDBConnection


class PsycopgPoolConnection(AbstractDBConnection):
    """Class that wraps DB connection using psycopg connection pool.
    
    This class can connect directly to any PostgreSQL database, including:
    - Aurora PostgreSQL (using the cluster endpoint)
    - RDS PostgreSQL (using the instance endpoint)
    - Self-hosted PostgreSQL
    
    It supports two authentication methods:
    1. Direct credentials (user and password)
    2. AWS Secrets Manager (secret_arn and region_name)
    """

    def __init__(
        self, 
        host: str,
        port: int,
        database: str,
        readonly: bool,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secret_arn: Optional[str] = None,
        region_name: Optional[str] = None,
        min_size: int = 1,
        max_size: int = 10,
        is_test: bool = False
    ):
        """Initialize a new DB connection pool.

        Args:
            host: Database host (Aurora cluster endpoint or RDS instance endpoint)
            port: Database port
            database: Database name
            readonly: Whether connections should be read-only
            user: Database user (optional if secret_arn is provided)
            password: Database password (optional if secret_arn is provided)
            secret_arn: ARN of the secret containing credentials (optional if user and password are provided)
            region_name: AWS region for Secrets Manager (required if secret_arn is provided)
            min_size: Minimum number of connections in the pool
            max_size: Maximum number of connections in the pool
            is_test: Whether this is a test connection
        """
        super().__init__(readonly)
        self.host = host
        self.port = port
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        
        # Get credentials from either direct parameters or Secrets Manager
        if user and password:
            logger.info("Using provided user and password credentials")
            self.user = user
            self.password = password
        elif secret_arn and region_name:
            logger.info(f"Retrieving credentials from Secrets Manager: {secret_arn}")
            self.user, self.password = self._get_credentials_from_secret(secret_arn, region_name, is_test)
            logger.info(f"Successfully retrieved credentials for user: {self.user}")
        else:
            raise ValueError("Either (user, password) or (secret_arn, region_name) must be provided")
        
        # Initialize the connection pool
        if not is_test:
            from psycopg_pool import ConnectionPool
            
            # Connection string (mask password in logs)
            masked_conninfo = f"host={host} port={port} dbname={database} user={self.user} password=******"
            self.conninfo = f"host={host} port={port} dbname={database} user={self.user} password={self.password}"
            
            logger.info(f"Initializing connection pool with: {masked_conninfo}")
            
            try:
                self.pool = ConnectionPool(
                    conninfo=self.conninfo,
                    min_size=min_size,
                    max_size=max_size,
                    # Configure additional pool settings
                    timeout=5.0,  # Connection timeout in seconds
                    max_idle=60.0,  # Max idle time for connections in seconds
                    reconnect_timeout=5.0,  # Time between reconnection attempts
                )
                # Open the pool with a shorter timeout for faster feedback
                logger.info("Opening connection pool...")
                self.pool.open(wait=True, timeout=5.0)
                logger.info("Connection pool opened successfully")
                
                # If readonly, set default transaction read only for all connections
                if readonly:
                    logger.info("Setting connections to read-only mode")
                    self._set_all_connections_readonly()
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {str(e)}")
                # Re-raise with more context
                raise ValueError(f"Failed to connect to database at {host}:{port}/{database}: {str(e)}")
    
    def _set_all_connections_readonly(self) -> None:
        """Set all connections in the pool to read-only mode."""
        try:
            with self.pool.connection(timeout=5.0) as conn:
                with conn.cursor() as cur:
                    cur.execute("ALTER ROLE CURRENT_USER SET default_transaction_read_only = on;")
                    logger.info("Successfully set connection to read-only mode")
        except Exception as e:
            logger.warning(f"Failed to set connections to read-only mode: {str(e)}")
            logger.warning("Continuing without setting read-only mode")
    
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
    
    def _get_credentials_from_secret(self, secret_arn: str, region_name: str, is_test: bool = False) -> Tuple[str, str]:
        """Get database credentials from AWS Secrets Manager.
        
        Args:
            secret_arn: ARN of the secret containing credentials
            region_name: AWS region for Secrets Manager
            is_test: Whether this is a test connection
            
        Returns:
            Tuple containing (username, password)
            
        Raises:
            ValueError: If the secret cannot be retrieved or doesn't contain the required fields
        """
        if is_test:
            return "test_user", "test_password"
        
        try:
            # Create a Secrets Manager client
            logger.info(f"Creating Secrets Manager client in region {region_name}")
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=region_name
            )
            
            # Get the secret value
            logger.info(f"Retrieving secret value for {secret_arn}")
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_arn
            )
            logger.info("Successfully retrieved secret value")
            
            # Parse the secret string
            if 'SecretString' in get_secret_value_response:
                secret = json.loads(get_secret_value_response['SecretString'])
                logger.info(f"Secret keys: {', '.join(secret.keys())}")
                
                # Extract username and password
                # The keys can vary depending on how the secret was created
                username = secret.get('username') or secret.get('user') or secret.get('Username')
                password = secret.get('password') or secret.get('Password')
                
                if not username:
                    logger.error(f"Username not found in secret. Available keys: {', '.join(secret.keys())}")
                    raise ValueError(f"Secret does not contain username. Available keys: {', '.join(secret.keys())}")
                
                if not password:
                    logger.error("Password not found in secret")
                    raise ValueError(f"Secret does not contain password. Available keys: {', '.join(secret.keys())}")
                
                logger.info(f"Successfully extracted credentials for user: {username}")
                return username, password
            else:
                logger.error("Secret does not contain a SecretString")
                raise ValueError("Secret does not contain a SecretString")
        except Exception as e:
            logger.error(f"Error retrieving secret: {str(e)}")
            raise ValueError(f"Failed to retrieve credentials from Secrets Manager: {str(e)}")
    
    def close(self) -> None:
        """Close the connection pool."""
        if hasattr(self, 'pool'):
            self.pool.close()
