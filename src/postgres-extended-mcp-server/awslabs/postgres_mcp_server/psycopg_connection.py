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

"""PostgreSQL direct connection using psycopg3."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, Dict, Any, AsyncGenerator, List
from psycopg_pool import AsyncConnectionPool
from loguru import logger
import asyncio
import boto3
import json


@dataclass
class PostgresConfig:
    """Configuration for PostgreSQL connection."""
    reader_endpoint: str
    writer_endpoint: str
    port: int
    database: str
    secret_arn: str
    region: str
    readonly: bool = True
    min_connections: int = 1
    max_connections: int = 10
    connect_timeout: int = 10


class PostgresDirectConnection:
    """PostgreSQL connection using psycopg3."""

    def __init__(self, config: PostgresConfig):
        """Initialize the connection pool manager.

        Args:
            config: PostgreSQL connection configuration
        """
        self.config = config
        self._pool = None
        self._session_stats: Dict[str, Dict[str, Any]] = {}
        self._credentials = None

    async def _get_credentials(self) -> Dict[str, str]:
        """Get credentials from AWS Secrets Manager.
        
        Returns:
            Dictionary containing username and password
            
        Raises:
            Exception: If the secret cannot be retrieved
        """
        if self._credentials is None:
            client = boto3.client('secretsmanager', region_name=self.config.region)
            response = client.get_secret_value(SecretId=self.config.secret_arn)
            secret_string = response['SecretString']
            secret = json.loads(secret_string)
            
            username = secret.get('username')
            password = secret.get('password')
            
            if not username or not password:
                raise ValueError('Secret does not contain username or password')
                
            self._credentials = {'username': username, 'password': password}
            
        return self._credentials

    async def initialize(self) -> None:
        """Initialize and test the connection pool.

        Raises:
            Exception: If connection pool initialization fails
        """
        try:
            # Get credentials from Secrets Manager
            credentials = await self._get_credentials()
            
            # Choose endpoint based on readonly flag
            endpoint = None
            if self.config.readonly:
                if not self.config.reader_endpoint:
                    raise ValueError('Reader endpoint is required for readonly operations')
                endpoint = self.config.reader_endpoint
                logger.info(f'Initializing connection pool to reader endpoint: {endpoint}')
            else:
                if not self.config.writer_endpoint:
                    raise ValueError('Writer endpoint is required for write operations')
                endpoint = self.config.writer_endpoint
                logger.info(f'Initializing connection pool to writer endpoint: {endpoint}')
            
            self._pool = AsyncConnectionPool(
                conninfo=self._build_conninfo(endpoint, credentials),
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                open=True,
                configure=self._configure_connection
            )
            # Test connection
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT 1')
                    await cur.fetchone()
            logger.info('Successfully initialized PostgreSQL connection pool')
        except Exception as e:
            logger.error(f'Failed to initialize connection pool: {str(e)}')
            raise

    def _build_conninfo(self, endpoint: str, credentials: Dict[str, str]) -> str:
        """Build the PostgreSQL connection string.

        Args:
            endpoint: The endpoint to connect to (reader or writer)
            credentials: Dictionary containing username and password

        Returns:
            Connection string with all necessary parameters
        """
        params = {
            'host': endpoint,
            'port': self.config.port,
            'dbname': self.config.database,
            'user': credentials['username'],
            'password': credentials['password'],
            'connect_timeout': self.config.connect_timeout
        }
        
        return ' '.join(f'{k}={v}' for k, v in params.items())

    async def _configure_connection(self, conn) -> None:
        """Configure a new connection.

        Args:
            conn: psycopg connection to configure
        """
        if self.config.readonly:
            async with conn.cursor() as cur:
                await cur.execute('SET default_transaction_read_only = on')

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.config.readonly

    @property
    def is_connected(self) -> bool:
        """Check if the pool is initialized and connected.

        Returns:
            bool: True if connected, False otherwise
        """
        return self._pool is not None

    @asynccontextmanager
    async def session_connection(self, session_id: str) -> AsyncGenerator:
        """Get a connection from the pool with session context.

        Args:
            session_id: Client session identifier

        Yields:
            An active database connection configured for the session

        Raises:
            RuntimeError: If the pool hasn't been initialized
        """
        if session_id not in self._session_stats:
            self._session_stats[session_id] = {'queries': 0, 'last_used': None}

        try:
            async with self._pool.connection() as conn:
                # Set session-specific parameters
                async with conn.cursor() as cur:
                    # Set application name to session ID for monitoring
                    await cur.execute('SET application_name = %s', (session_id,))

                self._session_stats[session_id]['queries'] += 1
                self._session_stats[session_id]['last_used'] = asyncio.get_event_loop().time()
                
                yield conn
        except Exception as e:
            logger.error(f'Error in session {session_id}: {str(e)}')
            raise

    async def execute_query(
        self, 
        query: str, 
        session_id: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> list:
        """Execute a query in the context of a session.

        Args:
            query: SQL query to execute
            session_id: Client session identifier
            parameters: Query parameters (optional)

        Returns:
            Query results as a list of dictionaries

        Raises:
            Exception: If query execution fails
        """
        async with self.session_connection(session_id) as conn:
            async with conn.cursor() as cur:
                try:
                    if parameters:
                        # Convert RDS Data API parameters to psycopg3 format
                        psycopg_params = self._convert_parameters(parameters)
                        await cur.execute(query, psycopg_params)
                    else:
                        await cur.execute(query)
                    
                    if cur.description:
                        columns = [desc.name for desc in cur.description]
                        rows = await cur.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    return []
                except Exception as e:
                    logger.error(f'Query execution failed for session {session_id}: {str(e)}')
                    raise

    def _convert_parameters(self, rds_parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert RDS Data API parameters to psycopg3 format.

        Args:
            rds_parameters: Parameters in RDS Data API format

        Returns:
            Parameters in psycopg3 format
        """
        params = {}
        for param in rds_parameters:
            name = param['name']
            value_dict = param['value']
            
            # Extract the value based on its type
            for key in ('stringValue', 'longValue', 'doubleValue', 'booleanValue', 'isNull'):
                if key in value_dict:
                    if key == 'isNull' and value_dict[key]:
                        params[name] = None
                    else:
                        params[name] = value_dict[key]
                    break
        
        return params

    async def execute_readonly_query(
        self, 
        query: str, 
        session_id: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> list:
        """Execute a query under readonly transaction.

        Args:
            query: SQL query to execute
            session_id: Client session identifier
            parameters: Query parameters (optional)

        Returns:
            Query results as a list of dictionaries

        Raises:
            Exception: If query execution fails
        """
        async with self.session_connection(session_id) as conn:
            # Start a transaction
            async with conn.transaction():
                # Set transaction to read-only
                async with conn.cursor() as cur:
                    await cur.execute('SET TRANSACTION READ ONLY')
                    
                    # Execute the query
                    if parameters:
                        psycopg_params = self._convert_parameters(parameters)
                        await cur.execute(query, psycopg_params)
                    else:
                        await cur.execute(query)
                    
                    # Format and return results
                    if cur.description:
                        columns = [desc.name for desc in cur.description]
                        rows = await cur.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    return []

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific session.

        Args:
            session_id: Client session identifier

        Returns:
            Optional[Dict[str, Any]]: Session statistics if found, None otherwise
        """
        return self._session_stats.get(session_id)

    async def close(self) -> None:
        """Close the connection pool and clean up resources."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._session_stats.clear()
            logger.info('Connection pool closed and session stats cleared')
